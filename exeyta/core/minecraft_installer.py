# -*- coding: utf-8 -*-
"""Установка клиента Minecraft: версия, библиотеки, нативные, ресурсы.

Всё в отдельном QThread (см. workers/download_worker), с отменой и retry.
Клиент -> <game_dir>/versions/<id>/, ресурсы -> <game_dir>/assets/.
"""
import json
import re
import shutil
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen

from . import config as cfg

MANIFEST_URL = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
ASSET_BASE = "https://resources.download.minecraft.net"
UA = "ExeytaLauncher/1.0 (+https://t.me/exeyta)"


class Cancelled(Exception):
    pass


def _noop(*_a, **_k):
    pass


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------
def http_get(url: str, timeout=30) -> bytes:
    req = Request(url, headers={"User-Agent": UA})
    with urlopen(req, timeout=timeout) as resp:
        return resp.read()


def http_json(url: str, timeout=30):
    return json.loads(http_get(url, timeout).decode("utf-8"))


def download_file(url: str, dest: Path, cancel=None, progress=None):
    """Скачивает в dest атомарно (.part -> dest). Пропускает существующие."""
    dest = Path(dest)
    if dest.exists() and dest.stat().st_size > 0:
        if progress:
            progress(dest.stat().st_size, dest.stat().st_size)
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = Request(url, headers={"User-Agent": UA})
    tmp = dest.with_suffix(dest.suffix + ".part")
    with urlopen(req, timeout=60) as resp:
        total = int(resp.headers.get("Content-Length") or 0)
        done = 0
        with open(tmp, "wb") as f:
            while True:
                if cancel and cancel():
                    raise Cancelled()
                chunk = resp.read(256 * 1024)
                if not chunk:
                    break
                f.write(chunk)
                done += len(chunk)
                if progress:
                    progress(done, total)
    tmp.replace(dest)
    return dest


# ---------------------------------------------------------------------------
# Манифест версий
# ---------------------------------------------------------------------------
_manifest_cache = None


def fetch_manifest(force=False) -> dict:
    global _manifest_cache
    if _manifest_cache is not None and not force:
        return _manifest_cache
    cache = cfg.cache_dir() / "version_manifest_v2.json"
    try:
        data = http_json(MANIFEST_URL, timeout=20)
        try:
            cache.write_text(json.dumps(data), encoding="utf-8")
        except Exception:
            pass
    except Exception:
        if cache.exists():
            data = json.loads(cache.read_text(encoding="utf-8"))
        else:
            raise
    _manifest_cache = data
    return data


def _ver_sort_key(vid: str):
    m = re.match(r"^(\d+)\.(\d+)(?:\.(\d+))?$", vid)
    if m:
        return (1, int(m.group(1)), int(m.group(2)), int(m.group(3) or 0), "")
    return (0, 0, 0, 0, vid)


def list_all_versions(include_snapshots=True, force=False):
    """Все версии: релизы (по убыванию), затем снапшоты и старые версии.

    Снапшоты (24w14a и т.п.) и old_beta/old_alpha идут в манифесте
    хронологически (новые сверху) — сохраняем этот порядок.
    Дополнительно кэширует список и ПОСЛЕДНЮЮ обычную версию
    (latest_release.txt) — по ней определяется Java для снапшотов.
    """
    manifest = fetch_manifest(force=force)
    versions = manifest.get("versions", [])
    releases = [v for v in versions if v.get("type") == "release"]
    releases.sort(key=lambda v: _ver_sort_key(v.get("id", "")), reverse=True)
    snaps = [v for v in versions if v.get("type") == "snapshot"]
    olds = [v for v in versions
            if v.get("type") in ("old_beta", "old_alpha")]
    result = releases + (snaps + olds if include_snapshots else [])
    # кэш для оффлайна + «последняя обычная версия»
    try:
        cache = cfg.cache_dir()
        cache.joinpath("versions.json").write_text(
            json.dumps([v["id"] for v in result], ensure_ascii=False),
            encoding="utf-8")
        if releases:
            cache.joinpath("latest_release.txt").write_text(
                releases[0]["id"], encoding="utf-8")
    except Exception:
        pass
    return result


def list_release_versions(force=False):
    """Только релизы (совместимость со старыми вызовами)."""
    return list_all_versions(include_snapshots=False, force=force)


def cached_version_ids():
    try:
        cache = cfg.cache_dir() / "versions.json"
        if cache.exists():
            return json.loads(cache.read_text(encoding="utf-8"))
    except Exception:
        pass
    return []


def version_meta_url(version_id: str) -> str:
    manifest = fetch_manifest()
    for v in manifest.get("versions", []):
        if v.get("id") == version_id:
            return v["url"]
    raise RuntimeError("Версия %s не найдена в манифесте" % version_id)


# ---------------------------------------------------------------------------
# Rules (OS / features)
# ---------------------------------------------------------------------------
def rules_allow(rules) -> bool:
    """Оценка правил version.json для Windows без спец-фич."""
    if not rules:
        return True
    allowed = False
    for rule in rules:
        match = True
        osr = rule.get("os") or {}
        name = osr.get("name")
        if name and name != "windows":
            match = False
        arch = osr.get("arch")
        if arch and arch != "x86":
            match = False  # у нас x64
        feats = rule.get("features") or {}
        for _k, need in feats.items():
            # demo_user / has_custom_resolution / is_demo_user / has_quick_plays_support
            if bool(need):
                match = False
        if match:
            allowed = (rule.get("action", "allow") == "allow")
    return allowed


# ---------------------------------------------------------------------------
# Установка версии
# ---------------------------------------------------------------------------
def paths_for(version_id: str, game_dir: Path = None):
    gd = Path(game_dir) if game_dir else cfg.get_config().game_dir
    vdir = gd / "versions" / version_id
    return {
        "game_dir": gd,
        "version_dir": vdir,
        "json": vdir / ("%s.json" % version_id),
        "jar": vdir / ("%s.jar" % version_id),
        "natives": vdir / "natives",
        "libraries": gd / "libraries",
        "assets": gd / "assets",
    }


def is_client_installed(version_id: str, game_dir: Path = None) -> bool:
    p = paths_for(version_id, game_dir)
    if not (p["json"].exists() and p["jar"].exists() and p["jar"].stat().st_size > 1024):
        return False
    try:
        meta = json.loads(p["json"].read_text(encoding="utf-8"))
    except Exception:
        return False
    idx = meta.get("assets") or "legacy"
    if not (p["assets"] / "indexes" / (idx + ".json")).exists():
        return False
    return True


def load_meta(version_id: str, game_dir: Path = None) -> dict:
    p = paths_for(version_id, game_dir)
    if not p["json"].exists():
        raise RuntimeError("Клиент %s не установлен" % version_id)
    return json.loads(p["json"].read_text(encoding="utf-8"))


def _lib_artifact_url(lib: dict):
    """(path, url, size) артефакта библиотеки; url=None — скачивать нечего.

    Секция downloads есть, но downloads.artifact отсутствует/без url —
    типичный случай pom-only пакетов (org.lwjgl.lwjgl:lwjgl-platform),
    их jar отсутствует и на CDN Mojang: пропускаем, нативные качаются
    отдельно через classifiers.
    """
    dl = lib.get("downloads") or {}
    art = dl.get("artifact")
    if art is not None:
        if art.get("url") and art.get("path"):
            return art.get("path"), art["url"], art.get("size", 0)
        return None, None, 0
    # легаси-библиотеки без секции downloads — конструируем maven-путь
    name = lib.get("name", "")
    parts = name.split(":")
    if len(parts) >= 3:
        g, a, v = parts[0], parts[1], parts[2]
        classifier = (":" + parts[3]) if len(parts) > 3 else ""
        path = "%s/%s/%s/%s-%s%s.jar" % (g.replace(".", "/"), a, v, a, v, classifier)
        return path, "https://libraries.minecraft.net/" + path, 0
    return None, None, 0


def _natives_key(lib: dict) -> str:
    nat = lib.get("natives") or {}
    key = nat.get("windows") or ""
    return key.replace("${arch}", "64") if key else ""


def collect_tasks(meta: dict, p: dict):
    """Список задач скачивания клиента: [(kind, dest, url)]."""
    tasks = []
    # 1) client jar
    client = (meta.get("downloads") or {}).get("client") or {}
    if client.get("url"):
        tasks.append(("jar", p["jar"], client["url"]))

    # 2) библиотеки + нативные классификаторы
    for lib in meta.get("libraries", []):
        if not rules_allow(lib.get("rules")):
            continue
        _path, url, _size = _lib_artifact_url(lib)
        if url:
            tasks.append(("lib", p["libraries"] / _path, url))
        key = _natives_key(lib)
        if key:
            cls = ((lib.get("downloads") or {}).get("classifiers") or {}).get(key)
            if cls and cls.get("url"):
                tasks.append(("natives", p["libraries"] / cls["path"], cls["url"]))

    # 3) asset index
    aidx = meta.get("assetIndex") or {}
    idx_id = meta.get("assets") or "legacy"
    if aidx.get("url"):
        tasks.append(("asset_index", p["assets"] / "indexes" / (idx_id + ".json"),
                      aidx["url"]))

    # 4) logging config
    log = ((meta.get("logging") or {}).get("client") or {}).get("file") or {}
    if log.get("id") and log.get("url"):
        tasks.append(("logging", p["assets"] / "log_configs" / log["id"], log["url"]))
    return tasks


def _asset_tasks(p: dict):
    """Объекты ресурсов по скачанному индексу."""
    idx_files = list((p["assets"] / "indexes").glob("*.json"))
    if not idx_files:
        return []
    idx = json.loads(idx_files[0].read_text(encoding="utf-8"))
    tasks = []
    for _name, obj in (idx.get("objects") or {}).items():
        h = obj.get("hash", "")
        if len(h) < 2:
            continue
        dest = p["assets"] / "objects" / h[:2] / h
        tasks.append(("asset", dest, "%s/%s/%s" % (ASSET_BASE, h[:2], h)))
    return tasks


def _unzip_flat(jar_path: Path, dest: Path):
    """Плоская распаковка jar в каталог (только файлы, без META-INF)."""
    try:
        with zipfile.ZipFile(jar_path) as zf:
            for name in zf.namelist():
                if name.endswith("/") or name.startswith("META-INF/"):
                    continue
                with zf.open(name) as src, \
                        open(dest / Path(name).name, "wb") as dst:
                    shutil.copyfileobj(src, dst)
    except Exception:
        pass


def extract_natives(p: dict, meta: dict):
    """Распаковка нативных библиотек в versions/<id>/natives.

    Поддерживает оба формата:
      * классический (<=1.21.x): секции natives/classifiers у библиотек;
      * новый (26.x): отдельные jar'ы *-natives-windows.jar, перечисленные
        как обычные библиотеки (lwjgl 3.4.x, jtracy и т.п.).
    """
    natives_dir = Path(p["natives"])
    natives_dir.mkdir(parents=True, exist_ok=True)
    # уже распаковано?
    if any(natives_dir.glob("*.dll")) or any(natives_dir.glob("*.jnilib")):
        return natives_dir
    # 1) классический формат: classifiers
    for lib in meta.get("libraries", []):
        if not rules_allow(lib.get("rules")) or not _natives_key(lib):
            continue
        _path, url, _s = _lib_artifact_url(lib)
        cls = ((lib.get("downloads") or {}).get("classifiers") or {}).get(_natives_key(lib))
        if not cls:
            continue
        jar_path = p["libraries"] / cls["path"]
        if not jar_path.exists():
            continue
        excludes = (lib.get("extract") or {}).get("exclude") or []
        try:
            with zipfile.ZipFile(jar_path) as zf:
                for name in zf.namelist():
                    if name.endswith("/"):
                        continue
                    if any(name.startswith(ex) for ex in excludes):
                        continue
                    if name.startswith("META-INF/"):
                        continue
                    target = natives_dir / Path(name).name
                    with zf.open(name) as src, open(target, "wb") as dst:
                        shutil.copyfileobj(src, dst)
        except Exception:
            continue
    # 2) новый формат 26.x: *-natives-windows.jar (обычные библиотеки)
    if not any(natives_dir.glob("*.dll")):
        lib_root = Path(p["libraries"])
        for jar in sorted(lib_root.rglob("*-natives-windows.jar")):
            low = jar.name.lower()
            if "arm64" in low or "x86" in low or "apple" in low or "macos" in low:
                continue   # у нас Windows x64
            _unzip_flat(jar, natives_dir)
    return natives_dir


def install_version(version_id: str, progress=None, cancel=None,
                    game_dir: Path = None) -> dict:
    """Полная установка клиента. progress(stage='client', done, total, msg)."""
    progress = progress or _noop
    cancel = cancel or (lambda: False)

    p = paths_for(version_id, game_dir)
    p["version_dir"].mkdir(parents=True, exist_ok=True)

    # 1) version.json
    if not p["json"].exists() or p["json"].stat().st_size < 10:
        progress("client", 0, 1, "Метаданные версии %s..." % version_id)
        if cancel():
            raise Cancelled()
        url = version_meta_url(version_id)
        data = http_get(url)
        p["json"].write_bytes(data)
    meta = json.loads(p["json"].read_text(encoding="utf-8"))

    # 2) задачи
    tasks = collect_tasks(meta, p)
    total = len(tasks)
    done = 0
    progress("client", 0, max(total, 1), "Подготовка: %d файлов" % total)

    for kind, dest, url in tasks:
        if cancel():
            raise Cancelled()
        label = {
            "jar": "Клиент",
            "lib": "Библиотеки",
            "natives": "Нативные",
            "asset_index": "Индекс ресурсов",
            "logging": "Логирование",
        }.get(kind, kind)
        try:
            download_file(url, dest, cancel=cancel)
        except Cancelled:
            raise
        except Exception as e:
            code = getattr(e, "code", None)
            if code == 404 and kind in ("lib", "natives", "logging"):
                # отсутствует на CDN (pom-only и т.п.) — не критично
                done += 1
                progress("client", done, total, "%s: пропущен (%s)" %
                         (label, dest.name))
                continue
            if kind == "logging":
                pass  # не критично
            elif kind == "natives":
                pass
            else:
                raise RuntimeError("%s: %s (%s)" % (label, dest.name, e))
        done += 1
        progress("client", done, total, "%s: %s" % (label, dest.name))

    # 3) ресурсы
    atasks = _asset_tasks(p)
    if atasks:
        atotal = len(atasks)
        adone = 0
        progress("client", 0, atotal, "Ресурсы: %d файлов" % atotal)
        errors = 0
        for kind, dest, url in atasks:
            if cancel():
                raise Cancelled()
            try:
                download_file(url, dest, cancel=cancel)
            except Cancelled:
                raise
            except Exception:
                errors += 1
            adone += 1
            if adone % 5 == 0 or adone == atotal:
                progress("client", adone, atotal, "Ресурсы: %d/%d" % (adone, atotal))
        if errors and adone == errors:
            raise RuntimeError("Не удалось скачать ресурсы (%d файлов)" % errors)

    # 4) нативные
    progress("client", total, total, "Распаковка нативных библиотек...")
    extract_natives(p, meta)

    progress("client", 100, 100, "Клиент %s готов" % version_id)
    return meta

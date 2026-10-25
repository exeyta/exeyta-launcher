# -*- coding: utf-8 -*-
r"""Генератор команды запуска и .bat файлов игры.

Контракт (жёсткое требование):
    scripts/launch_<version>_<nick>.bat:
        @echo off
        chcp 65001 >nul
        set "JAVA_EXE=%~dp0..\runtime\jre21\bin\java.exe"
        "%JAVA_EXE%" -Xmx6G -XX:+UseG1GC ... --username "Nick" --uuid ... \
                     --accessToken 0 --userType legacy

Класспасс выносится в маленький jar с Class-Path манифеста (работает на
Java 8/17/21 и удерживает строку .bat далеко ниже лимита cmd 8191).
"""
import json
import re
import zipfile
from pathlib import Path
from urllib.parse import quote

from . import config as cfg
from .java_resolver import major_for
from .minecraft_installer import load_meta, paths_for, rules_allow, extract_natives

LAUNCHER_NAME = "ExeytaLauncher"
LAUNCHER_VERSION = "1.0.0"


# ---------------------------------------------------------------------------
# Основная команда
# ---------------------------------------------------------------------------
def _split_legacy_args(s: str):
    """minecraftArguments -> список (кавычки сохраняются для bat)."""
    out, cur, in_q = [], "", False
    for ch in s:
        if ch == '"':
            in_q = not in_q
            cur += ch
        elif ch.isspace() and not in_q:
            if cur:
                out.append(cur)
                cur = ""
        else:
            cur += ch
    if cur:
        out.append(cur)
    return out


def _jvm_args(meta: dict, placeholders: dict, natives_dir: Path, classpath_jar: Path):
    args = []
    raw = meta.get("arguments", {}).get("jvm") if isinstance(meta.get("arguments"), dict) else None
    if raw:
        for item in raw:
            if isinstance(item, str):
                args.append(item)
            elif isinstance(item, dict):
                if rules_allow(item.get("rules")):
                    v = item.get("value")
                    if isinstance(v, list):
                        args.extend(v)
                    elif isinstance(v, str):
                        args.append(v)
    else:
        # legacy (1.6 - 1.12): явные JVM-аргументы
        args = ["-Djava.library.path=${natives_directory}", "-cp", "${classpath}"]

    # подстановка плейсхолдеров (класспасс -> наш classpath jar)
    resolved = []
    for a in args:
        for k, v in placeholders.items():
            a = a.replace(k, v)
        resolved.append(a)

    # гарантируем classpath (jar с Class-Path манифестом), если его не задали
    has_cp = any(x in ("-cp", "-classpath") for x in resolved)
    if not has_cp:
        resolved += ["-cp", str(classpath_jar)]
    else:
        out, i = [], 0
        while i < len(resolved):
            x = resolved[i]
            if x in ("-cp", "-classpath"):
                out.append(x)
                # всегда подставляем наш classpath jar
                out.append(str(classpath_jar))
                i += 2
                continue
            out.append(x)
            i += 1
        resolved = out

    # гарантируем -Djava.library.path=<natives>
    if not any(a.startswith("-Djava.library.path") for a in resolved):
        resolved.insert(0, "-Djava.library.path=%s" % str(natives_dir))
    return resolved


def _game_args(meta: dict, placeholders: dict):
    args = []
    raw = meta.get("arguments", {}).get("game") if isinstance(meta.get("arguments"), dict) else None
    if raw:
        for item in raw:
            if isinstance(item, str):
                args.append(item)
            elif isinstance(item, dict):
                if rules_allow(item.get("rules")):
                    v = item.get("value")
                    if isinstance(v, list):
                        args.extend(v)
                    elif isinstance(v, str):
                        args.append(v)
    elif meta.get("minecraftArguments"):
        args = _split_legacy_args(meta["minecraftArguments"])
    else:
        args = []
    out = []
    for a in args:
        for k, v in placeholders.items():
            a = a.replace(k, v)
        out.append(a)
    return out


# ---------------------------------------------------------------------------
# Classpath jar (Class-Path в манифесте)
# ---------------------------------------------------------------------------
def build_classpath_jar(game_dir: Path, meta: dict, version_id: str) -> Path:
    """Создаёт <game_dir>/cp_<id>.jar с Class-Path из всех библиотек + клиента."""
    from pathlib import Path as _Path
    game_dir = _Path(game_dir)
    p = paths_for(version_id, game_dir)
    entries = []
    # библиотеки (те же rules, что и в -cp)
    for lib in meta.get("libraries", []):
        if not rules_allow(lib.get("rules")):
            continue
        dl = (lib.get("downloads") or {}).get("artifact")
        if dl and dl.get("path"):
            entries.append(dl["path"])
        else:
            name = lib.get("name", "")
            parts = name.split(":")
            if len(parts) >= 3:
                g, a, v = parts[0], parts[1], parts[2]
                cls = (":" + parts[3]) if len(parts) > 3 else ""
                entries.append("%s/%s/%s/%s-%s%s.jar" % (
                    g.replace(".", "/"), a, v, a, v, cls))
    entries.append("versions/%s/%s.jar" % (version_id, version_id))
    # дедупликация, порядок сохраняем
    seen, ordered = set(), []
    for e in entries:
        if e not in seen:
            seen.add(e)
            ordered.append(e)

    # отбрасываем отсутствующие файлы: это pom-only платформы легаси-json
    # (lwjgl-platform, jinput-platform, twitch-*): их jar нет ни на CDN Mojang,
    # ни на диске — их нативные части уже распакованы в natives/.
    # Клиент (versions/...) обязателен и остаётся всегда.
    filtered = []
    for e in ordered:
        if e.startswith("versions/"):
            filtered.append(e)
        elif (game_dir / "libraries" / e).exists():
            filtered.append(e)
    ordered = filtered

    # относительные URL от каталога game_dir (jar лежит там же):
    # библиотеки -> libraries/<path>, клиент -> versions/<id>/<id>.jar
    rel = []
    for e in ordered:
        if e.startswith("versions/") or e.startswith("libraries/"):
            full = e
        else:
            full = "libraries/" + e          # maven-путь artifact -> libraries/
        rel.append("./" + "/".join(quote(seg, safe="") if seg else seg
                                   for seg in full.split("/")))

    # манифест с переносами по <=72 байт (продолжение начинается с пробела)
    lines = ["Manifest-Version: 1.0", "Created-By: Exeyta Launcher"]
    cp_line = "Class-Path: " + " ".join(rel)
    # байтовый перенос для ASCII-PercentEncoded строк корректен
    while len(cp_line.encode("utf-8")) > 72:
        # найдём точку переноса: первые 72 байта, затем продолжение " X..."
        chunk = cp_line[:70]  # ASCII -> байты == символы
        lines.append(chunk)
        cp_line = " " + cp_line[70:]
    lines.append(cp_line)
    lines.append("")
    manifest = "\r\n".join(lines).encode("utf-8")

    jar_path = game_dir / ("cp_%s.jar" % version_id)
    game_dir.mkdir(parents=True, exist_ok=True)
    tmp = jar_path.with_suffix(".jar.tmp")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("META-INF/MANIFEST.MF", manifest)
        zf.writestr("META-INF/EXEYTA_VERSION", version_id)
    tmp.replace(jar_path)
    return jar_path


# ---------------------------------------------------------------------------
# Полная команда
# ---------------------------------------------------------------------------
def build_command(version_id: str, account: dict, mem_mb: int = 6144,
                  game_dir: Path = None, jvm_extra: str = "") -> dict:
    """Возвращает {'java': Path, 'args': [..], 'bat': Path, 'major': int}."""
    gd = Path(game_dir) if game_dir else cfg.get_config().game_dir
    meta = load_meta(version_id, gd)
    p = paths_for(version_id, gd)
    if not p["natives"].exists() or not any(p["natives"].glob("*.dll")):
        extract_natives(p, meta)

    major = major_for(version_id)
    java = cfg.root_dir() / "runtime" / ("jre%d" % major) / "bin" / "java.exe"
    if not java.exists():
        raise RuntimeError("Не найдена portable Java %d: %s" % (major, java))

    cp_jar = build_classpath_jar(gd, meta, version_id)

    name = (account or {}).get("name") or "Player"
    uuid = (account or {}).get("uuid") or ""
    skin = (account or {}).get("skin") or ""

    placeholders = {
        "${auth_player_name}": name,
        "${version_name}": version_id,
        "${game_directory}": str(gd),
        "${game_assets}": str(p["assets"] / "virtual" / "legacy"),
        "${assets_root}": str(p["assets"]),
        "${assets_index_name}": (meta.get("assets") or "legacy"),
        "${auth_uuid}": uuid,
        "${auth_access_token}": "0",
        "${auth_session}": "0",
        "${user_type}": "legacy",
        "${user_properties}": "{}",
        "${version_type}": (meta.get("type") or "release"),
        "${natives_directory}": str(p["natives"]),
        "${classpath}": str(cp_jar),
        "${classpath_separator}": ";",
        "${library_directory}": str(p["libraries"]),
        "${auth_xuid}": "0",
        "${clientid}": "0",
        "${launcher_name}": LAUNCHER_NAME,
        "${launcher_version}": LAUNCHER_VERSION,
        "${resolution_width}": "1280",
        "${resolution_height}": "720",
    }

    # память: -Xmx6G при кратности 1024, иначе -Xmx...M
    if mem_mb % 1024 == 0:
        mem = "-Xmx%dG" % (mem_mb // 1024)
        mem_ms = "-Xms%dG" % (mem_mb // 1024)
    else:
        mem = "-Xmx%dM" % mem_mb
        mem_ms = "-Xms%dM" % mem_mb

    jvm = [mem, mem_ms]
    extra = (jvm_extra or "").strip()
    if extra:
        jvm.extend(_split_legacy_args(extra))
    jvm.extend(_jvm_args(meta, placeholders, p["natives"], cp_jar))

    game = _game_args(meta, placeholders)

    # принудительные offline-поля (контракт: только offline)
    force = {
        "--username": name,
        "--uuid": uuid,
        "--accessToken": "0",
        "--userType": "legacy",
    }
    out_game = []
    i = 0
    while i < len(game):
        a = game[i]
        key = a.split("=")[0] if a.startswith("--") and "=" in a else a
        if key in force and key.startswith("--"):
            if "=" in a:
                out_game.append("%s=%s" % (key, force[key]))
            else:
                out_game.append(key)
                if i + 1 < len(game) and not game[i + 1].startswith("--"):
                    out_game.append(force[key])
                    i += 1
                else:
                    out_game.append(force[key])
        else:
            out_game.append(a)
        i += 1
    for k, v in force.items():
        if k not in out_game:
            out_game.extend([k, v])

    main_class = meta.get("mainClass") or "net.minecraft.client.main.Main"

    # JVM-аргументы уже содержат -cp <classpath jar> (см. _jvm_args)
    args = []
    args.extend(jvm)
    if not any(x in ("-cp", "-classpath") for x in jvm):
        args += ["-cp", str(cp_jar)]
    args.append(main_class)
    args.extend(out_game)

    return {
        "java": java,
        "args": args,
        "major": major,
        "main_class": main_class,
        "natives": p["natives"],
        "classpath_jar": cp_jar,
        "game_dir": gd,
        "version": version_id,
        "skin": skin,
        "meta": meta,
    }


# ---------------------------------------------------------------------------
# .bat
# ---------------------------------------------------------------------------
def _safe(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.\-а-яА-ЯёЁ]+", "_", s).strip("_") or "x"


def bat_path(version_id: str, nick: str, game_dir: Path = None) -> Path:
    return cfg.scripts_dir() / ("launch_%s_%s.bat" % (_safe(version_id), _safe(nick)))


def write_bat(version_id: str, account: dict, mem_mb: int = 6144,
              game_dir: Path = None, jvm_extra: str = "") -> Path:
    cmd = build_command(version_id, account, mem_mb, game_dir, jvm_extra)
    major = cmd["major"]
    name = (account or {}).get("name") or "Player"
    path = bat_path(version_id, name, game_dir)

    # экранирование % в bat; по контракту кавычки у значений,
    # которые в макете показаны в кавычках (--username "Nick" --uuid ...),
    # а также у любого аргумента со спецсимволами/пробелами (пути).
    FORCE_QUOTE_PREV = {"--username", "--uuid"}

    def esc(a: str, prev: str = "") -> str:
        a = a.replace("%", "%%")
        if a.startswith('"') and a.endswith('"') and len(a) >= 2:
            return a
        special = any(c in a for c in " &^()|<>\"")
        if special or prev in FORCE_QUOTE_PREV:
            return '"%s"' % a
        return a

    args_list = cmd["args"]
    arg_line = " ".join(
        esc(a, args_list[i - 1] if i else "")
        for i, a in enumerate(args_list))

    lines = [
        "@echo off",
        "chcp 65001 >nul",
        'set "JAVA_EXE=%%~dp0..\\runtime\\jre%d\\bin\\java.exe"' % major,
        'cd /d "%~dp0.."',
        '"%JAVA_EXE%" ' + arg_line,
    ]
    path.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")
    return path


def ensure_ready(version_id: str, account: dict, mem_mb: int = 6144,
                 game_dir: Path = None, jvm_extra: str = "") -> Path:
    """Проверка готовности + запись bat. Кидает RuntimeError при неготовности."""
    gd = Path(game_dir) if game_dir else cfg.get_config().game_dir
    from .minecraft_installer import is_client_installed
    from .portable_java import is_installed
    major = major_for(version_id)
    if not is_client_installed(version_id, gd):
        raise RuntimeError("Клиент %s не установлен" % version_id)
    if not is_installed(major):
        raise RuntimeError("Java %d не установлена" % major)
    return write_bat(version_id, account, mem_mb, gd, jvm_extra)

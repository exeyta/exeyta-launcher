# -*- coding: utf-8 -*-
"""Rust Edition (Horizon): поиск установки, ник, скин и запуск через .bat.

Horizon — Minecraft: Java Edition 26.3, переписанный на Rust. Это отдельный
клиент, а не Java-версия: у него свои ресурсы, инстансы и моды. Здесь только
запуск уже установленной сборки и передача offline-ника/скина.

Ожидаемая структура (как у Horizon Offline Launcher):
  %APPDATA%/horizon-launcher/versions/<tag>/horizon-client.exe
  %APPDATA%/horizon-launcher/versions/<tag>/.local/horizon-client/26.3/
  %APPDATA%/horizon/instances/<instance>/
"""
import json
import os
import re
import time
from pathlib import Path

from . import config as cfg

PREFERRED_TAG = "v0.2.97.1"
DEFAULT_MC = "26.3"
DEFAULT_INSTANCE = "df"


def _appdata() -> Path:
    base = os.environ.get("APPDATA")
    if base:
        return Path(base)
    return Path.home() / "AppData" / "Roaming"


def _read_json(path: Path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default if default is not None else {}


def data_dir() -> Path:
    """Каталог данных Horizon Offline Launcher."""
    env = os.environ.get("HORIZON_LAUNCHER_HOME")
    return Path(env) if env else (_appdata() / "horizon-launcher")


def game_root() -> Path:
    """Корень игровых данных Horizon (миры, инстансы)."""
    env = os.environ.get("HORIZON_HOME")
    return Path(env) if env else (_appdata() / "horizon")


def settings() -> dict:
    return _read_json(data_dir() / "settings.json", {})


def installed_tags():
    """Теги установленных сборок Horizon, у которых есть клиент."""
    root = data_dir() / "versions"
    out = []
    try:
        for p in root.iterdir():
            if p.is_dir() and (p / "horizon-client.exe").is_file():
                out.append(p.name)
    except Exception:
        pass
    return out


def pick_tag(preferred=PREFERRED_TAG):
    tags = installed_tags()
    if not tags:
        return None
    if preferred and preferred in tags:
        return preferred
    selected = settings().get("selected")
    if selected in tags:
        return selected
    # новые сборки — сверху, но v0.2.x стабильнее nightly
    stable = [t for t in tags if re.match(r"^v\d", t)]
    if stable:
        return sorted(stable)[-1]
    return sorted(tags)[-1]


def mc_version(tag: str) -> str:
    lock = _read_json(data_dir() / "versions" / tag / "research-lock.json", {})
    try:
        return str(lock.get("minecraft", {}).get("version") or DEFAULT_MC)
    except Exception:
        return DEFAULT_MC


def instance_id() -> str:
    return str(settings().get("instance") or DEFAULT_INSTANCE)


def instance_home(iid: str = None) -> Path:
    iid = iid or instance_id()
    root = game_root()
    own = root / "instances" / iid
    return own if own.is_dir() else root


def resources_dir(tag: str) -> Path:
    return (data_dir() / "versions" / tag / ".local" / "horizon-client"
            / mc_version(tag))


def info(preferred=PREFERRED_TAG) -> dict:
    """Всё, что нужно для запуска Rust Edition, или понятная ошибка."""
    tag = pick_tag(preferred)
    if not tag:
        return {"ok": False, "error": "Horizon не установлен",
                "tag": None, "instance": instance_id()}
    vdir = data_dir() / "versions" / tag
    client = vdir / "horizon-client.exe"
    res = resources_dir(tag)
    prepared = (res / "horizon-resources.json").is_file()
    home = instance_home()
    ok = client.is_file() and prepared and home.is_dir()
    err = ""
    if not client.is_file():
        err = "Не найден horizon-client.exe в %s" % vdir
    elif not prepared:
        err = ("Ресурсы 26.3 не подготовлены: %s\n"
               "Запустите Horizon Offline Launcher и нажмите Prepare." % res)
    elif not home.is_dir():
        err = "Не найден инстанс: %s" % home
    return {
        "ok": ok,
        "error": err,
        "tag": tag,
        "version_dir": str(vdir),
        "client": str(client),
        "resources": str(res),
        "prepared": prepared,
        "mc_version": mc_version(tag),
        "instance": instance_id(),
        "home": str(home),
    }


def default_skin_path(nick: str) -> Path:
    return cfg.appdata_dir() / "skins" / ("%s.png" % nick)


def skin_path(account: dict):
    """Путь к PNG скина Exeyta-аккаунта, если он есть."""
    acc = account or {}
    candidates = []
    if acc.get("skin"):
        candidates.append(Path(str(acc["skin"])))
    nick = str(acc.get("name") or "")
    if nick:
        candidates.append(default_skin_path(nick))
        candidates.append(_appdata() / "horizon-launcher" / "skins"
                          / (nick.lower() + ".png"))
    for p in candidates:
        try:
            if p.is_file():
                return str(p)
        except Exception:
            pass
    return ""


def cape_path(account: dict):
    acc = account or {}
    nick = str(acc.get("name") or "")
    candidates = []
    if acc.get("cape"):
        candidates.append(Path(str(acc["cape"])))
    if nick:
        candidates.append(cfg.appdata_dir() / "skins" / (nick + ".cape.png"))
    for p in candidates:
        try:
            if p.is_file():
                return str(p)
        except Exception:
            pass
    return ""


def skin_model(account: dict):
    acc = account or {}
    model = str(acc.get("skin_model") or "").lower()
    if model in ("classic", "slim"):
        return model
    try:
        model = str(cfg.get_config().get("skin_model") or "classic").lower()
    except Exception:
        model = "classic"
    return "slim" if model == "slim" else "classic"


def rust_dir() -> Path:
    """Отдельная папка с .bat и настройками Rust Edition."""
    p = cfg.appdata_dir() / "rust-edition"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _bat_quote(text):
    return str(text).replace('"', "")


def write_launch_bat(nick, skin="", cape="", model="classic",
                     info_data=None):
    """Создаёт отдельный .bat для запуска сборки и возвращает его путь.

    Батник самодостаточный: его можно запускать двойным щелчком, без
    Exeyta. Если скин/плащ не найдены, соответствующие переменные не
    выставляются — Horizon возьмёт стандартный вид.
    """
    data = info_data or info()
    if not data.get("ok"):
        raise RuntimeError(data.get("error") or "Rust Edition не готов")
    nick = (nick or "Player").strip() or "Player"
    if not re.match(r"^[A-Za-z0-9_]{1,16}$", nick):
        nick = re.sub(r"[^A-Za-z0-9_]", "_", nick)[:16] or "Player"

    out = rust_dir()
    lines = [
        "@echo off",
        "chcp 65001 >nul",
        "setlocal",
        "title Minecraft 26.3 Rust Edition",
        'set "HORIZON_HOME=%s"' % _bat_quote(data["home"]),
        'cd /d "%HORIZON_HOME%" || exit /b 1',
    ]
    if skin and Path(skin).is_file():
        lines.append('set "HORIZON_OFFLINE_SKIN=%s"' % _bat_quote(skin))
        lines.append('set "HORIZON_OFFLINE_SKIN_MODEL=%s"'
                     % ("slim" if model == "slim" else "classic"))
    if cape and Path(cape).is_file():
        lines.append('set "HORIZON_OFFLINE_CAPE=%s"' % _bat_quote(cape))
    lines += [
        '"%s" --resources "%s" --name "%s"'
        % (_bat_quote(data["client"]), _bat_quote(data["resources"]), nick),
        'set "RC=%ERRORLEVEL%"',
        "endlocal & exit /b %RC%",
        "",
    ]
    text = "\r\n".join(lines)
    tagged = out / ("launch_%s.bat" % nick)
    tagged.write_text(text, encoding="utf-8", newline="")
    (out / "launch.bat").write_text(text, encoding="utf-8", newline="")

    meta = dict(data)
    meta.update({"nick": nick, "skin": skin or "", "cape": cape or "",
                 "model": model, "written": time.strftime("%Y-%m-%d %H:%M:%S")})
    (out / "config.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "README.txt").write_text(
        "Minecraft 26.3 Rust Edition (Horizon)\r\n"
        "=====================================\r\n\r\n"
        "launch.bat — запуск с текущим ником и скином.\r\n"
        "launch_<ник>.bat — запуск под конкретным ником.\r\n"
        "config.json — пути, ник, скин и модель.\r\n\r\n"
        "Папку можно открыть из Exeyta Launcher: Rust Edition.\r\n"
        "Скин: HORIZON_OFFLINE_SKIN, модель: HORIZON_OFFLINE_SKIN_MODEL.\r\n"
        "Моды Java Edition сюда не подходят — у Horizon свои .hmod.\r\n",
        encoding="utf-8")
    return tagged


def launch_bat_path(nick="Player"):
    p = rust_dir() / ("launch_%s.bat" % (nick or "Player"))
    return p

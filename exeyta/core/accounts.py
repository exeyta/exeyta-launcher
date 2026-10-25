# -*- coding: utf-8 -*-
"""Offline-аккаунты Exeyta.

Только offline: никаких Microsoft/Mojang OAuth и онлайн-сессий.
Хранение: %APPDATA%/Exeyta/accounts.json
    {
      "active": 0,
      "accounts": [
        {"name": "Exeyta", "uuid": "....-....", "skin": "C:/path/skin.png"}
      ]
    }
UUID — offline UUID (uuid5 от имени), скин — локальный путь к PNG.
"""
import json
import threading
import uuid as uuid_mod
from pathlib import Path

from .config import accounts_path

_NS = uuid_mod.UUID("6ba7b811-9dad-11d1-80b4-00c04fd430c8")  # URL namespace


def offline_uuid(name: str) -> str:
    """Классический offline UUID: uuid5(URL, 'OfflinePlayer:<name>')."""
    name = (name or "").strip()
    return str(uuid_mod.uuid5(_NS, "OfflinePlayer:" + name))


def default_skin_path() -> str:
    return ""


class AccountStore:
    def __init__(self, path: Path = None):
        self.path = Path(path) if path else accounts_path()
        self._lock = threading.RLock()
        self.accounts = []
        self.active = 0
        self.load()

    # --- persistence -------------------------------------------------------
    def load(self):
        with self._lock:
            existed = self.path.exists()
            try:
                if existed:
                    raw = json.loads(self.path.read_text(encoding="utf-8"))
                    accs = raw.get("accounts") or []
                    if isinstance(accs, list):
                        self.accounts = [a for a in accs if isinstance(a, dict) and a.get("name")]
                    self.active = int(raw.get("active", 0) or 0)
            except Exception:
                self.accounts, self.active = [], 0
            if not self.accounts:
                self.accounts = [{"name": "Exeyta",
                                  "uuid": offline_uuid("Exeyta"),
                                  "skin": default_skin_path()}]
                self.active = 0
            if not (0 <= self.active < len(self.accounts)):
                self.active = 0
            if not existed:
                # файл создаём сразу: %APPDATA%/Exeyta/accounts.json
                self.save()
        return self

    def save(self):
        with self._lock:
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                tmp = self.path.with_suffix(".json.tmp")
                tmp.write_text(
                    json.dumps({"active": self.active, "accounts": self.accounts},
                               ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                tmp.replace(self.path)
            except Exception:
                pass
        return self

    # --- API ---------------------------------------------------------------
    def all(self):
        with self._lock:
            return [dict(a) for a in self.accounts]

    def current(self):
        with self._lock:
            if not self.accounts:
                return None
            i = max(0, min(self.active, len(self.accounts) - 1))
            return dict(self.accounts[i])

    def current_name(self) -> str:
        cur = self.current()
        return cur["name"] if cur else "Player"

    def current_uuid(self) -> str:
        cur = self.current()
        if not cur:
            return offline_uuid("Player")
        return cur.get("uuid") or offline_uuid(cur["name"])

    def current_skin(self) -> str:
        cur = self.current()
        return (cur or {}).get("skin") or ""

    def add(self, name: str):
        name = (name or "").strip()
        if not name:
            raise ValueError("Имя не может быть пустым")
        if len(name) > 16:
            raise ValueError("Ник не длиннее 16 символов")
        allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")
        if not all(c in allowed for c in name):
            raise ValueError("Только латиница, цифры и _")
        with self._lock:
            for a in self.accounts:
                if a["name"].lower() == name.lower():
                    self.active = self.accounts.index(a)
                    self.save()
                    return dict(a)
            acc = {"name": name, "uuid": offline_uuid(name), "skin": default_skin_path()}
            self.accounts.append(acc)
            self.active = len(self.accounts) - 1
            self.save()
            return dict(acc)

    def remove(self, index: int):
        with self._lock:
            if 0 <= index < len(self.accounts) and len(self.accounts) > 1:
                del self.accounts[index]
                if self.active >= len(self.accounts):
                    self.active = len(self.accounts) - 1
                self.save()

    def set_active(self, index: int):
        with self._lock:
            if 0 <= index < len(self.accounts):
                self.active = index
                self.save()

    def set_skin(self, path: str, index: int = None):
        with self._lock:
            i = self.active if index is None else index
            if 0 <= i < len(self.accounts):
                self.accounts[i]["skin"] = str(path)
                self.save()

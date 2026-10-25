# -*- coding: utf-8 -*-
"""Публикация обновления Exeyta на GitHub одной командой.

    python build/publish_release.py 1.0.0-alpha.2 "что нового"

Что делает:
  1) git add/commit/push текущих изменений (если есть);
  2) создаёт GitHub Release (помечен как Pre-release — это альфа);
  3) загружает dist/ExeytaSetup.exe в Assets релиза.

Авторизация: GITHUB_TOKEN (env) либо Windows Credential Manager
(`git credential fill`, как обычный git-push). Токен никогда не пишется
на диск и не выводится в лог.

Сайт (exeyta.github.io) ссылкой releases/latest/download/ExeytaSetup.exe
сразу начнёт отдавать новую сборку.
"""
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SETUP = ROOT / "dist" / "ExeytaSetup.exe"
ALPHA_DEFAULT_NOTE = ("**Альфа-версия.** Проект в активной разработке — "
                      "возможны изменения и ошибки.")


def run(args, **kw):
    return subprocess.run(args, cwd=str(ROOT), capture_output=True,
                          text=True, encoding="utf-8", errors="replace", **kw)


def die(msg):
    print("ОШИБКА:", msg, file=sys.stderr)
    sys.exit(1)


def github_repo():
    """owner/name из origin."""
    r = run(["git", "remote", "get-url", "origin"])
    if r.returncode != 0 or not r.stdout.strip():
        die("нет remote origin (git remote add origin <url>)")
    url = r.stdout.strip()
    m = re.search(r"github\.com[:/]([^/]+)/(.+?)(?:\.git)?$", url)
    if not m:
        die("origin не на github.com: %s" % url)
    return "%s/%s" % (m.group(1), m.group(2))


def github_token():
    tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if tok:
        return tok.strip()
    # Windows Credential Manager через git (токен не печатается)
    try:
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        r = subprocess.run(
            ["git", "credential", "fill"],
            input="protocol=https\nhost=github.com\n\n",
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", creationflags=flags,
        )
        for line in (r.stdout or "").splitlines():
            if line.startswith("password="):
                return line.split("=", 1)[1].strip()
    except Exception:
        pass
    die("нет токена: задайте GITHUB_TOKEN или войдите в git credential manager")


def api(method, url, token, payload=None, raw=None, content_type="application/json"):
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    elif raw is not None:
        data = raw
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", "Bearer %s" % token)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if payload is not None:
        req.add_header("Content-Type", content_type)
    if raw is not None:
        req.add_header("Content-Type", content_type)
        req.add_header("Content-Length", str(len(raw)))
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            body = resp.read()
            return json.loads(body.decode("utf-8")) if body else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:500]
        die("GitHub API %s %s -> %s %s" % (method, url, e.code, detail))
    except Exception as e:
        die("сетевая ошибка GitHub: %s" % e)


def git_publish(tag, notes):
    status = run(["git", "status", "--porcelain"])
    if status.stdout.strip():
        run(["git", "add", "-A"])
        msg = "release: %s" % tag
        n = run(["git", "commit", "-m", msg])
        if n.returncode != 0:
            print(n.stdout, n.stderr)
            die("коммит не прошёл")
        print("совершён коммит: %s" % msg, flush=True)
    else:
        print("дерево чистое — коммит не нужен", flush=True)
    p = run(["git", "push", "origin", "HEAD"])
    if p.returncode != 0:
        print(p.stdout, p.stderr)
        die("push не прошёл")
    print("код запушен на origin", flush=True)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("Пример: python build/publish_release.py 1.0.0-alpha.2 "
              "\"исправления запуска\"")
        return 2
    tag = sys.argv[1].lstrip("v")
    notes = sys.argv[2] if len(sys.argv) > 2 else ""
    tag = "v%s" % tag

    if not SETUP.exists():
        die("нет сборки %s — сначала build_installer.bat" % SETUP)

    repo = github_repo()
    token = github_token()
    print("репозиторий:", repo, "| тег:", tag, flush=True)

    # 1) код
    git_publish(tag, notes)

    # 2) релиз (помечаем как Pre-release: это альфа)
    body = ("%s\n\n### Скачать для Windows\n"
            "`ExeytaSetup.exe` — установщик лаунчера.\n\n"
            "Сайт всегда отдаёт эту сборку:\n"
            "https://exeyta.github.io/\n" % ALPHA_DEFAULT_NOTE)
    if notes:
        body = "### Что нового\n%s\n\n%s" % (notes, body)

    payload = {
        "tag_name": tag,
        # prerelease=False: иначе /releases/latest/download/... на сайте
        # НЕ увидит альфа-релиз («latest» игнорирует prerelease).
        # Альфа явно указана в названии и описании.
        "name": "Exeyta Launcher %s — АЛЬФА" % tag,
        "body": body,
        "prerelease": False,
    }
    rel = api("POST", "https://api.github.com/repos/%s/releases" % repo,
              token, payload=payload)
    print("релиз создан:", rel.get("html_url"), flush=True)

    # 3) загрузка ассета (89 МБ)
    upload_url = rel["upload_url"].split("{", 1)[0]
    data = SETUP.read_bytes()
    print("загрузка %s (%.1f МБ)..." % (SETUP.name, len(data) / 1048576),
          flush=True)
    api("POST", "%s?name=%s" % (upload_url, SETUP.name), token, raw=data,
        content_type="application/octet-stream")
    print("ассет загружен", flush=True)

    print("\nГОТОВО:")
    print("  релиз:      %s" % rel.get("html_url"))
    print("  скачивание: https://github.com/%s/releases/latest/download/%s"
          % (repo, SETUP.name))
    return 0


if __name__ == "__main__":
    sys.exit(main())

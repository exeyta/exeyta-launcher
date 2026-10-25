# Exeyta Launcher

> ⚠️ **АЛЬФА-ВЕРСИЯ** — проект в активной разработке. Возможны изменения
> и ошибки; обратная связь в [Telegram](https://t.me/exeyta).

**Скачать для Windows (всегда последняя сборка):**
https://github.com/exeyta/exeyta-launcher/releases/latest/download/ExeytaSetup.exe

**Исходный код:** https://github.com/exeyta/exeyta-launcher

Офлайн-лаунчер Minecraft и его установщик для Windows.
Стек: **Python 3.11+ / PyQt5** (лаунчер и установщик). Интерфейс — русский.

Визуальный источник правды лаунчера — `assets/launcher-ui.svg`
(viewBox `28 22 1864 1036`): цвета, градиенты, радиусы, отступы и
иерархия блоков воспроизведены 1:1 нативными Qt-виджетами + QSS
(`exeyta/ui/styles.qss`), общий модуль темы — `exeyta_shared/theme.py`.

---

## Быстрый старт

```bat
install_deps.bat        :: pip install -r requirements.txt (PyQt5)
start.bat               :: python launcher.py
start_installer.bat     :: python installer.py
```

Сборка бинарников:

```bat
build_launcher.bat      :: dist/ExeytaLauncher/ExeytaLauncher.exe (onedir)
build_installer.bat     :: dist/ExeytaSetup.exe (onefile)
```

> В корне репозитория ровно два входа продуктов: `launcher.py` и
> `installer.py`. Вся логика — в пакетах `exeyta/`, `exeyta_installer/`,
> `exeyta_shared/`. `python launcher.py` ≡ `ExeytaLauncher.exe`,
> `python installer.py` ≡ `ExeytaSetup.exe`.

---

## Возможности

* **Только offline-аккаунты** — без Microsoft/Mojang OAuth и онлайн-сессий.
  Хранение: `%APPDATA%/Exeyta/accounts.json` (ник, offline UUID, путь к скину).
  В карточке профиля статус — **Premium Offline**; шестерёнка рядом
  открывает управление аккаунтами (добавить / удалить / выбрать активный).
* **Единый мастер «Установка Minecraft и Java»** — клиент и портативная Java
  качаются вместе (QThread, отмена, retry), UI не блокируется.
* **Автовыбор Java по версии Minecraft:**

| Minecraft         | runtime/ |
|-------------------|----------|
| 1.7.x – 1.16.5    | jre8     |
| 1.17.x – 1.20.4   | jre17    |
| 1.20.5 – 1.21.x   | jre21    |
| 26.x+ и снапшоты  | jre25    |

  Снапшоты определяют Java по **последней обычной (релизной) версии**
  (кэш `latest_release.txt`).
  Java распаковывается в `runtime/jre<major>` **рядом с exe** (Temurin JRE
  portable ZIP, Win x64), ставится маркер `.exeyta_ok` и проверяется
  `java -version`. Системная Java не используется и не ставится. Уже
  установленная Java повторно не скачивается.
* **Запуск игры**: генерируется `scripts/launch_<version>_<nick>.bat`
  (команда `java` идёт через переменную `JAVA_EXE=%~dp0..\runtime\jreXX\bin\java.exe`),
  исполняется Python-оркестратором (`QThread` + `subprocess.Popen`),
  логи пишутся в `%APPDATA%/Exeyta/logs/`.
* **Скин в игре (offline)**: ванильный клиент при отсутствии онлайн-профиля
  берёт стандартный скин из клиентского jar — лаунчер **автоматически
  подменяет эти текстуры** на композит из редактора: при запуске (статус
  «применение скина…») и по кнопке «В игру». Охват: `entity/steve|alex.png`
  (классика) и пул `entity/player/{wide,slim}/*.png` (26.x). Оригиналы
  хранятся в `<jar>.skinbak` — у аккаунта без скина всё возвращается.
  Ограничение: ник реального премиум-аккаунта получит онлайн-скин Mojang;
  другие игроки в сети увидят ваш скин только на клиентах с таким же
  патчем.
  Класспасс выносится в маленький `game/cp_<version>.jar` с `Class-Path`
  в манифесте — строка .bat далеко ниже лимита cmd (8191) и одинаково
  работает на Java 8/17/21.
* **Редактор скина** (один слой): карандаш/заливка/ластик/отмена, зум ±,
  палитра 12 цветов, UV-холст 512×448 с чекер-фоном и сеткой,
  3D-превью 336×448 с вращением мышью (рендер по требованию, ≤30 fps),
  Сохранить / Импорт PNG / Экспорт / В игру.
* **Настройки**: Память (4096–8192 MB) + автозапуск, Java (путь портативной
  JVM + JVM-аргументы), Папка игры (+ «Обзор»), Язык.
* **«Моды» / «Из коробки»** — в UI нет Fabric/Quilt (по требованию).

---

## Производительность

* `QPropertyAnimation`, `OutCubic`: hover 180–320 мс, переходы 280–420 мс.
* Нет таймеров на 16 мс с repaint всего окна: анимируются только свойства,
  repaint — только изменённый маленький виджет.
* Скачивание — исключительно в `QThread`; 3D перерисовывается только при
  вращении/правке скина (троттлинг 33 мс); текстуры кэшируются в `QPixmap`;
  styles один — `exeyta/ui/styles.qss`.
* Ориентир idle: RAM < 120 МБ, CPU < 2% на слабом ПК.

---

## Структура репозитория

```
exeyta-launcher/
├── launcher.py                 # ЕДИНСТВЕННЫЙ вход лаунчера
├── installer.py                # ЕДИНСТВЕННЫЙ вход установщика
├── requirements.txt            # PyQt5
├── requirements-build.txt      # pyinstaller
├── install_deps.bat
├── start.bat                   # python launcher.py
├── start_installer.bat         # python installer.py
├── build_launcher.bat
├── build_installer.bat
├── README.md
├── assets/
│   ├── launcher-ui.svg         # визуальный источник правды
│   ├── icon.ico
│   └── icons/
├── exeyta/
│   ├── app.py
│   ├── ui/
│   │   ├── main_window.py      # окно 1864×1036, вкладки-разделы + анимации
│   │   ├── home_panel.py       # раздел «Главная» (стартовый)
│   │   ├── sidebar.py          # логотип, навигация, Telegram, аккаунт
│   │   ├── launch_panel.py     # «Запуск» 430×648
│   │   ├── skin_editor.py      # «Редактор скина» 1090×648
│   │   ├── settings_panel.py   # «Настройки» 1536×320
│   │   ├── install_wizard.py   # мастер MC+Java
│   │   ├── controls.py         # кнопки/слайдеры/чипы (ручная отрисовка)
│   │   └── styles.qss
│   ├── core/
│   │   ├── accounts.py         # %APPDATA%/Exeyta/accounts.json
│   │   ├── java_resolver.py    # таблица MC -> major Java
│   │   ├── portable_java.py    # runtime/jre8|17|21|25, .exeyta_ok, java -version
│   │   ├── minecraft_installer.py
│   │   ├── launch_builder.py   # .bat + classpath jar
│   │   ├── game_launcher.py    # QThread-оркестратор, логи
│   │   └── config.py
│   └── workers/
│       └── download_worker.py  # InstallWorker/VersionsWorker/SkinLoadWorker
├── exeyta_installer/
│   ├── app.py
│   ├── ui/
│   │   ├── wizard_window.py    # приветствие→согласие→путь→ярлыки→прогресс→готово
│   │   ├── pages/
│   │   └── styles.qss
│   └── core/
│       ├── install_paths.py    # %LOCALAPPDATA%\Exeyta, install.json, .lnk
│       └── file_copy.py        # CopyWorker (QThread)
├── exeyta_shared/
│   ├── theme.py                # токены цветов + помощники рисования
│   └── animations.py           # OutCubic, HoverFader
├── build/
│   ├── exeyta_launcher.spec
│   ├── exeyta_setup.spec
│   ├── build_launcher.py
│   └── build_installer.py
└── scripts/                    # генерируемые bat игры
```

### Каталоги у пользователя

```
%LOCALAPPDATA%\Exeyta\          (или выбранный путь)
├── ExeytaLauncher.exe
├── _internal/                  # PyInstaller onedir
├── assets/
├── runtime/                    # jre8, jre17, jre21, jre25 — качает лаунчер
├── game/                       # versions/, libraries/, assets/
├── mods/
├── scripts/
├── config.json
├── install.json
└── logs/

%APPDATA%\Exeyta\
├── accounts.json               # offline-аккаунты
├── skins\                      # локальные скины
├── cache\                      # кэш скачиваний
└── logs\                       # логи запусков
```

### Дистрибуция

```
dist/
├── ExeytaSetup.exe             # для пользователей
└── ExeytaLauncher/
    └── ExeytaLauncher.exe
```

Установщик **не качает** Minecraft/Java — он только разворачивает лаунчер
(копирование в QThread), создаёт структуру каталогов, `install.json` и
ярлыки, а по завечшении может запустить `Exeyta`.

---

## Как это работает

1. Выбираете версию в плашке «Запуск» → резолвер версии
   (`java_resolver.major_for`) определяет major Java по таблице.
2. «ИГРАТЬ» проверяет готовность (клиент + runtime). Если чего-то нет —
   открывается мастер «Установка Minecraft и Java»: version.json, client.jar,
   библиотеки, нативные, ресурсы → затем portable JRE (если нужна).
3. `launch_builder` пишет `scripts/launch_<version>_<nick>.bat`
   (`-Xmx… -XX:+UseG1GC … --username "Nick" --uuid … --accessToken 0
   --userType legacy`) и `game/cp_<version>.jar`.
4. `game_launcher.GameWorker` исполняет .bat через `subprocess.Popen`,
   стримит вывод в `%APPDATA%/Exeyta/logs/` и в статус панели, не блокируя UI.

---

## Публикация обновления на GitHub (релизы)

Одна команда — коммит, пуш, тег, GitHub Release (prerelease) и загрузка
`ExeytaSetup.exe` в Assets:

```bat
python build\publish_release.py 1.0.0-alpha.2 "что нового"
```

(или `publish_release.bat 1.0.0-alpha.2 "что нового"`). Токен берётся из
`GITHUB_TOKEN` либо из Windows Credential Manager (`git credential fill`).
Сайт https://exeyta.github.io/ ссылкой
`releases/latest/download/ExeytaSetup.exe` всегда отдаёт последний релиз.

## Требования и совместимость

* Windows 10/11 x64; Python 3.11+ (для `python launcher.py`).
* Для сборки: `pip install -r requirements-build.txt` (PyInstaller 6).
* Высокое DPI: `AA_EnableHighDpiScaling`; окно 1864×1036 масштабируется
  с сохранением пропорций, если экран меньше.

## Лицензия и права

Лаунчер не связан с Mojang/Microsoft, использует только offline-аккаунты.
Скачивание клиента идёт из официальных источников Mojang; Java — Eclipse
Temurin (Adoptium). Для игры нужна собственная копия Minecraft (EULA).

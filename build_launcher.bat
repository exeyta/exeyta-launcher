@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ==========================================
echo   Сборка ExeytaLauncher.exe (onedir)
echo ==========================================
python -m pip install -q -r requirements.txt -r requirements-build.txt
python -m PyInstaller --noconfirm --clean build\exeyta_launcher.spec
if errorlevel 1 (
    echo [ОШИБКА] Сборка лаунчера не удалась.
    pause
    exit /b 1
)
echo.
echo Готово: dist\ExeytaLauncher\ExeytaLauncher.exe
pause

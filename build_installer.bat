@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ==========================================
echo   Сборка ExeytaSetup.exe (onefile)
echo ==========================================
if not exist "dist\ExeytaLauncher\ExeytaLauncher.exe" (
    echo [Подсказка] сначала соберите лаунчер: build_launcher.bat
)
python -m pip install -q -r requirements.txt -r requirements-build.txt
python -m PyInstaller --noconfirm --clean build\exeyta_setup.spec
if errorlevel 1 (
    echo [ОШИБКА] Сборка установщика не удалась.
    pause
    exit /b 1
)
echo.
echo Готово: dist\ExeytaSetup.exe
pause

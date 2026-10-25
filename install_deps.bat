@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ==========================================
echo   Exeyta — установка зависимостей
echo ==========================================
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [ОШИБКА] Не удалось установить зависимости.
    echo Проверьте, что Python 3.11+ установлен и доступен в PATH.
    pause
    exit /b 1
)
echo.
echo Готово. Запуск: start.bat  (python launcher.py)
pause

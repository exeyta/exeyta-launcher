@echo off
chcp 65001 >nul
cd /d "%~dp0"
if "%~1"=="" (
  echo Использование: publish_release.bat 1.0.0-alpha.2 "что нового"
  pause
  exit /b 1
)
python build\publish_release.py %*
if errorlevel 1 pause

@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo [1/3] Installing build dependencies...
python -m pip install -q -r requirements.txt -r requirements-dev.txt
if errorlevel 1 (
    echo Failed to install dependencies.
    pause
    exit /b 1
)

echo [2/3] Building portable exe...
python -m PyInstaller pomodoro.spec --noconfirm --clean
if errorlevel 1 (
    echo Build failed.
    pause
    exit /b 1
)

echo [3/3] Done.
echo.
echo Portable executable:
echo   dist\PomodoroOverlay.exe
echo.
echo Upload this file to GitHub Releases for users without Python.
pause

@echo off
chcp 65001 >nul
cd /d "%~dp0"

set "MAIN=%~dp0main.py"

if exist ".venv\Scripts\pythonw.exe" (
    start "" ".venv\Scripts\pythonw.exe" "%MAIN%"
) else if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
    start "" pythonw "%MAIN%"
) else (
    start "" python "%MAIN%"
)
exit

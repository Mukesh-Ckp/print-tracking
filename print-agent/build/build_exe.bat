@echo off
REM ============================================================
REM  Build PrintTrackingAgent.exe with PyInstaller.
REM ============================================================

setlocal
cd /d "%~dp0\.."

if not exist .venv\ (
    echo Creating virtual environment...
    python -m venv .venv
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller==6.10.0

pyinstaller build\agent.spec --clean --noconfirm

echo.
echo Build complete. EXE is at: dist\PrintTrackingAgent.exe
endlocal

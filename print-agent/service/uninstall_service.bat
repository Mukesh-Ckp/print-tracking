@echo off
REM ============================================================
REM  Uninstall the Print Tracking Agent Windows service.
REM  RUN AS ADMINISTRATOR.
REM ============================================================

setlocal
cd /d "%~dp0\.."

call .venv\Scripts\activate.bat 2>NUL

python service\windows_service.py stop
python service\windows_service.py remove

echo Service removed.
endlocal

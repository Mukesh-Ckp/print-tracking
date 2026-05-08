@echo off
REM ============================================================
REM  Install the Print Tracking Agent as a Windows service.
REM  RUN AS ADMINISTRATOR.
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

echo.
echo Registering pywin32 system files (one-time)...
python -m pywin32_postinstall -install

echo.
echo Installing the service with auto-start enabled...
python service\windows_service.py --startup auto install

echo.
echo Starting the service...
python service\windows_service.py start

echo.
echo Done. To check status: sc query PrintTrackingAgent
echo Logs are written to: %~dp0..\logs\print_agent.log

endlocal

@echo off
REM ============================================================
REM  Register PrintTrackingAgent.exe as a Windows scheduled task
REM  that runs at user logon (works without elevation after first
REM  install). RUN AS ADMINISTRATOR for the most reliable setup.
REM ============================================================

setlocal
set EXE_PATH=%~dp0..\dist\PrintTrackingAgent.exe

if not exist "%EXE_PATH%" (
    echo ERROR: %EXE_PATH% does not exist.
    echo Build the EXE first with build\build_exe.bat
    exit /b 1
)

schtasks /Create /F ^
    /SC ONLOGON ^
    /RL HIGHEST ^
    /TN "PrintTrackingAgent" ^
    /TR "\"%EXE_PATH%\"" ^
    /RU "%USERNAME%"

echo.
echo Scheduled task "PrintTrackingAgent" registered.
echo It will run at user logon and survive restarts.
endlocal

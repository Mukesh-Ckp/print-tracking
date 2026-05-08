@echo off
schtasks /Delete /F /TN "PrintTrackingAgent"
echo Scheduled task removed.

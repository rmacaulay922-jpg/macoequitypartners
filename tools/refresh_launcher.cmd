@echo off
rem Diagnostic launcher for the Maco Market Refresh scheduled task.
rem Logs BEFORE PowerShell param binding so a silent early death becomes visible.
set LOG=C:\Users\rmaca\OneDrive\Documents\GitHub\macoequitypartners\tools\real_refresh_log.txt
echo %date% %time%  [launcher] task fired; invoking refresh_markets.ps1 -Market auto >> "%LOG%" 2>nul
powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "C:\Users\rmaca\OneDrive\Documents\GitHub\macoequitypartners\tools\refresh_markets.ps1" -Market auto >> "%LOG%" 2>&1
echo %date% %time%  [launcher] refresh_markets.ps1 exited with code %errorlevel% >> "%LOG%" 2>nul
exit /b %errorlevel%

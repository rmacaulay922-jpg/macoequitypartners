@echo off
cd /d "%~dp0"
echo === Pull Miami-Dade county-wide leads (runs on THIS machine, then publishes) ===
echo This reads the county property roll and can take a few minutes. Please wait...
if exist ".git\index.lock" del /f ".git\index.lock"
powershell -ExecutionPolicy Bypass -File tools\refresh_markets.ps1 -Market miami
echo.
echo === If it printed "wrote miami-leads.js", the county-wide market is now live in ~1-2 min. ===
pause

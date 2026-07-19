@echo off
REM Registers the 6-hourly inbound-lead poller as a Windows scheduled task.
REM Run once, as administrator. See tools\inbox-README.md.
setlocal
set "REPO=%~dp0.."
pushd "%REPO%" || exit /b 1

if not exist "%LOCALAPPDATA%\Maco\inbox-config.json" (
  echo.
  echo   No credentials file found at:
  echo     %LOCALAPPDATA%\Maco\inbox-config.json
  echo.
  echo   The mailbox has to exist first. See tools\inbox-README.md steps 1-4.
  echo   Nothing was scheduled.
  echo.
  popd & exit /b 1
)

schtasks /create /tn "Maco Inbox Poller" /f ^
  /tr "cmd /c cd /d \"%CD%\" && python tools\inbox_poller.py >> tools\inbox\poller.log 2>&1" ^
  /sc hourly /mo 6 /st 07:00 /rl LIMITED

if errorlevel 1 (
  echo   Could not register the task. Run this file as administrator.
  popd & exit /b 1
)

echo.
echo   Scheduled: "Maco Inbox Poller" runs every 6 hours from 07:00.
echo   Drafts will appear in tools\inbox\drafts\
echo   Check it with:  schtasks /query /tn "Maco Inbox Poller"
echo.
popd
endlocal

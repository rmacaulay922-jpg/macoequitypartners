@echo off
rem One-shot launcher: bake Miami ZIP sale bands (overnight cold-quota window), then publish.
set REPO=C:\Users\rmaca\OneDrive\Documents\GitHub\macoequitypartners
set LOG=%REPO%\tools\real_refresh_log.txt
cd /d "%REPO%"
echo %date% %time%  [band-launcher] baking ALL-county ZIP sale bands + comps >> "%LOG%" 2>nul
"C:\Users\rmaca\AppData\Local\Python\pythoncore-3.14-64\python.exe" tools\bake_zip_bands.py miami >> "%LOG%" 2>&1
if errorlevel 1 (
  echo %date% %time%  [band-launcher] band bake FAILED - not committing >> "%LOG%" 2>nul
  exit /b 1
)
git add zip-value-bands.js
git commit -m "Miami ZIP sale bands (overnight bake)" >> "%LOG%" 2>&1
git push origin main >> "%LOG%" 2>&1
echo %date% %time%  [band-launcher] done - bands committed and pushed >> "%LOG%" 2>nul
exit /b 0

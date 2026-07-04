# === Auto-finish Clermont once the Lake County server unblocks ===============
# The Lake PA GIS (gis.lakecountyfl.gov) IP-blocked us during schema mapping (multi-hour WAF block).
# This runs periodically (scheduled task "Maco Finish Clermont"); when the server is reachable it
# scrapes Clermont, wires the Lake market, commits & pushes, then removes its own task. Idempotent
# and safe: if still blocked or data looks wrong, it changes nothing and retries next run.
# ASCII ONLY (Windows PowerShell 5.1).
$ErrorActionPreference='Continue'
$repo='C:\Users\rmaca\OneDrive\Documents\GitHub\macoequitypartners'
$logDir=Join-Path $env:LOCALAPPDATA 'Maco'
if(-not(Test-Path $logDir)){New-Item -ItemType Directory -Path $logDir -Force|Out-Null}
$log=Join-Path $logDir 'clermont.log'
function Say($m){$l="{0}  {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'),$m; Add-Content $log $l; Write-Output $l}
$py=$null
foreach($p in @("$env:LOCALAPPDATA\Python\pythoncore-3.14-64\python.exe","$env:LOCALAPPDATA\Python\bin\python.exe")){if(Test-Path $p){$py=$p;break}}
if(-not $py){foreach($c in (Get-Command python -All -ErrorAction SilentlyContinue)){if(-not $py -and $c.Source -notmatch 'WindowsApps'){$py=$c.Source}}}
if(-not $py){Say 'no python';exit 1}
Set-Location $repo
# Already done?
if(Select-String -Path 'portal.html' -Pattern 'lake-leads.js' -SimpleMatch -Quiet){
  Say 'Clermont already wired - removing task.'; schtasks /delete /tn 'Maco Finish Clermont' /f 2>$null; exit 0
}
Say '===== attempt ====='
& $py 'tools\scrape_lake_clermont.py' 2>&1 | ForEach-Object { Add-Content $log ("   "+$_) }
if(-not(Test-Path 'lake-leads.js')){Say 'no lake-leads.js (still blocked) - will retry.'; exit 0}
$n=(& $py -c "import re,json,io;s=io.open('lake-leads.js',encoding='utf-8').read();m=re.search(r'LAKE_LEADS=(\[.*?\]);',s,re.S);print(len(json.loads(m.group(1))) if m else 0)")
if([int]$n -lt 30){Say "only $n leads - treating as bad/blocked, will retry."; Remove-Item 'lake-leads.js' -Force; exit 0}
# Good data - wire + verify + ship
& $py 'tools\wire_lake.py' 2>&1 | ForEach-Object { Add-Content $log ("   "+$_) }
$chk=(& $py -c "import re,io; s=io.open('portal.html',encoding='utf-8').read(); import sys; blocks=re.findall(r'<script(?![^>]*src=)[^>]*>(.*?)</script>',s,re.S); print('OK' if 'lake-leads.js' in s else 'NOWIRE')")
if($chk -notmatch 'OK'){Say 'wire failed'; git checkout portal.html 2>$null; exit 0}
& node -e "global.window={};require('./lake-leads.js');if(window.LAKE_LEADS.length<30)process.exit(1)" 2>$null
if($LASTEXITCODE -ne 0){Say 'lake-leads.js failed node check'; exit 0}
git pull --rebase origin main 2>&1 | ForEach-Object { Add-Content $log ("   "+$_) }
git add lake-leads.js portal.html tools/scrape_lake_clermont.py tools/wire_lake.py
git commit -m "Add Lake County (Clermont) market - $n motivated-seller leads (auto)" 2>&1 | ForEach-Object { Add-Content $log ("   "+$_) }
git push origin main 2>&1 | ForEach-Object { Add-Content $log ("   "+$_) }
if($LASTEXITCODE -eq 0){Say "SHIPPED Clermont ($n leads). Removing task."; schtasks /delete /tn 'Maco Finish Clermont' /f 2>$null}
else{Say 'push failed (concurrent change?) - will retry next run.'}

# === Maco market refresh - ONE market per run ================================
# Refreshes a single market's lead file from its source, then commits + pushes
# only if the result passes a sanity check.
#
# Usage:  powershell -ExecutionPolicy Bypass -File tools\refresh_markets.ps1 -Market broward
#   broward | lee | collier  -> FDOR statewide roll  -> <market>-leads.js
#   clermont                 -> Lake County PA GIS   -> lake-leads.js
#
# WHY ONE MARKET PER RUN (changed 2026-07-09):
#   The FDOR hosted layer (services9) throttles bursts, then rejects EVERY query
#   with "Invalid query parameters" for many MINUTES. Running Broward/Lee/Collier
#   back-to-back meant counties 2 and 3 failed every time (observed 2026-07-03:
#   broward OK, lee FAILED, collier FAILED). The scheduled tasks now stagger the
#   markets across days - Wed/Thu/Fri/Sat - so each run touches FDOR exactly once.
#
# WHY THE SANITY GUARD:
#   Both scrapers degrade SILENTLY. scrape_fl_county.py prints "page failed after
#   retries - baking the N parcels already pulled" and still exits 0; the Clermont
#   scraper skips failed slices and always exits 0. Without a guard, a throttled
#   run would happily commit a gutted lead file over good data. So we refuse to
#   commit on a partial crawl, a collapsed lead count, or a materially smaller
#   file - and restore the file from git instead.
#
# NOT covered here (by design):
#   - Miami-Dade: already LIVE (the portal pulls county data on every page load).
#   - Polk (incl. Davenport): the county site blocks servers (WebKnight firewall),
#     so Polk must be refreshed from a real Chrome session.
#
# ASCII ONLY - Windows PowerShell 5.1 mis-parses non-ASCII in a no-BOM .ps1.
# ----------------------------------------------------------------------------
param(
  [Parameter(Mandatory=$true)]
  [ValidateSet('broward','lee','collier','clermont')]
  [string]$Market
)
$ErrorActionPreference = 'Continue'
$repo = 'C:\Users\rmaca\OneDrive\Documents\GitHub\macoequitypartners'
$logDir = Join-Path $env:LOCALAPPDATA 'Maco'
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
$log = Join-Path $logDir 'refresh.log'
function Say($m) {
  $line = "{0}  [{1}] {2}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Market, $m
  Add-Content -Path $log -Value $line
  Write-Output $line
}

# Prefer the REAL interpreter - never the Microsoft Store stub in WindowsApps
# (it is first on PATH but can no-op under a headless scheduled task).
$py = $null
foreach ($p in @(
  "$env:LOCALAPPDATA\Python\pythoncore-3.14-64\python.exe",
  "$env:LOCALAPPDATA\Python\bin\python.exe",
  "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe")) { if (Test-Path $p) { $py = $p; break } }
if (-not $py) { foreach ($c in (Get-Command python -All -ErrorAction SilentlyContinue)) { if (-not $py -and $c.Source -notmatch 'WindowsApps') { $py = $c.Source } } }
if (-not $py) { Say 'ERROR: real python not found (only the Store stub) - aborting.'; exit 1 }

Set-Location $repo
Say '--- start ---'
Say "python: $py"

if ($Market -eq 'clermont') { $scrp = 'tools\scrape_lake_clermont.py'; $file = 'lake-leads.js' }
else                        { $scrp = 'tools\scrape_fl_county.py';    $file = "$Market-leads.js" }

function Get-LeadCount($path) {
  if (-not (Test-Path $path)) { return 0 }
  $txt = Get-Content -Path $path -Raw
  $m = [regex]::Match($txt, '"count"\s*:\s*(\d+)')
  if ($m.Success) { return [int]$m.Groups[1].Value }
  return 0
}
function Get-FileSize($path) { if (Test-Path $path) { return (Get-Item $path).Length } else { return 0 } }
function Restore-File { & git checkout -- $file 2>&1 | Out-Null }

$beforeCount = Get-LeadCount $file
$beforeSize  = Get-FileSize  $file
Say "existing: $beforeCount leads, $beforeSize bytes"

# Returns "<exitcode>|<partial 0|1>"
function Invoke-Scrape {
  if ($Market -eq 'clermont') { $out = & $py $scrp 2>&1 | Out-String }
  else                        { $out = & $py $scrp $Market 2>&1 | Out-String }
  $code = $LASTEXITCODE
  if ($out) { Add-Content -Path $log -Value $out.TrimEnd() }
  # Both scrapers can bake partial data and STILL exit 0 - catch that here.
  $partial = 0
  if ($out -and ($out -match 'page failed after retries')) { $partial = 1 }
  if ($out -and ($out -match 'slice \d+ failed'))          { $partial = 1 }
  return ("{0}|{1}" -f $code, $partial)
}

$r = (Invoke-Scrape) -split '\|'
$rc = [int]$r[0]; $partial = [int]$r[1]

if ($rc -ne 0 -or $partial -eq 1) {
  if ($partial -eq 1) { Say 'attempt 1 returned a PARTIAL crawl - discarding.' }
  else                { Say "attempt 1 failed (exit $rc) - source throttle suspected." }
  Restore-File
  Say 'waiting 10 min for the throttle to clear, then retrying once...'
  Start-Sleep -Seconds 600
  $r = (Invoke-Scrape) -split '\|'
  $rc = [int]$r[0]; $partial = [int]$r[1]
}

if ($rc -ne 0 -or $partial -eq 1) {
  Say "FAILED after retry (exit $rc, partial $partial). Restoring file; next scheduled run retries."
  Restore-File
  exit 1
}

# --- sanity guard: never commit a gutted lead file --------------------------
$afterCount = Get-LeadCount $file
$afterSize  = Get-FileSize  $file
Say "scraped: $afterCount leads, $afterSize bytes"

if ($afterCount -lt 25) {
  Say "ABORT: only $afterCount leads - source returned garbage. Restoring."
  Restore-File; exit 1
}
if ($beforeCount -gt 0 -and $afterCount -lt [int]($beforeCount * 0.75)) {
  Say "ABORT: leads collapsed $beforeCount -> $afterCount (>25 pct loss). Restoring."
  Restore-File; exit 1
}
if ($beforeSize -gt 0 -and $afterSize -lt [int]($beforeSize * 0.75)) {
  Say "ABORT: file shrank $beforeSize -> $afterSize bytes (>25 pct loss). Restoring."
  Restore-File; exit 1
}

# Commit ONLY this market's file (the old script swept all four in together).
$changed = (& git status --porcelain -- $file) | Where-Object { $_ }
if ($changed) {
  & git add $file
  $when = Get-Date -Format 'yyyy-MM-dd'
  $msg = "Market refresh ($when) - $Market ($afterCount leads)"
  & git commit -m $msg | Out-Null
  & git push origin main 2>&1 | Out-String | ForEach-Object { if ($_) { Add-Content -Path $log -Value $_.TrimEnd() } }
  if ($LASTEXITCODE -eq 0) { Say "pushed: $msg" }
  else { Say 'ERROR: git push failed - will retry next run.'; exit 1 }
} else {
  Say 'no change (roll unchanged since last run).'
}
Say '--- end ---'
exit 0

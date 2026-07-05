# === Maco weekly market refresh ==============================================
# Re-bakes the Broward / Lee (Fort Myers) / Collier (Naples) lead files from the
# Florida DOR statewide tax roll, then commits and pushes if anything changed.
#
# Scheduled: every Wednesday (Windows Task Scheduler task "Maco Weekly Market Refresh").
# Run by hand any time:  powershell -ExecutionPolicy Bypass -File tools\refresh_markets.ps1
#
# NOT covered here (by design):
#   - Miami-Dade: already LIVE (the portal pulls county comps/violations on every load).
#   - Polk: its county site blocks servers (WebKnight firewall), so Polk must be
#           refreshed from a real Chrome session, then baked with tools\bake_polk_v4.py.
# ASCII ONLY - Windows PowerShell 5.1 mis-parses non-ASCII in a no-BOM .ps1.
# ----------------------------------------------------------------------------
$ErrorActionPreference = 'Continue'
$repo = 'C:\Users\rmaca\OneDrive\Documents\GitHub\macoequitypartners'
$logDir = Join-Path $env:LOCALAPPDATA 'Maco'
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
$log = Join-Path $logDir 'refresh.log'
function Say($m) { $line = "{0}  {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $m; Add-Content -Path $log -Value $line; Write-Output $line }

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
Say '===== weekly refresh start ====='
Say "python: $py"

$counties = @('broward','lee','collier')
$ok = @(); $failed = @()
$first = $true
foreach ($c in $counties) {
  # FDOR throttles after a county's burst; give the service a few minutes to reset between counties
  # so the next county doesn't start inside the throttle window (the scraper also backs off internally).
  if (-not $first) { Say 'cooldown 240s before next county...'; Start-Sleep -Seconds 240 }
  $first = $false
  Say "--- scraping $c ---"
  try {
    $out = & $py 'tools\scrape_fl_county.py' $c 2>&1 | Out-String
    Add-Content -Path $log -Value $out.TrimEnd()
    if ($LASTEXITCODE -eq 0) { $ok += $c; Say "$c OK" } else { $failed += $c; Say "$c FAILED (exit $LASTEXITCODE)" }
  } catch { $failed += $c; Say "$c FAILED ($($_.Exception.Message))" }
}

# Lake County (Clermont) - different server, quote-free scraper (see scrape_lake_clermont.py).
Say 'cooldown 120s, then Lake (Clermont)...'
Start-Sleep -Seconds 120
try {
  $out = & $py 'tools\scrape_lake_clermont.py' 2>&1 | Out-String
  Add-Content -Path $log -Value $out.TrimEnd()
  if ($LASTEXITCODE -eq 0) { $ok += 'clermont'; Say 'clermont OK' } else { $failed += 'clermont'; Say "clermont FAILED (exit $LASTEXITCODE)" }
} catch { $failed += 'clermont'; Say "clermont FAILED ($($_.Exception.Message))" }

# Commit only the lead files that actually changed.
$changed = (& git status --porcelain -- 'broward-leads.js' 'lee-leads.js' 'collier-leads.js' 'lake-leads.js') | Where-Object { $_ }
if ($changed) {
  & git add broward-leads.js lee-leads.js collier-leads.js lake-leads.js
  $when = Get-Date -Format 'yyyy-MM-dd'
  $which = if ($ok.Count) { $ok -join '/' } else { 'no counties' }
  $msg = "Weekly market refresh ($when) - $which"
  & git commit -m $msg | Out-Null
  & git push origin main 2>&1 | Out-String | ForEach-Object { Add-Content -Path $log -Value $_.TrimEnd() }
  if ($LASTEXITCODE -eq 0) { Say "pushed: $msg" } else { Say 'ERROR: git push failed - will retry next run.' }
} else {
  Say 'no changes to commit (county roll unchanged since last run).'
}

if ($failed.Count) { Say ("NOTE: failed this run: {0} (FDOR server is flaky; next Wednesday will retry)." -f ($failed -join ', ')) }
Say 'REMINDER: Polk (incl Davenport) needs a manual browser refresh; Miami-Dade is already live.'
Say '===== weekly refresh end ====='

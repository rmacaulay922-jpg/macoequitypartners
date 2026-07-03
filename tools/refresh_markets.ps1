# ── Maco weekly market refresh ────────────────────────────────────────────────
# Re-bakes the Broward / Lee (Fort Myers) / Collier (Naples) lead files from the
# Florida DOR statewide tax roll, then commits & pushes if anything changed.
#
# Scheduled: every Wednesday (Windows Task Scheduler task "Maco Weekly Market Refresh").
# Run by hand any time:  powershell -ExecutionPolicy Bypass -File tools\refresh_markets.ps1
#
# NOT covered here (by design):
#   • Miami-Dade  — already LIVE (the portal pulls county comps/violations on every load).
#   • Polk        — its county site blocks servers (WebKnight firewall), so Polk must be
#                   refreshed from a real Chrome session, then baked with tools\bake_polk_v4.py.
# ------------------------------------------------------------------------------
$ErrorActionPreference = 'Continue'
$repo = 'C:\Users\rmaca\OneDrive\Documents\GitHub\macoequitypartners'
$logDir = Join-Path $env:LOCALAPPDATA 'Maco'
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
$log = Join-Path $logDir 'refresh.log'
function Say($m) { $line = "{0}  {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $m; Add-Content -Path $log -Value $line; Write-Output $line }

# Resolve python (scheduled tasks may have a lean PATH).
$py = $null
$cmd = Get-Command python -ErrorAction SilentlyContinue
if ($cmd) { $py = $cmd.Source }
if (-not $py) { foreach ($p in @(
  "$env:LOCALAPPDATA\Python\pythoncore-3.14-64\python.exe",
  "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
  "$env:LOCALAPPDATA\Microsoft\WindowsApps\python.exe")) { if (Test-Path $p) { $py = $p; break } } }
if (-not $py) { Say 'ERROR: python not found — aborting.'; exit 1 }

Set-Location $repo
Say '===== weekly refresh start ====='
Say "python: $py"

$counties = @('broward','lee','collier')
$ok = @(); $failed = @()
foreach ($c in $counties) {
  Say "--- scraping $c ---"
  try {
    $out = & $py 'tools\scrape_fl_county.py' $c 2>&1 | Out-String
    Add-Content -Path $log -Value $out.TrimEnd()
    if ($LASTEXITCODE -eq 0) { $ok += $c; Say "$c OK" } else { $failed += $c; Say "$c FAILED (exit $LASTEXITCODE)" }
  } catch { $failed += $c; Say "$c FAILED ($($_.Exception.Message))" }
}

# Commit only the lead files that actually changed.
$changed = (& git status --porcelain -- 'broward-leads.js' 'lee-leads.js' 'collier-leads.js') | Where-Object { $_ }
if ($changed) {
  & git add broward-leads.js lee-leads.js collier-leads.js
  $msg = "Weekly market refresh ({0}) — {1}" -f (Get-Date -Format 'yyyy-MM-dd'), ($(if ($ok.Count) { $ok -join '/' } else { 'no counties' }))
  & git commit -m $msg | Out-Null
  & git push origin main 2>&1 | Out-String | ForEach-Object { Add-Content -Path $log -Value $_.TrimEnd() }
  if ($LASTEXITCODE -eq 0) { Say "pushed: $msg" } else { Say 'ERROR: git push failed — will retry next run.' }
} else {
  Say 'no changes to commit (county roll unchanged since last run).'
}

if ($failed.Count) { Say ("NOTE: failed this run: {0} (FDOR server is flaky; next Wednesday will retry)." -f ($failed -join ', ')) }
Say 'REMINDER: Polk needs a manual browser refresh; Miami-Dade is already live.'
Say '===== weekly refresh end ====='

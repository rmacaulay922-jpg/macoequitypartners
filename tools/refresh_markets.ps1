# === Maco market refresh - ONE market per run ================================
# Refreshes a single market's lead file from its source, then commits + pushes
# only if the result passes a sanity check.
#
# Usage:  powershell -ExecutionPolicy Bypass -File tools\refresh_markets.ps1 -Market broward
#   broward | lee | collier  -> FDOR statewide roll  -> <market>-leads.js
#   clermont                 -> Lake County PA GIS   -> lake-leads.js
#
# WHY ONE MARKET PER RUN, AND NO IN-RUN RETRY (measured 2026-07-09):
#   The FDOR hosted layer (services9) enforces a harsh, SLOW-RESETTING rate limit.
#   Once tripped it rejects EVERYTHING with "Invalid query parameters" after ~55s -
#   including a PARCEL_ID index seek that returned instantly minutes earlier. It is
#   NOT a query-cost problem: cutting page size to 250, dropping geometry, slimming
#   outFields, removing the ORDER BY, and bounding OBJECTID all failed identically.
#   Retrying inside a run just digs the hole deeper. So: ONE market per run, ONE
#   attempt, and a failed market is retried on the NEXT MORNING'S run (see 'auto').
#
# 'auto' MODE (what the scheduled task uses):
#   Picks the single stalest market that has not already been attempted today, so
#   a daily 7am task rotates through all four over ~4 days and self-heals - a market
#   that fails today is retried tomorrow instead of waiting a whole week.
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
#
# !!! CONTAINER TRAP (root cause of the 2026-07-11 "silent failure" misdiagnosis):
# Claude desktop sessions run inside an MSIX app container that VIRTUALIZES
# %LOCALAPPDATA%. A shell inside Claude reads/writes a private copy at
#   AppData\Local\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Local\Maco\
# while the 7am scheduled task (outside the container) uses the REAL
#   C:\Users\rmaca\AppData\Local\Maco\
# The two histories DIVERGE: from a Claude shell the task looks like it never
# logs, and manual runs from a Claude shell update the WRONG state file.
#   - To READ the real log/state from a Claude session: schtasks /run /tn
#     "MacoLogPeek" (runs tools\peek_real_log.bat outside the container, copies
#     both files to tools\real_refresh_*.txt).
#   - To RUN a refresh manually from a Claude session: schtasks /run /tn
#     "Maco Market Refresh" - NEVER run this .ps1 directly from a Claude shell.
# ----------------------------------------------------------------------------
param(
  [Parameter(Mandatory=$true)]
  [ValidateSet('miami','broward','lee','collier','clermont','auto')]
  [string]$Market
)
$ErrorActionPreference = 'Continue'
$repo = 'C:\Users\rmaca\OneDrive\Documents\GitHub\macoequitypartners'
# Hardcoded, NOT $env:LOCALAPPDATA - no scheduled-task run ever landed a log line
# while interactive runs always did (checked 2026-07-11: 224 log lines, zero from
# any 7am run, yet the 7/10 7am run demonstrably committed lake-leads.js). Until
# the vanishing-write cause is confirmed, every write here must be env-independent
# and every failure must land SOMEWHERE we can read.
$logDir = 'C:\Users\rmaca\AppData\Local\Maco'
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
$log = Join-Path $logDir 'refresh.log'
$fallbackLog = Join-Path $repo 'tools\refresh_task_debug.log'
function Say($m) {
  $line = "{0}  [{1}] {2}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Market, $m
  try { Add-Content -Path $log -Value $line -ErrorAction Stop }
  catch { try { Add-Content -Path $fallbackLog -Value ("MAINLOG-FAIL {0} :: {1}" -f $_.Exception.Message, $line) } catch {} }
  Write-Output $line
}
# Boot breadcrumb: records the run context FIRST, so a run that dies early still
# leaves evidence of where it ran and what environment it saw.
$bootLine = "{0}  [boot] market={1} user={2} localappdata={3} cwd={4} ps={5}" -f `
  (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Market, $env:USERNAME, $env:LOCALAPPDATA, (Get-Location).Path, $PSVersionTable.PSVersion
try { Add-Content -Path $log -Value $bootLine -ErrorAction Stop }
catch { try { Add-Content -Path $fallbackLog -Value ("BOOT-FALLBACK {0} :: {1}" -f $_.Exception.Message, $bootLine) } catch {} }

# --- refresh state -----------------------------------------------------------
# One line per market: name|lastSuccess|lastAttempt. Plain text on purpose -
# PS 5.1's ConvertFrom-Json has no -AsHashtable, so JSON here is more trouble
# than it is worth.
# NOTE: 'miami' is EXPLICIT-ONLY (refresh_miami.bat / -Market miami) until the first
# county-wide bake is verified. It must NOT join the daily auto rotation yet: as a
# never-attempted market it would sort stalest and win the pick EVERY morning, and
# a whole-county FDOR pull (topn 3000) is a much bigger bite of the rate budget
# than the 600-row county farms this rotation was tuned for.
$ALL_MARKETS = @('broward','lee','collier','clermont')
$stateFile = Join-Path $logDir 'refresh_state.txt'
$today = Get-Date -Format 'yyyy-MM-dd'
function Read-State {
  $h = @{}
  if (Test-Path $stateFile) {
    foreach ($ln in (Get-Content $stateFile)) {
      if ($ln -notmatch '\S') { continue }
      $p = $ln -split '\|'
      if ($p.Count -ge 3) { $h[$p[0]] = @{ success = $p[1]; attempt = $p[2] } }
    }
  }
  return $h
}
function Save-State($h) {
  $lines = foreach ($k in ($h.Keys | Sort-Object)) { '{0}|{1}|{2}' -f $k, $h[$k].success, $h[$k].attempt }
  try { Set-Content -Path $stateFile -Value $lines -Encoding ASCII -ErrorAction Stop }
  catch { try { Add-Content -Path $fallbackLog -Value ("STATE-FAIL {0} :: {1}" -f $_.Exception.Message, ($lines -join ' / ')) } catch {} }
}
function Set-MarketState($m, $succeeded) {
  $h = Read-State
  if (-not $h.ContainsKey($m)) { $h[$m] = @{ success = 'never'; attempt = 'never' } }
  $h[$m].attempt = $today
  if ($succeeded) { $h[$m].success = $today }
  Save-State $h
}

# 'auto': refresh the stalest market that has not already been attempted today.
# A market that fails is therefore retried tomorrow, not next week.
if ($Market -eq 'auto') {
  $st = Read-State
  $cand = @($ALL_MARKETS | Where-Object { -not $st.ContainsKey($_) -or $st[$_].attempt -ne $today })
  if ($cand.Count -eq 0) { Say 'auto: every market was already attempted today - nothing to do.'; exit 0 }
  # Primary key: oldest success ('never' -> '0000-00-00', so never-succeeded goes first).
  # Secondary key: oldest ATTEMPT. Without it, two never-succeeded markets tie forever and
  # the stable sort would keep picking the same one, starving the other.
  # NOTE: @(...) then Select-Object - Sort-Object on a 1-item list returns the STRING,
  # and [0] on a string yields its first CHARACTER. That silently set $Market='c'.
  $picked = @($cand | Sort-Object -Property `
      @{ Expression = { if ($st.ContainsKey($_) -and $st[$_].success -ne 'never') { $st[$_].success } else { '0000-00-00' } } }, `
      @{ Expression = { if ($st.ContainsKey($_) -and $st[$_].attempt -ne 'never') { $st[$_].attempt } else { '0000-00-00' } } }) |
      Select-Object -First 1
  if ($ALL_MARKETS -notcontains $picked) { Say "auto: could not select a market (got '$picked') - aborting."; exit 1 }
  $Market = $picked
  Say "auto: selected '$Market' (stalest market not yet attempted today)"
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

# ONE attempt. FDOR's rate limit resets over HOURS, not minutes - measured
# 2026-07-09, when even an indexed PARCEL_ID seek that had worked minutes before
# started failing at ~55s. Retrying in-run only extends the lockout. Tomorrow's
# 'auto' run will pick this market again because its lastSuccess stays stale.
if ($rc -ne 0 -or $partial -eq 1) {
  if ($partial -eq 1) { Say 'PARTIAL crawl (source cut us off mid-pull) - discarding, NOT committing.' }
  else                { Say "scrape failed (exit $rc) - source rate limit or outage." }
  Restore-File
  Set-MarketState $Market $false
  Say 'will retry on tomorrow morning''s run.'
  exit 1
}

# --- sanity guard: never commit a gutted lead file --------------------------
$afterCount = Get-LeadCount $file
$afterSize  = Get-FileSize  $file
Say "scraped: $afterCount leads, $afterSize bytes"

if ($afterCount -lt 25) {
  Say "ABORT: only $afterCount leads - source returned garbage. Restoring."
  Restore-File; Set-MarketState $Market $false; exit 1
}
if ($beforeCount -gt 0 -and $afterCount -lt [int]($beforeCount * 0.75)) {
  Say "ABORT: leads collapsed $beforeCount -> $afterCount (>25 pct loss). Restoring."
  Restore-File; Set-MarketState $Market $false; exit 1
}
if ($beforeSize -gt 0 -and $afterSize -lt [int]($beforeSize * 0.75)) {
  Say "ABORT: file shrank $beforeSize -> $afterSize bytes (>25 pct loss). Restoring."
  Restore-File; Set-MarketState $Market $false; exit 1
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
  else { Say 'ERROR: git push failed - will retry next run.'; Set-MarketState $Market $false; exit 1 }
} else {
  Say 'no change (roll unchanged since last run).'
}
Set-MarketState $Market $true
Say '--- end ---'
exit 0

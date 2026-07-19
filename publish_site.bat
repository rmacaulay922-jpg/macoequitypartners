@echo off
cd /d "%~dp0"
echo === Maco Equity Partners - publish site ===
if exist ".git\index.lock" del /f ".git\index.lock"
if exist "_preview_maco_homepage.html" del /f "_preview_maco_homepage.html"
git add index.html firm.html about.html research.html portal.html demo.html MARKETING-KIT.md styles.css da.css site-config.js markets.html reports.html methodology.html compare.html updates.html handout.html auctions-fl.js tools/scrape_auctions.py tools/lispendens-README.md trial/index.html off-market-deals-miami-dade.html off-market-deals-broward.html off-market-deals-lee.html off-market-deals-collier.html off-market-deals-polk.html off-market-deals-lake.html tools/bake_zip_bands.py tools/band_bake_launcher.cmd WEEK-1-PLAYBOOK.md tools/prospects-miami.csv tools/prospects-README.md robots.txt sitemap.xml fdor-mailing-miami.js fdor-enrich.js zip-value-bands.js fdor-harness-report.md tools/refresh_launcher.cmd og-card.png lake-leads.js trial.html Q1_2026_New_Industrial_Supply.html Q1_2026_SFL_Industrial_Overview.html Q1_2026_Small_Bay_Deals.html logo-full.png logo-full-light.png logo-mark.png logo-mark-light.png favicon.png favicon.jpg logo.jpg assets/da-01.png blog.html privacy.html terms.html disclosures.html post-2026-outlook.html post-first-100-days.html post-hiring-operators.html post-palm-beach-industrial.html post-underwriting-is-the-edge.html post-value-add-underwrite.html Q1_2026_New_Industrial_Supply.html Q1_2026_SFL_Industrial_Overview.html Q1_2026_SFL_Residential_Overview.html Q1_2026_Small_Bay_Deals.html Q2_2026_SFL_Residential_Overview.html miami-leads.js tools/scrape_fl_county.py tools/refresh_markets.ps1 publish_site.bat refresh_miami.bat pricing.html hero-miami.mp4 hero-miami-aerial.jpg dossier-1.jpg dossier-2.jpg dossier-3.jpg tools/inbox_poller.py tools/inbox-README.md tools/inbox_launcher.cmd .gitignore
REM Ask for a message instead of reusing a stale hardcoded one. The old default
REM described a release from weeks ago and was being stamped on every deploy,
REM which makes the history useless for working out when something changed.
set "MSG="
set /p "MSG=Describe this change (Enter for a dated default): "
if "%MSG%"=="" set "MSG=Site update %DATE% %TIME%"

git commit -m "%MSG%"
if errorlevel 1 (
  echo.
  echo === Nothing to commit, or the commit failed. Not pushing. ===
  pause
  exit /b 1
)

git push origin main
if errorlevel 1 (
  echo.
  echo === PUSH FAILED - the site was NOT updated. Scroll up for the reason. ===
  pause
  exit /b 1
)

echo.
echo === Done. Site updates at macoequitypartners.com in ~1-2 minutes. ===
pause

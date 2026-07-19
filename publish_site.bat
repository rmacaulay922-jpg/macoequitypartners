@echo off
cd /d "%~dp0"
echo === Maco Equity Partners - publish site ===
if exist ".git\index.lock" del /f ".git\index.lock"
if exist "_preview_maco_homepage.html" del /f "_preview_maco_homepage.html"
git add index.html firm.html about.html research.html portal.html demo.html MARKETING-KIT.md styles.css da.css site-config.js markets.html reports.html methodology.html compare.html updates.html off-market-deals-miami-dade.html off-market-deals-broward.html off-market-deals-lee.html off-market-deals-collier.html off-market-deals-polk.html off-market-deals-lake.html tools/bake_zip_bands.py tools/band_bake_launcher.cmd WEEK-1-PLAYBOOK.md tools/prospects-miami.csv tools/prospects-README.md robots.txt sitemap.xml fdor-mailing-miami.js fdor-enrich.js zip-value-bands.js fdor-harness-report.md tools/refresh_launcher.cmd og-card.png lake-leads.js trial.html Q1_2026_New_Industrial_Supply.html Q1_2026_SFL_Industrial_Overview.html Q1_2026_Small_Bay_Deals.html logo-full.png logo-full-light.png logo-mark.png logo-mark-light.png favicon.png favicon.jpg logo.jpg assets/da-01.png blog.html privacy.html terms.html disclosures.html post-2026-outlook.html post-first-100-days.html post-hiring-operators.html post-palm-beach-industrial.html post-underwriting-is-the-edge.html post-value-add-underwrite.html Q1_2026_New_Industrial_Supply.html Q1_2026_SFL_Industrial_Overview.html Q1_2026_SFL_Residential_Overview.html Q1_2026_Small_Bay_Deals.html Q2_2026_SFL_Residential_Overview.html miami-leads.js tools/scrape_fl_county.py tools/refresh_markets.ps1 publish_site.bat refresh_miami.bat
git commit -m "Wider homepage, pricing CTAs + footer, RYAN-01 login, Miami-Dade county-wide pipeline"
git push origin main
echo.
echo === Done. Site updates at macoequitypartners.com in ~1-2 minutes. ===
pause

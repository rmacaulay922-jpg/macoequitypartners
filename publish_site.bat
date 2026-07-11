@echo off
cd /d "%~dp0"
echo === Maco Equity Partners - publish site ===
if exist ".git\index.lock" del /f ".git\index.lock"
if exist "_preview_maco_homepage.html" del /f "_preview_maco_homepage.html"
git add index.html firm.html research.html portal.html styles.css blog.html privacy.html terms.html disclosures.html post-2026-outlook.html post-first-100-days.html post-hiring-operators.html post-palm-beach-industrial.html post-underwriting-is-the-edge.html post-value-add-underwrite.html Q1_2026_New_Industrial_Supply.html Q1_2026_SFL_Industrial_Overview.html Q1_2026_SFL_Residential_Overview.html Q1_2026_Small_Bay_Deals.html Q2_2026_SFL_Residential_Overview.html miami-leads.js tools/scrape_fl_county.py tools/refresh_markets.ps1 publish_site.bat refresh_miami.bat
git commit -m "Wider homepage, pricing CTAs + footer, RYAN-01 login, Miami-Dade county-wide pipeline"
git push origin main
echo.
echo === Done. Site updates at macoequitypartners.com in ~1-2 minutes. ===
pause

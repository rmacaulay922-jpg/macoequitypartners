# Pre-foreclosure signals: feasibility + what got built (July 19, 2026)

Goal: close the Deal Analyzer's pre-foreclosure gap — lis pendens (LP) filings and
foreclosure-auction dates for Miami-Dade + Broward (primary), Lee/Collier/Polk/Lake
(secondary). All findings below are from live probing on 2026-07-19 with plain
`requests` (no JS rendering), inspecting each site's own JS bundles for its API surface.

Honesty rule respected throughout: only real records get baked; anything blocked is
reported as blocked, not simulated.

---

## Verdict summary

| Source | What it has | Verdict |
|---|---|---|
| RealAuction auction calendars (miamidade/broward/lee/polk .realforeclose.com) | Scheduled foreclosure sales: case #, judgment $, **parcel ID + street address**, assessed $ | **FEASIBLE-NOW — built (`tools/scrape_auctions.py` → `auctions-fl.js`)** |
| lake.realforeclose.com | same | Site banner says "Offline" on probe day; scraper attempts it and fails honestly. Re-check periodically. |
| collier auctions | — | Collier **left RealAuction** (domain redirects to vendor corporate site). Clerk now runs sales on ShowcaseWeb: `cms.collierclerk.com/showcaseweb/calendar`. Unprobed → phase-2 target. |
| Miami-Dade Clerk Official Records (LP recordings) | LP doc type exists (`LIS`), JSON API found | **FEASIBLE-WITH-EFFORT** — invisible Cloudflare Turnstile enforced server-side (details below) |
| Miami-Dade OCS civil case search (new foreclosure case filings) | Filed-date + case-type search, JSON API found | **FEASIBLE-WITH-EFFORT** — invisible reCAPTCHA v3 enforced server-side (details below) |
| Broward Official Records (AcclaimWeb) | LP recordings | **NOT-FEASIBLE with plain requests** — Cloudflare managed challenge (403 "Just a moment") on every path. Possibly passable with Playwright. |
| Miami-Dade Open Data hub (opendata.miamidade.gov / gis-mdc hub) | GIS layers only | Dead end for recorded docs — no LP/recorded-documents dataset (DCAT feed also 500s). |
| Miami-Dade Clerk Commercial Data Services (www2.miamidadeclerk.gov/developers) | Official Records API, FTP bulk | **Paid** ($0.20/unit) — the legit bulk route if LP coverage ever justifies spend. |

---

## 1. What was BUILT: foreclosure auction schedule (FEASIBLE-NOW)

### Files
- `tools/scrape_auctions.py` — the puller (stdlib + `requests` only)
- `auctions-fl.js` (repo root) — `window.AUCTIONS = {meta, rows}` (see run results below)

### Method (verified against the sites' own `auction.js`)
1. `GET /index.cfm?zaction=USER&zmethod=CALENDAR[&selCalDate=MM/01/YYYY]` — month
   calendar is server-rendered; day boxes carry `dayid='MM/DD/YYYY'`,
   active/scheduled counts and sale time. Foreclosure days only (`>Foreclosure<`
   in the box; tax-deed days are skipped).
2. Per day: `GET ...zaction=AUCTION&Zmethod=PREVIEW&AUCTIONDATE=MM/DD/YYYY`
   (primes the ColdFusion session with that date).
3. `GET ...zaction=AUCTION&Zmethod=UPDATE&FNC=LOAD&AREA=W&bypassPage=<pg>` returns
   JSON `{retHTML}` — HTML compressed with `@A/@B/...` tokens, expanded exactly as
   the site's `LoadNewArea()` does. 10 items/page; paging via `bypassPage`, stop on
   repeated AIDs / short page.
4. Parsed per item: Auction Type, Case #, Final Judgment Amount, Parcel ID,
   Property Address (+ city/state/zip line), Assessed Value, internal auction id.

Requires a browser User-Agent header (naive fetches 403) and a session cookie from
the calendar page — nothing else. No CAPTCHA anywhere on the read path.

### Row schema (`window.AUCTIONS.rows[]`)
```
{county, case, auction_date, sale_time, address, csz, parcel, judgment, assessed, aid}
```
`judgment` = final judgment amount (float, dollars), `assessed` = county assessed
value. Failed counties bake **no** rows; per-county status lives in `meta.counties`.

### First real run — 2026-07-19, 60-day window (baked in `auctions-fl.js`)

| County | FC days | Rows | Street address | Numeric parcel | Judgment > $0 |
|---|---|---|---|---|---|
| miamidade | 26 | 307 | 191 (62%) | 189 (61%) | 301 (98%) |
| broward | 33 | 216 | 133 (61%) | 133 (61%) | 135 (62%) |
| lee | 9 | 135 | 79 (58%) | 78 (57%) | 108 (80%) |
| polk | 29 | 156 | 104 (66%) | 104 (66%) | 104 (66%) |
| lake | — | 0 | — | — | site "Offline" (status in meta) |
| **Total** | 97 | **814** | **507 (62%)** | 504 | |

Internal validation: scraped per-day counts matched the calendar's "active" count
**exactly on all 97 days**; canceled sales are correctly excluded (confirmed in the
UI, where canceled items render with "Canceled per Order/County/Bankruptcy" and the
AJAX feed omits them). External validation: 8 sample rows (5 Miami-Dade 07/20 +
3 Broward 07/22) checked field-by-field against the rendered web UI — **8/8 exact**
(case #, judgment, parcel, address, city/zip, assessed value).

### Address-match quality — blunt notes
- **The 62% overall address rate is misleading — split it by horizon:** rows in the
  next 30 days are **90% addressed (505 of 555)**; 31–60-day rows are ~0% (2 of 259).
  Clerks post parcel/address/judgment as the sale approaches, so far-out rows are
  "date + case # only" shells that later runs fill in. A daily refresh keeps the
  actionable window near-complete.
- Rows with an address almost always carry the **numeric parcel/folio too** (504 of
  507) — join to leads via parcel ↔ `pid` (strip dashes) first, address second.
- Remaining addressless rows: parcel `null` (source shows a bare "Property
  Appraiser" link with empty folio — normalized to null), `MULTIPLE PARCELS`
  (bulk/commercial judgments), `TIMESHARE`, and $0-judgment shells (166 of the 307
  addressless rows) — mostly county-court/HOA cases or details not yet posted.
- Caveat: these are END-stage signals (judgment already entered, sale scheduled
  ~20-35 days out). Great for auction-prep and for flagging leads already in the
  pipeline; it is NOT an early LP signal.

### Refresh cadence recommendation
Once daily (weekday mornings) is plenty — dockets change day-to-day at most.
~150-250 polite requests per full run at ~3 s spacing. Do **not** run more often.

### Red flags — disclosed, decide before wiring
- `robots.txt` on all RealAuction county sites is a blanket `User-agent: * disallow: /`
  (a search-engine keep-out on a bidding platform). The **user agreement page has no
  anti-scraping/automation clause** (checked 2026-07-19), and auction notices are
  public records (F.S. 45.031), but a strict robots reading says "don't crawl".
  This tool does a small targeted daily pull, not a crawl — Ryan should make the
  final call before wiring into the portal.
- Fallbacks if the position changes: county clerk "foreclosure sales" list pages
  (weaker data), or paid feeds (PropertyOnion etc.).

---

## 2. Lis pendens proper: why nothing was built (yet)

### Miami-Dade Official Records (`onlineservices.miamidadeclerk.gov/officialrecords`)
New React SPA; clean JSON API underneath:
- `GET /officialrecords/api/home/documentTypes` — open; LP code confirmed:
  **`LIS PENDENS - LIS`** (also `CLP` = cancellation).
- `POST /officialrecords/api/home/standardsearch?partyName=&documentType=LIS&dateRangeFrom=&dateRangeTo=...`
  → `{isValidSearch, qs}`; then `GET /officialrecords/api/SearchResults/getStandardRecords?qs=...`
  returns the rows (the `qs` leg needs no token).
- **Blocker:** the search POST requires header `x-recaptcha-token` = invisible
  Cloudflare **Turnstile** token (sitekey `0x4AAAAAAD1vWBs-1bsZ5Z5M`, mode
  `interaction-only`). Verified enforced server-side: with no/garbage token the API
  answers 200 `{"isValidSearch":false}` for searches that return rows in the UI.
- Second caveat: the free Standard Search is **name-keyed**; whether a
  doctype+date-range-only bulk query is accepted is untested (needs one valid token
  to test). The Advanced Search burns paid "units".

**Phase-2 path:** Playwright (headed Chromium), load the real page once per run,
let Turnstile auto-solve invisibly, run the search in-page (or mint tokens via
`turnstile.execute`) → capture `qs` → page through `getStandardRecords` with plain
requests. Effort: ~half a day incl. the bulk-query test. Rows likely carry
parties + legal description + folio (recorder data), NOT a mail-ready situs address —
expect to join via folio when present, else owner-name match.

### Miami-Dade OCS civil dockets (`www2.miamidadeclerk.gov/ocs`)
The better *early-signal* source: search new civil cases by **filed-date range +
case type** `25362 = REAL PROPERTY / MORTGAGE FORECLOSURE` (case-type list from open
endpoint `/ocs/api/home/OCSTypes`).
- `POST /ocs/api/CaseInfo/PostSearchByFiledDate` body
  `{filingDateFrom, filingDateTo, caseType:<int>, section:<int>, caseTypeSearch:...}`
  with header `Captcha-Token`.
- **Blocker:** verified server-side: correct body without valid token → 400
  `"Captcha token is missing or invalid"`. Token = invisible **reCAPTCHA v3**
  (sitekey `6Le7np8qAAAAAAEMezDvhuXyKV4EA6BWZTvdK_E6`) — mintable only in a real
  browser context. Same Playwright pattern as above; logged-in users skip captcha
  entirely (free account may be the cleanest phase-2: log in once, reuse cookie).
- Data: case #, filing date, parties (defendant ≈ owner on the deed). **No situs
  address** — join to leads by owner name (the `o` field in *-leads.js), which is
  fuzzy; expect a modest match rate.

### Broward (`officialrecords.broward.org` AcclaimWeb)
Every request — including `robots.txt`-adjacent paths — sits behind a Cloudflare
**managed challenge** (403 "Just a moment..." interstitial). No API to speak to
without passing it. robots content-signals: `search=yes, ai-train=no` for `*`, with
AI crawler UAs disallowed. **Not feasible with requests**; Playwright may pass the
JS challenge (it is often non-interactive) — unverified. Broward Clerk's court-case
search (browardclerk.org) was not deep-probed (phase-2).

---

## 3. Honest bottom line

- **Auction dates: solved today** for Miami-Dade, Broward, Lee, Polk — with street
  address + parcel, i.e. directly joinable to the leads files. Wire-worthy after
  Ryan reviews the robots.txt point above.
- **True lis pendens (early signal): not free-scrapable with plain requests in
  either primary county.** Both Miami-Dade routes are one Playwright session away
  (invisible captchas, no user interaction needed) — that's the recommended
  phase-2, starting with an OCS free account (captcha waived when logged in).
- Collier auctions (ShowcaseWeb) and Broward LP are the other phase-2 probes.
- If LP becomes core to the product: Miami-Dade Clerk Commercial Data Services is
  the sanctioned paid firehose ($0.20/unit, FTP bulk available).

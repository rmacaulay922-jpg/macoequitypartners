#!/usr/bin/env python3
"""
scrape_auctions.py - Florida county foreclosure-auction calendar puller.

Pulls upcoming foreclosure auctions (next N days, default 60) from the
county RealAuction sites ({county}.realforeclose.com) and bakes them into
a portal-style data file:  auctions-fl.js  ->  window.AUCTIONS

Counties (July 2026 status, verified by live probe):
  miamidade  OK   - full detail: case #, judgment, parcel/folio, street address
  broward    OK   - same vendor/markup
  lee        OK   - same vendor/markup
  polk       OK   - same vendor/markup
  lake       DOWN - site banner says "Offline" (attempted anyway; fails honestly)
  collier    GONE - left RealAuction; clerk now uses ShowcaseWeb
                    (cms.collierclerk.com/showcaseweb/calendar) - not scraped here.

Method (no JS rendering needed):
  1. GET /index.cfm?zaction=USER&zmethod=CALENDAR          (day boxes w/ FC counts)
     plus following months via &selCalDate=MM/01/YYYY to cover the window
  2. Per auction day: GET ...zaction=AUCTION&Zmethod=PREVIEW&AUCTIONDATE=MM/DD/YYYY
     (primes the CF session with that date)
  3. AJAX JSON: ...zaction=AUCTION&Zmethod=UPDATE&FNC=LOAD&AREA=W&bypassPage=<pg>
     -> {"retHTML": token-compressed HTML}. Tokens (@A,@B,...) are expanded
     exactly the way the site's own /CORE/System/JS/auction.js does, then the
     AUCTION_ITEM blocks are parsed for the detail table.

Honesty rules: a county either completes cleanly or its rows are DROPPED and
the failure is printed + recorded in meta. No partial-silent bakes.

Politeness: single session per county, ~3s between requests, one run per day
is plenty (calendar changes daily at most). NOTE: these sites publish a
blanket robots.txt "disallow: /" (aimed at search crawlers). This tool does a
small, targeted, once-daily pull of public-record sale notices (F.S. 45.031);
keep the pacing as-is and do not increase run frequency.

Usage:
  python tools/scrape_auctions.py                 # default counties, 60 days
  python tools/scrape_auctions.py --counties miamidade,broward --days 30
  python tools/scrape_auctions.py --dry-run       # scrape + report, no file write
"""

import argparse
import datetime as dt
import html as htmlmod
import json
import random
import re
import sys
import time
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_FILE = REPO_ROOT / "auctions-fl.js"

DEFAULT_COUNTIES = ["miamidade", "broward", "lee", "polk", "lake"]

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
BASE_HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# retHTML token expansion - mirrors LoadNewArea() in the site's auction.js
RETHTML_SUBS = [
    ("@A", '<div class="'), ("@B", "</div>"), ("@C", 'class="'), ("@D", "<div>"),
    ("@E", "AUCTION"), ("@F", "</td><td"), ("@G", "</td></tr>"), ("@H", "<tr><td "),
    ("@I", "table"), ("@J", 'p_back="NextCheck='), ("@K", 'style="Display:none"'),
    ("@L", "/index.cfm?zaction=auction&zmethod=details&AID="),
]

MAX_PAGES_PER_DAY = 40          # hard safety cap (10 items/page)
SLEEP_BASE = 2.6                # seconds between HTTP requests
SLEEP_JITTER = 1.2


def polite_sleep():
    time.sleep(SLEEP_BASE + random.random() * SLEEP_JITTER)


def clean_text(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s)
    s = htmlmod.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def money(s: str):
    m = re.search(r"\$?\s*([\d,]+(?:\.\d+)?)", s)
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", ""))
    except ValueError:
        return None


def decode_rethtml(rh: str) -> str:
    for a, b in RETHTML_SUBS:
        rh = rh.replace(a, b)
    return rh


def month_starts(start: dt.date, end: dt.date):
    """First-of-month dates covering [start, end]."""
    out = []
    d = start.replace(day=1)
    while d <= end:
        out.append(d)
        d = (d + dt.timedelta(days=32)).replace(day=1)
    return out


def get_fc_days(sess, base, start, end, log):
    """Return sorted [(date, active_count, sched_count, sale_time)] of FC days in window."""
    days = {}
    for ms in month_starts(start, end):
        url = f"{base}/index.cfm?zaction=USER&zmethod=CALENDAR&selCalDate={ms:%m/%d/%Y}"
        r = sess.get(url, timeout=40)
        r.raise_for_status()
        if "Offline" in r.text[:6000] and "CALDAYBOX" not in r.text:
            raise RuntimeError("site reports itself Offline")
        boxes = re.findall(r"dayid='(\d\d/\d\d/\d{4})'(.*?)(?=dayid='|CALDAYBOX|$)",
                           r.text, re.S)
        for dstr, blob in boxes:
            if ">Foreclosure<" not in blob:
                continue  # tax-deed or other auction types
            m = re.search(r'CALACT">(\d+)</span>\s*/\s*<span[^>]*class="CALSCH">(\d+)</span>', blob)
            if not m:
                continue
            tmt = re.search(r'CALTIME">\s*([^<]+?)\s*<', blob)
            d = dt.datetime.strptime(dstr, "%m/%d/%Y").date()
            if start <= d <= end:
                days[d] = (int(m.group(1)), int(m.group(2)),
                           tmt.group(1).strip() if tmt else None)
        polite_sleep()
    out = sorted((d, a, s, t) for d, (a, s, t) in days.items())
    log(f"  calendar: {len(out)} foreclosure day(s) in window")
    return out


ITEM_SPLIT = re.compile(r'id="AITEM_(\d+)"')
PAIR_RE = re.compile(
    r'class="AD_LBL"[^>]*>\s*(.*?)\s*</td>\s*<td[^>]*class="AD_DTA[^"]*"[^>]*>(.*?)</td>',
    re.S)


def parse_items(decoded_html):
    """Yield dicts parsed from AUCTION_ITEM blocks of a decoded retHTML page."""
    parts = ITEM_SPLIT.split(decoded_html)
    # parts = [prefix, aid1, chunk1, aid2, chunk2, ...]
    for i in range(1, len(parts) - 1, 2):
        aid, chunk = parts[i], parts[i + 1]
        item = {"aid": aid}
        pending_addr = False
        for lbl_raw, val_raw in PAIR_RE.findall(chunk):
            lbl = clean_text(lbl_raw).rstrip(":").lower()
            val = clean_text(val_raw)
            if lbl == "auction type":
                item["auction_type"] = val
            elif lbl in ("case #", "case number"):
                item["case"] = val
            elif lbl == "final judgment amount":
                item["judgment"] = money(val)
            elif lbl == "parcel id":
                # Items with no parcel on file render a bare "Property Appraiser"
                # link (empty folio= href) - that placeholder becomes None. Other
                # non-numeric markers (MULTIPLE PARCELS, TIMESHARE) are kept verbatim.
                item["parcel"] = None if val.upper() == "PROPERTY APPRAISER" else val
            elif lbl == "property address":
                item["address"] = val
                pending_addr = True
            elif lbl == "assessed value":
                item["assessed"] = money(val)
            elif lbl == "" and pending_addr and val:
                item["csz"] = val          # "MIAMI, FL- 33184" line under address
                pending_addr = False
        yield item


def scrape_day(sess, base, day, log):
    """Scrape all W-area (scheduled) auction items for one date."""
    prev_url = f"{base}/index.cfm?zaction=AUCTION&Zmethod=PREVIEW&AUCTIONDATE={day:%m/%d/%Y}"
    r = sess.get(prev_url, timeout=40)
    r.raise_for_status()
    polite_sleep()

    ajax_headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": prev_url,
    }
    rows, seen = [], set()
    for pg in range(1, MAX_PAGES_PER_DAY + 1):
        tx = int(time.time() * 1000)
        url = (f"{base}/index.cfm?zaction=AUCTION&Zmethod=UPDATE&FNC=LOAD"
               f"&AREA=W&PageDir=0&doR=0&tx={tx}&bypassPage={pg}")
        r = sess.get(url, headers=ajax_headers, timeout=40)
        r.raise_for_status()
        data = r.json()
        page_items = list(parse_items(decode_rethtml(data.get("retHTML", ""))))
        new = [it for it in page_items if it["aid"] not in seen]
        if not new:
            break  # past the last page (server repeats/empties)
        for it in new:
            seen.add(it["aid"])
            rows.append(it)
        polite_sleep()
        if len(page_items) < 10:
            break  # short page = last page
    return rows


def scrape_county(county, start, end, log):
    base = f"https://{county}.realforeclose.com"
    sess = requests.Session()
    sess.headers.update(BASE_HEADERS)

    r = sess.get(f"{base}/index.cfm?zaction=USER&zmethod=CALENDAR", timeout=40)
    r.raise_for_status()
    final_host = requests.utils.urlparse(r.url).netloc
    if county not in final_host:
        raise RuntimeError(f"redirected off-site to {final_host} (county left RealAuction?)")
    if "<h1>Offline</h1>" in r.text:
        raise RuntimeError("site reports itself Offline")
    polite_sleep()

    days = get_fc_days(sess, base, start, end, log)
    county_rows, day_notes = [], []
    for day, active, sched, sale_time in days:
        items = scrape_day(sess, base, day, log)
        fc = [it for it in items if "FORECLOS" in it.get("auction_type", "").upper()]
        log(f"  {day}: {len(fc)} items scraped (calendar says {active} active / {sched} scheduled)")
        if active and abs(len(fc) - active) > max(2, active * 0.2):
            day_notes.append(f"{day}: scraped {len(fc)} vs {active} active on calendar")
        for it in fc:
            county_rows.append({
                "county": county,
                "case": it.get("case"),
                "auction_date": day.isoformat(),
                "sale_time": sale_time,
                "address": it.get("address"),
                "csz": it.get("csz"),
                "parcel": it.get("parcel"),
                "judgment": it.get("judgment"),
                "assessed": it.get("assessed"),
                "aid": it.get("aid"),
            })
    return county_rows, len(days), day_notes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--counties", default=",".join(DEFAULT_COUNTIES))
    ap.add_argument("--days", type=int, default=60)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    counties = [c.strip().lower() for c in args.counties.split(",") if c.strip()]
    today = dt.date.today()
    end = today + dt.timedelta(days=args.days)

    def log(msg):
        print(msg, flush=True)

    log(f"Foreclosure auction pull  {today} .. {end}  counties: {', '.join(counties)}")

    all_rows, meta_counties = [], {}
    for county in counties:
        log(f"\n[{county}]")
        try:
            rows, ndays, notes = scrape_county(county, today, end, log)
            addr = sum(1 for r in rows if r.get("address"))
            meta_counties[county] = {
                "status": "ok", "days": ndays, "rows": len(rows),
                "with_address": addr,
            }
            if notes:
                meta_counties[county]["day_notes"] = notes
            all_rows.extend(rows)
            log(f"  => {len(rows)} rows, {addr} with street address")
        except Exception as e:
            meta_counties[county] = {"status": f"FAILED: {e}", "days": 0, "rows": 0}
            log(f"  => FAILED, no rows baked for this county: {e}")

    ok_counties = [c for c, m in meta_counties.items() if m["status"] == "ok"]
    if not ok_counties or not all_rows:
        log("\nNo county completed cleanly - refusing to write output file.")
        sys.exit(1)

    payload = {
        "meta": {
            "as_of": today.isoformat(),
            "window_days": args.days,
            "src": "county RealAuction foreclosure calendars ({county}.realforeclose.com), scheduled ('W') items only",
            "generated_by": "tools/scrape_auctions.py",
            "counties": meta_counties,
            "notes": [
                "collier left RealAuction (clerk uses ShowcaseWeb at cms.collierclerk.com) - not covered",
                "judgment = final judgment amount as listed; assessed = county assessed value as listed",
                "rows are auctions still scheduled at pull time; canceled sales drop off the source",
            ],
        },
        "rows": all_rows,
    }

    log(f"\nTOTAL: {len(all_rows)} auction rows from {len(ok_counties)} county/ies "
        f"({sum(1 for r in all_rows if r.get('address'))} with street address)")

    if args.dry_run:
        log("--dry-run: not writing file.")
        return

    js = ("// Florida foreclosure-auction schedule - generated "
          f"{dt.datetime.now():%Y-%m-%d %H:%M} by tools/scrape_auctions.py\n"
          "// Source: county RealAuction foreclosure calendars (public judicial-sale notices, F.S. 45.031).\n"
          "// Counties + per-county status in meta.counties. Failed counties bake NO rows.\n"
          "window.AUCTIONS=" + json.dumps(payload, ensure_ascii=True, separators=(",", ":")) + ";\n")
    OUT_FILE.write_text(js, encoding="utf-8")
    log(f"Wrote {OUT_FILE}  ({OUT_FILE.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()

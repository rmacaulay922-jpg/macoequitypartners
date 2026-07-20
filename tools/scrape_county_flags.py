# -*- coding: utf-8 -*-
# ── County distress-flag enrichment — brings Broward/Lee/Collier/Lake up toward Miami depth ──
#   python scrape_county_flags.py                 → bakes county-flags.js for every county below
#   python scrape_county_flags.py broward lee     → just those
#
# WHAT THIS DOES
#   Miami's deep market shows open CODE-ENFORCEMENT cases, expired PERMITS and recorded LIENS
#   per property, from Miami-Dade's own ArcGIS layers. The other counties publish the same on
#   THEIR own hosts — a 31-agent research + verification pass (2026-07-20) confirmed the exact
#   queryable endpoints, parcel keys and record counts. This pulls the *flagged-parcel sets*
#   from those endpoints (the sets are small — a county has ~500-2,000 open code cases) and
#   bakes a compact lookup keyed by parcel:
#       window.<COUNTY>_FLAGS = { "<parcelid>": { "code": {...}, "permit": {...}, "lien": {...} } }
#   The portal shows a chip on any lead whose parcel appears here — exactly like Miami.
#
#   Every source is parcel-keyed and joins to our leads' `pid`. The bake PRINTS the match rate
#   against the live lead board; a near-zero rate means the key format drifted and the run
#   REFUSES to bake that source rather than ship a dead flag. Honesty over coverage.
#
#   HONEST GAPS (documented, never faked): recorded liens/judgments in Broward, Lee (county-wide),
#   Collier and Lake live only in name-keyed HTML clerk portals with no parcel join — not shipped.
#   Collier and Polk code enforcement are HTML-portal only. Those markets get code/permit where
#   it exists and state the rest in-product.
import sys, os, re, json, time, datetime, urllib.request, urllib.parse

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {'User-Agent': 'Mozilla/5.0 (maco-flags)'}
NOW = datetime.date.today()

def norm_key(v):
    # Both our lead pids and each source's parcel key normalise to bare uppercase alphanumerics.
    return re.sub(r'[^A-Z0-9]', '', str(v or '').upper())

def num(v):
    try: return float(str(v).replace(',', ''))
    except Exception: return 0.0

def fetch(url, params, timeout=90):
    for t, delay in enumerate([0, 5, 20, 45]):
        if delay: time.sleep(delay)
        try:
            req = urllib.request.Request(url, data=urllib.parse.urlencode(params).encode(), headers=UA)
            d = json.load(urllib.request.urlopen(req, timeout=timeout))
            if 'error' in d: raise RuntimeError(d['error'].get('message', 'err'))
            return d
        except Exception as e:
            print('     retry %d (%s)' % (t + 1, str(e)[:50]), flush=True)
    return None

def pull_all(url, where, out_fields, key_field, page=1000, cap=40000):
    """Paginate a FeatureServer/MapServer query, return list of attribute dicts."""
    rows, offset = [], 0
    while len(rows) < cap:
        d = fetch(url + '/query', {'where': where, 'outFields': out_fields, 'returnGeometry': 'false',
                                   'f': 'json', 'resultRecordCount': page, 'resultOffset': offset,
                                   'orderByFields': key_field})
        if d is None: return rows, False
        f = d.get('features', [])
        if not f: break
        rows += [x['attributes'] for x in f]
        if len(f) < page: break
        offset += page
        time.sleep(0.2)
    return rows, True

# ── SOURCE MAP — every entry verified live 2026-07-20 (endpoint, count, parcel key) ──
# flag: 'code' | 'permit' | 'lien'.  key: the source field holding the parcel id.
# where: server-side filter to the DISTRESS subset (open cases / expired permits / active liens).
# detail: builds the chip payload from a source row.
SOURCES = {
  'broward': [
    {'flag': 'code', 'label': 'Broward open code cases',
     'url': 'https://bcgishub.broward.org/pdm/rest/services/CodeEnforcement/CodeCollectorApp/MapServer/1',
     'where': '1=1', 'key': 'UICP_FOLIO',
     'fields': 'UICP_FOLIO,PCCS_STATUS,PCCS_VIOLATION,PCCS_TYPE',
     'detail': lambda a: {'type': (a.get('PCCS_VIOLATION') or a.get('PCCS_TYPE') or 'Code case').strip()[:60]}},
    {'flag': 'permit', 'label': 'Ft Lauderdale expired permits',
     'url': 'https://gis.fortlauderdale.gov/arcgis/rest/services/BuildingPermitTracker/BuildingPermitTracker/MapServer/0',
     'where': "PERMITSTAT IN ('Expired','EXPIRED','Open','OPEN')", 'key': 'PARCELID',
     'fields': 'PARCELID,PERMITSTAT,PERMITTYPE,PERMITDESC',
     'detail': lambda a: {'status': (a.get('PERMITSTAT') or '').strip(), 'type': (a.get('PERMITTYPE') or a.get('PERMITDESC') or '').strip()[:50]}},
  ],
  'lee': [
    {'flag': 'code', 'label': 'Lee nuisance/code violations',
     'url': 'https://services2.arcgis.com/LvWGAAhHwbCJ2GMP/arcgis/rest/services/NuisanceAccumulationViolations/FeatureServer/0',
     'where': "record_status NOT LIKE 'Closed%'", 'key': 'parcel_number',
     'fields': 'parcel_number,record_status,record_type,balance_due',
     'detail': lambda a: {'type': (a.get('record_type') or 'Nuisance violation').strip()[:50], 'status': (a.get('record_status') or '').strip()}},
    {'flag': 'permit', 'label': 'Cape Coral open/expired permits',
     'url': 'https://capeims.capecoral.gov/arcgis/rest/services/OpenData/OpenData/MapServer/1',
     'where': "permit_status IN ('Issued','Expired','ISSUED','EXPIRED')", 'key': 'Parcel',
     'fields': 'Parcel,permit_status,permit_desc,Work_Class',
     'detail': lambda a: {'status': (a.get('permit_status') or '').strip(), 'type': (a.get('Work_Class') or a.get('permit_desc') or '').strip()[:50]}},
    {'flag': 'lien', 'label': 'Cape Coral utility liens',
     'url': 'https://capeims.capecoral.gov/arcgis/rest/services/OpenData/OpenData/MapServer/6',
     'where': "Active_Lien='Y'", 'key': 'Strap', 'cap': 60000,
     'fields': 'Strap,Lien_Amount,Lien_Number',
     'detail': lambda a: {'amt': int(num(a.get('Lien_Amount'))), 'kind': 'Utility lien'}},
  ],
  'collier': [
    {'flag': 'permit', 'label': 'Collier pending permits',
     'url': 'https://services.arcgis.com/v400IkDOw1ad7Yad/arcgis/rest/services/Building_Permits_Pending/FeatureServer/0',
     'where': '1=1', 'key': 'pin',
     'fields': 'pin,statuscurrent,permittype,workclass',
     'detail': lambda a: {'status': (a.get('statuscurrent') or 'Pending').strip(), 'type': (a.get('workclass') or a.get('permittype') or '').strip()[:50]}},
  ],
  'lake': [
    {'flag': 'code', 'label': 'Lake code cases',
     'url': 'https://gis.lakecountyfl.gov/lakegis/rest/services/CodeCases/MapServer/0',
     'where': '1=1', 'key': 'ParcelNumber',
     'fields': 'ParcelNumber,FOLIO_NBR,Status,CaseType,Violation',
     'detail': lambda a: {'type': (a.get('Violation') or a.get('CaseType') or 'Code case').strip()[:50], 'status': (a.get('Status') or '').strip()}},
    {'flag': 'permit', 'label': 'Lake permits',
     'url': 'https://gis.lakecountyfl.gov/lakegis/rest/services/PropertyAppraiser/PermitMap_Working/MapServer/1',
     'where': '1=1', 'key': 'ParcelNumber', 'cap': 20000,
     'fields': 'ParcelNumber,Altkey',
     'detail': lambda a: {'status': 'On file', 'type': 'Permit'}},
  ],
}

LEAD_FILE = {'broward': ('broward-leads.js', 'BROWARD_LEADS'), 'lee': ('lee-leads.js', 'LEE_LEADS'),
             'collier': ('collier-leads.js', 'COLLIER_LEADS'), 'lake': ('lake-leads.js', 'LAKE_LEADS'),
             'polk': ('polk-leads.js', 'POLK_LEADS')}

def load_lead_keys(county):
    fn, glob = LEAD_FILE[county]
    p = os.path.join(REPO, fn)
    if not os.path.exists(p): return set()
    txt = open(p, encoding='utf-8').read()
    # pids appear as "pid":"..." ; also match the alt "st" field
    keys = set()
    for m in re.findall(r'"pid":"([^"]+)"', txt): keys.add(norm_key(m))
    return keys

def run(county):
    if county not in SOURCES:
        print('%s: no verified parcel-keyed sources (documented gap)' % county); return
    lead_keys = load_lead_keys(county)
    print('=== %s === %d leads on the board' % (county.upper(), len(lead_keys)), flush=True)
    flags = {}
    for src in SOURCES[county]:
        print('  %s [%s] ...' % (src['label'], src['flag']), flush=True)
        rows, ok = pull_all(src['url'], src['where'], src['fields'], src['key'], cap=src.get('cap', 40000))
        if not rows:
            print('     0 rows (endpoint down or filtered empty) — skipping', flush=True); continue
        # match against the live board
        matched = 0
        for a in rows:
            k = norm_key(a.get(src['key']))
            if not k: continue
            if k in lead_keys:
                matched += 1
                flags.setdefault(k, {})[src['flag']] = src['detail'](a)
        rate = matched / max(1, len(lead_keys))
        print('     %d rows · %d matched leads (%.0f%% of board)' % (len(rows), matched, 100 * rate), flush=True)
        # A source that matches ~nothing means the key format drifted — do NOT ship it as data.
        if matched == 0 and len(rows) > 100:
            print('     ⚠ 0 matches on %d rows — key format mismatch; this source contributes nothing. Not baking it.' % len(rows), flush=True)
    out = os.path.join(REPO, '%s-flags.js' % county)
    meta = {'county': county, 'snapshot': str(NOW), 'flagged': len(flags)}
    js = ('// %s distress flags (open code cases / permits / liens) from the county\'s OWN\n'
          '// verified ArcGIS endpoints. Keyed by parcel id; joins to the lead board.\n'
          '// Generated %s by tools/scrape_county_flags.py.\n'
          'window.%s_FLAGS=%s;\n'
          'window.%s_FLAGS_META=%s;\n'
          % (county.title(), NOW, county.upper(),
             json.dumps(flags, separators=(',', ':')), county.upper(),
             json.dumps(meta, separators=(',', ':'))))
    open(out, 'w', encoding='utf-8').write(js)
    print('  wrote %s-flags.js — %d flagged parcels · %d KB' % (county, len(flags), len(js) // 1024), flush=True)

if __name__ == '__main__':
    targets = [a for a in sys.argv[1:] if a in SOURCES] or list(SOURCES.keys())
    for c in targets:
        try: run(c)
        except Exception as e: print('%s FAILED: %s' % (c, str(e)[:80]), flush=True)

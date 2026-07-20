# -*- coding: utf-8 -*-
# ── Miami-Dade COUNTY-WIDE motivated-seller scraper — Miami-Dade's OWN reliable host ──
#   python scrape_miami_pa.py            → bakes miami-leads.js (MIAMI_LEADS/_META)
#
# WHY THIS EXISTS, and why it is NOT scrape_fl_county.py:
#   The FDOR statewide cadastral layer answers a trivial `1=1` query instantly but TIMES
#   OUT on the heavy filtered county queries a real crawl needs (measured repeatedly
#   2026-07-20). Every heavy attempt against it extends the lockout, and county-wide Miami
#   has therefore NEVER baked — miami-leads.js has been a 438-byte stub since 07-11, so the
#   portal's "Miami-Dade · County-wide" market shows nothing.
#
#   Miami-Dade publishes its OWN full parcel roll on its OWN ArcGIS host — the same host
#   the deep-Miami market already queries live and reliably — via
#     PaGISView_gdb / FeatureServer / 0   (services.arcgis.com/8Pc9XBTAsYuxx9Ny)
#   319,543 single-family parcels (DOR_CODE_CUR '0101'), paginated at 2000/page with
#   resultOffset, responding in milliseconds. It carries owner, full mailing address,
#   heated sqft, year built, bedroom/bathroom counts, lot size, AND last sale price + date.
#   VERIFIED 2026-07-20.
#
#   The ONE thing Miami-Dade's public GIS withholds is parcel value (TOTAL_VAL_CUR is null
#   county-wide — a county policy). That is fine: every market's headline value already
#   comes from the ZIP sale band × sqft, and we compute Miami's bands HERE from PaGISView's
#   own PRICE_1/DOS_1 sale data — so the entire Miami pipeline runs on the reliable host and
#   never touches throttled FDOR.
import json, re, time, datetime, urllib.request, urllib.parse, os
sys_path = os.path.dirname(os.path.abspath(__file__))

REPO = os.path.dirname(sys_path)
BASE = 'https://services.arcgis.com/8Pc9XBTAsYuxx9Ny/arcgis/rest/services/PaGISView_gdb/FeatureServer/0/query'
UA = {'User-Agent': 'Mozilla/5.0 (maco-miami-pa)'}
NOW = datetime.date.today()
PAGE = 2000
TOPN = 3000          # top leads by motivation score that ship to the board

OUT_LEADS = os.path.join(REPO, 'miami-leads.js')
OUT_BANDS = os.path.join(REPO, 'zip-value-bands.js')

# ZIP → investor-recognizable neighborhood. PaGISView's TRUE_SITE_CITY is "Miami" for most
# of the county; investors farm by neighborhood, and neighborhood == ZIP here. Same map the
# FDOR scraper used, so labels are consistent across both Miami markets.
MIAMI_ZIP_AREA = {
 '33125':'Little Havana','33126':'Flagami','33127':'Wynwood/Little Haiti','33128':'Downtown','33129':'Brickell/Coconut Grove',
 '33130':'Little Havana','33131':'Brickell','33132':'Downtown','33133':'Coconut Grove','33134':'Coral Gables',
 '33135':'Little Havana','33136':'Overtown','33137':'Upper Eastside','33138':'Upper Eastside','33139':'Miami Beach',
 '33140':'Miami Beach','33141':'North Beach','33142':'Brownsville','33143':'South Miami','33144':'Flagami',
 '33145':'Shenandoah','33146':'Coral Gables','33147':'West Little River','33150':'Little Haiti','33154':'Bal Harbour/Surfside',
 '33155':'Westchester','33156':'Pinecrest','33157':'Palmetto Bay','33158':'Palmetto Bay','33160':'Sunny Isles/NMB',
 '33161':'North Miami','33162':'North Miami Beach','33165':'Westchester','33166':'Miami Springs/Doral','33167':'North Miami',
 '33168':'North Miami','33169':'Miami Gardens','33170':'Goulds','33172':'Doral','33173':'Kendall',
 '33174':'Sweetwater','33175':'Tamiami','33176':'Kendall','33177':'Three Lakes','33178':'Doral',
 '33179':'NE Miami-Dade','33180':'Aventura','33181':'North Miami','33182':'Tamiami West','33183':'Kendale Lakes',
 '33184':'Tamiami','33185':'West Kendall','33186':'Kendall SE','33187':'Redland','33189':'Cutler Bay',
 '33190':'Cutler Bay','33193':'West Kendall','33196':'West Kendall','33055':'Miami Gardens','33056':'Miami Gardens',
 '33054':'Opa-locka','33010':'Hialeah','33012':'Hialeah','33013':'Hialeah','33014':'Hialeah','33015':'Miami Lakes',
 '33016':'Hialeah','33018':'Hialeah Gardens','33030':'Homestead','33031':'Redland','33032':'Princeton/Naranja',
 '33033':'Homestead','33034':'Florida City','33035':'Homestead',
}

_STATES = {'ALABAMA':'AL','ALASKA':'AK','ARIZONA':'AZ','ARKANSAS':'AR','CALIFORNIA':'CA','COLORADO':'CO',
 'CONNECTICUT':'CT','DELAWARE':'DE','FLORIDA':'FL','GEORGIA':'GA','HAWAII':'HI','IDAHO':'ID','ILLINOIS':'IL',
 'INDIANA':'IN','IOWA':'IA','KANSAS':'KS','KENTUCKY':'KY','LOUISIANA':'LA','MAINE':'ME','MARYLAND':'MD',
 'MASSACHUSETTS':'MA','MICHIGAN':'MI','MINNESOTA':'MN','MISSISSIPPI':'MS','MISSOURI':'MO','MONTANA':'MT',
 'NEBRASKA':'NE','NEVADA':'NV','NEW HAMPSHIRE':'NH','NEW JERSEY':'NJ','NEW MEXICO':'NM','NEW YORK':'NY',
 'NORTH CAROLINA':'NC','NORTH DAKOTA':'ND','OHIO':'OH','OKLAHOMA':'OK','OREGON':'OR','PENNSYLVANIA':'PA',
 'RHODE ISLAND':'RI','SOUTH CAROLINA':'SC','SOUTH DAKOTA':'SD','TENNESSEE':'TN','TEXAS':'TX','UTAH':'UT',
 'VERMONT':'VT','VIRGINIA':'VA','WASHINGTON':'WA','WEST VIRGINIA':'WV','WISCONSIN':'WI','WYOMING':'WY',
 'DISTRICT OF COLUMBIA':'DC'}
_US_ABBR = set(_STATES.values()) | {'PR','VI','GU','DC'}

def norm_state(s):
    s = (s or '').strip().upper()
    if not s: return ''
    if s in _STATES: return _STATES[s]
    if len(s) == 2 and s in _US_ABBR: return s
    if len(s) == 2: return s          # unknown 2-char — keep, treated as non-FL
    return 'Foreign'

def num(v):
    try: return float(str(v).replace(',', ''))
    except Exception: return 0.0

def norm(s): return re.sub(r'[^A-Z0-9]', '', (s or '').upper())

def classify(own):
    o = ' ' + (own or '').upper() + ' '
    if ' LLC ' in o or ' INC ' in o or 'CORP' in o or 'COMPANY' in o or ' LP ' in o or ' LTD ' in o: return 'entity'
    if 'EST OF' in o or 'ESTATE OF' in o or ' HEIRS' in o or o.rstrip().endswith(' EST'): return 'probate'
    if 'TRUST' in o or ' TR ' in o or o.rstrip().endswith(' TR') or ' TRS ' in o: return 'trust'
    return 'other'

def query(where, offset, out_fields):
    body = {'where': where, 'outFields': out_fields, 'returnGeometry': 'false',
            'f': 'json', 'resultRecordCount': PAGE, 'resultOffset': offset, 'orderByFields': 'FOLIO'}
    # This host is reliable, but be a good citizen: a short escalating retry, no marathon.
    for t, delay in enumerate([0, 5, 20, 60]):
        if delay: time.sleep(delay)
        try:
            req = urllib.request.Request(BASE, data=urllib.parse.urlencode(body).encode(), headers=UA)
            d = json.load(urllib.request.urlopen(req, timeout=90))
            if 'error' in d: raise RuntimeError(d['error'].get('message', 'error'))
            return d
        except Exception as e:
            print('   retry %d (%s)' % (t + 1, str(e)[:55]), flush=True)
    return None

def sale_year(dos):
    # DOS_1 is 'YYYYMMDD' string or epoch-ms via DATEOFSALE_UTC; PRICE_1 pairs with DOS_1.
    s = str(dos or '')
    m = re.match(r'(\d{4})', s)
    if m:
        y = int(m.group(1))
        if 1900 < y <= NOW.year: return y
    return None

def run():
    fields = ('FOLIO,TRUE_SITE_ADDR,TRUE_SITE_CITY,TRUE_SITE_ZIP_CODE,TRUE_OWNER1,TRUE_OWNER2,'
              'TRUE_MAILING_ADDR1,TRUE_MAILING_CITY,TRUE_MAILING_STATE,TRUE_MAILING_ZIP_CODE,'
              'BUILDING_HEATED_AREA,YEAR_BUILT,LOT_SIZE,BEDROOM_COUNT,BATHROOM_COUNT,PRICE_1,DOS_1,X_COORD,Y_COORD')
    where = "DOR_CODE_CUR='0101' AND BUILDING_HEATED_AREA>400"
    print('=== Miami-Dade county-wide (PaGISView, Miami-Dade host) ===', flush=True)
    print('single-family with a real house; paginating %d/page' % PAGE, flush=True)

    raw, offset = [], 0
    while True:
        d = query(where, offset, fields)
        if d is None:
            if not raw: raise SystemExit('first page failed — Miami-Dade host unreachable, re-run later.')
            print('   page failed after retries — baking the %d parcels pulled so far.' % len(raw), flush=True)
            break
        f = d.get('features', [])
        if not f: break
        raw += [x['attributes'] for x in f]
        print('   ...%d parcels' % len(raw), flush=True)
        if len(f) < PAGE: break
        offset += PAGE
        time.sleep(0.25)
    if not raw:
        raise SystemExit('0 parcels — schema/filter wrong; not baking.')
    print('pulled %d single-family parcels' % len(raw), flush=True)

    # ---- 1) Build ZIP bands from PaGISView's own recent sales (reliable-host comps) ----
    # $/sf from PRICE_1 / heated sqft, recent (>=2022), sane range — the same qualified-sale
    # convention as bake_zip_bands.py, but sourced from Miami-Dade's host instead of FDOR.
    by_zip = {}
    for a in raw:
        z = (str(a.get('TRUE_SITE_ZIP_CODE') or '')[:5])
        sp, sf, sy = num(a.get('PRICE_1')), num(a.get('BUILDING_HEATED_AREA')), sale_year(a.get('DOS_1'))
        if z and sp > 50000 and sf > 400 and sy and sy >= 2022:
            ppsf = sp / sf
            if 60 <= ppsf <= 1200:
                by_zip.setdefault(z, {'ppsf': [], 'sales': []})
                by_zip[z]['ppsf'].append(ppsf)
                by_zip[z]['sales'].append({'a': (a.get('TRUE_SITE_ADDR') or '').strip().title(),
                                           'p': int(sp), 'sf': int(sf), 'ppsf': int(round(ppsf)), 'y': sy})

    def pct(vals, q):
        vals = sorted(vals); i = q * (len(vals) - 1); lo = int(i)
        return vals[lo] + (vals[min(lo + 1, len(vals) - 1)] - vals[lo]) * (i - lo)

    bands = {}
    if os.path.exists(OUT_BANDS):
        m = re.search(r'window\.ZIP_BANDS\s*=\s*(\{.*?\});', open(OUT_BANDS, encoding='utf-8').read(), re.S)
        if m: bands = json.loads(m.group(1))
    baked_zips = 0
    for z, agg in by_zip.items():
        ppsf = [p for p in agg['ppsf'] if 60 <= p <= 1200]
        k = int(len(ppsf) * 0.05)
        ppsf = sorted(ppsf)[k:len(ppsf) - k] if len(ppsf) > 2 * k else sorted(ppsf)
        if len(ppsf) < 8: continue
        sales = sorted(agg['sales'], key=lambda r: -r['y'])[:6]
        bands[z] = {'med': round(pct(ppsf, 0.5)), 'p25': round(pct(ppsf, 0.25)),
                    'p75': round(pct(ppsf, 0.75)), 'n': len(ppsf),
                    'as_of': '%d-%02d' % (NOW.year, NOW.month), 'comps': sales}
        baked_zips += 1
    print('baked %d Miami ZIP bands from PaGISView sales' % baked_zips, flush=True)
    js_b = ('// ZIP-level qualified-sale $/sf bands (Miami-Dade from PaGISView PRICE_1; other\n'
            '// counties from FDOR). p25/med/p75 per sqft; n = trimmed sale count; comps = recent sales.\n'
            '// Generated %s by tools/scrape_miami_pa.py + bake_zip_bands.py.\n'
            'window.ZIP_BANDS=%s;\n' % (NOW, json.dumps(bands, sort_keys=True, separators=(',', ':'))))
    open(OUT_BANDS, 'w', encoding='utf-8').write(js_b)

    def band_mid(z, sqft):
        b = bands.get(z)
        if b and b.get('med') and b.get('n', 0) >= 8 and sqft > 0:
            return int(b['med'] * sqft)
        return 0

    # ---- 2) Score + shape leads (schema matches POLK_LEADS so the portal renders unchanged) ----
    cands = []
    for a in raw:
        addr = (a.get('TRUE_SITE_ADDR') or '').strip()
        fol = re.sub(r'\s', '', str(a.get('FOLIO') or ''))
        if not addr or not fol: continue
        z = str(a.get('TRUE_SITE_ZIP_CODE') or '')[:5]
        sqft = int(num(a.get('BUILDING_HEATED_AREA')))
        est = band_mid(z, sqft)
        if not (60000 <= est <= 700000):        # flip band, priced off the ZIP band × sqft
            continue
        own = (a.get('TRUE_OWNER1') or '').strip()
        if a.get('TRUE_OWNER2'): own = (own + ' ' + a['TRUE_OWNER2'].strip()).strip()
        cls = classify(own)
        mst = norm_state(a.get('TRUE_MAILING_STATE'))
        m1 = (a.get('TRUE_MAILING_ADDR1') or '').strip()
        oos = bool(mst) and mst != 'FL'
        absentee = (not oos) and bool(m1) and norm(m1)[:12] != norm(addr)[:12]
        yr = int(num(a.get('YEAR_BUILT'))); age = (NOW.year - yr) if yr > 1800 else 0
        sy = sale_year(a.get('DOS_1')); sp = int(num(a.get('PRICE_1')))
        held = (NOW.year - sy) if sy else None
        signal = cls != 'other' or oos or absentee or (held is not None and held >= 15)
        if not signal: continue
        sc = {'probate': 42, 'entity': 26, 'trust': 22, 'other': 8}[cls]
        if oos: sc += 22
        elif absentee: sc += 12
        if held is not None: sc += 18 if held >= 25 else (12 if held >= 15 else (6 if held >= 8 else 0))
        if age >= 55: sc += 14
        elif age >= 45: sc += 10
        ozip = str(a.get('TRUE_MAILING_ZIP_CODE') or '')[:5]
        mail3 = ((a.get('TRUE_MAILING_CITY') or '').strip() + (' ' + mst if mst else '') + (' ' + ozip if ozip else '')).strip()
        area = MIAMI_ZIP_AREA.get(z, (a.get('TRUE_SITE_CITY') or 'Miami').strip().title())
        lat = round(num(a.get('Y_COORD')), 6) if a.get('Y_COORD') else None
        lng = round(num(a.get('X_COORD')), 6) if a.get('X_COORD') else None
        # X/Y here are state-plane, not lat/lng — leave lat/lng null (portal maps by address); keep for future.
        cands.append({'a': addr.title(), 'c': area, 'z': z,
            'o': own, 'm1': m1.title(), 'm3': mail3, 'mst': mst or 'FL', 'oos': 1 if oos else 0, 'abs': 1 if absentee else 0,
            'tag': cls, 'sc': min(sc, 100), 'mkt': est, 'asr': 0, 'tax': 0,
            'bld': 0, 'lnd': 0, 'lot': round(num(a.get('LOT_SIZE')) / 43560, 2),
            'held': held, 'lsY': sy, 'lsP': sp or None, 'rt': None,
            'sqft': (sqft if sqft > 200 else None), 'yb': (yr if yr > 1800 else None),
            'bed': int(num(a.get('BEDROOM_COUNT'))) or None, 'bath': num(a.get('BATHROOM_COUNT')) or None,
            'pid': fol, 'st': fol})
    cands.sort(key=lambda x: (-x['sc'], -x['mkt']))
    cands = cands[:TOPN]
    markets = sorted(set(x['c'] for x in cands))
    meta = {'county': 'Miami-Dade', 'count': len(cands), 'snapshot': str(NOW),
            'roll': 'Miami-Dade PA (PaGISView)', 'markets': markets}
    js = ('// Miami-Dade COUNTY-WIDE motivated-seller leads — generated %s by scrape_miami_pa.py\n'
          '// from the Miami-Dade Property Appraiser PaGISView layer (the county\'s own host,\n'
          '// NOT the throttled FDOR statewide roll). Non-condo single-family, priced off ZIP\n'
          '// sale bands, top %d by motivation score. Schema matches the other county boards.\n'
          'window.MIAMI_LEADS=%s;\n'
          'window.MIAMI_META=%s;\n'
          % (NOW, len(cands), json.dumps(cands, separators=(',', ':')), json.dumps(meta, separators=(',', ':'))))
    open(OUT_LEADS, 'w', encoding='utf-8').write(js)
    print('wrote miami-leads.js — %d leads · %d neighborhoods · %d KB' % (len(cands), len(markets), len(js) // 1024), flush=True)

if __name__ == '__main__':
    run()

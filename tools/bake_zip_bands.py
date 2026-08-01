# Bake/refresh ZIP-level qualified-sale $/sf bands into zip-value-bands.js (MERGE, not overwrite).
# Usage: python bake_zip_bands.py miami   (or: python bake_zip_bands.py 33125,33126,...)
# Method proven by the July-18 FDOR harness: QUAL_CD1 in ('01','02') separates arm's-length sales
# from $100 quitclaims; stats are computed locally (server-side statistics 400 on this host);
# throttles are ridden out with full 8.5-minute cooldowns, and partials are saved to disk.
import sys, os, re, json, time, urllib.request, urllib.parse, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fdor_lock import fdor_lock

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT  = os.path.join(REPO, 'zip-value-bands.js')
SERVICE = 'https://services9.arcgis.com/Gh9awoU677aKree0/arcgis/rest/services/Florida_Statewide_Cadastral/FeatureServer/0'
UA = {'User-Agent': 'Mozilla/5.0 (maco-band-bake)'}
NOW = datetime.date.today()

MIAMI_ZIPS = ['33125','33126','33127','33128','33129','33130','33131','33132','33133','33134',
 '33135','33136','33137','33138','33139','33140','33141','33142','33143','33144','33145','33146',
 '33147','33150','33154','33155','33156','33157','33158','33160','33161','33162','33165','33166',
 '33167','33168','33169','33170','33172','33173','33174','33175','33176','33177','33178','33179',
 '33180','33181','33182','33183','33184','33185','33186','33187','33189','33190','33193','33196',
 '33055','33056','33054','33010','33012','33013','33014','33015','33016','33018','33030','33031',
 '33032','33033','33034','33035']

def num(v):
    try: return float(v or 0)
    except Exception: return 0.0

def query(where, last_oid, out_fields):
    w = where + (' AND OBJECTID>%d' % last_oid if last_oid else '')
    body = {'where': w, 'outFields': out_fields, 'returnGeometry': 'false', 'f': 'json',
            'resultRecordCount': 2000, 'orderByFields': 'OBJECTID'}
    DELAYS = [20, 60, 510, 510]   # ride out up to two full 8.5-min cooldowns
    for t in range(5):
        try:
            req = urllib.request.Request(SERVICE + '/query', data=urllib.parse.urlencode(body).encode(), headers=UA)
            d = json.load(urllib.request.urlopen(req, timeout=120))
            if 'error' in d: raise RuntimeError(d['error'].get('message', 'error'))
            return d
        except Exception as e:
            print('   retry %d (%s)' % (t + 1, str(e)[:60]), flush=True)
            if t < len(DELAYS): time.sleep(DELAYS[t])
    return None

# FDOR county numbers (alphabetical + 10) for the counties whose ZIPs we bake.
# Used to BOUND each zip query to one county — see band_for_zip.
ZIP_CO = {}          # populated in main() from the leads files; zip -> CO_NO
CO_BY_FILE = {'broward': 16, 'collier': 21, 'lake': 45, 'lee': 46, 'miami': 23, 'polk': 63}


def band_for_zip(z):
    # HYPOTHESIS, NOT YET PROVEN (2026-08-01): this query carried no CO_NO bound, making it a
    # STATEWIDE scan filtered by zip — the same unbounded-deep-scan shape that FDOR load-sheds
    # elsewhere (see scrape_fl_county.py's sweep comment). Every other query in this codebase that
    # works is county-bounded. The bake has produced ZERO zips on every logged run for weeks
    # ("DONE: 0 baked ... 4 failed", 07-26 through 07-29), so a bounded query cannot be worse.
    # Measured the same day: the unbounded form hung past 100s without responding; the bounded
    # form returned an error in 55s — but FDOR was already throttled by then, so that comparison
    # does NOT establish the bound as the cure. Re-test on a cold service before believing it.
    co = ZIP_CO.get(str(z))
    where = ("DOR_UC='001' AND QUAL_CD1 IN ('01','02') AND SALE_YR1>=2024 "
             "AND TOT_LVG_AR>500 AND SALE_PRC1>50000 AND PHY_ZIPCD=%s" % z)
    if co:
        where += " AND CO_NO=%d" % co
    rows, sales, last = [], [], 0
    while True:
        d = query(where, last, 'OBJECTID,SALE_PRC1,TOT_LVG_AR,PHY_ADDR1,SALE_YR1')
        if d is None: return None            # terminal — caller records the failure honestly
        f = d.get('features', [])
        if not f: break
        for x in f:
            a = x['attributes']
            sp, sf = num(a.get('SALE_PRC1')), num(a.get('TOT_LVG_AR'))
            if sp > 0 and sf > 0:
                rows.append((sp / sf, sf))     # keep sqft — $/sf varies strongly WITH house size
                addr = (a.get('PHY_ADDR1') or '').strip()
                yr = int(num(a.get('SALE_YR1')))
                if addr and 60 <= sp / sf <= 1200:
                    sales.append({'a': addr.title(), 'p': int(sp), 'sf': int(sf),
                                  'ppsf': int(round(sp / sf)), 'y': yr})
        last = max(int(num(x['attributes'].get('OBJECTID'))) for x in f)
        if len(f) < 2000: break
        time.sleep(3)
    rows = [r for r in rows if 60 <= r[0] <= 1200]
    rows.sort(key=lambda r: r[0])
    k = int(len(rows) * 0.05)
    rows = rows[k:len(rows) - k] if len(rows) > 2 * k else rows
    if len(rows) < 8: return {'thin': len(rows)}
    # Keep the 6 most recent as displayable comps — real recorded arm's-length
    # sales, the same rows the band statistics were computed from.
    sales.sort(key=lambda r: -r['y'])
    comps = sales[:6]

    def pct_of(vals, q):
        i = q * (len(vals) - 1); lo = int(i)
        return vals[lo] + (vals[min(lo + 1, len(vals) - 1)] - vals[lo]) * (i - lo)

    ppsf_all = [r[0] for r in rows]

    def band(vals):
        vals = sorted(vals)
        return {'med': round(pct_of(vals, 0.5)),
                'p25': round(pct_of(vals, 0.25)),
                'p75': round(pct_of(vals, 0.75)), 'n': len(vals)}

    # SIZE-STRATIFIED BANDS (added 2026-08-01). A ZIP-wide p25–p75 mixes every house size in the
    # ZIP, and $/sf falls sharply as size rises — in 33033's own comps, 1,365 sf sold at $286/sf
    # while 2,568 sf sold at $173/sf. Quoting one ZIP-wide spread therefore hands a homeowner a
    # range far wider than the data actually supports for a house of THEIR size. Bucketing by
    # living area lets the portal quote the band for comparable homes instead.
    # Buckets need >=12 sales to be published; the portal falls back to the ZIP-wide band when a
    # bucket is missing, so a thin ZIP degrades to exactly today's behaviour rather than breaking.
    SIZE_BUCKETS = [(0, 1100), (1100, 1500), (1500, 2000), (2000, 2800), (2800, 99999)]
    sz = {}
    for lo_sf, hi_sf in SIZE_BUCKETS:
        vals = [r[0] for r in rows if lo_sf <= r[1] < hi_sf]
        if len(vals) >= 12:
            sz['%d-%d' % (lo_sf, hi_sf)] = band(vals)

    out = band(ppsf_all)
    out.update({'n': len(rows), 'as_of': '%d-%02d' % (NOW.year, NOW.month), 'comps': comps})
    if sz: out['sz'] = sz
    return out

def main():
    arg = (sys.argv[1] if len(sys.argv) > 1 else 'miami').strip()
    if arg == 'all':
        # Every ZIP that appears on any county lead board, plus the Miami list —
        # so one nightly run gives every market bands AND comps, not just Miami.
        import glob as _g
        found = set(MIAMI_ZIPS)
        for z in MIAMI_ZIPS:
            ZIP_CO.setdefault(str(z), CO_BY_FILE['miami'])
        for lf in _g.glob(os.path.join(REPO, '*-leads.js')):
            key = os.path.basename(lf).replace('-leads.js', '')
            zs = set(re.findall(r'"z":"(\d{5})"', open(lf, encoding='utf-8').read()))
            found |= zs
            # Bound each zip to the county whose board it came from. A zip that straddles a county
            # line resolves to whichever board claimed it first — the bound is a query optimisation,
            # not a filter on which sales count, so a tie costs coverage only at the very edge.
            co = CO_BY_FILE.get(key)
            if co:
                for z in zs:
                    ZIP_CO.setdefault(z, co)
        zips = sorted(found)
        print('county-bounded %d/%d zips' % (sum(1 for z in zips if z in ZIP_CO), len(zips)), flush=True)
    elif arg == 'miami':
        zips = MIAMI_ZIPS
    else:
        zips = [z.strip() for z in arg.split(',') if re.match(r'^\d{5}$', z.strip())]
    # Load the existing bands file and MERGE — other counties' bands must survive.
    bands = {}
    if os.path.exists(OUT):
        m = re.search(r'window\.ZIP_BANDS\s*=\s*(\{.*?\});', open(OUT, encoding='utf-8').read(), re.S)
        if m: bands = json.loads(m.group(1))
    print('bands file has %d zips; baking %d more' % (len(bands), len(zips)), flush=True)
    ok, thin, fail = 0, [], []
    # Circuit breaker. Every zip runs its own 5-attempt ladder, so a throttled service
    # meant 74 zips x 5 attempts = up to 370 hammering requests that kept the throttle
    # engaged and produced nothing. Observed 2026-07-20: this ground for two hours,
    # failed all 74, AND starved the leads crawl running beside it.
    # When the service is down, the correct move is to stop, not to keep knocking.
    STREAK_ABORT = 4
    streak = 0
    for i, z in enumerate(zips):
        print('[%d/%d] zip %s' % (i + 1, len(zips), z), flush=True)
        b = band_for_zip(z)
        if b is None:
            fail.append(z); streak += 1
            print('   FAILED (throttle exhausted) — continuing', flush=True)
            if streak >= STREAK_ABORT:
                print('ABORT: %d zips failed back to back — the service is throttling, not '
                      'flaking. Stopping so we stop making it worse; %d zips baked this run. '
                      'Re-run when the cooldown has cleared.' % (streak, ok), flush=True)
                break
        elif 'thin' in b: thin.append('%s(n=%d)' % (z, b['thin'])); streak = 0
        else: bands[z] = b; ok += 1; streak = 0
        # save partials every 10 zips so a crash never loses the run
        if i % 10 == 9: _write(bands)
        time.sleep(4)
    _write(bands)
    print('DONE: %d baked, %d thin-skipped [%s], %d failed [%s], file now %d zips'
          % (ok, len(thin), ','.join(thin), len(fail), ','.join(fail), len(bands)), flush=True)
    # exit 1 if most failed so the wrapper doesn't commit a useless run
    if ok == 0: sys.exit(1)

def _write(bands):
    js = ('// ZIP-level qualified-sale $/sf bands (FDOR statewide roll, QUAL_CD1 arm\'s-length only).\n'
          '// p25/med/p75 per sqft; n = trimmed sale count. Generated %s by tools/bake_zip_bands.py.\n'
          'window.ZIP_BANDS=%s;\n' % (NOW, json.dumps(bands, sort_keys=True, separators=(',', ':'))))
    open(OUT, 'w', encoding='utf-8').write(js)

if __name__ == '__main__':
    # One FDOR job at a time — see tools/fdor_lock.py. Waits up to 40 min for the
    # leads crawl rather than giving up, since this runs unattended overnight.
    with fdor_lock('bands:miami', wait_seconds=2400):
        main()

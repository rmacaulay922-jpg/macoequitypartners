# Bake/refresh ZIP-level qualified-sale $/sf bands into zip-value-bands.js (MERGE, not overwrite).
# Usage: python bake_zip_bands.py miami   (or: python bake_zip_bands.py 33125,33126,...)
# Method proven by the July-18 FDOR harness: QUAL_CD1 in ('01','02') separates arm's-length sales
# from $100 quitclaims; stats are computed locally (server-side statistics 400 on this host);
# throttles are ridden out with full 8.5-minute cooldowns, and partials are saved to disk.
import sys, os, re, json, time, urllib.request, urllib.parse, datetime

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

def band_for_zip(z):
    where = ("DOR_UC='001' AND QUAL_CD1 IN ('01','02') AND SALE_YR1>=2024 "
             "AND TOT_LVG_AR>500 AND SALE_PRC1>50000 AND PHY_ZIPCD=%s" % z)
    rows, last = [], 0
    while True:
        d = query(where, last, 'OBJECTID,SALE_PRC1,TOT_LVG_AR')
        if d is None: return None            # terminal — caller records the failure honestly
        f = d.get('features', [])
        if not f: break
        for x in f:
            a = x['attributes']
            sp, sf = num(a.get('SALE_PRC1')), num(a.get('TOT_LVG_AR'))
            if sp > 0 and sf > 0: rows.append(sp / sf)
        last = max(int(num(x['attributes'].get('OBJECTID'))) for x in f)
        if len(f) < 2000: break
        time.sleep(3)
    rows = [p for p in rows if 60 <= p <= 1200]
    rows.sort()
    k = int(len(rows) * 0.05)
    rows = rows[k:len(rows) - k] if len(rows) > 2 * k else rows
    if len(rows) < 8: return {'thin': len(rows)}
    def pct(q):
        i = q * (len(rows) - 1); lo = int(i)
        return rows[lo] + (rows[min(lo + 1, len(rows) - 1)] - rows[lo]) * (i - lo)
    return {'med': round(pct(0.5)), 'p25': round(pct(0.25)), 'p75': round(pct(0.75)),
            'n': len(rows), 'as_of': '%d-%02d' % (NOW.year, NOW.month)}

def main():
    arg = (sys.argv[1] if len(sys.argv) > 1 else 'miami').strip()
    zips = MIAMI_ZIPS if arg == 'miami' else [z.strip() for z in arg.split(',') if re.match(r'^\d{5}$', z.strip())]
    # Load the existing bands file and MERGE — other counties' bands must survive.
    bands = {}
    if os.path.exists(OUT):
        m = re.search(r'window\.ZIP_BANDS\s*=\s*(\{.*?\});', open(OUT, encoding='utf-8').read(), re.S)
        if m: bands = json.loads(m.group(1))
    print('bands file has %d zips; baking %d more' % (len(bands), len(zips)), flush=True)
    ok, thin, fail = 0, [], []
    for i, z in enumerate(zips):
        print('[%d/%d] zip %s' % (i + 1, len(zips), z), flush=True)
        b = band_for_zip(z)
        if b is None: fail.append(z); print('   FAILED (throttle exhausted) — continuing', flush=True)
        elif 'thin' in b: thin.append('%s(n=%d)' % (z, b['thin']))
        else: bands[z] = b; ok += 1
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
    main()

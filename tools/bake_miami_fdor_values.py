# -*- coding: utf-8 -*-
"""
Bake Miami-Dade just/land values from the FDOR statewide roll into a LOCAL cache.

WHY
---
scrape_miami_pa.py builds the Miami-Dade board from PaGISView, which is the right source for
county-wide coverage and owner/mailing enrichment — but it publishes NO property value. Verified
2026-08-01 against the live layer: the only value-ish fields on PaGISView are ASSESSMENT_YEAR_CUR
and ASSESSED_VAL_CUR (there is no TOTAL_VAL_CUR / LAND_VAL_CUR / BLDG_VAL_CUR), ASSESSED_VAL_CUR
came back null for 40/40 sampled parcels, and it cannot even be filtered on.

So the scraper substitutes band_mid(zip, sqft) — a modelled ZIP estimate — and hardcodes bld/lnd
to 0. Measured on folio 3040020090330 (7310 NW 4 ST): modelled $699,300 against FDOR's real
$476,776, a +47% overstatement. FDOR joins on the bare folio with no reformatting
(PARCEL_ID='3040020090330' returns exactly one row) and carries JV, LND_VAL and AV_NSD.

WHY A SEPARATE JOB, AND WHY A CACHE
-----------------------------------
The value cannot simply be patched onto the finished leads file. In scrape_miami_pa.py the value
GATES which parcels become leads at all:

    est = band_mid(z, sqft)
    if not (60000 <= est <= 700000): continue      # flip band

and it is the sort tiebreak. Enriching after the bake would leave the board SELECTED on the
modelled number and merely DISPLAYED with the real one — the harder half of the bug would survive.
So the real value must be available BEFORE selection.

But the nightly Miami bake must not depend on a live FDOR crawl: FDOR is aggressively rate-limited
and is already the bottleneck for the county leads rotation and the ZIP band bake. Hence this
split — a slow, rare, lock-serialised job writes a cache; the nightly scraper just reads it,
exactly as it already reads zip-value-bands.js.

Run this only when the roll year changes (FDOR publishes annually), or on demand:

    python tools/bake_miami_fdor_values.py            # full run
    python tools/bake_miami_fdor_values.py --resume   # continue into an existing cache

Output: tools/fdor_miami_values.json
    {"_meta": {...}, "<folio13>": [jv, lnd, av, tv], ...}
"""

import json
import os
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fdor_lock import fdor_lock  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'fdor_miami_values.json')
SERVICE = ('https://services9.arcgis.com/Gh9awoU677aKree0/arcgis/rest/services/'
           'Florida_Statewide_Cadastral/FeatureServer/0/query')
UA = {'User-Agent': 'Mozilla/5.0'}

CO_NO = 23                 # Miami-Dade. Alphabetical+10; confirmed live against the zip mix.
WHERE = "CO_NO=%d AND DOR_UC='001'" % CO_NO
# Deliberately NOT scrape_fl_county.py's clause: its JV band would pre-decide the very number we
# are here to measure, and its JV_HMSTD filter would drop every homesteaded parcel — and the Miami
# board has no homestead filter, so those parcels are on it.

PAGE = 1000                # small pages: FDOR sheds heavy ones
PACE = 2.0
SEGMENTS = 14              # OBJECTID-range sweep — bounded scans survive where deep cursors die
STREAK_ABORT = 3           # consecutive dead segments before we stop making it worse
DELAYS = [20, 60, 120, 510, 510]


def num(v):
    try:
        return float(str(v).replace(',', ''))
    except Exception:
        return 0.0


def nf(v):
    """Folio normalisation — digits only, zero-padded to 13. MUST match scrape_miami_pa.py."""
    d = ''.join(ch for ch in str(v or '') if ch.isdigit())
    return d.zfill(13) if d else ''


def q(where, fields='PARCEL_ID,JV,LND_VAL,AV_NSD,TV_NSD,ASMNT_YR,OBJECTID', page=PAGE, order=None):
    body = {'where': where, 'outFields': fields, 'returnGeometry': 'false',
            'f': 'json', 'resultRecordCount': page}
    if order:
        body['orderByFields'] = order
    for t in range(6):
        try:
            req = urllib.request.Request(SERVICE, data=urllib.parse.urlencode(body).encode(), headers=UA)
            d = json.load(urllib.request.urlopen(req, timeout=120))
            if 'error' in d:
                raise RuntimeError(d['error'].get('message', 'error'))
            return d
        except Exception as e:
            print('   retry %d (%s)' % (t + 1, str(e)[:70]), flush=True)
            if t < len(DELAYS):
                time.sleep(DELAYS[t])
    return None


def load_cache():
    if os.path.exists(OUT):
        try:
            return json.load(open(OUT, encoding='utf-8'))
        except Exception:
            pass
    return {}


def save(vals, meta):
    out = {'_meta': meta}
    out.update(vals)
    tmp = OUT + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as fh:
        json.dump(out, fh, separators=(',', ':'))
    os.replace(tmp, OUT)          # atomic: a crash mid-write can never leave a truncated cache


def main():
    resume = '--resume' in sys.argv
    vals = {k: v for k, v in load_cache().items() if k != '_meta'} if resume else {}
    print('%s with %d cached parcels' % ('resuming' if resume else 'starting fresh', len(vals)), flush=True)

    probe = q(WHERE, 'OBJECTID', page=1, order='OBJECTID')
    if probe is None or not probe.get('features'):
        raise SystemExit('span probe failed — FDOR unreachable or throttled. Nothing written.')
    lo = int(num(probe['features'][0]['attributes'].get('OBJECTID')))
    hi_d = q(WHERE, 'OBJECTID', page=1, order='OBJECTID DESC')
    hi = int(num(hi_d['features'][0]['attributes'].get('OBJECTID'))) if hi_d and hi_d.get('features') else lo + 5000000
    print('OBJECTID span %d..%d over %d segments' % (lo, hi, SEGMENTS), flush=True)

    step = max(1, (hi - lo) // SEGMENTS + 1)
    years, dead, trunc, streak = {}, 0, 0, 0
    for s in range(SEGMENTS):
        a1, b1 = lo + s * step, lo + (s + 1) * step
        got, last, ok = 0, 0, True
        while True:
            w = WHERE + ' AND OBJECTID>=%d AND OBJECTID<%d' % (a1, b1)
            if last:
                w += ' AND OBJECTID>%d' % last
            d = q(w, order='OBJECTID')
            if d is None:
                ok = False
                break
            f = d.get('features', [])
            if not f:
                break
            for x in f:
                at = x['attributes']
                fol = nf(at.get('PARCEL_ID'))
                jv = num(at.get('JV'))
                if not fol or jv <= 0:
                    continue
                vals[fol] = [int(round(jv)), int(round(num(at.get('LND_VAL')))),
                             int(round(num(at.get('AV_NSD')))), int(round(num(at.get('TV_NSD'))))]
                y = str(int(num(at.get('ASMNT_YR')) or 0) or '')
                if y:
                    years[y] = years.get(y, 0) + 1
            got += len(f)
            last = max(int(num(x['attributes'].get('OBJECTID')) or 0) for x in f)
            if len(f) < PAGE:
                break
            time.sleep(PACE)
        if not ok:
            if got:
                trunc += 1
                streak = 0
                print('  seg %d/%d truncated after %d rows' % (s + 1, SEGMENTS, got), flush=True)
            else:
                dead += 1
                streak += 1
                print('  seg %d/%d DEAD' % (s + 1, SEGMENTS), flush=True)
        else:
            streak = 0
            print('  seg %d/%d ok (%d rows) · cache %d' % (s + 1, SEGMENTS, got, len(vals)), flush=True)
        save(vals, {'partial': True, 'co_no': CO_NO})     # partial save: a crash never loses the run
        if streak >= STREAK_ABORT:
            print('ABORT: %d dead segments back to back — FDOR is throttling, stopping.' % streak, flush=True)
            break
        time.sleep(PACE)

    holes = dead + trunc
    roll = max(years, key=years.get) if years else ''
    print('\nparcels cached: %d · segments: %d dead, %d truncated · roll %s' % (len(vals), dead, trunc, roll), flush=True)
    if holes > SEGMENTS * 0.5:
        print('REFUSING to mark complete: %d/%d segments incomplete — coverage would be skewed.' % (holes, SEGMENTS))
        save(vals, {'partial': True, 'co_no': CO_NO, 'roll': roll, 'dead': dead, 'trunc': trunc})
        return 1
    save(vals, {'partial': False, 'co_no': CO_NO, 'roll': roll, 'count': len(vals),
                'dead': dead, 'trunc': trunc, 'built': time.strftime('%Y-%m-%d')})
    print('wrote %s' % OUT)
    return 0


if __name__ == '__main__':
    with fdor_lock('values:miami-fdor'):
        sys.exit(main())

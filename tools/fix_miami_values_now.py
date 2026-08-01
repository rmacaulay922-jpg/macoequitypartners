# -*- coding: utf-8 -*-
"""
Put the REAL county value on the 3,000 Miami-Dade leads already on the board — today.

WHY THIS EXISTS ALONGSIDE bake_miami_fdor_values.py
---------------------------------------------------
The correct long-term fix is the other script: it caches FDOR values so scrape_miami_pa.py can
use them BEFORE it decides which parcels become leads, because the value gates selection and is
the sort tiebreak. That remains the real fix.

But letters are going out TODAY against the leads that are already on the board, and every one of
those carries a MODELLED value measured +47% high (folio 3040020090330: modelled $699,300 vs
FDOR's real $476,776). Telling a homeowner their house is worth 47% more than the county says is
the single worst thing this product can do, so the displayed numbers get corrected now.

BE CLEAR ABOUT WHAT THIS DOES AND DOES NOT FIX:
  FIXES     — the value shown on every existing lead, in the dossier, in letters, in CSV exports.
  DOES NOT  — the SELECTION of which 3,000 parcels are on the board, or their ordering. Those were
              decided using the modelled value. A parcel wrongly included or excluded stays that
              way until a full re-bake runs with the value cache in place.
So: safe to mail from after this runs. Not a substitute for the re-bake.

Queries are batched PARCEL_ID IN (...) — bounded and indexed, the shape that reliably survives
FDOR, unlike the statewide scans that get load-shed.

Usage:  python tools/fix_miami_values_now.py [--dry-run]
"""

import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fdor_lock import fdor_lock  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
LEADS = os.path.join(REPO, 'miami-leads.js')
CACHE = os.path.join(HERE, 'fdor_miami_values.json')
SERVICE = ('https://services9.arcgis.com/Gh9awoU677aKree0/arcgis/rest/services/'
           'Florida_Statewide_Cadastral/FeatureServer/0/query')
UA = {'User-Agent': 'Mozilla/5.0'}
CO_NO = 23
BATCH = 60
PACE = 1.5
MIN_MATCH = 0.80
DELAYS = [20, 60, 120, 510, 510]
STREAK_ABORT = 3


def num(v):
    try:
        return float(str(v).replace(',', ''))
    except Exception:
        return 0.0


def q(where):
    body = {'where': where, 'outFields': 'PARCEL_ID,JV,LND_VAL,AV_NSD,TV_NSD,ASMNT_YR',
            'returnGeometry': 'false', 'f': 'json', 'resultRecordCount': 2000}
    for t in range(6):
        try:
            req = urllib.request.Request(SERVICE, data=urllib.parse.urlencode(body).encode(), headers=UA)
            d = json.load(urllib.request.urlopen(req, timeout=120))
            if 'error' in d:
                raise RuntimeError(d['error'].get('message', 'error'))
            return d
        except Exception as e:
            print('   retry %d (%s)' % (t + 1, str(e)[:65]), flush=True)
            if t < len(DELAYS):
                time.sleep(DELAYS[t])
    return None


def main():
    dry = '--dry-run' in sys.argv
    src = open(LEADS, encoding='utf-8').read()
    m = re.search(r'window\.MIAMI_LEADS\s*=\s*(\[.*?\]);\s*window\.MIAMI_META\s*=\s*(\{.*?\});', src, re.S)
    if not m:
        raise SystemExit('could not parse miami-leads.js — refusing to touch it.')
    leads = json.loads(m.group(1))
    meta = json.loads(m.group(2))
    print('board: %d leads' % len(leads), flush=True)

    by_pid = {}
    for l in leads:
        pid = re.sub(r'[^0-9]', '', str(l.get('pid') or ''))
        if pid:
            by_pid.setdefault(pid, []).append(l)
    pids = sorted(by_pid)

    found, years, streak = {}, {}, 0
    total = (len(pids) + BATCH - 1) // BATCH
    for i in range(0, len(pids), BATCH):
        chunk = pids[i:i + BATCH]
        n = i // BATCH + 1
        d = q("CO_NO=%d AND PARCEL_ID IN (%s)" % (CO_NO, ','.join("'%s'" % p for p in chunk)))
        if d is None:
            streak += 1
            print('   batch %d/%d FAILED (%d consecutive)' % (n, total, streak), flush=True)
            if streak >= STREAK_ABORT:
                print('ABORT: %d batches failed back to back — FDOR is throttling. '
                      'Nothing written; re-run later.' % streak, flush=True)
                return 1
            continue
        streak = 0
        for f in d.get('features', []):
            a = f['attributes']
            pid = re.sub(r'[^0-9]', '', str(a.get('PARCEL_ID') or ''))
            jv = num(a.get('JV'))
            if not pid or jv <= 0:
                continue
            found[pid] = a
            y = str(int(num(a.get('ASMNT_YR')) or 0) or '')
            if y:
                years[y] = years.get(y, 0) + 1
        if n % 5 == 0 or n == total:
            print('   batch %d/%d · %d/%d parcels resolved' % (n, total, len(found), len(pids)), flush=True)
        time.sleep(PACE)

    rate = len(found) / max(1, len(pids))
    print('\nFDOR matched %d/%d (%.0f%%)' % (len(found), len(pids), 100 * rate), flush=True)
    if rate < MIN_MATCH:
        print('ABORT: below %.0f%% — the join is wrong. Nothing written.' % (100 * MIN_MATCH))
        return 1

    deltas, real = [], 0
    for pid, rows in by_pid.items():
        a = found.get(pid)
        for l in rows:
            if not a:
                l['vm'] = 1                     # still modelled — portal labels it per-lead
                continue
            jv, lv = num(a.get('JV')), num(a.get('LND_VAL'))
            old = num(l.get('mkt'))
            if old > 0:
                deltas.append((jv - old) / old)
            l['mkt'] = int(round(jv))
            l['lnd'] = int(round(lv))
            l['bld'] = int(round(max(0, jv - lv)))
            l['asr'] = int(round(num(a.get('AV_NSD'))))
            l['tax'] = int(round(num(a.get('TV_NSD'))))
            l.pop('vm', None)                   # real value -> no modelled flag
            real += 1

    roll = max(years, key=years.get) if years else ''
    meta['valSrc'] = 'fdor' if real == len(leads) else ('fdor+model' if real else 'model')
    meta['valReal'], meta['valModel'] = real, len(leads) - real
    if roll:
        meta['val_roll'] = roll + ' roll'
    meta['roll'] = 'Miami-Dade PA (PaGISView) + FDOR %s just value' % roll if real else meta.get('roll')

    if deltas:
        deltas.sort()
        med = deltas[len(deltas) // 2]
        over10 = sum(1 for d in deltas if d < -0.10)
        over25 = sum(1 for d in deltas if d < -0.25)
        print('real values on %d leads · %d still modelled' % (real, len(leads) - real))
        print('median change vs the modelled number: %+.1f%%' % (100 * med))
        print('overstated >10%%: %d of %d (%.0f%%)' % (over10, len(deltas), 100 * over10 / len(deltas)))
        print('overstated >25%%: %d of %d (%.0f%%)' % (over25, len(deltas), 100 * over25 / len(deltas)))
        print('roll year: %s' % roll)

    if dry:
        print('\n--dry-run: nothing written.')
        return 0

    assert len(leads) == len(json.loads(m.group(1))), 'lead count changed — refusing to write'
    out = (src[:m.start(1)] + json.dumps(leads, separators=(',', ':')) +
           src[m.end(1):m.start(2)] + json.dumps(meta, separators=(',', ':')) + src[m.end(2):])
    open(LEADS, 'w', encoding='utf-8').write(out)
    print('\nwrote miami-leads.js (%d KB)' % (len(out) // 1024))

    # Seed the value cache too, so the next full re-bake starts with these and can fix SELECTION.
    cache = {}
    if os.path.exists(CACHE):
        try:
            cache = json.load(open(CACHE, encoding='utf-8'))
        except Exception:
            cache = {}
    cache.pop('_meta', None)
    for pid, a in found.items():
        jv, lv = num(a.get('JV')), num(a.get('LND_VAL'))
        cache[pid.zfill(13)] = [int(round(jv)), int(round(lv)),
                                int(round(num(a.get('AV_NSD')))), int(round(num(a.get('TV_NSD'))))]
    outc = {'_meta': {'partial': True, 'co_no': CO_NO, 'roll': roll, 'count': len(cache),
                      'note': 'board parcels only — not a full county crawl',
                      'built': time.strftime('%Y-%m-%d')}}
    outc.update(cache)
    json.dump(outc, open(CACHE, 'w', encoding='utf-8'), separators=(',', ':'))
    print('seeded %s with %d parcels' % (os.path.basename(CACHE), len(cache)))
    return 0


if __name__ == '__main__':
    with fdor_lock('values:miami-board'):
        sys.exit(main())

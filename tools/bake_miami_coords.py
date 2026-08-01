# -*- coding: utf-8 -*-
"""
Give the Miami-Dade board coordinates.

WHY
---
All 3,000 Miami-Dade leads bake with lat/lng null, and two features die because of it:
  * the leads map plots nothing on the deepest market (Broward, Lee and Collier have coords)
  * FEMA flood zone can never be looked up — and in South Florida an AE-zone parcel carries
    thousands a year of mandatory flood premium and a smaller resale buyer pool

The scraper leaves them null on purpose: PaGISView's X_COORD/Y_COORD are state-plane, not lat/lng.
But the county publishes exact parcel centroids, keyless, on a DIFFERENT host from FDOR — so this
costs nothing against the rate budget that gates everything else:

    Parcelpoly_gdb/FeatureServer/0/query  ?returnCentroid=true&outSR=4326  keyed by FOLIO

Verified live 2026-08-01 on folio 3040020090330 -> (-80.31427, 25.77428). That is a true parcel
centroid, not a street geocode, so it lands on the roof rather than the kerb.

Batched FOLIO IN (...) — the bounded shape that survives. Writes lat/lng onto miami-leads.js.
Idempotent: re-running only fills what is missing unless --all is passed.

Usage:  python tools/bake_miami_coords.py [--all] [--dry-run]
"""

import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
LEADS = os.path.join(REPO, 'miami-leads.js')
SERVICE = ('https://services.arcgis.com/8Pc9XBTAsYuxx9Ny/arcgis/rest/services/'
           'Parcelpoly_gdb/FeatureServer/0/query')
UA = {'User-Agent': 'Mozilla/5.0'}
BATCH = 80
PACE = 1.0
STREAK_ABORT = 4
DELAYS = [10, 30, 60, 120]

# Miami-Dade's bounding box. A centroid outside this is a bad join, not a real parcel, and must
# not be written — a lead plotted in the Everglades or off the coast is worse than no pin.
LAT_MIN, LAT_MAX = 25.10, 26.00
LNG_MIN, LNG_MAX = -80.90, -80.05


def q(where):
    body = {'where': where, 'outFields': 'FOLIO', 'returnGeometry': 'false',
            'returnCentroid': 'true', 'outSR': '4326', 'f': 'json', 'resultRecordCount': 2000}
    for t in range(5):
        try:
            req = urllib.request.Request(SERVICE, data=urllib.parse.urlencode(body).encode(), headers=UA)
            d = json.load(urllib.request.urlopen(req, timeout=120))
            if 'error' in d:
                raise RuntimeError(d['error'].get('message', 'error'))
            return d
        except Exception as e:
            print('   retry %d (%s)' % (t + 1, str(e)[:60]), flush=True)
            if t < len(DELAYS):
                time.sleep(DELAYS[t])
    return None


def main():
    dry = '--dry-run' in sys.argv
    redo = '--all' in sys.argv
    src = open(LEADS, encoding='utf-8').read()
    m = re.search(r'window\.MIAMI_LEADS\s*=\s*(\[.*?\]);\s*window\.MIAMI_META\s*=\s*(\{.*?\});', src, re.S)
    if not m:
        raise SystemExit('could not parse miami-leads.js — refusing to touch it.')
    leads = json.loads(m.group(1))
    meta = json.loads(m.group(2))

    todo, by_pid = [], {}
    for l in leads:
        pid = re.sub(r'[^0-9]', '', str(l.get('pid') or ''))
        if not pid:
            continue
        by_pid.setdefault(pid, []).append(l)
        if redo or l.get('lat') is None:
            todo.append(pid)
    todo = sorted(set(todo))
    print('%d leads · %d need coordinates' % (len(leads), len(todo)), flush=True)
    if not todo:
        print('nothing to do.')
        return 0

    found, bad, streak = {}, 0, 0
    total = (len(todo) + BATCH - 1) // BATCH
    for i in range(0, len(todo), BATCH):
        chunk = todo[i:i + BATCH]
        n = i // BATCH + 1
        d = q("FOLIO IN (%s)" % ','.join("'%s'" % p for p in chunk))
        if d is None:
            streak += 1
            print('   batch %d/%d failed (%d consecutive)' % (n, total, streak), flush=True)
            if streak >= STREAK_ABORT:
                print('ABORT after %d consecutive failures — writing what we have.' % streak, flush=True)
                break
            continue
        streak = 0
        for f in d.get('features', []):
            pid = re.sub(r'[^0-9]', '', str((f.get('attributes') or {}).get('FOLIO') or ''))
            c = f.get('centroid') or {}
            x, y = c.get('x'), c.get('y')
            if not pid or x is None or y is None:
                continue
            if not (LAT_MIN <= y <= LAT_MAX and LNG_MIN <= x <= LNG_MAX):
                bad += 1                     # outside the county — a bad join, drop it
                continue
            found[pid] = (round(y, 6), round(x, 6))
        if n % 5 == 0 or n == total:
            print('   batch %d/%d · %d resolved' % (n, total, len(found)), flush=True)
        time.sleep(PACE)

    print('\nresolved %d of %d (%d rejected as outside Miami-Dade)' % (len(found), len(todo), bad))
    if not found:
        print('nothing resolved — file untouched.')
        return 1

    n_set = 0
    for pid, (lat, lng) in found.items():
        for l in by_pid.get(pid, []):
            l['lat'] = lat
            l['lng'] = lng
            n_set += 1
    meta['coords'] = sum(1 for l in leads if l.get('lat') is not None)
    print('lat/lng now on %d of %d leads' % (meta['coords'], len(leads)))

    if dry:
        print('--dry-run: nothing written.')
        return 0
    assert len(leads) == len(json.loads(m.group(1))), 'lead count changed — refusing to write'
    out = (src[:m.start(1)] + json.dumps(leads, separators=(',', ':')) +
           src[m.end(1):m.start(2)] + json.dumps(meta, separators=(',', ':')) + src[m.end(2):])
    open(LEADS, 'w', encoding='utf-8').write(out)
    print('wrote miami-leads.js (%d KB)' % (len(out) // 1024))
    return 0


if __name__ == '__main__':
    sys.exit(main())

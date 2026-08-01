# -*- coding: utf-8 -*-
"""
Homestead check for the five non-Miami boards, and write the answer into the lead files.

WHY
---
Miami-Dade turned out to be 38.9% homesteaded while every card claimed "non-homestead". The other
five boards make the same blanket claim and have never been checked. The Save-Our-Homes proxy is
not good enough to settle it — measured against the real field on Miami it was only 59% precise —
so this reads FDOR's JV_HMSTD, which is >0 exactly when an exemption is on the parcel.

CAREFUL WITH PARCEL IDS: Lee's are alphanumeric (054524C4005440100). The Miami script stripped to
digits, which is right for Dade folios and WRONG here — ids go to FDOR exactly as baked.

Writes hs:1 onto matched leads and records counts in each market's META. Refuses to write a market
whose match rate is too low to trust.

Usage:  python tools/check_all_homestead.py [--dry-run]
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
SERVICE = ('https://services9.arcgis.com/Gh9awoU677aKree0/arcgis/rest/services/'
           'Florida_Statewide_Cadastral/FeatureServer/0/query')
UA = {'User-Agent': 'Mozilla/5.0'}
BATCH = 60
PACE = 1.5
MIN_MATCH = 0.70
STREAK_ABORT = 3
DELAYS = [20, 60, 120, 510, 510]

MARKETS = [
    ('broward', 'BROWARD', 16),
    ('lee',     'LEE',     46),
    ('collier', 'COLLIER', 21),
    ('polk',    'POLK',    63),
    ('lake',    'LAKE',    45),
]
if '--only' in sys.argv:
    _want = set(sys.argv[sys.argv.index('--only') + 1].split(','))
    MARKETS = [m for m in MARKETS if m[0] in _want]


def num(v):
    try:
        return float(str(v).replace(',', ''))
    except Exception:
        return 0.0


def q(where):
    body = {'where': where, 'outFields': 'PARCEL_ID,JV,JV_HMSTD',
            'returnGeometry': 'false', 'f': 'json', 'resultRecordCount': 2000}
    for t in range(6):
        try:
            req = urllib.request.Request(SERVICE, data=urllib.parse.urlencode(body).encode(), headers=UA)
            d = json.load(urllib.request.urlopen(req, timeout=120))
            if 'error' in d:
                raise RuntimeError(d['error'].get('message', 'error'))
            return d
        except Exception as e:
            print('     retry %d (%s)' % (t + 1, str(e)[:60]), flush=True)
            if t < len(DELAYS):
                time.sleep(DELAYS[t])
    return None


def esc(pid):
    return str(pid).replace("'", "''")


def do_market(key, gv, co, dry):
    path = os.path.join(REPO, key + '-leads.js')
    src = open(path, encoding='utf-8').read()
    # Match the two blocks INDEPENDENTLY — Polk and Lake declare META *before* LEADS, and a single
    # combined pattern assuming LEADS-then-META silently skipped both boards on the first run.
    ml = re.search(r'window\.%s_LEADS\s*=\s*(\[.*?\]);' % gv, src, re.S)
    mm = re.search(r'window\.%s_META\s*=\s*(\{.*?\});' % gv, src, re.S)
    if not ml or not mm:
        print('  %s: could not parse — skipped' % key)
        return None
    leads = json.loads(ml.group(1))
    meta = json.loads(mm.group(1))

    by_pid = {}
    for l in leads:
        pid = str(l.get('pid') or '').strip()      # AS BAKED — Lee's ids contain letters
        if pid:
            by_pid.setdefault(pid, []).append(l)
    pids = sorted(by_pid)
    print('  %s: %d leads, %d parcels' % (key, len(leads), len(pids)), flush=True)

    hs, seen, streak = set(), set(), 0
    total = (len(pids) + BATCH - 1) // BATCH
    for i in range(0, len(pids), BATCH):
        chunk = pids[i:i + BATCH]
        d = q("CO_NO=%d AND PARCEL_ID IN (%s)" % (co, ','.join("'%s'" % esc(p) for p in chunk)))
        if d is None:
            streak += 1
            print('     batch %d/%d failed (%d consecutive)' % (i // BATCH + 1, total, streak), flush=True)
            if streak >= STREAK_ABORT:
                print('     ABORT %s — FDOR throttling.' % key, flush=True)
                break
            continue
        streak = 0
        for f in d.get('features', []):
            a = f['attributes']
            pid = str(a.get('PARCEL_ID') or '').strip()
            if not pid:
                continue
            seen.add(pid)
            if num(a.get('JV_HMSTD')) > 0:
                hs.add(pid)
        time.sleep(PACE)

    rate = len(seen) / max(1, len(pids))
    n_hs = sum(len(by_pid[p]) for p in hs)
    print('     resolved %d/%d (%.0f%%) · homesteaded %d (%.1f%%)'
          % (len(seen), len(pids), 100 * rate, n_hs, 100.0 * n_hs / max(1, len(leads))), flush=True)
    if rate < MIN_MATCH:
        print('     match rate too low — NOT writing %s' % key, flush=True)
        return {'market': key, 'written': False, 'rate': rate, 'hs': n_hs, 'leads': len(leads)}

    for p, rows in by_pid.items():
        for l in rows:
            if p in hs:
                l['hs'] = 1
            else:
                l.pop('hs', None)
    meta['homesteaded'] = n_hs
    meta['hs_checked'] = len(seen)
    meta['hs_asof'] = time.strftime('%Y-%m-%d')
    if not dry:
        # Splice each block at its own offsets, highest-first so the earlier index stays valid
        # regardless of which of the two comes first in the file.
        edits = sorted([(ml.start(1), ml.end(1), json.dumps(leads, separators=(',', ':'))),
                        (mm.start(1), mm.end(1), json.dumps(meta, separators=(',', ':')))],
                       key=lambda e: -e[0])
        out = src
        for a, b, txt in edits:
            out = out[:a] + txt + out[b:]
        open(path, 'w', encoding='utf-8').write(out)
        print('     wrote %s-leads.js' % key, flush=True)
    return {'market': key, 'written': not dry, 'rate': rate, 'hs': n_hs, 'leads': len(leads)}


def main():
    dry = '--dry-run' in sys.argv
    res = []
    for key, gv, co in MARKETS:
        r = do_market(key, gv, co, dry)
        if r:
            res.append(r)
        time.sleep(3)
    print('\n' + '=' * 58)
    for r in res:
        print('%-9s %4d leads · %4d homesteaded (%.1f%%) · match %.0f%% · %s'
              % (r['market'], r['leads'], r['hs'], 100.0 * r['hs'] / max(1, r['leads']),
                 100 * r['rate'], 'written' if r['written'] else 'NOT WRITTEN'))
    print('=' * 58)
    return 0


if __name__ == '__main__':
    with fdor_lock('check:all-homestead'):
        sys.exit(main())

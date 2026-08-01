# -*- coding: utf-8 -*-
"""
Settle whether the Miami-Dade board's "Non-homestead" claim is true.

WHY
---
Every one of the 3,000 Miami-Dade leads renders "Non-homestead" as fact, and the board's whole
premise is that these owners do not live there. But 57% of them show assessed value more than 25%
below just value, which is the Save-Our-Homes signature of a capped — i.e. homesteaded — property.
If a meaningful share really are homesteaded, a chunk of the mail is going to owner-occupants:
the wrong list, wasted postage, and a call that opens with a motivation story the county contradicts.

PaGISView cannot answer this — verified 2026-08-01, the layer has NO exemption field of any kind.
FDOR does: JV_HMSTD is the homestead portion of just value, >0 exactly when a homestead exemption
is on the parcel. Same batched PARCEL_ID IN shape that ran 50/50 clean earlier today.

READ-ONLY. Writes nothing except a report. Decide what to do with the answer afterwards.

Usage:  python tools/check_miami_homestead.py [--sample N]
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
SERVICE = ('https://services9.arcgis.com/Gh9awoU677aKree0/arcgis/rest/services/'
           'Florida_Statewide_Cadastral/FeatureServer/0/query')
UA = {'User-Agent': 'Mozilla/5.0'}
CO_NO = 23
BATCH = 60
PACE = 1.5
DELAYS = [20, 60, 120, 510, 510]
STREAK_ABORT = 3


def num(v):
    try:
        return float(str(v).replace(',', ''))
    except Exception:
        return 0.0


def q(where):
    body = {'where': where, 'outFields': 'PARCEL_ID,JV,JV_HMSTD,AV_NSD,OWN_NAME',
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
    n_arg = 0
    if '--sample' in sys.argv:
        try:
            n_arg = int(sys.argv[sys.argv.index('--sample') + 1])
        except Exception:
            n_arg = 0

    src = open(LEADS, encoding='utf-8').read()
    m = re.search(r'window\.MIAMI_LEADS\s*=\s*(\[.*?\]);', src, re.S)
    leads = json.loads(m.group(1))
    by_pid = {}
    for l in leads:
        pid = re.sub(r'[^0-9]', '', str(l.get('pid') or ''))
        if pid:
            by_pid[pid] = l
    pids = sorted(by_pid)
    if n_arg:
        pids = pids[:n_arg]
    print('checking %d of %d Miami-Dade parcels for a homestead exemption' % (len(pids), len(leads)), flush=True)

    hs, nohs, missing, streak = [], [], 0, 0
    total = (len(pids) + BATCH - 1) // BATCH
    for i in range(0, len(pids), BATCH):
        chunk = pids[i:i + BATCH]
        n = i // BATCH + 1
        d = q("CO_NO=%d AND PARCEL_ID IN (%s)" % (CO_NO, ','.join("'%s'" % p for p in chunk)))
        if d is None:
            streak += 1
            print('   batch %d/%d failed (%d consecutive)' % (n, total, streak), flush=True)
            if streak >= STREAK_ABORT:
                print('ABORT: FDOR is throttling. Partial result below — treat as indicative only.', flush=True)
                break
            continue
        streak = 0
        seen = set()
        for f in d.get('features', []):
            a = f['attributes']
            pid = re.sub(r'[^0-9]', '', str(a.get('PARCEL_ID') or ''))
            if not pid or pid in seen:
                continue
            seen.add(pid)
            lead = by_pid.get(pid)
            rec = {'pid': pid, 'addr': (lead or {}).get('a', ''), 'owner': a.get('OWN_NAME', ''),
                   'jv': num(a.get('JV')), 'hmstd': num(a.get('JV_HMSTD')),
                   'av': num(a.get('AV_NSD'))}
            (hs if rec['hmstd'] > 0 else nohs).append(rec)
        missing += len(chunk) - len(seen)
        if n % 10 == 0 or n == total:
            print('   batch %d/%d · homesteaded so far: %d' % (n, total, len(hs)), flush=True)
        time.sleep(PACE)

    checked = len(hs) + len(nohs)
    if not checked:
        print('nothing resolved — FDOR unreachable. No conclusion.')
        return 1

    pct = 100.0 * len(hs) / checked
    print('\n' + '=' * 62)
    print('parcels resolved     : %d  (no FDOR row: %d)' % (checked, missing))
    print('HOMESTEADED          : %d  (%.1f%%)  <- board calls every one of these "Non-homestead"' % (len(hs), pct))
    print('genuinely non-hmstd  : %d  (%.1f%%)' % (len(nohs), 100 - pct))
    print('=' * 62)

    # Is the Save-Our-Homes proxy I used earlier actually a good predictor? Worth knowing, because
    # if it is, the other five county boards can be screened offline without touching FDOR again.
    def cap(r):
        return (1 - r['av'] / r['jv']) if r['jv'] > 0 else 0
    if hs and nohs:
        hs_cap = sorted(cap(r) for r in hs)
        no_cap = sorted(cap(r) for r in nohs)
        print('\nassessed-below-just gap (the Save-Our-Homes proxy):')
        print('  homesteaded    median %.0f%%' % (100 * hs_cap[len(hs_cap) // 2]))
        print('  non-homestead  median %.0f%%' % (100 * no_cap[len(no_cap) // 2]))
        over25_hs = sum(1 for c in hs_cap if c > .25)
        over25_no = sum(1 for c in no_cap if c > .25)
        print('  >25%% gap: %d/%d homesteaded vs %d/%d non-homesteaded' % (over25_hs, len(hs_cap), over25_no, len(no_cap)))
        if over25_hs + over25_no:
            print('  -> a >25%% gap is homesteaded %.0f%% of the time' % (100.0 * over25_hs / (over25_hs + over25_no)))

    if hs:
        print('\nfirst 10 homesteaded leads the board is mailing as absentee:')
        for r in hs[:10]:
            print('   %-24s %-28s JV %s / hmstd %s' % (r['addr'][:24], (r['owner'] or '')[:28],
                                                       format(int(r['jv']), ','), format(int(r['hmstd']), ',')))
    out = os.path.join(HERE, 'miami_homestead_report.json')
    json.dump({'checked': checked, 'homesteaded': len(hs), 'pct': round(pct, 2),
               'missing': missing, 'pids_homesteaded': [r['pid'] for r in hs]},
              open(out, 'w', encoding='utf-8'), separators=(',', ':'))
    print('\nwrote %s' % os.path.basename(out))
    return 0


if __name__ == '__main__':
    with fdor_lock('check:miami-homestead'):
        sys.exit(main())

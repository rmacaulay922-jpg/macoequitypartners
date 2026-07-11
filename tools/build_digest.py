#!/usr/bin/env python3
"""Maco Deal Analyzer — daily digest.

Diffs the live Miami-Dade county feeds against yesterday's snapshot and emails a
"new since yesterday" digest. Runs from the scheduled task `Maco Daily Digest`
(07:40, after the 07:00 market refresh) — or by hand:

    python tools/build_digest.py            # normal run (diff + send)
    python tools/build_digest.py --dry-run  # build + print, send nothing
    python tools/build_digest.py --no-send  # build + update state, send nothing

STATE LIVES IN THIS FOLDER (tools/digest_state.json, gitignored), NOT in
%LOCALAPPDATA% — Claude-session shells see a container-virtualized LOCALAPPDATA,
so a repo-relative path is the only location both the scheduled task and an
interactive session read identically. See refresh_markets.ps1 header.

Delivery: POSTs to the site's FormSubmit endpoint (lands in Ryan's inbox; he
forwards to subscribers while the list is small). If tools/digest_smtp.json
exists (gitignored) it ALSO sends directly:
    { "host": "smtp.gmail.com", "port": 587, "user": "you@gmail.com",
      "app_password": "xxxx xxxx xxxx xxxx", "from": "you@gmail.com",
      "recipients": ["sub1@example.com", "..."] }

These are the SAME queries portal.html and index.html run (CCVIOL cases/liens,
Open_Building_Violations unsafe+expired, FARM_BBOX). They are Miami-Dade County
endpoints — NOT the rate-limited FDOR service. Never point this at FDOR.
"""
import json, sys, urllib.request, urllib.parse, datetime, os, html

HERE = os.path.dirname(os.path.abspath(__file__))
STATE_PATH = os.path.join(HERE, 'digest_state.json')
LOG_PATH = os.path.join(HERE, 'digest.log')
SMTP_CFG = os.path.join(HERE, 'digest_smtp.json')

FORMSUBMIT = 'https://formsubmit.co/ajax/rmac@macoequitypartners.com'
PORTAL_URL = 'https://macoequitypartners.com/portal.html'

BBOX = json.dumps({"xmin": -80.55, "ymin": 25.43, "xmax": -80.19, "ymax": 25.92,
                   "spatialReference": {"wkid": 4326}})
GEOM = ('&geometry=' + urllib.parse.quote(BBOX) +
        '&geometryType=esriGeometryEnvelope&inSR=4326&spatialRel=esriSpatialRelIntersects')

VIOL = 'https://services.arcgis.com/8Pc9XBTAsYuxx9Ny/arcgis/rest/services/CCVIOL_gdb/FeatureServer/0/query'
BVIOL = 'https://services.arcgis.com/8Pc9XBTAsYuxx9Ny/arcgis/rest/services/Open_Building_Violations/FeatureServer/0/query'

FEEDS = [
    # key, endpoint, where, label, detail fields (address first)
    ('cases', VIOL, "CASE_STATUS IN ('1','9')", 'new open code cases',
     ['ADDRESS', 'PROBLEM_DESC', 'CASE_NUM']),
    ('liens', VIOL, "LN_RECDATE IS NOT NULL AND LN_RECDATE<>''", 'newly recorded code-enforcement liens',
     ['ADDRESS', 'LN_RECDATE', 'CASE_NUM']),
    ('bldg', BVIOL, "CASE_TYPE IN ('Unsafe Structure','Expired Permit')", 'new unsafe-structure / expired-permit cases',
     ['ADDRESS', 'CASE_TYPE', 'CASE_NUMBER']),
]

MAX_DETAIL = 120   # detail-fetch at most this many new records per feed
SHOW = 8           # show at most this many addresses per section in the email


def log(msg):
    line = '%s  %s' % (datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), msg)
    print(line)
    try:
        with open(LOG_PATH, 'a', encoding='ascii', errors='replace') as f:
            f.write(line + '\n')
    except OSError:
        pass


def fetch_json(url, timeout=60):
    req = urllib.request.Request(url, headers={'User-Agent': 'MacoDigest/1.0'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8', 'replace'))


def feed_ids(endpoint, where):
    url = (endpoint + '?where=' + urllib.parse.quote(where) + GEOM +
           '&returnIdsOnly=true&f=json')
    j = fetch_json(url)
    ids = j.get('objectIds') or []
    if j.get('error'):
        raise RuntimeError('feed error: %s' % j['error'])
    return set(ids)


def feed_details(endpoint, ids, fields):
    out = []
    ids = sorted(ids)[:MAX_DETAIL]
    for i in range(0, len(ids), 50):
        chunk = ids[i:i + 50]
        url = (endpoint + '?objectIds=' + ','.join(map(str, chunk)) +
               '&outFields=' + ','.join(fields) + '&returnGeometry=false&f=json')
        try:
            j = fetch_json(url)
            for f in j.get('features', []):
                out.append(f.get('attributes', {}))
        except Exception as e:  # detail fetch is best-effort; counts still stand
            log('detail fetch failed (%s): %s' % (endpoint[-40:], e))
            break
    return out


def load_state():
    try:
        with open(STATE_PATH, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def save_state(state):
    with open(STATE_PATH, 'w', encoding='utf-8') as f:
        json.dump(state, f)


def refresh_line():
    """Best-effort line about last night's lead-market refresh (real file when run
    by the scheduled task; container copy when run from a Claude shell — cosmetic)."""
    p = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Maco', 'refresh_state.txt')
    try:
        rows = [ln.strip().split('|') for ln in open(p, encoding='ascii', errors='replace') if '|' in ln]
        today = datetime.date.today().isoformat()
        done = [r[0] for r in rows if len(r) >= 2 and r[1] == today]
        if done:
            return 'Lead market refreshed this morning: ' + ', '.join(done) + '.'
        return ''
    except OSError:
        return ''


def build(now, state, counts, news):
    d = now.strftime('%A, %B %-d, %Y') if os.name != 'nt' else now.strftime('%A, %B %d, %Y')
    total_new = sum(len(v) for v in news.values())
    subject = 'Deal Analyzer digest — %s new county signals (%s)' % (
        format(total_new, ','), now.strftime('%b %d'))

    lines_html, lines_txt = [], []
    for key, _ep, _wh, label, fields in FEEDS:
        n = len(news.get(key, []))
        lines_txt.append('%s %s (total now %s)' % (format(n, ','), label, format(counts[key], ',')))
        sec = '<p style="margin:14px 0 4px"><b>%s %s</b> <span style="color:#888">(total on the board: %s)</span></p>' % (
            format(n, ','), label, format(counts[key], ','))
        items = news.get(key, [])[:SHOW]
        if items:
            lis = []
            for a in items:
                addr = html.escape(str(a.get(fields[0]) or 'address withheld'))
                extra = html.escape(str(a.get(fields[1]) or ''))[:60]
                lis.append('<li>%s <span style="color:#888">%s</span></li>' % (addr, extra))
            more = len(news[key]) - len(items)
            if more > 0:
                lis.append('<li style="color:#888">… and %s more — see the portal</li>' % format(more, ','))
            sec += '<ul style="margin:4px 0 0 18px;padding:0">%s</ul>' % ''.join(lis)
        lines_html.append(sec)

    rl = refresh_line()
    html_body = (
        '<div style="font-family:Georgia,serif;max-width:640px">'
        '<p style="font-size:11px;letter-spacing:.15em;color:#8C6C36">MACO DEAL ANALYZER · DAILY DIGEST</p>'
        '<h2 style="margin:0 0 4px">New on the board — %s</h2>'
        '<p style="color:#555;margin:4px 0 14px">Everything below appeared in the Miami-Dade county feeds since yesterday\'s run.</p>'
        '%s'
        '%s'
        '<p style="margin-top:18px"><a href="%s" style="color:#1B704A;font-weight:bold">Open the Deal Analyzer →</a> '
        '<span style="color:#888">— every item above is already scored on the board.</span></p>'
        '<p style="color:#aaa;font-size:11px;margin-top:16px">Sources: Miami-Dade County code-compliance and building feeds, farm area. '
        'Estimates from public records — not investment advice. Reply to stop receiving this.</p>'
        '</div>'
    ) % (html.escape(d), ''.join(lines_html), ('<p style="color:#555">%s</p>' % html.escape(rl)) if rl else '', PORTAL_URL)

    txt = 'New on the board — %s\n%s\n%s\nPortal: %s' % (d, '\n'.join(lines_txt), rl, PORTAL_URL)
    return subject, html_body, txt


def send_formsubmit(subject, txt):
    payload = json.dumps({'_subject': subject, '_template': 'table',
                          'digest': txt, 'note': 'Forward to subscribers, or add tools/digest_smtp.json for direct send.'}).encode()
    req = urllib.request.Request(FORMSUBMIT, data=payload,
                                 headers={'Content-Type': 'application/json',
                                          'Accept': 'application/json',
                                          'User-Agent': 'MacoDigest/1.0'})
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.status


def send_smtp(subject, html_body, txt):
    try:
        with open(SMTP_CFG, encoding='utf-8') as f:
            cfg = json.load(f)
    except (OSError, ValueError):
        return 0
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    sent = 0
    with smtplib.SMTP(cfg['host'], cfg.get('port', 587), timeout=60) as s:
        s.starttls()
        s.login(cfg['user'], cfg['app_password'])
        for rcpt in cfg.get('recipients', []):
            m = MIMEMultipart('alternative')
            m['Subject'] = subject
            m['From'] = cfg.get('from', cfg['user'])
            m['To'] = rcpt
            m.attach(MIMEText(txt, 'plain'))
            m.attach(MIMEText(html_body, 'html'))
            s.sendmail(m['From'], rcpt, m.as_string())
            sent += 1
    return sent


def main():
    dry = '--dry-run' in sys.argv
    no_send = '--no-send' in sys.argv or dry
    now = datetime.datetime.now()
    log('--- digest run start (dry=%s) ---' % dry)

    ids_now, counts = {}, {}
    for key, ep, where, _label, _fields in FEEDS:
        ids_now[key] = feed_ids(ep, where)
        counts[key] = len(ids_now[key])
        log('%s: %d ids' % (key, counts[key]))

    state = load_state()
    if state is None:
        log('no previous state — baseline established, nothing to diff yet.')
        if not dry:
            save_state({'date': now.isoformat(), 'ids': {k: sorted(v) for k, v in ids_now.items()}})
        log('--- digest run end (baseline) ---')
        return 0

    prev = {k: set(state.get('ids', {}).get(k, [])) for k in ids_now}
    news = {}
    for key, ep, _wh, _label, fields in FEEDS:
        fresh = ids_now[key] - prev.get(key, set())
        news[key] = feed_details(ep, fresh, fields) if fresh else []
        log('%s: %d new since %s' % (key, len(fresh), state.get('date', '?')[:10]))

    subject, html_body, txt = build(now, state, counts, news)
    total_new = sum(len(ids_now[k] - prev.get(k, set())) for k in ids_now)

    if dry:
        print('\nSUBJECT:', subject)
        print(txt)
    elif total_new == 0:
        log('nothing new — skipping send (state still updated).')
    elif not no_send:
        try:
            st = send_formsubmit(subject, txt)
            log('formsubmit delivery: HTTP %s' % st)
        except Exception as e:
            log('formsubmit delivery FAILED: %s' % e)
        try:
            n = send_smtp(subject, html_body, txt)
            if n:
                log('smtp delivery: %d recipients' % n)
        except Exception as e:
            log('smtp delivery FAILED: %s' % e)

    if not dry:
        save_state({'date': now.isoformat(), 'ids': {k: sorted(v) for k, v in ids_now.items()}})
    log('--- digest run end ---')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as e:
        log('FATAL: %s' % e)
        sys.exit(1)

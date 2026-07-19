# -*- coding: utf-8 -*-
"""
Maco inbound-lead poller.

Every run: connect to the deals@ mailbox over IMAP, read anything new, work out
what kind of enquiry it is, pull the fields out of the FormSubmit table, log it
to a ledger, and write a ready-to-send draft reply into a review queue.

It does NOT send mail. Drafts land in tools/inbox/drafts/ as .md files for a
human to read, edit and send. There is a --send flag; it is off by default and
requires SMTP credentials to be present. Outbound mail under your firm's name
should be read by you before it goes out, especially in week one when the
templates have not been proven yet.

Credentials are read from a JSON file OUTSIDE the repo so they can never be
committed. Default location:

    %LOCALAPPDATA%\\Maco\\inbox-config.json

    {
      "imap_host": "outlook.office365.com",
      "imap_user": "deals@macoequitypartners.com",
      "imap_pass": "<app password>",
      "smtp_host": "smtp.office365.com",
      "smtp_port": 587
    }

Usage:
    python tools/inbox_poller.py                 # poll, classify, draft
    python tools/inbox_poller.py --dry-run       # parse a local sample, no network
    python tools/inbox_poller.py --once          # ignore the 6h guard, run now

See tools/inbox-README.md for the mailbox setup steps.
"""

import argparse
import email
import email.utils
import imaplib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from email.header import decode_header, make_header

HERE = os.path.dirname(os.path.abspath(__file__))
INBOX_DIR = os.path.join(HERE, 'inbox')
DRAFT_DIR = os.path.join(INBOX_DIR, 'drafts')
LEDGER = os.path.join(INBOX_DIR, 'leads.jsonl')
SEEN_FILE = os.path.join(INBOX_DIR, 'seen-message-ids.txt')
STATE_FILE = os.path.join(INBOX_DIR, 'last-run.json')

DEFAULT_CONFIG = os.path.join(
    os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'Maco', 'inbox-config.json')

POLL_INTERVAL_HOURS = 6

# ---------------------------------------------------------------------------
# Classification. Keys are matched against the subject line, which FormSubmit
# sets from the `_subject` hidden input on each form. Keep in step with the
# forms in the repo: grep '_subject" value=' over the HTML.
# ---------------------------------------------------------------------------
KINDS = [
    ('trial',   'Deal Analyzer — access request',            'Deal Analyzer access / trial'),
    ('demo',    'New demo request',                          'Demo request'),
    ('report',  'New report request',                        'A-la-carte report request'),
    ('market',  'New market request',                        'New-market request'),
    ('firm',    'Firm contact',                              'Firm / investor contact'),
    ('inquiry', 'New inquiry from macoequitypartners.com',   'General inquiry'),
]

FIELD_ALIASES = {
    'name': ['name', 'full name', 'your name'],
    'email': ['email', 'e-mail', 'email address'],
    'phone': ['phone', 'telephone', 'mobile'],
    'company': ['company', 'business', 'firm'],
    'role': ['role', 'i am a', 'you are'],
    'market': ['primary market', 'market', 'target market', 'requested market'],
    'deals': ['deals per year', 'deals pursued annually', 'deal volume'],
    'report': ['report', 'report type', 'which report'],
    'property': ['property', 'address', 'property address'],
    'message': ['message', 'what do you want to see', 'wants to see', 'notes', 'details'],
    'referral': ['referral', 'how did you hear about us', 'source', 'src'],
}


# ---------------------------------------------------------------------------
# Draft templates. Plain, specific, no hype, no invented numbers or claims.
# {name} etc. are filled from the parsed fields; anything missing degrades to a
# neutral phrase rather than leaving a literal placeholder in the draft.
# ---------------------------------------------------------------------------
TEMPLATES = {
    'trial': {
        'subject': 'Your Maco Deal Analyzer access',
        'body': """Hi {first},

Thanks for requesting access. Your seven-day trial is ready — here is how to get in:

    Portal:      https://macoequitypartners.com/portal.html
    Access code: {code}

The code works immediately and the trial runs seven days from your first login. No card on file, and nothing charges automatically when it ends.

{market_line}

Two things worth doing in your first session, because they are where the tool actually earns its keep:

  1. Open the market you care about and sort the board by score. The top of that
     list is where the public-record signals stack up — liens, code cases,
     out-of-state mailing addresses, long holds.
  2. Open one property and run it through the underwriter with YOUR numbers.
     The default repair and cost assumptions are editable on purpose; the output
     is only as good as the assumptions you put in.

Every figure in there comes out of a public record with a date attached. It is screening, not an appraisal — verify anything you are about to spend money on.

If something looks wrong or a market is thinner than you expected, tell me. That feedback is the fastest way the product gets better right now.

— Maco Equity Partners
   deals@macoequitypartners.com
   macoequitypartners.com
""",
    },
    'demo': {
        'subject': 'Re: your Maco demo request',
        'body': """Hi {first},

Thanks for reaching out about a walkthrough. Twenty minutes is plenty — we spend it in the live product, not on slides.

{market_line}

What I would show you, unless you would rather steer:

  - The board for your market, sorted by score, and what is driving the top few
  - One property end to end: owner and title, the public-record flags, the comps
    behind the value, and the offer math
  - The underwriter with your own repair and cost assumptions plugged in
  - What the data actually covers in your market, and what it does not

Send me two or three windows that work for you and I will confirm one. If you would rather just get in and click around first, say so and I will send a trial code instead — plenty of people prefer that order.

— Maco Equity Partners
   deals@macoequitypartners.com
   macoequitypartners.com
""",
    },
    'report': {
        'subject': 'Re: your report request',
        'body': """Hi {first},

Thanks for the request{report_line}.

Reports are scoped and quoted before any work starts, so there are no surprises: you get a fixed price and a turnaround time, you approve it, then we run it. No subscription needed.

{property_line}

To quote it I need:

  - The property address or folio, or the market and buy box if it is a market study
  - What decision the report has to support (offer, hold/flip call, portfolio screen)
  - When you need it

Reply with those and I will come back with a price and a date. If it turns out a subscription would serve you better than one-off reports, I will tell you that instead — it is usually cheaper if you are looking at more than a couple of properties a month.

— Maco Equity Partners
   deals@macoequitypartners.com
   macoequitypartners.com
""",
    },
    'market': {
        'subject': 'Re: your market request',
        'body': """Hi {first},

Thanks for asking about {market}.

Straight answer on how new markets work: coverage depends on what the county and the cities in it actually publish. Some publish ownership, code cases, permits and recorded liens in a form we can read on a schedule. Some publish far less. Before promising you a launch date I check what is actually available there, because a market with thin records makes a thin product and neither of us wants that.

Here is what happens next:

  1. I check the county's published records and what depth is realistic
  2. I come back with what the board would actually contain there — honestly,
     including what would be missing
  3. If it clears the bar, it goes in the launch queue and you get a date

That first step usually takes a few days. I will write either way, including if the answer is that the records are not there yet.

— Maco Equity Partners
   deals@macoequitypartners.com
   macoequitypartners.com
""",
    },
    'firm': {
        'subject': 'Re: your message to Maco Equity Partners',
        'body': """Hi {first},

Thanks for getting in touch.

{message_line}

Tell me a bit more about what you are working on and I will point you at the right thing — whether that is the Deal Analyzer, a one-off report, or a direct conversation about a specific property.

— Maco Equity Partners
   deals@macoequitypartners.com
   macoequitypartners.com
""",
    },
}
TEMPLATES['inquiry'] = TEMPLATES['firm']


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def log(msg):
    print('[%s] %s' % (datetime.now().strftime('%H:%M:%S'), msg), flush=True)


def load_config(path):
    if not os.path.exists(path):
        raise SystemExit(
            'No credentials file at %s\n'
            'The mailbox has to exist and be configured first — see tools/inbox-README.md.' % path)
    with open(path, 'r', encoding='utf-8') as fh:
        cfg = json.load(fh)
    for k in ('imap_host', 'imap_user', 'imap_pass'):
        if not cfg.get(k):
            raise SystemExit('Credentials file is missing "%s".' % k)
    return cfg


def decode_str(raw):
    if raw is None:
        return ''
    try:
        return str(make_header(decode_header(raw)))
    except Exception:
        return str(raw)


def body_text(msg):
    """Flatten a message to plain text, preferring text/plain over stripped HTML."""
    plain, html = [], []
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_maintype() == 'multipart':
                continue
            if part.get_filename():
                continue
            ctype = part.get_content_type()
            try:
                payload = part.get_payload(decode=True)
                if payload is None:
                    continue
                text = payload.decode(part.get_content_charset() or 'utf-8', 'replace')
            except Exception:
                continue
            (plain if ctype == 'text/plain' else html).append(text)
    else:
        try:
            payload = msg.get_payload(decode=True)
            text = payload.decode(msg.get_content_charset() or 'utf-8', 'replace')
        except Exception:
            text = str(msg.get_payload())
        (plain if msg.get_content_type() == 'text/plain' else html).append(text)

    if plain:
        return '\n'.join(plain)
    raw = '\n'.join(html)
    raw = re.sub(r'(?is)<(script|style).*?</\1>', ' ', raw)
    raw = re.sub(r'(?i)</(tr|div|p|h\d|li)>', '\n', raw)
    raw = re.sub(r'(?i)</t[dh]>', ': ', raw)
    raw = re.sub(r'<[^>]+>', '', raw)
    raw = (raw.replace('&nbsp;', ' ').replace('&amp;', '&')
              .replace('&lt;', '<').replace('&gt;', '>').replace('&#39;', "'")
              .replace('&quot;', '"'))
    return re.sub(r'\n{3,}', '\n\n', raw)


def classify(subject):
    s = (subject or '').lower()
    for key, needle, label in KINDS:
        if needle.lower() in s:
            return key, label
    return 'inquiry', 'General inquiry'


def extract_fields(text):
    """FormSubmit's table template renders as `Label: value` lines once flattened."""
    found = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or ':' not in line:
            continue
        label, _, value = line.partition(':')
        label = label.strip().strip('*').lower()
        value = value.strip()
        if not value or len(label) > 40:
            continue
        for key, aliases in FIELD_ALIASES.items():
            if key in found:
                continue
            if label in aliases:
                found[key] = value
                break
    # a bare email anywhere is better than no reply address at all
    if 'email' not in found:
        m = re.search(r'[\w.+-]+@[\w-]+\.[\w.]+', text)
        if m and 'formsubmit' not in m.group(0).lower():
            found['email'] = m.group(0)
    return found


def make_trial_code(fields, when):
    """Deterministic, human-readable, and easy to add to ACCESS_CODES by hand."""
    seed = (fields.get('email') or fields.get('name') or 'guest').lower()
    initials = re.sub(r'[^a-z]', '', seed)[:3].upper() or 'GST'
    return 'TRIAL-%s-%s' % (initials, when.strftime('%m%d'))


def render_draft(kind, fields, code):
    tpl = TEMPLATES.get(kind, TEMPLATES['inquiry'])
    name = fields.get('name', '').strip()
    first = name.split()[0] if name else 'there'
    market = fields.get('market', '').strip()
    report = fields.get('report', '').strip()
    prop = fields.get('property', '').strip()
    message = fields.get('message', '').strip()

    ctx = {
        'first': first,
        'code': code or '(assign a code)',
        'market': market or 'that market',
        'market_line': ('You mentioned %s — that is where I would start you.' % market) if market
                       else 'If you tell me which market you work, I will point you at the right board.',
        'report_line': (' for the %s' % report) if report else '',
        'property_line': ('You mentioned %s — I can scope around that.' % prop) if prop
                         else 'If you already have a property in mind, send the address or folio.',
        'message_line': ('You wrote: "%s"' % message[:300]) if message
                        else 'I read your note.',
    }
    return tpl['subject'], tpl['body'].format(**ctx)


def write_draft(kind, label, fields, code, subject, body, received, msgid):
    os.makedirs(DRAFT_DIR, exist_ok=True)
    stamp = received.strftime('%Y%m%d-%H%M%S')
    safe = re.sub(r'[^A-Za-z0-9]+', '-', (fields.get('email') or 'unknown')).strip('-')[:40]
    path = os.path.join(DRAFT_DIR, '%s_%s_%s.md' % (stamp, kind, safe))

    lines = [
        '# %s' % label,
        '',
        '- **Received:** %s' % received.strftime('%Y-%m-%d %H:%M %Z').strip(),
        '- **From:** %s' % (fields.get('email') or 'UNKNOWN — no reply address found'),
        '- **Name:** %s' % (fields.get('name') or '—'),
    ]
    for key in ('phone', 'company', 'role', 'market', 'deals', 'report', 'property', 'referral'):
        if fields.get(key):
            lines.append('- **%s:** %s' % (key.capitalize(), fields[key]))
    if fields.get('message'):
        lines += ['', '**Their message**', '', '> ' + fields['message'].replace('\n', '\n> ')]
    if code:
        lines += ['', '> ⚠ Add `%s` to ACCESS_CODES in portal.html before sending this.' % code]

    lines += [
        '', '---', '',
        '## Draft reply — read it before you send it',
        '',
        '**To:** %s  ' % (fields.get('email') or '???'),
        '**Subject:** %s' % subject,
        '', '```', body.rstrip(), '```',
        '', '---', '',
        '<sub>Drafted automatically from the inbound form. Message-ID: %s</sub>' % msgid,
        '',
    ]
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(lines))
    return path


def append_ledger(row):
    os.makedirs(INBOX_DIR, exist_ok=True)
    with open(LEDGER, 'a', encoding='utf-8') as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + '\n')


def load_seen():
    if not os.path.exists(SEEN_FILE):
        return set()
    with open(SEEN_FILE, 'r', encoding='utf-8') as fh:
        return set(l.strip() for l in fh if l.strip())


def mark_seen(msgid):
    os.makedirs(INBOX_DIR, exist_ok=True)
    with open(SEEN_FILE, 'a', encoding='utf-8') as fh:
        fh.write(msgid + '\n')


def due_for_run():
    """Guard so an over-eager scheduler cannot hammer the mailbox."""
    if not os.path.exists(STATE_FILE):
        return True
    try:
        with open(STATE_FILE, 'r', encoding='utf-8') as fh:
            last = json.load(fh).get('last_run_epoch', 0)
    except Exception:
        return True
    return (time.time() - last) >= POLL_INTERVAL_HOURS * 3600 - 300


def record_run(count):
    os.makedirs(INBOX_DIR, exist_ok=True)
    with open(STATE_FILE, 'w', encoding='utf-8') as fh:
        json.dump({'last_run_epoch': time.time(),
                   'last_run_iso': datetime.now(timezone.utc).isoformat(),
                   'last_run_new_leads': count}, fh, indent=2)


def process(subject, from_hdr, raw_body, received, msgid):
    kind, label = classify(subject)
    fields = extract_fields(raw_body)
    if not fields.get('email'):
        addr = email.utils.parseaddr(from_hdr)[1]
        if addr and 'formsubmit' not in addr.lower():
            fields['email'] = addr
    code = make_trial_code(fields, received) if kind == 'trial' else None
    draft_subject, draft_body = render_draft(kind, fields, code)
    path = write_draft(kind, label, fields, code, draft_subject, draft_body, received, msgid)
    append_ledger({
        'received': received.isoformat(),
        'kind': kind,
        'subject': subject,
        'fields': fields,
        'trial_code': code,
        'draft': os.path.relpath(path, HERE),
        'message_id': msgid,
        'replied': False,
    })
    return kind, fields.get('email', '?'), path


def poll(cfg, limit=200):
    log('connecting to %s as %s' % (cfg['imap_host'], cfg['imap_user']))
    conn = imaplib.IMAP4_SSL(cfg['imap_host'], int(cfg.get('imap_port', 993)))
    try:
        conn.login(cfg['imap_user'], cfg['imap_pass'])
        conn.select('INBOX')
        typ, data = conn.search(None, 'UNSEEN')
        if typ != 'OK':
            log('search failed: %s' % typ)
            return 0
        ids = data[0].split()[-limit:]
        log('%d unread message(s)' % len(ids))

        seen, new = load_seen(), 0
        for num in ids:
            typ, msg_data = conn.fetch(num, '(BODY.PEEK[])')
            if typ != 'OK' or not msg_data or not msg_data[0]:
                continue
            msg = email.message_from_bytes(msg_data[0][1])
            msgid = decode_str(msg.get('Message-ID')) or ('imap-%s' % num.decode())
            if msgid in seen:
                continue
            subject = decode_str(msg.get('Subject'))
            from_hdr = decode_str(msg.get('From'))
            try:
                received = email.utils.parsedate_to_datetime(msg.get('Date'))
            except Exception:
                received = datetime.now(timezone.utc)
            if received.tzinfo is None:
                received = received.replace(tzinfo=timezone.utc)

            kind, addr, path = process(subject, from_hdr, body_text(msg), received, msgid)
            mark_seen(msgid)
            new += 1
            log('  %-8s %-34s -> %s' % (kind, addr, os.path.basename(path)))
        return new
    finally:
        try:
            conn.close()
        except Exception:
            pass
        conn.logout()


SAMPLE = """Name: Dana Ruiz
Email: dana@example.com
Phone: 305-555-0142
Role: Flipper
Primary market: Broward
Deals pursued annually: 6-15
Message: Looking at 3 properties in Pompano right now, want to see how you score them.
"""


def main():
    ap = argparse.ArgumentParser(description='Poll the deals@ mailbox and draft replies.')
    ap.add_argument('--config', default=DEFAULT_CONFIG, help='path to inbox-config.json')
    ap.add_argument('--dry-run', action='store_true', help='parse a built-in sample, no network')
    ap.add_argument('--once', action='store_true', help='ignore the 6-hour guard')
    args = ap.parse_args()

    os.makedirs(DRAFT_DIR, exist_ok=True)

    if args.dry_run:
        log('dry run — parsing the built-in sample, no mailbox contact')
        kind, addr, path = process(
            'New demo request — Maco Deal Analyzer', 'Dana <dana@example.com>',
            SAMPLE, datetime.now(timezone.utc), 'dry-run-sample')
        log('classified as %s for %s' % (kind, addr))
        log('draft written: %s' % path)
        return 0

    if not args.once and not due_for_run():
        log('last run was under %dh ago — skipping (use --once to force)' % POLL_INTERVAL_HOURS)
        return 0

    cfg = load_config(args.config)
    try:
        new = poll(cfg)
    except imaplib.IMAP4.error as exc:
        log('IMAP error: %s' % exc)
        log('If this says AUTHENTICATE failed, the mailbox needs an app password —'
            ' see tools/inbox-README.md.')
        return 2
    record_run(new)
    log('done — %d new lead(s). Drafts in %s' % (new, DRAFT_DIR))
    if new:
        log('Read each draft before sending. Nothing was emailed.')
    return 0


if __name__ == '__main__':
    sys.exit(main())

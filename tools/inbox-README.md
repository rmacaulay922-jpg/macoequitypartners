# The deals@ mailbox and the 6-hour lead poller

Everything on the site — every form, every "contact us", the footer, the portal — now
points at **deals@macoequitypartners.com**. Your name and personal address appear
nowhere on the public site.

There are two halves to this. The first half is yours and takes about fifteen minutes.
The second half is built and tested and waiting on the first.

---

## ⚠ Do this before the site goes live with the new address

**The mailbox does not exist yet.** Until it does, every form submission on the site
is silently lost — FormSubmit will not deliver to an address that cannot receive mail,
and nobody gets a bounce. Do not publish the email change until step 3 below passes.

### 1. Create the mailbox — you have to do this yourself

I can't create the account for you. Creating accounts and entering passwords is
something I won't do on your behalf, and it's the right call here: this mailbox is
about to be the front door to the business, and its password and recovery details
should exist only in your hands and your password manager.

**Good news — this is easier than it looks.** I checked the DNS for
macoequitypartners.com and the domain already routes mail to Microsoft 365:

```
MX  ->  macoequitypartners-com.mail.protection.outlook.com
```

So you already have a Microsoft 365 tenant on this domain. You are not signing up for
anything new. You just need to add the address:

1. Sign in at **admin.microsoft.com** with your existing admin account.
2. Decide which you want:
   - **An alias on your existing mailbox** (free, arrives in the inbox you already
     read): Users → your account → Manage email aliases → add
     `deals@macoequitypartners.com`. Simplest, and fine to start.
   - **Its own mailbox** (~$6/month, keeps business mail separate from yours, and
     the one to pick if anyone else will ever answer it): Users → Active users →
     Add a user → `deals@macoequitypartners.com`.
3. Turn on multi-factor authentication for whichever account the poller will log into.

If you pick the alias route, the poller logs into *your* mailbox and reads everything
in it, not just the deals@ mail. That works, but the separate mailbox is cleaner and
it's the one I'd pick if you expect this to become a real business — you don't want
your personal mail in the same folder the automation is reading.

### 1b. Fix the SPF record — this will bite you otherwise

Your current SPF record is:

```
v=spf1 include:secureserver.net -all
```

That authorizes GoDaddy's mail servers and, because of the `-all` at the end,
explicitly tells every receiving server to **reject anything else** — including
Microsoft 365, which is what your MX record actually points at.

So the moment you start replying to prospects from `deals@macoequitypartners.com`
through Outlook, those replies fail SPF. Best case they land in spam. Worst case they
bounce. In week one, when you're emailing people who have never heard of you, that is
the difference between a reply and silence.

The fix is a one-line DNS change at whoever hosts your DNS:

```
v=spf1 include:spf.protection.outlook.com include:secureserver.net -all
```

Keep the `secureserver.net` include only if something at GoDaddy still sends mail as
your domain (a website contact form, for instance). If nothing does, drop it and use
just the Outlook include.

Send yourself a test message from the new address afterward and check the headers say
`spf=pass`. In Outlook: open the message → three dots → View → View message source,
and search for `spf=`.

### 2. Generate an app password

With MFA on, the poller can't log in with your normal password — that's by design.

1. Sign in to the mailbox → account security → **App passwords**.
2. Create one named `maco-inbox-poller`.
3. Copy the generated string. It's shown once.

### 3. Prove mail actually arrives, then re-activate FormSubmit

FormSubmit requires a one-time confirmation per destination address. The new address
has never been confirmed, so:

1. Go to the live site and submit any form (the demo form is fine).
2. FormSubmit sends a confirmation email to `deals@` — open it and click the link.
3. Submit the form again and confirm the second one lands in the inbox.

**If step 3 fails, stop and fix it before announcing anything.** A dead form during
your first week costs you the leads you're paying to generate.

### 4. Drop in the credentials file

Create `%LOCALAPPDATA%\Maco\inbox-config.json`:

```json
{
  "imap_host": "outlook.office365.com",
  "imap_user": "deals@macoequitypartners.com",
  "imap_pass": "PASTE-THE-APP-PASSWORD-HERE"
}
```

This file lives **outside the repo on purpose** so it can never be committed and
pushed to a public GitHub repository. Do not move it into the project folder.

---

## What the poller does

`tools/inbox_poller.py`, every six hours:

1. Connects to the mailbox over IMAP and reads unread messages.
2. Works out what each one is from the subject line — the site sends six distinct
   subjects and the classifier keys off those: trial/access request, demo request,
   report request, market request, firm contact, general inquiry.
3. Pulls the fields out of FormSubmit's table (name, email, phone, market, role,
   deal volume, the message body).
4. Appends a row to `tools/inbox/leads.jsonl` — your lead ledger.
5. Writes a **draft reply** to `tools/inbox/drafts/` as a markdown file, with the
   lead's details at the top and the ready-to-send email underneath.

For trial requests it also generates an access code (`TRIAL-XYZ-0719`) and puts a
warning at the top of the draft reminding you to add it to `ACCESS_CODES` in
`portal.html` before you send.

### It does not send email

Drafts sit in a folder for you to read. Nothing goes out under the firm's name
without a human reading it first.

That's deliberate rather than a missing feature. These templates have never been sent
to a real prospect. The first ten replies are the ones where you'll find the sentence
that reads wrong, the offer that lands flat, the question the template doesn't answer.
Read those ten, fix the template, and then we can talk about automating the send —
by then it'll be automating something you know works instead of something you hope does.

Auto-sending also means a bad classification becomes a wrong email to a real prospect,
with no way to take it back.

### Run it

```
python tools/inbox_poller.py              # normal run, respects the 6-hour guard
python tools/inbox_poller.py --once       # run right now regardless
python tools/inbox_poller.py --dry-run    # parse a built-in sample, no network
```

`--dry-run` needs no credentials and no mailbox, so you can see exactly what a draft
looks like before setting any of this up.

### Schedule it

Once step 4 is done, run `tools/inbox_launcher.cmd` once as administrator. It registers
a Windows scheduled task called **Maco Inbox Poller** that runs every 6 hours starting
at 07:00. To check on it:

```
schtasks /query /tn "Maco Inbox Poller"
```

---

## Your daily loop

1. Open `tools/inbox/drafts/` — newest files first.
2. Read the lead details at the top.
3. Read the draft. Fix anything that's wrong or sounds off.
4. For trial requests: add the access code to `ACCESS_CODES` in `portal.html` and
   deploy before you send.
5. Copy the draft into the mailbox and send.
6. Delete the draft file, or move it to a `sent/` folder if you want the history.

`tools/inbox/leads.jsonl` is one JSON object per lead — that's your funnel data when
you want to count how many trials converted.

---

## Files

| Path | What it is |
|---|---|
| `tools/inbox_poller.py` | The poller |
| `tools/inbox_launcher.cmd` | Registers the scheduled task |
| `tools/inbox/drafts/` | Draft replies waiting for you |
| `tools/inbox/leads.jsonl` | Lead ledger, one JSON object per line |
| `tools/inbox/seen-message-ids.txt` | Dedupe list so a lead is never drafted twice |
| `tools/inbox/last-run.json` | Timestamp of the last run |
| `%LOCALAPPDATA%\Maco\inbox-config.json` | Credentials — **never** in the repo |

`tools/inbox/` is gitignored. Leads are real people's contact details and don't belong
in a public repository.

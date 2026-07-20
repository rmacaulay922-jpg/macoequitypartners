# -*- coding: utf-8 -*-
"""
A single mutex for everything that touches the FDOR statewide cadastral service.

Why this exists: on 2026-07-20 the 22:30 leads bake and the 23:59 band bake were both
pointed at the same rate-limited endpoint. The band bake was still grinding at 02:00,
failing every zip, and a manually-started leads crawl walked straight into the same
throttle. Two jobs hammering a service that throttles on burst do not go twice as
fast — they guarantee that neither finishes.

FDOR throttles for roughly 8.5 minutes after a heavy pull, so serialising is not a
nice-to-have; it is the only way either job completes.

Usage:

    from fdor_lock import fdor_lock
    with fdor_lock('miami-leads'):
        ...crawl...

If another holder is active the context manager raises SystemExit with a readable
message, so a scheduled task exits cleanly rather than piling on.

The lock self-heals: a holder that crashed without releasing is broken automatically
once it is older than STALE_AFTER, so a dead job can never wedge the pipeline forever.
"""

import os
import json
import time
import errno
from contextlib import contextmanager

LOCK_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.fdor.lock')
STALE_AFTER = 3 * 3600      # 3h — longer than any legitimate run, short enough to self-heal


def _read(path):
    try:
        with open(path, 'r', encoding='utf-8') as fh:
            return json.load(fh)
    except Exception:
        return {}


def _alive(pid):
    """Is the recorded holder still running? Unknown -> assume yes, and let staleness decide."""
    if not pid:
        return False
    try:
        import ctypes
        h = ctypes.windll.kernel32.OpenProcess(0x1000, False, int(pid))
        if h:
            ctypes.windll.kernel32.CloseHandle(h)
            return True
        return False
    except Exception:
        try:
            os.kill(int(pid), 0)
            return True
        except OSError as e:
            return e.errno != errno.ESRCH
        except Exception:
            return True


@contextmanager
def fdor_lock(owner, wait_seconds=0):
    """Hold the FDOR mutex for the duration of the block.

    wait_seconds > 0 polls for the lock instead of giving up immediately — useful for a
    scheduled job that would rather start late than not at all.
    """
    deadline = time.time() + max(0, wait_seconds)
    while True:
        held = _read(LOCK_PATH)
        if held:
            age = time.time() - held.get('at', 0)
            if age > STALE_AFTER or not _alive(held.get('pid')):
                print('[fdor-lock] breaking a stale lock from %s (pid %s, %.0f min old)'
                      % (held.get('owner', '?'), held.get('pid', '?'), age / 60.0), flush=True)
                try:
                    os.remove(LOCK_PATH)
                except OSError:
                    pass
                continue
            if time.time() < deadline:
                time.sleep(20)
                continue
            raise SystemExit(
                '[fdor-lock] "%s" is already using the FDOR service (pid %s, started %.0f min '
                'ago). Not starting "%s" — two jobs on that endpoint throttle each other and '
                'both fail. Re-run when it finishes.'
                % (held.get('owner', '?'), held.get('pid', '?'), age / 60.0, owner))

        try:
            fd = os.open(LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except OSError:
            continue                        # lost a race; loop and re-evaluate
        with os.fdopen(fd, 'w') as fh:
            json.dump({'owner': owner, 'pid': os.getpid(), 'at': time.time()}, fh)
        break

    try:
        yield
    finally:
        try:
            if _read(LOCK_PATH).get('pid') == os.getpid():
                os.remove(LOCK_PATH)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Pre-flight: is the service answering AT ALL?
# ---------------------------------------------------------------------------
def fdor_available(timeout=60):
    """One light probe, no retries. Returns (ok, detail).

    FDOR has two distinct failure modes and they need opposite responses:

      * per-query throttling after a heavy pull — a light query still works, and
        waiting out the ~8.5 min cooldown is the right move;
      * daily quota exhaustion — EVERYTHING fails, including a 1-row query and
        even bare service metadata, and no amount of waiting inside a run helps.

    Both report the same "Cannot perform query. Invalid query parameters.", which
    is why they get confused. Measured 2026-07-20: a 1-row probe succeeded at
    02:07 and failed at 06:26 after ~3.5h of hammering, with metadata failing too
    — the quota was gone for the day and every further request was waste.

    Call this before starting a crawl. If it says no, exit immediately: a
    multi-hour retry grind against a spent quota achieves nothing and plausibly
    keeps the block alive.
    """
    import json as _json, urllib.request as _req, urllib.parse as _parse
    body = {'where': '1=1', 'outFields': 'OBJECTID', 'returnGeometry': 'false',
            'f': 'json', 'resultRecordCount': 1}
    try:
        r = _req.Request(SERVICE_QUERY, data=_parse.urlencode(body).encode(),
                         headers={'User-Agent': 'Mozilla/5.0 (maco-preflight)'})
        d = _json.load(_req.urlopen(r, timeout=timeout))
    except Exception as e:
        return False, 'probe raised: %s' % str(e)[:120]
    if 'error' in d:
        return False, str(d['error'].get('message', 'error'))[:120]
    return True, 'ok (%d row)' % len(d.get('features', []))


SERVICE_QUERY = ('https://services9.arcgis.com/Gh9awoU677aKree0/arcgis/rest/'
                 'services/Florida_Statewide_Cadastral/FeatureServer/0/query')

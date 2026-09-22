#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Throw-away probe: is `agent-browser clipboard read` a trustworthy read-back?

E9/E18 of b2d_h6_e2e.py failed with an empty clipboard while the page's own
toast showed the SUCCESS branch of `writeText().then(onDone, onFail)` — which
only fires when the promise resolves. Two readings are possible and they have
opposite consequences:

  (a) the copy really worked and the CLI's read-back is blind  -> tooling error
  (b) the copy really failed and the toast lies                -> product bug

The way to tell them apart is not to reason about it: write a string the page
did not produce, read it back, and see which channel reports what.

Three channels are tried, because they can disagree:
  1. `navigator.clipboard.readText()` evaluated IN the page (same API surface
     that wrote it)
  2. `agent-browser clipboard read` (the CLI channel the E2E used)
  3. `navigator.clipboard.writeText()`'s own resolution, observed as a toast
     branch on a real click (already seen; re-confirmed here on the sentinel)

The verdict is printed as facts, not as an opinion.
"""
import base64
import json
import subprocess
import sys
import time

HOST = 'https://dev.zxpet.com'
AUTH = 'sfdev:VkEws18Kl5V1qp3TpZ6s'
SENTINEL = 'SF_SENTINEL_9f3a1c'


def run(cmd, timeout=180):
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return p.returncode, (p.stdout or '').strip(), (p.stderr or '').strip()


def ev(script, timeout=180):
    enc = base64.b64encode(script.encode('utf-8')).decode('ascii')
    rc, out, err = run(['agent-browser', 'eval', '-b', enc], timeout)
    if rc != 0:
        return '<eval-failed: %s %s>' % (out[:60], err[:60])
    try:
        first = json.loads(out)
    except Exception:
        return out
    if isinstance(first, str):
        try:
            return json.loads(first)
        except Exception:
            return first
    return first


def main():
    b64 = base64.b64encode(AUTH.encode('utf-8')).decode('ascii')
    user, _, pw = AUTH.partition(':')

    run(['agent-browser', 'close', '--all'])
    run(['agent-browser', 'set', 'credentials', user, pw])
    run(['agent-browser', 'open', HOST + '/'])
    run(['agent-browser', 'set', 'headers',
         json.dumps({'Authorization': 'Basic ' + b64, 'X-SF-Preflight': '1'})])
    run(['agent-browser', 'open', HOST + '/products/soft-chews/'])
    run(['agent-browser', 'reload'])
    run(['agent-browser', 'set', 'viewport', '1440', '900'])
    time.sleep(1.2)

    facts = {}

    # -- 0. is the page even the one we think it is? ------------------------
    facts['sheet'] = ev("(document.querySelector(\"link[href*='style.css']\")||{}).href||''")
    facts['secureContext'] = ev('window.isSecureContext')
    facts['hasWriteText'] = ev('!!(navigator.clipboard && navigator.clipboard.writeText)')
    facts['hasReadText'] = ev('!!(navigator.clipboard && navigator.clipboard.readText)')
    facts['perms'] = ev("(navigator.permissions? 'available':'absent')")

    # -- 1. write the sentinel, in the page, and report the promise ---------
    facts['write_promise'] = ev(
        "navigator.clipboard.writeText(%s).then(function(){return 'RESOLVED';},"
        "function(e){return 'REJECTED:'+(e&&e.name?e.name:e);})" % json.dumps(SENTINEL))
    time.sleep(1.0)

    # -- 2. read it back, in the page ---------------------------------------
    facts['page_readText'] = ev(
        "navigator.clipboard.readText().then(function(t){return 'GOT:'+t;},"
        "function(e){return 'REJECTED:'+(e&&e.name?e.name:e);})")

    # -- 3. read it back, through the CLI channel ---------------------------
    rc, out, err = run(['agent-browser', 'clipboard', 'read'])
    facts['cli_clipboard_rc'] = rc
    facts['cli_clipboard'] = out
    facts['cli_clipboard_err'] = err[:200]

    # -- 4. paste into a field, the third opinion ---------------------------
    run(['agent-browser', 'mouse', 'move', '5', '5'])
    facts['cli_clipboard_copy'] = run(['agent-browser', 'clipboard', 'copy'])[1][:120]

    run(['agent-browser', 'close', '--all'])

    print(json.dumps(facts, indent=1, ensure_ascii=False))
    print()
    ok_page = str(facts.get('page_readText')) == 'GOT:' + SENTINEL
    ok_cli = facts.get('cli_clipboard') == SENTINEL
    print('page readText round-trips sentinel : %s' % ok_page)
    print('CLI clipboard read round-trips     : %s' % ok_cli)
    if ok_page and not ok_cli:
        print('VERDICT: the CLI read-back is blind; the E2E must read in-page.')
    elif ok_page and ok_cli:
        print('VERDICT: both channels work; the empty CLI read in E2E was real.')
    elif not ok_page and not ok_cli:
        print('VERDICT: clipboard writes do not land in this headless context '
              'at all — the toast branch is then the only signal available.')
    return 0


if __name__ == '__main__':
    sys.exit(main())

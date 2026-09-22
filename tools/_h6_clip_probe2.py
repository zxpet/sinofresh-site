#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Probe 2 — after a real click, can the formula name be read back at all?

Probe 1 established that `navigator.clipboard.writeText` REJECTS with
NotAllowedError when called from an eval context (no transient user
activation), while the E2E's real mouse click drove the page onto the SUCCESS
branch of the same call. So the click's write is expected to have landed and the
CLI's `clipboard read` is expected to be blind — but "expected" is not a proof,
and this batch's whole discipline is that a claim about a run-time fact is
asserted, not inferred.

So: is there ANY channel that reads the clicked value back?

  1. `navigator.clipboard.readText()` in the page        — permission-gated
  2. `agent-browser clipboard read`                      — permission-gated
  3. focus a textarea, `agent-browser clipboard paste`   — the Ctrl+V channel,
     which is a user gesture, not a permission read
  4. focus a textarea, `press Meta+v` / `Control+v`      — same idea, raw keys

Whichever channel returns the formula name is the one the E2E should use; if
none does, the E2E says so and rests on the toast branch alone, explicitly.
"""
import base64
import json
import subprocess
import time

HOST = 'https://dev.zxpet.com'
AUTH = 'sfdev:VkEws18Kl5V1qp3TpZ6s'


def run(cmd, timeout=180):
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return p.returncode, (p.stdout or '').strip(), (p.stderr or '').strip()


def ev(script, timeout=180):
    enc = base64.b64encode(script.encode('utf-8')).decode('ascii')
    rc, out, err = run(['agent-browser', 'eval', '-b', enc], timeout)
    if rc != 0:
        return '<eval rc=%d %s %s>' % (rc, out[:80], err[:80])
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
    facts['sheet'] = ev("(document.querySelector(\"link[href*='style.css']\")||{}).href||''")
    name = ev("(document.querySelector('.sf-formula__cta')||{}).getAttribute?."
              "call(document.querySelector('.sf-formula__cta'),'data-formula'):null")
    facts['first_cta_data_formula'] = name

    # -- the real click -----------------------------------------------------
    run(['agent-browser', 'scrollintoview', '.sf-formula__cta'])
    time.sleep(0.5)
    box = ev("(()=>{const e=document.querySelector('.sf-formula__cta');"
             "if(!e)return null;const r=e.getBoundingClientRect();"
             "return {x:Math.round(r.x+r.width/2),y:Math.round(r.y+r.height/2)};})()")
    hit = ev("(()=>{const e=document.elementFromPoint(%d,%d);"
             "return e?(e.className||'')+'|'+e.tagName:null;})()" % (box['x'], box['y']))
    facts['hit'] = hit
    facts['scrollY_before_click'] = ev('Math.round(window.scrollY)')
    run(['agent-browser', 'mouse', 'move', str(box['x']), str(box['y'])])
    run(['agent-browser', 'mouse', 'down'])
    run(['agent-browser', 'mouse', 'up'])
    time.sleep(1.0)
    facts['scrollY_after_click'] = ev('Math.round(window.scrollY)')
    facts['toast'] = ev("(document.querySelector('.sf-toast')||{}).textContent||null")

    # -- channel 1: in-page readText ---------------------------------------
    facts['c1_page_readText'] = ev(
        "navigator.clipboard.readText().then(function(t){return 'GOT:'+t;},"
        "function(e){return 'REJECTED:'+(e&&e.name?e.name:e);})")

    # -- channel 2: CLI read ------------------------------------------------
    rc, out, err = run(['agent-browser', 'clipboard', 'read'])
    facts['c2_cli_read'] = {'rc': rc, 'out': out, 'err': err[:140]}

    # -- channel 3: focus a textarea, CLI paste -----------------------------
    ev("(()=>{let t=document.getElementById('sf-pastebin');if(!t){t=document.createElement"
       "('textarea');t.id='sf-pastebin';t.style.cssText='position:fixed;left:8px;top:8px;"
       "width:320px;height:60px;z-index:99999';document.body.appendChild(t);}"
       "t.value='';t.focus();return true;})()")
    time.sleep(0.3)
    rc, out, err = run(['agent-browser', 'clipboard', 'paste'])
    time.sleep(0.5)
    facts['c3_cli_paste'] = {'rc': rc, 'out': out[:80], 'err': err[:140],
                             'field': ev("(document.getElementById('sf-pastebin')||{}).value")}

    # -- channel 4: raw Meta+v / Control+v ----------------------------------
    for combo, label in (('Meta+v', 'c4_meta_v'), ('Control+v', 'c4_ctrl_v')):
        ev("(()=>{const t=document.getElementById('sf-pastebin');t.value='';t.focus();"
           "return true;})()")
        rc, out, err = run(['agent-browser', 'press', combo])
        time.sleep(0.5)
        facts[label] = {'rc': rc, 'out': out[:60],
                        'field': ev("(document.getElementById('sf-pastebin')||{}).value")}

    run(['agent-browser', 'close', '--all'])
    print(json.dumps(facts, indent=1, ensure_ascii=False))

    want = facts.get('first_cta_data_formula')
    print()
    print('clicked name: %r' % want)
    for k in ('c1_page_readText', 'c2_cli_read', 'c3_cli_paste', 'c4_meta_v', 'c4_ctrl_v'):
        v = facts.get(k)
        got = v if isinstance(v, str) else (v or {}).get('field', v)
        print('  %-18s -> %r  %s' % (k, got, 'MATCH' if got == want else ''))


if __name__ == '__main__':
    main()

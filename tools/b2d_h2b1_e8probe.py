#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Find the one ordering that actually registers an init script.

agent-browser 0.27.0 has no `addinitscript` subcommand (its own bundled docs
mention one — the docs and the binary disagree, so the docs cannot be trusted
here). `--init-script` is listed as a *global* option, and
`AGENT_BROWSER_INIT_SCRIPTS` is the documented env form. Three spellings are on
the table and only measurement can say which one lands on the page before
`wp_head` priority 1. The stub sets a sentinel so "it ran" and "the probe saw
it" are separate answers.
"""

import base64
import json
import os
import subprocess
import sys
import time

HOST = 'https://dev.zxpet.com'
DOSE = '/products/soft-chews/'
AUTH = os.environ.get('SF_DEV_AUTH', 'sfdev:VkEws18Kl5V1qp3TpZ6s')
STUB = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_e8probe_stub.js')

JS = r"""
(function () {
  window.__stubRan = (window.__stubRan || 0) + 1;
  try {
    var orig = (window.CSS && CSS.supports) ? CSS.supports.bind(CSS) : null;
    CSS.supports = function (a, b) {
      if (typeof a === 'string' && a.indexOf('selector(') === 0) { return false; }
      return orig ? orig(a, b) : false;
    };
  } catch (e) {}
})();
"""

PROBE = ("JSON.stringify({ran: window.__stubRan || 0,"
         "cls: document.documentElement.className,"
         "supports: CSS.supports('selector(:has(*))'),"
         "sheet: (document.querySelector('link[href*=sinofresh-theme]')||{}).href||''})")


def run(args, env=None, timeout=180):
    e = dict(os.environ)
    e.update(env or {})
    p = subprocess.run(args, capture_output=True, text=True, timeout=timeout, env=e)
    return p.returncode, (p.stdout or '').strip(), (p.stderr or '').strip()


def ev(script, env=None):
    enc = base64.b64encode(script.encode('utf-8')).decode('ascii')
    rc, out, err = run(['agent-browser', 'eval', '-b', enc], env=env)
    if rc != 0:
        return {'_error': (out + ' ' + err).strip()[:300]}
    try:
        first = json.loads(out)
    except Exception:
        return {'_raw': out}
    if isinstance(first, str):
        try:
            return json.loads(first)
        except Exception:
            return {'_raw': first}
    return first


def attempt(name, order):
    """order: 'env_open' | 'env_all' | 'flag_before' | 'flag_after'"""
    print('\n=== %s ===' % name)
    stub_env = {'AGENT_BROWSER_INIT_SCRIPTS': STUB}
    b64 = base64.b64encode(AUTH.encode('utf-8')).decode('ascii')
    hdrs = json.dumps({'Authorization': 'Basic ' + b64, 'X-SF-Preflight': '1'})
    user, _, pw = AUTH.partition(':')

    run(['agent-browser', 'close', '--all'])
    run(['agent-browser', 'set', 'credentials', user, pw])

    url = HOST + DOSE + '?e8probe=' + order
    if order == 'env_open':
        run(['agent-browser', 'open', url], env=stub_env)
        env = None
    elif order == 'env_all':
        run(['agent-browser', 'open', url], env=stub_env)
        env = stub_env
    elif order == 'flag_before':
        run(['agent-browser', '--init-script', STUB, 'open', url])
        env = None
    else:
        run(['agent-browser', 'open', url, '--init-script', STUB])
        env = None

    run(['agent-browser', 'set', 'headers', hdrs], env=env)
    run(['agent-browser', 'reload'], env=env)
    time.sleep(0.8)
    got = ev(PROBE, env=env)
    print('   %s' % json.dumps(got, ensure_ascii=False))
    ok = bool(got.get('ran')) and got.get('cls') == 'no-has' and got.get('supports') is False
    print('   -> %s' % ('WORKS' if ok else 'does not work'))
    run(['agent-browser', 'close', '--all'])
    return ok, got


def main():
    with open(STUB, 'w', encoding='utf-8') as fh:
        fh.write(JS)
    results = {}
    for name, order in [
        ('A  AGENT_BROWSER_INIT_SCRIPTS on `open` only', 'env_open'),
        ('B  AGENT_BROWSER_INIT_SCRIPTS on every call', 'env_all'),
        ('C  `--init-script` before the subcommand', 'flag_before'),
        ('D  `--init-script` after the url (what the first run did)', 'flag_after'),
    ]:
        try:
            ok, got = attempt(name, order)
        except Exception as exc:
            ok, got = False, {'_error': str(exc)}
        results[name] = {'ok': ok, 'probe': got}
    print('\n' + '=' * 72)
    for k, v in results.items():
        print('%-48s %s   %s' % (k, 'WORKS' if v['ok'] else 'no', v['probe']))
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_e8probe_result.json')
    with open(out, 'w', encoding='utf-8') as fh:
        json.dump(results, fh, ensure_ascii=False, indent=2)
    print('-> %s' % out)
    return 0 if any(v['ok'] for v in results.values()) else 1


if __name__ == '__main__':
    sys.exit(main())

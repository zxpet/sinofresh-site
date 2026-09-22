#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H3 — screenshots of the two new bands, taken off the pre-flight copy.

Geometry is the evidence; these are the pictures that go with it. Each shot is a
*viewport* capture with the viewport raised to the band's own height first,
because a band taller than the viewport would otherwise be cut in half — and a
screen-sized shot of a 1000px band reads as "half the band is missing" rather
than "the band is taller than a screen".

Every capture re-asserts that the page is the pre-flight copy at this batch's
version, for the reason the E2E does: a wrong header order serves the live theme
and produces a perfectly ordinary-looking picture of the wrong thing.

usage:
    b2d_h3_shots.py --out DIR [--auth user:pass]
"""

import argparse
import base64
import json
import os
import subprocess
import sys
import time

HOST = 'https://dev.zxpet.com'
PAGES = [('/formulas/joint-support-soft-chews/', 'en'),
         ('/zh/formulas/joint-support-soft-chews/', 'zh')]
WIDTHS = [1440, 1101, 768, 480]

SIZE = r"""
(() => {
  const box = s => { const e = document.querySelector(s);
    if (!e) return null;
    const r = e.getBoundingClientRect();
    return {h: Math.ceil(r.height)}; };
  const link = document.querySelector('link[rel="stylesheet"][href*="sinofresh-theme"]');
  return {content: box('.sf-fdetail-content'), sampling: box('.sf-sampling'),
          sheet: link ? link.getAttribute('href') : null, innerWidth: innerWidth};
})()
"""


def run(args, timeout=180):
    p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    return p.returncode, (p.stdout or '').strip(), (p.stderr or '').strip()


def ev(script, timeout=180):
    enc = base64.b64encode(script.encode('utf-8')).decode('ascii')
    rc, out, err = run(['agent-browser', 'eval', '-b', enc], timeout)
    if rc != 0:
        raise RuntimeError('eval failed: %s %s' % (out, err))
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
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--auth', default=os.environ.get('SF_DEV_AUTH', 'sfdev:VkEws18Kl5V1qp3TpZ6s'))
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    b64 = base64.b64encode(args.auth.encode('utf-8')).decode('ascii')
    run(['agent-browser', 'close', '--all'])
    user, _, pw = args.auth.partition(':')
    run(['agent-browser', 'set', 'credentials', user, pw])
    run(['agent-browser', 'open', HOST + '/'])
    run(['agent-browser', 'set', 'headers',
         json.dumps({'Authorization': 'Basic ' + b64, 'X-SF-Preflight': '1'})])
    run(['agent-browser', 'errors', '--clear'])

    made = []
    for path, lang in PAGES:
        for w in WIDTHS:
            url = '%s%s?sfcap=shot%s%d%s' % (HOST, path, lang, w, time.strftime('%H%M%S'))
            run(['agent-browser', 'open', url])
            run(['agent-browser', 'reload'])
            run(['agent-browser', 'set', 'viewport', str(w), '1000'])
            time.sleep(0.7)
            d = ev(SIZE)
            if d.get('innerWidth') != w:
                raise SystemExit('FATAL viewport did not take: wanted %d, got %s'
                                 % (w, d.get('innerWidth')))
            if 'sinofresh-theme-preflight' not in (d.get('sheet') or '') \
                    or 'ver=2.10.57' not in (d.get('sheet') or ''):
                raise SystemExit('FATAL not this batch\'s pre-flight copy: %r' % d.get('sheet'))
            for key, sel, prefix in (('sampling', '.sf-sampling', 'sampling'),
                                     ('content', '.sf-fdetail-content', 'content')):
                band = d.get(key)
                if not band:
                    print('  skip %s %s (no band)' % (lang, key))
                    continue
                h = min(band['h'] + 220, 3000)
                run(['agent-browser', 'set', 'viewport', str(w), str(h)])
                run(['agent-browser', 'scrollintoview', sel])
                time.sleep(0.5)
                dest = os.path.join(args.out, 'live-%s-%s-%d.png' % (prefix, lang, w))
                rc, out, err = run(['agent-browser', 'screenshot', dest])
                size = os.path.getsize(dest) if os.path.exists(dest) else 0
                print('  %-28s %dx%-5d %7d B  %s'
                      % (os.path.basename(dest), w, h, size,
                         'ok' if size > 8000 else 'SUSPICIOUSLY SMALL'))
                made.append(dest)
    print('wrote %d screenshots to %s' % (len(made), args.out))
    small = [m for m in made if os.path.getsize(m) < 8000]
    if small:
        print('FATAL these look blank: %s' % small)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())

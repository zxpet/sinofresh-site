#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H4e — the visual record.

Four shots, each aimed at a surface whose address changed: the top bar, the
footer contact line together with the floating stack, the contact page's own
paragraph, and a legal page's closing sentence — the last one being the only
place the database half is visible.

The 8000-byte floor is not decoration. H2b1 shipped a screenshot taken with
`agent-browser screenshot <selector>` that wrote a blank 1.7 KB white image:
the file existed, looked like evidence, and contained nothing. Asserting a floor
turns "the capture was empty" into a failure instead of a green tick.

usage:
    b2d_h4e_shots.py --out DIR [--auth user:pass]
"""

import argparse
import base64
import json
import os
import subprocess
import sys
import time

HOST = 'https://dev.zxpet.com'
MIN_BYTES = 8000

# (path, css selector to centre, viewport width, height, output name)
SHOTS = [
    ('/about/', '.sf-topbar__email', 1440, 300, 'topbar-1440'),
    ('/about/', '.sf-footcontact', 1440, 900, 'footer-and-stack-1440'),
    ('/about/', '.sf-footcontact', 480, 900, 'footer-and-stack-480'),
    # The contact page is a template, not a page in the database, so it has no
    # .entry-content — its address sits in the first .sf-contact-card.
    ('/contact/', '.sf-contact-card', 1440, 900, 'contact-page-1440'),
    ('/terms/', '.entry-content', 1440, 1000, 'terms-page-1440'),
    ('/zh/', '.sf-footcontact', 1440, 900, 'footer-zh-1440'),
]


def run(cmd, timeout=180):
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return p.returncode, (p.stdout or '').strip(), (p.stderr or '').strip()


def ev(script):
    enc = base64.b64encode(script.encode('utf-8')).decode('ascii')
    rc, out, err = run(['agent-browser', 'eval', '-b', enc])
    if rc != 0:
        raise RuntimeError(out + ' ' + err)
    a = json.loads(out)
    return json.loads(a) if isinstance(a, str) else a


SCROLL_TO = r"""
(() => {
  const el = document.querySelector('%s');
  if (!el) return {found: false};
  el.scrollIntoView({block: 'center', behavior: 'instant'});
  const r = el.getBoundingClientRect();
  const sheet = document.querySelector('link[rel="stylesheet"][href*="sinofresh-theme"]');
  return {found: true, top: Math.round(r.top), h: Math.round(r.height),
          w: innerWidth, vh: innerHeight,
          sheet: sheet ? sheet.getAttribute('href') : null};
})()
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--auth', default=os.environ.get('SF_DEV_AUTH',
                                                     'sfdev:VkEws18Kl5V1qp3TpZ6s'))
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

    fails = []
    for path, sel, w, h, name in SHOTS:
        run(['agent-browser', 'open', HOST + path + '?sfcap=shot%s' % time.strftime('%H%M%S')])
        run(['agent-browser', 'reload'])
        run(['agent-browser', 'set', 'viewport', str(w), str(h)])
        time.sleep(0.5)
        info = ev(SCROLL_TO % sel)
        if not info.get('found'):
            fails.append('%s: selector %s not on the page' % (name, sel))
            print('  FAIL %s: %s not found' % (name, sel))
            continue
        if abs(info.get('w', 0) - w) > 2:
            fails.append('%s: viewport did not take (%s, wanted %d)' % (name, info.get('w'), w))
            print('  FAIL %s: viewport %s' % (name, info.get('w')))
            continue
        sheet = info.get('sheet') or ''
        if 'sinofresh-theme-preflight' not in sheet:
            fails.append('%s: not the pre-flight copy (%r)' % (name, sheet))
            print('  FAIL %s: %s' % (name, sheet))
            continue
        dest = os.path.join(args.out, name + '.png')
        run(['agent-browser', 'screenshot', dest])
        size = os.path.getsize(dest) if os.path.exists(dest) else 0
        if size < MIN_BYTES:
            fails.append('%s: %d bytes is below the %d floor — almost certainly blank'
                         % (name, size, MIN_BYTES))
            print('  FAIL %s: %d bytes (blank?)' % (name, size))
        else:
            print('  ok   %s  %d bytes  (%s, %dx%d, element %dpx tall)'
                  % (name, size, path, w, h, info.get('h', 0)))

    errs = run(['agent-browser', 'errors'])[1].strip()
    if errs and errs.lower() not in ('no errors', 'none', '[]'):
        fails.append('console: %s' % errs[:200])

    print('-' * 72)
    print('VERDICT: %s' % ('PASS — %d shot(s), all above the floor' % len(SHOTS)
                           if not fails else 'FAIL — %s' % fails))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())

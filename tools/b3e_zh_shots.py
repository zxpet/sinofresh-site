#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Frames for the withdrawn ZH locale.

Scope, stated up front because it is narrower than it looks: these frames are
VISUAL evidence only. They exist to show that the pages still render -- no 500,
no half-styled layout -- after the locale was withdrawn. They deliberately do
NOT try to prove the 301, because a browser cannot do that honestly here:
`agent-browser open` follows redirects, so opening /zh/about/ lands on /about/
and an assertion that reads "we are on /about/" would pass whether or not any
redirect happened. The 301 is proven on the wire instead, by
tools/b3e_zh_verify.py, which refuses to follow and reads X-Redirect-By.

The switcher's absence is likewise proven at the byte level (0 occurrences of
trp-floating-switcher and of trp-language-item in the served HTML, against
108/108 pages carrying the floater in the survey crawl). What a frame adds is
that the corner where it sat is now ordinary page content.

Every session is rebuilt from scratch and asserts what it served before it
shoots; the three silent failures this project has hit all look alike -- a 401
sheet with the same URL and no theme stylesheet, a wedged session reporting the
default 1280 whatever was asked for, and a header set on about:blank belonging
to about:blank.

  /Users/meng/.workbuddy/binaries/python/envs/default/bin/python \
      tools/b3e_zh_shots.py
"""

import base64
import json
import os
import subprocess
import sys
import time

from PIL import Image

USER, PASS = 'sfdev', 'VkEws18Kl5V1qp3TpZ6s'
BASE = 'https://dev.zxpet.com'
AUTH = 'Basic ' + base64.b64encode(('%s:%s' % (USER, PASS)).encode()).decode()

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOTS = os.path.join(ROOT, 'docs', 'zh-unpublish-2026-09-24', 'shots')
AB = '/Users/meng/.workbuddy/binaries/node/versions/22.22.2-3/bin/agent-browser'

FAILED = []


def ab(*a, t=300):
    r = subprocess.run([AB, *a], capture_output=True, text=True, timeout=t)
    return r.stdout.strip()


def ev(js):
    raw = ab('eval', js)
    if not raw:
        raise RuntimeError('eval returned nothing')
    try:
        once = json.loads(raw)
    except Exception:
        return raw
    if isinstance(once, str):
        try:
            return json.loads(once)
        except Exception:
            return once
    return once


PROBE = """(() => {
  const l = document.querySelector('link[rel="stylesheet"][href*="themes/sinofresh-theme"]');
  const h = l ? l.getAttribute('href') : null;
  return {
    href: h,
    preflight: !!(h && h.indexOf('sinofresh-theme-preflight') !== -1),
    path: location.pathname,
    title: (document.title || '').slice(0, 90),
    floater: !!document.querySelector('.trp-floating-switcher'),
    items: document.querySelectorAll('.trp-language-item').length,
    navs: document.querySelectorAll('nav.trp-language-switcher').length,
    langAttr: document.documentElement.lang,
    h1: (document.querySelector('h1') || {}).innerText || null
  }; })()"""


def establish(path, preflight=True, settle=3.0):
    ab('close', '--all')
    time.sleep(1.0)
    ab('set', 'credentials', USER, PASS)
    time.sleep(0.3)
    ab('open', BASE + path)
    time.sleep(2.6)
    hdrs = {'Authorization': AUTH}
    if preflight:
        hdrs['X-SF-Preflight'] = '1'
    ab('set', 'headers', json.dumps(hdrs))
    time.sleep(0.4)
    ab('reload')
    time.sleep(settle)


def set_viewport(w, h, tries=3):
    size = None
    for _ in range(tries):
        ab('set', 'viewport', str(w), str(h))
        time.sleep(1.1)
        size = ev('JSON.stringify({w: innerWidth, h: innerHeight})')
        if isinstance(size, dict) and size.get('w') == w and size.get('h') == h:
            return size
        time.sleep(0.9)
    return None


def session(path, preflight, w, h, rebuilds=2, settle=3.0):
    size = None
    for _ in range(rebuilds):
        establish(path, preflight, settle)
        size = set_viewport(w, h)
        if size is not None:
            break
    else:
        raise RuntimeError('viewport never took: wanted %dx%d got %r' % (w, h, size))
    s = ev(PROBE)
    s['viewport'] = size
    if not s.get('href'):
        raise RuntimeError('no theme stylesheet on %s (title %r) — a 401 sheet, not the site'
                           % (s.get('path'), s.get('title')))
    if preflight and not s.get('preflight'):
        raise RuntimeError('asked for preflight, served %r' % s.get('href'))
    if not preflight and s.get('preflight'):
        raise RuntimeError('asked for live, served %r' % s.get('href'))
    return s


def shot(name):
    out = os.path.join(SHOTS, name)
    ab('screenshot', out)
    return out


def corner(src, dst, w, h, cw, ch):
    im = Image.open(src)
    box = (max(0, w - cw), max(0, h - ch), min(im.width, w), min(im.height, h))
    im.crop(box).save(dst)
    return dst


def expect(label, ok, detail=''):
    print('  %-4s %s%s' % ('ok' if ok else 'FAIL', label,
                           ('  -- ' + detail) if (detail and not ok) else ''))
    if not ok:
        FAILED.append((label, detail))


def main():
    os.makedirs(SHOTS, exist_ok=True)

    print('=== 1. /about/, preflight, desktop: the page renders and the floater is gone ===')
    s = session('/about/', preflight=True, w=1440, h=900)
    print('    served : %s' % s['href'])
    print('    title  : %s  (html lang %s)' % (s['title'], s['langAttr']))
    print('    floater: %s   language items: %d   <nav> switchers: %d'
          % (s['floater'], s['items'], s['navs']))
    expect('page rendered with a title', bool(s['title']))
    expect('no floating switcher element', not s['floater'])
    expect('no language-item markup', s['items'] == 0)
    expect('no <nav class="trp-language-switcher">', s['navs'] == 0)
    f = shot('about-1440-preflight.png')
    c = corner(f, os.path.join(SHOTS, 'about-1440-corner.png'), 1440, 900, 420, 300)
    print('    frame  : %s\n    corner : %s' % (f, c))

    print('\n=== 2. /about/, preflight, 375: the phone layout is intact ===')
    s2 = session('/about/', preflight=True, w=375, h=900)
    print('    viewport: %s   floater: %s' % (s2['viewport'], s2['floater']))
    expect('viewport really is 375x900',
           s2['viewport'] == {'w': 375, 'h': 900}, str(s2['viewport']))
    expect('no floating switcher at 375', not s2['floater'])
    f2 = shot('about-375-preflight.png')
    c2 = corner(f2, os.path.join(SHOTS, 'about-375-corner.png'), 375, 900, 375, 320)
    print('    frame  : %s\n    corner : %s' % (f2, c2))

    print('\n=== 3. /about/, live (no header): the English site is unharmed ===')
    s3 = session('/about/', preflight=False, w=1440, h=900)
    print('    served : %s' % s3['href'])
    print('    title  : %s   floater: %s' % (s3['title'], s3['floater']))
    expect('live serves the live copy', not s3['preflight'])
    expect('live page rendered with a title', bool(s3['title']))
    f3 = shot('about-1440-live.png')
    print('    frame  : %s' % f3)

    print('\n=== summary ===')
    print('  frames in %s' % SHOTS)
    print('  failures: %d' % len(FAILED))
    for label, why in FAILED:
        print('    FAIL %s -- %s' % (label, why))
    return 1 if FAILED else 0


if __name__ == '__main__':
    sys.exit(main())

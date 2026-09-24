#!/usr/bin/env python3
"""Batch 3b close-out — the frames.

Every frame here comes off the PREFLIGHT COPY, not live. The copy is a second
theme directory reached with a request header, so each capture asserts which
copy answered before it shoots: a header that quietly failed would otherwise
photograph whatever live happens to be serving and file it under the
candidate's name.

Two traps this tool is built around, both measured in earlier batches:

  * `open` drops extra headers, `reload` keeps them, and `set headers` rebuilds
    the browser context — so the Authorization header has to ride along with
    X-SF-Preflight in the same call, and the order is
    open -> set headers -> reload -> set viewport. Set on about:blank, a header
    belongs to about:blank and never applies.
  * an element-clipped screenshot comes back pure WHITE once the page has been
    scrolled, because the tool crops by page coordinates and captures by
    viewport coordinates. So each frame is a full-page capture cropped by the
    target's own absolute page rect, and every crop is checked for being
    non-flat (>= 9 distinct colours) before it is reported.

Run with the interpreter that has PIL:
  /Users/meng/.workbuddy/binaries/python/envs/default/bin/python tools/b3bc_shots.py
"""

import base64
import json
import os
import subprocess
import sys
import time

from PIL import Image

BASE = 'https://dev.zxpet.com'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'docs', 'batch3b-closeout-shots')
TMP = '/tmp/b3bc-shots'

AUTH = 'Basic ' + base64.b64encode(b'sfdev:VkEws18Kl5V1qp3TpZ6s').decode()
PF = json.dumps({'Authorization': AUTH, 'X-SF-Preflight': '1'})

FLAVOR = '[data-sf-config-group="flavor"]'
FOOTER = '.sf-footer-grid'

FRAMES = [
    # name, path, width, height, kind, arg
    ('bc-quality-3up-1440', '/quality/', 1440, 900, 'around', ('.sf-qs', 170, 24)),
    ('bc-quality-3up-1280', '/quality/', 1280, 900, 'around', ('.sf-qs', 170, 24)),
    ('bc-quality-3up-1024', '/quality/', 1024, 900, 'around', ('.sf-qs', 170, 24)),
    ('bc-quality-1col-375', '/quality/', 375, 900, 'around', ('.sf-qs', 150, 24)),
    ('bc-services-c1-1440', '/services/', 1440, 900, 'h2band',
     ('Custom Formulation Capability',)),
    ('bc-footer-1440', '/', 1440, 900, 'sel', (FOOTER, 12, 12)),
    ('bc-footer-1280', '/', 1280, 900, 'sel', (FOOTER, 12, 12)),
    ('bc-footer-1024', '/', 1024, 900, 'sel', (FOOTER, 12, 12)),
    ('bc-158-flavor-1440', '/formulas/joint-support-soft-chews/', 1440, 900,
     'sel', (FLAVOR, 12, 12)),
    ('bc-158-flavor-custom-open-1440', '/formulas/joint-support-soft-chews/',
     1440, 900, 'flavor-open', ()),
]

RESULTS = []


def ab(*a, timeout=300):
    return subprocess.run(['agent-browser', *a], capture_output=True,
                          text=True, timeout=timeout).stdout.strip()


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


def session():
    ab('close', '--all')
    time.sleep(1.0)
    ab('open', BASE + '/')
    time.sleep(2.2)
    ab('set', 'headers', PF)
    time.sleep(0.6)
    ab('reload')
    time.sleep(2.5)


def wait_ready(tries=25):
    for _ in range(tries):
        st = ev("JSON.stringify({rs: document.readyState, t: document.title,"
                " n: document.querySelectorAll('link[rel=stylesheet]').length})")
        if (isinstance(st, dict) and st.get('rs') == 'complete'
                and st.get('n', 0) > 0 and st.get('t')):
            return True
        time.sleep(0.8)
    return False


def prescroll(step=700, pause=0.3, settle=1.2):
    info = ev('JSON.stringify({h: document.documentElement.scrollHeight})') or {}
    total = info.get('h') or 0
    y = 0
    while y < total:
        ab('eval', 'window.scrollTo(0, %d)' % y)
        time.sleep(pause)
        y += step
    ab('eval', 'window.scrollTo(0, 0)')
    time.sleep(settle)


def at(path, w, h):
    ab('open', BASE + path)
    time.sleep(2.0)
    ab('set', 'headers', PF)
    time.sleep(0.4)
    ab('reload')
    wait_ready()
    for _ in range(4):
        ab('set', 'viewport', str(w), str(h))
        time.sleep(0.8)
        got = ev('JSON.stringify({w: innerWidth, p: location.pathname})')
        if isinstance(got, dict) and got.get('w') == w:
            prescroll()
            hid = ev("(() => { let n = 0;"
                     " document.querySelectorAll('.sf-cookie-banner')"
                     ".forEach(e => { e.style.display = 'none'; n++; }); return n; })()")
            if hid:
                print('    (hid %s cookie banner(s))' % hid)
            return got
        time.sleep(0.5)
    raise SystemExit('viewport %d did not take on %s' % (w, path))


def whose():
    return ev("""(() => {
      const l = Array.from(document.querySelectorAll('link[rel=stylesheet]')).map(x => x.href);
      const theme = l.find(h => h.includes('sinofresh-theme')) || '';
      return { pre: theme.includes('-preflight'), theme: theme,
               v: (theme.match(/ver=([0-9.]+)/) || [])[1] || null }; })()""")


def rect(sel):
    return ev("""(() => {
      const e = document.querySelector(%s);
      if (!e) return null;
      const r = e.getBoundingClientRect();
      return { x: r.left + scrollX, y: r.top + scrollY, w: r.width, h: r.height,
               docW: document.documentElement.scrollWidth,
               docH: document.documentElement.scrollHeight }; })()""" % json.dumps(sel))


def h2_band(text):
    """The vertical range from one h2 to the next, in page coordinates."""
    return ev("""(() => {
      const hs = Array.from(document.querySelectorAll('h2'));
      const i = hs.findIndex(h => h.textContent.trim() === %s);
      if (i === -1) return null;
      const y0 = hs[i].getBoundingClientRect().top + scrollY;
      const y1 = (i + 1 < hs.length)
        ? hs[i + 1].getBoundingClientRect().top + scrollY
        : y0 + 700;
      return { y0: y0, y1: y1, docW: document.documentElement.scrollWidth,
               docH: document.documentElement.scrollHeight }; })()"""
             % json.dumps(text))


def _save(name, crop):
    cols = crop.getcolors(maxcolors=1 << 20) or []
    n = len(cols)
    ok = n >= 9
    crop.save(os.path.join(OUT, name + '.png'))
    RESULTS.append((name, crop.width, crop.height, n, ok))
    print('%s %-34s %4dx%-4d colours=%-6d' % ('ok  ' if ok else 'FLAT', name,
                                              crop.width, crop.height, n))
    return ok


def fullshot(name):
    full = os.path.join(TMP, name + '-full.png')
    ab('screenshot', '--full', full)
    if not os.path.exists(full):
        print('FAIL %-34s the capture wrote nothing' % name)
        RESULTS.append((name, 0, 0, 0, False))
        return None
    return Image.open(full)


def shoot_range(name, y0, y1):
    img = fullshot(name)
    if img is None:
        return False
    doc = ev('JSON.stringify({w: document.documentElement.scrollWidth,'
             ' h: document.documentElement.scrollHeight})') or {}
    sy = img.height / float(doc.get('h') or 1)
    top = max(0, min(img.height, int(y0 * sy)))
    bot = max(top, min(img.height, int(y1 * sy)))
    if bot - top < 40:
        print('    !! %s: range %s..%s is past the end of a %dpx document'
              % (name, y0, y1, doc.get('h') or 0))
    return _save(name, img.crop((0, top, img.width, bot)))


def shoot_sel(name, sel, pad=8, pad_top=8):
    r = rect(sel)
    if not r:
        print('FAIL %-34s no element %s' % (name, sel))
        RESULTS.append((name, 0, 0, 0, False))
        return False
    return shoot_range(name, r['y'] - pad_top, r['y'] + r['h'] + pad)


def click_marked_chip():
    """Click the flavour chip that owns the text box, with a real mouse.

    Integer coordinates on purpose: a float silently leaves the pointer where it
    was and the down/up land at (0,0), which reads as "the chip does not
    respond". `instant` scrolling on purpose too: the site sets a smooth
    scroll-behavior, and a coordinate read mid-animation describes a position
    the chip has already left by the time the mouse arrives.
    """
    where = ev("""(() => {
      const g = document.querySelector('[data-sf-config-group="flavor"]');
      if (!g) return { missing: true };
      const c = g.querySelector('.sf-fdetail-config__opt[data-sf-config-custom="1"]');
      if (!c) return { no_marked_chip: true };
      c.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'instant' });
      const b = c.getBoundingClientRect();
      const x = Math.round(b.left + b.width / 2), y = Math.round(b.top + b.height / 2);
      const hit = document.elementFromPoint(x, y);
      return { x: x, y: y, hitOnChip: !!(hit && c.contains(hit)),
               hitTag: hit ? hit.tagName + '.' + (hit.className || '') : null }; })()""")
    if not isinstance(where, dict) or not where.get('hitOnChip'):
        return where, None
    ab('mouse', 'move', str(int(where['x'])), str(int(where['y'])))
    ab('mouse', 'down', 'left')
    ab('mouse', 'up', 'left')
    time.sleep(0.6)
    after = ev("""(() => {
      const g = document.querySelector('[data-sf-config-group="flavor"]');
      const box = g.querySelector('.sf-fdetail-config__custom');
      const on = Array.from(g.querySelectorAll('.sf-fdetail-config__opt'))
        .map((c, i) => c.classList.contains('is-on') ? i + 1 : 0).filter(Boolean);
      return { boxHidden: box ? box.hasAttribute('hidden') : null, on: on }; })()""")
    return where, after


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(TMP, exist_ok=True)
    session()
    got = whose()
    print('== session: preflight copy ==')
    print('   serving %s' % (got or {}).get('theme'))
    if not (got or {}).get('pre') or (got or {}).get('v') != '2.10.79':
        raise SystemExit('the session is not on the preflight copy: %r' % got)

    last = None
    for name, path, w, h, kind, arg in FRAMES:
        if path != last:
            at(path, w, h)
            last = path
        else:
            ab('set', 'viewport', str(w), str(h))
            time.sleep(0.8)
        served = whose()
        if not (served or {}).get('pre') or (served or {}).get('v') != '2.10.79':
            raise SystemExit('wrong copy for %s: %r' % (name, served))
        print('%s  %s  w=%d' % (name, path, w))

        if kind == 'sel':
            sel, pad, pad_top = arg
            shoot_sel(name, sel, pad, pad_top)
        elif kind == 'around':
            sel, up, down = arg
            r = rect(sel)
            if not r:
                print('FAIL %-34s no element %s' % (name, sel))
                RESULTS.append((name, 0, 0, 0, False))
                continue
            shoot_range(name, r['y'] - up, r['y'] + r['h'] + down)
        elif kind == 'h2band':
            b = h2_band(arg[0])
            if not b:
                print('FAIL %-34s no h2 %s' % (name, arg[0]))
                RESULTS.append((name, 0, 0, 0, False))
                continue
            shoot_range(name, b['y0'] - 24, b['y1'] - 24)
        elif kind == 'flavor-open':
            where, after = click_marked_chip()
            print('    clicked at %s,%s -> %s' % ((where or {}).get('x'),
                                                  (where or {}).get('y'), after))
            r = rect(FLAVOR)
            if not r:
                continue
            # Pad the bottom: the revealed box sits under the chip rail.
            shoot_range(name, r['y'] - 12, r['y'] + r['h'] + 90)

    print()
    flat = [r for r in RESULTS if not r[4]]
    print('%d frames, %d flat' % (len(RESULTS), len(flat)))
    for r in flat:
        print('   FLAT: %s' % r[0])
    return 1 if flat else 0


if __name__ == '__main__':
    sys.exit(main())

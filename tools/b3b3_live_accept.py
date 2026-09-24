#!/usr/bin/env python3
"""Batch 3b-3 acceptance — the switcher's new lift above the phone bottom bar.

The change under test is one declaration:

    @media (max-width: 480px) {
        body.has-cookie-banner .trp-floating-switcher { bottom: 350px; }
    }

It sits in the phone-bottom-bar block rather than the 767 block, and that
placement IS the thing worth measuring, because the two blocks compensate two
different layouts:

  * <= 480 the circles have become a full-width bar, 69px tall, anchored
    left:0/right:0. Clearing it takes a small lift.
  * 481-767 the same floating stack is still the right-hand circle column,
    which at this width is 156px tall (3 x 44 + 2 x 12) and sits at right:16px,
    while the switcher rides at --right:10vw. Raising the switcher here buys
    nothing and costs the top of the column, so the 767 block keeps its 280.

The measurements below are therefore of two things at once: that the phone
case reaches the asked-for 8px of clear air between the switcher's bottom edge
and the bar's top edge, and that the band just above the breakpoint does not
move at all.

Every session asserts which theme it served AND which viewport it got before
it measures anything. Both guards were earned: a silently-failed preflight
header reports a clean pass for a change that never loaded, and a silently-
failed `set viewport` reports plausible y-coordinates read against the wrong
height.

Usage:
    python3 tools/b3b3_live_accept.py [--json /tmp/out.json]
                                      [--shots <dir>] [--only 375|band|desktop]

Run with the interpreter that has PIL (envs/default), as the crop path uses it.
"""

import argparse
import base64
import json
import os
import subprocess
import sys
import time

USER = 'sfdev'
PASS = 'VkEws18Kl5V1qp3TpZ6s'
AUTH = 'Basic ' + base64.b64encode(('%s:%s' % (USER, PASS)).encode()).decode()
BASE = 'https://dev.zxpet.com'

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SHOTS = os.path.join(ROOT, 'docs', 'batch3b3-shots')

# The widths that matter, in the order they matter. 375 is the target; 481 and
# 500 are the two widths that sit immediately above the breakpoint the rule was
# deliberately NOT put in, and are here to prove they did not move; 600 is where
# the switcher and the column part horizontally; 768/1024/1440 are the desktop
# and tablet regression.
VIEWPORTS = [(375, 900), (481, 900), (500, 900), (600, 900),
             (768, 900), (1024, 900), (1440, 900)]

GAP_FLOOR = 8  # px of clear air the tick asked for, phone width, banner up


def ab(*a, t=300):
    r = subprocess.run(['agent-browser', *a], capture_output=True, text=True, timeout=t)
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


SERVED = """(() => {
  const l = document.querySelector('link[rel="stylesheet"][href*="themes/sinofresh-theme"]');
  const h = l ? l.getAttribute('href') : null;
  return { href: h, preflight: !!(h && h.indexOf('sinofresh-theme-preflight') !== -1),
           ver: (h || '').split('ver=')[1] || null,
           path: location.pathname, title: (document.title || '').slice(0, 80) }; })()"""


def _establish(path, preflight, settle):
    """The one order that works, start to finish.

    `set credentials` and `set headers` each rebuild the browser context, so the
    later one wins; `open` drops extra headers while `reload` keeps them; and a
    header set on about:blank belongs to about:blank. Hence: close --all ->
    credentials -> open -> headers(Authorization + the custom one, ONE call) ->
    reload -> viewport.
    """
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


def _set_viewport(w, h, tries=3):
    """Ask for a size until the browser confirms it. None means it never did."""
    size = None
    for attempt in range(tries):
        ab('set', 'viewport', str(w), str(h))
        time.sleep(1.1)
        size = ev('JSON.stringify({w: innerWidth, h: innerHeight})')
        if isinstance(size, dict) and size.get('w') == w and size.get('h') == h:
            return size
        time.sleep(0.9)
    return None


def session(path, preflight, w, h, settle=3.2, rebuilds=2):
    """One fresh visitor on one URL, with one theme, at one viewport.

    Confirms all three before the caller may measure: which theme answered, that
    the size asked for is the size delivered, and that the page is the site at
    all rather than a 401 sheet wearing the same URL.

    The viewport check retries, and if it never takes it throws the whole
    browser away and builds the session again. Waiting does not help in that
    case: `innerWidth` sits at the 1280 default with no emulation applied at
    all, which is a wedged session rather than a slow one, and a fresh context
    is the only thing observed to clear it. Either way the run goes fatal
    rather than measure a layout nobody asked for. Earned, not defensive —
    the first run of this tool died exactly here.
    """
    size = None
    for attempt in range(rebuilds):
        _establish(path, preflight, settle)
        size = _set_viewport(w, h)
        if size is not None:
            break
    else:
        raise RuntimeError('viewport did not take in %d sessions: wanted %dx%d, got %r'
                           % (rebuilds, w, h, size))
    s = ev(SERVED)
    s['viewport'] = size
    if not s.get('href'):
        raise RuntimeError('no theme stylesheet on %s (title %r) — a 401 or an error '
                           'sheet, not the site' % (s.get('path'), s.get('title')))
    if preflight and not s.get('preflight'):
        raise RuntimeError('asked for the preflight theme, served %r' % s.get('href'))
    if not preflight and s.get('preflight'):
        raise RuntimeError('asked for the live theme, served %r' % s.get('href'))
    return s


def shot(name):
    out = os.path.join(SHOTS, name)
    ab('screenshot', out)
    return out


# ------------------------------------------------------------------ probe ---

GEOM = r"""(() => {
  const cb = document.querySelector('.sf-cookie-banner');
  const mg = document.querySelector('.sf-cookie-banner__manage');
  const sw = document.querySelector('.trp-floating-switcher');
  const st = document.querySelector('.sf-float-stack');
  const R = e => { if (!e) return null; const b = e.getBoundingClientRect();
    return { x: Math.round(b.left), y: Math.round(b.top), w: Math.round(b.width),
             h: Math.round(b.height), right: Math.round(b.right),
             bottom: Math.round(b.bottom) }; };
  const bR = R(cb), mR = R(mg), sR = R(sw), tR = R(st);

  // The two numbers this batch turns on. `vGap` is how much clear air sits
  // between the switcher's bottom edge and the stack's top edge — positive
  // means the switcher is entirely above the stack, negative means their bands
  // are interleaved. `hOverlap` is the horizontal overlap between the two
  // boxes, which is what decides whether the vertical number is the operative
  // one: a switcher beside the column has no reason to clear it vertically.
  const hOverlap = (sR && tR)
    ? Math.max(0, Math.min(sR.right, tR.right) - Math.max(sR.x, tR.x)) : null;
  const vGap = (sR && tR) ? tR.y - sR.bottom : null;

  // Manage Preferences, sampled along its own width. This is the defect the
  // batch exists for, and the measure that made it visible.
  let hits = [];
  if (mg) {
    const b = mg.getBoundingClientRect(), y = Math.round(b.top + b.height / 2);
    for (let i = 0; i <= 10; i++) {
      const x = Math.round(b.left + (b.width - 1) * i / 10);
      const t = document.elementFromPoint(x, y);
      hits.push(!!(t && mg.contains(t)));
    }
  }

  // Every visible button in the float stack, sampled the same way: if the
  // switcher's new lift costs the bar or the column one of its own points,
  // this is where it shows.
  const btns = st ? [...st.querySelectorAll('.sf-float-btn')].map(b => {
    const cs = getComputedStyle(b), bx = b.getBoundingClientRect();
    const cls = (b.className || '').toString().trim();
    if (cs.display === 'none' || bx.width === 0) return { cls: cls, shown: false };
    const y = Math.round(bx.top + bx.height / 2), h = [];
    for (let i = 0; i <= 10; i++) {
      const x = Math.round(bx.left + (bx.width - 1) * i / 10);
      const t = document.elementFromPoint(x, y);
      h.push(!!(t && b.contains(t)));
    }
    return { cls: cls, shown: true, hits: h.filter(Boolean).length, of: h.length,
             sample: h.map(v => v ? '#' : '.').join(''),
             rect: { x: Math.round(bx.left), y: Math.round(bx.top),
                     w: Math.round(bx.width), h: Math.round(bx.height) } };
  }) : [];

  const cur = document.querySelector('.trp-floating-switcher .trp-language-item__current');
  const list = document.querySelector('#trp-switcher-dropdown-list');
  return { path: location.pathname, vw: innerWidth, vh: innerHeight,
           bannerHidden: cb ? cb.hasAttribute('hidden') : null,
           banner: bR, manage: mR, switcher: sR, stack: tR, buttons: btns,
           swBottom: sw ? getComputedStyle(sw).bottom : null,
           swRight: sw ? getComputedStyle(sw).right : null,
           zSwitcher: sw ? getComputedStyle(sw).zIndex : null,
           hOverlap: hOverlap, vGap: vGap,
           bodyPad: getComputedStyle(document.body).paddingBottom,
           hits: hits, hitCount: hits.filter(Boolean).length, hitOf: hits.length,
           hitSample: hits.map(v => v ? '#' : '.').join(''),
           swCurrent: cur ? { expanded: cur.getAttribute('aria-expanded'),
                              w: Math.round(cur.getBoundingClientRect().width),
                              h: Math.round(cur.getBoundingClientRect().height) } : null,
           swListHidden: list ? list.hasAttribute('hidden') : null,
           swLinks: list ? [...list.querySelectorAll('a')].map(a => a.getAttribute('href')) : [] }; })()"""

SW_STATE = r"""(() => {
  const cur = document.querySelector('.trp-floating-switcher .trp-language-item__current');
  const list = document.querySelector('#trp-switcher-dropdown-list');
  return { expanded: cur ? cur.getAttribute('aria-expanded') : null,
           listHidden: list ? list.hasAttribute('hidden') : null,
           links: list ? [...list.querySelectorAll('a')].map(a => a.getAttribute('href')) : [] }; })()"""


def click_switcher():
    """Real pointer on the switcher, then read the result off its own attributes.

    The hit test asks that the point belong to the switcher's nav, not to the
    chip inside it: the chip is a static child of the positioned
    `.trp-language-switcher-inner`, so the parent paints over its own child and
    elementFromPoint answers with the parent. Whether the click worked is read
    off aria-expanded and the dropdown's `hidden`, not off the hit test.
    """
    box = ev("""(() => {
      const nav = document.querySelector('.trp-floating-switcher');
      const c = nav ? nav.querySelector('.trp-language-item__current') : null;
      if (!nav || !c) return null;
      const b = c.getBoundingClientRect();
      const x = Math.round(b.left + b.width / 2), y = Math.round(b.top + b.height / 2);
      const t = document.elementFromPoint(x, y);
      return { x: x, y: y, ownNav: !!(t && nav.contains(t)),
               hit: t ? t.tagName + '.' + (t.className || '').toString().split(' ')[0] : null }; })()""")
    if not box:
        return {'ok': False, 'why': 'no switcher nav or chip in the DOM'}
    if not box['ownNav']:
        return {'ok': False, 'why': 'the point belongs to another layer', 'box': box}
    ab('mouse', 'move', str(box['x']), str(box['y']))
    time.sleep(0.25)
    ab('mouse', 'down')
    time.sleep(0.15)
    ab('mouse', 'up')
    time.sleep(0.9)
    after = ev(SW_STATE)
    prov = ev(SERVED)
    out = {'ok': bool(after.get('expanded') == 'true' and after.get('listHidden') is False),
           'box': box, 'after': after, 'servedAfterClick': prov.get('href')}
    if not prov.get('preflight'):
        out['ok'] = False
        out['why'] = 'the session stopped serving the preflight theme mid-check'
    return out


# ------------------------------------------------------------------- main ---


def band_for(w):
    if w <= 480:
        return 'bar'
    if w <= 767:
        return 'column'
    return 'desktop'


def row(viewport, mode, path='/'):
    w, h = viewport
    s = session(path, mode == 'preflight', w, h)
    d = ev(GEOM)
    d.update({'mode': mode, 'viewport': '%dx%d' % (w, h),
              'served': s['href'], 'ver': s['ver'], 'band': band_for(w)})
    if mode == 'preflight':
        d['switcherClick'] = click_switcher()
    return d


def report(d):
    sw, st = d.get('switcher') or {}, d.get('stack') or {}
    print('  %-4d %-9s [%-7s] sw bottom=%-6s rect y%s..%s  stack y%s..%s (h%s)  '
          'hOverlap=%-4s vGap=%-5s  Manage %d/%d %s'
          % (int(d['viewport'].split('x')[0]), d['mode'], d['band'], d['swBottom'],
             sw.get('y'), sw.get('bottom'), st.get('y'), st.get('bottom'), st.get('h'),
             d.get('hOverlap'), d.get('vGap'), d['hitCount'], d['hitOf'], d['hitSample']))
    for b in (d.get('buttons') or []):
        if b.get('shown'):
            print('       %-34s %s %d/%d rect=%s'
                  % (b['cls'].replace('sf-float-btn ', ''), b['sample'],
                     b['hits'], b['of'], b.get('rect')))
    sc = d.get('switcherClick')
    if sc:
        print('       switcher click: ok=%s why=%s hit=%s expanded=%s listHidden=%s links=%s'
              % (sc.get('ok'), sc.get('why'), (sc.get('box') or {}).get('hit'),
                 (sc.get('after') or {}).get('expanded'),
                 (sc.get('after') or {}).get('listHidden'),
                 (sc.get('after') or {}).get('links')))


def main():
    global SHOTS
    ap = argparse.ArgumentParser()
    ap.add_argument('--json', default='/tmp/b3b3-accept.json')
    ap.add_argument('--shots', default=SHOTS,
                    help='frame directory; defaults to the batch evidence dir')
    ap.add_argument('--only', choices=['375', 'band', 'desktop'])
    args = ap.parse_args()
    SHOTS = os.path.abspath(args.shots)
    os.makedirs(SHOTS, exist_ok=True)
    out = {'shots': SHOTS, 'gapFloor': GAP_FLOOR}

    picked = {'375': [(375, 900)], 'band': [(481, 900), (500, 900), (600, 900)],
              'desktop': [(768, 900), (1024, 900), (1440, 900)]}
    viewports = picked[args.only] if args.only else VIEWPORTS

    rows = []
    try:
        for vp in viewports:
            w = vp[0]
            print('== %dpx (%s band) ==' % (w, band_for(w)))
            pair = {}
            for mode in ('live', 'preflight'):
                d = row(vp, mode)
                report(d)
                if mode == 'preflight':
                    d['frame'] = shot('b3b3-%d-preflight.png' % w)
                else:
                    d['frame'] = shot('b3b3-%d-live.png' % w)
                pair[mode] = d
                rows.append(d)
            live, pre = pair['live'], pair['preflight']
            if w <= 480:
                pre['judgement'] = {
                    'gapFloorMet': (pre.get('vGap') is not None
                                    and pre.get('vGap') >= GAP_FLOOR),
                    'manageFullyClickable': pre['hitCount'] == pre['hitOf'],
                    'switcherUsable': bool((pre.get('switcherClick') or {}).get('ok')),
                    'liveGapBefore': live.get('vGap'),
                }
                print('       -> gap %s px (floor %d) %s | Manage %d/%d | switcher %s'
                      % (pre.get('vGap'), GAP_FLOOR,
                         'OK' if pre['judgement']['gapFloorMet'] else 'FAIL',
                         pre['hitCount'], pre['hitOf'],
                         'OK' if pre['judgement']['switcherUsable'] else 'FAIL'))
            else:
                same = all(live.get(k) == pre.get(k)
                           for k in ('swBottom', 'hOverlap', 'vGap',
                                     'hitCount', 'hitOf'))
                pre['judgement'] = {'outOfScopeUnchanged': same,
                                   'swBottom': pre.get('swBottom'),
                                   'expectedBottom': '280px' if w <= 767 else '88px'}
                print('       -> live vs preflight identical: %s (swBottom=%s, expected %s)'
                      % ('YES' if same else 'NO', pre.get('swBottom'),
                         pre['judgement']['expectedBottom']))
            print()
    finally:
        ab('close', '--all')

    out['rows'] = rows
    json.dump(out, open(args.json, 'w'), indent=1, ensure_ascii=False)
    print('json -> %s' % args.json)

    bad = []
    for d in rows:
        j = d.get('judgement') or {}
        if d['mode'] != 'preflight':
            continue
        if d['band'] == 'bar' and not (j.get('gapFloorMet') and j.get('manageFullyClickable')
                                       and j.get('switcherUsable')):
            bad.append('%dpx preflight judgement %r' % (int(d['viewport'].split('x')[0]), j))
        if d['band'] != 'bar' and not j.get('outOfScopeUnchanged'):
            bad.append('%dpx moved although the rule is out of scope' % int(d['viewport'].split('x')[0]))
    if bad:
        print('\nFAILED:')
        for b in bad:
            print('  %s' % b)
        return 1
    print('\nall judgements pass')
    return 0


if __name__ == '__main__':
    sys.exit(main())

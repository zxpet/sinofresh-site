#!/usr/bin/env python3
"""Batch 3b-2 acceptance on the dev host.

Two groups, both measured through the preflight theme (2.10.78) with the live
theme (2.10.77) read the same way as the before-picture:

  A  the cookie banner and TranslatePress's floating language switcher, which
     both anchor to the bottom edge, at 375 / 768 / 1024 / 1440. The measure is
     not "do the rectangles overlap" alone but "how much of the Manage
     Preferences button still belongs to the button" — sampled along its own
     width with elementFromPoint, which is what made the defect visible in the
     first place (2 of 11 points at 1440). The switcher's own usability is then
     checked by clicking it and reading aria-expanded off the element that
     declares it.

  B  the spec sheet's label column at 1024 / 1280 / 1440, plus two more formula
     pages of different dosage forms. The claims are that every label track is
     the same width, that the values therefore share one x, and that nothing
     overflows the viewport.

Every session asserts WHICH theme it served before it measures anything. A
preflight run that quietly rendered the live bytes would otherwise report a
clean pass for a change it never loaded — the failure this project has hit
before, and the reason the assertion is here rather than in the caller.

Usage:
    python3 tools/b3b2_live_accept.py [--json /tmp/out.json] [--only a|b]
                                      [--shots <dir>]

NOTE — `--shots` exists for the same reason it exists on the h7c E2E: the
default is the directory holding the committed evidence, so a post-pull re-run
would quietly overwrite the BEFORE frames with the AFTER picture and leave the
pair meaningless. Point it at /tmp when re-measuring a site that has already
moved to the candidate.
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
SHOTS = os.path.join(ROOT, 'docs', 'batch3b2-shots')


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


def session(path, preflight, w, h, settle=3.2):
    """One fresh visitor on one URL, with one theme. Asserts which one it got."""
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
    ab('set', 'viewport', str(w), str(h))
    time.sleep(1.3)
    s = ev(SERVED)
    if preflight and not s.get('preflight'):
        raise RuntimeError('asked for the preflight theme, served %r' % s.get('href'))
    if not preflight and s.get('preflight'):
        raise RuntimeError('asked for the live theme, served %r' % s.get('href'))
    return s


def shot_viewport(name):
    out = os.path.join(SHOTS, name)
    ab('screenshot', out)
    return out


def shot_full_crop(name, sel, pad=18):
    """Scroll the band into view, take the full page, crop the band's own rows.

    Cropping the viewport after scrolling is what used to come back blank; the
    full-page frame plus an absolute crop is the shape that survives. Uses PIL,
    so this script runs under the PIL-carrying interpreter.
    """
    from PIL import Image
    ev("(() => { const e = document.querySelector(%s);"
       "if (e) e.scrollIntoView({ block: 'start', behavior: 'instant' }); })()" % json.dumps(sel))
    time.sleep(1.2)
    box = ev("""(() => { const e = document.querySelector(%s);
      if (!e) return null; const b = e.getBoundingClientRect();
      return { y: b.top + scrollY, h: b.height, docH: document.documentElement.scrollHeight }; })()"""
             % json.dumps(sel))
    if not box:
        return None
    full = '/tmp/b3b2-full.png'
    ab('screenshot', '--full', full)
    img = Image.open(full)
    sy = img.height / float(box['docH']) if box['docH'] else 1.0
    top = max(0, int((box['y'] - pad) * sy))
    bot = min(img.height, int((box['y'] + box['h'] + pad) * sy))
    out = os.path.join(SHOTS, name)
    img.crop((0, top, img.width, bot)).save(out)
    return out


# --------------------------------------------------------------- group A ----

A_PROBE = r"""(() => {
  const cb = document.querySelector('.sf-cookie-banner');
  const mg = document.querySelector('.sf-cookie-banner__manage');
  const sw = document.querySelector('.trp-floating-switcher');
  const st = document.querySelector('.sf-float-stack');
  const R = e => { if (!e) return null; const b = e.getBoundingClientRect();
    return { x: Math.round(b.left), y: Math.round(b.top), w: Math.round(b.width),
             h: Math.round(b.height), right: Math.round(b.right), bottom: Math.round(b.bottom) }; };
  const ix = (a, b) => { if (!a || !b) return null;
    const w = Math.max(0, Math.min(a.right, b.right) - Math.max(a.x, b.x));
    const h = Math.max(0, Math.min(a.bottom, b.bottom) - Math.max(a.y, b.y));
    return { w: w, h: h, area: w * h }; };
  const bR = R(cb), mR = R(mg), sR = R(sw), tR = R(st);
  let hits = [];
  if (mg) {
    const b = mg.getBoundingClientRect(), y = Math.round(b.top + b.height / 2);
    for (let i = 0; i <= 10; i++) {
      const x = Math.round(b.left + (b.width - 1) * i / 10);
      const t = document.elementFromPoint(x, y);
      hits.push(!!(t && mg.contains(t)));
    }
  }
  const centre = (() => {
    if (!mg) return null;
    const b = mg.getBoundingClientRect();
    const x = Math.round(b.left + b.width / 2), y = Math.round(b.top + b.height / 2);
    const t = document.elementFromPoint(x, y);
    return { x: x, y: y, self: !!(t && mg.contains(t)),
             tag: t ? t.tagName + '.' + (t.className || '').toString().split(' ')[0] : null }; })();
  // The float stack is measured too: the switcher is lifted past the banner,
  // and the stack is lifted past the same banner, so the two now share a band.
  // What matters is not that the rectangles touch but whether the stack's own
  // buttons still belong to themselves.
  const stk = document.querySelector('.sf-float-stack');
  let stackHits = [];
  if (stk) {
    stackHits = [...stk.querySelectorAll('.sf-float-btn')].map(b => {
      const cs = getComputedStyle(b), bx = b.getBoundingClientRect();
      const cls = (b.className || '').toString().trim();
      if (cs.display === 'none' || bx.width === 0) return { cls: cls, shown: false };
      const y = Math.round(bx.top + bx.height / 2);
      const h = [];
      for (let i = 0; i <= 10; i++) {
        const x = Math.round(bx.left + (bx.width - 1) * i / 10);
        const t = document.elementFromPoint(x, y);
        h.push(!!(t && b.contains(t)));
      }
      return { cls: cls, shown: true,
               rect: { x: Math.round(bx.left), y: Math.round(bx.top),
                       w: Math.round(bx.width), h: Math.round(bx.height) },
               hits: h.filter(Boolean).length, of: h.length,
               sample: h.map(v => v ? '#' : '.').join('') };
    });
  }
  const cur = document.querySelector('.trp-floating-switcher .trp-language-item__current');
  const list = document.querySelector('#trp-switcher-dropdown-list');
  return { path: location.pathname, vw: innerWidth, vh: innerHeight,
           stackHits: stackHits,
           bannerHidden: cb ? cb.hasAttribute('hidden') : null,
           banner: bR, manage: mR, switcher: sR, stack: tR,
           zBanner: cb ? getComputedStyle(cb).zIndex : null,
           zSwitcher: sw ? getComputedStyle(sw).zIndex : null,
           swBottom: sw ? getComputedStyle(sw).bottom : null,
           swRight: sw ? getComputedStyle(sw).right : null,
           ixBannerSwitcher: ix(bR, sR), ixManageSwitcher: ix(mR, sR),
           ixSwitcherStack: ix(sR, tR),
           hits: hits, hitCount: hits.filter(Boolean).length, hitOf: hits.length,
           hitSample: hits.map(v => v ? '#' : '.').join(''),
           centre: centre,
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
           listH: list ? Math.round(list.getBoundingClientRect().height) : null,
           links: list ? [...list.querySelectorAll('a')].map(a => a.getAttribute('href')) : [] }; })()"""


def click_switcher():
    """Real pointer on the switcher, then read the result off its own attributes.

    The hit check asks that the point belong to the switcher's nav, not to the
    chip inside it. The chip is a static child of `.trp-language-switcher-inner`,
    a positioned box, so the parent paints over its own child and
    elementFromPoint answers with the parent — measured, not assumed. Demanding
    the chip itself would fail the switcher for being built the way the plugin
    builds it. What the check is for is that the point belongs to the switcher
    and not to the banner or the float stack underneath it.

    Whether the click worked is a separate question, answered by aria-expanded
    and the dropdown's `hidden` rather than by the hit test.
    """
    box = ev("""(() => {
      const nav = document.querySelector('.trp-floating-switcher');
      const c = nav ? nav.querySelector('.trp-language-item__current') : null;
      if (!nav || !c) return null;
      const b = c.getBoundingClientRect();
      const x = Math.round(b.left + b.width / 2), y = Math.round(b.top + b.height / 2);
      const t = document.elementFromPoint(x, y);
      return { x: x, y: y, ownNav: !!(t && nav.contains(t)), ownChip: !!(t && c.contains(t)),
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


def group_a(out):
    rows = []
    for w, h in ((375, 800), (768, 900), (1024, 900), (1440, 900)):
        for mode in ('live', 'preflight'):
            s = session('/', mode == 'preflight', w, h)
            d = ev(A_PROBE)
            d.update({'mode': mode, 'viewport': '%dx%d' % (w, h), 'served': s['href'], 'ver': s['ver']})
            name = 'a-cookie-%d-%s.png' % (w, mode)
            d['frame'] = shot_viewport(name)
            if mode == 'preflight':
                d['switcherClick'] = click_switcher()
            rows.append(d)
            c = d['centre'] or {}
            print('  A %-4d %-9s banner=%s switcher_bottom=%-6s Manage×sw=%s  Manage %d/%d %s'
                  % (w, mode, (d['banner'] or {}).get('h'), d['swBottom'],
                     (d['ixManageSwitcher'] or {}).get('area'), d['hitCount'], d['hitOf'],
                     d['hitSample']))
            for sh in (d.get('stackHits') or []):
                if sh.get('shown'):
                    print('       stack %-32s %s %d/%d  rect=%s'
                          % (sh['cls'].replace('sf-float-btn ', ''), sh['sample'],
                             sh['hits'], sh['of'], sh.get('rect')))
            if mode == 'preflight':
                sc = d['switcherClick']
                print('       switcher: ok=%s why=%s hit=%s expanded=%s listHidden=%s links=%s'
                      % (sc.get('ok'), sc.get('why'), (sc.get('box') or {}).get('hit'),
                         (sc.get('after') or {}).get('expanded'),
                         (sc.get('after') or {}).get('listHidden'),
                         (sc.get('after') or {}).get('links')))
    out['A'] = rows


# --------------------------------------------------------------- group B ----

B_PROBE = r"""(() => {
  const rows = [...document.querySelectorAll('.sf-fdetail-specs__row')];
  const inner = document.querySelector('.sf-fdetail-specs__inner');
  if (!rows.length) return { missing: true, inner: !!inner };
  const cells = rows.map(r => {
    const t = r.querySelector('.sf-fdetail-specs__term');
    const v = r.querySelector('.sf-fdetail-specs__value');
    if (!t || !v) return null;
    const tr = t.getBoundingClientRect(), vr = v.getBoundingClientRect();
    const rg = document.createRange();
    rg.selectNodeContents(t);
    const q = rg.getBoundingClientRect();
    return { label: t.textContent.trim().slice(0, 24),
             termW: Math.round(tr.width), valueL: Math.round(vr.left),
             termR: Math.round(tr.right), textW: Math.round(q.width),
             textR: Math.round(q.right), gap: Math.round(vr.left - tr.right) };
  }).filter(Boolean);
  const cs = getComputedStyle(rows[0]);
  return { rowTemplate: cs.gridTemplateColumns, rowGap: cs.columnGap,
           innerTemplate: inner ? getComputedStyle(inner).gridTemplateColumns : null,
           rowCount: rows.length, cells: cells,
           docW: document.documentElement.scrollWidth, winW: innerWidth,
           overflow: document.documentElement.scrollWidth > innerWidth + 1 }; })()"""


def group_b(out):
    rows = []
    pages = [('tablets', '/formulas/joint-support-tablets/', (1024, 1280, 1440)),
             ('powder', '/formulas/probiotic-powder/', (1440,)),
             ('chews', '/formulas/joint-support-soft-chews/', (1440,))]
    for tag, path, widths in pages:
        for w in widths:
            for mode in ('live', 'preflight'):
                s = session(path, mode == 'preflight', w, 900)
                d = ev(B_PROBE)
                d.update({'page': tag, 'path': path, 'mode': mode, 'viewport': '%dx%d' % (w, 900),
                          'served': s['href'], 'ver': s['ver']})
                if w == 1440:
                    d['frame'] = shot_full_crop('b-specs-%s-1440-%s.png' % (tag, mode),
                                                '.sf-fdetail-specs')
                rows.append(d)
                cells = d.get('cells') or []
                widths_set = sorted(set(c['termW'] for c in cells))
                vals = sorted(set(c['valueL'] for c in cells))
                gaps = sorted(set(c['gap'] for c in cells))
                print('  B %-8s %-4d %-9s rows=%-3s term 宽=%s  value x=%s  gap=%s  overflow=%s'
                      % (tag, w, mode, d.get('rowCount'), widths_set, vals, gaps, d.get('overflow')))
                if mode == 'preflight' and cells:
                    print('       template=%s' % d.get('rowTemplate'))
    out['B'] = rows


def main():
    global SHOTS
    ap = argparse.ArgumentParser()
    ap.add_argument('--json', default='/tmp/b3b2-accept.json')
    ap.add_argument('--only', choices=['a', 'b'])
    ap.add_argument('--shots', default=SHOTS,
                    help='frame directory; defaults to the committed evidence dir')
    args = ap.parse_args()
    SHOTS = os.path.abspath(args.shots)
    os.makedirs(SHOTS, exist_ok=True)
    out = {'shots': SHOTS}
    try:
        if args.only in (None, 'a'):
            print('== A: cookie banner vs the floating language switcher ==')
            group_a(out)
        if args.only in (None, 'b'):
            print('== B: the spec sheet label column ==')
            group_b(out)
    finally:
        ab('close', '--all')
    json.dump(out, open(args.json, 'w'), indent=1, ensure_ascii=False)
    print('\njson -> %s' % args.json)
    print('frames -> %s' % SHOTS)
    return 0


if __name__ == '__main__':
    sys.exit(main())

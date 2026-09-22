#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H2b1 — live vs pre-flight geometry, side by side.

The E2E assertions have to be *derived from measurement*, not invented. Three of
them were wrong on the first run because the numbers were guessed:

  * `.sf-explore` is `box-sizing: content-box`, so its border box is
    `max-width(1200px) + 2 x 32px` = 1264px while the section around it is
    1440px. Comparing the panel to the section said "not full width" about a
    panel that is exactly where it belongs.
  * the pill row and the wall button each have a `<=768px` branch, so a single
    expected value cannot hold at every width.
  * the vertical rhythm is the *site* block gap (24px) plus the section's own
    48px bottom padding — 72px of whitespace between the last card and the
    panel, at the content edge 48 + 24.

This harness renders the same page twice — once against the LIVE theme and once
with the pre-flight header (candidate) — and prints every quantity the E2E
asserts on, so the assertions can be written as "identical to live" or "changed
exactly this way" instead of as a hard-coded guess.

usage:
    b2d_h2b1_geom.py --out DIR [--auth user:pass]
"""

import argparse
import base64
import json
import os
import subprocess
import sys
import time

HOST = 'https://dev.zxpet.com'
DOSE_EN = '/products/soft-chews/'
DOSE_ZH = '/zh/products/soft-chews/'
DETAIL_EN = '/formulas/calming-soft-chews/'
WIDTHS = [(480, 900), (768, 1000), (1024, 1000), (1100, 1000), (1101, 1000), (1440, 1000)]
# an empty value is how a shell clears the variable, so the geometry passes can
# never accidentally inherit a stub from the caller's environment
NO_INIT = {'AGENT_BROWSER_INIT_SCRIPTS': ''}

MEASURE = r"""
(() => {
  const q = (s) => document.querySelector(s);
  const cs = (e) => e ? getComputedStyle(e) : null;
  const num = (v) => (v === null || v === undefined) ? null : parseFloat(v);
  const rect = (e) => { if (!e) return null; const r = e.getBoundingClientRect();
    return {x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width),
            h: Math.round(r.height), top: Math.round(r.top), bottom: Math.round(r.bottom)}; };
  const band = q('section.sf-explore-band');
  const explore = q('.sf-explore');
  const wall = q('section#formulas');
  const wallH2 = wall ? wall.querySelector('h2') : null;
  const wallBtn = q('#formulas .sf-explore__btn');
  const chip = q('.sf-explore__chip');
  const chips = q('.sf-explore__chips');
  const toc = q('.sf-toc');
  const heroBtn = [...document.querySelectorAll('a.sf-quote-cta')]
      .find(a => /Build Custom Formula/.test(a.textContent)) || null;
  const ws = cs(wall);
  const ex = cs(explore);
  const wallRect = rect(wall);
  const wallPad = wall ? num(ws.paddingBottom) : null;
  const exRect = rect(explore);
  const wallH2Rect = rect(wallH2);
  return JSON.stringify({
    vw: window.innerWidth,
    overflowX: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    sheet: (document.querySelector('link[rel="stylesheet"][href*="sinofresh-theme"]') || {}).href || '',
    band: rect(band), explore: exRect, wall: wallRect, wallH2: wallH2Rect,
    bandSections: document.querySelectorAll('section.sf-explore-band').length,
    bandPad: band ? {l: cs(band).paddingLeft, r: cs(band).paddingRight,
                     t: cs(band).paddingTop, b: cs(band).paddingBottom} : null,
    explorePadL: ex ? ex.paddingLeft : null,
    exploreMarginL: ex ? ex.marginLeft : null,
    exploreBoxSizing: ex ? ex.boxSizing : null,
    exploreMaxW: ex ? ex.maxWidth : null,
    wallPadBottom: wallPad,
    wallContentBottom: (wallRect && wallPad !== null)
        ? Math.round(wallRect.bottom - wallPad) : null,
    gapWallContentToBand: (wallRect && exRect && wallPad !== null)
        ? Math.round(exRect.top - (wallRect.bottom - wallPad)) : null,
    gapWallEdgeToBand: (wallRect && exRect) ? Math.round(exRect.top - wallRect.bottom) : null,
    gutterL: exRect ? exRect.x : null,
    gutterR: (exRect && band) ? Math.round(band.getBoundingClientRect().width
             - (exRect.x + exRect.w)) : null,
    exploreContentX: (exRect && ex) ? Math.round(exRect.x + num(ex.paddingLeft)) : null,
    wallContentX: wallH2Rect ? wallH2Rect.x : null,
    chipCount: document.querySelectorAll('.sf-explore__chip').length,
    chipCurrent: [...document.querySelectorAll('.sf-explore__chip.is-current')]
        .map(a => a.textContent.trim()),
    chipFont: chip ? cs(chip).fontSize : null,
    chipPad: chip ? cs(chip).padding : null,
    chipRadius: chip ? cs(chip).borderRadius : null,
    chipsGap: chips ? cs(chips).gap : null,
    chipsScroll: chips ? chips.scrollWidth - chips.clientWidth : null,
    chipsNowrap: chips ? cs(chips).flexWrap : null,
    bandBtn: wallBtn ? {border: cs(wallBtn).borderWidth + ' ' + cs(wallBtn).borderStyle + ' '
              + cs(wallBtn).borderColor, color: cs(wallBtn).color,
              padding: cs(wallBtn).padding, radius: cs(wallBtn).borderRadius,
              minHeight: cs(wallBtn).minHeight, display: cs(wallBtn).display,
              w: Math.round(wallBtn.getBoundingClientRect().width)} : null,
    heroBtnHref: heroBtn ? heroBtn.getAttribute('href') : null,
    heroBtnClass: heroBtn ? heroBtn.className : null,
    tocPresent: !!toc,
    tocDisplay: toc ? cs(toc).display : null,
    tocLinks: [...document.querySelectorAll('.sf-toc a')].map(a => a.textContent.trim()),
    configuratorLeft: document.querySelectorAll('#configurator, .configurator').length,
    buildH2: [...document.querySelectorAll('h2')]
        .filter(t => /^Build Your /.test(t.textContent.trim())).length
  });
})()
"""


def run(args, timeout=180, env=None):
    e = dict(os.environ)
    e.update(env or {})
    p = subprocess.run(args, capture_output=True, text=True, timeout=timeout, env=e)
    return p.returncode, (p.stdout or '').strip(), (p.stderr or '').strip()


def ev(script, env=None):
    enc = base64.b64encode(script.encode('utf-8')).decode('ascii')
    rc, out, err = run(['agent-browser', 'eval', '-b', enc], env=env)
    if rc != 0:
        raise RuntimeError('eval failed: %s %s' % (out, err))
    first = json.loads(out)
    if isinstance(first, str):
        try:
            return json.loads(first)
        except Exception:
            return first
    return first


NO_HAS_STUB = r"""
(function () {
  window.__stubRan = (window.__stubRan || 0) + 1;
  try {
    var orig = (window.CSS && CSS.supports) ? CSS.supports.bind(CSS) : null;
    window.CSS.supports = function (a, b) {
      if (typeof a === 'string' && a.indexOf('selector(') === 0) { return false; }
      return orig ? orig(a, b) : false;
    };
  } catch (e) { window.__stubErr = String(e); }
})();
"""

FLOAT_PROBE = ("JSON.stringify({nohas:document.documentElement.className.indexOf('no-has')!==-1,"
               "ran:window.__stubRan||0,"
               "float:(()=>{var e=document.querySelector('.sf-float-stack');"
               "return e?getComputedStyle(e).bottom:null;})(),"
               "lang:(()=>{var e=document.querySelector('.trp-language-switcher');"
               "return e?getComputedStyle(e).bottom:null;})(),"
               "banner:!!document.querySelector('.sf-cookie-banner'),"
               "sheet:(document.querySelector('link[rel=\"stylesheet\"]"
               "[href*=\"sinofresh-theme\"]')||{}).href||''})")


def measure_nohas(mode, auth, stub_path):
    """The floating layers at 480px, with and without html.no-has.

    `configurator.css:675-684` lifts the language switcher and the float stack
    above the configurator bar (68px / 132px) and `:700-707` repeat the same two
    offsets unconditionally for engines that cannot evaluate `:has()`. Those
    declarations have the same specificity as style.css's cookie-banner
    calibration, so configurator.css wins on load order and the legacy branch
    silently overrides it. H2b1 removed the bar but this file is still enqueued
    until H2b2, so the pair below is what H2b2 has to reason about.
    """
    user, _, pw = auth.partition(':')
    b64 = base64.b64encode(auth.encode('utf-8')).decode('ascii')
    rows = {}
    for label, stub in (('no-stub', None), ('stub', stub_path)):
        env = {'AGENT_BROWSER_INIT_SCRIPTS': stub} if stub else None
        run(['agent-browser', 'close', '--all'], env=env)
        run(['agent-browser', 'set', 'credentials', user, pw], env=env)
        run(['agent-browser', 'open', HOST + DOSE_EN + '?nohas=' + mode + label], env=env)
        if mode == 'cand':
            run(['agent-browser', 'set', 'headers',
                 json.dumps({'Authorization': 'Basic ' + b64, 'X-SF-Preflight': '1'})], env=env)
        run(['agent-browser', 'reload'], env=env)
        time.sleep(0.9)
        run(['agent-browser', 'set', 'viewport', '480', '900'], env=env)
        time.sleep(0.6)
        got = ev(FLOAT_PROBE, env=env)
        want = '-preflight' if mode == 'cand' else '/sinofresh-theme/'
        bad = ('preflight' not in (got.get('sheet') or '')) if mode == 'cand' \
            else ('preflight' in (got.get('sheet') or ''))
        if bad:
            raise SystemExit('FATAL %s/%s captured the wrong theme: %s'
                             % (mode, label, got.get('sheet')))
        rows[label] = got
    run(['agent-browser', 'close', '--all'])
    return rows


def measure(mode, auth):
    """mode: 'live' (no pre-flight header) or 'cand' (with it)."""
    user, _, pw = auth.partition(':')
    b64 = base64.b64encode(auth.encode('utf-8')).decode('ascii')
    out = {'mode': mode, 'widths': {}}
    run(['agent-browser', 'close', '--all'], env=NO_INIT)
    run(['agent-browser', 'set', 'credentials', user, pw], env=NO_INIT)
    run(['agent-browser', 'open', HOST + DOSE_EN + '?geom=' + mode], env=NO_INIT)
    if mode == 'cand':
        hdrs = json.dumps({'Authorization': 'Basic ' + b64, 'X-SF-Preflight': '1'})
        run(['agent-browser', 'set', 'headers', hdrs], env=NO_INIT)
    run(['agent-browser', 'reload'], env=NO_INIT)
    time.sleep(1.0)
    first = ev(MEASURE, env=NO_INIT)
    if mode == 'cand' and 'preflight' not in (first.get('sheet') or ''):
        raise SystemExit('FATAL candidate capture is the LIVE theme: %s' % first.get('sheet'))
    if mode == 'live' and 'preflight' in (first.get('sheet') or ''):
        raise SystemExit('FATAL live capture got the candidate: %s' % first.get('sheet'))
    for w, h in WIDTHS:
        run(['agent-browser', 'set', 'viewport', str(w), str(h)], env=NO_INIT)
        time.sleep(0.5)
        out['widths'][str(w)] = ev(MEASURE, env=NO_INIT)
    out['zh'] = None
    if mode == 'cand':
        run(['agent-browser', 'open', HOST + DOSE_ZH + '?geom=zh'], env=NO_INIT)
        run(['agent-browser', 'reload'], env=NO_INIT)
        time.sleep(0.8)
        out['zh'] = ev("JSON.stringify({heroHref:(()=>{const a=[...document.querySelectorAll"
                       "('a.sf-quote-cta')].find(x=>/Build Custom Formula/.test(x.textContent));"
                       "return a?a.getAttribute('href'):null;})(),"
                       "sheet:(document.querySelector('link[rel=stylesheet][href*="
                       "\"sinofresh-theme\"]')||{}).href||''})", env=NO_INIT)
    out['detail'] = None
    run(['agent-browser', 'open', HOST + DETAIL_EN + '?geom=detail'], env=NO_INIT)
    run(['agent-browser', 'reload'], env=NO_INIT)
    time.sleep(0.8)
    det = ev("JSON.stringify({sheet:(document.querySelector('link[rel=stylesheet]"
             "[href*=sinofresh-theme]')||{}).href||'',"
             "anchor:(()=>{const a=document.querySelector('a.sf-formula-hero__build');"
             "return a?{href:a.getAttribute('href'),cls:a.className}:null;})(),"
             "configuratorLeft:document.querySelectorAll('#configurator,.configurator').length,"
             "buildH2:[...document.querySelectorAll('h2')]"
             ".filter(t=>/^Build Your /.test(t.textContent.trim())).length})", env=NO_INIT)
    out['detail'] = det
    if mode == 'cand' and 'preflight' not in (det.get('sheet') or ''):
        raise SystemExit('FATAL detail capture is the LIVE theme: %s' % det.get('sheet'))
    run(['agent-browser', 'close', '--all'], env=NO_INIT)
    return out


FIELDS = ['overflowX', 'bandSections', 'gutterL', 'gutterR', 'exploreContentX',
          'wallContentX', 'wallPadBottom', 'wallContentBottom',
          'gapWallContentToBand', 'gapWallEdgeToBand', 'chipCount', 'chipCurrent',
          'chipFont', 'chipPad', 'chipsGap', 'chipsScroll', 'chipsNowrap',
          'tocDisplay', 'configuratorLeft', 'buildH2', 'heroBtnHref']
RECTS = ['band', 'explore', 'wall', 'wallH2']


def fmt(v):
    if isinstance(v, dict):
        return 'x%s w%s h%s' % (v.get('x'), v.get('w'), v.get('h'))
    if isinstance(v, list):
        return ','.join(str(x) for x in v)
    return str(v)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--auth', default=os.environ.get('SF_DEV_AUTH', 'sfdev:VkEws18Kl5V1qp3TpZ6s'))
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    live = measure('live', args.auth)
    cand = measure('cand', args.auth)
    stub = os.path.join(args.out, 'no-has-stub.js')
    with open(stub, 'w', encoding='utf-8') as fh:
        fh.write(NO_HAS_STUB)
    nohas = {'live': measure_nohas('live', args.auth, stub),
             'cand': measure_nohas('cand', args.auth, stub)}
    with open(os.path.join(args.out, 'geom-live-cand.json'), 'w', encoding='utf-8') as fh:
        json.dump({'live': live, 'cand': cand, 'nohas': nohas}, fh,
                  ensure_ascii=False, indent=2)
    print('\nhtml.no-has at 480px (.sf-float-stack / .trp-language-switcher bottom)')
    print('%-10s %-28s %-28s' % ('', 'no stub (modern engine)', 'with stub (legacy)'))
    for m in ('live', 'cand'):
        a = nohas[m]['no-stub']
        b = nohas[m]['stub']
        print('%-10s float=%-8s lang=%-8s   float=%-8s lang=%-8s  nohas=%s/%s ran=%s'
              % (m, a['float'], a['lang'], b['float'], b['lang'],
                 a['nohas'], b['nohas'], b.get('ran')))

    keys = [str(w) for w, _ in WIDTHS]
    print('\n%-26s %-30s %-30s %s' % ('field (per width)', 'LIVE', 'CANDIDATE', 'verdict'))
    print('-' * 104)
    for f in FIELDS + RECTS:
        for k in keys:
            lv = live['widths'][k].get(f)
            cv = cand['widths'][k].get(f)
            verdict = 'same' if lv == cv else ('C H A N G E D' if f not in
                                               ('explore',) else 'changed')
            print('%-12s %-6s %-30s %-30s %s'
                  % (f, k + 'px', fmt(lv)[:30], fmt(cv)[:30], verdict))
        print('-' * 104)
    print('\nbandBtn (per width)')
    for k in keys:
        lv = live['widths'][k].get('bandBtn')
        cv = cand['widths'][k].get('bandBtn')
        print('  %-6s live %s' % (k, lv))
        print('         cand %s   %s' % (cv, 'same' if lv == cv else 'CHANGED'))
    print('\nband width vs viewport (candidate should be full bleed)')
    for k in keys:
        c = cand['widths'][k]
        print('  %-6s band x%s w%s   vw %s   explore x%s w%s  pad%s/%s  box %s'
              % (k, (c['band'] or {}).get('x'), (c['band'] or {}).get('w'), c['vw'],
                 (c['explore'] or {}).get('x'), (c['explore'] or {}).get('w'),
                 c['explorePadL'], (c['bandPad'] or {}).get('r'), c['exploreBoxSizing']))
    print('\nlive: was there a band at all?')
    for k in keys:
        l = live['widths'][k]
        print('  %-6s band %s   explore %s   wallPadB %s  cfgLeft %s'
              % (k, l['band'], l['explore'], l['wallPadBottom'], l['configuratorLeft']))
    print('\nzh / detail')
    print('  live zh %s' % live['zh'])
    print('  cand zh %s' % cand['zh'])
    print('  live detail %s' % live['detail'])
    print('  cand detail %s' % cand['detail'])
    print('\n-> %s' % os.path.join(args.out, 'geom-live-cand.json'))
    return 0


if __name__ == '__main__':
    sys.exit(main())

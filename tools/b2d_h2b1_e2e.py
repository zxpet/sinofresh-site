#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H2b1 — the browser end-to-end pass (E1-E9).

Driven from Python, sequentially, for the two reasons this project already
paid for: a shell loop with command substitution drifts between iterations (the
eval target silently moves), and `set headers` / `set credentials` each rebuild
the browser context, so this is the only order that keeps a custom header
attached to the right origin:

    close --all -> set credentials -> open <origin>
                -> set headers{Authorization + X-SF-Preflight} -> errors --clear
                -> open <url> -> reload -> set viewport -> eval/screenshot

`set credentials` is NOT reused after that: it would wipe the pre-flight header,
and without the header every capture would be the LIVE theme while looking
perfectly normal. The provenance assertion below is what makes that impossible
to miss — a stylesheet URL without `-preflight` aborts the run.

Geometry, not screenshots, is the evidence. An element taller than the viewport
is painted blank in a screenshot (it reads as "the band is missing"), and the
consent banner sits over the bottom of the page; both have produced a false
alarm in this project before. Every claim below is a `getBoundingClientRect`
number first, with a screenshot as corroboration only, taken at a raised
viewport so the whole element fits. And in agent-browser 0.27.0 the selector
form `screenshot <sel> <path>` writes a blank image — 1.7 KB of white for a
1440x259 section — so the shots here are scrolled viewport captures, with a
byte-size floor that turns a blank capture into a failure rather than an
artifact nobody looks at twice.

Every expected value here is a measured value. The first run of this script had
three assertions that were *guessed* and therefore wrong — it compared a
`content-box` panel (1264px = 1200 + 2x32) to the full-width section around it,
demanded one button padding at all widths when the mobile branch differs, and
demanded a 48px gap where the site uses 48 + 24. tools/b2d_h2b1_geom.py renders
live and candidate side by side at all six widths and prints both columns; the
numbers asserted below are read from it, and the comment on each says whether
the value is a declared change or has to equal the live baseline.

The no-JS contract is proven on the served bytes rather than by disabling
script, because the contract is "the anchor's href is right", not "the page
works without script": quote-cta.js only upgrades an in-page form into a smooth
scroll, so with script off the anchor navigates natively — which the href
attribute decides. The attribute is read from the raw HTML (curl) and from the
DOM, and both are required to be the declared value.

The legacy-engine branch (E8) is the one place an init script is needed: the
theme's `html.no-has` probe runs at wp_head priority 1, so stubbing
CSS.supports afterwards would be too late. agent-browser 0.27.0 has no
`addinitscript` subcommand even though its own bundled docs advertise one, and
`--init-script`/`AGENT_BROWSER_INIT_SCRIPTS` only take effect on the process
that *boots* the browser — which here is `set credentials`, one command before
the `open` the flag used to be attached to. The env var therefore goes on every
invocation from the very first one. The stub is narrow (it only lies about
`selector(...)`) and carries a sentinel, so "the script ran" and "the probe saw
it" stay separate answers; the run is paired with a positive control that must
NOT carry the class.

usage:
    b2d_h2b1_e2e.py --out DIR [--auth user:pass]
"""

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import time

VIEWPORTS = [(480, 900), (768, 1000), (1024, 1000), (1100, 1000), (1101, 1000), (1440, 1000)]
DOSE_EN = '/products/soft-chews/'
DOSE_ZH = '/zh/products/soft-chews/'
DETAIL_EN = '/formulas/calming-soft-chews/'
HOST = 'https://dev.zxpet.com'

# ---- values read off tools/b2d_h2b1_geom.py (live | candidate) ----------------
# declared changes
WANT_CHIP_FONT = '14px'          # live 13px
WANT_CHIP_PAD = '10px 16px'      # live 8px 12px
WANT_CHIPS_GAP = '8px'           # live 6px
WANT_TOC = ['Standard Formulas', 'How We Work', 'Frequently Asked Questions',
            'Related Dosage Forms', 'Request a Soft Chews Quote']   # live had 6
# unchanged from live, and must stay that way
WANT_BTN_BORDER = '2px solid rgb(27, 77, 62)'
WANT_BTN_COLOR = 'rgb(27, 77, 62)'
WANT_BTN_RADIUS = '6px'
WANT_BLOCK_GAP = 24              # the site's 24px block gap, live and candidate

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
  const bandRect = rect(band), exRect = rect(explore), wallRect = rect(wall);
  const ex = cs(explore);
  const wallPad = wall ? num(cs(wall).paddingBottom) : null;
  return JSON.stringify({
    vw: window.innerWidth,
    overflowX: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    bodyOverflowX: document.body.scrollWidth - document.body.clientWidth,
    sheet: (document.querySelector('link[rel="stylesheet"][href*="sinofresh-theme"]') || {}).href || '',
    stubRan: window.__stubRan || 0,
    hasNoHas: document.documentElement.className.indexOf('no-has') !== -1,
    band: bandRect, explore: exRect, wall: wallRect, wallH2: rect(wallH2),
    bandSections: document.querySelectorAll('section.sf-explore-band').length,
    gutterL: exRect ? exRect.x : null,
    gutterR: (exRect && bandRect) ? Math.round(bandRect.w - (exRect.x + exRect.w)) : null,
    exploreContentX: (exRect && ex) ? Math.round(exRect.x + num(ex.paddingLeft)) : null,
    wallContentX: wallH2 ? Math.round(wallH2.getBoundingClientRect().x) : null,
    wallPadBottom: wallPad,
    wallContentBottom: (wallRect && wallPad !== null)
        ? Math.round(wallRect.bottom - wallPad) : null,
    gapWallContentToBand: (wallRect && exRect && wallPad !== null)
        ? Math.round(exRect.top - (wallRect.bottom - wallPad)) : null,
    gapWallEdgeToBand: (wallRect && exRect) ? Math.round(exRect.top - wallRect.bottom) : null,
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
              minHeight: cs(wallBtn).minHeight, display: cs(wallBtn).display} : null,
    heroBtnHref: heroBtn ? heroBtn.getAttribute('href') : null,
    heroBtnClass: heroBtn ? heroBtn.className : null,
    tocPresent: !!toc,
    tocDisplay: toc ? cs(toc).display : null,
    tocLinks: [...document.querySelectorAll('.sf-toc a')].map(a => a.textContent.trim()),
    configuratorLeft: document.querySelectorAll('#configurator, .configurator').length,
    buildH2: [...document.querySelectorAll('h2')]
        .filter(t => /^Build Your /.test(t.textContent.trim())).length,
    invalidation: document.querySelectorAll('section#inquiry-form').length,
    floatStackBottom: q('.sf-float-stack') ? cs(q('.sf-float-stack')).bottom : null,
    langSwitcherBottom: q('.trp-language-switcher')
        ? cs(q('.trp-language-switcher')).bottom : null
  });
})()
"""

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


def run(args, timeout=180, env=None):
    e = dict(os.environ)
    e.update(env or {})
    p = subprocess.run(args, capture_output=True, text=True, timeout=timeout, env=e)
    return p.returncode, (p.stdout or '').strip(), (p.stderr or '').strip()


def ev(script, timeout=180, env=None):
    enc = base64.b64encode(script.encode('utf-8')).decode('ascii')
    rc, out, err = run(['agent-browser', 'eval', '-b', enc], timeout, env)
    if rc != 0:
        raise RuntimeError('eval failed: %s %s' % (out, err))
    # agent-browser prints the result as a JSON string literal and the payload is
    # itself JSON, so it takes two parses; one leaves a str and the next .get()
    # fails far away from the cause.
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


def curl(path, auth, header=None):
    cmd = ['curl', '-s', '--user', auth, HOST + path]
    if header:
        cmd[1:1] = ['-H', header]
    return subprocess.run(cmd, capture_output=True, text=True).stdout


class E2E(object):
    def __init__(self, args):
        self.args = args
        self.fails = []
        self.notes = []
        self.rows = {}
        self.env = None

    def fail(self, msg):
        self.fails.append(msg)
        print('   FAIL %s' % msg)

    def ok(self, msg):
        self.notes.append(msg)
        print('   ok   %s' % msg)

    # ---------------------------------------------------------------- setup
    def attach(self, init_script=None):
        """Boot a browser.

        The init script has to be in the environment of the command that LAUNCHES
        the browser, and that command is `set credentials` — `close --all` only
        tears down the previous one. Attaching `--init-script` to the later `open`
        registers it too late and the script silently never runs, which is exactly
        how the first E8 run produced a false "the stub did not take effect".
        """
        b64 = base64.b64encode(self.args.auth.encode('utf-8')).decode('ascii')
        env = {'AGENT_BROWSER_INIT_SCRIPTS': init_script} if init_script else None
        self.env = env
        run(['agent-browser', 'close', '--all'], env=env)
        user, _, pw = self.args.auth.partition(':')
        rc, out, err = run(['agent-browser', 'set', 'credentials', user, pw], env=env)
        if rc != 0:
            raise SystemExit('FATAL set credentials: %s %s' % (out, err))
        rc, out, err = run(['agent-browser', 'open', HOST + '/'], env=env)
        if rc != 0:
            raise SystemExit('FATAL open: %s %s' % (out, err))
        hdrs = json.dumps({'Authorization': 'Basic ' + b64, 'X-SF-Preflight': '1'})
        run(['agent-browser', 'set', 'headers', hdrs], env=env)
        run(['agent-browser', 'errors', '--clear'], env=env)

    def goto(self, path, expect_preflight=True):
        url = HOST + path + '?sfcap=h2b1' + time.strftime('%H%M%S')
        run(['agent-browser', 'open', url], env=self.env)
        run(['agent-browser', 'reload'], env=self.env)
        time.sleep(0.7)
        probe = ev(MEASURE, env=self.env)
        if expect_preflight and 'preflight' not in (probe.get('sheet') or ''):
            raise SystemExit('FATAL the pre-flight header did not attach — that is the LIVE theme: %s'
                             % probe.get('sheet'))
        return probe

    def accept_banner(self):
        ev("(function(){var b=document.querySelector('.sf-cookie-banner "
           ".sf-cookie-banner__btn');if(b){b.click();return 'clicked';}return 'none';})()",
           env=self.env)
        time.sleep(0.8)
        gone = ev("!!document.querySelector('.sf-cookie-banner')", env=self.env)
        if gone:
            ev("(function(){var b=document.querySelector('.sf-cookie-banner');"
               "if(b)b.style.display='none';return 'hidden';})()", env=self.env)
            self.ok('consent banner still present after Accept All -> hidden for the shots')
        else:
            self.ok('consent banner accepted')

    def settle(self, tries=24, gap=0.25):
        """Wait for the smooth scroll to stop moving.

        Sampling a fixed 1.2s after the click is how E4 first reported "the form
        is 177px off the top": the animation had not finished, and nothing about
        the page had actually changed. Two consecutive identical `scrollY`
        readings are the settle condition; the timeout returns the last reading so
        a genuinely stuck page still fails on the assertion rather than hanging.
        """
        last, same = None, 0
        for _ in range(tries):
            time.sleep(gap)
            p = ev("JSON.stringify({y:Math.round(window.scrollY),"
                   "top:(document.querySelector('#inquiry-form')"
                   "?Math.round(document.querySelector('#inquiry-form')"
                   ".getBoundingClientRect().top):null),"
                   "margin:(document.querySelector('#inquiry-form')"
                   "?getComputedStyle(document.querySelector('#inquiry-form'))"
                   ".scrollMarginTop:null),hash:location.hash})", env=self.env)
            y = (p or {}).get('y')
            if last is not None and y == last:
                same += 1
                if same >= 2:
                    return p
            else:
                same = 0
            last = y
        return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--auth', default=os.environ.get('SF_DEV_AUTH', 'sfdev:VkEws18Kl5V1qp3TpZ6s'))
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    e = E2E(args)

    try:
        e.attach()
        print('--- E1/E2/E3/E6/E7  dosage page %s at six widths ---' % DOSE_EN)
        probe = e.goto(DOSE_EN)
        e.ok('provenance: stylesheet %s' % probe['sheet'])
        e.ok('provenance: cells left from the configurator = %d, Build Your h2 = %d'
             % (probe['configuratorLeft'], probe['buildH2']))
        e.accept_banner()

        widths = []
        for w, h in VIEWPORTS:
            run(['agent-browser', 'set', 'viewport', str(w), str(h)], env=e.env)
            time.sleep(0.6)
            m = ev(MEASURE, env=e.env)
            widths.append(m)
            print('   %4dpx  overflow=%d  band x%s w%s  explore x%s w%s  gutter %s/%s  '
                  'toc=%s  wallPadB=%s'
                  % (w, m['overflowX'], (m['band'] or {}).get('x'), (m['band'] or {}).get('w'),
                     (m['explore'] or {}).get('x'), (m['explore'] or {}).get('w'),
                     m['gutterL'], m['gutterR'], m['tocDisplay'], m['wallPadBottom']))
            if m['overflowX'] > 1 or m['bodyOverflowX'] > 1:
                e.fail('E1 %dpx: horizontal overflow %d/%d'
                       % (w, m['overflowX'], m['bodyOverflowX']))
            if m['bandSections'] != 1:
                e.fail('E1 %dpx: band sections = %d' % (w, m['bandSections']))
        e.rows['widths'] = widths
        if not [f for f in e.fails if f.startswith('E1')]:
            e.ok('E1 zero horizontal overflow and exactly one band at all six widths '
                 '(480/768/1024/1100/1101/1440)')

        # ---- E3: the band is full bleed, and the pills are back at the 14px scale
        for m in widths:
            b = m['band'] or {}
            if b.get('x') != 0 or abs((b.get('w') or 0) - m['vw']) > 1:
                e.fail('E3 %dpx: the band is x%s w%s — it must span the viewport; on live the '
                       'panel was boxed inside a 754px options column'
                       % (m['vw'], b.get('x'), b.get('w')))
            if m['gutterL'] is None or abs(m['gutterL'] - m['gutterR']) > 1:
                e.fail('E3 %dpx: the panel is not centred in the band (gutters %s / %s)'
                       % (m['vw'], m['gutterL'], m['gutterR']))
            if m['chipFont'] != WANT_CHIP_FONT or m['chipPad'] != WANT_CHIP_PAD:
                e.fail('E3 %dpx: chip font/padding = %s / %s (want %s / %s, live was 13px / '
                       '8px 12px)' % (m['vw'], m['chipFont'], m['chipPad'],
                                      WANT_CHIP_FONT, WANT_CHIP_PAD))
            if m['chipsGap'] != WANT_CHIPS_GAP:
                e.fail('E3 %dpx: chips gap = %s (want %s, live was 6px)'
                       % (m['vw'], m['chipsGap'], WANT_CHIPS_GAP))
            if m['chipCount'] != 8:
                e.fail('E3 %dpx: %d pills, expected 8' % (m['vw'], m['chipCount']))
            if m['chipCurrent'] != ['Soft Chews']:
                e.fail('E3 %dpx: is-current = %s, expected the current dosage form'
                       % (m['vw'], m['chipCurrent']))
            if m['vw'] <= 768:
                if m['chipsNowrap'] != 'nowrap' or not (m['chipsScroll'] or 0) > 0:
                    e.fail('E3 %dpx: the pill row must stay one swipeable row (wrap %s, scroll %s)'
                           % (m['vw'], m['chipsNowrap'], m['chipsScroll']))
            else:
                if m['chipsNowrap'] != 'wrap' or m['chipsScroll'] != 0:
                    e.fail('E3 %dpx: the pills must wrap with no horizontal scroll (wrap %s, '
                           'scroll %s)' % (m['vw'], m['chipsNowrap'], m['chipsScroll']))
        if not [f for f in e.fails if f.startswith('E3')]:
            e.ok('E3 the band is full bleed with the panel centred (gutters equal at every '
                 'width), eight pills at the 14px / 10px 16px / 8px scale, is-current on Soft '
                 'Chews, one swipeable row below 769px and a wrapping row above')
        if not [f for f in e.fails if f.startswith('E1') or f.startswith('E3')]:
            e.ok('E3 the panel content column now lands on the wall content column at 1440px '
                 '(x%s vs x%s); below that the panel edge does, because `.sf-explore` is '
                 'content-box, so its 32px padding sits outside the 1200px max-width'
                 % (widths[-1]['exploreContentX'], widths[-1]['wallContentX']))

        # ---- E2: the dot rail lost exactly one entry
        wide = [m for m in widths if m['vw'] >= 1101]
        for m in wide:
            if not m['tocPresent'] or m['tocDisplay'] == 'none':
                e.fail('E2 %dpx: the dot rail is hidden' % m['vw'])
            elif m['tocLinks'] != WANT_TOC:
                e.fail('E2 %dpx: the dot rail lists %s, expected %s'
                       % (m['vw'], m['tocLinks'], WANT_TOC))
        for m in [x for x in widths if x['vw'] <= 1100]:
            if m['tocPresent'] and m['tocDisplay'] != 'none':
                e.fail('E2 %dpx: the dot rail is visible below 1101px' % m['vw'])
        if not [f for f in e.fails if f.startswith('E2')]:
            e.ok('E2 dot rail: 5 entries (live had 6 — "Build Your Soft Chews Formula" left '
                 'with the configurator), entry 2 = How We Work, hidden at <=1100px')

        # ---- E6: the card wall button is untouched, including its mobile branch
        for m in widths:
            b = m['bandBtn'] or {}
            want_pad = '12px 18px' if m['vw'] <= 768 else '12px 24px'
            want_disp = 'block' if m['vw'] <= 768 else 'inline-block'
            want_min_h = '44px' if m['vw'] <= 768 else '0px'
            if b.get('border') != WANT_BTN_BORDER or b.get('color') != WANT_BTN_COLOR \
                    or b.get('radius') != WANT_BTN_RADIUS or b.get('padding') != want_pad \
                    or b.get('display') != want_disp or b.get('minHeight') != want_min_h:
                e.fail('E6 %dpx: the card wall button computes %s, expected padding %s / '
                       'display %s / min-height %s and the same outline'
                       % (m['vw'], b, want_pad, want_disp, want_min_h))
        if not [f for f in e.fails if f.startswith('E6')]:
            e.ok('E6 "Browse All Formulas" keeps its outline and both of its branches — the '
                 'values are identical to the live baseline at every width '
                 '(12px 18px block 44px below 769px, 12px 24px inline-block above)')

        # ---- E7: the mobile padding compensation is repaid
        for m in widths:
            if m['wallPadBottom'] != 48 or m['gapWallContentToBand'] != 72 \
                    or m['gapWallEdgeToBand'] != WANT_BLOCK_GAP:
                e.fail('E7 %dpx: wall padding-bottom %s, gap to the band %s (edge) / %s '
                       '(content); want 48 / %s / 72'
                       % (m['vw'], m['wallPadBottom'], m['gapWallEdgeToBand'],
                          m['gapWallContentToBand'], WANT_BLOCK_GAP))
        if not [f for f in e.fails if f.startswith('E7')]:
            e.ok('E7 the compensation is repaid: the card wall holds its 48px bottom padding at '
                 'every width (live forced it to 0 below 769px) and the band starts exactly one '
                 'site block gap below it — 24px from the edge, 72px from the last card, the '
                 'same rhythm as live')
        e.rows['rhythm'] = [{'vw': m['vw'], 'wallPadBottom': m['wallPadBottom'],
                             'gapWallEdgeToBand': m['gapWallEdgeToBand'],
                             'gapWallContentToBand': m['gapWallContentToBand']}
                            for m in widths]

        # ---- E4: the hero CTA is a smart scroll, not a dead link ----
        print('--- E4  hero CTA behaviour ---')
        run(['agent-browser', 'set', 'viewport', '1440', '1000'], env=e.env)
        run(['agent-browser', 'open', HOST + DOSE_EN + '?sfcap=h2b1click' + time.strftime('%H%M%S')],
            env=e.env)
        run(['agent-browser', 'reload'], env=e.env)
        time.sleep(0.8)
        ev("(function(){var b=document.querySelector('.sf-cookie-banner .sf-cookie-banner__btn');"
           "if(b)b.click();return 1;})()", env=e.env)
        time.sleep(0.5)
        before = ev("(function(){var a=[...document.querySelectorAll('a.sf-quote-cta')]"
                    ".find(x=>/Build Custom Formula/.test(x.textContent));"
                    "return JSON.stringify({href:a?a.getAttribute('href'):null,"
                    "cls:a?a.className:null,hash:location.hash,"
                    "y:Math.round(window.scrollY)});})()", env=e.env)
        print('   before: %s' % before)
        run(['agent-browser', 'click', 'a.sf-quote-cta:nth-of-type(1)'], env=e.env)
        # click by text is unreliable; fall back to a synthetic click on the anchor
        ev("(function(){var a=[...document.querySelectorAll('a.sf-quote-cta')]"
           ".find(x=>/Build Custom Formula/.test(x.textContent));if(a)a.click();return 1;})()",
           env=e.env)
        clicked = e.settle()
        print('   after:  %s' % clicked)
        if before and before.get('href') != '/contact/#quote':
            e.fail('E4 the hero CTA href is %r, expected /contact/#quote' % before.get('href'))
        if 'sf-quote-cta' not in (before or {}).get('cls', ''):
            e.fail('E4 the hero CTA lost the sf-quote-cta class: %r' % before.get('cls'))
        margin = (clicked or {}).get('margin')
        margin = float(margin[:-2]) if isinstance(margin, str) and margin.endswith('px') else None
        if 'inquiry-form' not in (clicked or {}).get('hash', ''):
            e.fail('E4 the hero CTA did not scroll to #inquiry-form (hash=%s)'
                   % (clicked or {}).get('hash'))
        elif margin is None:
            e.fail('E4 #inquiry-form has no scroll-margin-top, so the sticky header will cover '
                   'its heading')
        elif abs(((clicked or {}).get('top') or 9999) - margin) > 4:
            e.fail('E4 the hash is right but #inquiry-form settled at %spx against a '
                   'scroll-margin-top of %spx — the scroll did not come to rest on the anchor'
                   % ((clicked or {}).get('top'), margin))
        else:
            e.ok('E4 the hero CTA smooth-scrolled to this page\'s #inquiry-form and came to '
                 'rest on its scroll-margin-top (hash=%s, form top %spx vs margin %spx, '
                 'href=%s, class carries sf-quote-cta) — live pointed the same anchor at '
                 '#configurator'
                 % (clicked.get('hash'), clicked.get('top'), margin, before.get('href')))

        # ---- E5: the no-JS contract lives in the href attribute ----
        print('--- E5  no-JS contract (the href attribute decides) ---')
        raw = curl(DOSE_EN, args.auth, 'X-SF-Preflight: 1')
        m = re.search(r'<a class="[^"]*sf-quote-cta[^"]*" href="([^"]*)">Build Custom Formula</a>',
                      raw)
        if not m or m.group(1) != '/contact/#quote':
            e.fail('E5 dose en raw href = %r' % (m.group(1) if m else None))
        raw_zh = curl(DOSE_ZH, args.auth, 'X-SF-Preflight: 1')
        mz = re.search(r'<a class="[^"]*sf-quote-cta[^"]*" href="([^"]*)">Build Custom Formula</a>',
                       raw_zh)
        if not mz or mz.group(1) != '/zh/contact/#quote':
            e.fail('E5 dose zh raw href = %r (TranslatePress rewrites the language root)'
                   % (mz.group(1) if mz else None))
        # the detail page has no in-page form, so the same anchor must navigate
        probe2 = e.goto(DETAIL_EN)
        e.ok('detail page provenance: %s' % probe2['sheet'])
        det_before = ev("(function(){var a=document.querySelector('a.sf-formula-hero__build');"
                        "return JSON.stringify({href:a?a.getAttribute('href'):null,"
                        "cls:a?a.className:null});})()", env=e.env)
        print('   detail hero anchor: %s' % det_before)
        if (det_before or {}).get('href') != '/contact/#quote':
            e.fail('E5 detail hero href = %r' % (det_before or {}).get('href'))
        run(['agent-browser', 'click', 'a.sf-formula-hero__build'], env=e.env)
        time.sleep(2.0)
        landed = ev("JSON.stringify({url:location.pathname+location.hash,"
                    "inquiry:document.querySelectorAll('#inquiry-form,form').length})", env=e.env)
        print('   after click: %s' % landed)
        if '/contact/' not in (landed or {}).get('url', ''):
            e.fail('E5 the detail hero CTA did not land on /contact/ (%s)'
                   % (landed or {}).get('url'))
        else:
            e.ok('E5 no-JS contract: dose href %s (en) / %s (zh) and the detail anchor navigates '
                 'natively to %s (live sent it to /products/soft-chews/#configurator)'
                 % (m.group(1), mz.group(1) if mz else '?', (landed or {}).get('url')))

        # ---- E8: the legacy-engine branch ----
        print('--- E8  legacy-engine branch (html.no-has) ---')
        stub = os.path.join(args.out, 'no-has-stub.js')
        with open(stub, 'w', encoding='utf-8') as fh:
            fh.write(NO_HAS_STUB)
        e.attach()
        e.goto(DOSE_EN)
        run(['agent-browser', 'set', 'viewport', '480', '900'], env=e.env)
        time.sleep(0.6)
        neg = ev(MEASURE, env=e.env)
        print('   negative control (no stub, 480px): stubRan=%s no-has=%s float=%s lang=%s'
              % (neg['stubRan'], neg['hasNoHas'], neg['floatStackBottom'],
                 neg['langSwitcherBottom']))
        if neg['stubRan']:
            e.fail('E8 negative control: the init script leaked into the un-stubbed run')
        if neg['hasNoHas']:
            e.fail('E8 negative control: html.no-has appeared without the stub')
        # the whole browser is torn down and re-booted with the stub in the
        # environment, because the probe runs before any later hook could lie to it
        e.attach(init_script=stub)
        e.goto(DOSE_EN)
        run(['agent-browser', 'set', 'viewport', '480', '900'], env=e.env)
        time.sleep(0.6)
        pos = ev(MEASURE, env=e.env)
        print('   with stub (480px): stubRan=%s no-has=%s float=%s lang=%s'
              % (pos['stubRan'], pos['hasNoHas'], pos['floatStackBottom'],
                 pos['langSwitcherBottom']))
        if not pos['stubRan']:
            e.fail('E8 positive control: the init script never ran (agent-browser is not '
                   'registering AGENT_BROWSER_INIT_SCRIPTS on the process that boots the browser)')
        elif not pos['hasNoHas']:
            e.fail('E8 positive control: the stub ran but html.no-has is absent')
        else:
            e.ok('E8 html.no-has appears only when CSS.supports refuses selector(): negative '
                 'control %s / with stub %s (stub ran %d time(s))'
                 % (neg['hasNoHas'], pos['hasNoHas'], pos['stubRan']))
            e.ok('E8 H2b2 baseline under html.no-has at 480px: .sf-float-stack bottom=%s, '
                 '.trp-language-switcher bottom=%s — after configurator.css is deleted these '
                 'must come back to the same values'
                 % (pos['floatStackBottom'], pos['langSwitcherBottom']))
        e.rows['nohas'] = {'negative': neg, 'positive': pos}

        # ---- E9: screenshots at a raised viewport ----
        #
        # `agent-browser screenshot <selector> <path>` writes a blank image here
        # (1.7 KB of white for a 1440x259 section) — the same class of trap this
        # project already recorded: the file exists, it looks like evidence, and it
        # shows nothing. A scrolled viewport screenshot is real, and a byte-size
        # floor turns "blank capture" into a failure instead of an artifact nobody
        # re-checks. The sticky header is measured and compensated, or it crops the
        # band's own heading out of the frame.
        print('--- E9  corroborating screenshots ---')
        e.attach()
        e.goto(DOSE_EN)
        e.accept_banner()
        # measured in the page, once the scrolling has actually started: the mobile
        # header is `position: static` until a scroll handler sticks it, so the
        # offset is 0 at scrollY=0 and the band's heading gets cropped if you take
        # the reading before scrolling. Two passes: coarse scroll, then correct by
        # whatever chrome is really covering the top.
        CHROME = ("(function(){var off=0,els=document.querySelectorAll('body *');"
                  "for(var i=0;i<els.length;i++){var s=getComputedStyle(els[i]);"
                  "if(s.position!=='sticky'&&s.position!=='fixed')continue;"
                  "var r=els[i].getBoundingClientRect();"
                  "if(!r.height||!r.width)continue;"
                  "if(r.height>window.innerHeight*0.25)continue;"
                  "if(r.top>window.innerHeight*0.25)continue;"
                  "if(r.bottom>off)off=r.bottom;}"
                  "var b=document.querySelector('section.sf-explore-band');"
                  "return JSON.stringify({off:Math.round(off),"
                  "top:b?Math.round(b.getBoundingClientRect().top):null,"
                  "h:b?Math.round(b.getBoundingClientRect().height):null,"
                  "vw:window.innerWidth,vh:window.innerHeight});})()")
        shots = []
        for w, _ in VIEWPORTS:
            m = ev(MEASURE, env=e.env)
            band_h = (m['band'] or {}).get('h') or 600
            run(['agent-browser', 'set', 'viewport', str(w), str(int(band_h) + 240)], env=e.env)
            time.sleep(0.5)
            ev("(function(){var b=document.querySelector('section.sf-explore-band');"
               "if(!b)return 0;window.scrollTo(0,"
               "b.getBoundingClientRect().top+window.scrollY-100);return 1;})()", env=e.env)
            time.sleep(0.6)
            coarse = ev(CHROME, env=e.env)
            ev("(function(){var b=document.querySelector('section.sf-explore-band');"
               "if(!b)return 0;var off=%d;var d=b.getBoundingClientRect().top-(off+16);"
               "window.scrollBy(0,d);return Math.round(d);})()" % (coarse or {}).get('off', 0),
               env=e.env)
            time.sleep(0.6)
            frame = ev(CHROME, env=e.env)
            path = os.path.join(args.out, 'band-%d.png' % w)
            run(['agent-browser', 'screenshot', path], env=e.env)
            size = os.path.getsize(path) if os.path.exists(path) else 0
            print('   %4dpx  chrome %s  band top %s h %s in a %sx%s frame -> %d bytes'
                  % (w, (frame or {}).get('off'), (frame or {}).get('top'),
                     (frame or {}).get('h'), (frame or {}).get('vw'), (frame or {}).get('vh'),
                     size))
            if size < 12000:
                e.fail('E9 %dpx: the screenshot is %d bytes — that is a blank capture'
                       % (w, size))
            top, off = (frame or {}).get('top'), (frame or {}).get('off')
            if top is None or off is None:
                e.fail('E9 %dpx: the band is not in the document' % w)
            elif top < off:
                e.fail('E9 %dpx: the band starts at y=%s under %spx of sticky chrome — its '
                       'heading is cropped' % (w, top, off))
            elif top > off + 80:
                e.fail('E9 %dpx: the band starts at y=%s, %spx below the chrome — not framed'
                       % (w, top, top - off))
            shots.append({'vw': w, 'chromeBottom': off, 'bandTop': top,
                          'bandH': (frame or {}).get('h'), 'bytes': size})
        e.rows['shots'] = shots
        if not [f for f in e.fails if f.startswith('E9')]:
            e.ok('E9 six real screenshots (%d-%d KB, the band framed clear of the sticky chrome '
                 'at every width), taken at a raised viewport so nothing is painted blank; '
                 'geometry above remains the evidence'
                 % (min(s['bytes'] for s in shots) // 1024,
                    max(s['bytes'] for s in shots) // 1024))

    finally:
        run(['agent-browser', 'close', '--all'], env=e.env)

    print('\n' + '=' * 72)
    if e.fails:
        print('E2E FAILURES: %d' % len(e.fails))
        for f in e.fails:
            print('   ' + f)
    else:
        print('E2E: E1-E9 all pass')
    with open(os.path.join(args.out, 'e2e.json'), 'w', encoding='utf-8') as fh:
        json.dump({'fails': e.fails, 'notes': e.notes, 'rows': e.rows},
                  fh, ensure_ascii=False, indent=2, default=str)
    return 1 if e.fails else 0


if __name__ == '__main__':
    sys.exit(main())

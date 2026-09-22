#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H2b2 — the browser end-to-end pass (E1-E6).

Same launch discipline as H2b1's pass, for the same measured reasons: a shell
loop drifts between iterations, `set headers` and `set credentials` each rebuild
the browser context, and the `AGENT_BROWSER_INIT_SCRIPTS` / `--init-script`
mechanism only takes effect on the command that *boots* the browser — which is
`set credentials`, not `open`. So the only workable order is

    close --all -> set credentials (init script in env) -> open <origin>
                -> set headers{Authorization + X-SF-Preflight} -> errors --clear
                -> open <url> -> reload -> set viewport -> eval/screenshot

and the env var rides along on every call from the first one.

What is new here, and why:

E3  H2b1 left `configurator.js` enqueued but *inert*: its first statement is
    `var root = document.querySelector('.configurator'); if (!root) return;`
    and H2b1 deleted `.configurator` from the DOM. So this batch's claim is not
    "the page looks the same" but "the script cannot do anything", and that is
    provable directly: inject the baseline's own configurator.js into the
    candidate page and compare fingerprints. It runs top-level (measured: it is
    a bare IIFE, not a DOMContentLoaded handler), so it really does execute and
    really does return at line 17. A sentinel line in front of the injected
    bytes separates "the injection ran" from "the injection did nothing".

E4  H2b1 measured a four-cell table for the two fixed layers and left one
    planned change unadjudicated: `configurator.css:700/705` carried
    *unconditional* `html.no-has` replicas, so legacy engines kept 132/68 while
    modern ones converged to the site-wide values. Deleting the file removes
    those replicas, so the assertion flips: the stub on and the stub off must
    now produce the *same* numbers. That is the one behavioural change this
    batch declares, and it is checked rather than assumed.

E5  Geometry is compared field-by-field against the H2b1 candidate's measurements
    (`docs/batchH2b1-shots/geom-live-cand.json`), whose bytes are this batch's
    baseline. That is what turns "nothing moved" into a claim with a reference.

usage:
    b2d_h2b2_e2e.py --out DIR [--auth user:pass]
"""

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOST = 'https://dev.zxpet.com'
VIEWPORTS = [(480, 900), (768, 1000), (1024, 1000), (1100, 1000), (1101, 1000), (1440, 1000)]
PRE = '/wp-content/themes/sinofresh-theme-preflight'
LIVE = '/wp-content/themes/sinofresh-theme'

DOSE_PAGES = [
    ('/products/soft-chews/', 'products__soft-chews'),
    ('/products/tablets/', 'products__tablets'),
    ('/products/powders/', 'products__powders'),
    ('/products/pastes/', 'products__pastes'),
    ('/products/drops/', 'products__drops'),
    ('/products/liquids/', 'products__liquids'),
    ('/products/fish-oil/', 'products__fish-oil'),
    ('/products/dental-chews/', 'products__dental-chews'),
    ('/zh/products/soft-chews/', 'zh__products__soft-chews'),
    ('/zh/products/tablets/', 'zh__products__tablets'),
    ('/zh/products/powders/', 'zh__products__powders'),
    ('/zh/products/pastes/', 'zh__products__pastes'),
    ('/zh/products/drops/', 'zh__products__drops'),
    ('/zh/products/liquids/', 'zh__products__liquids'),
    ('/zh/products/fish-oil/', 'zh__products__fish-oil'),
    ('/zh/products/dental-chews/', 'zh__products__dental-chews'),
]
DOSE_EN = '/products/soft-chews/'

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
  const chip = q('.sf-explore__chip');
  const chips = q('.sf-explore__chips');
  const wallBtn = q('#formulas .sf-explore__btn');
  const toc = q('.sf-toc');
  const heroBtn = [...document.querySelectorAll('a.sf-quote-cta')]
      .find(a => /Build Custom Formula/.test(a.textContent)) || null;
  const ws = cs(wall);
  const ex = cs(explore);
  const bandRect = rect(band), exRect = rect(explore), wallRect = rect(wall);
  const wallH2Rect = rect(wallH2);
  const wallPad = wall ? num(ws.paddingBottom) : null;
  const res = performance.getEntriesByType('resource').map(e => e.name);
  return JSON.stringify({
    vw: window.innerWidth,
    overflowX: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    bodyOverflowX: document.body.scrollWidth - document.body.clientWidth,
    sheet: (document.querySelector('link[rel="stylesheet"][href*="sinofresh-theme"]') || {}).href || '',
    cfgLinks: document.querySelectorAll("[id^='sinofresh-configurator']").length,
    cfgInHead: document.head.innerHTML.indexOf('sinofresh-configurator') !== -1,
    cfgInBody: document.body.innerHTML.indexOf('sinofresh-configurator') !== -1,
    cfgRequests: res.filter(u => u.indexOf('configurator') !== -1).length,
    cfgRequestsAll: res.filter(u => u.indexOf('configurator') !== -1),
    stubRan: window.__stubRan || 0,
    cfgRan: window.__cfgRan || 0,
    hasNoHas: document.documentElement.className.indexOf('no-has') !== -1,
    ssLen: sessionStorage.length,
    ssKeys: Object.keys(sessionStorage).sort(),
    // Nothing in the DOM for the deleted script to bind to. This is what makes
    // the injection below inert, and it is asserted rather than assumed.
    cfgTargets: document.querySelectorAll(
        '.configurator, .configurator__bar, #configurator-drawer, #configurator').length,
    band: bandRect, explore: exRect, wall: wallRect, wallH2: wallH2Rect,
    bandSections: document.querySelectorAll('section.sf-explore-band').length,
    bandPad: band ? {l: cs(band).paddingLeft, r: cs(band).paddingRight,
                     t: cs(band).paddingTop, b: cs(band).paddingBottom} : null,
    explorePadL: ex ? ex.paddingLeft : null,
    exploreMarginL: ex ? ex.marginLeft : null,
    exploreBoxSizing: ex ? ex.boxSizing : null,
    exploreMaxW: ex ? ex.maxWidth : null,
    gutterL: exRect ? exRect.x : null,
    gutterR: (exRect && bandRect) ? Math.round(bandRect.w - (exRect.x + exRect.w)) : null,
    exploreContentX: (exRect && ex) ? Math.round(exRect.x + num(ex.paddingLeft)) : null,
    wallContentX: wallH2Rect ? wallH2Rect.x : null,
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
              minHeight: cs(wallBtn).minHeight, display: cs(wallBtn).display,
              w: Math.round(wallBtn.getBoundingClientRect().width)} : null,
    heroBtnHref: heroBtn ? heroBtn.getAttribute('href') : null,
    heroBtnClass: heroBtn ? heroBtn.className : null,
    tocPresent: !!toc,
    tocDisplay: toc ? cs(toc).display : null,
    tocLinks: [...document.querySelectorAll('.sf-toc a')].map(a => a.textContent.trim()),
    configuratorLeft: document.querySelectorAll('#configurator, .configurator').length,
    buildH2: [...document.querySelectorAll('h2')]
        .filter(t => /^Build Your /.test(t.textContent.trim())).length,
    floatStackBottom: q('.sf-float-stack') ? cs(q('.sf-float-stack')).bottom : null,
    langSwitcherBottom: q('.trp-language-switcher')
        ? cs(q('.trp-language-switcher')).bottom : null,
    outline: (function () {
      // A structural fingerprint of the body that survives class/style churn.
      // SCRIPT/STYLE are skipped on purpose: E3 appends a script element, and
      // counting it would make the two states differ for a reason that has
      // nothing to do with the page.
      const out = [];
      const walk = (el, d) => {
        if (d > 9 || out.length > 900) return;
        for (const c of el.children) {
          if (c.tagName === 'SCRIPT' || c.tagName === 'STYLE') continue;
          out.push(d + ':' + c.tagName + ':' +
                   (c.className && typeof c.className === 'string'
                     ? c.className.split(/\s+/).slice(0, 2).join('.') : '') + ':' +
                   (c.children.length ? '' : (c.textContent || '').trim().slice(0, 24)));
          walk(c, d + 1);
        }
      };
      walk(document.body, 0);
      return out.length;
    })()
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


def curl_code(url, auth, header=None):
    cmd = ['curl', '-s', '-o', '/dev/null', '-w', '%{http_code}', '--user', auth, url]
    if header:
        cmd[1:1] = ['-H', header]
    return subprocess.run(cmd, capture_output=True, text=True).stdout.strip()


def curl_body(url, auth, header=None):
    cmd = ['curl', '-s', '--user', auth, url]
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

    def attach(self, init_script=None):
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

    def goto(self, path, tag='h2b2'):
        url = HOST + path + '?sfcap=' + tag + time.strftime('%H%M%S') + str(id(path) % 97)
        run(['agent-browser', 'open', url], env=self.env)
        run(['agent-browser', 'reload'], env=self.env)
        time.sleep(0.7)
        probe = ev(MEASURE, env=self.env)
        if 'preflight' not in (probe.get('sheet') or ''):
            raise SystemExit('FATAL the pre-flight header did not attach — that is the LIVE '
                             'theme: %s' % probe.get('sheet'))
        return probe

    def errors(self):
        rc, out, _ = run(['agent-browser', 'errors'], env=self.env)
        txt = out.strip()
        if not txt or txt.lower() in ('no errors', 'none', '[]'):
            return []
        try:
            return json.loads(txt)
        except Exception:
            return [txt]


def baseline_js():
    """The exact configurator.js bytes H2b1 left enqueued."""
    p = subprocess.run(['git', '-C', ROOT, 'show',
                        'ebe8f50:sinofresh-theme/assets/js/configurator.js'],
                       capture_output=True)
    if p.returncode != 0:
        raise SystemExit('cannot read the baseline configurator.js from git')
    return p.stdout.decode('utf-8')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--auth', default=os.environ.get('SF_DEV_AUTH', 'sfdev:VkEws18Kl5V1qp3TpZ6s'))
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    e = E2E(args)

    try:
        # ---- E1: the assets are gone from every dosage page ------------------
        print('--- E1  16 dosage pages: no configurator asset, no console errors ---')
        e.attach()
        e.goto(DOSE_EN)
        e.rows['e1'] = []
        for path, slug in DOSE_PAGES:
            raw = curl_body(HOST + path, args.auth, 'X-SF-Preflight: 1')
            code = curl_code(HOST + path, args.auth, 'X-SF-Preflight: 1')
            refs = raw.count('sinofresh-configurator')
            if code != '200':
                e.fail('E1 %s: http %s' % (path, code))
            if refs:
                e.fail('E1 %s: %d references to sinofresh-configurator in the served HTML'
                       % (path, refs))
            e.rows['e1'].append({'path': path, 'code': code, 'refs': refs})
        if not [f for f in e.fails if f.startswith('E1')]:
            e.ok('E1 all 16 dosage pages serve 200 with zero references to '
                 'sinofresh-configurator (en + zh)')

        probe = e.goto(DOSE_EN)
        print('   dose page: cfgLinks=%d cfgInHead=%s cfgInBody=%s cfgRequests=%d sheet=%s'
              % (probe['cfgLinks'], probe['cfgInHead'], probe['cfgInBody'],
                 probe['cfgRequests'], probe['sheet']))
        if probe['cfgLinks'] or probe['cfgInHead'] or probe['cfgInBody']:
            e.fail('E1 the served candidate page still carries a configurator reference in the DOM')
        if probe['cfgRequests'] != 0:
            e.fail('E1 the candidate page requested %d configurator resources (%s) — the '
                   'enqueue is not actually gone'
                   % (probe['cfgRequests'], probe['cfgRequestsAll'][:3]))
        if probe['configuratorLeft'] or probe['buildH2']:
            e.fail('E1 the configurator DOM is back: left=%d BuildYourH2=%d'
                   % (probe['configuratorLeft'], probe['buildH2']))
        errs = e.errors()
        if errs:
            e.fail('E1 %d console error(s) on the dosage page: %s' % (len(errs), errs[:2]))
        else:
            e.ok('E1 the dosage page in a real browser: no configurator element, no '
                 'configurator request, no console error, and the H2b1 page order is intact')

        # ---- E2: the deleted URLs really are gone ---------------------------
        print('--- E2  the two asset URLs, under the pre-flight copy ---')
        e.rows['e2'] = []
        for rel, label in (('/assets/css/configurator.css', 'css'), ('/assets/js/configurator.js', 'js')):
            code = curl_code(HOST + PRE + rel, args.auth, 'X-SF-Preflight: 1')
            e.rows['e2'].append({'asset': rel, 'preflight': code})
            if code != '404':
                e.fail('E2 %s under the pre-flight copy returns %s, expected 404'
                       % (rel, code))
        # A sibling asset that still exists is the control: it proves the 404 is
        # about these two files and not about the whole directory being broken.
        control = curl_code(HOST + PRE + '/assets/js/formulas.js', args.auth, 'X-SF-Preflight: 1')
        e.rows['e2'].append({'asset': '/assets/js/formulas.js (control)', 'preflight': control})
        if control != '200':
            e.fail('E2 control: /assets/js/formulas.js under the pre-flight copy returns %s, '
                   'expected 200 — the 404s above may be a broken directory rather than '
                   'deleted files' % control)
        else:
            e.ok('E2 both deleted URLs 404 while a sibling asset in the same directory still '
                 'serves 200 — the 404s are the deletion, not a broken copy')

        # ---- E3: the inert script cannot change anything ---------------------
        print('--- E3  the enqueued-but-inert script (two-state injection) ---')
        js = baseline_js()
        sentinel = 'window.__cfgRan=(window.__cfgRan||0)+1;\n'
        runner = (sentinel + js).replace('</script', '<\\/script')
        state_a = probe
        if state_a['cfgTargets'] != 0:
            e.fail('E3 the page still holds %d element(s) the script binds to, so the injection '
                   'cannot be shown to be inert' % state_a['cfgTargets'])
        inj = ev("(function(){var s=document.createElement('script');"
                 "s.textContent=%s;document.body.appendChild(s);return 1;})()"
                 % json.dumps(runner), env=e.env)
        time.sleep(0.6)
        # Interact without leaving the page. The first version of this test
        # clicked `a.sf-explore__btn` directly — whose href is `/formulas/` — so
        # the browser navigated, the sentinel was erased with the old document,
        # and the outline count "changed" because it was measuring a different
        # page. Cancelling the default action in the CAPTURE phase keeps the
        # event propagating to the element's own handlers (so anything the script
        # had bound would still fire) while suppressing the navigation.
        clicks = ev("(function(){document.addEventListener('click',function(v){"
                    "v.preventDefault();},true);var n=0;"
                    "var b=document.querySelector('#formulas .sf-explore__btn');"
                    "if(b){b.click();n++;}"
                    "var c=document.querySelector('.sf-explore__chip');if(c){c.click();n++;}"
                    "return JSON.stringify({clicks:n,url:location.pathname});})()", env=e.env)
        time.sleep(0.6)
        state_b = ev(MEASURE, env=e.env)

        def fp(s):
            strip = lambda d: ({k: d.get(k) for k in ('x', 'w', 'h')} if isinstance(d, dict) else d)
            return {'ssLen': s['ssLen'], 'ssKeys': s['ssKeys'], 'outline': s['outline'],
                    'band': strip(s['band']), 'wall': strip(s['wall']),
                    'explore': strip(s['explore']), 'wallH2': strip(s['wallH2']),
                    'chipCount': s['chipCount'], 'chipsScroll': s['chipsScroll'],
                    'cfgLinks': s['cfgLinks'], 'cfgTargets': s['cfgTargets'],
                    'configuratorLeft': s['configuratorLeft'], 'buildH2': s['buildH2']}
        fa, fb = fp(state_a), fp(state_b)
        e.rows['e3'] = {'injected': inj, 'clicks': clicks, 'cfgRan': state_b['cfgRan'],
                        'ssA': state_a['ssLen'], 'ssB': state_b['ssLen'],
                        'ssKeysA': state_a['ssKeys'], 'ssKeysB': state_b['ssKeys'],
                        'outlineA': state_a['outline'], 'outlineB': state_b['outline'],
                        'cfgRequestsA': state_a['cfgRequests'], 'cfgRequestsB': state_b['cfgRequests'],
                        'before': fa, 'after': fb}
        print('   injected cfgRan=%s  clicks=%s  sessionStorage %d -> %d %s  outline %d -> %d  '
              'cfgRequests %d -> %d'
              % (state_b['cfgRan'], (clicks or {}).get('clicks'), state_a['ssLen'],
                 state_b['ssLen'], state_b['ssKeys'], state_a['outline'], state_b['outline'],
                 state_a['cfgRequests'], state_b['cfgRequests']))
        if not isinstance(clicks, dict) or clicks.get('url') != '/products/soft-chews/':
            e.fail('E3 the page navigated away during the injection test (%r) — the two states '
                   'would not be the same document' % (clicks,))
        elif not state_b['cfgRan']:
            e.fail('E3 the injected baseline script never ran, so the two-state comparison is '
                   'vacuous')
        elif state_b['configuratorLeft'] != 0 or state_b['cfgTargets'] != 0:
            e.fail('E3 the injection created a configurator root — the test is not inert')
        else:
            diffs = [k for k in fa if fa[k] != fb[k]]
            if diffs:
                e.fail('E3 injecting the script changed the page: %s'
                       % {k: (fa[k], fb[k]) for k in diffs})
            else:
                e.ok('E3 the baseline configurator.js, injected and executed on the candidate '
                     'page, changes nothing: the sessionStorage keys are unchanged (%s), the '
                     'body outline count is identical (%d nodes), the band/card-wall geometry '
                     'is identical, and clicking the wall button and a chip changes nothing'
                     % (state_b['ssKeys'], state_b['outline']))
        # The session keys the deleted script would have written. Their absence is
        # H6 dead-code item 4, and it is cheap to assert here rather than to
        # re-derive later.
        contract_keys = [k for k in state_b['ssKeys']
                         if k.startswith('sinofresh_config_') or k.startswith('sinofresh_formula_')]
        if contract_keys:
            e.fail('E3 the page carries configurator session keys %s' % contract_keys)
        else:
            e.ok('E3 no sinofresh_config_* / sinofresh_formula_* key exists in sessionStorage, '
                 'before or after the injection (%s) — those keys have had no writer since H2b1'
                 % (state_b['ssKeys'] or 'no keys at all'))
        if state_b['cfgRequests'] != 0:
            e.fail('E3 the page requested a configurator resource (%s)'
                   % state_b['cfgRequestsAll'][:2])
        else:
            e.ok('E3 zero configurator requests in both states — the inline injection cannot '
                 'fetch a file that no longer exists, and the served page never asked for one')

        # ---- E4: the legacy-engine delta is now zero ------------------------
        print('--- E4  html.no-has four-cell: the two fixed layers ---')
        stub = os.path.join(args.out, 'no-has-stub.js')
        with open(stub, 'w', encoding='utf-8') as fh:
            fh.write(NO_HAS_STUB)
        e.rows['e4'] = {}
        for w, h in ((480, 900), (1440, 1000)):
            # A clean browser per width: the previous iteration ended with the stub
            # in the environment, and reusing it would make the "un-stubbed" cell
            # identical to the stubbed one — the negative control would then be
            # checking the wrong thing instead of failing.
            e.attach()
            e.goto(DOSE_EN, tag='e4a')
            run(['agent-browser', 'set', 'viewport', str(w), str(h)], env=e.env)
            time.sleep(0.6)
            off = ev(MEASURE, env=e.env)
            e.attach(init_script=stub)
            e.goto(DOSE_EN, tag='e4b')
            run(['agent-browser', 'set', 'viewport', str(w), str(h)], env=e.env)
            time.sleep(0.6)
            on = ev(MEASURE, env=e.env)
            e.rows['e4'][str(w)] = {'noStub': {'float': off['floatStackBottom'],
                                               'lang': off['langSwitcherBottom'],
                                               'noHas': off['hasNoHas'], 'stubRan': off['stubRan']},
                                    'stub': {'float': on['floatStackBottom'],
                                             'lang': on['langSwitcherBottom'],
                                             'noHas': on['hasNoHas'], 'stubRan': on['stubRan']}}
            print('   %4dpx  no-stub float=%s lang=%s no-has=%s | stub float=%s lang=%s '
                  'no-has=%s (stubRan=%s)'
                  % (w, off['floatStackBottom'], off['langSwitcherBottom'], off['hasNoHas'],
                     on['floatStackBottom'], on['langSwitcherBottom'], on['hasNoHas'],
                     on['stubRan']))
            if off['stubRan'] or off['hasNoHas']:
                e.fail('E4 %dpx negative control: the stub leaked into the un-stubbed run' % w)
            if not on['stubRan']:
                e.fail('E4 %dpx positive control: the init script never ran' % w)
            elif not on['hasNoHas']:
                e.fail('E4 %dpx positive control: the stub ran but html.no-has is absent' % w)
            if on['hasNoHas'] and (off['floatStackBottom'] != on['floatStackBottom']
                                   or off['langSwitcherBottom'] != on['langSwitcherBottom']):
                e.fail('E4 %dpx: the legacy branch still differs (float %s vs %s, lang %s vs %s) '
                       '— an unconditional html.no-has replica survived the deletion'
                       % (w, off['floatStackBottom'], on['floatStackBottom'],
                          off['langSwitcherBottom'], on['langSwitcherBottom']))
        if not [f for f in e.fails if f.startswith('E4')]:
            e.ok('E4 the legacy-engine delta is zero: with html.no-has forced on, both fixed '
                 'layers compute exactly what the modern engine gives — the two unconditional '
                 'replicas at the old configurator.css:700/705 are gone (H2b1 measured 132/68 '
                 'on live and 100/24/268/16 + lang 0 on the candidate)')

        # ---- E5: geometry parity with the baseline measurements -------------
        print('--- E5  geometry vs the H2b1 candidate measurements ---')
        ref_path = os.path.join(ROOT, 'docs', 'batchH2b1-shots', 'geom-live-cand.json')
        ref = json.load(open(ref_path, encoding='utf-8'))['cand']['widths']
        e.attach()
        e.goto(DOSE_EN, tag='e5')
        ev("(function(){var b=document.querySelector('.sf-cookie-banner .sf-cookie-banner__btn');"
           "if(b)b.click();return 1;})()", env=e.env)
        time.sleep(0.6)
        widths, diffs = [], []
        # Every field the H2b1 geometry harness recorded and this run can measure.
        # Comparing a hand-picked subset is how "nothing moved" quietly becomes
        # "the three things I thought to look at did not move".
        FIELDS = ['overflowX', 'band', 'explore', 'wall', 'wallH2', 'bandSections', 'bandPad',
                  'explorePadL', 'exploreMarginL', 'exploreBoxSizing', 'exploreMaxW',
                  'gutterL', 'gutterR', 'exploreContentX', 'wallContentX', 'wallPadBottom',
                  'wallContentBottom', 'gapWallContentToBand', 'gapWallEdgeToBand',
                  'chipCount', 'chipCurrent', 'chipFont', 'chipPad', 'chipRadius', 'chipsGap',
                  'chipsScroll', 'chipsNowrap', 'bandBtn', 'heroBtnHref', 'heroBtnClass',
                  'tocPresent', 'tocDisplay', 'tocLinks', 'configuratorLeft', 'buildH2']
        RECTS = ('band', 'explore', 'wall', 'wallH2')
        checked = 0
        for w, h in VIEWPORTS:
            run(['agent-browser', 'set', 'viewport', str(w), str(h)], env=e.env)
            time.sleep(0.6)
            m = ev(MEASURE, env=e.env)
            r = ref[str(w)]
            for f in FIELDS:
                if f not in r:
                    continue
                a, b = r.get(f), m.get(f)
                if f in RECTS:
                    # x/width/height are the position-independent half of a
                    # rect; `y`/`top` follow the scroll position, which the E4
                    # and E6 passes have already moved.
                    a = {k: (a or {}).get(k) for k in ('x', 'w', 'h')}
                    b = {k: (b or {}).get(k) for k in ('x', 'w', 'h')}
                checked += 1
                if a != b:
                    diffs.append('%dpx %s: %r -> %r' % (w, f, a, b))
            widths.append({k: m.get(k) for k in FIELDS})
            print('   %4dpx  overflow=%s band=%s explore w%s chips=%s font=%s pad=%s gap=%s '
                  'wallPadB=%s edgeGap=%s'
                  % (w, m['overflowX'], (m['band'] or {}).get('w'),
                     (m['explore'] or {}).get('w'), m['chipCount'], m['chipFont'], m['chipPad'],
                     m['chipsGap'], m['wallPadBottom'], m['gapWallEdgeToBand']))
        e.rows['e5'] = {'widths': widths, 'diffs': diffs, 'checked': checked}
        if diffs:
            e.fail('E5 geometry moved against the baseline: %s' % diffs[:6])
        else:
            e.ok('E5 %d measured fields are identical to the H2b1 candidate at all six widths '
                 '— deleting the assets changed no geometry' % checked)

        # ---- E6: corroborating screenshots ---------------------------------
        print('--- E6  corroborating screenshots ---')
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
        e.attach()
        e.goto(DOSE_EN, tag='e6')
        ev("(function(){var b=document.querySelector('.sf-cookie-banner .sf-cookie-banner__btn');"
           "if(b)b.click();return 1;})()", env=e.env)
        time.sleep(0.6)
        shots = []
        for w, _ in VIEWPORTS:
            m = ev(MEASURE, env=e.env)
            band_h = (m['band'] or {}).get('h') or 600
            run(['agent-browser', 'set', 'viewport', str(w), str(int(band_h) + 240)], env=e.env)
            time.sleep(0.5)
            ev("(function(){var b=document.querySelector('section.sf-explore-band');"
               "if(!b)return 0;window.scrollTo(0,b.getBoundingClientRect().top+window.scrollY-100);"
               "return 1;})()", env=e.env)
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
            print('   %4dpx  chrome %s  band top %s h %s -> %d bytes'
                  % (w, (frame or {}).get('off'), (frame or {}).get('top'),
                     (frame or {}).get('h'), size))
            if size < 12000:
                e.fail('E6 %dpx: the screenshot is %d bytes — a blank capture' % (w, size))
            top, off = (frame or {}).get('top'), (frame or {}).get('off')
            if top is None or off is None:
                e.fail('E6 %dpx: the band is not in the document' % w)
            elif top < off or top > off + 80:
                e.fail('E6 %dpx: the band sits at y=%s under %spx of chrome — not framed'
                       % (w, top, off))
            shots.append({'vw': w, 'chromeBottom': off, 'bandTop': top,
                          'bandH': (frame or {}).get('h'), 'bytes': size})
        e.rows['e6'] = shots
        if not [f for f in e.fails if f.startswith('E6')]:
            e.ok('E6 six real screenshots (%d-%d KB), the band framed clear of the sticky '
                 'chrome, from the candidate bytes'
                 % (min(s['bytes'] for s in shots) // 1024, max(s['bytes'] for s in shots) // 1024))

    finally:
        run(['agent-browser', 'close', '--all'], env=e.env)

    print('\n' + '=' * 72)
    if e.fails:
        print('E2E FAILURES: %d' % len(e.fails))
        for f in e.fails:
            print('   ' + f)
    else:
        print('E2E: E1-E6 all pass')
    with open(os.path.join(args.out, 'e2e.json'), 'w', encoding='utf-8') as fh:
        json.dump({'fails': e.fails, 'notes': e.notes, 'rows': e.rows},
                  fh, ensure_ascii=False, indent=2, default=str)
    return 1 if e.fails else 0


if __name__ == '__main__':
    sys.exit(main())

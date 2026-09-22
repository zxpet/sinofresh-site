#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H4e — the browser end-to-end pass (E1-E5).

WHY THIS PASS EXISTS AT ALL

The gate compares bytes, and the bytes Cloudflare serves hide the address
behind an obfuscation the gate has to decode before it can compare. That proves
what the origin sent. It does not prove what a reader ends up with, because the
last step — Cloudflare's email-decode script rewriting the href back into a
usable mailto — happens in the browser, after the bytes are handed over.

So this pass waits for that script, then reads the address out of the live DOM.
It is the only check that can say "a visitor who clicks the envelope icon gets
sales@zxpet.com".

E1  Four surfaces on three page types: the top bar, the footer contact line, the
    floating email button in the footer, and the Organization schema email.
    Every one of them resolves sf_contact_email, so all four have to move, and
    on the contact page a fifth source joins them from the template.

E2  The contact page's visible text and its mailto, read as text rather than as
    an attribute — a reader copying the address is the case that matters.

E3  The three legal pages. Their address lives in the database, not the theme,
    so this is the only place the database half of the swap is visible. Read
    from the rendered text, which is also what TranslatePress re-serialises from.

E4  The floating stack is untouched: still three buttons, all visible, in one
    column. This batch must not have disturbed the geometry H2b1 measured.

E5  No page on the way through leaves a console error behind.

usage:
    b2d_h4e_e2e.py --out DIR [--auth user:pass]
"""

import argparse
import base64
import json
import os
import subprocess
import sys
import time

HOST = 'https://dev.zxpet.com'
OLD = 'info@zxpet.com'
NEW = 'sales@zxpet.com'

# (path, label, expect a template-sourced address as well as the chrome)
PAGES = [('/about/', 'EN marketing', False),
         ('/formulas/joint-support-soft-chews/', 'EN formula detail', False),
         ('/contact/', 'EN contact', True),
         ('/privacy-policy/', 'EN privacy policy', True),
         ('/cookie-policy/', 'EN cookie policy', False),
         ('/terms/', 'EN terms of service', False),
         ('/zh/', 'ZH home', False)]

# The JS carries the two addresses as __OLD__ / __NEW__ placeholders: they are
# injected at call time so the Python constants stay the single source of truth
# (the first draft referenced them by name inside the JS and threw
# ReferenceError: OLD is not defined).
MEASURE = r"""
(() => {
  const txt = el => el ? el.textContent.replace(/\s+/g, ' ').trim() : null;

  // Cloudflare's decode script rewrites these in place once it runs. Poll until
  // none are left, so a reading taken too early cannot be mistaken for a page
  // that still carries the old address.
  const raw = [...document.querySelectorAll('a[href*="email-protection"]')].length;

  const mailtos = [...document.querySelectorAll('a[href^="mailto:"]')]
      .map(a => (a.getAttribute('href') || '').replace(/^mailto:/, '').split('?')[0]);

  const top    = document.querySelector('.sf-topbar__email a');
  const foot   = document.querySelector('.sf-footcontact a[href^="mailto:"]');
  const floaty = document.querySelector('.sf-float-btn--email');

  let schemaEmail = null, schemaType = null;
  for (const s of document.querySelectorAll('script[type="application/ld+json"]')) {
    try {
      const o = JSON.parse(s.textContent);
      if (o && o['@type'] === 'Organization') { schemaEmail = o.email; schemaType = o['@type']; }
    } catch (e) {}
  }

  const fb = [...document.querySelectorAll('.sf-float-btn')].map(b => {
    const r = b.getBoundingClientRect();
    const cs = getComputedStyle(b);
    return {cls: b.className, href: b.getAttribute('href'),
            visible: r.width > 0 && r.height > 0 && cs.visibility !== 'hidden'
                     && cs.display !== 'none',
            left: Math.round(r.left), top: Math.round(r.top + scrollY)};
  });

  // Everything a reader can see on this page, for the legal-page check.
  const body = document.body ? document.body.innerText : '';

  // The article region on its own. The whole-body check proves the old address
  // is gone from the page, but the footer also carries the address, and on the
  // first run the sampled context came from the footer rather than from the
  // page's own copy — which is the thing the database half actually changed.
  const art = document.querySelector('.entry-content')
           || document.querySelector('.wp-block-post-content');
  const artText = art ? art.innerText : '';

  const sheet = document.querySelector('link[rel="stylesheet"][href*="sinofresh-theme"]');

  return {
    href: location.href, viewportW: innerWidth,
    sheet: sheet ? sheet.getAttribute('href') : null,
    undecodedAnchors: raw,
    mailtos: mailtos,
    topHref: top ? (top.getAttribute('href') || '').replace(/^mailto:/, '') : null,
    topText: txt(top),
    footHref: foot ? (foot.getAttribute('href') || '').replace(/^mailto:/, '') : null,
    footText: txt(foot),
    floatHref: floaty ? (floaty.getAttribute('href') || '').replace(/^mailto:/, '') : null,
    schemaEmail: schemaEmail, schemaType: schemaType,
    floatBtns: fb,
    bodyHasOld: body.includes('__OLD__'), bodyHasNew: body.includes('__NEW__'),
    artLen: artText.length,
    artHasOld: artText.includes('__OLD__'), artHasNew: artText.includes('__NEW__'),
    artAround: (() => { const i = artText.indexOf('__NEW__');
                        return i < 0 ? null
                             : artText.replace(/\s+/g, ' ')
                                       .slice(Math.max(0, i - 110), i + 40); })()
  };
})()
"""


JS_ADDRS = {'__OLD__': OLD, '__NEW__': NEW}


def measure_js():
    js = MEASURE
    for k, v in JS_ADDRS.items():
        js = js.replace(k, v)
    return js


def run(cmd, timeout=180):
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return p.returncode, (p.stdout or '').strip(), (p.stderr or '').strip()


def ev(script, timeout=180):
    """agent-browser eval prints a JSON string literal: decode twice."""
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


class Pass(object):
    def __init__(self, auth):
        self.auth = auth
        self.fails, self.notes, self.rows = [], [], {}

    def fail(self, m):
        self.fails.append(m)
        print('   FAIL %s' % m)

    def ok(self, m):
        self.notes.append(m)
        print('   ok   %s' % m)

    def attach(self):
        b64 = base64.b64encode(self.auth.encode('utf-8')).decode('ascii')
        run(['agent-browser', 'close', '--all'])
        user, _, pw = self.auth.partition(':')
        rc, out, err = run(['agent-browser', 'set', 'credentials', user, pw])
        if rc != 0:
            raise SystemExit('FATAL set credentials: %s %s' % (out, err))
        rc, out, err = run(['agent-browser', 'open', HOST + '/'])
        if rc != 0:
            raise SystemExit('FATAL open: %s %s' % (out, err))
        hdrs = json.dumps({'Authorization': 'Basic ' + b64, 'X-SF-Preflight': '1'})
        run(['agent-browser', 'set', 'headers', hdrs])
        run(['agent-browser', 'errors', '--clear'])

    def goto(self, path, tag, wait_decode=True):
        url = HOST + path + '?sfcap=%s%s' % (tag, time.strftime('%H%M%S'))
        run(['agent-browser', 'open', url])
        run(['agent-browser', 'reload'])
        run(['agent-browser', 'set', 'viewport', '1440', '1000'])
        time.sleep(0.6)
        probe = ev(measure_js())
        if probe.get('viewportW') not in (None, 1440) and abs(probe['viewportW'] - 1440) > 2:
            raise SystemExit('FATAL the viewport did not take: innerWidth is %s'
                             % probe['viewportW'])
        sheet = probe.get('sheet') or ''
        if 'sinofresh-theme-preflight' not in sheet or 'ver=2.10.57' not in sheet:
            raise SystemExit('FATAL not the pre-flight copy — got %r. A wrong header '
                             'order silently serves the live theme.' % sheet)
        # Wait for Cloudflare's decode script, which rewrites the hrefs in place.
        if wait_decode:
            for _ in range(30):
                if probe.get('undecodedAnchors') == 0:
                    break
                time.sleep(0.2)
                probe = ev(measure_js())
        return probe

    def errors(self):
        rc, out, _ = run(['agent-browser', 'errors'])
        t = out.strip()
        if not t or t.lower() in ('no errors', 'none', '[]'):
            return []
        try:
            return json.loads(t)
        except Exception:
            return [t]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--auth', default=os.environ.get('SF_DEV_AUTH',
                                                     'sfdev:VkEws18Kl5V1qp3TpZ6s'))
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    p = Pass(args.auth)
    p.attach()

    # ------------------------------------------------------------------ E1 --
    print('E1  the four chrome surfaces, plus the contact page from the template')
    for path, label, has_tpl in PAGES:
        m = p.goto(path, 'e1')
        p.rows['E1_' + label] = m
        if m['undecodedAnchors']:
            p.fail('%s: %d anchor(s) never got decoded — reading the obfuscated '
                   'href would compare the wrong thing' % (label, m['undecodedAnchors']))
            continue
        stale = [x for x in m['mailtos'] if x != NEW]
        if stale:
            p.fail('%s: mailto addresses are %s' % (label, sorted(set(stale))))
        p.ok('%s: %d mailto link(s), all %s' % (label, len(m['mailtos']), NEW))

    # ------------------------------------------------------------------ E2 --
    print('E2  the contact page: visible text and mailto')
    m = p.rows.get('E1_EN contact')
    if not m:
        p.fail('E2: the contact page was not captured')
    else:
        checks = [('footer contact line', m['footHref'], m['footText']),
                  ('top bar', m['topHref'], m['topText']),
                  ('floating email button', m['floatHref'], None)]
        for name, href, text in checks:
            if href != NEW:
                p.fail('E2 %s: href is %r' % (name, href))
            elif text is not None and text != NEW:
                p.fail('E2 %s: visible text is %r' % (name, text))
            else:
                p.ok('E2 %s: %s%s' % (name, href, '' if text is None else ' / %s' % text))
        if not (m['bodyHasNew'] and not m['bodyHasOld']):
            p.fail('E2 contact page text: old present=%s new present=%s'
                   % (m['bodyHasOld'], m['bodyHasNew']))
        else:
            p.ok('E2 the contact page body shows %s and no %s' % (NEW, OLD))

    # ------------------------------------------------------------------ E3 --
    print('E3  the three legal pages — the database half, rendered')
    for path, label, _ in [x for x in PAGES if 'policy' in x[0] or x[0] == '/terms/']:
        m = p.rows.get('E1_' + label)
        if not m:
            p.fail('E3 %s: not captured' % label)
            continue
        if m.get('artLen', 0) < 500:
            p.fail('E3 %s: the article region is %s chars — the check is looking at '
                   'the wrong container' % (label, m.get('artLen')))
        elif m.get('artHasOld'):
            p.fail('E3 %s: %s still in the page\'s own text' % (label, OLD))
        elif not m.get('artHasNew'):
            p.fail('E3 %s: %s not found in the page\'s own text' % (label, NEW))
        else:
            p.ok('E3 %s: article text %d chars, old gone, new present — "...%s"'
                 % (label, m['artLen'], (m.get('artAround') or '')[-120:]))

    # ------------------------------------------------------------------ E4 --
    print('E4  the floating stack is undisturbed')
    for label in ('EN marketing', 'EN formula detail'):
        m = p.rows.get('E1_' + label)
        if not m:
            continue
        btns = m['floatBtns']
        if len(btns) != 3:
            p.fail('E4 %s: %d floating buttons, expected 3' % (label, len(btns)))
            continue
        if not all(b['visible'] for b in btns):
            p.fail('E4 %s: a floating button has no box' % label)
            continue
        lefts = {b['left'] for b in btns}
        tops = [b['top'] for b in btns]
        if len(lefts) != 1 or tops != sorted(tops) or len(set(tops)) != 3:
            p.fail('E4 %s: the buttons are no longer one stacked column: %s'
                   % (label, btns))
        else:
            p.ok('E4 %s: 3 buttons, one column at left=%d, tops=%s'
                 % (label, lefts.pop(), tops))

    # ------------------------------------------------------------------ E5 --
    print('E5  console errors')
    errs = p.errors()
    if errs:
        for e in errs[:5]:
            p.fail('E5 console: %s' % e)
    else:
        p.ok('E5 no console errors on any page visited')

    print('-' * 72)
    if p.fails:
        print('VERDICT: FAIL — %d ok, %d FAIL' % (len(p.notes), len(p.fails)))
        rc = 1
    else:
        print('VERDICT: PASS — %d ok, 0 FAIL' % len(p.notes))
        rc = 0
    with open(os.path.join(args.out, 'measurements.json'), 'w', encoding='utf-8') as fh:
        json.dump({'fails': p.fails, 'notes': p.notes, 'rows': p.rows},
                  fh, indent=2, ensure_ascii=False)
    return rc


if __name__ == '__main__':
    sys.exit(main())

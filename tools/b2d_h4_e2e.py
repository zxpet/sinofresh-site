#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H4 — the browser end-to-end pass.

WHY THIS PASS EXISTS AT ALL

The gate compares bytes served by the pre-flight copy. Some of what H4 adds
cannot be settled in bytes:

  * "the capsule appears once the visitor has scrolled to the parameter band"
    is a scroll listener and a geometry threshold. Snapshotting the markup
    proves the capsule is emitted `hidden`; it cannot prove the listener
    removes `hidden` at the right moment, or that removing it leaves the three
    buttons already in the stack where H2b1 put them.
  * "appending the capsule as the stack's first child moves nothing" is the
    one claim in this batch that is purely positional. The stack is
    bottom-anchored, so it is the *only* place a new button could be added
    without shifting its neighbours — and the only way to know is to measure
    all four before and after in a real layout.
  * the submit path ends in wp_mail(). Whether a lead can actually be
    delivered is not visible in any byte of HTML.
  * the two server-side guards (honeypot, three-second floor) are rejections.
    A rejection that never fires in a browser is indistinguishable, from the
    markup alone, from a check that does not exist.

E1  The reveal. At the top of the page the capsule is `hidden`; after real
    wheel scrolling it is not, and it stays shown after scrolling back up
    (one-way, or the CTA would blink out from under a visitor).
E2  The geometry, which is the fragile thing. The three pre-existing buttons
    must hold the exact boxes they had while the capsule was still hidden,
    and the capsule must join them in the same column at the same right edge
    at the same gap.
E3  The dialog opens: `hidden` off, `is-open` on, body locked, focus moved
    into the panel, and the panel is the declared dialog with aria-modal.
E4  The closes: Escape returns focus to the opener; a click on the backdrop
    closes; a click inside the panel does not.
E5  The honeypot. A filled `website` must be rejected — and rejected *before*
    anything else, which is why the same payload carries a valid clock.
E6  The three-second floor. A submission faster than a human must be refused.
    The measured elapsed time is reported, because "rejected" only means
    something if the clock really was under the floor.
E7  A real submission: the success panel replaces the form, and the dialog
    closes itself three seconds later. This is also the only check that says
    a lead can reach sales@.
E8  The plain pages. Nine tenths of the site has no capsule, no dialog and no
    inquiry.js — the enqueue is conditional on the post type.
E9  One row vs two. The panel is rebuilt from the record, so a formula with a
    Pack Size shows two rows and one without shows one.
E10 The phone. 44px targets in a 16px gutter, and the panel is a bottom sheet.

usage:
    b2d_h4_e2e.py --out DIR [--auth user:pass] [--skip-mail]
"""

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import time

HOST = 'https://dev.zxpet.com'
PREFLIGHT_DIR = 'sinofresh-theme-preflight'
NEW_VER = '2.10.59'

DETAIL_2ROW = '/formulas/joint-support-soft-chews/'      # Piece Weight + Pack Size
DETAIL_1ROW = '/formulas/bladder-support-powder/'        # Piece Weight only
DETAIL_ZH = '/zh/formulas/bladder-support-powder/'
PLAIN = '/about/'

PRODUCT_2ROW = 'Joint Support Soft Chews'
PRODUCT_1ROW = 'Bladder Support Powder'

# The marker makes the one test mail findable in the sales@ inbox, so a human
# can confirm delivery without guessing which message was the machine's.
MAIL_TAG = 'H4 E2E'

STATE = r"""
(() => {
  const box = el => {
    if (!el) return null;
    const r = el.getBoundingClientRect();
    return {x: Math.round(r.left), y: Math.round(r.top),
            w: Math.round(r.width), h: Math.round(r.height),
            right: Math.round(innerWidth - r.right),
            bottom: Math.round(innerHeight - r.bottom)};
  };
  const q = s => document.querySelector(s);
  const sheet = q('link[rel="stylesheet"][href*="sinofresh-theme"]');
  const cap = q('.sf-float-btn--inquiry');
  const modal = q('.sf-inquiry-modal');
  const panel = q('.sf-inquiry-modal__panel');
  const form = q('.sf-inquiry-form');
  const succ = q('.sf-inquiry-modal__success');
  const band = q('.sf-fdetail2__params');
  const capCS = cap ? getComputedStyle(cap) : null;
  const rockers = [...document.querySelectorAll('.sf-float-btn')]
      .filter(b => !b.classList.contains('sf-float-btn--inquiry'));
  const active = document.activeElement;
  const stack = q('.sf-float-stack');

  return {
    href: location.href,
    vw: innerWidth, vh: innerHeight, scrollY: Math.round(window.scrollY),
    sheet: sheet ? sheet.getAttribute('href') : null,
    hasScript: !!q('script[src*="assets/js/inquiry.js"]'),
    bodyClass: document.body ? document.body.className : '',
    bandTop: band ? Math.round(band.getBoundingClientRect().top) : null,
    bandFound: !!band,

    capPresent: !!cap,
    capHidden: cap ? cap.hasAttribute('hidden') : null,
    capIsVisible: cap ? cap.classList.contains('is-visible') : null,
    capBox: box(cap),
    capDisplay: capCS ? capCS.display : null,
    capRadius: capCS ? capCS.borderTopLeftRadius : null,
    capBg: capCS ? capCS.backgroundColor : null,
    capText: cap ? cap.textContent.replace(/\s+/g, ' ').trim() : null,
    capHref: cap ? cap.getAttribute('href') : null,
    capLabel: cap ? cap.getAttribute('aria-label') : null,
    capFirstChild: (() => {
      if (!cap || !stack) return null;
      const kids = [...stack.children].filter(e => e.nodeType === 1);
      return kids.length ? kids[0] === cap : null;
    })(),
    stackGap: stack ? (getComputedStyle(stack).rowGap || getComputedStyle(stack).gap) : null,
    stackDir: stack ? getComputedStyle(stack).flexDirection : null,
    rockers: rockers.map(b => ({
      cls: (b.className || '').split(' ').filter(c => c.indexOf('--') > -1).join(''),
      box: box(b),
      visible: b.getBoundingClientRect().width > 0 && getComputedStyle(b).visibility !== 'hidden'
    })),

    modalPresent: !!modal,
    modalHidden: modal ? modal.hasAttribute('hidden') : null,
    modalOpen: modal ? modal.classList.contains('is-open') : null,
    modalDisplay: modal ? getComputedStyle(modal).display : null,
    lock: document.body ? document.body.classList.contains('sf-inquiry-lock') : null,
    panelBox: box(panel),
    panelRole: panel ? panel.getAttribute('role') : null,
    panelAriaModal: panel ? panel.getAttribute('aria-modal') : null,
    panelRadius: panel ? getComputedStyle(panel).borderTopLeftRadius : null,
    formHidden: form ? form.hasAttribute('hidden') : null,
    successHidden: succ ? succ.hasAttribute('hidden') : null,
    successText: succ ? succ.textContent.replace(/\s+/g, ' ').trim() : null,
    status: (q('.sf-inquiry-form__status') || {}).textContent || '',
    submitDisabled: !!q('.sf-inquiry-form__submit') && q('.sf-inquiry-form__submit').disabled,
    focus: active ? {
      tag: active.tagName,
      cls: (active.className || ''),
      name: active.getAttribute ? active.getAttribute('name') : null,
      inModal: !!(modal && modal.contains(active))
    } : null,

    formulaValue: (q('input[name="formula"]') || {}).value || '',
    tsValue: (q('input[name="ts"]') || {}).value || '',
    terms: [...document.querySelectorAll('.sf-inquiry-modal__term')].map(e => e.textContent.trim()),
    values: [...document.querySelectorAll('.sf-inquiry-modal__value')].map(e => e.textContent.trim()),
    stepTitles: [...document.querySelectorAll('.sf-inquiry-modal__step-title')].map(e => e.textContent.trim()),
    stepCount: document.querySelectorAll('.sf-inquiry-modal__step').length,
    titleText: (q('.sf-inquiry-modal__title') || {}).textContent || '',
    leadText: (q('.sf-inquiry-modal__lead') || {}).textContent || '',

    rawAnchors: document.querySelectorAll('a[href*="email-protection"]').length
  };
})()
"""

# Set the fields without a real keyboard. Used only where the timing is the
# thing under test: Playwright's fill() needs a visible input, and the three
# seconds would be gone by the time four of them ran.
INJECT = r"""
(() => {
  const form = document.querySelector('.sf-inquiry-form');
  if (!form) return {error: 'no form'};
  const set = (n, v) => { const el = form.querySelector('[name="' + n + '"]');
                          if (el) el.value = v; };
  set('name', %s); set('email', %s); set('company', %s); set('country', %s);
  set('message', %s); set('website', %s);
  %s
  const ts = form.querySelector('[name="ts"]');
  return {ts: ts ? ts.value : null, now: Date.now(),
          delta: ts ? (Date.now() - Number(ts.value)) : null};
})()
"""

SUBMIT = r"""
(() => {
  const form = document.querySelector('.sf-inquiry-form');
  if (!form) return {error: 'no form'};
  const ts = form.querySelector('[name="ts"]');
  const before = ts ? Number(ts.value) : null;
  form.requestSubmit();
  return {tsBefore: before, now: Date.now(),
          delta: before ? (Date.now() - before) : null};
})()
"""


def jsstr(s):
    return json.dumps(s)


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
    def __init__(self, auth, out):
        self.auth = auth
        self.out = out
        self.fails, self.notes, self.data = [], [], {}
        self.mail_sent = False

    def fail(self, m):
        self.fails.append(m)
        print('   FAIL %s' % m)

    def ok(self, m):
        self.notes.append(m)
        print('   ok   %s' % m)

    def note(self, m):
        print('   ..   %s' % m)

    # ------------------------------------------------------------- plumbing

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
        # Custom header and Basic auth in ONE call: `set credentials` and
        # `set headers` each rebuild the context, so whichever runs second
        # wins and the other is lost.
        hdrs = json.dumps({'Authorization': 'Basic ' + b64, 'X-SF-Preflight': '1'})
        run(['agent-browser', 'set', 'headers', hdrs])
        run(['agent-browser', 'errors', '--clear'])

    def goto(self, path, tag, width=1440, height=1000, wait=0.7):
        url = HOST + path + '?sfcap=%s%s' % (tag, time.strftime('%H%M%S'))
        run(['agent-browser', 'open', url])
        run(['agent-browser', 'reload'])         # reload is what keeps the header
        run(['agent-browser', 'set', 'viewport', str(width), str(height)])
        ev('window.scrollTo(0,0)')
        time.sleep(wait)
        st = ev(STATE)
        if st.get('vw') and abs(st['vw'] - width) > 2:
            raise SystemExit('FATAL the viewport did not take: innerWidth %s != %s'
                             % (st['vw'], width))
        # The provenance assertion the H4e pass learned to insist on: a wrong
        # header order serves the live theme and every check below would pass
        # against the wrong bytes, silently.
        sheet = st.get('sheet') or ''
        if PREFLIGHT_DIR not in sheet or NEW_VER not in sheet:
            raise SystemExit('FATAL not the pre-flight copy — stylesheet is %r. '
                             'A wrong header order silently serves the live theme.'
                             % sheet)
        return st

    def wheel(self, dy):
        run(['agent-browser', 'mouse', 'wheel', str(dy)])
        time.sleep(0.25)

    def hit(self, x, y, want):
        """What a click at (x, y) actually lands on, and whether it is the target.

        A click on the capsule lands on the label span inside it, not on the
        <a>: asking elementFromPoint() for the exact element is too strict and
        reports a miss for a click that works. What matters is that the point
        is inside the target's own subtree — still a strong check, because a
        layout shift that moves another element under the cursor fails it.
        """
        return ev("(() => { const e = document.elementFromPoint(%d, %d);"
                  " if (!e) return {ok: false, what: null};"
                  " const t = e.closest('.%s');"
                  " return {ok: !!t, what: e.tagName + '|' + (e.className || ''),"
                  " owner: t ? (t.className || '') : null}; })()"
                  % (x, y, want))

    def box_of(self, selector):
        box = ev("(() => { const e = document.querySelector(%s); if (!e) return null;"
                 " const r = e.getBoundingClientRect();"
                 " return {x: Math.round(r.left), y: Math.round(r.top),"
                 " w: Math.round(r.width), h: Math.round(r.height)}; })()"
                 % jsstr(selector))
        return box if isinstance(box, dict) and box.get('w') else None

    def click_capsule(self, tag):
        """The capsule's box, re-read immediately before the click.

        Never reuse a box read a step earlier: the modal's own body scrolls,
        the reveal moves the stack, and a stale coordinate is the one failure
        mode that produces a *pass* by clicking something that happens to be
        inert.
        """
        st = ev(STATE)
        if st.get('capHidden') or not st.get('capBox') or not st['capBox']['w']:
            self.fail('%s: the capsule is not clickable (hidden=%s box=%s)'
                      % (tag, st.get('capHidden'), st.get('capBox')))
            return False
        return self.click_at(st['capBox'], 'sf-float-btn--inquiry', tag)

    def click_selector(self, selector, want, tag):
        run(['agent-browser', 'scrollintoview', selector])
        time.sleep(0.25)
        box = self.box_of(selector)
        if not box:
            self.fail('%s: %s has no box' % (tag, selector))
            return False
        return self.click_at(box, want, tag)


    def click_at(self, box, want, what):
        """Real mouse click, with the hit test the last batches learned to do.

        A lazy-loading image shifting the layout after the coordinates were
        computed turns a click into a click on whatever moved into that spot;
        the test then passes or fails for the wrong reason. Check, move,
        check again, then press.
        """
        x = box['x'] + max(1, box['w'] // 2)
        y = box['y'] + max(1, box['h'] // 2)
        got = self.hit(x, y, want)
        if not got or not got.get('ok'):
            self.fail('%s: (x=%d,y=%d) resolves to %r, which is not inside .%s'
                      % (what, x, y, (got or {}).get('what'), want))
            return False
        run(['agent-browser', 'mouse', 'move', str(x), str(y)])
        got2 = self.hit(x, y, want)
        if got2 != got:
            self.fail('%s: the hit target changed under the cursor (%r -> %r)'
                      % (what, got, got2))
            return False
        run(['agent-browser', 'mouse', 'down'])
        run(['agent-browser', 'mouse', 'up'])
        time.sleep(0.45)
        return True

    def errors(self):
        rc, out, _ = run(['agent-browser', 'errors'])
        t = out.strip()
        if not t or t.lower() in ('no errors', 'none', '[]'):
            return []
        try:
            return json.loads(t)
        except Exception:
            return [t]

    def shot(self, name):
        path = os.path.join(self.out, name)
        run(['agent-browser', 'screenshot', path])
        if os.path.exists(path):
            n = os.path.getsize(path)
            if n < 8000:
                self.fail('screenshot %s is %d bytes — under the 8000 floor'
                          % (name, n))
        return path

    # ------------------------------------------------------------- helpers

    def rockers_key(self, st):
        """The three pre-existing buttons as a comparable tuple."""
        return [(r['cls'], r['box']['x'], r['box']['y'], r['box']['w'], r['box']['h'])
                for r in st['rockers']]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--auth', default=os.environ.get('SF_DEV_AUTH',
                                                     'sfdev:VkEws18Kl5V1qp3TpZ6s'))
    ap.add_argument('--skip-mail', action='store_true',
                    help='skip E7, the one check that sends a real message')
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    p = Pass(args.auth, args.out)
    p.attach()

    # ------------------------------------------------------------------ E1 --
    # The reveal, driven by real wheel events rather than by scrollTo, so what
    # is being tested is the listener a visitor actually triggers.
    print('E1  the capsule appears once the band is reached, and stays')
    st0 = p.goto(DETAIL_2ROW, 'e1', wait=1.0)
    p.data['E1_top'] = st0
    if not st0['capPresent']:
        p.fail('E1: no capsule on a detail page')
    elif not (st0['capHidden'] and st0['capDisplay'] == 'none'):
        p.fail('E1: the capsule is shown at the top of the page (hidden=%s display=%s)'
               % (st0['capHidden'], st0['capDisplay']))
    elif st0['bandTop'] is not None and st0['bandTop'] <= st0['vh'] * 0.5:
        p.fail('E1: the band starts already inside the reveal threshold '
               '(bandTop=%s, vh=%s) — this page cannot test the reveal'
               % (st0['bandTop'], st0['vh']))
    else:
        p.ok('E1 at the top: capsule hidden, bandTop=%d beyond the %d threshold'
             % (st0['bandTop'], st0['vh'] // 2))

    before = p.rockers_key(st0)
    if len(st0['rockers']) != 3:
        p.fail('E1: %d pre-existing float buttons, expected 3' % len(st0['rockers']))

    # Walk down in wheel steps, stopping as soon as the band crosses the
    # threshold — and check that the capsule is still hidden one step before.
    stepped, mid_hidden = 0, None
    st = st0
    for _ in range(40):
        if st['bandTop'] is not None and st['bandTop'] <= st['vh'] * 0.5:
            break
        p.wheel(400)
        stepped += 1
        prev = st
        st = ev(STATE)
        if st['bandTop'] is not None and st['bandTop'] > st['vh'] * 0.5 \
                and prev['bandTop'] is not None and prev['bandTop'] > st['vh'] * 0.5:
            mid_hidden = st['capHidden']
    p.data['E1_steps'] = stepped
    p.data['E1_band'] = st

    if stepped == 0:
        p.fail('E1: the band never crossed the threshold')
    elif mid_hidden is False:
        p.fail('E1: the capsule was already shown while the band was still '
               'below the threshold — the trigger is early')
    elif mid_hidden is None:
        p.note('E1 the page was short enough that no intermediate state was '
               'observed; the threshold crossing is still asserted')
    else:
        p.ok('E1 mid-scroll: capsule still hidden while the band was below the threshold')

    if st['capHidden']:
        p.fail('E1: the band crossed the threshold (bandTop=%s, vh=%s) and the '
               'capsule is still hidden' % (st['bandTop'], st['vh']))
    elif st['capDisplay'] == 'none' or not st['capBox'] or st['capBox']['w'] == 0:
        p.fail('E1: `hidden` is off but the capsule has no box (%s)' % st['capBox'])
    elif not st['capIsVisible']:
        p.fail('E1: the capsule is missing the is-visible class')
    else:
        p.ok('E1 after %d wheel step(s): capsule visible, box %dx%d'
             % (stepped, st['capBox']['w'], st['capBox']['h']))

    # One-way: scroll well past and back to the top; it must not blink out.
    p.wheel(2000)
    p.wheel(-9000)
    time.sleep(0.4)
    st = ev(STATE)
    if st['scrollY'] > 20:
        p.note('E1 could not return to the top (scrollY=%s); one-way check is partial'
               % st['scrollY'])
    if st['capHidden'] or not st['capIsVisible']:
        p.fail('E1: the capsule disappeared again after scrolling back up '
               '(hidden=%s is-visible=%s)' % (st['capHidden'], st['capIsVisible']))
    else:
        p.ok('E1 one-way: still visible at scrollY=%d after scrolling back up' % st['scrollY'])

    # ------------------------------------------------------------------ E2 --
    print('E2  the four buttons: one column, same right edge, same gap')
    p.data['E2'] = st
    after = p.rockers_key(st)
    if len(after) != len(before) or after != before:
        p.fail('E2: revealing the capsule moved the pre-existing buttons: %s -> %s'
               % (before, after))
    else:
        p.ok('E2 the three pre-existing buttons hold their exact boxes: %s'
             % ', '.join('%s(%d,%d)' % (c, x, y) for c, x, y, w, h in after))

    if not st['capFirstChild']:
        p.fail('E2: the capsule is not the stack\'s first child')
    else:
        p.ok('E2 the capsule is the stack\'s first element child (dir=%s, gap=%s)'
             % (st['stackDir'], st['stackGap']))

    boxes = [r['box'] for r in st['rockers']] + [st['capBox']]
    kids = [b for b in boxes if b and b['w'] > 0]
    circle_sizes = sorted({r['box']['w'] for r in st['rockers']})
    if len(kids) != 4:
        p.fail('E2: only %d of the four buttons have a box' % len(kids))
    else:
        rights = {b['right'] for b in kids}
        if len(rights) != 1:
            p.fail('E2: the buttons no longer share a right edge: %s (offsets from '
                   'the viewport right)' % sorted(rights))
        elif circle_sizes != [52]:
            p.fail('E2: the three circle buttons are %s wide, expected 52'
                   % circle_sizes)
        elif st['capBox']['w'] <= 52:
            p.fail('E2: the capsule is %dpx wide — it did not hug its label'
                   % st['capBox']['w'])
        else:
            col = sorted(kids, key=lambda b: b['y'])
            gaps = [col[i + 1]['y'] - (col[i]['y'] + col[i]['h']) for i in range(3)]
            if any(g != 12 for g in gaps):
                p.fail('E2: the vertical gaps are %s, expected 12px' % gaps)
            elif col[0] is not st['capBox']:
                p.fail('E2: the capsule is not the topmost button (its y=%d)'
                       % st['capBox']['y'])
            else:
                p.ok('E2 four buttons on one right edge (%dpx from the right), '
                     'three 52px circles and a %dpx capsule, gaps %s, capsule '
                     'topmost at y=%d'
                     % (rights.pop(), st['capBox']['w'], gaps, st['capBox']['y']))

    if st['capHref'] and 'contact' not in st['capHref']:
        p.fail('E2: the no-JS fallback href is %r' % st['capHref'])
    elif st['capText'] != 'Send Inquiry':
        p.fail('E2: the capsule label is %r' % st['capText'])
    else:
        p.ok('E2 label %r, fallback %s' % (st['capText'], st['capHref']))

    # ------------------------------------------------------------------ E3 --
    print('E3  the dialog opens')
    p.click_capsule('E3 capsule click')
    st = ev(STATE)
    p.data['E3_open'] = st
    if st['modalHidden'] or not st['modalOpen']:
        p.fail('E3: the dialog did not open (hidden=%s is-open=%s)'
               % (st['modalHidden'], st['modalOpen']))
    else:
        p.ok('E3 open: hidden off, is-open on, display=%s' % st['modalDisplay'])
    if not st['lock']:
        p.fail('E3: the body lock class is missing')
    else:
        p.ok('E3 the body is locked while the dialog is up')
    if st['panelRole'] != 'dialog' or st['panelAriaModal'] != 'true':
        p.fail('E3: panel role=%r aria-modal=%r' % (st['panelRole'], st['panelAriaModal']))
    else:
        p.ok('E3 the panel is role=dialog aria-modal=true')
    if not st['focus'] or not st['focus']['inModal']:
        p.fail('E3: focus did not move into the dialog (%s)' % (st['focus'],))
    else:
        p.ok('E3 focus moved to <%s name=%s> inside the panel'
             % (st['focus']['tag'].lower(), st['focus']['name']))
    if st['panelBox'] and st['panelBox']['w'] and abs(st['panelBox']['w'] - 560) > 8:
        p.note('E3 panel width is %dpx (the design table says 560)' % st['panelBox']['w'])
    else:
        p.ok('E3 panel is %dpx wide, %dpx tall, radius %s'
             % (st['panelBox']['w'], st['panelBox']['h'], st['panelRadius']))

    if st['terms'] != ['Piece Weight', 'Pack Size']:
        p.fail('E3 E9: the selection rows are %s, expected [Piece Weight, Pack Size]'
               % st['terms'])
    elif not all(v.strip() for v in st['values']):
        p.fail('E3: a selection row has an empty value: %s' % st['values'])
    else:
        p.ok('E3 E9 two rows from the record: %s'
             % ' | '.join('%s = %s' % (t, v) for t, v in zip(st['terms'], st['values'])))
    if st['stepCount'] != 4 or len(st['stepTitles']) != 4:
        p.fail('E3: the sampling panel has %d steps' % st['stepCount'])
    else:
        p.ok('E3 the four shared sampling steps: %s' % ' / '.join(st['stepTitles']))
    if not st['formulaValue'].isdigit() or int(st['formulaValue'] or 0) <= 0:
        p.fail('E3: the form carries no post id (%r) — the server cannot rebuild '
               'the selection' % st['formulaValue'])
    else:
        p.ok('E3 the form carries post id %s' % st['formulaValue'])
    p.shot('h4-e3-desktop-open.png')

    # ------------------------------------------------------------------ E4 --
    print('E4  the closes')
    run(['agent-browser', 'press', 'Escape'])
    time.sleep(0.5)
    st = ev(STATE)
    p.data['E4_esc'] = st
    if not st['modalHidden'] or st['modalOpen']:
        p.fail('E4 Escape: the dialog is still up (hidden=%s is-open=%s)'
               % (st['modalHidden'], st['modalOpen']))
    elif st['lock']:
        p.fail('E4 Escape: the body is still locked')
    elif not st['focus'] or 'inquiry' not in (st['focus']['cls'] or ''):
        p.fail('E4 Escape: focus was not returned to the capsule (%s)' % (st['focus'],))
    else:
        p.ok('E4 Escape closes it, unlocks the body and returns focus to the capsule')

    p.click_capsule('E4 reopen')
    st = ev(STATE)
    if st['modalHidden']:
        p.fail('E4: the dialog did not reopen')
    else:
        # A click inside the panel must not close it.
        inner = st['panelBox']
        p.click_at({'x': inner['x'] + 20, 'y': inner['y'] + 14,
                    'w': 8, 'h': 8}, 'sf-inquiry-modal__title', 'E4 inner click')
        st2 = ev(STATE)
        if st2['modalHidden']:
            p.fail('E4: a click inside the panel closed the dialog')
        else:
            p.ok('E4 a click inside the panel leaves it open')
        # The backdrop is the dialog's own outer box: aim at the far corner.
        p.click_at({'x': 4, 'y': 4, 'w': 8, 'h': 8}, 'sf-inquiry-modal',
                   'E4 backdrop click')
        st3 = ev(STATE)
        if not st3['modalHidden']:
            p.fail('E4: a click on the backdrop did not close the dialog')
        elif st3['lock']:
            p.fail('E4 backdrop: the body is still locked')
        else:
            p.ok('E4 the backdrop click closes it and unlocks the body')

    # ------------------------------------------------------------------ E5 --
    print('E5  the honeypot is checked first')
    p.click_capsule('E5 reopen')
    res = ev(INJECT % (jsstr('Sino Fresh E2E'), jsstr('e2e@example.com'),
                       jsstr('Sino Fresh'), jsstr('CN'),
                       jsstr('[%s] honeypot probe — please ignore' % MAIL_TAG),
                       jsstr('http://spam.example'),
                       "const t = form.querySelector('[name=\"ts\"]');"
                       " if (t) t.value = String(Date.now() - 10000);"))
    sub = ev(SUBMIT)
    p.data['E5'] = {'inject': res, 'submit': sub}
    time.sleep(1.2)
    st = ev(STATE)
    p.data['E5_state'] = st
    if 'rejected' in st['status'].lower():
        p.ok('E5 the honeypot is refused before anything else: %r' % st['status'])
    elif not st['status']:
        p.fail('E5 the honeypot produced no response at all (status is empty)')
    else:
        p.fail('E5 the honeypot was not refused: status is %r' % st['status'])
    if not st['successHidden']:
        p.fail('E5 a honeypot submission reached the success state')
    if st['formHidden']:
        p.fail('E5 the form was hidden by a honeypot submission')

    # ------------------------------------------------------------------ E6 --
    print('E6  the three-second floor')
    p.click_capsule('E6 reopen')
    res = ev(INJECT % (jsstr('Sino Fresh E2E'), jsstr('e2e@example.com'),
                       jsstr('Sino Fresh'), jsstr('CN'),
                       jsstr('[%s] speed probe — please ignore' % MAIL_TAG),
                       jsstr(''), ''))
    sub = ev(SUBMIT)
    delta = sub.get('delta')
    p.data['E6'] = {'inject': res, 'submit': sub}
    time.sleep(1.2)
    st = ev(STATE)
    p.data['E6_state'] = st
    if delta is None or delta >= 3000:
        p.fail('E6: the submission was %sms after the stamp, not under the 3000ms '
               'floor — the check did not test what it claims' % delta)
    elif 'take a moment' in st['status'].lower():
        p.ok('E6 refused at %dms since the dialog opened: %r' % (delta, st['status']))
    else:
        p.fail('E6: submitted %dms after the stamp and the answer was %r'
               % (delta, st['status']))
    if not st['successHidden']:
        p.fail('E6 an impossibly fast submission reached the success state')
    if not st['formHidden']:
        p.ok('E6 the form survives a rejection, ready for the visitor to retry')

    # ------------------------------------------------------------------ E7 --
    print('E7  a real submission, and the self-close')
    if args.skip_mail:
        p.note('E7 skipped by --skip-mail: the delivery path was not exercised')
    else:
        st = ev(STATE)
        # The client re-stamps on failure, so the clock has to be allowed to
        # pass again before the real attempt.
        time.sleep(3.4)
        run(['agent-browser', 'fill', 'input[name="name"]', 'Sino Fresh E2E'])
        run(['agent-browser', 'fill', 'input[name="email"]', 'sales@zxpet.com'])
        run(['agent-browser', 'fill', 'input[name="company"]', 'Sino Fresh (internal test)'])
        run(['agent-browser', 'fill', 'input[name="country"]', 'CN'])
        run(['agent-browser', 'fill', 'textarea[name="message"]',
             '[%s] automated end-to-end check from the pre-flight copy. '
             'If you are reading this, the inquiry path delivered a lead.'
             % MAIL_TAG])
        st = ev(STATE)
        filled = st['tsValue']
        if not p.click_selector('.sf-inquiry-form__submit',
                                'sf-inquiry-form__submit', 'E7 submit'):
            p.fail('E7: could not land the click on Submit')
        else:
            ok_seen = False
            for _ in range(20):
                time.sleep(0.3)
                st = ev(STATE)
                if not st['successHidden']:
                    ok_seen = True
                    break
            p.data['E7_state'] = st
            if not ok_seen:
                p.fail('E7: the success panel never appeared (status %r)'
                       % st['status'])
            elif not st['formHidden']:
                p.fail('E7: the success panel is up but the form is still there')
            else:
                p.mail_sent = True
                p.ok('E7 delivered: %r (form replaced, ts stamped %s)'
                     % ((st['successText'] or '')[:70], filled))
                p.shot('h4-e7-desktop-success.png')
            # The dialog closes itself three seconds after success.
            t0 = time.time()
            closed_at = None
            for _ in range(24):
                time.sleep(0.25)
                st = ev(STATE)
                if st['modalHidden']:
                    closed_at = time.time() - t0
                    break
            p.data['E7_close_after'] = closed_at
            if closed_at is None:
                p.fail('E7: the dialog never closed itself after success')
            elif not (2.2 <= closed_at <= 4.6):
                p.fail('E7: the dialog closed %0.1fs after success, expected ~3s'
                       % closed_at)
            else:
                p.ok('E7 the dialog closed itself %0.1fs after the confirmation'
                     % closed_at)
            # Reopening after a success: the modal state is never reset, so the
            # visitor sees the confirmation rather than an empty form. Not a
            # defect this batch created (nothing resets it), but worth a note.
            if p.click_capsule('E7 reopen after success'):
                st = ev(STATE)
                if st['formHidden'] and not st['successHidden']:
                    p.note('E7 reopening after a success shows the confirmation, not '
                           'an empty form — flagged for H6 (no reset path exists)')
                p.click_at({'x': 4, 'y': 4, 'w': 8, 'h': 8}, 'sf-inquiry-modal',
                           'E7 close again')

    # ------------------------------------------------------------------ E10 --
    # Before leaving this page: the same four buttons on a phone.
    print('E10 the phone: 44px targets in a 16px gutter, panel as a bottom sheet')
    st = p.goto(DETAIL_2ROW, 'e10', width=390, height=844, wait=1.0)
    for _ in range(40):
        if st['bandTop'] is not None and st['bandTop'] <= st['vh'] * 0.5:
            break
        p.wheel(400)
        st = ev(STATE)
    p.data['E10'] = st
    if st['capHidden']:
        p.fail('E10: the capsule never revealed at 390px wide')
    else:
        circles = sorted({r['box']['w'] for r in st['rockers']})
        rights = {r['box']['right'] for r in st['rockers']} | {st['capBox']['right']}
        if circles != [44]:
            p.fail('E10: the circle buttons at 390px are %s wide, expected 44'
                   % circles)
        elif rights != {16}:
            p.fail('E10: the right gutter at 390px is %s, expected 16 '
                   '(circles and capsule together)' % sorted(rights))
        else:
            p.ok('E10 three 44px circles and a %dpx capsule, all 16px from the '
                 'right edge, at 390x844' % st['capBox']['w'])
    p.shot('h4-e10-mobile-capsule.png')
    if st['capBox']:
        p.click_capsule('E10 capsule click')
        st = ev(STATE)
        p.data['E10_open'] = st
        if st['modalHidden']:
            p.fail('E10: the dialog does not open on a phone')
        else:
            pb = st['panelBox']
            if pb['w'] < st['vw'] - 2 or pb['y'] + pb['h'] < st['vh'] - 4:
                p.fail('E10: the panel is not a full-width bottom sheet: %s in %sx%s'
                       % (pb, st['vw'], st['vh']))
            else:
                p.ok('E10 the panel fills the width and is anchored to the bottom: '
                     '%dx%d at y=%d of %d' % (pb['w'], pb['h'], pb['y'], st['vh']))
            p.shot('h4-e10-mobile-sheet.png')
        run(['agent-browser', 'press', 'Escape'])
        time.sleep(0.4)

    # ------------------------------------------------------------------ E9 --
    print('E9  one row where the record has one')
    st = p.goto(DETAIL_1ROW, 'e9', wait=1.0)
    for _ in range(40):
        if st['bandTop'] is not None and st['bandTop'] <= st['vh'] * 0.5:
            break
        p.wheel(400)
        st = ev(STATE)
    p.click_capsule('E9 capsule click')
    st = ev(STATE)
    p.data['E9'] = st
    if st['terms'] != ['Piece Weight']:
        p.fail('E9 %s: the selection rows are %s, expected [Piece Weight]'
               % (PRODUCT_1ROW, st['terms']))
    else:
        p.ok('E9 one row on %s: %s' % (PRODUCT_1ROW, st['values']))
    if st['stepCount'] != 4:
        p.fail('E9: the sampling panel lost its steps on the one-row page')
    run(['agent-browser', 'press', 'Escape'])
    time.sleep(0.3)

    # --------------------------------------------------------------- E8/ZH --
    print('E8  the ZH page carries the same widget')
    st = p.goto(DETAIL_ZH, 'e8', wait=1.0)
    for _ in range(40):
        if st['bandTop'] is not None and st['bandTop'] <= st['vh'] * 0.5:
            break
        p.wheel(400)
        st = ev(STATE)
    p.data['E8_zh'] = st
    if not st['capPresent'] or st['capHidden']:
        p.fail('E8 the ZH detail page has no revealed capsule')
    else:
        p.ok('E8 ZH: capsule %r joins the stack' % st['capText'])
    p.click_capsule('E8 capsule click')
    st = ev(STATE)
    if st['modalHidden'] or st['stepCount'] != 4:
        p.fail('E8 the ZH dialog did not open intact (hidden=%s steps=%d)'
               % (st['modalHidden'], st['stepCount']))
    else:
        p.ok('E8 ZH dialog opens with %d rows and %d shared steps'
             % (len(st['terms']), st['stepCount']))
    run(['agent-browser', 'press', 'Escape'])
    time.sleep(0.3)

    print('E8  the plain pages carry none of it')
    st = p.goto(PLAIN, 'e8plain', wait=0.9)
    p.data['E8_plain'] = st
    if st['capPresent'] or st['modalPresent']:
        p.fail('E8 %s: the capsule or dialog is emitted off a formula page '
               '(capsule=%s modal=%s)' % (PLAIN, st['capPresent'], st['modalPresent']))
    elif st['hasScript']:
        p.fail('E8 %s: inquiry.js is enqueued off a formula page' % PLAIN)
    else:
        p.ok('E8 %s: no capsule, no dialog, no inquiry.js' % PLAIN)

    # ------------------------------------------------------------------ E11 --
    print('E11 console errors')
    errs = p.errors()
    if errs:
        for e in errs[:5]:
            p.fail('E11 console: %s' % e)
    else:
        p.ok('E11 no console errors on any page visited')

    print('-' * 72)
    if p.fails:
        print('VERDICT: FAIL — %d ok, %d FAIL' % (len(p.notes), len(p.fails)))
        rc = 1
    else:
        print('VERDICT: PASS — %d ok, 0 FAIL' % len(p.notes))
        rc = 0
    if p.mail_sent:
        print('NOTE: one real test message was sent to the sf_contact_email '
              'inbox (marker "%s").' % MAIL_TAG)
    with open(os.path.join(args.out, 'e2e-measurements.json'), 'w',
              encoding='utf-8') as fh:
        json.dump({'fails': p.fails, 'notes': p.notes, 'data': p.data,
                   'mail_sent': p.mail_sent}, fh, indent=2, ensure_ascii=False)
    return rc


if __name__ == '__main__':
    sys.exit(main())

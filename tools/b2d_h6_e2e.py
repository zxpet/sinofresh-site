#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H6 — the functional pass on the candidate: does the rewritten button still work?

WHY A BROWSER PASS EXISTS FOR A JS DELETION

formulas.js lost 21 lines (116 -> 95): a sessionStorage write with no reader and
a scroll branch whose target no template carries. The byte gate cannot see any
of that — the file is enqueued by URL, so its contents never appear in a
capture. What the capture can prove is only that the *token* moved.

The deletion is also the kind that fails quietly. A script with a syntax error, or
a handler that throws on the now-absent `#configurator`, would leave the button
looking perfect in the markup and dead in the browser, and the 75-page byte proof
would be green throughout.

WHAT IS ASSERTED, AND WHAT IS ACCEPTED

The copy path has two branches and the handler's toast says which one ran: the
success text, or "Copy unavailable". The click must leave the page on one of
them — no toast at all is what a broken handler produces.

THE CLIPBOARD CANNOT BE READ BACK HERE, AND THAT IS MEASURED, NOT ASSUMED

The obvious check — click, then read the clipboard and compare — is not
available in this context, and both halves of that were established by
experiment before this file was written (tools/_h6_clip_probe.py,
tools/_h6_clip_probe2.py):

  * `navigator.clipboard.writeText` REJECTS with NotAllowedError when called
    from an eval (no transient user activation), and RESOLVES after a real
    mouse click. So the write is activation-gated, and the E2E's click has it.
  * every read-back channel is permission-denied: `readText` in the page,
    `agent-browser clipboard read`, and the CLI's own paste all come back
    empty/NotAllowedError. `clipboard-write` is auto-granted, `clipboard-read`
    is not, and nothing in the CLI grants it.

So the toast branch IS the observable, and it is a real one — `writeText(...)
.then(onDone, onFail)` routes a rejection to the other message. That the toast
discriminates is then not taken on faith either: [E11b] stubs `writeText` to
reject and requires the OTHER toast. What is asserted at [E9] is therefore
"the click drove the handler onto the success branch", and the unreadable
clipboard is printed as a stated limitation, not silently passed over.

expected() DOES NOT COME FROM MEMORY

[E1] compares the button count against the frozen baseline capture, not against
a number written down here: /products/soft-chews/ is a dosage landing page and
carries only the soft-chew formulas (4), while /formulas/ carries all 21. The
first run of this file asserted 21 in both places and was wrong about the page
it was looking at — a number typed in from expectation is how that happens.

The removals are asserted directly rather than inferred: after a click,
sessionStorage must hold no `sinofresh_formula_*` key (the write is gone), the
document must contain no `#configurator` (the branch has nothing to find), and
scrollY must not move (the branch is gone, so nothing scrolls).

usage:
    b2d_h6_e2e.py --out _backup/b2d-h6-e2e.json [--auth user:pass]
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
DESKTOP = (1440, 900)
DOSE = '/products/soft-chews/'
DOSE_CAPTURE = 'products__soft-chews'
DETAIL = '/formulas/joint-support-soft-chews/'
DETAIL_ZH = '/zh/formulas/joint-support-soft-chews/'
ARCHIVE = '/formulas/'
ARCHIVE_CAPTURE = 'formulas'

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BASE_CAPTURE = os.path.join(ROOT, '_backup', 'b2d-h6-baselines')
BASELINE_SHA = '084b24692e716b62514ab9190f88ead1e38e5944'

SUCCESS_TOAST = 'Formula name copied. Paste it in your inquiry.'
FALLBACK_TOAST = 'Copy unavailable'


def baseline_cta_count(capture):
    """How many CTAs the frozen baseline capture of a page carries.

    The expectation is read out of the evidence rather than typed in, and the
    capture is the pre-flight copy of the batch's own baseline commit, so the
    number and the thing it is compared against come from the same site.
    """
    path = os.path.join(BASE_CAPTURE, capture + '.html')
    with open(path, encoding='utf-8') as fh:
        return len(re.findall(r'class="sf-formula__cta', fh.read()))

PROBE = r"""
(() => {
  try {
    const sheet = (document.querySelector("link[href*='style.css']") || {}).href || '';
    const ld = [];
    document.querySelectorAll('script[type="application/ld+json"]').forEach(s => {
      let ok = false, items = null, type = null;
      try { const j = JSON.parse(s.textContent); ok = true; type = j['@type'] || null;
            if (j.itemListElement) items = j.itemListElement.length; } catch (e) {}
      ld.push({ok: ok, type: type, items: items});
    });
    const cta = document.querySelector('.sf-formula__cta');
    const title = document.querySelector('.sf-fdetail2__title');
    return {
      sheet: sheet,
      vw: window.innerWidth,
      url: location.pathname,
      ldJson: ld,
      payload: document.querySelectorAll('script.sf-formulas-data').length,
      payloadByClass: (document.documentElement.innerHTML.match(/class="sf-formulas-data"/g) || []).length,
      ctaCount: document.querySelectorAll('.sf-formula__cta').length,
      ctaName: cta ? cta.getAttribute('data-formula') : null,
      ctaForm: cta ? cta.getAttribute('data-form') : null,
      configurator: document.querySelectorAll('#configurator').length,
      h1: document.querySelectorAll('h1').length,
      sideH1: document.querySelectorAll('h1.sf-fdetail2__title').length,
      titleText: title ? title.textContent.trim() : null,
      pills: document.querySelectorAll('.sf-actives__pill').length,
      labels: document.querySelectorAll('.sf-actives__label').length,
      ing: document.querySelectorAll('.sf-actives__ing').length,
      fgrid: document.querySelectorAll('.sf-fgrid').length,
      fcard: document.querySelectorAll('.sf-fcard').length,
      fjs: !!document.getElementById('sinofresh-formulas-js'),
      toast: (document.querySelector('.sf-toast') || {}).textContent || null,
      scrollY: Math.round(window.scrollY),
    };
  } catch (e) {
    return {error: String(e && e.message ? e.message : e)};
  }
})()
"""


def run(cmd, timeout=240):
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return p.returncode, (p.stdout or '').strip(), (p.stderr or '').strip()


def ev(script, timeout=240):
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


class Rep(object):
    def __init__(self):
        self.rows = []

    def ok(self, label, cond, detail=''):
        self.rows.append({'label': label, 'ok': bool(cond), 'detail': str(detail)})
        print('  %s  %-62s %s' % ('ok  ' if cond else 'FAIL', label, detail))
        return bool(cond)

    def eq(self, label, got, want):
        return self.ok(label, got == want, 'got %r want %r' % (got, want))


class E2E(object):
    def __init__(self, auth):
        self.auth = auth
        self.errors = []

    def attach(self):
        b64 = base64.b64encode(self.auth.encode('utf-8')).decode('ascii')
        user, _, pw = self.auth.partition(':')
        run(['agent-browser', 'close', '--all'])
        rc, out, err = run(['agent-browser', 'set', 'credentials', user, pw])
        if rc != 0:
            raise SystemExit('FATAL set credentials: %s %s' % (out, err))
        rc, out, err = run(['agent-browser', 'open', HOST + '/'])
        if rc != 0:
            raise SystemExit('FATAL open: %s %s' % (out, err))
        hdrs = json.dumps({'Authorization': 'Basic ' + b64, 'X-SF-Preflight': '1'})
        run(['agent-browser', 'set', 'headers', hdrs])
        run(['agent-browser', 'errors', '--clear'])
        run(['agent-browser', 'console', '--clear'])

    def goto(self, path, tag):
        url = HOST + path + '?sfe2e=%s%s' % (tag, time.strftime('%H%M%S'))
        st = None
        for attempt in (1, 2, 3):
            run(['agent-browser', 'open', url])
            run(['agent-browser', 'reload'])          # reload keeps the header
            run(['agent-browser', 'set', 'viewport', str(DESKTOP[0]), str(DESKTOP[1])])
            time.sleep(0.8)
            st = ev(PROBE)
            if isinstance(st, dict) and 'error' in st:
                self.errors.append((path, 'probe: %s' % st['error']))
                st = None
                time.sleep(0.8)
                continue
            sheet = (st or {}).get('sheet') or ''
            if PREFLIGHT_DIR in sheet and 'ver=2.10.61' in sheet:
                return st
            print('   ..   %s attempt %d served %r' % (path, attempt, sheet or 'no sheet'))
            time.sleep(0.8)
        raise SystemExit('FATAL not the pre-flight copy at ver=2.10.61 on %s (sheet=%r)'
                         % (path, (st or {}).get('sheet')))

    def click_cta(self, sel, stub_write_fail=False):
        """Real click: scroll it in, hit-check, then a mouse press/release.

        The click target is below the fold on every page that carries it, and a
        coordinate taken before the lazy-loaded images settle lands on whatever
        moved into that spot — so the hit check runs immediately before the
        press, against the coordinates actually used.

        The scroll offset is read AFTER the scrollIntoView and immediately
        before the press. Reading it any earlier measures this method's own
        scrolling rather than the page's response to the click, which is what
        the caller is asking about (the deleted #configurator branch used to
        scroll, so a surviving scroll would be the regression).

        stub_write_fail installs the negative control: a `writeText` that
        rejects, which must produce the OTHER toast.
        """
        run(['agent-browser', 'scrollintoview', sel])
        time.sleep(0.4)
        if stub_write_fail:
            ev("navigator.clipboard.writeText = function(){"
               "return Promise.reject(new Error('h6 negative control')); };")
        box = ev("(()=>{const e=document.querySelector(%s);if(!e)return null;"
                 "const r=e.getBoundingClientRect();"
                 "return {x:Math.round(r.x+r.width/2),y:Math.round(r.y+r.height/2),"
                 "w:Math.round(r.width),h:Math.round(r.height)};})()" % json.dumps(sel))
        if not box:
            return None
        hit = ev("(()=>{const e=document.elementFromPoint(%d,%d);"
                 "return e?(e.className||'')+'|'+(e.tagName||''):null;})()"
                 % (box['x'], box['y']))
        if not hit or 'sf-formula__cta' not in str(hit):
            return {'box': box, 'hit': None, 'err': 'hit check failed: %r' % (hit,),
                    'scroll_before': None}
        scroll_before = ev('Math.round(window.scrollY)')
        run(['agent-browser', 'mouse', 'move', str(box['x']), str(box['y'])])
        run(['agent-browser', 'mouse', 'down'])
        run(['agent-browser', 'mouse', 'up'])
        time.sleep(0.7)
        return {'box': box, 'hit': str(hit), 'err': None,
                'scroll_before': scroll_before}

    def clipboard(self):
        rc, out, _ = run(['agent-browser', 'clipboard', 'read'])
        return out if rc == 0 else ''

    def session_storage(self):
        rc, out, _ = run(['agent-browser', 'storage', 'session'])
        return out if rc == 0 else ''

    def page_errors(self):
        rc, out, _ = run(['agent-browser', 'errors'])
        if rc != 0:
            return ['<errors command failed>']
        t = out.strip()
        if not t or t.lower() in ('no errors', 'none', '[]'):
            return []
        return [t]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='_backup/b2d-h6-e2e.json')
    ap.add_argument('--auth', default=os.environ.get('SF_DEV_AUTH') or
                    'sfdev:VkEws18Kl5V1qp3TpZ6s')
    args = ap.parse_args()

    rep = Rep()
    s = E2E(args.auth)
    s.attach()
    facts = {}

    # ---------------------------------------------------------- dosage page ---
    want = baseline_cta_count(DOSE_CAPTURE)
    print('== %s (a dosage landing page: %d cards, per the baseline capture) =='
          % (DOSE, want))
    st = s.goto(DOSE, 'dose')
    facts['dose'] = st
    facts['dose_cta_expected'] = want
    rep.eq('[E1] the card count matches the baseline capture', st['ctaCount'], want)
    rep.eq('[E2] the K2 payload is not in the DOM', st['payloadByClass'], 0)
    items = [b['items'] for b in st['ldJson'] if b.get('type') == 'ItemList']
    rep.eq('[E3] the ItemList still parses', items, [want])
    rep.eq('[E3] and there is exactly one of it', len(items), 1)
    rep.eq('[E4] every ld+json block parses', [b['ok'] for b in st['ldJson']],
           [True] * len(st['ldJson']))
    rep.eq('[E5] formulas.js is enqueued', st['fjs'], True)
    rep.eq('[E6] no #configurator on the page', st['configurator'], 0)

    name = st['ctaName']
    c = s.click_cta('.sf-formula__cta')
    st2 = ev(PROBE)
    clip = s.clipboard()
    stor = s.session_storage()
    print('   clicked %s at %s' % (c['hit'], c['box']))
    rep.ok('[E7] the click landed on the button', c['err'] is None, c['err'] or c['hit'])
    rep.ok('[E8] a toast appeared', bool(st2['toast']), repr(st2['toast'])[:70])
    rep.eq('[E9] the click drove the handler onto its success branch',
           st2['toast'], SUCCESS_TOAST)
    print('   note the clipboard itself is unreadable in this context '
          '(clipboard-read is permission-denied; see the module docstring) — '
          'the branch is the observable. cli read returned %r' % (clip[:30],))
    facts['copy_path'] = ('success-branch (unreadable)' if st2['toast'] == SUCCESS_TOAST
                          else 'fallback')
    rep.eq('[E10] the sessionStorage write is GONE',
           [k for k in re.findall(r'sinofresh_formula_[\w\-]*', stor)], [])
    rep.eq('[E11] the click did not scroll the page',
           st2['scrollY'] - (c['scroll_before'] or 0), 0)
    print('   scroll before press %r, after %r' % (c['scroll_before'], st2['scrollY']))

    # ---- negative control: the toast must discriminate ---------------------
    c = s.click_cta('.sf-formula__cta', stub_write_fail=True)
    st3 = ev(PROBE)
    rep.ok('[E11b] with writeText rejecting, the OTHER toast is the one shown',
           bool(st3['toast']) and FALLBACK_TOAST in (st3['toast'] or ''),
           '%r vs success %r' % ((st3['toast'] or '')[:46], SUCCESS_TOAST[:30]))
    rep.eq('[E11b] so [E9] is a discriminating signal, not a constant',
           bool(st3['toast'] and st3['toast'] != SUCCESS_TOAST)
           and st2['toast'] == SUCCESS_TOAST, True)
    facts['negctl_toast'] = st3['toast']

    # ---------------------------------------------------------- detail page ---
    print('== %s ==' % DETAIL)
    st = s.goto(DETAIL, 'detail')
    facts['detail'] = st
    rep.eq('[E12] exactly one h1', st['h1'], 1)
    rep.eq('[E12] it is the right-column title', st['sideH1'], 1)
    rep.ok('[E13] the hero CTA carries the formula name', bool(st['ctaName']), st['ctaName'])
    rep.eq('[E13] and the name equals the page title', st['ctaName'], st['titleText'])
    rep.eq('[E14] the K2 payload is not in the DOM', st['payloadByClass'], 0)
    rep.ok('[E15] the helper-dependent band still renders pills', st['pills'] > 0,
           'pills=%d ingredients=%d' % (st['pills'], st['ing']))
    rep.eq('[E15] both band labels are present', st['labels'], 2)
    rep.eq('[E16] no #configurator on the detail page', st['configurator'], 0)

    c = s.click_cta('.sf-formula__cta')
    st2 = ev(PROBE)
    print('   clicked %s at %s' % (c['hit'], c['box']))
    rep.ok('[E17] the click landed on the hero button', c['err'] is None,
           c['err'] or c['hit'])
    rep.ok('[E17] a toast appeared', bool(st2['toast']), repr(st2['toast'])[:70])
    rep.eq('[E18] the hero click drove the same success branch',
           st2['toast'], SUCCESS_TOAST)
    rep.eq('[E19] the click did not scroll the hero page',
           st2['scrollY'] - (c['scroll_before'] or 0), 0)

    # -------------------------------------------------------------- archive ---
    want = baseline_cta_count(ARCHIVE_CAPTURE)
    print('== %s (the archive: %d cards, per the baseline capture) =='
          % (ARCHIVE, want))
    st = s.goto(ARCHIVE, 'archive')
    facts['archive'] = st
    rep.eq('[E20] the card count matches the baseline capture', st['ctaCount'], want)
    rep.eq('[E20] one .sf-fgrid', st['fgrid'], 1)
    rep.eq('[E21] the K2 payload is not in the DOM', st['payloadByClass'], 0)
    items = [b['items'] for b in st['ldJson'] if b.get('type') == 'ItemList']
    rep.eq('[E21] the ItemList still parses over every card', items, [want])

    # -------------------------------------------------------------- zh page ---
    print('== %s ==' % DETAIL_ZH)
    st = s.goto(DETAIL_ZH, 'zh')
    facts['zh'] = st
    rep.eq('[E22] no #configurator', st['configurator'], 0)
    rep.ok('[E22] the zh detail page still renders its actives band', st['pills'] > 0,
           'pills=%d' % st['pills'])

    # ------------------------------------------------------------- console ---
    errs = s.page_errors()
    rep.eq('[E23] no page errors on any visited page', errs, [])
    rep.eq('[E23] no probe failures', s.errors, [])
    facts['page_errors'] = errs
    facts['probe_errors'] = s.errors

    run(['agent-browser', 'close', '--all'])

    fails = [r for r in rep.rows if not r['ok']]
    json.dump({'rows': rep.rows, 'fails': len(fails), 'facts': facts},
              open(args.out, 'w'), indent=1, ensure_ascii=False)
    print('\n%s  E2E: %d ok / %d FAIL  (copy path: %s)'
          % ('PASS' if not fails else 'FAIL', len(rep.rows) - len(fails), len(fails),
             facts.get('copy_path')))
    print('  json -> %s' % args.out)
    return 0 if not fails else 1


if __name__ == '__main__':
    sys.exit(main())

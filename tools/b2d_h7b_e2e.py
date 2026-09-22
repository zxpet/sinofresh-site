#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H7b — the browser pass.

Three things the byte gate cannot see, all of them about a click:

  * WHICH element a handler is bound to. H7b's 84 data-sf-inquiry-open
    occurrences are the same 84 whether inquiry.js binds both openers or only
    the first one, and only the second is a bug — the capsule would go inert
    with no error anywhere. So: click the capsule and require the dialog.
  * WHETHER both handlers fire on one element. formulas.js binds
    .sf-formula__cta globally; the hero CTA carries that class and now opens a
    dialog, so without the skip the click would toast AND open. A toast beside
    an open dialog is the failure, and no byte differs.
  * A GEOMETRY delta, which for H7b is not only the type size. The hero CTA
    stopped being a <button> and became an <a>, and a button does not inherit
    font-family while an anchor does — so the same 14px/600 text can render in a
    different face. `--mode geometry` measures that in whichever state is
    installed, so it can be run twice and compared.

usage:
    b2d_h7b_e2e.py --mode full               # candidate checks, desktop + phone
    b2d_h7b_e2e.py --mode geometry --tag before
"""
import argparse
import base64
import json
import os
import subprocess
import sys
import time

HOST = 'https://dev.zxpet.com'
PREFLIGHT_DIR = 'sinofresh-theme-preflight'
DESKTOP = (1440, 900)
PHONE = (420, 900)
DETAIL = '/formulas/joint-support-soft-chews/'
DETAIL_ZH = '/zh/formulas/joint-support-soft-chews/'
DOSAGE = '/products/soft-chews/'
DEFAULT_AUTH = 'sfdev:VkEws18Kl5V1qp3TpZ6s'
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


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
        print('  %s  %-58s %s' % ('ok  ' if cond else 'FAIL', label, detail))
        return bool(cond)

    def eq(self, label, got, want):
        return self.ok(label, got == want, 'got %r want %r' % (got, want))


PROBE = """
(()=>{const l=document.querySelector('link[rel=stylesheet][href*="sinofresh-theme"]');
return {sheet:l?l.getAttribute('href'):null,h1:document.querySelectorAll('h1').length};})()
"""

HERO_STATE = """
(()=>{
 const hero=document.querySelector('.sf-formula-hero__actions .sf-formula__cta--solid');
 const cap=document.querySelector('.sf-float-btn--inquiry');
 const all=[].slice.call(document.querySelectorAll('[data-sf-inquiry-open]'));
 const cards=[].slice.call(document.querySelectorAll('.sf-formula__cta'))
   .filter(e=>!e.hasAttribute('data-sf-inquiry-open'));
 const cs=hero?getComputedStyle(hero):null;
 return {
  heroTag: hero?hero.tagName:null,
  heroText: hero?hero.textContent.trim():null,
  heroHref: hero?hero.getAttribute('href'):null,
  heroHasAttr: hero?hero.hasAttribute('data-sf-inquiry-open'):null,
  heroFamily: cs?cs.fontFamily:null,
  heroSize: cs?cs.fontSize:null,
  heroWeight: cs?cs.fontWeight:null,
  heroDecoration: cs?cs.textDecorationLine:null,
  openerCount: all.length,
  heroFirst: all.length? all[0].classList.contains('sf-formula__cta--solid'):null,
  cardCount: cards.length,
  cardTag: cards.length?cards[0].tagName:null,
  cardText: cards.length?cards[0].textContent.trim():null,
  cardHasAttr: cards.length?cards[0].hasAttribute('data-sf-inquiry-open'):null,
  h1: document.querySelectorAll('h1').length,
  title: (()=>{const t=document.querySelector('.sf-fdetail2__title');
    if(!t) return null; const c=getComputedStyle(t);
    return {size:c.fontSize, lh:c.lineHeight, mb:c.marginBottom, weight:c.fontWeight};})()
 };})()
"""

MODAL_STATE = """
(()=>{const m=document.querySelector('.sf-inquiry-modal');
 const t=document.querySelector('.sf-inquiry-modal__title');
 const lead=document.querySelector('.sf-inquiry-modal__lead');
 const toast=document.querySelector('.sf-toast');
 return {
  present: !!m,
  hidden: m? m.hidden : null,
  open: m? m.classList.contains('is-open') : null,
  lock: document.body.classList.contains('sf-inquiry-lock'),
  title: t? t.textContent.trim() : null,
  lead: lead? lead.textContent.trim() : null,
  toast: toast? (toast.classList.contains('is-visible') ? toast.textContent.trim() : null) : null,
  focused: document.activeElement ? (document.activeElement.className || document.activeElement.tagName) : null,
  href: location.pathname + location.hash
 };})()
"""

GALLERY_STATE = """
(()=>{const root=document.querySelector('.sf-gallery');
 const tabs=[].slice.call(document.querySelectorAll('.sf-gallery__tab'));
 const strip=document.querySelector('.sf-gallery__thumbs');
 const stage=document.querySelector('.sf-gallery__stage');
 const vis=e=>{if(!e) return null; const c=getComputedStyle(e); return c.display!=='none' && c.visibility!=='hidden';};
 return {
  js: root? root.classList.contains('sf-gallery--js') : null,
  tabCount: tabs.length,
  tabKinds: tabs.map(t=>t.getAttribute('data-sf-gallery-tab')),
  tabPressed: tabs.map(t=>t.getAttribute('aria-pressed')),
  tabsVisible: (()=>{const w=document.querySelector('.sf-gallery__tabs'); return vis(w);})(),
  stripVisible: vis(strip),
  stageVisible: vis(stage),
  videoFrameVisible: (()=>{const v=document.querySelector('.sf-gallery__slide--video');
    if(!v) return 'absent'; return !v.hidden && vis(v);})()
 };})()
"""


class Runner(object):
    def __init__(self, auth, shots_dir):
        self.auth = auth
        self.shots = shots_dir
        self.rep = Rep()
        self.hdrs = None
        self.trace = True

    def ok(self, *a, **k):
        return self.rep.ok(*a, **k)

    def eq(self, *a, **k):
        return self.rep.eq(*a, **k)

    def assert_headers(self):
        """Re-assert the custom headers AFTER a navigation.

        `set headers` is origin-scoped: it applies to whatever document is
        loaded when it is called, so it has to be re-asserted once the browser is
        on the target origin — and `open` is the call that moves it there. Do it
        in the other order and the header lands on about:blank, the request goes
        out unauthenticated, and the run quietly measures the 401 page while
        every assertion about "no stylesheet" reads as a missing element.
        """
        if self.hdrs:
            run(['agent-browser', 'set', 'headers', self.hdrs])

    def where(self):
        return ev("(()=>({url:location.pathname+location.hash,"
                  "sheet:(()=>{const l=document.querySelector('link[rel=stylesheet]"
                  "[href*=\"sinofresh-theme\"]');return l?l.getAttribute('href'):null;})(),"
                  "modal:!!document.querySelector('.sf-inquiry-modal'),"
                  "focus:document.activeElement?(document.activeElement.tagName+'.'"
                  "+document.activeElement.className):null}))()")

    def where_str(self):
        return json.dumps(self.where())

    def on_page(self):
        """Is the harness still on the served page?

        Every assertion here reads the current document, so a click that
        navigates — or a failed close that leaves the session on about:blank —
        turns the rest of the run into a measurement of the wrong page, with
        every missing element reading as a missing feature. This guard names
        that instead. It was added after the second Escape in one session was
        found to land the harness on about:blank, which then failed seven
        unrelated assertions.
        """
        w = self.where() or {}
        return bool(w.get('sheet') and PREFLIGHT_DIR in (w.get('sheet') or ''))

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
        self.hdrs = json.dumps({'Authorization': 'Basic ' + b64, 'X-SF-Preflight': '1'})
        self.assert_headers()
        run(['agent-browser', 'errors', '--clear'])
        run(['agent-browser', 'console', '--clear'])

    def goto(self, path, tag, want_ver):
        """open -> reload (keeps the header) -> viewport -> assert WHICH copy.

        The provenance assertion is not optional: with the header lost, the
        browser silently renders the LIVE site, every check passes, and the
        batch is reported as verified against bytes it never saw.
        """
        url = '%s%s?sfe2e=%s%s' % (HOST, path, tag, time.strftime('%H%M%S'))
        st = None
        for attempt in (1, 2, 3):
            run(['agent-browser', 'open', url])
            self.assert_headers()            # open moved the browser onto the origin
            run(['agent-browser', 'reload'])  # reload carries them to the document
            run(['agent-browser', 'set', 'viewport', str(DESKTOP[0]), str(DESKTOP[1])])
            time.sleep(0.8)
            st = ev(PROBE)
            sheet = (st or {}).get('sheet') or ''
            if PREFLIGHT_DIR in sheet and want_ver in sheet:
                return st
            print('   ..   %s attempt %d served %r' % (path, attempt, sheet or 'no sheet'))
            time.sleep(0.8)
        raise SystemExit('FATAL not the pre-flight copy at ver=%s on %s (sheet=%r)'
                         % (want_ver, path, (st or {}).get('sheet')))

    def viewport(self, w, h):
        run(['agent-browser', 'set', 'viewport', str(w), str(h)])
        time.sleep(0.4)

    def click(self, sel):
        """Real click: scroll in, hit-check, then press. Coordinates are taken
        after the scroll and checked immediately before the press, because lazy
        images below the fold move the target between the two."""
        run(['agent-browser', 'scrollintoview', sel])
        time.sleep(0.4)
        box = ev("(()=>{const e=document.querySelector(%s);if(!e)return null;"
                 "const r=e.getBoundingClientRect();"
                 "return {x:Math.round(r.left+r.width/2),y:Math.round(r.top+r.height/2),"
                 "w:Math.round(r.width),h:Math.round(r.height)};})()" % json.dumps(sel))
        if not box or box.get('w', 0) <= 0:
            return None, 'no box'
        hit = ev("(()=>{const e=document.elementFromPoint(%d,%d);"
                 "return {tag:e?e.tagName:null,cls:e?e.className:null,"
                 "ok:!!(e&&e.closest(%s))};})()"
                 % (box['x'], box['y'], json.dumps(sel)))
        if not (hit or {}).get('ok'):
            return None, 'hit check failed: %r' % hit
        run(['agent-browser', 'mouse', 'move', str(box['x']), str(box['y'])])
        run(['agent-browser', 'mouse', 'down'])
        run(['agent-browser', 'mouse', 'up'])
        time.sleep(0.6)
        if self.trace:
            print('   ..   after click %-52s %s' % (sel, json.dumps(self.where())))
        return box, 'hit ok'

    def key(self, k):
        run(['agent-browser', 'press', k])
        time.sleep(0.6)
        if self.trace:
            print('   ..   after press %-6s %s' % (k, json.dumps(self.where())))

    def scroll(self, y):
        ev('window.scrollTo(0,%d); scrollY' % int(y))
        time.sleep(0.5)

    def shot(self, name, full=False):
        os.makedirs(self.shots, exist_ok=True)
        path = os.path.join(self.shots, name)
        cmd = ['agent-browser', 'screenshot']
        if full:
            cmd.append('--full')
        cmd.append(path)
        run(cmd, timeout=300)
        size = os.path.getsize(path) if os.path.exists(path) else 0
        print('  ..   shot %-34s %d bytes' % (name, size))
        return path

    def errors(self):
        rc, out, _ = run(['agent-browser', 'errors'])
        return out


# --------------------------------------------------------------------- modes

def mode_full(r, want_ver):
    r.rep = Rep()
    print('== candidate state (%s) ==' % want_ver)

    # ---------------- detail page, desktop: markup, type, and the H7a switch
    print('-- detail page, desktop %dx%d' % DESKTOP)
    r.goto(DETAIL, 'detail', want_ver)
    st = ev(HERO_STATE)
    r.eq('the hero primary action is an anchor', st.get('heroTag'), 'A')
    r.eq('and it says Send Inquiry', st.get('heroText'), 'Send Inquiry')
    r.ok('and its href is the no-JS destination',
         (st.get('heroHref') or '').endswith('/contact/#quote'), st.get('heroHref'))
    r.eq('and it carries the dialog hook', st.get('heroHasAttr'), True)
    # The no-JS contract: without scripting the element must still navigate, and
    # only an anchor can. The old <button> had no href at all.
    r.eq('two openers on the page', st.get('openerCount'), 2)
    r.eq('the hero CTA is the FIRST of them', st.get('heroFirst'), True)
    r.ok('the card buttons on this page are untouched',
         st.get('cardCount') == 3 and st.get('cardTag') == 'BUTTON'
         and st.get('cardText') == 'Reference this formula →'
         and st.get('cardHasAttr') is False,
         'n=%s tag=%s text=%r attr=%s' % (st.get('cardCount'), st.get('cardTag'),
                                          st.get('cardText'), st.get('cardHasAttr')))
    r.eq('still exactly one h1', st.get('h1'), 1)
    t = st.get('title') or {}
    r.eq('the column title is 32px', t.get('size'), '32px')
    r.eq('with 1.3 leading', t.get('lh'), '41.6px')
    r.eq('and 24px under it', t.get('mb'), '24px')

    r.scroll(0)
    r.shot('h7b-01-desktop-hero.png')
    r.shot('h7b-02-desktop-hero-full.png', full=True)

    print('-- the H7a media switch, on the same pages')
    g = ev(GALLERY_STATE)
    r.eq('the switch is painted only with scripting', g.get('js'), True)
    r.eq('one tab today (no record has a video)', g.get('tabCount'), 1)
    r.eq('and it is the photo tab', g.get('tabKinds'), ['photos'])
    r.eq('pressed', g.get('tabPressed'), ['true'])
    r.eq('the strip is on screen', g.get('stripVisible'), True)
    r.eq('the stage is on screen', g.get('stageVisible'), True)
    r.eq('no video frame is painted', g.get('videoFrameVisible'), 'absent')

    # ---------------- the hero CTA opens the dialog, and nothing else fires
    print('-- the hero CTA opens the dialog')
    box, why = r.click('.sf-formula-hero__actions .sf-formula__cta--solid')
    r.ok('the hero CTA is clickable', box is not None, why)
    r.ok('and the harness stayed on the served page', r.on_page(), r.where_str())
    m = ev(MODAL_STATE)
    r.eq('the dialog opened', m.get('open'), True)
    r.eq('its hidden attribute is gone', m.get('hidden'), False)
    r.eq('the body is locked', m.get('lock'), True)
    r.ok('it is the inquiry dialog', m.get('title') == 'Send Inquiry', m.get('title'))
    r.ok('and it names the product', 'Joint Support Soft Chews' in (m.get('lead') or ''),
         m.get('lead'))
    # the double-fire regression: formulas.js binds .sf-formula__cta globally
    r.eq('NO copy toast appeared', m.get('toast'), None)
    r.ok('the URL did not navigate away', m.get('href') == '/formulas/joint-support-soft-chews/',
         m.get('href'))
    r.shot('h7b-03-desktop-dialog.png')

    r.key('Escape')
    m = ev(MODAL_STATE)
    r.eq('Escape closed it', m.get('hidden'), True)
    r.ok('focus went back to the hero CTA',
         'sf-formula__cta--solid' in (m.get('focused') or ''), m.get('focused'))

    # ---------------- the capsule still opens it (the singular-query regression)
    print('-- the float capsule still opens it')
    r.scroll(900)
    box, why = r.click('.sf-float-btn--inquiry')
    r.ok('the capsule is revealed and clickable', box is not None, why)
    r.ok('and the harness stayed on the served page', r.on_page(), r.where_str())
    m = ev(MODAL_STATE)
    r.eq('the capsule still opens the dialog', m.get('open'), True)
    r.eq('and still fires no toast', m.get('toast'), None)
    # Closed with the dialog's own button, not a second Escape: two Escape
    # presses in one agent-browser session leave the harness on about:blank
    # (measured), and a close BUTTON is the path a visitor with a mouse takes
    # anyway. The focus-return claim is the same either way.
    box, why = r.click('.sf-inquiry-modal__close')
    r.ok('the dialog close button is clickable', box is not None, why)
    m = ev(MODAL_STATE)
    r.eq('the close button closed it', m.get('hidden'), True)
    r.ok('focus went back to the CAPSULE',
         'sf-float-btn--inquiry' in (m.get('focused') or ''), m.get('focused'))
    r.ok('and the harness is still on the served page', r.on_page(), r.where_str())

    # ---------------- card wall still copies
    print('-- the card wall on a dosage page still copies')
    r.goto(DOSAGE, 'dosage', want_ver)
    r.ok('a dosage page carries no inquiry dialog at all',
         (ev(MODAL_STATE) or {}).get('present') is False)
    box, why = r.click('.sf-formula__cta')
    r.ok('a card CTA is clickable', box is not None, why)
    m = ev(MODAL_STATE)
    r.ok('the copy toast appeared', 'Formula name copied' in (m.get('toast') or ''),
         m.get('toast'))
    r.eq('and there is still no dialog to open', m.get('present'), False)
    r.shot('h7b-04-dosage-toast.png')

    # ---------------- phone
    print('-- detail page, phone %dx%d' % PHONE)
    r.goto(DETAIL, 'phone', want_ver)
    r.viewport(*PHONE)
    st = ev(HERO_STATE)
    t = st.get('title') or {}
    r.eq('the column title steps to 26px', t.get('size'), '26px')
    r.eq('still one h1', st.get('h1'), 1)
    r.ok('the hero CTA is still an anchor', st.get('heroTag') == 'A', st.get('heroTag'))
    layout = ev("(()=>{const h=document.querySelector('.sf-formula-hero__actions .sf-formula__cta--solid');"
                "const t=document.querySelector('.sf-fdetail2__title');"
                "const r=h?h.getBoundingClientRect():null; const q=t?t.getBoundingClientRect():null;"
                "return {heroW:r?Math.round(r.width):null, heroH:r?Math.round(r.height):null,"
                " titleW:q?Math.round(q.width):null, vw:innerWidth,"
                " scrollW:document.documentElement.scrollWidth,"
                " overflow:document.documentElement.scrollWidth>innerWidth+1};})()")
    r.ok('the hero CTA still has a box', (layout.get('heroW') or 0) > 0, layout)
    r.ok('and the phone layout does not overflow', layout.get('overflow') is False, layout)
    r.scroll(0)
    r.shot('h7b-05-phone-hero.png')
    box, why = r.click('.sf-formula-hero__actions .sf-formula__cta--solid')
    r.ok('the hero CTA is clickable on a phone', box is not None, why)
    m = ev(MODAL_STATE)
    r.eq('the dialog opened on the phone', m.get('open'), True)
    r.shot('h7b-06-phone-dialog.png')

    errs = r.errors()
    r.ok('no page errors on the last page', not errs.strip(), errs.strip()[:200])
    return r.rep


def mode_geometry(r, want_ver, tag, shots):
    """Two-state measurements: run once per installed state and diff the JSON."""
    r.goto(DETAIL, 'geom-%s' % tag, want_ver)
    out = {'tag': tag, 'sheet': (ev(PROBE) or {}).get('sheet')}
    out['desktop'] = ev(HERO_STATE)
    r.scroll(0)
    r.shot('h7b-geom-%s-desktop-hero.png' % tag)
    band = ev("(()=>{const t=document.querySelector('.sf-fdetail2__title');"
              "if(!t) return null; const r=t.getBoundingClientRect();"
              "return {top:Math.round(r.top+scrollY), h:Math.round(r.height)};})()")
    if band:
        r.scroll(band['top'] - 120)
        r.shot('h7b-geom-%s-desktop-title.png' % tag)
    r.viewport(*PHONE)
    out['phone'] = ev(HERO_STATE)
    r.scroll(0)
    band = ev("(()=>{const t=document.querySelector('.sf-fdetail2__title');"
              "if(!t) return null; const r=t.getBoundingClientRect();"
              "return {top:Math.round(r.top+scrollY), h:Math.round(r.height)};})()")
    if band:
        r.scroll(band['top'] - 80)
        r.shot('h7b-geom-%s-phone-title.png' % tag)
    print('  ..   %s' % json.dumps({k: out[k] for k in ('desktop', 'phone')}, indent=1)[:1600])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mode', choices=('full', 'geometry'), default='full')
    ap.add_argument('--tag', default='cand')
    ap.add_argument('--want-ver', default='2.10.63')
    ap.add_argument('--out', default=None)
    ap.add_argument('--shots', default=None)
    ap.add_argument('--auth', default=os.environ.get('SF_DEV_AUTH') or DEFAULT_AUTH)
    args = ap.parse_args()

    shots = args.shots or os.path.join(
        ROOT, 'docs', 'batchH7b-shots' if args.mode == 'full' else 'batchH7b-geom')
    r = Runner(args.auth, shots)
    r.attach()

    if args.mode == 'full':
        rep = mode_full(r, args.want_ver)
        data = {'rows': rep.rows}
        ok = all(x['ok'] for x in rep.rows)
    else:
        data = mode_geometry(r, args.want_ver, args.tag, shots)
        ok = True

    out = args.out or os.path.join(ROOT, '_backup', 'b2d-h7b-%s.json' % args.mode)
    json.dump(data, open(out, 'w'), indent=1)
    print('\n%s  batch H7b browser pass (%s)  json -> %s'
          % ('PASS' if ok else 'FAIL', args.mode, out))
    run(['agent-browser', 'close', '--all'])
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())

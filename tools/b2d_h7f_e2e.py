#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H7f — the browser pass.

The byte gate proved the bag button, the drawer, the script tag and 1,125 basket
bytes are gone from all 75 pages, that the header CTA container and the cookie
banner that shared the drawer's block are still there, and that the endpoint no
longer answers a basket payload. The confinement proof added what a page's bytes
cannot show: the stylesheet's 15 removal intervals and what survived beside them,
and that no still-called `sinofresh_*` name is undefined.

Five things neither of those can see, and this pass exists for all five:

  * WHETHER THE SCRIPT IS ACTUALLY NOT FETCHED. `functions.php` no longer
    enqueues it, and the coverage count proves the <script> tag is gone -- but
    the claim a reader lives with is "the browser never asks for basket.js". So
    it is read back off `performance.getEntriesByType('resource')`, which is the
    only place the request would show up if a cached page, a plugin or an
    unrelated shortcode still emitted the tag.
  * WHETHER THE HEADER STILL WORKS WITHOUT IT. The bag button lived inside
    `.sf-header__cta`, a flex box. Removing a child can leave the box collapsed,
    the sibling shifted, or the container itself empty -- all invisible to a
    string count. So the CTA's own box, the Get a Quote button's box, and the
    header's height are measured, and the container's child count is read.
  * WHETHER THE TWO DIALOGS THAT SHARED ITS RULES STILL OPEN. The basket shared
    a backdrop rule, an open-state rule, a hidden-state rule and the scroll lock
    with the certificate dialog and the inquiry dialog; the carve took the
    basket's selector lines out of all four. A selector list that lost the wrong
    member leaves the rule present, ordered, and applying to nothing -- the H7b
    lesson. The only way to know is to open both dialogs and ask what is under
    the cursor.
  * WHETHER THE ENDPOINT ANSWERS AT ALL. This is the one path in the batch that
    no captured page exercises. Two POSTs: a basket payload must be refused with
    400 and the live site's own message -- the OLD theme answered 200 with a PDF,
    so that is also how this pass proves which copy replied -- and a real
    single-configuration payload must still come back as a PDF.
  * and that the site was still while all of it was measured.

usage:
    b2d_h7f_e2e.py --want-ver 2.10.67
"""
import argparse
import importlib.util
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def _load(name, fname):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, fname))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


h7b = _load('h7b_e2e', 'b2d_h7b_e2e.py')
geom = _load('h6_geom', 'b2d_h6_geom.py')

HOST = h7b.HOST
DETAIL = h7b.DETAIL
DESKTOP = h7b.DESKTOP
PHONE = h7b.PHONE
QUALITY = '/quality/'
ENDPOINT = HOST + '/wp-json/sinofresh/v1/config-pdf'
# Responses land on disk, not on a pipe: the good one is a PDF.
BODY1 = '/tmp/h7f-post-basket.bin'
BODY2 = '/tmp/h7f-post-config.bin'

# ---- the header, read back from the browser -------------------------------
HEADER_STATE = """
(()=>{
 const q=s=>document.querySelector(s);
 const qa=s=>[].slice.call(document.querySelectorAll(s));
 const res=performance.getEntriesByType('resource').map(r=>r.name);
 const cta=q('.sf-header__cta');
 const quote=q('.sf-quote-cta') || (cta?cta.querySelector('a'):null);
 const box=e=>{if(!e)return null;const r=e.getBoundingClientRect();
   return {x:Math.round(r.left),y:Math.round(r.top),
           w:Math.round(r.width),h:Math.round(r.height)};};
 const qcs=quote?getComputedStyle(quote):null;
 const hdr=q('header.sf-header');
 return {
  bagBtn: !!q('.sf-basket-btn'),
  bagAny: qa('[class*="sf-basket"]').length,
  bagScript: !!q('#sinofresh-basket-js'),
  bagFetched: res.filter(n=>/basket\\.js/.test(n)).length,
  bagFetchedNames: res.filter(n=>/basket/.test(n)),
  drawer: !!q('.sf-basket-drawer'),
  overlay: !!q('.sf-basket-overlay'),
  ariaBag: qa('[aria-label]').filter(e=>/basket/i.test(e.getAttribute('aria-label'))).length,
  ctaPresent: !!cta,
  ctaChildren: cta?cta.children.length:null,
  ctaLinks: cta?cta.querySelectorAll('a').length:null,
  ctaText: cta?cta.textContent.trim():null,
  ctaBox: box(cta),
  quoteText: quote?quote.textContent.trim():null,
  quoteHref: quote?quote.getAttribute('href'):null,
  quoteBox: box(quote),
  quoteVisible: !!(quote&&qcs&&qcs.display!=='none'&&qcs.visibility!=='hidden'&&
                  parseFloat(qcs.opacity)>0),
  headerBox: box(hdr),
  logo: !!q('.sf-logo, .wp-block-site-logo, header .custom-logo-link'),
  navLinks: qa('header nav a, header .wp-block-navigation a').length,
  footer: !!q('footer'),
  cookie: !!q('.sf-cookie-banner'),
  floatPrefix: qa('[class*="sf-float"]').length,
  h1: document.querySelectorAll('h1').length,
  overflow: document.documentElement.scrollWidth - window.innerWidth,
  sheet: (()=>{const l=q('link[href*="style.css"]');return l?l.getAttribute('href'):null;})()
 };})()
"""

# ---- a dialog, and what is actually under the cursor in it ----------------
MODAL_STATE = """
((sel)=>{
 const m=document.querySelector(sel);
 if(!m) return {present:false};
 const cs=getComputedStyle(m);
 const boxOf=e=>{if(!e)return null;const r=e.getBoundingClientRect();
   return {x:Math.round(r.left),y:Math.round(r.top),
           w:Math.round(r.width),h:Math.round(r.height),
           cx:Math.round(r.left+r.width/2),cy:Math.round(r.top+r.height/2)};};
 const panel=m.querySelector('[class*="__panel"]')||m.querySelector('[class*="__body"]')||m;
 const pb=boxOf(panel);
 // The panel centre is the one point the whole dialog has to own: it is inside
 // the panel, so if anything is painted over it -- the sticky header at y0-54,
 // the cookie banner, the float stack at z9998 -- this resolves to that thing.
 const hit=document.elementFromPoint(pb.cx,pb.cy);
 return {present:true,
   hidden:m.hasAttribute('hidden'),
   isOpen:m.classList.contains('is-open'),
   display:cs.display, visibility:cs.visibility, opacity:cs.opacity,
   zIndex:cs.zIndex,
   box:boxOf(m), panel:pb,
   centerOwner: hit? (hit.closest(sel)?'the dialog':String(hit.className||hit.tagName).slice(0,60)) : null,
   bodyLock: /sf-(certmodal|inquiry)-lock/.test(document.body.className),
   bodyClass: document.body.className };})
"""


# The phone header is a different design, and the difference predates this
# batch: a rule has always hidden the CTA *button* on a phone, and before H7f the
# comment above it said so -- "the inquiry basket icon inside the same container
# stays". The carve rewrote that comment because the icon is what left. So the
# phone claim is not "the button is visible" (it never was) but "the same divider
# still falls where it always fell, and the container it divides is intact".
PHONE_CTA = """
(()=>{
 const c=document.querySelector('.sf-header__cta');
 const b=c?c.querySelector('.wp-block-button'):null;
 const cs=c?getComputedStyle(c):null, bs=b?getComputedStyle(b):null;
 const r=c?c.getBoundingClientRect():null;
 return {cta:!!c, ctaChildren:c?c.children.length:null,
   ctaDisplay:cs?cs.display:null, ctaVisibility:cs?cs.visibility:null,
   ctaW:r?Math.round(r.width):null, ctaH:r?Math.round(r.height):null,
   btn:!!b, btnDisplay:bs?bs.display:null,
   hamburger:!!document.querySelector(
     '.sf-header .wp-block-navigation__responsive-container-open')};})()
"""


def modal_state(sel):
    """The dialog probe, with the selector passed IN.

    An arrow function, so it has to be invoked rather than formatted into: the
    first version of this read `MODAL_STATE % json.dumps(sel)` and died inside
    %-formatting, which is a failure at the call site that looks nothing like the
    mistake.
    """
    return '%s(%s)' % (MODAL_STATE, json.dumps(sel))


def post_json(payload, auth, bodyfile):
    """POST a JSON body with the pre-flight header; return (code, ctype, body).

    The response is written straight to a FILE rather than captured on stdout.
    A successful call answers with PDF bytes, and reading those through a text
    pipe dies inside subprocess's decoder on the first 0xfe -- a crash in the
    harness that reads like a failure of the thing under test.
    """
    rc, out, err = h7b.run([
        'curl', '-s', '-u', auth, '-H', 'X-SF-Preflight: 1',
        '-H', 'Content-Type: application/json',
        '-o', bodyfile,
        '-d', json.dumps(payload),
        '-w', '%{http_code} %{content_type}',
        ENDPOINT], 120)
    if rc != 0:
        return None, None, (out or err)[:200]
    code, _, ctype = out.partition(' ')
    with open(bodyfile, 'rb') as fh:
        raw = fh.read()
    try:
        text = raw.decode('utf-8')
    except UnicodeDecodeError:
        text = raw[:8].decode('latin-1')
    return code.strip(), ctype.strip(), text


def mode_full(r, want_ver, auth):
    r.rep = h7b.Rep()
    rep = r.rep

    # ---- home: the header, the footer, the script that is not fetched -----
    d = r.goto('/', 'h7f-home', want_ver)
    rep.eq('the home page still has exactly one h1', (d or {}).get('h1'), 1)
    h = h7b.ev(HEADER_STATE) or {}

    rep.ok('no bag button anywhere in the header', h.get('bagBtn') is False,
           'bagBtn=%r' % h.get('bagBtn'))
    rep.ok('no element carrying a basket class at all', (h.get('bagAny') or 0) == 0,
           'sf-basket* elements = %r' % h.get('bagAny'))
    rep.ok('no basket script tag', h.get('bagScript') is False,
           'script#sinofresh-basket-js present = %r' % h.get('bagScript'))
    # THE ONE ONLY THE BROWSER CAN ANSWER: an enqueue that was removed but a tag
    # that is still emitted shows up here as a request, and nowhere in the bytes
    # of a page that was captured before the change.
    rep.eq('and the browser never asks for basket.js', h.get('bagFetched'), 0)
    rep.ok('no drawer and no overlay in the footer',
           h.get('drawer') is False and h.get('overlay') is False,
           'drawer=%r overlay=%r' % (h.get('drawer'), h.get('overlay')))
    rep.eq('no aria-label mentions a basket', h.get('ariaBag'), 0)

    # ---- and the header still works without it ---------------------------
    rep.ok('the header CTA container is still there', h.get('ctaPresent') is True)
    rep.eq('with the Get a Quote button as its only child', h.get('ctaLinks'), 1)
    rep.eq('and the bare button last', h.get('quoteText'), 'Get a Quote')
    rep.eq('still pointing at the quote form', h.get('quoteHref'), '/contact/#quote')
    rep.ok('the button is laid out, not collapsed',
           (h.get('quoteBox') or {}).get('w', 0) > 40 and
           (h.get('quoteBox') or {}).get('h', 0) > 20,
           'quote box = %r' % (h.get('quoteBox'),))
    rep.ok('and visible to a reader', h.get('quoteVisible') is True)
    rep.ok('the CTA box still has a size after losing a child',
           (h.get('ctaBox') or {}).get('w', 0) > 60 and
           (h.get('ctaBox') or {}).get('h', 0) > 20,
           'cta box = %r children=%r' % (h.get('ctaBox'), h.get('ctaChildren')))
    rep.ok('the header still carries its logo and its links',
           h.get('logo') is True and (h.get('navLinks') or 0) >= 4,
           'logo=%r navLinks=%r' % (h.get('logo'), h.get('navLinks')))
    rep.ok('the header is still a header, not a collapsed strip',
           (h.get('headerBox') or {}).get('h', 0) >= 40,
           'header height = %r' % ((h.get('headerBox') or {}).get('h'),))
    rep.ok('the footer and the cookie banner survived the same block',
           h.get('footer') is True and h.get('cookie') is True,
           'footer=%r cookie banner=%r' % (h.get('footer'), h.get('cookie')))
    rep.ok('nothing overflows the viewport at 1440', (h.get('overflow') or 0) <= 1,
           'overflow=%rpx' % h.get('overflow'))
    rep.ok('the served sheet is the candidate', want_ver in (h.get('sheet') or ''),
           'sheet=%r' % h.get('sheet'))

    r.shot('h7f-01-header-desktop.png')
    # the footer, in a frame that shows the drawer's old neighbourhood
    r.scroll(99999)
    time.sleep(0.6)
    r.shot('h7f-03-footer-desktop.png')
    rep.ok('and the harness stayed on the served page', r.on_page(), r.where_str())

    # ---- the same header on a phone --------------------------------------
    r.viewport(*PHONE)
    time.sleep(0.6)
    p = h7b.ev(HEADER_STATE) or {}
    pc = h7b.ev(PHONE_CTA) or {}
    rep.ok('the bag button is gone at 420 too', p.get('bagBtn') is False)
    rep.eq('and so is the request for its script', p.get('bagFetched'), 0)
    rep.ok('the CTA container is still in flow on a phone, not collapsed',
           pc.get('cta') is True and pc.get('ctaDisplay') not in ('none', None) and
           pc.get('ctaVisibility') != 'hidden',
           'display=%r visibility=%r box=%rx%r children=%r'
           % (pc.get('ctaDisplay'), pc.get('ctaVisibility'),
              pc.get('ctaW'), pc.get('ctaH'), pc.get('ctaChildren')))
    # Pre-existing, and asserted so that a future edit to that comment block has
    # something to trip over: on a phone the BUTTON is hidden, the box is not.
    rep.ok('and the button is still hidden by the phone rule, as it always was',
           pc.get('btn') is True and pc.get('btnDisplay') == 'none',
           'button display=%r' % pc.get('btnDisplay'))
    rep.ok('and the hamburger it now hugs is still there',
           pc.get('hamburger') is True)
    rep.ok('the phone page does not scroll sideways', (p.get('overflow') or 0) <= 1,
           'overflow=%rpx' % p.get('overflow'))
    rep.eq('the h1 count is unchanged on a phone', p.get('h1'), 1)
    r.shot('h7f-02-header-phone.png')
    rep.ok('and the harness stayed on the served page', r.on_page(), r.where_str())

    # ---- the certificate dialog, which shared four rules with the basket ---
    r.viewport(*DESKTOP)
    r.goto(QUALITY, 'h7f-quality', want_ver)
    before = h7b.ev(modal_state('.sf-certmodal')) or {}
    rep.ok('the quality page carries the certificate dialog',
           before.get('present') is True)
    rep.ok('and it starts closed', before.get('hidden') is True and
           before.get('isOpen') is False,
           'hidden=%r is-open=%r' % (before.get('hidden'), before.get('isOpen')))
    trig = h7b.ev("document.querySelectorAll('.sf-cert-trigger').length")
    rep.ok('the page still has a certificate trigger', (trig or 0) >= 1,
           'triggers=%r' % trig)
    box, why = r.click('.sf-cert-trigger')
    rep.ok('the trigger is hittable where it is drawn', box is not None, why)
    time.sleep(0.8)
    open_ = h7b.ev(modal_state('.sf-certmodal')) or {}
    rep.ok('the certificate dialog opens', open_.get('isOpen') is True,
           'is-open=%r hidden=%r display=%r' % (open_.get('isOpen'),
                                                open_.get('hidden'),
                                                open_.get('display')))
    rep.ok('with a panel that has a size',
           (open_.get('panel') or {}).get('w', 0) > 200 and
           (open_.get('panel') or {}).get('h', 0) > 150,
           'panel = %r' % (open_.get('panel'),))
    # the z-order claim: nothing the site stacks above z=9998 may own the point
    rep.eq('and the dialog owns the middle of its own panel',
           open_.get('centerOwner'), 'the dialog')
    # 10010 is the dialog's OWN step, one above the shared backdrop's 10000 --
    # the carve rewrote the comment that says so at style.css:6354. Asserted by
    # value AND against the layer it has to clear, because the value alone would
    # go stale silently and the ordering check is what a reader depends on.
    rep.eq('and it keeps its own step above the shared backdrop',
           open_.get('zIndex'), '10010')
    rep.ok('...which is above the float stack at 9998',
           int(open_.get('zIndex') or 0) > 9998,
           'z=%r' % open_.get('zIndex'))
    rep.ok('and it took the scroll lock the basket used to share',
           open_.get('bodyLock') is True, 'body=%r' % open_.get('bodyClass'))
    r.shot('h7f-04-certmodal-open.png')
    # closed by the page's own control: two Escapes land the harness on
    # about:blank, and every assertion after that measures the wrong document.
    cb, cwhy = r.click('.sf-certmodal__close')
    rep.ok('the dialog closes by its own button', cb is not None, cwhy)
    time.sleep(0.8)
    shut = h7b.ev(modal_state('.sf-certmodal')) or {}
    rep.ok('and it is hidden again', shut.get('hidden') is True and
           shut.get('isOpen') is False,
           'hidden=%r is-open=%r' % (shut.get('hidden'), shut.get('isOpen')))
    rep.ok('and the scroll lock came off', shut.get('bodyLock') is False,
           'body=%r' % shut.get('bodyClass'))
    rep.ok('and the harness stayed on the served page', r.on_page(), r.where_str())

    # ---- the inquiry dialog, which shared the same four rules --------------
    r.goto(DETAIL, 'h7f-detail', want_ver)
    n = h7b.ev("document.querySelectorAll('[data-sf-inquiry-open]').length")
    rep.ok('the detail page still has an inquiry opener', (n or 0) >= 1,
           'openers=%r' % n)

    # The frame pair is taken here, and it is taken from the FIXED opener on
    # purpose. The other opener is in the flow, so clicking it scrolls the page
    # and the two frames would differ by the scroll rather than by the dialog --
    # a pair that differs for the wrong reason is not evidence of the change it
    # claims. The float button is position:fixed, so `scrollintoview` leaves the
    # page exactly where it was and the only difference is the dialog.
    r.scroll(99999)
    time.sleep(0.6)
    y_before = h7b.ev('Math.round(window.scrollY)')
    r.shot('h7f-05-detail-bottom-closed.png')
    FLOAT_OPENER = '.sf-float-btn--inquiry[data-sf-inquiry-open]'
    rep.ok('the fixed inquiry button is on the page',
           h7b.ev("!!document.querySelector(%s)" % json.dumps(FLOAT_OPENER)) is True)
    box, why = r.click(FLOAT_OPENER)
    rep.ok('the opener is hittable where it is drawn', box is not None, why)
    time.sleep(0.8)
    y_after = h7b.ev('Math.round(window.scrollY)')
    rep.ok('...and opening it did not move the page',
           abs((y_after or 0) - (y_before or 0)) <= 2,
           'scrollY %r -> %r' % (y_before, y_after))
    io = h7b.ev(modal_state('.sf-inquiry-modal')) or {}
    rep.ok('the inquiry dialog opens', io.get('isOpen') is True,
           'is-open=%r hidden=%r' % (io.get('isOpen'), io.get('hidden')))
    rep.ok('with a panel that has a size',
           (io.get('panel') or {}).get('w', 0) > 200 and
           (io.get('panel') or {}).get('h', 0) > 150,
           'panel = %r' % (io.get('panel'),))
    rep.eq('and it owns the middle of its own panel', io.get('centerOwner'), 'the dialog')
    rep.eq('and it keeps the same own step above the shared backdrop',
           io.get('zIndex'), '10010')
    rep.ok('...also above the float stack at 9998',
           int(io.get('zIndex') or 0) > 9998, 'z=%r' % io.get('zIndex'))
    rep.ok('and it took the same scroll lock', io.get('bodyLock') is True,
           'body=%r' % io.get('bodyClass'))
    r.shot('h7f-06-detail-bottom-inquiry-open.png')
    cb, cwhy = r.click('.sf-inquiry-modal__close')
    rep.ok('the dialog closes by its own button', cb is not None, cwhy)
    time.sleep(0.8)
    ishut = h7b.ev(modal_state('.sf-inquiry-modal')) or {}
    rep.ok('and it is hidden again', ishut.get('hidden') is True,
           'hidden=%r is-open=%r' % (ishut.get('hidden'), ishut.get('isOpen')))
    rep.eq('the h1 count is unchanged by all of it',
           h7b.ev("document.querySelectorAll('h1').length"), 1)
    rep.ok('and the harness stayed on the served page', r.on_page(), r.where_str())

    # ---- the endpoint: the one path no captured page exercises ------------
    # The basket payload is also the provenance test. The dev site's live theme
    # is several batches behind and its endpoint still had basket mode, which
    # answered 200 with a PDF. A 400 carrying the single-configuration message
    # is therefore only producible by the candidate.
    code, ctype, body = post_json({'basket': [
        {'slug': 'soft-chews', 'title': 'x', 'summary': 'y'}]}, auth, BODY1)
    rep.eq('a basket payload is refused with 400', str(code), '400')
    rep.ok('...with the single-configuration message, not a 500',
           'Unknown dosage form slug.' in (body or ''),
           'body=%r' % (body or '')[:120])
    rep.ok('...and it is JSON, not an HTML error page',
           'application/json' in (ctype or ''), 'content-type=%r' % ctype)
    rep.ok('...and no PDF came back', not (body or '').startswith('%PDF'),
           'first bytes=%r' % (body or '')[:8])

    # email is left empty on purpose: this pass must not send anything.
    code, ctype, body = post_json({
        'slug': 'soft-chews',
        'config': [{'label': 'Shape', 'value': 'Bone'}, {'label': 'Size', 'value': '60 ct'}],
        'email': ''}, auth, BODY2)
    rep.eq('a real configuration still comes back as a PDF', str(code), '200')
    rep.ok('...with the PDF content type', 'application/pdf' in (ctype or ''),
           'content-type=%r' % ctype)
    rep.ok('...and PDF bytes', (body or '').startswith('%PDF'),
           'first bytes=%r' % (body or '')[:8])
    rep.ok('...and a non-trivial one',
           os.path.getsize(BODY2) > 20000, '%d bytes' % os.path.getsize(BODY2))

    rep.ok('the page logged no script errors', not (r.errors() or '').strip(),
           (r.errors() or '').strip()[:200] or 'none')
    return rep, h


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--want-ver', default='2.10.67')
    ap.add_argument('--out', default=None)
    ap.add_argument('--shots', default=None)
    ap.add_argument('--auth', default=os.environ.get('SF_DEV_AUTH') or h7b.DEFAULT_AUTH)
    args = ap.parse_args()

    shots = args.shots or os.path.join(ROOT, 'docs', 'batchH7f-shots')

    # The site must be still. A render comparison of a live site without this is
    # a comparison to a moving target, and the difference it finds would be
    # somebody else's edit -- so it runs before the browser is even attached.
    print('== quiescence: is the site still? ==')
    fp_before = geom.content_fingerprint(args.auth)
    print('   before: %s  (%d rows)' % (fp_before['sha'][:16], fp_before['rows']))

    r = h7b.Runner(args.auth, shots)
    r.attach()
    rep, hdr = mode_full(r, args.want_ver, args.auth)
    ok = all(x['ok'] for x in rep.rows)

    fp_after = geom.content_fingerprint(args.auth)
    print('   after : %s  (%d rows)' % (fp_after['sha'][:16], fp_after['rows']))
    still = fp_before['sha'] == fp_after['sha'] and fp_before['rows'] == fp_after['rows']
    print('  %s  the site was unchanged for the whole pass  %s'
          % ('ok  ' if still else 'FAIL',
             'same digest' if still else 'CONTENT MOVED UNDER THE PASS'))
    ok &= still

    out = args.out or os.path.join(ROOT, '_backup', 'b2d-h7f-e2e.json')
    json.dump({'rows': rep.rows, 'fingerprint_before': fp_before,
               'fingerprint_after': fp_after, 'header': hdr},
              open(out, 'w'), indent=1)
    npass = sum(1 for x in rep.rows if x['ok'])
    print('\n%s  batch H7f browser pass  %d/%d  json -> %s'
          % ('PASS' if ok else 'FAIL', npass, len(rep.rows), out))
    h7b.run(['agent-browser', 'close', '--all'])
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())

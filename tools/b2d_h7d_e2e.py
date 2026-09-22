#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H7d — the browser pass.

The byte gate proves the band is emitted on the right 42 pages, once each, in
the right place, with the declared groups, options, hints and no others, and
that `config.js` contains the lines that make the summary and the drawer. Every
one of those can be true of a configurator that does not work. What this pass
adds, and why none of it is a second opinion on the bytes:

  * WHETHER THE LIST IS STILL THERE ON A DESKTOP. The batch hides the list with
    `.sf-fdetail-config--js .sf-fdetail-config__list { display: none; }` — inside
    the 768px query, because on a phone the list becomes a drawer. Move that one
    rule 60 bytes up, out of the query, and the desktop gets a hidden list with
    a button that is itself hidden at that width: a blank right column, no error,
    no byte out of place at the wrong nesting depth. This is the batch H7b
    lesson (a media query adds no specificity) read in the other direction, and
    only `getComputedStyle` can tell the two apart.
  * WHETHER A CHOICE ACTUALLY REACHES THE DIALOG. `inquiry.js` posts whatever
    the form carries; `config.js` is what puts the choice in the form, as JSON
    in one hidden input, keyed one key per group — an array for a multi group and
    a scalar for a single one. That key shape is the endpoint's contract and no
    byte in the page states it: the same script with `payload[group.key] =
    values` would still pass every source claim and post `["60"]` where the
    endpoint reads `"60"`.
  * WHETHER AN EMPTY CHOICE FALLS BACK. The brief: nothing picked means the
    dialog keeps the server-rendered specification. That branch is only
    reachable while no group has a tick, so it is asserted at load (carrier
    empty, panel equal to the server's rows) and, on the one record with a
    single radio, again after unticking the last checkbox — the panel has to
    come back byte-for-byte, not merely stop updating.
  * WHETHER THE DRAWER IS A DRAWER. `position: fixed; inset: 0` covering the
    viewport, a close button above it, the body locked, focus moved in and back
    out, one Escape closing it once, and a resize out of the breakpoint closing
    it rather than stranding it. Six claims, all of them about pixels at a
    width, none of them about a string.
  * WHETHER THE NO-JS PAGE IS STILL USABLE. The controls are server-rendered
    checkboxes and radios and the two buttons are created by the script. The
    claim "a visitor without the script is never shown a button that cannot open
    anything" is a statement about the SERVED BYTES, so it is read off a raw
    fetch rather than out of a DOM the script has already touched.

WHAT THIS PASS DOES NOT DO

It never presses submit. The form posts to `sales@zxpet.com`; a browser pass
that ended with a real inquiry in the sales inbox would be a worse bug than any
it could find. The submit path's server-side logic is covered by the batch's own
mu-plugin probe (a foreign value in the same field is dropped per value, the
valid one survives) and by the unit test of the pack-size splitter, and the
endpoint's auth and anti-spam were verified in batch H4. So the run opens the
dialog, reads the panel, and closes it — and asserts, at the end, that no
navigation happened and that no page error was raised.

usage:
    b2d_h7d_e2e.py --want-ver 2.10.65 [--json OUT]
"""
import argparse
import importlib.util
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

_spec = importlib.util.spec_from_file_location(
    'h7b_e2e', os.path.join(HERE, 'b2d_h7b_e2e.py'))
h7b = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(h7b)

run = h7b.run
ev = h7b.ev
HOST = h7b.HOST
DETAIL = h7b.DETAIL            # /formulas/joint-support-soft-chews/  (post 158)
DETAIL_ZH = h7b.DETAIL_ZH
PLAIN = '/formulas/calming-soft-chews/'   # a record with no flavour/container/price
DESKTOP = h7b.DESKTOP
PHONE = (420, 900)

# The five groups post 158 renders, in the order PHP emits them, with the control
# type and option count each one actually has. Written out rather than derived so
# that a renderer that dropped a group, or turned a radio into a checkbox, has to
# disagree with a number somebody chose.
GROUPS_158 = [
    ('flavor', 'Flavor', 'checkbox', 7),
    ('weight', 'Piece Weight', 'radio', 1),
    ('pack', 'Pack Size', 'checkbox', 3),
    ('container', 'Container Type', 'radio', 7),
    ('pricing', 'Quantity & Pricing', 'radio', 1),
]
GROUPS_PLAIN = [
    ('weight', 'Piece Weight', 'radio', 1),
    ('pack', 'Pack Size', 'checkbox', 3),
]
# The dialog's server-rendered fallback on post 158: the product's own figures,
# four rows. `Container Type` is absent here and present in the band on purpose —
# the dialog's panel is the reader's *fallback*, and the record's container is a
# library slug with no image, so it is a choice rather than a printed figure.
SERVER_ROWS_158 = ['Flavor', 'Piece Weight', 'Pack Size', 'Quantity & Pricing']

# The no-JS contract, read off the served bytes. `--js` is added by the script,
# the two buttons are created by it, `is-on` is set by it, and the summary ships
# empty and hidden so that the no-JS page makes no claim about a selection that
# cannot be made. Anything here found in the raw HTML means the fallback story is
# false, whatever the DOM looks like afterwards.
NOJS_ABSENT = [
    ('the drawer button', 'sf-fdetail-config__open'),
    ('the drawer close button', 'sf-fdetail-config__close'),
    ('the script marker class', 'sf-fdetail-config--js'),
    ('the open state class', 'sf-fdetail-config--open'),
    ('a ticked option', 'sf-fdetail-config__opt is-on'),
]
NOJS_PRESENT = [
    ('the real controls are server-rendered',
     'class="sf-fdetail-config__input" type="checkbox"'),
    ('the list is not hidden in the markup', 'class="sf-fdetail-config__list"'),
    ('the summary ships empty and hidden', 'data-sf-config-summary hidden'),
]


# The floating capsule, which this batch moved onto a new trigger: `inquiry.js`
# used to reveal it when `.sf-fdetail2__params` crossed halfway up the viewport,
# and the seven rows it watched are now inside the configurator, above those rows.
CAP_STATE = """
(()=>{
 const c=document.querySelector('.sf-float-btn--inquiry');
 if(!c) return {present:false};
 const cs=getComputedStyle(c);
 return {
  present:true,
  hidden:c.hidden,
  visible:c.classList.contains('is-visible'),
  painted:cs.display!=='none'&&cs.visibility!=='hidden'&&cs.opacity!=='0',
  scrollY:Math.round(window.scrollY)
 };})()
"""

STATE = """
(()=>{
 const root=document.querySelector('[data-sf-config]');
 if(!root) return {present:false, bands:document.querySelectorAll('.sf-fdetail-config').length};
 const list=root.querySelector('.sf-fdetail-config__list');
 const openBtn=root.querySelector('.sf-fdetail-config__open');
 const closeBtn=root.querySelector('.sf-fdetail-config__close');
 const summary=root.querySelector('[data-sf-config-summary]');
 const note=root.querySelector('[data-sf-config-note]');
 const inputs=[].slice.call(root.querySelectorAll('.sf-fdetail-config__input'));
 const opts=[].slice.call(root.querySelectorAll('.sf-fdetail-config__opt'));
 const cs=e=>e?getComputedStyle(e):null;
 const vis=e=>{if(!e)return null;const c=cs(e);
   return c.display!=='none'&&c.visibility!=='hidden'&&c.opacity!=='0';};
 const box=e=>{if(!e)return null;const b=e.getBoundingClientRect();
   return {top:Math.round(b.top),left:Math.round(b.left),
           w:Math.round(b.width),h:Math.round(b.height),
           bottom:Math.round(b.bottom),right:Math.round(b.right)};};
 const modal=document.querySelector('.sf-inquiry-modal');
 const carrier=modal?modal.querySelector('input[name="config"]'):null;
 const rowsEl=modal?modal.querySelector('.sf-inquiry-modal__rows'):null;
 const lcs=cs(list), ocs=cs(openBtn), ccs=cs(closeBtn);
 return {
  present:true,
  bands:document.querySelectorAll('.sf-fdetail-config').length,
  groups:document.querySelectorAll('[data-sf-config-group]').length,
  groupInfo:[].slice.call(document.querySelectorAll('[data-sf-config-group]')).map(function(g){
    var ins=[].slice.call(g.querySelectorAll('.sf-fdetail-config__input'));
    var lab=g.querySelector('.sf-fdetail-config__label');
    var meta=g.querySelector('.sf-fdetail-config__meta');
    var hint=g.querySelector('.sf-fdetail-config__hint');
    return {key:g.getAttribute('data-sf-config-group'),
            label:lab?lab.textContent.trim():null,
            meta:meta?meta.textContent.trim():null,
            hint:hint?hint.textContent.trim():null,
            n:ins.length,
            types:ins.map(function(i){return i.type;}).filter(function(t,k,a){return a.indexOf(t)===k;}),
            values:ins.map(function(i){return i.value;}),
            imgs:g.querySelectorAll('.sf-fdetail-config__img').length,
            emptyImgs:g.querySelectorAll('.sf-fdetail-config__img--empty').length,
            notes:[].slice.call(g.querySelectorAll('.sf-fdetail-config__note')).map(function(n){return n.textContent.trim();})};
  }),
  checked:inputs.filter(i=>i.checked).map(i=>i.value),
  onOpts:opts.filter(o=>o.classList.contains('is-on')).length,
  onValues:opts.filter(o=>o.classList.contains('is-on')).map(function(o){
    var i=o.querySelector('.sf-fdetail-config__input');return i?i.value:null;}),
  summaryText:summary?summary.textContent.trim():null,
  summaryHidden:summary?summary.hidden:null,
  summaryVisible:vis(summary),
  noteHidden:note?note.hidden:null,
  noteVisible:vis(note),
  carrier:carrier?carrier.value:null,
  carrierPresent:!!carrier,
  panelTerms:rowsEl?[].slice.call(rowsEl.querySelectorAll('.sf-inquiry-modal__term'))
    .map(function(t){return t.textContent.trim();}):null,
  panelValues:rowsEl?[].slice.call(rowsEl.querySelectorAll('.sf-inquiry-modal__value'))
    .map(function(t){return t.textContent.trim();}):null,
  panelOwn:rowsEl?(rowsEl.dataset.sfOwn!==undefined):null,
  js:root.classList.contains('sf-fdetail-config--js'),
  open:root.classList.contains('sf-fdetail-config--open'),
  lock:document.body.classList.contains('sf-config-lock'),
  hasOpenBtn:!!openBtn, hasCloseBtn:!!closeBtn,
  openText:openBtn?openBtn.textContent.trim():null,
  closeText:closeBtn?closeBtn.textContent.trim():null,
  openAria:openBtn?openBtn.getAttribute('aria-expanded'):null,
  openVisible:vis(openBtn), closeVisible:vis(closeBtn), listVisible:vis(list),
  listDisplay:lcs?lcs.display:null,
  listPosition:lcs?lcs.position:null,
  listZ:lcs?lcs.zIndex:null,
  listOverflowY:lcs?lcs.overflowY:null,
  listBox:box(list), openBox:box(openBtn),
  openZ:ocs?ocs.zIndex:null, closeZ:ccs?ccs.zIndex:null,
  viewport:[window.innerWidth,window.innerHeight],
  focus:document.activeElement?(document.activeElement.className||document.activeElement.tagName):null,
  h1:document.querySelectorAll('h1').length,
  overflow:document.documentElement.scrollWidth-window.innerWidth,
  href:location.pathname
 };})()
"""


# The open drawer against everything else the site fixes to the viewport. A
# full-screen overlay reports `inset: 0` in its own box whatever is painted over
# it, so the only way to state "this drawer is on top" is to ask what the pixels
# belong to. This scans a column down the middle of the screen, while the drawer
# is open, and returns every run of samples that does NOT belong to the drawer —
# together with the layer responsible and its z-index, so the report names the
# cause and not just the symptom.
PIERCE = """
(()=>{
 const root=document.querySelector('[data-sf-config].sf-fdetail-config--open');
 const list=root?root.querySelector('.sf-fdetail-config__list'):null;
 if(!list) return {open:false};
 const r=e=>{if(!e)return null;const x=e.getBoundingClientRect();
   return {top:Math.round(x.top),left:Math.round(x.left),w:Math.round(x.width),
           h:Math.round(x.height),bottom:Math.round(x.bottom),right:Math.round(x.right)};};
 const z=e=>e?getComputedStyle(e).zIndex:null;
 const name=e=>{if(!e)return null;
   const cls=(typeof e.className==='string'&&e.className)?e.className:e.tagName;
   return cls.slice(0,64);};
 const STEP=18;
 const pierced=[];
 for(let y=0;y<innerHeight;y+=STEP){
   const e=document.elementFromPoint(Math.round(innerWidth/2),Math.min(y,innerHeight-1));
   const inside=!!(e&&(list.contains(e)||(e.closest&&e.closest('.sf-fdetail-config'))));
   if(!inside) pierced.push({y:y,cls:name(e),z:z(e)});
 }
 const bands=[];
 pierced.forEach(function(p){
   const last=bands[bands.length-1];
   if(last && p.y-last.to<=STEP){last.to=p.y;last.n++;if(!last.z)last.z=p.z;}
   else bands.push({from:p.y,to:p.y,n:1,cls:p.cls,z:p.z});
 });
 const done=document.querySelector('.sf-fdetail-config__close');
 const dr=r(done);
 /* A horizontal sweep along the button's vertical centre, which is the widest
    part of the pill: a grid over the bounding box would count the rounded ends
    as "covered" and report a defect that is only a border-radius. */
 let hits=0,total=0;
 if(dr&&dr.w>0&&dr.h>0){
   for(let k=1;k<20;k++){
     total++;
     const x=Math.round(dr.left+dr.w*k/20), y=Math.round(dr.top+dr.h/2);
     const e=document.elementFromPoint(x,y);
     if(e===done||(done&&done.contains(e))) hits++;
   }
 }
 const hdr=document.querySelector('.sf-header');
 const ban=document.querySelector('.sf-cookie-banner');
 const trp=document.querySelector('.trp-floating-switcher, .trp-language-switcher');
 const vis=e=>{if(!e)return null;const c=getComputedStyle(e);
   return !e.hidden&&c.display!=='none'&&c.visibility!=='hidden';};
 return {
  open:true,
  bands:bands,
  done:{box:dr,z:z(done),hits:hits,total:total,covered:total-hits},
  header:{box:r(hdr),cls:name(hdr),z:z(hdr),sticky:hdr?hdr.classList.contains('is-sticky'):null},
  banner:{box:r(ban),z:z(ban),shown:vis(ban)},
  trp:{box:r(trp),cls:name(trp),z:z(trp),pos:trp?getComputedStyle(trp).position:null,
       shown:vis(trp)},
  viewport:[innerWidth,innerHeight]
 };})()
"""


def dismiss_banner():
    """Take the cookie banner out of the way, as a returning visitor has it.

    Not a workaround: the drawer's own behaviour (Done, Escape, resize, focus)
    has to be measured in a state where another overlay is not standing on the
    only exit. What the overlap itself is, is asserted before this, on its own,
    so the finding is stated once and loudly instead of hiding inside seven
    cascading failures of the tests that come after it.
    """
    return ev("(()=>{const b=document.querySelector('.sf-cookie-banner');"
              "if(b){b.hidden=true;b.style.display='none';} return true;})()")


def click_opt(r, value, label=None):
    """Click the option whose input carries `value`, by pressing its label.

    `Runner.click` cannot be used directly: the input is a 1x1 transparent box
    (`position: absolute; width: 1px; height: 1px; opacity: 0`), so the pixel at
    its own centre belongs to the label that wraps it and a hit-check against the
    input would fail on a control that is in fact perfectly clickable. The label
    is the target; the hit-check then has to prove the pixel belongs to the label
    of THIS option, which is the part that a scroll-then-click without a check
    gets wrong when a lazy image reflows the column in between.
    """
    sel = 'input.sf-fdetail-config__input[value=%s]' % json.dumps(value)
    run(['agent-browser', 'scrollintoview', sel])
    time.sleep(0.4)
    box = ev("(()=>{const i=document.querySelector(%s);if(!i)return null;"
             "const l=i.closest('label');if(!l)return null;"
             "const b=l.getBoundingClientRect();"
             "return {x:Math.round(b.left+b.width/2),y:Math.round(b.top+b.height/2),"
             "w:Math.round(b.width),h:Math.round(b.height),"
             "label:l.querySelector('.sf-fdetail-config__text')"
             "?l.querySelector('.sf-fdetail-config__text').textContent.trim():null};})()"
             % json.dumps(sel))
    if not box or box.get('w', 0) <= 0:
        return None, 'no box for %r' % value
    hit = ev("(()=>{const e=document.elementFromPoint(%d,%d);"
             "const l=e?e.closest('label.sf-fdetail-config__opt'):null;"
             "const i=l?l.querySelector('.sf-fdetail-config__input'):null;"
             "return {tag:e?e.tagName:null,val:i?i.value:null,"
             "ok:!!(i&&i.value===%s)};})()"
             % (box['x'], box['y'], json.dumps(value)))
    if not (hit or {}).get('ok'):
        return None, 'hit check failed at (%d,%d): %r' % (box['x'], box['y'], hit)
    run(['agent-browser', 'mouse', 'move', str(box['x']), str(box['y'])])
    run(['agent-browser', 'mouse', 'down'])
    run(['agent-browser', 'mouse', 'up'])
    time.sleep(0.5)
    return box, 'hit ok'


def scroll_to(r, selector, margin=110):
    """Put `selector` near the top of the viewport and return the offset.

    Every frame this pass takes is a full viewport frame at a known scrollY, not
    an element crop: an element crop is only trustworthy while the element is
    inside the initial scrollY=0 viewport, and the right column is below the fold
    on both widths. The offset is returned so it can be printed in the frame's
    note rather than assumed.
    """
    y = ev("(()=>{const e=document.querySelector(%s);if(!e)return null;"
           "return Math.max(0,Math.round(e.getBoundingClientRect().top"
           "+window.scrollY-%d));})()" % (json.dumps(selector), margin))
    if y is None:
        raise SystemExit('FATAL %s is not on the page — refusing a frame about '
                         'nothing' % selector)
    ev('window.scrollTo(0,%d)' % y)
    time.sleep(0.5)
    return y


def jload(s):
    """The carrier as parsed JSON, or a marker when it is not JSON at all."""
    if s in (None, ''):
        return None
    try:
        return json.loads(s)
    except Exception as exc:
        return '<unparsable: %s>' % exc


def group_shape(info):
    return [(g['key'], g['label'], tuple(g['types']), g['n']) for g in (info or [])]


def assets_absent(html):
    """Which runtime-only markers the served bytes carry (want: none)."""
    return [name for name, needle in NOJS_ABSENT if needle in html]


def mode_full(r, want_ver):
    print('== candidate state (%s) ==' % want_ver)

    # ------------------------------------------------------------------ desktop
    print('-- the band at %dx%d, post 158 (five groups)' % DESKTOP)
    r.goto(DETAIL, 'h7d-desktop', want_ver)
    s0 = ev(STATE) or {}
    r.ok('the configurator is on the page', s0.get('present') is True)
    r.eq('and there is exactly one of it', s0.get('bands'), 1)
    r.eq('the five groups the record has are all rendered', s0.get('groups'), 5)
    r.ok('each one with the label, the control type and the option count it declares',
         group_shape(s0.get('groupInfo')) ==
         [(k, l, (t,), n) for k, l, t, n in GROUPS_158],
         '%r' % (group_shape(s0.get('groupInfo')),))
    r.ok('nothing is ticked at load', s0.get('checked') == [],
         'checked=%r' % (s0.get('checked'),))
    r.eq('and no option carries the ticked style', s0.get('onOpts'), 0)
    # The container library is empty, so the picker degrades to a dashed slot on
    # every option. Had PHP written <img src=""> these would be broken images.
    cg = [g for g in (s0.get('groupInfo') or []) if g['key'] == 'container']
    r.ok('every container option ships a dashed slot, not an image',
         bool(cg) and cg[0]['imgs'] == 7 and cg[0]['emptyImgs'] == 7,
         'imgs=%s empty=%s' % (cg[0]['imgs'], cg[0]['emptyImgs']) if cg else 'no container group')
    # The record's own figures stay printed above the controls: the reader can
    # still see what the product is while choosing what to ask about.
    la = {g['key']: g for g in (s0.get('groupInfo') or [])}
    r.ok('the record still prints its own flavour list above the options',
         'Chicken' in (la.get('flavor', {}).get('meta') or ''),
         la.get('flavor', {}).get('meta'))
    r.ok('the pack hint reads as a sentence, not "Per per"',
         la.get('pack', {}).get('hint') == 'Per bottle',
         la.get('pack', {}).get('hint'))
    r.ok('and the price tier carries its unit',
         'USD 2.5 / unit' == la.get('pricing', {}).get('meta', '')[-14:],
         la.get('pricing', {}).get('meta'))
    r.ok('the price tier prints its unit price beside the option too',
         la.get('pricing', {}).get('notes') == ['USD 2.5 / unit'],
         la.get('pricing', {}).get('notes'))

    # ---- the desktop layout claim (the one a misplaced media query kills)
    r.eq('the script marked the band', s0.get('js'), True)
    r.ok('the option list is VISIBLE on a desktop', s0.get('listVisible') is True,
         'display=%r' % s0.get('listDisplay'))
    r.ok('its computed display is not none', s0.get('listDisplay') != 'none',
         'display=%r' % s0.get('listDisplay'))
    r.ok('and it has real height', (s0.get('listBox') or {}).get('h', 0) > 100,
         'box=%r' % (s0.get('listBox'),))
    r.ok('the two drawer buttons exist in the DOM', s0.get('hasOpenBtn') and s0.get('hasCloseBtn'))
    r.ok('but neither is painted at this width',
         s0.get('openVisible') is False and s0.get('closeVisible') is False,
         'open=%r close=%r' % (s0.get('openVisible'), s0.get('closeVisible')))
    r.ok('the drawer is shut', s0.get('open') is False)
    r.eq('and the body is not locked', s0.get('lock'), False)
    r.eq('still exactly one h1 on the page', s0.get('h1'), 1)
    r.ok('and the band does not overflow the viewport',
         (s0.get('overflow') or 0) <= 1, 'overflow=%r' % s0.get('overflow'))

    # ---- the reveal this batch moved in inquiry.js (the band it watches)
    print('-- the floating capsule still waits for a band, and the band moved')
    cap0 = ev(CAP_STATE) or {}
    r.ok('at the top of the page the capsule is not offered yet',
         cap0.get('hidden') is True and cap0.get('visible') is False, '%r' % (cap0,))
    y = scroll_to(r, '.sf-fdetail-config', 300)
    tops = ev("(()=>{const c=document.querySelector('.sf-fdetail-config');"
              "const p=document.querySelector('.sf-fdetail2__params');"
              "return {config:c?Math.round(c.getBoundingClientRect().top):null,"
              "params:p?Math.round(p.getBoundingClientRect().top):null,"
              "half:Math.round(window.innerHeight*0.5)};})()") or {}
    cap1 = ev(CAP_STATE) or {}
    r.ok('the configurator has crossed the halfway line',
         (tops.get('config') if tops.get('config') is not None else 999) <=
         (tops.get('half') or 0), '%r' % (tops,))
    r.ok('and the OLD parameter rows have not — so the reveal is driven by the '
         'configurator, which is the move this batch made',
         (tops.get('params') or 0) > (tops.get('half') or 0), '%r' % (tops,))
    r.ok('so the capsule is offered', cap1.get('visible') is True
         and cap1.get('hidden') is False, '%r' % (cap1,))
    r.ok('it is painted', cap1.get('painted') is True, '%r' % (cap1,))
    ev('window.scrollTo(0,0)')
    time.sleep(0.4)
    cap2 = ev(CAP_STATE) or {}
    r.ok('and the reveal is one-way: scrolling back up does not take it away',
         cap2.get('visible') is True, '%r' % (cap2,))

    # ---- the fallback, at rest: nothing picked, so the dialog keeps the product
    print('-- nothing picked: the dialog panel is still the product')
    r.ok('the dialog carries the carrier field', s0.get('carrierPresent') is True)
    r.eq('and it ships empty', s0.get('carrier'), '')
    r.ok('the dialog panel is the server-rendered specification',
         s0.get('panelTerms') == SERVER_ROWS_158, '%r' % (s0.get('panelTerms'),))
    r.eq('and the panel is not the script\'s own rendering yet', s0.get('panelOwn'), False)
    r.eq('the summary ships hidden', s0.get('summaryHidden'), True)
    r.eq('with no text in it', s0.get('summaryText'), '')
    r.eq('and its note is hidden too', s0.get('noteHidden'), True)
    r.ok('so the no-JS/no-choice page claims nothing about a selection',
         s0.get('summaryVisible') is False, 'visible=%r' % s0.get('summaryVisible'))
    y = scroll_to(r, '.sf-fdetail-config')
    print('   ..   frame 01 at scrollY=%d (viewport %dx%d)' % (y, DESKTOP[0], DESKTOP[1]))
    r.shot('h7d-01-desktop-band.png')

    # ---- a multi group: one value is a scalar, two are an array
    print('-- Flavor (multi): one pick, then two')
    box, why = click_opt(r, 'Chicken')
    r.ok('the Chicken option is clickable', box is not None, why)
    s1 = ev(STATE) or {}
    r.ok('the option reports itself ticked', s1.get('checked') == ['Chicken'],
         '%r' % (s1.get('checked'),))
    r.eq('the option also carries the script\'s style hook', s1.get('onOpts'), 1)
    r.eq('the summary appears', s1.get('summaryHidden'), False)
    r.eq('and names the group and the choice', s1.get('summaryText'), 'Flavor: Chicken')
    r.eq('one value in a multi group posts a scalar, as the endpoint reads it',
         jload(s1.get('carrier')), {'flavor': 'Chicken'})
    r.ok('and the dialog panel now mirrors the choice',
         s1.get('panelTerms') == ['Flavor'] and s1.get('panelValues') == ['Chicken'],
         '%r %r' % (s1.get('panelTerms'), s1.get('panelValues')))
    r.eq('the panel is the script\'s own rendering', s1.get('panelOwn'), True)
    r.eq('the note under the summary is revealed', s1.get('noteHidden'), False)

    box, why = click_opt(r, 'Beef')
    r.ok('the second flavour is clickable', box is not None, why)
    s2 = ev(STATE) or {}
    r.ok('both flavours are ticked', s2.get('checked') == ['Chicken', 'Beef'],
         '%r' % (s2.get('checked'),))
    r.eq('the summary lists both', s2.get('summaryText'), 'Flavor: Chicken, Beef')
    r.eq('two values in a multi group post an array',
         jload(s2.get('carrier')), {'flavor': ['Chicken', 'Beef']})
    r.ok('and the panel shows both', s2.get('panelValues') == ['Chicken, Beef'],
         '%r' % (s2.get('panelValues'),))

    # ---- a single group: a radio, and the value that travels is the slug
    print('-- Container Type (single, radio): exclusivity and value-vs-label')
    box, why = click_opt(r, 'round')
    r.ok('the Round option is clickable', box is not None, why)
    r.ok('Round is ticked', (ev(STATE) or {}).get('checked') == ['Chicken', 'Beef', 'round'],
         '%r' % ((ev(STATE) or {}).get('checked'),))
    box, why = click_opt(r, 'square')
    r.ok('the Square option is clickable', box is not None, why)
    s3 = ev(STATE) or {}
    r.ok('choosing Square released Round: a radio group holds one value',
         'square' in (s3.get('checked') or []) and 'round' not in (s3.get('checked') or []),
         '%r' % (s3.get('checked'),))
    r.eq('exactly one option carries the ticked style in that group', s3.get('onOpts'), 3)
    r.ok('the summary shows the reader-facing LABEL',
         'Container Type: Square' in (s3.get('summaryText') or ''),
         s3.get('summaryText'))
    r.eq('while the carrier posts the slug the endpoint validates',
         (jload(s3.get('carrier')) or {}).get('container'), 'square')

    # ---- Quantity & Pricing: the tier's unit price travels with the number
    print('-- Quantity & Pricing (single): the tier note rides along')
    box, why = click_opt(r, '200')
    r.ok('the price tier option is clickable', box is not None, why)
    s4 = ev(STATE) or {}
    r.eq('the tier posts its quantity', (jload(s4.get('carrier')) or {}).get('pricing'), '200')
    r.ok('and the summary carries the unit price in brackets, so the sales desk '
         'reads a price and not a bare number',
         'Quantity & Pricing: 200 (USD 2.5 / unit)' in (s4.get('summaryText') or ''),
         s4.get('summaryText'))
    r.ok('the panel mirrors the same bracketed form',
         (s4.get('panelValues') or [])[-1] == '200 (USD 2.5 / unit)',
         '%r' % (s4.get('panelValues'),))
    r.eq('and all four picked groups are in the carrier',
         sorted((jload(s4.get('carrier')) or {}).keys()),
         ['container', 'flavor', 'pricing'])
    y = scroll_to(r, '.sf-fdetail-config')
    print('   ..   frame 02 at scrollY=%d: summary %r'
          % (y, s4.get('summaryText')))
    r.shot('h7d-02-desktop-picked.png')

    # ---- the dialog after a choice
    print('-- the dialog after a choice (opened, read, closed — never submitted)')
    y = scroll_to(r, '.sf-fdetail-config')
    box, why = r.click('.sf-float-btn--inquiry')
    r.ok('the inquiry capsule is clickable over the band', box is not None, why)
    r.ok('and the harness stayed on the served page', r.on_page(), r.where_str())
    m = h7b.ev(h7b.MODAL_STATE) or {}
    r.eq('the dialog opened', m.get('open'), True)
    r.ok('it is the inquiry dialog', m.get('title') == 'Send Inquiry', m.get('title'))
    s5 = ev(STATE) or {}
    r.ok('its panel shows the visitor the choice they made, group for group',
         s5.get('panelTerms') == ['Flavor', 'Container Type', 'Quantity & Pricing'],
         '%r' % (s5.get('panelTerms'),))
    r.ok('so what the customer sees is what the sales desk will receive',
         'Chicken, Beef' in (s5.get('panelValues') or [])[0]
         and (s5.get('panelValues') or [])[-1].startswith('200'),
         '%r' % (s5.get('panelValues'),))
    r.ok('the carrier is still the one hidden field the form will post',
         isinstance(jload(s5.get('carrier')), dict), s5.get('carrier'))
    # The submit button is present and is deliberately NOT pressed.
    sub = ev("(()=>{const b=document.querySelector('.sf-inquiry-form__submit');"
             "return {present:!!b, text:b?b.textContent.trim():null,"
             "disabled:b?!!b.disabled:null};})()")
    r.ok('the submit button is there and enabled', sub.get('present') and not sub.get('disabled'),
         '%r' % (sub,))
    print('   ..   frame 03 is the dialog opened over the band (scrollY=%d), '
          'submit NOT pressed' % y)
    r.shot('h7d-03-desktop-dialog-choice.png')
    box, why = r.click('.sf-inquiry-modal__close')
    r.ok('the dialog closes with its own button', box is not None, why)
    r.ok('and the harness is still on the served page', r.on_page(), r.where_str())
    r.eq('closed', (h7b.ev(h7b.MODAL_STATE) or {}).get('hidden'), True)
    r.eq('and nothing navigated away from the detail page',
         (ev(STATE) or {}).get('href'), '/formulas/joint-support-soft-chews/')

    # ---- the restore path, on the one record where it is reachable
    print('-- %s: pick, then UNPICK, and the panel must come back' % PLAIN)
    r.goto(PLAIN, 'h7d-plain', want_ver)
    p0 = ev(STATE) or {}
    r.eq('the plainer record renders its two groups', p0.get('groups'), 2)
    r.ok('with the same shapes the declaration claims',
         group_shape(p0.get('groupInfo')) == [(k, l, (t,), n) for k, l, t, n in GROUPS_PLAIN],
         '%r' % (group_shape(p0.get('groupInfo')),))
    base_terms = p0.get('panelTerms')
    base_vals = p0.get('panelValues')
    r.eq('its dialog opens on the product, as before this batch', p0.get('carrier'), '')
    r.ok('with the server\'s own rows', bool(base_terms) == bool(base_vals),
         '%r %r' % (base_terms, base_vals))
    box, why = click_opt(r, '60')
    r.ok('a pack size is clickable', box is not None, why)
    p1 = ev(STATE) or {}
    r.eq('it posts as a scalar', jload(p1.get('carrier')), {'pack': '60'})
    r.eq('the summary names it', p1.get('summaryText'), 'Pack Size: 60')
    r.ok('the panel switched to the choice',
         p1.get('panelTerms') == ['Pack Size'] and p1.get('panelValues') == ['60'],
         '%r %r' % (p1.get('panelTerms'), p1.get('panelValues')))
    box, why = click_opt(r, '60')
    r.ok('the same option untick\'s', box is not None, why)
    p2 = ev(STATE) or {}
    r.eq('unticking the last group empties the carrier rather than posting a stale one',
         p2.get('carrier'), '')
    r.eq('the summary hides again', p2.get('summaryHidden'), True)
    r.eq('and empties', p2.get('summaryText'), '')
    r.ok('the panel is RESTORED to the server\'s rows, byte for byte',
         p2.get('panelTerms') == base_terms and p2.get('panelValues') == base_vals,
         '%r vs %r' % (p2.get('panelTerms'), base_terms))
    r.eq('and it is no longer the script\'s rendering', p2.get('panelOwn'), False)

    # ------------------------------------------------------------------- phone
    print('-- the drawer at %dx%d' % PHONE)
    r.goto(DETAIL, 'h7d-phone', want_ver)
    r.viewport(*PHONE)
    time.sleep(0.5)
    d0 = ev(STATE) or {}
    r.eq('the band is still there', d0.get('bands'), 1)
    r.eq('still five groups', d0.get('groups'), 5)
    r.eq('the script marked it', d0.get('js'), True)
    r.ok('the drawer button is now PAINTED', d0.get('openVisible') is True,
         'visible=%r box=%r' % (d0.get('openVisible'), d0.get('openBox')))
    r.eq('and it says what it does', d0.get('openText'), 'Build your specification')
    r.eq('and reports itself collapsed', d0.get('openAria'), 'false')
    r.ok('while the option list is collapsed behind it',
         d0.get('listVisible') is False and d0.get('listDisplay') == 'none',
         'display=%r' % d0.get('listDisplay'))
    r.ok('so the price and the CTA are not pushed down the page by seven groups',
         (d0.get('listBox') or {}).get('h', 0) == 0, 'box=%r' % (d0.get('listBox'),))
    r.ok('the phone layout does not scroll sideways',
         (d0.get('overflow') or 0) <= 1, 'overflow=%r' % d0.get('overflow'))
    r.eq('and the page still has one h1', d0.get('h1'), 1)
    r.eq('the drawer is shut', d0.get('open'), False)
    y = scroll_to(r, '.sf-fdetail-config', 90)
    print('   ..   frame 04 at scrollY=%d: the list collapsed, one button in its '
          'place' % y)
    r.shot('h7d-04-phone-closed.png')

    box, why = r.click('.sf-fdetail-config__open')
    r.ok('the drawer button is clickable', box is not None, why)
    r.ok('and the harness stayed on the served page', r.on_page(), r.where_str())
    d1 = ev(STATE) or {}
    r.eq('the drawer opened', d1.get('open'), True)
    r.eq('the body is locked so the page cannot scroll behind it', d1.get('lock'), True)
    r.eq('the button now reports itself expanded', d1.get('openAria'), 'true')
    r.ok('the list is painted', d1.get('listVisible') is True)
    lb = d1.get('listBox') or {}
    vw, vh = d1.get('viewport') or [0, 0]
    r.ok('it is laid out as a fixed overlay, not a reflow',
         d1.get('listPosition') == 'fixed', 'position=%r' % d1.get('listPosition'))
    r.ok('and it covers the viewport',
         lb.get('top') == 0 and lb.get('left') == 0
         and abs(lb.get('w', 0) - vw) <= 1 and abs(lb.get('h', 0) - vh) <= 1,
         'box=%r viewport=%r' % (lb, d1.get('viewport')))
    r.ok('it scrolls internally if the seven groups are long',
         d1.get('listOverflowY') in ('auto', 'scroll'), 'overflow-y=%r' % d1.get('listOverflowY'))
    r.ok('the close button is painted', d1.get('closeVisible') is True)
    r.eq('and it says Done', d1.get('closeText'), 'Done')
    r.ok('it stacks above the list', int(d1.get('closeZ') or 0) > int(d1.get('listZ') or 0),
         'list z=%r close z=%r' % (d1.get('listZ'), d1.get('closeZ')))
    r.ok('focus moved into the drawer',
         'sf-fdetail-config__close' in (d1.get('focus') or ''), d1.get('focus'))
    print('   ..   frame 05: the drawer is fixed, so its own scroll is separate '
          'from the page (page scrollY was %r)'
          % ev('Math.round(window.scrollY)'))
    r.shot('h7d-05-phone-drawer-open.png')

    # ---- is the drawer actually ON TOP? -----------------------------------
    # The declaration puts the list at z-index 96 and its exit at 97. Every other
    # full-screen layer in this stylesheet is at 9998 or above and says so in a
    # comment -- the float stack 9998, the toast and the cookie banner 9999, the
    # inquiry modal 10000/10010, the basket drawer 10001, the lightbox 99999 --
    # all of them deliberately above the banner. A drawer at 96 is below the
    # sticky header (999) as well. That is a stacking order, and a stacking order
    # is only observable in pixels.
    print('-- the drawer against the site\'s other fixed layers')
    pc = ev(PIERCE) or {}
    r.eq('the drawer is the layer being measured', pc.get('open'), True)
    bands = pc.get('bands') or []
    r.ok('nothing is painted over the open drawer', bands == [],
         'pierced by %s' % '; '.join(
             'y%d-%d %s (z=%s)' % (b['from'], b['to'], b['cls'], b['z'])
             for b in bands))
    dn = pc.get('done') or {}
    r.ok('and the drawer\'s only exit is reachable', (dn.get('covered') or 0) == 0,
         'the Done button (%sx%s at y%s) is covered at %s of %s points along its '
         'own centre line'
         % ((dn.get('box') or {}).get('w'), (dn.get('box') or {}).get('h'),
            (dn.get('box') or {}).get('top'), dn.get('covered'), dn.get('total')))
    # Named on purpose: whoever reads the failure should see WHICH layer, not
    # have to reproduce the scan.
    hd = pc.get('header') or {}
    bn = pc.get('banner') or {}
    tp = pc.get('trp') or {}
    print('   ..   the fixed layers on this page: header z=%s sticky=%s box=%s | '
          'cookie banner z=%s shown=%s box=%s | language switcher z=%s pos=%s box=%s '
          '| the drawer: list z=96, exit z=97'
          % (hd.get('z'), hd.get('sticky'), hd.get('box'),
             bn.get('z'), bn.get('shown'), bn.get('box'),
             tp.get('z'), tp.get('pos'), tp.get('box')))
    r.ok('the drawer stacks above every fixed layer on the page',
         int(pc.get('listZ') if pc.get('listZ') is not None else
             (d1.get('listZ') or 0)) > max(int(hd.get('z') or 0),
                                           int(bn.get('z') or 0),
                                           int(tp.get('z') or 0)),
         'the drawer is at %s; header %s, banner %s, switcher %s'
         % (d1.get('listZ'), hd.get('z'), bn.get('z'), tp.get('z')))

    # Everything below runs with the banner out of the way: those assertions are
    # about the drawer's own logic, and an overlay standing on its exit would
    # turn each of them into a second report of the same defect.
    print('-- the drawer\'s own logic, with no other overlay in the way')
    dismiss_banner()
    time.sleep(0.3)
    pc2 = ev(PIERCE) or {}
    bands2 = pc2.get('bands') or []
    r.ok('with the banner answered, nothing but the sticky header paints over '
         'the drawer', bands2 == [] or
         all((b.get('cls') or '').startswith('wp-block-group sf-header') for b in bands2),
         'still pierced by %s' % ('; '.join(
             'y%d-%d %s (z=%s)' % (b['from'], b['to'], b['cls'], b['z'])
             for b in bands2) or 'nothing'))
    dn2 = pc2.get('done') or {}
    centre2 = ev("(()=>{const b=document.querySelector('.sf-fdetail-config__close');"
                 "const x=b.getBoundingClientRect();"
                 "const e=document.elementFromPoint(Math.round(x.left+x.width/2),"
                 "Math.round(x.top+x.height/2));"
                 "return {own:e===b||b.contains(e),cls:e?e.className:null};})()") or {}
    r.ok('and a tap at the exit\'s centre reaches it — the drawer is closable '
         'once the banner is answered', centre2.get('own') is True, '%r' % (centre2,))
    r.ok('but no other layer overlaps the exit at all', (dn2.get('covered') or 1) == 0,
         'covered at %s of %s points along its centre line' % (dn2.get('covered'),
                                                               dn2.get('total')))

    # the drawer is not inert: an option inside it is still a real control
    box, why = click_opt(r, 'Salmon')
    r.ok('an option inside the open drawer is clickable', box is not None, why)
    d2 = ev(STATE) or {}
    r.ok('and the summary updates from inside the drawer',
         d2.get('summaryText') == 'Flavor: Salmon', d2.get('summaryText'))

    box, why = r.click('.sf-fdetail-config__close')
    r.ok('the Done button is clickable', box is not None, why)
    d3 = ev(STATE) or {}
    r.eq('the drawer closed', d3.get('open'), False)
    r.eq('the body lock was released', d3.get('lock'), False)
    r.eq('the button reports collapsed again', d3.get('openAria'), 'false')
    r.ok('the list is collapsed behind it again', d3.get('listVisible') is False)
    r.ok('and focus went back to the button that opened it',
         'sf-fdetail-config__open' in (d3.get('focus') or ''), d3.get('focus'))
    r.ok('while the choice the visitor made inside is still on the page',
         d3.get('summaryText') == 'Flavor: Salmon' and d3.get('summaryHidden') is False,
         '%r hidden=%r' % (d3.get('summaryText'), d3.get('summaryHidden')))

    # one Escape closes the drawer — and, because the dialog is shut, only the drawer
    box, why = r.click('.sf-fdetail-config__open')
    r.ok('the drawer reopens', box is not None, why)
    r.eq('and is open', (ev(STATE) or {}).get('open'), True)
    r.key('Escape')          # exactly once: two presses land the harness on about:blank
    r.ok('the harness is still on the served page after one Escape',
         r.on_page(), r.where_str())
    d4 = ev(STATE) or {}
    r.eq('one Escape closed the drawer', d4.get('open'), False)
    r.eq('and released the lock', d4.get('lock'), False)
    r.eq('the dialog was never involved', (h7b.ev(h7b.MODAL_STATE) or {}).get('hidden'), True)

    # a rotation out of the phone breakpoint must not strand a fixed overlay
    box, why = r.click('.sf-fdetail-config__open')
    r.ok('the drawer opens once more', box is not None, why)
    r.eq('open before the resize', (ev(STATE) or {}).get('open'), True)
    r.viewport(*DESKTOP)
    time.sleep(0.6)
    d5 = ev(STATE) or {}
    r.eq('resizing past the breakpoint closed it', d5.get('open'), False)
    r.eq('and released the lock', d5.get('lock'), False)
    r.ok('the list is visible again as a plain desktop list',
         d5.get('listVisible') is True, 'display=%r' % d5.get('listDisplay'))
    r.ok('and the button is hidden again at this width',
         d5.get('openVisible') is False, d5.get('openVisible'))

    # ------------------------------------------------- the ZH page carries it too
    print('-- the /zh/ page (the same shortcode, one renderer)')
    r.goto(DETAIL_ZH, 'h7d-zh', want_ver)
    z = ev(STATE) or {}
    r.eq('the ZH page carries the band', z.get('bands'), 1)
    r.eq('with the same five groups', z.get('groups'), 5)
    r.ok('and the same group shapes — the renderer, not a copy',
         group_shape(z.get('groupInfo')) == group_shape(s0.get('groupInfo')),
         '%r' % (group_shape(z.get('groupInfo')),))
    r.eq('still exactly one h1', z.get('h1'), 1)
    box, why = click_opt(r, 'Lamb')
    r.ok('an option on the ZH page is clickable', box is not None, why)
    z1 = ev(STATE) or {}
    r.eq('and the mechanism works there identically',
         jload(z1.get('carrier')), {'flavor': 'Lamb'})
    r.eq('with the group label the server printed',
         z1.get('summaryText'), 'Flavor: Lamb')
    r.viewport(*PHONE)
    time.sleep(0.5)
    box, why = r.click('.sf-fdetail-config__open')
    r.ok('and the drawer exists on /zh/ too', box is not None, why)
    r.eq('open', (ev(STATE) or {}).get('open'), True)
    zb = ev(PIERCE) or {}
    print('   ..   frame 06: the same drawer on /zh/. Labels stay English because '
          'the band is the shortcode; pierced here by %s'
          % ('; '.join('%s (z=%s)' % (b['cls'], b['z'])
                       for b in (zb.get('bands') or [])) or 'nothing'))
    r.shot('h7d-06-phone-drawer-zh.png')
    r.ok('and the harness stayed on the served page', r.on_page(), r.where_str())

    # ------------------------------------------------------------ the no-JS page
    print('-- the served bytes: what a visitor without the script gets')
    path = DETAIL
    rc, html, err = run(['curl', '-s', '-u', r.auth, '-H', 'X-SF-Preflight: 1',
                         HOST + path + '?nojs=h7d'])
    r.ok('the page was fetched raw', len(html) > 20000, '%d bytes' % len(html))
    r.ok('and it is the pre-flight copy', h7b.PREFLIGHT_DIR in html)
    r.ok('and it is the candidate version', want_ver in html,
         'no ?ver=%s in the served bytes' % want_ver)
    left = assets_absent(html)
    r.ok('none of the script-created markers is in the served HTML', not left,
         'found: %s' % ', '.join(left))
    for name, needle in NOJS_PRESENT:
        r.ok(name, needle in html, needle[:60])
    r.ok('the real controls are checkboxes and radios, so they work without it',
         html.count('class="sf-fdetail-config__input"') == 19,
         '%d inputs (7 flavour + 1 weight + 3 pack + 7 container + 1 tier = 19)'
         % html.count('class="sf-fdetail-config__input"'))
    r.eq('of which ten are checkboxes and nine are radios',
         (html.count('class="sf-fdetail-config__input" type="checkbox"'),
          html.count('class="sf-fdetail-config__input" type="radio"')), (10, 9))

    errs = r.errors()
    r.ok('no page errors anywhere in the run', not errs.strip(), errs.strip()[:200])
    return r.rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--want-ver', default='2.10.65')
    ap.add_argument('--json', default=None)
    ap.add_argument('--auth', default=os.environ.get('SF_DEV_AUTH') or h7b.DEFAULT_AUTH)
    args = ap.parse_args()

    shots = os.path.join(ROOT, 'docs', 'batchH7d-shots')
    r = h7b.Runner(args.auth, shots)
    r.attach()

    rep = mode_full(r, args.want_ver)
    ok = all(x['ok'] for x in rep.rows)

    out = args.json or os.path.join(ROOT, '_backup', 'b2d-h7d-e2e.json')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump({'rows': rep.rows, 'ver': args.want_ver}, open(out, 'w'), indent=1)
    n = len(rep.rows)
    bad = [x['label'] for x in rep.rows if not x['ok']]
    print('\n%s  batch H7d browser pass  %d/%d  json -> %s'
          % ('PASS' if ok else 'FAIL', n - len(bad), n, out))
    for b in bad:
        print('   FAILED: %s' % b)
    h7b.run(['agent-browser', 'close', '--all'])
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())

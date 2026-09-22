#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H7d — is the drawer's Done button really covered on a phone?

The browser pass failed seven assertions from one cause: the click aimed at
`.sf-fdetail-config__close` landed on `.sf-cookie-banner__manage`. Seven failures
from one hit is what a harness does, and it says nothing about whether a visitor
would hit the same thing. This probe answers the product question and only the
product question:

  * IS THE COOKIE BANNER ON SCREEN when a first-time phone visitor opens the
    drawer? (It is fixed at the bottom, z-index 9999, and the drawer's Done
    button is fixed at bottom:20px, z-index 97 — so the numbers say yes. The
    numbers are not the evidence; the overlap is.)
  * HOW MUCH of the Done button is covered, and does the pixel at its centre
    belong to the banner?
  * IS THERE ANY OTHER WAY OUT of the drawer — a close control above the banner,
    a tap outside, one Escape? If not, the only exit is behind another overlay.

It measures and reports; it changes nothing and asserts nothing about the
candidate being right or wrong.

usage:
    b2d_h7d_banner.py --want-ver 2.10.65
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
    'h7d_e2e', os.path.join(HERE, 'b2d_h7d_e2e.py'))
E = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(E)
h7b = E.h7b

PROBE = """
(()=>{
 const b=document.querySelector('.sf-cookie-banner');
 const d=document.querySelector('.sf-fdetail-config__close');
 const o=document.querySelector('.sf-fdetail-config__open');
 const r=e=>{if(!e)return null;const x=e.getBoundingClientRect();
   return {top:Math.round(x.top),left:Math.round(x.left),w:Math.round(x.width),
           h:Math.round(x.height),bottom:Math.round(x.bottom),right:Math.round(x.right)};};
 const z=e=>e?getComputedStyle(e).zIndex:null;
 const shown=e=>{if(!e)return null;const c=getComputedStyle(e);
   return !e.hidden && c.display!=='none' && c.visibility!=='hidden' && c.opacity!=='0';};
 const br=r(b), dr=r(d), orr=r(o);
 let at=null;
 if(dr && dr.w>0){
   const x=Math.round(dr.left+dr.w/2), y=Math.round(dr.top+dr.h/2);
   const e=document.elementFromPoint(x,y);
   at={x:x,y:y,tag:e?e.tagName:null,cls:e?e.className:null};
 }
 /* how much of the Done button's box is covered: sample a 12x5 grid over it and
    count the points whose topmost element is NOT the Done button itself */
 let grid=null, covered=0, total=0;
 if(dr && dr.w>0 && dr.h>0){
   for(let i=0;i<12;i++){
     for(let j=0;j<5;j++){
       const x=Math.round(dr.left+dr.w*(i+0.5)/12);
       const y=Math.round(dr.top+dr.h*(j+0.5)/5);
       total++;
       const e=document.elementFromPoint(x,y);
       if(!(e===d || (d && d.contains(e)))) covered++;
     }
   }
   grid={covered:covered,total:total};
 }
 /* every other way out of the drawer */
 const closers=[].slice.call(document.querySelectorAll(
   '.sf-fdetail-config__close, .sf-fdetail-config__list button, '+
   '.sf-fdetail-config__x, [data-sf-config-close]')).map(function(e){
     return {cls:e.className, rect:r(e), shown:shown(e), z:z(e)};});
 /* A vertical scan down the middle of the screen, while the drawer is open:
    what is PAINTED at each sample, and whether it belongs to the drawer. A
    full-screen overlay that reports inset:0 in its own box can still be pierced
    by anything with a bigger z-index, and this is how many bands that is. */
 let scan=null;
 const list=document.querySelector('.sf-fdetail-config__list');
 if(list && document.querySelector('[data-sf-config].sf-fdetail-config--open')){
   const rows=[];
   for(let k=0;k<=24;k++){
     const yy=Math.round(innerHeight*k/24);
     const e=document.elementFromPoint(Math.round(innerWidth/2), Math.min(yy,innerHeight-1));
     const inside=!!(e && (list.contains(e) ||
       (e.closest && e.closest('.sf-fdetail-config'))));
     rows.push({y:yy, inside:inside,
       cls:e?(typeof e.className==='string'?e.className.slice(0,42):null):null,
       tag:e?e.tagName:null});
   }
   scan=rows;
 }
 /* per-point attribution along the Done button's centre line: a count says the
    exit is covered, this says by which layer, at which x */
 let sweep=null;
 if(dr && dr.w>0 && dr.h>0){
   sweep=[];
   for(let k=1;k<20;k++){
     const x=Math.round(dr.left+dr.w*k/20);
     const y=Math.round(dr.top+dr.h/2);
     const e=document.elementFromPoint(x,y);
     const own=(e===d||(d&&d.contains(e)));
     if(!own) sweep.push({x:x, cls:e?(typeof e.className==='string'?e.className.slice(0,38):e.tagName):null,
                          z:e?getComputedStyle(e).zIndex:null});
   }
 }
 /* WHO is that? Walk up from the element painted at the bottom centre-right and
    list the chain, with the numbers that decide the stacking order. */
 let chain=null;
 if(document.querySelector('[data-sf-config].sf-fdetail-config--open')){
   const e=document.elementFromPoint(Math.round(innerWidth*0.74), Math.round(innerHeight*0.955));
   chain=[];
   let n=e;
   while(n && n!==document.documentElement && chain.length<14){
     const c=getComputedStyle(n);
     chain.push({tag:n.tagName,
       cls:(typeof n.className==='string'?n.className:'').slice(0,44),
       z:c.zIndex, pos:c.position, transform:c.transform==='none'?null:'set',
       rect:r(n)});
     n=n.parentElement;
   }
   chain.unshift({painted:e?(typeof e.className==='string'?e.className.slice(0,44):e.tagName):null});
 }
 return {
  banner:{shown:shown(b), box:br, z:z(b), text:(b?b.textContent.trim().slice(0,60):null)},
  done:{shown:shown(d), box:dr, z:z(d)},
  opener:{shown:shown(o), box:orr},
  open:!!document.querySelector('[data-sf-config].sf-fdetail-config--open'),
  centreElement:at,
  grid:grid,
  sweep:sweep,
  chain:chain,
  closers:closers,
  scan:scan,
  viewport:[innerWidth,innerHeight]
 };})()
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--want-ver', default='2.10.65')
    ap.add_argument('--auth', default=os.environ.get('SF_DEV_AUTH') or h7b.DEFAULT_AUTH)
    ap.add_argument('--json', default=None)
    args = ap.parse_args()

    out = []
    r = h7b.Runner(args.auth, os.path.join(ROOT, 'docs', 'batchH7d-shots'))
    r.attach()

    def rec(label, obj):
        print('   %-46s %s' % (label, json.dumps(obj)))
        out.append({'label': label, 'value': obj})

    # --- a first-time visitor: fresh session, banner up, phone width ---------
    print('== fresh session, %s at 420x900' % E.DETAIL)
    r.goto(E.DETAIL, 'h7d-banner', args.want_ver)
    r.viewport(420, 900)
    time.sleep(0.6)
    e0 = h7b.ev(PROBE) or {}
    rec('banner before anything', e0.get('banner'))
    rec('Done button (drawer shut)', e0.get('done'))
    rec('drawer state', {'open': e0.get('open')})

    # --- open the drawer -----------------------------------------------------
    box, why = E.click_opt(r, 'Chicken')          # a real selection, inside nothing
    rec('a flavour tick (no drawer open)', {'ok': box is not None, 'why': why})
    r.scroll(0)
    box, why = r.click('.sf-fdetail-config__open')
    rec('the drawer button click', {'ok': box is not None, 'why': why})
    e1 = h7b.ev(PROBE) or {}
    rec('banner with the drawer open', e1.get('banner'))
    rec('Done button (drawer open)', e1.get('done'))
    rec('drawer open', {'open': e1.get('open')})
    rec('what is painted at the Done button centre', e1.get('centreElement'))
    rec('how much of the Done button is covered', e1.get('grid'))
    rec('which layer covers the exit, at which x — banner up', e1.get('sweep'))
    rec('every close control in the drawer', e1.get('closers'))
    for i, step in enumerate((e1.get('chain') or [])[:10]):
        rec('ancestor chain [%d]' % i, step)
    sc = e1.get('scan') or []
    pierced = [x for x in sc if not x.get('inside')]
    rec('the drawer surface is pierced at %d of %d sample rows'
        % (len(pierced), len(sc)),
        [{'y': x['y'], 'tag': x['tag'], 'cls': x['cls']} for x in pierced])
    runs = []
    for x in pierced:
        if runs and runs[-1]['to'] >= x['y'] - 40:
            runs[-1]['to'] = x['y']
            runs[-1]['n'] += 1
        else:
            runs.append({'from': x['y'], 'to': x['y'], 'n': 1,
                         'cls': x['cls']})
    rec('as contiguous bands', runs)
    r.shot('h7d-07-banner-over-drawer.png')

    # --- is a tap outside the list a way out? --------------------------------
    tapped = h7b.ev("(()=>{const x=Math.round(innerWidth/2), y=60;"
                    "const e=document.elementFromPoint(x,y);"
                    "return {tag:e?e.tagName:null, cls:e?e.className:null};})()")
    rec('what is at (mid, 60) — is there an outside to tap', tapped)

    # --- one Escape, the keyboard-only exit ----------------------------------
    r.key('Escape')
    e2 = h7b.ev(PROBE) or {}
    rec('after one Escape', {'open': e2.get('open'),
                             'banner': (e2.get('banner') or {}).get('shown'),
                             'on_page': r.on_page()})

    # --- the same measurement with consent already given ---------------------
    print('== with the cookie banner dismissed (as a returning visitor has it)')
    h7b.ev("(()=>{const b=document.querySelector('.sf-cookie-banner');"
           "if(b){b.hidden=true;b.style.display='none';} return true;})()")
    box, why = r.click('.sf-fdetail-config__open')
    rec('the drawer button click (banner gone)', {'ok': box is not None, 'why': why})
    e3 = h7b.ev(PROBE) or {}
    rec('Done button with no banner', e3.get('done'))
    rec('what is painted at its centre now', e3.get('centreElement'))
    rec('how much is covered now', e3.get('grid'))
    rec('which layer covers the exit, at which x — with the banner down',
        e3.get('sweep'))
    box, why = r.click('.sf-fdetail-config__close')
    rec('the Done click', {'ok': box is not None, 'why': why})
    rec('drawer open after Done', {'open': (h7b.ev(PROBE) or {}).get('open')})

    errs = r.errors()
    rec('page errors', errs.strip()[:200])

    dst = args.json or os.path.join(ROOT, '_backup', 'b2d-h7d-banner.json')
    json.dump(out, open(dst, 'w'), indent=1)
    print('\njson -> %s' % dst)
    h7b.run(['agent-browser', 'close', '--all'])
    return 0


if __name__ == '__main__':
    sys.exit(main())

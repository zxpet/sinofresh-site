#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H7c — the browser pass.

The byte gate proved the sheet is emitted on the right 42 pages, once each, in
the right place in the source, with the declared rows and no others. Four things
it cannot see, all of them about layout:

  * WHETHER THE TWO COLUMNS ARE SIDE BY SIDE. The declaration proves the CSS is
    in the file, in order, with the phone step below its base rule -- and none of
    that means a reader gets two columns. This is the batch H7b lesson applied:
    a media query adds no specificity, so a rule can be present, ordered, and
    dead. The only way to know is to read the computed grid back.
  * WHETHER THE ROWS STACK ON A PHONE, for the same reason in reverse.
  * WHERE THE SHEET LANDS ON THE SCREEN, not in the source. The `order`
    invariant checks four anchors in the HTML byte string; a section can sit in
    the right place in the file and be moved off-screen (or behind the fold of an
    absolutely positioned sibling) by CSS.
  * WHETHER THE EMPTY ROWS ARE ACTUALLY ABSENT to a reader. The coverage pass
    counts the label strings in the bytes, which is the same fact only as long as
    nothing re-adds them; the reading is "Applicable Pet" is not on the page.

usage:
    b2d_h7c_e2e.py --want-ver 2.10.64
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

DETAIL = h7b.DETAIL
DETAIL_ZH = h7b.DETAIL_ZH
PHONE = (420, 900)
DESKTOP = h7b.DESKTOP

# The four anchors are the gate's own `order` declaration, in the same sequence:
# media parameter list -> the sheet -> the Specification band -> the actives band.
ORDER_ANCHORS = [
    ('.sf-fdetail2__params', 'media parameter list'),
    ('.sf-fdetail-specs', 'the spec sheet'),
    ('.sf-fdetail__grid', 'the Specification band'),
    ('.sf-fdetail-actives__inner', 'the actives band'),
]

SPECS_STATE = """
(()=>{
 const s=document.querySelector('.sf-fdetail-specs');
 const box=e=>{const r=e.getBoundingClientRect();
   return {top:Math.round(r.top+scrollY),left:Math.round(r.left),
           w:Math.round(r.width),h:Math.round(r.height),
           bottom:Math.round(r.bottom+scrollY)};};
 const probe=(sel)=>{const e=document.querySelector(sel); return e? box(e): null;};
 const orderAnchors=%(anchors)s.map(function(p){return {sel:p[0],label:p[1],b:probe(p[0])};});
 if(!s) return {present:false, count:0,
   orderAnchors:orderAnchors,
   h1:document.querySelectorAll('h1').length,
   overflow:document.documentElement.scrollWidth-window.innerWidth};
 const groups=[].slice.call(s.querySelectorAll('.sf-fdetail-specs__group'));
 const rows=[].slice.call(s.querySelectorAll('.sf-fdetail-specs__row'));
 const chips=[].slice.call(s.querySelectorAll('.sf-fdetail-specs__chip'));
 const inner=s.querySelector('.sf-fdetail-specs__inner');
 const grid=inner?getComputedStyle(inner):null;
 const cs=chips.length?getComputedStyle(chips[0]):null;
 const terms=rows.map(function(r){const t=r.querySelector('.sf-fdetail-specs__term');
   return t?t.textContent.trim():null;});
 const vals=rows.map(function(r){const v=r.querySelector('.sf-fdetail-specs__value');
   return v?v.textContent.trim().replace(/\\s+/g,' '):null;});
 return {
  present:true,
  count:document.querySelectorAll('.sf-fdetail-specs').length,
  groups:groups.length,
  groupBoxes:groups.map(box),
  rows:rows.length,
  terms:terms,
  values:vals,
  chips:chips.length,
  chipRadius:cs?cs.borderRadius:null,
  chipBorderStyle:cs?cs.borderStyle:null,
  columns:grid?grid.gridTemplateColumns:null,
  columnGap:grid?grid.columnGap:null,
  box:box(s),
  orderAnchors:orderAnchors,
  h1:document.querySelectorAll('h1').length,
  h1InSection:s.querySelectorAll('h1').length,
  h2InSection:s.querySelectorAll('h2').length,
  overflow:document.documentElement.scrollWidth-window.innerWidth,
  viewportW:window.innerWidth
 };})()
""" % {'anchors': json.dumps([[a, l] for a, l in ORDER_ANCHORS])}


# Row budget: the declaration offers twelve rows and drops the empty ones, so a
# page can legitimately present anywhere from a handful to all twelve. The
# assertions below are therefore "within budget and internally consistent", not
# one blessed number -- which is also why the byte gate asserts per-page counts
# (8/9/10 rows across the 42 pages) instead of one figure.
ROW_MIN, ROW_MAX = 8, 12
EMPTY_LABELS = ('Applicable Pet', 'Life Stage', 'Lead Time')


def tracks(value):
    """Split a computed grid-template-columns into its tracks.

    Computed values come back as pixel sizes ("484px 484px") or as the keywords
    the declaration wrote; either way the number of tracks is the count of
    top-level space-separated terms, and that is what "two columns" means.
    """
    if not value:
        return []
    return [t for t in value.replace('repeat(', ' ').replace(')', ' ')
            .replace(',', ' ').split() if t and t not in ('/',)]


def mode_full(r, want_ver):
    rep = r.rep

    # ---- desktop ---------------------------------------------------------
    r.goto(DETAIL, 'h7c', want_ver)
    d = h7b.ev(SPECS_STATE) or {}
    rep.ok('the sheet is on the page', d.get('present') is True)
    rep.ok('and there is exactly one of it', d.get('count') == 1,
           'count=%r' % d.get('count'))
    rows = d.get('rows') or 0
    rep.ok('the row count is inside the declared budget',
           ROW_MIN <= rows <= ROW_MAX, 'rows=%d want %d..%d' % (rows, ROW_MIN, ROW_MAX))
    terms = d.get('terms') or []
    rep.ok('every rendered row has a label',
           bool(terms) and all(terms), '%r' % (terms,))
    rep.ok('and every one of them has a value',
           bool(d.get('values')) and all(d.get('values')), '%r' % (d.get('values'),))
    rep.ok('no two rows carry the same label', len(set(terms)) == len(terms))
    for label in EMPTY_LABELS:
        rep.ok('an empty %s row is not rendered' % label, label not in terms,
               'terms=%r' % (terms,))

    # the layout claim: two columns, and they are actually beside each other
    gb = d.get('groupBoxes') or []
    rep.eq('there are two column groups', d.get('groups'), 2)
    if len(gb) == 2:
        rep.ok('the two groups sit on the same line',
               abs(gb[0]['top'] - gb[1]['top']) <= 4,
               'tops %d vs %d' % (gb[0]['top'], gb[1]['top']))
        rep.ok('and in different columns',
               gb[1]['left'] - gb[0]['left'] > 100,
               'lefts %d vs %d' % (gb[0]['left'], gb[1]['left']))
    rep.ok('the grid computes to two tracks', len(tracks(d.get('columns'))) == 2,
           'grid-template-columns=%r' % d.get('columns'))
    rep.ok('with a column gap between them',
           (d.get('columnGap') or '0px') not in ('0px', 'normal'),
           'column-gap=%r' % d.get('columnGap'))
    chips = d.get('chips') or 0
    rep.ok('the value chips are rendered', 1 <= chips <= 3,
           'chips=%d (ingredients are capped at three)' % chips)
    rep.ok('and they are pills, not boxes',
           (d.get('chipRadius') or '0px').endswith('px')
           and float((d.get('chipRadius') or '0px')[:-2] or 0) >= 100,
           'border-radius=%r' % d.get('chipRadius'))

    # the heading invariants, seen from the browser
    rep.eq('the page still carries exactly one h1', d.get('h1'), 1)
    rep.eq('the sheet introduces no h1 of its own', d.get('h1InSection'), 0)
    rep.eq('and no h2 either', d.get('h2InSection'), 0)

    # placement, measured on screen
    anchors = d.get('orderAnchors') or []
    have = [(a['label'], a['b']) for a in anchors if a.get('b')]
    rep.ok('all four placement anchors resolve on the page',
           len(have) == len(ORDER_ANCHORS),
           'found %s' % ', '.join('%s@%s' % (l, b['top']) for l, b in have))
    tops = [b['top'] for _, b in have]
    rep.ok('and they appear down the page in the declared order',
           tops == sorted(tops) and len(set(tops)) == len(tops),
           ' -> '.join('%s@%d' % (l, b['top']) for l, b in have))
    rep.ok('nothing overflows the viewport at 1440', (d.get('overflow') or 0) <= 1,
           'overflow=%rpx' % d.get('overflow'))

    r.scroll(0)
    r.shot('h7c-desktop-page.png')
    y = (d.get('box') or {}).get('top', 0)
    r.scroll(max(0, y - 90))
    r.shot('h7c-desktop-specs.png')
    # a frame that carries the media band and the sheet together: the placement
    # claim as a reader sees it, not as the source orders it
    if have:
        r.scroll(max(0, have[0][1]['top'] - 90))
        r.shot('h7c-desktop-placement.png')
    rep.ok('and the harness stayed on the served page', r.on_page(), r.where_str())

    # ---- phone -----------------------------------------------------------
    r.viewport(*PHONE)
    time.sleep(0.6)
    p = h7b.ev(SPECS_STATE) or {}
    rep.ok('the sheet is still there at 420', p.get('present') is True)
    pgb = p.get('groupBoxes') or []
    rep.eq('still two groups in the markup', p.get('groups'), 2)
    if len(pgb) == 2:
        rep.ok('but they are stacked, not side by side',
               pgb[1]['top'] >= pgb[0]['bottom'] - 2,
               'group0 bottom=%d group1 top=%d' % (pgb[0]['bottom'], pgb[1]['top']))
        rep.ok('and share the same left edge',
               abs(pgb[0]['left'] - pgb[1]['left']) <= 2,
               'lefts %d vs %d' % (pgb[0]['left'], pgb[1]['left']))
    rep.ok('the grid computes to one track',
           len(tracks(p.get('columns'))) == 1,
           'grid-template-columns=%r' % p.get('columns'))
    rep.ok('the sheet fits the phone width',
           (p.get('box') or {}).get('w', 0) <= (p.get('viewportW') or 0) + 1,
           'w=%r viewport=%r' % ((p.get('box') or {}).get('w'), p.get('viewportW')))
    rep.ok('and the page does not scroll sideways',
           (p.get('overflow') or 0) <= 1, 'overflow=%rpx' % p.get('overflow'))
    rep.eq('the h1 count is unchanged on a phone', p.get('h1'), 1)
    py = (p.get('box') or {}).get('top', 0)
    r.scroll(max(0, py - 70))
    r.shot('h7c-phone-specs.png')
    rep.ok('and the harness stayed on the served page', r.on_page(), r.where_str())

    # ---- the German/Spanish-carrying ZH page -----------------------------
    r.goto(DETAIL_ZH, 'h7c-zh', want_ver)
    z = h7b.ev(SPECS_STATE) or {}
    rep.ok('the ZH page carries the sheet too', z.get('present') is True)
    rep.eq('once, like the English one', z.get('count'), 1)
    rep.eq('with the same two groups', z.get('groups'), 2)
    rep.ok('and the same row budget',
           ROW_MIN <= (z.get('rows') or 0) <= ROW_MAX, 'rows=%r' % z.get('rows'))
    rep.eq('the ZH page still has exactly one h1', z.get('h1'), 1)
    zt = z.get('terms') or []
    rep.ok('the ZH sheet renders the same labels (the shortcode, not a copy)',
           zt == (d.get('terms') or []), 'zh=%r en=%r' % (zt, d.get('terms')))
    r.viewport(*PHONE)
    time.sleep(0.6)
    r.scroll(max(0, (z.get('box') or {}).get('top', 0) - 70))
    r.shot('h7c-phone-specs-zh.png')
    rep.ok('and the harness stayed on the served page', r.on_page(), r.where_str())

    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--want-ver', default='2.10.64')
    ap.add_argument('--out', default=None)
    ap.add_argument('--shots', default=None)
    ap.add_argument('--auth', default=os.environ.get('SF_DEV_AUTH') or h7b.DEFAULT_AUTH)
    args = ap.parse_args()

    shots = args.shots or os.path.join(ROOT, 'docs', 'batchH7c-shots')
    r = h7b.Runner(args.auth, shots)
    r.attach()

    rep = mode_full(r, args.want_ver)
    ok = all(x['ok'] for x in rep.rows)

    out = args.out or os.path.join(ROOT, '_backup', 'b2d-h7c-full.json')
    json.dump({'rows': rep.rows}, open(out, 'w'), indent=1)
    print('\n%s  batch H7c browser pass  json -> %s' % ('PASS' if ok else 'FAIL', out))
    h7b.run(['agent-browser', 'close', '--all'])
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())

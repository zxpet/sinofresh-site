#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H6 — screenshots.

H6 deletes: 48 dead CSS selectors (8,976 B), a dead JS branch and write, an
orphaned shortcode renderer, and a JSON payload that was printed into 60 pages
and read by nobody. Not one of those is something a photograph can show. A
deleted selector has no pixels; a deleted `<script>` does not cast a shadow.

So these frames claim the two things a byte gate cannot state:

  * THE SITE STILL LOOKS LIKE ITSELF. 8,976 B left the stylesheet of a theme
    that uses `:has()` heavily. The geometry sweep compares 81 page-views
    element by element; a frame is what makes that comparison inspectable by a
    person, and it is the only check that would catch "the gate and the browser
    agree, and both are looking at a broken page".
  * THE BUTTON THE DELETED BRANCH BELONGED TO STILL WORKS. The E2E asserts the
    toast branch; the frame after a real click shows it.

WHAT IS NOT PHOTOGRAPHED, AND WHY THAT IS NOT AN OMISSION

There is no "before" frame. The baseline copy is no longer installed, and
re-installing it to take pictures would buy nothing the geometry pass does not
already state numerically: the two-state claim is 81 element-by-element
comparisons over two installs, not two PNGs. A hand-picked pair of images would
be the weaker evidence dressed as the stronger.

Two measured facts about element crops (established in batch H5 on this site,
re-confirmed here): `screenshot <selector>` returns a correct crop only while
the element is inside the initial scrollY=0 viewport; scrolling first — even
via the guide's own scrollIntoView — yields a blank block at the right
dimensions. So regions below the fold are taken as VIEWPORT frames after
scrolling to them, and the scroll offset is printed in the note.

usage:
    b2d_h6_shots.py --out DIR
"""
import argparse
import importlib.util
import json
import os
import struct
import sys
import time
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    'h6e2e', os.path.join(HERE, 'b2d_h6_e2e.py'))
E = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(E)

FORMULA_EN = '/formulas/joint-support-soft-chews/'
FORMULA_ZH = '/zh/formulas/joint-support-soft-chews/'
DOSAGE_EN = '/products/soft-chews/'
ARCHIVE = '/formulas/'

FLOOR = 400          # truncated / empty file only; not a quality proxy
MIN_DISTINCT = 8     # scanlines of a real render vary; a blank one is constant


def png_probe(path):
    """(width, height, distinct byte values in the decompressed IDAT)."""
    with open(path, 'rb') as fh:
        data = fh.read()
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('not a PNG: %s' % path)
    w = h = None
    idat = bytearray()
    i = 8
    while i + 12 <= len(data):
        ln = struct.unpack('>I', data[i:i + 4])[0]
        typ = data[i + 4:i + 8]
        body = data[i + 8:i + 8 + ln]
        if typ == b'IHDR':
            w, h = struct.unpack('>II', body[:8])
        elif typ == b'IDAT':
            idat += body
        elif typ == b'IEND':
            break
        i += 12 + ln
    if w is None:
        raise ValueError('no IHDR in %s' % path)
    return w, h, len(set(zlib.decompress(bytes(idat))))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--auth', default=os.environ.get('SF_DEV_AUTH',
                                                     'sfdev:VkEws18Kl5V1qp3TpZ6s'))
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    s = E.E2E(args.auth)
    s.attach()

    taken, fails, rounding = [], [], []

    def shot(name, selector=None, full=False, want=None, note=''):
        path = os.path.join(args.out, name)
        cmd = ['agent-browser', 'screenshot']
        if full:
            cmd.append('--full')
        if selector:
            cmd.append(selector)
        cmd.append(path)
        E.run(cmd)
        if not os.path.exists(path):
            fails.append('%s was not written' % name)
            print('   %-32s   MISSING   %s' % (name, note))
            return
        size = os.path.getsize(path)
        try:
            w, h, distinct = png_probe(path)
        except Exception as exc:
            fails.append('%s unreadable: %s' % (name, exc))
            print('   %-32s   BAD PNG   %s' % (name, note))
            return
        taken.append((name, note, size))
        bad = []
        if want:
            if full:
                if w != want[0] or h < want[1]:
                    bad.append('is %dx%d, expected %d wide and >=%d tall'
                               % (w, h, want[0], want[1]))
            elif abs(w - want[0]) > 1 or abs(h - want[1]) > 1:
                bad.append('is %dx%d, expected %dx%d' % (w, h, want[0], want[1]))
            elif (w, h) != want:
                rounding.append('%s: %dx%d vs measured %dx%d'
                                % (name, w, h, want[0], want[1]))
        if distinct < MIN_DISTINCT:
            bad.append('only %d distinct byte values — a flat capture' % distinct)
        if size < FLOOR:
            bad.append('%d bytes — truncated' % size)
        if bad:
            fails.append('%s %s' % (name, '; '.join(bad)))
            print('   %-32s %8d B  %4dx%-5d  FAIL  %s'
                  % (name, size, w, h, '; '.join(bad)))
        else:
            print('   %-32s %8d B  %4dx%-5d  %s' % (name, size, w, h, note))

    def view(path, width, height, tag):
        """Measure with the provenance assertion at the requested viewport."""
        E.DESKTOP = (width, height)
        return s.goto(path, tag)

    def box(selector):
        r = E.ev('(function(){var e=document.querySelector(%s);'
                 'if(!e)return null;var b=e.getBoundingClientRect();'
                 'return [Math.round(b.width), Math.round(b.height)];})()'
                 % json.dumps(selector))
        if not isinstance(r, list) or len(r) != 2:
            raise SystemExit('FATAL %s is not on the page — refusing to shoot a '
                             'frame whose box cannot be checked' % selector)
        return (r[0], r[1])

    def viewport_box():
        r = E.ev('[window.innerWidth, window.innerHeight]')
        return (r[0], r[1])

    def scroll_to(selector, margin=140):
        y = E.ev('(function(){var e=document.querySelector(%s);if(!e)return null;'
                 'return Math.max(0, Math.round(e.getBoundingClientRect().top'
                 ' + window.scrollY - %d));})()'
                 % (json.dumps(selector), margin))
        if y is None:
            raise SystemExit('FATAL %s is not on the page — refusing to scroll '
                             'to nothing' % selector)
        E.ev('window.scrollTo(0, %d)' % y)
        time.sleep(1.1)
        return y

    # --- desktop, English: the dosage page, where the card grid lives -------
    st = view(DOSAGE_EN, 1440, 900, 'shots-en-dose')
    shot('01-dose-top.png', want=viewport_box(),
         note='dosage page top after 8,976 B left the stylesheet')

    # A crop is only trustworthy inside the initial scrollY=0 viewport (see the
    # docstring), and the card CTA here sits below the fold: asking for its crop
    # on the first run returned a blank block of exactly the right size (192 B,
    # 4 distinct byte values) — the failure mode the docstring warns about, and
    # the png_probe caught it. So this region is a VIEWPORT frame, with the
    # offset in the note. The detail page's hero CTA (frame 06) is above the
    # fold and is shot as a true crop.
    y = scroll_to('.sf-formula__cta')
    shot('02-dose-cta.png', want=viewport_box(),
         note='the K1 button in the card wall (the deleted branch served it) '
              'at y=%d' % y)

    y = scroll_to('.sf-fcard')
    shot('03-dose-cardwall.png', want=viewport_box(),
         note='the card wall, %d cards (baseline count 4) at y=%d'
              % (st['ctaCount'], y))

    # --- the money shot: the toast after a real click ----------------------
    c = s.click_cta('.sf-formula__cta')
    time.sleep(0.3)
    toast = E.ev("(document.querySelector('.sf-toast')||{}).textContent||null")
    shot('04-dose-toast-after-click.png', want=viewport_box(),
         note='after a real click: %r (hit %s)' % (toast, c['hit']))

    # --- desktop, English: the formula detail page -------------------------
    st = view(FORMULA_EN, 1440, 900, 'shots-en-formula')
    shot('05-detail-top.png', want=viewport_box(),
         note='detail page: hero, right column, %d h1 in the page' % st['h1'])
    shot('06-detail-hero-cta-crop.png', '.sf-formula__cta',
         want=box('.sf-formula__cta'),
         note='the hero CTA: %r' % st['ctaName'])

    # The band's container is `section.sf-fdetail-actives`; there is no
    # `.sf-actives` anywhere on the site (0 hits in all four captures, baseline
    # included — asked for it by mistake on the first run and the script refused
    # to scroll to nothing). The `sf-actives__*` classes inside it are the
    # helpers the orphan removal deliberately kept.
    y = scroll_to('.sf-fdetail-actives')
    shot('07-detail-actives.png', want=viewport_box(),
         note='the band whose helpers survived the orphan removal '
              '(%d pills, %d labels) at y=%d' % (st['pills'], st['labels'], y))
    y = scroll_to('.sf-fdetail-more')
    shot('08-detail-more.png', want=viewport_box(),
         note='the "more formulas" grid (the second link source) at y=%d' % y)

    E.ev('window.scrollTo(0, 0)')
    time.sleep(0.7)
    shot('09-detail-full.png', full=True, want=viewport_box(),
         note='the whole detail page in one frame')

    # --- desktop, English: the archive -------------------------------------
    st = view(ARCHIVE, 1440, 900, 'shots-en-archive')
    y = scroll_to('.sf-fgrid')
    shot('10-archive-grid.png', want=viewport_box(),
         note='the archive grid, %d cards at y=%d' % (st['ctaCount'], y))

    # --- desktop, Chinese --------------------------------------------------
    st = view(FORMULA_ZH, 1440, 900, 'shots-zh-formula')
    y = scroll_to('.sf-fdetail-actives')
    shot('11-zh-detail-actives.png', want=viewport_box(),
         note='the same band on /zh/ (%d pills) at y=%d' % (st['pills'], y))

    # --- phone -------------------------------------------------------------
    view(DOSAGE_EN, 390, 844, 'shots-phone-dose')
    shot('12-phone-dose-top.png', want=viewport_box(),
         note='phone 390x844, dosage page top')
    y = scroll_to('.sf-fcard')
    shot('13-phone-dose-cards.png', want=viewport_box(),
         note='phone, the card wall at y=%d' % y)
    view(FORMULA_EN, 390, 844, 'shots-phone-formula')
    shot('14-phone-detail-top.png', want=viewport_box(),
         note='phone, detail page top')

    E.run(['agent-browser', 'close', '--all'])

    print()
    for r in rounding:
        print('   note rounding: %s' % r)
    if fails:
        for f in fails:
            print('   FAIL %s' % f)
        print('VERDICT: FAIL — %d of %d frames rejected'
              % (len(fails), len(taken) + len(fails)))
        return 1
    print('VERDICT: PASS — %d frames, each a real render the size it claims '
          '(min %d B, max %d B)' % (len(taken), min(t[2] for t in taken),
                                    max(t[2] for t in taken)))
    return 0


if __name__ == '__main__':
    sys.exit(main())

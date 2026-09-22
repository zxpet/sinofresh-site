#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H5 — screenshots.

H5 changes what crawlers read, not what a visitor sees: the four scopes are a
schema key set, an audience, a related-to list and an alt string. A screenshot
cannot show a JSON key. So this batch's frames are not "proof of the change" —
they are proof of the two things a byte gate cannot say:

  * the page still renders, and renders the same page, after the renderer that
    emits the schema was edited (the schema is printed by the same PHP that
    prints the band above it, so a schema edit is a template edit);
  * the specific elements the four scopes read FROM are on the page and intact —
    the facts band the dosage additionalProperty mirrors, the card grid
    isRelatedTo mirrors, the gallery stage whose aria-label is the live
    accessibility name of the string, and the run-time thumbnail strip that is
    the fourth carrier (built by the gallery script, so it exists in no capture).

Every frame carries the provenance assertion, because Sweep.measure refuses to
return unless the served stylesheet came from the pre-flight copy AND the page
renders the post-batch logo alt. That is the one failure this batch is exposed
to: a wrong header order serves the live theme and every frame below would then
be a picture of the wrong site, silently.

TWO MEASURED FACTS ABOUT ELEMENT CROPS, AND WHAT THE FRAMES ARE BUILT FROM

Both were established by experiment on this site, not assumed:

  * `screenshot <selector>` returns a CORRECT crop only while the element sits
    inside the initial (scrollY=0) viewport. Scrolling first — by hand or by the
    guide's own scrollIntoView — makes it come back a flat block of the
    element's background, with the RIGHT dimensions. `scrollIntoView` was tried
    as the fix and made things worse: it turned a working crop (`.sf-facts-mini`,
    22,935 B) into a blank one (474 B).
  * so a below-the-fold source cannot be photographed by cropping it at all.
    The frames for those regions are VIEWPORT frames taken after scrolling to
    the target, which renders correctly (verified: 1440x900, 256 distinct byte
    values).

That is also why the check is dimensions + flatness and not a byte floor: the
blank crops pass a byte floor sized for anything else, and 474 B vs 22,935 B is
the only difference that shows up.

  * GEOMETRY — the PNG's own IHDR must match the box of the element the frame
    claims to show, or the viewport. A silently ignored selector comes back
    viewport-sized and the dimensions say so. A 1px gap is rounding
    (getBoundingClientRect is fractional) and is printed as a note, not hidden.
  * NOT FLAT — the decompressed pixel stream must hold more than a handful of
    distinct byte values. This is the check that caught the blank crop.

PNG is read with the standard library (struct + zlib): the claim "this is a real
render of this box" should not depend on an imaging package being installed.

It drives the E2E tool's session rather than starting a second driver: two
drivers disagree eventually, and the one nobody runs is the one that is wrong.

scope, stated plainly: desktop 1440x900, one 390x844 pass, one `--full` frame.
H5 touches no CSS, so a geometry sweep would vary a variable this batch does not
move; what is claimed here is a set of frames showing the sources the schema
mirrors, and it is claimed as such.

usage:
    b2d_h5_shots.py --sha <preflight-sha> --out DIR
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
    'h5e2e', os.path.join(HERE, 'b2d_h5_e2e.py'))
E = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(E)

FORMULA_EN = '/formulas/joint-support-soft-chews/'
FORMULA_ZH = '/zh/formulas/joint-support-soft-chews/'
DOSAGE_EN = '/products/soft-chews/'
DOSAGE_ZH = '/zh/products/soft-chews/'

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
    ap.add_argument('--sha', required=True)
    ap.add_argument('--auth', default=os.environ.get('SF_DEV_AUTH',
                                                     'sfdev:VkEws18Kl5V1qp3TpZ6s'))
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    s = E.Sweep(args.auth, args.sha)
    s.attach()

    taken = []
    fails = []
    rounding = []

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
            print('   %-34s   MISSING   %s' % (name, note))
            return
        size = os.path.getsize(path)
        try:
            w, h, distinct = png_probe(path)
        except Exception as exc:
            fails.append('%s unreadable: %s' % (name, exc))
            print('   %-34s   BAD PNG   %s' % (name, note))
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
            print('   %-34s %8d B  %4dx%-5d  FAIL  %s'
                  % (name, size, w, h, '; '.join(bad)))
        else:
            print('   %-34s %8d B  %4dx%-5d  %s' % (name, size, w, h, note))

    def view(path, width, height, tag, scroll_to=None):
        """Measure with provenance at the requested viewport, then settle.

        DESKTOP is read by measure() at call time, so re-pointing it is how a
        second viewport reuses the same code path — including the provenance
        assertion, which a hand-rolled viewport call would skip.
        """
        E.DESKTOP = (width, height)
        st = s.measure(path, tag)
        if scroll_to is not None:
            E.ev('window.scrollTo(0, %d)' % scroll_to)
            time.sleep(0.6)
        return st

    def box(selector):
        """The element's rendered box, as an element crop must come back."""
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
        """Scroll the target into the upper viewport; return the offset used.

        Used for the regions that cannot be cropped (see the module docstring):
        the frame is then the viewport, and the offset goes in the note so a
        reader knows which part of the page they are looking at.
        """
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

    # --- desktop, English: the formula page -------------------------------
    view(FORMULA_EN, 1440, 900, 'shots-en-top')
    shot('01-desktop-top.png', want=viewport_box(),
         note='formula page, top — the hero and the gallery')

    # crops: taken while the page is still at scrollY=0, which is the only
    # position where a crop is trustworthy (see the docstring).
    shot('02-desktop-gallery-stage.png', '.sf-gallery__stage',
         want=box('.sf-gallery__stage'),
         note='the stage: aria-label is the live a11y name of the still')
    shot('03-desktop-gallery-frame.png', '.sf-gallery__slide[id$="-1"]',
         want=box('.sf-gallery__slide[id$="-1"]'),
         note='the first frame: alt + data-label live here')
    shot('04-desktop-gallery-thumbs.png', '.sf-gallery__thumbs',
         want=box('.sf-gallery__thumbs'),
         note='carrier 4: built at run time; its imgs must stay decorative')

    vp = viewport_box()
    y = scroll_to('.sf-fcard')
    shot('05-desktop-cardwall.png', want=vp,
         note='the card wall isRelatedTo mirrors, in order (viewport at y=%d)' % y)
    y = scroll_to('.sf-fdetail-more')
    shot('06-desktop-more.png', want=vp,
         note='the "more formulas" grid, the second link source (y=%d)' % y)

    E.ev('window.scrollTo(0, 0)')
    time.sleep(0.7)
    shot('07-desktop-full.png', full=True, want=vp,
         note='full page, formula, desktop')

    # --- desktop, English: the dosage page --------------------------------
    view(DOSAGE_EN, 1440, 900, 'shots-en-facts')
    y = scroll_to('.sf-facts-mini')
    shot('08-dosage-facts.png', want=viewport_box(),
         note='the four rows additionalProperty mirrors (y=%d)' % y)

    # --- desktop, Chinese: both page kinds --------------------------------
    view(FORMULA_ZH, 1440, 900, 'shots-zh-formula')
    shot('09-zh-gallery-stage.png', '.sf-gallery__stage',
         want=box('.sf-gallery__stage'),
         note='the same stage on /zh/ — the EN/ZH serialisation differs')

    view(DOSAGE_ZH, 1440, 900, 'shots-zh-facts')
    y = scroll_to('.sf-facts-mini')
    shot('10-zh-dosage-facts.png', want=viewport_box(),
         note='the facts band on /zh/ (y=%d)' % y)

    # --- phone ------------------------------------------------------------
    view(DOSAGE_EN, 390, 844, 'shots-phone')
    shot('11-phone-dosage-top.png', want=viewport_box(),
         note='phone, dosage page top')

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

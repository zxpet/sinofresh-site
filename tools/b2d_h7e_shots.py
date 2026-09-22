#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H7e — the frames, and what makes them evidence.

The two browser passes assert states numerically, and a number can be right
about a page that renders nothing. So four frames are left behind, and this
checks that each one is a photograph of something rather than the right file
with the wrong content:

  * each is a real PNG whose width is what the capture asked for. Width is
    checked exactly and height mostly is not: three of the four are full-page
    frames, so their height is the content's height and will move the day an
    admin notice appears — a check that broke on that would be a check about
    wp-admin's chrome, not about this batch. The one viewport frame is held to
    both, because a viewport frame has no such excuse.
  * each decompresses to more than a handful of distinct byte values. A
    `screenshot <selector>` on this site returns a correctly sized BLANK block
    once the element is below the fold (batch H5's measurement, re-measured in
    H6), and "the size is right" is therefore accepted as evidence of nothing.
  * two pairs of frames DIFFER — two different admin pages, and one admin page
    against a product page. A pass that had photographed the same screen four
    times would satisfy every size and every assertion above, and only a pair
    comparison can see it.

usage:
    b2d_h7e_shots.py [--dir docs/batchH7e-shots]
"""
import argparse
import hashlib
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# The captures run at deviceScaleFactor 2, so a 1440px viewport is 2880px wide.
VIEWPORT_2X = 2880

# name -> (width, height or None to leave it free, what the frame is for)
EXPECT = [
    ('h7e-01-factory-info.png', VIEWPORT_2X, None,
     'the whole Factory Information page: heading, both fields, menu, Save'),
    ('h7e-02-factory-info-fields.png', 2564, None,
     'the field cluster close up — defaults legible, labels naming the spec rows'),
    ('h7e-03-container-library-contrast.png', VIEWPORT_2X, None,
     'the Container Library, which DOES carry the shared admin assets'),
    ('h7e-04-product-spec-sheet.png', VIEWPORT_2X, 1800,
     'the product page, scrolled to the spec sheet, as a viewport frame'),
]
# Pairs that must not be identical: (a, b, the difference they have to show)
MUST_DIFFER = [
    ('h7e-01-factory-info.png', 'h7e-03-container-library-contrast.png',
     'two different admin pages'),
    ('h7e-01-factory-info.png', 'h7e-04-product-spec-sheet.png',
     'an admin page against a product page'),
]

FLOOR = 400          # truncated / empty file only; not a quality proxy
MIN_HEIGHT = 300     # a frame shorter than this photographed nothing
MIN_DISTINCT = 8     # scanlines of a real render vary; a blank one is constant


def png_probe(path):
    """(width, height, distinct byte values in the decompressed IDAT, sha256)."""
    with open(path, 'rb') as fh:
        data = fh.read()
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('not a PNG')
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
        raise ValueError('no IHDR')
    return w, h, len(set(zlib.decompress(bytes(idat)))), hashlib.sha256(data).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', default=os.path.join(ROOT, 'docs', 'batchH7e-shots'))
    args = ap.parse_args()

    fails, taken, digests = [], [], {}
    for name, want_w, want_h, note in EXPECT:
        path = os.path.join(args.dir, name)
        if not os.path.exists(path):
            fails.append('%s was never written' % name)
            print('   %-38s  MISSING   %s' % (name, note))
            continue
        size = os.path.getsize(path)
        try:
            w, h, distinct, sha = png_probe(path)
        except Exception as exc:
            fails.append('%s unreadable: %s' % (name, exc))
            print('   %-38s  BAD PNG   %s' % (name, note))
            continue
        digests[name] = sha
        taken.append((name, size, w, h, distinct))
        bad = []
        if w != want_w:
            bad.append('is %dpx wide, expected %d' % (w, want_w))
        if want_h is not None and h != want_h:
            bad.append('is %dpx tall, expected %d' % (h, want_h))
        if h < MIN_HEIGHT:
            bad.append('only %dpx tall' % h)
        if distinct < MIN_DISTINCT:
            bad.append('only %d distinct byte values — a flat capture' % distinct)
        if size < FLOOR:
            bad.append('%d bytes — truncated' % size)
        if bad:
            fails.append('%s %s' % (name, '; '.join(bad)))
            print('   %-38s %8d B  %4dx%-5d  FAIL  %s'
                  % (name, size, w, h, '; '.join(bad)))
        else:
            print('   %-38s %8d B  %4dx%-5d  %3d values  %s'
                  % (name, size, w, h, distinct, note))

    print()
    for a, b, note in MUST_DIFFER:
        if a not in digests or b not in digests:
            fails.append('%s vs %s could not be compared (one is missing)' % (a, b))
            print('   %-38s  cannot compare  %s' % ('%s vs %s' % (a, b), note))
            continue
        same = digests[a] == digests[b]
        if same:
            fails.append('%s and %s are byte-identical: %s' % (a, b, note))
        print('   %-38s  %s  %s' % ('%s vs %s' % (a, b),
                                    'IDENTICAL' if same else 'differ  ', note))

    if fails:
        print()
        for f in fails:
            print('   FAIL %s' % f)
        print('VERDICT: FAIL — %d problem(s) across %d frame(s)'
              % (len(fails), len(taken) + len(fails)))
        return 1
    print('VERDICT: PASS — %d frames, each a real render at the width it claims '
          '(min %d B, max %d B), and both pairs differ'
          % (len(taken), min(t[1] for t in taken), max(t[1] for t in taken)))
    return 0


if __name__ == '__main__':
    sys.exit(main())

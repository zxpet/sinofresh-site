#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H7d — the frames, and what makes them evidence.

The browser pass asserts the states numerically. A number can be right about a
page that renders nothing: "the summary element's `hidden` is false" is true of a
summary that is off-screen, under an overlay, or one pixel tall. So the pass
leaves seven frames behind, and this checks that they are photographs of
something:

  * each frame is a real PNG, at the viewport width and height it claims — a
    screenshot of a 401 page, or of about:blank, is the right file with the wrong
    content, and its size is what catches that;
  * each frame is a RENDER and not a flat block — the decompressed IDAT carries
    more than a handful of distinct byte values. `screenshot <selector>` on this
    site returns a correctly sized blank block once the element is below the
    fold (measured in batch H5 and re-measured in H6), which is why every frame
    here is a viewport frame and why "the size is right" is not accepted as
    evidence of anything;
  * two pairs of frames DIFFER. `01` and `02` are the same band before and after
    a choice; `04` and `05` are the same phone before and after the drawer opens.
    If the E2E's assertions were measuring a page that never changed, the pair
    would come back byte-identical, and no single frame could show it.

usage:
    b2d_h7d_shots.py [--dir docs/batchH7d-shots]
"""
import argparse
import hashlib
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

DESKTOP = (1440, 900)
PHONE = (420, 900)

# name -> (width, height, what the frame is for)
EXPECT = [
    ('h7d-01-desktop-band.png', DESKTOP,
     'the band as it loads: five groups, nothing ticked, summary hidden'),
    ('h7d-02-desktop-picked.png', DESKTOP,
     'the same band with four groups chosen and the summary printed'),
    ('h7d-03-desktop-dialog-choice.png', DESKTOP,
     'the dialog over the band, its panel showing the choice, submit NOT pressed'),
    ('h7d-04-phone-closed.png', PHONE,
     '420px: the list collapsed behind one button'),
    ('h7d-05-phone-drawer-open.png', PHONE,
     'the drawer open, over the page — and over its other fixed layers'),
    ('h7d-06-phone-drawer-zh.png', PHONE,
     'the same drawer on /zh/'),
    ('h7d-07-phone-layers.png', PHONE,
     'the layering measured on its own: who owns the pixels on the drawer'),
]
# Pairs that must not be identical: (a, b, the change they are supposed to show)
MUST_DIFFER = [
    ('h7d-01-desktop-band.png', 'h7d-02-desktop-picked.png',
     'choosing options changed the render'),
    ('h7d-04-phone-closed.png', 'h7d-05-phone-drawer-open.png',
     'opening the drawer changed the render'),
]

FLOOR = 400          # truncated / empty file only; not a quality proxy
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
    ap.add_argument('--dir', default=os.path.join(ROOT, 'docs', 'batchH7d-shots'))
    args = ap.parse_args()

    fails, taken, digests = [], [], {}
    for name, want, note in EXPECT:
        path = os.path.join(args.dir, name)
        if not os.path.exists(path):
            fails.append('%s was never written' % name)
            print('   %-32s  MISSING   %s' % (name, note))
            continue
        size = os.path.getsize(path)
        try:
            w, h, distinct, sha = png_probe(path)
        except Exception as exc:
            fails.append('%s unreadable: %s' % (name, exc))
            print('   %-32s  BAD PNG   %s' % (name, note))
            continue
        digests[name] = sha
        taken.append((name, size, w, h, distinct))
        bad = []
        if abs(w - want[0]) > 1 or abs(h - want[1]) > 1:
            bad.append('is %dx%d, expected %dx%d' % (w, h, want[0], want[1]))
        if distinct < MIN_DISTINCT:
            bad.append('only %d distinct byte values — a flat capture' % distinct)
        if size < FLOOR:
            bad.append('%d bytes — truncated' % size)
        if bad:
            fails.append('%s %s' % (name, '; '.join(bad)))
            print('   %-32s %8d B  %4dx%-5d  FAIL  %s'
                  % (name, size, w, h, '; '.join(bad)))
        else:
            print('   %-32s %8d B  %4dx%-5d  %2d values  %s'
                  % (name, size, w, h, distinct, note))

    print()
    for a, b, note in MUST_DIFFER:
        if a not in digests or b not in digests:
            fails.append('%s vs %s could not be compared (one is missing)' % (a, b))
            print('   %-32s  cannot compare  %s' % ('%s vs %s' % (a, b), note))
            continue
        same = digests[a] == digests[b]
        if same:
            fails.append('%s and %s are byte-identical: %s' % (a, b, note))
        print('   %-32s  %s  %s' % ('%s vs %s' % (a, b),
                                    'IDENTICAL' if same else 'differ  ',
                                    note))

    if fails:
        print()
        for f in fails:
            print('   FAIL %s' % f)
        print('VERDICT: FAIL — %d of %d frames rejected, %d pairs compared'
              % (len(fails), len(taken) + len(fails), len(MUST_DIFFER)))
        return 1
    print('VERDICT: PASS — %d frames, each a real render the size it claims '
          '(min %d B, max %d B), and both state pairs differ'
          % (len(taken), min(t[1] for t in taken), max(t[1] for t in taken)))
    return 0


if __name__ == '__main__':
    sys.exit(main())

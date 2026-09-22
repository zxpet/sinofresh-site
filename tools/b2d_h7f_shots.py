#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H7f — the frames, and what makes them evidence.

The browser pass asserts the states numerically, and for a deletion batch a
number can be right about a page that renders nothing: "no element carrying a
basket class" is true of a page whose header collapsed, whose CTA fell off the
viewport, or which is a 401 page. So the pass leaves six frames behind and this
checks that they are photographs of something:

  * each frame is a real PNG at the viewport width and height it claims. A
    screenshot of a 401 page, or of about:blank, is the right file with the wrong
    content, and its size is what catches that -- the whole run is behind Basic
    auth, and the one failure mode that produces a uniform green here is
    measuring the 401 page.
  * each frame is a RENDER and not a flat block: the decompressed IDAT has to
    carry more than a handful of distinct byte values. `screenshot <selector>`
    on this site returns a correctly sized BLANK block once the element is below
    the fold (measured in H5, re-measured in H6), which is why every frame here
    is a viewport frame and why "the size is right" is not accepted as evidence
    of anything.
  * one pair DIFFERS, and differs for the declared reason. `05` and `06` are the
    same page at the same scroll offset -- the E2E asserts the offset is
    unchanged across the pair, which is why the opener used is the fixed float
    button and not one in the flow -- with the inquiry dialog closed and then
    open. If the run had been measuring a frozen render, this pair would come
    back byte-identical and no single frame could show it.
  * and `01`/`03` differ, which is the cheap sanity check that the capture is
    not stuck on one frame for the whole pass: two scroll positions on the same
    page, same viewport, must not be the same picture.

usage:
    b2d_h7f_shots.py [--dir docs/batchH7f-shots]
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
    ('h7f-01-header-desktop.png', DESKTOP,
     'the header at 1440: the CTA where the bag button sat, now holding only Get a Quote'),
    ('h7f-02-header-phone.png', PHONE,
     'the same header at 420, where the CTA button is hidden by the phone rule'),
    ('h7f-03-footer-desktop.png', DESKTOP,
     'the footer: the cookie banner and the float stack that shared the drawer\'s block'),
    ('h7f-04-certmodal-open.png', DESKTOP,
     '/quality/ with the certificate dialog open, over the layers it used to share with the basket'),
    ('h7f-05-detail-bottom-closed.png', DESKTOP,
     'the detail page at the bottom of the scroll, nothing open'),
    ('h7f-06-detail-bottom-inquiry-open.png', DESKTOP,
     'the same offset with the inquiry dialog open — and the page did not move'),
]
# Pairs that must not be identical: (a, b, the change they are supposed to show)
MUST_DIFFER = [
    ('h7f-05-detail-bottom-closed.png', 'h7f-06-detail-bottom-inquiry-open.png',
     'opening the dialog changed the render, at an unchanged scroll offset'),
    ('h7f-01-header-desktop.png', 'h7f-03-footer-desktop.png',
     'the capture is not stuck on one frame (same page, same viewport, two offsets)'),
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


def verify(expect, must_differ, shots_dir, floor=FLOOR, min_distinct=MIN_DISTINCT):
    """Check a frame set. Split out so a batch with two frames reuses this
    rather than growing a second copy of the probe -- H7a's Video path does, and
    two copies of a checker drift until one of them stops checking."""
    fails, taken, digests = [], [], {}
    for name, want, note in expect:
        path = os.path.join(shots_dir, name)
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
        if abs(w - want[0]) > 1 or abs(h - want[1]) > 1:
            bad.append('is %dx%d, expected %dx%d' % (w, h, want[0], want[1]))
        if distinct < min_distinct:
            bad.append('only %d distinct byte values — a flat capture' % distinct)
        if size < floor:
            bad.append('%d bytes — truncated' % size)
        if bad:
            fails.append('%s %s' % (name, '; '.join(bad)))
            print('   %-38s %8d B  %4dx%-5d  FAIL  %s'
                  % (name, size, w, h, '; '.join(bad)))
        else:
            print('   %-38s %8d B  %4dx%-5d  %2d values  %s'
                  % (name, size, w, h, distinct, note))

    print()
    for a, b, note in must_differ:
        if a not in digests or b not in digests:
            fails.append('%s vs %s could not be compared (one is missing)' % (a, b))
            print('   %-38s  cannot compare  %s' % ('%s vs %s' % (a, b), note))
            continue
        same = digests[a] == digests[b]
        if same:
            fails.append('%s and %s are byte-identical: %s' % (a, b, note))
        print('   %-38s  %s  %s' % ('%s vs %s' % (a[:8], b[:8]),
                                    'IDENTICAL' if same else 'differ  ', note))
    return fails, taken


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', default=os.path.join(ROOT, 'docs', 'batchH7f-shots'))
    args = ap.parse_args()

    fails, taken = verify(EXPECT, MUST_DIFFER, args.dir)

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

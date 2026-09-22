#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H7a — the frames for the Video path, checked.

Two frames, and they are the whole point of the fixture: without them the
verification of the [Video] branch is a set of attributes read out of a live DOM,
and an attribute read can be right about a band that renders as nothing. The
checker is H7f's, reused rather than copied — its own docstring lists what it
asserts (a real PNG at the size it claims, more than eight distinct byte values
in the decompressed IDAT, and a pair that must not be identical).

The pair here carries the claim: `01` is the band on [Photos] and `02` is the
same band with [Video] chosen. If the click had not changed the render the two
files would be byte-identical, and no single frame could show it.

usage:
    b2d_h7a_shots.py [--dir docs/batchH7a-shots]
"""
import argparse
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

_spec = importlib.util.spec_from_file_location(
    'h7f_shots', os.path.join(HERE, 'b2d_h7f_shots.py'))
h7f = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(h7f)

DESKTOP = (1440, 900)

EXPECT = [
    ('h7a-01-gallery-photos.png', DESKTOP,
     'the media band as it ships: two tabs, [Photos] active, the product photo showing'),
    ('h7a-02-gallery-video.png', DESKTOP,
     'the same band after [Video]: the video frame revealed, the photo frames off'),
]
MUST_DIFFER = [
    ('h7a-01-gallery-photos.png', 'h7a-02-gallery-video.png',
     'choosing [Video] changed the render, at an unchanged scroll offset'),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', default=os.path.join(ROOT, 'docs', 'batchH7a-shots'))
    args = ap.parse_args()

    fails, taken = h7f.verify(EXPECT, MUST_DIFFER, args.dir)

    if fails:
        print()
        for f in fails:
            print('   FAIL %s' % f)
        print('VERDICT: FAIL — %d of %d frames rejected, %d pair compared'
              % (len(fails), len(taken) + len(fails), len(MUST_DIFFER)))
        return 1
    print('VERDICT: PASS — %d frames, each a real render the size it claims, '
          'and the state pair differs' % len(taken))
    return 0


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Non-flat-frame assertion for PNG screenshots.

"A screenshot exists and has the right dimensions" is never evidence that it
shows anything: a solid colour of the right size passes both, and so does a 401
page or an empty modal. This decompresses the IDAT stream and counts DISTINCT
byte values. A frame with fewer than nine distinct byte values is a flat fill
and is reported FLAT rather than counted as a delivered frame.

    _png_nonflat.py docs/batchH7b-shots            # a directory of *.png
    _png_nonflat.py a.png b.png                    # or individual files
    _png_nonflat.py docs/batchH7b-shots --floor 12

Zero frames is a FAIL, not a pass. The first version of this tool globbed
`argv[1]/*.png`; handed a file it matched nothing, printed `PASS 0 frame(s)`
and exited 0 -- a silent all-green, which is the exact failure mode the tool
exists to prevent. Now a path that yields no frame is an error.
"""
import argparse
import glob
import os
import struct
import sys
import zlib

FLOOR = 9


def distinct(path):
    with open(path, 'rb') as fh:
        data = fh.read()
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        return None, None, None
    pos, idat, w, h = 8, bytearray(), None, None
    while pos < len(data):
        ln = struct.unpack('>I', data[pos:pos + 4])[0]
        typ = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + ln]
        if typ == b'IHDR':
            w, h = struct.unpack('>II', body[:8])
        elif typ == b'IDAT':
            idat += body
        pos += 12 + ln
    return w, h, len(set(zlib.decompress(bytes(idat))))


def collect(paths):
    names, missing = [], []
    for p in paths:
        if os.path.isdir(p):
            names += sorted(glob.glob(os.path.join(p, '*.png')))
        elif os.path.isfile(p):
            names.append(p)
        else:
            missing.append(p)
    return names, missing


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('paths', nargs='+', help='PNG files and/or directories')
    ap.add_argument('--floor', type=int, default=FLOOR,
                    help='distinct-byte floor; at or below is FLAT (default %d)' % FLOOR)
    args = ap.parse_args()

    names, missing = collect(args.paths)
    for p in missing:
        print('  MISS  %s  (no such file or directory)' % p)
    if not names:
        print('FAIL  0 frame(s) found in: %s' % ', '.join(args.paths))
        return 2

    bad = len(missing)
    for p in names:
        w, h, n = distinct(p)
        ok = n is not None and n > args.floor
        if not ok:
            bad += 1
        print('  %s  %-38s %sx%s  distinct bytes=%-4s'
              % ('ok  ' if ok else 'FLAT', os.path.basename(p), w, h, n))
    print('%s  %d frame(s), %d flat, %d missing'
          % ('PASS' if not bad else 'FAIL', len(names), bad - len(missing), len(missing)))
    return 0 if not bad else 1


if __name__ == '__main__':
    sys.exit(main())

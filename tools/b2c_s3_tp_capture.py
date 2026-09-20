#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Capture the /zh/ pages around the TranslatePress re-collection step.

Why not reuse `sf_masked_cmp.py --fetch`: that helper writes one file per PATH,
so a cache-busting query string would end up in the filename and the two
snapshots (before / after) would no longer line up by name.

Cloudflare stamps `cache-control: max-age=86400` on HTML. A plain re-fetch of
the same URL therefore never reaches the origin the second time, and the "after"
snapshot would silently be the "before" bytes. Every request here carries
`?sfcap=<tag>`; the tag goes in the QUERY only, never in the filename, and
`sf_masked_cmp.py` masks `sfcap=...` on both sides before hashing.

  python3 tools/b2c_s3_tp_capture.py /tmp/sfs3/pre --tag pre1726... [--header K:V]
"""
import argparse
import os
import subprocess
import sys

DEFAULT_PATHS = [
    '/zh/',
    '/zh/blog/',
    '/zh/products/',
    '/zh/products/soft-chews/',
    '/zh/products/tablets/',
    '/zh/products/powders/',
    '/zh/products/pastes/',
    '/zh/products/drops/',
    '/zh/products/liquids/',
    '/zh/products/fish-oil/',
    '/zh/products/dental-chews/',
    '/zh/formulas/',
    '/zh/formulas/ear-care-drops/',
    '/zh/formulas/liquid-joint-support/',
    '/zh/contact/',
    '/zh/about/',
    '/zh/quality/',
    '/formulas/',
    '/blog/',
]


def slug_of(path):
    return path.strip('/').replace('/', '-').replace('?', '_').replace('=', '-') or 'home'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('dir')
    ap.add_argument('--tag', required=True, help='cache-buster value (query only)')
    ap.add_argument('--base', default='https://dev.zxpet.com')
    ap.add_argument('--header', default=None)
    ap.add_argument('--paths', nargs='*', default=None)
    args = ap.parse_args()

    os.makedirs(args.dir, exist_ok=True)
    paths = args.paths or DEFAULT_PATHS
    for p in paths:
        sep = '&' if '?' in p else '?'
        url = args.base.rstrip('/') + '/' + p.lstrip('/') + sep + 'sfcap=' + args.tag
        cmd = ['curl', '-s', '-L', '--max-time', '45', url]
        if args.header:
            cmd[1:1] = ['-H', args.header]
        body = subprocess.run(cmd, capture_output=True, text=True).stdout
        out = os.path.join(args.dir, slug_of(p) + '.html')
        open(out, 'w', encoding='utf-8').write(body)
        print(f"  {p:<34} -> {out}  {len(body.encode())} B")
    print(f"captured {len(paths)} pages into {args.dir}")
    return 0


if __name__ == '__main__':
    sys.exit(main())

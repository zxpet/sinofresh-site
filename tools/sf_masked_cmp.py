#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Masked page-by-page regression comparator (the batch standard gate).

Two renders of the same URL are never byte-identical: Cloudflare rewrites every
mailto into /cdn-cgi/l/email-protection#<hex> with a fresh token per response,
and Gravity Forms stamps per-request hidden values. A raw md5 comparison
therefore reports a difference on every page that contains a contact link —
a guaranteed false positive that hides the real regressions.

This comparator masks that noise first, with ONE mask set applied to both
sides. The mask set is the one Batch2C Step0 established
(tools/b2s0_missing_img_e2e.py), so hashes stay comparable with those
baselines.

  # regression: two directories, files matched by name (<slug>.html)
  python3 tools/sf_masked_cmp.py /tmp/pre/new /tmp/pre/live [--json out.json]

  # mandatory A/A self-test first: one URL, fetched twice, must be SAME
  python3 tools/sf_masked_cmp.py --aa https://dev.zxpet.com/blog/

  # fetch a list of paths into one side (one <slug>.html per path)
  python3 tools/sf_masked_cmp.py --fetch /tmp/pre/live --base https://dev.zxpet.com \\
      --header 'X-SF-Preflight: 1' /blog/ /products/soft-chews/

Exit code 0 = every pair matched, 1 = at least one difference (so it can be
used directly as a gate in a shell pipeline).
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys

# The Step0 mask set. Order matters: the specific patterns run before the
# catch-all base64 run.
MASKS = [
    (re.compile(r'email-protection#[0-9a-f]+'), 'email-protection#MASK', 'cf_email_link'),
    (re.compile(r'data-cfemail="[0-9a-f]+"'), 'data-cfemail="MASK"', 'cf_email_attr'),
    (re.compile(r"'[A-Za-z0-9+/=]{16,}'"), "'MASK'", 'quoted_blob'),
    (re.compile(r'[A-Za-z0-9+/]{40,}={0,2}'), 'MASK', 'long_b64_run'),
]


def masked(text):
    counts = {}
    for pat, repl, name in MASKS:
        counts[name] = len(pat.findall(text))
        text = pat.sub(repl, text)
    return text, counts


def digest(path):
    raw = open(path, encoding='utf-8', errors='replace').read()
    m, counts = masked(raw)
    return {
        'raw_bytes': len(raw.encode()),
        'masked_bytes': len(m.encode()),
        'masks': {k: v for k, v in counts.items() if v},
        'sha256': hashlib.sha256(m.encode()).hexdigest()[:16],
        'masked_text': m,
    }


def curl(url, header=None):
    cmd = ['curl', '-s', '-L', url]
    if header:
        cmd[1:1] = ['-H', header]
    return subprocess.run(cmd, capture_output=True, text=True).stdout


def slug_of(path):
    s = path.strip('/').replace('/', '-').replace('?', '_').replace('=', '-')
    return s or 'home'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--aa', metavar='URL', help='A/A self-test: fetch URL twice, must match')
    ap.add_argument('--fetch', metavar='DIR', help='fetch the given paths into DIR')
    ap.add_argument('--base', default='https://dev.zxpet.com', help='base URL for --fetch')
    ap.add_argument('--header', default=None, help='extra request header (e.g. preflight gate)')
    ap.add_argument('--json', default=None, help='write the result JSON here')
    ap.add_argument('dirs', nargs='*', help='dirA dirB for a directory comparison')
    args = ap.parse_args()

    if args.aa:
        a, b = curl(args.aa, args.header), curl(args.aa, args.header)
        ma, _ = masked(a)
        mb, _ = masked(b)
        ok = ma == mb
        print(f"{'PASS' if ok else 'FAIL'}  A/A masked self-test  {args.aa}  "
              f"({len(a)} / {len(b)} bytes)")
        if not ok:
            for i in range(min(len(ma), len(mb))):
                if ma[i] != mb[i]:
                    print("  first masked diff at", i)
                    print("   A:", repr(ma[max(0, i - 60):i + 40]))
                    print("   B:", repr(mb[max(0, i - 60):i + 40]))
                    break
        return 0 if ok else 1

    if args.fetch:
        if len(args.dirs) < 1:
            ap.error('--fetch needs at least one path')
        os.makedirs(args.fetch, exist_ok=True)
        for p in args.dirs:
            url = args.base.rstrip('/') + '/' + p.lstrip('/')
            body = curl(url, args.header)
            out = os.path.join(args.fetch, slug_of(p) + '.html')
            open(out, 'w', encoding='utf-8').write(body)
            print(f"  fetched {url} -> {out} ({len(body.encode())} bytes)")
        return 0

    if len(args.dirs) != 2:
        ap.error('need dirA dirB (or --aa / --fetch)')
    A, B = args.dirs
    names = sorted({f[:-5] for f in os.listdir(A) if f.endswith('.html')} |
                   {f[:-5] for f in os.listdir(B) if f.endswith('.html')})
    rows, bad = [], 0
    for n in names:
        pa, pb = os.path.join(A, n + '.html'), os.path.join(B, n + '.html')
        if not (os.path.exists(pa) and os.path.exists(pb)):
            rows.append({'page': n, 'status': 'MISSING'})
            bad += 1
            continue
        da, db = digest(pa), digest(pb)
        same = da['sha256'] == db['sha256']
        row = {
            'page': n,
            'status': 'SAME' if same else 'DIFF',
            'sha_new': da['sha256'], 'sha_live': db['sha256'],
            'bytes_new': da['raw_bytes'], 'bytes_live': db['raw_bytes'],
            'masks_new': da['masks'],
        }
        if not same:
            bad += 1
            ma, mb = da['masked_text'], db['masked_text']
            for i in range(min(len(ma), len(mb))):
                if ma[i] != mb[i]:
                    row['first_diff_at'] = i
                    row['ctx_new'] = ma[max(0, i - 80):i + 60]
                    row['ctx_live'] = mb[max(0, i - 80):i + 60]
                    break
        rows.append(row)

    width = max((len(r['page']) for r in rows), default=10)
    for r in rows:
        line = f"  {r['page']:<{width}}  {r['status']}"
        if r['status'] == 'SAME':
            line += f"  {r['sha_new']}  {r['bytes_new']}B  masks={r['masks_new']}"
        elif r['status'] == 'DIFF':
            line += (f"  {r['sha_new']} vs {r['sha_live']}"
                     f"  {r['bytes_new']}B vs {r['bytes_live']}B"
                     f"  first diff @{r.get('first_diff_at')}")
        print(line)
        if r['status'] == 'DIFF':
            print("      new :", repr(r.get('ctx_new')))
            print("      live:", repr(r.get('ctx_live')))
    print(f"\n{'PASS' if bad == 0 else 'FAIL'}  masked regression: "
          f"{len(rows) - bad}/{len(rows)} identical")

    if args.json:
        json.dump({'rows': rows, 'diff': bad}, open(args.json, 'w'), indent=1)
        print(f"  json -> {args.json}")
    return 0 if bad == 0 else 1


if __name__ == '__main__':
    sys.exit(main())

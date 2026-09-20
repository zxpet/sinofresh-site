#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch2C Step4 gate: read the *visible* breadcrumb + the BreadcrumbList
JSON-LD out of a rendered page, so a fix to the archive-title prefix stripper
can be checked on both surfaces at once.

The page has two independent carriers of the same string:
  * `{{ARCHIVE_TITLE}}` in the block template  -> <span class="sf-breadcrumb__current">
  * the wp_head callback that reads the template off disk -> BreadcrumbList JSON-LD
Both must converge; checking only the visible one is how a JSON-LD regression
slips through.

  python3 tools/b2c_s4_breadcrumb_check.py --base https://dev.zxpet.com \\
      --header 'X-SF-Preflight: 1' /zh/formulas/ /formulas/

Every request carries a unique `?sfcap=` query so Cloudflare (cache-control
max-age=86400, keyed by URL) is forced back to the origin — otherwise the
"after" read is whatever the edge cached before the change.
"""
import argparse
import json
import os
import re
import subprocess
import tempfile
import time

UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'


def fetch(url, header=None):
    """curl writes the body to a file and the headers to another: `-D -`
    (headers on stdout) returns nothing under this shell, so header capture
    goes through a temp file instead."""
    with tempfile.TemporaryDirectory() as d:
        hpath, bpath = os.path.join(d, 'h.txt'), os.path.join(d, 'b.html')
        cmd = ['curl', '-s', '-L', '-A', UA, '-D', hpath, '-o', bpath, url]
        if header:
            cmd[1:1] = ['-H', header]
        subprocess.run(cmd, capture_output=True, text=True)
        head = open(hpath, encoding='utf-8', errors='replace').read()
        body = open(bpath, encoding='utf-8', errors='replace').read()
    status = re.findall(r'HTTP/\S+ (\d{3})', head)
    cache = re.search(r'cf-cache-status:\s*(\S+)', head, re.I)
    return {
        'status': status[-1] if status else '???',
        'cache': cache.group(1) if cache else '-',
        'len': len(body.encode()),
        'body': body,
    }


def visible_breadcrumb(html):
    m = re.search(r'<nav[^>]*class="[^"]*sf-breadcrumb[^"]*"[^>]*>(.*?)</nav>', html, re.S)
    if not m:
        return None
    txt = re.sub(r'<[^>]+>', '', m.group(1))
    return re.sub(r'\s+', ' ', txt).strip()


def current_crumb(html):
    m = re.search(r'class="[^"]*sf-breadcrumb__current[^"]*"[^>]*>(.*?)</span>', html, re.S)
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', m.group(1))).strip() if m else None


def h1(html):
    m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S)
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', m.group(1))).strip() if m else None


def breadcrumb_ld(html):
    for m in re.finditer(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.S):
        try:
            data = json.loads(m.group(1))
        except Exception:
            continue
        for node in (data if isinstance(data, list) else [data]):
            if not isinstance(node, dict):
                continue
            if node.get('@type') == 'BreadcrumbList':
                return [it.get('name') for it in node.get('itemListElement', [])]
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', default='https://dev.zxpet.com')
    ap.add_argument('--header', default=None)
    ap.add_argument('--tag', default='', help='label for this column set')
    ap.add_argument('paths', nargs='+')
    args = ap.parse_args()

    print(f"# tag={args.tag or '-'}  header={args.header or '(none)'}")
    print(f"{'path':<28} {'st':<4} {'cache':<9} {'bytes':>7}  {'current crumb':<24} "
          f"{'h1':<14} BreadcrumbList names")
    print('-' * 158)
    for p in args.paths:
        sep = '&' if '?' in p else '?'
        url = args.base.rstrip('/') + '/' + p.lstrip('/') + sep + 'sfcap=s' + str(int(time.time() * 1000))
        r = fetch(url, args.header)
        cur, title, names = current_crumb(r['body']), h1(r['body']), breadcrumb_ld(r['body'])
        print(f"{p:<28} {r['status']:<4} {r['cache']:<9} {r['len']:>7}  {str(cur):<24} "
              f"{str(title):<14} {names}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

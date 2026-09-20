#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""19 页 HTML 抓取器（可复用回归仪器）。

用途：为「删除操作前后零变化」提供逐字节基线。
刻意不用 JS/浏览器：直接 HTTP GET 原始 HTML，结果必须可复现；
若两次抓取（同代码、无改动）字节不一致，则仪器本身不可信，必须先修正。

用法:
  python3 tools/t19_fetch.py <out_dir> [--expect <baseline_json>]

  <out_dir>          输出目录（自动创建）
  --expect <json>    可选：与既有掩码基线 json 比对（用于先行验证仪器有效性）
"""
import os, sys, json, gzip, io, urllib.request, urllib.error

BASE = 'http://sinofresh.local'
# 19 页（与 /tmp/t22、/tmp/t23、/tmp/t24 的 pages/ 目录一致）
SLUGS = ['home', 'about', 'products', 'soft-chews', 'tablets', 'powders', 'pastes',
         'drops', 'liquids', 'fish-oil', 'dental-chews', 'quality', 'faq', 'services',
         'cooperation', 'contact', 'blog', 'factory-tour', 'feedback']
PATH = {
    'home': '/', 'about': '/about/', 'products': '/products/',
    'soft-chews': '/products/soft-chews/', 'tablets': '/products/tablets/',
    'powders': '/products/powders/', 'pastes': '/products/pastes/',
    'drops': '/products/drops/', 'liquids': '/products/liquids/',
    'fish-oil': '/products/fish-oil/', 'dental-chews': '/products/dental-chews/',
    'quality': '/quality/', 'faq': '/faq/', 'services': '/services/',
    'cooperation': '/cooperation/', 'contact': '/contact/', 'blog': '/blog/',
    'factory-tour': '/factory-tour/', 'feedback': '/feedback/',
}

def fetch(url):
    req = urllib.request.Request(url, headers={
        'Accept-Encoding': 'identity',
        'User-Agent': 'sf-regression-probe/1.0',
        'Cache-Control': 'no-cache',
    })
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read()
        if r.headers.get('Content-Encoding') == 'gzip':
            raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
        return r.status, raw

def main():
    out_dir = sys.argv[1]
    expect = None
    if '--expect' in sys.argv:
        expect = json.load(open(sys.argv[sys.argv.index('--expect') + 1]))
    os.makedirs(out_dir, exist_ok=True)
    codes = {}
    for s in SLUGS:
        url = BASE + PATH[s]
        try:
            st, raw = fetch(url)
        except urllib.error.HTTPError as e:
            codes[s] = e.code
            print(f'  ❌ {s:<14} HTTP {e.code}')
            continue
        except Exception as e:
            codes[s] = 'ERR'
            print(f'  ❌ {s:<14} {e}')
            continue
        codes[s] = st
        with open(os.path.join(out_dir, s + '.html'), 'wb') as f:
            f.write(raw)
        print(f'  {"✅" if st == 200 else "⚠️"} {s:<14} HTTP {st}  {len(raw):>7,} B')
    n200 = sum(1 for v in codes.values() if v == 200)
    print(f'\n19 页抓取完成: 200 = {n200}/19, 非 200 = ' +
          (', '.join(f'{k}:{v}' for k, v in codes.items() if v != 200) or '0 ✅'))
    print('→ ' + out_dir)
    return 0 if n200 == 19 else 1

if __name__ == '__main__':
    sys.exit(main())

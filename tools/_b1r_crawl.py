#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch 1 —— 全站 19 页抓取（掩码回归 / 限定证明的输入）

固化此前的内联 curl 循环，供每一批次复用：
  · 固定 19 个 slug，逐页 curl → 落盘 <outdir>/<slug>.html
  · ⚠️ 8 个剂型页的**规范路径**是 /products/{slug}/；/{slug}/ 会 301 跳转，
    必须带 -L 跟随，否则拿到空 301 体（本工具已内置正确路径）
  · 记录 HTTP 码、字节数、PHP 报错特征（Fatal error / Warning / Notice / Deprecated）
  · 任何一页非 200 或含 PHP 报错特征 → 退出码 1（门禁）

⚠️ 每完成一次**改状态**的动作，必须重新抓取基线，否则基线会滞后 ——
   步骤 2 的限定证明就抓到过一次滞后（Lead time 措辞）。

用法：python3 tools/_b1r_crawl.py <outdir> [host]
"""
import os
import re
import subprocess
import sys

HOST = sys.argv[2] if len(sys.argv) > 2 else 'http://sinofresh.local'
OUT = sys.argv[1]
PAGES = [('home', '/'), ('products', '/products/'), ('about', '/about/'),
         ('quality', '/quality/'), ('factory-tour', '/factory-tour/'),
         ('cooperation', '/cooperation/'), ('contact', '/contact/'),
         ('blog', '/blog/'), ('faq', '/faq/'), ('services', '/services/'),
         ('feedback', '/feedback/'),
         ('soft-chews', '/products/soft-chews/'), ('tablets', '/products/tablets/'),
         ('powders', '/products/powders/'), ('pastes', '/products/pastes/'),
         ('drops', '/products/drops/'), ('liquids', '/products/liquids/'),
         ('fish-oil', '/products/fish-oil/'), ('dental-chews', '/products/dental-chews/')]
ERR = re.compile(r'(Fatal error|Parse error|Warning:|Notice:|Deprecated:|'
                 r'Uncaught\s+\w*Error)')

os.makedirs(OUT, exist_ok=True)
print('=' * 76)
print(f'抓取 {len(PAGES)} 页 ← {HOST}')
print('=' * 76)
print(f"{'slug':<16}{'HTTP':>5}{'字节':>10}{'PHP报错':>10}{'页内CSS版本':>14}")
bad, total, vers = [], 0, set()
for slug, path in PAGES:
    url = HOST + path
    r = subprocess.run(['curl', '-sL', '-w', '\n%{http_code}', url],
                       capture_output=True)
    raw = r.stdout.decode('utf-8', 'replace')
    body, _, code = raw.rpartition('\n')
    code = code.strip()
    path = os.path.join(OUT, slug + '.html')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(body)
    n = len(body.encode())
    total += n
    errs = sorted(set(ERR.findall(body)))
    ver = set(re.findall(r'sinofresh-theme/style\.css\?ver=([0-9.]+)', body))
    vers |= ver
    ok = code == '200' and not errs
    if not ok:
        bad.append((slug, code, errs))
    print(f"{slug:<16}{code:>5}{n:>10}{('—' if not errs else ','.join(errs)):>10}"
          f"{(','.join(sorted(ver)) or '—'):>14}{'' if ok else '   ❌'}")

print()
print(f'落盘 {len(PAGES)} 页 / {total:,} 字节 → {OUT}')
print(f'HTTP 200 且无 PHP 报错: {"✅ 是" if not bad else f"❌ 否 —— {bad}"}')
print(f'style.css 版本一致性: {sorted(vers) if vers else "未出现"}')
sys.exit(1 if bad else 0)

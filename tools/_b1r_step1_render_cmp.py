#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch 1 / 步骤 1 —— 全站掩码 sha256 回归

在 tools/t22_render_cmp.py 的掩码集上**补齐两个已知盲区**：
  (a) wp-statistics 的 `nonce=<10hex>`
  (b) Gravity Forms 表单页的 `config_nonce":"<10hex>"`
这两个是 12h tick 量；基线（CST 09:17）与本轮（CST 10:1x）同处 UTC 00:00–12:00
一个 tick 内，理论稳定，但仍掩码以求稳健（与基线用**同一套掩码**，故可比）。

用法：python3 tools/_b1r_step1_render_cmp.py <dirA> <dirB> [out_json]
"""
import hashlib
import json
import os
import re
import sys

MASKERS = [
    (re.compile(r"value='[A-Za-z0-9+/=$]{40,}'"), "value='__MASKED__'", 'gf_hidden_val'),
    (re.compile(r"gform_phone_dropdown_[0-9a-f]{8,}"), "gform_phone_dropdown___MASKED__", 'gf_phone_uid'),
    (re.compile(r'config_nonce"\s*:\s*"[0-9a-f]{8,}"'), 'config_nonce":"__MASKED__"', 'gf_config_nonce'),
    (re.compile(r'nonce=[0-9a-f]{8,}'), 'nonce=__MASKED__', 'wp_nonce'),
    (re.compile(r'"nonce"\s*:\s*"[0-9a-f]{8,}"'), '"nonce":"__MASKED__"', 'json_nonce'),
]


def masked(path):
    raw = open(path, encoding='utf-8', errors='replace').read()
    counts = {}
    m = raw
    for rx, rep, name in MASKERS:
        counts[name] = len(rx.findall(m))
        m = rx.sub(rep, m)
    return {
        'raw_bytes': len(raw.encode()),
        'masked_bytes': len(m.encode()),
        'masks': counts,
        'mask_total': sum(counts.values()),
        'sha256': hashlib.sha256(m.encode()).hexdigest(),
    }


def scan(d):
    out = {}
    for fn in sorted(os.listdir(d)):
        if fn.endswith('.html'):
            out[fn[:-5]] = masked(os.path.join(d, fn))
    return out


A, B = sys.argv[1], sys.argv[2]
OUT = sys.argv[3] if len(sys.argv) > 3 else '/tmp/b1/step1/render_cmp.json'
a, b = scan(A), scan(B)
names = sorted(set(a) | set(b))

same, diff = [], []
for n in names:
    if n not in a:
        diff.append((n, 'ONLY_IN_B', '-', '-'))
    elif n not in b:
        diff.append((n, 'ONLY_IN_A', '-', '-'))
    elif a[n]['sha256'] == b[n]['sha256']:
        same.append(n)
    else:
        diff.append((n, a[n]['sha256'][:16], b[n]['sha256'][:16],
                     f"{a[n]['masked_bytes']}->{b[n]['masked_bytes']}B"))
        # byte-level locate: first differing offset after masking
        ra = open(os.path.join(A, n + '.html'), encoding='utf-8', errors='replace').read()
        rb = open(os.path.join(B, n + '.html'), encoding='utf-8', errors='replace').read()
        for rx, rep, _ in MASKERS:
            ra = rx.sub(rep, ra)
            rb = rx.sub(rep, rb)
        i = 0
        while i < min(len(ra), len(rb)) and ra[i] == rb[i]:
            i += 1
        ctx_a = ra[max(0, i - 60):i + 90].replace('\n', ' ')
        ctx_b = rb[max(0, i - 60):i + 90].replace('\n', ' ')
        print(f'\n### {n}  首异偏移 {i:,}')
        print(f'    A: …{ctx_a}')
        print(f'    B: …{ctx_b}')

DOSAGE = ['soft-chews', 'tablets', 'powders', 'pastes', 'drops', 'liquids', 'fish-oil', 'dental-chews']
print('=' * 78)
print(f'A = {A}')
print(f'B = {B}')
print('=' * 78)
print(f'页面总数 {len(names)}  相同 {len(same)}  不同 {len(diff)}')
print('  相同:', ', '.join(same))
print()
print(f'{"page":<16}{"A sha256":<18}{"B sha256":<18}note')
for n in names:
    sa = a[n]['sha256'][:16] if n in a else '-'
    sbb = b[n]['sha256'][:16] if n in b else '-'
    mark = 'SAME' if (n in a and n in b and a[n]['sha256'] == b[n]['sha256']) else 'DIFF'
    print(f'{n:<16}{sa:<18}{sbb:<18}{mark}  {b[n]["masked_bytes"] if n in b else "-":>7}B  masks={b[n]["mask_total"] if n in b else "-"}')
print()
dset = sorted(n for n in names if n in a and n in b and a[n]['sha256'] != b[n]['sha256'])
print(f'变化集合 ({len(dset)}): {dset}')
print(f'变化集合 == 8 剂型页: {"是" if dset == sorted(DOSAGE) else "否"}')
nondose = [n for n in names if n not in DOSAGE]
nd_same = all(n in a and n in b and a[n]['sha256'] == b[n]['sha256'] for n in nondose)
print(f'非剂型页（{len(nondose)}）逐字节全同: {"是" if nd_same else "否"}')

json.dump({'A': A, 'B': B, 'same': same, 'diff': [d[0] for d in diff],
           'detail': {n: b[n] for n in names if n in b}},
          open(OUT, 'w'), ensure_ascii=False, indent=1, sort_keys=True)
print('→', OUT)

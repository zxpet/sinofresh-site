#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch 2A —— 原始字节差异的「限定证明」

掩码后 sha256 相等只说明差异被掩码覆盖，不能证明差异**只**发生在掩码区间。
本工具把这件事证死：对每页计算 A/B 的逐字节差异偏移，再对 B 求出所有掩码
命中区间，断言

        差异偏移集合  ⊆  掩码命中区间集合

并输出差异字节数、差异段数、覆盖判定，以及一段可人工复核的原文摘录。

用法：python3 tools/_cpt2a_ab_confine.py <dirA> <dirB>
"""
import os
import re
import sys

A, B = sys.argv[1], sys.argv[2]
PAGES = ['home', 'products', 'about', 'quality', 'factory-tour', 'cooperation',
         'contact', 'blog', 'faq', 'services', 'feedback',
         'soft-chews', 'tablets', 'powders', 'pastes', 'drops', 'liquids',
         'fish-oil', 'dental-chews']

MASKERS = [
    (re.compile(rb"value='[A-Za-z0-9+/=$]{40,}'"), 'gf_hidden_val'),
    (re.compile(rb"gform_phone_dropdown_[0-9a-f]{8,}"), 'gf_phone_uid'),
    (re.compile(rb'config_nonce"\s*:\s*"[0-9a-f]{8,}"'), 'gf_config_nonce'),
    (re.compile(rb'nonce=[0-9a-f]{8,}'), 'wp_nonce'),
    (re.compile(rb'"nonce"\s*:\s*"[0-9a-f]{8,}"'), 'json_nonce'),
    (re.compile(rb'sinofresh-theme/style\.css\?ver=[0-9.]+'), 'style_ver'),
]


def load(d, name):
    with open(os.path.join(d, name + '.html'), 'rb') as f:
        return f.read()


def spans(raw):
    """所有掩码命中区间（在 raw 坐标下），已合并重叠。"""
    out = []
    for rx, slot in MASKERS:
        for m in rx.finditer(raw):
            out.append((m.start(), m.end(), slot))
    out.sort()
    merged = []
    for s, e, slot in out:
        if merged and s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e), merged[-1][2] + '+' + slot)
        else:
            merged.append((s, e, slot))
    return merged


def diff_runs(a, b):
    """长度相同时，返回连续的差异段 [(start, end)]。"""
    runs, i, n = [], 0, min(len(a), len(b))
    while i < n:
        if a[i] != b[i]:
            j = i
            while j < n and a[j] != b[j]:
                j += 1
            runs.append((i, j))
            i = j
        else:
            i += 1
    if len(a) != len(b):
        runs.append((n, max(len(a), len(b))))
    return runs


print('=' * 104)
print('原始字节差异的限定证明：差异偏移集合 ⊆ 掩码命中区间集合')
print(f'A = {A}\nB = {B}')
print('=' * 104)
print(f"{'page':<15}{'差异字节':>9}{'差异段':>7}{'掩码段':>7}{'全部被掩码覆盖':>16}   差异段所在掩码类型")
all_ok, total_diff = True, 0
exhibit = None
for name in PAGES:
    ra, rb = load(A, name), load(B, name)
    sp = spans(rb)
    runs = diff_runs(ra, rb)
    ndiff = sum(e - s for s, e in runs)
    total_diff += ndiff
    if not runs:
        print(f"{name:<15}{0:>9}{0:>7}{len(sp):>7}{'—（完全一致）':>16}   —")
        continue
    kinds, covered = set(), True
    for s, e in runs:
        hit = [slot for (ms, me, slot) in sp if s >= ms and e <= me]
        if hit:
            kinds.add(hit[0])
        else:
            covered = False
    if not covered:
        all_ok = False
    print(f"{name:<15}{ndiff:>9}{len(runs):>7}{len(sp):>7}"
          f"{('✅ 是' if covered else '❌ 否'):>16}   {','.join(sorted(kinds)) or '—'}")
    if name == 'soft-chews':
        s, e = runs[0]
        lo, hi = max(0, s - 40), min(len(rb), e + 40)
        exhibit = (name, s, e, rb[lo:hi], ra[lo:hi])

print()
print(f'全站差异字节合计 = {total_diff:,}（19 页 / {sum(len(load(A,p)) for p in PAGES):,} 字节）')
print(f'「差异 ⊆ 掩码区间」在 19 页上成立: {"✅ 是" if all_ok else "❌ 否"}')
if exhibit:
    name, s, e, bctx, actx = exhibit
    print()
    print(f'--- 样本摘录 {name} 差异段 [{s},{e}) ---')
    print(f'  B: {bctx!r}')
    print(f'  A: {actx!r}')
sys.exit(0 if all_ok else 1)

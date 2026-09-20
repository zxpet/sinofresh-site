#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch 2A —— A/B 字节级封闭性证明

用途：证明「只新增 CPT 注册 + shortcode」对既有 19 页的渲染输出**零影响**。
做法：同一站点、同一非 nonce 时间窗内抓两次（A = 2A 代码，B = 2A 之前的备份），
逐页比对原始字节与掩码后字节。

⚠️ 二进制读入，不用文本模式 —— 文本模式会把 \r\n 折成 \n，每对假丢字节
   （批次 1 的 t22_render_cmp.py 就因此在 5 页上各假报 +23 B）。

用法：python3 tools/_cpt2a_ab_cmp.py <dirA> <dirB>
"""
import hashlib
import os
import re
import sys

A, B = sys.argv[1], sys.argv[2]
PAGES = ['home', 'products', 'about', 'quality', 'factory-tour', 'cooperation',
         'contact', 'blog', 'faq', 'services', 'feedback',
         'soft-chews', 'tablets', 'powders', 'pastes', 'drops', 'liquids',
         'fish-oil', 'dental-chews']

# 与 tools/_b1r_step2_render_cmp.py 保持一致；此处用 bytes 模式
MASKERS = [
    (re.compile(rb"value='[A-Za-z0-9+/=$]{40,}'"), b"value='__MASKED__'", 'gf_hidden_val'),
    (re.compile(rb"gform_phone_dropdown_[0-9a-f]{8,}"), b"gform_phone_dropdown___MASKED__", 'gf_phone_uid'),
    (re.compile(rb'config_nonce"\s*:\s*"[0-9a-f]{8,}"'), b'config_nonce":"__MASKED__"', 'gf_config_nonce'),
    (re.compile(rb'nonce=[0-9a-f]{8,}'), b'nonce=__MASKED__', 'wp_nonce'),
    (re.compile(rb'"nonce"\s*:\s*"[0-9a-f]{8,}"'), b'"nonce":"__MASKED__"', 'json_nonce'),
    (re.compile(rb'sinofresh-theme/style\.css\?ver=[0-9.]+'), b'sinofresh-theme/style.css?ver=__MASKED__', 'style_ver'),
]


def load(d, name):
    with open(os.path.join(d, name + '.html'), 'rb') as f:
        return f.read()


def mask(raw):
    counts, out = {}, raw
    for rx, rep, slot in MASKERS:
        out, n = rx.subn(rep, out)
        if n:
            counts[slot] = counts.get(slot, 0) + n
    return out, counts


def first_diff(a, b):
    n = min(len(a), len(b))
    for i in range(n):
        if a[i] != b[i]:
            return i
    return n if len(a) != len(b) else -1


print('=' * 100)
print(f'A = {A}')
print(f'B = {B}')
print('=' * 100)
print(f"{'page':<15}{'B受':>7}{'A受':>7}{'ΔB':>6}{'原sha256':>10}{'掩码sha256':>12}{'掩码命中(B)':>26}")
raw_bad, masked_bad, total_b, total_a = [], [], 0, 0
detail = {}
for name in PAGES:
    rb_raw, ra_raw = load(B, name), load(A, name)
    rb, cb = mask(rb_raw)
    ra, ca = mask(ra_raw)
    total_b += len(rb_raw)
    total_a += len(ra_raw)
    hb_raw = hashlib.sha256(rb_raw).hexdigest()[:8]
    ha_raw = hashlib.sha256(ra_raw).hexdigest()[:8]
    hb, ha = hashlib.sha256(rb).hexdigest()[:8], hashlib.sha256(ra).hexdigest()[:8]
    same_raw, same_mask = (hb_raw == ha_raw), (hb == ha)
    if not same_raw:
        raw_bad.append(name)
    if not same_mask:
        masked_bad.append(name)
    detail[name] = dict(bytes_b=len(rb_raw), bytes_a=len(ra_raw), mask=cb,
                        same_raw=same_raw, same_mask=same_mask)
    print(f"{name:<15}{len(rb_raw):>7}{len(ra_raw):>7}"
          f"{len(ra_raw) - len(rb_raw):>+6}"
          f"{'✅' if same_raw else '✗' + hb_raw + '/' + ha_raw:>10}"
          f"{'✅' if same_mask else '✗' + hb + '/' + ha:>12}"
          f"{(','.join(f'{k}×{v}' for k, v in sorted(cb.items())) or '—'):>26}")

print()
print(f'总字节 B={total_b:,}  A={total_a:,}  Δ={total_a - total_b:+,}')
print(f'原始字节完全一致: {"✅ 19/19" if not raw_bad else "❌ " + str(len(PAGES) - len(raw_bad)) + "/19  差异页=" + ','.join(raw_bad)}')
print(f'掩码后完全一致:   {"✅ 19/19" if not masked_bad else "❌ 差异页=" + ','.join(masked_bad)}')

if masked_bad:
    print()
    print('--- 掩码后仍有差异的页：首个差异偏移与上下文 ---')
    for name in masked_bad:
        rb_raw, ra_raw = load(B, name), load(A, name)
        rb, _ = mask(rb_raw)
        ra, _ = mask(ra_raw)
        i = first_diff(rb, ra)
        print(f'  {name}: offset {i}')
        lo = max(0, i - 70)
        print(f'    B: {rb[lo:i + 70]!r}')
        print(f'    A: {ra[lo:i + 70]!r}')

sys.exit(1 if masked_bad else 0)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch 1 / 步骤 2 —— 全站掩码 sha256 回归 + 差异限定证明

在步骤 1 比对器（tools/_b1r_step1_render_cmp.py）的掩码集上再补一项：
  (c) `sinofresh-theme/style.css?ver=<x.y.z>` —— 决策 ⑧ 的**有意**版本 bump
      （2.10.38 → 2.10.39）会出现在每一页的 <link> 里；不掩掉它，11 个非剂型页
      都会被判“有差异”，掩盖真正的“无意外改动”判据。

差异限定证明（比“变化集合 == 8 剂型页”更强）：
  对 8 个剂型页，把基线掩码文本里的 `<section class="…sf-hero-inner">…</section>`
  换成当前版本对应段落，若结果与当前掩码文本**逐字节相同**，即证明全页改动
  100% 局限于 Hero 段（其余 7 个区块的 HTML 一字未动）。

用法：python3 tools/_b1r_step2_render_cmp.py <dirA> <dirB> [out_json]
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
    # 步骤 2 新增：主题样式表版本号（决策 ⑧ 的有意 bump）
    (re.compile(r'sinofresh-theme/style\.css\?ver=[0-9]+\.[0-9]+\.[0-9]+'),
     'sinofresh-theme/style.css?ver=__MASKED__', 'style_ver'),
]

# 渲染后 WP 会给 section 追加布局类（is-layout-constrained …），故用包含匹配；
# hero 内部无嵌套 <section>，非贪婪匹配到其闭合标签即为准确边界。
HERO_RE = re.compile(r'<section class="[^"]*\bsf-hero-inner\b[^"]*"[^>]*>.*?</section>', re.S)
DOSAGE = ['soft-chews', 'tablets', 'powders', 'pastes', 'drops', 'liquids',
          'fish-oil', 'dental-chews']


def masked_text(path):
    raw = open(path, encoding='utf-8', errors='replace').read()
    counts = {}
    m = raw
    for rx, rep, name in MASKERS:
        counts[name] = len(rx.findall(m))
        m = rx.sub(rep, m)
    return raw, m, counts


def sha(t):
    return hashlib.sha256(t.encode()).hexdigest()


A, B = sys.argv[1], sys.argv[2]
OUT = sys.argv[3] if len(sys.argv) > 3 else '/tmp/b1/step2/render_cmp.json'

names = sorted(fn[:-5] for fn in os.listdir(A) if fn.endswith('.html'))
names_b = sorted(fn[:-5] for fn in os.listdir(B) if fn.endswith('.html'))
assert names == names_b, f'页面集合不一致: A\B={set(names)-set(names_b)} B\A={set(names_b)-set(names)}'

rows, same, diff = {}, [], []
for n in names:
    ra, ma, ca = masked_text(os.path.join(A, n + '.html'))
    rb, mb, cb = masked_text(os.path.join(B, n + '.html'))
    ha, hb = sha(ma), sha(mb)
    rows[n] = {'sha256_A': ha, 'sha256_B': hb, 'masks_A': ca, 'masks_B': cb,
               'bytes_A': len(ma.encode()), 'bytes_B': len(mb.encode())}
    (same if ha == hb else diff).append(n)

print('=' * 80)
print(f'A = {A}')
print(f'B = {B}')
print('=' * 80)
print(f'页面总数 {len(names)}   掩码后相同 {len(same)}   不同 {len(diff)}')
print(f'  相同: {", ".join(same) if same else "(无)"}')
print()
print(f'{"page":<15}{"A":<18}{"B":<18}{"判定":<7}{"A字节":>8}{"B字节":>8}{"style_ver掩码":>13}')
for n in names:
    r = rows[n]
    mark = 'SAME' if r['sha256_A'] == r['sha256_B'] else 'DIFF'
    print(f"{n:<15}{r['sha256_A'][:16]:<18}{r['sha256_B'][:16]:<18}{mark:<7}"
          f"{r['bytes_A']:>8}{r['bytes_B']:>8}{r['masks_B'].get('style_ver', 0):>13}")

print()
nd = [n for n in names if n not in DOSAGE]
nd_same = [n for n in nd if rows[n]['sha256_A'] == rows[n]['sha256_B']]
print(f'非剂型页（{len(nd)}）掩码后逐字节全同: '
      f'{"✅ 是" if len(nd_same) == len(nd) else f"❌ 否 —— 不同: {sorted(set(nd)-set(nd_same))}"}')
dset = sorted(n for n in names if rows[n]['sha256_A'] != rows[n]['sha256_B'])
print(f'变化集合（{len(dset)}）: {dset}')
print(f'变化集合 == 8 剂型页: {"✅ 是" if dset == sorted(DOSAGE) else "❌ 否"}')

# ---------------- 差异限定证明 ----------------
print()
print('=' * 80)
print('差异限定证明：基线Hero段 → 替换为当前Hero段 后是否与当前逐字节相同')
print('=' * 80)
print(f"{'page':<15}{'Hero匹配数':>10}{'替换后==当前':>14}{'其他区块改动':>14}")
proof = {}
for n in DOSAGE:
    ra, ma, _ = masked_text(os.path.join(A, n + '.html'))
    rb, mb, _ = masked_text(os.path.join(B, n + '.html'))
    ha = HERO_RE.findall(ma)
    hb = HERO_RE.findall(mb)
    ok = len(ha) == 1 and len(hb) == 1 and ma.replace(ha[0], hb[0]) == mb
    proof[n] = {'hero_matches_A': len(ha), 'hero_matches_B': len(hb), 'confinement_ok': ok}
    print(f"{n:<15}{len(ha):>10}{('✅ 相同' if ok else '❌ 不同'):>14}"
          f"{('0（全局限 Hero）' if ok else '有'):>14}")
allok = all(v['confinement_ok'] for v in proof.values())
print()
print('结论: ' + ('✅ 8 剂型页的全部改动 100% 局限于 Hero 段（其余 7 区块 HTML 一字未动）'
               if allok else '❌ 存在 Hero 之外的改动，需复核'))

# ---------------- 非剂型页原始差异（不掩版本号） ----------------
print()
print('--- 补充：非剂型页「不掩版本号」时的原始差异量（应只有版本字符串）---')
for n in nd:
    ra = open(os.path.join(A, n + '.html'), encoding='utf-8', errors='replace').read()
    rb = open(os.path.join(B, n + '.html'), encoding='utf-8', errors='replace').read()
    d = sum(1 for x, y in zip(ra, rb) if x != y) + abs(len(ra) - len(rb))
    delta = len(rb) - len(ra)
    print(f'  {n:<15} 字符差异 {d:>4}  字节差 {delta:+d}   '
          f'ver 出现 A={ra.count("?ver=2.10.38")} B={rb.count("?ver=2.10.39")}')

json.dump({'A': A, 'B': B, 'same': same, 'diff': diff, 'rows': rows,
           'confinement_proof': proof},
          open(OUT, 'w'), ensure_ascii=False, indent=1, sort_keys=True)
print('→', OUT)

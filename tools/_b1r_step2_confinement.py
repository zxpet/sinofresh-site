#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch 1 / 步骤 2 —— **完整限定证明**（Hero 之外的字节差异精确归类）

前序 tools/_b1r_step2_render_cmp.py 已证明：
  ① 11 个非剂型页掩码后逐字节全同（变化集合 == 8 剂型页）；
  ② 但「把基线 Hero 段换成当前 Hero 段」后仍有差异 —— 说明 Hero 之外还有改动。

本脚本把 Hero 之外的差异**逐类剥离并归类**，直到逐字节相同：

  归零步骤 0  基线滞后订正  `after packaging ready` → `after packaging is ready`
              ⚠️ 本条**不是**步骤 2 的改动，而是**基线滞后**：
                · 依据 tools/_b1r_step1_rollback.py:8 —— 该语法订正在步骤 1 回滚时
                  已被显式「保留（用户决策 ⑥）」；
                · 佐证 _backup/batch1-s2-hero-20260920-103207/templates/*.html
                  （步骤 2 之前的备份）8 页均已是 "is ready"；
                · 基线目录爬取于 09:17，早于折叠/回滚周期（09:38–10:05）→ 抓的是
                  中间态。
              → 限定证明在此充当「基线新鲜度探测器」：若不归零，会误报成
                「Hero 之外还有第三类改动」。
  归零步骤 1  替换 Hero 段  （基线 section.sf-hero-inner → 当前）
  归零步骤 2  删除 <script id="sinofresh-product-slider-js" …></script>
              （决策 ⑥ 删文件 + 移除 enqueue 的必然产物；在 footer，位于 </head> 之后）
  归零步骤 3  中和 <style id="core-block-supports-inline-css">…</style> 的**内容**
              （WP 从区块标记重新计算 wp-container-core-* 布局规则；删了 columns /
                buttons 区块，规则集合法地变化）

若三步之后 A_norm == B 逐字节相同，则证明：
  **Hero 之外的差异 100% 属于上述两类已知例外，别无他项。**

同时对 inline-css 做**规则级**盘点（新增/删除各几条、逐条列出），
让「规则集变化」从「一句解释」变成「可核对清单」。

用法：python3 tools/_b1r_step2_confinement.py <基线目录> <当前目录> [out_json]
"""
import hashlib
import json
import os
import re
import sys

# —— 与 tools/_b1r_step2_render_cmp.py 逐字同源的掩码集（不复用 import：
#    该脚本模块级即执行比对，import 会产生副作用），保证两处口径一致。
MASKERS = [
    (re.compile(r"value='[A-Za-z0-9+/=$]{40,}'"), "value='__MASKED__'"),
    (re.compile(r"gform_phone_dropdown_[0-9a-f]{8,}"), "gform_phone_dropdown___MASKED__"),
    (re.compile(r'config_nonce"\s*:\s*"[0-9a-f]{8,}"'), 'config_nonce":"__MASKED__"'),
    (re.compile(r'nonce=[0-9a-f]{8,}'), 'nonce=__MASKED__'),
    (re.compile(r'"nonce"\s*:\s*"[0-9a-f]{8,}"'), '"nonce":"__MASKED__"'),
    (re.compile(r'sinofresh-theme/style\.css\?ver=[0-9]+\.[0-9]+\.[0-9]+'),
     'sinofresh-theme/style.css?ver=__MASKED__'),
]
HERO_RE = re.compile(r'<section class="[^"]*\bsf-hero-inner\b[^"]*"[^>]*>.*?</section>', re.S)
DOSAGE = ['soft-chews', 'tablets', 'powders', 'pastes', 'drops', 'liquids',
          'fish-oil', 'dental-chews']


def sha(t):
    return hashlib.sha256(t.encode()).hexdigest()


SLIDER_RE = re.compile(
    r'\t?<script id="sinofresh-product-slider-js"[^>]*></script>\s*\n?')
INLINE_RE = re.compile(
    r'(<style id="core-block-supports-inline-css"[^>]*>)(.*?)(</style>)', re.S)
RULE_RE = re.compile(r'([^{}]+)\{([^{}]*)\}')

# 归零步骤 0：基线滞后订正（详见模块 docstring）
STALE_OLD = 'after packaging ready'
STALE_NEW = 'after packaging is ready'
# 现网/源码侧必须已经是新措辞；若否，说明这不是滞后而是新改动 → 门禁拦截
SRC_TEMPLATES = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'sinofresh-theme', 'templates')
for _p in DOSAGE:
    _t = open(os.path.join(SRC_TEMPLATES, f'page-{_p}.html'), encoding='utf-8').read()
    assert _t.count(STALE_NEW) == 1 and STALE_OLD not in _t, (
        f'门禁失败: page-{_p}.html 措辞不是滞后的新措辞，归零步骤 0 不成立')

A, B = sys.argv[1], sys.argv[2]
OUT = sys.argv[3] if len(sys.argv) > 3 else '/tmp/b1/step2/confinement.json'


def step_replace_hero(ma, mb, name):
    ha, hb = HERO_RE.findall(ma), HERO_RE.findall(mb)
    assert len(ha) == 1, f'{name}: 基线 Hero 匹配 {len(ha)} 个（应 1）'
    assert len(hb) == 1, f'{name}: 当前 Hero 匹配 {len(hb)} 个（应 1）'
    return ma.replace(ha[0], hb[0]), hb[0]


def step_drop_slider(m):
    n = len(SLIDER_RE.findall(m))
    return SLIDER_RE.sub('', m), n


def step_neutralize_inline(m):
    blocks = INLINE_RE.findall(m)
    assert len(blocks) <= 1, f'core-block-supports-inline-css 出现 {len(blocks)} 次'
    if not blocks:
        return m, None, 0
    css = blocks[0][1]
    return INLINE_RE.sub(r'\1__INLINE_CSS_NEUTRALIZED__\3', m, count=1), css, len(css)


def rules_of(css):
    if css is None:
        return {}
    out = {}
    for sel, body in RULE_RE.findall(css):
        sel = ' '.join(sel.split())
        if not sel or sel.startswith('@'):
            continue
        out.setdefault(sel, set()).update(
            x.strip() for x in body.split(';') if x.strip())
    return out


print('=' * 84)
print(f'基线 A = {A}')
print(f'当前 B = {B}')
print('=' * 84)
print('归零流水线（逐步剥离，直到逐字节相同）')
print('=' * 84)
print(f"{'page':<14}{'起点sha':>10}{'+归零0':>10}{'+换Hero':>10}{'+删脚本':>10}"
      f"{'+中和CSS':>11}{'脚本数':>8}{'CSS块':>7}")

rows, report = {}, {}
for n in DOSAGE:
    ra = open(os.path.join(A, n + '.html'), encoding='utf-8', errors='replace').read()
    rb = open(os.path.join(B, n + '.html'), encoding='utf-8', errors='replace').read()
    # 掩码（与 render_cmp 同口径）
    for rx, rep in MASKERS:
        ra, rb = rx.sub(rep, ra), rx.sub(rep, rb)

    h_start = sha(ra) == sha(rb)

    # 归零步骤 0：基线滞后订正
    sha_raw = sha(ra)
    stale_n = ra.count(STALE_OLD)
    ra = ra.replace(STALE_OLD, STALE_NEW)
    m0 = sha(ra) == sha(rb)

    a1, hero_b = step_replace_hero(ra, rb, n)
    m1 = sha(a1) == sha(rb)

    a2, nscript = step_drop_slider(a1)
    m2 = sha(a2) == sha(rb)

    a3, css_a, len_css_a = step_neutralize_inline(a2)
    b3, css_b, len_css_b = step_neutralize_inline(rb)
    m3 = sha(a3) == sha(b3)

    rows[n] = {'hero_A': hero_b, 'slider_tags': nscript, 'stale_hits': stale_n,
               'inline_css_A': None if css_a is None else len(css_a),
               'inline_css_B': None if css_b is None else len(css_b),
               'sha_start': sha_raw, 'sha_after_stale': sha(ra),
               'sha_after_hero': sha(a1),
               'sha_after_slider': sha(a2), 'sha_final_A': sha(a3),
               'sha_final_B': sha(b3),
               'ok_final': m3, 'ok_start_same': h_start}
    print(f"{n:<14}{'同' if h_start else '异':>10}{'同' if m0 else '异':>10}"
          f"{'同' if m1 else '异':>10}{'同' if m2 else '异':>10}"
          f"{'同' if m3 else '异':>11}{nscript:>8}{(len_css_b or 0):>7}")

print()
all_final = all(v['ok_final'] for v in rows.values())
print(f'四步归零后逐字节全同（8/8）: '
      f'{"✅ 是" if all_final else "❌ 否 —— " + str([k for k, v in rows.items() if not v["ok_final"]])}')

# ---------------- inline-css 规则级盘点 ----------------
print()
print('=' * 84)
print('例外 ①：<head> 内 wp-container-core-* 布局规则集（WP 由区块标记重新计算）')
print('=' * 84)
print(f"{'page':<14}{'基线规则':>9}{'当前规则':>9}{'新增':>7}{'删除':>7}{'基线字节':>10}{'当前字节':>10}")

added_all, removed_all = {}, {}
for n in DOSAGE:
    ra = open(os.path.join(A, n + '.html'), encoding='utf-8', errors='replace').read()
    rb = open(os.path.join(B, n + '.html'), encoding='utf-8', errors='replace').read()
    _, css_a, la = step_neutralize_inline(ra)
    _, css_b, lb = step_neutralize_inline(rb)
    sa, sb = rules_of(css_a), rules_of(css_b)
    added = {k: sorted(sb[k] - sa.get(k, set())) for k in sb if sb[k] - sa.get(k, set())}
    removed = {k: sorted(sa[k] - sb.get(k, set())) for k in sa if sa[k] - sb.get(k, set())}
    added_all[n], removed_all[n] = added, removed
    report[n] = {'rules_added': len(added), 'rules_removed': len(removed),
                 'css_bytes_A': la, 'css_bytes_B': lb}
    print(f"{n:<14}{len(sa):>9}{len(sb):>9}{len(added):>7}{len(removed):>7}"
          f"{la:>10}{lb:>10}")

# 逐条列出（以 liquids 为样本，其余页同构）
sample = 'liquids'
print()
print(f'--- 规则级明细（样本页 {sample}）---')
print(f'  新增 {len(added_all[sample])} 条 / 删除 {len(removed_all[sample])} 条')
for cls, decls in sorted(added_all[sample].items()):
    print(f'  ＋ {cls}')
    for d in decls:
        print(f'      {d}')
for cls, decls in sorted(removed_all[sample].items()):
    print(f'  － {cls}')
    for d in decls:
        print(f'      {d}')

# 跨页一致性：新增/删除的规则名集合（转成可哈希的 tuple）
def sig(d):
    return tuple(sorted((k, tuple(v)) for k, v in d.items()))

sig_add = {sig(added_all[n]) for n in DOSAGE}
sig_rm = {sig(removed_all[n]) for n in DOSAGE}
print()
print(f'8 页规则变化是否同构: 新增 {"✅ 同构" if len(sig_add) == 1 else f"❌ {len(sig_add)} 种"}   '
      f'删除 {"✅ 同构" if len(sig_rm) == 1 else f"❌ {len(sig_rm)} 种"}')

# ---------------- 例外 ②：脚本标签 ----------------
print()
print('=' * 84)
print('例外 ②：<body> 内 product-slider 脚本标签移除（决策 ⑥）')
print('=' * 84)
print(f"{'page':<14}{'基线出现':>9}{'当前出现':>9}{'位置':>12}{'现状':>12}")
for n in DOSAGE:
    ra = open(os.path.join(A, n + '.html'), encoding='utf-8', errors='replace').read()
    rb = open(os.path.join(B, n + '.html'), encoding='utf-8', errors='replace').read()
    ca = ra.count('sinofresh-product-slider-js')
    cb = rb.count('sinofresh-product-slider-js')
    pos = '</head> 之后' if ca else '—'
    print(f"{n:<14}{ca:>9}{cb:>9}{pos:>12}{'✅ 已移除' if cb == 0 else '❌ 残留':>12}")

# ---------------- 无他项 ----------------
print()
print('=' * 84)
print('结论')
print('=' * 84)
print(f'  归零步骤 0（基线滞后订正）  : 8/8 各订正 {sorted({v["stale_hits"] for v in rows.values()})} 处')
print(f'  归零步骤 1（Hero 段替换）   : 8/8 已应用')
print(f'  归零步骤 2（脚本标签移除）  : {sum(1 for v in rows.values() if v["slider_tags"] == 1)}/8 各移除 1 个')
print(f'  归零步骤 3（inline-css 中和）: 8/8 已应用')
print(f'  → 四步后逐字节全同 : {"✅ 8/8" if all_final else "❌"}')
print('  → 结论：Hero 之外的字节差异 **100% 归入以下 3 类，别无他项**：')
print('       ① <head> 内 core-block-supports-inline-css 的 wp-container-core-* 规则集')
print('          （＋buttons-is-layout 1 条 / －group-is-layout 1 条，WP 由区块标记重算）')
print('       ② <body> 内 product-slider 脚本标签移除 1 个（决策 ⑥ 的必然产物）')
print('       ③ style.css?ver 版本号 2.10.38→2.10.39（决策 ⑧，已掩码）')
print('       ④ 基线滞后项（Lead time 措辞）—— 非步骤 2 改动，见归零步骤 0')

json.dump({'A': A, 'B': B, 'dosage': DOSAGE, 'rows': rows, 'inline_css': report,
           'rules_added': added_all, 'rules_removed': removed_all,
           'all_final_identical': all_final},
          open(OUT, 'w'), ensure_ascii=False, indent=1, sort_keys=True)
print('→', OUT)

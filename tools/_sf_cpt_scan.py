#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Standard Formulas 卡片化 + CPT 架构 —— 第一步：21 个配方完整数据抽取（只读）

遍历 8 个剂型页的 `section.sf-formulas`，逐个 `<details class="sf-formula__item">` 提取：
  配方名 / 分类标签 / Ingredients / Guaranteed Analysis / Standard Specs / CTA data-formula /
  剂型归属 / 在页内的字节偏移
同时抽出模板内**硬编码**的 `ItemList` JSON-LD，与 DOM 里的配方逐项对表。

只读；只写 /tmp。用法：python3 tools/_sf_cpt_scan.py [outdir]
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL = os.path.join(ROOT, 'sinofresh-theme', 'templates')
OUT = sys.argv[1] if len(sys.argv) > 1 else '/tmp/b1/cpt_scan'
os.makedirs(OUT, exist_ok=True)

DOSAGE = ['soft-chews', 'tablets', 'powders', 'pastes', 'drops', 'liquids',
          'fish-oil', 'dental-chews']
EXPECT = {'soft-chews': 4, 'tablets': 3, 'powders': 3, 'pastes': 2, 'drops': 2,
          'liquids': 2, 'fish-oil': 2, 'dental-chews': 3}

SECTION_RE = re.compile(
    r'<section id="formulas"[^>]*>(.*?)</section>', re.S)
ITEM_RE = re.compile(r'<details class="sf-formula__item">(.*?)</details>', re.S)
NAME_RE = re.compile(r'<span class="sf-formula__name">(.*?)</span>', re.S)
USE_RE = re.compile(r'<span class="sf-formula__use">(.*?)</span>', re.S)
CTA_RE = re.compile(r'data-formula="(.*?)"', re.S)
VALUE_RE = re.compile(
    r'<h4 class="sf-formula__label">(.*?)</h4>\s*<p class="sf-formula__value">(.*?)</p>', re.S)
LDLIST_RE = re.compile(
    r'<script type="application/ld\+json">(\{"@context".*?"ItemList".*?\})</script>', re.S)

LABELS = ['Ingredients', 'Guaranteed Analysis', 'Standard Specs']


def unesc(s):
    return (s.replace('&amp;', '&').replace('&middot;', '·')
             .replace('&nbsp;', ' ').replace('&mdash;', '—').replace('&#8217;', '’'))


rows, page_rows, problems = [], {}, []
for slug in DOSAGE:
    path = os.path.join(TPL, f'page-{slug}.html')
    raw = open(path, encoding='utf-8').read()
    sec = SECTION_RE.search(raw)
    if not sec:
        problems.append(f'{slug}: 找不到 section#formulas')
        continue
    body = sec.group(1)
    items = ITEM_RE.findall(body)
    page_rows[slug] = {'section_bytes': len(sec.group(0).encode()),
                       'items': len(items),
                       'section_start': sec.start()}
    if len(items) != EXPECT[slug]:
        problems.append(f'{slug}: 配方数 {len(items)} ≠ 预期 {EXPECT[slug]}')

    for i, it in enumerate(items, 1):
        m_name = NAME_RE.search(it)
        m_use = USE_RE.search(it)
        m_cta = CTA_RE.search(it)
        labels = {}
        for lab, val in VALUE_RE.findall(it):
            labels[unesc(lab.strip())] = unesc(val.strip())
        row = {
            'slug': slug, 'idx': i,
            'name': unesc(m_name.group(1).strip()) if m_name else None,
            'use': unesc(m_use.group(1).strip()) if m_use else None,
            'cta_data_formula': unesc(m_cta.group(1).strip()) if m_cta else None,
            'labels': labels,
            'missing_labels': [l for l in LABELS if l not in labels],
        }
        # 门禁：name 与 cta 的 data-formula 必须一致（前者是展示名，后者是配方身份锚）
        if row['name'] != row['cta_data_formula']:
            problems.append(f"{slug}#{i}: name={row['name']!r} ≠ data-formula={row['cta_data_formula']!r}")
        rows.append(row)

    # 模板内硬编码的 ItemList
    m_ld = LDLIST_RE.search(body)
    if m_ld:
        try:
            ld = json.loads(unesc(m_ld.group(1)))
            names_ld = [e['name'] for e in ld.get('itemListElement', [])]
            names_dom = [unesc(NAME_RE.search(x).group(1).strip()) for x in items]
            page_rows[slug]['itemlist_name'] = ld.get('name')
            page_rows[slug]['itemlist_ok'] = names_ld == names_dom
            page_rows[slug]['itemlist_n'] = len(names_ld)
            if names_ld != names_dom:
                problems.append(f'{slug}: ItemList 与 DOM 不一致 → LD={names_ld} DOM={names_dom}')
        except Exception as e:
            problems.append(f'{slug}: ItemList JSON 解析失败 {e}')
    else:
        page_rows[slug]['itemlist_ok'] = None
        problems.append(f'{slug}: 未找到 ItemList JSON-LD')

# ---------------- 输出 ----------------
print('=' * 88)
print('一、21 个配方完整数据')
print('=' * 88)
print(f"{'#':>3} {'剂型':<14}{'配方名':<34}{'分类标签':<16}{'字段数':>6}")
for i, r in enumerate(rows, 1):
    print(f"{i:>3} {r['slug']:<14}{r['name']:<34}{r['use']:<16}{len(r['labels']):>6}")

print()
print(f"总配方数: {len(rows)}   " +
      ('✅ 与 21 一致' if len(rows) == 21 else f'❌ 与预期 21 不一致'))
print()
print(f"{'剂量型':<15}{'配方数':>7}{'预期':>7}{'区块字节':>10}{'ItemList条数':>13}{'ItemList一致':>13}")
for slug in DOSAGE:
    p = page_rows.get(slug, {})
    print(f"{slug:<15}{p.get('items', 0):>7}{EXPECT[slug]:>7}{p.get('section_bytes', 0):>10}"
          f"{p.get('itemlist_n', 0):>13}{('✅' if p.get('itemlist_ok') else '❌'):>13}")

print()
print('=' * 88)
print('分类标签（use）分布')
print('=' * 88)
uses = {}
for r in rows:
    uses.setdefault(r['use'], []).append(f"{r['slug']}/{r['name']}")
for u, lst in sorted(uses.items(), key=lambda kv: -len(kv[1])):
    print(f'  {u:<20} {len(lst):>2} 个')
print(f'  不同标签数: {len(uses)}')

print()
print('=' * 88)
print('字段完整性')
print('=' * 88)
miss = [r for r in rows if r['missing_labels']]
print(f"  三字段（Ingredients / Guaranteed Analysis / Standard Specs）齐备: "
      f"{'✅ 21/21' if not miss else f'❌ 缺字段 {[(r[chr(39)+chr(39)] if False else r['slug'], r['name'], r['missing_labels']) for r in miss]}'}")

print()
print('=' * 88)
print('门禁')
print('=' * 88)
if problems:
    for p in problems:
        print('  ❌ ' + p)
else:
    print('  ✅ 全部通过：配方数达标 / name ≡ data-formula / ItemList ≡ DOM')

json.dump({'formulas': rows, 'pages': page_rows, 'expect': EXPECT,
           'problems': problems},
          open(os.path.join(OUT, 'formulas.json'), 'w'),
          ensure_ascii=False, indent=1)
print()
print('→', os.path.join(OUT, 'formulas.json'))

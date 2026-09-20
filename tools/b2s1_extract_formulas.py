#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批次 2B 阶段1.2a：从 8 个剂型页模板抽取 21 条配方 → 迁移 JSON（只读模板，只写 _migration/cpt-2b/）。
复用 _sf_cpt_scan.py 的正则口径。门禁：总数=21、name≡data-formula、三字段齐备、ItemList 逐页一致。
"""
import json, os, re, html as htmllib

ROOT = "/Users/meng/WorkBuddy/sinofresh外贸网站建设"
TPL = os.path.join(ROOT, "sinofresh-theme", "templates")
OUTDIR = os.path.join(ROOT, "_migration", "cpt-2b")
os.makedirs(OUTDIR, exist_ok=True)

DOSAGE = ["soft-chews", "tablets", "powders", "pastes", "drops", "liquids", "fish-oil", "dental-chews"]
EXPECT = {"soft-chews": 4, "tablets": 3, "powders": 3, "pastes": 2, "drops": 2, "liquids": 2, "fish-oil": 2, "dental-chews": 3}
FORM_TITLE = {"soft-chews": "Soft Chews", "tablets": "Tablets", "powders": "Powders", "pastes": "Pastes",
              "drops": "Drops", "liquids": "Liquids", "fish-oil": "Fish Oil", "dental-chews": "Dental Chews"}

SECTION_RE = re.compile(r'<section id="formulas"[^>]*>(.*?)</section>', re.S)
ITEM_RE = re.compile(r'<details class="sf-formula__item">(.*?)</details>', re.S)
NAME_RE = re.compile(r'<span class="sf-formula__name">(.*?)</span>', re.S)
USE_RE = re.compile(r'<span class="sf-formula__use">(.*?)</span>', re.S)
CTA_RE = re.compile(r'data-formula="(.*?)"', re.S)
VALUE_RE = re.compile(r'<h4 class="sf-formula__label">(.*?)</h4>\s*<p class="sf-formula__value">(.*?)</p>', re.S)
LDLIST_RE = re.compile(r'<script type="application/ld\+json">(\{"@context".*?"ItemList".*?\})</script>', re.S)
LABELS = ["Ingredients", "Guaranteed Analysis", "Standard Specs"]

def unesc(s):
    return (s.replace("&amp;", "&").replace("&middot;", "·").replace("&nbsp;", " ")
             .replace("&mdash;", "—").replace("&#8217;", "’"))

rows, problems, itemlist_raw = [], [], {}
for slug in DOSAGE:
    raw = open(os.path.join(TPL, f"page-{slug}.html"), encoding="utf-8").read()
    sec = SECTION_RE.search(raw)
    if not sec:
        problems.append(f"{slug}: 找不到 section#formulas"); continue
    body = sec.group(1)
    items = ITEM_RE.findall(body)
    if len(items) != EXPECT[slug]:
        problems.append(f"{slug}: 配方数 {len(items)} ≠ 预期 {EXPECT[slug]}")
    # ItemList 原文留档（阶段1.2d 要比对 &amp; 修正）
    m_ld = LDLIST_RE.search(body)
    if not m_ld:
        problems.append(f"{slug}: 未找到 ItemList JSON-LD")
    else:
        itemlist_raw[slug] = m_ld.group(1)
        names_ld = [e["name"] for e in json.loads(unesc(m_ld.group(1)))["itemListElement"]]
        names_dom = [unesc(NAME_RE.search(x).group(1).strip()) for x in items]
        if names_ld != names_dom:
            problems.append(f"{slug}: ItemList 与 DOM 不一致")
    for i, it in enumerate(items, 1):
        m_name, m_use, m_cta = NAME_RE.search(it), USE_RE.search(it), CTA_RE.search(it)
        labels = {unesc(l.strip()): unesc(v.strip()) for l, v in VALUE_RE.findall(it)}
        row = {
            "dosage_slug": slug, "idx": i,
            "name": unesc(m_name.group(1).strip()) if m_name else None,
            "use_label": unesc(m_use.group(1).strip()) if m_use else None,
            "cta_data_formula": unesc(m_cta.group(1).strip()) if m_cta else None,
            "ingredients": labels.get("Ingredients"),
            "analysis": labels.get("Guaranteed Analysis"),
            "specs": labels.get("Standard Specs"),
            "source": f"page-{slug}.html #{i} (pre-2B template, extracted 2026-09-20)",
        }
        if row["name"] != row["cta_data_formula"]:
            problems.append(f"{slug}#{i}: name={row['name']!r} ≠ data-formula={row['cta_data_formula']!r}")
        missing = [l for l in LABELS if not labels.get(l)]
        if missing:
            problems.append(f"{slug}#{i}: 缺字段 {missing}")
        rows.append(row)

assert len(rows) == 21, f"门禁失败：总数 {len(rows)} ≠ 21"
assert not problems, "门禁失败：\n" + "\n".join(problems)

out = {"extracted_at": "2026-09-20", "total": len(rows), "form_title_map": FORM_TITLE, "records": rows}
with open(os.path.join(OUTDIR, "formulas.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
with open(os.path.join(OUTDIR, "itemlist-raw.json"), "w", encoding="utf-8") as f:
    json.dump(itemlist_raw, f, ensure_ascii=False, indent=2)

print(f"✅ 门禁全过：21 条 | name≡data-formula 21/21 | 三字段齐备 21/21 | ItemList 8/8 一致")
print(f"输出: {OUTDIR}/formulas.json ({os.path.getsize(os.path.join(OUTDIR, 'formulas.json'))} B)")
for r in rows:
    print(f"  {r['dosage_slug']:<14}#{r['idx']} {r['name']}  [use: {r['use_label']}]")

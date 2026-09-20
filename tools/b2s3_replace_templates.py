#!/usr/bin/env python3
"""2B Stage3 Step1: replace <section id="formulas"> legacy details markup
with the [sf_formula_grid] shortcode on the 8 dosage templates.
Serial per-file processing with assertions (2A lesson: no parallel edits).
"""
import re
import sys
from pathlib import Path

THEME = Path("/Users/meng/WorkBuddy/sinofresh外贸网站建设/sinofresh-theme/templates")

# slug -> expected details count
PAGES = {
    "soft-chews": 4,
    "tablets": 3,
    "powders": 3,
    "liquids": 2,
    "pastes": 2,
    "dental-chews": 3,
    "drops": 2,
    "fish-oil": 2,
}
INTRO = "Proven recipes from our existing OEM production"

def fail(msg):
    print(f"  ❌ {msg}")
    sys.exit(1)

total_old = total_new = 0
for slug, n_details in PAGES.items():
    path = THEME / f"page-{slug}.html"
    src = path.read_text(encoding="utf-8")
    old_size = len(src.encode("utf-8"))
    print(f"== {slug} ({old_size}B) ==")

    # --- assertions on the source structure ---
    if src.count('id="formulas"') != 1:
        fail(f'id="formulas" 出现 {src.count("id=formulas")} 次')
    if src.count('<details class="sf-formula__item">') != n_details:
        fail(f"details 数 {src.count('<details class=sf-formula__item>')} != {n_details}")
    if src.count("application/ld+json") != 1:
        fail("ItemList ld+json 数 != 1")
    if src.count(INTRO) != 1:
        fail("引导句不唯一")

    # section open tag line
    m = re.search(r'^<section id="formulas".*$', src, re.M)
    if not m:
        fail("找不到 section 开标签")
    # intro paragraph closes right after; keep through its <!-- /wp:paragraph -->
    keep_end = src.find("<!-- /wp:paragraph -->", m.end())
    if keep_end == -1:
        fail("找不到引导句收尾")
    keep_end += len("<!-- /wp:paragraph -->")

    # first </section> after the kept head
    sec_close = src.find("</section>", keep_end)
    if sec_close == -1:
        fail("找不到 </section>")

    # sanity: what we drop must contain all details + the ItemList, and nothing else structural
    dropped = src[keep_end:sec_close]
    if dropped.count('<details class="sf-formula__item">') != n_details:
        fail("待删段落 details 数不符")
    if "ItemList" not in dropped:
        fail("待删段落缺 ItemList")
    if "wp:shortcode" in dropped or "sf-fcard" in dropped:
        fail("待删段落含未知内容，中止")

    block = (
        "\n<!-- wp:shortcode -->\n"
        f'[sf_formula_grid form="{slug}"]\n'
        "<!-- /wp:shortcode -->\n"
    )
    new_src = src[:keep_end] + block + src[sec_close:]

    # --- post-edit assertions ---
    if new_src.count("sf-formula__item") != 0:
        fail("编辑后仍有 sf-formula__item 残留")
    if new_src.count("sf_formula_grid") != 1 or new_src.count("wp:shortcode") != 2:
        fail("shortcode 块不完整")
    if new_src.count(INTRO) != 1 or 'id="formulas"' not in new_src:
        fail("编辑后丢掉了 h2/引导句/section")
    if "&amp;" in re.search(r'"@type":"ItemList".*?</script>', new_src, re.S).group(0) if re.search(r'"@type":"ItemList"', new_src) else False:
        pass  # ItemList 已整体删除，模板内不应再有
    if 'ItemList' in new_src:
        fail("模板内仍有 ItemList 残留")
    if " / -->" in new_src:
        fail("自闭合残留 ' / -->'")

    new_size = len(new_src.encode("utf-8"))
    total_old += old_size
    total_new += new_size
    path.write_text(new_src, encoding="utf-8")
    print(f"  ✅ {old_size}B → {new_size}B (-{100*(old_size-new_size)/old_size:.1f}%)，details删{n_details}，shortcode=[sf_formula_grid form=\"{slug}\"]")

print(f"\n=== 合计 {total_old}B → {total_new}B (-{100*(total_old-total_new)/total_old:.1f}%) ===")

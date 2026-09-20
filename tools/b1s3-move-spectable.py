#!/usr/bin/env python3
"""批次1步骤3：把 sf-spectable（Key Facts 速览表）从 Hero 后移到 Configurator 之后、How We Work 之前。8 个剂型页模板。"""
import re, sys, pathlib

TPL = pathlib.Path(__file__).resolve().parent.parent / "sinofresh-theme" / "templates"
SLUGS = ["soft-chews", "tablets", "powders", "liquids", "pastes", "dental-chews", "drops", "fish-oil"]
SPECT_OPEN = '<!-- wp:group {"tagName":"section","className":"sf-spectable"'
HW9 = "<!-- Block 9: How We Work -->"

def find_block(lines):
    """返回 (start, end_inclusive)——spectable wp:group 起点 到 其配对 /wp:group。"""
    starts = [i for i, l in enumerate(lines) if l.startswith(SPECT_OPEN)]
    assert len(starts) == 1, f"spectable 起点数 {len(starts)} != 1"
    s = starts[0]
    for e in range(s + 1, len(lines)):
        if lines[e].strip() == "<!-- /wp:group -->":
            # 确认这是 spectable 自己的闭合（期间没有新 wp:group 开启）
            seg = lines[s + 1 : e]
            assert not any(l.startswith("<!-- wp:group") for l in seg), "区间内嵌套 wp:group，闭合判据失效"
            return s, e
    raise AssertionError("找不到 spectable 闭合")

for slug in SLUGS:
    f = TPL / f"page-{slug}.html"
    lines = f.read_text(encoding="utf-8").splitlines(keepends=True)

    s, e = find_block(lines)
    block = lines[s : e + 1]           # 含闭合
    # 块后若紧跟一个空行，一并带走，避免残留双空行
    trail = 1 if e + 1 < len(lines) and lines[e + 1].strip() == "" else 0
    cut = lines[s : e + 1 + trail]

    # 插入点：Block 9 注释之前（其前应有一个空行）
    hw = [i for i, l in enumerate(lines) if l.strip().startswith(HW9)]
    assert len(hw) == 1, f"{slug}: Block 9 注释数 {len(hw)} != 1"
    hw = hw[0]
    assert hw > e, f"{slug}: Block 9 在 spectable 之前，结构异常"

    new_lines = lines[:s] + lines[e + 1 + trail :]
    hw2 = [i for i, l in enumerate(new_lines) if l.strip().startswith(HW9)][0]
    ins = block + ["\n"]
    out = new_lines[:hw2] + ins + new_lines[hw2:]
    f.write_text("".join(out), encoding="utf-8")

    # ---- 复核 ----
    txt = "".join(out)
    assert txt.count("sf-spectable") >= 2  # 注释 + section
    pos_hero = txt.find("sf-hero-inner")
    pos_cfg = txt.find('id="configurator"')
    pos_spec = txt.find('sf-spectable"') 
    pos_hw = txt.find("How We Work")
    assert pos_hero < pos_cfg < pos_spec < pos_hw, f"{slug}: 区块顺序错误"
    print(f"✅ {slug}: 移动 {len(cut)} 行 | hero < configurator < spectable < howwework")
print("全部 8 页完成")

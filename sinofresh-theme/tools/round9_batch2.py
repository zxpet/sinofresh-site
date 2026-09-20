#!/usr/bin/env python3
"""Round9 批次二：首页 Learn More / Client Stories / Read More 链接修复。

任务1  8 个 Learn More href="#" → /products/{剂型}/（按卡片图片 stem 配对）
任务2  12 个 Client Stories 卡 <a href="#"> → <div>（去 aria-label，卡片视觉不变）
任务3  3 个 Read More href="#" → /blog/

用法:  python3 tools/round9_batch2.py --dry   # 只打印计划，不写盘
       python3 tools/round9_batch2.py --apply # 写盘
所有断言失败即中止且不写任何内容。
"""
import re, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
F = ROOT / "templates" / "front-page.html"

SLUGS = ["soft-chews","tablets","powders","pastes","drops","liquids","fish-oil","dental-chews"]
STORY_OPEN = re.compile(
    r'<a href="#" class="sf-card sf-card--quote sf-story" aria-label="Client story: ([^"]+)">')
LEARN_MORE = re.compile(r'<a href="#">(Learn More →)</a>')
READ_MORE = re.compile(r'<a href="#">(Read More →)</a>')

def main(apply: bool):
    text = F.read_text(encoding="utf-8")
    orig = text
    plan = []

    # ── 任务1 + 任务3：先按行扫描确定每个空链接的剂型归属 ──────────────
    lines = text.split("\n")
    cur_stem = None
    learn_hits, read_hits = [], []          # (行号, stem, 缩进前原文)
    for idx, line in enumerate(lines):
        m = re.search(r'sf-tile__media.*?uploads/2026/09/([a-z-]+)\.webp', line)
        if m:
            cur_stem = m.group(1)
        if LEARN_MORE.search(line):
            assert cur_stem in SLUGS, f"行{idx+1}: Learn More 前方未找到剂型图 (stem={cur_stem})"
            learn_hits.append((idx, cur_stem))
        if READ_MORE.search(line):
            read_hits.append(idx)
    assert len(learn_hits) == 8, f"Learn More 空链接应为 8 处，实际 {len(learn_hits)}"
    assert [s for _, s in learn_hits] == SLUGS, \
        f"剂型顺序不符: {[s for _, s in learn_hits]}"
    assert len(read_hits) == 3, f"Read More 空链接应为 3 处，实际 {len(read_hits)}"

    for idx, stem in learn_hits:
        lines[idx] = LEARN_MORE.sub(f'<a href="/products/{stem}/">\\1</a>', lines[idx])
        plan.append(f"任务1 行{idx+1}: Learn More → /products/{stem}/")
    for idx in read_hits:
        lines[idx] = READ_MORE.sub(r'<a href="/blog/">\1</a>', lines[idx])
        plan.append(f"任务3 行{idx+1}: Read More → /blog/")
    text = "\n".join(lines)

    # ── 任务2：<a href="#" ...>Client Stories 卡 → <div> ────────────────
    names = STORY_OPEN.findall(text)
    assert len(names) == 12, f"Client Stories 空链接卡应为 12 张，实际 {len(names)}"
    out, pos, closed = [], 0, 0
    while True:
        m = STORY_OPEN.search(text, pos)
        if not m:
            out.append(text[pos:])
            break
        out.append(text[pos:m.start()])
        out.append(f'<div class="sf-card sf-card--quote sf-story">')   # 去 aria-label：非交互元素不允许 aria-label
        plan.append(f"任务2: 卡「{m.group(1)}」 <a> → <div>（含去 aria-label）")
        # 找配对的 </a>（卡内已核验无嵌套 <a>，取其后第一个 </a>）
        end = text.index("</a>", m.end())
        inner = text[m.end():end]
        assert "<a " not in inner and "<a>" not in inner, \
            f"卡「{m.group(1)}」内部出现嵌套 <a>，需人工处理"
        assert m.group(1) in inner, f"卡「{m.group(1)}」内部未找到同名客户名，配对存疑"
        out.append(inner)
        out.append("</div>")
        closed += 1
        pos = end + len("</a>")
    assert closed == 12, f"应闭合 12 张卡，实际 {closed}"
    text = "".join(out)

    # ── 全局断言 ────────────────────────────────────────────────────────
    assert text.count('href="#"') == 0, \
        f"front-page.html 仍残留 {text.count(chr(39)+'#'+chr(39))} 处 href=\"#\":\n" + \
        "\n".join(l for l in text.split("\n") if 'href="#"' in l)
    assert text.count("<a ") == orig.count("<a ") - 12, "锚点数应恰好减 12"
    assert text.count("</a>") == orig.count("</a>") - 12, "闭合锚点数应恰好减 12"
    assert text.count("<div") == orig.count("<div") + 12, "div 数应恰好加 12"
    assert text.count("</div>") == orig.count("</div>") + 12, "闭合 div 数应恰好加 12"
    assert re.findall(r'alt="([^"]*)"', text) == re.findall(r'alt="([^"]*)"', orig), "alt 必须零变化"
    assert re.findall(r'src="([^"]*)"', text) == re.findall(r'src="([^"]*)"', orig), "src 必须零变化"
    assert '/ -->' not in text, "出现自闭合区块错误写法 / -->"
    for slug in SLUGS:
        assert f'href="/products/{slug}/">Learn More →' in text, f"缺 {slug} 的 Learn More 链接"
    assert text.count('href="/blog/">Read More →') == 3, "Read More → /blog/ 应恰 3 处"
    # 可见文字不变：去掉所有标签后逐字比对
    strip = lambda s: re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s)).strip()
    assert strip(text) == strip(orig), "可见文本发生变化"

    print(f"计划 {len(plan)} 项改动，全部断言通过：")
    for p in plan:
        print("  " + p)
    if apply:
        F.write_text(text, encoding="utf-8")
        print(f"\n已写入 {F}")
    else:
        print("\n[dry-run] 未写盘")

if __name__ == "__main__":
    main(apply="--apply" in sys.argv)

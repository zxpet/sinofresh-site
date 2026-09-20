#!/usr/bin/env python3
"""批次1 步骤2 —— style.css 清理（删废弃轮播样式 + 订正过时注释）。

删除（内容锚点定位，不依赖行号）：
  A. 16b 注释里的 `.sf-pslider` / `product-slider.js` 提及           → 订正
  B. `25c. Dosage hero: three-layer CTA row`（13 行规则 + 6 行注释） → 全删
  C. 26 节标题注释里的 "Hero image frame, "                          → 订正
  D. `/* Hero product image … plinth) */` + `.sf-product-hero-image` 三条规则（21 行）
  E. 共用 `@media (prefers-reduced-motion)` 里的 `.sf-product-hero-image img` 一行选择器
  F. `37. Product hero slider (dosage pages)` 整节（96 行规则 + 注释） → 全删
  G. 锚点注释里的「81px sticky bar」→ 实测 61px                        → 订正

保留：`.sf-slider-progress`（首页 hero-slider.js 共用）。

断言全部通过才写盘。
"""
import os
import re
import sys

FAM = ['sf-pslider', 'sf-product-hero-image', 'sf-hero-textlink']
KEEP_FAM = 'sf-slider-progress'


def find_theme():
    cur = os.path.abspath(os.getcwd())
    while True:
        c = os.path.join(cur, 'sinofresh-theme')
        if os.path.isdir(c):
            return c
        nxt = os.path.dirname(cur)
        if nxt == cur:
            sys.exit('[ABORT] 未找到 sinofresh-theme')
        cur = nxt


def cut(s, start_anchor, end_anchor, label, tally):
    """删除 [start_anchor, end_anchor) 区间，并把被删段的大括号数累加进 tally。"""
    if s.count(start_anchor) != 1:
        sys.exit(f'[ABORT] {label}: 起始锚点计数 {s.count(start_anchor)}（应 1）')
    if s.count(end_anchor) != 1:
        sys.exit(f'[ABORT] {label}: 结束锚点计数 {s.count(end_anchor)}（应 1）')
    i, j = s.index(start_anchor), s.index(end_anchor)
    if j <= i:
        sys.exit(f'[ABORT] {label}: 锚点顺序异常')
    seg = s[i:j]
    tally['{'] += seg.count('{')
    tally['}'] += seg.count('}')
    return s[:i] + s[j:], j - i


def main():
    theme = find_theme()
    p = os.path.join(theme, 'style.css')
    s0 = open(p, encoding='utf-8').read()
    s = s0
    log = []
    tally = {'{': 0, '}': 0}


    if s.count('{') != s.count('}'):
        sys.exit('[ABORT] 改前大括号已不平衡')

    # ---------- A. 16b 注释订正 ----------
    reps = [
        ('/* === 16b. Slider autoplay progress (hero + dosage pages) ==================',
         '/* === 16b. Slider autoplay progress (home hero) ============================='),
        ('   3px track hugging the bottom edge of .sf-hero-slider / .sf-pslider, below',
         '   3px track hugging the bottom edge of .sf-hero-slider, below'),
        ('   transform:scaleX from hero-slider.js / product-slider.js rAF loop — same',
         '   transform:scaleX from hero-slider.js rAF loop — same'),
        ('   absolutely positioned inside each stage. Hidden entirely when the visitor',
         '   absolutely positioned inside the stage. Hidden entirely when the visitor'),
    ]
    for a, b in reps:
        if s.count(a) != 1:
            sys.exit(f'[ABORT] A: 锚点计数 {s.count(a)}（应 1）: {a[:60]}')
        s = s.replace(a, b)
    log.append(('A', '16b 注释订正（去掉 .sf-pslider / product-slider.js）', 0))

    # ---------- B. 删 25c 节 ----------
    s, n = cut(s, '/* === 25c. Dosage hero: three-layer CTA row',
               '/* === 25d. Dosage page: specification strip', 'B', tally)
    log.append(('B', '删 25c 三按钮行样式（.sf-hero-textlink）', n))

    # ---------- C. 26 节标题注释订正 ----------
    a = '   Hero image frame, merged Specifications/Formula/Packaging band, compact'
    b = '   Merged Specifications/Formula/Packaging band, compact spec list, and'
    if s.count(a) != 1:
        sys.exit(f'[ABORT] C: 锚点计数 {s.count(a)}')
    s = s.replace(a, b).replace(
        '   spec list, and Related tiles reusing the homepage catalogue tile. */',
        '   Related tiles reusing the homepage catalogue tile. */')
    log.append(('C', '26 节标题注释订正（去掉 Hero image frame）', 0))

    # ---------- D. 删 .sf-product-hero-image 三条规则 ----------
    s, n = cut(s, '/* Hero product image fills its frame edge-to-edge (was a 60px plinth) */',
               '/* Merged band: Specifications | Formula Options | Packaging Options.', 'D', tally)
    log.append(('D', '删 .sf-product-hero-image（21 行 + 子注释）', n))

    # ---------- E. 共用 reduced-motion 里摘掉一行选择器 ----------
    a = '\t.sf-related-grid .sf-tile__media img,\n\t.sf-product-hero-image img {'
    b = '\t.sf-related-grid .sf-tile__media img {'
    if s.count(a) != 1:
        sys.exit(f'[ABORT] E: 锚点计数 {s.count(a)}')
    s = s.replace(a, b)
    log.append(('E', '共用 @media reduced-motion 摘掉 .sf-product-hero-image img 一行', 0))

    # ---------- F. 删 37 节（.sf-pslider 整节）----------
    s, n = cut(s, '/* === 37. Product hero slider (dosage pages)',
               '/* === 45. Inquiry basket: header bag + badge + slide-in drawer', 'F', tally)
    s = re.sub(r'\n{3,}(/\* === 45\. Inquiry basket)', r'\n\n\1', s)
    log.append(('F', '删 37 节 .sf-pslider（96 行规则 + 注释 + 2 个 @media）', n))

    # ---------- G. 「81px」→ 实测 61px ----------
    a = 'land the form below the 81px sticky bar on desktop. On phones the'
    b = 'land the form below the 61px sticky bar on desktop. On phones the'
    if s.count(a) != 1:
        sys.exit(f'[ABORT] G: 锚点计数 {s.count(a)}')
    s = s.replace(a, b)
    log.append(('G', '锚点注释 81px → 61px', 0))

    # ---------- 断言 ----------
    bad = []
    for f in FAM:
        if s.count(f) != 0:
            bad.append(f'仍残留 {f} × {s.count(f)}')
    if s.count(KEEP_FAM) != s0.count(KEEP_FAM):
        bad.append(f'{KEEP_FAM} 计数变化 {s0.count(KEEP_FAM)} → {s.count(KEEP_FAM)}')
    d_open = s0.count('{') - s.count('{')
    d_close = s0.count('}') - s.count('}')
    if d_open != tally['{'] or d_close != tally['}']:
        bad.append(f'大括号减少量 {{:{d_open} }}:{d_close} 与删除段统计 {{:{tally["{"]} }}:{tally["}"]} 不符')
    if s.count('{') != s.count('}'):
        bad.append('大括号不平衡')
    for must in ['#inquiry-form,\n#quote,\n#booking-form {\n\tscroll-margin-top: 96px;',
                 '.sf-slider-progress__bar {',
                 '.sf-related-grid .sf-tile__media img {',
                 '.sf-hero-slider']:
        if must not in s:
            bad.append(f'误删了应保留的内容: {must[:46]!r}')
    if re.search(r'/ -->', s):
        bad.append('存在 "/ -->" 写法')
    if bad:
        print('❌ 断言未通过：')
        for b_ in bad:
            print(f'     {b_}')
        sys.exit('[ABORT] 磁盘未改动')

    with open(p, 'w', encoding='utf-8') as f:
        f.write(s)
    assert open(p, encoding='utf-8').read() == s

    print(f'style.css  {len(s0):>8,} → {len(s):>8,} B   行 {s0.count(chr(10))+1} → {s.count(chr(10))+1}')
    for tag, what, n in log:
        print(f'  {tag}. {what}' + (f'   删除 {n} 字符' if n else ''))
    print(f'\n大括号 {s.count("{")}/{s.count("}")} 平衡（减少 {d_open}，与删除段统计一致）；'
          f'{KEEP_FAM} 保留 {s.count(KEEP_FAM)} 次')


if __name__ == '__main__':
    main()

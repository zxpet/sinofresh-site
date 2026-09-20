#!/usr/bin/env python3
"""批次1 步骤2 —— 8 个剂型页 Hero 极简化（方案 A：单栏居中）。

每个模板的 Hero 形态（8 页完全同构）：
  <section class="wp-block-group sf-hero-inner" …>          ← 深墨绿 #2E6B54
    <!-- wp:html --><nav class="sf-breadcrumb …">…</nav><!-- /wp:html -->
    <!-- wp:columns -->
      col1: h1 + p(描述18px) + p(认证13px) + buttons×3(Build实心/Browse描边/Request 文本链)
      col2: .sf-product-hero-image > .sf-pslider(4 slides + dots + 进度条)
    <!-- /wp:columns -->
  </section>

改为单栏居中：
  <section class="wp-block-group sf-hero-inner" …>
    <nav class="sf-breadcrumb …">…</nav>                    ← 逐页原文
    <h1 …textAlign center>…</h1>                            ← 逐页原文
    <p …align center>新的 8 页统一副标题</p>
    <buttons justifyContent center> Browse(cta 实心, 主) + Build(outline, 次) </buttons>
  </section>

删除：.sf-pslider 整块、.sf-product-hero-image 容器、描述段、认证行、Request a Quote。
保留：H1 原文（逐页）、面包屑原文（逐页）、Lead time 措辞（步骤 1 成果）。

断言全部通过才写盘（写盘前断言，失败则磁盘不动）。
"""
import json
import os
import re
import sys

SL = ['soft-chews', 'tablets', 'powders', 'pastes', 'drops', 'liquids',
      'fish-oil', 'dental-chews']

HERO_MARK = '<section class="wp-block-group sf-hero-inner"'
HERO_OPEN = ('<section class="wp-block-group sf-hero-inner" '
             'style="padding-top:var(--wp--preset--spacing--80);'
             'padding-bottom:var(--wp--preset--spacing--80)">')
SECTION_CLOSE = '</section>'

SUB = ('8 dosage forms &middot; FDA, cGMP, ISO 9001, FSSC 22000, HACCP, BRC '
       '&middot; Flexible MOQ &middot; Export to 30+ countries')

BODY_TMPL = '''<!-- wp:html -->
@@NAV@@
<!-- /wp:html -->
<!-- wp:heading {"level":1,"textAlign":"center","textColor":"card-white","style":{"typography":{"fontSize":"clamp(36px, 4vw, 52px)"}}} -->
<h1 class="has-text-align-center wp-block-heading has-card-white-color has-text-color" style="font-size:clamp(36px, 4vw, 52px)">@@H1@@</h1>
<!-- /wp:heading -->
<!-- wp:paragraph {"align":"center","textColor":"card-white","style":{"typography":{"fontSize":"18px"}}} -->
<p class="has-text-align-center has-card-white-color has-text-color" style="font-size:18px">@@SUB@@</p>
<!-- /wp:paragraph -->
<!-- wp:buttons {"layout":{"type":"flex","justifyContent":"center"},"style":{"spacing":{"margin":{"top":"var:preset|spacing|40"}}}} -->
<div class="wp-block-buttons is-layout-flex is-content-justification-center" style="margin-top:var(--wp--preset--spacing--40)">
<!-- wp:button {"backgroundColor":"cta","textColor":"card-white"} -->
<div class="wp-block-button"><a class="wp-block-button__link has-card-white-color has-cta-background-color has-text-color has-background wp-element-button" href="#formulas">Browse Standard Formulas</a></div>
<!-- /wp:button -->
<!-- wp:button {"textColor":"card-white","className":"is-style-outline"} -->
<div class="wp-block-button is-style-outline"><a class="wp-block-button__link has-card-white-color has-text-color wp-element-button" href="#configurator">Build Custom Formula</a></div>
<!-- /wp:button -->
</div>
<!-- /wp:buttons -->
'''

# --- 整页级「增量」断言：改写后应精确减少的量 ---
PAGE_DELTA = {
    '<!-- wp:columns': -1,
    '<!-- wp:column ': -2,
    '<!-- /wp:columns -->': -1,
    '<!-- wp:button ': -1,       # 3 → 2
    '<!-- wp:paragraph ': -1,    # 2 → 1
    '<!-- wp:heading ': 0,       # 去 1 加 1
    '<!-- wp:buttons ': 0,
    '<!-- wp:html': -1,          # 2 → 1（轮播那一组 wp:html 随 .sf-pslider 一起走）
    '<!-- /wp:html -->': -1,
}
PAGE_ZERO = ['sf-pslider', 'sf-product-hero-image', 'sf-hero-textlink',
             'sf-slider-progress', 'Request a Quote']


def find_root():
    cur = os.path.abspath(os.getcwd())
    while True:
        if os.path.isdir(os.path.join(cur, 'sinofresh-theme')):
            return cur
        nxt = os.path.dirname(cur)
        if nxt == cur:
            sys.exit('[ABORT] 未找到 sinofresh-theme')
        cur = nxt


def bowt(t, tag):
    return len(re.findall(rf'<{tag}[\s>]', t)), t.count(f'</{tag}>')


def check_kernel_new(k, t):
    bad = []
    if k.count('<!-- wp:html') != 1 or k.count('<!-- /wp:html -->') != 1:
        bad.append('wp:html 块不成对')
    for s, want in [('sf-pslider', 0), ('sf-product-hero-image', 0),
                    ('sf-hero-textlink', 0), ('Request a Quote', 0),
                    ('<!-- wp:columns', 0), ('<!-- wp:column ', 0)]:
        if k.count(s) != want:
            bad.append(f'残留 {s!r}={k.count(s)}（应 {want}）')
    for s, want in [('<!-- wp:heading ', 1), ('<!-- wp:paragraph ', 1),
                    ('<!-- wp:buttons ', 1), ('<!-- wp:button ', 2),
                    ('<h1', 1), ('<nav', 1), ('</nav>', 1),
                    ('href="#formulas"', 1), ('href="#configurator"', 1),
                    (SUB, 1)]:
        if k.count(s) != want:
            bad.append(f'{s!r} 应为 {want}，实为 {k.count(s)}')
    for tag in ('div', 'section', 'nav', 'p', 'h1', 'a'):
        o, c = bowt(k, tag)
        if o != c:
            bad.append(f'<{tag}> 失衡: {o} vs {c}')
    # 每个区块注释里的 JSON 必须能解析（按 --> 终结符切分，避免嵌套花括号被截断）
    for m in re.finditer(r'<!-- wp:([a-z0-9/-]+)(.*?)(/?)\s*-->', k, re.S):
        attrs = m.group(2).strip()
        if attrs:
            try:
                json.loads(attrs)
            except Exception as e:
                bad.append(f'区块属性 JSON 非法: {attrs[:70]}… ({e})')
    return bad


def main():
    root = find_root()
    theme = os.path.join(root, 'sinofresh-theme')
    rec, before = {}, {}

    # 先全量读取（避免写到一半失败造成半成品）
    texts = {}
    for t in SL:
        p = os.path.join(theme, 'templates', f'page-{t}.html')
        texts[t] = open(p, encoding='utf-8').read()

    # ---------- 阶段 1：构造 + 断言（不写盘） ----------
    for t in SL:
        s = texts[t]
        if s.count(HERO_MARK) != 1:
            sys.exit(f'[ABORT] {t}: Hero section 计数 {s.count(HERO_MARK)}（应 1）')
        if 'class="sf-pslider"' not in s:
            sys.exit(f'[ABORT] {t}: 无 .sf-pslider，疑似已改过，中止')

        i0 = s.index(HERO_MARK)
        i1 = s.index(SECTION_CLOSE, i0)
        k = s[i0:i1 + len(SECTION_CLOSE)]

        # --- 改写前内核断言 ---
        pre = [('class="sf-pslider"', 1),
               ('class="wp-block-group sf-product-hero-image', 1),
               ('class="wp-block-button sf-hero-textlink"', 1),
               ('<!-- wp:columns', 1), ('<!-- wp:column ', 2),
               ('<!-- /wp:columns -->', 1), ('<!-- wp:heading ', 1),
               ('<!-- wp:paragraph ', 2), ('<!-- wp:buttons ', 1),
               ('<!-- wp:button ', 3), ('<h1', 1), ('<nav', 1),
               ('Request a Quote', 1),
               ('class="sf-slider-progress"', 1),
               ('class="sf-slider-progress__bar"', 1),
               ('<!-- wp:html', 2), ('<!-- /wp:html -->', 2)]
        for mk, want in pre:
            got = k.count(mk)
            if got != want:
                sys.exit(f'[ABORT] {t}: 改写前 {mk!r} 应 {want}，实为 {got}')

        nav_m = re.search(r'<nav class="sf-breadcrumb.*?</nav>', k, re.S)
        h1_m = re.search(r'<h1[^>]*>(.*?)</h1>', k, re.S)
        desc_m = re.search(
            r'<p class="has-card-white-color has-text-color" '
            r'style="font-size:18px">(.*?)</p>', k, re.S)
        if not nav_m or not h1_m:
            sys.exit(f'[ABORT] {t}: 面包屑 / H1 抽取失败')
        nav, h1 = nav_m.group(0), h1_m.group(1)

        # --- 组装新内核 ---
        body = (BODY_TMPL.replace('@@NAV@@', nav)
                        .replace('@@H1@@', h1)
                        .replace('@@SUB@@', SUB))
        new_k = HERO_OPEN + '\n' + body + SECTION_CLOSE
        out = s[:i0] + new_k + s[i1 + len(SECTION_CLOSE):]

        # --- 改写后内核断言 ---
        nk = out[out.index(HERO_MARK):out.index(SECTION_CLOSE, out.index(HERO_MARK))
                 + len(SECTION_CLOSE)]
        bad = check_kernel_new(nk, t)

        # --- 整页增量断言 ---
        for mk, delta in PAGE_DELTA.items():
            d = out.count(mk) - s.count(mk)
            if d != delta:
                bad.append(f'整页 {mk!r} 变化 {d:+d}（应 {delta:+d}）')
        for mk in PAGE_ZERO:
            if out.count(mk) != 0:
                bad.append(f'整页仍残留 {mk!r} × {out.count(mk)}')
        if out.count('after packaging is ready') != 1:
            bad.append('Lead time 措辞受损')
        if re.search(r'/ -->', out):
            bad.append('存在 "/ -->" 分隔写法')
        for tag in ('div', 'section', 'nav', 'p', 'h1', 'details', 'summary', 'a'):
            o, c = bowt(out, tag)
            if o != c:
                bad.append(f'整页 <{tag}> 失衡: {o} vs {c}')

        if bad:
            print(f'❌ {t}')
            for b in bad:
                print(f'     {b}')
            sys.exit('[ABORT] 断言未通过，磁盘未改动')

        before[t] = s
        texts[t] = out
        rec[t] = {'h1': h1,
                  'desc_removed': desc_m.group(1) if desc_m else None,
                  'nav_current': re.search(r'--current"[^>]*>(.*?)</span>', nav).group(1)
                                 if re.search(r'--current"[^>]*>(.*?)</span>', nav) else None,
                  'bytes_before': len(s.encode()),
                  'bytes_after': len(out.encode())}
        print(f"  ✔ {t:<13} 断言通过  {len(s):>7,} → {len(out):>7,} B")

    # ---------- 阶段 2：全部通过后统一写盘 ----------
    print('\n全部断言通过 → 写盘')
    for t in SL:
        p = os.path.join(theme, 'templates', f'page-{t}.html')
        with open(p, 'w', encoding='utf-8') as f:
            f.write(texts[t])
        assert open(p, encoding='utf-8').read() == texts[t]
        print(f"  ✔ {t:<13} {rec[t]['bytes_before']:>7,} → {rec[t]['bytes_after']:>7,} B"
              f"  H1={rec[t]['h1'][:44]}")

    ev = '/tmp/b1/step2'
    os.makedirs(ev, exist_ok=True)
    with open(os.path.join(ev, 'hero_rewrite.json'), 'w', encoding='utf-8') as f:
        json.dump(rec, f, ensure_ascii=False, indent=1)
    print(f'\n逐页 H1 / 被删描述段 → {ev}/hero_rewrite.json')


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批次1 步骤2 · 追加修复 —— Product JSON-LD 的 description / image 失源

背景（步骤 2 的连带影响，非有意改动）：
  functions.php 的 Product JSON-LD 从模板文件解析：
    description ← hero 里「class 以 has-card-white-color 为首的 18px 段落」= 被删的描述段
    image       ← 文件中「第一个 <img>」= 原 hero 轮播的第一张 slide
  Hero 极简化后：description 正则 8 页全部落空（输出空串）；image 变成 Related 区块里
  其它剂型的产品图（7 页取到 soft-chews.webp），即「错页的图」。

修复原则：不改 PHP 里的文案（项目禁止硬编码），把逐页描述以**机器可读载体**留在
模板内；image 改为按文件名解析本页自有图，解析不到就不输出该键（宁可缺，不可错）。

做法：
  1) 在 8 个模板的 Hero <section> 起始标签后插入
     `<!-- sf-schema-desc: {原描述} -->`（纯 HTML 注释；非可见文本、不影响布局，
     且位于 Hero 段内 → 差异仍局限于 Hero 段）
  2) functions.php 按下方补丁改写两处抽取逻辑
断言全部通过才写盘。
"""
import json
import os
import re
import sys

SL = ['soft-chews', 'tablets', 'powders', 'pastes', 'drops', 'liquids',
      'fish-oil', 'dental-chews']

HERO_OPEN = ('<section class="wp-block-group sf-hero-inner" '
             'style="padding-top:var(--wp--preset--spacing--80);'
             'padding-bottom:var(--wp--preset--spacing--80)">')


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


def main():
    theme = find_theme()
    rec = json.load(open('/tmp/b1/step2/hero_rewrite.json', encoding='utf-8'))
    changed = []

    for t in SL:
        p = os.path.join(theme, 'templates', f'page-{t}.html')
        s = open(p, encoding='utf-8').read()
        desc = rec[t]['desc_removed']
        if not desc:
            sys.exit(f'[ABORT] {t}: 没有留档的原始描述')
        marker = f'<!-- sf-schema-desc: {desc} -->'

        if marker in s:
            print(f'  – {t:<13} 已存在，跳过')
            continue
        if s.count(HERO_OPEN) != 1:
            sys.exit(f'[ABORT] {t}: Hero 起始标签计数 {s.count(HERO_OPEN)}')
        if '<!-- sf-schema-desc:' in s:
            sys.exit(f'[ABORT] {t}: 已存在不同内容的 sf-schema-desc')

        out = s.replace(HERO_OPEN, HERO_OPEN + '\n' + marker, 1)

        # --- 断言 ---
        bad = []
        if out.count(marker) != 1:
            bad.append('载体注记计数不为 1')
        if out.count('sf-hero-inner') != s.count('sf-hero-inner'):
            bad.append('sf-hero-inner 计数变化')
        if out.count('<!-- wp:html') != s.count('<!-- wp:html'):
            bad.append('wp:html 计数变化')
        if out.count('<!-- /wp:html -->') != s.count('<!-- /wp:html -->'):
            bad.append('/wp:html 计数变化')
        if out.count('after packaging is ready') != 1:
            bad.append('Lead time 措辞受损')
        if re.search(r'/ -->', out):
            bad.append('存在 "/ -->" 写法')
        for tag in ('div', 'section', 'nav', 'p', 'h1', 'a'):
            o1 = len(re.findall(rf'<{tag}[\s>]', out)); c1 = out.count(f'</{tag}>')
            o0 = len(re.findall(rf'<{tag}[\s>]', s)); c0 = s.count(f'</{tag}>')
            if (o1, c1) != (o0, c0):
                bad.append(f'<{tag}> 计数变化 {(o0,c0)}→{(o1,c1)}')
        if bad:
            print(f'❌ {t}')
            for b in bad:
                print(f'     {b}')
            sys.exit('[ABORT] 断言未通过，磁盘未改动')

        with open(p, 'w', encoding='utf-8') as f:
            f.write(out)
        changed.append(t)
        print(f"  ✔ {t:<13} {len(s):>7,} → {len(out):>7,} B  载体注记已插入")

    print(f'\n模板改动 {len(changed)}/8')
    print('下一步：改写 functions.php 的两处抽取逻辑（见下方 Edit）')


if __name__ == '__main__':
    main()

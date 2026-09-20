#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Round9 · 剂型卡片图片链接（方案 A）
给 11 处位置 / 80 张剂型卡的图片加站内链接：
  wp:image 属性追加 linkDestination:"custom" + href:"/products/{stem}/"
  figure 内包一层 <a href="/products/{stem}/"> 包住 <img>（figure 仍是 .sf-tile 首子元素 → 布局零位移）

两族结构：
  家族1（52 张）figure 带 sf-tile__media，直接位于 .sf-tile group 内
  家族2（28 张）4 个未改造剂型页的 Related 卡，wp:image 嵌在 <p> 内（只在 Related 标题之后处理，
                避免误伤同页顶部的主产品图）

用法：python3 round9_image_links.py --dry | --apply
"""
import re
import sys
import os
import glob
import json
import shutil
import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES = os.path.join(ROOT, 'templates')

DOSAGES = ['soft-chews', 'tablets', 'powders', 'pastes',
           'drops', 'liquids', 'fish-oil', 'dental-chews']

# 家族1：sf-tile__media
PAT1 = re.compile(
    r'(?P<i1>[ \t]*)<!-- wp:image \{"align":"center","className":"sf-tile__media"\} -->\n'
    r'(?P<i2>[ \t]*)<figure class="wp-block-image aligncenter sf-tile__media">'
    r'<img src="/wp-content/uploads/2026/09/(?P<stem>[a-z-]+)\.webp"(?P<attrs>[^>]*)/></figure>\n'
    r'(?P<i3>[ \t]*)<!-- /wp:image -->'
)

# 家族2：旧版 Related 卡，图片块嵌在 <p> 内
PAT2 = re.compile(
    r'(?P<pre><p[^>]*>)<!-- wp:image \{"align":"center"\} -->\n'
    r'<figure class="wp-block-image aligncenter">'
    r'<img src="/wp-content/uploads/2026/09/(?P<stem>[a-z-]+)\.webp"(?P<attrs>[^>]*)/></figure>\n'
    r'<!-- /wp:image --></p>'
)

RELATED_MARK = 'Related Dosage Forms'


def repl1(m, report, fname):
    stem = m.group('stem')
    assert stem in DOSAGES, f'{fname}: 未知剂型 {stem}'
    report.append((fname, 'family1', stem))
    return (
        f'{m.group("i1")}<!-- wp:image {{"align":"center","className":"sf-tile__media",'
        f'"linkDestination":"custom","href":"/products/{stem}/"}} -->\n'
        f'{m.group("i2")}<figure class="wp-block-image aligncenter sf-tile__media">'
        f'<a href="/products/{stem}/"><img src="/wp-content/uploads/2026/09/{stem}.webp"'
        f'{m.group("attrs")}/></a></figure>\n'
        f'{m.group("i3")}<!-- /wp:image -->'
    )


def repl2(m, report, fname):
    stem = m.group('stem')
    assert stem in DOSAGES, f'{fname}: 未知剂型 {stem}'
    report.append((fname, 'family2', stem))
    return (
        f'{m.group("pre")}<!-- wp:image {{"align":"center","linkDestination":"custom",'
        f'"href":"/products/{stem}/"}} -->\n'
        f'<figure class="wp-block-image aligncenter">'
        f'<a href="/products/{stem}/"><img src="/wp-content/uploads/2026/09/{stem}.webp"'
        f'{m.group("attrs")}/></a></figure>\n'
        f'<!-- /wp:image --></p>'
    )


def transform(text, fname, report):
    # 家族1
    text = PAT1.sub(lambda m: repl1(m, report, fname), text)
    # 家族2：只处理 Related Dosage Forms 之后的部分
    idx = text.find(RELATED_MARK)
    if idx != -1:
        head, tail = text[:idx], text[idx:]
        tail = PAT2.sub(lambda m: repl2(m, report, fname), tail)
        text = head + tail
    return text


def visible_text(html):
    """去掉注释、标签、属性，仅留可见文本 + 块结构，用于零丢失断言"""
    h = re.sub(r'<!--.*?-->', '', html, flags=re.S)
    h = re.sub(r'<(script|style)\b.*?</\1>', '', h, flags=re.S | re.I)
    h = re.sub(r'<[^>]+>', ' ', h)
    return re.sub(r'\s+', ' ', h).strip()


def block_json_ok(text, fname):
    bad = []
    for m in re.finditer(r'<!-- wp:([a-z-]+(?:/[a-z-]+)?) (\{.*?\}) -->', text):
        try:
            json.loads(m.group(2))
        except Exception as e:
            bad.append((fname, m.group(1), m.group(2)[:80], str(e)))
    return bad


def main():
    dry = '--apply' not in sys.argv
    files = []
    for f in sorted(glob.glob(os.path.join(TEMPLATES, '*.html'))):
        if '.bak' in f:
            continue
        if 'sf-tile__media' in open(f, encoding='utf-8').read() or \
           'Related Dosage Forms' in open(f, encoding='utf-8').read():
            files.append(f)

    report = []
    new_texts = {}
    problems = []

    for f in files:
        fname = os.path.basename(f)
        src = open(f, encoding='utf-8').read()
        out = transform(src, fname, report)
        # 断言：可见文本零丢失/零新增
        if visible_text(src) != visible_text(out):
            problems.append(f'{fname}: 可见文本发生变化')
        # 断言：无 <a> 嵌套
        st = 0
        for m in re.finditer(r'<a\b[^>]*>|</a>', out):
            if m.group(0).startswith('</'):
                st -= 1
            else:
                if st > 0:
                    problems.append(f'{fname}: 出现 <a> 嵌套')
                st += 1
        # 断言：块注释 JSON 合法
        for b in block_json_ok(out, fname):
            problems.append(f'JSON 非法 {b}')
        # 断言：img 标签总数不变
        if len(re.findall(r'<img\b', src)) != len(re.findall(r'<img\b', out)):
            problems.append(f'{fname}: img 数量变化')
        # 断言：src / width / height / alt 未变
        for attr in ['src', 'width', 'height', 'alt']:
            if re.findall(r'%s="[^"]*"' % attr, src) != re.findall(r'%s="[^"]*"' % attr, out):
                problems.append(f'{fname}: {attr} 属性被改动')
        new_texts[f] = out

    # 统计
    by_fam = {'family1': 0, 'family2': 0}
    per_file = {}
    for fname, fam, stem in report:
        by_fam[fam] += 1
        per_file.setdefault(fname, []).append(stem)

    print('=' * 96)
    print('转换统计（dry=%s）' % dry)
    print('=' * 96)
    total = 0
    for fname in sorted(per_file):
        stems = per_file[fname]
        total += len(stems)
        print(f'{fname:28s} {len(stems):2d} 张  {" ".join(stems)}')
    print('-' * 96)
    print(f'家族1(sf-tile__media) = {by_fam["family1"]}   家族2(旧版 Related) = {by_fam["family2"]}   合计 = {total}')
    print()
    if problems:
        print('!!! 断言失败 !!!')
        for p in problems:
            print('  -', p)
        sys.exit(1)
    print('断言全部通过：可见文本零变化 / 无 <a> 嵌套 / 块 JSON 合法 / img 数与 src|width|height|alt 未变')

    if total != 80:
        print(f'!!! 数量不符：期望 80，实际 {total}')
        sys.exit(1)

    if dry:
        print('\n[dry-run] 未写入。确认后加 --apply 执行。')
        return

    # 备份
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    bdir = os.path.join(ROOT, '_backup', f'round9-imagelink-{stamp}')
    os.makedirs(bdir, exist_ok=True)
    for f in new_texts:
        shutil.copy2(f, os.path.join(bdir, os.path.basename(f)))
    print(f'\n备份 → {bdir}')

    for f, out in new_texts.items():
        open(f, 'w', encoding='utf-8').write(out)
    print(f'已写入 {len(new_texts)} 个模板文件')


if __name__ == '__main__':
    main()

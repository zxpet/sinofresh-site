#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H5, ruling E — the 80/20 content audit, as a report and nothing else.

Ruling E was "produce the audit, change no page". This tool therefore takes a
capture directory and writes a markdown report; it never edits a theme file.
Run it against the post-batch captures so the numbers describe what the site
serves now.

WHY THREE WORD COUNTS ARE NAMED BUT TWO ARE REPORTED

The obvious count — strip the tags and split on whitespace — counts attribute
residue, inline CSS bodies and script bodies, so it reads high by a factor of
about 2.5 on this site: the theme prints 100 KB of block CSS into every page,
and every CSS declaration token counts as a word. That count is NOT reported;
it is the number this report exists to replace. It was the number the H5 scan
published (1,930 words on /about/), and the only part of that figure that was
honest was the caveat attached to it.

What IS reported, on the page's own content region (see region_of below):

  strict — the text of h1-h6, p, li, td, th, dt and dd: the prose a visitor
           reads and a crawler weighs.
  broad  — the whole region, tags stripped: adds button labels, form field
           labels and captions that the strict count drops.

Both are emitted, the strict one leads, and the ranking is asserted to agree
between them — if the two orders ever diverge, the report says so instead of
picking the flattering one.

WHAT 80/20 MEANS HERE

The audit answers one question: is the body copy informational or promotional?
The proxy is CTA density — calls to action per thousand words of prose. A page
that is 80% substance and 20% ask lands near 200/1000; these pages are one to
two orders of magnitude below that, which is the finding: the copy is almost
purely informational, so raising it "to 20%" would be the wrong direction.

Depth (thin pages) is measured and reported as its own line, because it is a
different axis: a short utility page is not evidence of an 80/20 imbalance.

usage:
    b2d_h5_audit8020.py --pages DIR [--out report.md]
"""
import argparse
import collections
import glob
import html as htmlmod
import json
import os
import re
import statistics
import sys

BODY = re.compile(r'<body\b[^>]*>(.*)</body>', re.S)
CHROME = re.compile(r'<(header|footer)\b.*?</\1>', re.S)
LDJSON = re.compile(r'<script[^>]*application/ld\+json[^>]*>.*?</script>', re.S)
SCRIPT = re.compile(r'<script\b[^>]*>.*?</script>', re.S)
STYLE = re.compile(r'<style\b[^>]*>.*?</style>', re.S)
PROSE = re.compile(r'<(h[1-6]|p|li|td|th|dt|dd)\b[^>]*>(.*?)</\1>', re.S | re.I)
TAG = re.compile(r'<[^>]+>')

# Case-insensitive, word-bounded. Kept narrow on purpose: a phrase list that
# also matches body prose would inflate the numerator and make the site look
# more promotional than it is, which is the one direction this report must not
# err in.
CTA = re.compile(
    r'\b(get a quote|request a quote|get a sample|request a sample|'
    r'send an inquiry|send inquiry|contact us|talk to us|start your project|'
    r'request pricing|get pricing|download (?:the )?(?:brochure|catalog|spec)|'
    r'book a call|schedule a call|ask for a quote|place an order|'
    r'submit an inquiry|start an inquiry|get in touch|email us|'
    r'request a consultation|claim your (?:quote|sample))\b', re.I)

CATEGORY = [
    ('home', r'^root$'),
    ('product/剂型页', r'^products__'),
    ('formula/配方页', r'^formulas__(?!$)|^zh__formulas__(?!$)'),
    ('index/列表页', r'^(formulas|products|zh|zh__formulas|zh__products)$'),
    ('blog/内容页', r'^blog|^zh__blog'),
    ('legal/法务页', r'policy|terms|disclaimer|accessibility'),
]


TARGET = 200.0      # the 80/20 line: one ask per 200 words of prose


def region_of(t):
    """The page's own content: <body>, minus script/style, minus the chrome.

    The obvious wrapper is <main>, and this theme does not have one: it is a
    full-site-editing block theme whose only top-level container is
    .wp-site-blocks. So the region is defined by subtraction instead, and the
    subtraction is CHECKED rather than assumed — a silent fallback to the whole
    document is exactly the failure this function must not repeat. The caller
    asserts on the returned shape.
    """
    t = STYLE.sub(' ', t)
    t = SCRIPT.sub(' ', t)
    m = BODY.search(t)
    if not m:
        return None, 0, 0
    inner = m.group(1)
    n_h = len(re.findall(r'<header\b', inner))
    n_f = len(re.findall(r'<footer\b', inner))
    return CHROME.sub(' ', inner), n_h, n_f


def words(s):
    s = htmlmod.unescape(TAG.sub(' ', s))
    return len([w for w in re.split(r'\s+', s) if re.search(r'[A-Za-z0-9]', w)])


def plain(s):
    return htmlmod.unescape(TAG.sub(' ', s))


def category(k):
    # the language prefix is not part of the page's kind
    k = re.sub(r'^zh__', '', k)
    for name, pat in CATEGORY:
        if re.search(pat, k):
            return name
    return 'other/其它'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pages', required=True)
    ap.add_argument('--out', default=None)
    ap.add_argument('--limit', type=int, default=0)
    args = ap.parse_args()

    rows = []
    missing = []
    chrome = collections.Counter()
    for f in sorted(glob.glob(os.path.join(args.pages, '*.html'))):
        k = os.path.basename(f)[:-5]
        t = open(f, encoding='utf-8', errors='replace').read()
        body, n_h, n_f = region_of(t)
        if body is None:
            missing.append(k)
            continue
        chrome[(n_h, n_f)] += 1
        strict = words(' '.join(m.group(0) for m in PROSE.finditer(body)))
        rows.append({'page': k, 'cat': category(k),
                     'coarse': words(body), 'strict': strict,
                     'cta': len(CTA.findall(plain(body)))})
    if args.limit:
        rows = rows[:args.limit]

    # The region is measured, not assumed. A page without <body>, or a chrome
    # shape that never varies from the 2/2 this theme renders, would make every
    # number below describe something other than the page.
    if missing:
        sys.exit('FATAL: %d page(s) have no <body>: %s' % (len(missing), missing[:4]))
    if len(chrome) != 1:
        sys.exit('FATAL: the header/footer shape varies across pages: %r' % dict(chrome))
    if list(chrome) != [(2, 2)]:
        sys.exit('FATAL: expected two <header> and two <footer> per page, saw %r'
                 % dict(chrome))

    co = [r['coarse'] for r in rows]
    st = [r['strict'] for r in rows]
    ct = [r['cta'] for r in rows]
    med_co, med_st = statistics.median(co), statistics.median(st)
    total_cta, total_st = sum(ct), sum(st)
    thin = [r for r in rows if r['strict'] < 300]
    zero_cta = [r for r in rows if r['cta'] == 0]

    dens = sorted(rows, key=lambda r: (r['cta'] / r['strict'] if r['strict'] else 0))
    dens_desc = list(reversed(dens))
    by_cat = collections.OrderedDict()
    for r in rows:
        d = by_cat.setdefault(r['cat'], {'n': 0, 'strict': 0, 'cta': 0, 'med': []})
        d['n'] += 1
        d['strict'] += r['strict']
        d['cta'] += r['cta']
        d['med'].append(r['strict'])
    for d in by_cat.values():
        d['med'] = statistics.median(d['med'])
        d['dens'] = d['cta'] / d['strict'] * 1000 if d['strict'] else 0

    # the two orderings must agree, or the report says so
    rank_co = {r['page']: i for i, r in enumerate(sorted(rows, key=lambda r: r['coarse']))}
    rank_st = {r['page']: i for i, r in enumerate(sorted(rows, key=lambda r: r['strict']))}
    disagree = [r['page'] for r in rows if abs(rank_co[r['page']] - rank_st[r['page']]) > 12]

    # The verdict is DERIVED from the measurement, never asserted ahead of it.
    # A report that states its conclusion and then prints numbers that may
    # contradict it is the same class of failure as a gate whose criterion
    # cannot see the defect: it reads green regardless of the truth.
    dens_total = total_cta / total_st * 1000 if total_st else 0.0
    # 80/20 is one axis: promotion against substance. Depth is a second, and the
    # verdict is not allowed to smuggle it in — a thin utility page is not
    # evidence of an imbalance, so it is reported beside the verdict instead.
    satisfied = dens_total < TARGET
    if satisfied:
        verdict = ('**80/20 已满足，且余量极大；本项不需要任何改造动作。**'
                   if dens_total * 10 < TARGET else
                   '**80/20 已满足；本项不需要任何改造动作。**')
        action = '把密度"提到 20%"是**反方向**的处方；正确动作是**不动**。'
    else:
        verdict = ('**80/20 未满足 —— 本项需要改造动作，但裁决 E 只授权出报告，'
                   '故此处只登记、不改页面。**')
        action = '密度越线，**H6 需要一条内容项**；本报告不改任何页面。'
    ratio = '低 %.0f 倍' % (TARGET / dens_total) if dens_total else '（密度为 0）'
    depth = ('无薄页' if not thin else
             '薄页 %d 页（%s%s）——**这是深度轴，不是 80/20 轴**，单列'
             % (len(thin), '、'.join('`%s`' % r['page'] for r in thin[:4]),
                ' 等' if len(thin) > 4 else ''))

    L = []
    L.append('# Batch H5 · 内容 80/20 审计（裁决 E：只出报告，不改页面）\n')
    L.append('断面：`%s` 共 **%d 页**。本批**未改动任何页面内容** —— 本批的改动是 schema 与 ' % (
        args.pages, len(rows)))
    L.append('`alt` 字符串，不增删正文，所以这份审计同时是对"H5 有没有偷偷改内容"的旁证。\n')

    L.append('## 1. 结论\n')
    L.append(verdict + '\n')
    L.append('| 指标 | 严口径（`h1-6/p/li/td/th/dt/dd`） | 宽口径（正文区去标签） |')
    L.append('|---|---|---|')
    L.append('| 正文词数中位 | **%d 词/页** | %d 词/页 |' % (med_st, med_co))
    L.append('| <300 词的页 | **%d / %d** | %d / %d |' % (
        len(thin), len(rows), len([r for r in rows if r['coarse'] < 300]), len(rows)))
    L.append('| CTA 命中总数 | %d | — |' % total_cta)
    L.append('| **CTA 密度** | **%.1f / 千词 ＝ %.2f%%** | — |' % (
        dens_total, dens_total / 10))
    L.append('| CTA ＝ 0 的页 | %d / %d | — |' % (len(zero_cta), len(rows)))
    L.append('')
    L.append('判据（先说判据再读数）：一个"80%% 实质 / 20%% 招徕"的页面，密度应落在 '
             '**%.0f / 千词** 量级。' % TARGET)
    L.append('实测 **%.1f / 千词** ⇒ 距判据线 **%s**。' % (dens_total, ratio))
    L.append('⇒ %s' % action)
    L.append('深度轴另计：%s。\n' % depth)

    L.append('## 2. 口径、正文区定义与一致性核验\n')
    L.append('**正文区（region）定义**：本站是**全站编辑块主题，没有 `<main>`** —— '
             '顶层容器只有 `.wp-site-blocks`。')
    L.append('所以正文区＝`<body>` 去掉 `<script>`/`<style>` 后再**减去页头页脚**'
             '（每页 `2×<header>` ＋ `2×<footer>`，**形状实测为常量**，工具会断言，'
             '不允许静默回退到整页）。')
    L.append('被丢弃的第三个口径：**整页去标签（含行内 CSS）** —— 本主题每页内联约 100 KB 块 CSS，'
             '每条 CSS 声明都算一个"词"，该口径偏高约 2.5 倍。')
    L.append('H5 扫描档曾用这个口径报 `/about/` 1,930 词 —— **本报告不复用该数**，'
             '只在本节说明它为何不可比。\n')
    L.append('同一个词数有两个算法，本报告**两个都报、严口径领衔**：')
    L.append('- **严口径**：只数 `h1-6 / p / li / td / th / dt / dd` 的文本 —— 访客读、爬虫称重的那部分；')
    L.append('- **宽口径**：正文区去标签后按空白切 —— 多出按钮文字、表单标签、图注等。')
    L.append('')
    L.append('两种口径差约 %.2f 倍。**排名一致性核验**：两侧排序偏移 >12 位的页 = **%d** 个' % (
        (med_co / med_st) if med_st else 0, len(disagree)))
    if disagree:
        L.append('⇒ **排序不一致**：本节的两个结论必须并列，不得挑好看的报。以下分类/排名表'
                 '一律标口径；有 %d 页在两种口径下位次相差 12 位以上。\n' % len(disagree))
    else:
        L.append('⇒ 排序一致，**结论不依赖口径选择**（若不一致，本报告必须并列两个结论而不是挑好看的）。\n')

    L.append('## 3. 分类断面（严口径）\n')
    L.append('| 类别 | 页数 | 词数中位 | CTA 总数 | CTA 密度(/千词) |')
    L.append('|---|---|---|---|---|')
    for name, d in by_cat.items():
        L.append('| %s | %d | %d | %d | %.1f |' % (
            name, d['n'], d['med'], d['cta'], d['dens']))
    L.append('')
    L.append('> 注：legal 类页面的密度偏高是**结构性的**（页短、且每页都带"contact us"），')
    L.append('> 不是"推销性内容多"。**密度必须与词数一起读**，单看密度会把法务页读成营销页。\n')

    L.append('## 4. 密度最高的 8 页（严口径）\n')
    L.append('| 页 | 类别 | 词数 | CTA | 密度(/千词) |')
    L.append('|---|---|---|---|---|')
    for r in dens_desc[:8]:
        L.append('| `%s` | %s | %d | %d | %.1f |' % (
            r['page'], r['cat'], r['strict'], r['cta'],
            r['cta'] / r['strict'] * 1000 if r['strict'] else 0))
    L.append('')
    L.append('## 5. 密度最低的 8 页（严口径）\n')
    L.append('| 页 | 类别 | 词数 | CTA | 密度(/千词) |')
    L.append('|---|---|---|---|---|')
    for r in dens[:8]:
        L.append('| `%s` | %s | %d | %d | %.1f |' % (
            r['page'], r['cat'], r['strict'], r['cta'],
            r['cta'] / r['strict'] * 1000 if r['strict'] else 0))
    L.append('')
    L.append('## 6. 给下批的结论\n')
    if satisfied:
        L.append('1. **本项关闭**：无可执行动作。不存在"内容太促销"的问题，改动只会降低信息密度。')
        L.append('2. 若日后要提升转化，方向是**CTA 的位置与时机的质量**（已在 H4 的弹窗＋胶囊里做过），')
        L.append('   不是**数量**。数量在此已被证明不是瓶颈。')
    else:
        L.append('1. **本项未关闭**：密度 %.1f/千词 或薄页 %d 页越线 ⇒ 登记 H6 一条内容项，'
                 '本批按裁决 E 不改页面。' % (dens_total, len(thin)))
        L.append('2. 若改为执行，方向以本节排名表为准（密度最高的页与最薄的页两张表）。')
    L.append('3. **口径警告**：任何后续报告引用本页数字，必须带口径；两个口径差 %.2f 倍。\n' % (
        (med_co / med_st) if med_st else 0))

    md = '\n'.join(L)
    if args.out:
        open(args.out, 'w', encoding='utf-8').write(md)
        print('wrote %s' % args.out)
    else:
        print(md)
    return 0


if __name__ == '__main__':
    sys.exit(main())

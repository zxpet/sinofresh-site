#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
oem_patch.py — OEM/ODM 服务板块 2 张卡 → 4 张卡
  A. front-page.html  「OEM & ODM Services」      → sf-card sf-card--roomy 体系
  B. page-services.html「OEM or ODM — Choose Your Path」→ 原生白卡体系
       · 4 张卡（老卡补首页同款 ✓ 明细，四卡文案统一）
       · section 加 sf-oem 类（供等高规则挂钩）
做法：整块替换 wp:columns 区块，避免局部替换产生重复闭合标签。
"""
import io
import os

BASE = "/Users/meng/WorkBuddy/sinofresh外贸网站建设/sinofresh-theme"
HOME = os.path.join(BASE, "templates/front-page.html")
SERV = os.path.join(BASE, "templates/page-services.html")
CK = "\u2713"

BLOCK_START = '<!-- wp:columns {"verticalAlignment":"stretch","style":{"spacing":{"margin":{"top":"var:preset|spacing|60"}}}} -->'
COL_DIV_OPEN = '<div class="wp-block-columns are-vertically-aligned-stretch" style="margin-top:var(--wp--preset--spacing--60)">'
END_MARK = '</div>\n<!-- /wp:columns -->'

CARDS = [
    ("OEM &#8212; You Bring the Formula",
     "You provide the formula, specifications, and packaging requirements. We manufacture, test, and deliver.",
     ["Manufacturing", "Testing", "COA per batch", "Packaging", "Delivery"]),
    ("ODM &#8212; We Develop From Your Idea",
     "You provide a concept, reference sample, or functional requirement. We develop the formula, sample it, test palatability, and produce the finished product.",
     ["Formula development", "Palatability testing", "Sampling", "Stability testing", "Label support"]),
    ("Contract Manufacturing",
     "For established brands with full specifications. You own the IP, we run the production line.",
     ["Your formula, your IP", "Scaled mass production", "NDA-protected process",
      "Batch-level traceability", "COA and export documents"]),
    ("Private Label",
     "Pick from our proven formulas. Launch fast under your own brand.",
     ["Ready-to-market recipes", "Custom flavor and packaging", "Low MOQ for new brands",
      "3-7 day sampling", "No brand conflict"]),
]

GRP_OPEN = '<!-- wp:group {"backgroundColor":"card-white","layout":{"type":"constrained"},"style":{"border":{"radius":"8px"},"spacing":{"padding":{"top":"40px","bottom":"40px","left":"40px","right":"40px"}}}} -->'
GRP_DIV = '<div class="wp-block-group has-card-white-background-color has-background" style="border-radius:8px;padding-top:40px;padding-right:40px;padding-bottom:40px;padding-left:40px">'
HOME_GRP = '<!-- wp:group {"layout":{"type":"constrained"},"className":"sf-card sf-card--roomy"} --><div class="wp-block-group sf-card sf-card--roomy">'


def bullets(items):
    out = []
    for b in items:
        out.append('<!-- wp:paragraph {"style":{"typography":{"fontSize":"14px"}},"textColor":"primary"} -->')
        out.append('<p class="has-primary-color has-text-color" style="font-size:14px">%s %s</p>' % (CK, b))
        out.append('<!-- /wp:paragraph -->')
    return "\n".join(out)


def card(title, desc, bl, kind):
    body = [
        '<!-- wp:heading {"level":3} -->',
        '<h3 class="wp-block-heading">%s</h3>' % title,
        '<!-- /wp:heading -->',
        '<!-- wp:paragraph {"textColor":"text-secondary"} -->',
        '<p class="has-text-secondary-color has-text-color">%s</p>' % desc,
        '<!-- /wp:paragraph -->',
        bullets(bl),
    ]
    if kind == "home":
        return "\n".join([
            '<!-- wp:column {"verticalAlignment":"stretch"} -->',
            '<div class="wp-block-column is-vertically-aligned-stretch">',
            HOME_GRP,
        ] + body + [
            '</div>',
            '<!-- /wp:group -->',
            '</div>',
            '<!-- /wp:column -->',
        ])
    return "\n".join([
        '<!-- wp:column {"verticalAlignment":"stretch"} -->',
        '<div class="wp-block-column is-vertically-aligned-stretch">',
        GRP_OPEN,
        GRP_DIV,
    ] + body + [
        '</div>',
        '<!-- /wp:group -->',
        '</div>',
        '<!-- /wp:column -->',
    ])


def build(kind):
    cards = "\n".join(card(t, d, b, kind) for t, d, b in CARDS)
    return BLOCK_START + "\n" + COL_DIV_OPEN + "\n" + cards + "\n" + END_MARK


def patch(path, kind, expect_ctx):
    s = io.open(path, encoding="utf-8").read()
    start = s.find(BLOCK_START)
    assert start != -1, "block start not found in " + path
    assert expect_ctx in s[max(0, start - 700):start], "context guard failed in " + path
    sec_end = s.find("</section>", start)
    assert sec_end != -1
    end = s.rfind(END_MARK, start, sec_end)
    assert end != -1, "block end not found"
    end += len(END_MARK)
    old = s[start:end]
    n_old = old.count('<!-- wp:column {"verticalAlignment":"stretch"} -->')
    assert n_old == 2, "expected 2 columns, found %d in %s" % (n_old, path)
    new = build(kind)
    s2 = s[:start] + new + s[end:]
    # 结构断言
    assert s2.count('<!-- wp:column {"verticalAlignment":"stretch"} -->') == s.count('<!-- wp:column {"verticalAlignment":"stretch"} -->') + 2
    nt = 0
    for t, _, _ in CARDS:
        nt += s2.count("<h3 class=\"wp-block-heading\">%s</h3>" % t)
    assert nt == len(CARDS), "title count %d" % nt
    io.open(path, "w", encoding="utf-8", newline="").write(s2)
    print("OK %s  block %d -> %d chars" % (os.path.basename(path), len(old), len(new)))


patch(HOME, "home", "OEM &amp; ODM Services")
patch(SERV, "serv", "Choose Your Path")

# services: section 加 sf-oem
s = io.open(SERV, encoding="utf-8").read()
OLD_SEC = '<!-- wp:group {"tagName":"section","backgroundColor":"bg-light","layout":{"type":"constrained"},"style":{"spacing":{"padding":{"top":"var:preset|spacing|80","bottom":"var:preset|spacing|80"}}}} -->\n<section class="wp-block-group has-bg-light-background-color has-background" style="padding-top:var(--wp--preset--spacing--80);padding-bottom:var(--wp--preset--spacing--80)">'
NEW_SEC = '<!-- wp:group {"tagName":"section","backgroundColor":"bg-light","className":"sf-oem","layout":{"type":"constrained"},"style":{"spacing":{"padding":{"top":"var:preset|spacing|80","bottom":"var:preset|spacing|80"}}}} -->\n<section class="wp-block-group sf-oem has-bg-light-background-color has-background" style="padding-top:var(--wp--preset--spacing--80);padding-bottom:var(--wp--preset--spacing--80)">'
assert s.count(OLD_SEC) == 1, "services sf-oem section count=%d" % s.count(OLD_SEC)
s = s.replace(OLD_SEC, NEW_SEC, 1)
assert 'sf-oem' in s
io.open(SERV, "w", encoding="utf-8", newline="").write(s)
print("OK page-services.html sf-oem class added")

#!/usr/bin/env python3
"""
批次 1 / 阶段 1 —— 8 个剂型页模板改写
  ① Hero 三层按钮（主 Build Custom Formula → #configurator / 次 Browse Standard
     Formulas → #formulas / 三 Request a Quote 文字链 → #inquiry-form，
     Download Catalog 死链移除）
  ② section.sf-formulas 加固定锚点 id="formulas"（wp:group 注释同步加 anchor）
  ③ Hero 之后新增「参数速览表」区块（5 字段：Unit size / Pack options /
     Shelf life / MOQ / Lead time；表头品牌绿；无 H2 以免扰动 TOC 的 sf-sec-N）
  ④ MOQ 措辞统一：liquids / fish-oil / dental-chews 补
     "New brands can start with small trial orders."

只改模板文件；CSS / JS / functions.php 不在此脚本内。
数据全部取自各页自身的 FAQ 首问与 Standard Specs 原文，无新编造。
"""
import re, sys, os, hashlib

TPL = "/Users/meng/WorkBuddy/sinofresh外贸网站建设/sinofresh-theme/templates"

PAGES = ['soft-chews', 'tablets', 'powders', 'pastes',
         'drops', 'liquids', 'fish-oil', 'dental-chews']

EN, EM = '\u2013', '\u2014'   # en dash / em dash

LEAD = f"7{EN}15 working days after packaging ready"

DATA = {
    'soft-chews':   dict(unit='2 g/piece',               pack='60/90/120 per bottle',        life='18 months',      moq='from 500\u20131,000 units'),
    'tablets':      dict(unit='1 g/tablet',              pack='60/120/180 per bottle',       life='24 months',      moq='from 1,000 units'),
    'powders':      dict(unit='4/8/16 oz jar',           pack=EM,                            life=f'18{EN}24 months', moq='from 500 units'),
    'pastes':       dict(unit='50/60/100/120 g tube',    pack=EM,                            life='24 months',      moq='from 500 units'),
    'drops':        dict(unit='30/50 ml dropper bottle', pack=EM,                            life='24 months',      moq='from 500 units'),
    'liquids':      dict(unit='8/16/32 oz pump bottle',  pack=EM,                            life='24 months',      moq='from 500 units'),
    'fish-oil':     dict(unit='8/16/32 oz pump bottle',  pack=EM,                            life='24 months',      moq='from 1,000 units'),
    'dental-chews': dict(unit=f'15{EN}20 g/piece',       pack='7/14/28 or 14/28/56 per bag', life='18 months',      moq='from 1,000 units'),
}

TRIAL = " New brands can start with small trial orders."

# ---------------------------------------------------------------- 旧块（8 页逐字节相同）
OLD_BUTTONS = '''<!-- wp:buttons {"style":{"spacing":{"margin":{"top":"var:preset|spacing|40"}}}} -->
<div class="wp-block-buttons" style="margin-top:var(--wp--preset--spacing--40)">
<!-- wp:button {"backgroundColor":"cta","textColor":"card-white"} -->
<div class="wp-block-button"><a class="wp-block-button__link has-card-white-color has-cta-background-color has-text-color has-background wp-element-button" href="#inquiry-form">Request a Quote</a></div>
<!-- /wp:button -->
<!-- wp:button {"textColor":"card-white","className":"is-style-outline"} -->
<!-- TODO: 指向 PDF Catalog，等目录文件就绪 -->
<div class="wp-block-button is-style-outline"><a class="wp-block-button__link has-card-white-color has-text-color wp-element-button" href="#">Download Catalog</a></div>
<!-- /wp:button -->
</div>
<!-- /wp:buttons -->'''

NEW_BUTTONS = '''<!-- wp:buttons {"style":{"spacing":{"margin":{"top":"var:preset|spacing|40"}}}} -->
<div class="wp-block-buttons" style="margin-top:var(--wp--preset--spacing--40)">
<!-- wp:button {"backgroundColor":"cta","textColor":"card-white"} -->
<div class="wp-block-button"><a class="wp-block-button__link has-card-white-color has-cta-background-color has-text-color has-background wp-element-button" href="#configurator">Build Custom Formula</a></div>
<!-- /wp:button -->
<!-- wp:button {"textColor":"card-white","className":"is-style-outline"} -->
<div class="wp-block-button is-style-outline"><a class="wp-block-button__link has-card-white-color has-text-color wp-element-button" href="#formulas">Browse Standard Formulas</a></div>
<!-- /wp:button -->
<!-- wp:button {"textColor":"card-white","className":"sf-hero-textlink"} -->
<div class="wp-block-button sf-hero-textlink"><a class="wp-block-button__link has-card-white-color has-text-color wp-element-button" href="#inquiry-form">Request a Quote</a></div>
<!-- /wp:button -->
</div>
<!-- /wp:buttons -->'''

OLD_FM = '<!-- wp:group {"tagName":"section","className":"sf-formulas","layout":{"type":"constrained"},"style":{"spacing":{"padding":{"top":"var:preset|spacing|80","bottom":"var:preset|spacing|80"}}}} -->\n<section class="wp-block-group sf-formulas"'

NEW_FM = '<!-- wp:group {"tagName":"section","anchor":"formulas","className":"sf-formulas","layout":{"type":"constrained"},"style":{"spacing":{"padding":{"top":"var:preset|spacing|80","bottom":"var:preset|spacing|80"}}}} -->\n<section id="formulas" class="wp-block-group sf-formulas"'


def spec_table(slug):
    d = DATA[slug]
    fields = [('Unit size', d['unit']), ('Pack options', d['pack']),
              ('Shelf life', d['life']), ('MOQ', d['moq']), ('Lead time', LEAD)]
    head = '\n'.join('<th scope="col">%s</th>' % k for k, _ in fields)
    body = '\n'.join('<td data-label="%s">%s</td>' % (k, v) for k, v in fields)
    return '''<!-- wp:group {"tagName":"section","className":"sf-spectable","layout":{"type":"constrained"},"style":{"spacing":{"padding":{"top":"var:preset|spacing|60","bottom":"var:preset|spacing|60"}}}} -->
<section class="wp-block-group sf-spectable" style="padding-top:var(--wp--preset--spacing--60);padding-bottom:var(--wp--preset--spacing--60)">
<!-- wp:html -->
<table class="sf-spectable__table">
<caption class="sf-spectable__caption">Typical specifications</caption>
<thead>
<tr>
%s
</tr>
</thead>
<tbody>
<tr>
%s
</tr>
</tbody>
</table>
<!-- /wp:html -->
</section>
<!-- /wp:group -->
''' % (head, body)


def patch(slug):
    path = os.path.join(TPL, 'page-%s.html' % slug)
    src = open(path, encoding='utf-8').read()
    log = []

    # ① 按钮
    n = src.count(OLD_BUTTONS)
    assert n == 1, '%s: OLD_BUTTONS 命中 %d 次（应为 1）' % (slug, n)
    src = src.replace(OLD_BUTTONS, NEW_BUTTONS)
    log.append('① 按钮三层')

    # ② + ③ formulas 锚点 & 速览表（一次性：速览表插在 formulas 块注释之前）
    n = src.count(OLD_FM)
    assert n == 1, '%s: OLD_FM 命中 %d 次（应为 1）' % (slug, n)
    src = src.replace(OLD_FM, spec_table(slug) + '\n' + NEW_FM)
    log.append('② id=formulas')
    log.append('③ 速览表')

    # ④ MOQ 措辞
    if slug in ('liquids', 'fish-oil', 'dental-chews'):
        amt = '1,000' if slug in ('fish-oil', 'dental-chews') else '500'
        old_moq = ('<p class="has-text-secondary-color has-text-color">'
                   'Standard formulas start from %s units.</p>' % amt)
        n = src.count(old_moq)
        assert n == 1, '%s: MOQ 段落命中 %d 次（应为 1）' % (slug, n)
        src = src.replace(old_moq, old_moq[:-4] + TRIAL + '</p>')
        log.append('④ MOQ 补句')

    open(path, 'w', encoding='utf-8').write(src)
    return log


def main():
    ok = True
    for slug in PAGES:
        log = patch(slug)
        p = os.path.join(TPL, 'page-%s.html' % slug)
        h = open(p, encoding='utf-8').read()
        # 断言
        a = []
        a.append(('按钮 #configurator', h.count('href="#configurator"') >= 1))
        a.append(('按钮 #formulas', h.count('href="#formulas"') >= 1))
        a.append(('按钮 #inquiry-form', h.count('href="#inquiry-form"') >= 1))
        a.append(('无 href="#" 死链', ' href="#">' not in h))
        a.append(('无 Download Catalog', 'Download Catalog' not in h))
        a.append(('id="formulas"', h.count('id="formulas"') == 1))
        a.append(('sf-spectable', h.count('sf-spectable__table') == 1))
        a.append(('5 个字段', h.count('<th scope="col">') == 5))
        a.append(('5 个 data-label', h.count('data-label="') == 5))
        bad = [k for k, v in a if not v]
        status = '✅' if not bad else '❌ ' + ','.join(bad)
        if bad:
            ok = False
        print('%-14s %-28s %s  %s' % (slug, ' '.join(log), status,
                                      hashlib.md5(h.encode()).hexdigest()[:12]))
    print()
    print('阶段 1 模板改写：', 'ALL PASS' if ok else '★存在失败★')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())

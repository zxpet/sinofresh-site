#!/usr/bin/env python3
"""Push the Soft Chews template optimisation to the other dosage pages.

Generic transform driven by per-page tip maps. Run: python3 tools/batch1_transform.py tablets powders pastes
"""
import re
import sys

TPL = 'sinofresh-theme/templates/page-{slug}.html'

TIPS = {
    'tablets': {
        'shape': 'Round and Oval are the most common for tablets; Bone shapes work well for chewable variants.',
        'color': 'White and beige read as clean and clinical on retail shelves.',
        'flavor': 'Chicken and liver are the top flavors for dog tablets.',
        'functions': 'Joint and multivitamin lead tablet requests from US and EU brands.',
        'weight': '500mg and 750mg are the most common tablet weights for daily supplements.',
        'packaging': 'Plastic bottles with desiccant are the standard for tablet supplements.',
    },
    'powders': {
        'appearance': 'Fine Powder is the most versatile; Granules work well for larger dogs.',
        'color': 'Light, natural tones signal clean-label recipes to buyers.',
        'flavor': 'Chicken and bacon are the most popular powder flavors.',
        'functions': 'Digestive (probiotic) and joint powders are the fastest-growing segments.',
        'serving_size': '2g scoops are the industry standard for probiotic powders.',
        'packaging': 'Stand-up pouches with dosing scoops are the standard for powders.',
    },
    'pastes': {
        'texture': 'Smooth Paste is most common for hairball formulas; Squeezable Gel works better for cats.',
        'color': 'Light creamy tones are the norm for oral pastes.',
        'flavor': 'Malt and chicken are proven winners for cat pastes.',
        'functions': 'Hairball and skin &amp; coat formulas lead the paste category.',
        'tube_weight': '75g is the standard size for retail; 30-50g works well for trial sizes.',
        'packaging': 'Syringe tubes with long nozzles keep dosing clean and precise.',
    },
}


def section_span(s, start_marker, end_marker=None):
    """(start, end) char span of a section that starts at start_marker and ends
    before end_marker (or at the close of its outer wp:group)."""
    start = s.index(start_marker)
    if end_marker:
        end = s.index(end_marker, start)
    else:
        m = re.compile(r'</section>\n<!-- /wp:group -->', re.S).search(s, start)
        end = m.end()
    return start, end


def spec_band(spec_rows, page_label):
    rows = '\n'.join(
        f'\t<div class="sf-spec-row"><span class="sf-spec-term">{t}</span><span class="sf-spec-value">{v}</span></div>'
        for t, v in spec_rows)
    return f'''<!-- Block 3: Specifications · Formula Options · Packaging Options (merged three-column) -->
<!-- wp:group {{"tagName":"section","backgroundColor":"bg-light","layout":{{"type":"constrained"}},"style":{{"spacing":{{"padding":{{"top":"48px","bottom":"48px"}}}}}}}} -->
<section class="wp-block-group has-bg-light-background-color has-background" style="padding-top:48px;padding-bottom:48px">
<!-- wp:columns {{"className":"sf-triple"}} -->
<div class="wp-block-columns sf-triple">
<!-- wp:column -->
<div class="wp-block-column">
<!-- wp:heading {{"level":3}} -->
<h3 class="wp-block-heading">Specifications</h3>
<!-- /wp:heading -->
<!-- wp:html -->
<div class="sf-spec-list">
%%ROWS%%
</div>
<!-- /wp:html -->
</div>
<!-- /wp:column -->
<!-- wp:column -->
<div class="wp-block-column">
<!-- wp:heading {{"level":3}} -->
<h3 class="wp-block-heading">Formula Options</h3>
<!-- /wp:heading -->
<!-- wp:list {{"className":"sf-triple__list","style":{{"typography":{{"fontSize":"15px","lineHeight":"1.7"}},"spacing":{{"margin":{{"top":"16px"}}}}}}}} -->
<ul class="sf-triple__list" style="margin-top:16px;font-size:15px;line-height:1.7">
{{formula_items}}
</ul>
<!-- /wp:list -->
</div>
<!-- /wp:column -->
<!-- wp:column -->
<div class="wp-block-column">
<!-- wp:heading {{"level":3}} -->
<h3 class="wp-block-heading">Packaging Options</h3>
<!-- /wp:heading -->
<!-- wp:list {{"className":"sf-triple__list","style":{{"typography":{{"fontSize":"15px","lineHeight":"1.7"}},"spacing":{{"margin":{{"top":"16px"}}}}}}}} -->
<ul class="sf-triple__list" style="margin-top:16px;font-size:15px;line-height:1.7">
{{packaging_items}}
</ul>
<!-- /wp:list -->
</div>
<!-- /wp:column -->
</div>
<!-- /wp:columns -->
</section>
<!-- /wp:group -->
'''.replace('{formula_items}', '{formula_items}')  # keep placeholders; filled by caller


def transform(slug):
    tips = TIPS[slug]
    path = TPL.format(slug=slug)
    s = open(path, encoding='utf-8').read()
    orig_len = len(s)
    report = []

    # ---------- 1. HERO ----------
    hero_re = re.compile(
        r'<!-- wp:column \{"verticalAlignment":"center"\} -->\n'
        r'<div class="wp-block-column is-vertically-aligned-center">\n'
        r'<!-- wp:group \{"backgroundColor":"card-white","layout":\{"type":"flex".*?'
        r'<!-- /wp:column -->', re.S)
    m = hero_re.search(s)
    assert m, 'hero column not found'
    img = re.search(r'<img src="([^"]+)" alt="([^"]+)"', m.group(0))
    src, alt = img.group(1), img.group(2)
    new_hero = f'''<!-- wp:column {{"verticalAlignment":"center"}} -->
<div class="wp-block-column is-vertically-aligned-center">
<!-- wp:group {{"className":"sf-product-hero-image","backgroundColor":"card-white","layout":{{"type":"flex","justifyContent":"center","verticalAlignment":"center","orientation":"vertical"}},"style":{{"border":{{"radius":"12px"}}}}}} -->
<div class="wp-block-group sf-product-hero-image has-card-white-background-color has-background" style="border-radius:12px">
<!-- wp:image {{"align":"center"}} -->
<figure class="wp-block-image aligncenter"><img src="{src}" alt="{alt}" width="800" height="600" loading="lazy"/></figure>
<!-- /wp:image -->
</div>
<!-- /wp:group -->
</div>
<!-- /wp:column -->'''
    s = s[:m.start()] + new_hero + s[m.end():]
    report.append('hero: old padded card -> sf-product-hero-image')

    # ---------- 2. KEY FACTS -> TRIPLE BAND ----------
    # extract spec rows from the old two-column + separator table
    a, b = section_span(s, '<!-- Block 3: Key Facts')
    seg = s[a:b]
    terms = re.findall(r'flex-basis:35%">\s*<!-- wp:paragraph[^>]*-->\s*<p[^>]*>(.*?)</p>', seg, re.S)
    values = re.findall(r'<p class="has-primary-color has-text-color"[^>]*>(.*?)</p>', seg, re.S)
    assert len(terms) == len(values) and len(terms) >= 6, f'spec rows mismatch {len(terms)}/{len(values)}'
    spec_rows = list(zip(terms, values))

    # formula + packaging lists from Blocks 6/7
    fseg_a = s.index('<!-- Block 6: Formula Options -->')
    pseg_b = s.index('<!-- /wp:group -->', s.index('<!-- Block 7: Packaging Options -->'))
    mid = s[fseg_a:]
    f_li = re.findall(r'<li>(.*?)</li>', mid[:mid.index('<!-- Block 7: Packaging Options -->')], re.S)
    p_li = re.findall(r'<li>(.*?)</li>', mid[mid.index('<!-- Block 7: Packaging Options -->'):pseg_b + 18], re.S)
    assert f_li and p_li, 'formula/packaging lists empty'

    band = (TPL_TRIPLE
        .replace('%%ROWS%%', '\n'.join(f'\t<div class="sf-spec-row"><span class="sf-spec-term">{t}</span><span class="sf-spec-value">{v}</span></div>' for t, v in spec_rows))
        .replace('%%FORMULA%%', '\n'.join(f'<!-- wp:list-item -->\n<li>{x}</li>\n<!-- /wp:list-item -->' for x in f_li))
        .replace('%%PACKAGING%%', '\n'.join(f'<!-- wp:list-item -->\n<li>{x}</li>\n<!-- /wp:list-item -->' for x in p_li)))
    # replace Key Facts section with the band
    s = s[:a] + band + s[b:]
    # delete Blocks 6+7 (their offsets shifted; re-locate)
    a6 = s.index('<!-- Block 6: Formula Options -->')
    b7end = re.compile(r'</section>\n<!-- /wp:group -->\n?').search(s, s.index('<!-- Block 7: Packaging Options -->')).end()
    s = s[:a6] + s[b7end:]
    report.append(f'triple band: {len(spec_rows)} spec rows, {len(f_li)} formula + {len(p_li)} packaging items; Blocks 6/7 removed')

    # ---------- 3. CONFIGURATOR ----------
    ca = s.index('<div class="configurator">')
    _m = re.compile(r'</div>\n<!-- /wp:html -->').search(s, ca)
    cb = _m.end()
    cfg = s[ca:cb]
    n_multi = cfg.count('data-multi="true"')
    cfg = cfg.replace('data-multi="true"', 'data-multi="false"')
    # wrap h4 in configurator__label + insert tips
    n_tips = 0
    for group, tip in tips.items():
        def _wrap(m):
            global_unused = None
            return (m.group(1)
                    + '<div class="configurator__label">\n'
                    + ' ' * 8 + '<h4>' + m.group(2) + '</h4>\n'
                    + ' ' * 8 + f'<p class="configurator__tip">{tip}</p>\n'
                    + ' ' * 6 + '</div>')
        new_cfg, n = re.subn(rf'(data-group="{group}" data-multi="false">\s*)<h4>(.*?)</h4>', _wrap, cfg, count=1)
        assert n == 1, f'tip group {group} not found'
        cfg = new_cfg
        n_tips += 1
    n_groups = len(re.findall(r'data-group="[a-z_]+" data-multi', cfg))
    # progress line after the summary h3
    cfg = cfg.replace('<h3>Your Configuration</h3>',
                      f'<h3>Your Configuration</h3>\n      <div class="configurator__progress" aria-live="polite">0 of {n_groups} selected</div>', 1)
    # actions + note + mobilebar at the end
    old_end = '''<button type="button" class="configurator__submit">Submit This Configuration</button>
    </aside>
  </div>
</div>'''
    new_end = '''<button type="button" class="configurator__submit">Submit This Configuration</button>
      <div class="configurator__actions">
        <button type="button" class="configurator__reset">Reset</button>
        <button type="button" class="configurator__copy" aria-label="Copy configuration summary"><span class="configurator__copy-label">Copy</span></button>
      </div>
      <p class="configurator__note">Need multiple colors, flavors, or specifications for the same product? Describe in Notes below in the quote form.</p>
    </aside>
  </div>
  <div class="configurator__mobilebar">
    <button type="button" class="configurator__submit configurator__submit--bar">Submit This Configuration</button>
  </div>
</div>'''
    assert old_end in cfg, 'configurator end pattern not found'
    cfg = cfg.replace(old_end, new_end, 1)
    s = s[:ca] + cfg + s[cb:]
    report.append(f'configurator: {n_multi} multi->single, {n_tips} tips, {n_groups} groups, progress/reset/copy/mobilebar added')

    # ---------- 4. HOW WE WORK ----------
    hw_a = s.index('<!-- Block 9: How We Work -->')
    hw_end = s.index('<!-- Block 10: FAQ -->')
    hw = s[hw_a:hw_end]
    hw = hw.replace('<!-- wp:columns {"style":{"spacing":{"margin":{"top":"var:preset|spacing|60"}}}} -->\n<div class="wp-block-columns" style="margin-top:var(--wp--preset--spacing--60)">',
                    '<!-- wp:columns {"className":"sf-panel sf-panel--4 sf-panel--bare","style":{"spacing":{"margin":{"top":"32px"}}}} -->\n<div class="wp-block-columns sf-panel sf-panel--4 sf-panel--bare" style="margin-top:32px">')
    hw = hw.replace('<!-- wp:columns {"style":{"spacing":{"margin":{"top":"var:preset|spacing|40"}}}} -->\n<div class="wp-block-columns" style="margin-top:var(--wp--preset--spacing--40)">',
                    '<!-- wp:columns {"className":"sf-panel sf-panel--4 sf-panel--bare"} -->\n<div class="wp-block-columns sf-panel sf-panel--4 sf-panel--bare">')
    old_cell = '''<!-- wp:group {"style":{"border":{"top":{"color":"var:preset|color|accent","width":"2px"}},"spacing":{"padding":{"top":"var:preset|spacing|20"}}},"layout":{"type":"constrained"}} -->
<div class="wp-block-group has-top-border-color has-top-border" style="border-top-color:var(--wp--preset--color--accent);border-top-width:2px;padding-top:var(--wp--preset--spacing--20)">'''
    new_cell = '''<!-- wp:group {"style":{"border":{"top":{"color":"var:preset|color|accent","width":"2px"}}},"layout":{"type":"constrained"},"className":"sf-cell"} --><div class="wp-block-group has-top-border-color has-top-border sf-cell" style="border-top-color:var(--wp--preset--color--accent);border-top-width:2px">'''
    n_cells = hw.count(old_cell)
    hw = hw.replace(old_cell, new_cell)
    s = s[:hw_a] + hw + s[hw_end:]
    report.append(f'how we work: panel/bare classes, {n_cells} sf-cells')

    # ---------- 5. FAQ ----------
    fq_a = s.index('<!-- Block 10: FAQ -->')
    fq_end = s.index('<!-- Block 11: Related')
    fq = s[fq_a:fq_end]
    fq = fq.replace('<!-- wp:group {"className":"sf-faq","layout":{"type":"constrained","contentSize":"800px"}} -->',
                    '<!-- wp:group {"className":"sf-faq","layout":{"type":"constrained"}} -->')
    fq = re.sub(r'(<div class="wp-block-group sf-faq")([^>]*style="[^"]*")([^>]*>)', r'\1\3', fq)
    fq = fq.replace('<!-- wp:heading {"textAlign":"center"} -->\n<h2 class="has-text-align-center wp-block-heading">Frequently Asked Questions</h2>',
                    '<!-- wp:heading -->\n<h2 class="wp-block-heading">Frequently Asked Questions</h2>')
    s = s[:fq_a] + fq + s[fq_end:]
    report.append('faq: contentSize removed, H2 left-aligned')

    # ---------- 6. RELATED ----------
    ra = s.index('<!-- Block 11: Related')
    rend = s.index('<!-- Block 12: CTA')
    rel = s[ra:rend]
    rel = rel.replace('<!-- wp:columns {"style":{"spacing":{"margin":{"top":"var:preset|spacing|50"}}}} -->\n<div class="wp-block-columns" style="margin-top:var(--wp--preset--spacing--50)">',
                      '<!-- wp:columns {"className":"sf-dosage-grid sf-related-grid","style":{"spacing":{"margin":{"top":"var:preset|spacing|50"}}}} -->\n<div class="wp-block-columns sf-dosage-grid sf-related-grid" style="margin-top:var(--wp--preset--spacing--50)">')
    rel = rel.replace('<!-- wp:columns {"style":{"spacing":{"margin":{"top":"var:preset|spacing|40"}}}} -->\n<div class="wp-block-columns" style="margin-top:var(--wp--preset--spacing--40)">',
                      '<!-- wp:columns {"className":"sf-dosage-grid sf-related-grid","style":{"spacing":{"margin":{"top":"var:preset|spacing|40"}}}} -->\n<div class="wp-block-columns sf-dosage-grid sf-related-grid" style="margin-top:var(--wp--preset--spacing--40)">')
    card_re = re.compile(
        r'<!-- wp:group \{"backgroundColor":"card-white","layout":\{"type":"constrained"\},"style":\{"border":\{"radius":"8px".*?'
        r'(?=</div>\n<!-- /wp:column -->)', re.S)
    def tile(m):
        c = m.group(0)
        img = re.search(r'<img src="([^"]+)" alt="([^"]+)"', c)
        title = re.search(r'<h3[^>]*>([^<]+)</h3>', c)
        desc = re.search(r'<p class="has-text-secondary-color has-text-color" style="font-size:14px">(.*?)</p>', c, re.S)
        link = re.search(r'href="([^"]+)"', c)
        assert img and title and desc and link, 'card parse failed'
        return f'''<!-- wp:group {{"layout":{{"type":"constrained"}},"className":"sf-tile"}} --><div class="wp-block-group sf-tile">
<!-- wp:image {{"align":"center","className":"sf-tile__media"}} -->
<figure class="wp-block-image aligncenter sf-tile__media"><img src="{img.group(1)}" alt="{img.group(2)}" width="800" height="600" loading="lazy" decoding="async"/></figure>
<!-- /wp:image -->
<!-- wp:heading {{"level":3}} -->
<h3 class="wp-block-heading">{title.group(1)}</h3>
<!-- /wp:heading -->
<!-- wp:paragraph {{"textColor":"text-secondary","style":{{"typography":{{"fontSize":"14px"}}}}}} -->
<p class="has-text-secondary-color has-text-color" style="font-size:14px">{desc.group(1)}</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph {{"style":{{"typography":{{"fontSize":"14px","fontWeight":"600"}}}}}} -->
<p style="font-size:14px;font-weight:600"><a href="{link.group(1)}" rel="noopener">Learn More &rarr;</a></p>
<!-- /wp:paragraph -->
</div>
<!-- /wp:group -->'''
    rel, n_cards = card_re.subn(tile, rel)
    s = s[:ra] + rel + s[rend:]
    report.append(f'related: {n_cards} cards -> sf-tile')

    open(path, 'w', encoding='utf-8').write(s)
    print(f'== {slug} == ({orig_len} -> {len(s)} chars, {orig_len - len(s):+d})')
    for r in report:
        print('  -', r)


TPL_TRIPLE = '''<!-- Block 3: Specifications · Formula Options · Packaging Options (merged three-column) -->
<!-- wp:group {"tagName":"section","backgroundColor":"bg-light","layout":{"type":"constrained"},"style":{"spacing":{"padding":{"top":"48px","bottom":"48px"}}}} -->
<section class="wp-block-group has-bg-light-background-color has-background" style="padding-top:48px;padding-bottom:48px">
<!-- wp:columns {"className":"sf-triple"} -->
<div class="wp-block-columns sf-triple">
<!-- wp:column -->
<div class="wp-block-column">
<!-- wp:heading {"level":3} -->
<h3 class="wp-block-heading">Specifications</h3>
<!-- /wp:heading -->
<!-- wp:html -->
<div class="sf-spec-list">
%%ROWS%%
</div>
<!-- /wp:html -->
</div>
<!-- /wp:column -->
<!-- wp:column -->
<div class="wp-block-column">
<!-- wp:heading {"level":3} -->
<h3 class="wp-block-heading">Formula Options</h3>
<!-- /wp:heading -->
<!-- wp:list {"className":"sf-triple__list","style":{"typography":{"fontSize":"15px","lineHeight":"1.7"},"spacing":{"margin":{"top":"16px"}}}} -->
<ul class="sf-triple__list" style="margin-top:16px;font-size:15px;line-height:1.7">
%%FORMULA%%
</ul>
<!-- /wp:list -->
</div>
<!-- /wp:column -->
<!-- wp:column -->
<div class="wp-block-column">
<!-- wp:heading {"level":3} -->
<h3 class="wp-block-heading">Packaging Options</h3>
<!-- /wp:heading -->
<!-- wp:list {"className":"sf-triple__list","style":{"typography":{"fontSize":"15px","lineHeight":"1.7"},"spacing":{"margin":{"top":"16px"}}}} -->
<ul class="sf-triple__list" style="margin-top:16px;font-size:15px;line-height:1.7">
%%PACKAGING%%
</ul>
<!-- /wp:list -->
</div>
<!-- /wp:column -->
</div>
<!-- /wp:columns -->
</section>
<!-- /wp:group -->
'''


if __name__ == '__main__':
    for slug in sys.argv[1:]:
        transform(slug)

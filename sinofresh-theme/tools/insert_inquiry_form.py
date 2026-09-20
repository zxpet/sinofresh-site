#!/usr/bin/env python3
"""Insert Inquiry Form section (layout-only placeholder) into front-page.html before the footer."""
import sys

PATH = "/Users/meng/WorkBuddy/sinofresh外贸网站建设/sinofresh-theme/templates/front-page.html"

BLOCK = '''<!-- wp:group {"tagName":"section","backgroundColor":"primary","layout":{"type":"constrained"},"style":{"spacing":{"padding":{"top":"var:preset|spacing|80","bottom":"var:preset|spacing|80"}}}} -->
<section class="wp-block-group has-primary-background-color has-background" style="padding-top:var(--wp--preset--spacing--80);padding-bottom:var(--wp--preset--spacing--80)">
<!-- wp:columns -->
<div class="wp-block-columns">
<!-- wp:column {"verticalAlignment":"center"} -->
<div class="wp-block-column is-vertically-aligned-center">
<!-- wp:heading {"textColor":"card-white"} -->
<h2 class="wp-block-heading has-card-white-color has-text-color">Ready to Launch Your Product?</h2>
<!-- /wp:heading -->
<!-- wp:paragraph {"style":{"typography":{"fontSize":"16px"}},"textColor":"card-white"} -->
<p class="has-card-white-color has-text-color" style="font-size:16px">Send us your requirements and we will respond within 24 hours.</p>
<!-- /wp:paragraph -->
<!-- wp:group {"style":{"spacing":{"margin":{"top":"var:preset|spacing|40"}}},"layout":{"type":"constrained"}} -->
<div class="wp-block-group" style="margin-top:var(--wp--preset--spacing--40)">
<!-- wp:group {"layout":{"type":"flex","justifyContent":"left","verticalAlignment":"top"}} -->
<div class="wp-block-group">
<!-- wp:paragraph {"style":{"typography":{"fontWeight":"700"}},"textColor":"accent"} -->
<p class="has-accent-color has-text-color" style="font-weight:700">✓</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph {"textColor":"card-white"} -->
<p class="has-card-white-color has-text-color">24-hour response on business days</p>
<!-- /wp:paragraph -->
</div>
<!-- /wp:group -->
<!-- wp:group {"layout":{"type":"flex","justifyContent":"left","verticalAlignment":"top"}} -->
<div class="wp-block-group">
<!-- wp:paragraph {"style":{"typography":{"fontWeight":"700"}},"textColor":"accent"} -->
<p class="has-accent-color has-text-color" style="font-weight:700">✓</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph {"textColor":"card-white"} -->
<p class="has-card-white-color has-text-color">Formula and branding stay confidential</p>
<!-- /wp:paragraph -->
</div>
<!-- /wp:group -->
<!-- wp:group {"layout":{"type":"flex","justifyContent":"left","verticalAlignment":"top"}} -->
<div class="wp-block-group">
<!-- wp:paragraph {"style":{"typography":{"fontWeight":"700"}},"textColor":"accent"} -->
<p class="has-accent-color has-text-color" style="font-weight:700">✓</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph {"textColor":"card-white"} -->
<p class="has-card-white-color has-text-color">Small trial orders welcome</p>
<!-- /wp:paragraph -->
</div>
<!-- /wp:group -->
</div>
<!-- /wp:group -->
</div>
<!-- /wp:column -->
<!-- wp:column {"verticalAlignment":"center"} -->
<div class="wp-block-column is-vertically-aligned-center">
<!-- wp:group {"backgroundColor":"card-white","style":{"border":{"radius":"8px"},"spacing":{"padding":{"top":"var:preset|spacing|40","bottom":"var:preset|spacing|40","left":"var:preset|spacing|40","right":"var:preset|spacing|40"}}}} -->
<div class="wp-block-group has-card-white-background-color has-background" style="border-radius:8px;padding-top:var(--wp--preset--spacing--40);padding-right:var(--wp--preset--spacing--40);padding-bottom:var(--wp--preset--spacing--40);padding-left:var(--wp--preset--spacing--40)">
<!-- wp:group {"style":{"border":{"radius":"8px","color":"var:preset|color|border-light","width":"1px"},"dimensions":{"minHeight":"400px"}},"layout":{"type":"flex","justifyContent":"center","verticalAlignment":"center","orientation":"vertical"}} -->
<div class="wp-block-group has-border-color has-border-light-border-color" style="border-radius:8px;border-width:1px;min-height:400px">
<!-- wp:paragraph {"align":"center","style":{"typography":{"fontSize":"16px"}},"textColor":"text-primary"} -->
<p class="has-text-align-center has-text-primary-color has-text-color" style="font-size:16px">表单嵌入区 / Form goes here</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph {"align":"center","style":{"typography":{"fontSize":"12px"}},"textColor":"text-secondary"} -->
<p class="has-text-align-center has-text-secondary-color has-text-color" style="font-size:12px">下一步安装 Gravity Forms 后嵌入实际表单</p>
<!-- /wp:paragraph -->
</div>
<!-- /wp:group -->
</div>
<!-- /wp:group -->
</div>
<!-- /wp:column -->
</div>
<!-- /wp:columns -->
</section>
<!-- /wp:group -->

'''

with open(PATH, "r", encoding="utf-8") as f:
    lines = f.readlines()

footer_idx = [i for i, l in enumerate(lines) if l.startswith('<!-- wp:group {"tagName":"footer"')]
assert len(footer_idx) == 1, f"expected exactly 1 footer comment, got {len(footer_idx)}"
fi = footer_idx[0]
assert lines[fi - 1].strip() == "", f"line before footer is not blank: {lines[fi-1]!r}"

faq_idx = [i for i, l in enumerate(lines) if 'Frequently Asked Questions' in l]
assert len(faq_idx) == 1 and faq_idx[0] < fi, "FAQ section position check failed"

faq_lines = BLOCK.splitlines(keepends=True)
new_lines = lines[:fi] + faq_lines + lines[fi:]

with open(PATH, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

with open(PATH, "r", encoding="utf-8") as f:
    content = f.read()
checks = {
    "H2 title": content.count("Ready to Launch Your Product?"),
    "H2 card-white": content.count('<h2 class="wp-block-heading has-card-white-color has-text-color">Ready to Launch Your Product?</h2>'),
    "subtitle": content.count("Send us your requirements and we will respond within 24 hours."),
    "trust items": sum(content.count(t) for t in ["24-hour response on business days", "Formula and branding stay confidential", "Small trial orders welcome"]),
    "check marks": content.count('style="font-weight:700">✓</p>'),
    "placeholder text": content.count("表单嵌入区 / Form goes here"),
    "placeholder note": content.count("下一步安装 Gravity Forms 后嵌入实际表单"),
    "minHeight 400px": content.count("min-height:400px"),
    "card-white card padding 40": content.count('has-card-white-background-color has-background" style="border-radius:8px;padding-top:var(--wp--preset--spacing--40)'),
    "wp:group balance": content.count("<!-- wp:group ") - content.count("<!-- /wp:group -->"),
    "wp:columns balance": content.count("<!-- wp:columns ") - content.count("<!-- /wp:columns -->"),
    "wp:column balance": content.count("<!-- wp:column ") - content.count("<!-- /wp:column -->"),
    "wp:heading balance": content.count("<!-- wp:heading ") - content.count("<!-- /wp:heading -->"),
    "wp:paragraph balance": content.count("<!-- wp:paragraph ") - content.count("<!-- /wp:paragraph -->"),
    "footer comment": content.count('<!-- wp:group {"tagName":"footer"'),
}
for k, v in checks.items():
    print(f"{k}: {v}")
print("total lines:", len(new_lines))

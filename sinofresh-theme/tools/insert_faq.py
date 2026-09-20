#!/usr/bin/env python3
"""Insert FAQ section into front-page.html before the inline footer (atomic, line-based)."""
import sys

PATH = "/Users/meng/WorkBuddy/sinofresh外贸网站建设/sinofresh-theme/templates/front-page.html"

FAQS = [
    ("What is your MOQ?",
     "From 500 units depending on dosage form. New brands can start with small trial orders."),
    ("How long does sampling take?",
     "3\u20137 working days for standard formulas. Complex formulas may take longer."),
    ("What certifications do you hold?",
     "FDA registration, cGMP, ISO 9001, ISO 22000."),
    ("Do you provide COA for every batch?",
     "Yes. Every batch is tested in our QC laboratory and ships with a COA."),
    ("What payment terms do you offer?",
     "30% deposit, 70% before shipment. T/T and other terms negotiable."),
    ("Can I visit your factory?",
     "Yes. We support both on-site and video factory tours."),
    ("Do you support private label?",
     "Yes. We are 100% OEM/ODM and do not sell our own retail brand."),
    ("Can you handle regulatory documentation for my market?",
     "Yes. We support FDA, EU, and other target market requirements."),
]

def item(q, a):
    return f'''<!-- wp:group {{"layout":{{"type":"flex","justifyContent":"space-between","verticalAlignment":"top"}},"style":{{"spacing":{{"margin":{{"top":"var:preset|spacing|30"}}}}}}}} -->
<div class="wp-block-group" style="margin-top:var(--wp--preset--spacing--30)">
<!-- wp:heading {{"level":3}} -->
<h3 class="wp-block-heading">{q}</h3>
<!-- /wp:heading -->
<!-- wp:paragraph {{"style":{{"typography":{{"fontSize":"24px","fontWeight":"700"}}}},"textColor":"accent"}} -->
<p class="has-accent-color has-text-color" style="font-size:24px;font-weight:700">+</p>
<!-- /wp:paragraph -->
</div>
<!-- /wp:group -->
<!-- wp:paragraph {{"style":{{"typography":{{"fontSize":"14px"}},"spacing":{{"margin":{{"bottom":"var:preset|spacing|30"}}}}}},"textColor":"text-secondary"}} -->
<p class="has-text-secondary-color has-text-color" style="margin-bottom:var(--wp--preset--spacing--30);font-size:14px">{a}</p>
<!-- /wp:paragraph -->'''

def separator():
    return '''<!-- wp:separator {"backgroundColor":"border-light","className":"is-style-wide"} -->
<hr class="wp-block-separator has-border-light-background-color has-background is-style-wide"/>
<!-- /wp:separator -->'''

items = []
for i, (q, a) in enumerate(FAQS):
    items.append(item(q, a))
    if i < len(FAQS) - 1:
        items.append(separator())

BLOCK = f'''<!-- wp:group {{"tagName":"section","backgroundColor":"bg-light","layout":{{"type":"constrained"}},"style":{{"spacing":{{"padding":{{"top":"var:preset|spacing|80","bottom":"var:preset|spacing|80"}}}}}}}} -->
<section class="wp-block-group has-bg-light-background-color has-background" style="padding-top:var(--wp--preset--spacing--80);padding-bottom:var(--wp--preset--spacing--80)">
<!-- wp:heading {{"textAlign":"center"}} -->
<h2 class="wp-block-heading has-text-align-center">Frequently Asked Questions</h2>
<!-- /wp:heading -->
<!-- wp:paragraph {{"align":"center","textColor":"text-secondary"}} -->
<p class="has-text-align-center has-text-secondary-color has-text-color">Answers to the questions we hear most from brand owners and procurement teams.</p>
<!-- /wp:paragraph -->
<!-- wp:group {{"style":{{"spacing":{{"margin":{{"top":"var:preset|spacing|60"}}}}}},"layout":{{"type":"constrained","contentSize":"800px"}}}} -->
<div class="wp-block-group" style="margin-top:var(--wp--preset--spacing--60)">
{chr(10).join(items)}
</div>
<!-- /wp:group -->
</section>
<!-- /wp:group -->

'''

with open(PATH, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Boundary assertion: find footer comment line (must be unique, near end)
footer_idx = [i for i, l in enumerate(lines) if l.startswith('<!-- wp:group {"tagName":"footer"')]
assert len(footer_idx) == 1, f"expected exactly 1 footer comment, got {len(footer_idx)}"
fi = footer_idx[0]
# The line before it should be blank (separator between Blog section and footer)
assert lines[fi - 1].strip() == "", f"line before footer is not blank: {lines[fi-1]!r}"

faq_lines = BLOCK.splitlines(keepends=True)
new_lines = lines[:fi] + faq_lines + lines[fi:]

with open(PATH, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

# Verification
with open(PATH, "r", encoding="utf-8") as f:
    content = f.read()
checks = {
    "H2 FAQ": content.count("Frequently Asked Questions"),
    "section open (bg-light FAQ)": content.count('<section class="wp-block-group has-bg-light-background-color has-background" style="padding-top:var(--wp--preset--spacing--80);padding-bottom:var(--wp--preset--spacing--80)">'),
    "plus signs (accent 24px)": content.count('style="font-size:24px;font-weight:700">+</p>'),
    "separators (border-light wide)": content.count('wp-block-separator has-border-light-background-color has-background is-style-wide'),
    "answers 14px in FAQ": content.count('margin-bottom:var(--wp--preset--spacing--30);font-size:14px'),
    "footer comment": content.count('<!-- wp:group {"tagName":"footer"'),
    "wp:group balance": content.count("<!-- wp:group ") - content.count("<!-- /wp:group -->"),
    "wp:heading balance": content.count("<!-- wp:heading ") - content.count("<!-- /wp:heading -->"),
    "wp:paragraph balance": content.count("<!-- wp:paragraph ") - content.count("<!-- /wp:paragraph -->"),
    "wp:separator balance": content.count("<!-- wp:separator ") - content.count("<!-- /wp:separator -->"),
}
for k, v in checks.items():
    print(f"{k}: {v}")
print("total lines:", len(new_lines))

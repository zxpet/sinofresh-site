#!/usr/bin/env python3
"""Mobile optimisation round 1 — homepage pilot.

Template-side edits (13-task brief, homepage only):
  header.html  : sf-header__cta on the nav CTA group, sf-topbar-wa on the
                 WhatsApp line (so CSS can drop both on phones)
  footer.html  : drop the redundant WhatsApp text line from Contact Us
  front-page   : sf-section--large/medium/xl on every top-level section,
                 sf-certs on the certificate columns, sf-about__cta + a real
                 href on the About button, five redrawn Formulated Clean icons
Nothing is removed from the DOM except the duplicate footer WhatsApp anchor
(the brief asks for it; the same link stays in the social icon row).
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
THEME = ROOT / "sinofresh-theme"

ICONS = {
    "Gluten-Free": (
        '<path d="M12 19.5V5.2"/>'
        '<path d="M9.3 8.3 12 10.5 14.7 8.3"/>'
        '<path d="M9.3 12 12 14.2 14.7 12"/>'
        '<path d="M9.3 15.7 12 17.9 14.7 15.7"/>'
    ),
    "Corn-Free": (
        '<path d="M12 5.2c2.4 0 4 3 4 6.9S14.4 19 12 19s-4-3-4-6.9S9.6 5.2 12 5.2z"/>'
        '<path d="M8.7 9.4h6.6"/><path d="M8.2 12.7h7.6"/><path d="M8.7 16h6.6"/>'
    ),
    "Soy-Free": (
        '<path d="M12 4.6c2.7 0 4.6 3.3 4.6 7.4s-1.9 7.4-4.6 7.4-4.6-3.3-4.6-7.4S9.3 4.6 12 4.6z"/>'
        '<path d="M12 7.4c-1.3 1.3-1.3 8 0 9.3"/>'
    ),
    "No Artificial Flavors": (
        '<path d="M9.6 4.4h4.8"/>'
        '<path d="M10.7 4.4v5.1L6.2 17a2.2 2.2 0 0 0 1.9 3.3h7.8a2.2 2.2 0 0 0 1.9-3.3l-4.5-7.5V4.4"/>'
        '<path d="M8.4 14.6h7.2"/>'
    ),
    "Non-GMO": (
        '<path d="M6.2 19.2C6.2 11.6 11 6.4 18.6 6.4c0 7.6-4.8 12.8-12.4 12.8z"/>'
        '<path d="M6.2 19.2C8.8 14.6 12.6 10.8 17 8.4"/>'
    ),
}
SLASH = '<path d="M5.2 5.2 18.8 18.8"/>'


def svg_for(label: str) -> str:
    body = ICONS[label] + SLASH
    return (
        '<svg class="sf-claim__icon" width="22" height="22" viewBox="0 0 24 24" '
        'fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" '
        'stroke-linejoin="round" aria-hidden="true" focusable="false">' + body + "</svg>"
    )


def patch_header() -> None:
    p = THEME / "parts" / "header.html"
    s = p.read_text()
    assert 'sf-header__cta' not in s
    # nav CTA group -> classed so the phone layout can drop it
    s = s.replace(
        '<!-- wp:buttons -->\n<div class="wp-block-buttons">\n<!-- wp:button -->\n'
        '<div class="wp-block-button"><a class="wp-block-button__link wp-element-button" href="#quote">Get a Quote</a></div>',
        '<!-- wp:buttons {"className":"sf-header__cta"} -->\n'
        '<div class="wp-block-buttons sf-header__cta">\n<!-- wp:button -->\n'
        '<div class="wp-block-button"><a class="wp-block-button__link wp-element-button" href="#quote">Get a Quote</a></div>',
    )
    # WhatsApp line in the top bar
    s = s.replace(
        '<!-- wp:paragraph {"style":{"typography":{"fontSize":"12px"}}} -->\n'
        '\t\t<p style="font-size:12px"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false" style="vertical-align:-2px;margin-right:5px"><path d="M12 3a9 9 0 0 1 9 9 9 9 0 0 1-9 9 9 9 0 0 1-4.6-1.3L3 21l1.4-4.3A9 9 0 0 1 3 12a9 9 0 0 1 9-9z"/>',
        '<!-- wp:paragraph {"className":"sf-topbar-wa","style":{"typography":{"fontSize":"12px"}}} -->\n'
        '\t\t<p class="sf-topbar-wa" style="font-size:12px"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false" style="vertical-align:-2px;margin-right:5px"><path d="M12 3a9 9 0 0 1 9 9 9 9 0 0 1-9 9 9 9 0 0 1-4.6-1.3L3 21l1.4-4.3A9 9 0 0 1 3 12a9 9 0 0 1 9-9z"/>',
    )
    assert 'sf-header__cta' in s and 'sf-topbar-wa' in s, "header patch incomplete"
    p.write_text(s)
    print("header.html  ok")


def patch_footer() -> None:
    p = THEME / "parts" / "footer.html"
    s = p.read_text()
    old = re.search(
        r'<a href="\{\{sf-social:whatsapp\}\}" target="_blank" rel="noopener noreferrer">WhatsApp</a>', s
    )
    assert old, "footer WhatsApp anchor not found"
    s = s.replace(old.group(0), "")
    p.write_text(s)
    print("footer.html  ok  (WhatsApp text line removed)")


SEC_MAP = {"48px": "sf-section sf-section--large", "40px": "sf-section sf-section--medium",
           "56px": "sf-section sf-section--xl"}


def patch_front_page() -> None:
    p = THEME / "templates" / "front-page.html"
    s = p.read_text()

    # --- 1. section classes (block comment + rendered tag) ---------------
    n = 0
    out = []
    lines = s.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r'^<!-- wp:group \{"tagName":"section",(.*) -->$', line)
        if m and i + 1 < len(lines):
            nxt = lines[i + 1]
            pm = re.search(r'"padding":\{"top":"(\d+)px","bottom":"\1px"\}', m.group(1))
            if pm and nxt.startswith("<section "):
                cls = SEC_MAP[pm.group(1) + "px"]
                if '"className"' in m.group(1):
                    comment = re.sub(r'"className":"([^"]*)"', lambda mm: '"className":"%s %s"' % (cls, mm.group(1)), m.group(1))
                else:
                    comment = m.group(1) + ',"className":"%s"' % cls
                lines[i] = '<!-- wp:group {"tagName":"section",%s -->' % comment
                lines[i + 1] = nxt.replace('<section class="wp-block-group ', '<section class="wp-block-group %s ' % cls, 1)
                n += 1
                i += 2
                continue
        i += 1
    s = "\n".join(lines)
    print("front-page   section classes on %d sections" % n)

    # --- 2. certifications columns -> swipe container --------------------
    s, c = re.subn(
        r'<!-- wp:columns \{"style":\{"spacing":\{"margin":\{"top":"var:preset\|spacing\|60"\}\}\}\} -->\n'
        r'<div class="wp-block-columns" style="margin-top:var\(--wp--preset--spacing--60\)">',
        '<!-- wp:columns {"className":"sf-certs","style":{"spacing":{"margin":{"top":"var:preset|spacing|60"}}}} -->\n'
        '<div class="wp-block-columns sf-certs" style="margin-top:var(--wp--preset--spacing--60)">',
        s, count=1)
    assert c == 1, "cert columns not patched"
    print("front-page   sf-certs ok")

    # --- 3. About button: real href + hook class -------------------------
    s, c = re.subn(
        r'<!-- wp:buttons \{"style":\{"spacing":\{"margin":\{"top":"var:preset\|spacing\|40"\}\}\}\} -->\n'
        r'<div class="wp-block-buttons" style="margin-top:var\(--wp--preset--spacing--40\)">\n'
        r'<!-- wp:button -->\n'
        r'<div class="wp-block-button"><a class="wp-block-button__link wp-element-button">Learn More About Us</a></div>',
        '<!-- wp:buttons {"className":"sf-about__cta","style":{"spacing":{"margin":{"top":"var:preset|spacing|40"}}}} -->\n'
        '<div class="wp-block-buttons sf-about__cta" style="margin-top:var(--wp--preset--spacing--40)">\n'
        '<!-- wp:button -->\n'
        '<div class="wp-block-button"><a class="wp-block-button__link wp-element-button" href="/about/">Learn More About Us</a></div>',
        s, count=1)
    assert c == 1, "about button not patched"
    print("front-page   about button href + class ok")

    # --- 4. Formulated Clean icons ---------------------------------------
    for label in ICONS:
        block_pat = re.compile(
            r'(<p class="sf-claim[^"]*"[^>]*>)<svg class="sf-claim__icon".*?</svg>('
            + re.escape(label) + r')</p>', re.S)
        s, c = block_pat.subn(lambda m: m.group(1) + svg_for(label) + m.group(2) + "</p>", s)
        assert c == 1, "icon not replaced for %s (c=%d)" % (label, c)
    print("front-page   5 claim icons redrawn")

    p.write_text(s)


if __name__ == "__main__":
    patch_header()
    patch_footer()
    patch_front_page()
    print("done")

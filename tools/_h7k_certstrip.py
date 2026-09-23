#!/usr/bin/env python3
"""待办18 — rebuild the home certification band as a compact strip.

The six seals keep the SVG *body* they already had (circle + ribbon, byte for
byte) and lose only what a 32px chip cannot use: the 88px box, the two <text>
elements (at 32px the inner "FDA" renders about 4px tall — mush next to the
label that already says it), and role/aria-label, which made every chip
announce "FDA certification seal" immediately followed by "FDA Registered".

The names are read out of the markup being replaced, so the strip cannot
drift from the six credentials that were there before it.

Idempotent: running it twice changes nothing (it refuses when the strip is
already present).
"""
import re
import sys

PATH = 'sinofresh-theme/templates/front-page.html'

src = open(PATH, encoding='utf-8').read()

if 'sf-certstrip' in src:
    print('already migrated — nothing to do')
    sys.exit(0)

# --- the block being replaced: eyebrow, h2, lede paragraph, the card grid ----
#
# Anchored on the GRID, then walked outwards — never on the eyebrow comment.
# The first run of this script anchored on
# `<!-- wp:paragraph {"align":"center","className":"sf-eyebrow"} -->`, which
# the home page writes ten times: it matched the "Partnership" band 114 lines
# higher up and deleted 310 lines of the home page before anyone noticed. The
# grid div is unique in the file, so it is the only safe anchor; the guards
# below make a wrong walk fail loudly instead of writing a shorter page.
grid = src.index('<div class="sf-certgrid" role="list">')
assert src.count('<div class="sf-certgrid" role="list">') == 1, 'grid anchor is not unique'
end = src.index('<!-- /wp:html -->', grid) + len('<!-- /wp:html -->')
open_html = src.rindex('<!-- wp:html -->', 0, grid)
section = src.rindex('<section', 0, open_html)
start = src.index('<!-- wp:paragraph', section)
assert start < open_html < grid < end
old = src[start:end]
assert 30 <= old.count('\n') + 1 <= 60, 'block is %d lines — wrong anchor' % (old.count('\n') + 1)

# the wp:group wrapper line above it carries the section padding in two places
wrapper_open = src.rindex('<!-- wp:group', 0, start)
wrapper_close = src.index('\n', src.index('<section', wrapper_open))
wrapper = src[wrapper_open:wrapper_close]

cards = re.findall(r'<article class="sf-certcard">(.*?)</article>', old, re.S)
names = re.findall(r'<h3 class="sf-certcard__name">(.*?)</h3>', old, re.S)
seals = re.findall(r'<svg class="sf-certcard__seal".*?</svg>', old, re.S)
assert len(cards) == len(names) == len(seals) == 6, (len(cards), len(names), len(seals))

badges = []
for name, seal in zip(names, seals):
    body = seal[seal.index('>') + 1: -len('</svg>')]
    stripped = re.sub(r'<text\b[^>]*>.*?</text>', '', body, flags=re.S)
    assert stripped != body, 'the <text> elements are the point of the strip'
    assert '<text' not in stripped
    assert '<circle' in stripped and '<path' in stripped, 'artwork body must survive'
    icon = ('<svg class="sf-certstrip__icon" width="32" height="32" viewBox="0 0 96 96"'
            ' aria-hidden="true" focusable="false">' + stripped + '</svg>')
    badges.append('\t\t\t<li class="sf-certstrip__badge">%s<span class="sf-certstrip__name">%s</span></li>'
                  % (icon, name))

new_block = ('<!-- wp:html -->\n'
             '<div class="sf-certstrip">\n'
             '<p class="sf-certstrip__lede">Certified to the standards global pet brands trust</p>\n'
             '<ul class="sf-certstrip__row" role="list">\n'
             + '\n'.join(badges) + '\n'
             '</ul>\n'
             '<p class="sf-certstrip__more"><a href="/quality/#certifications">View all certifications &rarr;</a></p>\n'
             '</div>\n'
             '<!-- /wp:html -->')

src = src[:start] + new_block + src[end:]

# --- the section's own padding: 48 -> 32, in BOTH places it is written -------
new_wrapper = (wrapper.replace('"padding":{"top":"48px","bottom":"48px"}', '"padding":{"top":"32px","bottom":"32px"}')
                      .replace('padding-top:48px;padding-bottom:48px', 'padding-top:32px;padding-bottom:32px'))
assert new_wrapper != wrapper, 'wrapper padding not found'
assert '48px' not in new_wrapper, new_wrapper
src = src[:wrapper_open] + new_wrapper + src[wrapper_close:]

open(PATH, 'w', encoding='utf-8').write(src)

print('replaced %d lines with %d' % (old.count('\n') + 1, new_block.count('\n') + 1))
print('badges: %s' % ', '.join(names))
print('padding: 48px -> 32px')

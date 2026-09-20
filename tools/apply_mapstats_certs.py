#!/usr/bin/env python3
"""One-shot, serial, assertion-guarded edit pass:
   A) remove the 4 map-number cards (front-page.html) + dead CSS rule (style.css)
   B) add HACCP + BRC to 5 cert lists (front-page.html x4, parts/footer.html x1)
   D) bump cache-busting version to 2.10.2 (functions.php + style.css header)
Every mutation asserts its anchor first; nothing is written unless all asserts pass.
"""
import io, sys, os

ROOT = '/Users/meng/WorkBuddy/sinofresh外贸网站建设/sinofresh-theme'
FP = os.path.join(ROOT, 'templates/front-page.html')
FT = os.path.join(ROOT, 'parts/footer.html')
CSS = os.path.join(ROOT, 'style.css')
FUN = os.path.join(ROOT, 'functions.php')

log = []


def read(p):
    with io.open(p, encoding='utf-8') as f:
        return f.read()


def write(p, s):
    with io.open(p, 'w', encoding='utf-8') as f:
        f.write(s)


# ---------------------------------------------------------------- A1: delete cards
src = read(FP)
lines = src.split('\n')
orig_lines = len(lines)

A_START = '<!-- wp:columns {"className":"sf-panel sf-panel--4 sf-map-stats"'
A_OPEN = '<div class="wp-block-columns sf-panel sf-panel--4 sf-map-stats" style="margin-top:24px">'
A_END = '<!-- /wp:columns -->'
PREV = '<!-- /wp:group -->'
NEXT = '<!-- wp:group {"className":"sf-map__regions"'

assert lines[1199].startswith(A_START), 'L1200 anchor mismatch: %r' % lines[1199][:80]
assert lines[1200] == A_OPEN, 'L1201 anchor mismatch: %r' % lines[1200][:80]
assert lines[1266] == A_END, 'L1267 anchor mismatch: %r' % lines[1266][:80]
assert lines[1198] == PREV, 'L1199 anchor mismatch: %r' % lines[1198][:80]
assert lines[1267].startswith(NEXT), 'L1268 anchor mismatch: %r' % lines[1267][:80]
# make sure the range really is the 4 cards and nothing else
block = '\n'.join(lines[1199:1267])
assert block.count('<div class="wp-block-column">') == 4, 'expected 4 columns in range'
assert block.count('class="wp-block-group sf-cell"') == 4, 'expected 4 sf-cell in range'
assert 'sf-map__regions' not in block, 'range leaked outside the stat row'

del lines[1199:1267]
src = '\n'.join(lines)
log.append('A1 front-page.html: removed lines 1200-1267 (68 lines) → %d → %d lines' % (orig_lines, len(lines)))

# ---------------------------------------------------------------- B: 4 text swaps in front-page
SWAPS_FP = [
    ('B1 map subtitle',
     'Exporting to 4 Continents \u00b7 30+ Countries \u00b7 FDA, cGMP, ISO 9001, FSSC 22000</p>',
     'Exporting to 4 Continents \u00b7 30+ Countries \u00b7 FDA, cGMP, ISO 9001, FSSC 22000, HACCP, BRC</p>'),
    ('B3 hero subtitle',
     'FDA registered, cGMP, ISO 9001, FSSC 22000. Exporting to 30+ countries.</p>',
     'FDA registered, cGMP, ISO 9001, FSSC 22000, HACCP, BRC. Exporting to 30+ countries.</p>'),
    ('B4 about check',
     'FDA registered, cGMP, ISO 9001, FSSC 22000</p>',
     'FDA registered, cGMP, ISO 9001, FSSC 22000, HACCP, BRC</p>'),
    ('B5 faq answer',
     'FDA registration, cGMP, ISO 9001, FSSC 22000.</p>',
     'FDA registration, cGMP, ISO 9001, FSSC 22000, HACCP, BRC.</p>'),
]
for name, old, new in SWAPS_FP:
    n = src.count(old)
    assert n == 1, '%s: expected 1 occurrence, found %d' % (name, n)
    src = src.replace(old, new)
    log.append('%s: 1 replacement' % name)
assert src.count('sf-map-stats') == 0, 'sf-map-stats still present in front-page.html'
write(FP, src)

# ---------------------------------------------------------------- B2: footer blurb
ft = read(FT)
old = 'Private label pet supplement manufacturer with 8 dosage forms, FDA, cGMP, ISO 9001, FSSC 22000.</p>'
new = 'Private label pet supplement manufacturer with 8 dosage forms, FDA, cGMP, ISO 9001, FSSC 22000, HACCP, BRC.</p>'
assert ft.count(old) == 1, 'footer blurb: expected 1 occurrence, found %d' % ft.count(old)
write(FT, ft.replace(old, new))
log.append('B2 parts/footer.html: 1 replacement')

# ---------------------------------------------------------------- A2: drop dead CSS rule
css = read(CSS)
cl = css.split('\n')
DEAD = [
    '/* 26d map stat row: the sf-panel--4 row under the map goes 2x2 on phone',
    '   (instead of the default single column); desktop stays 4-up. */',
    '@media (max-width: 781px) {',
    '\t.wp-block-columns.sf-map-stats {',
    '\t\tgrid-template-columns: repeat(2, minmax(0, 1fr)) !important;',
    '\t}',
    '}',
]
assert cl[1859:1866] == DEAD, 'style.css dead-rule anchor mismatch:\n%r' % cl[1859:1866]
del cl[1859:1866]
css = '\n'.join(cl)
assert 'sf-map-stats' not in css, 'sf-map-stats still referenced in style.css'
log.append('A2 style.css: removed dead sf-map-stats rule (lines 1860-1866, 7 lines)')

# ---------------------------------------------------------------- D: version bump
css_old = 'Version: 2.5.3'
assert css.count(css_old) == 1
css = css.replace(css_old, 'Version: 2.10.2')
write(CSS, css)
log.append('D style.css header: Version 2.5.3 -> 2.10.2')

fun = read(FUN)
assert fun.count("'2.10.1'") == 1, 'functions.php version anchor not unique'
fun = fun.replace("'2.10.1'", "'2.10.2'")
write(FUN, fun)
log.append('D functions.php: enqueue style version 2.10.1 -> 2.10.2')

print('\n'.join(log))
print('\nALL EDITS APPLIED')

#!/usr/bin/env python3
"""Batch 3b — offline self-check of five template edits and the two version tokens.

Reads the WORKING TREE only: no site, no database, no server.  That is the whole
point.  This batch is committed and pushed under "do not pull", so dev still
serves the 2.10.76 tree and the rendered bytes cannot be read from here at all.
What can be proven offline is:

  (a) the edits landed in the source, byte for byte;
  (b) the block markup they write is balanced — the one failure mode a hand
      edit has that a block-editor save does not;
  (c) the bands the batch promised to leave alone were in fact left alone;
  (d) the negative controls name their owner: a heading that WAS unlinked is
      asserted gone, not merely missing from a count.

Companion to `b2d_h8c_live_check.py`, which reads served bytes.  Run this one
right after an edit; run that one after a preflight install or a pull.  Neither
substitutes for the other.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TT = os.path.join(ROOT, 'sinofresh-theme')

rows = []


def read(path):
    with open(os.path.join(TT, path), encoding='utf-8') as fh:
        return fh.read()


def ck(label, ok, got=None):
    rows.append((label, bool(ok)))
    print('  %-74s %s' % (label, 'ok' if ok else 'FAIL'))
    if not ok and got is not None:
        print('        got: %r' % (got,))


ARROW = '\u2192'

# --------------------------------------------------------------- A. the footer
print('== A. the footer gains a Services column (item 2 + item 5) ==')
ftr = read('parts/footer.html')
sums = re.findall(r'<summary>([^<]+)</summary>', ftr)
ck('four columns stand, Services between Products and Company',
   sums == ['Products', 'Services', 'Company', 'Contact Us'], sums)

WANT_FOOT = [('/services/oem/', 'OEM Manufacturing'),
             ('/services/odm/', 'ODM Custom Formulation'),
             ('/services/private-label/', 'Private Label'),
             ('/services/contract-manufacturing/', 'Contract Manufacturing'),
             ('/cooperation/', 'Cooperation Models')]
m = re.search(r'<summary>Services</summary>.*?<p class="sf-footlinks"[^>]*>(.*?)</p>',
              ftr, re.S)
foot_links = re.findall(r'<a href="([^"]+)">([^<]+)</a>', m.group(1)) if m else []
ck('it carries the four services and the cooperation page, in the given order',
   foot_links == WANT_FOOT, foot_links)
ck('five links and no sixth', len(foot_links) == 5, len(foot_links))
ck('the three older columns keep their own link paragraphs',
   # One <p> per column. The class STRING 'sf-footlinks' also appears in the
   # block comments as "className", so counting that would give 6, not 4 — quote
   # the tag instead.
   ftr.count('<p class="sf-footlinks') == 4 and ftr.count('<summary>') == 4,
   (ftr.count('<p class="sf-footlinks'), ftr.count('<summary>')))

# ----------------------------------------------------------- B. the front page
print('== B. the front page teaser cards link to their own pages (item 3) ==')
fp = read('templates/front-page.html')
WANT_TP = [('/services/oem/', 'OEM &#8212; You Bring the Formula'),
           ('/services/odm/', 'ODM &#8212; We Develop From Your Idea'),
           ('/services/contract-manufacturing/', 'Contract Manufacturing'),
           ('/services/private-label/', 'Private Label')]
wrapped = re.findall(r'<h3 class="wp-block-heading"><a class="sf-card__title-link" '
                     r'href="([^"]+)">([^<]+)</a></h3>', fp)
ck('four card headings are wrapped as stretched links, in card order',
   wrapped == WANT_TP, wrapped)
ck('the wrapped text is the card\'s own copy, character for character',
   [t for _, t in wrapped] == [t for _, t in WANT_TP], wrapped)
for _, label in WANT_TP:
    ck('NC the unlinked heading %s is gone from the front page' % label[:38],
       ('<h3 class="wp-block-heading">%s</h3>' % label) not in fp)
ck('the engagement band is still the white one the outline button needs',
   'sf-oem has-card-white-background-color' in fp,
   'sf-oem has-card-white-background-color' in fp)

# ------------------------------------------------------------ C. the band button
print('== C. the band gains one See-all button (item 3) ==')
# Scoped to the engagement band: the front page already carries two outline
# buttons of its own (articles, FAQ), and a bare page-wide count would sweep
# them in and call the result "the new button".
m = re.search(r'<section class="[^"]*\bsf-oem\b[^"]*"(.*?)</section>', fp, re.S)
oem_band = m.group(1) if m else ''
band_btn = re.findall(r'<a class="wp-block-button__link wp-element-button sf-btn-outline '
                      r'has-border-color" href="([^"]+)">([^<]+)</a>', oem_band)
ck('the overview button is there, once, and the band draws no other',
   band_btn == [('/services/', 'See all services %s' % ARROW)], band_btn)
ck('it sits after the columns and before the section close',
   re.search(r'<!-- /wp:columns -->\s*<!-- wp:buttons .*?/wp:buttons -->\s*</section>',
             fp, re.S) is not None)
ck('the outline style it names is one the stylesheet actually defines',
   '.wp-block-button .sf-btn-outline' in read('style.css'))

# ------------------------------------------------------------- D. the overview
print('== D. the overview gains two bands, and the alternation holds (item 4) ==')
svc = read('templates/page-services.html')
WANT_H2 = ['OEM or ODM &#8212; Choose Your Path',
           'Key Facts: MOQ, Lead Time, Payment &amp; Trade Terms',
           'What We Handle &#8212; R&amp;D, Compliance &amp; Export Documentation',
           'Custom Formulation Capability',
           'How We Work &#8212; From Inquiry to Delivery in 5 Steps',
           'Manufacturing Capability',
           'Frequently Asked Questions',
           'Request a Sample']
h2s = re.findall(r'<h2 class="[^"]*wp-block-heading[^"]*">([^<]+)</h2>', svc)
ck('the overview draws eight bands, in the declared order', h2s == WANT_H2, h2s)

bands = []
for cls in re.findall(r'<section class="wp-block-group([^"]*)"', svc):
    for token, name in (('has-bg-light-background-color', 'light'),
                        ('has-card-white-background-color', 'white'),
                        ('has-primary-background-color', 'primary'),
                        ('sf-hero-inner', 'hero')):
        if token in cls:
            bands.append(name)
            break
    else:
        bands.append('?')
ck('light and white alternate, hero first and the CTA band last',
   bands == ['hero', 'light', 'white', 'light', 'white', 'light', 'white',
             'light', 'primary'], bands)


def band_of(h2, text):
    m = re.search(re.escape(h2) + r'(.*?)<!-- /wp:group -->', text, re.S)
    return m.group(1) if m else ''


c1 = band_of('Custom Formulation Capability', svc)
c2 = band_of('Manufacturing Capability', svc)
ck('C1 lists the four formulation items',
   re.findall(r'<li>([^<]+)</li>', c1) ==
   ['Custom formula development', 'Custom active ingredient levels',
    'Palatability testing', 'Stability testing'],
   re.findall(r'<li>([^<]+)</li>', c1))
ck('C2 lists the four manufacturing items',
   re.findall(r'<li>([^<]+)</li>', c2) ==
   ['GMP-certified facility', '8 dosage form production lines',
    'In-house QC laboratory', 'Full traceability'],
   re.findall(r'<li>([^<]+)</li>', c2))
ck('C1 sends the reader to ODM and to quality',
   re.findall(r'href="([^"]+)"', c1) == ['/services/odm/', '/quality/'],
   re.findall(r'href="([^"]+)"', c1))
ck('C2 sends the reader to the factory tour and to quality',
   re.findall(r'href="([^"]+)"', c2) == ['/factory-tour/', '/quality/'],
   re.findall(r'href="([^"]+)"', c2))
ck('both new lists use the panel checklist class the stylesheet dresses',
   c1.count('<ul class="sf-checklist sf-checklist--panel">') == 1
   and c2.count('<ul class="sf-checklist sf-checklist--panel">') == 1)
ck('How We Work moved off white onto light, and is the only band that moved',
   'backgroundColor":"bg-light"' in svc
   and svc.count('>How We Work &#8212; From Inquiry to Delivery in 5 Steps<') == 1)
ck('NC the summary no longer claims the overview is untouched',
   'otherwise untouched by the batch' not in svc)

# ---------------------------------------------------------------- E. the tokens
print('== E. the two version tokens move together (item 6) ==')
css, phpx = read('style.css'), read('functions.php')
ck('style.css declares 2.10.77', re.search(r'^Version: 2\.10\.77$', css, re.M) is not None)
ck('functions.php enqueues 2.10.77', "array(), '2.10.77');" in phpx)
stale = []
for dirpath, _, names in os.walk(TT):
    for name in names:
        if name.endswith(('.php', '.css')):
            with open(os.path.join(dirpath, name), encoding='utf-8', errors='ignore') as fh:
                if '2.10.76' in fh.read():
                    stale.append(os.path.relpath(os.path.join(dirpath, name), TT))
ck('NC no 2.10.76 token survives anywhere in the theme tree', not stale, stale)

# ------------------------------------------------------- F. the block markup
print('== F. the block markup this batch writes is balanced ==')
for name in ['templates/front-page.html', 'templates/page-services.html',
             'parts/footer.html', 'templates/page-oem.html']:
    text = read(name)
    opens = len(re.findall(r'<!--\s+wp:', text))
    selfc = len(re.findall(r'<!--\s+wp:[^\n]*?/-->', text))
    closes = len(re.findall(r'<!--\s+/wp:', text))
    ck('%-28s opens %3d - self-closing %2d == closes %3d'
       % (name.split('/')[-1] + ':', opens, selfc, closes), opens - selfc == closes,
       (opens, selfc, closes))
    # A hand-written block comment that will not parse is the one thing a block
    # editor would never produce and a reviewer cannot see by eye: WordPress
    # falls back to "attempt block recovery" on the next save.
    bad = []
    for m in re.finditer(r'<!--\s+wp:[a-z][a-z0-9/-]*\s+(\{[^\n]*\})\s*/?-->', text):
        try:
            json.loads(m.group(1))
        except ValueError as exc:
            bad.append((m.group(1)[:40], str(exc)[:40]))
    ck('...and every block attribute JSON parses', not bad, bad[:3])

passed = sum(1 for _, ok in rows if ok)
print('\n== batch 3b local: %d/%d %s'
      % (passed, len(rows), 'PASS' if passed == len(rows) else 'FAIL'))
sys.exit(0 if passed == len(rows) else 1)

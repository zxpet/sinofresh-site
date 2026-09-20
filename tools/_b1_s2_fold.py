#!/usr/bin/env python3
"""
Batch 1 / Stage 2.1 + 2.6 — wrap the dosage-form configurator in <details>.

Per dosage template:
  A. Copy edits the Lead time wording ("after packaging ready" -> "is ready").
  B. Moves <div class="sf-explore"> OUT of .configurator__options and places it
     after the fold. The seven internal links must never be hidden by the fold,
     and <details> hides every child but <summary>, so the band cannot stay in.
     Verified safe: configurator.js binds nothing inside sf-explore (it only
     queries .configurator / __group / __item / __summary-row / __bar / drawer),
     so the band is re-parented, never detached, and no listener is lost.
  C. Wraps the heading + description + <div class="configurator"> in
     <details class="configurator__fold">. The configurator DOM itself is
     untouched — it just sits one level deeper inside .configurator__fold-body.

Every anchor is asserted to match exactly once before anything is written.

Usage:  python3 tools/_b1_s2_fold.py [--dry]
"""
import re
import sys

PAGES = ['soft-chews', 'tablets', 'powders', 'pastes', 'drops', 'liquids', 'fish-oil', 'dental-chews']
TPL = 'sinofresh-theme/templates/page-%s.html'

HEAD_RE = re.compile(
    r'<!-- wp:heading \{"textAlign":"center"\} -->\n'
    r'<h2 class="has-text-align-center wp-block-heading">(.*?)</h2>\n'
    r'<!-- /wp:heading -->\n'
    r'<!-- wp:paragraph \{"align":"center","textColor":"text-secondary"\} -->\n'
    r'<p class="has-text-align-center has-text-secondary-color has-text-color">(.*?)</p>\n'
    r'<!-- /wp:paragraph -->\n'
    r'<!-- wp:html -->\n'
    r'<svg class="configurator__sprite"', re.S)

EXPLORE_RE = re.compile(
    r'[ \t]*<div class="sf-explore">\n'
    r'[ \t]*<h3 class="sf-explore__title">Explore more dosage forms</h3>\n'
    r'[ \t]*\[sf_explore_chips\]\n'
    r'[ \t]*<a class="sf-explore__btn" href="/products/">Browse All Products &rarr;</a>\n'
    r'[ \t]*</div>\n')

CLOSE_RE = re.compile(r'</div>\n<!-- /wp:html -->\n</section>\n<!-- /wp:group -->')

# The description ships as a <span>, not a <p>: <summary>'s content model is
# "phrasing content, optionally intermixed with heading content", so a nested
# <p> would be invalid. The classes and display:block give it the paragraph box
# back, and .configurator__fold-desc re-adds the block gap the constrained
# layout used to supply.
HEAD_NEW = """<!-- wp:html -->
<details class="configurator__fold">
<summary class="configurator__fold-head">
<h2 class="has-text-align-center wp-block-heading">%(h2)s</h2>
<span class="configurator__fold-desc has-text-align-center has-text-secondary-color has-text-color">%(desc)s</span>
<span class="configurator__fold-icon" aria-hidden="true"></span>
</summary>
<div class="configurator__fold-body">
<svg class="configurator__sprite\"""" 

CLOSE_NEW = """</div>
</div>
</details>
<div class="configurator__explore-row">
<div class="configurator__explore-col">
<div class="sf-explore">
<h3 class="sf-explore__title">Explore more dosage forms</h3>
[sf_explore_chips]
<a class="sf-explore__btn" href="/products/">Browse All Products &rarr;</a>
</div>
</div>
</div>
<!-- /wp:html -->
</section>
<!-- /wp:group -->"""

LEAD_OLD = 'after packaging ready'
LEAD_NEW = 'after packaging is ready'


def tag_balance(html):
    """Count block-level openers/closers so a botched splice cannot ship."""
    out = {}
    for tag in ('div', 'section', 'details', 'summary'):
        out[tag] = (len(re.findall(r'<%s[ >]' % tag, html)), len(re.findall(r'</%s>' % tag, html)))
    return out


def main(dry):
    ok = True
    for slug in PAGES:
        path = TPL % slug
        src = open(path, encoding='utf-8').read()

        heads = HEAD_RE.findall(src)
        explores = EXPLORE_RE.findall(src)
        closes = CLOSE_RE.findall(src)
        leads = src.count(LEAD_OLD)
        for name, n in (('HEAD', len(heads)), ('EXPLORE', len(explores)), ('CLOSE', len(closes)), ('LEAD', leads)):
            if n != 1:
                print('  !! %-14s %s matched %d times (expected 1) — aborting this page' % (slug, name, n))
                ok = False
        if not ok:
            continue

        h2, desc = heads[0]
        out = src
        out = HEAD_RE.sub(lambda m: HEAD_NEW % {'h2': m.group(1), 'desc': m.group(2)}, out, count=1)
        out = EXPLORE_RE.sub('', out, count=1)
        out = CLOSE_RE.sub(lambda m: CLOSE_NEW, out, count=1)
        out = out.replace(LEAD_OLD, LEAD_NEW)

        # --- structural assertions on the result -------------------------
        # NOTE: the pages already carry 7 other <details> (2 formula items + 5
        # FAQ rows), so "</details>" alone is ambiguous. Anchor on the exact
        # three-tag splice this script emits instead.
        FOLD_CLOSE = '</details>\n<div class="configurator__explore-row">'
        problems = []
        if out.count('<details class="configurator__fold">') != 1:
            problems.append('fold open tag')
        if out.count(FOLD_CLOSE) != 1:
            problems.append('fold close+explore-row splice')
        if out.count('<div class="configurator__fold-body">') != 1:
            problems.append('fold body')
        if out.count('<div class="configurator">') != 1:
            problems.append('configurator root')
        if out.count('<div class="sf-explore">') != 1:
            problems.append('sf-explore root')
        if out.count('<!-- wp:html -->') != src.count('<!-- wp:html -->'):
            problems.append('wp:html opener count changed')
        if out.count('<!-- /wp:html -->') != src.count('<!-- /wp:html -->'):
            problems.append('wp:html closer count changed')
        # the heading/paragraph block pair must be folded into the wp:html block
        # (other wp:heading comments on the page are unrelated — match the anchor)
        if HEAD_RE.search(out):
            problems.append('original heading/paragraph anchor still present')
        if out.count('<span class="configurator__fold-desc') != 1:
            problems.append('fold description span')
        if out.count('after packaging is ready') != 1 or LEAD_OLD in out:
            problems.append('lead time wording')
        b = tag_balance(out)
        for tag, (o, c) in b.items():
            if o != c:
                problems.append('%s unbalanced %d/%d' % (tag, o, c))
        # the band has to sit after the fold, and inside the explore row
        i_det = out.find(FOLD_CLOSE)
        i_exp = out.find('<div class="sf-explore">')
        i_body = out.find('<div class="configurator__fold-body">')
        if not (0 < i_body < i_det < i_exp):
            problems.append('order fold-body < </details> < sf-explore violated')
        if '</div>\n</div>\n</div>\n<!-- /wp:html -->' not in out:
            problems.append('explore row not closed before /wp:html')

        status = 'OK ' if not problems else 'FAIL'
        print('  %s %-14s wp:html %d/%d  div %d/%d  section %d/%d  details %d/%d  order=%s %s'
              % (status, slug, out.count('<!-- wp:html -->'), src.count('<!-- wp:html -->'),
                 b['div'][0], b['div'][1], b['section'][0], b['section'][1],
                 b['details'][0], b['details'][1],
                 (i_body < i_det < i_exp), ('| ' + '; '.join(problems)) if problems else ''))
        if problems:
            ok = False
            continue

        if not dry:
            open(path, 'w', encoding='utf-8').write(out)

    print('\n%s' % ('DRY RUN — nothing written' if dry else 'WRITTEN: 8 templates'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main('--dry' in sys.argv))

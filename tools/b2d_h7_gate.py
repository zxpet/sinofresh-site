#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H7 — one gate for the H7a..H7f batches, declaration per batch.

WHY ONE TOOL AND NOT SIX

The H7 batches are not six shapes. Every one of them is "the rendered page must
equal the baseline with a DECLARED edit applied, and nothing else may differ", on
the same 75-page capture, against the same preflight copy of the same site.
Writing six gates would mean six copies of the comparison, six copies of the mask
set and six chances for them to drift apart — and the mask set is the part that
must not drift, because a mask that is too wide hides the very change the gate
exists to see (batch H5's lesson) while one that is too narrow reports noise as
regression forever (batch H4e's).

So the comparison lives here once, and each batch contributes a DECLARATION:
the version tokens it moves, the edit it applies to the baseline, the old strings
it claims are gone, and the counts that must not have moved.

FROM H7b THE BATCH-SPECIFIC PARTS MOVED INTO THE DECLARATION

H7a's declaration drove the comparison; the plausible-wrong-answer set (--matrix)
and the two coverage controls (NC3/NC4 in --negctl) were still literals in the
machinery, and --source could only reach three hard-coded files. H7b needs
different mutants, a different injection and two more files (plus the block
template, for which H6's CSS comment stripper is the wrong stripper), so those
four places now read from the declaration — `matrix`, `reinject`, `delete` and
`sources`. H7a's declarations for them are the literals that used to be there,
unedited.

THE MASK SET IS IMPORTED, NOT RETYPED

Straight from tools/b2d_h6_confine.py, per the rule batch H4e wrote down after
finding two tools with hand-copied masks that had already drifted. H6's set is
also the right one to inherit: it deliberately EXCLUDES sf_masked_cmp.py's two
catch-all blob masks (`'[A-Za-z0-9+/=]{16,}'`, `[A-Za-z0-9+/]{40,}`), which can
erase a 40-character stretch of real content, and it replaces the second of them
with a DECODE-BASED mask for Gravity Forms' 612-byte state blob. A gate for a
batch that deletes DOM cannot afford a mask that eats arbitrary base64.

WHAT EACH MODE PROVES

  (default)   main proof: mask(transform(baseline)) == mask(candidate), page by
              page, with the number of applications asserted equal to the
              declared count. Then the old-string coverage claim, then the
              unmoved counts, then the masked-blob read-back.
  --aa DIR2   two captures of the SAME state must be byte-identical under the
              same mask set. This is the precondition for believing the main
              proof: a mask set that cannot make A/A clean cannot be trusted to
              make a real difference mean anything.
  --matrix    sabotage: mutants of the declaration must each FAIL. A mutant that
              changes nothing is reported INVALID rather than counted.
  --negctl    named negative controls, each of which must print its own FAIL.
  --source    the theme-side claims a rendered capture cannot see.

usage:
    b2d_h7_gate.py --batch BATCH --base DIR --cand DIR [--json OUT]
    b2d_h7_gate.py --batch BATCH --base DIR --cand DIR --aa DIR2
    b2d_h7_gate.py --batch BATCH --base DIR --cand DIR --matrix
    b2d_h7_gate.py --batch BATCH --base DIR --cand DIR --negctl
    b2d_h7_gate.py --batch BATCH --source [--theme DIR]
"""
import argparse
import base64
import copy
import hashlib
import importlib.util
import json
import os
import re
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# The mask machinery and the capture helpers come from batch H6's gate. Imported
# rather than copied: one implementation, one place for it to be wrong.
h6 = _load('b2d_h6_confine', os.path.join(HERE, 'b2d_h6_confine.py'))

mask = h6.mask                 # (text, counts) -> text with the noise removed
pages = h6.pages               # (dir) -> sorted page names
read = h6.read                 # (path) -> text
gf_blob_proof = h6.gf_blob_proof
first_diff = h6.first_diff
ctx = h6.ctx

# The two masks H6 removed from the shared set, named here so a future edit that
# puts them back is caught by name rather than by a shifting count.
BANNED_MASKS = ('quoted_blob', 'long_b64_run')


def strip_html_comments(text):
    """Blank HTML comment bodies, length-preserving (newlines kept).

    Needed from H7b on, where the checks moved off the stylesheet and onto the
    block template: the comments there NAME the very strings the absence checks
    look for, so a naive search reads the explanation as a survivor — the exact
    mistake the CSS-side checks made on their first run, one file over.
    """
    return re.sub(r'<!--.*?-->',
                  lambda m: ''.join('\n' if c == '\n' else ' ' for c in m.group(0)),
                  text, flags=re.S)


# --------------------------------------------------------------- declarations

BATCHES = {}


def _h7a_transform(text, tabs=None):
    """Batch H7a's declared edit to one baseline page.

    Removes the band's heading and puts the [Photos][Video] switch where it
    was, which is not where the heading was: the switch is the inner grid's
    third child, so it lands AFTER the stage's closing </div>, not before it.
    The non-greedy `.*?</div>}` is what makes that unambiguous — the stage's own
    </div> is the first one after the figures, and the frames carry no nested
    div of their own to be mistaken for it.
    """
    tabs = H7A_TABS if tabs is None else tabs
    return H7A_INNER_H2.subn(lambda m: m.group(1) + m.group(2) + tabs + '</div>', text)


H7A_TABS = ('<div class="sf-gallery__tabs" role="group" aria-label="Product media">'
            '<button type="button" class="sf-gallery__tab is-active" '
            'data-sf-gallery-tab="photos" aria-pressed="true">Photos</button></div>')

H7A_INNER_H2 = re.compile(
    r'(<div class="sf-gallery__inner" data-gallery="[^"]+">)'
    r'<h2 class="sf-gallery__title">A Closer Look at [^<]*</h2>'
    r'(.*?</div>)</div>', re.S)


def _wrong_place(text):
    """The switch placed where the heading was is the plausible wrong answer, and
    it is wrong: the switch is the grid's third child, after the stage."""
    out, n = H7A_INNER_H2.subn(
        lambda m: m.group(1) + H7A_TABS + m.group(2) + '</div>', text)
    return out, n


BATCHES['h7a'] = {
    'name': 'H7a — the media switch replaces the gallery heading',
    'tokens': [
        ('?ver=2.10.61', '?ver=2.10.62'),                    # style.css
        ('formula-gallery.js?ver=2.0.0', 'formula-gallery.js?ver=2.1.0'),
    ],
    'transform': _h7a_transform,
    'applies': 42,
    'coverage': [
        ('sf-gallery__title', 0),
        ('A Closer Look at', 0),
        ('sf-gallery__thumb--video', 0),
        ('?ver=2.10.61', 0),
        ('formula-gallery.js?ver=2.0.0', 0),
    ],
    'insertions': [
        ('sf-gallery__tabs', 42),
        ('data-sf-gallery-tab="photos"', 42),
        ('data-sf-gallery-tab="video"', 0),   # 0/21 records have a video yet
    ],
    'unmoved': [
        # (label, regex, expected page count) — the same on both sides
        ('h1', r'<h1[^>]*>', None),
        ('formula CTA pages', r'class="sf-formula__cta', 60),
        ('gallery stage pages', r'sf-gallery__stage', 42),
        ('right-column title pages', r'sf-fdetail2__title', 42),
        ('ld+json blocks', r'<script type="application/ld\+json">', None),
    ],
    'h2_delta': -1,          # on the 42 declared pages only
    'source': [
        # (label, target, pattern, want) — target picks the text to search:
        #   css/php/js   the file as written, comments included
        #   css_live     style.css with comments blanked (length-preserving), so
        #                a rule that a comment merely NAMES does not count as a
        #                survivor — the mistake this check made on its first run
        #   js_live/php_live  same, comments stripped
        #
        # The two version literals below are BASELINE-TIME claims: they name the
        # version H7a's candidate carried, and a later batch that bumps
        # style.css makes them read FAIL by design. A gate that quietly relaxed
        # them would be agreeing with a change it never saw. The 16/16 from when
        # H7a shipped is preserved in _backup/b2d-h7a-source.json; from H7b on,
        # read this mode as 14 timeless claims plus 2 historical ones.
        ('style.css declares 2.10.62', 'css', r'(?m)^Version: 2\.10\.62$', True),
        ('functions.php enqueues 2.10.62 for style.css', 'php',
         r"wp_enqueue_style\('sinofresh-style'[^;]*'2\.10\.62'", True),
        ('functions.php enqueues 2.1.0 for formula-gallery.js', 'php',
         r"wp_enqueue_script\('sinofresh-formula-gallery'[^;]*'2\.1\.0'", True),
        ('the switch has its own grid area', 'css', r'grid-area: tabs;', True),
        ('the switch is painted only with scripting', 'css',
         r'\.sf-gallery--js \.sf-gallery__tabs', True),
        ('video mode takes the strip out', 'css',
         r'\.sf-gallery--video \.sf-gallery__thumbs', True),
        ('no selector for the deleted heading survives', 'css_live',
         r'sf-gallery__title', False),
        ('no rule for the deleted video tile survives', 'css_live',
         r'sf-gallery__thumb--video', False),
        ('no grid area named title survives', 'css_live', r'"title', False),
        ('the strip builder no longer names a video tile', 'js_live',
         r'thumb--video', False),
        ('the renderer still emits both tab kinds', 'php',
         r'data-sf-gallery-tab="(photos|video)"', True),
        ('the renderer gates [Video] on a real video', 'php', r'\$has_video', True),
    ],
    'source_body': [
        # Checked INSIDE the renderer's own body, not across the file. The first
        # draft asserted "functions.php no longer calls get_the_title()", which
        # was wrong twice over: that call has two other readers here (the params
        # shortcode and the FAQ), and a heading can be gone while the call
        # remains. Brace-matching from the function's own name beats a line
        # number, which would drift on the next edit.
        ('the renderer emits no heading', '<h2', False),
        ('the renderer keeps no title local', '$title', False),
        ('the renderer keeps no dosage label fallback', '$label', False),
        ('the renderer builds the switch', 'sf-gallery__tabs', True),
    ],
    'reinject': ('coverage fails when one old heading is re-injected',
                 'formulas__joint-support-soft-chews.html',
                 '<div class="sf-gallery__tabs"',
                 '<h2 class="sf-gallery__title">A Closer Look at X</h2>'),
    'delete': ('coverage fails when one switch is deleted',
               'formulas__calming-soft-chews.html', H7A_TABS),
    'matrix': [
        # (name, decl override, page mutation)
        ('switch not inserted', {'transform': (lambda t: (t, 0)), 'applies': 0}, None),
        ('switch inserted before the stage closes', {'transform': _wrong_place}, None),
        ('style token not folded', {'tokens': [('?ver=2.10.61', '?ver=2.10.62')]}, None),
        ('JS token not folded', {'tokens': [('formula-gallery.js?ver=2.0.0', 'formula-gallery.js?ver=2.1.0')]}, None),
        ('one page left untransformed', {}, ('formulas__joint-support-soft-chews.html',
                                            lambda s: s.replace(H7A_TABS, ''))),
        ('a stray character on one page', {}, ('formulas__calming-soft-chews.html',
                                               lambda s: s.replace('</body>', '<!-- stray --></body>'))),
        ('one label flipped to Video', {}, ('formulas__joint-support-soft-chews.html',
                                            lambda s: s.replace('>Photos<', '>Video<'))),
    ],
}


# ---------------------------------------------------------------------- H7b

def _h7b_transform(text, replacement=None):
    """Batch H7b's declared edit to one baseline page.

    The detail page's hero primary action: a <button> that copied the formula
    name becomes an <a> that opens the inquiry dialog. The WHOLE element is
    replaced — open tag, label, close tag — so a candidate that keeps the button
    and merely adds the attribute cannot pass: that variant opens the dialog
    with scripting and does nothing at all without it, and the no-JS href is
    exactly what this change is for. data-formula/data-form are page-specific,
    hence the two [^"]* holes.

    THE HREF IS NOT HARDCODED, and that is the whole reason for the lookahead.
    The sibling CTA already carries this destination and TranslatePress rewrites
    it per language: the same template byte `/contact/#quote` renders as
    `/contact/#quote` on the 21 English pages and `/zh/contact/#quote` on the 21
    Chinese ones. A literal would have declared 42 edits and matched 21 — one of
    those failures that looks like a content problem for an hour. Reading the
    destination off the sibling also states the invariant that matters: the new
    CTA goes exactly where "Build Custom Formula" beside it already went.
    """
    if replacement is not None:
        return H7B_HERO.subn(lambda m: replacement, text)

    def sub(m):
        return ('<a class="sf-formula__cta sf-formula__cta--solid" href="%s"'
                ' data-sf-inquiry-open>Send Inquiry</a>' % m.group(1))
    return H7B_HERO.subn(sub, text)


H7B_NEW = ('<a class="sf-formula__cta sf-formula__cta--solid" href="/contact/#quote"'
           ' data-sf-inquiry-open>Send Inquiry</a>')

# The lookahead captures the sibling's href, which is the destination the new
# CTA must carry.
H7B_HERO = re.compile(
    r'<button type="button" class="sf-formula__cta sf-formula__cta--solid"'
    r' data-formula="[^"]*" data-form="[^"]*">Reference this formula →</button>'
    r'(?=<a class="sf-formula-hero__build sf-quote-cta" href="([^"]+)")')


def _h7b_wrong_shape(text):
    """The plausible wrong answer: keep the <button>, bolt the attribute on.
    It opens the dialog with scripting and strands the visitor without it."""
    return H7B_HERO.subn(
        lambda m: ('<button type="button" class="sf-formula__cta sf-formula__cta--solid"'
                   ' data-sf-inquiry-open>Send Inquiry</button>'), text)


BATCHES['h7b'] = {
    'name': 'H7b — the hero CTA opens the dialog; the column title steps up',
    'tokens': [
        ('?ver=2.10.62', '?ver=2.10.63'),                        # style.css
        ('formulas.js?ver=1.2.0', 'formulas.js?ver=1.3.0'),
        ('inquiry.js?ver=1.0.0', 'inquiry.js?ver=1.1.0'),
    ],
    'transform': _h7b_transform,
    'applies': 42,
    # A NOTE ON THE TEMPLATE THIS BATCH EDITS, because it cost an hour.
    # templates/single-sf_formula.html is a BLOCK TEMPLATE, and freeform text
    # between its block delimiters is shipped: the page carries those HTML
    # comments verbatim (the baseline already carries H5-0's, B2D-S3's and batch
    # G's). So a comment added there is a product change on 42 pages, not
    # documentation — the first cut of this batch added one, found its own prose
    # in the candidate bytes, and declared the edit as one element instead. Put
    # the explanation in the PHP/JS/CSS around the template, or in the batch
    # record; if it must live in the template, declare every byte of it here.
    'coverage': [
        # Absent from the candidate, counted on the raw bytes.
        # The old open tag is the sharp one: it pins the element AND the two
        # data attributes that only the copy behaviour ever read.
        ('class="sf-formula__cta sf-formula__cta--solid" data-formula=', 0),
        ('?ver=2.10.62', 0),
        ('formulas.js?ver=1.2.0', 0),
        ('inquiry.js?ver=1.0.0', 0),
    ],
    'insertions': [
        # Present on the candidate, at a declared total.
        # 84 = 42 pages x 2, which is the shape the batch is: the hero CTA joins
        # the float capsule as a second opener. Had inquiry.js kept its singular
        # querySelector this count would still be 84 and the capsule would still
        # be broken — counts cannot see which of the two is bound, so the source
        # pass below owns that claim.
        ('data-sf-inquiry-open', 84),
        ('data-sf-inquiry-open>Send Inquiry</a>', 42),
        ('?ver=2.10.63', 75),
        ('formulas.js?ver=1.3.0', 60),
        ('inquiry.js?ver=1.1.0', 42),
    ],
    'counts': [
        # (label, string, base total, candidate total) — BOTH sides measured.
        # Stronger than `unmoved`, which only compares page counts and would not
        # notice 160 card buttons becoming 159, and able to state a string the
        # batch expects to move DOWN, which `insertions` cannot.
        ('the card grid keeps its class', 'class="sf-formula__cta"', 160, 160),
        ('the card labels keep copying', 'Reference this formula', 202, 160),
        ('the card buttons keep data-formula', 'data-form="', 202, 160),
        ('the hero button loses its payload',
         'class="sf-formula__cta sf-formula__cta--solid" data-formula=', 42, 0),
        ('the hero CTA keeps its paint modifier', 'sf-formula__cta--solid', 42, 42),
        # The two rows that catch a language-blind declaration. TranslatePress
        # rewrites the destination per language, so a transform that hardcoded
        # /contact/#quote would leave these at 21 -> 21 on the Chinese half and
        # the main proof would have reported 21 differing pages.
        ('the English pages gain one opener',
         'href="/contact/#quote" data-sf-inquiry-open', 21, 42),
        ('the Chinese pages gain one opener',
         'href="/zh/contact/#quote" data-sf-inquiry-open', 21, 42),
        ('the float capsule is untouched', 'sf-float-btn--inquiry', 42, 42),
        ('the column title is untouched', 'sf-fdetail2__title', 42, 42),
        ('the global quote CTA is untouched', 'sf-quote-cta', 208, 208),
        ('the hero action row is untouched', 'sf-formula-hero__actions', 42, 42),
        ('the dialog markup is untouched', 'class="sf-inquiry-modal"', 42, 42),
        ('the gallery switch is untouched', 'sf-gallery__tabs', 42, 42),
    ],
    'unmoved': [
        # (label, regex, expected page count) — the same on both sides
        ('formula CTA pages', r'class="sf-formula__cta', 60),
        ('detail band pages', r'sf-fdetail2__title', 42),
        ('capsule pages', r'sf-float-btn--inquiry', 42),
        ('ld+json blocks', r'<script type="application/ld\+json">', None),
    ],
    'per_page': [
        # (label, regex, count required on EVERY page) — the brief's "each page
        # still has exactly one h1". `unmoved` compares page counts and would
        # pass a page that lost its h1 as long as another page kept one.
        ('h1', r'<h1[\s>]', 1),
    ],
    'h2_delta': None,        # this batch moves no heading
    'sources': {
        'formulas': 'assets/js/formulas.js',
        'inquiry': 'assets/js/inquiry.js',
        'tpl': 'templates/single-sf_formula.html',
    },
    'source': [
        ('style.css declares 2.10.63', 'css', r'(?m)^Version: 2\.10\.63$', True),
        ('functions.php enqueues 2.10.63 for style.css', 'php',
         r"wp_enqueue_style\('sinofresh-style'[^;]*'2\.10\.63'", True),
        ('functions.php enqueues 1.3.0 for formulas.js', 'php',
         r"wp_enqueue_script\('sinofresh-formulas'[^;]*'1\.3\.0'", True),
        ('functions.php enqueues 1.1.0 for inquiry.js', 'php',
         r"wp_enqueue_script\('sinofresh-inquiry'[^;]*'1\.1\.0'", True),
        ('no 2.10.62 stylesheet enqueue survives', 'php_live',
         r"enqueue_style\('sinofresh-style'[^;]*'2\.10\.62'", False),
        ('no 1.2.0 formulas enqueue survives', 'php_live',
         r"enqueue_script\('sinofresh-formulas'[^;]*'1\.2\.0'", False),
        ('no 1.0.0 inquiry enqueue survives', 'php_live',
         r"enqueue_script\('sinofresh-inquiry'[^;]*'1\.0\.0'", False),

        ('the hero CTA is an anchor with the no-JS href', 'tpl',
         r'<a class="sf-formula__cta sf-formula__cta--solid" href="/contact/#quote"'
         r' data-sf-inquiry-open>Send Inquiry</a>', True),
        ('the sibling CTA is untouched', 'tpl',
         r'class="sf-formula-hero__build sf-quote-cta" href="/contact/#quote"', True),
        ('the template no longer offers to copy a name', 'tpl_live',
         r'Reference this formula', False),
        ('the hero CTA carries no copy payload', 'tpl_live', r'data-formula=', False),

        ('the column title is 32px', 'css',
         r'\.sf-fdetail2__title \{[^}]*font-size: 32px', True),
        ('the column title leading is 1.3', 'css',
         r'\.sf-fdetail2__title \{[^}]*line-height: 1\.3', True),
        ('the column title margin is 24px', 'css',
         r'\.sf-fdetail2__title \{[^}]*margin: 0 0 24px', True),
        ('the column title keeps its weight', 'css',
         r'\.sf-fdetail2__title \{[^}]*font-weight: 700', True),
        ('the phone step is 26px', 'css',
         r'\.sf-fdetail2__title \{\s+font-size: 26px;', True),
        ('no 28px column title survives', 'css_live',
         r'\.sf-fdetail2__title \{\s+font-size: 28px;', False),
        ('the anchor keeps its button surface', 'css',
         r'\.sf-formula-hero \.sf-formula__cta--solid \{[^}]*text-decoration: none', True),
        ('the anchor does not underline on hover', 'css',
         r'\.sf-formula-hero \.sf-formula__cta--solid:hover \{[^}]*text-decoration: none', True),

        ('every opener is bound, not the first one', 'inquiry_live',
         r"querySelectorAll\('\[data-sf-inquiry-open\]'\)", True),
        ('no singular opener query survives', 'inquiry_live',
         r"querySelector\('\[data-sf-inquiry-open\]'\)", False),
        ('the reveal is scoped to the capsule', 'inquiry_live',
         r"capsule\.hidden = false", True),
        ('the focus return follows the click', 'inquiry_live',
         r"opener = from \|\| null", True),
        ('each opener passes itself to open()', 'inquiry_live', r"open\(el\)", True),

        ('the copy handler skips dialog openers', 'formulas_live',
         r"hasAttribute\('data-sf-inquiry-open'\)", True),
        ('the copy handler still binds the class', 'formulas_live',
         r"querySelectorAll\('\.sf-formula__cta'\)", True),
    ],
    'source_body': [],       # the gallery renderer is not this batch's business
    'reinject': ('coverage fails when one hero button is put back',
                 'formulas__joint-support-soft-chews.html',
                 '<div class="sf-formula-hero__actions">',
                 '<button type="button" class="sf-formula__cta sf-formula__cta--solid"'
                 ' data-formula="X" data-form="x">Reference this formula →</button>'),
    'delete': ('coverage fails when one hero opener loses its hook',
               'formulas__calming-soft-chews.html',
               'data-sf-inquiry-open>Send Inquiry</a>'),
    'matrix': [
        ('hero CTA not replaced', {'transform': (lambda t: (t, 0)), 'applies': 0}, None),
        ('the button kept, the attribute bolted on', {'transform': _h7b_wrong_shape}, None),
        ('style token not folded',
         {'tokens': [('formulas.js?ver=1.2.0', 'formulas.js?ver=1.3.0'),
                     ('inquiry.js?ver=1.0.0', 'inquiry.js?ver=1.1.0')]}, None),
        ('formulas token not folded',
         {'tokens': [('?ver=2.10.62', '?ver=2.10.63'),
                     ('inquiry.js?ver=1.0.0', 'inquiry.js?ver=1.1.0')]}, None),
        ('inquiry token not folded',
         {'tokens': [('?ver=2.10.62', '?ver=2.10.63'),
                     ('formulas.js?ver=1.2.0', 'formulas.js?ver=1.3.0')]}, None),
        ('one hero label left alone', {}, ('formulas__joint-support-soft-chews.html',
                                           lambda s: s.replace('>Send Inquiry</a>',
                                                               '>Reference this formula →</a>', 1))),
        ('the attribute dropped on one page', {}, ('formulas__calming-soft-chews.html',
                                                   lambda s: s.replace(
                                                       ' data-sf-inquiry-open>Send Inquiry',
                                                       '>Send Inquiry', 1))),
        ('a stray character on one page', {}, ('formulas__urinary-care-drops.html',
                                               lambda s: s.replace('</body>', '<!-- stray --></body>', 1))),
    ],
}


# ------------------------------------------------------------------- machinery

def fold(text, pairs):
    for old, new in pairs:
        text = text.replace(old, new)
    return text


def main_proof(decl, base, cand, verbose=True):
    names = sorted(set(pages(base)) & set(pages(cand)))
    rows, applied, ok = [], 0, True
    for n in names:
        a = read(os.path.join(base, n + '.html'))
        b = read(os.path.join(cand, n + '.html'))
        exp, cnt = decl['transform'](a)
        applied += cnt
        exp = fold(exp, decl['tokens'])
        am, _ = mask(exp)
        bm, _ = mask(b)
        if am == bm:
            continue
        ok = False
        i = first_diff(am, bm)
        rows.append({'page': n, 'expected': ctx(am, i), 'candidate': ctx(bm, i),
                     'expected_len': len(am), 'candidate_len': len(bm)})
    if applied != decl['applies']:
        ok = False
    if verbose:
        for r in rows[:8]:
            print('  %-42s expected %d B / candidate %d B' % (r['page'], r['expected_len'], r['candidate_len']))
            print('      expected : %r' % r['expected'])
            print('      candidate: %r' % r['candidate'])
        print('  pages compared          : %d' % len(names))
        print('  differing pages         : %d' % len(rows))
        print('  declared edits applied   : %d (declared %d)' % (applied, decl['applies']))
        print('  %s  main proof: mask(transform(baseline)) == mask(candidate)' % ('PASS' if ok else 'FAIL'))
    return {'ok': ok, 'pages': len(names), 'differing': len(rows), 'applied': applied,
            'declared': decl['applies'], 'rows': rows[:8]}


def coverage(decl, base, cand, verbose=True):
    """The declared OLD strings must be GONE from the candidate, and the declared
    NEW ones must be there in the declared number. Counted on the raw bytes, not
    on the masked ones: the mask is the thing that could hide a survivor."""
    ok = True
    rows = []
    total = {'base': {}, 'cand': {}}
    for tag, d in (('base', base), ('cand', cand)):
        blob = ''.join(read(os.path.join(d, p + '.html')) for p in pages(d))
        total[tag]['len'] = len(blob)
    for label, want in decl['coverage']:
        got = sum(read(os.path.join(cand, p + '.html')).count(label) for p in pages(cand))
        good = got == want
        ok &= good
        rows.append({'claim': 'absent', 'string': label, 'want': want, 'got': got, 'ok': good})
        if verbose:
            print('  %-34s candidate count = %-4d (want %d)  %s'
                  % (label, got, want, 'ok' if good else 'FAIL'))
    for label, want in decl['insertions']:
        got = sum(read(os.path.join(cand, p + '.html')).count(label) for p in pages(cand))
        good = got == want
        ok &= good
        rows.append({'claim': 'present', 'string': label, 'want': want, 'got': got, 'ok': good})
        if verbose:
            print('  %-34s candidate count = %-4d (want %d)  %s'
                  % (label, got, want, 'ok' if good else 'FAIL'))
    # `counts` measures BOTH sides, so a string a batch expects to move down can
    # be declared with its before and after rather than smuggled into a list
    # whose name says "insertions".
    for label, needle, want_b, want_c in decl.get('counts', []):
        got_b = sum(read(os.path.join(base, p + '.html')).count(needle) for p in pages(base))
        got_c = sum(read(os.path.join(cand, p + '.html')).count(needle) for p in pages(cand))
        good = got_b == want_b and got_c == want_c
        ok &= good
        rows.append({'claim': 'counted', 'string': needle, 'want': [want_b, want_c],
                     'got': [got_b, got_c], 'ok': good})
        if verbose:
            print('  %-34s base %-4d -> candidate %-4d (want %d -> %d)  %s'
                  % (label, got_b, got_c, want_b, want_c, 'ok' if good else 'FAIL'))
    if verbose:
        print('  %s  coverage: every declared old string is gone, every declared new one is present'
              % ('PASS' if ok else 'FAIL'))
    return {'ok': ok, 'rows': rows}


def counts_of(text, pattern):
    return len(re.findall(pattern, text))


def invariants(decl, base, cand, verbose=True):
    """Counts measured WITHOUT reference to what the batch meant to change."""
    ok = True
    rows = []
    names = sorted(set(pages(base)) & set(pages(cand)))

    for label, pat, want_pages in decl['unmoved']:
        pb = sum(1 for n in names if counts_of(read(os.path.join(base, n + '.html')), pat))
        pc = sum(1 for n in names if counts_of(read(os.path.join(cand, n + '.html')), pat))
        good = pb == pc and (want_pages is None or pc == want_pages)
        ok &= good
        rows.append({'label': label, 'base': pb, 'cand': pc, 'want': want_pages, 'ok': good})
        if verbose:
            print('  %-28s pages base=%d cand=%d%s  %s'
                  % (label, pb, pc, '' if want_pages is None else ' (want %d)' % want_pages,
                     'ok' if good else 'FAIL'))

    # A per-page count, which `unmoved` cannot express: comparing page counts
    # lets one page lose its h1 as long as another keeps one.
    for label, pat, want in decl.get('per_page', []):
        bad = [n for n in names
               if counts_of(read(os.path.join(cand, n + '.html')), pat) != want]
        good = not bad
        ok &= good
        rows.append({'label': '%s per page' % label, 'bad_pages': len(bad), 'ok': good})
        if verbose:
            print('  %-28s pages whose %s count is not %d = %d  %s'
                  % ('%s per page' % label, label, want, len(bad), 'ok' if good else 'FAIL'))

    # The heading count is the one count a declaration may move, and only on the
    # pages it applied to. A batch that declares no delta — H7b moves no heading
    # — must not move one anywhere, which is the same check read at zero.
    h2b, h2c, moved = {}, {}, []
    for n in names:
        h2b[n] = counts_of(read(os.path.join(base, n + '.html')), r'<h2[^>]*>')
        h2c[n] = counts_of(read(os.path.join(cand, n + '.html')), r'<h2[^>]*>')
        if h2b[n] != h2c[n]:
            moved.append((n, h2b[n], h2c[n]))
    delta = decl.get('h2_delta')
    if delta is None:
        good = not moved
        verdict = 'pages with a moved h2 = %d (declared: none)' % len(moved)
    else:
        good = (len(moved) == decl['applies']
                and all(hc - hb == delta for _, hb, hc in moved))
        verdict = 'pages with a moved h2 = %d (declared %d), each %+d' % (
            len(moved), decl['applies'], delta)
    ok &= good
    rows.append({'label': 'h2 delta', 'moved_pages': len(moved), 'ok': good})
    if verbose:
        print('  %-28s %s  %s' % ('h2 delta', verdict, 'ok' if good else 'FAIL'))

    # JSON-LD is compared as DATA, not as bytes: TranslatePress re-serialises the
    # block per language, so a byte comparison would call 21 zh pages a regression
    # every time (batch H3's lesson).
    try:
        ld_ok, ld_pages = jsonld_equal(names, base, cand)
    except Exception as exc:                                    # pragma: no cover
        ld_ok, ld_pages = False, 'error: %s' % exc
    ok &= ld_ok
    rows.append({'label': 'json-ld deep equal', 'ok': ld_ok})
    if verbose:
        print('  %-28s pages parsed = %s  %s' % ('json-ld deep equal', ld_pages, 'ok' if ld_ok else 'FAIL'))

    if verbose:
        print('  %s  invariants: the counts the batch did not claim to move did not move'
              % ('PASS' if ok else 'FAIL'))
    return {'ok': ok, 'rows': rows}


def json_blocks(text):
    return re.findall(r'<script type="application/ld\+json">(.*?)</script>', text, re.S)


def jsonld_equal(names, base, cand):
    bad = 0
    for n in names:
        ab = json_blocks(read(os.path.join(base, n + '.html')))
        ac = json_blocks(read(os.path.join(cand, n + '.html')))
        if len(ab) != len(ac):
            bad += 1
            continue
        for x, y in zip(ab, ac):
            if json.loads(x) != json.loads(y):
                bad += 1
                break
    return bad == 0, len(names)


def aa(dir_a, dir_b, verbose=True):
    names = sorted(set(pages(dir_a)) & set(pages(dir_b)))
    rows = []
    for n in names:
        am, _ = mask(read(os.path.join(dir_a, n + '.html')))
        bm, _ = mask(read(os.path.join(dir_b, n + '.html')))
        if am != bm:
            i = first_diff(am, bm)
            rows.append({'page': n, 'a': ctx(am, i), 'b': ctx(bm, i)})
    ok = not rows
    if verbose:
        for r in rows[:8]:
            print('  %-42s' % r['page'])
            print('      A: %r' % r['a'])
            print('      B: %r' % r['b'])
        print('  pages compared   : %d' % len(names))
        print('  differing pages  : %d' % len(rows))
        print('  %s  A/A: two captures of the same state are identical under this mask set'
              % ('PASS' if ok else 'FAIL'))
    return {'ok': ok, 'pages': len(names), 'differing': len(rows), 'rows': rows[:8]}


# --------------------------------------------------------------- sabotage set

def _clone(src, dst):
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    return dst


def _write(path, text):
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(text)


def _mutate_page(cand_dir, page, fn):
    p = os.path.join(cand_dir, page)
    _write(p, fn(read(p)))


def matrix(decl, base, cand, verbose=True):
    """Each mutation must break the proof, and each mutation must actually have
    changed something — a mutant that changes nothing reports INVALID, not pass.

    The plan lives in the declaration, because what counts as the plausible
    wrong answer is batch-specific: H7a's is a switch in the wrong grid slot,
    H7b's is the button kept with the attribute bolted on.
    """
    ok = True
    rows = []
    for name, override, mutation in decl['matrix']:
        d = dict(decl)
        d.update(override)
        work = tempfile.mkdtemp(prefix='h7mat-')
        try:
            c = _clone(cand, os.path.join(work, 'cand'))
            mutated = False
            if mutation:
                page, fn = mutation
                p = os.path.join(c, page)
                before = read(p)
                after = fn(before)
                mutated = after != before
                _write(p, after)
            else:
                mutated = True   # a declaration change IS the mutation
            r = main_proof(d, base, c, verbose=False)
            if not mutated:
                rows.append((name, 'INVALID', 'the mutant changed nothing'))
                ok = False
            elif r['ok']:
                rows.append((name, 'PASSED', 'the gate let this through'))
                ok = False
            else:
                rows.append((name, 'caught', 'differing pages = %d' % r['differing']))
        finally:
            shutil.rmtree(work, ignore_errors=True)
    if verbose:
        for name, verdict, why in rows:
            print('  %-40s %-8s %s' % (name, verdict, why))
        print('  %s  sabotage matrix: every mutant is caught and none is a no-op'
              % ('PASS' if ok else 'FAIL'))
    return {'ok': ok, 'rows': [{'case': a, 'verdict': b, 'why': c} for a, b, c in rows]}


# ---------------------------------------------------------- named neg controls

def negctl(decl, base, cand, theme, verbose=True):
    ok = True
    rows = []
    work = tempfile.mkdtemp(prefix='h7nc-')

    def report(label, good, why=''):
        nonlocal ok
        ok &= good
        rows.append({'label': label, 'ok': good, 'why': why})
        if verbose:
            print('  %-46s %s%s' % (label, 'ok' if good else 'FAIL', '' if not why else '  ' + why))
        return good

    try:
        # NC1 — the mask set must not carry the two catch-all blob masks
        names = [m[2] for m in h6.MASK_SET]
        bad = [n for n in BANNED_MASKS if n in names]
        report('NC1 the mask set carries no catch-all blob mask', not bad, ','.join(bad))

        # NC2 — and the danger is real, not theoretical. Two things it is NOT:
        #   * not "a blob can be smuggled in" — mask() substitutes a marker
        #     rather than deleting, so an INSERTED run leaves 'MASK' behind and
        #     stays visible;
        #   * not reachable on this site's own pages either — the 60+ character
        #     runs of base64 shape that exist here are Gravity Forms' two fields,
        #     and the named masks already take them.
        # The blind spot is a run present at the SAME offset on both sides with
        # different content, which is why the control builds one: the same 60
        # characters inserted at the same place on both sides, differing only
        # inside the run. With the catch-all mask the proof must go blind; with
        # the set this gate actually uses it must see the edit.
        wb = _clone(base, os.path.join(work, 'wb'))
        wc = _clone(cand, os.path.join(work, 'wc'))
        page = 'contact.html'
        for d, run in ((wb, 'A' * 60), (wc, 'B' * 60)):
            p = os.path.join(d, page)
            _write(p, read(p).replace('</body>', '<!-- ' + run + ' --></body>', 1))
        saved = h6.MASK_SET[:]
        h6.MASK_SET[:] = saved + [(re.compile(r'[A-Za-z0-9+/]{40,}={0,2}'), 'MASK', 'wide_blob')]
        blind = main_proof(decl, wb, wc, verbose=False)['ok']
        h6.MASK_SET[:] = saved
        sighted = main_proof(decl, wb, wc, verbose=False)['ok']
        report('NC2 the catch-all mask hides a same-offset run edit, the real set sees it',
               blind and not sighted, 'page=%s blind=%s sighted=%s' % (page, blind, sighted))

        # NC3 — coverage is a real signal: re-injecting a declared-old string must
        # FAIL. The (label, page, anchor, snippet) comes from the declaration,
        # because which old string is the sharp one is batch-specific.
        label, page, anchor, snippet = decl['reinject']
        c = _clone(cand, os.path.join(work, 'c'))
        p = os.path.join(c, page)
        _write(p, read(p).replace(anchor, snippet + anchor, 1))
        r = coverage(decl, base, c, verbose=False)
        report('NC3 ' + label, not r['ok'])

        # NC4 — and so is the presence count: removing one declared-new string
        # must FAIL. Same reason for living in the declaration.
        label, page, snippet = decl['delete']
        c = _clone(cand, os.path.join(work, 'c2'))
        p = os.path.join(c, page)
        _write(p, read(p).replace(snippet, '', 1))
        r = coverage(decl, base, c, verbose=False)
        report('NC4 ' + label, not r['ok'])

        # NC5 — the h2 delta is a real signal: one extra h2 must FAIL
        c = _clone(cand, os.path.join(work, 'c3'))
        p = os.path.join(c, 'formulas__calming-soft-chews.html')
        _write(p, read(p).replace('</body>', '<h2>extra</h2></body>', 1))
        r = invariants(decl, base, c, verbose=False)
        report('NC5 the invariants fail on one injected h2', not r['ok'])

        # NC6 — A/A is a real signal: A/A against the baseline must FAIL
        r = aa(cand, base, verbose=False)
        report('NC6 A/A against a different state fails', not r['ok'])

        # NC7 — the masked-blob read-back is a signal, not a rubber stamp: the
        # stretch mask() erased is read back, so doctoring its DECODED content —
        # in a place outside every masked token class — must make it fail.
        c = _clone(cand, os.path.join(work, 'c4'))
        p = os.path.join(c, 'contact.html')
        s = read(p)
        raw, dec = h6._gf_state_blob(s)
        if raw and dec:
            dec2 = dec.replace('gform_theme', 'gform_themX')
            if dec2 == dec:
                dec2 = dec + ' '
            raw2 = base64.b64encode(dec2.encode('utf-8')).decode('ascii')
            _write(p, s.replace(raw, raw2, 1))
            r = gf_blob_proof(base, c, verbose=False)
            report('NC7 the masked-blob read-back fails on a doctored blob', not r['ok'])
        else:
            report('NC7 the masked-blob read-back fails on a doctored blob', False,
                   'no decodable state blob on that page')

        # NC8 — JSON-LD is compared as data: a value flip must FAIL
        c = _clone(cand, os.path.join(work, 'c5'))
        p = os.path.join(c, 'formulas__calming-soft-chews.html')
        s = read(p)
        blk = json_blocks(s)
        if blk:
            flipped = blk[0].replace('"name"', '"nome"', 1)
            _write(p, s.replace(blk[0], flipped, 1))
            r = invariants(decl, base, c, verbose=False)
            report('NC8 the json-ld data comparison fails on a renamed key', not r['ok'])
        else:
            report('NC8 the json-ld data comparison fails on a renamed key', False,
                   'no ld+json block on that page')
    finally:
        shutil.rmtree(work, ignore_errors=True)

    if verbose:
        print('  %s  named negative controls: every control that must fail, failed'
              % ('PASS' if ok else 'FAIL'))
    return {'ok': ok, 'rows': rows}


# ------------------------------------------------------------------ source side

def _live_of(rel, text, prune):
    """The comment-blanked twin of one theme file, or None for a language this
    gate has no stripper for. Chosen by extension, not by target name, so adding
    a file to a declaration cannot silently skip the blanking."""
    if rel.endswith('.css'):
        return prune.strip_comments(text)
    if rel.endswith('.html'):
        return strip_html_comments(text)
    if rel.endswith('.php') or rel.endswith('.js'):
        return h6.strip_js_comments(text)
    return None


def source_checks(decl, theme, verbose=True):
    """The theme-side claims a rendered capture cannot see.

    Three of them matter most and none is visible in a page: the switch's CSS,
    because style.css is an external file the page only links; the deleted
    selectors, because a rule that nothing matches renders identically to no rule
    at all; and — from H7b — WHICH element a handler is bound to, because
    H7b's 84 data-sf-inquiry-open occurrences are the same 84 whether the script
    binds both openers or only the first one, and only the second is a bug. The
    comments are blanked for the absence checks — a rule or a string a comment
    merely NAMES is not a survivor, and this check failed on exactly that the
    first time it ran.

    Not checked here: that the bytes this gate declares as the expected edit are
    the bytes the theme prints. That is the main proof's job (it applies the
    declaration to the declared pages and requires the result to equal the
    candidate) and the coverage pass (which counts the result on the raw
    candidate).
    """
    prune = _load('b2d_h6_css_prune', os.path.join(HERE, 'b2d_h6_css_prune.py'))
    files = {
        'css': 'style.css',
        'php': 'functions.php',
        'js': 'assets/js/formula-gallery.js',
    }
    files.update(decl.get('sources', {}))
    raw = {k: open(os.path.join(theme, rel), encoding='utf-8').read()
           for k, rel in files.items()}
    live = {}
    for k, rel in files.items():
        live[k] = raw[k]
        twin = _live_of(rel, raw[k], prune)
        if twin is not None:
            live[k + '_live'] = twin
    ok = True
    rows = []
    for label, target, pat, want in decl['source']:
        n = len(re.findall(pat, live[target]))
        good = (n > 0) if want else (n == 0)
        ok &= good
        rows.append({'label': label, 'target': target, 'want': want, 'got': n, 'ok': good})
        if verbose:
            print('  %-52s %-9s %-4s %s'
                  % (label, target, 'x%d' % n, 'ok' if good else 'FAIL'))

    if decl.get('source_body'):
        m = re.search(r'\nfunction sinofresh_formula_gallery\(.*?\n\}\n', live['php'], re.S)
        body = m.group(0) if m else ''
        if not body:
            ok = False
            if verbose:
                print('  %-52s FAIL  the renderer could not be located' % 'renderer body')
        for label, needle, want in decl['source_body']:
            n = body.count(needle)
            good = (n > 0) if want else (n == 0)
            ok &= good
            rows.append({'label': label, 'target': 'renderer body', 'want': want,
                         'got': n, 'ok': good})
            if verbose:
                print('  %-52s %-9s %-4s %s'
                      % (label, 'renderer', 'x%d' % n, 'ok' if good else 'FAIL'))

    if verbose:
        print('  %s  source: the theme-side claims hold' % ('PASS' if ok else 'FAIL'))
    return {'ok': ok, 'rows': rows}


# ---------------------------------------------------------------------- driver

def parse(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--batch', required=True, choices=sorted(BATCHES))
    ap.add_argument('--base')
    ap.add_argument('--cand')
    ap.add_argument('--aa', metavar='DIR2')
    ap.add_argument('--matrix', action='store_true')
    ap.add_argument('--negctl', action='store_true')
    ap.add_argument('--source', action='store_true')
    ap.add_argument('--theme', default=os.path.join(ROOT, 'sinofresh-theme'))
    ap.add_argument('--skip-readback', action='store_true')
    ap.add_argument('--json')
    return ap.parse_args(argv)


def main(argv=None):
    args = parse(argv)
    decl = BATCHES[args.batch]
    out = {'batch': args.batch, 'name': decl['name']}
    ok = True
    print('== %s ==' % decl['name'])

    if args.source:
        r = source_checks(decl, args.theme)
        out['source'] = r
        ok &= r['ok']
    else:
        if not (args.base and args.cand):
            print('--base and --cand are required unless --source is given')
            return 2
        if args.aa:
            print('== A/A: two captures of the same state ==')
            r = aa(args.cand, args.aa)
            out['aa'] = r
            ok &= r['ok']
        print('== main proof: the declared edit, and nothing else ==')
        r = main_proof(decl, args.base, args.cand)
        out['main'] = r
        ok &= r['ok']
        print('== coverage: the declared old strings are gone, the new ones are here ==')
        r = coverage(decl, args.base, args.cand)
        out['coverage'] = r
        ok &= r['ok']
        print('== invariants: the counts not tied to the declaration ==')
        r = invariants(decl, args.base, args.cand)
        out['invariants'] = r
        ok &= r['ok']
        if not args.skip_readback:
            print('== masked-blob read-back: what the mask erased ==')
            r = gf_blob_proof(args.base, args.cand)
            out['readback'] = r
            ok &= r['ok']
        if args.matrix:
            print('== sabotage matrix ==')
            r = matrix(decl, args.base, args.cand)
            out['matrix'] = r
            ok &= r['ok']
        if args.negctl:
            print('== named negative controls ==')
            r = negctl(decl, args.base, args.cand, args.theme)
            out['negctl'] = r
            ok &= r['ok']

    print('\n%s  batch H7 gate (%s)' % ('PASS' if ok else 'FAIL', args.batch))
    if args.json:
        json.dump(out, open(args.json, 'w'), indent=1)
        print('  json -> %s' % args.json)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())

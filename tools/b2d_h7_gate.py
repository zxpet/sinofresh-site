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
              make a real difference mean anything. DIR2 must be a second
              capture taken on the same install as --cand: if the two carry
              different theme version tokens they are captures of different
              states and the run ABORTS (H7c was first run the other way round,
              which produced 75 wall-of-red diffs that read like a regression).
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
        ('the phone step is 26px AND follows the rule it steps',
         'css',
         # Contents alone are not the claim. A media query adds no specificity,
         # so a 480px override placed ABOVE the base rule is dead at every width
         # — which is how the first cut of this batch shipped, and what the
         # browser pass caught at 420px. The regex therefore spans from the base
         # rule to the media block, which only matches while the order holds.
         r'\.sf-fdetail2__title \{[^}]*font-size: 32px;[\s\S]*?'
         r'@media \(max-width: 480px\) \{\s*\.sf-fdetail2__title \{\s*font-size: 26px;',
         True),
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


# ------------------------------------------------------------------ H7c -----
# This batch runs the proof in the OTHER direction, and that is the whole reason
# `mode` exists.
#
# H7a and H7b replaced a string the baseline already carried, so the expected
# page could be BUILT from the baseline. H7c ADDS markup whose content is
# per-record — eight rows on one formula, ten on another — so there is no fixed
# string to splice into the baseline. Two ways out, and only one of them is
# honest:
#
#   * reconstruct the table from the baseline's own copy (the dosage-form crumb,
#     the parsed spec line, the ingredient pills are all somewhere on the page).
#     That means teaching the gate to render, and a gate that renders is a gate
#     that can agree with a broken renderer — the same homeopathy the H6 scan
#     rejected when it refused to re-derive a value it was supposed to measure.
#   * REMOVE the declared region from the candidate and require what is left to
#     equal the baseline. Nothing is re-derived; the payload is simply declared
#     rather than built.
#
# The second one has a price and it is paid in NC13: a region removed whole is
# not compared internally, so the payload's own bytes are invisible to the main
# proof. That is not a hole to paper over — it is a division of labour. The
# payload's CONTENT is owned by the coverage pass (which counts on the raw
# candidate), its PLACEMENT by the `order` invariant, and its per-page shape by
# `scoped`. Each of those three is sabotage-tested below.
H7C_PAYLOAD = re.compile(
    # The leading \s* is not cosmetic: a block template's blank lines are page
    # bytes too, so the inserted block brought its own newlines with it. Deleting
    # the comment and the section but leaving those behind left three extra
    # newlines on all 42 pages and the proof failed on exactly that — correctly.
    r'\s*<!-- H7c: the spec sheet\..*?-->\s*'
    r'<section class="sf-fdetail-specs">.*?</section>',
    re.S,
)


def _h7c_transform(text):
    """Delete the declared payload. One section, no nested section inside it,
    so the non-greedy match ends where the band does."""
    return H7C_PAYLOAD.subn('', text)


def _h7c_dead_phone_step(css):
    """The batch H7b mistake, re-made on purpose: lift the 768 step out and put
    it ABOVE the rule it means to override. A media query adds no specificity,
    so that is the version which is dead at every width, and the source pass has
    to say so."""
    i = css.find('@media (max-width: 768px) {\n\t.sf-fdetail-specs {')
    if i < 0:
        return css
    depth, j = 0, i
    while j < len(css):
        if css[j] == '{':
            depth += 1
        elif css[j] == '}':
            depth -= 1
            if depth == 0:
                break
        j += 1
    block = css[i:j + 1] + '\n'
    rest = css[:i] + css[j + 1:]
    anchor = '.sf-fdetail-specs {\n\tpadding: 48px 0;'
    if anchor not in rest:
        return css
    return rest.replace(anchor, block + anchor, 1)


def _is_formula_detail(name):
    """The 42 detail pages: /formulas/<slug>/ and /zh/formulas/<slug>/.

    The two archives are stored as `formulas` and `zh__formulas`, so neither
    prefix catches them — which is exactly the claim: the band is on the detail
    pages and nowhere else, and `scoped` says so per page rather than in total.
    """
    return name.startswith('formulas__') or name.startswith('zh__formulas__')


BATCHES['h7c'] = {
    'name': 'H7c — the spec sheet, twelve rows at the top of the reading area',
    'mode': 'delete',
    'tokens': [
        ('?ver=2.10.63', '?ver=2.10.64'),                        # style.css
    ],
    'transform': _h7c_transform,
    'applies': 42,
    'coverage': [
        # Absent from the candidate, counted on the raw bytes. Only one, because
        # this batch removes nothing: the payload is new markup.
        ('?ver=2.10.63', 0),
    ],
    'insertions': [
        # Present on the candidate, at a declared total. The first two are
        # structural — one band and two column groups per detail page — and the
        # rest are row labels, which is the payload's CONTENT. The main proof
        # cannot see any of them (mode: delete removes the payload whole), so
        # these counts are not a second opinion, they are the only opinion.
        ('?ver=2.10.64', 75),
        ('class="sf-fdetail-specs"', 42),
        ('sf-fdetail-specs__group"', 84),
        ('>Dosage Form<', 42),
        ('>Unit Weight<', 42),
        ('>Shelf Life<', 42),
        ('>Main Ingredients<', 42),
        ('>Place of Origin<', 42),
        ('>OEM / ODM<', 42),
    ],
    'counts': [
        # (label, string, base total, candidate total) — BOTH sides measured.
        # The three rows below already existed elsewhere on the site; each gains
        # exactly one per detail page, which is what says the new band is the
        # thing that moved them and not some other edit.
        ('MOQ gains one row per detail page', '>MOQ<', 18, 60),
        ('Certifications gains one row per page', '>Certifications<', 58, 100),
        ('the origin line gains one row per page', 'Linyi, Shandong, China', 154, 196),
        # And the rows the empty-value rule has to DROP. Zero on both sides, so
        # they fail the moment the renderer prints an empty row instead of
        # skipping it — which is the whole contract, and the only way a count
        # can state a row that must not exist.
        ('no empty Applicable Pet row is printed', '>Applicable Pet<', 0, 0),
        ('no empty Life Stage row is printed', '>Life Stage<', 0, 0),
        # The thirteenth row the brief offered and this batch dropped. It had
        # two occurrences before and keeps them, which is what "dropped" means
        # in bytes.
        ('no Lead Time row is added', '>Lead Time<', 2, 2),
        # The two data-dependent rows. They move with the DATA, not with the
        # code: Pack Size exists on ten of the 21 records, Shape on one.
        ('Pack Size is printed only where the spec line has one', '>Pack Size<', 40, 60),
        ('Shape is printed only on the record that has it', '>Shape<', 0, 2),
        # Everything the batch did not touch.
        ('the media parameter list is untouched', 'sf-fdetail2__params', 42, 42),
        ('the actives band is untouched', 'sf-fdetail-actives__inner', 42, 42),
        ('the content band is untouched', 'sf-fdetail-content__inner', 42, 42),
        ('the parameter rows are untouched', 'sf-fdetail2__term', 234, 234),
    ],
    'unmoved': [
        ('media parameter list', r'sf-fdetail2__params', 42),
        ('actives band', r'sf-fdetail-actives__inner', 42),
        ('content band', r'sf-fdetail-content__inner', 42),
        ('H7b hero openers', r'data-sf-inquiry-open', 42),
        ('certification badges', r'sf-cert-badge', None),
    ],
    'per_page': [
        ('h1', r'<h1[ >]', 1),
    ],
    # Once per detail page, nowhere else. A site total of 42 would also be
    # produced by one page carrying 42 of them, so the claim is made per page.
    'scoped': [
        ('the spec sheet is on each detail page, once',
         'class="sf-fdetail-specs"', _is_formula_detail, 1),
        ('each detail page gets two column groups',
         'sf-fdetail-specs__group"', _is_formula_detail, 2),
    ],
    # Where the band SITS. The main proof cannot see this — a payload removed
    # whole is equally removed wherever it was — so placement is its own claim,
    # asserted on every detail page with both anchors required to be present.
    'order': [
        ('the spec sheet follows the media band', 'sf-fdetail2__params',
         'class="sf-fdetail-specs"', _is_formula_detail),
        ('and precedes the Specification band', 'class="sf-fdetail-specs"',
         'sf-fdetail__grid', _is_formula_detail),
        ('and precedes the Ingredients band', 'class="sf-fdetail-specs"',
         'sf-fdetail-actives__inner', _is_formula_detail),
    ],
    'h2_delta': None,
    'sources': {
        'tpl': 'templates/single-sf_formula.html',
    },
    # NC3/NC4 read these. Which string is the sharp one is batch-specific.
    'reinject': ('an old version token put back fails coverage',
                 'formulas__joint-support-soft-chews.html', '</head>',
                 '<link rel="stylesheet" href="style.css?ver=2.10.63">'),
    'delete': ('one column group deleted fails coverage',
               'formulas__calming-soft-chews.html', 'sf-fdetail-specs__group"'),
    'matrix': [
        # Every mutant must break the proof AND must actually have changed
        # something (a no-op reports INVALID, not pass).
        ('the spec sheet is never added',
         {'transform': (lambda t: (t, 0)), 'applies': 0}, None),
        ('the style token is not folded',
         {'tokens': []}, None),
        ('the payload is added but not declared',
         {'applies': 0}, None),
        # Deleting a payload that a page never had is a no-op on that page, so
        # this mutant leaves the diff EMPTY and is caught by the applied count
        # alone — which is why the matrix reports both numbers.
        ('the payload is missing from one page',
         {}, ('formulas__joint-support-soft-chews.html',
              lambda s: _h7c_transform(s)[0])),
        ('a stray character on one page',
         {}, ('formulas__calming-soft-chews.html',
              lambda s: s.replace('</body>', '<!-- stray --></body>', 1))),
    ],
    'nc_source': [
        ('NC9 the source pass fails when the phone step moves above its base rule',
         'style.css', _h7c_dead_phone_step, None),
        ('NC10 the source pass fails when the ingredient cap is removed',
         'functions.php', 'array_slice($ingredients, 0, 3)', '$ingredients'),
    ],
    'nc_page': [
        ('NC11 the scoped invariant fails on a spec sheet in the wrong page',
         'about.html',
         lambda s: s.replace('</body>', '<section class="sf-fdetail-specs"></section></body>', 1)),
        ('NC12 the scoped invariant fails when a detail page loses a group',
         'formulas__joint-support-soft-chews.html',
         lambda s: s.replace('class="sf-fdetail-specs__group"', 'class="sf-gone"', 1)),
    ],
    'nc_blind': ('formulas__joint-support-soft-chews.html',
                 '>Dosage Form<', '>Dosage Formx<'),
    'source': [
        # --- the template: the call site, and where it sits -------------------
        ('the template calls the spec-sheet shortcode', 'tpl_live',
         r'\[sf_formula_specs_table\]', True),
        ('...before the long copy', 'tpl_live',
         r'\[sf_formula_specs_table\][\s\S]*?\[sf_formula_body\]', True),
        ('...and before the Specification band', 'tpl_live',
         r'\[sf_formula_specs_table\][\s\S]*?\[sf_formula_detail\]', True),
        ('...and before the Ingredients band', 'tpl_live',
         r'\[sf_formula_specs_table\][\s\S]*?\[sf_formula_detail_actives\]', True),
        ('...and after the media band', 'tpl_live',
         r'\[sf_formula_params\][\s\S]*?\[sf_formula_specs_table\]', True),
        # --- the renderer: the claims a page cannot show ----------------------
        ('the renderer is registered', 'php_live',
         r"add_shortcode\('sf_formula_specs_table', 'sinofresh_formula_specs_table'\)", True),
        ('it guards the post type', 'php_live',
         r"function sinofresh_formula_specs_table\(\)[\s\S]{0,200}is_singular\('sf_formula'\)", True),
        ('Dosage Form is the taxonomy term name', 'php_live',
         r"\$rows\['Dosage Form'\] = esc_html\(\$form_name\)", True),
        ('Shape is read from the unregistered key', 'php_live',
         r"get_post_meta\(\$post_id, 'sf_formula_shape', true\)", True),
        ('Unit Weight is the parsed unit segment', 'php_live',
         r"\$rows\['Unit Weight'\] = esc_html\(trim\(\(string\) \$parts\['unit'\]\)\)", True),
        ('Pack Size is the parsed pack segment', 'php_live',
         r"\$rows\['Pack Size'\] = esc_html\(trim\(\(string\) \$parts\['pack'\]\)\)", True),
        ('Shelf Life is the parsed shelf segment', 'php_live',
         r"\$rows\['Shelf Life'\] = esc_html\(trim\(\(string\) \$parts\['shelf'\]\)\)", True),
        ('Main Ingredients stops at three', 'php_live',
         r"array_slice\(\$ingredients, 0, 3\)", True),
        ('MOQ reads the dosage page, not a new source', 'php_live',
         r"sinofresh_formula_spec_cell\(\$form_slug, 'MOQ'\)", True),
        ('Certifications reuses the existing reader', 'php_live',
         r"sf_formula_certifications_value\(\$form_slug\)", True),
        ('Place of Origin is a constant until H7e', 'php_live',
         r"\$rows\['Place of Origin'\] = esc_html\('Linyi, Shandong, China'\)", True),
        ('OEM / ODM is a constant until H7e', 'php_live',
         r"\$rows\['OEM / ODM'\] = esc_html\('Available'\)", True),
        ('no Lead Time row is added', 'php_live', r"\$rows\['Lead Time'\]", False),
        ('the split is over the rows actually rendered', 'php_live',
         r"\$half = \(int\) ceil\(count\(\$rows\) / 2\)", True),
        ('the band is emitted whole, zero bytes when empty', 'php_live',
         r"return '<section class=\"sf-fdetail-specs\"><div class=\"sf-fdetail-specs__inner\">'", True),
        ('the style token is bumped in the enqueue', 'php',
         r"wp_enqueue_style\('sinofresh-style', get_stylesheet_uri\(\), array\(\), '2\.10\.64'\)", True),
        ('no 2.10.63 enqueue survives', 'php_live', r"'2\.10\.63'", False),
        # --- the stylesheet: the geometry a page links rather than contains ---
        ('style.css declares 2.10.64', 'css', r'Version: 2\.10\.64', True),
        ('no 2.10.63 header survives', 'css', r'Version: 2\.10\.63', False),
        ('the band carries the white surface', 'css_live',
         r'\.sf-fdetail-specs \{[^}]*background-color: var\(--wp--preset--color--card-white\)', True),
        ('two columns on a desk', 'css_live',
         r'\.sf-fdetail-specs__inner \{[^}]*grid-template-columns: repeat\(2, minmax\(0, 1fr\)\)', True),
        ('a row is a label/value grid', 'css_live',
         r'\.sf-fdetail-specs__row \{[^}]*grid-template-columns: minmax\(150px, 40%\) minmax\(0, 1fr\)', True),
        # The ordering claim, as ONE chain. Each link is anchored twice — the
        # media query AND a marker only this band's rule carries — so the chain
        # cannot be satisfied by some other component's 1240/900/768 block later
        # in the file. This is the assertion H7b had to add after shipping a step
        # that sat above its own base rule and was dead at every width; a check
        # that only asserted the steps' contents would have passed that build.
        ('base rule, then 1240, then 900, then 768 — in that order', 'css_live',
         r'\.sf-fdetail-specs \{[^}]*background-color: var\(--wp--preset--color--card-white\);'
         r'[\s\S]{0,2200}@media \(max-width: 1240px\) \{[\s\S]{0,160}\.sf-fdetail-specs \{'
         r'[\s\S]{0,600}@media \(max-width: 900px\) \{[\s\S]{0,160}\.sf-fdetail-specs__inner \{'
         r'[\s\S]{0,1600}@media \(max-width: 768px\) \{[\s\S]{0,160}\.sf-fdetail-specs \{', True),
        ('the phone step is one column', 'css_live',
         r'@media \(max-width: 768px\) \{[\s\S]{0,260}\.sf-fdetail-specs__row \{[^}]*grid-template-columns: minmax\(0, 1fr\)', True),
        ('the chips are the outline-pill vocabulary', 'css_live',
         r'\.sf-fdetail-specs__chip \{[^}]*border-radius: 999px', True),
    ],
}


# ------------------------------------------------------------------- machinery

def fold(text, pairs):
    for old, new in pairs:
        text = text.replace(old, new)
    return text


def main_proof(decl, base, cand, verbose=True):
    """mask(transform(baseline)) == mask(candidate) — or, when the declaration
    says `mode: 'delete'`, mask(transform(candidate)) == mask(fold(baseline)).

    The two directions exist because there are two kinds of batch. H7a and H7b
    rewrote a string the baseline already carried, so the expected page could be
    BUILT from the baseline and the transform ran on it. H7c's payload is new
    markup whose content is per-record, so there is nothing fixed to splice in:
    the only honest proof is to REMOVE the declared region from the candidate
    and require the remainder to equal the baseline. Reconstructing that table
    from the baseline's own copy would have meant teaching the gate to render,
    and a gate that renders is a gate that can agree with a broken renderer.

    Read the direction off the declaration, never off the batch's name: the
    assertion is the same either way — everything outside the declared payload
    is byte-identical, and the payload is exactly as declared.
    """
    names = sorted(set(pages(base)) & set(pages(cand)))
    mode = decl.get('mode', 'insert')
    rows, applied, ok = [], 0, True
    for n in names:
        a = read(os.path.join(base, n + '.html'))
        b = read(os.path.join(cand, n + '.html'))
        if mode == 'delete':
            exp = fold(a, decl['tokens'])
            act, cnt = decl['transform'](b)
        else:
            act, cnt = decl['transform'](a)
            exp = fold(act, decl['tokens'])
        applied += cnt
        am, _ = mask(exp)
        bm, _ = mask(act)
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
        print('  %s  main proof: mask(transform(%s)) == mask(%s)'
              % ('PASS' if ok else 'FAIL',
                 'candidate' if mode == 'delete' else 'baseline',
                 'fold(baseline)' if mode == 'delete' else 'candidate'))
    return {'ok': ok, 'pages': len(names), 'differing': len(rows), 'applied': applied,
            'declared': decl['applies'], 'mode': mode, 'rows': rows[:8]}


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

    # A per-page count over a DECLARED SUBSET of the pages, which neither
    # `unmoved` (site totals) nor `per_page` (every page) can express. H7c adds
    # a band to 42 of the 75 pages, so "once per detail page" and "nowhere else"
    # are two different claims and both have to be made: a site total of 42
    # would also be produced by one page carrying 42 of them.
    for label, pat, scope, want in decl.get('scoped', []):
        bad = []
        for n in names:
            got = counts_of(read(os.path.join(cand, n + '.html')), pat)
            expect = want if scope(n) else 0
            if got != expect:
                bad.append((n, got))
        good = not bad
        ok &= good
        rows.append({'label': label, 'bad_pages': len(bad), 'ok': good,
                     'first': bad[:4]})
        if verbose:
            print('  %-28s pages off the declared count = %d %s  %s'
                  % (label, len(bad), bad[:3] if bad else '', 'ok' if good else 'FAIL'))

    # Where the new bytes SIT, which no other check can see. A page that carries
    # the band at the wrong address is byte-identical to one that carries it at
    # the right address as far as the main proof is concerned — with
    # `mode: delete` the payload is removed whole, so the proof is blind to
    # where it was. Order is asserted on every page in scope, and the page must
    # actually carry all three anchors or the check reports it rather than
    # passing vacuously on a find() that returned -1.
    for label, first, second, scope in decl.get('order', []):
        bad = []
        for n in names:
            if not scope(n):
                continue
            t = read(os.path.join(cand, n + '.html'))
            i, j = t.find(first), t.find(second)
            if i < 0 or j < 0 or i > j:
                bad.append((n, i, j))
        good = not bad
        ok &= good
        rows.append({'label': label, 'bad_pages': len(bad), 'first': bad[:4], 'ok': good})
        if verbose:
            print('  %-28s pages out of order = %d %s  %s'
                  % (label, len(bad), bad[:2] if bad else '', 'ok' if good else 'FAIL'))

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


AA_VER_RE = re.compile(r'\?ver=([0-9][0-9A-Za-z._-]*)')


def _ver_profile(d):
    """Which version tokens a capture directory carries, and on how many pages.

    A/A compares two captures of ONE state. If the two directories carry
    different tokens, they are captures of two different states -- which is an
    operator error, not a regression -- and every page would differ. That case
    is named below and aborts, instead of printing 75 wall-of-red diffs that
    read exactly like a real breakage. Same discipline as asserting which
    artifact a request actually fetched: a comparison against the wrong copy
    must not be able to report anything at all.
    """
    prof = {}
    for n in pages(d):
        for v in set(AA_VER_RE.findall(read(os.path.join(d, n + '.html')))):
            prof[v] = prof.get(v, 0) + 1
    return prof


def _page_diffs(dir_a, dir_b):
    """Per-page first-difference under the mask set. No policy, no guard.

    The primitive NC6 needs: it compares two states that are *supposed* to
    differ, to prove the comparison is sensitive at all.
    """
    names = sorted(set(pages(dir_a)) & set(pages(dir_b)))
    rows = []
    for n in names:
        am, _ = mask(read(os.path.join(dir_a, n + '.html')))
        bm, _ = mask(read(os.path.join(dir_b, n + '.html')))
        if am != bm:
            i = first_diff(am, bm)
            rows.append({'page': n, 'a': ctx(am, i), 'b': ctx(bm, i)})
    return names, rows


def aa(dir_a, dir_b, verbose=True, labels=('--cand', '--aa'), strict=True):
    """A/A: two captures of ONE state must be identical under this mask set.

    strict=True (the real A/A) additionally refuses the two ways this check can
    be quietly wrong rather than red:

      * page sets that differ -> FAIL here, instead of silently comparing the
        intersection (comparing 40 of 75 pages looks exactly like a pass);
      * directories carrying different version tokens -> abort, because they are
        captures of two different states. Without this, an operator who points
        --aa at a baseline-era copy gets 75 wall-of-red diffs, which read like a
        regression and send you hunting in the wrong place. Same discipline as
        asserting which artifact a request actually fetched.

    strict=False is for NC6, which must be able to see "different state -> not
    ok" as a *result*. The guard exists so that that cannot happen by accident.
    """
    set_a, set_b = set(pages(dir_a)), set(pages(dir_b))
    if set_a != set_b:
        only_a = sorted(set_a - set_b)
        only_b = sorted(set_b - set_a)
        if verbose:
            print('  %-12s pages: %d' % (labels[0], len(set_a)))
            print('  %-12s pages: %d' % (labels[1], len(set_b)))
            print('  only in %s: %s' % (labels[0], ', '.join(only_a[:8]) or '-'))
            print('  only in %s: %s' % (labels[1], ', '.join(only_b[:8]) or '-'))
            print('  FAIL  A/A: the two captures do not cover the same pages')
        return {'ok': False, 'pages': 0, 'differing': 0, 'rows': [],
                'only_a': only_a, 'only_b': only_b}
    if strict:
        prof_a, prof_b = _ver_profile(dir_a), _ver_profile(dir_b)
        if prof_a != prof_b:
            raise SystemExit(
                'FATAL A/A: these are captures of two DIFFERENT states, not two '
                'captures of one.\n  %s tokens: %s\n  %s tokens: %s\n'
                'Pass a second capture taken on the same install as the first.'
                % (labels[0], prof_a, labels[1], prof_b))
    names, rows = _page_diffs(dir_a, dir_b)
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
                # Both numbers, because the two catch different things: a
                # mutation inside the payload leaves the diff at 0 and is caught
                # by the applied count, and a mutation elsewhere is the reverse.
                rows.append((name, 'caught', 'differing pages = %d, applied = %d/%d'
                             % (r['differing'], r['applied'], d['applies'])))
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

        # NC6 — A/A is a real signal: A/A against the baseline must FAIL.
        # strict=False here on purpose: this control asserts the comparison
        # *notices* a state difference, while the strict guard's job is to make
        # that same difference impossible to feed in by accident. Running this
        # with strict=True would abort instead of reporting, and the control
        # would prove nothing about the comparison itself.
        r = aa(cand, base, verbose=False, strict=False, labels=('--cand', '--base'))
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

        # NC9/NC10 — the source assertions are signals, not decoration. Each
        # mutant is applied to a COPY of the theme in a temp tree; a source
        # check that survives its own sabotage is a check that cannot fail, and
        # the CSS-order claim in particular only exists because H7b shipped the
        # dead-step version of it.
        for label, rel, needle, replacement in decl.get('nc_source', []):
            t = _clone(theme, os.path.join(work, 'theme'))
            p = os.path.join(t, rel)
            before = read(p)
            # A callable is for the mutations a literal replace cannot express —
            # H7c's is a REORDER, which is the only way to rebuild the dead step.
            after = needle(before) if callable(needle) else before.replace(needle, replacement, 1)
            if after == before:
                report(label, False, 'the mutant needle is not in %s' % rel)
                continue
            _write(p, after)
            r = source_checks(decl, t, verbose=False)
            report(label, not r['ok'])

        # NC11/NC12 — the page-scoped counts and the order claim are each
        # breakable by a page edit the MAIN PROOF cannot see, for the same
        # reason: the payload is removed whole, so nothing about it is compared.
        for label, page, fn in decl.get('nc_page', []):
            c = _clone(cand, os.path.join(work, 'ncp'))
            p = os.path.join(c, page)
            before = read(p)
            after = fn(before)
            if after == before:
                report(label, False, 'the mutant changed nothing')
                continue
            _write(p, after)
            r = invariants(decl, base, c, verbose=False)
            report(label, not r['ok'])

        # NC13 — and the hole this batch's direction opens, stated on purpose.
        # With `mode: delete` the payload is removed whole, so its own bytes are
        # NOT compared by the main proof: renaming a row label inside it must
        # leave the main proof GREEN. That is not a bug to hide — it is why the
        # coverage pass, which counts on the raw candidate, owns the payload's
        # content. An NC that only showed the failure would leave the blast
        # radius unmeasured.
        page, needle, replacement = decl['nc_blind']
        c = _clone(cand, os.path.join(work, 'ncb'))
        p = os.path.join(c, page)
        _write(p, read(p).replace(needle, replacement, 1))
        blind = main_proof(decl, base, c, verbose=False)['ok']
        caught = not coverage(decl, base, c, verbose=False)['ok']
        report('NC13 the main proof is blind to the payload, coverage is not',
               blind and caught,
               'page=%s main_green=%s coverage_red=%s' % (page, blind, caught))

        # NC14 — the strict A/A guard is itself a signal. It exists because this
        # batch was run with --aa pointed at a baseline-era capture, which showed
        # up as 75 wall-of-red diffs that read exactly like a regression. A guard
        # nobody has watched fire is a comment, so this one is made to fire.
        try:
            aa(cand, base, verbose=False, labels=('--cand', '--base'))
            report('NC14 strict A/A refuses a capture of another state', False,
                   'it compared two states instead of aborting')
        except SystemExit:
            report('NC14 strict A/A refuses a capture of another state', True)

        # NC15 — and a capture directory that is short of pages must FAIL, not
        # silently shrink the comparison to the intersection: comparing 74 of 75
        # pages looks exactly like comparing all of them.
        c = _clone(cand, os.path.join(work, 'ncaa'))
        missing = sorted(pages(c))[0]
        os.remove(os.path.join(c, missing + '.html'))
        r = aa(cand, c, verbose=False)
        report('NC15 A/A fails when the two captures cover different pages',
               (not r['ok']) and r['only_a'] == [missing],
               'short by %s' % missing)

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
    ap.add_argument('--aa', metavar='DIR2',
                    help='second capture taken on the SAME install as --cand')
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

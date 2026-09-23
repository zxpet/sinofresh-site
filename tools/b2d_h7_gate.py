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
from urllib.parse import urlsplit

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


# ------------------------------------------------------------------ H7d -----
# The first batch that does two opposite things to the same band, and the first
# that needs the `symmetric` direction — because neither side can be built from
# the other.
#
#   * it ADDS a region: seven choice groups, whose content is per-record and
#     which the baseline does not carry in that shape anywhere;
#   * it REMOVES rows: the same seven parameters leave .sf-fdetail2__params.
#
# `insert` would need the added region's bytes. `delete` would need the removed
# rows' bytes. Both are per-record, so neither is available, and reconstructing
# either one means teaching the gate to render — the homeopathy H7c already
# refused. What is left is a single pure function applied to BOTH sides: delete
# the added band, the added script and the moved rows wherever they are found,
# then require the remainders to be identical byte for byte.
#
# The blind spot is the one H7c declared, and it stays a division of labour
# rather than a hole: a region deleted from both sides is not compared. The
# band's CONTENT is owned by the coverage pass (counts on the raw candidate),
# its per-page SHAPE by `scoped`, its PLACEMENT by `order` — and the fact that
# the moved values SURVIVED is its own count, because a rename that dropped one
# flavour and duplicated another would keep every count that only asks how many
# rows there are.

H7D_MOVED_LABELS = (
    'Flavor', 'Piece Weight', 'Pack Size', 'Suitable For', 'Life Stage',
    'Container Type', 'Quantity &amp; Pricing',
)

# One parameter row: its <dt> and the <dd> that follows. Bounded by the next
# </dd>, which is safe here because no row nests one — the tier row puts a
# <table> inside its <dd>, and that table contains no </dd>.
H7D_MOVED_ROW = re.compile(
    r'<dt class="sf-fdetail2__term">(?:%s)</dt>'
    r'<dd class="sf-fdetail2__value">.*?</dd>'
    % '|'.join(re.escape(x) for x in H7D_MOVED_LABELS), re.S)

# The added band. Bounded by the element that follows it, not by counting
# </div>s: <dl class="sf-fdetail2__params"> occurs once per page, so a lookahead
# pins the end without this pattern having to know how deep the band nests. The
# trailing newline is part of the insertion — the band arrives on a line of its
# own and the <dl> was already on the next one.
H7D_BAND = re.compile(
    r'<div class="sf-fdetail-config" data-sf-config>.*?</div>\n'
    r'(?=<dl class="sf-fdetail2__params">)', re.S)

# The added <script>. Path-independent on purpose: the same theme renders from
# sinofresh-theme-preflight on the dev box and from sinofresh-theme in
# production, and a declaration that spelled either directory name would be a
# declaration about the harness rather than about the product.
H7D_SCRIPT = re.compile(
    r'\n<script id="sinofresh-config-js" src="[^"]*assets/js/config\.js\?ver=[0-9.]+"></script>')


def _h7d_transform(text):
    """Delete this batch's added region, its added script and its removed rows,
    wherever it finds them. Applied to BOTH sides (mode: symmetric)."""
    text, band = H7D_BAND.subn('', text)
    text, script = H7D_SCRIPT.subn('', text)
    text, rows = H7D_MOVED_ROW.subn('', text)
    return text, band + script + rows


def _h7d_partial(band=True, script=True, rows=True):
    """The sabotage variants, each leaving ONE of the three declarations out.
    `rows=False` is the batch that adds the controls without taking the rows out
    of the list; `band=False` is the one that adds them without declaring them;
    `script=False` is the one that forgets the enqueue."""
    def run(text):
        n = 0
        if band:
            text, k = H7D_BAND.subn('', text)
            n += k
        if script:
            text, k = H7D_SCRIPT.subn('', text)
            n += k
        if rows:
            text, k = H7D_MOVED_ROW.subn('', text)
            n += k
        return text, n
    return run


# The dialog's carrier field, as a substitution. A FIXED insertion on all 42
# pages, so it is declared as a token rather than as a region the transform
# deletes — and the difference matters. As a token, the bytes on either side of
# it stay inside the comparison, so the main proof still says WHERE the carrier
# sits (between the formula's ts field and the honeypot). As a deleted region it
# would only say that a carrier exists somewhere, which is already the coverage
# pass's claim.
H7D_CARRIER = ('name="ts" value="0"><div class="sf-inquiry-form__trap"',
               'name="ts" value="0"><input type="hidden" name="config" value="">'
               '<div class="sf-inquiry-form__trap"')


def _h7d_dead_phone_step(css):
    """The batch H7b mistake, re-made on purpose for THIS band: lift the phone
    step out and put it ABOVE the base rule it means to override. A media query
    adds no specificity, so that is the version which is dead at every width,
    and the source pass has to say so. Without this control the ordering claim
    is decoration — a check nobody has watched fail is a comment."""
    anchor = '.sf-fdetail-config {\n\tmargin: 0 0 16px;'
    i = css.find('@media (max-width: 768px) {\n\t.sf-fdetail-config__open {')
    if i < 0 or anchor not in css:
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
    return rest.replace(anchor, block + anchor, 1)


def _h7d_drawer_out_of_query(css):
    """NC24: lift the opened-list rule OUT of the 768px query.

    The check it guards is a CONTAINMENT claim — the drawer may only leave the
    flow inside the phone step — and containment is exactly what a character
    budget stops measuring as the block around the rule grows. This mutant keeps
    every byte of the file and only moves the rule to the other side of the
    brace, so a check that has quietly become "the selector exists somewhere"
    fails here, while one that still reads the braces does not.
    """
    rule = re.search(r'\n(\t\.sf-fdetail-config--open \.sf-fdetail-config__list '
                     r'\{.*?\n\t\})\n', css, re.S)
    if not rule:
        return css
    mq = css.rfind('\n@media (max-width: 768px) {', 0, rule.start())
    if mq < 0:
        return css
    s = rule.start() + 1
    return (css[:mq + 1] + rule.group(1) + '\n' + css[mq + 1:s]
            + css[rule.end():])


BATCHES['h7d'] = {
    'name': 'H7d — seven parameter rows become choices, and leave the list they were in',
    'mode': 'symmetric',
    'tokens': [
        ('?ver=2.10.64', '?ver=2.10.65'),                       # style.css
        ('inquiry.js?ver=1.1.0', 'inquiry.js?ver=1.2.0'),       # inquiry.js
        H7D_CARRIER,                                            # the dialog's field
    ],
    'transform': _h7d_transform,
    # Two sides, two numbers. 84 = 42 bands + 42 script tags on the candidate;
    # 66 = the rows that left the parameter lists on the baseline, which is
    # 2 + 42 + 20 + 2 and matches the 234 -> 168 term count below. Declaring one
    # number for both sides would let each side be wrong in a way the other
    # cancels.
    'applies': 84,
    'applies_base': 66,
    'coverage': [
        # Absent from the candidate, counted on the raw bytes.
        ('?ver=2.10.64', 0),
        ('inquiry.js?ver=1.1.0', 0),
    ],
    'insertions': [
        # Present on the candidate, at a declared total. The first two are
        # structural and the rest are the payload's CONTENT, which the main
        # proof cannot see (the band is deleted from both sides): these counts
        # are not a second opinion, they are the only opinion.
        ('?ver=2.10.65', 75),
        ('<div class="sf-fdetail-config" data-sf-config>', 42),
        ('id="sinofresh-config-js"', 42),
        ('inquiry.js?ver=1.2.0', 42),
        ('data-sf-config-summary', 42),
        ('data-sf-config-note', 42),
        ('data-sf-config-group="', 68),
        ('class="sf-fdetail-config__opt"', 132),
        ('class="sf-fdetail-config__input"', 132),
        # The dialog carries the choice in one hidden field. It is declared as a
        # token, which is what keeps this count honest as a *content* claim
        # rather than the only claim there is.
        ('<input type="hidden" name="config" value="">', 42),
    ],
    'counts': [
        # The seven labels leave the parameter list, measured per label so a
        # renderer that dropped the wrong row cannot hide behind the total.
        ('Flavor leaves the parameter list', 'sf-fdetail2__term">Flavor<', 2, 0),
        ('Piece Weight leaves it', 'sf-fdetail2__term">Piece Weight<', 42, 0),
        ('Pack Size leaves it', 'sf-fdetail2__term">Pack Size<', 20, 0),
        ('Quantity & Pricing leaves it', 'sf-fdetail2__term">Quantity &amp; Pricing<', 2, 0),
        # The four rows that are NOT choices stay, unchanged.
        ('Shelf life stays', 'sf-fdetail2__term">Shelf life<', 42, 42),
        ('Packaging stays', 'sf-fdetail2__term">Packaging<', 42, 42),
        ('Certifications stays', 'sf-fdetail2__term">Certifications<', 42, 42),
        ('Lead time stays', 'sf-fdetail2__term">Lead time<', 42, 42),
        ('the list loses exactly the 66 rows the seven labels accounted for',
         'sf-fdetail2__term', 234, 168),
        # The same seven arrive as groups, with the same labels: the band is the
        # rows' new address, not a second, differently-worded set of names.
        ('the band names Flavor', 'sf-fdetail-config__label">Flavor<', 0, 2),
        ('...Piece Weight', 'sf-fdetail-config__label">Piece Weight<', 0, 42),
        ('...Pack Size', 'sf-fdetail-config__label">Pack Size<', 0, 20),
        ('...Quantity & Pricing', 'sf-fdetail-config__label">Quantity &amp; Pricing<', 0, 2),
        # The values MOVED rather than being replaced. A rename that dropped one
        # flavour and duplicated another keeps every count that only asks how
        # many rows there are; these four do not.
        ('the flavor values survive the move', '>Chicken</span>', 2, 2),
        ('...and Beef', '>Beef</span>', 2, 2),
        ('...and Lamb', '>Lamb</span>', 2, 2),
        ('...and Salmon', '>Salmon</span>', 2, 2),
        # What left, and what it left with.
        ('the old chip vocabulary is what left the list', 'sf-fdetail2__chip', 14, 0),
        ('the tier table left with its row', 'sf-fdetail2__tiers', 2, 0),
        # The empty library has no images yet, so the picker degrades to a
        # dashed slot. 14 = 7 containers x the 2 pages of the one record that
        # has a container. Had it rendered <img src=""> these would be broken
        # icons instead, and the count would be 0.
        ('the empty library ships dashed slots, not broken images',
         'sf-fdetail-config__img--empty', 0, 14),
        # The hint a reader sees. `>Per per <` is the doubled word the first cut
        # printed on all 20 pack pages, and a count of "how many hints exist"
        # cannot see a doubled word — which is why the assertion names it. The
        # other two are the same fact read positively: the tail is shown as a
        # sentence, 14 pages of bottles and 6 of bags.
        ('no hint reads "Per per"', 'sf-fdetail-config__hint">Per per ', 0, 0),
        ('the pack hint reads as a sentence', 'sf-fdetail-config__hint">Per bottle<', 0, 14),
        ('...and the bag one', 'sf-fdetail-config__hint">Per bag<', 0, 6),
        # Every option is rendered and none of them is ticked. The bare word
        # "checked" occurs twice on both sides in a pre-existing form, which is
        # why the claim is the attribute and not the word.
        ('no option is pre-checked', 'checked="checked"', 0, 0),
        # Everything the batch did not touch.
        ('the H7c spec sheet is untouched', 'sf-fdetail-specs__group"', 84, 84),
        ('the actives band is untouched', 'sf-fdetail-actives__inner', 42, 42),
        ('the content band is untouched', 'sf-fdetail-content__inner', 42, 42),
        ('the inquiry dialog is untouched', 'class="sf-inquiry-modal"', 42, 42),
        ('the column title is untouched', 'sf-fdetail2__title', 42, 42),
    ],
    'unmoved': [
        ('H7c spec sheet', r'sf-fdetail-specs__inner', 42),
        ('actives band', r'sf-fdetail-actives__inner', 42),
        ('content band', r'sf-fdetail-content__inner', 42),
        ('column title', r'sf-fdetail2__title', 42),
        ('H7b hero openers', r'data-sf-inquiry-open', 42),
        ('inquiry dialog', r'class="sf-inquiry-modal"', 42),
        ('certification badges', r'sf-cert-badge', None),
    ],
    'per_page': [
        ('h1', r'<h1[ >]', 1),
    ],
    # Once per detail page, nowhere else. A site total of 42 would also be
    # produced by one page carrying 42 of them, so the claim is made per page.
    # The "nowhere else" half is not a separate entry: `scoped` requires ZERO on
    # every page outside the declared subset, which is what makes one entry here
    # worth more than a site total. (The first cut of this batch added a third
    # entry with the predicate inverted, expecting zero on the detail pages too,
    # and the gate failed on all 42 — correctly.)
    'scoped': [
        ('the configurator is on each detail page, once',
         '<div class="sf-fdetail-config" data-sf-config>', _is_formula_detail, 1),
        ('so is its script', 'id="sinofresh-config-js"', _is_formula_detail, 1),
        ('and the dialog carries one selection field',
         '<input type="hidden" name="config" value="">', _is_formula_detail, 1),
    ],
    # Where the band SITS. The main proof cannot see this — a region deleted from
    # both sides is equally deleted wherever it was.
    'order': [
        ('the choices sit below the column title', 'sf-fdetail2__title',
         '<div class="sf-fdetail-config" data-sf-config>', _is_formula_detail),
        ('and above the parameter list', '<div class="sf-fdetail-config" data-sf-config>',
         '<dl class="sf-fdetail2__params">', _is_formula_detail),
        ('which still precedes the H7c spec sheet', '<dl class="sf-fdetail2__params">',
         'class="sf-fdetail-specs"', _is_formula_detail),
        ('the carrier sits in the dialog, after the formula id',
         'name="formula" value=', '<input type="hidden" name="config" value="">',
         _is_formula_detail),
    ],
    'h2_delta': None,
    'sources': {
        'js': 'assets/js/config.js',
        'inquiry': 'assets/js/inquiry.js',
        'tpl': 'templates/single-sf_formula.html',
    },
    # The renderer whose body the `source_body` claims are about.
    'body_of': 'sinofresh_formula_config',
    'source_body': [
        ('nothing is pre-checked in the renderer', 'checked', False),
        ('the summary ships empty and hidden', 'data-sf-config-summary hidden', True),
        ('an empty container library degrades to a dashed slot',
         'sf-fdetail-config__img--empty', True),
        ('the band is emitted whole, zero bytes when there is nothing',
         "return '<div class=\"sf-fdetail-config\" data-sf-config>'", True),
    ],
    # NC3/NC4 read these.
    'reinject': ('an old version token put back fails coverage',
                 'formulas__calming-soft-chews.html', '</head>',
                 '<link rel="stylesheet" href="style.css?ver=2.10.64">'),
    'delete': ('one configurator deleted fails coverage',
               'formulas__calming-soft-chews.html',
               '<div class="sf-fdetail-config" data-sf-config>'),
    'matrix': [
        ('the moved rows are never taken out of the parameter list',
         {'transform': _h7d_partial(rows=False)}, None),
        ('the band is added but not declared',
         {'transform': _h7d_partial(band=False)}, None),
        ('the added script is not declared',
         {'transform': _h7d_partial(script=False)}, None),
        ('the old style token is not folded',
         {'tokens': [('inquiry.js?ver=1.1.0', 'inquiry.js?ver=1.2.0'), H7D_CARRIER]}, None),
        # Deleting a band a page never had is a no-op on the bytes — the
        # transform would have removed it anyway — so this mutant leaves the
        # diff EMPTY and is caught by the applied count alone, which is why the
        # matrix reports both numbers.
        ('the band is missing from one page',
         {}, ('formulas__calming-soft-chews.html',
              lambda s: H7D_BAND.sub('', s, count=1))),
        ('a stray character on one page',
         {}, ('formulas__calming-soft-chews.html',
              lambda s: s.replace('</body>', '<!-- stray --></body>', 1))),
    ],
    'nc_source': [
        ('NC17 the source pass fails when the style token is not bumped',
         'functions.php', "'2.10.65'", "'2.10.64'"),
        ('NC18 the source pass fails when the two scripts lose their page guard',
         'functions.php', "is_singular('sf_formula')) {\n\t\twp_enqueue_script('sinofresh-inquiry'",
         "true) {\n\t\twp_enqueue_script('sinofresh-inquiry'"),
        ('NC19 the source pass fails when the endpoint stops filtering posted values',
         'functions.php', '!in_array($value, $allowed, true)', 'false'),
        ('NC22 the source pass fails when the container picker stops degrading',
         'functions.php', 'sf-fdetail-config__img--empty', 'sf-fdetail-config__img-x'),
        ('NC23 the source pass fails when the phone step moves above its base rule',
         'style.css', _h7d_dead_phone_step, None),
        ('NC24 the source pass fails when the opened-drawer rule leaves the phone step',
         'style.css', _h7d_drawer_out_of_query, None),
    ],
    'nc_page': [
        ('NC20 the scoped invariant fails on a band in the wrong page',
         'about.html',
         lambda s: s.replace('</body>',
                             '<div class="sf-fdetail-config" data-sf-config></div></body>', 1)),
        ('NC21 the scoped invariant fails when a detail page loses its band',
         'formulas__calming-soft-chews.html',
         lambda s: s.replace('<div class="sf-fdetail-config" data-sf-config>',
                             '<div class="sf-detail-config-gone">', 1)),
    ],
    # Renaming a label INSIDE the band: the main proof deletes the band whole,
    # so it stays green — which is the point — and the per-label count is what
    # notices. The first cut of this control renamed the group's data attribute,
    # and coverage did NOT go red: the declared needle was the prefix
    # `data-sf-config-group="`, which a rename of what FOLLOWS the quote leaves
    # intact. A control that names a string the declaration does not count
    # proves nothing about the declaration.
    'nc_blind': ('formulas__calming-soft-chews.html',
                 'sf-fdetail-config__label">Piece Weight<',
                 'sf-fdetail-config__label">Piece Waight<'),
    'source': [
        # --- the template: the call site, and where it sits -------------------
        ('the template calls the configurator', 'tpl_live',
         r'\[sf_formula_config\]', True),
        ('...before the parameter list', 'tpl_live',
         r'\[sf_formula_config\][\s\S]*?\[sf_formula_params\]', True),
        ('...and after the column title', 'tpl_live',
         r'\{\{FORMULA_INTRO\}\}[\s\S]*?\[sf_formula_config\]', True),
        # --- the renderer: the claims a page cannot show ----------------------
        ('the renderer is registered', 'php_live',
         r"add_shortcode\('sf_formula_config', 'sinofresh_formula_config'\)", True),
        ('it guards the post type', 'php_live',
         r"function sinofresh_formula_config\(\)[\s\S]{0,160}is_singular\('sf_formula'\)", True),
        ('one provider feeds the band and the endpoint', 'php_live',
         r'function sinofresh_formula_config_groups\(\$post_id\)', True),
        ('the endpoint drops values the record does not offer', 'php_live',
         r'!in_array\(\$value, \$allowed, true\)', True),
        ('the pack tail travels with the choice', 'php_live',
         r"\$rows\[\$group\['label'\]\] \.\= ' ' \. \$group\['unit_phrase'\]", True),
        # The display string and the machine string are two fields because one
        # cannot be both. This is the assertion that would have caught the first
        # cut, which printed "Per per bottle" beside "60 / 90 / 120" on every
        # pack page: the splitter's tail already BEGINS with the preposition.
        ('the hint is not the preposition prefixed onto the tail', 'php_live',
         r"'Per ' \. \$pack_tail", False),
        ('the renderer shows the tail as a sentence', 'php_live',
         r"\$pack_tail !== '' \? ucfirst\(\$pack_tail\)", True),
        ('the pack splitter still refuses a single size', 'php_live',
         r"if \(count\(\$nums\) < 2\) \{\n\t\treturn array\(array\(\$pack\), ''\);", True),
        ('the choices are not pre-selected', 'php_live', r'\$checked', False),
        # --- the two enqueues -------------------------------------------------
        ('the configurator is enqueued only on a formula page', 'php_live',
         r"is_singular\('sf_formula'\)\) \{[\s\S]{0,420}sinofresh-config", True),
        ('config.js is versioned 1.0.0', 'php',
         r"sinofresh-config'[^;]*'1\.0\.0'", True),
        ('inquiry.js is bumped to 1.2.0', 'php',
         r"sinofresh-inquiry'[^;]*'1\.2\.0'", True),
        ('no 1.1.0 inquiry enqueue survives', 'php_live',
         r"sinofresh-inquiry'[^;]*'1\.1\.0'", False),
        ('the style token is bumped in the enqueue', 'php',
         r"wp_enqueue_style\('sinofresh-style', get_stylesheet_uri\(\), array\(\), '2\.10\.65'\)", True),
        ('no 2.10.64 enqueue survives', 'php_live', r"'2\.10\.64'", False),
        # --- the script -------------------------------------------------------
        ('the carrier is keyed the way the endpoint reads it', 'js_live',
         r"form\.querySelector\('input\[name=\"config\"\]'\)", True),
        ('the choice is written as one JSON object per group', 'js_live',
         r'payload\[group\.key\] = values\.length > 1 \? values : values\[0\]', True),
        ('an empty choice empties the carrier rather than posting a stale one', 'js_live',
         r"carrier\.value = sel\.length \? carrierValue\(sel\) : ''", True),
        ('the summary is emitted empty and revealed by the script', 'js_live',
         r"summary\.hidden = text === ''", True),
        ('the dialog panel falls back to the server rendering', 'js_live',
         r'serverRows', True),
        ('the drawer button is created by the script, not by the markup', 'js_live',
         r"openBtn\.className = 'sf-fdetail-config__open'", True),
        ('the drawer reuses inquiry.js\'s Escape rather than fighting it', 'js_live',
         r'if \(modal && !modal\.hidden\) \{', True),
        ('the script keys off the data attribute, not a class', 'js_live',
         r"document\.querySelector\('\[data-sf-config\]'\)", True),
        # --- the stylesheet: the geometry a page links rather than contains ---
        ('style.css declares 2.10.65', 'css', r'Version: 2\.10\.65', True),
        ('no 2.10.64 header survives', 'css', r'Version: 2\.10\.64', False),
        ('the pills are pills', 'css_live',
         r'\.sf-fdetail-config__opt \{[^}]*border-radius: 999px', True),
        ('the input is 1px and transparent, not display:none', 'css_live',
         r'\.sf-fdetail-config__input \{[^}]*width: 1px', True),
        ('the checked pill is drawn from the input state', 'css_live',
         r'\.sf-fdetail-config__input:checked \+ \.sf-fdetail-config__box', True),
        ('the phone drawer hides the inline list', 'css_live',
         r'\.sf-fdetail-config--js \.sf-fdetail-config__list \{ display: none; \}', True),
        # Containment, not proximity. This used a 900-character budget between
        # the media query and the rule, and the rule now carries the reason for
        # its own z-index above it -- a comment longer than any budget a reader
        # would accept. Raising the budget would be the wrong repair: a bigger
        # one can leap out of the block and be satisfied by a LATER 768 block,
        # which is the very thing the check exists to refuse. `(?!\n\})` refuses
        # to cross the end of a top-level block instead: rules inside the media
        # query close with a tab-indented brace, and the block closes with one
        # at column 0. NC24 is the control that watches this fail.
        ('the drawer is only taken out of the flow inside the phone step', 'css_live',
         r'@media \(max-width: 768px\) \{(?:(?!\n\})[\s\S])*?'
         r'\.sf-fdetail-config--open \.sf-fdetail-config__list', True),
        # The ordering claim as ONE chain, each link anchored twice — the media
        # query AND a marker only this band carries — so it cannot be satisfied
        # by some other component's 768 block later in the file. H7b shipped the
        # reversed version of this and it was dead at every width.
        #
        # The 5200 between the base rule and the phone step is a measurement,
        # not a guess: the band's own rules occupy 4344 characters of the
        # comment-stripped file. A budget this size still refuses a chain that
        # skipped to a 768 block belonging to something else, and NC23 is the
        # control that proves the claim can fail at all.
        ('base rules, then the phone step, in that order', 'css_live',
         r'\.sf-fdetail-config \{[^}]*margin:[\s\S]{0,5200}'
         r'@media \(max-width: 768px\) \{[\s\S]{0,400}\.sf-fdetail-config__open \{', True),
    ],
}


# ------------------------------------------------------------------ H7e -----
# The first batch whose rendered output does not move at all, and the first
# whose direction is a NULL EDIT: `symmetric` with an identity transform.
#
# Place of Origin and OEM / ODM were constants inside the specification-sheet
# renderer. H7e moves them into Site Settings and reads them back through one
# reader. The two fields ship with the constants they replaced, character for
# character, so the question the gate has to answer is not "is the new string
# right" but "did anything else move" — and the answer must be no.
#
# That shape has consequences for what each pass is FOR, and they are why this
# declaration is longer than its diff:
#
#   * the main proof is an identity comparison plus a token fold. It is not a
#     formality: it fails the moment the default is mistyped by one character,
#     the moment the candidate forgets to bump its version token, and the
#     moment any stray byte lands on any of the 75 pages. NC13 runs the other
#     way round for this batch — the main proof is SIGHTED, not blind, because
#     nothing is carved out of either side before the comparison.
#   * a green main proof still cannot say the two rows are THERE, because it
#     would be equally green if they had vanished from both sides. `scoped`
#     owns that: one <dd> per detail page, carrying the default value.
#   * and nothing on a rendered page can say where a value CAME FROM. That is
#     the source pass — the reader and its fallback, the renderer calling it,
#     the absence of the two constants, the subpage and its two registrations
#     — and it is the only pass that can tell this batch apart from doing
#     nothing at all.

def _h7e_transform(text):
    """The null edit, and it is the claim rather than a placeholder.

    `symmetric` applies one function to both sides; here that function is the
    identity and the count it returns is 0, which is exactly what the
    declaration says the batch applies to a page: nothing. Reading
    `applies: 0` as "the gate is not really checking" would be the mistake —
    what it means is that the check IS the comparison, with no declared region
    carved out of it first. Every byte of every page is compared, including the
    two rows whose source this batch moved.
    """
    return text, 0


# The two cells as they actually render, which is a stronger claim than the
# bare value: it pins the string to the specification sheet's own <dd> rather
# than to "somewhere on the page".
H7E_ORIGIN_ROW = '<dd class="sf-fdetail-specs__value">Linyi, Shandong, China</dd>'
H7E_OEM_ROW = '<dd class="sf-fdetail-specs__value">Available</dd>'

BATCHES['h7e'] = {
    'name': 'H7e — Place of Origin and OEM/ODM move from constants to Site Settings',
    'mode': 'symmetric',
    'tokens': [
        ('?ver=2.10.65', '?ver=2.10.66'),                        # style.css
    ],
    'transform': _h7e_transform,
    'applies': 0,
    'applies_base': 0,
    'coverage': [
        # The one declared edit this batch makes to a page, and the reason the
        # main proof is not a capture compared with itself.
        ('?ver=2.10.65', 0),
    ],
    'insertions': [
        ('?ver=2.10.66', 75),
    ],
    'counts': [
        # BOTH sides measured, and the two numbers are equal on purpose: this
        # is where "the value did not move" is actually stated. The first two
        # lock a value to its cell — not "the string is somewhere on the page"
        # but "it is the spec sheet's own <dd>" — which is the difference
        # between the swap being correct and the swap being invisible because
        # the row was dropped.
        ('the origin row still carries its default', H7E_ORIGIN_ROW, 42, 42),
        ('the OEM row still carries its default', H7E_OEM_ROW, 42, 42),
        ('the origin row label is unmoved', '>Place of Origin<', 42, 42),
        ('the OEM row label is unmoved', '>OEM / ODM<', 42, 42),
        # The 154 occurrences that are NOT this row: the about page's copy, the
        # contact page's address line, and the Organization schema's
        # streetAddress. H7e leaves every one of them alone, and measuring them
        # here is what keeps a later batch from absorbing them silently — the
        # scanner found all three and the batch declined all three.
        ('every other origin mention is untouched', 'Linyi, Shandong, China', 196, 196),
    ],
    'unmoved': [
        ('media parameter list', r'sf-fdetail2__params', 42),
        ('the config band', r'sf-fdetail-config', 42),
        ('the spec sheet', r'class="sf-fdetail-specs"', 42),
        ('certification badges', r'sf-cert-badge', None),
        # The submenu slug, which must not reach the front end. A settings page
        # that leaked its own slug onto a product page is a bug no other check
        # in this gate would see.
        ('the factory settings slug stays in wp-admin', r'sf-factory-info', 0),
    ],
    'per_page': [
        ('h1', r'<h1[ >]', 1),
    ],
    'scoped': [
        ('the spec sheet is on each detail page, once',
         'class="sf-fdetail-specs"', _is_formula_detail, 1),
        ('each detail page gets two column groups',
         'sf-fdetail-specs__group"', _is_formula_detail, 2),
        # The claim the main proof cannot make: the row is still there, once,
        # on the pages that had it, carrying the value the field ships with.
        ('each detail page carries the origin row and its default',
         H7E_ORIGIN_ROW, _is_formula_detail, 1),
        ('each detail page carries the OEM row and its default',
         H7E_OEM_ROW, _is_formula_detail, 1),
    ],
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
        'pools': 'inc/formula-pools.php',
        'admin': 'inc/formula-admin.php',
    },
    # NC3/NC4 read these. Which string is the sharp one is batch-specific.
    'reinject': ('an old version token put back fails coverage',
                 'formulas__joint-support-soft-chews.html', '</head>',
                 "<link rel='stylesheet' href='style.css?ver=2.10.65'>"),
    'delete': ('one origin row deleted fails coverage',
               'formulas__calming-soft-chews.html', H7E_ORIGIN_ROW),
    # The main proof compares the payload on this direction, so it must SEE an
    # edit made inside it. Stated here rather than assumed by the control.
    'nc13_mode': 'sighted',
    'matrix': [
        # Every mutant must break the proof AND must actually have changed
        # something (a no-op reports INVALID, not pass).
        ('the version token is not folded', {'tokens': []}, None),
        # A mutant of the DECLARATION rather than of a page: with the real
        # `applies` at 0, claiming the batch applied something must fail the
        # count. This is the count doing its job on a direction where it would
        # otherwise be trivially satisfied.
        ('the null edit claims to have applied something', {'applies': 1}, None),
        ('the OEM row is renamed on one page',
         {}, ('formulas__joint-support-soft-chews.html',
              lambda s: s.replace('>OEM / ODM<', '>OEM / ODMs<', 1))),
        ('a stray character on one page',
         {}, ('formulas__calming-soft-chews.html',
              lambda s: s.replace('</body>', '<!-- stray --></body>', 1))),
    ],
    'nc_source': [
        ('NC17 the source pass fails when the reader stops falling back to the default',
         'inc/formula-pools.php', "return ($value !== '') ? $value : $default;", 'return $value;'),
        ('NC18 the source pass fails when the renderer goes back to a constant',
         'functions.php', "sf_formula_factory_value('sf_factory_origin')", "'Linyi, Shandong, China'"),
    ],
    'nc_page': [
        ('NC19 the scoped invariant fails on an origin row in the wrong page',
         'about.html',
         lambda s: s.replace('</body>', H7E_ORIGIN_ROW + '</body>', 1)),
        ('NC20 the scoped invariant fails when a detail page loses its origin row',
         'formulas__joint-support-soft-chews.html',
         lambda s: s.replace(H7E_ORIGIN_ROW, '<dd class="sf-fdetail-specs__value">X</dd>', 1)),
    ],
    'nc_blind': ('formulas__joint-support-soft-chews.html',
                 '>Place of Origin<', '>Place of Originn<'),
    'source': [
        # --- the reader: where the value now comes from -----------------------
        ('the reader is defined', 'pools_live',
         r'function sf_formula_factory_value\(\$key\)', True),
        ('...and reads the option by key', 'pools_live',
         r'get_option\(\$key, \$default\)', True),
        ('...and falls back to the Site Settings default, not a second copy', 'pools_live',
         r"\$default = isset\(\$d\[\$key\]\) \? \(string\) \$d\[\$key\] : '';", True),
        ('...and treats an empty value as the default', 'pools_live',
         r"return \(\$value !== ''\) \? \$value : \$default;", True),
        # --- the defaults: one value, one source ------------------------------
        ('the defaults carry the origin the constant used to hold', 'php_live',
         r"'sf_factory_origin'   => 'Linyi, Shandong, China'", True),
        ('...and the OEM value the constant used to hold', 'php_live',
         r"'sf_factory_oem'      => 'Available'", True),
        # --- the renderer: it reads, it no longer spells ----------------------
        ('the renderer reads the origin through the reader', 'php_live',
         r"\$value = sf_formula_factory_value\('sf_factory_origin'\);"
         r"[\s\S]{0,120}\$rows\['Place of Origin'\] = esc_html\(\$value\);", True),
        ('...and the OEM value the same way', 'php_live',
         r"\$value = sf_formula_factory_value\('sf_factory_oem'\);"
         r"[\s\S]{0,120}\$rows\['OEM / ODM'\] = esc_html\(\$value\);", True),
        ('the origin constant is gone from the renderer', 'php_live',
         r"esc_html\('Linyi, Shandong, China'\)", False),
        ('the OEM constant is gone from the renderer', 'php_live',
         r"esc_html\('Available'\)", False),
        # --- the settings page: what an admin can now reach -------------------
        ('the subpage is registered under Site Settings', 'admin_live',
         r"add_submenu_page\('sf-site-settings', 'Factory Information', 'Factory Information', "
         r"'manage_options', 'sf-factory-info', 'sf_render_factory_info_page'\)", True),
        ('the page renderer exists', 'admin_live',
         r'function sf_render_factory_info_page\(\)', True),
        ('both fields are registered in the Site Settings group', 'admin_live',
         r"foreach \(array\('sf_factory_origin', 'sf_factory_oem'\) as \$key\)", True),
        ('...with the parent page\'s empty-falls-back sanitizer', 'admin_live',
         r"register_setting\('sf_site_settings', \$key, array\([\s\S]{0,220}"
         r"return \(\$v !== ''\) \? \$v : \$d\[\$key\];", True),
        ('the hook list still names the other two subpages and no more', 'admin_live',
         r"'site-settings_page_sf-containers', 'site-settings_page_sf-global-faq'\), true\);", True),
        ('...and no factory hook was added to it', 'admin_live',
         r'site-settings_page_sf-factory-info', False),
        # --- the version token ------------------------------------------------
        ('the style token is bumped in the enqueue', 'php',
         r"wp_enqueue_style\('sinofresh-style', get_stylesheet_uri\(\), array\(\), '2\.10\.66'\)", True),
        ('no 2.10.65 enqueue survives', 'php_live', r"'2\.10\.65'", False),
        # --- the stylesheet, which this batch touched one line of -------------
        ('style.css declares 2.10.66', 'css', r'Version: 2\.10\.66', True),
        ('no 2.10.65 header survives', 'css', r'Version: 2\.10\.65', False),
    ],
}


# ---------------------------------------------------------------------------
# Batch H7f — the inquiry basket leaves.
#
# DIRECTION. This batch deletes, and the direction is still the DEFAULT branch:
# the expected page is the BASELINE with the declared runs removed, compared
# against the untouched candidate. The mode names are about which side can be
# BUILT, and here that side is the baseline — `exp = fold(transform(baseline))`.
# `delete` mode would ask the CANDIDATE to be transformed, and applying a
# deletion to a page that no longer carries the thing is a no-op that never
# reads the baseline. So `applies` counts what the transform found on the
# BASELINE side: 225, i.e. three runs on each of 75 pages.
#
# WHAT THIS DIRECTION CANNOT SEE, and who owns it instead:
#   * the three runs are removed from the baseline WHOLE, so the gate cannot say
#     what was in them. `counts` measures each of them on both sides — the
#     before column is the only statement that there was something to delete —
#     and the source pass owns the theme-side bytes.
#   * style.css is an external file the page only links. That the deleted lines
#     are exactly the declared ones, and that the four rule HEADERS the basket
#     shared with the two dialogs kept their other selectors, is
#     tools/b2d_h7f_confine.py.
#   * assets/js/basket.js is a FILE, and a deleted file has no bytes to grep for
#     absence. The confine tool compares the file set; the source pass can only
#     speak about files that still exist.
#
# TWO SEAM CLAIMS, because a deletion's sharpest witness is the join it leaves
# behind: the header's button slot and the footer's drawer slot must be gone, and
# the neighbours must now touch. Measured 0 -> 75 on both.

H7F_BUTTON = re.compile(r'<button type="button" class="sf-basket-btn".*?</button>\n\n\n',
                        re.S)
H7F_DRAWER = re.compile(r'<div class="sf-basket-overlay" hidden></div>\n'
                        r'<aside class="sf-basket-drawer".*?</aside>\n', re.S)
H7F_SCRIPT = re.compile(r'<script id="sinofresh-basket-js"[^>]*></script>\n')

H7F_SEAM_HEAD = ('class="wp-block-buttons sf-header__cta is-layout-flex '
                 'wp-block-buttons-is-layout-flex">\n\n<div class="wp-block-button">')
H7F_SEAM_FOOT = '</footer>\n\n\n\n<div class="sf-cookie-banner"'


def _h7f_transform(text):
    """Delete the three declared runs and report how many were found.

    13 newlines hang off these three patterns and every one of them is page
    bytes: the WordPress block parser drops the `<!-- wp:html -->` markers and
    leaves their lines behind, so the baseline carries `\\n\\n` before the button
    and `\\n\\n\\n` after it. H7c lost a run to exactly this. Deleting the markup
    but leaving its whitespace produced three extra newlines on 42 pages and the
    proof failed on precisely that — correctly.
    """
    n = 0
    text, k = H7F_BUTTON.subn('', text)
    n += k
    text, k = H7F_DRAWER.subn('', text)
    n += k
    text, k = H7F_SCRIPT.subn('', text)
    n += k
    return text, n


def _h7f_partial(**leave):
    """Mutants that keep one of the three runs. Each must break the proof, and
    each must actually have changed something."""
    def f(text):
        n = 0
        if not leave.get('button'):
            text, k = H7F_BUTTON.subn('', text)
            n += k
        if not leave.get('drawer'):
            text, k = H7F_DRAWER.subn('', text)
            n += k
        if not leave.get('script'):
            text, k = H7F_SCRIPT.subn('', text)
            n += k
        return text, n
    return f


BATCHES['h7f'] = {
    'name': 'H7f — the inquiry basket leaves: icon, drawer, script, CSS, endpoint mode',
    'mode': 'insert',          # see the direction note above
    'tokens': [
        ('?ver=2.10.66', '?ver=2.10.67'),                       # style.css
    ],
    'transform': _h7f_transform,
    'applies': 225,
    'coverage': [
        # Absent from the candidate, counted on the RAW bytes: the mask is the
        # thing that could hide a survivor.
        ('sf-basket', 0),
        ('sinofresh-basket-js', 0),
        ('assets/js/basket.js', 0),
        ('?ver=2.10.66', 0),
    ],
    'insertions': [
        ('?ver=2.10.67', 75),
        # Not a basket claim: the container the button used to sit in has to
        # still be there, or the batch removed the Get a Quote button with it.
        ('class="wp-block-buttons sf-header__cta', 75),
    ],
    'counts': [
        # BOTH sides measured. The before column is the content claim the main
        # proof cannot make: it removes these runs without looking inside.
        ('the header bag button is gone from every page',
         'class="sf-basket-btn"', 75, 0),
        ('the drawer overlay is gone from every page',
         'class="sf-basket-overlay"', 75, 0),
        ('the drawer is gone from every page',
         'class="sf-basket-drawer"', 75, 0),
        ('the script tag is gone from every page',
         'sinofresh-basket-js', 75, 0),
        ('every basket byte on every page is gone',
         'sf-basket', 1125, 0),
        ('the drawer\'s own heading is gone',
         '<h3>Your Inquiry Basket</h3>', 75, 0),
        # The two seams: where the removals joined the neighbours back up. This
        # is the deletion's sharpest witness and no other pass can state it — a
        # run removed whole leaves no trace of where it was.
        ('the header seam closes where the bag button was',
         H7F_SEAM_HEAD, 0, 75),
        ('the footer seam closes where the drawer was',
         H7F_SEAM_FOOT, 0, 75),
        # ...and everything that must NOT have moved with the basket.
        ('the header CTA container survives on every page',
         'sf-header__cta', 75, 75),
        ('the cookie banner is untouched',
         'class="sf-cookie-banner"', 75, 75),
        ('the float stack is untouched',
         'class="sf-float-stack"', 75, 75),
        ('the Get a Quote button is untouched',
         'sf-quote-cta', 208, 208),
        ('the certificate dialog is untouched', 'sf-certmodal', 9, 9),
        ('the inquiry dialog is untouched', 'sf-inquiry-modal', 1350, 1350),
        ('the navigation is untouched', 'wp-block-navigation', 23061, 23061),
        # The drawer's h3 is the only heading that leaves; the h2 count does not
        # move, which is what `h2_delta: None` asserts page by page.
        ('one heading leaves per page, and it is the drawer\'s',
         '<h3', 1430, 1355),
    ],
    'unmoved': [
        ('the header CTA container', r'class="wp-block-buttons sf-header__cta', 75),
        ('the cookie banner', r'class="sf-cookie-banner"', 75),
        ('the float stack', r'class="sf-float-stack"', 75),
        ('the certificate dialog', r'sf-certmodal', 1),
        ('the navigation', r'wp-block-navigation', None),
    ],
    'per_page': [
        ('h1', r'<h1[ >]', 1),
        # The removal, page by page. A site total of 0 would also be produced by
        # 74 clean pages and one page carrying nothing — these say each page is
        # clean on its own.
        ('the basket button', r'class="sf-basket-btn"', 0),
        ('the basket overlay', r'class="sf-basket-overlay"', 0),
        ('the basket drawer', r'class="sf-basket-drawer"', 0),
        ('the basket script', r'sinofresh-basket-js', 0),
        ('the basket PDF button', r'Download Basket PDF', 0),
        ('the header CTA container', r'class="wp-block-buttons sf-header__cta', 1),
    ],
    'h2_delta': None,
    'sources': {
        'hdr': 'parts/header.html',
        'ftr': 'parts/footer.html',
        'pdf': 'inc/config-pdf.php',
    },
    # NC3/NC4 read these. Which string is the sharp one is batch-specific.
    'reinject': ('a basket run put back fails coverage',
                 'about.html', '<div class="sf-cookie-banner"',
                 '<button type="button" class="sf-basket-btn" aria-label="put back"></button>'),
    'delete': ('one page loses the new version token fails coverage',
               'about.html', '?ver=2.10.67'),
    'nc13_mode': 'sighted',
    'nc13_label': ('NC13 the default direction compares the whole candidate, so a basket '
                   'run put back is caught twice'),
    'matrix': [
        # Every mutant must break the proof AND must actually have changed
        # something (a no-op reports INVALID, not pass).
        ('the header button is never removed',
         {'transform': _h7f_partial(button=True)}, None),
        ('the drawer is never removed',
         {'transform': _h7f_partial(drawer=True)}, None),
        ('the script tag is never removed',
         {'transform': _h7f_partial(script=True)}, None),
        ('the style token is not folded', {'tokens': []}, None),
        ('the run count is declared one short', {'applies': 224}, None),
        ('nothing is removed at all',
         {'transform': (lambda t: (t, 0)), 'applies': 0}, None),
        ('one page keeps its drawer',
         {}, ('root.html', lambda s: s.replace(
             '<div class="sf-cookie-banner"',
             '<div class="sf-basket-overlay" hidden></div>'
             '<div class="sf-cookie-banner"', 1))),
        ('the batch over-reaches and takes the cookie banner with the drawer',
         {}, ('contact.html', lambda s: s.replace(
             '<div class="sf-cookie-banner"', '', 1))),
        ('a stray character on one page',
         {}, ('about.html', lambda s: s.replace('</body>', '<!-- stray --></body>', 1))),
    ],
    'nc_source': [
        ('NC17 the source pass fails when the bag button comes back to the header',
         'parts/header.html',
         '<div class="wp-block-buttons sf-header__cta">',
         '<div class="wp-block-buttons sf-header__cta"><button class="sf-basket-btn"></button>'),
        ('NC18 the source pass fails when the endpoint reads a basket key again',
         'inc/config-pdf.php',
         "$slug = isset($data['slug'])",
         "$data['basket'] = array();\n\t$slug = isset($data['slug'])"),
        ('NC19 the source pass fails when a basket selector comes back to style.css',
         'style.css',
         '.sf-header .sf-header__cta {\n\talign-items: center;\n}',
         '.sf-basket-btn,\n.sf-header .sf-header__cta {\n\talign-items: center;\n}'),
    ],
    'nc_page': [
        ('NC20 the per-page invariant fails on a basket button in the wrong page',
         'about.html',
         lambda s: s.replace('<div class="sf-cookie-banner"',
                             '<button type="button" class="sf-basket-btn"></button>'
                             '<div class="sf-cookie-banner"', 1)),
        ('NC21 the per-page invariant fails when one page loses its header CTA',
         'about.html',
         lambda s: s.replace('class="wp-block-buttons sf-header__cta', 'class="sf-gone', 1)),
    ],
    'nc_blind': ('root.html', '<div class="sf-cookie-banner"',
                 '<button type="button" class="sf-basket-btn" aria-label="put back"></button>'
                 '\n<div class="sf-cookie-banner"'),
    'source': [
        # --- the header template: the button is gone, its container is not ----
        ('the header template no longer renders the basket button', 'hdr_live',
         r'sf-basket', False),
        ('...and still renders the CTA container', 'hdr_live',
         r'sf-header__cta', True),
        ('...and the Get a Quote button inside it', 'hdr_live',
         r'sf-quote-cta', True),
        # On the RAW file, both of these: `hdr_live` has its comment bodies
        # blanked (that is what makes it the right target for "no basket string
        # survives"), so a claim ABOUT the block comments cannot be made there —
        # it would pass vacuously.
        ('...which is now the buttons block\'s only child', 'hdr',
         r'<div class="wp-block-buttons sf-header__cta">\s*<!-- wp:button -->', True),
        ('no wp:html block is left inside the CTA container', 'hdr',
         r'sf-header__cta">[\s\S]{0,80}?wp:html', False),
        # --- the footer template: the drawer is gone, its block-mates are not --
        ('the footer template no longer renders the overlay', 'ftr_live',
         r'sf-basket-overlay', False),
        ('...nor the drawer', 'ftr_live',
         r'sf-basket-drawer', False),
        ('...nor any basket string at all', 'ftr_live',
         r'sf-basket', False),
        ('...and the cookie banner that shared its block is still there', 'ftr_live',
         r'sf-cookie-banner', True),
        ('...and so is the float stack', 'ftr_live',
         r'sf-float-stack', True),
        ('...and the inquiry button shortcode', 'ftr_live',
         r'\[sf_inquiry_button\]', True),
        # --- functions.php: the enqueue goes, the token moves ----------------
        ('functions.php no longer enqueues the basket script', 'php_live',
         r'sinofresh-basket', False),
        ('the style token is bumped in the enqueue', 'php_live',
         r"wp_enqueue_style\('sinofresh-style', get_stylesheet_uri\(\), array\(\), '2\.10\.67'\)",
         True),
        ('no 2.10.66 enqueue survives', 'php_live', r"'2\.10\.66'", False),
        # --- style.css: the rules go, the shared headers keep their selectors --
        ('style.css declares 2.10.67', 'css', r'Version: 2\.10\.67', True),
        ('no 2.10.66 header survives', 'css', r'Version: 2\.10\.66', False),
        ('no basket selector survives in the stylesheet', 'css_live',
         r'sf-basket', False),
        ('the section 45 banner names what survived', 'css',
         r'=== 45\. Header CTA alignment', True),
        ('the section 46 banner is gone', 'css',
         r'=== 46\. Basket pre-fill', False),
        ('the shared backdrop rule still names the certificate dialog', 'css',
         r'\.sf-certmodal,\n\.sf-inquiry-modal \{', True),
        ('no basket selector survives in the raw stylesheet either', 'css',
         r'\.sf-basket', False),
        ('the shared scroll lock keeps both dialogs', 'css',
         r'body\.sf-certmodal-lock,\nbody\.sf-inquiry-lock \{', True),
        ('the header CTA alignment rule survives', 'css',
         r'\.sf-header \.sf-header__cta \{\n\talign-items: center;\n\}', True),
        ('the toast is untouched (formulas.js and toc-nav.js share it)', 'css',
         r'\.sf-toast \{', True),
        ('the certificate modal section is untouched', 'css',
         r'=== 50\. Certificate request modal', True),
        # --- the endpoint: the route stays, the basket mode does not ----------
        ('the endpoint still registers its route', 'pdf_live',
         r"register_rest_route\('sinofresh/v1', '/config-pdf'", True),
        ('...with a public permission callback', 'pdf_live',
         r"'permission_callback'\s*=>\s*'__return_true'", True),
        ('the endpoint body no longer reads a basket key', 'pdf_live',
         r"\['basket'\]", False),
        ('the basket renderer is gone', 'pdf_live',
         r'sinofresh_basket_pdf_render', False),
        ('the basket summary parser is gone', 'pdf_live',
         r'sinofresh_config_pdf_parse_summary', False),
        ('...and the endpoint is no longer its caller', 'pdf_live',
         r'parse_summary\(', False),
        ('the shared reference generator survives', 'pdf_live',
         r'function sinofresh_config_pdf_ref\(', True),
        ('the shared stylesheet survives', 'pdf_live',
         r'function sinofresh_config_pdf_css\(', True),
        ('the shared Dompdf wrapper survives', 'pdf_live',
         r'function sinofresh_config_pdf_dompdf\(', True),
        ('the shared escaper survives', 'pdf_live',
         r'function sinofresh_config_pdf_esc\(', True),
        ('the single-configuration renderer survives', 'pdf_live',
         r'function sinofresh_config_pdf_render\(', True),
        ('...and still prints the whole single-configuration page set', 'pdf_live',
         r'function sinofresh_config_pdf_render\([\s\S]*?NEXT STEPS', True),
    ],
}


# ------------------------------------------------------------------- machinery

def fold(text, pairs):
    for old, new in pairs:
        text = text.replace(old, new)
    return text


def main_proof(decl, base, cand, verbose=True):
    """mask(transform(baseline)) == mask(candidate) — or, when the declaration
    says `mode: 'delete'`, mask(transform(candidate)) == mask(fold(baseline)),
    or, when it says `mode: 'symmetric'`, mask(transform(baseline)) ==
    mask(transform(candidate)) with the same tokens folded on the first.

    The directions exist because there are three kinds of batch, and the
    difference is which side can be BUILT from the other.

      * `insert` (H7a, H7b): the batch rewrites a string the baseline already
        carried, so the expected page can be built from the baseline.
      * `delete` (H7c): the batch adds markup whose content is per-record, so
        there is nothing fixed to splice in; the only honest proof is to REMOVE
        the declared region from the candidate and require the remainder to
        equal the baseline. Reconstructing that markup from the baseline's own
        copy would have meant teaching the gate to render, and a gate that
        renders is a gate that can agree with a broken renderer.
      * `symmetric` (H7d): the batch REMOVES one declared region and ADDS
        another, and both deltas are per-record, so neither side can be built
        from the other. What is left is to apply ONE pure function to both sides
        and require the remainders to be identical: whatever the transform
        declares is deleted from the baseline and from the candidate alike.
        The cost is the same one `delete` pays and it is stated in NC13 again —
        a region removed from both sides is not compared, so its content is
        owned by the coverage pass and its shape by `scoped`.

    Read the direction off the declaration, never off the batch's name: the
    assertion is the same either way — everything outside the declared payload
    is byte-identical, and the payload is exactly as declared.

    On the `insert` branch the proof must compare against `b`. It did not for
    one batch: a generalisation left `mask(act)` in place, which on this branch
    is the transformed BASELINE, so the check silently compared the baseline
    with itself and the candidate was never read. It failed closed (red on every
    page, not green), which is why the H7c batch it shipped with still passed —
    H7c takes the `delete` branch — but H7a/H7b would have been unable to prove
    anything. NC16 is the control: the insert direction must refuse a candidate
    that is the baseline, unmodified.
    """
    names = sorted(set(pages(base)) & set(pages(cand)))
    mode = decl.get('mode', 'insert')
    rows, applied, applied_b, ok = [], 0, 0, True
    for n in names:
        a = read(os.path.join(base, n + '.html'))
        b = read(os.path.join(cand, n + '.html'))
        if mode == 'delete':
            exp = fold(a, decl['tokens'])
            act, cnt = decl['transform'](b)
        elif mode == 'symmetric':
            act, cnt = decl['transform'](b)
            exp, cnt_b = decl['transform'](a)
            exp = fold(exp, decl['tokens'])
            applied_b += cnt_b
        else:
            exp, cnt = decl['transform'](a)
            exp = fold(exp, decl['tokens'])
            act = b
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
    # The baseline side's count, when the declaration states one. For
    # `symmetric` this is not a formality: it is the number that says the
    # function which removes the ADDED region found nothing to remove on the
    # baseline, and the function which removes the REMOVED rows found them all
    # there. One number for two sides would let each side's declaration be wrong
    # in a way the other cancels.
    if decl.get('applies_base') is not None and applied_b != decl['applies_base']:
        ok = False
    if verbose:
        for r in rows[:8]:
            print('  %-42s expected %d B / candidate %d B' % (r['page'], r['expected_len'], r['candidate_len']))
            print('      expected : %r' % r['expected'])
            print('      candidate: %r' % r['candidate'])
        print('  direction               : %s' % mode)
        print('  pages compared          : %d' % len(names))
        print('  differing pages         : %d' % len(rows))
        print('  declared edits applied   : %d (declared %d)' % (applied, decl['applies']))
        if decl.get('applies_base') is not None:
            print('  ...and on the baseline   : %d (declared %d)' % (applied_b, decl['applies_base']))
        shape = {'delete': 'mask(transform(candidate)) == mask(fold(baseline))',
                 'symmetric': 'mask(transform(baseline)) == mask(transform(candidate))'}.get(
                     mode, 'mask(transform(baseline)) == mask(candidate)')
        print('  %s  main proof: %s' % ('PASS' if ok else 'FAIL', shape))
    return {'ok': ok, 'pages': len(names), 'differing': len(rows), 'applied': applied,
            'applied_base': applied_b, 'declared': decl['applies'], 'mode': mode,
            'rows': rows[:8]}


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
    # every time (batch H3's lesson). A batch that legitimately rewrites one key
    # on named pages says so in `jsonld_delta`; the check then narrows rather
    # than loosens — see jsonld_with_exception.
    try:
        spec = decl.get('jsonld_delta')
        if spec:
            ld_ok, ld_pages, ld_bad = jsonld_with_exception(names, base, cand, spec)
        else:
            ld_ok, ld_pages = jsonld_equal(names, base, cand)
            ld_bad = []
    except Exception as exc:                                    # pragma: no cover
        ld_ok, ld_pages, ld_bad = False, 'error: %s' % exc, []
    ok &= ld_ok
    rows.append({'label': 'json-ld deep equal', 'ok': ld_ok, 'bad': ld_bad})
    if verbose:
        print('  %-28s pages parsed = %s%s  %s'
              % ('json-ld deep equal', ld_pages,
                 '' if not ld_bad else '  %s' % (ld_bad,), 'ok' if ld_ok else 'FAIL'))

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


def _offers_out(node, key):
    """Every value filed under `key`, wherever it sits, and the tree without
    them. Mutates `node` on purpose: the caller wants both halves of the same
    walk, not two traversals that could disagree."""
    got = []
    if isinstance(node, dict):
        for k in list(node):
            if k == key:
                got.append(node.pop(k))
            else:
                got += _offers_out(node[k], key)
    elif isinstance(node, list):
        for v in node:
            got += _offers_out(v, key)
    return got


def jsonld_with_exception(names, base, cand, spec):
    """JSON-LD as data, with ONE named exception instead of a loosened rule.

    Batch H7i rewrites the record's offer block — one tier becomes three — so
    the offers on that record MUST move, and a blanket deep-equal would call
    the batch a regression. The wrong fix is to stop comparing the block: that
    would hide a broken aggregate price on every other record too. So the
    exception is stated three ways at once, none of which can widen silently:

      * the pages it applies to are named, and every other page must still be
        deep-equal INCLUDING its own offer block, which is collected and
        compared rather than skipped;
      * on the named pages everything except the declared key must still be
        deep-equal — the Product node's name, image, properties and the other
        five blocks are all still compared;
      * and the key itself must equal the declared numbers, tier by tier.

    A declaration that named the wrong pages, or declared the wrong prices,
    fails on the second and third clauses.

    The page-set clause is also what the boundary is measured BY, and that is
    deliberate: on this site no other record is priced, so `offers` exists on the
    declared pages and nowhere else, and "and nowhere else" is a claim that can
    fail today. The `fb != fc` branch below would fire if some other record
    gained a price and the block moved on it — kept because it is the clause
    that keeps a pruned key from hiding a second copy, but noted as unreachable
    at the data this batch runs on, so that a reader does not mistake it for
    coverage it is not.
    """
    key = spec['key']
    exc = set(spec['pages'])
    want = spec['offers']
    bad, seen = [], set()
    for n in names:
        ab = json_blocks(read(os.path.join(base, n + '.html')))
        ac = json_blocks(read(os.path.join(cand, n + '.html')))
        if len(ab) != len(ac):
            bad.append((n, 'block count %d -> %d' % (len(ab), len(ac))))
            continue
        for x, y in zip(ab, ac):
            ob, oc = json.loads(x), json.loads(y)
            fb, fc = _offers_out(ob, key), _offers_out(oc, key)
            if ob != oc:
                bad.append((n, 'a field other than %s moved' % key))
                break
            # Most blocks on the site carry no offer key at all — the FAQ, the
            # HowTo, the breadcrumb. They are already compared above; running
            # the declared-shape clause on them asks an empty list to look like
            # an AggregateOffer, which is how the first version of this helper
            # reported a perfectly correct page as two failures.
            if not fb and not fc:
                continue
            if n in exc:
                seen.add(n)
                got = fc[0] if fc else {}
                good = (isinstance(got, dict)
                        and got.get('@type') == want['@type']
                        and got.get('priceCurrency') == want['priceCurrency']
                        and got.get('lowPrice') == want['lowPrice']
                        and got.get('highPrice') == want['highPrice']
                        and got.get('offerCount') == want['offerCount']
                        # The key has to have been found in the same number of
                        # places on both sides: a declaration that pruned one
                        # copy away would otherwise pass on a page that carries
                        # two. NOT `fb == fc` -- on the exception page the two
                        # are required to differ, and asserting equality there
                        # made every run red.
                        and len(fb) == len(fc))
                tiers = [(s.get('price'),
                          (s.get('minQuantity') or {}).get('value'),
                          (s.get('maxQuantity') or {}).get('value'))
                         for s in got.get('priceSpecification', [])] if good else []
                if not good or tiers != [tuple(t) for t in want['tiers']]:
                    bad.append((n, '%s is %r / tiers %r' % (key, got, tiers)))
                    break
            elif fb != fc:
                bad.append((n, 'the %s block moved off the declared record' % key))
                break
    if seen != exc:
        bad.append(('exception set', 'declared %r, hit %r'
                    % (sorted(exc), sorted(seen))))
    return (not bad), len(names), bad[:4]


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

        # ...and the same treatment for the one place where a pass is allowed to
        # NOT be deep-equal: `jsonld_delta`. It is a newer mechanism than the
        # rest of this pass and it narrows rather than loosens, so each of its
        # three clauses gets a mutant that makes it fire. A declarable exception
        # with no control is the cheapest way to hide a real regression: it
        # would go on passing after the declared numbers stopped being printed.
        for label, page, fn in decl.get('nc_jsonld', []):
            c = _clone(cand, os.path.join(work, 'ncld'))
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
        #
        # WHICH VERDICT IS THE RIGHT ONE IS A PROPERTY OF THE DIRECTION, so it
        # is read off the declaration (`nc13_mode`) instead of being written
        # into the control. H7c/H7d remove a region, so the main proof is blind
        # to it and `blind` is the pass. H7e is the first batch with a NULL edit
        # — `symmetric` with an identity transform, because it moves where two
        # values come from and not what they are — and on that direction the
        # main proof compares every byte of the payload, so the honest verdict
        # is the opposite: it must SEE the edit, and coverage must confirm it.
        # Hard-coding either verdict would have made this control assert the
        # direction rather than test it, and H7e is the batch that proves that
        # can be wrong: run against the old literal, it would have reported a
        # perfectly working gate as FAIL.
        page, needle, replacement = decl['nc_blind']
        c = _clone(cand, os.path.join(work, 'ncb'))
        p = os.path.join(c, page)
        _write(p, read(p).replace(needle, replacement, 1))
        main = main_proof(decl, base, c, verbose=False)['ok']
        caught = not coverage(decl, base, c, verbose=False)['ok']
        if decl.get('nc13_mode', 'blind') == 'sighted':
            report(decl.get('nc13_label')
                   or 'NC13 the null edit SEES the payload, and coverage confirms it',
                   (not main) and caught,
                   'page=%s main_red=%s coverage_red=%s' % (page, not main, caught))
        else:
            report(decl.get('nc13_label')
                   or 'NC13 the main proof is blind to the payload, coverage is not',
                   main and caught,
                   'page=%s main_green=%s coverage_red=%s' % (page, main, caught))

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

        # NC16 — THE INSERT DIRECTION ITSELF, because it was silently inverted.
        # During H7c the generalisation that added `mode` left `mask(act)` on the
        # branch where `act` is the transformed BASELINE, so the proof compared
        # the baseline with itself and never read the candidate. H7c takes the
        # `delete` branch and stayed green, which is exactly why this control
        # exists: a direction no batch of the moment exercises is a direction
        # nobody is watching.
        #
        # Built from scratch rather than borrowed from a capture directory: a
        # control that depends on scratch state nobody is obliged to keep is a
        # control that turns itself into a silent pass the week the directory is
        # cleaned. The pair is one synthetic page carrying H7b's own shapes.
        #
        # TWO halves, because "it refuses" on its own is satisfied by a direction
        # that is broken in the red direction — which is what the real bug was.
        # So it must also ACCEPT the genuine edit.
        old_page = (
            '<html><head><link rel="stylesheet" href="style.css?ver=2.10.62">'
            '</head><body>'
            '<button type="button" class="sf-formula__cta sf-formula__cta--solid"'
            ' data-formula="f" data-form="d">Reference this formula →</button>'
            '<a class="sf-formula-hero__build sf-quote-cta" href="/contact/#quote">'
            'Build Custom Formula</a>'
            '</body></html>')
        d_a = os.path.join(work, 'ins_a')
        d_b = os.path.join(work, 'ins_b')
        for d, text in ((d_a, old_page), (d_b, old_page)):
            os.makedirs(d, exist_ok=True)
            _write(os.path.join(d, 'synth.html'), text)
        # the genuine candidate: the declared edit actually applied
        d_c = os.path.join(work, 'ins_c')
        os.makedirs(d_c, exist_ok=True)
        _write(os.path.join(d_c, 'synth.html'), fold(_h7b_transform(old_page)[0],
                                                     [('?ver=2.10.62', '?ver=2.10.63')]))
        synth = dict(BATCHES['h7b'], applies=1, applies_base=None)
        refused = not main_proof(synth, d_a, d_b, verbose=False)['ok']
        accepted = main_proof(synth, d_a, d_c, verbose=False)['ok']
        report('NC16 the insert direction refuses an unapplied candidate and takes a real one',
               refused and accepted, 'refused=%s accepted=%s' % (refused, accepted))

    finally:
        shutil.rmtree(work, ignore_errors=True)

    if verbose:
        print('  %s  named negative controls: every control that must fail, failed'
              % ('PASS' if ok else 'FAIL'))
    return {'ok': ok, 'rows': rows}


# ---------------------------------------------------------- H7g / H7h batches

# Batch H7g adds the second global library. The eight shapes are constants of
# the code (slugs are permanent: the PDF endpoint validates against them), so
# the shape group's markup CAN be built from the declaration — this is the
# `insert` direction, unlike H7c's per-record spec sheet. The one per-record
# byte, the value-preview line, is derived from the page's own H7c spec sheet
# row, which is where the record's shape text already renders; the derivation
# applies the same rule the renderer does (case-insensitive match against the
# library labels, canonical label wins, no match -> empty).
H7G_SHAPES = [
    ('bone', 'Bone'), ('round', 'Round'), ('square', 'Square'), ('heart', 'Heart'),
    ('star', 'Star'), ('paw', 'Paw'), ('cylinder', 'Cylinder'), ('custom', 'Custom'),
]


def _h7g_shape_group(meta):
    opts = ''.join(
        '<label class="sf-fdetail-config__opt">'
        '<input class="sf-fdetail-config__input" type="radio" name="sf-config-shape"'
        ' value="%s" data-sf-config-opt="shape">'
        '<span class="sf-fdetail-config__box" aria-hidden="true"></span>'
        '<span class="sf-fdetail-config__img sf-fdetail-config__img--empty">'
        '<span class="sf-fdetail-config__empty-label">%s</span></span></label>'
        % (slug, label)
        for slug, label in H7G_SHAPES)
    return ('<div class="sf-fdetail-config__group" data-sf-config-group="shape">'
            '<p class="sf-fdetail-config__row">'
            '<span class="sf-fdetail-config__label">Shape</span>'
            '<span class="sf-fdetail-config__meta">%s</span>'
            '<span class="sf-fdetail-config__hint">Choose one</span></p>'
            '<div class="sf-fdetail-config__options" role="group" aria-label="Shape">%s'
            '</div></div>' % (meta, opts))


H7G_TEL_ANCHOR = ('<a href="tel:+865398669539">+86 539 866 9539</a>'
                  '<a href="https://wa.me/8613385397805"')
# The contact PAGE carries the identical anchor (its own card, kept by ruling);
# only the footer one is followed by the wa.me link, which is what makes the
# footer occurrence addressable without position arithmetic.
H7G_TEL_FOOTER = re.compile(
    r'<a href="tel:\+865398669539">\+86 539 866 9539</a>(?=<a href="https://wa\.me)')
H7G_SLOT_OLD = re.compile(
    r'sf-fdetail-config__img--empty" aria-hidden="true"></span>'
    r'<span class="sf-fdetail-config__text">([^<]+)</span></label>')
H7G_PREVIEW = re.compile(r'(</figure>)(</div><div class="sf-gallery__tabs")')
H7G_SHAPE_META = re.compile(
    r'sf-fdetail-specs__term">Shape</dt><dd class="sf-fdetail-specs__value">([^<]+)</dd>')
H7G_CONTAINER_ANCHOR = '<div class="sf-fdetail-config__group" data-sf-config-group="container">'
H7G_LIST_TAIL = '</div><p class="sf-fdetail-config__summary"'


def _h7g_transform(text):
    """H7g's declared edit to one baseline page: the landline anchor leaves the
    footer contact line, the preview layer joins the stage, the shape group
    joins the configurator (before the container group where the record has
    one, at the list's tail everywhere else), and every old empty slot — the
    container library's, on the two pages that carry it — hands its label
    inside the dashed box. Tokens are NOT the transform's business: fold()
    applies the declared token pairs."""
    n = 0
    text, k = H7G_TEL_FOOTER.subn('', text)
    n += k
    text, k = H7G_PREVIEW.subn(
        r'\1<div class="sf-gallery__preview" data-sf-gallery-preview hidden></div>\2',
        text)
    n += k
    meta = ''
    m = H7G_SHAPE_META.search(text)
    if m:
        raw = m.group(1).strip()
        for slug, label in H7G_SHAPES:
            if raw.lower() == label.lower():
                meta = label
                break
    group = _h7g_shape_group(meta)
    if H7G_CONTAINER_ANCHOR in text:
        text = text.replace(H7G_CONTAINER_ANCHOR, group + H7G_CONTAINER_ANCHOR, 1)
        n += 1
    elif H7G_LIST_TAIL in text:
        text = text.replace(H7G_LIST_TAIL, group + H7G_LIST_TAIL, 1)
        n += 1
    text, k = H7G_SLOT_OLD.subn(
        lambda mm: ('sf-fdetail-config__img--empty">'
                    '<span class="sf-fdetail-config__empty-label">%s</span></span></label>'
                    % mm.group(1)),
        text)
    n += k
    return text, n


def _h7g_partial(shape=False, preview=False, slots=False, tel=False):
    """Mutants that skip one declared edit; each must break the proof."""
    def f(text):
        n = 0
        text, k = H7G_TEL_FOOTER.subn('', text) if tel else (text, 0)
        n += k
        if preview:
            text, k = H7G_PREVIEW.subn(
                r'\1<div class="sf-gallery__preview" data-sf-gallery-preview hidden></div>\2',
                text)
            n += k
        if shape:
            m = H7G_SHAPE_META.search(text)
            meta = ''
            if m:
                raw = m.group(1).strip()
                for slug, label in H7G_SHAPES:
                    if raw.lower() == label.lower():
                        meta = label
                        break
            group = _h7g_shape_group(meta)
            if H7G_CONTAINER_ANCHOR in text:
                text = text.replace(H7G_CONTAINER_ANCHOR, group + H7G_CONTAINER_ANCHOR, 1)
                n += 1
            elif H7G_LIST_TAIL in text:
                text = text.replace(H7G_LIST_TAIL, group + H7G_LIST_TAIL, 1)
                n += 1
        if slots:
            text, k = H7G_SLOT_OLD.subn(
                lambda mm: ('sf-fdetail-config__img--empty">'
                            '<span class="sf-fdetail-config__empty-label">%s</span>'
                            '</span></label>' % mm.group(1)),
                text)
            n += k
        return text, n
    return f


BATCHES['h7g'] = {
    'name': "H7g — the shape picker joins, the footer's landline and the second WhatsApp source leave",
    'mode': 'insert',
    'tokens': [
        ('?ver=2.10.67', '?ver=2.10.68'),                      # style.css
        ('config.js?ver=1.0.0', 'config.js?ver=1.1.0'),
    ],
    'transform': _h7g_transform,
    'applies': 173,        # tel 75 + preview 42 + shape 42 + slots 7x2
    'coverage': [
        ('style.css?ver=2.10.67', 0),
        ('config.js?ver=1.0.0', 0),
        ('tel:+865398669539">+86 539 866 9539</a><a href="https://wa.me', 0),
        # The old empty slot: a dashed box and the name OUTSIDE it. The needle
        # carries the slot class — a bare "box + text" tail is H7d's TEXT-style
        # option, which survives this batch and must not be counted here.
        ('sf-fdetail-config__img--empty" aria-hidden="true"></span>'
         '<span class="sf-fdetail-config__text"', 0),
    ],
    'insertions': [
        ('style.css?ver=2.10.68', 75),
        ('config.js?ver=1.1.0', 42),
        ('data-sf-gallery-preview', 42),
        ('data-sf-config-group="shape"', 42),
        ('sf-config-shape', 336),                             # 8 radios x 42 pages
        ('sf-fdetail-config__empty-label', 350),              # 8x42 shapes + 7x2 containers
    ],
    'counts': [
        ('the footer anchor leaves every page',
         'tel:+865398669539">+86 539 866 9539</a><a href="https://wa.me', 75, 0),
        # ...but the contact page's own card keeps its phone link (ruling: the
        # footer one only). 76 = 75 footer + 1 contact.
        ('the contact card keeps its own phone link', 'tel:+865398669539', 76, 1),
        ('the preview layer joins every stage', 'data-sf-gallery-preview', 0, 42),
        ('the shape group joins every configurator', 'data-sf-config-group="shape"', 0, 42),
        ('the old empty slot form leaves entirely',
         'sf-fdetail-config__img--empty" aria-hidden="true"></span>'
         '<span class="sf-fdetail-config__text"', 14, 0),
        # The float button's href moved to sf_contact_whatsapp; the BUILT url is
        # the same digits, so the bytes do not move. Both sides, because "no
        # change" is itself the claim.
        ('the wa.me number bytes are unchanged', 'wa.me/8613385397805', 269, 269),
    ],
    'unmoved': [
        ('the cookie banner', r'class="sf-cookie-banner"', 75),
        ('the float stack', r'class="sf-float-stack"', 75),
        ('the certificate dialog', r'sf-certmodal', 1),
        ('the navigation', r'wp-block-navigation', None),
    ],
    'per_page': [
        ('h1', r'<h1[ >]', 1),
        ('the landline anchor', r'tel:\+865398669539">\+86 539 866 9539</a><a href="https://wa\.me', 0),
        ('the new style token', r'style\.css\?ver=2\.10\.68', 1),
    ],
    'scoped': [
        ('the shape group is on each detail page, once',
         'data-sf-config-group="shape"', _is_formula_detail, 1),
        ('so is the preview layer', 'data-sf-gallery-preview', _is_formula_detail, 1),
        ('and the new config token', r'config\.js\?ver=1\.1\.0', _is_formula_detail, 1),
    ],
    'order': [
        ('the preview layer sits inside the stage, before the tabs',
         'sf-gallery__stage', 'data-sf-gallery-preview', _is_formula_detail),
        ('the shape group precedes the container group where the record has one',
         'data-sf-config-group="shape"', 'data-sf-config-group="container"',
         lambda n: 'joint-support-soft-chews' in n),
    ],
    'h2_delta': None,
    'sources': {
        'ftr': 'parts/footer.html',
        'cfg': 'assets/js/config.js',
        'adm': 'inc/formula-admin.php',
    },
    'reinject': ('an old empty-slot run put back fails coverage',
                 'formulas__joint-support-soft-chews.html',
                 'data-sf-config-group="container"',
                 '<span class="sf-fdetail-config__img sf-fdetail-config__img--empty"'
                 ' aria-hidden="true"></span><span class="sf-fdetail-config__text">X</span></label>'),
    'delete': ('one page loses the new style token fails coverage',
               'about.html', '?ver=2.10.68'),
    'nc13_mode': 'sighted',
    'nc13_label': ('NC13 the insert direction SEES a payload edit, and coverage confirms it'),
    'matrix': [
        ('the shape group is never inserted',
         {'transform': _h7g_partial(preview=True, slots=True, tel=True)}, None),
        ('the preview layer is never inserted',
         {'transform': _h7g_partial(shape=True, slots=True, tel=True)}, None),
        ('the empty slots are never rewritten',
         {'transform': _h7g_partial(shape=True, preview=True, tel=True)}, None),
        ('the landline anchor is never removed',
         {'transform': _h7g_partial(shape=True, preview=True, slots=True)}, None),
        ('the tokens are not folded', {'tokens': []}, None),
        ('the run count is declared one short', {'applies': 172}, None),
        ('nothing is applied at all',
         {'transform': (lambda t: (t, 0)), 'applies': 0}, None),
    ],
    'nc_source': [
        ('NC-src the source pass fails when the renderer stops reading the library',
         'functions.php',
         'sf_shape_library()',
         "get_option('sf_shapes', array())"),
        ('NC-src the source pass fails when the footer tel token comes back',
         'parts/footer.html',
         '{{sf-whatsapp-link}}" target="_blank" rel="noopener noreferrer">{{sf-whatsapp}}</a>',
         '{{sf-whatsapp-link}}" target="_blank" rel="noopener noreferrer">{{sf-whatsapp}}</a>'
         '<a href="{{sf-phone-tel}}">{{sf-phone}}</a>'),
    ],
    'nc_page': [
        ('NC-page the scoped count fails when a page loses its shape group',
         'formulas__calming-soft-chews.html',
         lambda s: s.replace('data-sf-config-group="shape"', 'data-sf-config-group="shapX"', 1)),
    ],
    'nc_blind': ('formulas__joint-support-soft-chews.html',
                 'data-sf-config-group="shape"',
                 'data-sf-config-group="shapX"'),
    'source': [
        ('style.css declares 2.10.68', 'css', r'(?m)^Version: 2\.10\.68$', True),
        ('no 2.10.67 header survives', 'css', r'(?m)^Version: 2\.10\.67$', False),
        ('functions.php enqueues 2.10.68 for style.css', 'php',
         r"wp_enqueue_style\('sinofresh-style'[^;]*'2\.10\.68'", True),
        ('functions.php enqueues 1.1.0 for config.js', 'php',
         r"wp_enqueue_script\('sinofresh-config'[^;]*'1\.1\.0'", True),
        ('no 1.0.0 config enqueue survives', 'php',
         r"'sinofresh-config'[^;]*'1\.0\.0'", False),
        ('the renderer declares the shape group key', 'php', r"'key' => 'shape'", True),
        ('the shape library is read, not inlined', 'php', r'sf_shape_library\(\)', True),
        ('the library ships the eight slugs', 'adm', r"function sf_default_shapes", True),
        ('the admin page is registered', 'adm', r"'sf-shapes'", True),
        ('the footer contact line has no phone token left', 'ftr',
         r'\{\{sf-phone', False),
        ('the float button reads the shared WhatsApp source', 'ftr',
         r'\{\{sf-whatsapp-link\}\}', True),
        ('the stylesheet styles the preview layer', 'css', r'\.sf-gallery__preview', True),
        ('the stylesheet styles the named placeholder', 'css',
         r'\.sf-fdetail-config__empty-label', True),
        ('config.js reads the label back out of the box', 'cfg',
         r'sf-fdetail-config__empty-label', True),
        ('config.js still paints its --js flag', 'cfg',
         r'sf-fdetail-config--js', True),
    ],
}


# Batch H7h is the phone pass: every page-visible change is a version token or
# an EXTERNAL file (style.css section 62, config.js 1.2.0's fold, gallery 2.2.0's
# dots — JS-built DOM, invisible to server bytes on purpose). The main proof is
# therefore a NULL edit on the insert branch, H7e's shape: mask(fold(baseline))
# == mask(candidate), full-width. What the batch MEANS lives in the external
# files, and that is what the source pass owns; what it DOES lives in the
# browser, and that is what the E2E owns. The gate's job here is the discipline
# one: nothing else on any of the 75 pages moved, and the tokens moved together.
BATCHES['h7h'] = {
    'name': 'H7h — the phone pass: type floors, the fold, dots, the bottom bar',
    'mode': 'insert',
    'tokens': [
        ('?ver=2.10.68', '?ver=2.10.69'),                      # style.css
        ('config.js?ver=1.1.0', 'config.js?ver=1.2.0'),
        ('formula-gallery.js?ver=2.1.0', 'formula-gallery.js?ver=2.2.0'),
    ],
    'transform': lambda text: (text, 0),
    'applies': 0,
    'coverage': [
        ('style.css?ver=2.10.68', 0),
        ('config.js?ver=1.1.0', 0),
        ('formula-gallery.js?ver=2.1.0', 0),
    ],
    'insertions': [
        ('style.css?ver=2.10.69', 75),
        ('config.js?ver=1.2.0', 42),
        ('formula-gallery.js?ver=2.2.0', 42),
    ],
    'counts': [
        ('the config token moves on the detail pages and nowhere else',
         'config.js?ver=', 42, 42),
        ('the gallery token moves on the detail pages and nowhere else',
         'formula-gallery.js?ver=', 42, 42),
    ],
    'unmoved': [
        ('the cookie banner', r'class="sf-cookie-banner"', 75),
        ('the float stack', r'class="sf-float-stack"', 75),
        ('the certificate dialog', r'sf-certmodal', 1),
        ('the navigation', r'wp-block-navigation', None),
        ('the shape group', r'data-sf-config-group="shape"', 42),
    ],
    'per_page': [
        ('h1', r'<h1[ >]', 1),
        ('the new style token', r'style\.css\?ver=2\.10\.69', 1),
    ],
    'scoped': [
        ('the new config token is on each detail page, once',
         r'config\.js\?ver=1\.2\.0', _is_formula_detail, 1),
        ('so is the new gallery token', r'formula-gallery\.js\?ver=2\.2\.0',
         _is_formula_detail, 1),
    ],
    'order': [],
    'h2_delta': None,
    'sources': {
        'cfg': 'assets/js/config.js',
    },
    'reinject': ('an old style token put back fails coverage',
                 'about.html', '?ver=2.10.69', '?ver=2.10.68'),
    'delete': ('one page loses the new style token fails coverage',
               'about.html', '?ver=2.10.69'),
    'nc13_mode': 'sighted',
    'nc13_label': ('NC13 the null edit compares every byte, so a payload edit is seen '
                   'and coverage confirms it'),
    'matrix': [
        ('the tokens are not folded', {'tokens': []}, None),
        ('one token pair is dropped',
         {'tokens': [('?ver=2.10.68', '?ver=2.10.69')]}, None),
        ('the run count is declared non-zero', {'applies': 1}, None),
        ('a stray character on one page',
         {}, ('about.html', lambda s: s.replace('</body>', '<!-- stray --></body>', 1))),
        ('one page keeps its old config token',
         {}, ('formulas__calming-soft-chews.html',
              lambda s: s.replace('config.js?ver=1.2.0', 'config.js?ver=1.1.0', 1))),
    ],
    'nc_source': [
        ('NC-src the source pass fails when the fold rule leaves the stylesheet',
         'style.css',
         '.sf-fdetail-config--js .sf-fdetail-config__list.sf-config-folded',
         '.sf-zz-folded-removed'),
        ('NC-src the source pass fails when the fold state stops persisting',
         'assets/js/config.js',
         "sessionStorage.setItem(FOLD_KEY, open ? 'open' : 'folded');",
         '/* state is not kept */'),
        ('NC-src the source pass fails when the dots builder leaves the gallery',
         'assets/js/formula-gallery.js',
         # A callable on purpose: a first-occurrence replace leaves
         # 'sf-gallery__dots' as a substring of the mutant, and a check that
         # cannot notice its own sabotage proves nothing.
         lambda s: s.replace('sf-gallery__dots', 'sf-zz-dots-removed'),
         None),
    ],
    'nc_page': [
        ('NC-page the scoped count fails when a page loses its gallery token',
         'formulas__calming-soft-chews.html',
         lambda s: s.replace('formula-gallery.js?ver=2.2.0', 'formula-gallery.js?ver=X', 1)),
    ],
    'nc_blind': ('formulas__calming-soft-chews.html',
                 'config.js?ver=1.2.0', 'config.js?ver=1.2.X'),
    'source': [
        ('style.css declares 2.10.69', 'css', r'(?m)^Version: 2\.10\.69$', True),
        ('no 2.10.68 header survives', 'css', r'(?m)^Version: 2\.10\.68$', False),
        ('functions.php enqueues 2.10.69 for style.css', 'php',
         r"wp_enqueue_style\('sinofresh-style'[^;]*'2\.10\.69'", True),
        ('functions.php enqueues 1.2.0 for config.js', 'php',
         r"wp_enqueue_script\('sinofresh-config'[^;]*'1\.2\.0'", True),
        ('functions.php enqueues 2.2.0 for formula-gallery.js', 'php',
         r"wp_enqueue_script\('sinofresh-formula-gallery'[^;]*'2\.2\.0'", True),
        ('no 2.1.0 gallery enqueue survives', 'php',
         r"'sinofresh-formula-gallery'[^;]*'2\.1\.0'", False),
        ('the phone pass lives at the end of the stylesheet', 'css',
         r'62\. Batch H7h', True),
        ('the folded rule is scoped to the fold class', 'css',
         r'sf-config-folded', True),
        ('the drawer still exists for tablets', 'css',
         r'sf-fdetail-config--js \.sf-fdetail-config__list \{ display: none; \}', True),
        ('the dots have their own rules', 'css', r'\.sf-gallery__dot', True),
        ('the bottom bar rule is in the phone block', 'css',
         r'sf-float-stack \{\n\t\tleft: 0;', True),
        ('the hint line is withdrawn at the phone width', 'css',
         r'__hint \{\n\t\tdisplay: none;', True),
        ('config.js builds the fold button', 'cfg', r'sf-fdetail-config__fold', True),
        ('config.js persists the fold state', 'cfg',
         r"sessionStorage\.setItem\(FOLD_KEY", True),
        ('config.js derives the label the same way H7g rendered it', 'cfg',
         r'sf-fdetail-config__empty-label', True),
        ('gallery builds the dots', 'js', r'sf-gallery__dots', True),
        ('gallery syncs the dots in paint()', 'js',
         r"dotBtns.forEach", True),
    ],
}


# ---------------------------------------------------------- H7i batch
# Batch H7i is the first batch that carries a DATA write and a CODE write in one
# commit, so its gate covers both. The baseline is therefore the previous commit
# (5db481d) with post 158's three metas as they stood BEFORE the write — video
# url empty, the legacy single-tier `qty`/`price` pair, no sample fee — and the
# candidate is 967d252 with the batch's own values. The video frame, the price
# ladder and the three-offer aggregate exist on the candidate side only because
# of that write, so the three per-record literal pairs below are the write's
# rendering as much as the theme's.
#
# That makes this declaration NON-RE-RUNNABLE by design: re-capturing the
# baseline now would find post 158 already carrying the new data, none of the
# literals would match, `applies` would come out short and the gate would go
# RED. It fails closed, which is the direction a pinned declaration should fail
# in. Re-running it needs the pre-write data back — the snapshot is
# _backup/b2d-h7i-post158/before.json.

H7I_HERO = re.compile(r'<div class="sf-formula-hero__actions">.*?</div>')
# The hero's own two buttons go; the brief's hero is the identity of the record
# and nothing else. The comment that replaces them is byte-identical on both
# languages — the hero's hrefs were language-prefixed, and removing it must not
# depend on which prefix was there.
H7I_HERO_COMMENT = (
    "<!-- Batch H7i: the hero's two buttons (Send Inquiry / Build Custom Formula)\n     are gone. The brief's hero is the identity of the record and nothing else:\n     breadcrumb, name, one meta line. The inquiry path moved to the foot of the\n     parameters column, where the visitor has just read the specification —\n     and to the float capsule, which already carried the same destination. -->"
)

# The right column's foot: a plain "Request Sample" link to /contact/ becomes
# the page's own inquiry button, carrying the dialog hook and the no-JS
# destination. The prefix is the one byte that differs between the languages, so
# the pattern captures it instead of naming either.
H7I_CTA = re.compile(
    r'<a class="sf-fdetail2__cta" href="((?:/zh)?/contact/)">Request Sample</a>')
H7I_CTA_COMMENT = (
    "<!-- Batch H7i: this used to be a plain \"Request Sample\" link to /contact/.\n     It is now the page's own inquiry button: the same Send Inquiry the float\n     capsule carries, at the foot of the specification the visitor just read,\n     with data-sf-inquiry-open driving the dialog and /contact/#quote the\n     no-JS destination. The paint is 38a's own CTA rule, not a second style. -->\n"
)

# The record's own payload, part one: the gallery. It is the record's FAMILY
# gallery — the four soft-chew pages carry it byte for byte — which is why the
# transform scopes these edits on the canonical link rather than trusting the
# literal to be unique. The renderer puts the video frame at slot 2, so the
# three frames after it are renumbered and the tab group gains its Video button;
# both languages of the record carry the same bytes.
H7I_GALLERY_OLD = (
    '<div class="sf-gallery__inner" data-gallery="soft-chews"><div class="sf-gallery__stage" role="tabpanel" id="sf-gallery-panel-soft-chews" aria-label="SINO FRESH Soft Chews private label pet supplement product — brown star- and bone-shaped chews">'
    '<figure class="sf-gallery__slide" id="sf-gallery-slide-soft-chews-1" data-slot="1" data-label="SINO FRESH Soft Chews private label pet supplement product — brown star- and bone-shaped chews">'
    '<img src="https://dev.zxpet.com/wp-content/uploads/2026/09/soft-chews.webp" alt="SINO FRESH Soft Chews private label pet supplement product — brown star- and bone-shaped chews" width="720" height="720" loading="eager" decoding="async">'
    '</figure><figure class="sf-gallery__slide" id="sf-gallery-slide-soft-chews-2" data-slot="2" data-label="Soft Chews production line at the SINO FRESH GMP facility in Linyi, China" hidden>'
    '<img src="https://dev.zxpet.com/wp-content/uploads/2026/09/fac-placeholder.webp" alt="Soft Chews production line at the SINO FRESH GMP facility in Linyi, China" width="1100" height="733" loading="lazy" decoding="async">'
    '</figure><figure class="sf-gallery__slide" id="sf-gallery-slide-soft-chews-3" data-slot="3" data-label="Soft Chews packaging line at the SINO FRESH GMP facility in Linyi, China" hidden>'
    '<img src="https://dev.zxpet.com/wp-content/uploads/2026/09/fac-packaging.webp" alt="Soft Chews packaging line at the SINO FRESH GMP facility in Linyi, China" width="800" height="600" loading="lazy" decoding="async">'
    '</figure><figure class="sf-gallery__slide" id="sf-gallery-slide-soft-chews-4" data-slot="4" data-label="Soft Chews moving along the tray line inside the SINO FRESH GMP facility" hidden>'
    '<img src="https://dev.zxpet.com/wp-content/uploads/2026/09/fac-line.webp" alt="Soft Chews moving along the tray line inside the SINO FRESH GMP facility" width="800" height="600" loading="lazy" decoding="async">'
    '</figure><div class="sf-gallery__preview" data-sf-gallery-preview hidden></div></div><div class="sf-gallery__tabs" role="group" aria-label="Product media">'
    '<button type="button" class="sf-gallery__tab is-active" data-sf-gallery-tab="photos" aria-pressed="true">Photos</button>'
    '</div></div>'
)
H7I_GALLERY_NEW = (
    '<div class="sf-gallery__inner" data-gallery="soft-chews"><div class="sf-gallery__stage" role="tabpanel" id="sf-gallery-panel-soft-chews" aria-label="SINO FRESH Soft Chews private label pet supplement product — brown star- and bone-shaped chews">'
    '<figure class="sf-gallery__slide" id="sf-gallery-slide-soft-chews-1" data-slot="1" data-label="SINO FRESH Soft Chews private label pet supplement product — brown star- and bone-shaped chews">'
    '<img src="https://dev.zxpet.com/wp-content/uploads/2026/09/soft-chews.webp" alt="SINO FRESH Soft Chews private label pet supplement product — brown star- and bone-shaped chews" width="720" height="720" loading="eager" decoding="async">'
    '</figure><figure class="sf-gallery__slide sf-gallery__slide--video" id="sf-gallery-slide-soft-chews-2" data-slot="2" data-video-id="jNQXAC9IVRw" data-label="Soft Chews product video" hidden>'
    '<button type="button" class="sf-gallery__play"><img src="https://i.ytimg.com/vi/jNQXAC9IVRw/hqdefault.jpg" alt="Soft Chews product video" width="480" height="360" loading="lazy" decoding="async">'
    '<span class="sf-gallery__play-icon" aria-hidden="true"></span><span class="sf-gallery__play-text">Play video</span>'
    '</button></figure><figure class="sf-gallery__slide" id="sf-gallery-slide-soft-chews-3" data-slot="3" data-label="Soft Chews production line at the SINO FRESH GMP facility in Linyi, China" hidden>'
    '<img src="https://dev.zxpet.com/wp-content/uploads/2026/09/fac-placeholder.webp" alt="Soft Chews production line at the SINO FRESH GMP facility in Linyi, China" width="1100" height="733" loading="lazy" decoding="async">'
    '</figure><figure class="sf-gallery__slide" id="sf-gallery-slide-soft-chews-4" data-slot="4" data-label="Soft Chews packaging line at the SINO FRESH GMP facility in Linyi, China" hidden>'
    '<img src="https://dev.zxpet.com/wp-content/uploads/2026/09/fac-packaging.webp" alt="Soft Chews packaging line at the SINO FRESH GMP facility in Linyi, China" width="800" height="600" loading="lazy" decoding="async">'
    '</figure><figure class="sf-gallery__slide" id="sf-gallery-slide-soft-chews-5" data-slot="5" data-label="Soft Chews moving along the tray line inside the SINO FRESH GMP facility" hidden>'
    '<img src="https://dev.zxpet.com/wp-content/uploads/2026/09/fac-line.webp" alt="Soft Chews moving along the tray line inside the SINO FRESH GMP facility" width="800" height="600" loading="lazy" decoding="async">'
    '</figure><div class="sf-gallery__preview" data-sf-gallery-preview hidden></div></div><div class="sf-gallery__tabs" role="group" aria-label="Product media">'
    '<button type="button" class="sf-gallery__tab is-active" data-sf-gallery-tab="photos" aria-pressed="true">Photos</button>'
    '<button type="button" class="sf-gallery__tab" data-sf-gallery-tab="video" aria-pressed="false">Video</button></div>'
    '</div>'
)

# Part two: Quantity & Pricing. One legacy pill — "200 — USD 2.5 / unit", the
# shape of the single tier the record carried before the write — becomes the
# three-card ladder plus the sample row. The languages differ by the sample
# button's href and by TranslatePress's lowercasing of the SVG's viewBox; both
# are asserted when this block is generated.
H7I_PRICING_OLD = (
    '<div class="sf-fdetail-config__group" data-sf-config-group="pricing"><p class="sf-fdetail-config__row"><span class="sf-fdetail-config__label">Quantity &amp; Pricing</span>'
    '<span class="sf-fdetail-config__meta">200 — USD 2.5 / unit</span><span class="sf-fdetail-config__hint">Choose one</span>'
    '</p><div class="sf-fdetail-config__options" role="group" aria-label="Quantity &amp; Pricing"><label class="sf-fdetail-config__opt">'
    '<input class="sf-fdetail-config__input" type="radio" name="sf-config-pricing" value="200" data-sf-config-opt="pricing">'
    '<span class="sf-fdetail-config__box" aria-hidden="true"></span><span class="sf-fdetail-config__text">200</span>'
    '<span class="sf-fdetail-config__note">USD 2.5 / unit</span></label></div></div>'
)
H7I_PRICING_NEW_EN = (
    '<div class="sf-fdetail-config__group" data-sf-config-group="pricing"><p class="sf-fdetail-config__row"><span class="sf-fdetail-config__label">Quantity &amp; Pricing</span>'
    '<span class="sf-fdetail-config__meta">10-99 — US$3.88 / unit · 100-999 — US$3.58 / unit · ≥1,000 — US$3.28 / unit</span>'
    '<span class="sf-fdetail-config__hint">Choose one</span></p><div class="sf-fdetail-config__options sf-fdetail-config__tiers" role="group" aria-label="Quantity &amp; Pricing">'
    '<label class="sf-fdetail-config__opt sf-tier"><input class="sf-fdetail-config__input" type="radio" name="sf-config-pricing" value="10-99" data-sf-config-opt="pricing">'
    '<span class="sf-tier__price">US$3.88</span><span class="sf-tier__range">10-99</span><span class="sf-tier__unit">pieces</span>'
    '<span class="sf-tier__dot" aria-hidden="true"></span></label><label class="sf-fdetail-config__opt sf-tier"><input class="sf-fdetail-config__input" type="radio" name="sf-config-pricing" value="100-999" data-sf-config-opt="pricing">'
    '<span class="sf-tier__price">US$3.58</span><span class="sf-tier__range">100-999</span><span class="sf-tier__unit">pieces</span>'
    '<span class="sf-tier__dot" aria-hidden="true"></span></label><label class="sf-fdetail-config__opt sf-tier"><input class="sf-fdetail-config__input" type="radio" name="sf-config-pricing" value="≥1,000" data-sf-config-opt="pricing">'
    '<span class="sf-tier__price">US$3.28</span><span class="sf-tier__range">≥1,000</span><span class="sf-tier__unit">pieces</span>'
    '<span class="sf-tier__dot" aria-hidden="true"></span></label></div><div class="sf-fdetail-config__sample"><span class="sf-fdetail-config__sample-icon" aria-hidden="true">'
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" focusable="false">'
    '<path d="M21 8 12 3 3 8v8l9 5 9-5V8Z"/><path d="m3 8 9 5 9-5"/><path d="M12 13v8"/></svg></span><span class="sf-fdetail-config__sample-label">Sample price</span>'
    '<span class="sf-fdetail-config__sample-price">US$50.00</span><a class="sf-fdetail-config__sample-cta" href="/contact/#quote" data-sf-inquiry-open data-sf-inquiry-sample="US$50.00">Get Sample</a>'
    '</div></div>'
)
H7I_PRICING_NEW_ZH = (
    '<div class="sf-fdetail-config__group" data-sf-config-group="pricing"><p class="sf-fdetail-config__row"><span class="sf-fdetail-config__label">Quantity &amp; Pricing</span>'
    '<span class="sf-fdetail-config__meta">10-99 — US$3.88 / unit · 100-999 — US$3.58 / unit · ≥1,000 — US$3.28 / unit</span>'
    '<span class="sf-fdetail-config__hint">Choose one</span></p><div class="sf-fdetail-config__options sf-fdetail-config__tiers" role="group" aria-label="Quantity &amp; Pricing">'
    '<label class="sf-fdetail-config__opt sf-tier"><input class="sf-fdetail-config__input" type="radio" name="sf-config-pricing" value="10-99" data-sf-config-opt="pricing">'
    '<span class="sf-tier__price">US$3.88</span><span class="sf-tier__range">10-99</span><span class="sf-tier__unit">pieces</span>'
    '<span class="sf-tier__dot" aria-hidden="true"></span></label><label class="sf-fdetail-config__opt sf-tier"><input class="sf-fdetail-config__input" type="radio" name="sf-config-pricing" value="100-999" data-sf-config-opt="pricing">'
    '<span class="sf-tier__price">US$3.58</span><span class="sf-tier__range">100-999</span><span class="sf-tier__unit">pieces</span>'
    '<span class="sf-tier__dot" aria-hidden="true"></span></label><label class="sf-fdetail-config__opt sf-tier"><input class="sf-fdetail-config__input" type="radio" name="sf-config-pricing" value="≥1,000" data-sf-config-opt="pricing">'
    '<span class="sf-tier__price">US$3.28</span><span class="sf-tier__range">≥1,000</span><span class="sf-tier__unit">pieces</span>'
    '<span class="sf-tier__dot" aria-hidden="true"></span></label></div><div class="sf-fdetail-config__sample"><span class="sf-fdetail-config__sample-icon" aria-hidden="true">'
    '<svg width="16" height="16" viewbox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" focusable="false">'
    '<path d="M21 8 12 3 3 8v8l9 5 9-5V8Z"/><path d="m3 8 9 5 9-5"/><path d="M12 13v8"/></svg></span><span class="sf-fdetail-config__sample-label">Sample price</span>'
    '<span class="sf-fdetail-config__sample-price">US$50.00</span><a class="sf-fdetail-config__sample-cta" href="/zh/contact/#quote" data-sf-inquiry-open data-sf-inquiry-sample="US$50.00">Get Sample</a>'
    '</div></div>'
)

# Part three: the offers, as the crawler reads them. The ladder turns one tier
# into three, so the aggregate price, the offer count and the specification list
# all move — and they move IN THE PAGE BYTES, which is why the main proof has to
# declare them and not only the JSON-LD invariant. The en page carries the block
# compact; TranslatePress re-serialises the zh page with its own indentation, so
# there are two literal pairs. Each occurs exactly once on the whole site.
H7I_LD_OLD_EN = (
    '{"@type":"AggregateOffer","priceCurrency":"USD","lowPrice":2.5,"highPrice":2.5,"offerCount":1,"priceSpecification":[{"@type":"UnitPriceSpecification","price":2.5,"priceCurrency":"USD","minQuantity":{"@type":"QuantitativeValue","value":200,"unitText":"units"}}]}'
)
H7I_LD_NEW_EN = (
    '{"@type":"AggregateOffer","priceCurrency":"USD","lowPrice":3.28,"highPrice":3.88,"offerCount":3,"priceSpecification":[{"@type":"UnitPriceSpecification","price":3.88,"priceCurrency":"USD","minQuantity":{"@type":"QuantitativeValue","value":10,"unitText":"units"},"maxQuantity":{"@type":"QuantitativeValue","value":99,"unitText":"units"}},{"@type":"UnitPriceSpecification","price":3.58,"priceCurrency":"USD","minQuantity":{"@type":"QuantitativeValue","value":100,"unitText":"units"},"maxQuantity":{"@type":"QuantitativeValue","value":999,"unitText":"units"}},{"@type":"UnitPriceSpecification","price":3.28,"priceCurrency":"USD","minQuantity":{"@type":"QuantitativeValue","value":1000,"unitText":"units"}}]}'
)
H7I_LD_OLD_ZH = (
    '{\n        "@type": "AggregateOffer",\n        "priceCurrency": "USD",\n        "lowPrice": 2.5,\n        "highPrice": 2.5,\n        "offerCount": 1,\n        "priceSpecification": [\n            {\n                "@type": "UnitPriceSpecification",\n                "price": 2.5,\n                "priceCurrency": "USD",\n                "minQuantity": {\n                    "@type": "QuantitativeValue",\n                    "value": 200,\n                    "unitText": "units"\n                }\n            }\n        ]\n    }'
)
H7I_LD_NEW_ZH = (
    '{\n        "@type": "AggregateOffer",\n        "priceCurrency": "USD",\n        "lowPrice": 3.28,\n        "highPrice": 3.88,\n        "offerCount": 3,\n        "priceSpecification": [\n            {\n                "@type": "UnitPriceSpecification",\n                "price": 3.88,\n                "priceCurrency": "USD",\n                "minQuantity": {\n                    "@type": "QuantitativeValue",\n                    "value": 10,\n                    "unitText": "units"\n                },\n                "maxQuantity": {\n                    "@type": "QuantitativeValue",\n                    "value": 99,\n                    "unitText": "units"\n                }\n            },\n            {\n                "@type": "UnitPriceSpecification",\n                "price": 3.58,\n                "priceCurrency": "USD",\n                "minQuantity": {\n                    "@type": "QuantitativeValue",\n                    "value": 100,\n                    "unitText": "units"\n                },\n                "maxQuantity": {\n                    "@type": "QuantitativeValue",\n                    "value": 999,\n                    "unitText": "units"\n                }\n            },\n            {\n                "@type": "UnitPriceSpecification",\n                "price": 3.28,\n                "priceCurrency": "USD",\n                "minQuantity": {\n                    "@type": "QuantitativeValue",\n                    "value": 1000,\n                    "unitText": "units"\n                }\n            }\n        ]\n    }'
)

# Part four: the dialog carrier, which reprints the pricing group's own summary
# line. The ladder therefore shows up a fourth time, and here in identical bytes
# on both languages — the carrier is one component, not two.
H7I_MODAL_OLD = (
    '<dt class="sf-inquiry-modal__term">Quantity &amp; Pricing</dt><dd class="sf-inquiry-modal__value">200 — 2.5</dd>'
)
H7I_MODAL_NEW = (
    '<dt class="sf-inquiry-modal__term">Quantity &amp; Pricing</dt><dd class="sf-inquiry-modal__value">10-99 — US$3.88 · 100-999 — US$3.58 · ≥1,000 — US$3.28</dd>'
)

# The record the batch wrote data for. Anchored on the canonical link, which is
# the page's own statement of which record it is and which survives the excerpt,
# the hero and every other region the transform touches.
H7I_RECORD = re.compile(
    r'<link rel="canonical" href="https?://[^"]*/(?:zh/)?formulas/joint-support-soft-chews/"')
H7I_ZH = re.compile(r'<html lang="zh-CN"')


def _h7i_cta(prefix):
    return (H7I_CTA_COMMENT + '<a class="sf-fdetail2__cta" href="' + prefix
            + '#quote" data-sf-inquiry-open>Send Inquiry</a>')


def _h7i_record_payload(text, gallery=True, pricing=True, jsonld=True, modal=True):
    """The record's four payloads, each one literal pair: the gallery, the price
    ladder, the offer block and the dialog carrier's reprint of the ladder. Only
    the gallery is not the record's own data — it is its family's — so all four
    sit behind the same canonical-link scope, which is what keeps the family
    gallery from being patched onto the three sibling records."""
    n = 0
    if not H7I_RECORD.search(text):
        return text, n
    zh = bool(H7I_ZH.search(text))
    if gallery and H7I_GALLERY_OLD in text:
        text = text.replace(H7I_GALLERY_OLD, H7I_GALLERY_NEW, 1)
        n += 1
    if pricing and H7I_PRICING_OLD in text:
        text = text.replace(H7I_PRICING_OLD,
                            H7I_PRICING_NEW_ZH if zh else H7I_PRICING_NEW_EN, 1)
        n += 1
    ld_old = H7I_LD_OLD_ZH if zh else H7I_LD_OLD_EN
    if jsonld and ld_old in text:
        text = text.replace(ld_old, H7I_LD_NEW_ZH if zh else H7I_LD_NEW_EN, 1)
        n += 1
    if modal and H7I_MODAL_OLD in text:
        text = text.replace(H7I_MODAL_OLD, H7I_MODAL_NEW, 1)
        n += 1
    return text, n


def _h7i_transform(text):
    """H7i's declared edit to one baseline page: the hero's two buttons leave,
    the right column's foot becomes the inquiry button, and the one record the
    batch wrote data for swaps in the video frame, the price ladder, the
    three-offer aggregate and the dialog's reprint of it. Tokens are NOT the
    transform's business — fold()
    applies the declared token pairs."""
    n = 0
    text, k = H7I_HERO.subn(lambda m: H7I_HERO_COMMENT, text)
    n += k
    text, k = H7I_CTA.subn(lambda m: _h7i_cta(m.group(1)), text)
    n += k
    text, k = _h7i_record_payload(text)
    return text, n + k


def _h7i_partial(hero=False, cta=False, gallery=False, pricing=False,
                 jsonld=False, modal=False):
    """Mutants that skip one declared edit; each must break the proof."""
    def f(text):
        n = 0
        if hero:
            text, k = H7I_HERO.subn(lambda m: H7I_HERO_COMMENT, text)
            n += k
        if cta:
            text, k = H7I_CTA.subn(lambda m: _h7i_cta(m.group(1)), text)
            n += k
        text, k = _h7i_record_payload(text, gallery, pricing, jsonld, modal)
        return text, n + k
    return f


def _h7i_480_out_of_order(css):
    """Move the ladder's phone step IN FRONT of the rule it overrides — the dead
    step batch H7b shipped, rebuilt on this batch's own section. Without it the
    ordering claim is a claim nobody has watched fail."""
    i = css.find('.sf-fdetail-config__opt.sf-tier {')
    j = css.find('@media (max-width: 480px) {', i)
    if i < 0 or j < 0:
        return css
    k = css.find('\n}', j)
    if k < 0:
        return css
    return css[:i] + css[j:k + 2] + css[i:j] + css[k + 2:]


def _h7i_drop_every(text, needle, repl):
    """A mutant that takes ALL occurrences, for a needle the file legitimately
    uses twice: replacing only the first leaves the second one holding the claim
    up, and a control that cannot break its claim proves nothing."""
    return text.replace(needle, repl)


BATCHES['h7i'] = {
    'name': 'H7i — the price ladder, the sample row, the inquiry button, the hero goes quiet',
    'mode': 'insert',
    'tokens': [
        ('?ver=2.10.69', '?ver=2.10.70'),                      # style.css
        ('config.js?ver=1.2.0', 'config.js?ver=1.3.0'),
    ],
    'transform': _h7i_transform,
    'applies': 92,          # hero 42 + cta 42 + gallery 2 + pricing 2 + offers 2 + modal 2
    'coverage': [
        ('?ver=2.10.69', 0),
        ('config.js?ver=1.2.0', 0),
        ('sf-formula-hero__actions', 0),
        ('sf-formula__cta--solid', 0),
        ('sf-formula-hero__build', 0),
        ('sf-fdetail2__cta" href="/contact/">Request Sample</a>', 0),
        ('sf-fdetail2__cta" href="/zh/contact/">Request Sample</a>', 0),
        # The legacy pill's own note: the form the ladder replaced, and the only
        # place "USD" (rather than "US$") was spelled that way.
        ('sf-fdetail-config__note">USD 2.5 / unit', 0),
        # The dialog carrier's copy of the same old price, which the ladder
        # replaced along with the pill.
        ('sf-inquiry-modal__value">200 — 2.5</dd>', 0),
    ],
    'insertions': [
        ('?ver=2.10.70', 75),
        ('config.js?ver=1.3.0', 42),
        ('sf-fdetail2__cta" href="/contact/#quote" data-sf-inquiry-open>Send Inquiry</a>', 21),
        ('sf-fdetail2__cta" href="/zh/contact/#quote" data-sf-inquiry-open>Send Inquiry</a>', 21),
        ('Batch H7i', 84),                                    # 42 hero + 42 cta comments
        ('sf-fdetail-config__tiers', 2),
        ('sf-tier__price', 6),                                # 3 cards x 2 pages
        ('sf-tier__range', 6),
        ('sf-tier__dot', 6),
        ('sf-fdetail-config__sample-cta', 2),
        ('data-sf-inquiry-sample', 2),
        ('sf-gallery__slide--video', 2),
        ('data-sf-gallery-tab="video"', 2),
        ('data-video-id="jNQXAC9IVRw"', 2),
        ('"highPrice":3.88', 1),
        ('"highPrice": 3.88', 1),
        ('sf-inquiry-modal__value">10-99 — US$3.88 · 100-999 — US$3.58 · ≥1,000 — US$3.28</dd>', 2),
    ],
    'counts': [
        # The pill that carried the old price list: its box, its text and its
        # note each lose exactly the one the record had.
        ('the old pill loses its note', 'sf-fdetail-config__note', 44, 42),
        ('the old pill loses its box', 'sf-fdetail-config__box', 468, 466),
        ('the old pill loses its text span', 'sf-fdetail-config__text', 118, 116),
        # One radio per pill becomes three per ladder, on the two pages.
        ('the pricing group goes from one choice to three',
         'data-sf-config-opt="pricing"', 2, 6),
        # ...but the group itself stays on the same two pages as before.
        ('the pricing group stays where it was',
         'data-sf-config-group="pricing"', 2, 2),
        # Task 11 is a CSS rule and nothing else: the value-preview line and the
        # hint are still in the bytes on every page, both sides. These two lines
        # are the claim that says so — if a later batch deletes them
        # server-side, this is where it shows up.
        ('the echo line is still server-rendered everywhere',
         'sf-fdetail-config__meta', 110, 110),
        ('so is the hint', 'sf-fdetail-config__hint', 68, 68),
        ('the right column keeps one cta per detail page', 'sf-fdetail2__cta', 42, 42),
        ('the hero keeps its meta line', 'sf-formula-hero__meta', 42, 42),
        ('the dialog carries two more openers', 'data-sf-inquiry-open', 84, 128),
    ],
    'unmoved': [
        ('the cookie banner', r'class="sf-cookie-banner"', 75),
        ('the float stack', r'class="sf-float-stack"', 75),
        ('the certificate dialog', r'sf-certmodal', 1),
        ('the navigation', r'wp-block-navigation', 75),
        ('the configurator', r'sf-fdetail-config__group', 42),
        ('the shape group', r'data-sf-config-group="shape"', 42),
        ('the gallery tabs', r'sf-gallery__tabs', 42),
        ('the side column', r'sf-fdetail2__side', 42),
    ],
    'per_page': [
        ('h1', r'<h1[ >]', 1),
        ('the new style token', r'style\.css\?ver=2\.10\.70', 1),
    ],
    'scoped': [
        ('the new right cta is on each detail page, once',
         r'sf-fdetail2__cta" href="(?:/zh)?/contact/#quote" data-sf-inquiry-open>Send Inquiry</a>',
         _is_formula_detail, 1),
        ('only the record the batch wrote has a ladder', 'sf-fdetail-config__tiers',
         lambda n: 'joint-support-soft-chews' in n, 1),
        ('and three tier cards in it', 'sf-tier__dot',
         lambda n: 'joint-support-soft-chews' in n, 3),
        ('its radio group names the three breaks',
         r'sf-fdetail-config__input" type="radio" name="sf-config-pricing"',
         lambda n: 'joint-support-soft-chews' in n, 3),
        ('only that record has a sample row', 'data-sf-inquiry-sample',
         lambda n: 'joint-support-soft-chews' in n, 1),
        ('only that record has a video frame', 'sf-gallery__slide--video',
         lambda n: 'joint-support-soft-chews' in n, 1),
        ('the dialog reprints the ladder, once', r'sf-inquiry-modal__value">10-99 — US\$3\.88',
         lambda n: 'joint-support-soft-chews' in n, 1),
    ],
    'order': [
        ('the inquiry button sits at the foot of the specification, after the badges',
         'sf-cert-badge', 'sf-fdetail2__cta" href=', _is_formula_detail),
        ('the ladder comes before the sample row, which is a different question',
         'sf-fdetail-config__tiers', 'sf-fdetail-config__sample"',
         lambda n: 'joint-support-soft-chews' in n),
        ('the video frame sits inside the stage, before the tab group',
         'sf-gallery__slide--video', 'sf-gallery__tabs',
         lambda n: 'joint-support-soft-chews' in n),
        ('and after the first photo, which is the frame it follows',
         'id="sf-gallery-slide-soft-chews-1"', 'sf-gallery__slide--video',
         lambda n: 'joint-support-soft-chews' in n),
    ],
    'h2_delta': None,
    # One named exception, three clauses — see jsonld_with_exception. The record
    # the batch wrote now offers three tiers where it offered one; every other
    # page's offer block is still collected and compared. The same rewrite is
    # declared as bytes in the transform, so the two passes agree about it from
    # both sides: one by how it reads, one by which bytes moved.
    'jsonld_delta': {
        'key': 'offers',
        'pages': ['formulas__joint-support-soft-chews',
                  'zh__formulas__joint-support-soft-chews'],
        'offers': {
            '@type': 'AggregateOffer',
            'priceCurrency': 'USD',
            'lowPrice': 3.28,
            'highPrice': 3.88,
            'offerCount': 3,
            # (price, minQuantity, maxQuantity); the last tier is open-ended.
            'tiers': [(3.88, 10, 99), (3.58, 100, 999), (3.28, 1000, None)],
        },
    },
    'sources': {
        'cfg': 'assets/js/config.js',
        'adm': 'inc/formula-admin.php',
        'tpl': 'templates/single-sf_formula.html',
    },
    'reinject': ('an old "Request Sample" link put back fails coverage',
                 'formulas__calming-soft-chews.html',
                 '<a class="sf-fdetail2__cta" href="/contact/#quote" data-sf-inquiry-open>Send Inquiry</a>',
                 '<a class="sf-fdetail2__cta" href="/contact/">Request Sample</a>'),
    'delete': ('one page loses the new style token fails coverage',
               'about.html', '?ver=2.10.70'),
    'nc13_mode': 'sighted',
    'nc13_label': ('NC13 the insert direction SEES a payload edit, and coverage confirms it'),
    'matrix': [
        ('the hero buttons are never removed',
         {'transform': _h7i_partial(cta=True, gallery=True, pricing=True, jsonld=True,
                                    modal=True)}, None),
        ('the right cta is never rewritten',
         {'transform': _h7i_partial(hero=True, gallery=True, pricing=True, jsonld=True,
                                    modal=True)}, None),
        ('the video frame is never patched in',
         {'transform': _h7i_partial(hero=True, cta=True, pricing=True, jsonld=True,
                                    modal=True)}, None),
        ('the price ladder is never patched in',
         {'transform': _h7i_partial(hero=True, cta=True, gallery=True, jsonld=True,
                                    modal=True)}, None),
        ('the offers are never rewritten',
         {'transform': _h7i_partial(hero=True, cta=True, gallery=True, pricing=True,
                                    modal=True)}, None),
        ('the dialog keeps the old price',
         {'transform': _h7i_partial(hero=True, cta=True, gallery=True, pricing=True,
                                    jsonld=True)}, None),
        ('the tokens are not folded', {'tokens': []}, None),
        ('the run count is declared one short', {'applies': 91}, None),
        ('nothing is applied at all',
         {'transform': (lambda t: (t, 0)), 'applies': 0}, None),
    ],
    'nc_source': [
        ('NC-src the source pass fails when the ladder stops being a grid',
         'style.css', '.sf-fdetail-config__tiers {\n\tdisplay: grid;',
         '.sf-zz-tiers-removed {\n\tdisplay: grid;'),
        ('NC-src the source pass fails when the phone step moves before the rule it overrides',
         'style.css', _h7i_480_out_of_order, None),
        ('NC-src the source pass fails when the option stops carrying the derived range',
         'functions.php', "'range_text' => $range,", "'range_text' => $min,"),
        ('NC-src the source pass fails when the admin loses the sample-price field',
         'inc/formula-admin.php', "'sf_formula_sample_price'", "'sf-zz-sample-price'"),
        ('NC-src the source pass fails when the template regains the hero action row',
         'templates/single-sf_formula.html',
         "<!-- Batch H7i: the hero's two buttons (Send Inquiry / Build Custom Formula)",
         '<div class="sf-formula-hero__actions">'),
        ('NC-src the source pass fails when the summary line drops the price',
         'functions.php',
         "$tier_meta[] = $range . ($note !== '' ? ' — ' . $note : '');",
         '$tier_meta[] = $range;'),
        ('NC-src the source pass fails when the sample button loses its hook',
         'assets/js/config.js',
         lambda s: _h7i_drop_every(s, 'data-sf-inquiry-sample', 'data-sf-zz-inquiry-sample'),
         None),
    ],
    # The three clauses of the json-ld exception, each made to fire. The third
    # is the one that carries the boundary today: no other record on this site
    # is priced, so an offer block appearing anywhere else is the failure that
    # can actually happen, and it is the page-set clause that names it.
    'nc_jsonld': [
        ('NC-jsonld the exception fires when a declared number moves',
         'formulas__joint-support-soft-chews.html',
         lambda s: s.replace('"offerCount":3', '"offerCount":4', 1)),
        ('NC-jsonld the exception fires when the declared record loses the key',
         'zh__formulas__joint-support-soft-chews.html',
         lambda s: s.replace('"offers":', '"offersX":', 1)),
        ('NC-jsonld the pass fires when an offer block appears off the record',
         'formulas__calming-soft-chews.html',
         lambda s: s.replace(
             '"@type":"Product","name":"Calming Soft Chews"',
             '"@type":"Product","offers":{"@type":"AggregateOffer",'
             '"priceCurrency":"USD","lowPrice":2.5,"highPrice":2.5,'
             '"offerCount":1,"priceSpecification":[]},"name":"Calming Soft Chews"', 1)),
    ],
    'nc_page': [
        ('NC-page the scoped dot count fails when the record loses a tier card',
         'formulas__joint-support-soft-chews.html',
         lambda s: s.replace('sf-tier__dot', 'sf-zz-dot', 1)),
        ('NC-page the scoped video count fails when the frame leaves the record',
         'formulas__joint-support-soft-chews.html',
         lambda s: s.replace('sf-gallery__slide--video', 'sf-zz-video', 1)),
    ],
    'nc_blind': ('formulas__calming-soft-chews.html',
                 'data-sf-inquiry-open>Send Inquiry</a>',
                 'data-sf-inquiry-open>Send InquiryX</a>'),
    'source': [
        ('style.css declares 2.10.70', 'css', r'(?m)^Version: 2\.10\.70$', True),
        ('no 2.10.69 header survives', 'css', r'(?m)^Version: 2\.10\.69$', False),
        ('functions.php enqueues 2.10.70 for style.css', 'php',
         r"wp_enqueue_style\('sinofresh-style'[^;]*'2\.10\.70'", True),
        ('functions.php enqueues 1.3.0 for config.js', 'php',
         r"wp_enqueue_script\('sinofresh-config'[^;]*'1\.3\.0'", True),
        ('no 1.2.0 config enqueue survives', 'php',
         r"'sinofresh-config'[^;]*'1\.2\.0'", False),
        ('the ladder section names the batch', 'css',
         r'63\. Quantity & Pricing, the ladder', True),
        ('the ladder is laid out as a grid', 'css_live',
         r'\.sf-fdetail-config__tiers \{[^}]*display: grid;', True),
        ('the unit price is the headline of each card', 'css_live',
         r'\.sf-tier__price \{', True),
        ('the dot follows the input, not its neighbour', 'css_live',
         r'\.sf-fdetail-config__input:checked ~ \.sf-tier__dot \{', True),
        ('the hint is withdrawn only while the script is running', 'css_live',
         r'\.sf-fdetail-config--js \.sf-fdetail-config__hint \{ display: none; \}', True),
        # The ordering claim as ONE chain with a measured budget: the base card
        # rule and its phone step are 3227 comment-stripped characters apart. A
        # budget that could leap to some other 480 block would not be a claim;
        # NC-src reverses this and watches it fail.
        ('the phone step comes after the rule it overrides', 'css_live',
         r'\.sf-fdetail-config__opt\.sf-tier \{[^}]*padding: 11px 8px 27px'
         r'[\s\S]{0,3600}@media \(max-width: 480px\) \{[\s\S]{0,300}'
         r'\.sf-fdetail-config__opt\.sf-tier \{', True),
        ('the renderer derives the range label from both ends', 'php',
         r'sf_tier_range_label\(\$min, \$max\)', True),
        ('the option carries the derived range', 'php',
         r"'range_text' => \$range,", True),
        ('the renderer formats money through one helper', 'php',
         r'sf_tier_price_label\(', True),
        ('the ladder reads the sample fee off the record', 'php',
         r'sf_formula_sample_price', True),
        ('the ladder names its unit', 'php', r"'unit' => 'pieces'", True),
        ('the offer carries both ends of every range', 'php',
         r"'maxQuantity'", True),
        ('the summary line is the range and the price, joined', 'php',
         r"\$tier_meta\[\] = \$range \. \(\$note !== ''", True),
        # The dialog carrier prints the group's own summary, which is why the
        # ladder reaches it without the carrier knowing the ladder exists.
        ('the group publishes the joined ladder as its summary', 'php',
         r"'key' => 'pricing', 'label' => 'Quantity & Pricing', 'meta' => implode\(' · ', \$tier_meta\),",
         True),
        ('the admin table asks for min, max and price', 'adm',
         r"'min' => 'Min quantity', 'max' => 'Max quantity', 'price' => 'Unit price \(USD\)'",
         True),
        ('the admin has a sample-price field', 'adm',
         r"sf_formula_sample_price", True),
        ('the template carries the inquiry button, not a sample link', 'tpl',
         r'<a class="sf-fdetail2__cta" href="/contact/#quote" data-sf-inquiry-open>Send Inquiry</a>',
         True),
        ('the template no longer carries the hero action row', 'tpl_live',
         r'sf-formula-hero__actions', False),
        ('config.js fills the message from the sample button', 'cfg',
         r'data-sf-inquiry-sample', True),
        ('config.js writes the request into the dialog', 'cfg',
         r'I would like to request a sample', True),
    ],
}


# ---------------------------------------------------------- H7j batch
# Batch H7j is three edits that share one cause: the header bar and the band
# under the hero were the only two things on a dosage page that did not line up
# with the page around them.
#
#   10  the seven top-level menu items sat 10px apart; the brief's floor is 20.
#       The gap lives in the navigation block's own
#       `style.spacing.blockGap`, and WordPress hashes a block's attributes
#       into its wp-container-* class — so raising the gap renumbers the
#       container class (2cc8d8df -> 0c89a756) and rewrites the one inline
#       `gap:` rule the head prints, on all 75 pages. That coupling was
#       predicted before the candidate was captured, and it is why this
#       declaration has TWO entries for one attribute.
#   15  .sf-facts-mini ran edge to edge while every neighbouring band's content
#       sat on the content column. A style.css rule, so no page byte moves —
#       only the version token.
#   20  the navigation never said where the visitor was. Measured before the
#       batch: zero current-menu-item and zero aria-current on all 75 pages,
#       because a wp:navigation block carrying a `ref` renders the
#       wp_navigation post's own core/navigation-link blocks, so
#       wp_nav_menu()'s _wp_menu_item_classes_by_context() never runs.
#
# Item 20 is markup and it is the only one that moves the page bytes, so the
# transform below has to reproduce the marking itself — in Python, from the same
# three facts the PHP reads: the request path, the menu, and the item's own url.

# The menu, transcribed from the wp_navigation post that parts/header.html
# points at (`{"ref":16}`). Deliberately NOT read out of the capture: a model
# derived from the candidate's own markup would agree with the candidate by
# construction, and the one thing worth pinning here is WHICH item lights up on
# which page — a claim about the menu, not about the bytes that render it.
#
# Seven top-level items. The Products dropdown holds eight dosage links and,
# ninth and last, "All Formulas" — which is the only route to /formulas/ this
# menu offers, and therefore the reason a formula page lights up Products. That
# is the rule the batch shipped, not an accident of the render: the PRUNE below
# is what turns it into "the item that owns the dropdown is current" instead of
# "the ninth dropdown link is current".
H7J_MENU = (
    ('/products/', ('/products/soft-chews/', '/products/tablets/',
                    '/products/powders/', '/products/pastes/',
                    '/products/drops/', '/products/liquids/',
                    '/products/fish-oil/', '/products/dental-chews/',
                    '/formulas/')),
    ('/services/', ()),
    ('/quality/', ()),
    ('/about/', ()),
    ('/factory-tour/', ()),
    ('/blog/', ()),
    ('/contact/', ()),
)


def _h7j_under(path, url):
    """sf_nav_path_under(), transcribed: both sides end in "/" because every
    permalink on this site does, so the prefix test is already segment-safe."""
    url = '/' + url.strip('/') + '/'
    return path == url or path.startswith(url)


def _h7j_is_page(path, url):
    """sf_nav_path_is(). The difference from the test above is what aria-current
    turns on: a link that points AT the page is "page", a link whose section
    merely CONTAINS it is "true"."""
    return path == '/' + url.strip('/') + '/'


def _h7j_page_path(name):
    """Capture file name -> request path. The inverse of the fetch tool's own
    slug rule, which is the site's permalink shape and not the candidate's."""
    return '/' if name == 'root' else '/' + name.replace('__', '/') + '/'


def _h7j_expect(name):
    """(href, aria) the menu should carry on this page, or None. Computed from
    the request path and the menu — never from the candidate.

    This is its own implementation of the rule, which is the point: the scoped
    counts below say "the mark is HERE on these pages" and that claim is worth
    nothing if it is read back out of the thing it is meant to test."""
    full = _h7j_page_path(name)
    zh = full.startswith('/zh/')
    rel = ('/' + full[4:]) if zh else full      # what sf_nav_request_path() yields
    for href, kids in H7J_MENU:
        if not (_h7j_under(rel, href) or any(_h7j_under(rel, k) for k in kids)):
            continue
        return (('/zh' + href) if zh else href,
                'page' if _h7j_is_page(rel, href) else 'true')
    return None


def _h7j_in_menu(name):
    return _h7j_expect(name) is not None


def _h7j_mark_is(href, aria=None):
    """Scope: the pages whose menu should mark this href."""
    return lambda n: (lambda e: bool(e) and e[0] == href and (aria is None or e[1] == aria))(_h7j_expect(n))


def _h7j_aria_is(aria):
    """Scope: the pages whose menu should announce this aria-current value."""
    return lambda n: (lambda e: bool(e) and e[1] == aria)(_h7j_expect(n))


H7J_HREFLANG = re.compile(r'<link rel="alternate" hreflang="%s" href="([^"]+)"')


def _h7j_request_path(text):
    """The request path, read off the page's own language-announcement pair.

    sf_nav_request_path() reads $_SERVER['REQUEST_URI']; a capture has no
    request, so the same fact comes from the two hreflang links every page
    carries, and the language is the one the page itself declares so the pair
    cannot be crossed.

    NOT the canonical link: three of the 75 pages — the blog index, the formulas
    archive and its zh twin — carry no canonical at all, and two of those three
    are pages this batch has to mark. A reader that gave up on them would have
    put the batch's own coverage claim out of its own reach."""
    zh = '<html lang="zh-CN"' in text
    m = re.search(H7J_HREFLANG.pattern % ('zh-CN' if zh else 'en-US'), text)
    if not m:
        return None
    path = urlsplit(m.group(1)).path or '/'
    home = '/zh/' if zh else '/'
    if home != '/' and path.startswith(home):
        path = '/' + path[len(home):].lstrip('/')
    return path or '/'


H7J_NAV_UL = re.compile(r'<ul[^>]*class="wp-block-navigation__container[^"]*"[^>]*>')
H7J_NAV_TOKEN = re.compile(
    r'</?ul\b|<a class="wp-block-navigation-item__content"([^>]*)>')
H7J_BARE = 'class="wp-block-navigation-item__content"'
H7J_MARKED = 'class="wp-block-navigation-item__content sf-nav__link"'
H7J_MARKED_ON = ('class="wp-block-navigation-item__content sf-nav__link'
                 ' is-active" aria-current="%s"')
H7J_CONTAINER_TOKEN = '2cc8d8df'
H7J_CONTAINER_RENAMED = '0c89a756'
H7J_GAP_OLD = 'gap:10px'
H7J_GAP_NEW = 'gap:20px'
H7J_HEADER_OLD = 'class="wp-block-group sf-header '
H7J_HEADER_NEW = 'class="wp-block-group sf-header sf-header--nav-underline '


def _h7j_swap(text, old, new):
    """Every occurrence, and how many moved. `replace(old, new, 1)` would be
    wrong for the container token, which is legitimately on the page twice (the
    inline rule and the element that matches it), and a control that fixes only
    the first leaves the second holding the claim up."""
    k = text.count(old)
    return text.replace(old, new), k


def _h7j_nav_span(text):
    """(start, end) of the navigation list, by matching ul depth — the outer
    `<ul>` from its open tag to its own close, not the first `</ul>`, which
    closes the dropdown."""
    m = H7J_NAV_UL.search(text)
    if not m:
        return None
    i, depth = m.start(), 0
    for mo in re.finditer(r'</?ul\b', text[i:]):
        depth += 1 if mo.group(0) == '<ul' else -1
        if depth == 0:
            return i, text.index('>', i + mo.end()) + 1
    return None


def _h7j_nav_links(nav):
    """(offset of the class attribute, depth, href) for every link in one
    navigation list.

    depth 1 is a top-level item, depth 2 a link inside a dropdown, and that
    distinction IS the submenu rule: the item that owns a dropdown gets the
    mark, and the child that matched gives it up."""
    out, depth = [], 0
    for mo in H7J_NAV_TOKEN.finditer(nav):
        tok = mo.group(0)
        if tok.startswith('<ul'):
            depth += 1
        elif tok.startswith('</ul'):
            depth -= 1
        else:
            h = re.search(r'href="([^"]+)"', mo.group(1) or '')
            out.append((mo.start() + 3, depth, h.group(1) if h else ''))
    return out


def _h7j_mark_nav(nav, path, zh=False, owns=True, prune=True, aria=True):
    """The links of one navigation list, marked the way the two render_block
    filters mark them.

    The hrefs are read off the RENDERED anchors, which on a zh page carry the
    language prefix, while `path` has already had it stripped — so the prefix
    comes off the href too. That is not a convenience: the PHP compares
    sf_nav_request_path()'s stripped path against the block's own `url`
    attribute, which TranslatePress never rewrites. Both sides are language-less
    there, and both have to be here.

    A dropdown link that matches is marked by its own filter and then PRUNED by
    the item that owns the dropdown — so no dropdown link ever keeps a mark, and
    the owner inherits one instead. `prune=False` is the mutant that leaves the
    child's mark in place; `owns=False` is the one where the owner never hears
    about it. Both are plausible wrong answers and both are in the matrix."""
    links = _h7j_nav_links(nav)
    if zh:
        links = [(off, d, ('/' + h[4:].lstrip('/')) if h.startswith('/zh/') else h)
                 for off, d, h in links]
    tops = [k for k, (_, d, _) in enumerate(links) if d == 1]
    owns_at = {}
    for pos, k in enumerate(tops):
        end = tops[pos + 1] if pos + 1 < len(tops) else len(links)
        owns_at[k] = any(_h7j_under(path, links[j][2])
                         for j in range(k + 1, end) if links[j][1] > 1)

    edits = []
    for k, (off, depth, href) in enumerate(links):
        self_ = _h7j_under(path, href)
        page = _h7j_is_page(path, href)
        if depth == 1:
            active = self_ or (owns and owns_at.get(k, False))
        else:
            active = self_ and not prune
        if active:
            new = H7J_MARKED_ON % ('page' if (aria and page) else 'true')
        else:
            new = H7J_MARKED
        edits.append((off, H7J_BARE, new))
    for off, old, new in reversed(edits):
        if nav[off:off + len(old)] != old:
            continue
        nav = nav[:off] + new + nav[off + len(old):]
    return nav, len(edits)


def _h7j_transform(text, container=True, gap=True, header=True, marks=True,
                   owns=True, prune=True, aria=True):
    """H7j's declared edit to one baseline page: the container renumbered, the
    gap raised, the header's variant class, and the current item marked. The
    version token is NOT this function's business — fold() applies the declared
    token pairs."""
    n = 0
    if container:
        text, k = _h7j_swap(text, H7J_CONTAINER_TOKEN, H7J_CONTAINER_RENAMED)
        n += k
    if gap:
        text, k = _h7j_swap(text, H7J_GAP_OLD, H7J_GAP_NEW)
        n += k
    if header:
        text, k = _h7j_swap(text, H7J_HEADER_OLD, H7J_HEADER_NEW)
        n += k
    if marks:
        span = _h7j_nav_span(text)
        path = _h7j_request_path(text)
        if span and path:
            i, j = span
            nav, k = _h7j_mark_nav(text[i:j], path,
                                   zh='<html lang="zh-CN"' in text,
                                   owns=owns, prune=prune, aria=aria)
            text = text[:i] + nav + text[j:]
            n += k
    return text, n


def _h7j_partial(container=True, gap=True, header=True, marks=True,
                 owns=True, prune=True, aria=True):
    """Mutants that skip one declared edit, or keep one declared rule wrong;
    each must break the proof."""
    def f(text):
        return _h7j_transform(text, container=container, gap=gap, header=header,
                              marks=marks, owns=owns, prune=prune, aria=aria)
    return f


def _h7j_header_10px(text):
    """Put the old gap back in the block template. The block attributes live in
    an HTML comment, so the live twin of that file has them stripped — this is
    the mutant that keeps the raw-only claim honest."""
    return text.replace('"blockGap":"20px"', '"blockGap":"10px"')


H7J_MARK_PAT = r'class="wp-block-navigation-item__content sf-nav__link is-active"'


BATCHES['h7j'] = {
    'name': "H7j — the nav gap, the facts band's gutter, and the current item marked",
    'mode': 'insert',
    'tokens': [
        ('?ver=2.10.70', '?ver=2.10.71'),                      # style.css
    ],
    'transform': _h7j_transform,
    'applies': 1500,        # 75 x (container 2 + gap 1 + header 1 + marks 16)
    'coverage': [
        ('?ver=2.10.70', 0),
        ('2cc8d8df', 0),
        ('gap:10px', 0),
        ('class="wp-block-group sf-header has-card-white-color', 0),
        ('class="wp-block-navigation-item__content"', 0),
    ],
    'insertions': [
        ('?ver=2.10.71', 75),
        ('0c89a756', 150),
        ('gap:20px', 75),
        ('class="wp-block-group sf-header sf-header--nav-underline', 75),
        # Each claim below is a strict refinement of the one above it, so the
        # three together pin the shape rather than three separate totals: the
        # marker reaches all 1200 links, 67 of them say they are current, and
        # the 67 split 7 / 60 between the two aria-current values.
        (' sf-nav__link', 1200),
        (' sf-nav__link is-active" aria-current="page"', 7),
        (' sf-nav__link is-active" aria-current="true"', 60),
    ],
    'counts': [
        # The mark is ADDED to every link; the class WordPress already put there
        # stays, which is why the bare form goes to zero and the substring count
        # does not move.
        ('the wrapper class stays on all sixteen links',
         'wp-block-navigation-item__content', 2280, 2280),
        ('the bare form every link carried is gone',
         'class="wp-block-navigation-item__content"', 1200, 0),
        # One mark per page the menu covers — 67 of 75 — and none elsewhere.
        ('the menu gains one current item per page it covers',
         'sf-nav__link is-active"', 0, 67),
        ('the page-identity value is the batch\'s 7 links',
         'aria-current="page"', 94, 101),
        ('and the section value appears for the first time, 60 times',
         'aria-current="true"', 0, 60),
        # The two is-active sets the ladder already carried must not move: the
        # gallery tab and the blog chip. 44 before, 44 after.
        ('the gallery tab keeps its own is-active', 'sf-gallery__tab is-active', 42, 42),
        ('so does the blog chip', 'sf-fchip is-active', 2, 2),
        # The gap moves in two places at once, which is the coupling this
        # declaration exists to state.
        ('the container is renumbered in both of its two places',
         '2cc8d8df', 150, 0),
        ('the element keeps exactly one header class',
         'class="wp-block-group sf-header ', 75, 75),
    ],
    'unmoved': [
        ('the cookie banner', r'class="sf-cookie-banner"', 75),
        ('the float stack', r'class="sf-float-stack"', 75),
        ('the certificate dialog', r'sf-certmodal', 1),
        ('the primary cta', r'sf-quote-cta', None),
        ('the gallery tabs', r'sf-gallery__tabs', 42),
        ('the configurator', r'sf-fdetail-config__group', 42),
        ('the side column', r'sf-fdetail2__side', 42),
        ('the core-facts band itself', r'class="sf-facts-mini"', None),
    ],
    'per_page': [
        ('h1', r'<h1[ >]', 1),
        ('the new style token', r'style\.css\?ver=2\.10\.71', 1),
        ('the gap rule', r'\.wp-container-core-navigation-is-layout-0c89a756\{gap:20px;\}', 1),
        ('the header variant class', r'sf-header--nav-underline', 1),
    ],
    'scoped': [
        # The two structural counts, on every page. The first pattern carries
        # no closing quote on purpose: the marked link's class attribute
        # continues with " is-active", so a pattern that closed the quote would
        # count 15 and quietly exclude the one link the batch is about.
        ('the nav list carries sixteen marked links',
         r'class="wp-block-navigation-item__content sf-nav__link', lambda n: True, 16),
        # ONE entry, both directions. `scoped` expects `want` on the pages the
        # scope admits and ZERO on the rest, so naming the scope is naming the
        # negative too — a mark on /faq/ fails this line as surely as a missing
        # mark on /about/. Splitting it into two entries would have made the
        # "and none elsewhere" half expect zero on the pages that carry one.
        ('exactly one of them is current on every page the menu covers — and none '
         'on the eight it does not',
         r'class="wp-block-navigation-item__content sf-nav__link is-active"',
         _h7j_in_menu, 1),
        # WHERE it lands, page by page, from the independent model. Four clauses
        # because there are three answers, and the first two are also the claim
        # the probe is here for: a link that points AT the page announces
        # "page", a link whose section merely CONTAINS it announces "true".
        # Read together they say no page carries the wrong one of the two,
        # because each entry demands zero of its own value everywhere else.
        ('a link that points AT the page is the one marked',
         H7J_MARK_PAT + r' aria-current="page"', _h7j_aria_is('page'), 1),
        ('a link whose section only CONTAINS the page is the one marked',
         H7J_MARK_PAT + r' aria-current="true"',
         _h7j_aria_is('true'), 1),
        # ...and the sense test alone does not say WHICH link. The mark is one
        # href per page and the href differs page by page, so this half is a
        # table rather than a pattern: seven clauses for the seven links that
        # point AT a page, one for the Products branch on the pages it owns, one
        # for its zh twin. Each carries its own href and the aria value that
        # href must have, so a mark that moved to a DIFFERENT one of the seven
        # leaves its own clause one short even though the item it moved to is
        # itself legitimate — which is exactly the mutant NC-page builds.
        ('the Products branch owns the formula and dosage pages',
         H7J_MARK_PAT + r' aria-current="true"[^>]*?href="/products/"',
         _h7j_mark_is('/products/', 'true'), 1),
        ('and on the zh twins it is the zh Products link',
         H7J_MARK_PAT + r' aria-current="true"[^>]*?href="/zh/products/"',
         _h7j_mark_is('/zh/products/', 'true'), 1),
    ] + [
        ('the mark on %s is the link that points at it' % href,
         H7J_MARK_PAT + ' aria-current="page"[^>]*?href="%s"' % re.escape(href),
         _h7j_mark_is(href, 'page'), 1)
        for href, _kids in H7J_MENU
    ],
    'order': [
        ('the mark sits inside the navigation list',
         'wp-block-navigation__container', 'sf-nav__link is-active"', _h7j_in_menu),
        # `wp-block-navigation is-layout-flex` and not the bare class name: the
        # head's inline stylesheet mentions every block class long before the
        # markup does, and a claim that compared against the stylesheet would
        # have been red on all 75 pages while the markup was in perfect order.
        # The same trap took the dropdown claim below once already — both
        # needles are now the two-class form that only the markup carries.
        ('the header variant class precedes the bar it paints',
         'sf-header--nav-underline', 'wp-block-navigation is-layout-flex',
         lambda n: True),
        ('the container rule is declared before the element that matches it',
         '.wp-container-core-navigation-is-layout-0c89a756{gap:20px;}',
         'is-layout-flex wp-container-core-navigation-is-layout-0c89a756',
         lambda n: True),
        ('the dropdown links come after the item that owns them',
         'has-child open-on-hover-click wp-block-navigation-submenu',
         'wp-block-navigation__submenu-container wp-block-navigation-submenu',
         lambda n: True),
    ],
    'h2_delta': None,
    'jsonld_delta': None,
    'sources': {
        'hdr': 'parts/header.html',
    },
    'reinject': ('an old 10px container put back fails coverage',
                 'about.html', '0c89a756', '2cc8d8df'),
    'delete': ('one page loses the header variant class fails coverage',
               'about.html', 'sf-header--nav-underline'),
    'nc13_mode': 'sighted',
    'nc13_label': ('NC13 the insert direction SEES a payload edit, and coverage confirms it'),
    'matrix': [
        ('the tokens are not folded', {'tokens': []}, None),
        ('the container keeps its old name',
         {'transform': _h7j_partial(container=False)}, None),
        ('the gap is renamed but never raised',
         {'transform': _h7j_partial(gap=False)}, None),
        ('the header keeps one class',
         {'transform': _h7j_partial(header=False)}, None),
        ('no link is marked',
         {'transform': _h7j_partial(marks=False)}, None),
        ('the dropdown\'s own link keeps the mark',
         {'transform': _h7j_partial(prune=False)}, None),
        ('the owner never hears that a child matched',
         {'transform': _h7j_partial(owns=False)}, None),
        ('every mark announces "true"',
         {'transform': _h7j_partial(aria=False)}, None),
        ('the run count is declared one short', {'applies': 1499}, None),
        ('nothing is applied at all',
         {'transform': (lambda t: (t, 0)), 'applies': 0}, None),
    ],
    'nc_source': [
        ('NC-src the source pass fails when the default mark loses its rules',
         'style.css', '.sf-header--nav-underline .sf-nav__link.is-active {',
         '.sf-zz-nav-underline .sf-nav__link.is-active {'),
        ('NC-src the source pass fails when the facts band loses its gutter',
         'style.css',
         '.sf-facts-mini {\n\tpadding-left: max(38px, calc((100% - '
         'var(--wp--style--global--content-size, 1200px)) / 2));',
         '.sf-zz-facts {'),
        ('NC-src the source pass fails when one of the six marks loses its style',
         'style.css', '.sf-header--nav-pill .sf-nav__link.is-active {',
         '.sf-header--nav-pill .sf-nav__link.is-activeX {'),
        ('NC-src the source pass fails when a slug leaves the array',
         # A literal rename of `sf_nav_active_styles` cannot work here, and the
         # reason is worth keeping: the FIRST occurrence of that name in
         # functions.php is a doc comment (line 5120, "sf_nav_active_styles()'
         # keys — anything else falls back..."), not the definition on line 5351.
         # A first-occurrence replace therefore edits a comment, the file stays
         # functionally identical, and the control goes green while proving
         # nothing. So the mutant removes a real entry instead: the array stops
         # offering six marks, which is the regression the slug set can suffer.
         'functions.php', "\t\t'pill'       => 'Green pill',\n", ''),
        ('NC-src the source pass fails when the whitelist stops falling back',
         # Replaces EVERY copy on purpose. The guard is written twice — once in
         # the option's sanitiser (5127) and once in the reader (5369) — and the
         # claim searches the file, so a first-occurrence replace leaves the
         # second copy to satisfy it and the control never fires.
         'functions.php',
         lambda s: s.replace(
             "return isset($all[$v]) ? $v : $d['sf_nav_active_style'];", 'return $v;'),
         None),
        ('NC-src the source pass fails when a submenu stops inheriting',
         'functions.php',
         "$owns = (false !== strpos($tail, ' is-active'));",
         '$owns = false;'),
        ('NC-src the source pass fails when a matched child stops being pruned',
         'functions.php',
         "' sf-nav__link is-active\" aria-current=\"page\"',",
         "' sf-zz-nav__link is-active\" aria-current=\"page\"',"),
        ('NC-src the source pass fails when aria-current stops distinguishing',
         'functions.php', "$is_page ? 'page' : 'true'", "'page'"),
        ('NC-src the source pass fails when the language prefix stops being stripped',
         'functions.php', 'substr($path, strlen($home))', '$path'),
        ('NC-src the source pass fails when the header class moves off the element',
         'functions.php',
         "(<[a-z][a-z0-9]* class=\"wp-block-group sf-header)(?=[ \"])",
         "(<[a-z][a-z0-9]* class=\"wp-block-group sf-zz-header)(?=[ \"])"),
        ('NC-src the source pass fails when the gap goes back to 10px',
         'parts/header.html', _h7j_header_10px, None),
        # --- 63c, and the 63b repair behind it -----------------------------
        ('NC-src the source pass fails when the left rule goes back to the shallow '
         'selector its own base rule outranks',
         'style.css',
         '.sf-header--nav-left-line .wp-block-navigation__container > '
         '.wp-block-navigation-item > .sf-nav__link.is-active {',
         '.sf-header--nav-left-line .sf-nav__link.is-active {'),
        ('NC-src the source pass fails when the drawer loses the underline restatement',
         'style.css',
         '.sf-header--nav-underline .wp-block-navigation__responsive-container'
         '.is-menu-open',
         '.sf-zz-header--nav-underline .wp-block-navigation__responsive-container'
         '.is-menu-open'),
        ('NC-src the source pass fails when the drawer loses the thick-line restatement',
         'style.css',
         '.sf-header--nav-thick-line .wp-block-navigation__responsive-container'
         '.is-menu-open',
         '.sf-zz-header--nav-thick-line .wp-block-navigation__responsive-container'
         '.is-menu-open'),
        ('NC-src the source pass fails when the drawer loses the colour restatement',
         'style.css',
         '.sf-header--nav-color .wp-block-navigation__responsive-container'
         '.is-menu-open',
         '.sf-zz-header--nav-color .wp-block-navigation__responsive-container'
         '.is-menu-open'),
        ('NC-src the source pass fails when the separator restore is dropped',
         'style.css', '.sf-header:where(.sf-header--nav-underline,',
         '.sf-zz-header:where(.sf-header--nav-underline,'),
        ('NC-src the source pass fails when the drawer section re-states the left rule',
         # An INSERTION, appended inside the same media query and after the
         # separator rule's own last property, so it breaks the absence claim and
         # nothing else: the separator claim's regex has already finished by the
         # time the inserted selector starts.
         'style.css',
         "\t\tborder-bottom-color: rgba(255, 255, 255, 0.14);\n\t}\n}",
         "\t\tborder-bottom-color: rgba(255, 255, 255, 0.14);\n\t}\n"
         "\t.sf-header--nav-left-line .wp-block-navigation__responsive-container"
         ".is-menu-open .sf-nav__link { color: red; }\n}"),
    ],
    'nc_page': [
        ('NC-page the scoped count fails when a page loses its mark',
         'about.html',
         lambda s: s.replace(' sf-nav__link is-active" aria-current="page"',
                             ' sf-nav__link"', 1)),
        ('NC-page the scoped count fails when a page gains a second mark',
         'blog.html',
         lambda s: s.replace(
             '<a class="wp-block-navigation-item__content sf-nav__link"  href="/services/">',
             '<a class="wp-block-navigation-item__content sf-nav__link is-active"'
             ' aria-current="page"  href="/services/">', 1)),
        ('NC-page the scoped href claim fails when the mark moves to another item',
         'about.html',
         lambda s: s.replace('aria-current="page"  href="/about/"',
                             'aria-current="page"  href="/quality/"', 1)),
        ('NC-page the aria claim fails when the value is swapped',
         'about.html',
         lambda s: s.replace('aria-current="page"  href="/about/"',
                             'aria-current="true"  href="/about/"', 1)),
    ],
    'nc_blind': ('about.html',
                 ' sf-nav__link is-active" aria-current="page"',
                 ' sf-nav__link is-active" aria-current="pageX"'),
    'source': [
        ('style.css declares 2.10.71', 'css', r'(?m)^Version: 2\.10\.71$', True),
        ('no 2.10.70 header survives', 'css', r'(?m)^Version: 2\.10\.70$', False),
        ('functions.php enqueues 2.10.71 for style.css', 'php',
         r"wp_enqueue_style\('sinofresh-style'[^;]*'2\.10\.71'", True),
        ('the header asks the navigation for a 20px gap', 'hdr',
         r'"blockGap":"20px"', True),
        ('and not for the 10px it had', 'hdr', r'"blockGap":"10px"', False),
        # 63a — the facts band. The box stays full width on purpose; only the
        # content moves in, because the band draws the two hairlines.
        ('the core-facts band takes the content gutter', 'css_live',
         r'\.sf-facts-mini \{\n\tpadding-left: max\(38px, calc\(\(100% - '
         r'var\(--wp--style--global--content-size, 1200px\)\) / 2\)\);\n'
         r'\tpadding-right: max\(38px, calc\(\(100% - '
         r'var\(--wp--style--global--content-size, 1200px\)\) / 2\)\);\n\}', True),
        ('and drops to 20px at the phone breakpoint the hero uses', 'css_live',
         r'@media \(max-width: 1024px\) \{\n\t\.sf-facts-mini \{\n'
         r'\t\tpadding-left: 20px;\n\t\tpadding-right: 20px;\n\t\}\n\}', True),
        ('the band keeps its space-between', 'css_live',
         r'\.sf-facts-mini \{[^}]*padding-left', True),
        # 63b — the six marks, one claim each, so a variant cannot silently
        # lose its rules while the other five keep the section honest.
        ('the default mark is the underline', 'css_live',
         r'\.sf-header--nav-underline \.sf-nav__link\.is-active \{', True),
        ('the block mark is defined', 'css_live',
         r'\.sf-header--nav-bg \.sf-nav__link\.is-active \{', True),
        ('the thick-line mark is defined', 'css_live',
         r'\.sf-header--nav-thick-line \.sf-nav__link\.is-active \{', True),
        ('the colour mark is defined', 'css_live',
         r'\.sf-header--nav-color \.sf-nav__link\.is-active \{', True),
        # `left-line` is the one mark whose active rule is NOT written in the
        # short form. It has to be written at the depth of the base rule above it
        # — the one that reserves the 3px with `border-left: 3px solid
        # transparent` — or that base rule, being one class deeper, wins and the
        # mark paints a 3px rule of nothing. Measured at 1440px before the fix:
        # `border-left-width: 3px`, `border-left-color: rgba(0, 0, 0, 0)`, at
        # every width. So this claim is deliberately the long selector, and the
        # short one is claimed ABSENT right after it: the pair is what makes the
        # depth a recorded fact rather than a style choice.
        ('the left-rule mark is defined at the depth its base rule is', 'css_live',
         r'\.sf-header--nav-left-line \.wp-block-navigation__container > '
         r'\.wp-block-navigation-item > \.sf-nav__link\.is-active \{', True),
        ('...and not in the short form its base rule would outrank', 'css_live',
         r'\.sf-header--nav-left-line \.sf-nav__link\.is-active \{', False),
        ('the pill mark is defined', 'css_live',
         r'\.sf-header--nav-pill \.sf-nav__link\.is-active \{', True),
        ('every mark reserves its space on all seven top-level links', 'css_live',
         r'\.sf-header--nav-pill \.wp-block-navigation__container > '
         r'\.wp-block-navigation-item > \.sf-nav__link \{', True),
        ('and no mark reaches the links inside the dropdown', 'css_live',
         r'submenu-container[^}]*\.sf-nav__link', False),
        # 63c — the same marks in the phone drawer, and the drawer's own
        # furniture. The drawer's row rule is five classes deep and its modal
        # colour rule four; every mark is three or four, so inside the drawer
        # four of the six marks were invisible. Measured at 375px with the drawer
        # open, on the shipped default: the current row was indistinguishable
        # from an unmarked one. One claim per repair, and one absence claim for
        # the repair that deliberately lives elsewhere.
        ('the drawer re-states the underline mark at the depth it needs', 'css_live',
         r'\.sf-header--nav-underline \.wp-block-navigation__responsive-container'
         r'\.is-menu-open \.wp-block-navigation__container > '
         r'\.wp-block-navigation-item > \.sf-nav__link\.is-active \{\n'
         r'\t\tborder-bottom-width: 2px;', True),
        ('...and the thick line at four pixels', 'css_live',
         r'\.sf-header--nav-thick-line \.wp-block-navigation__responsive-container'
         r'\.is-menu-open \.wp-block-navigation__container > '
         r'\.wp-block-navigation-item > \.sf-nav__link\.is-active \{\n'
         r'\t\tborder-bottom-width: 4px;', True),
        ('...and the brand green the colour mark draws with', 'css_live',
         r'\.sf-header--nav-color \.wp-block-navigation__responsive-container'
         r'\.is-menu-open \.wp-block-navigation__container > '
         r'\.wp-block-navigation-item > \.sf-nav__link\.is-active \{\n'
         r'\t\tcolor: var\(--wp--preset--color--brand-green\);', True),
        ('and the drawer keeps its own row separator under every mark', 'css_live',
         r'\.sf-header:where\(\.sf-header--nav-underline, \.sf-header--nav-bg, '
         r'\.sf-header--nav-thick-line,\n\t\t\.sf-header--nav-color, '
         r'\.sf-header--nav-left-line, \.sf-header--nav-pill\)[\s\S]{0,240}'
         r'\.sf-nav__link:not\(\.is-active\) \{\n\t\tborder-bottom-color: '
         r'rgba\(255, 255, 255, 0\.14\);', True),
        # ...and `left-line` is NOT restated in 63c, on purpose: its repair was a
        # conflict between two rules inside 63b, so it was fixed in 63b. Claiming
        # the absence keeps a later edit from "helpfully" duplicating it here.
        ('the left rule is not re-stated in the drawer section', 'css_live',
         r'\.sf-header--nav-left-line \.wp-block-navigation__responsive-container'
         r'\.is-menu-open', False),
        # functions.php — the rule and its switches.
        ('the six slugs live in one array', 'php',
         r"function sf_nav_active_styles\(\) \{", True),
        ('all six slugs are in it', 'php',
         r"'underline'  => 'Underline',[\s\S]{0,240}'pill'       => 'Green pill',", True),
        ('the shipped default is the underline', 'php',
         r"'sf_nav_active_style' => 'underline',", True),
        ('the option is registered with a sanitiser', 'php',
         r"register_setting\('sf_site_settings', 'sf_nav_active_style'", True),
        ('and it falls back to the default rather than emit a dead class', 'php',
         r"return isset\(\$all\[\$v\]\) \? \$v : \$d\['sf_nav_active_style'\];", True),
        ('the request path loses the language prefix before it is compared', 'php',
         r"substr\(\$path, strlen\(\$home\)\)", True),
        ('a path under a link counts, a path equal to it is "page"', 'php',
         r"function sf_nav_path_is\(\$path, \$url\) \{", True),
        ('the mark goes on the link, once, and only on its first anchor', 'php',
         r"if \(false === strpos\(\$html, 'class=\"wp-block-navigation-item__content\"'\)\) \{", True),
        ('a submenu head inherits the mark from a child that matched', 'php',
         r"\$owns = \(false !== strpos\(\$tail, ' is-active'\)\);", True),
        ('and that child gives its own mark back up', 'php',
         r"' sf-nav__link is-active\" aria-current=\"page\"',", True),
        ('aria-current distinguishes the page from its section', 'php',
         r"\$is_page \? 'page' : 'true'", True),
        ('the variant class is applied as one string pass over the header', 'php',
         r"\(\?=\[ \"\]\)", True),
        # ...and the pass is anchored to the header GROUP by name. Without this
        # claim the element half of the anchor was unwitnessed: the source list
        # asserted only the trailing lookahead, so a mutant that renamed the
        # element inside the pattern still satisfied every clause. Measured --
        # that is exactly how this control failed before the claim was added.
        ('...anchored to the header group by name, not to any group', 'php',
         r'\(<\[a-z\]\[a-z0-9\]\* class="wp-block-group sf-header\)', True),
        ('the header anchor cannot match the cta row that starts the same way', 'php',
         r"false === strpos\(\$block_content, 'class=\"wp-block-group sf-header'\)", True),
        ('both filters are registered on render_block', 'php',
         r"add_filter\('render_block'", True),
        ('the admin offers one radio per mark, built from the same array', 'php',
         r"foreach \(sf_nav_active_styles\(\) as \$nav_slug => \$nav_label\)", True),
        ('and the switch sits under its own heading', 'php',
         r'<h2 class="title">Appearance</h2>', True),
    ],
}


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
        # Which renderer the claims are about comes from the declaration. It was
        # hard-coded to the gallery, which made the mechanism unusable by any
        # batch that adds a different renderer — and a check that can only be
        # written about one function is a check that gets skipped.
        fn = decl.get('body_of', 'sinofresh_formula_gallery')
        m = re.search(r'\nfunction %s\(.*?\n\}\n' % re.escape(fn), live['php'], re.S)
        body = m.group(0) if m else ''
        if not body:
            ok = False
            if verbose:
                print('  %-52s FAIL  %s() could not be located' % ('renderer body', fn))
        for label, needle, want in decl['source_body']:
            n = body.count(needle)
            good = (n > 0) if want else (n == 0)
            ok &= good
            rows.append({'label': label, 'target': 'renderer body', 'want': want,
                         'got': n, 'ok': good})
            if verbose:
                print('  %-52s %-9s %-4s %s'
                      % (label, fn[:9], 'x%d' % n, 'ok' if good else 'FAIL'))

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

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

    # A count that has a SECOND carrier on the page, read from the BASELINE, so
    # the claim is not "the candidate agrees with itself" one carrier over. H7k
    # is why this exists: its transform WALKS the card wall, so a wall that
    # renders twenty tiles while its own ItemList publishes `numberOfItems: 21`
    # is exactly what the transform mirrors — `mask(transform(baseline)) ==
    # mask(candidate)` is green, and the disagreement between the two carriers
    # of that one number is invisible. The counter takes (base, page) and must
    # read the baseline; reading the candidate would be the circularity this
    # clause is here to avoid.
    for label, pat, count_fn in decl.get('corroborated', []):
        bad = []
        for n in names:
            got = counts_of(read(os.path.join(cand, n + '.html')), pat)
            expect = count_fn(base, n)
            if got != expect:
                bad.append((n, got, expect))
        good = not bad
        ok &= good
        rows.append({'label': label, 'bad_pages': len(bad), 'first': bad[:4], 'ok': good})
        if verbose:
            print('  %-28s pages off their second carrier = %d %s  %s'
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
    elif isinstance(delta, dict):
        # H7k. The scalar form below keys the clause to `decl['applies']`, which
        # counts the batch's EDITS — 1500 for H7j, 163 for H7k. That makes the
        # scalar form able to say only "every declared edit moved a heading",
        # and H7k removes ONE heading from TWO of the 75 pages while making 163
        # edits elsewhere. The honest claim is therefore a page SET and a
        # per-page delta, and it is narrower than the scalar form rather than
        # looser: an h2 that moves on any other page fails, and one that moves
        # on a declared page by any other amount fails. Both halves are made to
        # fire by named controls (NC-page, --negctl): one injects an h2 on a
        # page outside the set, one strips a second h2 from a page inside it.
        want_pages = sorted(delta['pages'])
        step = delta['delta']
        good = ([n for n, _, _ in moved] == want_pages
                and all(hc - hb == step for _, hb, hc in moved))
        verdict = ('pages with a moved h2 = %d (declared %d: %s), each %+d'
                   % (len(moved), len(want_pages), ','.join(want_pages), step))
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
    """Clone a tree for a mutant to be applied to.

    `dirs_exist_ok=True` is load-bearing on this host, not a convenience. The
    sandbox's file broker creates the destination's directory skeleton itself
    before the real `copytree` walks the source, so the real one meets its own
    directories already built and raises a `shutil.Error` whose list contains
    DIRECTORIES ONLY — never files. Measured on the 745-file theme tree into a
    fresh `mkdtemp`: the failing names were exactly the theme's nine depth-1
    directories (`_backup`, `_backup_x`, `assets`, `docs`, `inc`, `parts`,
    `screenshots`, `templates`, `tools`) plus a varying handful of deeper
    `_backup/*` ones, and the count differed run to run (58, 60, 71) — which is
    how we know it is a race and not a rule. Tolerating the pre-existing
    directories is the right reading of it: the copy the broker made is the copy
    we want. Verified by sha256 manifest — `dirs_exist_ok=True` and `cp -a` both
    produced all 745 files with 0 missing, 0 extra and 0 differing bytes, three
    runs each, measured the instant the call returned.

    That last measurement is the reason for the count check below rather than a
    comment alone: if the broker's copy ever WERE still in flight when the
    original returned, every source claim downstream would silently read a
    half-cloned theme, and the controls that exist to fail loudly would instead
    pass quietly. A file count is 745 `stat`s — cheap next to that.
    """
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst, dirs_exist_ok=True)
    want = sum(len(f) for _, _, f in os.walk(src))
    got = sum(len(f) for _, _, f in os.walk(dst))
    if got != want:
        raise RuntimeError('_clone: %s got %d files, %s has %d — the copy is '
                           'not complete' % (dst, got, src, want))
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
        for entry in decl.get('nc_source', []):
            label, rel, needle, replacement = entry[:4]
            # The 5th element, when given, NAMES the source assertion the
            # mutation is supposed to break. "It fired" is not "it fired for the
            # stated reason" — this gate's own history has a control that went
            # green for a check nobody was aiming at.
            owner = entry[4] if len(entry) > 4 else None
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
            if not r['ok']:
                if owner is None:
                    report(label, True)
                else:
                    failed = [row['label'] for row in r['rows'] if not row['ok']]
                    report(label, owner in failed,
                           'wanted %r among %r' % (owner, failed))
            else:
                report(label, False, 'the sabotage survived')

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


# ---------------------------------------------------------------------- H7k
#
# 待办14 (the card still becomes a link), 待办17 (the card badge), 待办18 (the
# compliance band becomes a strip), 待办19 (the tour checklist becomes two
# columns), 待办22 (the Key Facts table spans the content box).
#
# ONE of the five lives entirely in the stylesheet — 待办22 never touches a page
# — and one of them renders NOTHING on this data set (待办17: no record carries a
# badge value yet). The remaining three are per-record or per-page markup, and
# none of them is a whole-region splice of fixed text, so this batch runs on the
# `insert` branch: the expected page is built from the baseline by
# RE-IMPLEMENTING the three declared rules.
#
# That is only honest if every byte the transform adds is DERIVED from the page
# it is added to, which is how H7g and H7i were built too. Here:
#
#   * the image link's href is the record's own URL and its label interpolates
#     the record's own title — both read off the card's title anchor, which is
#     the same `$url` and the same `$name` the renderer used to build the link,
#     because the renderer computes each once and uses it for the still, the
#     title and the "View formula" button;
#   * each chip's drawing is the seal's own `<g>` body, copied verbatim, and its
#     text is the seal's own `<h3>` — the batch replaced six card frames with six
#     chips and was never licensed to redraw or relabel anything;
#   * the two tour columns are built from the page's own five paragraphs.
#
# A table of 163 literal strings would have been shorter to write and would have
# drifted from the renderer the first time a formula was added — which is the
# same reason H7g rejected the table.

H7K_FIG = '<figure class="sf-fcard__media">'
H7K_FIG_TAIL = '</figure>'

# The card, from the media block through the title anchor. Every step is a
# bounded class rather than `.*?`, so the match cannot walk out of one card and
# into the next if a card ever loses a part: an unmatched card is left alone and
# then caught by the count guard below, instead of being silently re-cut.
H7K_CARD = re.compile(
    r'<figure class="sf-fcard__media">(?P<img><img [^>]*/>)' + re.escape(H7K_FIG_TAIL) +
    r'<div class="sf-fcard__body"><span class="sf-fcard__use">(?P<use>[^<]*)</span>'
    r'<h3 class="sf-fcard__name"><a href="(?P<url>[^"]+)">(?P<name>[^<]*)</a></h3>')

# The label is sprintf('View the %s formula', $name) through esc_attr(); the
# name is esc_html() of the SAME post title two elements later. In WordPress
# both escapers are one function (_wp_specialchars with ENT_QUOTES) and escape
# the same five characters to the same entities, so the title anchor's own text
# can be interpolated verbatim — which is what makes this a rule and not a
# lookup. If a future title ever makes the two disagree, the derivation guard
# does not fire (it cannot see the difference) and the MAIN PROOF does: the
# label would then differ from the renderer's bytes.
H7K_LINK = '<a class="sf-fcard__imagelink" href="%s" aria-label="View the %s formula">%s</a>'
H7K_LABEL_ALT = '<a class="sf-fcard__imagelink" href="%s" aria-label="%s">%s</a>'

# The two elements the band carried and no longer does. Named once, because
# the coverage claim and the transform must agree on the bytes to the last
# character — a needle that spelled them out again would be a second copy free
# to drift. Both carry the WHOLE tag: /quality/ writes the same words with the
# same two classes in the other order, so a needle stopping at the words would
# find a survivor.
H7K_EYEBROW_BAND = ('<p class="has-text-align-center sf-eyebrow wp-block-paragraph">'
                    'Compliance</p>')
H7K_H2_BAND = ('<h2 class="wp-block-heading has-text-align-center">'
               'Certifications &amp; Registrations</h2>')

# 待办18, the old head: the 48px padding, the eyebrow, the h2, the lede
# paragraph and the card grid's opening tag, all contiguous on both home pages.
# Anchored on the whole run rather than on the eyebrow comment, because the home
# page writes an `align:center` eyebrow comment TEN times — anchoring there
# despatched 310 lines of the page the first time this edit was scripted, which
# is why the uniqueness guard in _h7k_band() is not decoration.
H7K_BAND_OLD = (
    'style="padding-top:48px;padding-bottom:48px">\n\n' + H7K_EYEBROW_BAND + '\n\n\n' +
    H7K_H2_BAND + '\n\n\n'
    '<p class="has-text-align-center has-text-secondary-color has-text-color wp-block-paragraph">'
    'Registered and audited production — full documentation available on request.</p>\n\n\n'
    '<div class="sf-certgrid" role="list">')
H7K_BAND_NEW = (
    'style="padding-top:32px;padding-bottom:32px">\n\n'
    '<div class="sf-certstrip">\n'
    '<p class="sf-certstrip__lede">Certified to the standards global pet brands trust</p>\n'
    '<ul class="sf-certstrip__row" role="list">')

# One seal card. `pre` and `post` are captured because the "compact" mutant
# keeps the 88px frame, its role="img" and its decorative label — the wrong
# answer that a strip with the old seals would produce. The case of the viewBox
# attribute is captured rather than assumed: the zh twin renders through
# render_block() and writes `viewbox`, the raw template writes `viewBox`, and
# the chip must keep whichever one ITS page used.
H7K_SEAL = re.compile(
    r'\t\t\t\t<article class="sf-certcard">\n'
    r'\t\t\t<svg (?P<pre>[^>]*?)(?P<case>viewBox|viewbox)="0 0 96 96"(?P<post>[^>]*)>'
    r'(?P<body><g [^>]*>.*?</g>)'
    r'(?P<texts>(?:<text [^>]*>[^<]*</text>)*)</svg>\n'
    r'\t\t\t\t\t<h3 class="sf-certcard__name">(?P<name>[^<]*)</h3>\n'
    r'\t\t\t\t\t<p class="sf-certcard__issuer">[^<]*</p>\n'
    r'\t\t\t\t</article>')

H7K_CHIP = ('<li class="sf-certstrip__badge"><svg class="sf-certstrip__icon" '
            'width="32" height="32" %s="0 0 96 96" aria-hidden="true" focusable="false">'
            '%s</svg><span class="sf-certstrip__name">%s</span></li>')
H7K_CHIP_BIG = ('<li class="sf-certstrip__badge"><svg %s%s="0 0 96 96"%s>%s%s</svg>'
                '<span class="sf-certstrip__name">%s</span></li>')
H7K_BAND_TAIL = ('\n</ul>\n<p class="sf-certstrip__more"><a href="%s">'
                 'View all certifications &rarr;</a></p>\n</div>')

# --- 待办19: two columns ---------------------------------------------------
H7K_PREP_H2 = '<h2 class="has-text-align-center wp-block-heading">What to Prepare</h2>'
H7K_PREP_COLS = ('<div class="wp-block-columns sf-prepare is-layout-flex '
                 'wp-container-core-columns-is-layout-7387b849 '
                 'wp-block-columns-is-layout-flex">\n\n')
H7K_PREP_COL = '<div class="wp-block-column is-layout-flow wp-block-column-is-layout-flow">\n\n'
H7K_PREP_P = re.compile(r'<p class="wp-block-paragraph" style="font-size:16px">.*?</p>')


def _h7k_figure(img, url, name, outside=False, alt_label=False):
    """The media block after 待办14: the still inside a link, inside the figure.

    The link is INSIDE the figure and the body follows it, which is the
    renderer's own order — the badge is appended to the figure as a SIBLING of
    the still (K7), so a link around the FIGURE rather than around the image
    would swallow the badge's label into the link's accessible name. `outside`
    is that wrong answer; `alt_label` is the other one, a link named after what
    the still depicts instead of where it goes."""
    if alt_label:
        alt = re.search(r'alt="([^"]*)"', img)
        link = H7K_LABEL_ALT % (url, alt.group(1) if alt else '', img)
    else:
        link = H7K_LINK % (url, name, img)
    if outside:
        return H7K_LINK % (url, name, H7K_FIG + img + H7K_FIG_TAIL)
    return H7K_FIG + link + H7K_FIG_TAIL


def _h7k_body(m):
    return ('<div class="sf-fcard__body"><span class="sf-fcard__use">' + m.group('use') +
            '</span><h3 class="sf-fcard__name"><a href="' + m.group('url') + '">' +
            m.group('name') + '</a></h3>')


def _h7k_cards(text, outside=False, alt_label=False):
    n = 0

    def one(m):
        nonlocal n
        n += 1
        return (_h7k_figure(m.group('img'), m.group('url'), m.group('name'),
                            outside=outside, alt_label=alt_label) + _h7k_body(m))

    out = H7K_CARD.sub(one, text)
    figs = text.count(H7K_FIG)
    if n != figs:
        # A card the rule cannot read is NOT left half-linked: the batch claims
        # "every still on this page becomes a link", so a card that does not
        # match means the rule has stopped describing the renderer and the run
        # must stop rather than report a partial pass.
        raise AssertionError('H7k: %d of the %d stills did not carry the card shape'
                             % (figs - n, figs))
    return out, n


def _h7k_band(text, big_seals=False):
    """待办18 — six cards become one strip of six chips, and two elements go.

    `big_seals` is the wrong answer this batch is most likely to attract: the
    band is rebuilt, the chips are built, but the drawing is carried over whole
    — the 88px frame, its role="img", its decorative aria-label and the two
    <text> elements that letter it. It is the 'compact' band that is not
    compact, and it is why the seal regex captures the parts the good path
    throws away."""
    if H7K_BAND_OLD not in text:
        return text, 0
    if text.count(H7K_BAND_OLD) != 1:
        raise AssertionError('H7k: the compliance band run is not unique')
    text = text.replace(H7K_BAND_OLD, H7K_BAND_NEW)
    k = text.index(H7K_BAND_NEW) + len(H7K_BAND_NEW)
    j = text.index('\n</div>', k)
    old = text[k:j + len('\n</div>')]
    run = old[:-len('\n</div>')]
    if not old.endswith('\n</div>'):
        raise AssertionError('H7k: the chip run does not end where the grid does')
    ms = list(H7K_SEAL.finditer(run))
    if not ms or '\n'.join(m.group(0) for m in ms) != run.lstrip('\n'):
        raise AssertionError('H7k: the seal run did not parse whole')
    if big_seals:
        chips = '\n'.join('\t\t\t' + H7K_CHIP_BIG % (m.group('pre'), m.group('case'),
                                                     m.group('post'), m.group('body'),
                                                     m.group('texts'), m.group('name'))
                          for m in ms)
    else:
        chips = '\n'.join('\t\t\t' + H7K_CHIP % (m.group('case'), m.group('body'),
                                                 m.group('name'))
                          for m in ms)
    # The link's language prefix is the one TranslatePress would write, and it
    # is read off the page rather than assumed: the "View Full Certifications"
    # button eight lines below already carries it, on both home pages.
    href = ('/zh/quality/#certifications' if '<html lang="zh-CN"' in text
            else '/quality/#certifications')
    # Cut at `k + len(old)` and NOT at `j + len(old)`: `old` starts at `k`, not
    # at `j`, and the first version of this line resumed `len(run)` bytes too
    # far — it ate the opening tag of the next section and left its own tail
    # welded to the previous `</div>`, one mangled line and no other symptom.
    return text[:k] + '\n' + chips + H7K_BAND_TAIL % href + text[k + len(old):], 1


def _h7k_prepare(text, split_at=3):
    """待办19 — the five checklist paragraphs become two columns of 3 and 2.

    The paragraphs themselves are reused byte-for-byte; only the wrappers are
    new. Below 782px core's own `.wp-block-columns` media query stacks them, so
    this costs the theme no CSS at all — which is why the batch adds none.

    The blank runs are the block editor's, and they are NOT symmetric: the run
    before the first item is three newlines, the runs between items are three,
    a column closes on two, and the two columns close on two each. Measured off
    the rendered page rather than assumed — the first version of this function
    assumed a two-newline lead and the derivation guard stopped the run, which
    is what the guard is for."""
    if H7K_PREP_H2 not in text:
        return text, 0
    if text.count(H7K_PREP_H2) != 1:
        raise AssertionError('H7k: the What to Prepare heading is not unique')
    i = text.index(H7K_PREP_H2) + len(H7K_PREP_H2)
    j = text.index('\n\n</section>', i)
    block = text[i:j]
    sep = '\n\n\n'
    parts = block.split(sep)
    paras = H7K_PREP_P.findall(block)
    if len(parts) != 6 or len(paras) != 5 or parts[0] != '':
        raise AssertionError('H7k: the checklist is %d runs / %d items'
                             % (len(parts), len(paras)))
    if parts[1:] != paras:
        raise AssertionError('H7k: the checklist is not five plain paragraphs')
    left, right = split_at, 5 - split_at
    new = (sep + H7K_PREP_COLS + H7K_PREP_COL + sep.join(paras[:left]) +
           '\n\n</div>\n\n\n' + H7K_PREP_COL + sep.join(paras[left:left + right]) +
           '\n\n</div>\n\n</div>')
    return text[:i] + new + text[j:], 1


def _h7k_transform(text, cards=True, band=True, prepare=True, outside=False,
                   alt_label=False, split_at=3, big_seals=False):
    n = 0
    if cards:
        text, k = _h7k_cards(text, outside=outside, alt_label=alt_label)
        n += k
    if band:
        text, k = _h7k_band(text, big_seals=big_seals)
        n += k
    if prepare:
        text, k = _h7k_prepare(text, split_at=split_at)
        n += k
    return text, n


def _h7k_partial(**kw):
    """A mutant that answers one of the five declared questions differently."""
    def f(text):
        return _h7k_transform(text, **kw)
    return f


def _h7k_grid_page(name):
    """The pages `<code>sf_formula_grid</code>` is placed on, by NAME: the eight
    dosage pages, the archive and its twenty-one detail pages, and their zh twins
    — 60 of the 75.

    Transcribed from where the shortcode sits in the templates, which is the way
    H7j transcribed the menu, and not read off the page: an `order` claim whose
    scope came from the candidate would be asserting the candidate against
    itself. The two counts that pin 60 are in `unmoved`."""
    base = name[4:] if name.startswith('zh__') else name
    return (base.startswith('products__') or base == 'formulas'
            or base.startswith('formulas__'))


def _h7k_items(base, page):
    """How many cards the page's OWN ItemList says it has — the second carrier.

    Read from the BASELINE capture on purpose: the clause this feeds exists to
    catch the card wall and its ItemList drifting apart, and reading the number
    off the candidate would let both move together and still agree."""
    t = read(os.path.join(base, page + '.html'))
    return sum(int(x) for x in re.findall(r'"numberOfItems":\s*(\d+)', t))


# The same two facts as ONE regex: the link points at the record its own title
# link points at (`\1`), and the still sits inside that link, inside the figure,
# with the body following. A page whose count of these equals its ItemList total
# has both the shape and the target right, which is the claim `scoped` could not
# make — `scoped` demands zero OFF its scope, and 60 of these 75 pages carry one.
#
# The `aria-label` between the href and the `>` is why the first version of this
# pattern matched nothing at all: the link's href is not its last attribute.
H7K_IMAGELINK_EXACT = (
    r'<a class="sf-fcard__imagelink" href="([^"]+)" aria-label="[^"]*"><img [^>]*/></a>' +
    re.escape(H7K_FIG_TAIL) +
    r'<div class="sf-fcard__body"><span class="sf-fcard__use">[^<]*</span>'
    r'<h3 class="sf-fcard__name"><a href="\1">')

H7K_HOME = ('root', 'zh')


BATCHES['h7k'] = {
    'name': "H7k — the still links, the badge is addable, the cert band is a strip, "
            "the checklist is two columns, the Key Facts table fills the column",
    'mode': 'insert',
    'tokens': [
        ('?ver=2.10.71', '?ver=2.10.72'),                      # style.css
    ],
    'transform': _h7k_transform,
    'applies': 163,        # 160 card stills + 2 compliance bands + 1 checklist
    'coverage': [
        ('?ver=2.10.71', 0),
        ('sf-certgrid', 0),
        ('sf-certcard', 0),
        # The band's OWN two strings, which is why they carry the class order
        # the band wrote. /quality/ carries a heading with the same words and
        # the same two classes in the other order (`has-text-align-center`
        # first), so a needle that stopped at the words would claim 1 remains
        # where 0 must — measured, and the reason this is the whole tag.
        (H7K_H2_BAND, 0),
        (H7K_EYEBROW_BAND, 0),
        ('Registered and audited production', 0),        # The two <text> elements of every seal: 6 seals x 2 pages. The seal's
        # drawing stays (it is the chip's icon now); its lettering goes, because
        # the chip's own <span> carries the name.
        ('font-size="12.5"', 0),
        ('letter-spacing="1.6"', 0),
    ],
    'insertions': [
        ('?ver=2.10.72', 75),
        ('sf-fcard__imagelink', 160),
        ('sf-certstrip__lede', 2),
        ('sf-certstrip__row', 2),
        ('sf-certstrip__badge', 12),
        ('sf-certstrip__icon', 12),
        ('sf-certstrip__name', 12),
        ('sf-certstrip__more', 2),
        ('Certified to the standards global pet brands trust', 2),
        ('View all certifications', 2),
        ('class="wp-block-columns sf-prepare', 1),
        # 待办17 ships in this batch and renders NOWHERE, because no record
        # carries the value — the user fills it in wp-admin, and the batch is
        # forbidden from touching post meta. Zero is the claim, not an omission:
        # a badge here would mean either the meta had been populated behind our
        # back or the accessor had stopped treating "unset" as "no badge". The
        # three colours are a SOURCE claim; that each one actually paints is the
        # render harness's, which builds a record with every value in turn.
        ('sf-fcard__badge', 0),
    ],
    'counts': [
        # 待办18 — the band, four strings that only it carried, each with BOTH
        # numbers: a total alone would let the band keep its cards while some
        # other page grew six.
        ('the six cards leave the two home pages', 'sf-certcard', 48, 0),
        ('the page that carried the grid no longer does', 'sf-certgrid', 2, 0),
        ('the compliance heading leaves the two home pages', H7K_H2_BAND, 2, 0),
        ('and the eyebrow above it goes with it', H7K_EYEBROW_BAND, 2, 0),
        # The band was 1 of the 22 sections asking for 48px. The other 21 are
        # the ones that must NOT have moved — this pair is what says the edit
        # was aimed at one section rather than at every 48px in the site.
        ('the other twenty-one sections keep their 48px padding',
         'padding-top:48px;padding-bottom:48px', 22, 20),
        ('the seals stop lettering themselves', 'font-size="12.5"', 12, 0),
        # The chip is the seal's drawing in a 32px frame, and its attribute case
        # is the PAGE's: the template writes viewBox, the zh twin re-serialises
        # through render_block() and writes viewbox. Six of each before and six
        # of each after is what "the body survived, the frame was rebuilt" says
        # in bytes — and it fails if the icon is redrawn rather than copied.
        ('the drawing survives with its own case, six times over',
         'viewBox="0 0 96 96"', 6, 6),
        ('...and the lowercase form the zh renderer emits, six times',
         'viewbox="0 0 96 96"', 6, 6),
        # 待办14 — the still gains a link; the figure and the body around it do
        # not move. The card is inside a <figure>, which is why wrapping the
        # image cannot reorder anything.
        ('every card still keeps its figure', H7K_FIG, 160, 160),
        ('...and every card still keeps its body',
         '<div class="sf-fcard__body">', 160, 160),
        # The band kept its outline button and the testing bar under it.
        ('the band keeps the button it already had', 'View Full Certifications', 2, 2),
        ('and the testing bar under it is untouched', 'sf-certbar__item', 10, 10),
        # 待办19 — the five items are the page's own paragraphs, reused whole.
        ('the checklist still has the five items it had',
         '<p class="wp-block-paragraph" style="font-size:16px">', 5, 5),
    ],
    'unmoved': [
        ('the cookie banner', r'class="sf-cookie-banner"', 75),
        ('the float stack', r'class="sf-float-stack"', 75),
        ('the certificate dialog', r'sf-certmodal', 1),
        ('the primary cta', r'sf-quote-cta', None),
        ('the gallery tabs', r'sf-gallery__tabs', 42),
        ('the configurator', r'sf-fdetail-config__group', 42),
        ('the side column', r'sf-fdetail2__side', 42),
        ('the card walls', r'<article class="sf-fcard"', 60),
        ('the stills', H7K_FIG, 60),
        # 待办17's zero, carried a second time as a PAGE count rather than an
        # occurrence count. The two are not redundant: `insertions` counts the
        # string across the site (and so cannot tell one page carrying three from
        # three pages carrying one), while this counts the pages that carry it —
        # and this is the only form the NC-page control can break, because that
        # control runs `invariants` and `insertions` lives in `coverage`. Without
        # it the control aimed at "a badge appears unasked" reported FAIL: it
        # injected the badge correctly and no clause it could reach counted it.
        ('no page carries a badge until a record asks for one',
         r'sf-fcard__badge', 0),
        # 待办22 is stylesheet-only, so the table's own markup must not move: a
        # batch that reached its width by editing the table would be a different
        # batch, and this is the line that says so.
        ('the key facts table', r'<table class="sf-keyfacts"', 1),
        ('the strip is not the only band on the two home pages',
         r'class="sf-certbar"', 2),
    ],
    'per_page': [
        ('h1', r'<h1[ >]', 1),
        ('the new style token', r'style\.css\?ver=2\.10\.72', 1),
    ],
    'corroborated': [
        # The card wall and its own ItemList are two carriers of one number, and
        # the main proof cannot tell them apart: the transform walks the wall, so
        # a wall showing twenty tiles while the JSON-LD above it says 21 is
        # mirrored exactly and goes green. This reads the number from the
        # baseline's ItemList and requires the candidate's links to match it —
        # and because the pattern closes with a backreference, it also requires
        # each link to point at the record its own title link points at.
        ('the cards agree with the number the page publishes',
         H7K_IMAGELINK_EXACT, _h7k_items),
    ],
    'order': [
        ('the strip is a lede, then a row, then the link',
         'sf-certstrip__lede', 'sf-certstrip__more', lambda n: n in H7K_HOME),
        # The link is inside the figure, so the card's own title anchor comes
        # after it. A link placed around the figure would invert this.
        ('the still is linked ahead of the title it belongs to',
         '<a class="sf-fcard__imagelink"', '<h3 class="sf-fcard__name">', _h7k_grid_page),
        ('the tour columns open after the heading they belong to',
         H7K_PREP_H2, H7K_PREP_COLS, lambda n: n == 'factory-tour'),
    ],
    # Two pages lose one heading each, and 528 headings across the site become
    # 526. The scalar form of this clause keys itself to `applies` (163 edits),
    # so it can only say "every edit moved a heading" — see invariants().
    'h2_delta': {'delta': -1, 'pages': list(H7K_HOME)},
    'jsonld_delta': None,
    'sources': {
        'fp': 'templates/front-page.html',
        'fac': 'templates/page-factory-tour.html',
        'adm': 'inc/formula-admin.php',
    },
    'reinject': ('an old card grid put back fails coverage',
                 'root.html', '<div class="sf-certstrip">',
                 '<div class="sf-certgrid" role="list">'),
    'delete': ('one page loses an image link fails coverage',
               'formulas.html', '<a class="sf-fcard__imagelink"'),
    'nc13_mode': 'sighted',
    'nc13_label': ('NC13 the insert direction SEES a payload edit, and coverage confirms it'),
    'matrix': [
        ('the tokens are not folded', {'tokens': []}, None),
        ('the still is left unlinked',
         {'transform': _h7k_partial(cards=False)}, None),
        ('the link goes around the figure instead of around the still',
         {'transform': _h7k_partial(outside=True)}, None),
        ('the link describes the photograph instead of where it goes',
         {'transform': _h7k_partial(alt_label=True)}, None),
        ('the band keeps its six cards',
         {'transform': _h7k_partial(band=False)}, None),
        ('the band is rebuilt but the seals come along unshrunk',
         {'transform': _h7k_partial(big_seals=True)}, None),
        ('the checklist stays one column',
         {'transform': _h7k_partial(prepare=False)}, None),
        ('the checklist is cut four-and-one',
         {'transform': _h7k_partial(split_at=4)}, None),
        ('the run count is declared one short', {'applies': 162}, None),
        ('nothing is applied at all',
         {'transform': (lambda t: (t, 0)), 'applies': 0}, None),
    ],
    'nc_source': [
        ('NC-src the source pass fails when the stylesheet keeps its old version',
         'style.css', 'Version: 2.10.72', 'Version: 2.10.71'),
        # 待办14
        ('NC-src the source pass fails when the renderer stops linking the still',
         'functions.php', "if ($links) {\n\t\t\t\t$still = sprintf(",
         "if (false) {\n\t\t\t\t$still = sprintf("),
        ('NC-src the source pass fails when the label stops saying where it goes',
         'functions.php', "esc_attr(sprintf('View the %s formula', $name))",
         "esc_attr(sprintf('View the %s picture', $name))"),
        ('NC-src the source pass fails when the badge moves inside the link',
         'functions.php', "'<figure class=\"sf-fcard__media\">%s%s</figure>',",
         "'<figure class=\"sf-fcard__media\">%s</figure>%s',"),
        # 待办17
        ('NC-src the source pass fails when a badge label leaves the vocabulary',
         'functions.php', "\t\t'Hot'         => 'hot',\n", ''),
        ('NC-src the source pass fails when the whitelist stops dropping unknowns',
         'functions.php', "if ($raw === '' || !isset($map[$raw])) {",
         "if ($raw === '') {"),
        ('NC-src the source pass fails when a record with no still loses its badge',
         'functions.php', 'sinofresh_formula_badge_markup($badge, true)',
         "''"),
        ('NC-src the source pass fails when the badge stops being a select',
         'inc/formula-admin.php', "'type' => 'select', 'req' => 1,", "'type' => 'text', 'req' => 1,"),
        ('NC-src the source pass fails when the select loses its empty option',
         'inc/formula-admin.php',
         "esc_html(isset($spec['empty_label']) ? $spec['empty_label'] : 'None')",
         "esc_html('None')"),
        ('NC-src the source pass fails when the select stops being saved at all',
         'inc/formula-admin.php', "case 'radio':\n\t\t\tcase 'select':", "case 'radio':"),
        ('NC-src the source pass fails when the field leaves the media box',
         'inc/formula-admin.php', "'key' => 'sf_formula_card_badge', 'label' => 'Card badge', 'group' => 'media'",
         "'key' => 'sf_formula_card_badge', 'label' => 'Card badge', 'group' => 'zzz'"),
        # 待办18
        ('NC-src the source pass fails when the chips stop being list items',
         'templates/front-page.html', '<ul class="sf-certstrip__row" role="list">',
         '<div class="sf-certstrip__row" role="list">'),
        ('NC-src the source pass fails when the seals keep their role and label',
         'templates/front-page.html',
         '<svg class="sf-certstrip__icon" width="32" height="32" viewBox="0 0 96 96" '
         'aria-hidden="true" focusable="false">',
         '<svg class="sf-certcard__seal" width="88" height="88" viewBox="0 0 96 96" '
         'role="img" aria-label="FDA certification seal" focusable="false">'),
        ('NC-src the source pass fails when the band goes back to 48px',
         'templates/front-page.html',
         '"padding":{"top":"32px","bottom":"32px"}}},"className":"sf-section sf-section--large"}',
         '"padding":{"top":"48px","bottom":"48px"}}},"className":"sf-section sf-section--large"}'),
        ('NC-src the source pass fails when a dead card rule comes back',
         'style.css', '.sf-certstrip__lede {', '.sf-certgrid {\n\tcolor: red;\n}\n.sf-certstrip__lede {'),
        ('NC-src the source pass fails when the phone breakpoint stops halving',
         'style.css', '.sf-certstrip__row {\n\t\tgrid-template-columns: repeat(2, minmax(0, 1fr));',
         '.sf-zz-certstrip__row {\n\t\tgrid-template-columns: repeat(2, minmax(0, 1fr));'),
        ('NC-src the source pass fails when the strip goes to one column at 420px',
         'style.css', '@media (max-width: 420px) {\n\t.sf-certstrip__row {\n\t\tgap: 8px 12px;\n\t}\n}',
         '@media (max-width: 420px) {\n\t.sf-certstrip__row {\n\t\tgrid-template-columns: 1fr;\n\t}\n}'),
        # 待办17 css
        ('NC-src the source pass fails when the badge stops being an overlay',
         'style.css', '.sf-fcard__badge {\n\tposition: absolute;\n\ttop: 12px;\n\tright: 12px;',
         '.sf-fcard__badge {\n\tposition: static;\n\ttop: 12px;\n\tright: 12px;'),
        ('NC-src the source pass fails when the media block stops being its context',
         'style.css',
         # A literal cannot express this mutant: `position: relative;` is the LAST
         # declaration of seven in its block, after a nested comment, so
         # `.sf-fcard__media {\n\tposition: relative;` is not in style.css at all.
         # The first version of this control said exactly that — "the mutant
         # needle is not in style.css" — which is a control that cannot fire, not
         # a claim that cannot fail, and the difference matters: the claim it
         # guards (`\.sf-fcard__media \{[^}]*position: relative;`) matches the
         # block's real 539 bytes, so the product was right and the control was
         # wrong. The mutant reaches into the block instead of guessing its shape.
         (lambda s: re.sub(r'(\.sf-fcard__media \{[^}]*?)position: relative;',
                           r'\1position: static;', s, count=1)), None),
        ('NC-src the source pass fails when a badge colour leaves the palette',
         'style.css', '.sf-fcard__badge--hot {\n\tbackground: #B3261E;\n}',
         '.sf-zz-badge--hot {\n\tbackground: #B3261E;\n}'),
        ('NC-src the source pass fails when the no-still placement loses its rule',
         'style.css', '.sf-fcard__badge--inline {\n\tposition: static;',
         '.sf-zz-badge--inline {\n\tposition: static;'),
        ('NC-src the source pass fails when the still stops being a block',
         'style.css', '.sf-fcard__imagelink {\n\tdisplay: block;\n}',
         '.sf-fcard__imagelink {\n\tdisplay: inline;\n}'),
        # 待办19
        ('NC-src the source pass fails when the checklist stops being columns',
         'templates/page-factory-tour.html',
         '<!-- wp:columns {"className":"sf-prepare"} -->', '<!-- wp:group -->'),
        # 待办22
        ('NC-src the source pass fails when the table caps itself again',
         'style.css',
         'max-width: var(--wp--style--global--content-size);\n\tmargin: 24px 0 0;',
         'max-width: 720px;\n\tmargin: 24px auto 0;'),
    ],
    'nc_page': [
        # The one claim on this batch the MAIN PROOF cannot make, because the
        # transform walks the card wall: a link that points somewhere else is
        # still a link in the right place, so the proof is green while the card's
        # picture and its title lead to different formulas. The claim that
        # catches it is the `corroborated` one, and this is its control.
        ('NC-page the corroborated count fails when a link points at another record',
         'formulas.html',
         lambda s: s.replace(
             '<a class="sf-fcard__imagelink" href="https://dev.zxpet.com/formulas/ear-care-drops/"',
             '<a class="sf-fcard__imagelink" '
             'href="https://dev.zxpet.com/formulas/hairball-remedy-paste/"', 1)),
        ('NC-page the corroborated count fails when a page loses one of its links',
         'formulas.html',
         lambda s: s.replace('<a class="sf-fcard__imagelink"', '', 1)),
        ('NC-page the card count fails when a badge appears unasked',
         'products__drops.html',
         lambda s: s.replace('<figure class="sf-fcard__media">',
                             '<figure class="sf-fcard__media">'
                             '<span class="sf-fcard__badge sf-fcard__badge--hot">Hot</span>', 1)),
        ('NC-page the h2 clause fails when a heading moves on a page outside the set',
         'about.html',
         lambda s: s.replace('</body>', '<h2>extra</h2></body>', 1)),
        ('NC-page the h2 clause fails when a declared page moves by a second heading',
         'root.html',
         lambda s: s.replace('<h2 class="wp-block-heading', '<p class="wp-block-heading', 1)),
    ],
    # NC13's mutant has to be a string COVERAGE itself counts. The first version
    # appended an `X` (`...certificationsX`), which left the coverage claim's own
    # substring `View all certifications` intact — so the main proof saw the edit
    # (this mode is `sighted`) while coverage stayed green, and the control
    # reported `main_red=True coverage_red=False`: the half of its own label it
    # could not do. Changing the WORD keeps the main proof's verdict and moves the
    # declared insertion count from 2 to 1, which is the half the label promises.
    'nc_blind': ('root.html',
                 'View all certifications &rarr;',
                 'View every certification &rarr;'),
    'source': [
        ('style.css declares 2.10.72', 'css', r'(?m)^Version: 2\.10\.72$', True),
        ('no 2.10.71 header survives', 'css', r'(?m)^Version: 2\.10\.71$', False),
        ('functions.php enqueues 2.10.72 for style.css', 'php',
         r"wp_enqueue_style\('sinofresh-style'[^;]*'2\.10\.72'", True),
        # --- 待办14 -------------------------------------------------------
        ('the renderer wraps the still in a link carrying the record\'s url', 'php',
         r"'<a class=\"sf-fcard__imagelink\" href=\"%s\" aria-label=\"%s\">%s</a>',", True),
        ('...and the label says where the link goes, not what the still shows', 'php',
         r"esc_attr\(sprintf\('View the %s formula', \$name\)\)", True),
        ('...and only when the card is a route at all', 'php',
         r"if \(\$links\) \{\n\t\t\t\t\$still = sprintf\(", True),
        ('the badge stays a SIBLING of the still, never inside the link', 'php',
         r"'<figure class=\"sf-fcard__media\">%s%s</figure>',", True),
        # --- 待办17 -------------------------------------------------------
        ('the three labels and their class suffixes live in one map', 'php',
         r"'Best Seller' => 'best-seller',[\s\S]{0,90}'Hot'         => 'hot',"
         r"[\s\S]{0,90}'New'         => 'new',", True),
        ('an unset or unknown value resolves to NO badge, not a dead class', 'php',
         r"if \(\$raw === '' \|\| !isset\(\$map\[\$raw\]\)\) \{", True),
        ('a record with no still is not a record without a badge', 'php',
         r"sinofresh_formula_badge_markup\(\$badge, true\)", True),
        ('the badge carries its label as text, not as a class name', 'php',
         r"'<span class=\"sf-fcard__badge sf-fcard__badge--%s%s\">%s</span>',", True),
        ('the field is a real <select>, not a text box', 'adm',
         r"'type' => 'select', 'req' => 1,", True),
        ('...offered by the same map the renderer reads', 'adm',
         r"'pool' => array_keys\(sinofresh_formula_card_badges\(\)\)", True),
        ('...whose empty option is the word the field itself declares', 'adm',
         r"esc_html\(isset\(\$spec\['empty_label'\]\) \? \$spec\['empty_label'\] : 'None'\)",
         True),
        ('...rendered by a select case and not by the text branch', 'adm',
         r"case 'select':[\s\S]{0,400}sf-mb__select", True),
        ('...and saved through the same whitelist the select was built from', 'adm',
         r"case 'radio':\n\t\t\tcase 'select':", True),
        ('the field belongs to the media group and is optional', 'adm',
         r"'key' => 'sf_formula_card_badge', 'label' => 'Card badge', 'group' => 'media', "
         r"'type' => 'select', 'req' => 1,", True),
        # --- 待办18 -------------------------------------------------------
        ('the band is a lede, a row and a link', 'fp',
         r'<p class="sf-certstrip__lede">Certified to the standards global pet brands '
         r'trust</p>', True),
        ('the six chips are list items under one list', 'fp',
         r'<ul class="sf-certstrip__row" role="list">', True),
        ('the six names survive verbatim', 'fp',
         r'<span class="sf-certstrip__name">FDA Registered</span>', True),
        ('the seals lose their role and their label', 'fp',
         r'<svg class="sf-certstrip__icon" width="32" height="32" viewBox="0 0 96 96" '
         r'aria-hidden="true" focusable="false">', True),
        ('...and the two <text> elements that lettered them', 'fp', r'<text ', False),
        ('...and the six cards with them', 'fp', r'sf-certcard', False),
        ('...and the heading the band used to carry', 'fp',
         r'Certifications &amp; Registrations', False),
        ('the band asks for 32px, and one band only', 'fp',
         r'"padding":\{"top":"32px","bottom":"32px"\}\}\},'
         r'"className":"sf-section sf-section--large"\}', True),
        ('the dead card grid is out of the stylesheet', 'css', r'\.sf-certgrid\s*\{', False),
        ('...and so are the seals it drew', 'css', r'\.sf-certcard__seal', False),
        ('the strip draws a three-column row', 'css',
         r'\.sf-certstrip__row \{\n\tdisplay: grid;\n\tgrid-template-columns: '
         r'repeat\(3, minmax\(0, 1fr\)\);\n\tgap: 10px 20px;', True),
        ('a phone shows two columns of three', 'css',
         r'@media \(max-width: 768px\) \{[\s\S]{0,320}\.sf-certstrip__row \{\n'
         r'\t\tgrid-template-columns: repeat\(2, minmax\(0, 1fr\)\);\n\t\}\n'
         r'\t\.sf-certstrip__lede \{', True),
        # The 420px breakpoint narrows the gaps and deliberately does NOT stack:
        # the retired card grid went to one column there, which is exactly what a
        # six-chip strip must not do — six rows would out-tall the band it
        # replaced. The claim is the rule, and its absence is claimed above by
        # the source list rather than by a mutant.
        ('...and the phone breakpoint narrows the gaps instead of stacking', 'css',
         r'@media \(max-width: 420px\) \{\n\t\.sf-certstrip__row \{\n\t\tgap: 8px 12px;\n\t\}\n\}',
         True),
        ('the link is painted in the brand green', 'css',
         r'\.sf-certstrip__more a \{\n\tfont-size: 14px;\n\tfont-weight: 600;\n\tcolor: '
         r'var\(--wp--preset--color--brand-green\);', True),
        # --- 待办17 css ---------------------------------------------------
        ('the badge is an overlay pinned to the still', 'css',
         r'\.sf-fcard__badge \{\n\tposition: absolute;\n\ttop: 12px;\n\tright: 12px;\n\tz-index: 2;',
         True),
        ('the media block is its positioning context', 'css',
         r'\.sf-fcard__media \{[^}]*position: relative;', True),
        ('the gold badge', 'css',
         r'\.sf-fcard__badge--best-seller \{\n\tbackground: #8A6D1F;\n\}', True),
        ('the red badge', 'css',
         r'\.sf-fcard__badge--hot \{\n\tbackground: #B3261E;\n\}', True),
        ('the blue badge', 'css',
         r'\.sf-fcard__badge--new \{\n\tbackground: #1F5C99;\n\}', True),
        ('the no-still placement is static at the head of the body', 'css',
         r'\.sf-fcard__badge--inline \{\n\tposition: static;\n\talign-self: flex-start;', True),
        ('the still is a block so its link adds no line box', 'css',
         r'\.sf-fcard__imagelink \{\n\tdisplay: block;\n\}', True),
        ('and it shows a focus ring', 'css',
         r'\.sf-fcard__imagelink:focus-visible \{\n\toutline: 3px solid', True),
        # --- 待办19 -------------------------------------------------------
        ('the checklist is a columns block, classed for itself', 'fac',
         r'<!-- wp:columns \{"className":"sf-prepare"\} -->', True),
        # --- 待办22 -------------------------------------------------------
        # The claim is the CAP, not the removal of a cap. `max-width: none` was
        # the first answer and it was wrong in a way only geometry showed: the
        # section is an `is-layout-constrained` group, so its block children are
        # already capped at `--wp--style--global--content-size` and centred —
        # the heading measured 1200px inside a 1364px content box. `none` took
        # the table out of that rule and let it fill 1364px, putting its ends
        # 82px outside the heading's on each side, which is the opposite of what
        # the brief asked for. The claim now names the cap the heading is under.
        ('the key facts table takes the same cap as its heading', 'css',
         r'\.sf-keyfacts \{\n\twidth: 100%;[\s\S]{0,1200}?'
         r'max-width: var\(--wp--style--global--content-size\);\n\tmargin: 24px 0 0;',
         True),
        ('...and no 720px cap survives in its rule', 'css',
         r'\.sf-keyfacts \{[^}]*max-width: 720px', False),
        ('...and the table is never let out of that cap again', 'css',
         r'\.sf-keyfacts \{[^}]*max-width: none', False),
    ],
}

# ------------------------------------------------- 待办25/待办4/待办2/待办1 (H7l)
#
# The batch that closes the first tranche. TWO edits, and two claims that were
# already true when it opened and must still be true when it closes:
#
#   待办25  the price ladder moves from the foot of the parameter column to its
#           head — under the intro, above Flavor.
#   待办4   the certification band's six chips become six cards. CSS ONLY: not
#           one page carries this change in its bytes, which is why every
#           sf-certstrip count below is declared with the same number on both
#           sides rather than omitted.
#   待办2   the column's foot is still `Send Inquiry`, still carries
#           data-sf-inquiry-open, and still degrades to /contact/#quote.
#   待办1   the ladder still prints 10-99 / 100-999 / ≥1,000 — the text the user
#           reported as "Custom quantity". It was neither a data problem nor a
#           code problem: dev was serving the 2.10.69 renderer, which read the
#           LEGACY `qty` key, against meta that batch H7i had already rewritten
#           to {min,max,price}. Every row therefore fell through to the
#           'Custom quantity' default and printed the old "USD n / unit" note.
#           The pull to 2.10.72 made reader and data agree; these claims are what
#           stops a later edit from putting them back out of step.
#
# WHY THE TRANSFORM IS A MOVE AND NOT A REWRITE
#
# The group is not rebuilt, only relocated: the same bytes in a different order.
# The pure-move form is what lets the proof say exactly that, and it is also why
# the declaration can be so short — a transform that rendered the group would be
# free to agree with a broken renderer, the mistake H7c's docblock already names.
H7L_LIST = '<div class="sf-fdetail-config__list">'
H7L_PRICING = '<div class="sf-fdetail-config__group" data-sf-config-group="pricing">'
H7L_GROUPS = re.compile(
    r'<div class="sf-fdetail-config__group" data-sf-config-group="([a-z]+)">')
H7L_TAIL = '</div></div></div><p class="sf-fdetail-config__summary"'
H7L_GROUP_END = '</div></div>'
# The one record that has a ladder, in both languages. Every claim that is about
# the ladder rather than about the site is scoped to it, so a second record
# growing one is reported instead of absorbed.
H7L_RECORD = lambda n: 'joint-support-soft-chews' in n
H7L_HOME = H7K_HOME
H7L_CTA = ('sf-fdetail2__cta" href="/contact/#quote" '
           'data-sf-inquiry-open>Send Inquiry</a>')


def _h7l_move(text, place='head', drop=False, copy=False):
    """待办25's declared edit to one page: the ladder group leaves the end of the
    list and re-opens at its head.

    `place` and `drop`/`copy` are the sabotage knobs, kept here rather than in
    the mutants because a mutant that re-implements the batch is a second
    implementation of it — the thing this gate exists to not have.

      place='second'  the plausible wrong address: the ladder read as a quantity
                      row and filed behind Flavor, where the brief says it is not.
      place='tail'    the identity — the group put back where the batch found it.
      drop=True       a move implemented as a delete, which the main proof alone
                      would accept: the group is not where the transform says,
                      so it would report the page as wrong, but only coverage
                      says the group was LOST.
      copy=True       a move implemented as a copy, the other half of that pair.
    """
    i = text.find(H7L_LIST)
    if i < 0:
        return text, 0
    tail = text.find(H7L_TAIL, i)
    if tail < 0:
        return text, 0
    groups = [(m.start(), m.group(1)) for m in H7L_GROUPS.finditer(text[i:tail])]
    names = [g[1] for g in groups]
    if 'pricing' not in names:
        return text, 0
    if place == 'head' and names[0] == 'pricing' and not copy:
        return text, 0                      # already where the batch puts it
    s = i + [g for g in groups if g[1] == 'pricing'][0][0]
    e = text.find(H7L_GROUP_END, s)
    if e < 0:
        return text, 0
    e += len(H7L_GROUP_END)
    group = text[s:e]
    if copy:
        # The other half of the drop/move pair, and it has to be written before
        # the removal: a "move" implemented by writing a SECOND copy at the head
        # and leaving the first one where it was. Removing first and re-inserting
        # the same string is this batch, not a mutant of it — which is how this
        # control reported "the gate let this through" on its first run.
        j0 = i + len(H7L_LIST)
        return text[:j0] + group + text[j0:], 1
    rest = text[:s] + text[e:]
    if drop:
        return rest, 1
    j = rest.find(H7L_LIST) + len(H7L_LIST)
    if place == 'second':
        m = H7L_GROUPS.search(rest, j)
        if not m:
            return rest, 1
        e2 = rest.find(H7L_GROUP_END, m.start())
        if e2 < 0:
            return rest, 1
        e2 += len(H7L_GROUP_END)
        return rest[:e2] + group + rest[e2:], 1
    if place == 'tail':
        e3 = rest.find(H7L_TAIL)
        if e3 < 0:
            return rest, 1
        return rest[:e3] + group + rest[e3:], 1
    return rest[:j] + group + rest[j:], 1


def _h7l_transform(text):
    return _h7l_move(text)


def _h7l_partial(place='head', drop=False, copy=False, off=False):
    """Mutants that skip or misplace the one declared edit; each must break the
    proof."""
    def f(text):
        if off:
            return text, 0
        return _h7l_move(text, place=place, drop=drop, copy=copy)
    return f


BATCHES['h7l'] = {
    'name': "H7l — the ladder heads the parameter column, and the certification "
            "band's six chips become six cards",
    'mode': 'insert',
    'tokens': [
        ('?ver=2.10.72', '?ver=2.10.73'),                      # style.css
    ],
    'transform': _h7l_transform,
    'applies': 2,          # the one record that has a ladder, in both languages
    'coverage': [
        ('?ver=2.10.72', 0),
        # The group's OLD ADDRESS, expressed as the bytes that said it: the close
        # of the container group immediately followed by the ladder's open. A
        # declaration that only said "the ladder is now first" would pass on a
        # page that grew a second copy at the head and kept this one — which is
        # why the old adjacency is a claim and not an assumption.
        ('</div></div>' + H7L_PRICING, 0),
    ],
    'insertions': [
        ('?ver=2.10.73', 75),
        (H7L_LIST + H7L_PRICING, 2),
    ],
    'counts': [
        # Moved, not created and not lost: the same count on both sides, on the
        # same two pages.
        ('the ladder group moves without being copied or dropped',
         'data-sf-config-group="pricing"', 2, 2),
        ('the parameter column keeps all its groups', 'sf-fdetail-config__group', 110, 110),
        ('each detail page still opens exactly one list', 'sf-fdetail-config__list', 42, 42),
        # 待办1 — the ladder's three breaks. Counted rather than trusted, because
        # "Custom quantity" was precisely a case of these strings not being there;
        # zero is a claim here, not an omission.
        ('no row falls back to the placeholder', 'Custom quantity', 0, 0),
        ('...because all three breaks are printed', '>10-99<', 2, 2),
        ('...the middle one', '>100-999<', 2, 2),
        ('...and the open-ended top one', '>≥1,000<', 2, 2),
        # 待办4 is CSS only: every band count below is identical on both sides,
        # which is the claim that the DOM did not move with the paint.
        ('the card band keeps its six chips', 'sf-certstrip__badge', 12, 12),
        ('...their icons', 'sf-certstrip__icon', 12, 12),
        ('...their names', 'sf-certstrip__name', 12, 12),
        ('...and it is still one row under one lede', 'sf-certstrip__row', 2, 2),
        # 待办2 — the column's foot. Unchanged by this batch, and from here on
        # not allowed to drift.
        ('the column still closes on its own inquiry button', H7L_CTA, 21, 21),
    ],
    'unmoved': [
        ('the cookie banner', r'class="sf-cookie-banner"', 75),
        ('the float stack', r'class="sf-float-stack"', 75),
        ('the certificate dialog', r'sf-certmodal', 1),
        ('the navigation', r'wp-block-navigation', 75),
        ('the parameter column', r'sf-fdetail-config__group', 42),
        # Every group the ladder was filed among, claimed per page but — except
        # for the ladder itself — NOT with an absolute number. Which groups a
        # record has comes from its own meta, and the sales team fills that in
        # (measured on this baseline: weight 42 pages, shape 42, pack 20, the
        # ladder 2, container 2, flavor 2). The claim is the one that matters
        # here: the move added a group to no page and took one from no page.
        ('the flavor group', r'data-sf-config-group="flavor"', None),
        ('the unit weight group', r'data-sf-config-group="weight"', None),
        ('the pack size group', r'data-sf-config-group="pack"', None),
        ('the shape group', r'data-sf-config-group="shape"', None),
        ('the container group', r'data-sf-config-group="container"', None),
        ('...and the ladder is still on no page it was not on',
         r'data-sf-config-group="pricing"', 2),
        ('the gallery tabs', r'sf-gallery__tabs', 42),
        ('the side column', r'sf-fdetail2__side', 42),
    ],
    'per_page': [
        ('h1', r'<h1[ >]', 1),
        ('the new style token', r'style\.css\?ver=2\.10\.73', 1),
    ],
    'scoped': [
        ('the ladder is still on the one record that has one',
         'sf-fdetail-config__tiers', H7L_RECORD, 1),
        ('...and still holds exactly three breaks', 'sf-tier__dot', H7L_RECORD, 3),
        ('...and that record keeps its sample row',
         'data-sf-inquiry-sample', H7L_RECORD, 1),
        ('the six cards are on the two home pages and nowhere else',
         'sf-certstrip__badge', lambda n: n in H7L_HOME, 6),
    ],
    'order': [
        # Where the batch put it, which no count can say. Read on the record, so
        # a page that carries the group at the wrong address is reported.
        ('the ladder sits under the intro it belongs to',
         'sf-fdetail2__intro', H7L_PRICING, H7L_RECORD),
        ('...and above the flavor group it used to be filed behind',
         H7L_PRICING, 'data-sf-config-group="flavor"', H7L_RECORD),
        # Both halves of the old order, so a "move" that only re-ordered the
        # group's own insides is caught.
        ('the ladder stays ahead of the sample row it carries',
         'sf-fdetail-config__tiers', 'sf-fdetail-config__sample"', H7L_RECORD),
        ('the column still ends on its inquiry button, after the spec list',
         'sf-fdetail2__params', 'data-sf-inquiry-open>Send Inquiry</a>', H7L_RECORD),
        ('the strip is still a lede, then a row, then the link',
         'sf-certstrip__lede', 'sf-certstrip__more', lambda n: n in H7L_HOME),
    ],
    'h2_delta': None,
    'jsonld_delta': None,
    'sources': {
        'tpl': 'templates/single-sf_formula.html',
    },
    'reinject': ('an old address for the ladder fails coverage',
                 'formulas__joint-support-soft-chews.html', H7L_PRICING,
                 '</div></div>'),
    'delete': ('one page loses the ladder\'s new address fails coverage',
               'formulas__joint-support-soft-chews.html', H7L_LIST + H7L_PRICING),
    'nc13_mode': 'sighted',
    'nc13_label': ('NC13 the insert direction SEES a break renamed, and coverage confirms it'),
    'matrix': [
        ('the tokens are not folded', {'tokens': []}, None),
        ('the ladder is left where the batch found it',
         {'transform': _h7l_partial(off=True), 'applies': 0}, None),
        ('the ladder is filed behind Flavor instead of above it',
         {'transform': _h7l_partial(place='second')}, None),
        ('...and here is the identity, to prove "second" is not the batch',
         {'transform': _h7l_partial(place='tail')}, None),
        ('the ladder is copied to the head and left at the foot as well',
         {'transform': _h7l_partial(copy=True)}, None),
        ('the ladder is deleted instead of moved',
         {'transform': _h7l_partial(drop=True)}, None),
        ('the run count is declared one short', {'applies': 1}, None),
        ('nothing is applied at all',
         {'transform': (lambda t: (t, 0)), 'applies': 0}, None),
    ],
    'nc_source': [
        ('NC-src the source pass fails when the stylesheet keeps its old version',
         'style.css', 'Version: 2.10.73', 'Version: 2.10.72'),
        ('NC-src the source pass fails when the enqueue keeps its old version',
         'functions.php', "array(), '2.10.73');", "array(), '2.10.72');"),
        # 待办25 — the move undone at the source. The rendered proof cannot see
        # this: the transform would move the group either way, and the candidate
        # captured from a theme that appends it would differ from such a
        # transform's output — so this control is what says the SOURCE claim is
        # load-bearing rather than a comment about the code.
        ('NC-src the source pass fails when the ladder is appended, not unshifted',
         'functions.php',
         "array_unshift($groups, array(\n\t\t\t'key' => 'pricing'",
         "$groups[] = array(\n\t\t\t'key' => 'pricing'"),
        # 待办4 — the card surface and the icon size, each dropped on its own.
        ('NC-src the source pass fails when the card stops being a card',
         'style.css',
         "\tpadding: 16px;\n\tbackground: var(--wp--preset--color--bg-light);\n"
         "\tborder: 1px solid var(--wp--preset--color--border-light);\n"
         "\tborder-radius: 8px;\n",
         "\tpadding: 16px;\n"),
        ('NC-src the source pass fails when the icon goes back to 32',
         'style.css',
         "\twidth: 40px;\n\theight: 40px;\n\tcolor: var(--wp--preset--color--primary);\n}",
         "\tcolor: var(--wp--preset--color--primary);\n}"),
        ('NC-src the source pass fails when the phone step stacks the cards',
         'style.css',
         "\t.sf-certstrip__row {\n\t\tgap: 12px;\n\t}",
         "\t.sf-certstrip__row {\n\t\tgrid-template-columns: repeat(2, minmax(0, 1fr));\n\t}"),
    ],
    'nc_page': [
        # 待办25/待办4 — the claims a page edit can break that the MAIN PROOF
        # cannot see, because the payload is removed whole from the comparison:
        # the address, the card count, and a group that quietly leaves.
        ('NC-page the invariants fail when the ladder is pushed back to the foot',
         'formulas__joint-support-soft-chews.html',
         lambda t: _h7l_move(t, place='tail')[0]),
        ('NC-page the invariants fail on a seventh card in the band',
         'root.html',
         lambda t: t.replace('<ul class="sf-certstrip__row" role="list">',
                             '<ul class="sf-certstrip__row" role="list">'
                             '<li class="sf-certstrip__badge"></li>', 1)),
        ('NC-page the invariants fail when a record loses a parameter group',
         'formulas__joint-support-soft-chews.html',
         lambda t: t.replace('data-sf-config-group="shape"',
                             'data-sf-config-group="shapX"', 1)),
    ],
    'nc_blind': ('formulas__joint-support-soft-chews.html',
                 '>≥1,000<', '>≥1000<'),
    'source': [
        ('style.css declares 2.10.73', 'css', r'(?m)^Version: 2\.10\.73$', True),
        ('no 2.10.72 header survives', 'css_live', r'(?m)^Version: 2\.10\.72$', False),
        ('functions.php enqueues 2.10.73 for style.css', 'php',
         r"wp_enqueue_style\('sinofresh-style'[^;]*'2\.10\.73'", True),
        # --- 待办25 -------------------------------------------------------
        ('the ladder group is unshifted onto the head of the list', 'php',
         r"array_unshift\(\$groups, array\(\n\t+'key' => 'pricing'", True),
        ('...and the append form it replaced is gone', 'php_live',
         r"\$groups\[\] = array\(\n\t+'key' => 'pricing'", False),
        ('...while the group itself is unchanged, so the dialog reads it as before',
         'php', r"'key' => 'pricing', 'label' => 'Quantity & Pricing'", True),
        ('the ladder keeps its own card layout', 'php',
         r"'type' => 'single', 'style' => 'tiers', 'hint' => 'Choose one',", True),
        # --- 待办1: the three breaks, which is the claim the user's report made --
        ('a legacy qty still reads as the range start', 'php',
         r"isset\(\$tier\['min'\]\) \? \$tier\['min'\] : \(isset\(\$tier\['qty'\]\)",
         True),
        ('a closed tier still prints "min-max"', 'php', r"return \$min \. '-' \. \$max;", True),
        ('...an open-ended one still prints the ≥ form', 'php', r"return '≥' \. \$min;", True),
        ('...and its number still groups its thousands', 'php',
         r"number_format\(\(float\) str_replace\(',', '', \$value\)\)", True),
        # --- 待办2 -------------------------------------------------------
        ('the column cta still opens the dialog', 'tpl',
         r'<a class="sf-fdetail2__cta" href="/contact/#quote" '
         r'data-sf-inquiry-open>Send Inquiry</a>', True),
        ('...and no Request Sample link survives to be served', 'tpl_live',
         r'Request Sample', False),
        ('the no-js destination is still the quote anchor', 'tpl',
         r'sf-fdetail2__cta" href="/contact/#quote"', True),
        ('the float capsule is still the same opener', 'php',
         r'sf-float-btn--inquiry" href="/contact/#quote" data-sf-inquiry-open', True),
        # --- 待办4 -------------------------------------------------------
        ('the chips are a three-column grid with a 16px gutter', 'css',
         r'\.sf-certstrip__row \{\n\tdisplay: grid;\n\tgrid-template-columns: '
         r'repeat\(3, minmax\(0, 1fr\)\);\n\tgap: 16px;', True),
        ('the chips are cards: Mist surface, Line hairline, 8px radius', 'css',
         r'\.sf-certstrip__badge \{\n\tdisplay: flex;\n\talign-items: center;\n\tgap: 12px;\n'
         r'\tmin-width: 0;\n\tpadding: 16px;\n'
         r'\tbackground: var\(--wp--preset--color--bg-light\);\n'
         r'\tborder: 1px solid var\(--wp--preset--color--border-light\);\n'
         r'\tborder-radius: 8px;\n\}', True),
        ('the icon is 40px, not the 32 it was', 'css',
         r'\.sf-certstrip__icon \{\n\tflex: 0 0 auto;\n\twidth: 40px;\n\theight: 40px;\n'
         r'\tcolor: var\(--wp--preset--color--primary\);\n\}', True),
        ('the tablet step is two columns', 'css',
         r'@media \(max-width: 1024px\) \{[\s\S]{0,320}\.sf-certstrip__row \{\n'
         r'\t\tgrid-template-columns: repeat\(2, minmax\(0, 1fr\)\);\n\t\}', True),
        ('...and the phone keeps two instead of stacking', 'css',
         r'@media \(max-width: 420px\) \{[\s\S]{0,520}\.sf-certstrip__row \{\n'
         r'\t\tgap: 12px;\n\t\}', True),
        ('...stepping the icon and the padding down with them', 'css',
         r'\.sf-certstrip__badge \{\n\t\tgap: 10px;\n\t\tpadding: 12px;\n\t\}', True),
        # The retired literals, claimed gone rather than assumed gone: a rename
        # that leaves the old rule behind is the classic way a batch "changes" a
        # rule while both of them still apply.
        ('the old 10/20 gutter is gone', 'css_live', r'gap: 10px 20px;', False),
        ('...and so is the phone step that stacked them', 'css_live',
         r'\.sf-certstrip__row \{\n\t\tgap: 8px 12px;\n\t\}', False),
        ('...and the ≤768px cert step with it', 'css_live',
         r'@media \(max-width: 768px\) \{\n\t/\* 待办18: two columns of three', False),
    ],
}


# ------------------------------------------------------------- H8a batch

# Batch H8a is six edits to the right column, four of them inside markup whose
# content is per-record. It takes the `insert` direction — the DEFAULTS are
# constants of the code (the four fixed shelf lives, the word "Custom", the
# Custom pick's own markup, the retirement of one row), so the expected page can
# be built from the baseline, and the one per-record byte it also carries — the
# printed shelf life — is derived by the same rule the renderer uses (strip the
# value's own repeat of its name; on the record that holds a pool value, print
# the pool value instead).
#
# What the direction costs is stated in NC13: with `insert` the payload IS
# compared, so an edit inside it turns the main proof red — that is why this
# declaration sets `nc13_mode: 'sighted'` and not the default.
H8A_RECORD = lambda n: 'joint-support-soft-chews' in n
H8A_DETAIL = lambda n: 'formulas__' in n

# The groups a visitor may type their own answer into. `pricing` is deliberately
# absent: a price list has nothing to type, and a Custom break would be a number
# the sales desk cannot quote against.
H8A_BOXED = ('flavor', 'weight', 'pack', 'species', 'stage', 'shape', 'container')

def _h8a_label(key, kind):
    """The Custom pick. Its input type follows the group's OWN inputs, read off
    the bytes rather than assumed: seven dimensions are consistent about having
    a Custom answer, and they are not consistent about being single-select —
    Suitable For stays a multi-select that now also offers Custom, so its pick
    is a checkbox. Hard-coding `radio` here would have been a claim the theme
    does not make, and it would only have shown up the day a record carried a
    species value."""
    return ('<label class="sf-fdetail-config__opt" data-sf-config-custom="1">'
            '<input class="sf-fdetail-config__input" type="%s" name="sf-config-%s" '
            'value="Custom" data-sf-config-opt="%s">'
            '<span class="sf-fdetail-config__box" aria-hidden="true"></span>'
            '<span class="sf-fdetail-config__text">Custom</span></label>'
            % (kind, key, key))


H8A_BOX = (
    '<div class="sf-fdetail-config__custom" data-sf-config-custom-for="%(key)s" hidden>'
    '<input type="text" class="sf-fdetail-config__custom-input" '
    'data-sf-config-custom-input="%(key)s" maxlength="60" autocomplete="off" '
    'spellcheck="false" aria-label="Your own %(label)s" '
    'placeholder="Type your own"></div>')

# flavor and pack stop being multi-select. Scoped to the two groups BY NAME: a
# bare `type="checkbox"` replacement would also rewrite the Custom pick's own
# input if the order of the passes ever changed.
H8A_CHECKBOX = re.compile(
    r'(<input class="sf-fdetail-config__input" )type="checkbox"'
    r'( name="sf-config-(?:flavor|pack)")')

# The hint that used to promise more than the control now allows.
H8A_HINT_OLD = re.compile(
    r'<span class="sf-fdetail-config__hint">Choose one or more</span>')
H8A_HINT_NEW = '<span class="sf-fdetail-config__hint">Choose one</span>'

# One group at a time, up to and including the close of its option row. The
# alternation on the key is what keeps `pricing` out of the run: the group it
# needs left alone must not be matched at all, or the count of edits would
# include a pass that changed nothing.
H8A_GROUP = re.compile(
    r'(<div class="sf-fdetail-config__group" data-sf-config-group="('
    + '|'.join(H8A_BOXED) + r')">'
    r'[\s\S]*?<div class="sf-fdetail-config__options[^"]*" role="group" aria-label="([^"]*)">)'
    r'([\s\S]*?)'
    r'(</div>)')

# 待办26 — the row leaves the parameter list. Its value came from the form
# page's own `.sf-facts-mini` cell, which still prints it; JSON-LD never read
# this row. The field itself stays in the admin (see the source claims).
H8A_PACKAGING = re.compile(
    r'<dt class="sf-fdetail2__term">Packaging</dt>'
    r'<dd class="sf-fdetail2__value">[\s\S]*?</dd>')

# 待办29 — both carriers stop repeating the row's own label. Anchored on the
# term/value pair, because the same string appears six more times on a detail
# page (JSON-LD twice, the Standard Specs card, and three related-card specs)
# and only these two are the carriers.
H8A_SHELF_PARAMS = re.compile(
    r'(<dt class="sf-fdetail2__term">Shelf life</dt>'
    r'<dd class="sf-fdetail2__value">)(\d+) months shelf life(</dd>)')
H8A_SHELF_SPECS = re.compile(
    r'(<dt class="sf-fdetail-specs__term">Shelf Life</dt>'
    r'<dd class="sf-fdetail-specs__value">)(\d+) months shelf life(</dd>)')

# ...and the one record whose pool value says something the spec string does
# not. It is a second pass on purpose: the first strips the name, this one says
# what the pool holds, and the two are counted separately so a run that did the
# first and skipped the second cannot report the same total.
#
# This is the batch's only per-record byte beyond the shelf-life rule itself, so
# the page's identity has to be read out of the page (`_h8a_page`). Its control
# is the matrix mutant `pool=False` — `invariants` owns no clause for it, and
# giving it one would mean deriving the expected value from the baseline, which
# is the transform itself.
H8A_POOL_PARAMS = re.compile(
    r'(<dt class="sf-fdetail2__term">Shelf life</dt>'
    r'<dd class="sf-fdetail2__value">)\d+ months(</dd>)')
H8A_POOL_SPECS = re.compile(
    r'(<dt class="sf-fdetail-specs__term">Shelf Life</dt>'
    r'<dd class="sf-fdetail-specs__value">)\d+ months(</dd>)')


def _h8a_group(m, custom=True, box=True):
    head, key, label, body, close = m.groups()
    kind = 'checkbox' if 'type="checkbox"' in body else 'radio'
    if custom:
        if 'value="custom"' in body:
            # A library row already ends the group in Custom (shape, container).
            # It is marked, not re-added: the slug is validated by the PDF
            # endpoint, so the option stays exactly what the library publishes.
            body = body.replace(
                '<label class="sf-fdetail-config__opt"><input class="sf-fdetail-config__input" '
                'type="radio" name="sf-config-%s" value="custom"' % key,
                '<label class="sf-fdetail-config__opt" data-sf-config-custom="1">'
                '<input class="sf-fdetail-config__input" type="radio" '
                'name="sf-config-%s" value="custom"' % key, 1)
        else:
            body = body + _h8a_label(key, kind)
    return head + body + close + (H8A_BOX % {'key': key, 'label': label} if box else '')


def _h8a_move(text, page, check=True, hint=True, custom=True, box=True,
              packaging=True, shelf=True, pool=True):
    n = 0
    if check:
        text, k = H8A_CHECKBOX.subn(r'\1type="radio"\2', text)
        n += k
    if hint:
        text, k = H8A_HINT_OLD.subn(H8A_HINT_NEW, text)
        n += k
    if custom or box:
        text, k = H8A_GROUP.subn(
            lambda m: _h8a_group(m, custom=custom, box=box), text)
        n += k
    if packaging:
        text, k = H8A_PACKAGING.subn('', text)
        n += k
    if shelf:
        text, k = H8A_SHELF_PARAMS.subn(r'\g<1>\g<2> months\g<3>', text)
        n += k
        text, k = H8A_SHELF_SPECS.subn(r'\g<1>\g<2> months\g<3>', text)
        n += k
    if pool and H8A_RECORD(page):
        text, k = H8A_POOL_PARAMS.subn(r'\g<1>24 months\g<2>', text)
        n += k
        text, k = H8A_POOL_SPECS.subn(r'\g<1>24 months\g<2>', text)
        n += k
    return text, n
    if packaging:
        text, k = H8A_PACKAGING.subn('', text)
        n += k
    if shelf:
        text, k = H8A_SHELF_PARAMS.subn(r'\g<1>\g<2> months\g<3>', text)
        n += k
        text, k = H8A_SHELF_SPECS.subn(r'\g<1>\g<2> months\g<3>', text)
        n += k
    if pool and H8A_RECORD(page):
        text, k = H8A_POOL_PARAMS.subn(r'\g<1>24 months\g<2>', text)
        n += k
        text, k = H8A_POOL_SPECS.subn(r'\g<1>24 months\g<2>', text)
        n += k
    return text, n


def _h8a_page(text):
    """The transform needs the page's name for one clause — which record holds
    a pool value. The gate calls `transform(text)`, so the name arrives through
    the text, and the page's own canonical link is where it is stated (measured:
    on both copies of the record it is also the FIRST `/formulas/<slug>/` in the
    document, in both languages, so the fallback is the reading this actually
    takes; the canonical is preferred because it is the statement of identity
    rather than a coincidence of order)."""
    m = (re.search(r'<link rel="canonical" href="[^"]*?/formulas/([a-z0-9-]+)/"', text)
         or re.search(r'/formulas/([a-z0-9-]+)/', text))
    return H8A_RECORD(m.group(1)) if m else False


def _h8a_transform(text):
    return _h8a_move(text, 'joint-support-soft-chews' if _h8a_page(text) else '')


def _h8a_partial(**flags):
    def f(text):
        return _h8a_move(text, 'joint-support-soft-chews' if _h8a_page(text) else '',
                         **flags)
    return f


def _h8a_boxes(base, n):
    """How many Custom boxes the candidate must carry on this page: one per
    group that can be typed in, read off the BASELINE's own group inventory.
    Derived from the other side on purpose — counting the candidate's boxes
    against the candidate's boxes would be the circularity this clause exists
    to avoid, and so would counting them against a constant, because which
    groups a record has comes from its own meta and the sales team fills it."""
    t = read(os.path.join(base, n + '.html'))
    return sum(1 for g in H8A_BOXED if ('data-sf-config-group="%s"' % g) in t)


BATCHES['h8a'] = {
    'name': "H8a — the right column: a sticky gallery, one pick per group with "
            "a Custom answer, a fixed shelf-life pool, and the Packaging row retires",
    'mode': 'insert',
    'tokens': [
        ('?ver=2.10.73', '?ver=2.10.74'),                      # style.css
        ('config.js?ver=1.3.0', 'config.js?ver=1.4.0'),        # config.js
    ],
    # 314 edits: 74 inputs stop being checkboxes, 2 hints stop promising more
    # than one, 108 groups gain a Custom pick and its box, 42 Packaging rows
    # leave, 84 shelf-life carriers stop repeating their own name, and 4 files
    # on the two copies of the record that hold a pool value.
    'applies': 314,
    'transform': _h8a_transform,
    'coverage': [
        ('?ver=2.10.73', 0),
        ('config.js?ver=1.3.0', 0),
        ('>Choose one or more<', 0),
        # Both carriers, both numbers, in one claim: the row's own label is no
        # longer part of the value it prints. `shelf life` also appears inside
        # JSON-LD and the related-card specs, so the claim is anchored on the
        # close of a value cell.
        ('months shelf life</dd>', 0),
        ('<dt class="sf-fdetail2__term">Packaging</dt>', 0),
        # pricing is the group the batch must NOT touch, and this is the claim
        # that says so: a Custom box filed under it would be reachable only from
        # a price list, which is the one place a typed answer cannot be quoted.
        ('data-sf-config-custom-for="pricing"', 0),
    ],
    'insertions': [
        ('?ver=2.10.74', 75),
        ('config.js?ver=1.4.0', 42),
        ('data-sf-config-custom="1"', 108),
        ('data-sf-config-custom-input="', 108),
        ('type="radio"', 536),
    ],
    'counts': [
        # 待办27 — the two multi-select groups become single picks. 74 -> 0 is a
        # pair rather than a bare absence because the number it replaced (398
        # radios) is the other half of the same claim.
        ('the multi-select inputs become single picks', 'type="checkbox"', 74, 0),
        ('...and the radios they became join the ones already there',
         'type="radio"', 398, 536),
        # The theme did not rename the library's own Custom slug.
        ('the library Custom slugs are untouched', 'value="custom"', 44, 44),
        ('...and the picks the theme added are its own', 'value="Custom"', 0, 64),
        ('the parameter column keeps all its groups', 'sf-fdetail-config__group', 110, 110),
        ('every group that can be typed in gains a pick', 'sf-fdetail-config__opt', 582, 646),
        ('...and a box beside it', 'class="sf-fdetail-config__custom" data-sf-config-custom-for="', 0, 108),
        ('the hint stops promising more than one', 'sf-fdetail-config__hint">Choose one</span>', 46, 48),
        # 待办26 — the row retires on all 42 pages and on no others.
        ('the Packaging row leaves the parameter list',
         '<dt class="sf-fdetail2__term">Packaging</dt>', 42, 0),
        # 待办29 — the value loses its own name on 42 pages and 84 carriers,
        # split from the one record whose pool value says otherwise.
        ('the shelf life prints the spec value without its name',
         'sf-fdetail2__value">18 months</dd>', 0, 14),
        ('...and prints the pool value where there is one',
         'sf-fdetail2__value">24 months</dd>', 0, 28),
        ('...and the spec sheet carries both edits with it',
         'sf-fdetail-specs__value">18 months</dd>', 0, 14),
        ('...there too', 'sf-fdetail-specs__value">24 months</dd>', 0, 28),
        # 待办23's other half: the ladder is a price list and stays one.
        ('the ladder keeps its three breaks', 'sf-tier__dot', 6, 6),
    ],
    'unmoved': [
        ('the cookie banner', r'class="sf-cookie-banner"', 75),
        ('the float stack', r'class="sf-float-stack"', 75),
        ('the certificate dialog', r'sf-certmodal', 1),
        ('the navigation', r'wp-block-navigation', 75),
        ('the parameter column', r'sf-fdetail-config__group', 42),
        ('...and every group it holds', r'sf-fdetail-config__options', 42),
        # Which groups a record has comes from its own meta. The claim is that
        # this batch added a group to no page and took one from no page — the
        # four that changed gained a PICK inside a group they already had.
        ('the flavor group', r'data-sf-config-group="flavor"', None),
        ('the unit weight group', r'data-sf-config-group="weight"', None),
        ('the pack size group', r'data-sf-config-group="pack"', None),
        ('the shape group', r'data-sf-config-group="shape"', None),
        ('the container group', r'data-sf-config-group="container"', None),
        ('...and the ladder is still on no page it was not on',
         r'data-sf-config-group="pricing"', 2),
        ('the gallery tabs', r'sf-gallery__tabs', 42),
        ('the side column', r'sf-fdetail2__side', 42),
    ],
    'per_page': [
        ('h1', r'<h1[ >]', 1),
        ('the new style token', r'style\.css\?ver=2\.10\.74', 1),
    ],
    'scoped': [
        ('the ladder is still on the one record that has one',
         'sf-fdetail-config__tiers', H8A_RECORD, 1),
    ],
    'corroborated': [
        # Derived from the baseline, so the number of boxes is not read off the
        # side being checked. A box that quietly leaves one page is invisible to
        # every total in `counts` — it only moves that page by one.
        ('a Custom box for every group that can be typed in',
         r'data-sf-config-custom-input="', _h8a_boxes),
    ],
    'order': [
        # Where the batch put the pick, which no count can say: the Custom
        # answer ends the row it belongs to, and its box follows the row.
        ('the Custom pick ends the row it belongs to, its box after it',
         'value="custom"', 'data-sf-config-custom-for="shape"', H8A_DETAIL),
        ('the column still ends on its inquiry button, after the parameter list',
         'sf-fdetail2__params', 'data-sf-inquiry-open>Send Inquiry</a>', H8A_RECORD),
    ],
    'h2_delta': None,
    'jsonld_delta': None,
    'sources': {
        'cfg': 'assets/js/config.js',
        'pools': 'inc/formula-pools.php',
        'admin': 'inc/formula-admin.php',
    },
    'reinject': ('an old address for the retired row fails coverage',
                 'formulas__calming-soft-chews.html',
                 '<dt class="sf-fdetail2__term">Certifications</dt>',
                 '<dt class="sf-fdetail2__term">Packaging</dt>'
                 '<dd class="sf-fdetail2__value">Jar</dd>'),
    'delete': ("one page loses a Custom answer's box fails coverage",
               'formulas__calming-soft-chews.html',
               'data-sf-config-custom-input="'),
    'nc13_mode': 'sighted',
    'nc13_label': ('NC13 the insert direction SEES a Custom pick renamed, and coverage confirms it'),
    'matrix': [
        ('the tokens are not folded', {'tokens': []}, None),
        ('the pick is left off every group',
         {'transform': _h8a_partial(custom=False)}, None),
        ('...and the box is left off with it',
         {'transform': _h8a_partial(box=False)}, None),
        ('the group the visitor types into is skipped instead',
         {'transform': _h8a_partial(custom=False, box=False)}, None),
        ('pack size keeps its checkboxes',
         {'transform': _h8a_partial(check=False)}, None),
        ('the hint goes on promising more than one',
         {'transform': _h8a_partial(hint=False)}, None),
        ('the Packaging row is left in the parameter list',
         {'transform': _h8a_partial(packaging=False)}, None),
        ('the shelf life goes on repeating its own name',
         {'transform': _h8a_partial(shelf=False)}, None),
        ('the record keeps the spec value instead of its pool value',
         {'transform': _h8a_partial(pool=False)}, None),
        ('the run count is declared one short', {'applies': 313}, None),
        ('nothing is applied at all',
         {'transform': (lambda t: (t, 0)), 'applies': 0}, None),
    ],
    'nc_source': [
        ('NC-src the source pass fails when the stylesheet keeps its old version',
         'style.css', 'Version: 2.10.74', 'Version: 2.10.73'),
        ('NC-src the source pass fails when the enqueue keeps its old version',
         'functions.php', "array(), '2.10.74');", "array(), '2.10.73');"),
        ('NC-src ...and when config.js keeps its own',
         'functions.php', "'/assets/js/config.js', array(), '1.4.0'",
         "'/assets/js/config.js', array(), '1.3.0'"),
        # 待办23 — the sticky gallery, dropped.
        ('NC-src the source pass fails when the media column stops sticking',
         'style.css',
         "\t.sf-fdetail2__media {\n\t\tposition: sticky;\n\t\ttop: 100px;\n"
         "\t\talign-self: start;\n\t}\n",
         ""),
        # 待办28 — the phone fold, put back where H7l had left it.
        ('NC-src the source pass fails when the phone fold drops the ladder again',
         'style.css',
         ".sf-fdetail-config__group:nth-child(n + 5) {",
         ".sf-fdetail-config__group:nth-child(n + 4) {"),
        # 待办29 — the two carriers, reverted one at a time.
        ('NC-src the source pass fails when the parameter row reads the spec string again',
         'functions.php',
         "\t$shelf = sf_formula_shelf_life_line($post_id, $parts);\n",
         "\t$shelf = isset($parts['shelf']) ? $parts['shelf'] : '';\n"),
        ('NC-src ...and when the pool keeps no value the fixed list no longer offers',
         'inc/formula-admin.php', "'keep_unknown' => true,", "'keep_unknown' => false,"),
        # 待办27 — the Custom answer, disowned at both ends.
        ('NC-src the source pass fails when the pick stops reading its box',
         'assets/js/config.js',
         "opt.hasAttribute('data-sf-config-custom')", 'false'),
        ('NC-src ...and when the box stops following its pick',
         'assets/js/config.js', "function syncCustom(focus)", "function syncCustomX(focus)"),
        # 待办28 — the sliding row, disowned.
        ('NC-src the source pass fails when the shape row loses its arrows',
         'assets/js/config.js', "['shape', 'container'].forEach", "['shape'].forEach"),
    ],
    'nc_page': [
        # The two claims the MAIN PROOF cannot see, for the reason it cannot see
        # them: `invariants` is the pass `nc_page` drives, and both of these are
        # owned by clauses that live there. The record's PRINTED VALUE is not
        # one of them — it is owned by the main proof (the declaration builds
        # `24 months` for exactly that page, and `applies` counts the pass that
        # did it) and by the coverage pair; its control is the matrix mutant
        # `pool=False`, which is caught on 2 differing pages. Asserting it here
        # would have needed an `invariants` clause that re-derives the value
        # from the baseline, i.e. one that agrees with the transform by
        # construction — which is the circularity this file refuses.
        ('NC-page the invariants fail when a page loses a Custom box',
         'formulas__calming-soft-chews.html',
         lambda t: re.sub(
             r'<div class="sf-fdetail-config__custom" data-sf-config-custom-for='
             r'"[a-z]+" hidden>[\s\S]*?</div>', '', t, count=1)),
        ('NC-page the invariants fail when the box stops following its pick',
         'formulas__calming-soft-chews.html',
         lambda t: t.replace('data-sf-config-custom-for="shape"',
                             'data-sf-config-custom-for="shapX"', 1)),
        ('NC-page the invariants fail on a group that quietly leaves',
         'formulas__calming-soft-chews.html',
         lambda t: t.replace('data-sf-config-group="shape"',
                             'data-sf-config-group="shapX"', 1)),
    ],
    'nc_blind': ('formulas__calming-soft-chews.html',
                 'data-sf-config-custom="1"', 'data-sf-config-custom="X1"'),
    'source': [
        ('style.css declares 2.10.74', 'css', r'(?m)^Version: 2\.10\.74$', True),
        # Read on the RAW bytes, not on the comment-blanked twin: the theme
        # header is itself inside a `/* */` block, so the blanked twin has that
        # line erased and this claim could never have fired. Corrected in batch
        # H8b, which carries the same claim and the control that proves it lives.
        ('no 2.10.73 header survives', 'css', r'(?m)^Version: 2\.10\.73$', False),
        ('functions.php enqueues 2.10.74 for style.css', 'php',
         r"wp_enqueue_style\('sinofresh-style'[^;]*'2\.10\.74'", True),
        ('...and 1.4.0 for config.js', 'php',
         r"wp_enqueue_script\('sinofresh-config'[^;]*'1\.4\.0'", True),
        # --- 待办23: the gallery sticks ----------------------------------
        ('the media column sticks 100px down, desktop only', 'css_live',
         r'@media \(min-width: 769px\) \{[\s\S]{0,2000}\.sf-fdetail2__media \{\n'
         r'\t\tposition: sticky;\n\t\ttop: 100px;\n\t\talign-self: start;\n\t\}', True),
        ('...because the root guard ends on clip, which never creates a scroll container',
         'css_live',
         r'html,\nbody \{\n\toverflow-x: hidden;\n\toverflow-x: clip;\n\}', True),
        # --- 待办26: the row retires -------------------------------------
        ('the parameter list no longer files a Packaging row', 'php_live',
         r"\$rows\['Packaging'\]", False),
        ('...and it is still the form page that prints packaging formats',
         'php', r"sinofresh_formula_spec_cell\(\$form_slug, 'Packaging formats'\)", True),
        # --- 待办27: one pick per group, and a Custom answer --------------
        ('the theme can publish a Custom pick and its box', 'php',
         r'function sf_formula_custom_option\(', True),
        ('...the box is server-rendered, so no-js still has one', 'php',
         r'function sf_formula_custom_field\(', True),
        ('...a typed answer is filed with the marker the desk reads', 'php',
         r"\$text\[\] = \$own \. ' \(custom\)';", True),
        ('...and it is unwrapped server-side, not trusted as posted', 'php',
         r'function sinofresh_formula_custom_text\(\$value\)', True),
        ('the pick keeps the library Custom slug rather than renaming it',
         'php', r"if \('custom' === \(string\) \$s\[\'slug'\]\)", True),
        # The seventh dimension, and the one the rendered proof cannot reach:
        # no record in this capture carries a species value, so the group is on
        # 0 of 75 pages. The claim is a source claim for that reason, and it is
        # the pair — Suitable For stays multi AND gets a Custom pick.
        ('Suitable For stays a multi-select', 'php',
         r"'key' => 'species', 'label' => 'Suitable For', 'meta' => implode\(', ', \$species\),\n"
         r"\t\t\t'type' => 'multi', 'style' => 'chips',", True),
        ('...and still gets a Custom answer of its own', 'php',
         r"\$options\[\] = sf_formula_custom_option\(\);\n"
         r"\t\t\$groups\[\] = array\(\n\t\t\t'key' => 'species'", True),
        ('...and the pick answers with the typed text, not the word',
         'cfg_live', r"opt\.hasAttribute\('data-sf-config-custom'\)", True),
        ('...which is what the box appears for', 'cfg_live',
         r'function syncCustom\(focus\)', True),
        ('the box ships hidden and the pick reveals it', 'css_live',
         r'\.sf-fdetail-config__custom\[hidden\] \{\n\tdisplay: none;\n\}', True),
        # --- 待办28: the sliding row -------------------------------------
        ('the arrow ships display:none, so a page with no script has none',
         'css_live', r'\.sf-fdetail-config__arrow \{\n\tdisplay: none;', True),
        ('...and an overflowing row on a pointer device shows them', 'css_live',
         r'@media \(min-width: 769px\) \{\n\t\.sf-fdetail-config__rail--scrolls '
         r'\.sf-fdetail-config__arrow \{\n\t\tdisplay: inline-flex;\n\t\}', True),
        ('...outside the row, so they cover no picture', 'css_live',
         r'\.sf-fdetail-config__arrow--prev \{ left: -22px; \}', True),
        ('...and the row they serve is the one that slides', 'css_live',
         r'\.sf-fdetail-config__group\[data-sf-config-group="shape"\] '
         r'\.sf-fdetail-config__options,\n'
         r'\.sf-fdetail-config__group\[data-sf-config-group="container"\] '
         r'\.sf-fdetail-config__options \{\n\tflex-wrap: nowrap;\n\toverflow-x: auto;', True),
        ('...which is the pair of groups the script wires them onto', 'cfg_live',
         r"\['shape', 'container'\]\.forEach", True),
        ('...and the rails are built only when the row overflows', 'cfg_live',
         r'room > 4', True),
        # The fold: the cut moved from the fourth group to the fifth.
        ('the phone fold now keeps the ladder and the three named groups',
         'css_live',
         r'\.sf-fdetail-config__list\.sf-config-folded\n\t\t'
         r'\.sf-fdetail-config__group:nth-child\(n \+ 5\) \{', True),
        ('...and the fourth-group cut it replaced is gone', 'css_live',
         r'nth-child\(n \+ 4\) \{\n\t\tdisplay: none;', False),
        ('...while the fold button still says both of its states', 'cfg_live',
         r"open \? 'Show fewer specs ▴' : 'View all specs ▾'", True),
        # --- 待办29: the fixed pool -------------------------------------
        # WHERE THE PRINTED VALUE IS OWNED, stated because the clause that
        # reads the pool is easy to miss: `sf_formula_shelf_life_line()` on the
        # two rows below is what decides it, and the NC-src control for the
        # parameter row is the reason these two claims exist — without them the
        # control fired and the source pass still said ok, which is a source
        # pass that cannot see the batch's central edit.
        ('the parameter row asks the pool what to print', 'php',
         r"\$shelf = sf_formula_shelf_life_line\(\$post_id, \$parts\);\n"
         r"\tif \(\$shelf !== ''\) \{\n\t\t\$rows\['Shelf life'\]", True),
        ('...and the spec sheet asks the same reader', 'php',
         r"\$shelf = sf_formula_shelf_life_line\(\$post_id, \$parts\);\n"
         r"\tif \(\$shelf !== ''\) \{\n\t\t\$rows\['Shelf Life'\]", True),
        ('...so neither row reads the raw spec string any more', 'php_live',
         r"\$rows\['Shelf life'\] = esc_html\(isset\(\$parts\['shelf'\]\)", False),
        ('the shelf life is a fixed pool of four', 'pools',
         r"return array\('12 months', '18 months', '24 months', '36 months'\);", True),
        ('...a value the pool once held still prints as a pool value', 'pools',
         r"return \$m\[1\] \. ' months';", True),
        ('...the pool keeps a value it no longer offers instead of clearing it',
         'admin', r"'keep_unknown' => true,", True),
        ('...and the field is a select among the published parameters',
         'admin',
         r"'key' => 'sf_formula_shelf_life', 'label' => 'Shelf life', "
         r"'group' => 'params', 'type' => 'select'", True),
        ('no free-text shelf-life line survives in the packaging group',
         'admin_live', r"'sf_formula_shelf_life'[^\n]*'group' => 'packaging'", False),
    ],
}


# ------------------------------------------------------------------ batch H8b
# Shape and Container Type follow the dosage form.
#
# The whole delta lives inside two groups of one renderer, and every value it
# writes comes from inc/formula-pools.php's per-dosage pools — which the
# PUBLISHING FORM has been reading since batch H1. The tables below are therefore
# a second, independent transcription of those pools, and that is deliberate: a
# gate that reads its payload out of the product's PHP would agree with any
# mistake the product made. The `source` section is where the two are required to
# match, line by line.
#
# What the transform may NOT do is read the candidate. It reads the BASELINE and
# asks it two questions — which dosage form is this page for (the spec sheet's own
# "Dosage Form" row) and does it already draw the container group (post 158 is the
# one record that does) — and builds the expected bytes from those two facts plus
# the tables.

H8B_POOLS = {
    'soft-chews': {
        'label': 'Shape',
        'shape': ['Bone', 'Round', 'Square', 'Heart', 'Star', 'Paw', 'Cylinder', 'Custom'],
        'packaging': ['Aluminum Stand-up Pouch', 'Aluminum Foil Pouch with Zipper',
                      'Plastic Bottle', 'Jar', 'Blister Pack', 'Box + Foil', 'Custom'],
    },
    'tablets': {
        'label': 'Shape',
        'shape': ['Round', 'Oval', 'Square', 'Bone', 'Custom'],
        'packaging': ['Plastic Bottle', 'Jar', 'Blister Pack', 'Foil Pouch', 'Custom'],
    },
    'dental-chews': {
        'label': 'Shape',
        'shape': ['Bone', 'Stick', 'Round', 'Spiral', 'Toothbrush', 'Custom'],
        'packaging': ['Foil Pouch', 'Stand-up Pouch', 'Box', 'Custom'],
    },
    'pastes': {
        'label': 'Texture',
        'shape': ['Smooth Paste', 'Thick Paste', 'Squeezable Gel', 'Custom'],
        'packaging': ['Plastic Tube', 'Metal Tube', 'Aluminum Tube', 'Custom'],
    },
    'powders': {
        'label': 'Appearance',
        'shape': ['Fine Powder', 'Granules', 'Microencapsulated', 'Custom'],
        'packaging': ['Jar', 'Foil Pouch', 'Stand-up Pouch', 'Custom'],
    },
    'drops': {
        'label': 'Appearance',
        'shape': ['Clear', 'Light Yellow', 'Amber', 'Custom'],
        'packaging': ['Dropper Bottle', 'Glass Bottle', 'Plastic Bottle', 'Custom'],
    },
    'liquids': {
        'label': 'Appearance',
        'shape': ['Clear', 'Light Color', 'Suspension', 'Custom'],
        'packaging': ['Plastic Bottle', 'Glass Bottle', 'Bottle with Cup', 'Custom'],
    },
    'fish-oil': {
        'label': 'Form',
        'shape': ['Softgel', 'Liquid Oil', 'Pump Bottle', 'Custom'],
        'packaging': ['Plastic Bottle', 'Glass Bottle', 'Pump Bottle', 'Custom'],
    },
}

# The page states the dosage form by NAME ("Fish Oil"); the pools are keyed by
# slug. The two are one sanitize_title() apart, and transcribing the pairs rather
# than slugifying at run time is what keeps "Dental Chews" from silently
# becoming "dental-chews" in one place and meaning something else in another.
H8B_FORM_NAME = {
    'Soft Chews': 'soft-chews', 'Tablets': 'tablets', 'Dental Chews': 'dental-chews',
    'Pastes': 'pastes', 'Powders': 'powders', 'Drops': 'drops',
    'Liquids': 'liquids', 'Fish Oil': 'fish-oil',
}

H8B_ROW = re.compile(
    r'<dt class="sf-fdetail-specs__term">Dosage Form</dt>'
    r'<dd class="sf-fdetail-specs__value">([^<]*)</dd>')

# The shape group's own three carriers of its name, and its option list.
H8B_ROW_LABEL = '<span class="sf-fdetail-config__label">Shape</span>'
H8B_BOX_LABEL = 'aria-label="Your own Shape"'

# One option list. Non-greedy to the FIRST </div>: an option is a <label> of
# spans and carries no div of its own, so the first close is the container's.
H8B_OPTS = re.compile(
    r'<div class="sf-fdetail-config__options" role="group" aria-label="[^"]*">.*?</div>',
    re.S)

# Where the container group goes when the record does not have one: between the
# shape group's closing div and the one that closes the list they live in. The
# shape group is last on all forty of those pages (measured), which is why this
# anchor is unique there — and why a page without a configurator at all (the
# other thirty-three) is not touched: the anchor cannot match what is not there.
H8B_LIST_TAIL = '</div></div><p class="sf-fdetail-config__'


def _h8b_form(text):
    """The dosage form this page is about, from the page itself.

    The spec sheet's Dosage Form row is the page's own statement of identity and
    is present on all 42 detail pages. Reading it here — rather than keying the
    expected bytes on the file's name — is what makes the case where the
    renderer and the taxonomy disagree a RED page instead of a silently skipped
    one.
    """
    m = H8B_ROW.search(text)
    return H8B_FORM_NAME.get(m.group(1)) if m else None


def _h8b_options(key, labels):
    """One group's option list, byte for byte as the renderer writes it.

    The value IS the label — that is the batch's central claim, and the reason
    the option list cannot be produced by renaming the old one. The label the
    pool spells "Custom" carries the flag that opens batch H8a's text box; the
    pool already ends in one, so nothing is appended.
    """
    out = []
    for label in labels:
        flag = ' data-sf-config-custom="1"' if label == 'Custom' else ''
        out.append(
            '<label class="sf-fdetail-config__opt"%s>'
            '<input class="sf-fdetail-config__input" type="radio" name="sf-config-%s"'
            ' value="%s" data-sf-config-opt="%s">'
            '<span class="sf-fdetail-config__box" aria-hidden="true"></span>'
            '<span class="sf-fdetail-config__img sf-fdetail-config__img--empty">'
            '<span class="sf-fdetail-config__empty-label">%s</span></span></label>'
            % (flag, key, label, key, label))
    return ''.join(out)


def _h8b_opts_in(seg, key, labels, name):
    """Replace the first option list in `seg` with the pool's own."""
    exp = ('<div class="sf-fdetail-config__options" role="group" aria-label="%s">'
           % name) + _h8b_options(key, labels) + '</div>'
    new = H8B_OPTS.sub(lambda m: exp, seg, count=1)
    return new, (1 if new != seg else 0)


def _h8b_container_group(labels, meta=''):
    """The whole container group, for the forty pages that do not have one."""
    return (
        '<div class="sf-fdetail-config__group" data-sf-config-group="container">'
        '<p class="sf-fdetail-config__row">'
        '<span class="sf-fdetail-config__label">Container Type</span>'
        '<span class="sf-fdetail-config__meta">%s</span>'
        '<span class="sf-fdetail-config__hint">Choose one</span></p>'
        '<div class="sf-fdetail-config__options" role="group" aria-label="Container Type">%s</div>'
        '<div class="sf-fdetail-config__custom" data-sf-config-custom-for="container" hidden>'
        '<input type="text" class="sf-fdetail-config__custom-input" '
        'data-sf-config-custom-input="container" maxlength="60" autocomplete="off" '
        'spellcheck="false" aria-label="Your own Container Type" placeholder="Type your own">'
        '</div></div>' % (meta, _h8b_options('container', labels)))


def _h8b_rub(text, old, new):
    """One declared replacement. (text, 1) when it moved bytes, (text, 0) when
    the baseline already said it.

    The zero matters: the pool calls this question "Shape" on soft chews, tablets
    and dental chews, so on 20 of the 42 pages the group's NAME is not an edit at
    all. Counting those as edits would let a page whose name is wrong hide inside
    the run total, which is the one number the main proof checks.
    """
    if old == new or old not in text:
        return text, 0
    return text.replace(old, new, 1), 1


def _h8b_move(text, label=True, shape=True, container=True):
    form = _h8b_form(text)
    if not form:
        return text, 0
    pool = H8B_POOLS[form]
    n = 0

    i = text.find('data-sf-config-group="shape"')
    if i < 0:
        return text, 0
    j = text.find('data-sf-config-group="container"', i)
    has_container = j >= 0
    if not has_container:
        j = text.find('data-sf-config-summary', i)
    head, seg, rest = text[:i], text[i:j], text[j:]

    if label:
        seg, k = _h8b_rub(seg, H8B_ROW_LABEL,
                          '<span class="sf-fdetail-config__label">%s</span>' % pool['label'])
        n += k
        seg, k = _h8b_rub(seg, H8B_BOX_LABEL, 'aria-label="Your own %s"' % pool['label'])
        n += k
    if shape:
        seg, k = _h8b_opts_in(seg, 'shape', pool['shape'], pool['label'])
        n += k

    if container:
        if has_container:
            k = rest.find('data-sf-config-summary')
            cont, rest = rest[:k], rest[k:]
            cont, k2 = _h8b_opts_in(cont, 'container', pool['packaging'], 'Container Type')
            n += k2
            rest = cont + rest
        else:
            at = seg.rfind(H8B_LIST_TAIL)
            if at >= 0:
                seg = (seg[:at] + '</div>' + _h8b_container_group(pool['packaging'])
                       + '</div><p class="sf-fdetail-config__'
                       + seg[at + len(H8B_LIST_TAIL):])
                n += 1
    return head + seg + rest, n


def _h8b_transform(text):
    return _h8b_move(text)


def _h8b_partial(**flags):
    def f(text):
        return _h8b_move(text, **flags)
    return f


H8B_DETAIL = H8A_DETAIL      # a detail page: 21 in English, 21 in Chinese
H8B_RECORD = H8A_RECORD      # post 158 — the one record that stored a container


def _h8b_opts_expected(base, n, key):
    """How many options of one pool each page must end up with, read off the
    BASELINE's own dosage form rather than off the candidate.

    The numbers in this batch that cannot be fixed counts: soft chews keep eight
    shapes, tablets drop to five and five of the eight forms drop to four; and
    the packaging pool is seven on soft chews, six nowhere, five on tablets and
    four on the rest. A single expected total would be satisfied by the eight
    soft-chew shapes on a powder as long as something else was short by the same
    amount — which is exactly what the batch exists to stop being possible.
    """
    text = read(os.path.join(base, n + '.html'))
    form = _h8b_form(text)
    return len(H8B_POOLS[form][key]) if form else 0


def _h8b_shape_opts_expected(base, n):
    return _h8b_opts_expected(base, n, 'shape')


def _h8b_cont_opts_expected(base, n):
    return _h8b_opts_expected(base, n, 'packaging')


def _h8b_hoist_container(t):
    """Draw the container group BEFORE the shape group, which no count can see."""
    i = t.find('data-sf-config-group="shape"')
    j = t.find('data-sf-config-group="container"')
    k = t.find('data-sf-config-summary')
    if not (0 <= i < j < k):
        return t
    return t[:i] + t[j:k] + t[i:j] + t[k:]


BATCHES['h8b'] = {
    'name': "H8b — Shape and Container Type answer with the dosage form's own "
            "vocabulary, and the container group renders on every detail page",
    'mode': 'insert',
    'tokens': [
        ('?ver=2.10.74', '?ver=2.10.75'),                      # style.css
    ],
    # 128 edits: on the 22 pages whose dosage form calls this question something
    # other than "Shape", the group's own name and the box label go with it (22
    # + 22); every one of the 42 shape groups takes the pool's own options (42);
    # and the container group is rewritten on the one record that had one (1 x 2)
    # and inserted on the other forty (40).
    'applies': 128,
    'transform': _h8b_transform,
    'coverage': [
        ('?ver=2.10.74', 0),
        # The whole of the vocabulary this batch retires: the eight slugs of
        # sf_shape_library() and the seven of sf_container_library(), which were
        # the same eight and the same seven on all 42 detail pages. Each is a
        # lowercase library slug — the pool's spelling is the label, so the two
        # vocabularies are distinguishable by case alone and neither half of
        # that is an accident.
        ('value="bone"', 0),
        ('value="round"', 0),
        ('value="square"', 0),
        ('value="heart"', 0),
        ('value="star"', 0),
        ('value="paw"', 0),
        ('value="cylinder"', 0),
        ('value="oval"', 0),
        ('value="jar"', 0),
        ('value="pouch"', 0),
        ('value="tube"', 0),
        ('value="custom"', 0),
    ],
    'insertions': [
        ('?ver=2.10.75', 75),
        # One option per dosage form that no other form carries, so the eight
        # pools cannot have been collapsed back into one list: Oval is tablets,
        # Spiral is dental chews, Squeezable Gel is pastes, Microencapsulated is
        # powders, Amber is drops, Suspension is liquids, Softgel is fish oil —
        # and Bone, on twenty pages, is the one three forms share.
        ('name="sf-config-shape" value="Bone"', 20),
        ('name="sf-config-shape" value="Oval"', 6),
        ('name="sf-config-shape" value="Spiral"', 6),
        ('name="sf-config-shape" value="Squeezable Gel"', 4),
        ('name="sf-config-shape" value="Microencapsulated"', 6),
        ('name="sf-config-shape" value="Amber"', 4),
        ('name="sf-config-shape" value="Suspension"', 4),
        ('name="sf-config-shape" value="Softgel"', 4),
        # ...and the same for the packaging pool, form by form.
        ('name="sf-config-container" value="Aluminum Foil Pouch with Zipper"', 8),
        ('name="sf-config-container" value="Plastic Tube"', 4),
        ('name="sf-config-container" value="Stand-up Pouch"', 12),
        ('name="sf-config-container" value="Dropper Bottle"', 4),
        ('name="sf-config-container" value="Bottle with Cup"', 4),
        ('name="sf-config-container" value="Pump Bottle"', 4),
        ('name="sf-config-container" value="Custom"', 42),
    ],
    'counts': [
        # The reach, which is the half of the defect a per-form option list on
        # its own would not fix: 336 = 8 options x 42 pages.
        ('the shape group takes the dosage pool, not the global library',
         'name="sf-config-shape"', 336, 218),
        # ...and the group that used to wait for the record.
        ('the container group was on one record and is now on every detail page',
         'data-sf-config-group="container"', 2, 42),
        ('...its options being the dosage form\'s packaging pool',
         'name="sf-config-container"', 14, 198),
        # The name, on both of the carriers that spell it.
        ('the group name stops being the word Shape',
         'sf-fdetail-config__label">Shape<', 42, 20),
        ('...and becomes the pool\'s own word',
         'sf-fdetail-config__label">Appearance<', 0, 14),
        ('...which on pastes is Texture',
         'sf-fdetail-config__label">Texture<', 0, 4),
        ('...and on fish oil is Form',
         'sf-fdetail-config__label">Form<', 0, 4),
        ('the option list is announced with the same name as its group',
         'role="group" aria-label="Shape"', 42, 20),
        ('...and the container list says Container Type on every page',
         'role="group" aria-label="Container Type"', 2, 42),
        # 66 = (218 + 198) - (336 + 14): the two vocabularies differ by exactly
        # this much and the parameter column's option count moved by exactly it.
        ('every option the batch writes is a radio',
         'type="radio"', 536, 602),
        ('...inside a group', 'sf-fdetail-config__group', 110, 150),
        ('...and every one of them is a pick in an option list',
         'sf-fdetail-config__opt"', 530, 596),
        # The pool's own Custom row arrives already marked, so batch H8a\'s text
        # box opens on it without a second one being appended.
        ('the pools bring the Custom pick with them', 'value="Custom"', 64, 148),
        ('...and the box beside it',
         'data-sf-config-custom-input="', 108, 148),
        ('...carrying the marker the script reads',
         'data-sf-config-custom="1"', 108, 148),
        # Every attachment_id in both libraries is 0, so an option keeps a
        # picture only when the library spells its label — which is the route
        # the Site Settings pages promise, and the reason this count grows.
        ('an option with no picture yet is the dashed slot',
         'sf-fdetail-config__img--empty', 350, 416),
        ('the shape group stops asking for a box of its own',
         'aria-label="Your own Shape"', 42, 20),
        ('...and the container group starts', 
         'aria-label="Your own Container Type"', 2, 42),
        # 待办23/H8a's ladder is a price list and stays one — the batch's own
        # group is the one it republishes, and this says the neighbouring group
        # on the same two pages was not swept up with it.
        ('the ladder keeps its three breaks', 'sf-tier__dot', 6, 6),
    ],
    'unmoved': [
        ('the cookie banner', r'class="sf-cookie-banner"', 75),
        ('the float stack', r'class="sf-float-stack"', 75),
        ('the certificate dialog', r'sf-certmodal', 1),
        ('the navigation', r'wp-block-navigation', 75),
        # Which groups a record HAS comes from its own meta, and this batch
        # changed none of them: five pages carry a flavor picker, twenty a pack
        # size, all forty-two a unit weight, two a price ladder, and the
        # container group the batch republished was already on one of them.
        ('the flavor group', r'data-sf-config-group="flavor"', 2),
        ('the unit weight group', r'data-sf-config-group="weight"', 42),
        ('the pack size group', r'data-sf-config-group="pack"', 20),
        ('...and the ladder is still on the two pages that had one',
         r'data-sf-config-group="pricing"', 2),
        ('the gallery tabs', r'sf-gallery__tabs', 42),
        ('the side column', r'sf-fdetail2__side', 42),
        ('the spec sheet', r'sf-fdetail-specs__term', 42),
        ('the parameter list still ends on its summary',
         r'data-sf-config-summary', 42),
        ('the Send Inquiry button', r'data-sf-inquiry-open>Send Inquiry</a>', 42),
        ('the configurator itself', r'class="sf-fdetail-config"', 42),
    ],
    'per_page': [
        ('h1', r'<h1[ >]', 1),
        ('the new style token', r'style\.css\?ver=2\.10\.75', 1),
    ],
    'scoped': [
        # The group the batch republished is on every detail page and on no
        # other. `unmoved` cannot say this — 42 is also the count a single page
        # carrying all forty-two would produce.
        ('the container group is on every detail page and on no other',
         'data-sf-config-group="container"', H8B_DETAIL, 1),
        ('the picker the batch rewrote is on every detail page and on no other',
         'class="sf-fdetail-config"', H8B_DETAIL, 1),
    ],
    'corroborated': [
        # Read off the BASELINE's own dosage form, so neither number is taken
        # from the side being checked. A pool that quietly lost an option on one
        # page moves that page by one and no site total would notice.
        ('a shape option for every entry in the page\'s own pool',
         r'name="sf-config-shape" value="', _h8b_shape_opts_expected),
        ('...and a container option for every entry in its packaging pool',
         r'name="sf-config-container" value="', _h8b_cont_opts_expected),
    ],
    'order': [
        # Where the new group sits, which the main proof cannot see: with
        # `insert` the payload IS compared, but a page carrying the same two
        # groups in the other order is the same set of options under a title
        # that reads "Container Type" above "Shape".
        ('the container group follows the shape group on every detail page',
         'data-sf-config-group="shape"', 'data-sf-config-group="container"',
         H8B_DETAIL),
        ('...and both come before the summary that closes the column',
         'data-sf-config-group="container"', 'data-sf-config-summary', H8B_DETAIL),
    ],
    'h2_delta': None,
    'jsonld_delta': None,
    'sources': {
        'pools': 'inc/formula-pools.php',
        'admin': 'inc/formula-admin.php',
    },
    'reinject': ('an old library slug on the shape group fails coverage',
                 'formulas__calming-soft-chews.html',
                 '<div class="sf-fdetail-config__options" role="group" aria-label="Shape">',
                 '<label class="sf-fdetail-config__opt"><input class="sf-fdetail-config__input"'
                 ' type="radio" name="sf-config-shape" value="bone"></label>'),
    'delete': ("one page loses the container answer's Custom pick fails coverage",
               'formulas__calming-soft-chews.html',
               ' name="sf-config-container" value="Custom"'),
    'nc13_mode': 'sighted',
    'nc13_label': ('NC13 the insert direction SEES a container option renamed, '
                   'and coverage confirms it'),
    'matrix': [
        ('the tokens are not folded', {'tokens': []}, None),
        ('the group name is left as the word Shape',
         {'transform': _h8b_partial(label=False)}, None),
        ('the shape group keeps the library\'s eight soft-chew names',
         {'transform': _h8b_partial(shape=False)}, None),
        ('the container group is left exactly as it was',
         {'transform': _h8b_partial(container=False)}, None),
        ('the run count is declared one short', {'applies': 127}, None),
        ('nothing is applied at all',
         {'transform': (lambda t: (t, 0)), 'applies': 0}, None),
    ],
    'nc_source': [
        ('NC-src the source pass fails when the stylesheet keeps its old version',
         'style.css', 'Version: 2.10.75', 'Version: 2.10.74'),
        ('NC-src ...and when the enqueue keeps its own',
         'functions.php', "array(), '2.10.75');", "array(), '2.10.74');"),
        # The page went back to drawing the library instead of the pool.
        ('NC-src the source pass fails when the shape group reads the library again',
         'functions.php',
         "sf_formula_library_options(sf_formula_field_pool($form_slug, 'shape'), sf_shape_library())",
         'sf_shape_library()'),
        ('NC-src ...and when the container group reads it too',
         'functions.php',
         "sf_formula_library_options(sf_formula_field_pool($form_slug, 'packaging'), sf_container_library())",
         'sf_container_library()'),
        # The gate that kept the group off forty pages came back.
        ('NC-src ...and when the container group waits for the record again',
         'functions.php', 'if ($cont_opts) {', "if ($cont_opts && $container !== '') {"),
        # The spec sheet went back to naming its row by a literal.
        ('NC-src ...and when the spec sheet names its row by hand',
         'functions.php',
         "$rows[($shape_row !== '' ? $shape_row : 'Shape')] = esc_html($value);",
         "$rows['Shape'] = esc_html($value);"),
        # The pool renderer lost the two things it is for.
        ('NC-src ...and when the option stops asking the library for a picture',
         'inc/formula-pools.php',
         "'image' => sf_formula_pool_option_image($library, $label),", "'image' => '',"),
        ('NC-src ...and when the label is no longer matched case-insensitively',
         'inc/formula-pools.php', 'if ($spelt !== $label) {', 'if (false) {'),
        ('NC-src ...and when the pool\'s Custom row stops being marked',
         'inc/formula-pools.php',
         "if (0 === strcasecmp($label, 'Custom')) {", 'if (false) {'),
        # The publishing form, which owns the other end of the same vocabulary.
        ('NC-src the source pass fails when the form goes back to the library pool',
         'inc/formula-admin.php',
         "'pool' => 'packaging', 'keep_unknown' => true),",
         "'pool' => '_containers', 'keep_unknown' => true),"),
        ('NC-src ...and when a radio stops honouring keep_unknown',
         'inc/formula-admin.php',
         "if (!empty($spec['keep_unknown']) && '' !== (string) $raw && !in_array($raw, $opts, true)) {",
         'if (false) {'),
        ('NC-src ...and when the retired library resolver comes back',
         'inc/formula-admin.php',
         "/** Resolve a spec's option list: fixed array or dosage pool.",
         "function sf_formula_container_options() { return array(); }\n\n"
         "/** Resolve a spec's option list: fixed array or dosage pool."),
    ],
    'nc_page': [
        # Three claims the MAIN PROOF cannot see, all three owned by clauses
        # that live in `invariants`: the group that has to be on every detail
        # page, the order the two groups stand in, and the option count each
        # page's own pool dictates.
        ('NC-page the invariants fail when a detail page loses its container group',
         'formulas__calming-soft-chews.html',
         lambda t: t.replace('data-sf-config-group="container"',
                             'data-sf-config-group="containr"', 1)),
        ('NC-page ...and when the container group is drawn above the shape group',
         'formulas__calming-soft-chews.html', _h8b_hoist_container),
        ('NC-page ...and when a page is one shape option short of its pool',
         'formulas__calming-soft-chews.html',
         lambda t: t.replace('name="sf-config-shape" value="Paw"',
                             'nameX="sf-config-shape" value="Paw"', 1)),
    ],
    'nc_blind': ('formulas__calming-soft-chews.html', 'value="Custom"', 'value="Cust0m"'),
    'source': [
        ('style.css declares 2.10.75', 'css', r'(?m)^Version: 2\.10\.75$', True),
        # Read on the RAW bytes, not on the comment-blanked twin. The theme
        # header is itself inside a `/* */` block, so the blanked twin has it
        # erased and this claim could never fire — batch H8a shipped it that way
        # and it is corrected here, with the last NC-src below as its control.
        ('no 2.10.74 header survives', 'css', r'(?m)^Version: 2\.10\.74$', False),
        ('functions.php enqueues 2.10.75 for style.css', 'php',
         r"wp_enqueue_style\('sinofresh-style'[^;]*'2\.10\.75'", True),
        # --- the renderer reads the pool, not the library ---------------
        ('both groups resolve the record\'s dosage form the way the form does',
         'php',
         r"\$form_slug = function_exists\('sf_formula_record_form'\) \? "
         r"sf_formula_record_form\(\$post_id\) : '';", True),
        ('the shape group takes its name from the pool', 'php',
         r"\$shape_label = function_exists\('sf_formula_field_pool_label'\)", True),
        ('...and its options from the pool, with the library as the picture',
         'php',
         r"sf_formula_library_options\(sf_formula_field_pool\(\$form_slug, 'shape'\), "
         r"sf_shape_library\(\)\)", True),
        ('the container group reads the packaging pool', 'php',
         r"sf_formula_library_options\(sf_formula_field_pool\(\$form_slug, 'packaging'\), "
         r"sf_container_library\(\)\)", True),
        ('...and no longer waits for the record to own a value', 'php_live',
         r"if \(\$container !== '' && function_exists\('sf_container_library'\)\)",
         False),
        ('...which is what makes it render wherever the pool does', 'php',
         r"if \(\$cont_opts\) \{", True),
        ('the spec sheet\'s Shape row takes the same name', 'php',
         r"\$rows\[\(\$shape_row !== '' \? \$shape_row : 'Shape'\)\] = esc_html\(\$value\);",
         True),
        ('...so that row is named by no literal any more', 'php_live',
         r"\$rows\['Shape'\] = esc_html\(\$value\);", False),
        # --- the pool renderer ------------------------------------------
        ('the theme can match a pool label to a library picture', 'pools',
         r'function sf_formula_pool_option_image\(\$library, \$label\)', True),
        ('...case-insensitively, because both lists are hand-maintained', 'pools',
         r"\$spelt !== \$label", True),
        ('a pool renders as options whose VALUE is the LABEL', 'pools',
         r'function sf_formula_library_options\(\$pool, \$library\) \{', True),
        ('...which is what the publishing form posts', 'pools',
         r"'value' => \$label,\n\t\t\t'label' => \$label,", True),
        ('...each option asking the library for a picture', 'pools',
         r"'image' => sf_formula_pool_option_image\(\$library, \$label\),", True),
        ('...and the pool\'s own Custom row marked rather than appended', 'pools',
         r"if \(0 === strcasecmp\(\$label, 'Custom'\)\) \{", True),
        # --- the publishing form, the other reader of the same pools -----
        ('the publishing form reads the packaging pool for Container Type',
         'admin', r"'pool' => 'packaging', 'keep_unknown' => true\),", True),
        ('...and the retired library resolver is gone', 'admin_live',
         r'function sf_formula_container_options\(\)', False),
        ('...along with the branch that reached for it', 'admin_live',
         r"if \(\$spec\['pool'\] === '_containers'\) \{", False),
        ('a radio shows a stored value its pool no longer offers', 'admin',
         r"if \(!empty\(\$spec\['keep_unknown'\]\) && '' !== \(string\) \$raw && "
         r"!in_array\(\$raw, \$opts, true\)\) \{", True),
        ('...which is the value the record prints until it is re-saved', 'php',
         r"\$own = \(\$container !== '' && function_exists\('sinofresh_container_label'\)\)",
         True),
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


# ------------------------------------------------------------------- batch h8c

# The four cooperation-model cards on /services/ and the detail page each one
# points at. Both halves live in one table, so a card that links somewhere else
# cannot be declared without editing this line.
H8C_CARDS = (
    ('OEM &#8212; You Bring the Formula', '/services/oem/'),
    ('ODM &#8212; We Develop From Your Idea', '/services/odm/'),
    ('Contract Manufacturing &#8212; You Own the IP', '/services/contract-manufacturing/'),
    ('Private Label &#8212; Pick From Our Proven Formulas', '/services/private-label/'),
)

# The transform is handed a page's bytes and nothing else, and the two headings
# it must NOT touch stand verbatim on two other pages — the front page and its
# zh twin draw them in a two-card teaser band. The scope is therefore read off
# the page: `sf-keyfacts` is the overview's own table and sits on exactly one of
# the 75 pages (declared in `unmoved`). Unscoped, this transform would wrap the
# teaser's headings too, which is sabotage mutant #6 in the matrix.
H8C_SCOPE = 'sf-keyfacts'


def _h8c_transform(text):
    """Batch H8c's declared edit: the four cooperation-model cards on the
    overview become links to their own detail pages.

    The anchor goes INSIDE the existing <h3>, so the link text is the card's own
    name — a real label, one tab stop — while the theme's existing stretched-link
    rule (.sf-card__title-link::after, already carrying the front page's article
    cards) stretches the hit area over the whole card. Not one byte of CSS
    changes, and no JS is involved.
    """
    if H8C_SCOPE not in text:
        return text, 0
    n = 0
    for label, href in H8C_CARDS:
        old = '<h3 class="wp-block-heading">%s</h3>' % label
        new = ('<h3 class="wp-block-heading"><a class="sf-card__title-link" '
               'href="%s">%s</a></h3>' % (href, label))
        k = text.count(old)
        if k:
            text = text.replace(old, new)
            n += k
    return text, n


def _h8c_partial(skip=(), retarget=None):
    """Links all but `skip` of the cards, optionally pointing one of them at the
    wrong page. Sabotage matrix only."""
    def f(text):
        if H8C_SCOPE not in text:
            return text, 0
        n = 0
        for label, href in H8C_CARDS:
            if label in skip:
                continue
            if retarget and retarget[0] == label:
                href = retarget[1]
            old = '<h3 class="wp-block-heading">%s</h3>' % label
            new = ('<h3 class="wp-block-heading"><a class="sf-card__title-link" '
                   'href="%s">%s</a></h3>' % (href, label))
            k = text.count(old)
            if k:
                text = text.replace(old, new)
                n += k
        return text, n
    return f


def _h8c_unscoped(text):
    """The same transform with its scope removed: the front page's teaser cards
    get links too. Sabotage matrix only — the point of the mutant is that the
    scope is load-bearing rather than tidiness."""
    n = 0
    for label, href in H8C_CARDS:
        old = '<h3 class="wp-block-heading">%s</h3>' % label
        new = ('<h3 class="wp-block-heading"><a class="sf-card__title-link" '
               'href="%s">%s</a></h3>' % (href, label))
        k = text.count(old)
        if k:
            text = text.replace(old, new)
            n += k
    return text, n


def _h8c_swap_href(text):
    """Points the OEM card one slug over — a page edit neither the mask nor the
    h2 count can see. NC-page only."""
    return text.replace('href="/services/oem/"', 'href="/services/oem-2/"', 1)


def _h8c_link_one_more(text):
    """Turns a fifth heading on the overview into a card link, which is what a
    transform that walked the wrong set of headings would produce."""
    return text.replace('<h3 class="wp-block-heading">R&amp;D &amp; Formulation</h3>',
                        '<h3 class="wp-block-heading"><a class="sf-card__title-link"'
                        ' href="/services/oem/">R&amp;D &amp; Formulation</a></h3>', 1)


def _h8c_link_teaser(text):
    """Wraps the teaser's own heading, the thing the batch deliberately did not
    do. NC-page only."""
    return text.replace('<h3 class="wp-block-heading">OEM &#8212; You Bring the Formula</h3>',
                        '<h3 class="wp-block-heading"><a class="sf-card__title-link"'
                        ' href="/services/oem/">OEM &#8212; You Bring the Formula</a></h3>', 1)


# The four routes this batch creates, with the copy each one must carry. Read by
# the `new_pages` pass below.
H8C_NEW_ROUTES = {
    'services__oem.html': {
        'path':  '/services/oem/',
        'title': 'OEM Manufacturing &#8211; sinofresh',
        'crumb': 'OEM Manufacturing',
        'h1':    'OEM Manufacturing &#8212; You Bring the Formula',
    },
    'services__odm.html': {
        'path':  '/services/odm/',
        'title': 'ODM Development &#8211; sinofresh',
        'crumb': 'ODM Development',
        'h1':    'ODM Development &#8212; We Develop From Your Idea',
    },
    'services__contract-manufacturing.html': {
        'path':  '/services/contract-manufacturing/',
        'title': 'Contract Manufacturing &#8211; sinofresh',
        'crumb': 'Contract Manufacturing',
        'h1':    'Contract Manufacturing &#8212; You Own the IP',
    },
    'services__private-label.html': {
        'path':  '/services/private-label/',
        'title': 'Private Label &#8211; sinofresh',
        'crumb': 'Private Label',
        'h1':    'Private Label &#8212; Pick From Our Proven Formulas',
    },
}

# The region of /services/ the four new pages repeat verbatim: the commercial
# terms table and the two lines above it. Anchored on the content, not on the
# band's wrapper — the wrapper's background differs on purpose (the overview
# alternates its bands differently), so a claim written on the wrapper would be
# asserting the wrong object.
H8C_KEYFACTS_ANCHOR = 'Key Facts: MOQ, Lead Time, Payment &amp; Trade Terms'


def _h8c_keyfacts_region(text):
    """The overview's commercial-terms block, read off a SERVED page.

    Anchored on the rendered markup, not on a block comment: WordPress renders
    these pages with no `<!-- wp:` comments at all (measured 0 occurrences on
    the candidate's /services/), so an anchor written on `<!-- wp:heading`
    would return None on every page — and a claim that cannot find its region
    is not a claim. The region runs from the band's own <h2> to the table's
    closing tag, so it covers the heading, the lead line and the rows, and
    stops before the band wrapper (whose background differs by design — the
    overview alternates its bands differently from the four detail pages).
    """
    i = text.find(H8C_KEYFACTS_ANCHOR)
    if i < 0:
        return None
    s = text.rfind('<h2', 0, i)
    j = text.find('</table>', i)
    if s < 0 or j < 0:
        return None
    return text[s:j + len('</table>')]


def _h8c_norm_baseline(text, crumb):
    """Blank the route's OWN identity out of a render, by NAMING its carriers.

    The claim this feeds: before the batch, the theme drew all four routes with
    one generic page and nothing about the model appeared in it. What varies
    between the four renders is the route's identity, and the theme prints it in
    exactly four carriers, every one of them generated from the page being
    rendered: <title>, the BreadcrumbList's ListItem names, the breadcrumb's
    `aria-current` span, and the <h1>.

    Naming the carriers instead of replacing the name wherever it appears is not
    tidiness. On /services/private-label/ the name is ALSO a substring of a
    constant the Organization node publishes on all four pages —
    `"Private Label Pet Supplements"` — so a blanket replace takes the same
    bytes out of one page's constant only, and the normalisation MANUFACTURES
    the difference the claim exists to rule out. Measured: the blanket version
    put the four renders into two groups, three and one; this one puts them in
    one.

    The rest of the stripping is the route's own id and URL, which WordPress and
    wp_statistics print in the body class, in canonical/og:url, and in their own
    page-scoped analytics fields.
    """
    def blank_in(m):
        s = m.group(0)
        return s.replace(crumb, '\u00a7CRUMB\u00a7') if crumb in s else s

    for pat in (r'<title>[^<]*</title>',
                r'<h1[^>]*>[^<]*</h1>',
                r'aria-current="page">[^<]*</span>',
                r'"position":\d+,"name":"[^"]*"'):
        text = re.sub(pat, blank_in, text)

    t = text
    t = re.sub(r'pages/\d+', 'pages/\u00a7ID\u00a7', t)
    t = re.sub(r'\?p=\d+', '?p=\u00a7ID\u00a7', t)
    # The body class carries the page id too, and it is the FIRST difference the
    # four renders show up on — `pages/217` alone does not blank it.
    t = re.sub(r'page-id-\d+', 'page-id-\u00a7ID\u00a7', t)
    # wp_statistics prints its own page-scoped hit id and a per-page signature,
    # both of which differ between four routes that are otherwise the same page.
    t = re.sub(r'"source_id":\d+', '"source_id":\u00a7ID\u00a7', t)
    t = re.sub(r'"signature":"[0-9a-f]+"', '"signature":"\u00a7SIG\u00a7"', t)
    t = re.sub(r'services%2F[a-z\-]+%2F', '\u00a7ROUTE\u00a7', t)
    t = re.sub(r'/services/[a-z\-]+/', '\u00a7ROUTE\u00a7', t)
    t = re.sub(r'"services/[a-z\-]+"', '"\u00a7ROUTE\u00a7"', t)
    return t


def _h8c_neutral(text, crumb):
    """A render with the route's own identity and the per-render noise gone.

    Two claims are made on this form rather than on the raw bytes, and both need
    the same stripping: the four baseline renders were one page (so what still
    differs must be the route's identity, nothing else), and the four candidate
    renders share one document shell (so what still differs inside the shell
    must again be the route's identity). The per-render noise — Cloudflare's
    email-obfuscation hex, Gravity Forms' nonces — is what the site-wide mask
    already removes for the 75-page comparison; reusing it here keeps one
    definition of "noise" instead of a second one that could disagree.
    """
    return mask(_h8c_norm_baseline(text, crumb))[0]


def new_pages(decl, base_new, cand_new, base, cand, verbose=True):
    """The four routes the batch creates, proven against the state that had none.

    They cannot go through `main_proof`: that pass transforms the BASELINE and
    requires the result to equal the candidate, and the baseline render of these
    routes is a generic page. Making the transform build a whole page from one
    would mean teaching the gate to render, and a gate that renders is a gate
    that can agree with a broken renderer. So the claim is made here, on the two
    captures and on the served bytes alone:

      * BEFORE — the theme drew all four routes with ONE generic page: carrying
        none of the payload, and identical to each other once the route's own
        identity is blanked out.
      * AFTER — each carries its own payload (its own h1, its own third-level
        breadcrumb, its own three FAQ pairs), the four agree byte-for-byte
        wherever the batch says they must, and they disagree wherever they must.
    """
    spec = decl['new_pages']
    routes = spec['routes']
    ok = True
    rows = []

    def add(label, good, detail=''):
        nonlocal ok
        ok &= bool(good)
        rows.append({'label': label, 'ok': bool(good), 'detail': detail})
        if verbose:
            print('  %-62s %s%s' % (label, 'ok' if good else 'FAIL',
                                    ('  ' + detail) if detail else ''))

    bl, cd = {}, {}
    for name in sorted(routes):
        pb = os.path.join(base_new, name)
        pc = os.path.join(cand_new, name)
        if not (os.path.isfile(pb) and os.path.isfile(pc)):
            add('captured on both sides: %s' % name, False,
                'base=%s cand=%s' % (os.path.isfile(pb), os.path.isfile(pc)))
            continue
        bl[name] = read(pb)
        cd[name] = read(pc)
    if len(bl) != len(routes) or len(cd) != len(routes):
        return {'ok': False, 'rows': rows}

    # --- BEFORE -----------------------------------------------------------
    for name in sorted(routes):
        counts = {needle: bl[name].count(needle)
                  for needle in spec['baseline_absent']}
        add('before: %s carries none of the payload' % routes[name]['path'],
            all(v == 0 for v in counts.values()), str(counts))

    norms = {name: _h8c_neutral(bl[name], routes[name]['crumb'])
             for name in routes}
    uniq = len(set(norms.values()))
    add('before: the four routes were one generic page, re-titled per route',
        uniq == 1, 'distinct renders after blanking the route = %d' % uniq)

    # --- AFTER ------------------------------------------------------------
    for name in sorted(routes):
        r = routes[name]
        c = cd[name]
        bad = {}
        for needle, want in spec['candidate_counts']:
            got = c.count(needle)
            if got != want:
                bad[needle] = 'got %d want %d' % (got, want)
        add('after: %s carries the declared payload' % r['path'],
            not bad, str(bad) if bad else '')

        # Each name is asserted through the element that CARRIES it, not as a
        # bare substring: "OEM Manufacturing" is also inside the <title>, the
        # Service node's name, the h1 and the band-1 h2, which is why a bare
        # count runs to 5-7 and says nothing. These three needles each pick out
        # exactly one element, and each is the element the corresponding
        # schema node is generated from.
        ident = {}
        for key, needle in (('title', '<title>%s</title>' % r['title']),
                            ('h1', '>%s</h1>' % r['h1']),
                            ('crumb', 'aria-current="page">%s</span>' % r['crumb'])):
            got = c.count(needle)
            if got != 1:
                ident[key] = 'x%d' % got
        add('...and names itself exactly once in title, breadcrumb and h1',
            not ident, str(ident) if ident else '')

    for key in ('h1', 'crumb'):
        vals = [routes[n][key] for n in sorted(routes)]
        add('after: the four %s values are pairwise distinct' % key,
            len(set(vals)) == len(vals))

    # --- the four agree where they must ----------------------------------
    ref = None
    ref_path = os.path.join(cand, spec['keyfacts_ref'])
    if os.path.isfile(ref_path):
        ref = _h8c_keyfacts_region(read(ref_path))
    if ref is None:
        add('the commercial-terms region could not be read from %s'
            % spec['keyfacts_ref'], False)
    else:
        bad = []
        for name in sorted(routes):
            got = _h8c_keyfacts_region(cd[name])
            if got != ref:
                bad.append(name)
        add('the four pages repeat the overview\'s commercial terms verbatim',
            not bad, ','.join(bad))

    for label, s, e in spec['shell']:
        vals, unmatched = set(), 0
        for name in sorted(routes):
            t = _h8c_neutral(cd[name], routes[name]['crumb'])
            i = t.find(s)
            j = t.find(e, i + len(s)) if i >= 0 else -1
            if i < 0 or j < 0:
                unmatched += 1
                continue
            vals.add(t[i:j + len(e)])
        # `unmatched` is the half that matters: a shell claim whose anchors are
        # not on the page would otherwise compare two empty strings and pass.
        add('the %s is identical on all four' % label,
            unmatched == 0 and len(vals) == 1,
            'unmatched=%d distinct=%d' % (unmatched, len(vals)))

    # --- the JSON-LD each page must carry --------------------------------
    for name in sorted(routes):
        r = routes[name]
        blocks = []
        for raw in json_blocks(cd[name]):
            try:
                blocks.append(json.loads(raw))
            except ValueError:
                add('after: %s has a parseable JSON-LD block' % r['path'], False)
                blocks = None
                break
        if blocks is None:
            continue
        svc = [b for b in blocks if b.get('@type') == 'Service']
        crumb = [b for b in blocks if b.get('@type') == 'BreadcrumbList']
        faq = [b for b in blocks if b.get('@type') == 'FAQPage']
        good = (len(svc) == 1 and len(crumb) == 1 and len(faq) == 1)
        add('after: %s publishes one Service, one BreadcrumbList, one FAQPage'
            % r['path'], good,
            'service=%d breadcrumb=%d faq=%d' % (len(svc), len(crumb), len(faq)))
        if not good:
            continue
        # The Service node's name is the page's own H1 — the same
        # single-source-of-truth rule the parent page has always followed.
        add('...whose Service name is that page\'s own h1',
            svc[0].get('name') == r['h1'].replace('&#8212;', '\u2014'),
            repr(svc[0].get('name')))
        add('...and which points at the one Organization node',
            isinstance(svc[0].get('provider'), dict)
            and svc[0]['provider'].get('@id', '').endswith('/#organization'))
        items = crumb[0].get('itemListElement') or []
        add('...and whose breadcrumb has three levels ending on the page itself',
            len(items) == 3 and items[2].get('name') == r['crumb'],
            'levels=%d last=%r' % (len(items), items[2].get('name') if len(items) > 2 else None))
        add('...with the middle level pointing at the overview',
            len(items) > 1 and str(items[1].get('item', '')).endswith('/services/'),
            str(items[1].get('item', '')) if len(items) > 1 else '')
        qs = [q.get('name') for q in (faq[0].get('mainEntity') or [])]
        add('...and three FAQ answers, none of them a repeat',
            len(qs) == 3 and len(set(qs)) == 3, 'questions=%d' % len(qs))

        # The rail is why the toc whitelist had to be extended.
        add('...and the page loads the on-this-page rail',
            'assets/js/toc-nav.js' in cd[name])

    # --- and the overview now points at them -----------------------------
    svc_path = os.path.join(cand, spec['keyfacts_ref'])
    if os.path.isfile(svc_path):
        t = read(svc_path)
        got = {href: t.count('href="%s"' % href)
               for _, href in H8C_CARDS}
        add('the overview links all four models, each exactly once',
            all(v == 1 for v in got.values()), str(got))
    else:
        add('the overview page could not be read from %s' % spec['keyfacts_ref'],
            False)

    if verbose:
        print('  %s  new routes: the four pages exist, agree where declared, '
              'and the baseline had none' % ('PASS' if ok else 'FAIL'))
    return {'ok': ok, 'rows': rows}


BATCHES['h8c'] = {
    'name': "H8c — the four cooperation models get their own detail pages, and "
            "the overview's cards point at them",
    'mode': 'insert',
    'tokens': [
        ('?ver=2.10.75', '?ver=2.10.76'),                      # style.css
    ],
    # Four edits, all on the overview: one anchor per cooperation-model card.
    # The transform is scoped to the one page carrying `sf-keyfacts`, because the
    # front page and its zh twin stand two of these same headings in a teaser
    # band that this batch deliberately leaves alone.
    'applies': 4,
    'transform': _h8c_transform,
    'coverage': [
        ('?ver=2.10.75', 0),
        # These two headings are on the overview and on no other page, so they
        # can be asserted absent outright. The other two cannot: they also stand
        # (unlinked, and staying that way) on the front page and its zh twin —
        # see `counts`, where the move is 3 -> 2 rather than 1 -> 0.
        ('<h3 class="wp-block-heading">Contract Manufacturing &#8212; You Own the IP</h3>', 0),
        ('<h3 class="wp-block-heading">Private Label &#8212; Pick From Our Proven Formulas</h3>', 0),
    ],
    'insertions': [
        ('?ver=2.10.76', 75),
        ('<h3 class="wp-block-heading"><a class="sf-card__title-link"', 4),
    ],
    'counts': [
        # Zero on the baseline: no page referenced these routes before, because
        # the routes did not exist. The rows below are also what makes the four
        # links pointed at four DIFFERENT pages rather than four copies of one.
        ('the OEM card points at its own detail page', 'href="/services/oem/"', 0, 1),
        ('the ODM card points at its own', 'href="/services/odm/"', 0, 1),
        ('the Contract card points at its own',
         'href="/services/contract-manufacturing/"', 0, 1),
        ('the Private Label card points at its own',
         'href="/services/private-label/"', 0, 1),
        # The stretched-link class the theme already owns: three article cards on
        # the front page and three on its zh twin before, plus these four.
        ('the stretched-link class, already used by the front page\'s articles',
         'class="sf-card__title-link"', 6, 10),
        # Which headings were wrapped, stated on the heading itself. Two of the
        # four titles stand on three pages each, and only the overview's copy is
        # wrapped — 3 -> 2, not 1 -> 0. The other two are the overview's alone.
        ('the OEM heading as an unlinked card title',
         '<h3 class="wp-block-heading">OEM &#8212; You Bring the Formula</h3>', 3, 2),
        ('...and the ODM one, which the teaser band also carries',
         '<h3 class="wp-block-heading">ODM &#8212; We Develop From Your Idea</h3>', 3, 2),
        ('the Contract heading, which only the overview carries',
         '<h3 class="wp-block-heading">Contract Manufacturing &#8212; You Own the IP</h3>', 1, 0),
        ('...and the Private Label one likewise',
         '<h3 class="wp-block-heading">Private Label &#8212; Pick From Our Proven Formulas</h3>', 1, 0),
        # A heading tag stays a heading tag: the batch wraps four and creates
        # none, so the site's heading inventory is unchanged.
        ('the h3 headings the site draws', '<h3 class="wp-block-heading">', 839, 839),
        # The teaser band itself, by its own class.
        ('the card boxes on the site', 'sf-card--roomy', 34, 34),
    ],
    'unmoved': [
        ('the cookie banner', r'class="sf-cookie-banner"', 75),
        ('the float stack', r'class="sf-float-stack"', 75),
        ('the navigation', r'wp-block-navigation', 75),
        # The overview table that scopes the transform, and the reason that scope
        # is safe to read off a page: there is exactly one such page.
        ('the overview\'s commercial-terms table', r'sf-keyfacts', 1),
        ('the second-level breadcrumbs', r'sf-breadcrumb--d2', 15),
        ('...and the third-level ones only the dosage pages carry',
         r'sf-breadcrumb--d3', 16),
        ('the FAQ accordions', r'sf-faq__item', 67),
        ('the third-party card wall', r'sf-card ', 4),
        ('the dosage configurator', r'sf-fdetail-config', 42),
        ('the engagement band, shared with the front page', r'\bsf-oem\b', 3),
    ],
    'per_page': [
        ('h1', r'<h1[ >]', 1),
        ('the new style token', r'style\.css\?ver=2\.10\.76', 1),
    ],
    'scoped': [
        # NOT written on `class="sf-card__title-link"`: that class already had a
        # carrier before this batch (the front page's and /zh/'s three article
        # cards), so a per-page count of it over ALL pages would be 3 there and
        # 4 on the overview. The claim that is specific to this batch is the
        # combination of the two — the stretched-link class AND one of the four
        # new routes — and that combination has no carrier on any other page.
        ('the overview links all four models and no other page links any',
         r'href="/services/(oem|odm|contract-manufacturing|private-label)/"',
         lambda n: n == 'services', 4),
        ('...and the anchor pattern this batch writes exists only there',
         '<h3 class="wp-block-heading"><a class="sf-card__title-link"',
         lambda n: n == 'services', 4),
        # The front page and /zh/ draw two of the same card titles in their own
        # teaser band, unlinked. This is the claim that the batch stopped at the
        # overview, made on the served bytes rather than on intent.
        ('the teaser cards on the front page keep their unlinked headings',
         '<h3 class="wp-block-heading">OEM &#8212; You Bring the Formula</h3>',
         lambda n: n in ('root', 'zh'), 1),
    ],
    'corroborated': [
        # One link per card, with the CARD COUNT read off the baseline instead of
        # taken from the side being checked: a heading wrapped twice, or a fifth
        # heading wrapped, would move the candidate off the number of card boxes
        # the baseline actually drew on the overview.
        #
        # Everywhere else the class already had a carrier (three article cards on
        # the front page, three on /zh/), so the expectation there is the page's
        # own baseline count — the weaker claim that this batch did not move it,
        # which is the strongest one available on a page whose cards this batch
        # never touched.
        ('one link per cooperation-model card (cards counted on the baseline)',
         'class="sf-card__title-link"',
         lambda b, n: counts_of(
             read(os.path.join(b, n + '.html')),
             r'<div class="wp-block-group sf-card sf-card--roomy'
             if n == 'services' else r'class="sf-card__title-link"')),
    ],
    'order': [
        # With `insert` the payload IS compared, so this is not the H7c blind
        # spot — it is the cheaper half of the same claim: the four anchors stand
        # in the order the four cards are drawn, so no card can be pointed at a
        # neighbour's page while all four hrefs are still present.
        ('the OEM link comes before the ODM one',
         'href="/services/oem/"', 'href="/services/odm/"', lambda n: n == 'services'),
        ('...ODM before Contract Manufacturing',
         'href="/services/odm/"', 'href="/services/contract-manufacturing/"',
         lambda n: n == 'services'),
        ('...and Contract Manufacturing before Private Label',
         'href="/services/contract-manufacturing/"', 'href="/services/private-label/"',
         lambda n: n == 'services'),
    ],
    'h2_delta': None,
    # The overview's own Service node is byte-for-byte what it has always been —
    # the batch adds four entries to the lookup table in the hook without
    # touching the parent's. `None` here means the JSON-LD of all 75 pages is
    # required to be deep-equal, which is exactly that claim.
    'jsonld_delta': None,
    'sources': {
        'tpl_svc': 'templates/page-services.html',
        'tpl_oem': 'templates/page-oem.html',
        'tpl_odm': 'templates/page-odm.html',
        'tpl_con': 'templates/page-contract-manufacturing.html',
        'tpl_pri': 'templates/page-private-label.html',
    },
    'reinject': ('an unlinked card heading put back on the overview fails coverage',
                 'services.html',
                 '<a class="sf-card__title-link" href="/services/oem/">',
                 '<h3 class="wp-block-heading">OEM &#8212; You Bring the Formula</h3>'),
    'delete': ("the overview's Private Label link removed fails coverage",
               'services.html',
               '<a class="sf-card__title-link" href="/services/private-label/">'),
    'nc13_mode': 'sighted',
    'nc13_label': ('NC13 the insert direction SEES a card link renamed, '
                   'and coverage confirms it'),
    'matrix': [
        ('the tokens are not folded', {'tokens': []}, None),
        ('only three of the four cards link',
         {'transform': _h8c_partial(skip=('Private Label &#8212; Pick From Our Proven Formulas',)),
          'applies': 3}, None),
        ('the Contract card points at the ODM page',
         {'transform': _h8c_partial(
             retarget=('Contract Manufacturing &#8212; You Own the IP', '/services/odm/'))},
         None),
        ('the run count is declared one short', {'applies': 3}, None),
        ('nothing is applied at all',
         {'transform': (lambda t: (t, 0)), 'applies': 0}, None),
        # The scope is load-bearing: without it the front page's teaser cards get
        # links too, and the overview's own four are no longer the whole story.
        ('the transform reaches the front page\'s teaser band as well',
         {'transform': _h8c_unscoped, 'applies': 6}, None),
    ],
    # Each entry may carry a 5th element: the label of the source assertion the
    # mutation is supposed to break. Every entry here names one, because these
    # controls exist to show that a NAMED claim is load-bearing, and "some claim
    # went red" does not show that.
    'nc_source': [
        ('NC-src the source pass fails when the stylesheet keeps its old version',
         'style.css', 'Version: 2.10.76', 'Version: 2.10.75',
         'style.css declares 2.10.76'),
        ('NC-src ...and when the enqueue keeps its own',
         'functions.php', "array(), '2.10.76');", "array(), '2.10.75');",
         'functions.php enqueues 2.10.76 for style.css'),
        # The rail: without these four slugs the new pages get no dot rail, and
        # nothing about the served bytes would say so.
        ('NC-src ...and when the toc whitelist drops the new pages',
         'functions.php',
         "'services', 'oem', 'odm', 'contract-manufacturing', 'private-label'",
         "'services'",
         'the four new pages are on the on-this-page rail\'s whitelist'),
        # The schema: back to one hard-coded page.
        ('NC-src ...and when the Service schema hard-codes the overview again',
         'functions.php',
         "if (is_admin() || defined('REST_REQUEST') || !is_page()) {",
         "if (is_admin() || defined('REST_REQUEST')) {\n\t\treturn;\n\t}\n\tif (!is_page('services')) {",
         '...and no longer hard-codes the overview'),
        # The cards: every one of them, and the scope that keeps the teaser
        # alone.
        ('NC-src ...and when the OEM card stops linking',
         'templates/page-services.html',
         '<a class="sf-card__title-link" href="/services/oem/">', '<span>',
         'the OEM card is a stretched link to its own page'),
        ('NC-src ...and when the Contract card points one slug over',
         'templates/page-services.html',
         'href="/services/contract-manufacturing/"', 'href="/services/odm/"',
         '...and so are the Contract and Private Label cards'),
        ('NC-src ...and when the overview stops publishing its terms table',
         'templates/page-services.html',
         '<table class="sf-keyfacts">', '<table class="sf-terms">',
         'the overview still publishes that table itself'),
        # The detail pages themselves.
        ('NC-src ...and when a detail page drops to a two-level breadcrumb',
         'templates/page-oem.html', 'sf-breadcrumb--d3', 'sf-breadcrumb--d2',
         'every detail page opens at the third breadcrumb level'),
        ('NC-src ...and when a detail page stops naming its parent',
         'templates/page-odm.html',
         'sf-breadcrumb__crumb--mid" href="/services/">OEM/ODM Services</a>', '',
         'the ODM page\'s breadcrumb names the overview too'),
        # The needle is the Trade Terms ROW, not the <table> class: the assertion
        # this control owns is the verbatim-repeat claim, and a mutant that
        # renames the table's class leaves that row exactly where it was. An
        # earlier version of this entry did rename the class, and the control
        # went red for the honest reason that nothing it touched was asserted.
        ('NC-src ...and when a detail page loses its commercial terms',
         'templates/page-contract-manufacturing.html',
         '<tr><td>Trade Terms</td><td>FOB / CIF / EXW / DDP</td></tr>',
         '<tr><td>Trade Terms</td><td>FOB</td></tr>',
         '...which the other three repeat verbatim'),
        # The CLASS TOKEN, not the whole open tag: one of the three pairs in this
        # template is written with a bare ` open` attribute
        # (`class="wp-block-details sf-faq__item" open>`), so a needle that
        # demands `>` right after the closing quote matches only two of the
        # three — the mutant then leaves the assertion true and the control
        # reports "the sabotage survived". Measured, it cost one round.
        ('NC-src ...and when a detail page loses its FAQ markup',
         'templates/page-private-label.html',
         lambda t: t.replace('class="wp-block-details sf-faq__item"',
                             'class="wp-block-details"'),
         '',
         'every detail page carries the FAQ the schema generator reads'),
    ],
    'nc_page': [
        # Claims the MAIN PROOF cannot see, each owned by a clause that reads the
        # counts rather than the payload's position.
        ('NC-page the invariants fail when a card points at a page that is not there',
         'services.html', _h8c_swap_href),
        ('NC-page ...and when a fifth heading becomes a card link',
         'services.html', _h8c_link_one_more),
        ('NC-page ...and when the front page\'s teaser is linked as well',
         'root.html', _h8c_link_teaser),
    ],
    'nc_blind': ('services.html', 'class="sf-card__title-link"',
                 'class="sf-card__titlelink"'),
    'source': [
        ('style.css declares 2.10.76', 'css', r'(?m)^Version: 2\.10\.76$', True),
        # Read on the RAW bytes: the theme header lives inside a `/* */` block
        # and the comment-blanked twin has it erased, so this claim written on
        # `css_live` could never fire. (Batch H8a shipped exactly that.)
        ('no 2.10.75 header survives', 'css', r'(?m)^Version: 2\.10\.75$', False),
        ('functions.php enqueues 2.10.76 for style.css', 'php',
         r"wp_enqueue_style\('sinofresh-style'[^;]*'2\.10\.76'", True),
        # --- the overview links its four cards --------------------------
        ('the OEM card is a stretched link to its own page', 'tpl_svc',
         r'<a class="sf-card__title-link" href="/services/oem/">OEM &#8212; You Bring the Formula</a>',
         True),
        ('the ODM card is too', 'tpl_svc',
         r'<a class="sf-card__title-link" href="/services/odm/">ODM &#8212; We Develop From Your Idea</a>',
         True),
        ('...and so are the Contract and Private Label cards', 'tpl_svc',
         r'<a class="sf-card__title-link" href="/services/contract-manufacturing/">',
         True),
        ('...linking four different routes, not four copies of one', 'tpl_svc',
         r'<a class="sf-card__title-link" href="/services/private-label/">', True),
        # --- the four detail pages exist as templates -------------------
        # The templates open with a dark hero band, so the h1 carries the
        # card-white colour pair the theme already puts on the other heroes.
        ('the OEM template is titled with its own route name', 'tpl_oem',
         r'<h1 class="wp-block-heading has-card-white-color has-text-color">OEM Manufacturing &#8212; You Bring the Formula</h1>',
         True),
        ('...the ODM one likewise', 'tpl_odm',
         r'<h1 class="wp-block-heading has-card-white-color has-text-color">ODM Development &#8212; We Develop From Your Idea</h1>',
         True),
        ('...the Contract one likewise', 'tpl_con',
         r'<h1 class="wp-block-heading has-card-white-color has-text-color">Contract Manufacturing &#8212; You Own the IP</h1>',
         True),
        ('...and the Private Label one', 'tpl_pri',
         r'<h1 class="wp-block-heading has-card-white-color has-text-color">Private Label &#8212; Pick From Our Proven Formulas</h1>',
         True),
        ('every detail page names the overview in its breadcrumb', 'tpl_oem',
         r'sf-breadcrumb__crumb--mid" href="/services/">OEM/ODM Services</a>', True),
        ('...which is also what its BreadcrumbList is generated from', 'tpl_con',
         r'sf-breadcrumb__crumb--mid" href="/services/">OEM/ODM Services</a>', True),
        # The two elements the schema generator reads, asserted per page. Written
        # out rather than looped so that each page owns its own assertion: a
        # negative control edits ONE page, and a claim it cannot move on that one
        # page is a claim that is not being made.
        ('the ODM page\'s breadcrumb names the overview too', 'tpl_odm',
         r'sf-breadcrumb__crumb--mid" href="/services/">OEM/ODM Services</a>', True),
        ('...and so does the Private Label page\'s', 'tpl_pri',
         r'sf-breadcrumb__crumb--mid" href="/services/">OEM/ODM Services</a>', True),
        ('every detail page opens at the third breadcrumb level', 'tpl_oem',
         r'<nav class="sf-breadcrumb sf-breadcrumb--d3"', True),
        ('...the ODM page as well', 'tpl_odm',
         r'<nav class="sf-breadcrumb sf-breadcrumb--d3"', True),
        ('...the Contract page as well', 'tpl_con',
         r'<nav class="sf-breadcrumb sf-breadcrumb--d3"', True),
        ('...and the Private Label page', 'tpl_pri',
         r'<nav class="sf-breadcrumb sf-breadcrumb--d3"', True),
        ('every detail page carries the FAQ the schema generator reads', 'tpl_pri',
         r'<details class="wp-block-details sf-faq__item"', True),
        ('...and the commercial-terms table the overview publishes', 'tpl_oem',
         r'<table class="sf-keyfacts">', True),
        ('...which the other three repeat verbatim', 'tpl_con',
         r'<tr><td>Trade Terms</td><td>FOB / CIF / EXW / DDP</td></tr>', True),
        # The overview half of that claim. Without it "the four repeat the
        # overview's table verbatim" would only say the four agree with each
        # other, and the overview could have stopped publishing it.
        ('the overview still publishes that table itself', 'tpl_svc',
         r'<table class="sf-keyfacts">', True),
        ('the detail pages introduce no inline CSS of their own', 'tpl_odm',
         r'<style', False),
        # --- the two mechanisms the new pages need ---------------------
        ('the four new pages are on the on-this-page rail\'s whitelist', 'php',
         r"'services', 'oem', 'odm', 'contract-manufacturing', 'private-label'",
         True),
        ('the Service schema is keyed on the current page\'s slug', 'php',
         r"\$slug = \(string\) get_post_field\('post_name', get_queried_object_id\(\)\);",
         True),
        ('...and no longer hard-codes the overview', 'php_live',
         r"if \(!is_page\('services'\)\) \{", False),
        ('...carrying one name/description pair per page in the family', 'php',
         r"'contract-manufacturing' => array\(\s+'name'\s+=> 'Contract Manufacturing",
         True),
        ('...including the overview\'s own, unchanged', 'php',
         r"'name'\s+=> 'Pet Supplement OEM/ODM Manufacturing'", True),
    ],
    'new_pages': {
        'routes': H8C_NEW_ROUTES,
        'baseline_absent': ['sf-breadcrumb--d3', 'sf-keyfacts', 'sf-faq__item',
                            'sf-panel--3', 'sf-card__title-link'],
        'candidate_counts': [('sf-breadcrumb--d3', 1), ('sf-keyfacts', 1),
                             ('sf-faq__item', 3), ('<h2', 5), ('<h1', 1),
                             ('sf-panel--3', 1), ('sf-card__title-link', 0)],
        'keyfacts_ref': 'services.html',
        'shell': [
            # Anchored, and the pass fails if an anchor is missing — a shell
            # claim that compares two empty strings is not a claim. The regions
            # are cut from the NEUTRALISED render: the head legitimately carries
            # the page's own <title>/canonical and the analytics id, so on the
            # raw bytes "the shell is identical" is false by construction and
            # says nothing about whether four hand-written chromes got shipped.
            ('document shell above the first band', '</head>', '<section'),
            ('footer shell', '<footer', '</footer>'),
        ],
    },
}


# ---------------------------------------------------------------------- driver

def parse(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--batch', required=True, choices=sorted(BATCHES))
    ap.add_argument('--base')
    ap.add_argument('--cand')
    ap.add_argument('--aa', metavar='DIR2',
                    help='second capture taken on the SAME install as --cand')
    ap.add_argument('--base-new', metavar='DIR',
                    help='baseline capture of the routes this batch creates')
    ap.add_argument('--cand-new', metavar='DIR',
                    help='candidate capture of the routes this batch creates')
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
        if decl.get('new_pages'):
            # A pass with no call site is a pass that is silently green, so a
            # batch that declares new routes but is run without the two new-route
            # captures FAILS here rather than skipping the section.
            if not (args.base_new and args.cand_new):
                print('== new routes: the pages this batch creates ==')
                print('  FAIL  the batch declares new routes but --base-new / '
                      '--cand-new were not given')
                out['new_pages'] = {'ok': False,
                                    'rows': [{'label': 'new-route captures were '
                                                       'supplied', 'ok': False,
                                              'detail': 'missing --base-new/--cand-new'}]}
                ok = False
            else:
                print('== new routes: the pages this batch creates ==')
                r = new_pages(decl, args.base_new, args.cand_new,
                              args.base, args.cand)
                out['new_pages'] = r
                ok &= r['ok']

    print('\n%s  batch H7 gate (%s)' % ('PASS' if ok else 'FAIL', args.batch))
    if args.json:
        json.dump(out, open(args.json, 'w'), indent=1)
        print('  json -> %s' % args.json)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())

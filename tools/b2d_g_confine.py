#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch G — the six gates, run against two frozen 75-page captures.

What the batch does, and therefore what the gates have to be able to see:

  * the eight dosage pages gain a fourth .sf-facts-mini row
    (data-label="Packaging formats") — an INSERTION;
  * the 21+21 formula pages turn their gallery band into the left column of a
    two-column grid and gain a right column (intro / factsheet / CTA) —
    a RESTRUCTURE, neither a pure insertion nor a pure deletion;
  * style.css gains .sf-fdetail-media, and both files move one version number.

Six gates, each of which can fail on its own:

  0. the candidate capture really came from the pre-flight theme directory.
     Symmetrically, the two captures must NOT be byte-equal in their version
     tokens — a capture pair that agrees everywhere proves nothing.
  1. resource inventory: only style.css moved, on all 75 pages, with no page
     gaining or losing an asset (a SET change is not a version change).
  2. masked comparison against the expected-difference SET. A set, not a
     count: an unexpected difference and a missing one both fail.
  3. page-level confined proof, and HERE THE DIRECTION IS TWO DIFFERENT
     THINGS AT ONCE, which is the trap this batch carries:
       * 16 dosage pages — insertion direction (candidate minus the new row
         must be the base);
       * 42 formula pages — restructure direction (candidate, with the right
         column deleted, the left column lifted back to the top level and its
         class/style restored, must be the base).
     F1's note is the reason each direction is asserted separately rather
     than inferred from a count: getting a direction backwards produces a
     number that looks right.
     The values are never asserted from a local table. The factsheet's
     Certifications / Packaging and the intro's MOQ / Lead-time clauses are
     read out of the CANDIDATE DOSAGE PAGE's own row — the same single source
     sinofresh_formula_spec_cell() reads — so a drift between the row and the
     column fails here by construction.
  4. source-level reconstruction: undo the declared edits and the file must
     equal the pre-batch source again. The table cuts are recomputed here
     from markers rather than imported from the apply tool, so the two
     implementations have to agree.
  5. JSON-LD deep-equal on all 75 pages. This batch must not touch the
     schema: the intro deliberately re-words the schema's first sentence
     rather than sharing its function, so that a change here is a real
     finding and not a consequence of the design.

usage:
    python3 tools/b2d_g_confine.py --base-dir DIR --new-dir DIR \\
        --base-css F --new-css F --base-php F --new-php F \\
        --base-tpl-dir DIR --new-tpl-dir DIR [--report F]

Negative control: point --new-* at the base side. Every gate must report the
same thing the positive run does not: nothing moved, 58 pages that should
have differed and did not, and no restructure to undo. RC must be 1.
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# --diff-verbose turns this on; off keeps a failing run readable
DIFF_VERBOSE = False
sys.path.insert(0, HERE)
from b2d_s3_confine import masked, load  # noqa: E402  (shared mask set + loader)

VER_RE = re.compile(r'\?ver=[0-9A-Za-z._-]+')
VER_MASK = '?ver=MASK'
PAIR = re.compile(r'''(?:href|src)=["']([^"']+?)\?ver=([^"'&]+)''')
LD_RE = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)

DOSAGES = "soft-chews tablets powders pastes drops liquids fish-oil dental-chews".split()
FORMULAS = """bladder-support-powder calcium-phosphorus-tablets calming-soft-chews
digestive-soft-chews ear-care-drops hairball-remedy-paste joint-support-soft-chews
joint-support-tablets liquid-joint-support liquid-skin-coat multivitamin-tablets
natural-cleaning-dental-sticks nutrition-paste oral-care-dental-sticks
plaque-control-dental-chews probiotic-powder pumpkin-digestive-powder
pure-fish-oil-blend skin-coat-soft-chews urinary-care-drops wild-alaskan-salmon-oil
""".split()

PREFLIGHT_MARK = 'sinofresh-theme-preflight'
PREFLIGHT_DIR = '/wp-content/themes/sinofresh-theme-preflight/'
LIVE_DIR = '/wp-content/themes/sinofresh-theme/'

FROM_VER, TO_VER = '2.10.53', '2.10.54'

# --- page-side literals ---------------------------------------------------
# Measured on the renderer itself (do_blocks on the shipped block markup),
# not derived from the template text: the wrapper tags gain core's layout
# classes and the renderer's own newline arithmetic, and neither is visible
# in the source.
PAD_ATTR = ('style="padding-top:var(--wp--preset--spacing--80);'
            'padding-bottom:var(--wp--preset--spacing--80)"')
SEC_OUTER = ('<section class="wp-block-group sf-fdetail-media '
             'has-bg-light-background-color has-background is-layout-constrained '
             'wp-block-group-is-layout-constrained" ' + PAD_ATTR + '>')
INNER_OPEN = ('<div class="wp-block-group sf-fdetail-media__inner is-layout-flow '
              'wp-block-group-is-layout-flow">')
LEFT_CAND = ('<section id="gallery" class="wp-block-group sf-gallery '
             'sf-fdetail-media__left is-layout-flow wp-block-group-is-layout-flow">')
LEFT_BASE = ('<section id="gallery" class="wp-block-group sf-gallery '
             'has-bg-light-background-color has-background is-layout-constrained '
             'wp-block-group-is-layout-constrained" ' + PAD_ATTR + '>')
WRAPPERS_CAND = SEC_OUTER + '\n\n' + INNER_OPEN + '\n\n' + LEFT_CAND
# The renderer's own newline arithmetic, read off the do_blocks oracle rather
# than inferred: after the left column closes there are THREE newlines, then
# the aside; after </aside> the grid and the outer section close on '\n\n'
# boundaries and the section's own tail is another THREE newlines. Both ends
# carry the triple, so the undo has to take all three back — matching only two
# leaves one stray '\n' and every one of the 42 pages fails.
SIDE_RE = re.compile(r'\n\n\n<aside class="wp-block-group sf-fdetail-media__side'
                     r'[^>]*>[\s\S]*?</aside>')
CLOSERS_CAND = '\n\n</div>\n\n</section>\n\n\n'
CLOSERS_BASE = '\n\n\n'
# The batch also drops its own template comment between the B2D-S3 marker and
# the new section — the base predates it, so the undo takes it out again. The
# cut keeps the comment's trailing newline only (removing a leading one as well
# would eat a blank line the base does have). Pinned to the comment's opening
# words on purpose: reword the template and the undo stops firing, and the gate
# says so instead of passing quietly.
COMMENT_CUT_RE = re.compile(r'<!-- Batch G: media \+ facts[^>]*-->\n')

# the dosage page's new row, as it reaches the page (one line, no leading \n:
# the undo removes the line together with its own newline)
PKG_ROW_RE = re.compile(
    r'\n<div class="sf-facts-mini__item">'
    r'<span class="sf-facts-mini__label">Packaging</span> '
    r'<span class="sf-facts-mini__value" data-label="Packaging formats">'
    r'([^<]*)</span></div>')
MINI_RE = re.compile(r'<section class="sf-facts-mini">(.*?)</section>', re.S)
DETAIL_META_RE = re.compile(r'<p class="sf-formula-hero__meta">[^<]*</p>')
FORM_MARK_RE = re.compile(r'data-sf-form="([a-z-]+)"')
SIDE_PARTS = ('<p class="sf-fdetail-media__intro">',
              '<dl class="sf-fdetail-media__facts">',
              'class="sf-fdetail-media__cta"', 'href="/contact/"',
              'Request Sample')

LEAD = 'Typically 7\u201315 working days after packaging is ready'
CERTS = 'FDA, cGMP, ISO 9001, FSSC 22000, HACCP, BRC'

# --- source-side markers (the gate recomputes the cuts itself) -------------
G_CSS_BANNER = '/* G \u2014 formula detail: media + facts, two columns'
PHP_FUNCS_OPEN = '/**\n * The three facts buried in a formula\'s one-line sf_formula_specs value.'
PHP_SHORTCODE_TAIL = "add_shortcode('sf_formula_factsheet', 'sinofresh_formula_factsheet');\n"
PHP_SHORTCODE_ANCHOR = "add_shortcode('sf_formula_detail', 'sinofresh_formula_detail');\n"
PHP_INIT_ADD = "\t$formula_intro = '';\n"
PHP_MAP_OPEN = '\t\t/* Batch G: the media column\'s intro.'
PHP_MAP_KEEP = '\t}\n\t$map = array('
PHP_MAP_ROW = "\t\t'{{FORMULA_INTRO}}'   => $formula_intro,\n"
PHP_DOC_OPEN = ' *   {{FORMULA_INTRO}}    formula detail pages only'
PHP_JSONDOC = '/**\n * wp_json_encode() for the body of an inline <script>.'


def norm(html):
    """Shared masks first, then the version token — never the other way round."""
    return VER_RE.sub(VER_MASK, masked(html)[0])


def ver_map(html):
    return {os.path.basename(u).split('?')[0]: v for u, v in PAIR.findall(html)}


def ld_blocks(html):
    out = []
    for raw in LD_RE.findall(html):
        try:
            out.append(json.loads(raw.strip()))
        except Exception as exc:
            out.append({'__unparsed__': str(exc)})
    return out


def mini_values(block_html):
    """Every data-label'd value of one rendered/template .sf-facts-mini block."""
    out = {}
    for label in ('MOQ', 'Lead time', 'Certifications', 'Packaging formats'):
        m = re.search(r'data-label="%s"[^>]*>(.*?)</span>' % re.escape(label),
                      block_html, re.S)
        out[label] = re.sub(r'\s+', ' ', m.group(1)).strip() if m else None
    return out


def expected_diff_pages(names):
    """Every page served by a dosage template or by a formula post.

    Named from the capture rather than hard-coded so a page that stopped
    being fetched cannot quietly shrink the expectation: 8 + 8 dosage pages
    (en + /zh/) and 21 + 21 formula pages = 58.
    """
    return {n for n in names if re.match(r'^(zh__)?(products|formulas)__', n)}


def expected_packaging(tpl_dir, form):
    """The row value, rebuilt from the template's own configurator options.

    Deliberately a second implementation of the apply tool's rule (drop the
    trailing "Custom", close with ", or custom formats"): if the two ever
    disagree the rendered row and the configurator have drifted apart, and
    this gate is where that has to be visible.
    """
    path = os.path.join(tpl_dir, 'page-%s.html' % form)
    if not os.path.isfile(path):
        return None
    html = open(path, encoding='utf-8').read()
    m = re.search(r'<div class="configurator__group" data-group="packaging"[^>]*>'
                  r'(.*?)\n    </div>', html, re.S)
    if not m:
        return None
    values = re.findall(r'data-value="([^"]+)"', m.group(1))
    if not values:
        return None
    return ', '.join(values[:-1]) + ', or custom formats'


def dosage_reduce(name, base_norm, cand_norm, fails, say):
    """INSERTION direction: candidate minus the new row must be the base."""
    form = name.split('__')[-1]
    rows = PKG_ROW_RE.findall(cand_norm)
    if len(rows) != 1:
        fails.append('%s: expected exactly one Packaging formats row on the '
                     'candidate, found %d' % (name, len(rows)))
        say('    !! %s: Packaging rows %d' % (name, len(rows)))
        return False
    vals = mini_values(MINI_RE.search(cand_norm).group(1)) if MINI_RE.search(cand_norm) else {}
    if not vals.get('Packaging formats'):
        fails.append('%s: the row carries no value' % name)
        return False
    if vals.get('Lead time') != LEAD or vals.get('Certifications') != CERTS:
        fails.append('%s: the untouched rows drifted (lead %r / certs %r)'
                     % (name, vals.get('Lead time'), vals.get('Certifications')))
        say('    !! %s: untouched rows drifted' % name)
        return False
    if '<h2' in cand_norm.split('<section class="sf-facts-mini">')[-1][:600]:
        fails.append('%s: the row band carries a heading' % name)
    # the four rows that survive the undo must be the base's three, byte for
    # byte — that is what "only a row was added" means here.
    b = MINI_RE.search(base_norm)
    reduced = PKG_ROW_RE.sub('', cand_norm, count=1)
    if b and b.group(1) not in reduced:
        fails.append('%s: the base band is not intact after removing the row' % name)
        say('    !! %s: base band altered by the undo' % name)
        return False
    if 'Packaging formats' in reduced:
        fails.append('%s: the candidate still mentions the new row after the '
                     'undo' % name)
        return False
    for keep in ('<h2', 'Standard Formulas', 'configurator', 'Frequently Asked'):
        if keep in base_norm and keep not in reduced:
            fails.append('%s: the candidate lost %r' % (name, keep))
            say('    !! %s: candidate lost %r' % (name, keep))
            return False
    return reduced == base_norm


def detail_reduce(name, base_norm, cand_norm, dosage_vals, fails, say,
                  show_diff=False):
    """RESTRUCTURE direction: four declared steps, then byte equality.

      1. drop the batch's own template comment,
      2. delete the right column,
      3. lift the left column back to the top level (drop both wrapper opens,
         restore its class list and style),
      4. close the section the way the base closes it.
    """
    if base_norm.count(LEFT_BASE) != 1:
        fails.append('%s: the base page does not carry the expected gallery '
                     'section tag (%d)' % (name, base_norm.count(LEFT_BASE)))
        return False
    for lit, label in ((SEC_OUTER, 'outer section'), (INNER_OPEN, 'inner grid'),
                       (LEFT_CAND, 'left column'), (WRAPPERS_CAND, 'the three '
                        'wrapper tags in sequence')):
        n = cand_norm.count(lit)
        if n != 1:
            fails.append('%s: the candidate carries %d %s tag(s), expected 1'
                         % (name, n, label))
            say('    !! %s: %s x%d' % (name, label, n))
            return False
    sides = SIDE_RE.findall(cand_norm)
    if len(sides) != 1:
        fails.append('%s: expected exactly one right column, found %d'
                     % (name, len(sides)))
        return False
    aside = sides[0]
    for part in SIDE_PARTS:
        if part not in aside:
            fails.append('%s: the right column lacks %r' % (name, part))
            say('    !! %s: right column lacks %r' % (name, part))
            return False
    terms = re.findall(r'<dt class="sf-fdetail-media__term">([^<]*)</dt>'
                       r'<dd class="sf-fdetail-media__value">([^<]*)</dd>', aside)
    if len(terms) not in (4, 5):
        fails.append('%s: the factsheet has %d rows, expected 4 or 5'
                     % (name, len(terms)))
        say('    !! %s: factsheet rows %d' % (name, len(terms)))
        return False
    form = FORM_MARK_RE.findall(cand_norm)
    forms = set(form)
    if len(forms) != 1:
        fails.append('%s: cannot resolve its dosage form (data-sf-form %r)'
                     % (name, sorted(forms)))
        return False
    dv = dosage_vals.get(form[0], {})
    labels = [t[0] for t in terms]
    # The eleven two-segment records have no pack options, so their list is the
    # canonical order minus that row — never reordered, never a row that is not
    # in the canonical set.
    canon = ['Unit size', 'Pack options', 'Shelf life', 'Certifications',
             'Packaging']
    want_labels = [l for l in canon
                   if l in ('Unit size', 'Shelf life')
                   or (l == 'Pack options' and 'Pack options' in labels)
                   or (l == 'Certifications' and dv.get('Certifications'))
                   or (l == 'Packaging' and dv.get('Packaging formats'))]
    if labels != want_labels:
        fails.append('%s: the rows are %r, expected %r' % (name, labels, want_labels))
        say('    !! %s: rows %r (expected %r)' % (name, labels, want_labels))
        return False
    want = {'Certifications': dv.get('Certifications'),
            'Packaging': dv.get('Packaging formats')}
    for label, value in terms:
        if label in want:
            if want[label] is None:
                fails.append('%s: the dosage page yields no %s value to check '
                             'the column against' % (name, label))
                return False
            if value != want[label]:
                fails.append('%s: factsheet %s is %r, the dosage row says %r'
                             % (name, label, value, want[label]))
                say('    !! %s: %s %r != row %r' % (name, label, value, want[label]))
                return False
    if ('Packaging' in labels) != bool(dv.get('Packaging formats')):
        fails.append('%s: the Packaging row and the dosage row disagree about '
                     'existing' % name)
        return False
    # the intro's two clauses must quote the dosage row verbatim
    intro = re.search(r'<p class="sf-fdetail-media__intro">(.*?)</p>', aside, re.S)
    if not intro:
        fails.append('%s: no intro paragraph' % name)
        return False
    text = intro.group(1)
    if dv.get('MOQ') and ('Minimum order quantity: ' + dv['MOQ'] + '.') not in text:
        fails.append('%s: the intro does not quote the dosage MOQ' % name)
        say('    !! %s: intro MOQ mismatch' % name)
        return False
    if dv.get('Lead time') and ('Lead time: ' + dv['Lead time'] + '.') not in text:
        fails.append('%s: the intro does not quote the dosage lead time' % name)
        return False
    # the left column keeps everything it had: the heading, the four slides
    if '<h2 class="sf-gallery__title">' not in cand_norm:
        fails.append('%s: the gallery heading is gone' % name)
        return False
    if cand_norm.count('<figure class="sf-gallery__slide"') != 4:
        fails.append('%s: the gallery carries %d slides, expected 4'
                     % (name, cand_norm.count('<figure class="sf-gallery__slide"')))
        say('    !! %s: slides %d' % (name, cand_norm.count('<figure class="sf-gallery__slide"')))
        return False

    # --- the four undo steps ---------------------------------────────────
    s0 = COMMENT_CUT_RE.sub('', cand_norm, count=1)
    s1 = SIDE_RE.sub('', s0, count=1)
    s2 = s1.replace(WRAPPERS_CAND, LEFT_BASE, 1)
    s3 = s2.replace(CLOSERS_CAND, CLOSERS_BASE, 1)
    for a, b, what in ((cand_norm, s0, 'drop the batch comment'),
                       (s0, s1, 'delete the right column'),
                       (s1, s2, 'lift the left column back'),
                       (s2, s3, 'close the section the base way')):
        if a == b:
            fails.append('%s: the undo step %r did not fire' % (name, what))
            say('    !! %s: undo step is a no-op — %s' % (name, what))
            return False
    if 'sf-fdetail-media' in s3:
        fails.append('%s: the undid page still mentions sf-fdetail-media' % name)
        return False
    if s3 != base_norm:
        k = 0
        m = min(len(s3), len(base_norm))
        while k < m and s3[k] == base_norm[k]:
            k += 1
        say('    !! %s: undid page differs (undone %d B, base %d B, first diff @%d)'
            % (name, len(s3), len(base_norm), k))
        if show_diff:
            say('          undone:', repr(s3[max(0, k - 90):k + 60]))
            say('          base  :', repr(base_norm[max(0, k - 90):k + 60]))
    return s3 == base_norm


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base-dir', required=True)
    ap.add_argument('--new-dir', required=True)
    ap.add_argument('--base-css', required=True)
    ap.add_argument('--new-css', required=True)
    ap.add_argument('--base-php', required=True)
    ap.add_argument('--new-php', required=True)
    ap.add_argument('--base-tpl-dir', required=True)
    ap.add_argument('--new-tpl-dir', required=True)
    ap.add_argument('--from-ver', default=FROM_VER)
    ap.add_argument('--to-ver', default=TO_VER)
    ap.add_argument('--allow-live-capture', action='store_true',
                    help='gate 0 escape hatch, for an A/A self-test of the '
                         'gate itself; never for a real candidate')
    ap.add_argument('--report', default=None)
    ap.add_argument('--diff-verbose', action='store_true',
                    help='print the first diverging byte pair when the '
                         'page-level undo does not reproduce the base')
    args = ap.parse_args()

    global DIFF_VERBOSE
    DIFF_VERBOSE = bool(args.diff_verbose)

    lines, fails = [], []

    def say(*parts):
        s = ' '.join(str(p) for p in parts)
        print(s)
        lines.append(s)

    say('=' * 78)
    say('Batch G — gates for the two-column media band on the 42 formula pages')
    say('          and the Packaging formats row on the 8 dosage pages, '
        '%s -> %s' % (args.from_ver, args.to_ver))
    say('=' * 78)

    base, new = load(args.base_dir), load(args.new_dir)
    say('\n[0] inputs, and proof that the candidate is the candidate')
    say('    base dir %s : %d pages' % (args.base_dir, len(base)))
    say('    new  dir %s : %d pages' % (args.new_dir, len(new)))
    if len(base) != 75 or len(new) != 75:
        fails.append('expected 75 pages on each side, got %d / %d'
                     % (len(base), len(new)))
    marked = [n for n in new if PREFLIGHT_MARK in new[n]]
    say('    candidate pages carrying the pre-flight theme directory: %d/%d'
        % (len(marked), len(new)))
    if marked and len(marked) != len(new) and not args.allow_live_capture:
        fails.append('%d candidate page(s) do not mention the pre-flight theme '
                     'directory — this capture is not the candidate'
                     % (len(new) - len(marked)))
        say('    !! e.g. %s' % ', '.join(sorted(set(new) - set(marked))[:5]))
    elif not marked and not args.allow_live_capture:
        fails.append('no candidate page mentions the pre-flight theme '
                     'directory — this capture is not the candidate')
    say('    live dir mention on the candidate side: %d page(s) (the pre-flight '
        'copy rewrites them all)' % sum(1 for n in new if LIVE_DIR in new[n]))
    expect = expected_diff_pages(base.keys())
    say('    expected to differ: %d page(s) — 8 dosage + 8 /zh/ dosage '
        '+ 21 formula + 21 /zh/ formula' % len(expect))

    # ---- gate 1: resource inventory -------------------------------------
    say('\n[1] resource inventory (which cache tokens moved?)')
    moved, set_changed = {}, []
    for name in sorted(base):
        if name not in new:
            fails.append('page %s missing on the new side' % name)
            continue
        vb, vn = ver_map(base[name]), ver_map(new[name])
        if set(vb) != set(vn):
            set_changed.append(name)
            continue
        for asset in sorted(vb):
            if vb[asset] != vn[asset]:
                moved.setdefault(asset, {}).setdefault(
                    (vb[asset], vn[asset]), []).append(name)
    if not moved:
        fails.append('NOTHING moved — the two directories have identical '
                     'version tokens, so this gate proved nothing (is --new '
                     'pointing at base?)')
    for asset, transitions in sorted(moved.items()):
        for (vbase, vnew), pages in sorted(transitions.items()):
            say('    %-18s %s -> %-9s on %d page(s)'
                % (asset, vbase, vnew, len(pages)))
            if asset != 'style.css':
                fails.append('unexpected asset moved: %s %s->%s'
                             % (asset, vbase, vnew))
            if (vbase, vnew) != (args.from_ver, args.to_ver):
                fails.append('style.css moved %s->%s, expected %s->%s'
                             % (vbase, vnew, args.from_ver, args.to_ver))
            if len(pages) != 75:
                fails.append('style.css moved on %d pages, expected 75'
                             % len(pages))
    say('    asset SET changed on %d page(s) (must be 0)' % len(set_changed))
    if set_changed:
        fails.append('asset set changed on: %s' % ', '.join(set_changed[:6]))

    # ---- gate 2: masked comparison --------------------------------------
    say('\n[2] masked comparison of the 75 pages (?ver= folded, nonces and the '
        'pre-flight directory masked)')
    diff, same = [], []
    for name in sorted(base):
        if name not in new:
            continue
        (diff if norm(base[name]) != norm(new[name]) else same).append(name)
    say('    differ    %d page(s)' % len(diff))
    say('    identical %d page(s)' % len(same))
    for name in sorted(set(diff) - expect):
        say('    !! %s differs but was not expected to' % name)
        fails.append('%s differs but was not expected to' % name)
    for name in sorted(expect - set(diff)):
        say('    !! %s should have differed and did not' % name)
        fails.append('%s should have differed and did not' % name)

    # ---- gate 3: page-level confined proof -------------------------------
    say('\n[3] page-level confined proof — TWO directions, asserted separately')
    say('    dosage pages (16): INSERTION — candidate minus the new row must '
        'be the base.')
    say('    formula pages (42): RESTRUCTURE — delete the right column, lift '
        'the left one back,')
    say('    restore its class/style; that must be the base. Values are '
        'cross-read from the')
    say('    candidate dosage page\'s own row, the same source spec_cell reads.')
    dosage_vals = {}
    for form in DOSAGES:
        pname = 'products__%s.html' % form
        if pname not in new:
            fails.append('the capture lacks the dosage page %s' % pname)
            continue
        m = MINI_RE.search(norm(new[pname]))
        dosage_vals[form] = mini_values(m.group(1)) if m else {}
    # cross-source: the rendered row against the template's own configurator
    say('    row value vs the template\'s configurator options:')
    for form in DOSAGES:
        want = expected_packaging(args.new_tpl_dir, form)
        got = dosage_vals.get(form, {}).get('Packaging formats')
        if want is None:
            fails.append('%s: no packaging option set in the candidate template'
                         % form)
            say('        %-14s !! template has no packaging group' % form)
            continue
        ok = want == got
        say('        %-14s %s  %s' % (form, 'ok ' if ok else '!! ',
                                      (got or '')[:66]))
        if not ok:
            fails.append('%s: the rendered row is %r, the template\'s options '
                         'reduce to %r' % (form, got, want))
    confined = 0
    per_kind = {'dosage': 0, 'detail': 0}
    for name in sorted(expect):
        if name not in new or name not in base:
            continue
        b, n = norm(base[name]), norm(new[name])
        if re.match(r'^(zh__)?products__', name):
            ok = dosage_reduce(name, b, n, fails, say)
            kind = 'dosage'
        else:
            ok = detail_reduce(name, b, n, dosage_vals, fails, say,
                               show_diff=DIFF_VERBOSE)
            kind = 'detail'
        if ok:
            confined += 1
            per_kind[kind] += 1
        elif not any(f.startswith(name) for f in fails):
            fails.append('%s: undoing the batch does not reproduce the base'
                         % name)
    say('    %d/%d page(s) reduce to the base byte-for-byte '
        '(dosage %d/16, formula %d/42)'
        % (confined, len(expect), per_kind['dosage'], per_kind['detail']))
    if per_kind['dosage'] != 16:
        fails.append('only %d/16 dosage pages reduced' % per_kind['dosage'])
    if per_kind['detail'] != 42:
        fails.append('only %d/42 formula pages reduced' % per_kind['detail'])

    # ---- gate 4: source-level reconstruction -----------------------------
    say('\n[4] source reconstruction — undo the declared edits, compare to the '
        'pre-batch source')
    bphp = open(args.base_php, encoding='utf-8').read()
    nphp = open(args.new_php, encoding='utf-8').read()
    undone = nphp

    def cut_between(start_mark, end_mark, include_start, include_end, label):
        """Remove the insert between two markers.

        include_start / include_end say whether each marker's OWN bytes go with
        the insert. Three of the four cuts leave the closing marker in place
        (it is shipped code the batch was inserted in front of); only the
        factsheet cut takes its closing marker, because that line is the
        insert's own tail. Getting a flag backwards deletes a line that has to
        survive, and the byte comparison at the end is what catches it.

        Every cut is looked up in the WORKING string: the offsets move as the
        cuts come out, and a stale offset slices the wrong bytes while still
        leaving a file of roughly the right size.
        """
        nonlocal undone
        i = undone.find(start_mark)
        if i < 0:
            fails.append('%s: start marker not found' % label)
            say('    functions.php            !! %s start marker missing' % label)
            return
        j = undone.find(end_mark, i)
        if j < 0:
            fails.append('%s: end marker not found after the start' % label)
            say('    functions.php            !! %s end marker missing' % label)
            return
        i += 0 if include_start else len(start_mark)
        j += len(end_mark) if include_end else 0
        undone = undone[:i] + undone[j:]

    if undone.count(args.to_ver) != 1:
        fails.append('php/version: %r occurs %d time(s), expected 1'
                     % (args.to_ver, undone.count(args.to_ver)))
        say('    functions.php            !! php/version literal count != 1')
    undone = undone.replace(args.to_ver, args.from_ver, 1)
    for label, lit in (('php/init', PHP_INIT_ADD), ('php/map-row', PHP_MAP_ROW)):
        if undone.count(lit) != 1:
            fails.append('%s: %r occurs %d time(s), expected 1'
                         % (label, lit, undone.count(lit)))
            say('    functions.php            !! %s literal count != 1' % label)
        undone = undone.replace(lit, '', 1)
    cut_between(PHP_FUNCS_OPEN, PHP_JSONDOC, True, False, 'php/functions')
    cut_between(PHP_SHORTCODE_ANCHOR, PHP_SHORTCODE_TAIL, False, True,
                'php/factsheet')
    cut_between(PHP_MAP_OPEN, PHP_MAP_KEEP, True, False, 'php/map-compose')
    cut_between(PHP_DOC_OPEN, ' *   {{LAST_UPDATED}}', True, False,
                'php/docblock')
    same_php = undone == bphp
    say('    %-24s base %7d / new %7d / undone %7d  undone==base:%s'
        % ('functions.php', len(bphp.encode()), len(nphp.encode()),
           len(undone.encode()), 'YES' if same_php else 'NO'))
    if not same_php:
        fails.append('functions.php: reconstruction does not reproduce the base '
                     'byte-for-byte')
        k = next((q for q in range(min(len(undone), len(bphp)))
                  if undone[q] != bphp[q]), min(len(undone), len(bphp)))
        say('        first mismatch @%d' % k)
        say('          undone:', repr(undone[max(0, k - 70):k + 40]))
        say('          base  :', repr(bphp[max(0, k - 70):k + 40]))
    for keep in ('sinofresh_formula_spec_cell', '{{FORMULA_META}}',
                 'sinofresh_formula_detail', 'sinofresh_formula_gallery'):
        if keep not in nphp:
            fails.append('functions.php: the candidate lost %r' % keep)

    # style.css: the G block is appended last, so the undo runs to EOF.
    bcss = open(args.base_css, encoding='utf-8').read()
    ncss = open(args.new_css, encoding='utf-8').read()
    k = ncss.find(G_CSS_BANNER)
    if k < 0:
        fails.append('style.css: the G banner is missing')
        say('    style.css                !! G banner missing')
    else:
        cut = ncss[k - 1:]
        if not cut.startswith('\n/* G ') or not cut.endswith('}\n'):
            fails.append('style.css: the G block does not start/end where an '
                         'append would put it')
        if cut.count('.sf-fdetail-media__inner') < 3:
            fails.append('style.css: the G block is not the expected block')
        undone_css = ncss[:k - 1].replace('Version: ' + args.to_ver,
                                          'Version: ' + args.from_ver, 1)
        same_css = undone_css == bcss
        say('    %-24s base %7d / new %7d / undone %7d  undone==base:%s (+%d B)'
            % ('style.css + G block', len(bcss.encode()), len(ncss.encode()),
               len(undone_css.encode()), 'YES' if same_css else 'NO',
               len(ncss.encode()) - len(bcss.encode())))
        if not same_css:
            fails.append('style.css: the G block undo does not reproduce the base')
            q = next((i for i in range(min(len(undone_css), len(bcss)))
                      if undone_css[i] != bcss[i]), min(len(undone_css), len(bcss)))
            say('        first mismatch @%d' % q)
            say('          undone:', repr(undone_css[max(0, q - 70):q + 40]))
            say('          base  :', repr(bcss[max(0, q - 70):q + 40]))

    # the eight dosage templates: drop the line that carries the new data-label
    for form in DOSAGES:
        label = 'templates/page-%s.html' % form
        braw = open(os.path.join(args.base_tpl_dir, 'page-%s.html' % form),
                    encoding='utf-8').read()
        nraw = open(os.path.join(args.new_tpl_dir, 'page-%s.html' % form),
                    encoding='utf-8').read()
        hit = [ln for ln in nraw.split('\n') if 'data-label="Packaging formats"' in ln]
        problems = []
        if 'sf-facts-mini' not in braw:
            problems.append('the base template has no facts row at all')
        if len(hit) != 1:
            problems.append('the candidate carries %d Packaging lines, expected 1'
                            % len(hit))
        if problems:
            for p in problems:
                fails.append('%s: %s' % (label, p))
                say('    %-24s !! %s' % (label, p))
            continue
        line = hit[0]
        if '<h2' in line or '<h3' in line:
            problems.append('the new line carries a heading')
        if 'data-label="Packaging formats"' not in line:
            problems.append('the new line is not the labelled one')
        # the row and its own newline: the row was spliced in at the close of
        # the band, so removing "<row>\n" puts </section> back on the line
        # directly under the Certifications row, where the base had it.
        undone = nraw.replace(line + '\n', '', 1)
        same_file = undone == braw
        say('    %-24s base %7d / new %7d / undone %7d  undone==base:%s (+%d B)'
            % (label, len(braw.encode()), len(nraw.encode()),
               len(undone.encode()), 'YES' if same_file else 'NO',
               len(nraw.encode()) - len(braw.encode())))
        if problems:
            for p in problems:
                fails.append('%s: %s' % (label, p))
                say('    %-24s !! %s' % (label, p))
        if not same_file:
            fails.append('%s: reconstruction does not reproduce the base '
                         'byte-for-byte' % label)
            q = next((i for i in range(min(len(undone), len(braw)))
                      if undone[i] != braw[i]), min(len(undone), len(braw)))
            say('        first mismatch @%d' % q)
            say('          undone:', repr(undone[max(0, q - 70):q + 40]))
            say('          base  :', repr(braw[max(0, q - 70):q + 40]))

    # single-sf_formula.html: cut the batch's own region and drop the base's
    # back in — the region is read out of the base file, not restated here.
    label = 'templates/single-sf_formula.html'
    braw = open(os.path.join(args.base_tpl_dir, 'single-sf_formula.html'),
                encoding='utf-8').read()
    nraw = open(os.path.join(args.new_tpl_dir, 'single-sf_formula.html'),
                encoding='utf-8').read()
    m = re.search(r'<!-- wp:group \{"tagName":"section","anchor":"gallery",'
                  r'[\s\S]*?\[sf_formula_gallery\][\s\S]*?\n</section>\n'
                  r'<!-- /wp:group -->', braw)
    i = nraw.find('<!-- Batch G:')
    j = nraw.find('\n\n<!-- Block 3: long copy', i) if i >= 0 else -1
    if not m or i < 0 or j < 0:
        fails.append('%s: cannot locate the batch region (base marker %s, '
                     'candidate %s..%s)' % (label, bool(m), i, j))
        say('    %-24s !! region not locatable' % label)
    else:
        undone = nraw[:i] + m.group(0) + nraw[j:]
        same_file = undone == braw
        say('    %-24s base %7d / new %7d / undone %7d  undone==base:%s (+%d B)'
            % (label, len(braw.encode()), len(nraw.encode()),
               len(undone.encode()), 'YES' if same_file else 'NO',
               len(nraw.encode()) - len(braw.encode())))
        if not same_file:
            fails.append('%s: reconstruction does not reproduce the base '
                         'byte-for-byte' % label)
            q = next((i for i in range(min(len(undone), len(braw)))
                      if undone[i] != braw[i]), min(len(undone), len(braw)))
            say('        first mismatch @%d' % q)
            say('          undone:', repr(undone[max(0, q - 70):q + 40]))
            say('          base  :', repr(braw[max(0, q - 70):q + 40]))
        for needle in ('[sf_formula_gallery]', '{{FORMULA_INTRO}}',
                       '[sf_formula_factsheet]', 'sf-fdetail-media__cta'):
            if needle not in nraw:
                fails.append('%s: the candidate lacks %r' % (label, needle))
        if nraw.count('[sf_formula_gallery]') != 1:
            fails.append('%s: the gallery shortcode is not defined exactly once'
                         % label)

    # ---- gate 5: JSON-LD deep-equal --------------------------------------
    say('\n[5] JSON-LD deep-equal (decoded structures, not masked text)')
    ld_bad, ld_pages = [], 0
    for name in sorted(base):
        if name not in new:
            continue
        lb, ln = ld_blocks(base[name]), ld_blocks(new[name])
        ld_pages += 1
        if lb != ln:
            ld_bad.append(name)
            if len(ld_bad) <= 2:
                say('    DIFF %s' % name)
                say('      base: %s' % json.dumps(lb, ensure_ascii=False)[:300])
                say('      new : %s' % json.dumps(ln, ensure_ascii=False)[:300])
    say('    identical %d/%d page(s)' % (ld_pages - len(ld_bad), ld_pages))
    if ld_pages == 0:
        fails.append('no pages compared in gate 5')
    if ld_bad:
        fails.append('%d page(s) differ in JSON-LD: %s'
                     % (len(ld_bad), ', '.join(ld_bad[:6])))

    say('\n' + '=' * 78)
    if fails:
        say('FAIL — %d problem(s):' % len(fails))
        for f in fails:
            say('  * %s' % f)
    else:
        say('PASS — only style.css\'s version token moved, on all 75 pages, '
            'with no asset added or lost;')
        say('       %d pages differ and they are exactly the expected set;'
            % len(expect))
        say('       all 16 dosage pages reduce to the base once the new row is '
            'deleted, and all')
        say('       42 formula pages reduce once the right column is deleted and '
            'the left one is')
        say('       lifted back; every value in the column cross-checks against '
            'the dosage row;')
        say('       the eleven source files rebuild to their pre-batch bytes;')
        say('       75/75 pages byte-identical in decoded JSON-LD.')
    say('=' * 78)

    if args.report:
        os.makedirs(os.path.dirname(args.report) or '.', exist_ok=True)
        with open(args.report, 'w', encoding='utf-8') as fh:
            fh.write('\n'.join(lines) + '\n')
        print('\nreport -> %s' % args.report)
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# ARCHIVED 2026-09-22 (batch H7a) — DO NOT MAINTAIN.
#
# This tool lists the gallery band's heading, '<h2 class="sf-gallery__title">',
# among the strings it requires to survive (line ~273, its "keep" tuple).
# Batch H7a deleted that heading, so this tool now fails on any capture taken
# from H7a onward. That failure is expected and is not a regression.
#
# It is left byte-for-byte as it was, on purpose. A gate edited to agree with
# the change it was written to validate stops being a gate; the assertion it
# made at the time is the honest record, and it is the assertion that dates it.
# Its job belongs to tools/b2d_h7_gate.py from batch H7a on.
# ---------------------------------------------------------------------------
"""Batch C — the six gates, run against two 75-page captures.

What the batch does, and therefore what the gates have to be able to see:

  * 42 pages (21 formulas + 21 /zh/ formulas) gain a FAQ band between the
    closed composition block and the related-formulas grid — a core group
    carrying .sf-fdetail .sf-fdetail-faq, a core heading, and the accordion the
    [sf_formula_faq] shortcode returns: .sf-faq with nine <details>;
  * the same 42 pages gain one FAQPage <script> in <head>, ahead of the
    breadcrumb's;
  * NOTHING else moves. style.css and functions.php keep their version tokens:
    the batch ships no CSS change at all, so unlike batch G there is no asset
    transition to assert — the gate has to assert the absence of one, and it
    compares style.css byte for byte rather than trusting the claim.

Six gates, each of which can fail on its own:

  0. the candidate capture really came from the pre-flight theme directory,
     and both sides carry the SAME version token. Agreeing on the version is
     not evidence by itself — gate 2's difference set is.
  1. resource inventory: no page may gain, lose or move an asset. This is the
     gate that catches a styling change that was supposed to be free.
  2. masked comparison against the expected-difference SET. A set, not a
     count: an unexpected difference and a missing one both fail. When a
     second, independent baseline capture is supplied, the 33 untouched pages
     must also be masked-identical to it, and the two baselines must agree with
     each other after masking (the mask set's own control).
  3. page-level confined proof, insertion direction: candidate minus the FAQ
     region must be the base, byte for byte, on all 42. The region's own
     content is asserted first (tag, heading, nine items, first one open, the
     three dictated answers verbatim) and the two data-driven answers are
     cross-read from the CANDIDATE dosage page's row — the same template file
     sinofresh_formula_spec_cell() reads — so a drift between the row and the
     band fails here by construction.
  4. source-level reconstruction: undo the declared edits and each file must
     equal the pre-batch source again. The cuts are recomputed from markers
     here rather than imported from the apply tool, so the two
     implementations have to agree.
  5. JSON-LD on all 75 pages, as decoded structures. The 42 must be the base
     list with exactly ONE FAQPage inserted and nothing else; the 33 must be
     deep-equal. This is the only gate that can see the schema at all, so it
     also validates the inserted object's own content.

usage:
    python3 tools/b2d_c_confine.py --base-dir DIR --new-dir DIR [--base2-dir DIR] \\
        --base-php F --new-php F --base-css F --new-css F \\
        --base-tpl-dir DIR --new-tpl-dir DIR [--report F] [--diff-verbose]

Negative control: point --new-* at the base side. Gate 1 reports that nothing
moved, gate 2 that 42 pages should have differed and did not, gates 3-5 that
there is nothing to undo. RC must be 1.
"""
import argparse
import html as html_mod
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

DIFF_VERBOSE = False
SEAM_TALLY = {}
sys.path.insert(0, HERE)
from b2d_s3_confine import masked, load  # noqa: E402  (shared mask set + loader)

VER_RE = re.compile(r'\?ver=[0-9A-Za-z._-]+')
VER_MASK = '?ver=MASK'
PAIR = re.compile(r'''(?:href|src)=["']([^"']+?)\?ver=([^"'&]+)''')
LD_RE = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)

VER = '2.10.54'

PREFLIGHT_MARK = 'sinofresh-theme-preflight'
LIVE_DIR = '/wp-content/themes/sinofresh-theme/'

# --- page-side literals ---------------------------------------------------
# Read off the renderer's own arithmetic rather than inferred: the region
# starts at the batch's template comment and ends on the FAQ section's close,
# and the newline that followed the template's blank line stays behind, so
# removing the region alone restores the base's five newlines between the
# composition block and "Block 4".
REGION_RE = re.compile(r'<!-- Batch C:[\s\S]*?</section>\n\n')
SECTION_EXPECT = ('<section class="wp-block-group sf-fdetail sf-fdetail-faq '
                  'has-card-white-background-color has-background '
                  'is-layout-constrained wp-block-group-is-layout-constrained" '
                  'style="padding-top:var(--wp--preset--spacing--80);'
                  'padding-bottom:var(--wp--preset--spacing--80)">')
H2_EXPECT = '<h2 class="wp-block-heading">Frequently Asked Questions</h2>'
DIV_EXPECT = '<div class="sf-faq">'
LD_SCR_RE = re.compile(r'<script type="application/ld\+json">'
                       r'(?:(?!</script>)[\s\S])*?"@type"\s*:\s*"FAQPage"'
                       r'(?:(?!</script>)[\s\S])*?</script>')
# The theme's own enqueue token, and only that one: a page also carries WP
# core's and the plugins' ?ver= values, and asserting a set of {2.10.54} over
# all of them would fail on every page for reasons that have nothing to do
# with this batch.
STYLE_VER_RE = re.compile(r'/themes/[a-z0-9-]+/style\.css\?ver=([0-9A-Za-z._-]+)')
ITEM_RE = re.compile(
    r'<details class="wp-block-details sf-faq__item"( open)?>'
    r'<summary><h3 class="wp-block-heading">(.*?)</h3>'
    r'<span class="sf-faq__icon" aria-hidden="true"></span></summary>'
    r'<p class="has-text-secondary-color has-text-color">(.*?)</p></details>')
FORM_MARK_RE = re.compile(r'data-sf-form="([a-z-]+)"')
MINI_RE = re.compile(r'<section class="sf-facts-mini">(.*?)</section>', re.S)

QUESTIONS = [
    'Can the active ingredients be changed?',
    'Can the flavour be changed?',
    'Is a gluten-free or grain-free version available?',
    'Is this formula for dogs or for cats?',
    'Can I sample this formula before ordering?',
    'What certifications and documentation do you provide?',
    'Can the packaging and the label be customised?',
    'How should the finished product be stored?',
    'Will you keep my formula and my brand confidential?',
]
# The three the brief dictated word for word. Asserted verbatim because they
# are the batch's contract, not copy that merely happens to be here.
DICTATED = {
    3: 'Our formulas can be customised for dogs, cats, or both. Tell us your target '
       'species when you enquire and we will adjust the formula, the dosage, and the '
       'label accordingly.',
    7: 'Store in a cool, dry place, away from direct sunlight. Once opened, keep the '
       'container tightly closed and use within the recommended period.',
    8: 'Yes \u2014 every formula is produced exclusively under your own brand. We never '
       'sell your formula, your artwork, or your customer list to any third party, and '
       'we sign an NDA before sharing any custom formulation details.',
}
CERT_ANSWER = 5
PACK_ANSWER = 6

# --- source-side markers (the gate recomputes the cuts itself) -------------
PHP_FUNCS_OPEN = ('/**\n * The nine question/answer pairs of a formula\'s FAQ band '
                  '(batch C).')
# The insert sits BETWEEN two top-level functions: after intro()'s closing
# brace, in front of the docblock that opens the next one. So the cut runs from
# the block's own docblock up to (not including) that next docblock, which is
# the same PHP_JSONDOC the gate already anchors on elsewhere.
#
# Ending on intro()'s tail instead ("\treturn $text;\n}\n\n") was the first
# version's marker, and it was correct only while the block was nested INSIDE
# intro() — the arrangement that fatal-failed with "Cannot redeclare
# sinofresh_formula_faq_data()" on exactly the 42 formula pages. A marker that
# has to change when the placement is fixed is a marker that was describing the
# bug. This one is phrased against the file's invariant instead.
PHP_JSONDOC = '/**\n * wp_json_encode() for the body of an inline <script>.'
PHP_FUNCS_TAIL = PHP_JSONDOC
PHP_BRANCH_OPEN = "\t/* Batch C: the formula detail page's accordion is generated by the"
PHP_BRANCH_END = ('\t// Resolve the template file for the current view '
                  '(front page / page slug).')
TPL_OPEN = '<!-- Batch C: the formula FAQ.'
TPL_CLOSE = '</section>\n<!-- /wp:group -->\n'
TPL_SECTION = 'className":"sf-fdetail sf-fdetail-faq"'


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
    out = {}
    for label in ('Certifications', 'Packaging formats'):
        m = re.search(r'data-label="%s"[^>]*>(.*?)</span>' % re.escape(label),
                      block_html, re.S)
        out[label] = (html_mod.unescape(re.sub(r'\s+', ' ', m.group(1))).strip()
                      if m else None)
    return out


def expected_diff_pages(names):
    """Every page served by a formula post: 21 + 21 = 42.

    Named from the capture rather than hard-coded, so a page that stopped being
    fetched cannot quietly shrink the expectation.
    """
    return {n for n in names if re.match(r'^(zh__)?formulas__', n)}


def detail_reduce(name, base_norm, cand_norm, dosage_vals, fails, say,
                  show_diff=False):
    """INSERTION direction: candidate minus the FAQ region must be the base.

    The region's content is checked before it is removed, because a region that
    removes cleanly but carries the wrong nine answers would otherwise pass.
    """
    found = REGION_RE.findall(cand_norm)
    if len(found) != 1:
        fails.append('%s: expected exactly one FAQ region on the candidate, '
                     'found %d' % (name, len(found)))
        say('    !! %s: FAQ regions %d' % (name, len(found)))
        return False
    region = found[0]

    for lit, label in ((SECTION_EXPECT, 'the section tag'),
                       (H2_EXPECT, 'the heading'),
                       (DIV_EXPECT, 'the .sf-faq wrapper')):
        n = region.count(lit)
        if n != 1:
            fails.append('%s: the region carries %d %s, expected 1'
                         % (name, n, label))
            say('    !! %s: %s x%d' % (name, label, n))
            return False
    if '{{' in region:
        fails.append('%s: the region still carries an unreplaced placeholder' % name)
        say('    !! %s: unreplaced placeholder in the region' % name)
        return False
    if not (region.index(SECTION_EXPECT) < region.index(H2_EXPECT)
            < region.index(DIV_EXPECT)):
        fails.append('%s: the heading and the accordion are not inside the '
                     'section, in that order' % name)
        say('    !! %s: region order wrong' % name)
        return False
    if region.count('sf-faq__item') != len(QUESTIONS):
        fails.append('%s: the region carries %d accordion item(s), expected %d'
                     % (name, region.count('sf-faq__item'), len(QUESTIONS)))
        return False

    items = ITEM_RE.findall(region)
    if len(items) != len(QUESTIONS):
        fails.append('%s: %d accordion item(s) match the markup, expected %d'
                     % (name, len(items), len(QUESTIONS)))
        say('    !! %s: accordion items %d' % (name, len(items)))
        return False
    if items[0][0] != ' open':
        fails.append('%s: the first accordion item does not ship open' % name)
        say('    !! %s: first item not open' % name)
        return False
    if any(it[0] for it in items[1:]):
        fails.append('%s: an accordion item other than the first ships open' % name)
        return False
    got_q = [html_mod.unescape(it[1]) for it in items]
    if got_q != QUESTIONS:
        fails.append('%s: the questions are %r' % (name, got_q))
        say('    !! %s: questions differ' % name)
        return False
    answers = [html_mod.unescape(it[2]) for it in items]
    if any(len(a) < 50 for a in answers):
        fails.append('%s: an answer is shorter than 50 characters' % name)
        say('    !! %s: short answer' % name)
        return False
    for idx, want in sorted(DICTATED.items()):
        if answers[idx] != want:
            fails.append('%s: answer %d is %r, the dictated text is %r'
                         % (name, idx + 1, answers[idx][:70], want[:70]))
            say('    !! %s: dictated answer %d reworded' % (name, idx + 1))
            return False

    # cross-source: the two data-driven answers must quote the dosage row the
    # template file holds, which is what spec_cell() reads at render time.
    ok, dv = cross_check(name, cand_norm, answers, dosage_vals, fails, say)
    if not ok:
        return False

    # nothing the batch must keep may have gone with the region
    for keep in ('<h2 class="sf-gallery__title">', 'Formula &amp; nutrition',
                 'sf-fdetail-more', 'sf-formula-hero__meta'):
        if keep in base_norm and keep not in cand_norm:
            fails.append('%s: the candidate lost %r' % (name, keep))
            say('    !! %s: candidate lost %r' % (name, keep))
            return False

    reduced = cand_norm.replace(region, '', 1)
    if reduced == cand_norm:
        fails.append('%s: removing the region changed nothing' % name)
        return False
    # the band is only half of the insert: the FAQPage <script> in <head> goes
    # with it. The newline seam around that script is DERIVED here, not
    # assumed — the four (leading newline?, trailing newline?) variants are
    # tried and exactly the one that reproduces the base is accepted, so a
    # wrong model of the renderer's newline arithmetic fails instead of passing
    # quietly on a comparison that was never made.
    scripts = list(LD_SCR_RE.finditer(reduced))
    if len(scripts) != 1:
        fails.append('%s: expected exactly one FAQPage script to take out, '
                     'found %d' % (name, len(scripts)))
        say('    !! %s: FAQPage scripts %d' % (name, len(scripts)))
        return False
    i, j = scripts[0].span()
    seams = []
    for lead in ([1, 0] if reduced[i - 1:i] == '\n' else [0]):
        for trail in ([1, 0] if reduced[j:j + 1] == '\n' else [0]):
            cut = reduced[:i - lead] + reduced[j + trail:]
            seams.append(((lead, trail), cut))
    hit = [s for s in seams if s[1] == base_norm]
    if not hit:
        fails.append('%s: undoing the batch does not reproduce the base '
                     '(no newline seam around the FAQPage script works: %s)'
                     % (name, ', '.join(str(s[0]) for s in seams)))
        say('    !! %s: no seam reproduces the base' % name)
        return compare_report(name, seams[0][1], base_norm, say, show_diff)
    lead, trail = hit[0][0]
    if len(hit) > 1:
        fails.append('%s: %d newline seams reproduce the base' % (name, len(hit)))
        return False
    reduced = hit[0][1]
    if 'FAQPage' in reduced or 'Batch C' in reduced or 'sf-faq__item' in reduced:
        fails.append('%s: the candidate still mentions the batch after the undo'
                     % name)
        return False
    for keep in ('<script type="application/ld+json">', 'BreadcrumbList', 'Product'):
        if keep in base_norm and keep not in reduced:
            fails.append('%s: the undo lost %r' % (name, keep))
            say('    !! %s: undo lost %r' % (name, keep))
            return False
    say('    %s: region out, FAQPage script out (its own leading newline %s, '
        'its own trailing newline %s)' % (name, 'consumed' if lead else 'left',
                                          'consumed' if trail else 'left'))
    SEAM_TALLY[(lead, trail)] = SEAM_TALLY.get((lead, trail), 0) + 1
    return compare_report(name, reduced, base_norm, say, show_diff)


def compare_report(name, reduced, base_norm, say, show_diff):
    if reduced != base_norm:
        k = 0
        m = min(len(reduced), len(base_norm))
        while k < m and reduced[k] == base_norm[k]:
            k += 1
        say('    !! %s: undid page differs (undone %d B, base %d B, first diff @%d)'
            % (name, len(reduced), len(base_norm), k))
        if show_diff:
            say('          undone:', repr(reduced[max(0, k - 90):k + 60]))
            say('          base  :', repr(base_norm[max(0, k - 90):k + 60]))
        return False
    return True


def cross_check(name, page_html, answers, dosage_vals, fails, say):
    """The band's answers must quote the dosage page's own row values."""
    forms = set(FORM_MARK_RE.findall(page_html))
    if len(forms) != 1:
        fails.append('%s: cannot resolve its dosage form (data-sf-form %r)'
                     % (name, sorted(forms)))
        say('    !! %s: data-sf-form %r' % (name, sorted(forms)))
        return False, None
    dv = dosage_vals.get(forms.pop(), {})
    if not dv.get('Certifications'):
        fails.append('%s: the dosage page yields no Certifications value to '
                     'check the band against' % name)
        say('    !! %s: no Certifications row on the dosage page' % name)
        return False, dv
    want = 'Certifications: ' + dv['Certifications'] + '.'
    if want not in answers[CERT_ANSWER]:
        fails.append('%s: the certification answer does not quote the dosage row '
                     '(%r not in %r)' % (name, want, answers[CERT_ANSWER][:90]))
        say('    !! %s: certification answer != row' % name)
        return False, dv
    if dv.get('Packaging formats'):
        want = ('Standard formats for this dosage form: '
                + dv['Packaging formats'] + '.')
        if want not in answers[PACK_ANSWER]:
            fails.append('%s: the packaging answer does not quote the dosage row '
                         '(%r not in %r)' % (name, want, answers[PACK_ANSWER][:90]))
            say('    !! %s: packaging answer != row' % name)
            return False, dv
        if ('Standard formats for this dosage form: '
                not in answers[PACK_ANSWER]):
            fails.append('%s: the packaging answer dropped its value clause'
                         % name)
            return False, dv
    else:
        if 'Standard formats for this dosage form' in answers[PACK_ANSWER]:
            fails.append('%s: the packaging answer claims a value the dosage '
                         'page does not have' % name)
            say('    !! %s: packaging answer claims a missing value' % name)
            return False, dv
    return True, dv


def validate_faqpage(name, block, dosage_vals, page_html, fails, say):
    """The inserted object's own content: nine questions, in order, with text."""
    if block.get('@context') != 'https://schema.org':
        fails.append('%s: the FAQPage has no schema.org context' % name)
        return False
    ents = block.get('mainEntity')
    if not isinstance(ents, list) or len(ents) != len(QUESTIONS):
        fails.append('%s: the FAQPage carries %r mainEntity entries'
                     % (name, len(ents) if isinstance(ents, list) else ents))
        say('    !! %s: mainEntity count' % name)
        return False
    got, answers = [], []
    for e in ents:
        if e.get('@type') != 'Question':
            fails.append('%s: a mainEntity entry is not a Question' % name)
            return False
        got.append(e.get('name'))
        ans = e.get('acceptedAnswer') or {}
        if (ans.get('@type') != 'Answer'
                or not isinstance(ans.get('text'), str)
                or len(ans['text']) < 50):
            fails.append('%s: the answer to %r is not a usable Answer'
                         % (name, e.get('name')))
            say('    !! %s: bad answer' % name)
            return False
        answers.append(ans['text'])
    if got != QUESTIONS:
        fails.append('%s: the schema questions are %r' % (name, got))
        say('    !! %s: schema question order/content' % name)
        return False
    for idx, want in sorted(DICTATED.items()):
        if answers[idx] != want:
            fails.append('%s: schema answer %d is not the dictated text' % (name, idx + 1))
            say('    !! %s: schema answer %d reworded' % (name, idx + 1))
            return False
    # the schema answers must be the same text the page shows, and both must
    # quote the dosage row: one function feeds both readers, so a disagreement
    # here means the two paths have drifted apart.
    ok, dv = cross_check(name, page_html, answers, dosage_vals, fails, say)
    if not ok:
        return False
    region = REGION_RE.findall(page_html)
    if region:
        for it in ITEM_RE.findall(region[0]):
            pass
        shown = [html_mod.unescape(it[2]) for it in ITEM_RE.findall(region[0])]
        if shown != answers:
            fails.append('%s: the schema answers are not the answers on the page'
                         % name)
            say('    !! %s: schema answers != page answers' % name)
            return False
    raw = json.dumps(block, ensure_ascii=False)
    if '&amp;' in raw or '&#' in raw:
        fails.append('%s: the FAQPage JSON carries an HTML entity' % name)
        say('    !! %s: entity in JSON' % name)
        return False
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base-dir', required=True)
    ap.add_argument('--new-dir', required=True)
    ap.add_argument('--base2-dir', default=None,
                    help='a second, independent capture of the SAME baseline; '
                         'the untouched pages must also be masked-identical to '
                         'it, and the two baselines must agree with each other')
    ap.add_argument('--base-php', required=True)
    ap.add_argument('--new-php', required=True)
    ap.add_argument('--base-css', required=True)
    ap.add_argument('--new-css', required=True)
    ap.add_argument('--base-tpl-dir', required=True)
    ap.add_argument('--new-tpl-dir', required=True)
    ap.add_argument('--ver', default=VER)
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
    say('Batch C — gates for the FAQ band and its FAQPage schema on the 42 '
        'formula pages')
    say('          (style.css unchanged, so functions.php keeps version %s and '
        'no asset may move)' % args.ver)
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
    vb = {v for n in base for v in STYLE_VER_RE.findall(base[n])}
    vs = {v for n in new for v in STYLE_VER_RE.findall(new[n])}
    say('    theme enqueue token (style.css) — base %s / candidate %s (this '
        'batch moves neither)' % (sorted(vb), sorted(vs)))
    if vs != {args.ver} or vb != {args.ver}:
        fails.append('the theme enqueue token is not %s on both sides '
                     '(base %s, new %s)' % (args.ver, sorted(vb), sorted(vs)))
    expect = expected_diff_pages(base.keys())
    say('    expected to differ: %d page(s) — 21 formula + 21 /zh/ formula'
        % len(expect))
    if len(expect) != 42:
        fails.append('the capture names %d formula pages, expected 42'
                     % len(expect))

    # ---- gate 1: resource inventory -------------------------------------
    say('\n[1] resource inventory (which cache tokens moved? — none may)')
    moved, set_changed = {}, []
    for name in sorted(base):
        if name not in new:
            fails.append('page %s missing on the new side' % name)
            continue
        vbm, vnm = ver_map(base[name]), ver_map(new[name])
        if set(vbm) != set(vnm):
            set_changed.append(name)
            continue
        for asset in sorted(vbm):
            if vbm[asset] != vnm[asset]:
                moved.setdefault(asset, []).append(name)
    say('    asset SET changed on %d page(s) (must be 0)' % len(set_changed))
    if set_changed:
        fails.append('asset set changed on: %s' % ', '.join(set_changed[:6]))
    if moved:
        for asset, pages in sorted(moved.items()):
            say('    !! %-18s moved on %d page(s)' % (asset, len(pages)))
        fails.append('cache tokens moved (%s) — batch C ships no CSS/JS change'
                     % ', '.join(sorted(moved)))
    else:
        say('    no asset moved on any of the %d pages: every page still loads '
            'the same cache tokens' % len(new))

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
    if args.base2_dir:
        base2 = load(args.base2_dir)
        say('    second, independent baseline capture: %s (%d pages)'
            % (args.base2_dir, len(base2)))
        aa = [n for n in sorted(base)
              if n in base2 and norm(base[n]) != norm(base2[n])]
        say('    A/A control — the two baseline captures disagree on %d page(s) '
            '(must be 0)' % len(aa))
        if aa:
            fails.append('the two baseline captures differ on %d page(s) after '
                         'masking: %s' % (len(aa), ', '.join(aa[:6])))
        bad = [n for n in sorted(same)
               if n not in base2 or norm(base2[n]) != norm(new[n])]
        say('    of the %d untouched page(s), masked-identical to BOTH captures: '
            '%d' % (len(same), len(same) - len(bad)))
        if bad:
            fails.append('%d untouched page(s) are not masked-identical to the '
                         'second baseline: %s' % (len(bad), ', '.join(bad[:6])))

    # ---- gate 3: page-level confined proof -------------------------------
    say('\n[3] page-level confined proof — INSERTION direction')
    say('    candidate minus the FAQ region must be the base, byte for byte, on '
        'all 42 pages.')
    say('    The band\'s two data-driven answers are cross-read from the '
        'candidate dosage')
    say('    page\'s own row — the same template file spec_cell() reads.')
    dosage_vals = {}
    for name in sorted(new):
        slug = name[len('zh__'):] if name.startswith('zh__') else name
        if not slug.startswith('formulas__'):
            continue
        m = FORM_MARK_RE.search(new[name])
        if not m:
            fails.append('%s: no data-sf-form attribute on the candidate' % name)
            continue
        form = m.group(1)
        pname = 'products__%s.html' % form
        if pname not in new:
            fails.append('the capture lacks the dosage page %s' % pname)
            continue
        mm = MINI_RE.search(norm(new[pname]))
        dosage_vals[form] = mini_values(mm.group(1)) if mm else {}
    say('    dosage rows read from %d page(s) on the candidate side'
        % len(dosage_vals))
    for form, dv in sorted(dosage_vals.items()):
        if not dv.get('Certifications') or not dv.get('Packaging formats'):
            fails.append('the candidate dosage page %s is missing a row the band '
                         'reads' % form)
            say('    !! products__%s: incomplete row set %r' % (form, sorted(dv)))
    confined = 0
    for name in sorted(expect):
        if name not in new or name not in base:
            continue
        ok = detail_reduce(name, norm(base[name]), norm(new[name]), dosage_vals,
                           fails, say, show_diff=DIFF_VERBOSE)
        if ok:
            confined += 1
        elif not any(f.startswith(name) for f in fails):
            fails.append('%s: undoing the batch does not reproduce the base' % name)
    say('    %d/%d page(s) reduce to the base byte-for-byte (21 en + 21 zh)'
        % (confined, len(expect)))
    if SEAM_TALLY:
        say('    FAQPage <script> newline seam, derived per page (leading/trailing '
            'own newline consumed): %s'
            % ', '.join('%s on %d page(s)' % (str(k), v)
                        for k, v in sorted(SEAM_TALLY.items())))
    if confined != 42:
        fails.append('only %d/42 formula pages reduced' % confined)

    # ---- gate 4: source-level reconstruction -----------------------------
    say('\n[4] source reconstruction — undo the declared edits, compare to the '
        'pre-batch source')
    bphp = open(args.base_php, encoding='utf-8').read()
    nphp = open(args.new_php, encoding='utf-8').read()
    undone = nphp

    def cut_between(start_mark, end_mark, label):
        """Remove the insert between two markers, leaving both in place.

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
        undone = undone[:i] + undone[j:]

    if 'sinofresh_formula_faq' not in nphp:
        fails.append('functions.php: the candidate has no FAQ function at all')
    if '2.10.55' in nphp:
        fails.append('functions.php: the version moved, but this batch ships no '
                     'version change')
    for label, lit in (('php/faq-functions', 'sinofresh_formula_faq_data'),
                       ('php/faqpage-branch', "is_singular('sf_formula')")):
        if lit not in nphp:
            fails.append('%s: %r is missing from the candidate' % (label, lit))
    # The block has to be at INCLUDE time, i.e. between two top-level
    # functions. Miss that and everything else still looks green: the splice is
    # clean, `php -l` is happy, the undo proof below still reproduces the base.
    # What actually happens is that the declarations are reached only when the
    # enclosing function runs, and the second call in one request fatals with
    # "Cannot redeclare sinofresh_formula_faq_data()" — which is how the first
    # arrangement of this batch failed, on exactly the 42 formula pages (the
    # pages that call intro()) while the other 33 answered 200.
    #
    # The byte-level proxy for "top level" is that the block opens right after
    # a column-0 closing brace and a blank line. tools/b2d_c_php_scope.php
    # proves the property exactly, with PHP's own tokenizer; this line is what
    # makes the gate refuse on its own.
    i = nphp.find(PHP_FUNCS_OPEN)
    if i < 4 or nphp[i - 3:i] != '}\n\n' or nphp[i - 4] != '\n':
        fails.append('php/faq-functions: the block does not sit between two '
                     'top-level functions — it would be declared only when the '
                     'enclosing function runs, not at include time')
        say('    functions.php            !! the FAQ block is not at top level')
    cut_between(PHP_BRANCH_OPEN, PHP_BRANCH_END, 'php/faqpage-branch')
    cut_between(PHP_FUNCS_OPEN, PHP_FUNCS_TAIL, 'php/faq-functions')
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

    label = 'templates/single-sf_formula.html'
    braw = open(os.path.join(args.base_tpl_dir, 'single-sf_formula.html'),
                encoding='utf-8').read()
    nraw = open(os.path.join(args.new_tpl_dir, 'single-sf_formula.html'),
                encoding='utf-8').read()
    i = nraw.find(TPL_OPEN)
    j = nraw.find(TPL_CLOSE, i) if i >= 0 else -1
    if i < 0 or j < 0:
        fails.append('%s: cannot locate the batch region (start %d, close %d)'
                     % (label, i, j))
        say('    %-24s !! region not locatable' % label)
    else:
        j += len(TPL_CLOSE)
        region = nraw[i:j]
        for needle in (TPL_SECTION, '[sf_formula_faq]', H2_EXPECT):
            if needle not in region:
                fails.append('%s: the region lacks %r' % (label, needle))
        if region.count('[sf_formula_faq]') != 1:
            fails.append('%s: the FAQ shortcode is not in the region exactly once'
                         % label)
        # a bracket token inside an HTML comment is expanded by do_shortcode()
        # inside that comment: the template must not carry one
        for line in nraw.split('\n'):
            if line.strip().startswith('<!--') and '[' in line:
                fails.append('%s: a comment line carries a bracket token: %r'
                             % (label, line))
        undone = nraw[:i] + nraw[j:]
        same_file = undone == braw
        say('    %-24s base %7d / new %7d / undone %7d  undone==base:%s (+%d B)'
            % (label, len(braw.encode()), len(nraw.encode()),
               len(undone.encode()), 'YES' if same_file else 'NO',
               len(nraw.encode()) - len(braw.encode())))
        if not same_file:
            fails.append('%s: reconstruction does not reproduce the base '
                         'byte-for-byte' % label)
            k = next((q for q in range(min(len(undone), len(braw)))
                      if undone[q] != braw[q]), min(len(undone), len(braw)))
            say('        first mismatch @%d' % k)
            say('          undone:', repr(undone[max(0, k - 70):k + 40]))
            say('          base  :', repr(braw[max(0, k - 70):k + 40]))

    cb = open(args.base_css, 'rb').read()
    cn = open(args.new_css, 'rb').read()
    say('    %-24s base %7d / new %7d  identical:%s (batch C ships no CSS)'
        % ('style.css', len(cb), len(cn), 'YES' if cb == cn else 'NO'))
    if cb != cn:
        fails.append('style.css is not byte-identical — this batch was supposed '
                     'to change no CSS at all')

    # ---- gate 5: JSON-LD -------------------------------------------------
    say('\n[5] JSON-LD (decoded structures, not masked text)')
    ld_bad, shape_bad, ld_pages = [], [], 0
    for name in sorted(base):
        if name not in new:
            continue
        lb, ln = ld_blocks(base[name]), ld_blocks(new[name])
        ld_pages += 1
        if name in expect:
            if [b for b in lb if b.get('@type') == 'FAQPage']:
                shape_bad.append('%s: the base already carries a FAQPage' % name)
                continue
            idx = [k for k, b in enumerate(ln) if b.get('@type') == 'FAQPage']
            if len(idx) != 1:
                shape_bad.append('%s: the candidate carries %d FAQPage block(s), '
                                 'expected 1' % (name, len(idx)))
                continue
            if ln[:idx[0]] + ln[idx[0] + 1:] != lb:
                shape_bad.append('%s: removing the FAQPage does not reproduce '
                                 'the base list' % name)
                continue
            if not validate_faqpage(name, ln[idx[0]], dosage_vals, new[name],
                                    fails, say):
                shape_bad.append(name)
        elif lb != ln:
            ld_bad.append(name)
            if len(ld_bad) <= 2:
                say('    DIFF %s' % name)
                say('      base: %s' % json.dumps(lb, ensure_ascii=False)[:300])
                say('      new : %s' % json.dumps(ln, ensure_ascii=False)[:300])
    other = len(base) - len(expect)
    say('    pages compared: %d' % ld_pages)
    say('    formula pages (42): base list plus exactly one FAQPage, nothing '
        'else — %d ok' % (len(expect) - len(shape_bad)))
    say('    other pages (%d): deep-equal — %d/%d'
        % (other, other - len(ld_bad), other))
    if ld_pages != 75:
        fails.append('gate 5 compared %d pages, expected 75' % ld_pages)
    if shape_bad:
        fails.append('%d formula page(s) have the wrong JSON-LD shape: %s'
                     % (len(shape_bad), '; '.join(shape_bad[:4])))
    if ld_bad:
        fails.append('%d page(s) differ in JSON-LD outside the formula set: %s'
                     % (len(ld_bad), ', '.join(ld_bad[:6])))

    say('\n' + '=' * 78)
    if fails:
        say('FAIL — %d problem(s):' % len(fails))
        for f in fails:
            say('  * %s' % f)
    else:
        say('PASS — no asset moved on any of the 75 pages and both sides still '
            'carry version %s;' % args.ver)
        say('       %d pages differ and they are exactly the 42 formula pages '
            '(21 en + 21 zh), with' % len(expect))
        say('       the untouched %d masked-identical to two independent '
            'baseline captures;' % other)
        say('       all 42 reduce to the base byte-for-byte once the FAQ region '
            'is removed, with the')
        say('       nine questions, the open first item and the three dictated '
            'answers asserted, and')
        say('       the two data-driven answers cross-read from the dosage row;')
        say('       functions.php and the template rebuild to their pre-batch '
            'bytes, style.css is')
        say('       byte-identical;')
        say('       the 42 carry exactly one more FAQPage whose answers are the '
            'answers on the page,')
        say('       and the other %d pages are deep-equal.' % other)
    say('=' * 78)

    if args.report:
        os.makedirs(os.path.dirname(args.report) or '.', exist_ok=True)
        with open(args.report, 'w', encoding='utf-8') as fh:
            fh.write('\n'.join(lines) + '\n')
        print('\nreport -> %s' % args.report)
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())

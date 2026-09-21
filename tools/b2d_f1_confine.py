#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch F1 — gates for the .sf-facts-mini insertion on the dosage pages.

This batch only adds things. Eight dosage templates gain one wp:html block
each (section.sf-facts-mini, three data-label'd values), style.css gains the
.sf-facts-mini namespace, functions.php points sinofresh_formula_spec_cell()
at the new block, and both files move one version number.

Six gates, each of which can fail on its own:

  0. the candidate capture really came from the pre-flight theme directory.
     A capture that silently served live bytes would pass every other gate
     while proving nothing, so this is asserted before anything else.
  1. resource inventory: only style.css moved, on all 75 pages, and no page
     gained or lost an asset (a SET change is not a version change).
  2. masked comparison with the expected-difference set. The set is a set,
     not a count: an unexpected difference and a missing one both fail.
  3. page-level confined proof. THE DIRECTION IS THE REVERSE OF STEP E, and
     the direction is set by which side the batch's content lives on — this
     is an INSERTION batch, so the new block exists only on the CANDIDATE
     side and the reduction deletes it there (step E deleted from the base;
     getting this backwards cannot be detected by counting, which is exactly
     the failure mode recorded in the 2D-E notes):
       * 16 dosage pages: candidate minus the .sf-facts-mini block must be
         the base page byte-for-byte;
       * 42 formula pages: the hero meta line is composed from the dosage
         page's .sf-facts-mini values, so it was only the form label under
         2D-E and is restored here. Putting the degraded line back must
         reproduce the base byte-for-byte. The restored values are not
         asserted from a local table — the MOQ / lead time are read out of
         the CANDIDATE DOSAGE PAGE's own block (the same single source
         spec_cell reads), so a drift between the row and the hero meta
         fails here by construction.
  4. source-level reconstruction: undo the declared edits and the file must
     equal the pre-batch source again. The template undo is recomputed here
     from markers rather than imported from the apply tool, so the two
     implementations have to agree.
  5. JSON-LD deep-equal on all 75 pages.

usage:
    python3 tools/b2d_f1_confine.py --base-dir DIR --new-dir DIR \\
        --base-css F --new-css F --base-php F --new-php F \\
        --base-tpl-dir DIR --new-tpl-dir DIR [--report F]

Negative control: point --new-* at the base side. Gate 1 must report that
nothing moved, gate 2 must report 58 pages that should have differed and did
not, and gate 3 must not find a single block or a single restored meta line.
RC must be 1.
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from b2d_s3_confine import masked, load  # noqa: E402  (shared mask set + loader)

VER_RE = re.compile(r'\?ver=[0-9A-Za-z._-]+')
VER_MASK = '?ver=MASK'
PAIR = re.compile(r'''(?:href|src)=["']([^"']+?)\?ver=([^"'&]+)''')
LD_RE = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)

DOSAGES = "soft-chews tablets powders pastes drops liquids fish-oil dental-chews".split()

PREFLIGHT_MARK = 'sinofresh-theme-preflight'

# --- the inserted row, as it appears on the rendered page ------------------
# The wp:html wrapper's delimiter comments are consumed by the renderer but
# each line's newline stays. The base pages' hero -> #formulas seam is FOUR
# newlines (measured on the live capture; it is what 2D-E's join wrote down).
# The newline runs around the row are captured rather than assumed — the run
# lengths are printed in the gate 3 report so the seam is measured, not
# theorised — and the undo replaces the whole match with exactly the base's
# four-newline seam. A wrong prediction of the run lengths cannot fake a
# pass: the reduction must still reproduce the base byte-for-byte.
MINI_PAGE_RE = re.compile(
    r'\n+<section class="sf-facts-mini">[\s\S]*?</section>\n+'
    r'(?=<section id="formulas")')
MINI_JOIN = '\n\n\n\n'

# template-side markers (the wp:html wrapper is verbatim there)
TPL_BLOCK_OPEN = '<!-- wp:html -->\n<section class="sf-facts-mini">'
TPL_BLOCK_CLOSE = '</section>\n<!-- /wp:html -->\n\n'
DATA_LABELS = ('data-label="MOQ"', 'data-label="Lead time"',
               'data-label="Certifications"')
LEAD = 'Typically 7\u201315 working days after packaging is ready'
CERTS = 'FDA, cGMP, ISO 9001, FSSC 22000, HACCP, BRC'

# The dosage page meta paragraph, and the formula page's hero meta line.
META_RE = re.compile(r'<p class="sf-formula-hero__meta">([^<]*)</p>')
DETAIL_META_RE = re.compile(r'<p class="sf-formula-hero__meta">[^<]*</p>')
FORM_MARK_RE = re.compile(r'data-sf-form="([a-z-]+)"')

# --- the source-side edits, declared --------------------------------------
VER_CSS = ('Version: 2.10.52', 'Version: 2.10.53')
VER_PHP = ("array(), '2.10.52');", "array(), '2.10.53');")
# functions.php: the docblock and the parsing body. Each pair is (restore,
# currently-present); the undo replaces present->restore once, so both sides
# must occur exactly once in the file.
DOC_PHP = (
    """/**
 * One cell of a dosage page's "Typical specifications" table, by row label.
 *
 * The formula detail hero needs the MOQ and the lead time of the dosage form
 * the formula belongs to. Both already exist as rows of the sf-spectable
 * table on /products/<form>/, so the hero reads them from that template file
 * instead of restating them — same single-source-of-truth rule the FAQPage,
 * BreadcrumbList and Product schema generators follow. Editing the table on
 * the dosage page updates every formula hero of that form.
 *
 * $label is the data-label attribute ("MOQ", "Lead time"), not the header
 * text, because data-label is the stable machine-readable twin of the
 * column head (it also drives the stacked mobile table).""",
    """/**
 * One value of a dosage page's .sf-facts-mini core-facts row, by data-label.
 *
 * The formula detail hero needs the MOQ and the lead time of the dosage form
 * the formula belongs to. Both exist as value spans of the .sf-facts-mini row
 * on /products/<form>/ (batch F1 re-established what the sf-spectable table
 * fed before 2D-E deleted it), so the hero reads them from that template file
 * instead of restating them — same single-source-of-truth rule the FAQPage,
 * BreadcrumbList and Product schema generators follow. Editing the row on
 * the dosage page updates every formula hero of that form.
 *
 * $label is the data-label attribute ("MOQ", "Lead time"), not the visible
 * label text, because data-label is the stable machine-readable twin of the
 * visible label (it also survives a wording change to the row's labels).
 *
 * The lookup is scoped to the .sf-facts-mini block, not the whole page: a
 * second data-label anywhere else on the page must never shadow the value.""")
BODY_PHP = (
    """\t$html = (string) file_get_contents($file);
\tif (preg_match('/<td[^>]*data-label="' . preg_quote($label, '/') . '"[^>]*>(.*?)<\\/td>/s', $html, $m)) {
\t\t$cache[$key] = html_entity_decode(trim(wp_strip_all_tags($m[1])), ENT_QUOTES, 'UTF-8');
\t}
\treturn $cache[$key];""",
    """\t$html = (string) file_get_contents($file);
\t/* Scope to the .sf-facts-mini row (batch F1's replacement for the
\t   sf-spectable table): the band's wp:html wrapper is consumed by the
\t   renderer, so the template carries the section verbatim. Non-greedy on
\t   both spans — the row holds no nested section and the page must never
\t   gain one inside it. */
\tif (preg_match('/<section class="sf-facts-mini">(.*?)<\\/section>/s', $html, $band)
\t\t&& preg_match('/data-label="' . preg_quote($label, '/') . '"[^>]*>(.*?)<\\/span>/s', $band[1], $m)) {
\t\t$cache[$key] = html_entity_decode(trim(wp_strip_all_tags($m[1])), ENT_QUOTES, 'UTF-8');
\t}
\treturn $cache[$key];""")
# the {{FORMULA_META}} docblock mentions the source table too
MAP_PHP = (
    """ *                        "<form> · MOQ <row> · Lead time <row>", where the two
 *                        rows come from the form's /products/<form>/
 *                        specification table (sinofresh_formula_spec_cell).""",
    """ *                        "<form> · MOQ <value> · Lead time <value>", where
 *                        the two values come from the form's /products/<form>/
 *                        .sf-facts-mini row (sinofresh_formula_spec_cell).""")


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
    """The three data-label'd values of one rendered/template block."""
    out = {}
    for label in ('MOQ', 'Lead time', 'Certifications'):
        m = re.search(r'data-label="%s"[^>]*>(.*?)</span>' % label,
                      block_html, re.S)
        out[label] = re.sub(r'\s+', ' ', m.group(1)).strip() if m else None
    return out


def expected_diff_pages(names):
    """Every page served by a dosage template or by a formula post.

    21 formula posts x 2 languages, 8 dosage templates x 2 languages. Named
    from the capture rather than hard-coded so a page that stopped being
    fetched cannot quietly shrink the expectation.
    """
    return {n for n in names if re.match(r'^(zh__)?(products|formulas)__', n)}


def page_reduce(name, base_norm, cand_norm, fails, say):
    """Undo this batch on one page; return True when it reproduces the other.

    INSERTION batch — the reverse of step E. The .sf-facts-mini block exists
    only on the CANDIDATE side, so the reduction deletes it there: candidate
    minus the block must equal the base. For a formula page the batch's
    effect is the restored hero meta, which is on the CANDIDATE side too, so
    the degraded line goes back on and the result must equal the base.
    """
    if re.match(r'^(zh__)?products__', name):
        form = name.split('__')[-1]
        blocks = MINI_PAGE_RE.findall(cand_norm)
        if len(blocks) != 1:
            fails.append('%s: expected exactly one .sf-facts-mini block on the '
                         'candidate, found %d' % (name, len(blocks)))
            say('    !! %s: blocks on candidate %d' % (name, len(blocks)))
            return False
        m = MINI_PAGE_RE.search(cand_norm)
        runs = re.match(r'(\n+)<section', m.group(0)), re.search(r'</section>(\n+)$', m.group(0))
        say('    %s: seam runs lead %d / trail %d newline(s)'
            % (name, len(runs[0].group(1)), len(runs[1].group(1)) if runs[1] else -1))
        block = m.group(0)
        vals = mini_values(block)
        # what is being deleted has to look like the row, carry the form's own
        # values, and nothing that survives may be inside the deleted span.
        if not all(vals.values()):
            fails.append('%s: the block lacks a data-label value: %r'
                         % (name, vals))
            say('    !! %s: block values %r' % (name, vals))
            return False
        if vals['Lead time'] != LEAD or vals['Certifications'] != CERTS:
            fails.append('%s: block lead/certs drift from the declared values: '
                         '%r / %r' % (name, vals['Lead time'],
                                      vals['Certifications']))
            say('    !! %s: lead/certs drift' % name)
            return False
        if '<h2' in block or '<h3' in block:
            fails.append('%s: the deleted block carries a heading — the dot '
                         'rail must not move' % name)
            return False
        left = [tok for tok in ('sf-facts-mini',) if tok in
                MINI_PAGE_RE.sub('', cand_norm)]
        if left:
            fails.append('%s: the candidate still carries %r after the undo'
                         % (name, left))
            return False
        for keep in ('<section id="formulas"', 'configurator',
                     'Frequently Asked Questions', 'How We Work',
                     'Related Dosage Forms'):
            if keep not in cand_norm.replace(block, '', 1):
                fails.append('%s: the candidate lost %r' % (name, keep))
                say('    !! %s: candidate lost %r' % (name, keep))
                return False
        # the join: the match spans the row plus its surrounding newline runs;
        # replacing it with the base's measured seam must give the base.
        reduced = MINI_PAGE_RE.sub(MINI_JOIN, cand_norm, count=1)
        return reduced == base_norm

    # formula page handling lives in page_reduce_detail(); main() routes by
    # name. This function is dosage pages only — deliberately: one function
    # handling both shapes is what let step E's first version mix directions.


def page_reduce_detail(name, base_norm, cand_norm, dosage_vals, fails, say):
    """Formula pages: the hero meta was the form label alone under 2D-E and
    is restored here; putting the degraded line back must give the base."""
    basepage, cand = base_norm, cand_norm
    restored = DETAIL_META_RE.findall(cand)
    degraded = DETAIL_META_RE.findall(basepage)
    if len(restored) != 1 or len(degraded) != 1:
        fails.append('%s: meta lines base %d / candidate %d, expected 1/1'
                     % (name, len(degraded), len(restored)))
        say('    !! %s: meta lines %d/%d'
            % (name, len(degraded), len(restored)))
        return False
    label = META_RE.search(degraded[0]).group(1)
    moq, lead = dosage_vals['MOQ'], dosage_vals['Lead time']
    if not moq or not lead:
        fails.append('%s: the dosage page block did not yield MOQ/lead values'
                     % name)
        say('    !! %s: dosage values %r' % (name, dosage_vals))
        return False
    want = ('<p class="sf-formula-hero__meta">%s \u00b7 MOQ %s \u00b7 '
            'Lead time %s</p>' % (label, moq, lead))
    if restored[0] != want:
        fails.append('%s: restored hero meta is %r, expected exactly %r'
                     % (name, restored[0], want))
        say('    !! %s: meta %r' % (name, restored[0]))
        say('       expected %r' % want)
        return False
    return cand.replace(restored[0], degraded[0], 1) == basepage


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
    ap.add_argument('--from-ver', default='2.10.52')
    ap.add_argument('--to-ver', default='2.10.53')
    ap.add_argument('--allow-live-capture', action='store_true',
                    help='gate 0 escape hatch for an A/A self-test of the '
                         'gate itself; never use it for a real candidate')
    ap.add_argument('--report', default=None)
    args = ap.parse_args()

    lines, fails = [], []

    def say(*parts):
        s = ' '.join(str(p) for p in parts)
        print(s)
        lines.append(s)

    say('=' * 78)
    say('Batch F1 — gates for inserting the .sf-facts-mini core-facts row')
    say('                 on the eight dosage pages, %s -> %s'
        % (args.from_ver, args.to_ver))
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
    if len(marked) != len(new) and not args.allow_live_capture:
        fails.append('%d candidate page(s) do not mention the pre-flight theme '
                     'directory — this capture is not the candidate'
                     % (len(new) - len(marked)))
    if marked and len(marked) != len(new):
        say('    !! e.g. %s' % ', '.join(sorted(set(new) - set(marked))[:5]))
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
                     'version tokens, so this gate proved nothing '
                     '(is --new pointing at base?)')
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

    # ---- gate 2: masked comparison, expected set is a set ----------------
    say('\n[2] masked comparison of the 75 pages (?ver= folded, nonces and '
        'the pre-flight directory masked)')
    diff, same = [], []
    for name in sorted(base):
        if name not in new:
            continue
        (diff if norm(base[name]) != norm(new[name]) else same).append(name)
    say('    differ    %d page(s)' % len(diff))
    say('    identical %d page(s)' % len(same))
    unexpected = sorted(set(diff) - expect)
    missing = sorted(expect - set(diff))
    for name in unexpected:
        say('    !! %s differs but was not expected to' % name)
        fails.append('%s differs but was not expected to' % name)
    for name in missing:
        say('    !! %s should have differed and did not' % name)
        fails.append('%s should have differed and did not' % name)

    # ---- gate 3: page-level confined proof -------------------------------
    say('\n[3] page-level confined proof: undo this batch, compare the two '
        'sides')
    say('    INSERTION batch — direction is the reverse of step E: the block '
        'lives on the')
    say('    CANDIDATE side, so candidate minus the block must equal the '
        'base. The detail')
    say('    pages\' restored meta values are cross-read from the candidate '
        'dosage page\'s')
    say('    own block — the same single source spec_cell reads.')
    # cross-source values, read from the candidate dosage pages
    dosage_vals = {}
    for form in DOSAGES:
        pname = 'products__%s.html' % form
        if pname not in new:
            fails.append('the capture lacks the dosage page %s' % pname)
            continue
        m = MINI_PAGE_RE.search(norm(new[pname]))
        dosage_vals[form] = mini_values(m.group(0)) if m else {}

    confined = 0
    for name in sorted(expect):
        if name not in new or name not in base:
            continue
        b, n = norm(base[name]), norm(new[name])
        if re.match(r'^(zh__)?products__', name):
            ok = page_reduce(name, b, n, fails, say)
        else:
            marks = FORM_MARK_RE.findall(n)
            forms = set(marks)
            if len(forms) != 1:
                ok = False
                fails.append('%s: cannot resolve its dosage form '
                             '(data-sf-form values %r)' % (name, sorted(forms)))
                say('    !! %s: form unresolved %r' % (name, sorted(forms)))
            else:
                form = marks[0]
                ok = page_reduce_detail(name, b, n, dosage_vals[form],
                                        fails, say)
        if ok:
            confined += 1
        elif not any(f.startswith(name) for f in fails):
            fails.append('%s: undoing the batch does not reproduce the base'
                         % name)
            say('    DIFF %s does not reduce to the base page' % name)
    say('    %d/%d page(s) reduce to the base byte-for-byte'
        % (confined, len(expect)))

    # ---- gate 4: source-level reconstruction -----------------------------
    say('\n[4] style.css / functions.php / the eight templates — '
        'reconstruction')
    say('    each file: undo the declared edits, then compare to the source '
        'the batch started from.')
    # style.css is NOT in jobs: its two edits (version token + appended
    # block) are undone together in the block-wise reconstruction below —
    # undoing the version alone could never reproduce the base, and the
    # class token appears many times so it cannot be a literal pair.
    jobs = [('functions.php', args.base_php, args.new_php,
             [VER_PHP, DOC_PHP, BODY_PHP, MAP_PHP])]
    for label, bpath, npath, declared in jobs:
        braw = open(bpath, encoding='utf-8').read()
        nraw = open(npath, encoding='utf-8').read()
        undone, all_applied = nraw, True
        for old, newlit in declared:
            n_occ = undone.count(newlit)
            if n_occ != 1:
                fails.append('%s: declared new text occurs %d time(s), '
                             'expected 1' % (label, n_occ))
                say('    %-24s !! declared literal occurs %d time(s)'
                    % (label, n_occ))
                all_applied = False
                continue
            undone = undone.replace(newlit, old, 1)
        same_file = all_applied and undone == braw
        say('    %-24s base %7d / new %7d / undone %7d  applied:%-3s  '
            'undone==base:%s'
            % (label, len(braw.encode()), len(nraw.encode()),
               len(undone.encode()), 'YES' if all_applied else 'NO',
               'YES' if same_file else 'NO'))
        if not same_file:
            fails.append('%s: reconstruction does not reproduce the base '
                         'byte-for-byte' % label)
            k = next((i for i in range(min(len(undone), len(braw)))
                      if undone[i] != braw[i]), min(len(undone), len(braw)))
            say('        first mismatch @%d' % k)
            say('          undone:', repr(undone[max(0, k - 60):k + 40]))
            say('          base   :', repr(braw[max(0, k - 60):k + 40]))

    # style.css: the .sf-facts-mini block is delimited by its own comment
    # banner and its last rule; the undo cuts the whole insertion (separator
    # newline included) and must reproduce the base. Boundaries measured on
    # the real file; the byte comparison below is the proof.
    bcss = open(args.base_css, encoding='utf-8').read()
    ncss = open(args.new_css, encoding='utf-8').read()
    BANNER = '/* F1 — minimal core-facts row'
    TAIL = ('\n\t.sf-facts-mini__item:last-child {\n\t\t'
            'border-bottom: 0;\n\t}\n}\n')
    start = ncss.find(BANNER)
    if start < 0:
        fails.append('style.css: the F1 comment banner is missing')
        say('    style.css               !! F1 banner missing')
    else:
        end = ncss.find(TAIL, start)
        if end < 0:
            fails.append('style.css: the F1 block tail is missing')
            say('    style.css               !! F1 tail missing')
        else:
            end += len(TAIL)
            # the inserted text is '\n/* F1...' through '}\n': cut from one
            # byte before the banner (the separator newline) to the end.
            undone_css = ncss[:start - 1] + ncss[end:]
            undone_css = undone_css.replace(VER_CSS[1], VER_CSS[0], 1)
            same_css = undone_css == bcss
            say('    %-24s base %7d / new %7d / undone %7d  applied:YES  '
                'undone==base:%s  (+%d B CSS)'
                % ('  + .sf-facts-mini block',
                   len(bcss.encode()), len(ncss.encode()), len(undone_css.encode()),
                   'YES' if same_css else 'NO',
                   len(ncss.encode()) - len(bcss.encode())))
            if not same_css:
                fails.append('style.css: the .sf-facts-mini block undo does not '
                             'reproduce the base')
                k = next((q for q in range(min(len(undone_css), len(bcss)))
                          if undone_css[q] != bcss[q]), min(len(undone_css), len(bcss)))
                say('        first mismatch @%d' % k)
                say('          undone:', repr(undone_css[max(0, k - 60):k + 40]))
                say('          base   :', repr(bcss[max(0, k - 60):k + 40]))

    # The templates are recomputed here from the markers — deliberately not
    # imported from the apply tool, so the two implementations have to agree.
    for s in DOSAGES:
        label = 'templates/page-%s.html' % s
        braw = open(os.path.join(args.base_tpl_dir, 'page-%s.html' % s),
                    encoding='utf-8').read()
        nraw = open(os.path.join(args.new_tpl_dir, 'page-%s.html' % s),
                    encoding='utf-8').read()
        s0 = nraw.find(TPL_BLOCK_OPEN)
        problems = []
        if braw.count('sf-facts-mini') != 0:
            problems.append('the base template already carries the row')
        if s0 < 0:
            problems.append('the candidate template lacks the block open marker')
        if problems:
            for p in problems:
                fails.append('%s: %s' % (label, p))
                say('    %-24s !! %s' % (label, p))
            continue
        e0 = nraw.find(TPL_BLOCK_CLOSE, s0) + len(TPL_BLOCK_CLOSE)
        blob = nraw[s0:e0]
        vals = mini_values(blob)
        # what was inserted must look like the row, carry the form's values,
        # and nothing that survives may be inside the inserted span.
        if not all(vals.values()):
            problems.append('the inserted block lacks a data-label value')
        elif vals['Lead time'] != LEAD or vals['Certifications'] != CERTS:
            problems.append('lead/certs drift from the declared values')
        for needle in DATA_LABELS:
            if needle not in blob:
                problems.append('inserted block lacks %r' % needle)
        if '<h2' in blob or '<h3' in blob:
            problems.append('inserted block carries a heading')
        # the join must leave the base exactly: block + the blank line after
        # it, cut, gives back the pre-F1 bytes.
        undone = nraw.replace(blob, '', 1)
        same_file = undone == braw
        say('    %-24s base %7d / new %7d / undone %7d  applied:YES  '
            'undone==base:%s  (+%d B)'
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
            k = next((i for i in range(min(len(undone), len(braw)))
                      if undone[i] != braw[i]), min(len(undone), len(braw)))
            say('        first mismatch @%d' % k)
            say('          undone:', repr(undone[max(0, k - 60):k + 40]))
            say('          base   :', repr(braw[max(0, k - 60):k + 40]))

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
        say('       all %d changed pages reduce to the base byte-for-byte '
            'once the inserted row is deleted and the restored meta line '
            'degraded;' % len(expect))
        say('       the ten source files rebuild to their pre-batch bytes;')
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

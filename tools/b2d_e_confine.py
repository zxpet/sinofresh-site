#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch 2D · Step E — gates for the three-section deletion on the dosage pages.

This batch only removes things. Eight dosage templates lose three sections
each (the B2D-S5 core-facts band, the sf-spectable "typical specifications"
table, the B2D-S1 actives wrapper) and style.css/functions.php move one
version number. Nothing is added; every shortcode and every .sf-* CSS rule
stays, so the F1 batch can re-use them.

Six gates, each of which can fail on its own:

  0. the candidate capture really came from the pre-flight theme directory.
     A capture that silently served live bytes would pass every other gate
     while proving nothing, so this is asserted before anything else.
  1. resource inventory: only style.css moved, on all 75 pages, and no page
     gained or lost an asset (a SET change is not a version change).
  2. masked comparison with the expected-difference set. The set is a set,
     not a count: an unexpected difference and a missing one both fail.
  3. page-level confined proof. Two shapes, because the batch has two
     consequences:
       * 16 dosage pages: delete the three spans from the base page and the
         result must be the candidate byte-for-byte;
       * 42 formula pages: the hero meta line is composed from the dosage
         template's spectable cells, so it degrades to the form label alone
         (functions.php: meta_bits, implode(' · ')). Restoring the old line
         must reproduce the base byte-for-byte.
  4. source-level reconstruction: undo the declared edits and the file must
     equal the pre-batch source again. The template deletions are recomputed
     here from the markers rather than imported from the apply tool, so the
     two implementations have to agree.
  5. JSON-LD deep-equal on all 75 pages.

usage:
    python3 tools/b2d_e_confine.py --base-dir DIR --new-dir DIR \\
        --base-css F --new-css F --base-php F --new-php F \\
        --base-tpl-dir DIR --new-tpl-dir DIR [--report F]

Negative control: point --new-* at the base side. Gate 1 must report that
nothing moved, gate 2 must report 58 pages that should have differed and did
not, and gate 3 must not find a single span. RC must be 1.
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

# The candidate must come from the pre-flight copy. Masking folds this token
# away (sf_masked_cmp: preflight_theme_dir), which is exactly why the raw
# bytes have to be checked for it before anything is masked.
PREFLIGHT_MARK = 'sinofresh-theme-preflight'

# --- the two rendered spans, as they appear in the base pages -------------
# Derived from the base pages themselves, not from theory: block delimiter
# comments are consumed by the renderer but their line's newline stays, while
# author comments survive verbatim. Measured seams:
#   hero </section> + \n\n\n + band span + \n\n\n + <section id="formulas"
#   configurator </section> + \n\n\n\n + spectable span
#                          + \n\n\n + <!-- B2D-S1: actives --> + \n\n
#                          + actives span + \n\n\n + <!-- Block 9 ...
# After the deletion the two seams join, and the joins are what the patterns
# write down: \n\n\n\n before #formulas, \n\n\n before the Block 9 comment.
S5_OPEN = '<!-- B2D-S5: core facts -->'
S5_CLOSE = '<!-- /B2D-S5 -->'
S1_MARK = '<!-- B2D-S1: actives -->'
BLOCK9 = '<!-- Block 9: How We Work -->'
# The spectable section has two different literal forms and they must not be
# confused: the template carries the block's own JSON, the rendered page
# carries the section tag (with core's extra layout classes appended).
SPEC_PAGE_OPEN = '<section class="wp-block-group sf-spectable '
SPEC_TPL_OPEN = ('<!-- wp:group {"tagName":"section","className":"sf-spectable"'
                 ',"layout"')

S5_PAGE_RE = re.compile(
    r'\n\n\n' + re.escape(S5_OPEN) + r'[\s\S]*?' + re.escape(S5_CLOSE)
    + r'\n\n\n(?=<section id="formulas")')
SPEC_PAGE_RE = re.compile(
    r'</section>\n\n\n\n' + re.escape(SPEC_PAGE_OPEN) + r'[\s\S]*?</section>'
    + r'\n\n\n' + re.escape(S1_MARK) + r'\n\n'
    + r'<section id="actives" [\s\S]*?</section>\n\n\n'
    + r'(?=' + re.escape(BLOCK9) + r')')

# The dosage page meta paragraph, and the formula page's hero meta line.
META_RE = re.compile(r'<p class="sf-formula-hero__meta">([^<]*)</p>')
DETAIL_META_RE = re.compile(r'<p class="sf-formula-hero__meta">[^<]*</p>')

# --- the source-side edits, declared --------------------------------------
VER_CSS = ('Version: 2.10.51', 'Version: 2.10.52')
VER_PHP = ("array(), '2.10.51');", "array(), '2.10.52');")


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


def expected_diff_pages(names):
    """Every page served by a dosage template or by a formula post.

    21 formula posts x 2 languages, 8 dosage templates x 2 languages. Named
    from the capture rather than hard-coded so a page that stopped being
    fetched cannot quietly shrink the expectation.
    """
    return {n for n in names if re.match(r'^(zh__)?(products|formulas)__', n)}


def page_reduce(name, base_norm, cand_norm, fails, say):
    """Undo this batch on one page; return True when it reproduces the other.

    The direction is set by which side the batch's content lives on. This is a
    deletion batch, so for a dosage page the three spans are in the BASE and
    the reduction runs there: base minus the spans must equal the candidate.
    For a formula page the batch's effect is the shortened hero meta, which is
    in the CANDIDATE, so the full line goes back on and the result must equal
    the base. Getting this backwards (it was, in the first version) cannot be
    detected by counting: the run still produced 58 findings.
    """
    if re.match(r'^(zh__)?products__', name):
        basepage, cand = base_norm, cand_norm
        n_s5 = len(S5_PAGE_RE.findall(basepage))
        n_sp = len(SPEC_PAGE_RE.findall(basepage))
        if n_s5 != 1 or n_sp != 1:
            fails.append('%s: expected exactly one band span and one '
                         'spectable+actives span in the base, found %d and %d'
                         % (name, n_s5, n_sp))
            say('    !! %s: spans in the base %d (band) / %d (spectable+actives)'
                % (name, n_s5, n_sp))
            return False
        band = S5_PAGE_RE.search(basepage).group(0)
        spec = SPEC_PAGE_RE.search(basepage).group(0)
        ok_band = ('class="sf-facts__table"' in band
                   and 'sf-facts__answer' in band
                   and band.count('<th scope="row">') == 5
                   and '<h2' not in band)
        ok_spec = ('sf-spectable__table' in spec and 'data-label="MOQ"' in spec
                   and S1_MARK in spec and 'sf-actives' in spec)
        survivors = [s for s in ('Frequently Asked Questions', 'How We Work',
                                 'Related Dosage Forms', 'sf-formulas',
                                 'configurator') if s in band or s in spec]
        if not ok_band or not ok_spec or survivors:
            fails.append('%s: the spans do not look like the deleted sections '
                         '(band ok %s, spec ok %s, survivors %r)'
                         % (name, ok_band, ok_spec, survivors))
            say('    !! %s: band ok %s / spec ok %s / survivors %r'
                % (name, ok_band, ok_spec, survivors))
            return False
        # the other half of the proof: nothing of the batch may be left on the
        # candidate side, and the sections that survive have to be there.
        left = [tok for tok in (S5_OPEN, S5_CLOSE, SPEC_PAGE_OPEN, S1_MARK,
                                'sf-spectable', 'sf-facts')
                if tok in cand]
        if left:
            fails.append('%s: the candidate still carries %r'
                         % (name, left))
            say('    !! %s: candidate still carries %r' % (name, left))
            return False
        for keep in ('<section id="formulas"', 'configurator',
                     'Frequently Asked Questions', 'How We Work',
                     'Related Dosage Forms'):
            if keep not in cand:
                fails.append('%s: the candidate lost %r' % (name, keep))
                say('    !! %s: candidate lost %r' % (name, keep))
                return False
        # the joins, from the new template's own structure: hero -> #formulas
        # keeps four newlines; configurator -> the Block 9 comment keeps three.
        reduced = S5_PAGE_RE.sub('\n\n\n\n', basepage, count=1)
        reduced = SPEC_PAGE_RE.sub('</section>\n\n\n', reduced, count=1)
        return reduced == cand

    # formula page: the hero meta line degrades to the form label alone
    # (functions.php: meta_bits, implode(' · ')), so put the full line back.
    basepage, cand = base_norm, cand_norm
    asked = DETAIL_META_RE.findall(basepage)
    if len(asked) != 1 or ' \u00b7 ' not in asked[0]:
        fails.append('%s: base hero meta is not a single "label · ..." line'
                     % name)
        say('    !! %s: base meta %r' % (name, asked))
        return False
    label = META_RE.search(asked[0]).group(1).split(' \u00b7 ')[0]
    want = '<p class="sf-formula-hero__meta">%s</p>' % label
    got = DETAIL_META_RE.findall(cand)
    if len(got) != 1:
        fails.append('%s: candidate has %d hero meta lines' % (name, len(got)))
        say('    !! %s: candidate has %d meta line(s)' % (name, len(got)))
        return False
    if got[0] != want:
        fails.append('%s: candidate hero meta is %r, expected exactly %r'
                     % (name, got[0], want))
        say('    !! %s: candidate meta %r, expected %r' % (name, got[0], want))
        return False
    return cand.replace(got[0], asked[0], 1) == basepage


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
    ap.add_argument('--from-ver', default='2.10.51')
    ap.add_argument('--to-ver', default='2.10.52')
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

    def lit(pair):
        old, new = pair
        return (old, new % args.to_ver) if '%s' in new else (old, new)

    say('=' * 78)
    say('Batch 2D step E — gates for deleting sf-facts / sf-spectable / B2D-S1')
    say('                 from the eight dosage pages, %s -> %s'
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
    say('    dosage pages: the spans live on the base side, so base minus the '
        'spans must equal the candidate')
    say('    formula pages: the batch\'s effect is the shortened hero meta, so '
        'putting the full line back must equal the base')
    confined = 0
    for name in sorted(expect):
        if name not in new or name not in base:
            continue
        b, n = norm(base[name]), norm(new[name])
        ok = page_reduce(name, b, n, fails, say)
        if ok:
            confined += 1
        else:
            say('    DIFF %s does not reduce to the base page' % name)
            fails.append('%s: undoing the batch does not reproduce the base'
                         % name)
    say('    %d/%d page(s) reduce to the base byte-for-byte'
        % (confined, len(expect)))

    # ---- gate 4: source-level reconstruction -----------------------------
    say('\n[4] style.css / functions.php / the eight templates — '
        'reconstruction')
    say('    each file: undo the declared edits, then compare to the source '
        'the batch started from.')
    say('    A declaration is (restore_this, currently_present); restore_this '
        'of None means a pure insertion, so the literal is deleted.')
    say('')
    jobs = [('style.css', args.base_css, args.new_css, [lit(VER_CSS)]),
            ('functions.php', args.base_php, args.new_php, [lit(VER_PHP)])]
    for label, bpath, npath, declared in jobs:
        braw = open(bpath, encoding='utf-8').read()
        nraw = open(npath, encoding='utf-8').read()
        undone, all_applied = nraw, True
        for old, newlit in declared:
            if newlit == '':
                fails.append('%s: a declared literal is empty, which cannot be '
                             'undone unambiguously' % label)
                all_applied = False
                continue
            n_occ = undone.count(newlit)
            if n_occ != 1:
                fails.append('%s: declared new text occurs %d time(s), expected 1'
                             % (label, n_occ))
                say('    %-24s !! declared literal occurs %d time(s): %r'
                    % (label, n_occ, newlit[:60]))
                all_applied = False
                continue
            undone = undone.replace(newlit, '' if old is None else old, 1)
        same_file = all_applied and undone == braw
        say('    %-24s base %6d / new %6d / undone %6d  applied:%-3s  '
            'undone==base:%s'
            % (label, len(braw.encode()), len(nraw.encode()),
               len(undone.encode()), 'YES' if all_applied else 'NO',
               'YES' if same_file else 'NO'))
        if not same_file:
            fails.append('%s: reconstruction does not reproduce the base '
                         'byte-for-byte' % label)

    # The templates are recomputed here from the markers — deliberately not
    # imported from the apply tool, so the two implementations have to agree.
    for s in DOSAGES:
        label = 'templates/page-%s.html' % s
        braw = open(os.path.join(args.base_tpl_dir, 'page-%s.html' % s),
                    encoding='utf-8').read()
        nraw = open(os.path.join(args.new_tpl_dir, 'page-%s.html' % s),
                    encoding='utf-8').read()
        problems = []
        if braw.count(S5_OPEN) != 1 or braw.count(S5_CLOSE) != 1:
            problems.append('band markers not (1,1) in the base template')
        if braw.count(SPEC_TPL_OPEN) != 1:
            problems.append('spectable group JSON not found once in the base')
        if braw.count(BLOCK9) != 1:
            problems.append('Block 9 anchor not found once in the base')
        if braw.count(S1_MARK) != 1:
            problems.append('B2D-S1 marker not found once in the base')
        if problems:
            for p in problems:
                fails.append('%s: %s' % (label, p))
                say('    %-24s !! %s' % (label, p))
            continue
        s0 = braw.index(S5_OPEN)
        e0 = braw.index(S5_CLOSE) + len(S5_CLOSE)
        if braw[e0:e0 + 2] != '\n\n':
            fails.append('%s: the band close marker is not followed by the '
                         'blank line the deletion assumes' % label)
            say('    %-24s !! no blank line after %s' % (label, S5_CLOSE))
            continue
        d_band = braw[s0:e0 + 2]
        # the spectable group JSON is written as {"tagName":...,"layout"...}
        d_spec = braw[braw.index(SPEC_TPL_OPEN):braw.index(BLOCK9)]
        # what is being deleted has to look like the sections, and nothing
        # that survives may be inside a deleted span.
        for code, blob, needles in (('band', d_band, ('sf-facts', S5_OPEN)),
                                    ('spectable+actives', d_spec,
                                     ('sf-spectable', S1_MARK,
                                      '[sf_formula_actives form="%s"]' % s))):
            for needle in needles:
                if needle not in blob:
                    fails.append('%s: deleted %s span lacks %r'
                                 % (label, code, needle))
        for survivor in ('Frequently Asked Questions', 'How We Work',
                         'Related Dosage Forms'):
            if survivor in d_band or survivor in d_spec:
                fails.append('%s: a deleted span contains survivor content %r'
                             % (label, survivor))
        undone = braw.replace(d_band, '', 1).replace(d_spec, '', 1)
        same_file = undone == nraw
        say('    %-24s base %6d / new %6d / undone %6d  applied:YES  '
            'undone==base:%s  (-%d B in two spans)'
            % (label, len(braw.encode()), len(nraw.encode()),
               len(undone.encode()), 'YES' if same_file else 'NO',
               len(braw.encode()) - len(nraw.encode())))
        if not same_file:
            fails.append('%s: reconstruction does not reproduce the base '
                         'byte-for-byte' % label)
            k = next((i for i in range(min(len(undone), len(nraw)))
                      if undone[i] != nraw[i]), min(len(undone), len(nraw)))
            say('        first mismatch @%d' % k)
            say('          undone:', repr(undone[max(0, k - 60):k + 40]))
            say('          new   :', repr(nraw[max(0, k - 60):k + 40]))

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
            'once the batch is undone;' % len(expect))
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

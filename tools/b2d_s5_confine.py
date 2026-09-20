#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch 2D step 5 — the gates for the core-facts band on the eight dosage
pages: a new top-level section between the hero and #formulas, plus the How We
Work wording change, plus the 2.10.50 -> 2.10.51 bump in the two places that
must stay in step.

Shape is b2d_s4c_confine.py's, extended to a <em>mixed</em> batch. Step 4c was
one declaration in one file; this one adds a band to eight templates, edits one
sentence inside those same eight, appends CSS and moves a version. So the
reconstruction runs in two places:

  * source level — for each of the eight templates, undo the sentence and delete
    the inserted block, and the file must come back byte-identical to the one
    commit cc21dfc replaced. This is the "delete the band, restore the sentence"
    proof in its cheapest form, and it is the one that cannot be fooled by
    rendering.

  * page level — on the fetched captures, delete the band's rendered span and
    revert the sentence; the page must come back byte-identical to the base
    capture. This is what proves the band is the <em>only</em> thing that moved
    on those pages, at the byte level, after masking.

Gates:
  1. resource inventory. Exactly style.css moves, on all 75 pages, 2.10.50 ->
     2.10.51, and no other asset moves. Exits non-zero when NOTHING moved, so a
     run that compared a directory with itself cannot read as a pass.
  2. masked byte comparison with ?ver= folded, with an exact expected-diff set:
     the 8 English dosage pages and their 8 /zh/ twins must differ, and the
     other 59 pages must be byte-identical. Then the confinement reconstruction
     on each of the 16: remove the band's span, restore the sentence, and the
     page must equal the base capture byte for byte.
  3. style.css reconstruction: restore the version, delete the appended block.
  4. functions.php reconstruction: restore the enqueue version.
  5. the eight templates: restore the sentence, delete the inserted block.
  6. JSON-LD deep-equal on all 75 pages.

Four separate files are reconstructed rather than one because each carries a
different kind of declaration, and a single "undone == base" verdict over a
concatenation of them would not say which one broke.

usage:
    python3 tools/b2d_s5_confine.py --base-dir DIR --new-dir DIR \\
        --base-css F --new-css F --base-php F --new-php F \\
        --base-tpl-dir DIR --new-tpl-dir DIR [--report F]
"""
import argparse
import hashlib
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
FORMULAS_OPEN = '<section id="formulas"'

# The band's own markers. Author comments survive rendering (block delimiters do
# not), which is what makes them usable as span boundaries; the two blank-line
# runs around them are the whitespace the insertion contributed to the seam.
M_OPEN = '<!-- B2D-S5: core facts -->'
M_CLOSE = '<!-- /B2D-S5 -->'
BAND_SPAN_RE = re.compile(r'(\n+)' + re.escape(M_OPEN) + r'.*?' + re.escape(M_CLOSE) + r'(\n+)', re.S)
SEP_RE = re.compile(r'\n+' + re.escape(FORMULAS_OPEN))

# Declared edits, as (base literal -> new literal) with %s for the version.
VER_CSS = ('Version: 2.10.50', 'Version: %s')
VER_PHP = ("array(), '2.10.50');", "array(), '%s');")
SENT_OLD = 'delivered in 3\u20137 days.'
SENT_NEW = 'delivered in 3\u20137 working days.'

# The whole CSS block this step appends, taken from the source of truth rather
# than retyped: tools/b2d_s5_apply.py owns it, and a copy here would be the
# second place to keep in step.
sys.path.insert(0, HERE)
import b2d_s5_apply  # noqa: E402
CSS_ADDITION = b2d_s5_apply.CSS_ADDITION

# What the eight templates gained, per file. Recomputed from the same module so
# the two tools cannot disagree about what was inserted.
def inserted_block(slug):
    return b2d_s5_apply.block(slug)


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


def expected_diff_pages():
    """The band is in a template, and each dosage template serves two URLs."""
    out = set()
    for s in DOSAGES:
        out.add('products__%s.html' % s)
        out.add('zh__products__%s.html' % s)
    return out


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
    ap.add_argument('--from-ver', default='2.10.50')
    ap.add_argument('--to-ver', default='2.10.51')
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

    css_declared = [lit(VER_CSS), ('', CSS_ADDITION)]
    php_declared = [lit(VER_PHP)]

    say('=' * 78)
    say('Batch 2D step 5 — gates for the core-facts band + Direct Answer,')
    say('                 and the How We Work wording change, %s -> %s'
        % (args.from_ver, args.to_ver))
    say('=' * 78)

    base, new = load(args.base_dir), load(args.new_dir)
    say('\n[0] inputs')
    say('    base dir %s : %d pages' % (args.base_dir, len(base)))
    say('    new  dir %s : %d pages' % (args.new_dir, len(new)))
    if len(base) != 75 or len(new) != 75:
        fails.append('expected 75 pages on each side, got %d / %d' % (len(base), len(new)))
    expect = expected_diff_pages()
    say('    expected to differ: %d page(s) (8 dosage pages + their /zh/ twins)' % len(expect))

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
                moved.setdefault(asset, {}).setdefault((vb[asset], vn[asset]), []).append(name)
    if not moved:
        fails.append('NOTHING moved — the two directories have identical version '
                     'tokens, so this gate proved nothing (is --new pointing at base?)')
    for asset, transitions in sorted(moved.items()):
        for (vbase, vnew), pages in sorted(transitions.items()):
            say('    %-18s %s -> %-9s on %d page(s)' % (asset, vbase, vnew, len(pages)))
            if asset != 'style.css':
                fails.append('unexpected asset moved: %s %s->%s' % (asset, vbase, vnew))
            if (vbase, vnew) != (args.from_ver, args.to_ver):
                fails.append('style.css moved %s->%s, expected %s->%s'
                             % (vbase, vnew, args.from_ver, args.to_ver))
            if len(pages) != 75:
                fails.append('style.css moved on %d pages, expected 75' % len(pages))
    say('    asset SET changed on %d page(s) (must be 0)' % len(set_changed))
    if set_changed:
        fails.append('asset set changed on: %s' % ', '.join(set_changed[:6]))

    # ---- gate 2: masked comparison + confinement -------------------------
    say('\n[2] masked comparison of the 75 pages (?ver= folded)')
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
        say('    !! %s should have differed and did not — the band is missing there' % name)
        fails.append('%s should have differed and did not' % name)

    say('\n    confinement: delete the band\'s span, restore the sentence, compare to base')
    confined = 0
    for name in sorted(expect):
        if name not in new or name not in base:
            continue
        b, n = norm(base[name]), norm(new[name])
        m = BAND_SPAN_RE.search(n)
        if not m:
            fails.append('%s: the band span is not present (markers %r .. %r)'
                         % (name, M_OPEN, M_CLOSE))
            say('    !! %s: no band span found' % name)
            continue
        span = m.group(0)
        body = span[len(m.group(1)):len(span) - len(m.group(2))]
        # the span must actually contain the band, not just the markers
        ok_span = (len(body) > 900
                   and 'class="sf-facts__table"' in body
                   and 'class="sf-facts__answer"' in body
                   and body.count('<th scope="row">') == 5)
        if not ok_span:
            fails.append('%s: the span between the markers does not look like the band '
                         '(%d bytes, %d row headers)' % (name, len(body), body.count('<th scope="row">')))
            say('    !! %s: span is %d bytes, %d row headers'
                % (name, len(body), body.count('<th scope="row">')))
        # base's own separator between the hero and #formulas: the insertion
        # split that newline run in two, so restoring means re-joining it
        sm = SEP_RE.search(b)
        if not sm:
            fails.append('%s: base carries no newline run before %s'
                         % (name, FORMULAS_OPEN))
            continue
        base_sep = sm.group(0)[:-len(FORMULAS_OPEN)]
        cand2 = n[:m.start(1)] + base_sep + n[m.end(2):]
        # the sentence, and only now that the band is gone is it unique
        n_sent = cand2.count(SENT_NEW)
        if n_sent != 1:
            fails.append('%s: "delivered in 3-7 working days" occurs %d time(s) after '
                         'the band is removed, expected 1' % (name, n_sent))
            say('    !! %s: sentence literal occurs %d time(s)' % (name, n_sent))
            continue
        cand3 = cand2.replace(SENT_NEW, SENT_OLD, 1)
        if cand3 == b:
            confined += 1
        else:
            k = next((i for i in range(min(len(cand3), len(b))) if cand3[i] != b[i]),
                     min(len(cand3), len(b)))
            say('    DIFF %s @%d (cand has %d bytes, base has %d)'
                % (name, k, len(cand3.encode()), len(b.encode())))
            say('      cand:', repr(cand3[max(0, k - 70):k + 50]))
            say('      base:', repr(b[max(0, k - 70):k + 50]))
            fails.append('%s: removing the band and restoring the sentence does not '
                         'reproduce the base page' % name)
    say('    %d/%d page(s) reduce to the base byte-for-byte' % (confined, len(expect)))

    # ---- gates 3-5: reconstruction ---------------------------------------
    tpl_pairs = [('templates/page-%s.html' % s,
                  os.path.join(args.base_tpl_dir, 'page-%s.html' % s),
                  os.path.join(args.new_tpl_dir, 'page-%s.html' % s),
                  [(SENT_NEW, SENT_OLD), (inserted_block(s), '')])
                 for s in DOSAGES]
    jobs = ([('style.css', args.base_css, args.new_css, css_declared),
             ('functions.php', args.base_php, args.new_php, php_declared)]
            + tpl_pairs)
    say('\n[3] style.css / functions.php / the eight templates — reconstruction')
    say('    each file: undo the declared edits, then compare to the file commit')
    say('    cc21dfc replaced. Every declared literal must occur exactly once.')
    say('')
    for label, bpath, npath, declared in jobs:
        braw = open(bpath, encoding='utf-8').read()
        nraw = open(npath, encoding='utf-8').read()
        undone = nraw
        all_applied = True
        for old, newlit in declared:
            n_occ = undone.count(newlit)
            if n_occ != 1:
                fails.append('%s: declared new text occurs %d time(s), expected 1'
                             % (label, n_occ))
                say('    %-28s !! declared literal occurs %d time(s): %r'
                    % (label, n_occ, newlit[:60]))
                all_applied = False
                continue
            undone = undone.replace(newlit, old, 1)
        same_file = all_applied and undone == braw
        say('    %-28s base %6d / new %6d / undone %6d  applied:%-3s  undone==base:%s'
            % (label, len(braw.encode()), len(nraw.encode()), len(undone.encode()),
               'YES' if all_applied else 'NO', 'YES' if same_file else 'NO'))
        if not same_file:
            fails.append('%s: reconstruction does not reproduce the base byte-for-byte' % label)
            if all_applied:
                for k in range(min(len(undone), len(braw))):
                    if undone[k] != braw[k]:
                        say('        first mismatch @%d' % k)
                        say('          undone:', repr(undone[max(0, k - 60):k + 40]))
                        say('          base  :', repr(braw[max(0, k - 60):k + 40]))
                        break

    # ---- gate 6: JSON-LD deep-equal -------------------------------------
    say('\n[6] JSON-LD deep-equal (decoded structures, not masked text)')
    ld_bad, ld_pages = [], 0
    for name in sorted(base):
        if name not in new:
            continue
        lb, ln = ld_blocks(base[name]), ld_blocks(new[name])
        ld_pages += 1
        if lb != ln:
            ld_bad.append(name)
            if len(ld_bad) == 1:
                say('    DIFF %s' % name)
                say('      base: %s' % json.dumps(lb, ensure_ascii=False)[:400])
                say('      new : %s' % json.dumps(ln, ensure_ascii=False)[:400])
    say('    identical %d/%d page(s)' % (ld_pages - len(ld_bad), ld_pages))
    if ld_pages == 0:
        fails.append('no pages compared in gate 6')
    if ld_bad:
        fails.append('%d page(s) differ in JSON-LD: %s' % (len(ld_bad), ', '.join(ld_bad[:6])))

    say('\n' + '=' * 78)
    if fails:
        say('FAIL — %d problem(s):' % len(fails))
        for f in fails:
            say('  * %s' % f)
    else:
        say('PASS — style.css is base + the appended block and the version bump;')
        say('       functions.php is base + the enqueue bump;')
        say('       all eight templates are base + the band + the sentence change;')
        say('       16/16 changed pages reduce to base once the band is removed;')
        say('       59/59 other pages byte-identical after ?ver= is folded;')
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

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch 2D step 4b — the gates for a one-declaration CSS change.

The change under test is deliberately tiny: `.sf-fdetail__grid--solo` gains
`margin-inline: 0`, and the theme version moves 2.10.48 -> 2.10.49 in the two
places that must stay in step. Small changes are exactly where a gate is most
likely to be an empty check, so each gate below is written to fail loudly when
it has nothing to look at.

Four gates:

  1. resource inventory (base vs candidate). A version bump rewrites the
     stylesheet's cache token on EVERY page, so a whole-site byte comparison
     can never be SAME afterwards — and blanket-masking "?ver=" would equally
     hide an accidental version change on some other asset. This gate names
     the moved tokens instead: exactly style.css must move, on all 75 pages,
     2.10.48 -> 2.10.49, and no other asset may move at all. It exits non-zero
     when NOTHING moved, so a run that compared a directory with itself cannot
     read as a pass.

  2. masked byte comparison of the 75 pages, with ?ver= folded. After gate 1
     has accounted for the version token, everything else on every page must
     be byte-identical — this is what proves a CSS-only change never touched
     the markup. Order matters (see b2d_s3_confine.normalize): the shared
     Cloudflare/Gravity-Forms masks run first, then ?ver=.

  3. CSS reconstruction (the confinement claim, inverted for a one-line add).
     Take the NEW style.css, undo exactly the declared edits — delete the
     added comment lines, delete `margin-inline: 0;`, put 2.10.48 back — and
     the result must be byte-identical to the BASE style.css. Anything the
     change did that was not declared survives the undo and shows up as a
     mismatch, so this proves the file is base + the two declared edits and
     nothing else.

  4. the same reconstruction for functions.php (the enqueue version).

    python3 tools/b2d_s4b_confine.py --base-dir DIR --new-dir DIR \\
        --base-css F --new-css F --base-php F --new-php F [--report F]
"""
import argparse
import hashlib
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from b2d_s3_confine import masked, load  # noqa: E402  (shared mask set + loader)

VER_RE = re.compile(r'\?ver=[0-9A-Za-z._-]+')
VER_MASK = '?ver=MASK'
PAIR = re.compile(r'''(?:href|src)=["']([^"']+?)\?ver=([^"'&]+)''')

# The declared edits, as (base -> new) literals. Kept as data rather than as a
# regex so the undo is an exact string operation.
CSS_DECLARED = [
    ('Version: 2.10.48', 'Version: 2.10.49'),
    ("""   to several cards keeps its unconstrained auto-fit behaviour. */\n.sf-fdetail__grid--solo {\n\tmax-width: 560px;\n}\n""",
     """   to several cards keeps its unconstrained auto-fit behaviour.\n\n"""
     """   margin-inline is not redundant. The block sits inside a core\n"""
     """   `is-layout-constrained` container, and core sets\n"""
     """   `margin-left/-right: auto` on such children (via :where(), so specificity\n"""
     """   is 0 and this rule wins). With a 560px cap inside a 1200px measure that\n"""
     """   auto pair parked the single card at x=440 — measured on /formulas/ear-care-drops/\n"""
     """   at 1440. Left-aligning keeps the card on the same left edge as the\n"""
     """   Specification heading, the gallery band and every other band on the page. */\n"""
     """.sf-fdetail__grid--solo {\n\tmax-width: 560px;\n\tmargin-inline: 0;\n}\n"""),
]
PHP_DECLARED = [
    ("wp_enqueue_style('sinofresh-style', get_stylesheet_uri(), array(), '2.10.48');",
     "wp_enqueue_style('sinofresh-style', get_stylesheet_uri(), array(), '2.10.49');"),
]


def norm(html):
    """Shared masks first, then the version token — never the other way round.

    Reversing the two was a real bug in an earlier batch: the version pattern
    would run over un-masked text and a `>` inside a masked token could cut a
    following tag pattern short.
    """
    return VER_RE.sub(VER_MASK, masked(html)[0])


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def ver_map(html):
    """{asset basename: version} for every ?ver= token on the page."""
    return {os.path.basename(u).split('?')[0]: v for u, v in PAIR.findall(html)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base-dir', required=True)
    ap.add_argument('--new-dir', required=True)
    ap.add_argument('--base-css', required=True)
    ap.add_argument('--new-css', required=True)
    ap.add_argument('--base-php', required=True)
    ap.add_argument('--new-php', required=True)
    ap.add_argument('--report', default=None)
    args = ap.parse_args()

    lines, fails = [], []

    def say(*parts):
        # Variadic: the mismatch dump below passes a label and a repr() as two
        # arguments. Declared as say(s='') this raised TypeError on the very
        # path that exists to explain a failure — i.e. the bug could only ever
        # hide a problem, never invent one.
        s = ' '.join(str(p) for p in parts)
        print(s)
        lines.append(s)

    say('=' * 74)
    say('Batch 2D step 4b — gates for `margin-inline: 0` on .sf-fdetail__grid--solo')
    say('=' * 74)

    base, new = load(args.base_dir), load(args.new_dir)
    say('\n[0] inputs')
    say('    base dir %s : %d pages' % (args.base_dir, len(base)))
    say('    new  dir %s : %d pages' % (args.new_dir, len(new)))
    if len(base) != 75 or len(new) != 75:
        fails.append('expected 75 pages on each side, got %d / %d' % (len(base), len(new)))

    # ---- gate 1: resource inventory -------------------------------------
    # A changed token is ONE transition, not a removal plus an addition. The
    # first version of this gate used set differences, which printed
    # "2.10.48->?" and "?->2.10.49" as two separate findings and then failed
    # its own assertion — a harness bug that read like a product bug. Compare
    # per-asset versions instead, so a move is reported as base->new.
    say('\n[1] resource inventory (which cache tokens moved?)')
    moved = {}            # asset -> {(base_ver, new_ver): [pages]}
    set_changed = []      # pages where the asset SET itself differs
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
            if (vbase, vnew) != ('2.10.48', '2.10.49'):
                fails.append('style.css moved %s->%s, expected 2.10.48->2.10.49' % (vbase, vnew))
            if len(pages) != 75:
                fails.append('style.css moved on %d pages, expected 75' % len(pages))
    say('    asset SET changed on %d page(s) (must be 0)' % len(set_changed))
    if set_changed:
        fails.append('asset set changed on: %s' % ', '.join(set_changed[:6]))

    # ---- gate 2: masked byte comparison ---------------------------------
    say('\n[2] masked comparison of the 75 pages (?ver= folded)')
    diff = []
    for name in sorted(base):
        if name not in new:
            continue
        a, b = norm(base[name]), norm(new[name])
        if a != b:
            i = next((k for k in range(min(len(a), len(b))) if a[k] != b[k]), min(len(a), len(b)))
            diff.append((name, i, a[max(0, i - 70):i + 50], b[max(0, i - 70):i + 50]))
    say('    identical %d/%d' % (len(base) - len(diff), len(base)))
    for name, i, ca, cb in diff[:5]:
        say('    DIFF %s @%d' % (name, i))
        say('      base:', repr(ca))
        say('      new :', repr(cb))
    if diff:
        fails.append('%d page(s) differ after masking' % len(diff))

    # ---- gate 3/4: reconstruction (undo the declared edits) --------------
    for label, bpath, npath, declared in (
            ('style.css', args.base_css, args.new_css, CSS_DECLARED),
            ('functions.php', args.base_php, args.new_php, PHP_DECLARED)):
        say('\n[%d] %s reconstruction (undo the declared edits)' % (3 if label == 'style.css' else 4, label))
        braw = open(bpath, encoding='utf-8').read()
        nraw = open(npath, encoding='utf-8').read()
        undone = nraw
        # A vacuous reconstruction must not be able to print YES. When the
        # declared new text is absent nothing is undone, so `undone` stays
        # equal to `nraw`; if `nraw` happens to equal the base (the negative
        # control, where --new points at base) the naive comparison prints
        # "undone == base : YES" for a file it never touched. Track whether
        # every declaration was actually applied and fold that into the verdict.
        all_applied = True
        for old, newlit in declared:
            if newlit not in undone:
                fails.append('%s: the declared new text is not present, cannot undo it' % label)
                say('    !! declared new text absent — the edit is not what was declared')
                all_applied = False
                continue
            undone = undone.replace(newlit, old, 1)
        same = all_applied and undone == braw
        say('    base bytes %d / new bytes %d / undone bytes %d' % (
            len(braw.encode()), len(nraw.encode()), len(undone.encode())))
        say('    every declaration applied : %s' % ('YES' if all_applied else 'NO'))
        say('    undone == base : %s   (%s)' % (
            'YES' if same else 'NO',
            (hashlib.sha256(undone.encode()).hexdigest()[:16] + ' vs ' +
             hashlib.sha256(braw.encode()).hexdigest()[:16]) if all_applied
            else 'not comparable — nothing was undone'))
        if not same:
            fails.append('%s: reconstruction does not reproduce the base byte-for-byte' % label)
            for k in range(min(len(undone), len(braw))):
                if undone[k] != braw[k]:
                    say('    first mismatch @%d' % k)
                    say('      undone:', repr(undone[max(0, k - 60):k + 40]))
                    say('      base  :', repr(braw[max(0, k - 60):k + 40]))
                    break

    say('\n' + '=' * 74)
    if fails:
        say('FAIL — %d problem(s):' % len(fails))
        for f in fails:
            say('  * %s' % f)
    else:
        say('PASS — style.css is base + the two declared edits, byte for byte;')
        say('       functions.php is base + the enqueue bump;')
        say('       75/75 pages identical once the version token is folded.')
    say('=' * 74)

    if args.report:
        os.makedirs(os.path.dirname(args.report) or '.', exist_ok=True)
        with open(args.report, 'w', encoding='utf-8') as fh:
            fh.write('\n'.join(lines) + '\n')
        print('\nreport -> %s' % args.report)
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())

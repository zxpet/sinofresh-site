#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch 2D step 4c — the gates for the `--solo` cap moving from the box to
the track, plus the 2.10.49 -> 2.10.50 version bump in the two places that
must stay in step.

Same shape as b2d_s4b_confine.py (a one-declaration change still gets the full
treatment), with two differences that matter:

  * `--from-ver` selects which declared-edit set is undone. The change under
    test lands on top of the PREVIOUS candidate (2.10.49, commit effa435),
    which the live theme never served; verifying the step in isolation keeps
    each link of the chain small enough to read. The same file can also be
    pointed at the live 2.10.48 baseline (`--from-ver 2.10.48`) to check the
    whole pending delta in one hop.

  * gate 5 parses every application/ld+json block on every page and compares
    the decoded structures. The dosage pages build their Product/Organization
    schema by regex-scanning the rendered markup (so a new element that
    happens to look like the term/value span pair could silently rewrite the
    schema), and the masked gate cannot see that: masking folds whole tokens,
    not JSON fields.

Gates:

  1. resource inventory. Exactly style.css moves, on all 75 pages, from
     `--from-ver` to `--to-ver`, and no other asset moves. Exits non-zero when
     NOTHING moved, so a run that compared a directory with itself cannot read
     as a pass.

  2. masked byte comparison of the 75 pages with ?ver= folded. Order matters
     (see b2d_s3_confine.normalize): shared masks first, then the version
     token.

  3. style.css reconstruction (the confinement claim). Undo exactly the
     declared edits on the NEW file — put `--from-ver` back, delete the added
     comment paragraph, restore the previous rule body — and the result must
     be byte-identical to the BASE file. Every declared literal must also be
     present in the new file exactly once; a declaration that never applied
     proves nothing and is reported as such rather than counting as a pass.

  4. the same reconstruction for functions.php (the enqueue version).

  5. JSON-LD deep-equal: every decoded ld+json structure on every page.

    python3 tools/b2d_s4c_confine.py --base-dir DIR --new-dir DIR \\
        --base-css F --new-css F --base-php F --new-php F \\
        --from-ver 2.10.49 [--to-ver 2.10.50] [--report F]
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

# --- the NEW file's text, as literals ---------------------------------------
# The tail of the pre-existing comment, which every earlier revision ends on.
TAIL_ANCHOR = "   to several cards keeps its unconstrained auto-fit behaviour."

# The paragraph this step adds, i.e. the finding the hard way: a max-width can
# only be centred by core's auto margins, forcing them off is a no-op, and past
# them the card lands on the section's content-box edge instead of on the
# page's left edge. Sizing the track is what actually moves it.
NEW_PARA = (
    "\n   The cap is expressed as the track width, not as a max-width on the box.\n"
    "   A max-width plus auto margins — which is what a constrained-layout child\n"
    "   gets — can only centre the box: with a 560px cap inside a 1200px measure\n"
    "   the single card parked at x=440 on /formulas/ear-care-drops/ at 1440,\n"
    "   while x=120 is the left edge every heading and band on the page shares.\n"
    "   Forcing the auto margins off (margin-inline: 0) is a no-op — core locks\n"
    "   them with !important — and past it the card lands at x=38, the section's\n"
    "   has-background content-box edge. Sizing the track instead leaves the\n"
    "   grid's own centring untouched and puts the card at x=120, width 560."
)

NEW_RULE = ".sf-fdetail__grid--solo {\n\tgrid-template-columns: minmax(0, 560px);\n}"
NEW_ENQ = ("wp_enqueue_style('sinofresh-style', get_stylesheet_uri(), array(), "
           "'%s');")

# --- the declared-edit sets, as (base -> new) literal pairs -----------------
# For 2.10.49 the base carried a second comment paragraph; for 2.10.48 the
# comment stopped at the anchor and the rule held only the max-width.
CSS_PARA_49 = (
    "\n   margin-inline is not redundant. The block sits inside a core\n"
    "   `is-layout-constrained` container, and core sets\n"
    "   `margin-left/-right: auto` on such children (via :where(), so specificity\n"
    "   is 0 and this rule wins). With a 560px cap inside a 1200px measure that\n"
    "   auto pair parked the single card at x=440 — measured on /formulas/ear-care-drops/\n"
    "   at 1440. Left-aligning keeps the card on the same left edge as the\n"
    "   Specification heading, the gallery band and every other band on the page."
)
RULE_49 = ".sf-fdetail__grid--solo {\n\tmax-width: 560px;\n\tmargin-inline: 0;\n}"
RULE_48 = ".sf-fdetail__grid--solo {\n\tmax-width: 560px;\n}"

DECLARED = {
    '2.10.49': {
        'css': [
            ('Version: 2.10.49', 'Version: %s'),
            (CSS_PARA_49, NEW_PARA),
            (RULE_49, NEW_RULE),
        ],
        'php': [("array(), '2.10.49');", "array(), '%s');")],
    },
    '2.10.48': {
        'css': [
            ('Version: 2.10.48', 'Version: %s'),
            (TAIL_ANCHOR, TAIL_ANCHOR + NEW_PARA),
            (RULE_48, NEW_RULE),
        ],
        'php': [("array(), '2.10.48');", "array(), '%s');")],
    },
}


def norm(html):
    """Shared masks first, then the version token — never the other way round.

    Reversing the two was a real bug in an earlier batch: the version pattern
    would run over un-masked text and a `>` inside a masked token could cut a
    following tag pattern short.
    """
    return VER_RE.sub(VER_MASK, masked(html)[0])


def ver_map(html):
    """{asset basename: version} for every ?ver= token on the page."""
    return {os.path.basename(u).split('?')[0]: v for u, v in PAIR.findall(html)}


def ld_blocks(html):
    """Every decoded ld+json structure on the page, in document order."""
    out = []
    for raw in LD_RE.findall(html):
        try:
            out.append(json.loads(raw.strip()))
        except Exception as exc:
            out.append({'__unparsed__': str(exc)})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base-dir', required=True)
    ap.add_argument('--new-dir', required=True)
    ap.add_argument('--base-css', required=True)
    ap.add_argument('--new-css', required=True)
    ap.add_argument('--base-php', required=True)
    ap.add_argument('--new-php', required=True)
    ap.add_argument('--from-ver', default='2.10.49', choices=sorted(DECLARED))
    ap.add_argument('--to-ver', default='2.10.50')
    ap.add_argument('--report', default=None)
    args = ap.parse_args()

    def lit(pair):
        old, new = pair
        return (old, new % args.to_ver) if '%s' in new else (old, new)

    css_declared = [lit(p) for p in DECLARED[args.from_ver]['css']]
    php_declared = [lit(p) for p in DECLARED[args.from_ver]['php']]

    lines, fails = [], []

    def say(s=''):
        print(s)
        lines.append(s)

    say('=' * 74)
    say('Batch 2D step 4c — gates for `grid-template-columns: minmax(0, 560px)`')
    say('                on .sf-fdetail__grid--solo, %s -> %s'
        % (args.from_ver, args.to_ver))
    say('=' * 74)

    base, new = load(args.base_dir), load(args.new_dir)
    say('\n[0] inputs')
    say('    base dir %s : %d pages' % (args.base_dir, len(base)))
    say('    new  dir %s : %d pages' % (args.new_dir, len(new)))
    if len(base) != 75 or len(new) != 75:
        fails.append('expected 75 pages on each side, got %d / %d' % (len(base), len(new)))

    # ---- gate 1: resource inventory -------------------------------------
    # A changed token is ONE transition, not a removal plus an addition: the
    # first version of this gate used set differences and printed
    # "X->?" / "?->Y" as two findings, then failed its own assertion. Compare
    # per-asset versions instead.
    say('\n[1] resource inventory (which cache tokens moved?)')
    moved = {}
    set_changed = []
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

    # ---- gate 2: masked byte comparison ---------------------------------
    say('\n[2] masked comparison of the 75 pages (?ver= folded)')
    diff = []
    for name in sorted(base):
        if name not in new:
            continue
        a, b = norm(base[name]), norm(new[name])
        if a != b:
            i = next((k for k in range(min(len(a), len(b))) if a[k] != b[k]),
                     min(len(a), len(b)))
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
            ('style.css', args.base_css, args.new_css, css_declared),
            ('functions.php', args.base_php, args.new_php, php_declared)):
        say('\n[%d] %s reconstruction (undo the declared edits)'
            % (3 if label == 'style.css' else 4, label))
        braw = open(bpath, encoding='utf-8').read()
        nraw = open(npath, encoding='utf-8').read()
        undone = nraw
        # A vacuous reconstruction must not be able to print YES. When the
        # declared new text is absent nothing is undone, so `undone` stays
        # equal to `nraw`; if `nraw` happens to equal the base (the negative
        # control, where --new points at base) the naive comparison prints
        # "undone == base : YES" for a file it never touched. So the verdict
        # also requires that every declaration actually applied — and that it
        # applied exactly once, since a literal that matches twice makes the
        # undo ambiguous.
        all_applied = True
        for old, newlit in declared:
            n_occ = undone.count(newlit)
            if n_occ != 1:
                fails.append('%s: declared new text occurs %d time(s), expected 1'
                             % (label, n_occ))
                say('    !! declared new text occurs %d time(s) — cannot undo unambiguously'
                    % n_occ)
                say('       literal: %r' % newlit[:110])
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

    # ---- gate 5: JSON-LD deep-equal -------------------------------------
    say('\n[5] JSON-LD deep-equal (decoded structures, not masked text)')
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
        fails.append('no pages compared in gate 5')
    if ld_bad:
        fails.append('%d page(s) differ in JSON-LD: %s'
                     % (len(ld_bad), ', '.join(ld_bad[:6])))

    say('\n' + '=' * 74)
    if fails:
        say('FAIL — %d problem(s):' % len(fails))
        for f in fails:
            say('  * %s' % f)
    else:
        say('PASS — style.css is base + the three declared edits, byte for byte;')
        say('       functions.php is base + the enqueue bump;')
        say('       75/75 pages identical once the version token is folded;')
        say('       75/75 pages byte-identical in decoded JSON-LD.')
    say('=' * 74)

    if args.report:
        os.makedirs(os.path.dirname(args.report) or '.', exist_ok=True)
        with open(args.report, 'w', encoding='utf-8') as fh:
            fh.write('\n'.join(lines) + '\n')
        print('\nreport -> %s' % args.report)
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())

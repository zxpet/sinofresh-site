#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch F1 — insert the .sf-facts-mini core-facts row into the eight dosage
templates, at the seam batch 2D-E left behind (hero group close -> the
"formulas" card-wall group), and prove its own undo.

This is an INSERTION batch. The confined proof therefore runs the other way
round from step E: delete the inserted block from the CANDIDATE and it must be
the base byte-for-byte. The deletion span this tool writes is exactly what the
gate recomputes from markers, and the tool refuses to run if the anchors are
not in the expected state.

The block is a wp:html wrapper around section.sf-facts-mini with three items
(MOQ / Lead time / Certifications). Every value span carries data-label, which
is the machine-readable twin sinofresh_formula_spec_cell() reads — the page
stays the single source of truth for the formula-detail hero meta.

No heading: toc-nav.js builds one dot per h2, so an h2 here would silently
grow the dot rail. The rail must stay at 6 (post-2D-E).

usage:
    python3 tools/b2d_f1_apply.py --check
    python3 tools/b2d_f1_apply.py --apply --backup-dir DIR
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
THEME = os.path.join(HERE, '..', 'sinofresh-theme', 'templates')

DOSAGES = "soft-chews tablets powders pastes drops liquids fish-oil dental-chews".split()

# Declared values, transcribed from the sf-spectable tables batch 2D-E deleted
# (git show f4f43b6:.../page-<form>.html, the <td data-label="MOQ"> rows).
# Lead time and Certifications are the same on all eight pages; MOQ is not.
MOQ = {
    'soft-chews':   'from 500\u20131,000 units',
    'tablets':      'from 1,000 units',
    'fish-oil':     'from 1,000 units',
    'dental-chews': 'from 1,000 units',
    'powders':      'from 500 units',
    'pastes':       'from 500 units',
    'drops':        'from 500 units',
    'liquids':      'from 500 units',
}
LEAD = 'Typically 7\u201315 working days after packaging is ready'
CERTS = 'FDA, cGMP, ISO 9001, FSSC 22000, HACCP, BRC'

# The formulas card-wall group open comment — the anchor the block goes in
# front of. Must occur exactly once per template.
ANCHOR = '<!-- wp:group {"tagName":"section","anchor":"formulas"'

BLOCK_HEAD = '<!-- wp:html -->'
BLOCK_TAIL = '<!-- /wp:html -->'


def block_for(form):
    """The exact inserted text, no trailing newline (the join adds the blanks)."""
    item = ('<div class="sf-facts-mini__item">'
            '<span class="sf-facts-mini__label">%s</span> '
            '<span class="sf-facts-mini__value" data-label="%s">%s</span></div>')
    rows = '\n'.join([
        item % ('MOQ', 'MOQ', MOQ[form]),
        item % ('Lead time', 'Lead time', LEAD),
        item % ('Certifications', 'Certifications', CERTS),
    ])
    return '%s\n<section class="sf-facts-mini">\n%s\n</section>\n%s' % (
        BLOCK_HEAD, rows, BLOCK_TAIL)


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--check', action='store_true')
    g.add_argument('--apply', action='store_true')
    ap.add_argument('--backup-dir', default=None,
                    help='with --apply: copy the pre-batch files here first')
    args = ap.parse_args()

    problems = []
    for form in DOSAGES:
        path = os.path.join(THEME, 'page-%s.html' % form)
        if not os.path.isfile(path):
            problems.append('%s: template missing' % form)
            continue
        raw = open(path, encoding='utf-8').read()
        n_anchor = raw.count(ANCHOR)
        if n_anchor != 1:
            problems.append('%s: formulas anchor occurs %d time(s), expected 1'
                            % (form, n_anchor))
            continue
        if 'sf-facts-mini' in raw:
            problems.append('%s: sf-facts-mini already present — not idempotent'
                            % form)
            continue
        if BLOCK_HEAD not in raw:
            problems.append('%s: no wp:html anywhere, unexpected for this theme'
                            % form)
            continue
        block = block_for(form)
        rebuilt = raw.replace(ANCHOR, block + '\n\n' + ANCHOR, 1)
        # the tool's own undo must reproduce the input byte-for-byte; if it
        # does not, the block is not a clean splice and the gate cannot trust
        # the same span.
        if rebuilt.replace(block + '\n\n', '', 1) != raw:
            problems.append('%s: the block is not a clean splice (undo mismatch)'
                            % form)
            continue
        # what is being inserted must look like the row and carry no heading
        for needle in ('data-label="MOQ"', 'data-label="Lead time"',
                       'data-label="Certifications"', MOQ[form], LEAD, CERTS):
            if needle not in block:
                problems.append('%s: inserted block lacks %r' % (form, needle))
        if '<h2' in block or '<h3' in block:
            problems.append('%s: the block carries a heading — the dot rail '
                            'must not move' % form)
        if problems:
            continue
        if args.check:
            print('%-14s would insert %d B before the formulas anchor '
                  '(MOQ %r)' % (form, len(block.encode()), MOQ[form]))
            continue
        if args.backup_dir:
            os.makedirs(args.backup_dir, exist_ok=True)
            with open(os.path.join(args.backup_dir, 'page-%s.html' % form),
                      'w', encoding='utf-8') as fh:
                fh.write(raw)
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(rebuilt)
        # read-back self-verify
        back = open(path, encoding='utf-8').read()
        assert back.count('sf-facts-mini') >= 1, form
        assert back.replace(block + '\n\n', '', 1) == raw, form
        print('%-14s applied: YES  undone==base: YES  (+%d B)'
              % (form, len(rebuilt.encode()) - len(raw.encode())))

    if problems:
        print('\nFAIL — %d problem(s):' % len(problems), file=sys.stderr)
        for p in problems:
            print('  * %s' % p, file=sys.stderr)
        return 1
    print('\nall eight templates: %s OK'
          % ('would insert' if args.check else 'inserted'))
    return 0


if __name__ == '__main__':
    sys.exit(main())

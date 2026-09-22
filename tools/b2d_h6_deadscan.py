#!/usr/bin/env python3
"""H6 Step 0 dead-asset scan — read only, writes nothing.

Counts occurrences of a set of tokens across the theme tree, with the two things
that made the naive grep lie accounted for:

  1. `sinofresh-theme/_backup*/` and `screenshots/` are historical copies. A token
     that survives only there is dead; a bare recursive grep reports it as live.
     They are excluded and their counts reported separately as `backup`.
  2. A CSS *definition* and a live *reference* are different facts. `style.css` is
     reported on its own line, everything else as `live`, so "defined but never
     emitted" and "emitted but never defined" are both visible.

Usage:  python3 tools/b2d_h6_deadscan.py [--tree sinofresh-theme] [--json out.json]
"""

import argparse
import json
import os
import re
import sys

# Read-only: this script never writes except the optional --json report.

# Directories that hold historical copies, captures, or prose. `_backup*` and
# `screenshots` are earlier snapshots; `docs` and `tools` are dev material that
# never ships -- a token named only in a document or a dev script is dead on
# the site, so counting them as live would invert the verdict (RULES A: the
# source-token layer excludes docs/ and *.md).
SKIP_DIRS = {'_backup', '_backup_x', 'screenshots', '.git', 'docs', 'tools'}
SKIP_FILES = {'.DS_Store'}
TEXT_EXT = {'.php', '.css', '.js', '.html', '.json'}

# The tokens under judgement, one per H6 item. The control tokens are the ones
# that must come back alive -- if a control reads dead, the scanner is broken,
# not the site.
TOKENS = [
    # item 1 -- three legacy CSS families
    ('1a', 'sf-facts__',            'H1 legacy: the spec band H2b1 replaced'),
    ('1b', 'sf-spectable__',        'batch E legacy: the table batch E removed'),
    ('1c', 'sf-fdetail-media__',    'H2a legacy: the media column'),
    # item 5
    ('5',  'sessionStorage',        'the write side with no reader'),
    # item 6
    ('6',  'sf-formulas-data',      'K2 payload, 60/75 pages, 72,720 B'),
    # item 7
    ('7',  "getElementById('configurator')", 'formulas.js:110 dead branch'),
    # item 8
    ('8',  'configurator__summary-value',    'style.css:1220 dead selector'),
    # item 9
    ('9',  'sf_formula_shelf_life', 'registered key with no renderer'),
    # item 10
    ('10', 'sales@zxpet.com',       'three hardcoded copies, source is an option'),
    # item 13
    ('13', 'styles.elements',       'theme.json element rules'),
    # item 15
    ('15', 'WebSite',               'schema type the site never emits'),
    # ---- controls: these MUST read alive, or the scanner is lying ----------
    ('C1', 'sf-facts-mini',         'CONTROL: the live replacement for 1a'),
    ('C2', 'sf-fdetail2__side',     'CONTROL: H5-0 live class'),
    ('C3', 'sf_contact_email',      'CONTROL: the option item 10 should read'),
    ('C4', 'knowsAbout',            'CONTROL: landed in H5'),
]


def walk(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if name in SKIP_FILES:
                continue
            if os.path.splitext(name)[1].lower() not in TEXT_EXT:
                continue
            yield os.path.join(dirpath, name)


def count_token(files, token):
    """Return (per-file counts, total). Literal match, no regex."""
    hits = {}
    for path in files:
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as fh:
                n = fh.read().count(token)
        except OSError:
            continue
        if n:
            hits[path] = n
    return hits, sum(hits.values())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tree', default='sinofresh-theme')
    ap.add_argument('--json')
    args = ap.parse_args()

    if not os.path.isdir(args.tree):
        sys.exit('no such tree: %s' % args.tree)

    live_files = list(walk(args.tree))
    if not live_files:
        sys.exit('the tree is empty -- refusing to report all-dead on a bad walk')

    # The historical copies, counted only so their absence from `live` is a
    # stated fact rather than an accident of the walk.
    backup_files = []
    for sub in ('_backup', '_backup_x', 'screenshots'):
        d = os.path.join(args.tree, sub)
        if os.path.isdir(d):
            for dirpath, _dirnames, filenames in os.walk(d):
                for name in filenames:
                    if os.path.splitext(name)[1].lower() in TEXT_EXT:
                        backup_files.append(os.path.join(dirpath, name))

    style = os.path.join(args.tree, 'style.css')
    report = {'tree': args.tree, 'live_files': len(live_files),
              'backup_files': len(backup_files), 'tokens': {}}

    print('tree=%s  live text files=%d  historical copies=%d'
          % (args.tree, len(live_files), len(backup_files)))
    print('=' * 78)

    for item, token, note in TOKENS:
        hits, total = count_token(live_files, token)
        css_n = hits.get(style, 0)
        live_n = total - css_n
        _, backup_n = count_token(backup_files, token)

        # Where the live hits are, so a verdict can be argued rather than asserted.
        where = sorted(((p, n) for p, n in hits.items() if p != style),
                       key=lambda kv: -kv[1])
        report['tokens'][token] = {
            'item': item, 'note': note, 'style_css': css_n,
            'live': live_n, 'backup': backup_n,
            'live_files': {os.path.relpath(p, args.tree): n for p, n in where},
        }

        tag = 'CONTROL' if item.startswith('C') else 'item ' + item
        verdict = 'DEAD' if total == 0 else 'alive'
        if total == 0 and item.startswith('C'):
            verdict = '*** CONTROL READS DEAD -- scanner is broken ***'
        print('%-8s %-34s %s' % (tag, token, verdict))
        print('           %s' % note)
        print('           style.css=%d  live=%d  historical=%d'
              % (css_n, live_n, backup_n))
        for path, n in where[:6]:
            print('             %-52s %d' % (os.path.relpath(path, args.tree), n))
        if len(where) > 6:
            print('             ... and %d more files' % (len(where) - 6))
        print()

    if args.json:
        with open(args.json, 'w', encoding='utf-8') as fh:
            json.dump(report, fh, indent=2, ensure_ascii=False)
        print('wrote %s' % args.json)


if __name__ == '__main__':
    main()

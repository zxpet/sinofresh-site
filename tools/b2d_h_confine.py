#!/usr/bin/env python3
"""Batch H1 confinement gate.

Batch H1 is a ZERO-DIFF batch: the publishing form is admin-side, the
migration writes keys the front end does not read, and batch H1b's four
certification touch points render byte-identically while the Site Settings
option still holds the default rows. So the page gate is stricter than
batch C's — every one of the 75 captured pages must be byte-for-byte
identical, masks included. Any byte that moves is a failure, and the
sabotage matrix proves the gate notices when the certification data
actually does move a rendered byte.

Gates:
  [1] assets   style.css byte-identical; the theme's style.css?ver token
               equal on both sides; no admin asset leaks into a front page
  [2] pages    75/75 byte-for-byte identical (the manifest defines the set)
  [3] source   every functions.php edit re-applies from the base file and
               undoes to the exact pre-batch bytes; same for the 8 templates
  [4] files    the six new files match the recorded sha256 table
  [5] wiring   the H1b touch points are wired to one source: the token
               defined once, the schema through sf_cert_schema_credentials(),
               both detail-page consumers through
               sf_formula_certifications_value(); each dosage template
               carries the token exactly once and keeps its facts-mini
               certifications value untouched (the spec_cell data source)

Negative control: point every --new-* at the base — gate 3 and gate 5 must
refuse. --sabotage <kind> runs the gate against a deliberately broken
candidate instead; every kind must FAIL.
"""

import argparse
import hashlib
import importlib.util
import os
import re
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

spec = importlib.util.spec_from_file_location('b2d_h_apply', os.path.join(HERE, 'b2d_h_apply.py'))
APPLY = importlib.util.module_from_spec(spec)
spec.loader.exec_module(APPLY)

spec2 = importlib.util.spec_from_file_location('sf_masked_cmp', os.path.join(HERE, 'sf_masked_cmp.py'))
MASKED = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(MASKED)

STYLE_VER_RE = re.compile(r'/themes/[a-z0-9-]+/style\.css\?ver=([0-9a-z.\-]+)')

SABOTAGE = [
    'stray-byte', 'cert-rename', 'schema-drift', 'token-missing',
    'facts-mini-poisoned', 'version-bump', 'css-touched', 'admin-leak',
    'inc-drift', 'php-anchor-lost',
]


def read(p):
    with open(p, encoding='utf-8') as fh:
        return fh.read()


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def slug_for(path):
    """Same rule as b2d_s3_fetch.py: '/formulas/joint-care/' -> 'formulas__joint-care'."""
    s = path.strip('/').replace('/', '__')
    return s or 'root'


def load_manifest(base_dir):
    rows = []
    for line in read(os.path.join(base_dir, 'MANIFEST.tsv')).splitlines():
        if not line or line.startswith('#') or line.startswith('path\t'):
            continue
        rows.append(slug_for(line.split('\t')[0]) + '.html')
    return rows


def build_candidate(args, sabotage, tmp):
    """Copy the candidate side into tmp, then break it on purpose."""
    new_dir = os.path.join(tmp, 'pages')
    shutil.copytree(args.new_dir, new_dir,
                    ignore=shutil.ignore_patterns('MANIFEST.tsv'))
    for name in ('functions.php', 'style.css'):
        shutil.copy(args.new_php if name == 'functions.php' else args.new_css,
                    os.path.join(tmp, name))
    tpl_dir = os.path.join(tmp, 'templates')
    shutil.copytree(args.new_tpl_dir, tpl_dir)
    inc_dir = os.path.join(tmp, 'theme-files')
    shutil.copytree(args.new_theme_dir, inc_dir,
                    ignore=shutil.ignore_patterns('functions.php', 'style.css', 'templates'))

    def page(name):
        return os.path.join(new_dir, name)

    def tpl(slug):
        return os.path.join(tpl_dir, 'page-%s.html' % slug)

    if sabotage == 'stray-byte':
        p = page('products__soft-chews.html')
        s = read(p)
        open(p, 'w', encoding='utf-8').write(s + '\n')
    elif sabotage == 'cert-rename':
        p = page('products__soft-chews.html')
        s = read(p)
        assert 'FDA, cGMP' in s, 'marker missing'
        open(p, 'w', encoding='utf-8').write(s.replace('FDA, cGMP', 'FDA Extra, cGMP', 1))
    elif sabotage == 'schema-drift':
        p = page('formulas__joint-support-soft-chews.html')
        s = read(p)
        i = s.find('"name":"FDA Registered"')
        if i < 0:  # zh pages carry pretty-printed JSON
            i = s.find('"name": "FDA Registered"')
        assert i > 0, 'schema marker missing'
        open(p, 'w', encoding='utf-8').write(s[:i] + '"name":"ZZZ Drifted"' + s[i + len('"name":"FDA Registered"'):])
    elif sabotage == 'token-missing':
        p = tpl('soft-chews')
        s = read(p)
        open(p, 'w', encoding='utf-8').write(s.replace(APPLY.TPL_NEW, APPLY.TPL_OLD, 1))
    elif sabotage == 'facts-mini-poisoned':
        p = tpl('soft-chews')
        s = read(p)
        i = s.find('data-label="Certifications"')
        assert i > 0, 'facts-mini row missing'
        j = s.find('FDA', i)
        open(p, 'w', encoding='utf-8').write(s[:j] + '{{sf-certifications-line}}' + s[j + len('FDA, cGMP, ISO 9001, FSSC 22000, HACCP, BRC'):])
    elif sabotage == 'version-bump':
        p = page('products__soft-chews.html')
        s = read(p)
        open(p, 'w', encoding='utf-8').write(s.replace('style.css?ver=2.10.54', 'style.css?ver=2.10.55', 1))
    elif sabotage == 'css-touched':
        p = os.path.join(tmp, 'style.css')
        open(p, 'w', encoding='utf-8').write(read(p) + '\n')
    elif sabotage == 'admin-leak':
        p = page('blog.html')
        s = read(p)
        open(p, 'w', encoding='utf-8').write(s.replace('</head>',
            '<link rel="stylesheet" href="https://dev.zxpet.com/wp-content/themes/sinofresh-theme/assets/admin/sf-mb.css?ver=1.0.0" /></head>', 1))
    elif sabotage == 'inc-drift':
        p = os.path.join(inc_dir, 'inc', 'formula-admin.php')
        s = read(p)
        open(p, 'w', encoding='utf-8').write(s + '\n')
    elif sabotage == 'php-anchor-lost':
        p = os.path.join(tmp, 'functions.php')
        s = read(p)
        open(p, 'w', encoding='utf-8').write(s.replace("'{{sf-certifications-line}}' => esc_html(sf_certifications_line()),\n", '', 1))
    return new_dir, tmp


def run_gate(args, page_new, work, fails, notes):
    # [1] assets
    base_css = read(args.base_css)
    new_css = read(os.path.join(work, 'style.css'))
    if base_css != new_css:
        fails.append('[1] style.css is not byte-identical to the base')
    vers = set()
    for d in (args.base_dir, page_new):
        for name in os.listdir(d):
            if not name.endswith('.html'):
                continue
            m = STYLE_VER_RE.search(read(os.path.join(d, name)))
            if m:
                vers.add(m.group(1))
    if len(vers) != 1:
        fails.append('[1] the theme style version token moved: %s' % sorted(vers))
    else:
        notes.append('[1] theme style token constant at %s across %d pages' % (sorted(vers)[0], 75))
    leak = [n for n in os.listdir(page_new) if n.endswith('.html')
            and 'assets/admin/' in read(os.path.join(page_new, n))]
    if leak:
        fails.append('[1] admin assets leak into front pages: %s' % leak[:3])
    else:
        notes.append('[1] no admin asset is referenced by any front page')

    # [2] pages — byte-for-byte after the shared mask set: H1 has zero expected
    # diff. Two captures of the same page are never byte-identical (the
    # preflight theme dir, CF email protection and GF per-request artefacts all
    # rotate), so the comparison runs through sf_masked_cmp's ONE mask set,
    # applied identically to both sides. Sabotage bytes (an extra newline, a
    # renamed cert, a bumped version, an admin asset tag) are plain text the
    # mask set never touches, so a masked gate still refuses every sabotage.
    paths = load_manifest(args.base_dir)
    if len(paths) != 75:
        fails.append('[2] manifest carries %d paths (want 75)' % len(paths))
    diff = []
    for rel in paths:
        a = os.path.join(args.base_dir, rel)
        b = os.path.join(page_new, rel)
        if not os.path.exists(b):
            diff.append(rel)
            continue
        ma, _ = MASKED.masked(read(a))
        mb, _ = MASKED.masked(read(b))
        if ma != mb:
            diff.append(rel)
    if diff:
        fails.append('[2] %d page(s) differ from the base capture (masked): %s' % (len(diff), diff[:4]))
    else:
        notes.append('[2] %d/75 pages identical under the shared mask set (zero-diff batch)' % len(paths))

    # [3] source rebuild
    base_php = read(args.base_php)
    new_php = read(os.path.join(work, 'functions.php'))
    undone = new_php
    ok = True
    for label, old, new in APPLY.EDITS:
        if new_php.count(new) != 1:
            fails.append('[3] %s: the batch-H1 text occurs %d times in the candidate (want exactly 1)' % (label, new_php.count(new)))
            ok = False
            continue
        undone = undone.replace(new, old, 1)
    if ok and undone != base_php:
        fails.append('[3] functions.php does not rebuild to its pre-batch bytes')
    elif ok:
        notes.append('[3] functions.php: %d edits applied and undone to the exact pre-batch bytes' % len(APPLY.EDITS))
    for slug in APPLY.DOSAGE:
        base_t = read(os.path.join(args.base_tpl_dir, 'page-%s.html' % slug))
        new_t = read(os.path.join(work, 'templates', 'page-%s.html' % slug))
        if new_t.count(APPLY.TPL_NEW) != 1 or new_t.count(APPLY.TPL_OLD) != 0:
            fails.append('[3] template %s: token swap is not exactly-once' % slug)
            continue
        if new_t.replace(APPLY.TPL_NEW, APPLY.TPL_OLD, 1) != base_t:
            fails.append('[3] template %s does not rebuild to its pre-batch bytes' % slug)
    notes.append('[3] 8 dosage templates rebuild to their pre-batch bytes')

    # [4] new files
    table = {}
    if args.new_file_hashes:
        for line in read(args.new_file_hashes).splitlines():
            if line.strip():
                h, rel = line.split('  ', 1)
                table[rel] = h
    if not table:
        # A gate run without the recorded sha256 table has no reference to
        # compare against — refuse instead of silently skipping the check.
        fails.append('[4] no sha256 table given for the %d new files' % len(APPLY.NEW_FILES))
        notes.append('[4] skipped: no sha256 table')
    else:
        files_root = os.path.join(work, 'theme-files')
        if not os.path.isdir(files_root):
            # Never silently fall back to the untouched --new-theme-dir: that
            # directory is exactly the copy a sabotage would want to hide behind.
            if args.sabotage:
                fails.append('[4] the sabotaged theme-files copy is missing (silent-fallback path)')
                files_root = None
            else:
                files_root = args.new_theme_dir
        if files_root:
            for rel in APPLY.NEW_FILES:
                p = os.path.join(files_root, rel)
                if not os.path.exists(p):
                    fails.append('[4] new file missing from the candidate: %s' % rel)
                    continue
                got = sha(p)
                if rel in table and got != table[rel]:
                    fails.append('[4] %s drifted from the recorded sha256' % rel)
        notes.append('[4] %d new files hash-checked against the recorded table' % len(APPLY.NEW_FILES))

    # [5] wiring
    if new_php.count('sf_certifications_line()') != 1:
        fails.append('[5] the certifications-line token is not wired exactly once in functions.php')
    if new_php.count("'hasCredential'] = sf_cert_schema_credentials();") != 1:
        fails.append('[5] the schema hasCredential is not wired through the helper exactly once')
    if new_php.count('sf_formula_certifications_value(') != 2:
        fails.append('[5] the detail-page certification value is not consumed exactly twice (factsheet + batch-C FAQ)')
    for slug in APPLY.DOSAGE:
        t = read(os.path.join(work, 'templates', 'page-%s.html' % slug))
        if t.count('{{sf-certifications-line}}') != 1:
            fails.append('[5] template %s does not carry the token exactly once' % slug)
        if 'data-label="Certifications"' not in t or 'FDA, cGMP' not in t:
            fails.append('[5] template %s lost its facts-mini certifications value (the spec_cell source)' % slug)
    notes.append('[5] token/schema/detail consumers all read the one certification source')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base-dir', required=True)
    ap.add_argument('--new-dir', required=True)
    ap.add_argument('--base-php', required=True)
    ap.add_argument('--new-php', required=True)
    ap.add_argument('--base-css', required=True)
    ap.add_argument('--new-css', required=True)
    ap.add_argument('--base-tpl-dir', required=True)
    ap.add_argument('--new-tpl-dir', required=True)
    ap.add_argument('--new-theme-dir', help='candidate theme root (for inc/ and assets/)')
    ap.add_argument('--new-file-hashes', help='sha256 table from b2d_h_apply.py --apply')
    ap.add_argument('--sabotage', choices=SABOTAGE)
    ap.add_argument('--report')
    args = ap.parse_args()

    fails, notes = [], []
    tmp = tempfile.mkdtemp(prefix='b2d-h-')
    try:
        if args.sabotage:
            page_new, work = build_candidate(args, args.sabotage, tmp)
        else:
            page_new, work = args.new_dir, os.path.dirname(args.new_php)
        run_gate(args, page_new, work, fails, notes)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    out = []
    out.append('=' * 78)
    out.append('Batch H1 confinement gate%s' % (' — sabotage: %s' % args.sabotage if args.sabotage else ''))
    out.append('=' * 78)
    for n in notes:
        out.append('    ' + n)
    verdict = 'FAIL — %d problem(s)' % len(fails) if fails else 'PASS — the batch moves no rendered byte'
    for f in fails:
        out.append('  !! ' + f)
    out.append('')
    out.append(verdict)
    report = '\n'.join(out) + '\n'
    if args.report:
        with open(args.report, 'w', encoding='utf-8') as fh:
            fh.write(report)
    print(report)
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
"""Batch 3b close-out — the local, pre-install check.

Three items land in this batch (C1 wording, the Quality three-up grid, the
Custom dedup), and the user's constraint is "install to the preflight layer,
do not pull". That constraint means the served bytes of the new theme cannot
be read from this machine, so this file checks the layer that CAN be read: the
working-tree sources. What it proves is that the bytes on disk are the bytes
that were asked for — the templates carry the new copy and nothing else, the
stylesheet carries the three-up rules and no leftover zigzag, and the five
record-driven groups all route through the dedup helper.

The behaviour of that helper is not re-derived here. tools/b3bc_flavor_unit.php
lifts the shipped functions out of functions.php and runs them; this file
shells out to it and reports its verdict alongside the static checks. A
static check can see that the helper is called; only running it can see that
post 158 comes out at eight chips with one owner for the text box.

Run:  python3 tools/b3bc_local_check.py [--json /tmp/x.json]
"""

import argparse
import glob
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THEME = os.path.join(ROOT, 'sinofresh-theme')

FAILED = []
COUNT = 0
RESULTS = []


def read(rel):
    with open(os.path.join(THEME, rel), encoding='utf-8') as fh:
        return fh.read()


def ck(label, cond, got=None):
    global COUNT
    COUNT += 1
    RESULTS.append({'label': label, 'ok': bool(cond)})
    if cond:
        print('  PASS  %s' % label)
    else:
        FAILED.append(label)
        print('  FAIL  %s' % label)
        if got is not None:
            print('        got: %r' % (got,))


def find_php():
    pats = [
        '~/Library/Application Support/Local/lightning-services/php-*/bin/darwin-arm64/bin/php',
        '/Applications/Local.app/Contents/Resources/extraResources/'
        'lightning-services/php-*/bin/*/bin/php',
    ]
    for pat in pats:
        hits = sorted(glob.glob(os.path.expanduser(pat)))
        if hits:
            return hits[-1]
    return None


ap = argparse.ArgumentParser()
ap.add_argument('--json', default=None,
                help='write the per-check result table to this path')
args = ap.parse_args()


# --------------------------------------------------------------------------
# A. item 1 — the C1 band now carries the development path
# --------------------------------------------------------------------------
svc = read('templates/page-services.html')

STAGES = ['Brief &amp; reference match',
          'Prototype &amp; sample round',
          'Palatability &amp; stability trials',
          'Scale-up &amp; packaging validation']

print('== A. C1 — the four development stages, and the old four gone ==')

# Scope the check to the C1 band so an item that also appears elsewhere cannot
# satisfy it. The band opens at its own h2 and closes at the next wp:group.
m = re.search(r'Custom Formulation Capability</h2>(.*?)<!-- /wp:group -->', svc, re.S)
ck('the C1 band is present and delimited', m is not None)
band = m.group(1) if m else ''

for i, stage in enumerate(STAGES, 1):
    ck('stage %d is in the band and only there: %s'
       % (i, stage.replace('&amp;', '&')),
       band.count('<li>%s</li>' % stage) == 1
       and svc.count('<li>%s</li>' % stage) == 1,
       svc.count('<li>%s</li>' % stage))

OLD = ['Custom formula development', 'Custom active ingredient levels',
       'Palatability testing', 'Stability testing']
for old in OLD:
    ck('the old C1 item is gone from the band: %s' % old,
       ('<li>%s</li>' % old) not in band, band[:200])

# The four that must NOT have been touched: the What We Handle column keeps all
# five of its own lines, which is what makes C1 a different sentence now.
for old in OLD + ['Packaging compatibility testing']:
    ck('What We Handle keeps its own line: %s' % old,
       ('<li>%s</li>' % old) in svc)

# No C1 item may repeat a What We Handle line — that duplication is the bug.
handled = re.search(r'What We Handle.*?<!-- /wp:columns -->', svc, re.S)
handled = handled.group(0) if handled else ''
for stage in STAGES:
    ck('C1 does not restate a What We Handle line: %s'
       % stage.replace('&amp;', '&'),
       ('<li>%s</li>' % stage) not in handled)

ck('the C1 heading is unchanged',
   '<h2 class="has-text-align-center wp-block-heading">Custom Formulation Capability</h2>' in svc)
ck('the C1 lead-in now frames the stages',
   'Four stages of formulation development' in band)
ck('the old C1 lead-in is gone',
   'From concept to a validated recipe' not in svc)
ck('the band keeps the panel checklist, not a new component',
   '<ul class="sf-checklist sf-checklist--panel">' in band)
ck('both C1 buttons survive',
   '>Custom formulation \u2192</a>' in band and '>Palatability testing \u2192</a>' in band)

# --------------------------------------------------------------------------
# B. item 2 — the Quality band is a three-up grid
# --------------------------------------------------------------------------
css = read('style.css')

print()
print('== B. Quality — three-up grid, no zigzag left behind ==')

THREE = ('.sf-qs {\n'
         '\tmax-width: 1014px; /* three 319px columns + two 28px gutters */\n'
         '\tmargin: 32px auto 0;\n'
         '\tdisplay: grid;\n'
         '\tgrid-template-columns: repeat(3, minmax(0, 1fr));\n'
         '\tcolumn-gap: 28px;\n'
         '\trow-gap: 28px;\n'
         '}')
ck('the band is a 3-column grid with a real gutter', THREE in css)

CARD = ('.sf-qs__step,\n.sf-qs__step:nth-child(even) {\n'
        '\tdisplay: flex;\n\tflex-direction: column-reverse;\n'
        '\tcolumn-gap: 0;\n\trow-gap: 0;\n\talign-items: stretch;\n}')
ck('each step is a column-reverse card (photo above copy, DOM copy-first)',
   CARD in css)
ck('the copy block stacks its own three lines',
   '.sf-qs__text {\n\tdisplay: flex;\n\tflex-direction: column;\n}' in css)
ck('the number sits under the photo with a margin of its own',
   '.sf-qs__num {\n\tmargin: 16px 0 8px;\n\tfont-size: 64px;' in css)

# The zigzag's three signatures must all be gone, not merely overridden.
ck('the alternating 350px photo track is gone',
   'minmax(0, 350px)' not in css)
ck('the separator hairline is gone',
   'border-top: 1px solid #e0e5dc' not in css)
ck('no sibling-spacing rule survives on the step',
   '.sf-qs__step + .sf-qs__step' not in css)
ck('no even-row grid placement rule survives',
   '.sf-qs__step:nth-child(even) .sf-qs__text' not in css)

# What the tick asked to keep.
ck('the photo keeps its 4:3 ratio',
   'aspect-ratio: 4 / 3;' in css)
ck('the number keeps its 64px brand green',
   'color: var(--wp--preset--color--brand-green);' in css
   and '.sf-qs__num {\n\tmargin: 16px 0 8px;\n\tfont-size: 64px;' in css)
ck('the photo keeps the page image language (radius + soft shadow)',
   'border-radius: 8px;\n\tbox-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);' in css)

# The phone stack.
PHONE = ('.sf-qs {\n'
         '\t\tgrid-template-columns: minmax(0, 1fr);\n'
         '\t\tcolumn-gap: 0;\n'
         '\t}')
ck('the phone breakpoint drops the band to one column', PHONE in css)
ck('the phone breakpoint shrinks the number, not the ratio',
   '.sf-qs__num {\n\t\tfont-size: 44px;\n\t\tmargin: 12px 0 6px;\n\t}' in css)

# --------------------------------------------------------------------------
# C. item 3 — one Custom chip, and it owns the box
# --------------------------------------------------------------------------
fn = read('functions.php')

print()
print('== C. Flavor — every record-driven group routes through the helper ==')

ck('the helper exists',
   'function sf_formula_options_with_custom($options) {' in fn)
ck('the helper marks rather than appends',
   "if (0 === strcasecmp($label, 'Custom')) {" in fn
   and "$options[$i]['custom'] = true;" in fn)
ck('the helper appends only when the list does not already spell Custom',
   '$options[] = sf_formula_custom_option();' in fn)

# The definition line matches the same pattern as a call, so the definition is
# counted and subtracted rather than pattern-matched away — a bare count of
# `sf_formula_options_with_custom(` reads 6 on a correct file.
defs = len(re.findall(r'^function sf_formula_options_with_custom\(', fn, re.M))
calls = len(re.findall(r'sf_formula_options_with_custom\(', fn)) - defs
ck('the helper is defined exactly once and called by all five groups',
   defs == 1 and calls == 5, (defs, calls))

ck('no group appends a Custom unconditionally any more',
   # The append survives in exactly one place — inside the helper, for the
   # list that does not spell Custom. Every other call site was replaced.
   len(re.findall(r'\$options\[\] = sf_formula_custom_option\(\);', fn)) == 1
   and len(re.findall(r'^\t\t\t\tsf_formula_custom_option\(\),$', fn, re.M)) == 0,
   (len(re.findall(r'\$options\[\] = sf_formula_custom_option\(\);', fn)),
    len(re.findall(r'^\t\t\t\tsf_formula_custom_option\(\),$', fn, re.M))))

# Each of the five groups must reach the helper within its own block.
for key in ['flavor', 'weight', 'pack', 'species', 'stage']:
    gm = re.search(r"'key' => '%s'.*?\n\t\t\),\n" % key, fn, re.S)
    ck("the '%s' group builds its options through the helper" % key,
       bool(gm) and 'sf_formula_options_with_custom' in gm.group(0))

# --------------------------------------------------------------------------
# D. the block markup this batch writes is still balanced and parseable
# --------------------------------------------------------------------------
print()
print('== D. block markup ==')

for name in ['templates/page-services.html', 'templates/page-quality.html']:
    text = read(name)
    opens = len(re.findall(r'<!--\s+wp:', text))
    selfc = len(re.findall(r'<!--\s+wp:[^\n]*?/-->', text))
    closes = len(re.findall(r'<!--\s+/wp:', text))
    ck('%-28s opens %3d - self-closing %2d == closes %3d'
       % (name.split('/')[-1] + ':', opens, selfc, closes),
       opens - selfc == closes, (opens, selfc, closes))

bad = []
for name in ['templates/page-services.html', 'templates/page-quality.html']:
    text = read(name)
    for cm in re.finditer(r'<!--\s+wp:[a-z0-9/-]+(\s+(\{.*?\}))?\s*(/)?-->', text):
        blob = cm.group(2)
        if not blob:
            continue
        try:
            json.loads(blob)
        except Exception as exc:                      # noqa: BLE001
            bad.append((name, blob[:60], str(exc)))
ck('every block comment carries parseable JSON attributes', not bad, bad)

# --------------------------------------------------------------------------
# E. the version the batch ships under
# --------------------------------------------------------------------------
print()
print('== E. version and the gate constants that follow it ==')
ck('style.css declares 2.10.77',
   re.search(r'^Version: 2\.10\.77$', css, re.M) is not None)
ck('functions.php enqueues 2.10.77',
   "array(), '2.10.77');" in fn)
for tool, pat in [('tools/b2d_h8c_live_check.py', r"default='2\.10\.77'"),
                  ('tools/b2d_h8c_live_accept.py', r'EXPECT_VER = "2\.10\.77"')]:
    body = open(os.path.join(ROOT, tool), encoding='utf-8').read()
    ck('%s expects 2.10.77' % os.path.basename(tool),
       re.search(pat, body) is not None)

# --------------------------------------------------------------------------
# F. the shipped helper, actually run
# --------------------------------------------------------------------------
print()
print('== F. the shipped helper, run by PHP (tools/b3bc_flavor_unit.php) ==')
php = find_php()
if not php:
    ck('a PHP binary was found to run the unit harness', False, '(none found)')
else:
    print('  using %s' % php)
    proc = subprocess.run([php, os.path.join(ROOT, 'tools/b3bc_flavor_unit.php')],
                          capture_output=True, text=True, cwd=ROOT)
    for line in proc.stdout.rstrip().split('\n'):
        print('  | ' + line)
    if proc.stderr.strip():
        print('  | stderr: ' + proc.stderr.strip()[:400])
    ck('the unit harness exits 0', proc.returncode == 0, proc.returncode)

if args.json:
    with open(args.json, 'w', encoding='utf-8') as fh:
        json.dump({'checks': COUNT, 'failed': FAILED, 'results': RESULTS},
                  fh, indent=1)
    print('\n(wrote %s)' % args.json)

print()
print('%d checks, %d failed' % (COUNT, len(FAILED)))
for f in FAILED:
    print('  FAILED: %s' % f)
sys.exit(1 if FAILED else 0)

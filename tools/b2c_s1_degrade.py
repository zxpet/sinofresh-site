#!/usr/bin/env python3
"""Batch 2C step 1 — degradation proof for [sf_formula_detail].

All 21 formulas carry all three fields, so the skip-empty branch never runs on
real data. This drives it deliberately: blank one meta field on the dev site,
fetch the page, assert the card count drops to two AND the Product JSON-LD's
additionalProperty drops the same entry (both read the same source, so a
divergence would mean one of them is not honouring the empties), then restore
the exact original value in a finally block and re-assert three cards.

Safety: the original value is read from the database first and written back
with wp post meta update; the script refuses to run if the field is already
empty (nothing to restore) and re-verifies the restore at the end.

Run: python3 tools/b2c_s1_degrade.py
"""
import json
import re
import subprocess
import sys
import urllib.request

HOST = "https://dev.zxpet.com"
SLUG = "calming-soft-chews"
POST_ID = None            # resolved from the slug
SSH = ["ssh", "-o", "ConnectTimeout=20", "root@65.49.215.152"]
WP = "cd /var/www/dev.zxpet.com/public && wp"

fails = []


def check(cond, label, detail=""):
    print(("  PASS  " if cond else "  FAIL  ") + label + (f"   {detail}" if not cond else ""))
    if not cond:
        fails.append(label)


def ssh(cmd):
    r = subprocess.run(SSH + [cmd], capture_output=True, text=True, timeout=120)
    return (r.stdout + r.stderr).strip()


def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'sf-verify/1.0'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode('utf-8', 'replace')


def cards_and_props(doc):
    cards = re.findall(r'<h3 class="sf-fdetail__label">(.*?)</h3>', doc, re.S)
    prod = None
    for raw in re.findall(r'<script[^>]*application/ld[+]json[^>]*>(.*?)</script>', doc, re.S):
        try:
            j = json.loads(raw.strip())
        except Exception:                                          # noqa: BLE001
            continue
        for x in (j if isinstance(j, list) else [j]):
            if x.get('@type') == 'Product':
                prod = x
    props = [p['name'] for p in (prod or {}).get('additionalProperty', [])]
    return [c.strip() for c in cards], props


pid = ssh(f'{WP} post list --post_type=sf_formula --name={SLUG} --field=ID 2>/dev/null').strip()
print('post id:', pid)
if not pid.isdigit():
    print('cannot resolve the post id')
    sys.exit(2)

original = ssh(f'{WP} post meta get {pid} sf_formula_analysis 2>/dev/null')
print('original analysis:', repr(original))
if not original.strip():
    print('field already empty — nothing to restore, aborting')
    sys.exit(2)

url = f'{HOST}/formulas/{SLUG}/'
try:
    cards, props = cards_and_props(fetch(url))
    check(cards == ['Ingredients', 'Guaranteed Analysis', 'Standard Specs'],
          'baseline: three cards', str(cards))
    check(props == cards, 'baseline: additionalProperty mirrors the cards', str(props))

    ssh(f'{WP} post meta update {pid} sf_formula_analysis "" 2>/dev/null')
    cards2, props2 = cards_and_props(fetch(url))
    check(cards2 == ['Ingredients', 'Standard Specs'],
          'empty field drops its card', str(cards2))
    check(props2 == cards2, 'empty field drops its additionalProperty too', str(props2))
    check(len(props2) == 2, 'two PropertyValue entries', str(len(props2)))

    # A generic filter must not resurrect the blank: the field is skipped, not
    # rendered as an empty <p>.
    doc = fetch(url)
    check('<p class="sf-fdetail__value"></p>' not in doc, 'no empty value paragraph')
    check(doc.count('class="sf-fdetail__card"') == 2, 'exactly two card wrappers',
          str(doc.count('class="sf-fdetail__card"')))
finally:
    ssh(f'{WP} post meta update {pid} sf_formula_analysis "{original}" 2>/dev/null')
    back = ssh(f'{WP} post meta get {pid} sf_formula_analysis 2>/dev/null')
    check(back == original, 'restored the original value byte-for-byte', repr(back))
    cards3, props3 = cards_and_props(fetch(url))
    check(cards3 == ['Ingredients', 'Guaranteed Analysis', 'Standard Specs'],
          'restored: three cards again', str(cards3))
    check(props3 == cards3, 'restored: additionalProperty matches', str(props3))

print(f'--- {len(fails)} failed ---')
for f in fails:
    print('FAIL', f)
sys.exit(1 if fails else 0)

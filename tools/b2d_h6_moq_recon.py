#!/usr/bin/env python3
"""H6 Step 0b — the MOQ reconciliation, measured off rendered pages.

Read only. The question is not "where does MOQ appear" (it appears in prose
everywhere) but "does the same fact carry the same number everywhere a visitor
can read it". So this counts only the places that state a QUANTITY:

  1. the dosage page's sf-facts-mini row      (data-label="MOQ")
  2. the dosage page's own FAQ answer          (the <details> that asks the MOQ)
  3. the products index card                   (the literal on /products/)
  4. the formula detail page's hero meta line  (MOQ <value>, read through
                                                sinofresh_formula_spec_cell)
  5. anywhere else a bare "MOQ from N units" literal survives

Scans the captured pages, so it measures what ships, not what the source
intends. Prints one row per dosage form plus every literal it did not expect.

Usage: python3 tools/b2d_h6_moq_recon.py [--pages _backup/b2d-h5-candidates]
"""

import argparse
import os
import re
import sys
from collections import defaultdict

# A bytes pattern cannot carry \u escapes, so the en dash and the em dash are
# spelled as their UTF-8 bytes: e2 80 93 and e2 80 94.
FORM_TOKEN = re.compile(
    rb'MOQ\s*(?:from\s*)?([0-9][0-9,]*(?:\s*[\xe2\x80\x93\xe2\x80\x94-]\s*[0-9][0-9,]*)?)\s*units',
    re.I)
FACTS_ROW = re.compile(rb'data-label="MOQ"[^>]*>(.*?)</span>', re.S)
HERO_META = re.compile(rb'<p class="sf-formula-hero__meta"[^>]*>(.*?)</p>', re.S)
FAQ_BLOCK = re.compile(rb'<details\b[^>]*>(.*?)</details>', re.S)
SUMMARY = re.compile(rb'<summary\b[^>]*>(.*?)</summary>', re.S)
TAGS = re.compile(rb'<[^>]+>')


def text(raw):
    return re.sub(rb'\s+', b' ', TAGS.sub(b' ', raw)).strip().decode('utf-8', 'replace')


def walk(root):
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in sorted(filenames):
            if name.endswith('.html'):
                yield os.path.join(dirpath, name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pages', default='_backup/b2d-h5-candidates')
    ap.add_argument('--templates', default='sinofresh-theme/templates')
    args = ap.parse_args()

    if not os.path.isdir(args.pages):
        sys.exit('no capture dir: %s' % args.pages)

    facts = {}       # page -> the mini row value
    faq = {}         # page -> the MOQ FAQ answer
    hero = {}        # page -> the hero meta line
    literals = defaultdict(set)   # page -> every "MOQ from N units" literal

    pages = list(walk(args.pages))
    if not pages:
        sys.exit('capture dir is empty -- refusing to report "no MOQ" on a bad walk')

    for path in pages:
        raw = open(path, 'rb').read()
        rel = os.path.relpath(path, args.pages)

        m = FACTS_ROW.search(raw)
        if m:
            facts[rel] = text(m.group(1))

        block = HERO_META.search(raw)
        if block:
            hero[rel] = text(block.group(1))

        for d in FAQ_BLOCK.finditer(raw):
            s = SUMMARY.search(d.group(1))
            if s and b'MOQ' in s.group(1):
                body = d.group(1)[s.end():]
                faq[rel] = text(body)[:120]

        for m in FORM_TOKEN.finditer(raw):
            literals[rel].add(text(m.group(0)))

    print('capture: %s   pages: %d' % (args.pages, len(pages)))
    print('=' * 78)
    print('1) dosage pages -- the sf-facts-mini row  (%d pages)' % len(facts))
    for k in sorted(facts):
        print('   %-46s %s' % (k, facts[k]))
    print()
    print('2) dosage pages -- the MOQ FAQ answer  (%d pages)' % len(faq))
    for k in sorted(faq):
        print('   %-46s %s' % (k, faq[k]))
    print()
    print('3) formula detail pages -- the hero meta line  (%d pages)' % len(hero))
    seen = defaultdict(int)
    for k in sorted(hero):
        seen[hero[k]] += 1
    for v, n in sorted(seen.items(), key=lambda kv: -kv[1]):
        print('   x%-3d %s' % (n, v))
    print()
    print('4) every "MOQ ... N units" literal, by page  (%d pages)' % len(literals))
    grouped = defaultdict(set)
    for k, vs in literals.items():
        grouped[tuple(sorted(vs))].add(k)
    for vs, ks in sorted(grouped.items(), key=lambda kv: -len(kv[1])):
        print('   x%-3d %s' % (len(ks), ' | '.join(vs)))
        for k in sorted(ks)[:4]:
            print('           %s' % k)
        if len(ks) > 4:
            print('           ... and %d more' % (len(ks) - 4))
    print()

    # The source side: what the templates hard-code, which is what the numbers
    # above were supposed to come from.
    tdir = args.templates
    if os.path.isdir(tdir):
        print('5) source templates carrying the literal  (%s)' % tdir)
        for name in sorted(os.listdir(tdir)):
            if not name.endswith('.html'):
                continue
            raw = open(os.path.join(tdir, name), 'rb').read()
            hits = sorted({text(m.group(0)) for m in FORM_TOKEN.finditer(raw)})
            if hits:
                print('   %-32s %s' % (name, ' | '.join(hits)))


if __name__ == '__main__':
    main()

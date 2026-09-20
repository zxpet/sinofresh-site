#!/usr/bin/env python3
"""Phase 2.1 — re-scan the certificate wording across the live theme.

The 2.1 sheet in docs/about-prelaunch-todo.md was drawn up at 15:50 from the
同一批文件, but line numbers move and other batches have touched these pages, so
this script re-derives the list from the files rather than trusting it.

Matching is done on entity-decoded text (`&middot;` and `&#183;` both mean "·",
and four of the eight dosage pages write the badge that way), while the raw
line is reported as well — the replacement has to keep whichever spelling that
file already uses.

Buckets:

  A  badge bar       ·-separated four-cert list
  B  spec row        comma-separated four-cert list
  C  prose sentence  "FDA registered, cGMP compliant, ISO 9001 and FSSC 22000"
  D  cleanroom       "10,000-Class" (bad) vs "ISO 8" (good)
  S  six-cert        the target strings, so "already done" is verified not assumed
  F  other           any other line naming a certificate, for eyeballing

_backup*/ , docs/ and tools/ are archives and scripts, not served markup.
"""
import html
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {'_backup', '_backup_x', 'docs', 'tools', 'screenshots', 'node_modules', '.git'}
SKIP_EXT = {'.png', '.jpg', '.jpeg', '.webp', '.pdf', '.woff', '.woff2', '.ttf', '.svg', '.ico'}

CERT = r'(?:FDA|cGMP|ISO 9001|FSSC 22000)'
BULLET4 = re.compile(r'FDA\s*·\s*cGMP\s*·\s*ISO 9001\s*·\s*FSSC 22000(?!\s*·\s*HACCP)')
BULLET6 = re.compile(r'FDA\s*·\s*cGMP\s*·\s*ISO 9001\s*·\s*FSSC 22000\s*·\s*HACCP\s*·\s*BRC')
COMMA4 = re.compile(r'FDA,\s*cGMP,\s*ISO 9001,\s*FSSC 22000(?!,\s*HACCP)')
COMMA6 = re.compile(r'FDA,\s*cGMP,\s*ISO 9001,\s*FSSC 22000,\s*HACCP,\s*BRC')
PROSE4 = re.compile(r'FDA registered,\s*cGMP compliant,\s*ISO 9001 and\s*FSSC 22000', re.I)
BAD_ROOM = re.compile(r'10,?000-?[Cc]lass')
GOOD_ROOM = re.compile(r'ISO 8\b')
ANY_CERT = re.compile(r'FDA|cGMP|ISO 9001|FSSC 22000|HACCP|BRC|ISO 8|10,?000-?[Cc]lass')


def files():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if os.path.splitext(fn)[1].lower() in SKIP_EXT:
                continue
            yield os.path.join(dirpath, fn)


def window(text, m, pad=78):
    a, b = max(0, m.start() - pad), min(len(text), m.end() + pad)
    return ('…' if a else '') + text[a:b] + ('…' if b < len(text) else '')


buckets = {k: [] for k in ['A', 'B', 'C', 'D', 'S', 'F']}

for path in sorted(files()):
    rel = os.path.relpath(path, ROOT)
    try:
        raw_lines = open(path, encoding='utf-8').read().split('\n')
    except (UnicodeDecodeError, OSError):
        continue
    for n, raw in enumerate(raw_lines, 1):
        norm = html.unescape(raw)
        got = False
        for key, rx in (('A', BULLET4), ('B', COMMA4), ('C', PROSE4)):
            m = rx.search(norm)
            if m:
                buckets[key].append((rel, n, window(norm, m), raw))
                got = True
        m = BAD_ROOM.search(norm)
        if m:
            buckets['D'].append((rel, n, window(norm, m), raw))
            got = True
        for key, rx in (('S', BULLET6), ('S', COMMA6)):
            m = rx.search(norm)
            if m:
                buckets['S'].append((rel, n, window(norm, m), raw))
                got = True
        if GOOD_ROOM.search(norm):
            m = GOOD_ROOM.search(norm)
            buckets['D'].append((rel, n, window(norm, m), raw))
            got = True
        if not got:
            m = ANY_CERT.search(norm)
            if m:
                buckets['F'].append((rel, n, window(norm, m, 55), raw))

NAMES = {
    'A': 'A  badge bar — four certs, · separated                (TO FIX)',
    'B': 'B  list/copy — four certs, comma separated            (TO FIX)',
    'C': 'C  prose sentence — four certs                        (TO FIX)',
    'D': 'D  cleanroom — bad "10,000-Class" / good "ISO 8"',
    'S': 'S  six-cert strings already in place                  (VERIFY)',
    'F': 'F  other lines naming a certificate                   (REVIEW)',
}

for key in 'ABCDSF':
    rows = buckets[key]
    print('\n=== %s : %d ===' % (NAMES[key], len(rows)))
    for rel, n, text, raw in rows:
        entity = '  [entity]' if '&middot;' in raw or '&#183;' in raw else ''
        print('  %-32s %5d%s %s' % (rel, n, entity, text))

fix = [len(buckets[k]) for k in 'ABC']
print('\n--- code-level fix count: A %d + B %d + C %d = %d (plus D rows above) ---'
      % (fix[0], fix[1], fix[2], sum(fix)))

# grouped per file, which is what the editing pass consumes
per = {}
for key in 'ABCD':
    for rel, n, _t, _r in buckets[key]:
        per.setdefault(rel, []).append((n, key))
print('\n--- files with a four-cert residue: %d ---' % len(per))
for rel in sorted(per):
    print('  %-32s %s' % (rel, '  '.join('%d:%s' % (n, k) for n, k in sorted(per[rel]))))

sys.exit(0)

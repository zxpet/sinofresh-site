#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H2b1 — the eight static self-checks (S1-S8) that run before the gates.

These are the checks the plan declared, and they exist because every one of
them has caught something in an earlier batch:

  S1  block delimiters are balanced and properly nested on all eight pages.
      Counting `<!-- wp:` against `<!-- /wp:` alone is not enough — a
      self-closing delimiter (`<!-- wp:x /-->`) has no closer, so the naive
      count reads +3 on a perfectly valid file. That exact miscount shipped in
      the H2b scanner, so delimiters are matched by a stack here, and the raw
      counts are printed next to it for the record.
  S2  the moved band is byte-identical: sha256 prefix `835c81666e2a`. A move
      that re-typed the markup would render the same and pass a visual check.
  S3  no `#configurator` anchor survives anywhere in the templates.
  S4  selector uniqueness. Rule heads, not substrings — `sf-explore__chip`
      also appears inside two style.css comments, and the migrated block spent
      a release being silently overridden precisely because a copy was left in
      a file that loads later. New file: the same heads. Old file: zero.
  S5  the `:has(` ledger: 164 in style.css, 7 in configurator.css. The site
      total drops 171 -> 164 when H2b2 deletes the file; H2b1 must not move it.
  S6  line counts match what the plan declared.
  S7  `php -l functions.php` and brace balance on both stylesheets.
  S8  the diff touches nothing under the K1-K7 contract.

usage:
    python3 tools/b2d_h2b1_checks.py [--json out.json]
"""

import argparse
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
THEME = os.path.join(ROOT, 'sinofresh-theme')
sys.path.insert(0, HERE)
from b2d_h2b1_css import (brace_balance, family_heads, php_binary,  # noqa: E402
                          read, strip_comments)

T_HTML = os.path.join(THEME, 'templates')

# page, split-length before, expected split-length after
PAGES = [
    ('page-soft-chews.html', 652, 447),
    ('page-tablets.html', 585, 444),
    ('page-dental-chews.html', 608, 454),
    ('page-powders.html', 581, 444),
    ('page-fish-oil.html', 591, 454),
    ('page-pastes.html', 568, 444),
    ('page-liquids.html', 578, 454),
    ('page-drops.html', 577, 454),
]

SELF_CLOSING = re.compile(r'<!--\s*wp:[^>]*?/\s*-->')
DELIM = re.compile(r'<!--\s*(/?)wp:([A-Za-z0-9/_-]+)(.*?)-->', re.S)
BAND_OPEN = '    <div class="sf-explore">'
BAND_SHA12 = '835c81666e2a'
BAND_SECTION = '<section class="wp-block-group sf-explore-band" '

EXPECT = {
    'configurator.css': (958, 832),
    'style.css': (8778, 8899),
    'has_style': (164, 164),
    'has_cfg': (7, 7),
}

FORBIDDEN = ['assets/js/formulas.js', 'assets/js/basket.js', 'inc/config-pdf.php',
             'inc/formula-pools.php']
FORBIDDEN_PREFIX = ['inc/']


def delivered_balance(text):
    body = SELF_CLOSING.sub('', text)
    o = len(re.findall(r'<!--\s*wp:', body))
    c = len(re.findall(r'<!--\s*/wp:', body))
    return o, c, o - c


def delivered_stack(text):
    stack = []
    for m in DELIM.finditer(text):
        closing, name, rest = m.group(1), m.group(2), m.group(3)
        if not closing and rest.rstrip().endswith('/'):
            continue
        if closing:
            if not stack or stack.pop() != name:
                return False, 'closes %s, top of stack is %s' % (name, stack[-1:])
        else:
            stack.append(name)
    return (True, '') if not stack else (False, 'never closes %s' % stack[-3:])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--json', help='write the evidence here')
    args = ap.parse_args(argv)

    report = {'checks': {}, 'fails': []}
    fails = report['fails']

    def block(name, title):
        print('\n== %s  %s' % (name, title))
        report['checks'].setdefault(name, {})

    # ---- S1 / S2 / S3 : the templates -----------------------------------
    block('S1', 'block delimiters balanced and nested (8 pages + detail template)')
    s1 = []
    for name, before, after in PAGES:
        text = read(os.path.join(T_HTML, name))
        o, c, bal = delivered_balance(text)
        ok, why = delivered_stack(text)
        rows = len(text.split('\n'))
        good = bal == 0 and ok and rows == after
        s1.append({'page': name, 'opens': o, 'closes': c, 'balance': bal,
                   'stack': ok, 'lines': rows, 'ok': good})
        print('   %-24s wp:%-4d /wp:%-4d bal %+d  stack %-4s lines %d %s'
              % (name, o, c, bal, 'ok' if ok else 'BAD', rows, '' if good else 'FAIL ' + why))
        if not good:
            fails.append('S1 %s: balance %+d stack %s lines %d (want %d)'
                         % (name, bal, ok, rows, after))
    report['checks']['S1']['rows'] = s1
    dt = read(os.path.join(T_HTML, 'single-sf_formula.html'))
    do, dc, dbal = delivered_balance(dt)
    dok, dwhy = delivered_stack(dt)
    print('   %-24s wp:%-4d /wp:%-4d bal %+d  stack %-4s lines %d'
          % ('single-sf_formula.html', do, dc, dbal, 'ok' if dok else 'BAD',
             len(dt.split('\n'))))
    if dbal != 0 or not dok:
        fails.append('S1 detail template: balance %+d stack %s' % (dbal, dok))
    report['checks']['S1']['detail'] = {'balance': dbal, 'stack': dok}

    block('S2', 'the moved band is byte-identical (sha256 prefix %s)' % BAND_SHA12)
    s2 = []
    for name, before, after in PAGES:
        import hashlib
        text = read(os.path.join(T_HTML, name))
        lines = text.split('\n')
        hits = [i for i, l in enumerate(lines) if l == BAND_OPEN]
        if len(hits) != 1:
            fails.append('S2 %s: band open tag appears %d times' % (name, len(hits)))
            print('   %-24s FAIL %d occurrences' % (name, len(hits)))
            continue
        band = '\n'.join(lines[hits[0]:hits[0] + 5]) + '\n'
        got = hashlib.sha256(band.encode('utf-8')).hexdigest()[:12]
        v = read(os.path.join(T_HTML, name))
        ok = got == BAND_SHA12 and v.count(BAND_SECTION) == 1
        s2.append({'page': name, 'sha12': got, 'sections': v.count(BAND_SECTION)})
        print('   %-24s %s  section x%d  %s' % (name, got, v.count(BAND_SECTION),
                                                'OK' if ok else 'FAIL'))
        if not ok:
            fails.append('S2 %s: sha %s, band sections %d' % (name, got, v.count(BAND_SECTION)))
    report['checks']['S2']['rows'] = s2

    block('S3', 'no #configurator anchor survives in any template')
    import glob
    left = []
    for p in glob.glob(T_HTML + '/**/*.html', recursive=True):
        t = read(p)
        if '#configurator' in t or 'id="configurator"' in t:
            left.append(os.path.relpath(p, THEME))
    print('   templates still carrying the anchor: %s' % (left or 'none'))
    if left:
        fails.append('S3 anchor survives in %s' % left)
    report['checks']['S3'] = {'files': left}
    for needle, want in (('sf-quote-cta', 1), ('href="/contact/#quote"', 1),
                         ('{{FORM_HREF}}', 1), ('{{FORM_CRUMB}}', 2)):
        got = dt.count(needle)
        print('   detail template %-24s %d (want %d) %s'
              % (needle, got, want, 'OK' if got == want else 'FAIL'))
        if got != want:
            fails.append('S3 detail template %s = %d, want %d' % (needle, got, want))

    # ---- S4 / S5 : the stylesheets --------------------------------------
    cfg = read(os.path.join(THEME, 'assets', 'css', 'configurator.css'))
    sty = read(os.path.join(THEME, 'style.css'))

    block('S4', 'selector uniqueness — rule heads, both sides')
    old_heads = family_heads(cfg)
    new_heads = family_heads(sty)
    want = 15                       # 16 selectors, one comma-joined head
    print('   configurator.css .sf-explore* heads: %d (want 0)' % len(old_heads))
    print('   style.css        .sf-explore* heads: %d (want %d)' % (len(new_heads), want))
    for h in new_heads:
        print('      %s' % h.replace('\n', ' ').replace('\t', ' '))
    if old_heads:
        fails.append('S4 configurator.css still defines %s' % old_heads[:3])
    if len(new_heads) != want:
        fails.append('S4 style.css defines %d heads, want %d' % (len(new_heads), want))
    report['checks']['S4'] = {'cfg_heads': old_heads, 'style_heads': new_heads}

    block('S5', 'the :has() ledger')
    hs, hc = sty.count(':has('), cfg.count(':has(')
    print('   style.css %d (want %d)   configurator.css %d (want %d)   site %d'
          % (hs, EXPECT['has_style'][1], hc, EXPECT['has_cfg'][1], hs + hc))
    if hs != EXPECT['has_style'][1] or hc != EXPECT['has_cfg'][1]:
        fails.append('S5 :has() moved: style %d (want %d), cfg %d (want %d)'
                     % (hs, EXPECT['has_style'][1], hc, EXPECT['has_cfg'][1]))
    report['checks']['S5'] = {'style': hs, 'cfg': hc}

    # ---- S6 : line counts ------------------------------------------------
    block('S6', 'line counts (split-length, as the plan counted them)')
    s6 = {}
    for rel, (b, a) in (('assets/css/configurator.css', EXPECT['configurator.css']),
                        ('style.css', EXPECT['style.css'])):
        got = len(read(os.path.join(THEME, rel)).split('\n'))
        print('   %-26s %d -> %d (want %d) %s'
              % (rel, b, got, a, 'OK' if got == a else 'FAIL'))
        s6[rel] = {'before': b, 'after': got, 'want': a}
        if got != a:
            fails.append('S6 %s is %d lines, want %d' % (rel, got, a))
    for name, before, after in PAGES:
        got = len(read(os.path.join(T_HTML, name)).split('\n'))
        if got != after:
            fails.append('S6 %s is %d lines, want %d' % (name, got, after))
    print('   8 page templates: all at the declared line count'
          if not [1 for n, b, a in PAGES
                  if len(read(os.path.join(T_HTML, n)).split('\n')) != a] else '   FAIL')
    report['checks']['S6'] = s6

    # ---- S7 : syntax -----------------------------------------------------
    block('S7', 'syntax — php -l and CSS brace balance')
    php = php_binary()
    if php:
        lint = subprocess.run([php, '-l', os.path.join(THEME, 'functions.php')],
                              capture_output=True, text=True)
        print('   php -l functions.php: %s' % (lint.stdout or lint.stderr).strip())
        if lint.returncode != 0:
            fails.append('S7 php -l failed')
    else:
        print('   note: no php binary found; php -l skipped')
    for rel in ('style.css', 'assets/css/configurator.css'):
        txt = read(os.path.join(THEME, rel))
        b = brace_balance(txt)
        print('   %-26s braces %+d (comments stripped) %s'
              % (rel, b, 'OK' if b == 0 else 'FAIL'))
        if b != 0:
            fails.append('S7 %s brace balance %+d' % (rel, b))

    # ---- S8 : diff scope -------------------------------------------------
    block('S8', 'the diff stays out of the K1-K7 contract')
    out = subprocess.run(['git', '-C', ROOT, 'diff', '--name-only'],
                         capture_output=True, text=True).stdout.split()
    rel = [p[len('sinofresh-theme/'):] if p.startswith('sinofresh-theme/') else p
           for p in out]
    bad = [p for p in rel if p in FORBIDDEN
           or any(p.startswith(pre) for pre in FORBIDDEN_PREFIX)]
    print('   changed: %s' % (rel or 'nothing'))
    print('   contract files touched: %s' % (bad or 'none'))
    if bad:
        fails.append('S8 contract files changed: %s' % bad)
    report['checks']['S8'] = {'changed': rel, 'contract': bad}

    print('\n' + '=' * 72)
    if fails:
        print('S1-S8 FAILURES: %d' % len(fails))
        for f in fails:
            print('   ' + f)
    else:
        print('S1-S8: all eight checks pass.')
    if args.json:
        json.dump(report, open(args.json, 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=2)
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())

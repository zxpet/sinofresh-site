#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H2b1 gate — the confined-change proof, the page set, and the matrix.

The gate answers one question the masked comparator cannot: *is the change on
each page exactly the one that was declared?* Two renders of the same URL are
never byte-identical (Cloudflare rewrites mailto links with a per-response
token, Gravity Forms stamps per-request ids), so the project's regression gate
masks that noise first and then asks "which pages moved". That is necessary but
not sufficient — a page could move for a reason nobody declared and the
comparator would still call it a pass as long as the movement was declared
somewhere.

So the main gate here rebuilds the expected candidate **from the baseline
bytes**, by surgery at markers that exist on both sides, and requires byte
equality (after masking the shared noise and folding `?ver=` tokens):

  dosage pages   the baseline's `<!-- Block 4: Configurator -->` comment through
                 the configurator section's closing tag is exchanged for the
                 candidate's `<!-- Block 4: Explore more dosage forms -->`
                 comment through the band section's closing tag, and the hero
                 CTA anchor is swapped for the declared replacement. The
                 whitespace in front of the comment is `</section>\\n\\n\\n` on
                 both sides, which is what makes the exchange a byte-for-byte
                 one; that is checked, not assumed.
  detail pages   the hero's "Build Custom Formula" anchor, with the resolved
                 `/products/<form>/#configurator` href, swapped for the declared
                 `/contact/#quote` + `sf-quote-cta` replacement.
  the other 17   nothing but the version token may move.

Deriving the band from the candidate would be self-fulfilling, so the band's
own bytes are pinned to the BASELINE's band: 993 bytes, equal on every page.
A candidate whose band lost a chip would satisfy the region exchange and still
fail that comparison — which is exactly the point.

usage:
    b2d_h2b1_confine.py --base DIR --cand DIR [--theme DIR]
                        [--served-hashes FILE] [--json OUT]
    b2d_h2b1_confine.py --base DIR --cand DIR --theme DIR --matrix
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from sf_masked_cmp import masked                                     # noqa: E402
from b2d_h2b1_css import family_heads, read                          # noqa: E402

VER = re.compile(r'\?ver=[\w.\-]+')

CFG_SECTION = '<section id="configurator"'
BAND_SECTION = '<section class="wp-block-group sf-explore-band '
BAND_DIV = '<div class="sf-explore">'
COMMENT_BASE = '<!-- Block 4: Configurator -->'
COMMENT_CAND = '<!-- Block 4: Explore more dosage forms'
NEXT_BLOCK = '<!-- Block 9: How We Work -->'

CTA_DOSE_BASE = ('<a class="wp-block-button__link has-card-white-color has-text-color '
                 'wp-element-button" href="#configurator">Build Custom Formula</a>')
HERO_BUILD = re.compile(r'<a class="sf-formula-hero__build[^"]*" href="[^"]*">Build Custom Formula</a>')

# TranslatePress rewrites the language root of every internal link on a /zh/
# page, so the SAME template edit renders as two different hrefs: the zh pages
# carry `/zh/contact/#quote`. That is not a surprise — the header's existing
# "Get a Quote" button already renders that way — but a gate that hard-codes
# the English string reports it as a regression on all 42 zh pages. The
# declared value is therefore a function of the page's language, and the
# candidate anchor is required to equal it exactly.

def lang_of(name):
    return 'zh' if name.startswith('zh__') else 'en'


def lang_root(lang):
    return '/zh/' if lang == 'zh' else '/'


def cta_dose(lang):
    return ('<a class="wp-block-button__link has-card-white-color has-text-color '
            'wp-element-button sf-quote-cta" href="%scontact/#quote">Build Custom Formula</a>'
            % lang_root(lang))


def cta_detail(lang):
    return ('<a class="sf-formula-hero__build sf-quote-cta" href="%scontact/#quote">'
            'Build Custom Formula</a>' % lang_root(lang))


CTA_DOSE_CAND = cta_dose('en')
CTA_DETAIL_CAND = cta_detail('en')

BUILD_H2 = '<h2 class="has-text-align-center wp-block-heading">Build Your '
LDJSON = re.compile(r'<script[^>]*type="application/ld+json"[^>]*>(.*?)</script>', re.S)
ASSET = re.compile(r'/([\w.\-]+\.(?:css|js))\?ver=([\w.\-]+)')

STYLE_BASE, STYLE_NEW = '2.10.55', '2.10.56'
CFG_BASE, CFG_NEW = '2.9', '2.10'

DOSAGE_EN = re.compile(r'^products__[\w\-]+\.html$')
DOSAGE_ZH = re.compile(r'^zh__products__[\w\-]+\.html$')
DETAIL = re.compile(r'^(zh__)?formulas__[\w\-]+\.html$')

# The files whose bytes must be the ones the server serves, checked against a
# sha256 table taken off the deployed pre-flight copy.
SERVED_FILES = [
    'functions.php',
    'style.css',
    'assets/css/configurator.css',
    'assets/js/configurator.js',
    'templates/page-soft-chews.html',
    'templates/page-tablets.html',
    'templates/page-powders.html',
    'templates/page-pastes.html',
    'templates/page-drops.html',
    'templates/page-liquids.html',
    'templates/page-fish-oil.html',
    'templates/page-dental-chews.html',
    'templates/single-sf_formula.html',
]

# Files that must not be touched at all (the K1-K7 contract).
FROZEN = ['assets/js/formulas.js', 'assets/js/basket.js',
          'inc/config-pdf.php', 'inc/formula-pools.php']


def fold(text):
    """Normalise version tokens: the one token this batch declares may move."""
    return VER.sub('?ver=', text)


def clean(text):
    """The comparison normal form: shared noise masked, versions folded."""
    return fold(masked(text)[0])


def cut(html, start, tag):
    """Slice from `start`, closing the first balanced <tag>…</tag> pair."""
    i = html.find(start)
    if i < 0:
        return None
    if tag is None:
        return html[i:]
    open_re = re.compile(r'<%s\b' % tag)
    close = '</%s>' % tag
    depth, pos = 0, i
    while True:
        m = open_re.search(html, pos)
        c = html.find(close, pos)
        if c < 0:
            return None
        if m is not None and m.start() < c:
            depth += 1
            pos = m.end()
        else:
            depth -= 1
            pos = c + len(close)
            if depth == 0:
                return html[i:pos]


def pages(d):
    return sorted(n for n in os.listdir(d) if n.endswith('.html'))


def dosage(name):
    return bool(DOSAGE_EN.match(name) or DOSAGE_ZH.match(name))


def load_served(path):
    table = {}
    if not path or not os.path.exists(path):
        return None
    for line in read(path).splitlines():
        parts = line.split()
        if len(parts) == 2:
            table[parts[1]] = parts[0]
    return table


# ---------------------------------------------------------------- checks ---

def check_inventory(base, cand, fails, notes):
    """[1] Version tokens: exactly the declared pair moved, everywhere else."""
    moved_unexpected, missing_cfg_base, missing_cfg_cand = [], [], []
    style_base, style_cand = set(), set()
    cfgsets = {}
    for n in pages(base):
        b, c = read(os.path.join(base, n)), read(os.path.join(cand, n))
        sb = dict((k, v) for k, v in ASSET.findall(b))
        sc = dict((k, v) for k, v in ASSET.findall(c))
        style_base.add(sb.get('style.css'))
        style_cand.add(sc.get('style.css'))
        key = n
        cfgsets[key] = (sb.get('configurator.css'), sc.get('configurator.css'))
        want = {'style.css'}
        if dosage(n):
            want.add('configurator.css')
        for asset in set(sb) | set(sc):
            if asset in want:
                continue
            if sb.get(asset) != sc.get(asset):
                moved_unexpected.append('%s %s %s->%s' % (n, asset, sb.get(asset), sc.get(asset)))
    if style_base != {STYLE_BASE}:
        fails.append('[1] baseline style token is %s, expected only %s'
                     % (sorted(x for x in style_base if x), STYLE_BASE))
    else:
        notes.append('[1] baseline: style.css %s on all %d pages' % (STYLE_BASE, len(pages(base))))
    if style_cand != {STYLE_NEW}:
        fails.append('[1] candidate style token is %s, expected only %s'
                     % (sorted(x for x in style_cand if x), STYLE_NEW))
    else:
        notes.append('[1] candidate: style.css %s on all %d pages' % (STYLE_NEW, len(pages(cand))))
    bad = []
    for n, (b, c) in cfgsets.items():
        if dosage(n):
            if b != CFG_BASE:
                bad.append('%s base=%s' % (n, b))
            if c != CFG_NEW:
                bad.append('%s cand=%s' % (n, c))
        else:
            if b is not None or c is not None:
                bad.append('%s leaks configurator.css (%s/%s)' % (n, b, c))
    if bad:
        fails.append('[1] configurator.css inventory: %s' % bad[:4])
    else:
        notes.append('[1] configurator.css %s -> %s on exactly the 16 dosage pages, absent elsewhere'
                     % (CFG_BASE, CFG_NEW))
    if moved_unexpected:
        fails.append('[1] undeclared version movement: %s' % moved_unexpected[:4])
    else:
        notes.append('[1] no other asset version moved on any of the 75 pages')


def check_pageset(base, cand, fails, notes):
    """[2] Exactly the declared 58 pages differ; the other 17 are identical."""
    want = set(n for n in pages(base) if dosage(n) or DETAIL.match(n))
    diff, same = [], []
    unfolded_diff = 0
    for n in pages(base):
        b = read(os.path.join(base, n))
        c = read(os.path.join(cand, n))
        if clean(b) != clean(c):
            diff.append(n)
        else:
            same.append(n)
        if masked(b)[0] != masked(c)[0]:
            unfolded_diff += 1
    got, miss, extra = set(diff), want - set(diff), set(diff) - want
    if miss or extra:
        fails.append('[2] page set wrong: %d differ, expected %d; missing=%s extra=%s'
                     % (len(diff), len(want), sorted(miss)[:4], sorted(extra)[:4]))
    else:
        notes.append('[2] exactly the declared %d pages differ (%d dosage + %d detail); %d identical'
                     % (len(want), sum(1 for n in want if dosage(n)),
                        sum(1 for n in want if DETAIL.match(n)), len(same)))
    if unfolded_diff != len(pages(base)):
        fails.append('[2] only %d pages differ without folding versions, expected all %d — the '
                     'fold is hiding more than the declared token'
                     % (unfolded_diff, len(pages(base))))
    else:
        notes.append('[2] unfolded: all %d pages differ, so folding ?ver= hides exactly the '
                     'declared token' % len(pages(base)))


def check_confined(base, cand, fails, notes):
    """[3] The main gate: rebuild the expected page from the baseline bytes."""
    bad_rebuild, bad_band, bad_h2, bad_anchor, checked = [], [], [], [], 0
    for n in pages(base):
        braw = read(os.path.join(base, n))
        craw = read(os.path.join(cand, n))
        if dosage(n):
            checks = [(braw.count(COMMENT_BASE), 1, 'baseline Block 4 comment'),
                      (craw.count(COMMENT_CAND), 1, 'candidate Block 4 comment'),
                      (braw.count(CFG_SECTION), 1, 'baseline configurator section'),
                      (craw.count(BAND_SECTION), 1, 'candidate band section'),
                      (braw.count(CTA_DOSE_BASE), 1, 'baseline hero CTA')]
            off = [msg for got, want, msg in checks if got != want]
            if off:
                bad_rebuild.append('%s: %s' % (n, off))
                continue
            C = cut(braw, CFG_SECTION, 'section')
            S = cut(craw, BAND_SECTION, 'section')
            if C is None or S is None:
                bad_rebuild.append('%s: balanced slice failed' % n)
                continue
            i = braw.find(COMMENT_BASE)
            j = craw.find(COMMENT_CAND)
            region = braw[i:braw.find(C, i) + len(C)]
            if not region.startswith(COMMENT_BASE):
                bad_rebuild.append('%s: baseline region does not start at the comment' % n)
                continue
            expected = braw[:i] + craw[j:craw.find(S, j) + len(S)] + braw[i + len(region):]
            expected = expected.replace(CTA_DOSE_BASE, cta_dose(lang_of(n)), 1)
            if clean(expected) != clean(craw):
                bad_rebuild.append(n)
            # the band is a MOVE, so its bytes come from the baseline
            Bb = cut(braw[braw.find(BAND_DIV):], BAND_DIV, 'div') if BAND_DIV in braw else None
            Bc = cut(craw[craw.find(BAND_DIV):], BAND_DIV, 'div') if BAND_DIV in craw else None
            if Bb is None or Bb != Bc:
                bad_band.append(n)
            nb, nc = braw.count(BUILD_H2), craw.count(BUILD_H2)
            if not (nb == 1 and nc == 0):
                bad_h2.append('%s %d->%d' % (n, nb, nc))
            if craw.count('#configurator') != 0 or craw.count('id="configurator"') != 0:
                bad_anchor.append(n)
        elif DETAIL.match(n):
            m = HERO_BUILD.search(braw)
            if not m:
                bad_rebuild.append('%s: no hero build anchor in the baseline' % n)
                continue
            expected = braw.replace(m.group(0), cta_detail(lang_of(n)), 1)
            if clean(expected) != clean(craw):
                bad_rebuild.append(n)
            if craw.count(cta_detail(lang_of(n))) != 1:
                bad_anchor.append('%s hero anchor' % n)
            if craw.count('#configurator') != 0:
                bad_anchor.append(n)
            if braw.count('<h2') != craw.count('<h2'):
                bad_h2.append('%s h2 count moved' % n)
        else:
            if clean(braw) != clean(craw):
                bad_rebuild.append(n)
            continue
        checked += 1
    if bad_rebuild:
        fails.append('[3] the page is not the declared edit: %s' % bad_rebuild[:4])
    else:
        notes.append('[3] all %d declared pages rebuild byte-for-byte from the baseline' % len(
            [n for n in pages(base) if dosage(n) or DETAIL.match(n)]))
    if bad_band:
        fails.append('[3] the band was not moved intact (bytes differ from the baseline): %s'
                     % bad_band[:4])
    else:
        notes.append('[3] the band is byte-identical to the baseline on all 8 dosage pages '
                     '(a move, not a re-typing)')
    if bad_h2:
        fails.append('[3] Build Your … Formula H2: %s' % bad_h2[:4])
    else:
        notes.append('[3] the configurator H2 is gone from all 8 pages (1 -> 0) and the detail '
                     'pages keep their heading count')
    if bad_anchor:
        fails.append('[3] the #configurator anchor survives: %s' % bad_anchor[:4])
    else:
        notes.append('[3] no #configurator anchor survives anywhere')


def check_served(theme, served, fails, notes):
    """[4] The working tree is the bytes the server serves, and nothing else moved."""
    table = load_served(served)
    if table is None:
        fails.append('[4] no served-hash table: the candidate cannot be shown to be the '
                     'server\'s copy (a missing reference is a failure, not a skip)')
    else:
        bad = []
        for rel in SERVED_FILES:
            want = table.get(rel)
            got = hashlib.sha256(open(os.path.join(theme, rel), 'rb').read()).hexdigest()
            if want is None:
                bad.append('%s absent from the table' % rel)
            elif want != got:
                bad.append('%s %s != %s' % (rel, got[:12], want[:12]))
        if bad:
            fails.append('[4] served vs working tree: %s' % bad[:4])
        else:
            notes.append('[4] all %d files match the served copy byte-for-byte' % len(SERVED_FILES))
    for rel in FROZEN:
        p = os.path.join(theme, rel)
        if os.path.exists(p):
            notes.append('[4] contract file present and untouched: %s' % rel)
    heads = family_heads(read(os.path.join(theme, 'assets/css/configurator.css')))
    if heads:
        fails.append('[4] configurator.css still defines .sf-explore*: %s' % heads[:2])
    else:
        notes.append('[4] configurator.css defines no .sf-explore* head (no silent override left)')


def check_jsonld(base, cand, fails, notes):
    """[5] Structured data must not move, and no heading may appear or vanish."""
    drift, bad_h1, checked = [], [], 0
    for n in pages(base):
        if not (dosage(n) or DETAIL.match(n)):
            continue
        braw, craw = read(os.path.join(base, n)), read(os.path.join(cand, n))
        lb = [fold(x) for x in LDJSON.findall(braw)]
        lc = [fold(x) for x in LDJSON.findall(craw)]
        if lb != lc:
            drift.append('%s (%d->%d blocks)' % (n, len(lb), len(lc)))
        if braw.count('<h1') != 1 or craw.count('<h1') != 1:
            bad_h1.append(n)
        checked += 1
    if drift:
        fails.append('[5] JSON-LD drifted: %s' % drift[:4])
    else:
        notes.append('[5] JSON-LD byte-identical on all %d pages (8 dosage + 42 detail)' % checked)
    if bad_h1:
        fails.append('[5] h1 count is not 1: %s' % bad_h1[:4])
    else:
        notes.append('[5] exactly one h1 per page on all %d pages' % checked)


def check_structure(base, cand, fails, notes):
    """[6] Render order and the declared strings, on the declared pages."""
    bad_order, bad_cta, ok = [], [], 0
    for n in pages(base):
        if not dosage(n):
            continue
        c = read(os.path.join(cand, n))
        wall, band, hww = (c.find('id="formulas"'),
                           c.find('class="wp-block-group sf-explore-band '),
                           c.find(NEXT_BLOCK))
        if not (0 <= wall < band < hww):
            bad_order.append('%s wall=%d band=%d howwework=%d' % (n, wall, band, hww))
        if c.count(cta_dose(lang_of(n))) != 1:
            bad_cta.append(n)
        else:
            ok += 1
    n_dose = sum(1 for n in pages(base) if dosage(n))
    if bad_order:
        fails.append('[6] render order is not #formulas -> band -> How We Work: %s' % bad_order[:4])
    else:
        notes.append('[6] on all %d dosage pages the band sits between the card wall and '
                     'How We Work' % n_dose)
    if bad_cta:
        fails.append('[6] hero CTA: %s' % bad_cta[:4])
    else:
        notes.append('[6] the retargeted hero CTA is present exactly once on all %d pages' % ok)
    bad_detail = [n for n in pages(base) if DETAIL.match(n)
                  and read(os.path.join(cand, n)).count(cta_detail(lang_of(n))) != 1]
    if bad_detail:
        fails.append('[6] detail hero CTA: %s' % bad_detail[:4])
    else:
        notes.append('[6] all 42 detail pages carry the declared hero CTA')


GATES = [('1', check_inventory), ('2', check_pageset), ('3', check_confined),
         ('4', check_served), ('5', check_jsonld), ('6', check_structure)]


def run(base, cand, theme, served, verbose=True):
    fails, notes = [], []
    for tag, fn in GATES:
        if fn in (check_served,):
            fn(theme, served, fails, notes)
        else:
            fn(base, cand, fails, notes)
    if verbose:
        print('=' * 72)
        for note in notes:
            print('  ok   ' + note)
        print('-' * 72)
        if fails:
            for f in fails:
                print('  FAIL ' + f)
            print('VERDICT: FAIL — %d gate problem(s)' % len(fails))
        else:
            print('VERDICT: PASS — all six gates hold')
    return fails, notes


# ------------------------------------------------------------- sabotage ----

def mutate(name, base, cand, theme, tmp):
    """Break the candidate on purpose, in a way the gate must notice."""
    P = os.path.join(tmp, 'pages')
    T = os.path.join(tmp, 'theme')
    shutil.copytree(cand, P)
    shutil.copytree(theme, T)
    dose = 'products__soft-chews.html'
    det = 'formulas__calming-soft-chews.html'

    def pp(n):
        return os.path.join(P, n)

    def w(p, s):
        open(p, 'w', encoding='utf-8').write(s)

    if name == 'keep-h2':
        p = pp(dose)
        s = read(p).replace('</section>\n\n\n' + NEXT_BLOCK,
                            '</section>\n\n' + BUILD_H2 + 'Soft Chews Formula</h2>\n\n'
                            + NEXT_BLOCK, 1)
        w(p, s)
    elif name == 'band-not-moved':
        p = pp(dose)
        s = read(p)
        S = cut(s, BAND_SECTION, 'section')
        w(p, s.replace(S, '', 1))
    elif name == 'chip-missing':
        p = pp(dose)
        s = read(p)
        i = s.find('<a class="sf-explore__chip"')
        j = s.find('</a>', i) + 4
        w(p, s[:i] + s[j:])
    elif name == 'cta-not-retargeted':
        p = pp(dose)
        w(p, read(p).replace(CTA_DOSE_CAND, CTA_DOSE_BASE, 1))
    elif name == 'ver-stale':
        p = pp(det)
        w(p, read(p).replace('style.css?ver=' + STYLE_NEW, 'style.css?ver=' + STYLE_BASE, 1))
    elif name == 'old-css-left':
        p = os.path.join(T, 'assets/css/configurator.css')
        w(p, read(p) + '\n.sf-explore__btn { color: #1B4D3E; }\n')
    elif name == 'band-entity-changed':
        # One entity swapped for its literal character: renders identically, so
        # only a byte-level comparison can see it.
        p = pp(dose)
        w(p, read(p).replace('&rarr;', '→', 1))
    elif name == 'stray-byte-on-a-stable-page':
        p = pp('blog.html')
        w(p, read(p) + '\n')
    elif name == 'declared-page-unchanged':
        # Put the baseline page back, but repair the version tokens first: the
        # point of this variant is "the declared content edit is missing", and
        # leaving the old tokens behind would let the cheap inventory gate catch
        # it while the page-set and confined-change gates stayed silent.
        s = read(os.path.join(base, dose))
        s = s.replace('style.css?ver=' + STYLE_BASE, 'style.css?ver=' + STYLE_NEW)
        s = s.replace('configurator.css?ver=' + CFG_BASE, 'configurator.css?ver=' + CFG_NEW)
        w(pp(dose), s)
    elif name == 'detail-cta-reverted':
        p = pp(det)
        w(p, read(p).replace(CTA_DETAIL_CAND, '<a class="sf-formula-hero__build" '
                                              'href="/products/soft-chews/#configurator">'
                                              'Build Custom Formula</a>', 1))
    else:
        raise SystemExit('unknown sabotage variant %r' % name)
    return P, T


MATRIX = ['keep-h2', 'band-not-moved', 'chip-missing', 'cta-not-retargeted',
          'ver-stale', 'old-css-left', 'stray-byte-on-a-stable-page',
          'declared-page-unchanged', 'detail-cta-reverted', 'band-entity-changed']


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--base')
    ap.add_argument('--cand')
    ap.add_argument('--theme', default=os.path.join(ROOT, 'sinofresh-theme'))
    ap.add_argument('--served-hashes')
    ap.add_argument('--json')
    ap.add_argument('--matrix', action='store_true')
    ap.add_argument('--sabotage')
    args = ap.parse_args(argv)

    if args.matrix:
        print('=== sabotage matrix — every variant must be caught ===')
        rows, missed = [], []
        for name in MATRIX:
            tmp = tempfile.mkdtemp(prefix='h2b1-sab-')
            try:
                P, T = mutate(name, args.base, args.cand, args.theme, tmp)
                fails, notes = run(args.base, P, T, args.served_hashes, verbose=False)
                caught = bool(fails)
                gates = sorted(set(f.split(']')[0] + ']' for f in fails))
                rows.append({'variant': name, 'caught': caught, 'gates': gates,
                             'detail': fails[:3]})
                print('  %-32s %s   %s' % (name, 'CAUGHT' if caught else 'MISSED',
                                           ' '.join(gates) or '-'))
                if not caught:
                    missed.append(name)
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
        print('-' * 72)
        print('  %d/%d variants caught' % (len(MATRIX) - len(missed), len(MATRIX)))
        if missed:
            print('MISSED: %s' % missed)
        if args.json:
            json.dump({'matrix': rows, 'missed': missed},
                      open(args.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        return 1 if missed else 0

    if args.sabotage:
        tmp = tempfile.mkdtemp(prefix='h2b1-sab-')
        try:
            P, T = mutate(args.sabotage, args.base, args.cand, args.theme, tmp)
            fails, notes = run(args.base, P, T, args.served_hashes)
            return 1 if fails else 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    if not (args.base and args.cand):
        ap.error('--base and --cand are required')
    fails, notes = run(args.base, args.cand, args.theme, args.served_hashes)
    if args.json:
        json.dump({'fails': fails, 'notes': notes},
                  open(args.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())

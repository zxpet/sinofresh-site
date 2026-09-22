#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H2b2 gate — the confined-change proof, the page set, and the matrix.

H2b1's gate had to reason about a *move*: it rebuilt the expected candidate
from the baseline by exchanging a region, and pinned the moved band's bytes to
the baseline's own bytes so a re-typed band could not pass. H2b2 is a pure
deletion and the proof is correspondingly sharper:

    the candidate must equal the baseline with exactly two lines removed,
    on exactly the pages that referenced them, and be unchanged elsewhere.

That is a stronger statement than "the page set is right", because it fixes the
*content* of the change as well as its extent. No version token moves this
batch — the two deleted enqueues carried their own `?ver=` tokens away — so the
masked comparison needs no folding either, and the gate asserts that: the
folded and unfolded difference sets must be identical, which would fail if any
other token had drifted.

The two lines are claimed by id (`id='sinofresh-configurator-css'`,
`id="sinofresh-configurator-js"`), not by position, so a page whose line numbers
shifted still has to produce exactly the declared bytes.

usage:
    b2d_h2b2_confine.py --base DIR --cand DIR [--theme DIR]
                        [--served FILE] [--json OUT]
    b2d_h2b2_confine.py --base DIR --cand DIR --theme DIR --matrix
    b2d_h2b2_confine.py --base DIR --cand DIR --served FILE --negctl
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

VER = re.compile(r'\?ver=[\w.\-]+')
ASSET = re.compile(r'/([\w.\-]+\.(?:css|js))\?ver=([\w.\-]+)')
LDJSON = re.compile(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', re.S)

CFG_CSS_LINK = re.compile(r"<link rel='stylesheet' id='sinofresh-configurator-css'[^>]*>")
CFG_JS = re.compile(r'<script id="sinofresh-configurator-js"[^>]*></script>')
CFG_TOKEN = 'sinofresh-configurator'

STYLE_TOKEN = '2.10.56'
CFG_CSS_VER, CFG_JS_VER = '2.10', '2.3'

DOSE_EN = re.compile(r'^products__[\w\-]+\.html$')
DOSE_ZH = re.compile(r'^zh__products__[\w\-]+\.html$')
DETAIL = re.compile(r'^(zh__)?formulas__[\w\-]+\.html$')

BAND_SECTION = 'class="wp-block-group sf-explore-band '
H2B1_NOTE = 'moved out of the configurator, batch H2b1'
BUILD_H2 = 'Build Your '
NEXT_BLOCK = '<!-- Block 9: How We Work -->'

# Files that must not be touched at all (the K1-K7 contract).
FROZEN = ['assets/js/formulas.js', 'assets/js/basket.js',
          'inc/config-pdf.php', 'inc/formula-pools.php']
GONE = ['assets/css/configurator.css', 'assets/js/configurator.js']


def read(path):
    with open(path, encoding='utf-8', errors='replace') as fh:
        return fh.read()


def dosage(name):
    return bool(DOSE_EN.match(name) or DOSE_ZH.match(name))


def pages(d):
    return sorted(n for n in os.listdir(d) if n.endswith('.html'))


def clean(text):
    """The comparison normal form. No folding: nothing may move this batch."""
    return masked(text)[0]


def strip_cfg_lines(text):
    """Return (text-without-the-two-lines, n_removed)."""
    keep, removed = [], 0
    for ln in text.split('\n'):
        if CFG_CSS_LINK.fullmatch(ln) or CFG_JS.fullmatch(ln):
            removed += 1
            continue
        keep.append(ln)
    return '\n'.join(keep), removed


def load_served(path):
    table = {}
    if not path or not os.path.exists(path):
        return None
    for line in read(path).splitlines():
        parts = line.split(None, 1)
        if len(parts) == 2:
            table[parts[1].strip()] = parts[0]
    return table


# ---------------------------------------------------------------- checks ---

def check_inventory(base, cand, fails, notes):
    """[1] Only the two declared asset references vanish; no token moves."""
    cfg_base, cfg_cand, stray, style_b, style_c = {}, {}, [], set(), set()
    for n in pages(base):
        b, c = read(os.path.join(base, n)), read(os.path.join(cand, n))
        cb = (len(CFG_CSS_LINK.findall(b)), len(CFG_JS.findall(b)))
        cc = (len(CFG_CSS_LINK.findall(c)), len(CFG_JS.findall(c)))
        cfg_base[n], cfg_cand[n] = cb, cc
        style_b.add(dict(ASSET.findall(b)).get('style.css'))
        style_c.add(dict(ASSET.findall(c)).get('style.css'))
        if dosage(n):
            if cb != (1, 1) or cc != (0, 0):
                stray.append('%s %s->%s' % (n, cb, cc))
        else:
            if cb != (0, 0) or cc != (0, 0):
                stray.append('%s leaks configurator refs %s->%s' % (n, cb, cc))
        # the declared version tokens on the lines being removed
        for m in CFG_CSS_LINK.finditer(b):
            if ('configurator.css?ver=' + CFG_CSS_VER) not in m.group(0):
                stray.append('%s link ver != %s' % (n, CFG_CSS_VER))
        for m in CFG_JS.finditer(b):
            if ('configurator.js?ver=' + CFG_JS_VER) not in m.group(0):
                stray.append('%s script ver != %s' % (n, CFG_JS_VER))
        if CFG_TOKEN in c:
            stray.append('%s still mentions %s' % (n, CFG_TOKEN))
    if stray:
        fails.append('[1] asset inventory: %s' % stray[:4])
    else:
        notes.append('[1] the two configurator refs are present once each on exactly the 16 '
                     'dosage pages in the baseline and absent on all 75 in the candidate')
    if style_b != {STYLE_TOKEN} or style_c != {STYLE_TOKEN}:
        fails.append('[1] style token moved: base=%s cand=%s'
                     % (sorted(x for x in style_b if x), sorted(x for x in style_c if x)))
    else:
        notes.append('[1] style.css stays %s on all 75 pages — no version bump, and no token '
                     'moved anywhere else either' % STYLE_TOKEN)


def check_pageset(base, cand, fails, notes):
    """[2] Exactly 16 pages differ, 59 are identical, and folding is a no-op."""
    want = set(n for n in pages(base) if dosage(n))
    diff, same, folded_diff = [], [], 0
    for n in pages(base):
        b, c = read(os.path.join(base, n)), read(os.path.join(cand, n))
        if clean(b) != clean(c):
            diff.append(n)
        else:
            same.append(n)
        if VER.sub('?ver=', masked(b)[0]) != VER.sub('?ver=', masked(c)[0]):
            folded_diff += 1
    got, miss, extra = set(diff), want - set(diff), set(diff) - want
    if miss or extra:
        fails.append('[2] page set wrong: %d differ, expected %d; missing=%s extra=%s'
                     % (len(diff), len(want), sorted(miss)[:4], sorted(extra)[:4]))
    else:
        notes.append('[2] exactly the declared %d pages differ; %d identical'
                     % (len(want), len(same)))
    if folded_diff != len(diff):
        fails.append('[2] the ?ver= fold changes the answer (%d vs %d) — some token moved '
                     'that this batch does not declare' % (folded_diff, len(diff)))
    else:
        notes.append('[2] folding ?ver= changes nothing: no version token moved on any page')


def check_confined(base, cand, fails, notes):
    """[3] The main gate: candidate == baseline minus exactly two lines."""
    bad, bad_removed, bad_stable, checked = [], [], [], 0
    for n in pages(base):
        braw, craw = read(os.path.join(base, n)), read(os.path.join(cand, n))
        if dosage(n):
            expected, removed = strip_cfg_lines(braw)
            if removed != 2:
                bad_removed.append('%s removed %d lines, expected 2' % (n, removed))
                continue
            if clean(expected) != clean(craw):
                bad.append(n)
            checked += 1
        else:
            if clean(braw) != clean(craw):
                bad_stable.append(n)
            # and the two refs were never there to begin with
            if CFG_TOKEN in braw or CFG_TOKEN in craw:
                bad_stable.append('%s mentions %s' % (n, CFG_TOKEN))
            checked += 1
    if bad or bad_removed:
        fails.append('[3] the page is not the declared edit: %s'
                     % (bad[:4] + bad_removed[:4]))
    else:
        notes.append('[3] all 16 pages rebuild byte-for-byte as the baseline minus exactly '
                     'the two id-claimed lines')
    if bad_stable:
        fails.append('[3] the 59 non-dosage pages are not untouched: %s' % bad_stable[:4])
    else:
        notes.append('[3] the other 59 pages are byte-identical and never referenced the '
                     'assets')


def check_served(theme, served, fails, notes):
    """[4] The working tree is what the pre-flight copy serves, exactly."""
    table = load_served(served)
    if table is None:
        fails.append('[4] no served manifest: the tree cannot be shown to be the copy the '
                     'server holds (a missing reference is a failure, not a skip)')
    else:
        bad, n = [], 0
        for dirpath, dirnames, filenames in os.walk(theme):
            dirnames[:] = [d for d in dirnames if d not in ('_backup', '__pycache__')]
            for f in filenames:
                if f in ('.DS_Store',) or f.startswith('._'):
                    continue
                p = os.path.join(dirpath, f)
                rel = os.path.relpath(p, theme).replace(os.sep, '/')
                n += 1
                want = table.get(rel)
                got = hashlib.sha256(open(p, 'rb').read()).hexdigest()
                if want is None:
                    bad.append('%s absent from the manifest' % rel)
                elif want != got:
                    bad.append('%s %s != %s' % (rel, got[:12], want[:12]))
        if bad:
            fails.append('[4] working tree vs served copy: %s' % bad[:4])
        else:
            notes.append('[4] all %d files match the served pre-flight copy byte-for-byte' % n)
    for rel in FROZEN:
        if not os.path.exists(os.path.join(theme, rel)):
            fails.append('[4] contract file missing: %s' % rel)
        else:
            notes.append('[4] contract file present and untouched: %s' % rel)
    still_there = [rel for rel in GONE if os.path.exists(os.path.join(theme, rel))]
    if still_there:
        fails.append('[4] still in the tree: %s' % still_there)
    else:
        notes.append('[4] both configurator assets are gone from the tree')


def check_jsonld(base, cand, fails, notes):
    """[5] Structured data and heading counts must not move."""
    drift, bad_h1 = [], []
    for n in pages(base):
        braw, craw = read(os.path.join(base, n)), read(os.path.join(cand, n))
        if [m for m in LDJSON.findall(braw)] != [m for m in LDJSON.findall(craw)]:
            drift.append(n)
        if braw.count('<h1') != 1 or craw.count('<h1') != 1:
            bad_h1.append(n)
    if drift:
        fails.append('[5] JSON-LD drifted: %s' % drift[:4])
    else:
        notes.append('[5] JSON-LD byte-identical on all %d pages' % len(pages(base)))
    if bad_h1:
        fails.append('[5] h1 count is not 1: %s' % bad_h1[:4])
    else:
        notes.append('[5] exactly one h1 per page on all %d pages' % len(pages(base)))


def check_structure(base, cand, fails, notes):
    """[6] The H2b1 invariants survive on the pages this batch edits."""
    bad_order, bad_cta, bad_note, bad_anchor, bad_h2 = [], [], [], [], []
    for n in pages(base):
        if not dosage(n):
            continue
        c = read(os.path.join(cand, n))
        wall, band, hww = c.find('id="formulas"'), c.find(BAND_SECTION), c.find(NEXT_BLOCK)
        if not (0 <= wall < band < hww):
            bad_order.append('%s wall=%d band=%d hww=%d' % (n, wall, band, hww))
        if c.count('sf-quote-cta') < 1:
            bad_cta.append(n)
        if H2B1_NOTE not in c:
            bad_note.append(n)
        if 'id="configurator"' in c or 'href="#configurator"' in c:
            bad_anchor.append(n)
        if c.count(BUILD_H2) != 0:
            bad_h2.append(n)
    if bad_order:
        fails.append('[6] band no longer sits between the card wall and How We Work: %s'
                     % bad_order[:4])
    else:
        notes.append('[6] on all 16 dosage pages the band still sits between #formulas and '
                     'How We Work')
    probed = False
    for lst, msg in ((bad_cta, 'hero CTA missing'), (bad_note, 'the H2b1 author note is gone'),
                     (bad_anchor, 'a #configurator anchor survives'),
                     (bad_h2, 'the configurator heading came back')):
        probed = True
        if lst:
            fails.append('[6] %s: %s' % (msg, lst[:4]))
    if probed and not (bad_cta or bad_note or bad_anchor or bad_h2):
        notes.append('[6] hero CTA, the H2b1 note, and the absence of #configurator all hold')
    bad_detail = [n for n in pages(base) if DETAIL.match(n)
                  and 'sf-quote-cta' not in read(os.path.join(cand, n))]
    if bad_detail:
        fails.append('[6] detail hero CTA: %s' % bad_detail[:4])
    else:
        notes.append('[6] all 42 detail pages keep the retargeted hero CTA')


def check_inputs(base, cand, fails, notes):
    """[0] Both captures must exist and be non-empty — before anything else."""
    for label, d in (('baseline', base), ('candidate', cand)):
        if not os.path.isdir(d):
            fails.append('[0] %s directory does not exist: %s' % (label, d))
        elif len(pages(d)) == 0:
            fails.append('[0] %s directory holds no .html captures: %s' % (label, d))
        elif len(pages(d)) != 75:
            fails.append('[0] %s holds %d pages, expected 75' % (label, len(pages(d))))
    if not fails:
        notes.append('[0] both captures hold 75 pages')


GATES = [('0', check_inputs), ('1', check_inventory), ('2', check_pageset),
         ('3', check_confined), ('4', check_served), ('5', check_jsonld),
         ('6', check_structure)]


def run(base, cand, theme, served, verbose=True):
    fails, notes = [], []
    for tag, fn in GATES:
        if fn is check_served:
            fn(theme, served, fails, notes)
        else:
            fn(base, cand, fails, notes)
        # Gate 0 is a precondition: if either capture is unusable, every later
        # gate would report a derived symptom and bury the cause.
        if fn is check_inputs and fails:
            break
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
            print('VERDICT: PASS — all seven gates hold')
    return fails, notes


# ------------------------------------------------------------- sabotage ----

def mutate(name, base, cand, theme, tmp):
    """Break the candidate on purpose, in a way the gate must notice."""
    P, T = os.path.join(tmp, 'pages'), os.path.join(tmp, 'theme')
    shutil.copytree(cand, P)
    shutil.copytree(theme, T,
                    ignore=shutil.ignore_patterns('_backup', '__pycache__', '.DS_Store', '._*'))
    dose = 'products__soft-chews.html'
    det = 'formulas__calming-soft-chews.html'
    pp = lambda n: os.path.join(P, n)
    w = lambda p, s: open(p, 'w', encoding='utf-8').write(s)

    if name == 'link-restored':
        s = read(pp(dose))
        line = CFG_CSS_LINK.search(read(os.path.join(base, dose))).group(0)
        w(pp(dose), s.replace('<link rel=', line + '\n<link rel=', 1))
    elif name == 'script-restored':
        s = read(pp(dose))
        line = CFG_JS.search(read(os.path.join(base, dose))).group(0)
        w(pp(dose), s.replace('</body>', line + '\n</body>', 1))
    elif name == 'third-line-removed':
        p = pp(dose)
        s = read(p)
        out = [ln for ln in s.split('\n') if H2B1_NOTE not in ln]
        w(p, '\n'.join(out))
    elif name == 'band-chip-missing':
        p = pp(dose)
        s = read(p)
        i = s.find('<a class="sf-explore__chip"')
        j = s.find('</a>', i) + 4
        w(p, s[:i] + s[j:])
    elif name == 'stable-page-touched':
        p = pp('blog.html')
        w(p, read(p).replace('</body>', '<!-- NEGCTL --></body>', 1))
    elif name == 'style-token-moved':
        p = pp('blog.html')
        w(p, read(p).replace('style.css?ver=' + STYLE_TOKEN, 'style.css?ver=2.10.55', 1))
    elif name == 'asset-file-restored':
        src = subprocess.run(['git', '-C', ROOT, 'show',
                              'ebe8f50:sinofresh-theme/assets/css/configurator.css'],
                             capture_output=True).stdout
        d = os.path.join(T, 'assets', 'css')
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, 'configurator.css'), 'wb').write(src)
    elif name == 'jsonld-drift':
        p = pp(dose)
        s = read(p)
        extra = ('<script type="application/ld+json">{"@type":"Thing"}</script>')
        w(p, s.replace('</head>', extra + '</head>', 1))
    elif name == 'declared-page-unchanged':
        w(pp(dose), read(os.path.join(base, dose)))
    elif name == 'detail-cta-reverted':
        p = pp(det)
        w(p, read(p).replace('sf-formula-hero__build sf-quote-cta', 'sf-formula-hero__build', 1))
    else:
        raise SystemExit('unknown sabotage variant %r' % name)
    return P, T


MATRIX = ['link-restored', 'script-restored', 'third-line-removed', 'band-chip-missing',
          'stable-page-touched', 'style-token-moved', 'asset-file-restored',
          'jsonld-drift', 'declared-page-unchanged', 'detail-cta-reverted']


def negcontrol(base, cand, theme, served, tmp, name):
    """Break a *precondition*; the gate must FAIL, never skip."""
    if name == 'served-manifest-missing':
        fails, notes = run(base, cand, theme, os.path.join(tmp, 'nope.manifest'), verbose=False)
        return fails, 'served manifest points at a nonexistent path'
    if name == 'baseline-empty':
        d = os.path.join(tmp, 'empty')
        os.makedirs(d, exist_ok=True)
        fails, notes = run(d, cand, theme, served, verbose=False)
        return fails, 'baseline directory is empty'
    if name == 'candidate-equals-baseline':
        d = os.path.join(tmp, 'asbase')
        shutil.copytree(base, d)
        fails, notes = run(base, d, theme, served, verbose=False)
        return fails, 'candidate is a copy of the baseline'
    raise SystemExit('unknown negative control %r' % name)


NEGCTL = ['served-manifest-missing', 'baseline-empty', 'candidate-equals-baseline']


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--base')
    ap.add_argument('--cand')
    ap.add_argument('--theme', default=os.path.join(ROOT, 'sinofresh-theme'))
    ap.add_argument('--served')
    ap.add_argument('--json')
    ap.add_argument('--matrix', action='store_true')
    ap.add_argument('--negctl', action='store_true')
    ap.add_argument('--sabotage')
    args = ap.parse_args(argv)

    if args.matrix:
        print('=== sabotage matrix — every variant must be caught ===')
        rows, missed = [], []
        for name in MATRIX:
            tmp = tempfile.mkdtemp(prefix='h2b2-sab-')
            try:
                P, T = mutate(name, args.base, args.cand, args.theme, tmp)
                fails, notes = run(args.base, P, T, args.served, verbose=False)
                caught = bool(fails)
                gates = sorted(set(f.split(']')[0] + ']' for f in fails))
                rows.append({'variant': name, 'caught': caught, 'gates': gates,
                             'detail': fails[:3]})
                print('  %-28s %s   %s' % (name, 'CAUGHT' if caught else 'MISSED',
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

    if args.negctl:
        print('=== negative controls — each precondition break must FAIL ===')
        rows, wrong = [], []
        for name in NEGCTL:
            tmp = tempfile.mkdtemp(prefix='h2b2-neg-')
            try:
                fails, desc = negcontrol(args.base, args.cand, args.theme, args.served, tmp, name)
                caught = bool(fails)
                named = bool(re.findall(r'^\[\d+\]', ' '.join(fails)))
                rows.append({'control': name, 'description': desc, 'failed': caught,
                             'named_verdict': named, 'detail': fails[:2]})
                print('  %-28s %s  %s' % (name, 'FAIL (as required)' if caught and named
                                          else 'NOT A VERDICT', desc))
                if not (caught and named):
                    wrong.append(name)
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
        print('-' * 72)
        print('  %d/%d controls failed as required' % (len(NEGCTL) - len(wrong), len(NEGCTL)))
        if wrong:
            print('  WRONG: %s' % wrong)
        if args.json:
            json.dump({'controls': rows, 'wrong': wrong},
                      open(args.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        return 1 if wrong else 0

    if args.sabotage:
        tmp = tempfile.mkdtemp(prefix='h2b2-sab-')
        try:
            P, T = mutate(args.sabotage, args.base, args.cand, args.theme, tmp)
            fails, notes = run(args.base, P, T, args.served)
            return 1 if fails else 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    if not (args.base and args.cand):
        ap.error('--base and --cand are required')
    fails, notes = run(args.base, args.cand, args.theme, args.served)
    if args.json:
        json.dump({'fails': fails, 'notes': notes},
                  open(args.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())

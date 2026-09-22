#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H6 gate — the confined-change proof, the coverage claim, the
invariants, the sabotage matrix and the named negative controls.

WHY THIS IS NOT THE H5 GATE

H5 ADDED schema properties and REPLACED alt strings, so its gate had to parse
JSON-LD and invert declared substitutions. H6 only DELETES (dead CSS, an orphan
shortcode, a dead sessionStorage write, a dead scroll branch, a 1.2 KB JSON
payload) and corrects one version token. The proof this batch can carry is
consequently sharper than either of those:

    the candidate must equal the baseline with exactly the declared edits
    applied — the two version tokens moved, and every
    <script type="application/json" class="sf-formulas-data"> element removed —
    byte for byte, on all 75 pages, and nothing else may differ.

That fixes the CONTENT of the change as well as its EXTENT: a page that gained a
character somewhere else is a failure, and a page where the removal did not
happen is a failure, in the same single comparison.

AND A SECOND CLAIM, because the byte proof is derivable in principle from a
laxer gate

A gate that only asked "is the payload gone?" would pass a candidate carrying an
unrelated regression, and a gate that only asked "do the bytes match after
folding?" would pass a candidate where the payload removal silently did not
happen on 3 of 60 pages (folding never touches it, so it would show as a diff —
but only because this batch happens to declare the removal). H6 therefore states
the removal separately:

  * COVERAGE  the declared OLD strings must have ZERO occurrences on the
    candidate: `class="sf-formulas-data"`, `?ver=2.10.60`, `?ver=1.1.0`.
  * INVARIANTS, which outlive the declared pair list: the ItemList block count,
    the .sf-fcard / .sf-formula__cta / .sf-fgrid counts, the formulas.js
    handle, the detail-page h1 count and the site-wide logo alt count are the
    same on both sides — measured without reference to what the batch meant to
    touch.
  * SOURCE, which the rendered断面 cannot see: 36 CSS rules and one shortcode
    left the theme, and the two parsing helpers they were tangled with did NOT.
    The rendered pages look identical whether or not those helpers still exist,
    so this is the only place that trap can be caught.

WHY style.css's CONTENT IS NOT IN THE BYTE PROOF

style.css is enqueued as an external file; the pages carry only its URL and
token. Deleting 9 KB of dead rules is therefore invisible to a rendered capture,
which is exactly why the source-side check above exists rather than being
folded into the page comparison.

usage:
    b2d_h6_confine.py --base DIR --cand DIR            # main proof + coverage + invariants
    b2d_h6_confine.py --base DIR --cand DIR --aa DIR2  # A/A: two captures of the SAME state
    b2d_h6_confine.py --source [--theme DIR]           # source-side invariants
    b2d_h6_confine.py --base DIR --cand DIR --matrix   # sabotage matrix
    b2d_h6_confine.py --base DIR --cand DIR --negctl   # named negative controls
    [--json OUT] on any mode
"""
import argparse
import copy
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from sf_masked_cmp import masked                                     # noqa: E402

# ---------------------------------------------------------------- declarations

# The two version tokens. Paired with the file name so an unrelated asset that
# happens to carry the same number is never folded by accident.
FOLD = [
    ('style.css?ver=2.10.60',   'style.css?ver=2.10.61'),
    ('formulas.js?ver=1.1.0',   'formulas.js?ver=1.2.0'),
]
NEW_STYLE_VER = '2.10.61'
NEW_JS_VER = '1.2.0'
OLD_STYLE_VER = '2.10.60'
OLD_JS_VER = '1.1.0'

# The deleted element. Anchored on the exact attribute pair the shortcode
# printed, and non-greedy: the JSON body is escaped (`<\\/script`) by
# sinofresh_formula_script_json(), so the first </script> really is the end.
PAYLOAD_RE = re.compile(
    r'<script type="application/json" class="sf-formulas-data">.*?</script>', re.S)

# Declared OLD strings that must be gone from the candidate (coverage).
#
# File-qualified on purpose. A bare `?ver=1.1.0` is NOT specific to this batch:
# measured on the synthetic candidate, 76 occurrences of `?ver=1.1.0` survive on
# pages that never enqueue formulas.js at all (some other asset, shipped by
# something else, is also at 1.1.0). An unqualified token would make the
# coverage claim fail on pages this batch never touched — and, worse, would let
# a sabotage case look "caught" for the wrong reason.
GONE_TOKENS = ['class="sf-formulas-data"',
               'style.css?ver=' + OLD_STYLE_VER,
               'formulas.js?ver=' + OLD_JS_VER]

# The dead CSS families. Zero occurrences anywhere in style.css, comments
# included — the batch rewrote the four comments that used to name them.
DEAD_CSS = ['.sf-facts__', '.sf-spectable__', '.sf-fdetail-media__',
            '.configurator__summary-value']
# Live rules that must survive the same edit, including three that sit inside
# rules the batch rewrote or next to rules it cut.
LIVE_CSS = ['.sf-num', '.sf-facts-mini', '.sf-facts-mini__value',
            '.sf-actives__title', '.sf-actives__intro', '.sf-actives__list',
            '.sf-actives__item', '.sf-actives__name', '.sf-actives__label',
            '.sf-actives__ing', '.sf-actives__pill', '.sf-spectable {']

# Source-side declarations, per file.
PHP_DEF_ONCE = ['function sinofresh_formula_split_top_level(',
                'function sinofresh_formula_analysis_pairs(']
PHP_DEF_GONE = ['function sinofresh_formula_actives(',
                "<script type=\"application/json\" class=\"sf-formulas-data\">"]
PHP_REG_GONE = ["add_shortcode('sf_formula_actives'"]
PHP_TOKENS = ["'2.10.61'", "'1.2.0'"]
# call counts AFTER the batch: split_top_level is called by analysis_pairs and
# by [sf_formula_detail_actives]; analysis_pairs by [sf_formula_detail_actives].
PHP_CALLS = {'sinofresh_formula_split_top_level($': 2,
             'sinofresh_formula_analysis_pairs($': 1}
JS_CODE_GONE = ['sessionStorage', 'getElementById', 'scrollIntoView',
                "getAttribute('data-form')"]

H1_SIDE = re.compile(r'class="sf-fdetail2__title"')
DETAIL = re.compile(r'^(zh__)?formulas__[\w\-]+\.html$')
DOSE = re.compile(r'^(zh__)?products__[\w\-]+\.html$')
LOGO_ALT = 'alt="SINO FRESH logo"'
LOGO_ALT_TOTAL = 150          # batch H5's invariant, still carried


def pages(d):
    return sorted(f[:-5] for f in os.listdir(d) if f.endswith('.html'))


def read(p):
    return open(p, encoding='utf-8', errors='replace').read()


def strip_js_comments(s):
    s = re.sub(r'/\*.*?\*/', '', s, flags=re.S)
    return re.sub(r'(?m)^[ \t]*//.*$', '', s)


def first_diff(a, b):
    n = min(len(a), len(b))
    for i in range(n):
        if a[i] != b[i]:
            return i
    return n if len(a) != len(b) else -1


def ctx(s, i, back=80, fwd=70):
    return s[max(0, i - back):i + fwd]


# ------------------------------------------------------------------ main proof

def main_proof(base, cand, verbose=True):
    """expected = fold(base) minus every declared payload element; must == cand."""
    rows, bad = [], 0
    folds = {'style': 0, 'js': 0}
    pages_with_payload, payload_bytes, payload_elems = 0, 0, 0
    parsed_ok = 0
    ld_before = ld_after = 0

    names = sorted(set(pages(base)) | set(pages(cand)))
    for n in names:
        pa, pb = os.path.join(base, n + '.html'), os.path.join(cand, n + '.html')
        if not (os.path.exists(pa) and os.path.exists(pb)):
            rows.append({'page': n, 'status': 'MISSING'})
            bad += 1
            continue
        A, B = read(pa), read(pb)

        exp = A
        for old, new in FOLD:
            if old in exp:
                folds['style' if old.startswith('style.css') else 'js'] += 1
                exp = exp.replace(old, new)

        removed = []

        def _cut(m):
            removed.append(m.group(0))
            return ''

        exp = PAYLOAD_RE.sub(_cut, exp)

        if removed:
            pages_with_payload += 1
            payload_elems += len(removed)
            for el in removed:
                inner = el[el.index('>') + 1:-len('</script>')]
                payload_bytes += len(inner)
                try:
                    json.loads(inner)
                    parsed_ok += 1
                except ValueError:
                    pass

        ld_before += len(re.findall(r'type="application/ld\+json"', A))
        ld_after += len(re.findall(r'type="application/ld\+json"', B))

        ok = exp == B
        row = {'page': n, 'status': 'MATCH' if ok else 'MISMATCH',
               'removed_elems': len(removed),
               'removed_bytes': sum(len(x) for x in removed)}
        if not ok:
            bad += 1
            i = first_diff(exp, B)
            row['first_diff_at'] = i
            row['expected'] = ctx(exp, i)
            row['candidate'] = ctx(B, i)
            row['exp_len'] = len(exp)
            row['cand_len'] = len(B)
        rows.append(row)

    ok = bad == 0
    if verbose:
        for r in rows:
            if r['status'] != 'MATCH':
                print('  %-42s %s  exp %s / cand %s  @%s' % (
                    r['page'], r['status'], r.get('exp_len'), r.get('cand_len'),
                    r.get('first_diff_at')))
                if r['status'] == 'MISMATCH':
                    print('      expected :', repr(r['expected']))
                    print('      candidate:', repr(r['candidate']))
        print('  pages                : %d  (%d mismatched/missing)' % (len(rows), bad))
        print('  folded style token   : %d pages' % folds['style'])
        print('  folded js token      : %d pages' % folds['js'])
        print('  payload removed      : %d element(s) on %d page(s), %d JSON bytes'
              % (payload_elems, pages_with_payload, payload_bytes))
        print('  payload parsed ok    : %d/%d' % (parsed_ok, payload_elems))
        print('  ld+json blocks       : %d -> %d' % (ld_before, ld_after))
        print('  %s  confined change: %d/%d pages equal after the declared edit'
              % ('PASS' if ok else 'FAIL', len(rows) - bad, len(rows)))

    rep = {'ok': ok, 'rows': rows, 'diff': bad,
           'folded': folds, 'payload_pages': pages_with_payload,
           'payload_elems': payload_elems, 'payload_bytes': payload_bytes,
           'payload_parsed': parsed_ok, 'ld_json': [ld_before, ld_after]}
    # three side assertions the headline claim depends on
    extra = []
    if folds['style'] != 75:
        extra.append('style token folded on %d pages, expected 75' % folds['style'])
    if folds['js'] != 60:
        extra.append('js token folded on %d pages, expected 60' % folds['js'])
    if pages_with_payload != 60:
        extra.append('payload found on %d pages, expected 60' % pages_with_payload)
    if payload_elems != pages_with_payload:
        extra.append('more than one payload element on some page')
    if parsed_ok != payload_elems:
        extra.append('%d payload(s) did not parse as JSON' % (payload_elems - parsed_ok))
    if extra:
        rep['ok'] = False
        if verbose:
            for e in extra:
                print('  FAIL  ' + e)
    return rep


# -------------------------------------------------------------------- coverage

def coverage(cand, verbose=True):
    names = pages(cand)
    counts = {t: 0 for t in GONE_TOKENS}
    pages_hit = {t: [] for t in GONE_TOKENS}
    new_style = new_js = 0
    for n in names:
        t = read(os.path.join(cand, n + '.html'))
        for tok in GONE_TOKENS:
            c = t.count(tok)
            if c:
                counts[tok] += c
                pages_hit[tok].append('%s(%d)' % (n, c))
        if 'style.css?ver=' + NEW_STYLE_VER in t:
            new_style += 1
        if 'formulas.js?ver=' + NEW_JS_VER in t:
            new_js += 1
    bad = sum(counts.values())
    ok = bad == 0 and new_style == 75 and new_js == 60
    if verbose:
        for tok in GONE_TOKENS:
            flag = 'ok ' if counts[tok] == 0 else 'HIT'
            print('  %s  %-32s %d occurrence(s)  %s'
                  % (flag, tok, counts[tok], ' '.join(pages_hit[tok][:6])))
        print('  new style token 2.10.61 present on : %d pages (want 75)' % new_style)
        print('  new js token    1.2.0 present on   : %d pages (want 60)' % new_js)
        print('  %s  coverage: declared old strings are gone'
              % ('PASS' if ok else 'FAIL'))
    return {'ok': ok, 'counts': counts, 'pages_hit': pages_hit,
            'new_style_pages': new_style, 'new_js_pages': new_js}


# ------------------------------------------------------------------ invariants

def invariants(base, cand, verbose=True):
    names = sorted(set(pages(base)) & set(pages(cand)))
    keys = ['ld_json', 'sf-fgrid', 'sf-fcard', 'sf-formula__cta', 'logo_alt',
            'formulas_js_handle']
    rows, bad = [], 0
    for n in names:
        A = read(os.path.join(base, n + '.html'))
        B = read(os.path.join(cand, n + '.html'))
        rec = {}
        for k, pat in [('ld_json', 'type="application/ld+json"'),
                       ('sf-fgrid', 'class="sf-fgrid"'),
                       ('sf-fcard', 'class="sf-fcard"'),
                       ('sf-formula__cta', 'sf-formula__cta'),
                       ('logo_alt', LOGO_ALT),
                       ('formulas_js_handle', 'id="sinofresh-formulas-js"')]:
            rec[k] = (A.count(pat), B.count(pat))
        # detail pages keep exactly one h1, in the right column (H5-0's fix)
        if DETAIL.match(n):
            rec['detail_h1'] = (A.count('<h1'), B.count('<h1'))
            rec['side_title'] = (len(H1_SIDE.findall(A)), len(H1_SIDE.findall(B)))
        diffk = [k for k, v in rec.items() if v[0] != v[1]]
        if diffk:
            bad += 1
            rows.append({'page': n, 'diff': diffk, 'counts': rec})
    tot_logo = sum(read(os.path.join(cand, n + '.html')).count(LOGO_ALT) for n in names)
    ok = bad == 0 and tot_logo == LOGO_ALT_TOTAL
    if verbose:
        for r in rows[:10]:
            print('  %-42s %s' % (r['page'], r['diff']))
            for k in r['diff']:
                print('      %-20s %s -> %s' % (k, r['counts'][k][0], r['counts'][k][1]))
        print('  pages with a changing count : %d' % bad)
        print('  logo alt total on candidate  : %d (want %d)' % (tot_logo, LOGO_ALT_TOTAL))
        print('  %s  invariants' % ('PASS' if ok else 'FAIL'))
    return {'ok': ok, 'bad': bad, 'rows': rows, 'logo_total': tot_logo}


# ----------------------------------------------------------- source invariants

def source_checks(theme, verbose=True):
    fn = read(os.path.join(theme, 'functions.php'))
    css = read(os.path.join(theme, 'style.css'))
    js = read(os.path.join(theme, 'assets/js/formulas.js'))
    jscode = strip_js_comments(js)
    checks = []

    for s in PHP_DEF_ONCE:
        checks.append(('%s defined exactly once' % s.split()[-1][:-1], fn.count(s) == 1))
    for s in PHP_DEF_GONE:
        checks.append(('gone: %s' % s[:52], s not in fn))
    for s in PHP_REG_GONE:
        checks.append(('gone: %s' % s, s not in fn))
    for s, want in PHP_CALLS.items():
        checks.append(('%s called %d time(s) (defined once)'
                       % (s.split('(')[0], want), fn.count(s) - 1 == want))
    for s in PHP_TOKENS:
        checks.append(('token %s in functions.php' % s, s in fn))
    checks.append(('helper consumer note present',
                   'retired [sf_formula_actives] band' in fn))

    checks.append(('style.css Version: %s' % NEW_STYLE_VER,
                   ('Version: ' + NEW_STYLE_VER) in css))
    checks.append(('style.css no longer says Version: %s' % OLD_STYLE_VER,
                   ('Version: ' + OLD_STYLE_VER) not in css))
    for t in DEAD_CSS:
        checks.append(('css dead token gone: %s' % t, t not in css))
    for t in LIVE_CSS:
        checks.append(('css live rule kept: %s' % t, t in css))

    for t in JS_CODE_GONE:
        checks.append(('js code no longer mentions %s' % t, t not in jscode))

    ok = all(v for _, v in checks)
    if verbose:
        for name, v in checks:
            print('  %s  %s' % ('ok  ' if v else 'FAIL', name))
        print('  %s  source invariants (%d checks)' % ('PASS' if ok else 'FAIL', len(checks)))
    return {'ok': ok, 'checks': checks}


# ---------------------------------------------------------------- A/A control

def aa(dir_a, dir_b, verbose=True):
    rows, bad = [], 0
    names = sorted(set(pages(dir_a)) | set(pages(dir_b)))
    for n in names:
        pa, pb = os.path.join(dir_a, n + '.html'), os.path.join(dir_b, n + '.html')
        if not (os.path.exists(pa) and os.path.exists(pb)):
            rows.append({'page': n, 'status': 'MISSING'})
            bad += 1
            continue
        ma, _ = masked(read(pa))
        mb, _ = masked(read(pb))
        same = ma == mb
        if not same:
            bad += 1
            i = first_diff(ma, mb)
            rows.append({'page': n, 'status': 'DIFF', 'at': i,
                         'a': ctx(ma, i, 70, 50), 'b': ctx(mb, i, 70, 50)})
        else:
            rows.append({'page': n, 'status': 'SAME'})
    ok = bad == 0
    if verbose:
        for r in rows:
            if r['status'] != 'SAME':
                print('  %-42s %s @%s' % (r['page'], r['status'], r.get('at')))
                print('      A:', repr(r.get('a')))
                print('      B:', repr(r.get('b')))
        print('  %s  A/A masked self-test: %d/%d identical'
              % ('PASS' if ok else 'FAIL', len(rows) - bad, len(rows)))
    return {'ok': ok, 'diff': bad, 'rows': rows}


# ----------------------------------------------------------------- the matrix

def sabotage_cases(base, cand):
    """Each case returns (name, builder).

    A builder returns the number of BYTES it changed. Zero means the sabotage
    never happened — the target string was not there — and the matrix reports it
    as INVALID rather than as "caught". Without that check the first build of
    this tool scored 9/9 on a matrix whose unrelated-byte case was silently a
    no-op: proof=PASS, and the case was only counted because the coverage
    assertion was (then) wrong for an unrelated reason.
    """
    return [
        ('M1 restore style ver on ONE page',
         lambda D: _unfold(D, ['formulas'], 'style.css?ver=2.10.61', 'style.css?ver=2.10.60')),
        ('M2 restore style ver on ALL pages',
         lambda D: _unfold(D, None, 'style.css?ver=2.10.61', 'style.css?ver=2.10.60')),
        ('M3 restore js ver on all pages',
         lambda D: _unfold(D, None, 'formulas.js?ver=1.2.0', 'formulas.js?ver=1.1.0')),
        ('M4 restore the payload on ONE page',
         lambda D: _reinject(D, ['formulas'], base)),
        ('M5 restore the payload on all 60 pages',
         lambda D: _reinject(D, None, base)),
        ('M6 a stray comment before </body> on one page',
         lambda D: _stray(D, 'faq')),
        ('M7 one ItemList block deleted',
         lambda D: _drop_document(D, 'about')),
        ('M8 payload injected on a page that had none',
         lambda D: _inject_foreign(D, 'about', base)),
        ('M9 candidate == baseline (nothing changed at all)',
         lambda D: _clone(base, D)),
        ('M10 one character of visible copy changed',
         lambda D: _copyflip(D, 'faq')),
    ]


def _write(p, t):
    open(p, 'w', encoding='utf-8').write(t)


def _clone(src, dst):
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(src, dst)
    return sum(os.path.getsize(os.path.join(src, f)) for f in os.listdir(src)
               if f.endswith('.html'))


def _unfold(d, only, old, new):
    """Count REPLACEMENTS, not bytes: the two tokens are the same length, so a
    byte-count would report 0 and the matrix would call a real sabotage a no-op."""
    n = 0
    for pg in (only or pages(d)):
        p = os.path.join(d, pg + '.html')
        if os.path.exists(p):
            t = read(p)
            c = t.count(old)
            if c:
                _write(p, t.replace(old, new))
                n += c
    return n


def _reinject(d, only, base):
    n = 0
    for pg in (only or pages(d)):
        pc = os.path.join(d, pg + '.html')
        if not os.path.exists(pc):
            continue
        el = PAYLOAD_RE.search(read(os.path.join(base, pg + '.html')))
        if not el:
            continue
        t = read(pc)
        anchor = '<script type="application/ld+json">'
        if anchor in t:
            _write(pc, t.replace(anchor, el.group(0) + anchor, 1))
            n += len(el.group(0))
    return n


def _stray(d, pg):
    p = os.path.join(d, pg + '.html')
    t = read(p)
    if '</body>' not in t:
        return 0
    _write(p, t.replace('</body>', '<!--h6-sabotage--></body>', 1))
    return 15


def _copyflip(d, pg):
    p = os.path.join(d, pg + '.html')
    t = read(p)
    for needle in ('How We Work', 'Private Label', 'SINO FRESH'):
        if needle in t:
            _write(p, t.replace(needle, needle[:-1] + needle[-1].swapcase(), 1))
            return len(needle)
    return 0


def _drop_document(d, pg):
    p = os.path.join(d, pg + '.html')
    t = read(p)
    m = re.search(r'<script type="application/ld\+json">.*?</script>', t, re.S)
    if not m:
        return 0
    _write(p, t[:m.start()] + t[m.end():])
    return m.end() - m.start()


def _inject_foreign(d, pg, base):
    """Copy a payload element onto a page the batch never touched."""
    pc = os.path.join(d, pg + '.html')
    el = PAYLOAD_RE.search(read(os.path.join(base, 'formulas.html')))
    if not el:
        return 0
    t = read(pc)
    if '</head>' not in t:
        return 0
    _write(pc, t.replace('</head>', el.group(0) + '</head>', 1))
    return len(el.group(0))


def matrix(base, cand, verbose=True):
    rows = []
    for name, build in sabotage_cases(base, cand):
        with tempfile.TemporaryDirectory() as td:
            D = os.path.join(td, 'cand')
            shutil.copytree(cand, D)
            changed = build(D)
            proof = main_proof(base, D, verbose=False)
            cov = coverage(D, verbose=False)
            inv = invariants(base, D, verbose=False)
            caught = (not proof['ok']) or (not cov['ok']) or (not inv['ok'])
            rows.append({'case': name, 'changed': changed, 'caught': caught,
                         'proof_ok': proof['ok'], 'coverage_ok': cov['ok'],
                         'invariants_ok': inv['ok']})
            if verbose:
                print('  %s  %-46s changed=%-6d proof=%s coverage=%s invariants=%s'
                      % ('ok  ' if caught else 'MISS', name, changed,
                         'PASS' if proof['ok'] else 'FAIL',
                         'PASS' if cov['ok'] else 'FAIL',
                         'PASS' if inv['ok'] else 'FAIL'))
    # control: the real candidate must pass all three
    proof = main_proof(base, cand, verbose=False)
    cov = coverage(cand, verbose=False)
    inv = invariants(base, cand, verbose=False)
    control = proof['ok'] and cov['ok'] and inv['ok']
    vacuous = [r['case'] for r in rows if not r['changed']]
    missed = [r['case'] for r in rows if not r['caught']]
    ok = control and not missed and not vacuous
    if verbose:
        for c in vacuous:
            print('  FAIL  sabotage case was a no-op: %s' % c)
        print('  %s  control: the real candidate passes all three gates'
              % ('ok  ' if control else 'FAIL'))
        print('  %s  matrix: %d/%d sabotage cases caught, %d vacuous'
              % ('PASS' if ok else 'FAIL', len(rows) - len(missed), len(rows), len(vacuous)))
    return {'ok': ok, 'rows': rows, 'control': control, 'missed': missed, 'vacuous': vacuous}


# --------------------------------------------------------- named neg controls

def negctl(base, cand, theme, verbose=True):
    """Each control destroys one claim and MUST be caught by the matching check."""
    rows = []

    def rec(name, must_fail_ok, detail):
        rows.append({'control': name, 'caught': must_fail_ok, 'detail': detail})

    # N1  the proof is not vacuous: base vs base must FAIL (no edit happened)
    p = main_proof(base, base, verbose=False)
    rec('N1 base vs base must FAIL the byte proof', not p['ok'],
        'proof_ok=%s' % p['ok'])

    # N2  coverage alone is blind to an unrelated change
    with tempfile.TemporaryDirectory() as td:
        D = os.path.join(td, 'cand')
        shutil.copytree(cand, D)
        changed = _stray(D, 'faq')
        p = main_proof(base, D, verbose=False)
        c = coverage(D, verbose=False)
        rec('N2 coverage-only gate PASSES while the byte proof FAILS',
            changed > 0 and c['ok'] and not p['ok'],
            'changed=%d coverage=%s proof=%s' % (changed, c['ok'], p['ok']))

    # N3  the byte proof's fold cannot hide a missing removal on all pages
    with tempfile.TemporaryDirectory() as td:
        D = os.path.join(td, 'cand')
        shutil.copytree(cand, D)
        _reinject(D, None, base)
        p = main_proof(base, D, verbose=False)
        c = coverage(D, verbose=False)
        rec('N3 restoring every payload FAILS coverage and the byte proof',
            (not c['ok']) and (not p['ok']), 'coverage=%s proof=%s' % (c['ok'], p['ok']))

    # N4  deleting a helper with the orphan: rendered pages cannot see it, so the
    #     SOURCE check is the only thing that can catch this trap.
    with tempfile.TemporaryDirectory() as td:
        T = os.path.join(td, 'theme')
        shutil.copytree(theme, T)
        f = os.path.join(T, 'functions.php')
        t = read(f)
        i = t.index('function sinofresh_formula_split_top_level(')
        j = t.index('\nfunction ', i + 10)
        open(f, 'w', encoding='utf-8').write(t[:i] + t[j + 1:])
        s = source_checks(T, verbose=False)
        rec('N4 deleting sinofresh_formula_split_top_level must FAIL the source check',
            not s['ok'], 'source_ok=%s' % s['ok'])

    # N5  the same trap for its stylesheet hooks
    with tempfile.TemporaryDirectory() as td:
        T = os.path.join(td, 'theme')
        shutil.copytree(theme, T)
        f = os.path.join(T, 'style.css')
        open(f, 'w', encoding='utf-8').write(read(f).replace('.sf-actives__pill', '.sf-actives__pill-gone'))
        s = source_checks(T, verbose=False)
        rec('N5 deleting the .sf-actives__* styles must FAIL the source check',
            not s['ok'], 'source_ok=%s' % s['ok'])

    # N6  a theme that never got the edit must FAIL the source check
    with tempfile.TemporaryDirectory() as td:
        T = os.path.join(td, 'theme')
        shutil.copytree(theme, T)
        f = os.path.join(T, 'style.css')
        open(f, 'w', encoding='utf-8').write(read(f).replace('Version: ' + NEW_STYLE_VER,
                                                             'Version: ' + OLD_STYLE_VER))
        s = source_checks(T, verbose=False)
        rec('N6 an unapplied style.css version must FAIL the source check',
            not s['ok'], 'source_ok=%s' % s['ok'])

    ok = all(r['caught'] for r in rows)
    if verbose:
        for r in rows:
            print('  %s  %s  [%s]' % ('ok  ' if r['caught'] else 'MISS',
                                      r['control'], r['detail']))
        print('  %s  negctl: %d/%d controls caught'
              % ('PASS' if ok else 'FAIL', sum(1 for r in rows if r['caught']), len(rows)))
    return {'ok': ok, 'rows': rows}


# ----------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base')
    ap.add_argument('--cand')
    ap.add_argument('--aa', nargs=2, metavar=('DIR_A', 'DIR_B'))
    ap.add_argument('--source', action='store_true')
    ap.add_argument('--matrix', action='store_true')
    ap.add_argument('--negctl', action='store_true')
    ap.add_argument('--theme', default=os.path.join(ROOT, 'sinofresh-theme'))
    ap.add_argument('--json')
    args = ap.parse_args()

    out = {}
    ok = True

    if args.aa:
        print('== A/A (two captures of the same state) ==')
        r = aa(args.aa[0], args.aa[1]); out['aa'] = r; ok &= r['ok']

    if args.source:
        print('== source-side invariants (%s) ==' % os.path.relpath(args.theme, ROOT))
        r = source_checks(args.theme); out['source'] = r; ok &= r['ok']

    if args.base and args.cand:
        print('== main proof: candidate == fold(baseline) minus the declared payload ==')
        r = main_proof(args.base, args.cand); out['proof'] = r; ok &= r['ok']
        print('== coverage: the declared old strings are gone from the candidate ==')
        r = coverage(args.cand); out['coverage'] = r; ok &= r['ok']
        print('== invariants: counts that do not depend on the declaration ==')
        r = invariants(args.base, args.cand); out['invariants'] = r; ok &= r['ok']
        if args.matrix:
            print('== sabotage matrix ==')
            r = matrix(args.base, args.cand); out['matrix'] = r; ok &= r['ok']
        if args.negctl:
            print('== named negative controls ==')
            r = negctl(args.base, args.cand, args.theme); out['negctl'] = r; ok &= r['ok']

    print('\n%s  batch H6 gate' % ('PASS' if ok else 'FAIL'))
    if args.json:
        json.dump(out, open(args.json, 'w'), indent=1)
        print('  json -> %s' % args.json)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())

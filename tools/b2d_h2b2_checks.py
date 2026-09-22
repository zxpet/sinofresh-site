#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H2b2 — static self-checks S1-S8, run before any gate.

A pure-deletion batch is where a *silent* over-delete is most likely, because
the diff that proves correctness is also the diff that would hide it. So these
checks pin both directions: the things that had to go, and the things that had
to stay. Three of them exist because of specific traps found in the Step 0
scan:

  * `$is_dosage_page` (functions.php:185-186) is used twice — once by the
    configurator block being deleted, once by the formulas.js enqueue at the
    old L205 which is part of the K1 contract. Deleting "two lines" would leave
    an empty `if` shell; deleting the whole region blindly would break
    formulas.js. S1 asserts the surviving count is exactly 2.
  * `configurator.js` keeps appearing in five *comment* lines that record the
    K2 data block's rationale. A naive "no configurator.js anywhere" check
    fails on correct output; a naive pass lets those comments be tidied away.
    S5 counts them.
  * The `:has(` ledger is an *occurrence* count, not a line count —
    `grep -c` on configurator.css returns 5 and `grep -o | wc -l` returns 7,
    because two of the seven sit inside a comment. S3 uses occurrences.

usage:
    python3 tools/b2d_h2b2_checks.py [--json out.json]
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
# SF_THEME lets the negative-control harness point the same checks at a mutated
# copy — a check that cannot fail is not a check, and the only way to show it
# can fail is to run it against bytes that should fail.
THEME = os.environ.get('SF_THEME') or os.path.join(ROOT, 'sinofresh-theme')
sys.path.insert(0, HERE)
from b2d_h2b1_css import php_binary, read, strip_comments, family_heads  # noqa: E402

BASE_COMMIT = 'ebe8f50'
CSS_REL = 'assets/css/configurator.css'
JS_REL = 'assets/js/configurator.js'
FROZEN = ['assets/js/formulas.js', 'assets/js/basket.js',
          'inc/config-pdf.php', 'inc/formula-pools.php']
EXPECT_HAS = 164
DOSE_TEMPLATES = ['page-soft-chews.html', 'page-tablets.html', 'page-powders.html',
                  'page-pastes.html', 'page-drops.html', 'page-liquids.html',
                  'page-fish-oil.html', 'page-dental-chews.html']
H2B1_NOTE = 'moved out of the configurator, batch H2b1'

BLOCK_COMMENT = re.compile(r'/\*.*?\*/', re.S)
SKIP_DIRS = {'_backup', '__pycache__'}
SKIP_FILES = ('.DS_Store',)


def git(*args):
    return subprocess.run(['git', '-C', ROOT] + list(args),
                          capture_output=True, text=True).stdout


def theme_files():
    """Every file under sinofresh-theme bar the local-only `_backup` snapshots.

    `.DS_Store` and `__pycache__` are excluded because they are untracked
    macOS/Python droppings: they exist in the working tree but not at any
    commit, so counting them makes a file-count assertion fail for a reason
    that has nothing to do with the batch.
    """
    out = []
    for dirpath, dirnames, filenames in os.walk(THEME):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for f in filenames:
            if f in SKIP_FILES or f.startswith('._'):
                continue
            out.append(os.path.relpath(os.path.join(dirpath, f), THEME))
    return sorted(out)


def base_files():
    """The same set as `theme_files()`, but as recorded at BASE_COMMIT.

    `-z` + NUL split instead of line split: git quotes non-ASCII paths in
    `--name-only` output, so the 12 screenshot filenames here arrive as
    `"...\\345\\256..."` and a plain string comparison reports them as
    simultaneously added and deleted.
    """
    p = subprocess.run(['git', '-C', ROOT, 'ls-tree', '-r', '-z', '--name-only',
                        BASE_COMMIT, 'sinofresh-theme'], capture_output=True)
    names = p.stdout.decode('utf-8').split('\0')
    rel = []
    for n in names:
        if not n or not n.startswith('sinofresh-theme/'):
            continue
        r = n[len('sinofresh-theme/'):]
        if r.split('/')[0] in SKIP_DIRS or os.path.basename(r) in SKIP_FILES:
            continue
        rel.append(r)
    return sorted(rel)


def blob(rel):
    """The bytes of `rel` at BASE_COMMIT ('' when absent)."""
    p = subprocess.run(['git', '-C', ROOT, 'show', '%s:sinofresh-theme/%s' % (BASE_COMMIT, rel)],
                       capture_output=True)
    return p.stdout if p.returncode == 0 else None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--json')
    args = ap.parse_args(argv)

    res = {'checks': [], 'errors': []}

    def chk(tag, title, ok, detail):
        res['checks'].append({'id': tag, 'title': title, 'ok': bool(ok), 'detail': detail})
        print('  %-4s %-46s %s  %s' % (tag, title, 'PASS' if ok else 'FAIL', detail))
        if not ok:
            res['errors'].append('%s %s: %s' % (tag, title, detail))

    print('=== H2b2 static checks ===')

    # Required inputs, asserted first. Without this, a missing functions.php
    # surfaces as a FileNotFoundError traceback (exit 1) — numerically the same
    # as a FAIL but with no verdict, no check id, and no JSON. The
    # `functions-php-absent` negative control caught exactly that, so the
    # absence is now its own S0 FAIL.
    absent = [r for r in ('functions.php', 'style.css')
              if not os.path.exists(os.path.join(THEME, r))]
    if absent:
        chk('S0', 'required inputs present', False, 'absent=%s' % absent)
        res['ok'] = False
        print('-' * 72)
        print('  VERDICT: FAIL — 1 problem(s)')
        if args.json:
            json.dump(res, open(args.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        return 1

    func = read(os.path.join(THEME, 'functions.php'))
    func0 = blob('functions.php').decode('utf-8')

    # ---- S1 functions.php ---------------------------------------------------
    live = BLOCK_COMMENT.sub(lambda m: '\n' * m.group(0).count('\n'), func)
    detail = []
    ok = True
    if func.count('$dosage_pages = [') != 1:
        ok = False; detail.append('$dosage_pages x%d' % func.count('$dosage_pages = ['))
    if func.count('$is_dosage_page') != 2:
        ok = False; detail.append('$is_dosage_page x%d != 2' % func.count('$is_dosage_page'))
    if func.count("if ($is_dosage_page || is_singular('sf_formula')") != 1:
        ok = False; detail.append('formulas.js guard missing')
    if 'sinofresh-configurator' in live:
        ok = False; detail.append('sinofresh-configurator still live')
    for needle in ("'/assets/css/configurator.css'", "'/assets/js/configurator.js'"):
        if needle in live:
            ok = False; detail.append('enqueue path %s lives' % needle)
    if func.count('{') - func0.count('{') != -1 or func.count('}') - func0.count('}') != -1:
        ok = False; detail.append('brace delta %+d/%+d != -1/-1'
                                  % (func.count('{') - func0.count('{'),
                                     func.count('}') - func0.count('}')))
    dl = func.count('\n') - func0.count('\n')
    if dl != -4:
        ok = False; detail.append('line delta %+d != -4' % dl)
    chk('S1', 'functions.php: guard kept, enqueues gone', ok, '; '.join(detail) or
        'is_dosage_page x2, formulas guard intact, -4 lines')

    php = php_binary()
    p = subprocess.run([php, '-l', os.path.join(THEME, 'functions.php')],
                       capture_output=True, text=True) if php else None
    chk('S2', 'php -l functions.php', p is not None and p.returncode == 0,
        (p.stdout or p.stderr).strip() if p else 'no php binary')

    # ---- S3 assets gone ----------------------------------------------------
    css_p, js_p = os.path.join(THEME, CSS_REL), os.path.join(THEME, JS_REL)
    missing = [r for r in (CSS_REL, JS_REL) if not os.path.exists(os.path.join(THEME, r))]
    css_dir = os.path.join(THEME, 'assets', 'css')
    refs = []
    for rel in theme_files():
        if rel.endswith(('.css', '.js', '.php', '.html', '.json')):
            body = read(os.path.join(THEME, rel))
            for needle in (CSS_REL, JS_REL):
                if needle in body:
                    refs.append('%s -> %s' % (rel, needle))
    chk('S3', 'both assets gone; no path reference left',
        len(missing) == 2 and not os.path.isdir(css_dir) and not refs,
        'gone=%d, assets/css dir=%s, refs=%s'
        % (len(missing), 'no' if not os.path.isdir(css_dir) else 'YES', refs[:3] or 'none'))

    # ---- S4 file count and identity ---------------------------------------
    now_list, base_list = theme_files(), base_files()
    gone = sorted(set(base_list) - set(now_list))
    added = sorted(set(now_list) - set(base_list))
    chk('S4', 'theme file set is base minus exactly the two assets',
        gone == sorted([CSS_REL, JS_REL]) and not added,
        '%d now vs %d at %s; gone=%s added=%s'
        % (len(now_list), len(base_list), BASE_COMMIT, gone or 'none', added or 'none'))

    # ---- S5 the :has ledger ------------------------------------------------
    total = 0
    per = []
    for rel in theme_files():
        if rel.endswith('.css'):
            n = read(os.path.join(THEME, rel)).count(':has(')
            total += n
            if n:
                per.append('%s=%d' % (rel, n))
    style_has = read(os.path.join(THEME, 'style.css')).count(':has(')
    chk('S5', ':has( occurrences total %d, style.css %d' % (EXPECT_HAS, EXPECT_HAS),
        total == EXPECT_HAS and style_has == EXPECT_HAS,
        'total=%d [%s]' % (total, ', '.join(per)))

    # ---- S6 comment rationale survives ------------------------------------
    refs = [n for n, ln in enumerate(func.split('\n'), 1) if 'configurator.js' in ln]
    chk('S6', 'configurator.js survives in exactly 5 comment lines',
        len(refs) == 5 and 'configurator.js' not in live,
        'lines %s; live refs=%d' % (refs, live.count('configurator.js')))

    # ---- S7 frozen contract + untouched siblings --------------------------
    drift = []
    for rel in FROZEN:
        b = blob(rel)
        g = open(os.path.join(THEME, rel), 'rb').read() if os.path.exists(os.path.join(THEME, rel)) else None
        if b is None or g is None or b != g:
            drift.append(rel)
    chk('S7', 'K1-K7 contract files byte-identical to %s' % BASE_COMMIT,
        not drift, 'drift=%s' % (drift or 'none'))

    # ---- S8 the migrated .sf-explore* block still lives in style.css -------
    heads = family_heads(read(os.path.join(THEME, 'style.css')))
    # ---- and the eight templates still carry the H2b1 author note ---------
    notes = [t for t in DOSE_TEMPLATES
             if H2B1_NOTE in read(os.path.join(THEME, 'templates', t))]
    chk('S8', 'style.css keeps .sf-explore*; 8 templates keep the H2b1 note',
        bool(heads) and len(notes) == 8,
        'heads=%d notes=%d/8' % (len(heads), len(notes)))

    # ---- S9 file-level diff is exactly the declared three -----------------
    ns = [l for l in git('diff', '--name-status', BASE_COMMIT, '--', 'sinofresh-theme/').splitlines()
          if l.strip()]
    want = {'M\tsinofresh-theme/functions.php',
            'D\tsinofresh-theme/%s' % CSS_REL,
            'D\tsinofresh-theme/%s' % JS_REL}
    chk('S9', 'git diff vs base is exactly the three declared files',
        set(ns) == want, 'got=%s' % (sorted(ns) or 'none'))

    res['ok'] = not res['errors']
    print('-' * 72)
    print('  VERDICT: %s' % ('PASS — all %d checks hold' % len(res['checks'])
                             if res['ok'] else 'FAIL — %d problem(s)' % len(res['errors'])))
    if args.json:
        json.dump(res, open(args.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    return 0 if res['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())

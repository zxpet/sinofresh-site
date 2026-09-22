#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H2b2 — negative controls for the static checks (S1-S9).

A green check proves nothing until you have watched it go red for the right
reason. Each control below therefore takes a faithful copy of the theme,
breaks exactly one property the checks claim to protect, and requires that at
least one check FAILS.

The controls are chosen to cover both directions of this batch:

  * the deletions actually happened  — restore an asset, revert functions.php
  * nothing else was touched         — add a stray file, strip the migrated
                                       .sf-explore* block out of style.css

plus two that exist because of their past failure modes:

  * a *faithful* copy must PASS (`faithful-copy-passes`). Without this one,
    every other control would still pass if the harness itself were broken —
    a checker that always returns "FAIL" catches everything and proves nothing.
  * a *missing* input must FAIL rather than skip (`functions-php-absent`).
    In H2a the missing-reference control in the main gate was the one that
    proved the other controls meant something, and the checks here read several
    files by path; a FileNotFoundError traceback would be a crash, not a
    verdict, so this also pins that the failure is a clean FAIL.

usage:
    python3 tools/b2d_h2b2_negctl.py [--json out.json]
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
THEME = os.path.join(ROOT, 'sinofresh-theme')
CHECKS = os.path.join(HERE, 'b2d_h2b2_checks.py')
PY = sys.executable
CSS_REL = os.path.join('assets', 'css', 'configurator.css')


def run_checks(theme):
    env = dict(os.environ, SF_THEME=theme)
    p = subprocess.run([PY, CHECKS], capture_output=True, text=True, env=env)
    failed = re.findall(r'^\s+(S\d+)\s+.*?FAIL', p.stdout, re.M)
    return p.returncode, failed, p.stdout + p.stderr


def mutate(name, dst):
    """Build the mutated copy at `dst`; return a one-line description."""
    if name == 'faithful-copy-passes':
        return 'no mutation (A/A control)'
    if name == 'asset-restored':
        src = subprocess.run(['git', '-C', ROOT, 'show',
                              'ebe8f50:sinofresh-theme/' + CSS_REL.replace(os.sep, '/')],
                             capture_output=True).stdout
        d = os.path.dirname(os.path.join(dst, CSS_REL))
        os.makedirs(d, exist_ok=True)
        open(os.path.join(dst, CSS_REL), 'wb').write(src)
        return 'configurator.css restored (%d B)' % len(src)
    if name == 'functions-php-reverted':
        src = subprocess.run(['git', '-C', ROOT, 'show', 'ebe8f50:sinofresh-theme/functions.php'],
                             capture_output=True).stdout
        open(os.path.join(dst, 'functions.php'), 'wb').write(src)
        return 'functions.php reverted to ebe8f50 (%d B)' % len(src)
    if name == 'stray-file-added':
        open(os.path.join(dst, 'assets', 'js', 'stray.js'), 'w').write('// stray\n')
        return 'one stray file added under assets/js/'
    if name == 'migrated-block-stripped':
        p = os.path.join(dst, 'style.css')
        s = open(p, encoding='utf-8').read()
        lines = s.split('\n')
        keep = [l for l in lines if '.sf-explore' not in l]
        open(p, 'w', encoding='utf-8').write('\n'.join(keep))
        return '.sf-explore* lines stripped from style.css (%d -> %d lines)'
        _ = keep
    if name == 'functions-php-absent':
        os.remove(os.path.join(dst, 'functions.php'))
        return 'functions.php removed entirely'
    raise SystemExit('unknown control %r' % name)


CONTROLS = ['faithful-copy-passes', 'asset-restored', 'functions-php-reverted',
            'stray-file-added', 'migrated-block-stripped', 'functions-php-absent']
# The first must pass; every other must fail.
MUST_PASS = {'faithful-copy-passes'}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--json')
    args = ap.parse_args(argv)

    rows, wrong = [], []
    print('=== H2b2 static-check negative controls ===')
    for name in CONTROLS:
        tmp = tempfile.mkdtemp(prefix='h2b2-neg-')
        try:
            dst = os.path.join(tmp, 'sinofresh-theme')
            shutil.copytree(THEME, dst,
                            ignore=shutil.ignore_patterns('_backup', '__pycache__',
                                                          '.DS_Store', '._*'))
            desc = mutate(name, dst)
            rc, failed, out = run_checks(dst)
            caught = rc != 0
            want_caught = name not in MUST_PASS
            # A catch has to be a *verdict*, not a crash: a control that trips
            # an exception also exits non-zero, and would otherwise be counted
            # as "caught" while proving nothing. Requiring at least one named
            # check is what makes `functions-php-absent` mean something.
            good = (caught and bool(failed)) if want_caught else (not caught)
            rows.append({'control': name, 'mutation': desc, 'rc': rc,
                         'failed_checks': failed, 'clean_verdict': bool(failed),
                         'as_required': good})
            print('  %-26s %-9s rc=%d  failed=%s' % (
                name, 'CAUGHT' if caught else 'passed', rc, ','.join(failed) or '-(no verdict)'))
            if not good:
                wrong.append(name)
                print('      !! expected %s, got %s%s' % (
                    'FAIL' if want_caught else 'PASS',
                    'FAIL' if caught else 'PASS',
                    ' with no named check' if caught and not failed else ''))
                print('      ' + '\n      '.join(out.strip().splitlines()[-6:]))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    print('-' * 72)
    print('  %d/%d controls behaved as required' % (len(CONTROLS) - len(wrong), len(CONTROLS)))
    if wrong:
        print('  WRONG: %s' % wrong)
    if args.json:
        json.dump({'controls': rows, 'wrong': wrong},
                  open(args.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    return 1 if wrong else 0


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H2b1 — reproduce the commit from its parent, byte for byte.

A batch's evidence normally has a hole in it: the patches ran before the first
snapshot of the "after" state, so if the first run of an assertion was wrong the
report on disk says FAILED about a file that is in fact correct. That happened
here (`_backup/b2d-h2b1-apply.json` carries `"ok": false` and one error line from
a `{{FORM_HREF}}` expectation that was simply wrong — 2 -> 1, not 2 -> 2).

Re-running the patchers against the parent revision closes the hole and also
proves something the original run could not: that the committed bytes are
exactly what the tooling produces, with no hand edit in between. The sandbox is
built with `git archive` from the base revision, so the working tree is never
touched; the eight pages and the detail template are the templates here, and
style.css / functions.php / configurator.css are the CSS migration.

usage:
    b2d_h2b1_repro.py [--base REV] [--out FILE]
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PY = sys.executable

TEMPLATES = ['page-soft-chews.html', 'page-tablets.html', 'page-powders.html',
             'page-pastes.html', 'page-drops.html', 'page-liquids.html',
             'page-fish-oil.html', 'page-dental-chews.html', 'single-sf_formula.html']
SOURCES = ['templates/' + t for t in TEMPLATES]
FILES = SOURCES + ['style.css', 'functions.php', 'assets/css/configurator.css']

PHP_CANDIDATES = [
    '/Users/meng/Library/Application Support/Local/lightning-services/php-8.2.29+0/bin/darwin-arm64/bin/php',
    '/usr/bin/php',
]


def sh(args, cwd=None, env=None):
    e = dict(os.environ)
    e.update(env or {})
    p = subprocess.run(args, cwd=cwd, capture_output=True, text=True, env=e)
    return p.returncode, (p.stdout or '').strip(), (p.stderr or '').strip()


def sha(path):
    with open(path, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', default='ebe8f50~1',
                    help='the revision the batch was built from')
    ap.add_argument('--out', default=os.path.join(ROOT, 'docs', 'batchH2b1-gates',
                                                  'step1-2-reproduction.json'))
    args = ap.parse_args()

    box = tempfile.mkdtemp(prefix='h2b1-repro-')
    rep = {'base': args.base, 'sandbox': box, 'files': [], 'patchers': [], 'ok': False}
    try:
        paths = ['sinofresh-theme/' + f for f in FILES]
        rc, out, err = sh(['git', 'archive', args.base] + paths, cwd=ROOT)
        if rc != 0:
            raise SystemExit('git archive failed: %s %s' % (out, err))
        tar = os.path.join(box, 'src.tar')
        with open(tar, 'wb') as fh:
            fh.write(subprocess.run(['git', 'archive', args.base] + paths, cwd=ROOT,
                                    capture_output=True).stdout)
        if sh(['tar', '-xf', tar, '-C', box])[0] != 0:
            raise SystemExit('tar failed')
        os.makedirs(os.path.join(box, 'tools'), exist_ok=True)
        os.makedirs(os.path.join(box, '_backup'), exist_ok=True)
        for t in ('b2d_h2b1_patch.py', 'b2d_h2b1_css.py'):
            shutil.copy(os.path.join(HERE, t), os.path.join(box, 'tools', t))
        shutil.copy(os.path.join(ROOT, '_backup', 'b2d-h2b-scan.json'),
                    os.path.join(box, '_backup', 'b2d-h2b-scan.json'))

        php = next((p for p in PHP_CANDIDATES if os.path.exists(p)), None)
        if php:
            # the CSS patcher shells out to `php -l`; it degrades to a notice when
            # php is absent, but a syntax check is worth having
            os.environ['PATH'] = os.path.dirname(php) + os.pathsep + os.environ.get('PATH', '')

        run_patch = os.path.join(box, 'tools', 'b2d_h2b1_patch.py')
        rep_apply = os.path.join(box, 'apply.json')
        rc, out, err = sh([PY, run_patch, '--apply', '--json', rep_apply], cwd=box)
        rep['patchers'].append({'tool': 'b2d_h2b1_patch.py --apply', 'rc': rc,
                                'stdout': out, 'stderr': err})
        with open(rep_apply, encoding='utf-8') as fh:
            ap_json = json.load(fh)
        rep['patch_ok'] = ap_json['ok']
        rep['patch_errors'] = ap_json['errors']
        rep['patch_deltas'] = [(p['page'], p['delta']) for p in ap_json['applied']]

        run_css = os.path.join(box, 'tools', 'b2d_h2b1_css.py')
        rc, out, err = sh([PY, run_css, '--apply'], cwd=box)
        rep['patchers'].append({'tool': 'b2d_h2b1_css.py --apply', 'rc': rc,
                                'stdout': out, 'stderr': err})

        same = 0
        for f in FILES:
            a = os.path.join(box, 'sinofresh-theme', f)
            b = os.path.join(ROOT, 'sinofresh-theme', f)
            ha, hb = (sha(a), sha(b)) if os.path.exists(a) and os.path.exists(b) else (None, None)
            ok = ha is not None and ha == hb
            same += 1 if ok else 0
            rep['files'].append({'file': f, 'sha256': ha, 'committed': hb, 'identical': ok})
        rep['identical'] = same
        rep['total'] = len(FILES)
        rep['ok'] = (same == len(FILES) and rep['patch_ok'] and not rep['patch_errors'])

        print('base %s' % args.base)
        print('patch_ok=%s errors=%s' % (rep['patch_ok'], rep['patch_errors']))
        for r in rep['patchers']:
            tail = [l for l in r['stdout'].split('\n') if 'APPLIED' in l or 'net' in l]
            print('%-32s rc=%s  %s' % (r['tool'], r['rc'], ' | '.join(tail)))
        for r in rep['files']:
            print('  %-8s %s' % ('SAME' if r['identical'] else 'DIFF', r['file']))
        print('%d/%d files reproduce the commit byte-for-byte' % (same, len(FILES)))
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        with open(args.out, 'w', encoding='utf-8') as fh:
            json.dump(rep, fh, ensure_ascii=False, indent=2)
        print('-> %s' % args.out)
        return 0 if rep['ok'] else 1
    finally:
        shutil.rmtree(box, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main())

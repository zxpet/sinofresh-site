#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H7e — orchestrator for the admin half of the browser pass.

The batch adds a settings page, and a settings page can only be checked where
it lives: in wp-admin, behind a login, with the preflight copy serving the
theme. That needs a user, and a user is a DB row, so the run is built the way
batch H2a built its admin pass — throwaway credentials, deleted afterwards, with
the user list compared before and after rather than assumed.

Sequence:
  1. read the user list                                    -> before
  2. create sf-e2e with a random password (never a fixed one)
  3. run tools/b2d_h7e_admin_e2e.js against the candidate (X-SF-Preflight: 1)
  4. delete sf-e2e
  5. read the user list again                              -> after
  6. assert before == after, the password file is gone, and mu-plugins/ holds
     exactly what it held — the probe that ran before this one installs a
     fixture there, and a fixture left behind is a filter left behind

Nothing here writes to the theme and nothing is saved from wp-admin: the E2E
reads the form and never submits it. The only DB writes are the two user rows
the throwaway account costs, and they are removed in step 4.
"""

import argparse
import json
import os
import secrets
import string
import subprocess
import sys

HOST = 'root@65.49.215.152'
PUB = '/var/www/dev.zxpet.com/public'
MU = PUB + '/wp-content/mu-plugins'
WP = ('cd /var/www/dev.zxpet.com/site-repo && wp --allow-root '
      '--path=' + PUB)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NODE = '/Users/meng/.workbuddy/binaries/node/versions/22.22.2-3/bin/node'
NODE_PATH = '/Users/meng/.workbuddy/binaries/node/workspace/node_modules'
JS = os.path.join(ROOT, 'tools', 'b2d_h7e_admin_e2e.js')
PASSFILE = '/tmp/sf-e2e-pass.txt'
LOGIN = 'sf-e2e'


def wp(args, timeout=180):
    return subprocess.run(['ssh', '-o', 'ConnectTimeout=25', HOST, WP + ' ' + args],
                          capture_output=True, text=True, timeout=timeout)


def user_list():
    r = wp('user list --field=user_login --format=csv')
    if r.returncode != 0:
        raise SystemExit('FATAL wp user list: %s' % (r.stderr or r.stdout)[:300])
    return [l.strip() for l in r.stdout.splitlines() if l.strip() and l.strip() != 'user_login']


def mu_list():
    r = subprocess.run(['ssh', '-o', 'ConnectTimeout=25', HOST,
                        'ls -1 %s 2>/dev/null | sort' % MU], capture_output=True, text=True)
    return [l.strip() for l in r.stdout.splitlines() if l.strip()]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--json')
    args = ap.parse_args(argv)

    rows = []

    def ok(label, cond, detail=''):
        rows.append({'label': label, 'ok': bool(cond), 'detail': str(detail)})
        print('  %s  %-58s %s' % ('ok  ' if cond else 'FAIL', label, detail))
        return bool(cond)

    print('== H7e admin E2E ==')

    before = user_list()
    mu_before = mu_list()
    ok('the user list is readable', len(before) > 0, '%d user(s)' % len(before))
    ok('no throwaway admin is left over from an earlier run',
       LOGIN not in before, 'login=%s' % LOGIN)
    if LOGIN in before:
        print('  removing the stale one first')
        wp('user delete %s --yes --reassign=1' % LOGIN)
        before = user_list()

    alphabet = string.ascii_letters + string.digits
    pw = ''.join(secrets.choice(alphabet) for _ in range(24))
    r = wp("user create %s %s@example.com --role=administrator --user_pass='%s' --porcelain"
           % (LOGIN, LOGIN, pw))
    uid = (r.stdout or '').strip().splitlines()[-1].strip() if r.returncode == 0 else ''
    ok('the throwaway admin was created', uid.isdigit(), 'id=%s' % (uid or (r.stderr or '')[:120]))
    if not uid.isdigit():
        return 2

    open(PASSFILE, 'w', encoding='utf-8').write(pw + '\n')
    ok('its password was written to the file the E2E reads',
       os.path.exists(PASSFILE), PASSFILE)

    env = dict(os.environ, NODE_PATH=NODE_PATH)
    p = subprocess.run([NODE, JS], capture_output=True, text=True, env=env, timeout=600)
    tail = (p.stdout or '').strip().splitlines()
    for line in tail[-40:]:
        print('    ' + line)
    if p.stderr.strip():
        print('    stderr: ' + p.stderr.strip()[:400])
    ok('the admin E2E passes against the candidate', p.returncode == 0,
       'exit=%d' % p.returncode)

    r = wp('user delete %s --yes --reassign=1' % uid)
    ok('the throwaway admin was deleted', r.returncode == 0,
       (r.stdout + r.stderr).strip()[:120])

    # The password file lives HERE — on the machine that generated the password
    # and the only machine the browser reads it from — so it has to be removed
    # HERE, and the check has to look at the same path it wrote. The first
    # version of this orchestrator wrote it locally, removed it over ssh, and
    # then read the LOCAL path: the one cleanup step that actually matters, the
    # only place the throwaway password exists, was reported as failed while the
    # file sat on disk, and the remote delete was a no-op against a path that
    # never existed there. Both halves are now separate claims.
    try:
        os.remove(PASSFILE)
    except FileNotFoundError:
        pass
    ok('the password file is gone from this machine', not os.path.exists(PASSFILE), PASSFILE)
    r = subprocess.run(['ssh', '-o', 'ConnectTimeout=20', HOST,
                        'test -e %s && echo PRESENT || echo GONE' % PASSFILE],
                       capture_output=True, text=True)
    ok('...and no copy was left on the dev box either', 'GONE' in r.stdout, '')

    after = user_list()
    ok('the user list is exactly what it was (zero DB trace)',
       before == after, 'before=%d after=%d' % (len(before), len(after)))

    mu_after = mu_list()
    ok('mu-plugins/ holds exactly what it held (no fixture left behind)',
       mu_before == mu_after, '%s' % mu_after)
    ok('...and the H7e probe fixture is not among them',
       not any('h7e' in f for f in mu_after), '')

    passed = all(r['ok'] for r in rows)
    print('\n%s  H7e admin E2E' % ('PASS' if passed else 'FAIL'))
    if args.json:
        json.dump({'ok': passed, 'rows': rows}, open(args.json, 'w'), indent=1)
        print('  json -> %s' % args.json)
    return 0 if passed else 1


if __name__ == '__main__':
    sys.exit(main())

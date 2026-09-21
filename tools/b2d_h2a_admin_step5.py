#!/usr/bin/env python3
"""Batch H2a Step 5 — orchestrator for the candidate admin E2E + zero trace.

Sequence:
  1. close every browser session (the H1 immutable-cache rule)
  2. snapshot the DB (tools/b2d_h2a_dbprobe.php)          -> db-before.json
  3. create the throwaway admin (sf-e2e, random password)
  4. run tools/b2d_h2a_admin_e2e.js against the candidate (X-SF-Preflight: 1)
  5. delete the throwaway admin + every _edit_lock/_edit_last on sf_formula
  6. snapshot the DB again                                -> db-after.json
  7. diff: content half byte-identical, edit half zero, census 105/105
  8. re-run the batch-H1a verifier (wp eval-file b2d_h_migrate.php verify)

Nothing here writes to the theme; the only DB writes are the ones the real
admin save makes, and they are removed again in step 5.
"""

import hashlib
import json
import os
import secrets
import shlex
import string
import subprocess
import sys

HOST = 'root@65.49.215.152'
# the repo root and the docroot are *siblings* on the server: tools/ lives in
# site-repo, WordPress lives in public. wp-cli needs the docroot for --path but
# the repo root as CWD, or eval-file cannot see tools/.
WP = ("cd /var/www/dev.zxpet.com/site-repo && wp --allow-root "
      "--path=/var/www/dev.zxpet.com/public")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, 'tools')
BASE = os.path.join(ROOT, '_backup', 'b2d-h2a-baselines')
NODE = '/Users/meng/.workbuddy/binaries/node/versions/22.22.2-3/bin/node'
NODE_PATH = '/Users/meng/.workbuddy/binaries/node/workspace/node_modules'
PASSFILE = '/tmp/sf-e2e-pass.txt'
PLAN = os.path.join(ROOT, '_backup', 'b2d-h-migrate', 'plan.json')

LOGIN = 'sf-e2e'
ROUND = os.environ.get('SF_ROUND', 'r1')


def sh(cmd, **kw):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, **kw)


def remote(cmd, **kw):
    return sh('ssh %s %s' % (HOST, json.dumps(cmd)), **kw)


def wp(cmd, **kw):
    return remote(WP + ' ' + cmd, **kw)


def step(n, msg):
    print('\n=== [%s] %s' % (n, msg))


def ok(label, cond, extra=''):
    print(('PASS ' if cond else 'FAIL ') + label + (('  ' + extra) if extra else ''))
    return bool(cond)


def snapshot(tag):
    r = wp('eval-file /root/b2d_h2a_dbprobe.php')
    if r.returncode != 0:
        print('probe failed:', r.stderr[:400])
        sys.exit(2)
    raw = r.stdout.strip().splitlines()[-1]
    path = os.path.join(BASE, 'db-%s.json' % tag)
    open(path, 'w', encoding='utf-8').write(raw + '\n')
    return json.loads(raw), path


def main():
    results = []

    step(0, 'close every browser session')
    r = sh('agent-browser close --all')
    print('  ', (r.stdout or r.stderr).strip()[:120])

    step(1, 'upload probes')
    # NB: never json.dumps() a LOCAL path — it escapes non-ASCII (\u5916) and
    # scp then looks for a literal backslash-u directory. shlex.quote only.
    for local, dest in ((os.path.join(TOOLS, 'b2d_h2a_dbprobe.php'), '/root/b2d_h2a_dbprobe.php'),
                        (PLAN, '/tmp/sf-h1-plan.json')):
        r = sh('scp -q %s %s:%s' % (shlex.quote(local), HOST, shlex.quote(dest)))
        if r.returncode != 0:
            print('scp failed for', local, r.stderr[:300]); sys.exit(2)
    print('   uploaded dbprobe + the H1a plan')

    step(2, 'DB snapshot BEFORE')
    before, before_path = snapshot(ROUND + '-before')
    print('   meta rows=%d  edit rows=%d  census=%d  users=%s'
          % (before['meta_rows'], len(before['edit_rows']), before['census_105'], before['users']))
    print('   meta_sha', before['meta_sha'], '->', before_path)

    step(3, 'create the throwaway admin')
    alphabet = string.ascii_letters + string.digits
    pw = ''.join(secrets.choice(alphabet) for _ in range(24))
    r = wp("user create %s %s@example.com --role=administrator --user_pass='%s' --porcelain"
           % (LOGIN, LOGIN, pw))
    if r.returncode != 0:
        print('user create failed:', r.stderr[:400]); sys.exit(2)
    uid = r.stdout.strip().splitlines()[-1].strip()
    open(PASSFILE, 'w', encoding='utf-8').write(pw + '\n')
    print('   created %s (id=%s), password in %s' % (LOGIN, uid, PASSFILE))
    results.append(ok('throwaway admin created', uid.isdigit(), 'id=' + uid))

    step(4, 'run the candidate admin E2E')
    env = dict(os.environ, NODE_PATH=NODE_PATH)
    r = subprocess.run([NODE, os.path.join(TOOLS, 'b2d_h2a_admin_e2e.js')],
                       capture_output=True, text=True, env=env, cwd=ROOT)
    print(r.stdout)
    if r.stderr.strip():
        print('STDERR', r.stderr[:800])
    e2e_ok = r.returncode == 0
    open(os.path.join(BASE, 'admin-e2e-candidate-%s.txt' % ROUND), 'w', encoding='utf-8').write(r.stdout)
    results.append(ok('admin E2E on the candidate', e2e_ok, 'exit=%d' % r.returncode))

    step(5, 'delete the throwaway admin + every _edit_* on sf_formula')
    r = wp('user delete %s --yes --reassign=1' % uid)
    print('   ', (r.stdout + r.stderr).strip()[:200])
    clean = r'''<?php
$ids = get_posts(array('post_type'=>'sf_formula','post_status'=>'any','numberposts'=>-1,'fields'=>'ids'));
$n = 0;
foreach ($ids as $id) {
    foreach (array('_edit_lock','_edit_last') as $k) {
        if (get_post_meta($id, $k, true) !== '') { delete_post_meta($id, $k); $n++; }
    }
}
echo "removed {$n} edit rows across " . count($ids) . " formulas\n";
'''
    open('/tmp/sf_h2a_clean.php', 'w', encoding='utf-8').write(clean)
    sh('scp -q /tmp/sf_h2a_clean.php %s:/root/sf_h2a_clean.php' % HOST)
    r = wp('eval-file /root/sf_h2a_clean.php')
    print('   ', (r.stdout + r.stderr).strip()[:200])

    step(6, 'DB snapshot AFTER')
    after, after_path = snapshot(ROUND + '-after')
    print('   meta rows=%d  edit rows=%d  census=%d  users=%s'
          % (after['meta_rows'], len(after['edit_rows']), after['census_105'], after['users']))
    print('   meta_sha', after['meta_sha'], '->', after_path)

    step(7, 'diff')
    results.append(ok('content meta rows byte-identical (sha + count)',
                      before['meta_sha'] == after['meta_sha'] and before['meta_rows'] == after['meta_rows'],
                      '%d -> %d, sha %s' % (before['meta_rows'], after['meta_rows'], after['meta_sha'][:12])))
    results.append(ok('_edit_lock/_edit_last rows now zero',
                      len(after['edit_rows']) == 0, 'was %d' % len(before['edit_rows'])))
    results.append(ok('census 105/105 still holds', after['census_105'] == 105, str(after['census_105'])))
    results.append(ok('census bytes identical', before['census_blob_sha'] == after['census_blob_sha']))
    results.append(ok('only the admin account remains', after['users'] == ['1:admin'], str(after['users'])))
    results.append(ok('formula posts unchanged (21)',
                      before['formula_ids'] == after['formula_ids'] and len(after['formula_ids']) == 21))
    same_row = before['post158'] == after['post158']
    results.append(ok('post 158 row identical apart from post_modified', same_row,
                      'modified %s -> %s' % (before['post158_modified'][:19], after['post158_modified'][:19])))
    if not same_row:
        diff = {k: (before['post158'][k], after['post158'][k])
                for k in before['post158'] if before['post158'][k] != after['post158'].get(k)}
        print('   differing columns:', json.dumps(diff))
    for key, label in (('options', 'admin option values unchanged (certs/containers/global-faq)'),
                       ('terms', 'term + relationship counts unchanged'),
                       ('nontransient_rows', 'wp_options non-transient row count unchanged'),
                       ('nontransient_sha', 'wp_options non-transient values byte-identical')):
        b, a = before.get(key), after.get(key)
        shown = (str(b)[:16] + '...') if key.endswith('_sha') else json.dumps(b, sort_keys=True)
        shown_a = (str(a)[:16] + '...') if key.endswith('_sha') else json.dumps(a, sort_keys=True)
        results.append(ok(label, b == a, '%s -> %s' % (shown, shown_a)))
        if b != a:
            print('   ', key, 'DIFF', json.dumps({'before': b, 'after': a}, sort_keys=True))
    print('   INFO wp_options total rows/max_id: %s -> %s (transients are recreated by core/plugins/cron)'
          % (json.dumps(before['option_totals'], sort_keys=True), json.dumps(after['option_totals'], sort_keys=True)))
    print('   INFO transient rows: %s -> %s' % (before.get('transient_rows'), after.get('transient_rows')))

    step(8, 're-run the batch-H1a verifier')
    r = wp('eval-file tools/b2d_h_migrate.php verify /tmp/sf-h1-plan.json')
    out = (r.stdout + r.stderr).strip()
    print('   ', out[:600])
    try:
        rep = json.loads(out[out.index('{'):]) if '{' in out else {}
    except Exception:
        rep = {}
    results.append(ok('H1a verifier: 105/105, zero fails',
                      rep.get('key_census') == 105 and rep.get('fails') == [] and rep.get('pass') is True,
                      'census=%s fails=%s' % (rep.get('key_census'), rep.get('fails'))))

    step(9, 'summary')
    print('   %d/%d checks passed' % (sum(results), len(results)))
    bad = len(results) - sum(results)
    print('   RESULT:', 'ALL PASS' if bad == 0 else '%d FAIL' % bad)
    return 1 if (bad or not e2e_ok) else 0


if __name__ == '__main__':
    sys.exit(main())

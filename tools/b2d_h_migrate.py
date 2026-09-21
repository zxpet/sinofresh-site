#!/usr/bin/env python3
"""Batch H1 Step 3 — migration orchestrator (local side).

Backup → dump → dry-run → (STOP for user review) → apply → verify.

  python3 tools/b2d_h_migrate.py backup    # mysqldump-style export + row counts
  python3 tools/b2d_h_migrate.py dry-run   # plan.json + human-readable value table
  python3 tools/b2d_h_migrate.py apply     # uploads reviewed plan, applies, verifies
  python3 tools/b2d_h_migrate.py verify    # re-run SQL assertions only
  python3 tools/b2d_h_migrate.py rollback  # restore prestate.json (dangerous, ask user)

Everything that touches the DB runs on the dev server through ssh; the JSON
the PHP script prints on stdout is saved under _backup/b2d-h-migrate/.
"""

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, '_backup', 'b2d-h-migrate')
HOST = 'root@65.49.215.152'
WP_DIR = '/var/www/dev.zxpet.com/public'
REMOTE_PHP = '/tmp/b2d_h_migrate.php'
PF_HEADER = ('X-SF-Preflight: 1')  # not used by CLI; documented intent only

FORMULA_IDS = list(range(158, 179))  # 21 records, verified 2026-09-21


def ssh(cmd, capture=True, input_bytes=None):
    return subprocess.run(['ssh', HOST, cmd], capture_output=capture, input=input_bytes)


def run_php(*args):
    """Run the migrate PHP on the server; returns (rc, stdout, stderr)."""
    quoted = ' '.join("'%s'" % a.replace("'", "'\\''") for a in args)
    cmd = "cd %s && wp eval-file %s %s" % (WP_DIR, REMOTE_PHP, quoted)
    r = ssh(cmd)
    return r.returncode, r.stdout.decode(), r.stderr.decode()


def ensure_remote_script():
    with open(os.path.join(ROOT, 'tools', 'b2d_h_migrate.php'), 'rb') as f:
        data = f.read()
    r = subprocess.run(['scp', '-q', os.path.join(ROOT, 'tools', 'b2d_h_migrate.php'),
                        '%s:%s' % (HOST, REMOTE_PHP)], capture_output=True)
    if r.returncode != 0:
        sys.exit('scp failed: %s' % r.stderr.decode())
    return len(data)


def osql(sql):
    """Run a read-only SQL via wp db query and return stdout."""
    r = ssh("cd %s && wp db query \"%s\" --skip-column-names" % (WP_DIR, sql.replace('"', '\\"')))
    return r.stdout.decode().strip()


def meta_row_count():
    ids = ','.join(str(i) for i in FORMULA_IDS)
    return int(osql("SELECT COUNT(*) FROM wp_postmeta WHERE post_id IN (%s)" % ids))


def cmd_backup():
    os.makedirs(OUT, exist_ok=True)
    before = meta_row_count()
    # wp db export: full-table dump of everything the migration can touch.
    remote_sql = '/tmp/b2d-h-pre-migrate.sql'
    r = ssh("cd %s && wp db export %s --tables=wp_postmeta --add-drop-table && gzip -f %s && wc -c %s.gz"
            % (WP_DIR, remote_sql, remote_sql, remote_sql))
    if r.returncode != 0:
        sys.exit('db export failed: %s %s' % (r.stdout.decode(), r.stderr.decode()))
    subprocess.run(['scp', '-q', '%s:%s.gz' % (HOST, remote_sql),
                    os.path.join(OUT, 'pre-migrate-postmeta.sql.gz')], check=True)
    # Structured pre-state (what rollback restores).
    rc, out, err = run_php('dump')
    if rc != 0:
        sys.exit('dump failed: %s' % err)
    open(os.path.join(OUT, 'prestate-dump.json'), 'wb').write(out.encode())
    print('backup: wp_postmeta rows for the 21 records BEFORE = %d' % before)
    print('backup: pre-migrate-postmeta.sql.gz + prestate-dump.json saved to %s' % OUT)
    return before


def cmd_dry_run():
    os.makedirs(OUT, exist_ok=True)
    rc, out, err = run_php('dry-run')
    if rc != 0:
        sys.exit('dry-run failed: %s' % err)
    plan_path = os.path.join(OUT, 'plan.json')
    open(plan_path, 'wb').write(out.encode())
    plan = json.loads(out)
    print('dry-run: plan.json saved (%d records) — no data written' % len(plan['records']))
    return plan


def value_table(plan):
    """Human-readable 21-row table for user review."""
    lines = []
    for rec in plan['records']:
        w = rec['writes']
        faq = json.loads(w['sf_formula_faq_data'])
        answered = sum(1 for r in faq if r['a'])
        lines.append(
            '%d | %-32s | %-13s | shelf=%-12s | lead=%s | faq=%d rows(%d answered) | src=%s | intro=%s'
            % (rec['id'], rec['title'][:32], rec['form'],
               w['sf_formula_shelf_life'] or '(empty)',
               w['sf_formula_lead_time'][:24],
               len(faq), answered,
               ('+%d chars annotation' % len(w['sf_formula_source'])) if '[H1 migration' in w['sf_formula_source'] else 'MISSING',
               w['sf_formula_intro'][:40] + '…'))
    return lines


def cmd_apply():
    plan_path = os.path.join(OUT, 'plan.json')
    if not os.path.exists(plan_path):
        sys.exit('apply: no plan.json — run dry-run first')
    prestate_local = os.path.join(OUT, 'sf-h1-prestate.json')
    before = meta_row_count()
    # Upload the reviewed plan; apply byte-compares its recomputation to it.
    subprocess.run(['scp', '-q', plan_path, '%s:/tmp/sf-h1-plan.json' % HOST], check=True)
    rc, out, err = run_php('apply', '/tmp/sf-h1-plan.json')
    if rc != 0:
        sys.exit('apply failed rc=%d: %s' % (rc, err))
    for line in err.strip().splitlines():
        print('server:', line)
    subprocess.run(['scp', '-q', '%s:/tmp/sf-h1-prestate.json' % HOST, prestate_local], check=False)
    after = meta_row_count()
    print('apply: wp_postmeta rows for the 21 records %d -> %d (expect +%d new keys)'
          % (before, after, 5 * len(FORMULA_IDS)))
    return cmd_verify()


def cmd_verify():
    rc, out, err = run_php('verify', '/tmp/sf-h1-plan.json')
    if rc != 0 and not out.strip():
        sys.exit('verify failed: %s' % err)
    report = json.loads(out)
    open(os.path.join(OUT, 'verify-report.json'), 'w').write(json.dumps(report, indent=2))
    print('verify: %d writes checked, key census %d, fails %d'
          % (report['checked_writes'], report['key_census'], len(report['fails'])))
    for f in report['fails']:
        print('  FAIL:', f)
    return 0 if report['pass'] else 1


def cmd_rollback():
    prestate = os.path.join(OUT, 'sf-h1-prestate.json')
    if not os.path.exists(prestate):
        sys.exit('rollback: local sf-h1-prestate.json missing')
    subprocess.run(['scp', '-q', prestate, '%s:/tmp/sf-h1-prestate.json' % HOST], check=True)
    rc, out, err = run_php('rollback', '/tmp/sf-h1-prestate.json')
    print(err.strip())
    if rc != 0:
        sys.exit('rollback failed')
    after = meta_row_count()
    print('rollback done; wp_postmeta rows now %d' % after)


if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] not in ('backup', 'dry-run', 'apply', 'verify', 'rollback'):
        sys.exit(__doc__)
    n = ensure_remote_script()
    {'backup': cmd_backup, 'dry-run': cmd_dry_run, 'apply': cmd_apply,
     'verify': cmd_verify, 'rollback': cmd_rollback}[sys.argv[1]]()

#!/usr/bin/env python3
"""Batch H2a Step 5 — ambient-churn control.

The zero-trace diff uses MAX(option_id) — which walks forward whenever WordPress
core, Gravity Forms or WP cron deletes and recreates a transient, i.e. on a
completely idle site too. This control takes two snapshots N seconds apart with
NO admin activity in between, so the report can state how much of that drift is
ambient rather than ours.

usage: python3 tools/b2d_h2a_ambient_control.py [seconds]
"""

import json
import os
import subprocess
import sys
import time

HOST = 'root@65.49.215.152'
WP = ("cd /var/www/dev.zxpet.com/site-repo && wp --allow-root "
      "--path=/var/www/dev.zxpet.com/public")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(ROOT, '_backup', 'b2d-h2a-baselines')


def probe():
    r = subprocess.run('ssh %s %s' % (HOST, json.dumps(WP + ' eval-file /root/b2d_h2a_dbprobe.php')),
                       shell=True, capture_output=True, text=True)
    return json.loads(r.stdout.strip().splitlines()[-1])


def main():
    gap = int(sys.argv[1]) if len(sys.argv) > 1 else 150
    a = probe()
    print('T0  options rows=%s max_id=%s transients=%s  non-transient=%s'
          % (a['option_totals']['rows'], a['option_totals']['max_id'],
             a.get('transient_rows'), a.get('nontransient_rows')))
    print('    waiting %ds with no admin activity...' % gap)
    time.sleep(gap)
    b = probe()
    print('T1  options rows=%s max_id=%s transients=%s  non-transient=%s'
          % (b['option_totals']['rows'], b['option_totals']['max_id'],
             b.get('transient_rows'), b.get('nontransient_rows')))
    moved = a['option_totals']['max_id'] != b['option_totals']['max_id']
    same_nt = (a.get('nontransient_rows') == b.get('nontransient_rows')
               and a.get('nontransient_sha') == b.get('nontransient_sha'))
    print('CONTROL max option_id moved on an idle site : %s (%s -> %s)'
          % (moved, a['option_totals']['max_id'], b['option_totals']['max_id']))
    print('CONTROL non-transient options byte-identical: %s' % same_nt)
    json.dump({'t0': a['option_totals'], 't1': b['option_totals'],
               'transients': [a.get('transient_rows'), b.get('transient_rows')],
               'nontransient_sha': [a.get('nontransient_sha'), b.get('nontransient_sha')]},
              open(os.path.join(BASE, 'ambient-control.json'), 'w'), indent=2)
    return 0


if __name__ == '__main__':
    sys.exit(main())

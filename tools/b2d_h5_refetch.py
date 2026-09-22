#!/usr/bin/env python3
"""Finish an incomplete capture: refetch only the pages that are not 200+</html>.

Serial retries were the bottleneck (a hung request held up every later page), so
this runs a small pool and short timeouts, and only widens the timeout after the
pool has been given several chances. The manifest is rewritten after every round
so a kill leaves a truthful record.
"""
import argparse
import hashlib
import os
import subprocess
import sys
import time

AUTH = os.environ.get('SF_DEV_AUTH') or 'sfdev:VkEws18Kl5V1qp3TpZ6s'
HOST = 'https://dev.zxpet.com'
FLOOR = 2000


def slug(p):
    s = p.strip('/').replace('/', '__')
    return s or 'root'


def load(out):
    rows = {}
    with open(os.path.join(out, 'MANIFEST.tsv'), encoding='utf-8') as fh:
        for ln in fh:
            if ln.startswith('#') or ln.startswith('path\t'):
                continue
            q = ln.rstrip('\n').split('\t')
            if len(q) >= 4:
                rows[q[0]] = [q[1], int(q[2]), q[3]]
    return rows


def save(out, rows):
    with open(os.path.join(out, 'MANIFEST.tsv'), 'w', encoding='utf-8') as fh:
        fh.write('# header: X-SF-Preflight: 1\n')
        fh.write('path\tcode\tbytes\tsha256\n')
        for p in sorted(rows):
            fh.write('%s\t%s\t%d\t%s\n' % (p, rows[p][0], rows[p][1], rows[p][2]))


def complete(out, p):
    f = os.path.join(out, slug(p) + '.html')
    if not os.path.exists(f):
        return False
    b = open(f, 'rb').read()
    return len(b) >= FLOOR and '</html>' in b[-4000:].decode('utf-8', 'replace')


def fetch(out, p, timeout):
    dest = os.path.join(out, slug(p) + '.html')
    r = subprocess.run(['curl', '-s', '--max-time', str(timeout),
                        '-H', 'X-SF-Preflight: 1', '-u', AUTH,
                        '-o', dest, '-w', '%{http_code}', HOST + p],
                       capture_output=True, text=True)
    code = (r.stdout or '').strip() or '000'
    b = open(dest, 'rb').read() if os.path.exists(dest) else b''
    return [code, len(b), hashlib.sha256(b).hexdigest()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--rounds', type=int, default=12)
    ap.add_argument('--sleep', type=float, default=2.0,
                    help='pause between requests inside a round')
    ap.add_argument('--cooldown', type=float, default=20.0,
                    help='pause between rounds; the origin returns 502 when hammered')
    args = ap.parse_args()
    out = args.out
    rows = load(out)
    for rnd in range(args.rounds):
        bad = [p for p in rows if rows[p][0] != '200' or not complete(out, p)]
        if not bad:
            print('%s: round %d — all %d pages complete (200 + </html>)'
                  % (out, rnd, len(rows)), flush=True)
            save(out, rows)
            return 0
        # The first rounds are deliberately single-threaded: the failures here
        # are 502s from a saturated origin, and more concurrency makes them
        # worse rather than better.
        timeout = 60 if rnd < 6 else 120
        print('%s: round %d — %d to fix (timeout %ds, serial, %ds gap)'
              % (out, rnd, len(bad), timeout, args.sleep), flush=True)
        for p in bad:
            try:
                rows[p] = fetch(out, p, timeout)
            except Exception as exc:                          # noqa: BLE001
                print('    ERROR %-50s %s' % (p, exc), flush=True)
                continue
            print('    %-4s %-50s %7d %s'
                  % (rows[p][0], p, rows[p][1],
                     'complete' if complete(out, p) else 'INCOMPLETE'), flush=True)
            time.sleep(args.sleep)
        save(out, rows)
        if rnd + 1 < args.rounds:
            time.sleep(args.cooldown)
    bad = [p for p in rows if rows[p][0] != '200' or not complete(out, p)]
    print('%s: GAVE UP — %d still incomplete' % (out, len(bad)), flush=True)
    for p in bad:
        print('   FAILED', p, flush=True)
    return 1


if __name__ == '__main__':
    sys.exit(main())

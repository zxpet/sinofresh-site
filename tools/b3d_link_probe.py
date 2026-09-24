#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch 3d -- resolve the internal link targets the crawl did not cover.

The survey found 958 internal hrefs pointing at routes no published object owns.
All 958 collapse to 33 distinct targets, and "not in the crawl" is not the same
as "broken": WordPress answers the un-prefixed dosage routes with a 301 to the
/products/ path. The distinction only shows up in the response, so each distinct
target is fetched once, read-only, and classified by status.

HEAD first; a server that refuses HEAD falls back to a ranged GET, because a
405 would otherwise be misfiled as a dead link.
"""
import base64
import json
import os
import re
import subprocess
import time

USER, PASS = 'sfdev', 'VkEws18Kl5V1qp3TpZ6s'
BASE = 'https://dev.zxpet.com'
SLEEP = 1.3
OUT = os.path.join('docs', 'site-survey-2026-09-24', 'link-probe.json')


def probe(path):
    url = path if path.startswith('http') else BASE + path
    for method in (['-I'], ['-r', '0-0']):
        p = subprocess.run(['curl', '-sS', '--max-time', '40', '-u',
                            '%s:%s' % (USER, PASS)] + method +
                           ['-o', '/dev/null', '-w',
                            '%{http_code}\\t%{redirect_url}\\t%{size_download}\\t%{content_type}',
                            url], capture_output=True, text=True)
        if p.returncode != 0:
            return {'url': path, 'err': p.stderr.strip()[:120]}
        code, redir, size, ctype = (p.stdout.split('\t') + [''] * 4)[:4]
        if code != '405':
            return {'url': path, 'method': 'HEAD' if method == ['-I'] else 'GET-range',
                    'status': int(code), 'redirect': redir, 'size': int(size or 0),
                    'ctype': ctype}
    return {'url': path, 'status': 405}


def main():
    f = json.load(open(os.path.join(os.path.dirname(OUT), 'findings.json'),
                       encoding='utf-8'))
    seen, targets = set(), []
    for h in f['findings']['links']:
        t = h['detail']
        if t not in seen:
            seen.add(t)
            targets.append(t)
    print('probing %d distinct targets\n' % len(targets))
    rows = []
    for t in targets:
        r = probe(t)
        rows.append(r)
        flag = {'200': 'ok  ', '301': '301 ',
                '302': '302 ', '404': 'DEAD', '403': '403 ', '410': 'GONE'}.get(
            str(r.get('status')), '??  ')
        print('%s %-52s %s %s' % (flag, t, r.get('status'),
                                  (r.get('redirect') or '')[:60]))
        time.sleep(SLEEP)
    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(rows, fh, ensure_ascii=False, indent=1)
    dead = [r for r in rows if r.get('status') in (404, 410) or r.get('err')]
    redir = [r for r in rows if r.get('status') in (301, 302)]
    print('\n=== %d probed: %d dead, %d redirecting, %d direct 200 ===' %
          (len(rows), len(dead), len(redir), len(rows) - len(dead) - len(redir)))
    for r in dead:
        print('  DEAD %s  %s' % (r['url'], r.get('err') or r.get('status')))
    print('-> %s' % OUT)


if __name__ == '__main__':
    main()

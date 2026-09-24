#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch 3d -- read-only security probes against the dev host.

GET/HEAD only. No login, no form submission, no POST, nothing that writes. Each
target is one request, spaced by SLEEP.

Every target carries an expectation, and the expectation is what makes the run
readable: "404 expected" and "404 found" is a pass, but the same 404 without a
stated expectation is indistinguishable from a typo in the URL.
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
OUT = os.path.join('docs', 'site-survey-2026-09-24', 'security-probe.json')

# (path, expected status class, why it matters)
TARGETS = [
    ('/', ['200'], 'baseline'),
    ('/wp-login.php', ['200', '302'], 'login page must exist and must not leak'),
    ('/wp-admin/', ['302', '200'], 'admin entry redirects to login when logged out'),
    ('/xmlrpc.php', ['403', '404', '405'], 'XML-RPC is a brute-force amplifier'),
    ('/wp-json/wp/v2/users', ['401', '403', '404'],
     'user enumeration -- the theme blocks this for logged-out requests'),
    ('/wp-json/wp/v2/users/1', ['401', '403', '404'], 'single-user enumeration'),
    ('/?author=1', ['301', '302', '404'], 'author archive is the classic enumeration'),
    ('/wp-json/sinofresh/v1/', ['404', '200'], 'our own namespace index'),
    ('/readme.html', ['403', '404'], 'version disclosure'),
    ('/license.txt', ['403', '404'], 'version disclosure'),
    ('/wp-config.php', ['403', '404'], 'must never be served'),
    ('/wp-config.php.bak', ['403', '404'], 'must never be served'),
    ('/wp-config.php~', ['403', '404'], 'editor backup must never be served'),
    ('/.env', ['403', '404'], 'must never be served'),
    ('/.git/config', ['403', '404'], 'repository must not be web-reachable'),
    ('/.git/HEAD', ['403', '404'], 'repository must not be web-reachable'),
    ('/wp-content/debug.log', ['403', '404'], 'log leakage'),
    ('/wp-content/uploads/', ['403', '404'], 'directory listing'),
    ('/wp-includes/', ['403', '404'], 'directory listing'),
    ('/wp-content/plugins/', ['403', '404'], 'directory listing'),
    ('/wp-content/vendor/autoload.php', ['403', '404'],
     'composer vendor tree -- the config-pdf endpoint depends on it existing'),
    ('/wp-content/vendor/', ['403', '404'], 'directory listing over vendor'),
    ('/wp-content/themes/sinofresh-theme/README.md', ['403', '404'], 'dev notes in the docroot'),
    ('/wp-content/themes/sinofresh-theme/docs/', ['403', '404'], 'docs in the docroot'),
    ('/wp-content/themes/sinofresh-theme/_backup/', ['403', '404'],
     'the pre-change rollback archive must not be reachable'),
    ('/wp-content/themes/sinofresh-theme/tools/', ['403', '404'],
     'dev scaffolding must not be reachable'),
    ('/wp-json/', ['200'], 'REST index -- lists every namespace'),
    ('/wp-cron.php', ['200', '403', '404'], 'cron endpoint'),
    ('/feed/', ['200'], 'feed exists'),
    ('/?s=%3Cscript%3Ealert(1)%3C/script%3E', ['200'],
     'search reflection -- the payload must come back escaped'),
]

HEADERS_OF_INTEREST = ['strict-transport-security', 'content-security-policy',
                       'x-frame-options', 'x-content-type-options', 'referrer-policy',
                       'permissions-policy', 'x-xss-protection', 'server',
                       'x-powered-by', 'x-robots-tag', 'content-type',
                       'access-control-allow-origin', 'set-cookie']


def get(path, want_body=False):
    url = BASE + path
    args = ['curl', '-sS', '--max-time', '45', '-u', '%s:%s' % (USER, PASS),
            '-D', '/tmp/b3d_hdr.txt', '-o', '/tmp/b3d_body.txt',
            '-w', '%{http_code}\\t%{size_download}\\t%{redirect_url}', url]
    p = subprocess.run(args, capture_output=True, text=True)
    if p.returncode != 0:
        return {'path': path, 'err': p.stderr.strip()[:160]}
    code, size, redir = (p.stdout.split('\t') + [''] * 3)[:3]
    headers, statuses = {}, []
    with open('/tmp/b3d_hdr.txt', encoding='utf-8', errors='replace') as fh:
        for line in fh:
            if line.lower().startswith('http/'):
                statuses.append(line.strip())
            elif ':' in line:
                k, v = line.split(':', 1)
                headers.setdefault(k.strip().lower(), []).append(v.strip())
    body = open('/tmp/b3d_body.txt', 'rb').read().decode('utf-8', 'replace') if want_body else ''
    return {'path': path, 'status': int(code), 'size': int(size or 0),
            'redirect': redir, 'headers': {k: headers.get(k) for k in HEADERS_OF_INTEREST
                                           if k in headers},
            'status_lines': statuses, 'body': body}


def main():
    rows = []
    for path, expect, why in TARGETS:
        r = get(path, want_body='alert(1)' in path or path == '/wp-json/')
        r['expect'] = expect
        r['why'] = why
        r['verdict'] = ('ok' if str(r.get('status')) in expect else 'REVIEW')
        rows.append(r)
        extra = ''
        if 'alert(1)' in path:
            escaped = '&lt;script&gt;' in r['body']
            raw = '<script>alert(1)</script>' in r['body']
            r['payload_escaped'] = escaped
            r['payload_raw'] = raw
            extra = '  payload escaped=%s raw=%s' % (escaped, raw)
        print('%-4s %-52s %s  %s%s' % (r['verdict'], path, r.get('status'),
                                       ','.join(expect), extra))
        time.sleep(SLEEP)

    print('\n=== response headers on / ===')
    base = rows[0]['headers']
    for k in HEADERS_OF_INTEREST:
        print('  %-28s %s' % (k, (base.get(k) or ['(absent)'])[0][:110]))

    print('\n=== security headers: which are present ===')
    have = [k for k in HEADERS_OF_INTEREST if k in base]
    want = ['strict-transport-security', 'x-frame-options', 'x-content-type-options',
            'referrer-policy', 'permissions-policy', 'content-security-policy']
    for k in want:
        print('  %-28s %s' % (k, 'PRESENT' if k in base else 'absent'))

    print('\n=== REST namespace exposure ===')
    root = next((r for r in rows if r['path'] == '/wp-json/'), {})
    if root.get('body'):
        try:
            ns = json.loads(root['body']).get('namespaces', [])
            print('  namespaces:', ', '.join(ns))
        except Exception as e:
            print('  could not parse:', e)

    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump([{k: v for k, v in r.items() if k != 'body'} for r in rows], fh,
                  ensure_ascii=False, indent=1)
    review = [r for r in rows if r['verdict'] == 'REVIEW']
    print('\n=== %d probed, %d need review ===' % (len(rows), len(review)))
    for r in review:
        print('  REVIEW %-46s got %s, expected %s -- %s' %
              (r['path'], r.get('status'), ','.join(r['expect']), r['why']))
    print('-> %s' % OUT)


if __name__ == '__main__':
    main()

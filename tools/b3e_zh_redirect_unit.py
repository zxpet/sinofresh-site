#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Offline cases for the /zh/ redirect rule, run against the shipped PHP.

The rule's decision is pure -- given publish-languages and a REQUEST_URI,
redirect or not -- so it can be driven without a web server. Each case runs
tools/b3e_zh_redirect_probe.php in its own process, because the real function
calls exit() on the redirect path.

The load-bearing case is the first block: while zh_CN is still published the
rule must do nothing at all. That is the negative control, and without it a
rule that redirected unconditionally would pass every positive case here.

  python3 tools/b3e_zh_redirect_unit.py
"""

import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
THEME = os.path.join(ROOT, 'sinofresh-theme')
PROBE = os.path.join(HERE, 'b3e_zh_redirect_probe.php')

PHP = '/Users/meng/Library/Application Support/Local/lightning-services/php-8.2.29+0/bin/darwin-arm64/bin/php'

EN_ONLY = {'publish-languages': ['en_US']}
BOTH = {'publish-languages': ['en_US', 'zh_CN']}
THREE = {'publish-languages': ['en_US', 'zh_CN', 'de_DE']}
EMPTY = {'publish-languages': []}
NO_KEY = {'default-language': 'en_US'}

BASE = 'https://dev.zxpet.com'

# (label, uri, method, option, expected)  expected: 'no' or an absolute URL
CASES = [
    # --- negative control: zh_CN is published, so nothing may move -------------
    ('published: /zh/',                 '/zh/',                 'GET',  BOTH,   'no'),
    ('published: /zh/about/',           '/zh/about/',           'GET',  BOTH,   'no'),
    ('published: /zh/formulas/x/',      '/zh/formulas/x/',      'GET',  BOTH,   'no'),

    # --- the withdrawn state: per-page 301 to the English twin ----------------
    ('withdrawn: /zh/ -> home',         '/zh/',                 'GET',  EN_ONLY, BASE + '/'),
    ('withdrawn: /zh -> home',          '/zh',                  'GET',  EN_ONLY, BASE + '/'),
    ('withdrawn: /zh/about/',           '/zh/about/',           'GET',  EN_ONLY, BASE + '/about/'),
    ('withdrawn: /zh/quality/',         '/zh/quality/',         'GET',  EN_ONLY, BASE + '/quality/'),
    ('withdrawn: deep path',            '/zh/formulas/joint-support-soft-chews/',
                                                                 'GET',  EN_ONLY, BASE + '/formulas/joint-support-soft-chews/'),
    ('withdrawn: query kept',           '/zh/about/?a=1&b=2',   'GET',  EN_ONLY, BASE + '/about/?a=1&b=2'),
    ('withdrawn: search kept',          '/zh/?s=test',          'GET',  EN_ONLY, BASE + '/?s=test'),
    ('withdrawn: HEAD also redirects',  '/zh/about/',           'HEAD', EN_ONLY, BASE + '/about/'),
    ('withdrawn: double slash folded',  '/zh//about/',          'GET',  EN_ONLY, BASE + '/about/'),

    # --- must not fire on things that are not /zh/ ----------------------------
    ('en page untouched',               '/about/',              'GET',  EN_ONLY, 'no'),
    ('lookalike prefix untouched',      '/zhxyz/about/',        'GET',  EN_ONLY, 'no'),
    ('en root untouched',               '/',                    'GET',  EN_ONLY, 'no'),

    # --- exempted segments: these serve something under /zh/ ------------------
    ('wp-json exempt',                  '/zh/wp-json/wp/v2/types', 'GET', EN_ONLY, 'no'),
    ('feed exempt',                     '/zh/feed/',            'GET',  EN_ONLY, 'no'),
    ('feed exempt (no slash)',          '/zh/feed',             'GET',  EN_ONLY, 'no'),
    ('wp-content exempt',               '/zh/wp-content/uploads/a.png', 'GET', EN_ONLY, 'no'),
    ('wp-login exempt',                 '/zh/wp-login.php',     'GET',  EN_ONLY, 'no'),
    ('cdn-cgi exempt',                  '/zh/cdn-cgi/l/email-protection#ab', 'GET', EN_ONLY, 'no'),

    # --- the editor exemption, scoped to the parameter and not the prefix -----
    ('editor param exempt',             '/zh/about/?trp-edit-translation=true', 'GET', EN_ONLY, 'no'),
    ('editor param exempt (bare)',      '/zh/about/?trp-edit-translation',      'GET', EN_ONLY, 'no'),
    ('editor param + others exempt',    '/zh/about/?foo=1&trp-edit-translation=1', 'GET', EN_ONLY, 'no'),
    ('other params still redirect',     '/zh/about/?foo=1',     'GET',  EN_ONLY, BASE + '/about/?foo=1'),

    # --- methods other than GET/HEAD -----------------------------------------
    ('POST not redirected',             '/zh/about/',           'POST', EN_ONLY, 'no'),
    ('PUT not redirected',              '/zh/about/',           'PUT',  EN_ONLY, 'no'),

    # --- other shapes of publish-languages mean the rule has nothing to say ---
    ('empty publish-languages',         '/zh/about/',           'GET',  EMPTY,   'no'),
    ('no publish-languages key',        '/zh/about/',           'GET',  NO_KEY,  'no'),
    ('three languages',                 '/zh/about/',           'GET',  THREE,   'no'),
    ('no trp_settings at all',          '/zh/about/',           'GET',  None,    'no'),
]

FAILED = []


def run(label, uri, method, option, expected):
    payload = {'uri': uri, 'method': method, 'option': option}
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as fh:
        json.dump(payload, fh)
        path = fh.name
    try:
        p = subprocess.run([PHP, PROBE, path, THEME],
                           capture_output=True, text=True, timeout=30)
    finally:
        os.unlink(path)

    out = [ln for ln in p.stdout.strip().splitlines() if ln.strip()]
    if p.returncode != 0:
        FAILED.append((label, 'php exited %d: %s' % (p.returncode, p.stderr.strip()[:200])))
        return
    if len(out) != 1:
        FAILED.append((label, 'expected exactly one outcome line, got %r' % (out,)))
        return

    line = out[0]
    if expected == 'no':
        ok = (line == 'NO_REDIRECT')
        got = line
    else:
        ok = line.startswith('REDIRECT 301 ') and line[len('REDIRECT 301 '):] == expected
        got = line
    if not ok:
        FAILED.append((label, 'wanted %s, got %s' % (
            'NO_REDIRECT' if expected == 'no' else '301 ' + expected, got)))


for label, uri, method, option, expected in CASES:
    run(label, uri, method, option, expected)

print('cases: %d' % len(CASES))
if FAILED:
    print('FAILED: %d' % len(FAILED))
    for label, why in FAILED:
        print('  - %-34s %s' % (label, why))
    sys.exit(1)
print('all passed')

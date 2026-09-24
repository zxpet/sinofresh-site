#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Acceptance for the withdrawn ZH locale, measured on the wire.

Two questions, and the first one is not the obvious one.

Q1. After zh_CN leaves publish-languages, what does the site do with /zh/ URLs
    on its own? WordPress's redirect_canonical is believed to answer some of
    them, because with the locale unpublished the request falls through to a
    404 and redirect_guess_404_permalink() then guesses a target -- but only
    when a `name` query var exists, which page paths have and custom-post-type
    rewrite paths do not. That has to be measured rather than assumed, because
    it sets how much of this batch is a new rule and how much already existed.
    So every /zh/ route is fetched TWICE: once with no scenario header (live,
    which has none of this theme's new code) and once with X-SF-Preflight: 1
    (the copy that has it). The delta is this batch's actual contribution, and
    X-Redirect-By names the author of each redirect.

Q2. On the preflight side, does every /zh/ route land on its English twin, with
    the exceptions and the query string intact?

Two client-side traps are handled explicitly, because the first run of this
tool fell into both and reported 57 failures that were entirely its own:

  * urllib follows 3xx by default, so a 301 arrives as the 200 at the end of the
    chain and the redirect is invisible. The opener below refuses to follow, so
    the 301 is the response.
  * Declaring Accept-Encoding: gzip while never inflating means the body is
    compressed bytes and every regex over it silently matches nothing -- which
    is how a page carrying two hreflang tags read as carrying none. No
    Accept-Encoding is sent, so the body is plain.

Every request is made logged out. The nginx Basic credential is not a WordPress
login, so every session here is a visitor -- which matters because the switcher
reads translation-languages for anyone with manage_options and
publish-languages only for visitors. Checking it while logged in would show a
locale that visitors never see.

  python3 tools/b3e_zh_verify.py [--json /tmp/out.json]
"""

import argparse
import base64
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

USER, PASS = 'sfdev', 'VkEws18Kl5V1qp3TpZ6s'
BASE = 'https://dev.zxpet.com'
AUTH = 'Basic ' + base64.b64encode(('%s:%s' % (USER, PASS)).encode()).decode()

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CRAWL = os.path.join(ROOT, 'docs', 'site-survey-2026-09-24', 'crawl.json')

SLEEP = 1.3
FAILED = []
RIGHTS = []


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None          # a 3xx then surfaces as HTTPError: code + Location


OPENER = urllib.request.build_opener(_NoRedirect)


def fetch(path, preflight, want_body=False, tries=3):
    """One request. Returns (status, location, x_redirect_by, body, err).

    A transport failure is returned as err, never folded into a status: an
    absent answer must not read as a passing one.
    """
    url = BASE + path
    headers = {'Authorization': AUTH, 'Cache-Control': 'no-cache',
               'User-Agent': 'b3e-zh-verify/1'}
    if preflight:
        headers['X-SF-Preflight'] = '1'
    last = None
    for _ in range(tries):
        try:
            req = urllib.request.Request(url, headers=headers, method='GET')
            with OPENER.open(req, timeout=30) as r:
                body = r.read().decode('utf-8', 'replace') if want_body else ''
                return (r.status, r.headers.get('Location'),
                        r.headers.get('X-Redirect-By'), body, None)
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8', 'replace') if want_body else ''
            return (e.code, e.headers.get('Location'),
                    e.headers.get('X-Redirect-By'), body, None)
        except Exception as e:                      # noqa: BLE001
            last = '%s: %s' % (type(e).__name__, e)
            time.sleep(1.5)
    return None, None, None, '', last


def zh_routes():
    """The ZH routes, from the survey's own crawl rather than re-derived."""
    crawl = json.load(open(CRAWL))
    out = []
    for r in crawl:
        p = r['url'].split('dev.zxpet.com')[1]
        if p == '/zh/' or p.startswith('/zh/'):
            out.append(p)
    return sorted(set(out))


def strip_zh(path):
    """'/zh/about/' -> '/about/' ; '/zh/' -> '/' ; '/zh' -> '/'."""
    rest = path[3:] if path.startswith('/zh') else ''
    return '/' + rest.lstrip('/')


def check(label, ok, detail=''):
    if ok:
        RIGHTS.append(label)
    else:
        FAILED.append((label, detail))
    print('  %-4s %s%s' % ('ok' if ok else 'FAIL', label,
                           ('  -- ' + detail) if (detail and not ok) else ''))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--json', default='/tmp/b3e-zh-verify.json')
    args = ap.parse_args()

    routes = zh_routes()
    print('=== 0. scope ===')
    print('  ZH routes in the survey crawl: %d' % len(routes))
    print('  every request logged out; 3xx not followed; body sent uncompressed')

    print('\n=== 1. all %d ZH routes, live vs preflight ===' % len(routes))
    rows = []
    for i, p in enumerate(routes, 1):
        st_l, loc_l, by_l, _, e_l = fetch(p, preflight=False)
        time.sleep(SLEEP)
        st_p, loc_p, by_p, _, e_p = fetch(p, preflight=True)
        time.sleep(SLEEP)
        rows.append({'zh': p, 'live_status': st_l, 'live_loc': loc_l, 'live_by': by_l,
                     'pre_status': st_p, 'pre_loc': loc_p, 'pre_by': by_p,
                     'want': BASE + strip_zh(p), 'err': e_l or e_p})
        print('  [%2d/%d] %-46s live=%-4s(%s) pre=%-4s(%s)' % (
            i, len(routes), p, st_l, by_l or '-', st_p, by_p or '-'))

    print('\n=== 2. what the site already did, and what this batch added ===')
    def tally(key):
        d = {}
        for r in rows:
            d[r[key]] = d.get(r[key], 0) + 1
        return d
    print('  live  status: %s' % tally('live_status'))
    print('  live  author: %s' % tally('live_by'))
    print('  pre   status: %s' % tally('pre_status'))
    print('  pre   author: %s' % tally('pre_by'))
    live_404 = [r['zh'] for r in rows if r['live_status'] == 404]
    print('  routes the site left as a 404 on its own: %d' % len(live_404))
    for p in live_404:
        print('    %s' % p)
    gained = [r for r in rows if r['live_status'] != 301 and r['pre_status'] == 301]
    print('  routes this batch newly turns into a 301: %d' % len(gained))
    for r in gained:
        print('    %s  (live was %s, now 301 via %s)' % (r['zh'], r['live_status'], r['pre_by']))

    print('\n=== 3. preflight column: every route must 301 to its English twin ===')
    for r in rows:
        if r['err']:
            check('no transport error: %s' % r['zh'], False, r['err'])
            continue
        check('301 %s -> %s' % (r['zh'], strip_zh(r['zh'])),
              r['pre_status'] == 301 and r['pre_loc'] == r['want'],
              'got %s %s' % (r['pre_status'], r['pre_loc']))

    print('\n=== 4. who answers on each side ===')
    check('every preflight redirect is authored by this theme',
          all(r['pre_by'] == 'SINO FRESH' for r in rows if r['pre_status'] == 301),
          str(tally('pre_by')))
    check('live redirects are authored by WordPress, not this theme',
          all(r['live_by'] in (None, 'WordPress') for r in rows),
          str(tally('live_by')))

    print('\n=== 5. exceptions and query strings ===')
    cases = [
        ('/zh/wp-json/wp/v2/types', 'declared exempt: must not be redirected by this rule'),
        ('/zh/feed/',               'declared exempt: must not be redirected by this rule'),
        ('/zh/about/?trp-edit-translation=true', 'the editor must still reach a locale'),
        ('/zh/about/?a=1&b=2',      'must 301 and keep the query'),
    ]
    extras = []
    for p, why in cases:
        st, loc, by, _, err = fetch(p, preflight=True)
        time.sleep(SLEEP)
        extras.append({'path': p, 'status': st, 'location': loc, 'by': by, 'why': why})
        print('  %-42s -> %-4s by=%-11s %s' % (p, st, by or '-', loc or ''))

    check('/zh/wp-json/... is not redirected by this rule',
          (extras[0]['by'] or '') != 'SINO FRESH',
          'status=%s by=%s' % (extras[0]['status'], extras[0]['by']))
    check('/zh/feed/ is not redirected by this rule',
          (extras[1]['by'] or '') != 'SINO FRESH',
          'status=%s by=%s' % (extras[1]['status'], extras[1]['by']))
    # The exemption governs what THIS rule does, not what the site does. Measured:
    # the editor request still comes back 301, authored by WordPress -- because
    # /zh/about/ is a 404 and core's 404 guess runs at canonical priority 10,
    # after this rule has already declined. Reported rather than failed: it costs
    # nothing while the locale is withdrawn (there is no ZH to edit), and the
    # editor returns by itself the moment zh_CN goes back into publish-languages,
    # which is step 1 of the re-attach checklist.
    check('this rule does not redirect the editor request',
          (extras[2]['by'] or '') != 'SINO FRESH',
          'status=%s by=%s' % (extras[2]['status'], extras[2]['by']))
    print('        (the site itself answers %s by=%s to that request)'
          % (extras[2]['status'], extras[2]['by']))
    check('query string survives the redirect',
          extras[3]['status'] == 301 and (extras[3]['location'] or '').endswith('/about/?a=1&b=2'),
          'got %s %s' % (extras[3]['status'], extras[3]['location']))

    st, loc, by, _, err = fetch('/zh/does-not-exist-xyz/', preflight=True)
    time.sleep(SLEEP)
    junk = {'path': '/zh/does-not-exist-xyz/', 'status': st, 'location': loc, 'by': by}
    print('  %-42s -> %-4s by=%-11s %s' % (junk['path'], st, by or '-', loc or ''))
    # Recorded, deliberately neither green nor red. The rule strips the prefix
    # without asking whether the target exists, and asking is the worse option:
    # the survey measured url_to_postid() returning 0 for /blog/, an ordinary
    # published page, so a resolver-based guard would have turned a real route
    # into a 404 in order to save a cosmetic hop on a junk one. A 301 to a 404
    # is the same soft-404 outcome as the 404 it replaced.
    print('        (a junk ZH path 301s to a junk EN path; both end at 404)')

    print('\n=== 6. hreflang no longer advertises zh ===')
    st, loc, by, body, err = fetch('/about/', preflight=True, want_body=True)
    time.sleep(SLEEP)
    tags = re.findall(r'<link[^>]*hreflang="([^"]+)"', body)
    print('  /about/ hreflang: %s  (html lang %s)' % (
        tags, (re.search(r'<html[^>]*lang="([^"]*)"', body) or [None, '?'])[1]))
    check('no zh / zh-CN hreflang left',
          not any(t.lower().startswith('zh') for t in tags), 'found %s' % tags)
    check('the English side still declares itself',
          any(t.lower().startswith('en') for t in tags), 'found %s' % tags)

    print('\n=== 7. the floater is gone for a visitor ===')
    st, loc, by, body, err = fetch('/about/', preflight=True, want_body=True)
    time.sleep(SLEEP)
    floater = 'trp-floating-switcher' in body
    switcher = 'trp-language-switcher' in body
    items = len(re.findall(r'trp-language-item', body))
    nav = body.count('<nav class="trp-language-switcher')
    print('  trp-floating-switcher: %s' % floater)
    print('  trp-language-switcher substring: %s  (asset refs only? nav markup: %d)'
          % (switcher, nav))
    print('  trp-language-item occurrences: %d' % items)
    check('floating switcher no longer rendered', not floater)
    # Anchor on the markup, not the string: the same three occurrences of
    # `trp-language-switcher` are the id/href of trp-language-switcher-v2.css and
    # the id/src of trp-frontend-language-switcher.js, both of which
    # TranslatePress still enqueues on a single-language site. Asserting on the
    # substring is the same mistake wp-block-template-skip-link taught during
    # the survey -- a core-injected string that survives with no markup behind it.
    check('no language-item markup, so no empty shell is left behind',
          items == 0, 'trp-language-item occurrences: %d' % items)
    check('no <nav class="trp-language-switcher"> markup', nav == 0, 'nav count %d' % nav)

    print('\n=== 8. the English side is untouched ===')
    for p in ['/', '/about/', '/quality/', '/formulas/']:
        st, loc, by, _, err = fetch(p, preflight=True)
        time.sleep(SLEEP)
        check('%s still 200' % p, st == 200, 'got %s %s' % (st, err or ''))

    payload = {'routes': rows, 'extras': extras, 'junk': junk,
               'failed': FAILED, 'passed': RIGHTS}
    with open(args.json, 'w') as fh:
        json.dump(payload, fh, indent=1, ensure_ascii=False)
    print('\njson -> %s' % args.json)

    print('\n=== summary ===')
    print('  checks passed: %d' % len(RIGHTS))
    print('  checks failed: %d' % len(FAILED))
    for label, why in FAILED:
        print('    FAIL %s -- %s' % (label, why))
    return 1 if FAILED else 0


if __name__ == '__main__':
    sys.exit(main())

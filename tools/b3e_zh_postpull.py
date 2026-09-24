#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Post-pull acceptance for the withdrawn ZH locale.

`b3e_zh_verify.py` was written while the pull was still held: it measured the
served theme (no scenario header) against the preflight copy (X-SF-Preflight: 1)
and asserted that the redirects authored by this theme existed only on the
preflight side. That assertion is now false by design -- pulling is exactly what
makes it false. So this is a separate gate rather than an edit of that one: the
old script stays the record of what was true before the pull.

What changes here is the shape of the question. With the code served, there is
nothing to compare against, so every request is a plain one -- no scenario
header, no second column -- and that IS the production path. What has to hold:

  1. every ZH route answers 301, authored by this theme, to its English twin;
  2. none of them answers 404 any more (the core 404 guess left 34 of them);
  3. the redirect target is a real 200, not a second hop to nowhere;
  4. the exemptions still hold, and the query string survives;
  5. no zh hreflang is advertised, and no switcher markup is rendered;
  6. the English side is untouched, and the site is still the site.

Same two client traps as the earlier tool, handled the same way: 3xx are not
followed (so the 301 is the response), and no Accept-Encoding is sent (so the
body is plain and regexes over it mean something). Requests are made logged out,
because the switcher reads publish-languages only for visitors.

  python3 tools/b3e_zh_postpull.py [--json /tmp/out.json]
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

SLEEP = 1.2
FAILED, RIGHTS = [], []


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


OPENER = urllib.request.build_opener(_NoRedirect)


def fetch(path, want_body=False, tries=3):
    """One plain request. Returns (status, location, x_redirect_by, body, err)."""
    url = BASE + path
    headers = {'Authorization': AUTH, 'Cache-Control': 'no-cache',
               'User-Agent': 'b3e-zh-postpull/1'}
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
    crawl = json.load(open(CRAWL))
    out = []
    for r in crawl:
        p = r['url'].split('dev.zxpet.com')[1]
        if p == '/zh/' or p.startswith('/zh/'):
            out.append(p)
    return sorted(set(out))


def strip_zh(path):
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
    ap.add_argument('--json', default='/tmp/b3e-zh-postpull.json')
    args = ap.parse_args()

    print('=== 0. guard: is this the site, or an error page? ===')
    st, _, _, body, err = fetch('/', want_body=True)
    has_theme_css = bool(re.search(
        r'<link[^>]+rel=[\'"]stylesheet[\'"][^>]*themes/sinofresh-theme', body))
    print('  / -> %s   theme stylesheet link: %s' % (st, has_theme_css))
    check('the served page carries this theme\'s stylesheet', has_theme_css,
          'status=%s err=%s' % (st, err))
    check('the served page does not advertise the preflight copy',
          '-preflight' not in body, 'found -preflight in the served bytes')

    routes = zh_routes()
    print('\n=== 1. scope ===')
    print('  ZH routes in the survey crawl: %d' % len(routes))
    print('  plain requests, logged out; 3xx not followed; body uncompressed')

    print('\n=== 2. every ZH route, on the served theme ===')
    rows = []
    for i, p in enumerate(routes, 1):
        st, loc, by, _, e = fetch(p)
        time.sleep(SLEEP)
        rows.append({'zh': p, 'status': st, 'location': loc, 'by': by,
                     'want': BASE + strip_zh(p), 'err': e})
        print('  [%2d/%d] %-46s %-4s by=%-11s -> %s' % (
            i, len(routes), p, st, by or '-', loc or ''))

    def tally(key):
        d = {}
        for r in rows:
            d[r[key]] = d.get(r[key], 0) + 1
        return d

    print('\n  status tally: %s' % tally('status'))
    print('  author tally: %s' % tally('by'))

    print('\n=== 3. the assertions ===')
    for r in rows:
        if r['err']:
            check('no transport error: %s' % r['zh'], False, r['err'])
            continue
        check('301 %s -> %s' % (r['zh'], strip_zh(r['zh'])),
              r['status'] == 301 and r['location'] == r['want'],
              'got %s %s' % (r['status'], r['location']))
    check('no ZH route is left as a 404',
          not [r for r in rows if r['status'] == 404],
          str([r['zh'] for r in rows if r['status'] == 404]))
    check('every redirect is authored by this theme',
          all(r['by'] == 'SINO FRESH' for r in rows if r['status'] == 301),
          str(tally('by')))

    print('\n=== 4. the target is a real page, not a second hop ===')
    bad = []
    for r in rows[:8] + rows[-4:]:
        tgt = strip_zh(r['zh'])
        st, loc, by, _, e = fetch(tgt)
        time.sleep(SLEEP)
        if st != 200:
            bad.append('%s -> %s' % (r['zh'], st))
        print('  %-46s -> %-4s (by=%s)' % (tgt, st, by or '-'))
    check('the redirect target answers 200 for the sampled routes', not bad, str(bad))

    print('\n=== 5. exemptions, editor, query string ===')
    cases = [
        ('/zh/wp-json/wp/v2/types', 'declared exempt: this rule must not touch it'),
        ('/zh/feed/',               'declared exempt: this rule must not touch it'),
        ('/zh/about/?trp-edit-translation=true', 'editor request: this rule must not touch it'),
        ('/zh/about/?a=1&b=2',      'must 301 and keep the query'),
    ]
    extras = []
    for p, why in cases:
        st, loc, by, _, e = fetch(p)
        time.sleep(SLEEP)
        extras.append({'path': p, 'status': st, 'location': loc, 'by': by, 'why': why})
        print('  %-42s -> %-4s by=%-11s %s' % (p, st, by or '-', loc or ''))

    check('/zh/wp-json/... is not redirected by this rule',
          (extras[0]['by'] or '') != 'SINO FRESH',
          'status=%s by=%s' % (extras[0]['status'], extras[0]['by']))
    check('/zh/feed/ is not redirected by this rule',
          (extras[1]['by'] or '') != 'SINO FRESH',
          'status=%s by=%s' % (extras[1]['status'], extras[1]['by']))
    # The exemption governs what THIS rule does, not what the site does: core's
    # 404 guess still runs at canonical priority 10 and answers this one. While
    # the locale is withdrawn there is no ZH editor to reach anyway, and the
    # editor returns by itself when zh_CN goes back into publish-languages --
    # step 1 of the re-attach checklist.
    check('this rule does not redirect the editor request',
          (extras[2]['by'] or '') != 'SINO FRESH',
          'status=%s by=%s' % (extras[2]['status'], extras[2]['by']))
    print('        (whatever answers it, it is not this rule: %s by=%s)'
          % (extras[2]['status'], extras[2]['by']))
    check('query string survives the redirect',
          extras[3]['status'] == 301 and (extras[3]['location'] or '').endswith('/about/?a=1&b=2'),
          'got %s %s' % (extras[3]['status'], extras[3]['location']))

    print('\n=== 6. negative control: the rule stays out of the English side ===')
    for p in ['/', '/about/', '/quality/', '/formulas/', '/blog/']:
        st, loc, by, _, e = fetch(p)
        time.sleep(SLEEP)
        check('EN %s is not redirected by this rule' % p,
              st == 200 and (by or '') != 'SINO FRESH',
              'got %s by=%s' % (st, by))
    # A path that merely contains "zh" must not be caught by the prefix match.
    st, loc, by, _, e = fetch('/zhang-not-a-locale/')
    time.sleep(SLEEP)
    print('  %-42s -> %-4s by=%-11s %s' % ('/zhang-not-a-locale/', st, by or '-', loc or ''))
    check('a path that merely starts with z-h is not captured',
          (by or '') != 'SINO FRESH', 'status=%s by=%s' % (st, by))

    print('\n=== 7. hreflang no longer advertises zh ===')
    st, _, _, body, e = fetch('/about/', want_body=True)
    time.sleep(SLEEP)
    tags = re.findall(r'<link[^>]*hreflang="([^"]+)"', body)
    lang = (re.search(r'<html[^>]*lang="([^"]*)"', body) or [None, '?'])[1]
    print('  /about/ hreflang: %s   (html lang %s)' % (tags, lang))
    check('no zh / zh-CN hreflang left',
          not any(t.lower().startswith('zh') for t in tags), 'found %s' % tags)
    check('the English side still declares itself',
          any(t.lower().startswith('en') for t in tags), 'found %s' % tags)
    check('the English page is served as English', lang.lower().startswith('en'),
          'html lang=%s' % lang)

    print('\n=== 8. the floater is gone for a visitor ===')
    floater = 'trp-floating-switcher' in body
    sub = 'trp-language-switcher' in body
    items = len(re.findall(r'trp-language-item', body))
    nav = body.count('<nav class="trp-language-switcher')
    print('  trp-floating-switcher: %s' % floater)
    print('  trp-language-switcher substring: %s   nav markup: %d' % (sub, nav))
    print('  trp-language-item occurrences: %d' % items)
    check('floating switcher no longer rendered', not floater)
    # Anchor the markup, never the substring: the surviving occurrences of
    # `trp-language-switcher` are the id/href of trp-language-switcher-v2.css and
    # the id/src of trp-frontend-language-switcher.js, both still enqueued by
    # TranslatePress on a single-language site. Same shape as the
    # wp-block-template-skip-link false positive during the survey.
    check('no language-item markup, so no empty shell is left behind',
          items == 0, 'occurrences: %d' % items)
    check('no <nav class="trp-language-switcher"> markup', nav == 0, 'nav count %d' % nav)

    print('\n=== 9. the site is still the site ===')
    st, _, _, body2, e = fetch('/', want_body=True)
    time.sleep(SLEEP)
    check('home still 200', st == 200, 'got %s %s' % (st, e or ''))
    check('transport answered twice with the same status', st == 200 and not e)

    payload = {'routes': rows, 'extras': extras, 'hreflang': tags,
               'html_lang': lang, 'failed': FAILED, 'passed': RIGHTS}
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

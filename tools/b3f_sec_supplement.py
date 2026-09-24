#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Supplement to the site-wide survey's security section: 8.6 / 8.7 / 8.8.

The survey's own §3 answered "can a stranger reach something they should not",
with 30 designed probes. This tool answers the three questions that section did
not ask, each of which needs a different kind of evidence:

  8.8  Server headers. Not "is X present" on one page but a matrix over five
       kinds of response -- HTML, REST, a static asset, a 404, and the plain
       HTTP port -- because several headers are set per-handler, not globally
       (WP's REST controller sends nosniff; the front end does not).

  8.7  Third-party origins, from the survey's own crawl rather than a fresh
       fetch, so the inventory covers all 108 pages and not just the homepage.
       SRI is counted on external scripts and stylesheets, which is where a
       supply-chain compromise would land.

  8.6  Consent. Read from the theme's files rather than from rendered HTML:
       which storage key holds the decision, which buttons write it, which
       scripts consult it, and -- the question that matters -- whether the
       page's own analytics respect it.

Two client details are load-bearing here and both were measured rather than
assumed:

  * Cloudflare injects its Web Analytics beacon only when the request looks
    like a navigation (Accept: text/html,...). The same URL fetched with curl's
    default Accept: */* returns no beacon at all. A "no beacon" reading taken
    without the Accept header would have been an artefact of the probe.
  * No Accept-Encoding is sent, so the body is plain and the regexes over it
    mean something.

  python3 tools/b3f_sec_supplement.py [--json docs/security-supplement-2026-09-24/supplement.json]
"""

import argparse
import base64
import glob
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict

USER, PASS = 'sfdev', 'VkEws18Kl5V1qp3TpZ6s'
BASE = 'https://dev.zxpet.com'
AUTH = 'Basic ' + base64.b64encode(('%s:%s' % (USER, PASS)).encode()).decode()
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/140 Safari/537.36')
NAV_ACCEPT = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, 'docs', 'site-survey-2026-09-24', 'cache')
THEME = os.path.join(ROOT, 'sinofresh-theme')

SLEEP = 1.0
FAILED, RIGHTS = [], []

# Headers a public marketing site should send. The "why" is the point: each of
# these closes a class of attack that a bare CMS leaves open.
WANT = [
    ('strict-transport-security', 'no downgrade to plain HTTP for a year'),
    ('content-security-policy',   'injected script cannot run; XSS blast radius'),
    ('x-content-type-options',    'no MIME sniffing of uploaded/odd types'),
    ('x-frame-options',           'no framing: clickjacking'),
    ('referrer-policy',           'no full URL leaked to third parties'),
    ('permissions-policy',        'camera/mic/geolocation off by declaration'),
]


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


OPENER = urllib.request.build_opener(_NoRedirect)


def head(path, accept=None, base=BASE, auth=True, tries=3):
    """Returns (status, headers dict lowercased, body, err)."""
    h = {'Cache-Control': 'no-cache',
         'Accept': accept or '*/*',
         'User-Agent': UA}
    if auth:
        h['Authorization'] = AUTH
    last = None
    for _ in range(tries):
        try:
            req = urllib.request.Request(base + path, headers=h, method='GET')
            with OPENER.open(req, timeout=30) as r:
                body = r.read().decode('utf-8', 'replace')
                return r.status, {k.lower(): v for k, v in r.headers.items()}, body, None
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8', 'replace')
            return e.code, {k.lower(): v for k, v in e.headers.items()}, body, None
        except Exception as e:                       # noqa: BLE001
            last = '%s: %s' % (type(e).__name__, e)
            time.sleep(1.5)
    return None, {}, '', last


def check(label, ok, detail=''):
    (RIGHTS if ok else FAILED).append(label if ok else (label, detail))
    print('  %-4s %s%s' % ('ok' if ok else 'FAIL', label,
                           ('  -- ' + detail) if (detail and not ok) else ''))


def visible_text(html):
    """The words a reader sees, with markup and scripts removed.

    Asserting "the policy does not mention X" against the raw response is the
    substring-not-structure trap: the beacon's own URL contains the string
    'cloudflareinsights', so a raw-body search reports the policy as disclosing
    Cloudflare while the prose never does. Narrow the haystack to the prose.
    """
    import html as _html
    t = re.sub(r'(?is)<(script|style)\b[^>]*>.*?</\1>', ' ', html)
    t = re.sub(r'(?s)<[^>]+>', ' ', t)
    return re.sub(r'\s+', ' ', _html.unescape(t))


def sec_8_8():
    print('\n=== 8.8 server headers: matrix over five kinds of response ===')
    targets = [
        ('html front page', '/', NAV_ACCEPT),
        ('html deep page', '/about/', NAV_ACCEPT),
        ('rest api', '/wp-json/', None),
        ('static css', '/wp-content/themes/sinofresh-theme/style.css', None),
        ('404', '/no-such-page-8-8/', NAV_ACCEPT),
    ]
    matrix = {}
    for name, path, accept in targets:
        st, h, body, err = head(path, accept)
        time.sleep(SLEEP)
        matrix[name] = {'path': path, 'status': st, 'headers': h, 'err': err,
                        'beacon': 'cloudflareinsights' in body}
        print('  %-16s %-46s %s' % (name, path, st))

    print('\n  -- which security headers appear where --')
    for hname, why in WANT:
        where = [n for n, r in matrix.items() if hname in r['headers']]
        print('   %-28s %-22s %s' % (hname, (','.join(where) or 'NOWHERE'), why))

    html = matrix['html front page']['headers']
    for hname, why in WANT:
        # REST sends nosniff of its own accord; that is not a site-wide policy,
        # so the assertion is about the HTML response a visitor actually gets.
        check('front-end HTML sends %s' % hname, hname in html, why)

    check('no x-powered-by leaking the exact PHP build',
          'x-powered-by' not in html, html.get('x-powered-by', ''))
    check('the origin server is not named', html.get('server', '') == 'cloudflare',
          html.get('server', ''))
    check('HTML is not marked privately cacheable for a day',
          'max-age=86400' not in (html.get('cache-control') or ''),
          html.get('cache-control', ''))
    check('static assets are fingerprinted-immutable',
          'immutable' in (matrix['static css']['headers'].get('cache-control') or ''),
          matrix['static css']['headers'].get('cache-control', ''))
    check('no xmlrpc advertisement on the front page',
          'x-pingback' not in html, html.get('x-pingback', ''))

    print('\n  -- plain HTTP --')
    st, h, body, err = head('/', NAV_ACCEPT, base='http://dev.zxpet.com')
    time.sleep(SLEEP)
    print('   http://dev.zxpet.com/ -> %s  location=%s'
          % (st, h.get('location', '-')))
    check('plain HTTP is redirected to HTTPS', st == 301 and
          (h.get('location') or '').startswith('https://'), 'got %s' % st)

    print('\n  -- the beacon is conditional on the Accept header --')
    _, _, b_nav, _ = head('/', NAV_ACCEPT)
    time.sleep(SLEEP)
    _, _, b_any, _ = head('/', '*/*')
    time.sleep(SLEEP)
    nav_beacon = 'cloudflareinsights' in b_nav
    any_beacon = 'cloudflareinsights' in b_any
    print('   Accept: text/html -> beacon %s  |  Accept: */* -> beacon %s'
          % (nav_beacon, any_beacon))
    check('the CF beacon is present for a browser navigation', nav_beacon)
    return matrix


def sec_8_7():
    print('\n=== 8.7 third-party origins, over the whole crawl ===')
    pages = sorted(glob.glob(os.path.join(CACHE, '*.html')))
    if not pages:
        check('the survey crawl cache is present', False, CACHE)
        return {}
    hosts, example, on_pages = Counter(), defaultdict(set), defaultdict(set)
    ext_tags = sri = 0
    for f in pages:
        b = open(f, encoding='utf-8', errors='replace').read()
        for m in re.finditer(r'<(script|link|img|iframe)\b[^>]*>', b, re.I):
            tag = m.group(0)
            u = re.search(r'(?:src|href)\s*=\s*["\']([^"\']+)["\']', tag)
            if not u:
                continue
            v = u.group(1)
            if v.startswith('//'):
                v = 'https:' + v
            if not v.startswith('http'):
                continue
            h = re.sub(r'^https?://', '', v).split('/')[0].lower()
            if h.endswith('zxpet.com'):
                continue
            hosts[h] += 1
            example[h].add(v[:150])
            on_pages[h].add(os.path.basename(f))
            low = tag.lower()
            if low.startswith('<script') or (low.startswith('<link') and 'stylesheet' in low):
                ext_tags += 1
                if 'integrity=' in low:
                    sri += 1
    print('  pages scanned: %d' % len(pages))
    for h, n in hosts.most_common():
        print('   %5d refs / %3d pages  %s' % (n, len(on_pages[h]), h))
        for e in sorted(example[h])[:2]:
            print('         %s' % e)
    print('  external script/stylesheet tags: %d, carrying integrity=: %d'
          % (ext_tags, sri))
    check('every external script/stylesheet is covered by SRI',
          ext_tags == sri, '%d of %d' % (sri, ext_tags))
    check('no third-party font or asset CDN beyond Cloudflare and a video poster',
          set(hosts) <= {'static.cloudflareinsights.com', 'i.ytimg.com'},
          str(dict(hosts)))
    check('the video poster is the only Google-domain request before play',
          all('youtube' not in h or h == 'i.ytimg.com' for h in hosts),
          str(dict(hosts)))
    return {'hosts': dict(hosts),
            'pages': {h: len(v) for h, v in on_pages.items()},
            'example': {h: sorted(v) for h, v in example.items()},
            'ext_tags': ext_tags, 'sri': sri}


def sec_8_6():
    print('\n=== 8.6 consent, read from the files that implement it ===')
    ui = os.path.join(THEME, 'assets', 'js', 'ui-components.js')
    foot = os.path.join(THEME, 'parts', 'footer.html')
    if not (os.path.exists(ui) and os.path.exists(foot)):
        check('the consent sources are present', False, ui)
        return {}
    js = open(ui, encoding='utf-8', errors='replace').read()
    fh = open(foot, encoding='utf-8', errors='replace').read()

    key = re.search(r'const KEY = "([^"]+)"', js)
    print('  storage key: %s' % (key.group(1) if key else '?'))
    labels = re.findall(r'sf-cookie-banner__(?:btn--)?([a-z-]+)">([^<]+)<', fh)
    print('  banner buttons: %s' % [(a, b.strip()) for a, b in labels])

    decide = re.search(r'const decide = \(on\) => \{(.{0,600}?)\n\t\t\};', js, re.S)
    print('  decision object: %s' % (re.search(r'JSON\.stringify\(\{(.+?)\}\)', js, re.S).group(1).strip()
                                     if re.search(r'JSON\.stringify\(\{(.+?)\}\)', js, re.S) else '?'))
    manage = re.search(r'on\("\.sf-cookie-banner__manage", \(\) => ([a-zA-Z]+)\((\w+)\)\)', js)
    print('  Manage Preferences handler: %s' % (manage.group(0) if manage else '?'))

    # The question that matters is not whether a banner exists but whether the
    # analytics the page actually runs consult it. gtag is gated; the two
    # trackers the site really serves are checked on the wire in section 8.6b.
    check('the accept path grants analytics', 'decide(true)' in js)
    check('the reject path withholds analytics', 'decide(false)' in js)
    check('gtag is bridged to the stored decision',
          'applyGtagConsent' in js and 'analytics_storage' in js)
    # The lead event is emitted from functions.php, not from this file, so the
    # check has to read the file that emits it rather than assert that it does.
    fn = os.path.join(THEME, 'functions.php')
    fnsrc = open(fn, encoding='utf-8', errors='replace').read() if os.path.exists(fn) else ''
    check('the same flag drives the lead event in functions.php',
          'sf_cookie_consent' in fnsrc and 'analytics!==true' in fnsrc,
          'no consent gate found around the gtag generate_lead call')
    check('Manage Preferences opens a panel rather than deciding for the user',
          bool(manage) and manage.group(1) != 'decide',
          'handler is %s' % (manage.group(0) if manage else 'absent'))
    check('the theme publishes its decision through the Consent API',
          bool(re.search(r'wp_set_consent|wp_has_consent', js + fh)),
          'no wp_set_consent()/wp_has_consent() anywhere in the theme')
    check('consent carries a version or an expiry',
          bool(re.search(r'version|expires|maxAge', js)),
          'stored with timestamp only, so it never lapses')
    return {'key': key.group(1) if key else None,
            'buttons': [(a, b.strip()) for a, b in labels],
            'manage_handler': manage.group(0) if manage else None}


def sec_8_6b():
    """Consent, observed: which analytics the served page really starts."""
    print('\n=== 8.6b what the served page actually loads ===')
    st, h, body, err = head('/', NAV_ACCEPT)
    time.sleep(SLEEP)
    probes = {
        'wp-statistics tracker (site analytics)': 'wp-statistics/assets/js/tracker.js',
        'Cloudflare Web Analytics beacon': 'cloudflareinsights.com/beacon.min.js',
        'Google Analytics / gtag': 'googletagmanager.com',
        'WP Consent API client': 'wp-consent-api',
    }
    found = {}
    for label, needle in probes.items():
        found[label] = needle in body
        print('  %-40s %s' % (label, found[label]))
    check('nothing loads from a Google tag domain', not found['Google Analytics / gtag'])
    print('  Set-Cookie on an anonymous navigation: %s'
          % (h.get('set-cookie', 'none')))
    check('an anonymous visit sets no cookie at all',
          'set-cookie' not in h, str(h.get('set-cookie')))

    print('  -- the consent bridge is loaded but unused --')
    st2, _, body2, _ = head('/cookie-policy/', NAV_ACCEPT)
    time.sleep(SLEEP)
    prose = visible_text(body2)
    print('  cookie policy prose: %d chars' % len(prose))
    for kw in ('Cloudflare', 'Statistics', 'Google Analytics', 'Facebook Pixel',
               'LinkedIn', 'retention', 'withdraw'):
        print('    %-18s %d' % (kw, prose.lower().count(kw.lower())))
    check('the cookie policy does not promise trackers that are absent',
          not re.search(r'Google Ads|LinkedIn Insights|Facebook Pixel', prose),
          'policy names third-party cookies the site does not run')
    check('the cookie policy names the analytics that do run',
          'cloudflare' in prose.lower() or 'statistics' in prose.lower(),
          'the prose never mentions Cloudflare Web Analytics or WP Statistics')
    check('the cookie policy states retention or a withdrawal route',
          'withdraw' in prose.lower() or 'retention' in prose.lower(),
          'neither appears in the prose')
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--json',
                    default=os.path.join(ROOT, 'docs', 'security-supplement-2026-09-24',
                                         'supplement.json'))
    args = ap.parse_args()

    print('=== scope ===')
    print('  target %s, logged out, 3xx not followed, body uncompressed' % BASE)
    print('  headers are read with a browser Accept so edge-injected markup is visible')

    headers = sec_8_8()
    third = sec_8_7()
    consent = sec_8_6()
    served = sec_8_6b()

    os.makedirs(os.path.dirname(args.json), exist_ok=True)
    with open(args.json, 'w') as fh:
        json.dump({'headers': headers, 'third_party': third,
                   'consent_source': consent, 'consent_served': served,
                   'passed': RIGHTS, 'failed': FAILED},
                  fh, indent=1, ensure_ascii=False)
    print('\njson -> %s' % args.json)

    print('\n=== summary ===')
    print('  checks passed: %d' % len(RIGHTS))
    print('  checks failed: %d' % len(FAILED))
    for label, why in FAILED:
        print('    FAIL %s -- %s' % (label, why))
    return 1 if FAILED else 0


if __name__ == '__main__':
    sys.exit(main())

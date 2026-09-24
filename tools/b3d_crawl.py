#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch 3d step 2 -- one read-only pass over the whole site.

Fetches every published object twice, English and Chinese, and keeps the bytes
plus the response headers. The eight survey categories and the security pass all
read this one corpus rather than re-fetching: a survey that re-crawls per
question ends up comparing the site against itself at eight different moments,
and this project has already paid for that lesson more than once.

Nothing here writes to the site. GET only; every request spaced by SLEEP.

The 401 guard matters more than it looks: when the credentials are wrong the
site answers 200 with an authentication page, so a crawler that only checks the
status code fills its cache with 108 copies of the same login screen and every
downstream check reports "no title, no h1, no images" -- findings that read
exactly like a broken site.
"""
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import time

USER, PASS = 'sfdev', 'VkEws18Kl5V1qp3TpZ6s'
BASE = 'https://dev.zxpet.com'
SLEEP = 1.3
OUT = os.path.join('docs', 'site-survey-2026-09-24')
CACHE = os.path.join(OUT, 'cache')

# A 401 Basic-Auth sheet has neither of these; every real page has both.
SITE_MARK = re.compile(r'themes/sinofresh-theme/')
TITLE = re.compile(r'<title[^>]*>(.*?)</title>', re.S | re.I)


def slug(u):
    return hashlib.sha1(u.encode()).hexdigest()[:12]


def fetch(url, dest):
    p = subprocess.run(['curl', '-sS', '--max-time', '75', '-u',
                        '%s:%s' % (USER, PASS), '-H',
                        'Accept: text/html,application/xhtml+xml',
                        # Ask for gzip specifically. Offering `br` made the edge
                        # answer with Brotli, and this curl has no brotli: every
                        # one of the 108 fetches died with "(56) Unrecognized
                        # content encoding type" and the crawl produced an empty
                        # corpus that looked exactly like a site serving nothing.
                        '-H', 'Accept-Encoding: gzip',
                        '--compressed',
                        '-D', dest + '.hdr', '-o', dest, url],
                       capture_output=True, text=True)
    if p.returncode != 0:
        return {'url': url, 'ok': False, 'err': p.stderr.strip()[:200]}
    headers, status, clen = {}, None, None
    with open(dest + '.hdr', encoding='utf-8', errors='replace') as fh:
        for line in fh:
            if line.lower().startswith('http/'):
                status = int(line.split()[1])
            elif ':' in line:
                k, v = line.split(':', 1)
                headers[k.strip().lower()] = v.strip()
    body = open(dest, 'rb').read()
    html = body.decode('utf-8', 'replace')
    return {'url': url, 'ok': True, 'status': status, 'bytes': len(body),
            'sha1': hashlib.sha1(body).hexdigest()[:16],
            'site': bool(SITE_MARK.search(html)),
            'title': (TITLE.search(html).group(1).strip() if TITLE.search(html) else None),
            'headers': headers}


def main():
    os.makedirs(CACHE, exist_ok=True)
    inv = json.load(open(os.path.join(OUT, 'inventory.json'), encoding='utf-8'))
    items = inv['items']

    targets = []
    for it in items:
        link = it['link'] or ''
        path = re.sub(r'^https?://[^/]+', '', link) or '/'
        en = path
        zh = ('/zh' + path) if path != '/' else '/zh/'
        targets.append((it, 'en', en))
        targets.append((it, 'zh', zh))

    # The four archive/landing routes the navigation offers but no post type owns.
    for extra in ['/blog/', '/quality/', '/about/', '/contact/']:
        targets.append((None, 'route', extra))

    seen, rows = set(), []
    for it, loc, url in targets:
        if url in seen:
            continue
        seen.add(url)
        dest = os.path.join(CACHE, '%s.html' % slug(url))
        r = fetch(BASE + url, dest)
        r['locale'] = loc
        r['type'] = (it or {}).get('type', 'route')
        r['id'] = (it or {}).get('id')
        r['slug'] = (it or {}).get('slug')
        r['title_src'] = (it or {}).get('title')
        r['path'] = url
        rows.append(r)
        flag = 'ok ' if (r.get('ok') and r.get('site')) else '!! '
        print('%s%-46s %s %7s %s' % (flag, url, r.get('status'), r.get('bytes'),
                                     (r.get('title') or '')[:44]))
        sys.stdout.flush()
        time.sleep(SLEEP)

    with open(os.path.join(OUT, 'crawl.json'), 'w', encoding='utf-8') as fh:
        json.dump(rows, fh, ensure_ascii=False, indent=1)

    good = [r for r in rows if r.get('ok') and r.get('site')]
    bad = [r for r in rows if not (r.get('ok') and r.get('site'))]
    print('\n=== %d fetched, %d served the site, %d did not ===' %
          (len(rows), len(good), len(bad)))
    for r in bad:
        print('  !! %-44s status=%s site=%s err=%s' %
              (r['path'], r.get('status'), r.get('site'), r.get('err')))
    print('-> %s' % os.path.join(OUT, 'crawl.json'))


if __name__ == '__main__':
    main()

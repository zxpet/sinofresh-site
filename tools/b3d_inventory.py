#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch 3d step 1 -- the site's own opinion of what it publishes.

The survey needs a page list that is authoritative rather than remembered, and
the site can supply one: /wp-json/wp/v2/types names every public post type and
its rest_base, and each rest_base enumerates its own published items. That is
the same set WordPress would put in a sitemap, which is the definition we want
and is not available directly -- blog_public is 0 on this host, so the core
sitemap 404s on purpose.

Read-only throughout: GET on public REST routes, nothing else. Every request is
spaced by SLEEP seconds and every response is checked for the 401 page, which
arrives with status 200 and no site content if the credentials are dropped.
"""
import base64
import json
import os
import subprocess
import sys
import time
import urllib.parse

USER, PASS = 'sfdev', 'VkEws18Kl5V1qp3TpZ6s'
BASE = 'https://dev.zxpet.com'
AUTH = 'Basic ' + base64.b64encode(('%s:%s' % (USER, PASS)).encode()).decode()
SLEEP = 1.3
OUT = os.path.join('docs', 'site-survey-2026-09-24')
CACHE = os.path.join(OUT, 'cache')

TYPES = ['pages', 'posts']


def get(path, raw=False, timeout=60):
    url = path if path.startswith('http') else BASE + path
    p = subprocess.run(['curl', '-sS', '--max-time', str(timeout), '-u',
                        '%s:%s' % (USER, PASS), '-H', 'Accept: application/json',
                        '-w', '\n%{http_code}', url],
                       capture_output=True, text=True)
    body = p.stdout
    if p.returncode != 0:
        raise RuntimeError('curl failed on %s: %s' % (path, p.stderr.strip()))
    nl = body.rfind('\n')
    code, body = body[nl + 1:], body[:nl]
    if code != '200':
        return int(code), None, body
    return 200, (body if raw else json.loads(body)), body


def main():
    os.makedirs(CACHE, exist_ok=True)
    code, root, _ = get('/wp-json/')
    if code != 200:
        sys.exit('REST root returned %s' % code)
    site = {'name': root.get('name'), 'home': root.get('home'),
            'page_on_front': root.get('page_on_front'),
            'page_for_posts': root.get('page_for_posts'),
            'namespaces': root.get('namespaces')}
    print('site: %s  front=%s  posts=%s' % (site['name'], site['page_on_front'],
                                            site['page_for_posts']))
    print('namespaces: %s' % ', '.join(site['namespaces']))

    time.sleep(SLEEP)
    code, types, _ = get('/wp-json/wp/v2/types')
    public = {k: v for k, v in types.items()
              if v.get('rest_base') and not k.startswith('wp_')}
    print('\npublic post types:')
    for k, v in sorted(public.items()):
        print('  %-22s rest_base=%-16s hierarchical=%s' %
              (k, v.get('rest_base'), v.get('hierarchical')))

    items = []
    for key, v in sorted(public.items()):
        rb = v['rest_base']
        q = urllib.parse.urlencode({'per_page': 100, 'status': 'publish',
                                    '_fields': 'id,slug,link,title,type,parent',
                                    'orderby': 'id', 'order': 'asc'})
        time.sleep(SLEEP)
        code, rows, body = get('/wp-json/wp/v2/%s?%s' % (rb, q))
        if code != 200:
            print('  !! %s -> %s' % (rb, code))
            continue
        if not isinstance(rows, list):
            rows = [rows]
        for r in rows:
            items.append({'type': r.get('type') or key, 'id': r.get('id'),
                          'slug': r.get('slug'),
                          'link': r.get('link'),
                          'title': (r.get('title') or {}).get('rendered'),
                          'parent': r.get('parent')})
        print('  %-22s %3d published' % (rb, len(rows)))

    # A second page of each type, in case the catalogue is over 100.
    for key, v in sorted(public.items()):
        rb = v['rest_base']
        q = urllib.parse.urlencode({'per_page': 100, 'offset': 100, 'status': 'publish',
                                    '_fields': 'id,slug,link,title,type,parent'})
        time.sleep(SLEEP)
        code, rows, _ = get('/wp-json/wp/v2/%s?%s' % (rb, q))
        if code == 200 and isinstance(rows, list) and rows:
            print('  !! %s has more than 100 items (%d on page 2)' % (rb, len(rows)))
            for r in rows:
                items.append({'type': r.get('type') or key, 'id': r.get('id'),
                              'slug': r.get('slug'), 'link': r.get('link'),
                              'title': (r.get('title') or {}).get('rendered'),
                              'parent': r.get('parent')})

    seen, uniq = set(), []
    for it in items:
        k = (it['type'], it['id'])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(it)
    uniq.sort(key=lambda x: (x['type'], x['id']))

    by_type = {}
    for it in uniq:
        by_type.setdefault(it['type'], []).append(it)
    print('\n=== inventory: %d published objects ===' % len(uniq))
    for t, rows in sorted(by_type.items()):
        print('  %-22s %3d' % (t, len(rows)))

    with open(os.path.join(OUT, 'inventory.json'), 'w', encoding='utf-8') as fh:
        json.dump({'site': site, 'types': public, 'items': uniq}, fh,
                  ensure_ascii=False, indent=1)
    print('\n-> %s' % os.path.join(OUT, 'inventory.json'))


if __name__ == '__main__':
    main()

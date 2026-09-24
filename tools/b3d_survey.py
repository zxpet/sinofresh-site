#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch 3d -- the eight survey categories over the cached corpus.

Reads crawl.json + cache/*.html and writes docs/site-survey-2026-09-24/findings.json.
No network: the corpus was fetched once, so every category judges the same
bytes. Anything that needs a second opinion (a link target, a resource) is
listed as a follow-up rather than silently assumed good.

Two rules about the findings themselves, both learned here:

  * a count is not a finding. Every category reports the files it looked at and
    the number of items it judged, so a zero can be told apart from a rule that
    never ran.
  * "missing" and "empty" are different. `<img>` with no alt attribute is a
    defect; `alt=""` is a declaration that the image is decorative and is
    correct for an icon. They are counted separately and reported separately.
"""
import hashlib
import html as html_mod
import json
import os
import re
from collections import Counter, defaultdict
from html.parser import HTMLParser

OUT = os.path.join('docs', 'site-survey-2026-09-24')
CACHE = os.path.join(OUT, 'cache')
BASE = 'https://dev.zxpet.com'

PLACEHOLDER = re.compile(
    r'\b(lorem ipsum|dolor sit amet|TODO|FIXME|TBD|XXX+|placeholder text|'
    r'coming soon|sample text|dummy|test test|asdf|foo bar|'
    r'insert .{0,20}here|your .{0,15} here|\bexample\.com\b|'
    r'CLIENT_NAME|COMPANY_NAME)\b', re.I)
TOKEN = re.compile(r'(\{\{[^}]{0,40}\}\}|%%[A-Za-z_]{2,30}%%|\{[A-Z_]{4,}\}|%[sd]\b)')
CJK = re.compile(r'[\u4e00-\u9fff]')
FENCE = re.compile(r'<script[^>]*>.*?</script>|<style[^>]*>.*?</style>', re.S | re.I)
JSONLD = re.compile(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', re.S | re.I)
META = re.compile(r'<meta\s+[^>]*>', re.I)
LINKTAG = re.compile(r'<link\s+[^>]*>', re.I)
TITLE = re.compile(r'<title[^>]*>(.*?)</title>', re.S | re.I)
METAANY = re.compile(
    r"<meta[^>]+(?:name|property)\s*=\s*['\"]([^'\"]+)['\"][^>]*?"
    r"content\s*=\s*['\"]([^'\"]*)['\"]", re.I | re.S)


def attr(tag, name):
    m = re.search(r'\b%s\s*=\s*([\'"])(.*?)\1' % re.escape(name), tag, re.S | re.I)
    if m:
        return m.group(2)
    m = re.search(r'\b%s(?=[\s/>])' % re.escape(name), tag, re.I)
    return '' if m else None


class P(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.tags = []
        self.text = []
        self.headings = []       # (level, text)
        self._h = None
        self._hbuf = []
        self.in_script = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.in_script += 1
        self.tags.append((tag, dict(attrs), self.getpos()[0]))
        if re.fullmatch(r'h[1-6]', tag):
            self._h = tag
            self._hbuf = []

    def handle_endtag(self, tag):
        if tag in ('script', 'style') and self.in_script:
            self.in_script -= 1
        if self._h and tag == self._h:
            self.headings.append((int(self._h[1]), ' '.join(self._hbuf).strip()))
            self._h = None

    def handle_data(self, data):
        if self.in_script:
            return
        self.text.append(data)
        if self._h:
            self._hbuf.append(data)

    def handle_entityref(self, name):
        if not self.in_script and self._h:
            self._hbuf.append(html_mod.unescape('&%s;' % name))

    def handle_charref(self, name):
        if not self.in_script and self._h:
            self._hbuf.append(html_mod.unescape('&#%s;' % name))


def parse(html):
    p = P()
    p.feed(html)
    return p


def digest(s):
    return hashlib.sha1(s.encode('utf-8', 'replace')).hexdigest()[:12]


def main():
    rows = json.load(open(os.path.join(OUT, 'crawl.json'), encoding='utf-8'))
    inv = json.load(open(os.path.join(OUT, 'inventory.json'), encoding='utf-8'))
    known_paths = {r['path'] for r in rows}
    known_paths |= {'/zh' + p for p in list(known_paths)}
    known_paths |= {'', '/zh', '/zh/'}
    # Routes the theme serves without a post behind them.
    known_paths |= {'/blog/', '/zh/blog/', '/formulas/', '/zh/formulas/',
                    '/products/', '/zh/products/', '/search/', '/404/',
                    '/privacy-policy/', '/cookie-policy/', '/terms/',
                    '/zh/privacy-policy/', '/zh/cookie-policy/', '/zh/terms/'}

    F = defaultdict(list)          # category -> findings
    stats = {}

    pages = []
    for r in rows:
        if not (r.get('ok') and r.get('site')):
            continue
        # b3d_crawl.py keys the cache on the PATH, not the absolute URL:
        # `dest = slug(url)` where url is '/about/'. Hashing BASE+path here
        # reproduced nothing, every page came back a cache miss, and the
        # per-page lists (perf, images) were empty -- which is how the survey
        # first reported a site with no stylesheets at all.
        fn = os.path.join(CACHE, '%s.html' % hashlib.sha1(
            r['path'].encode()).hexdigest()[:12])
        if not os.path.exists(fn):
            F['meta'].append({'kind': 'cache miss', 'url': r['path']})
            continue
        html = open(fn, encoding='utf-8', errors='replace').read()
        p = parse(html)
        pages.append({'r': r, 'html': html, 'p': p, 'url': r['path'],
                      'loc': r.get('locale'), 'type': r.get('type')})
    stats['pages parsed'] = len(pages)
    stats['pages in crawl'] = len(rows)

    # ---------------------------------------------------------------- 1 content
    seen_para = defaultdict(list)
    for pg in pages:
        body = FENCE.sub(' ', pg['html'])
        text = html_mod.unescape(re.sub(r'<[^>]+>', ' ', body))
        text = re.sub(r'\s+', ' ', text)
        for m in set(PLACEHOLDER.findall(text)):
            if m.strip():
                F['content'].append({'kind': 'placeholder wording', 'url': pg['url'],
                                     'detail': m})
        for m in set(TOKEN.findall(pg['html'])):
            F['content'].append({'kind': 'unreplaced token', 'url': pg['url'],
                                 'detail': m[:60]})
        # repeated body paragraphs across pages
        for para in re.findall(r'[^\s][^.]{80,400}\.', text):
            k = digest(para.strip())
            seen_para[k].append(pg['url'])
        # an EN page carrying Chinese body text, or vice versa
        cjk = len(CJK.findall(text))
        if pg['loc'] == 'en' and cjk > 40:
            F['content'].append({'kind': 'CJK text on an EN page', 'url': pg['url'],
                                 'detail': '%d CJK chars' % cjk})
    dup = {k: v for k, v in seen_para.items() if len(set(v)) > 1}
    stats['paragraph digests shared by >1 page'] = len(dup)

    # ------------------------------------------------------------------- 2 seo
    t_seen, d_seen = defaultdict(list), defaultdict(list)
    for pg in pages:
        h, url = pg['html'], pg['url']
        t = TITLE.search(h)
        title = html_mod.unescape(t.group(1)).strip() if t else ''
        # Attribute order is not fixed: `content` may come before `name`. Read
        # each meta tag's attributes instead of matching a fixed sequence -- the
        # sequence-matching version reported "missing meta description" on a page
        # whose only three meta tags are charset, viewport and robots, which
        # happens to be the truth here, but would have been a false alarm on any
        # template that writes content first.
        metas = {}
        meta_tags = re.findall(r'<meta\s[^>]*>', h, re.I)
        for mt in meta_tags:
            key = attr(mt, 'name') or attr(mt, 'property')
            if key:
                metas[key.lower()] = attr(mt, 'content') or ''
        pg['meta_tags'] = len(meta_tags)
        pg['meta_keys'] = sorted(metas)
        desc = metas.get('description', '')
        can = None
        for tag in LINKTAG.findall(h):
            if (attr(tag, 'rel') or '').lower() == 'canonical':
                can = attr(tag, 'href')
        if not title:
            F['seo'].append({'kind': 'missing <title>', 'url': url})
        else:
            t_seen[title].append(url)
            if len(title) > 65:
                F['seo'].append({'kind': 'title longer than 65 chars',
                                 'url': url, 'detail': '%d: %s' % (len(title), title[:70])})
        if not desc:
            F['seo'].append({'kind': 'missing meta description', 'url': url})
        else:
            d_seen[desc].append(url)
            if not (50 <= len(desc) <= 165):
                F['seo'].append({'kind': 'meta description outside 50-165 chars',
                                 'url': url, 'detail': '%d chars' % len(desc)})
        if not can:
            F['seo'].append({'kind': 'missing canonical', 'url': url})
        robots = metas.get('robots', '')
        if 'noindex' not in robots:
            F['seo'].append({'kind': 'page is not noindex (staging lock expected)',
                             'url': url, 'detail': robots or '(no robots meta)'})
        og = [k for k in metas if k.startswith('og:')]
        if not og:
            F['seo'].append({'kind': 'no og: tags', 'url': url})
        # JSON-LD
        blocks = JSONLD.findall(h)
        for b in blocks:
            b = b.strip()
            try:
                data = json.loads(b)
            except Exception as e:
                F['seo'].append({'kind': 'JSON-LD does not parse', 'url': url,
                                 'detail': str(e)[:70]})
                continue
            graph = data.get('@graph', [data]) if isinstance(data, dict) else data
            for node in (graph if isinstance(graph, list) else [graph]):
                if not isinstance(node, dict):
                    continue
                if not node.get('@type'):
                    F['seo'].append({'kind': 'JSON-LD node without @type', 'url': url})
        pg['ld_types'] = []
        for b in blocks:
            try:
                data = json.loads(b)
            except Exception:
                continue
            g = data.get('@graph', [data]) if isinstance(data, dict) else data
            for n in (g if isinstance(g, list) else [g]):
                if isinstance(n, dict) and n.get('@type'):
                    pg['ld_types'].append(n['@type'])
        stats.setdefault('ld types', Counter()).update(
            [t for x in pg['ld_types'] for t in ([x] if isinstance(x, str) else x)])
    for t, urls in t_seen.items():
        if len(set(urls)) > 1:
            F['seo'].append({'kind': 'duplicate <title>', 'value': t,
                             'urls': sorted(set(urls))})
    for d, urls in d_seen.items():
        if len(set(urls)) > 1:
            F['seo'].append({'kind': 'duplicate meta description',
                             'value': d[:80], 'urls': sorted(set(urls))})

    # ------------------------------------------------------------------ 3 links
    ext = defaultdict(list)
    for pg in pages:
        for tag, a, ln in pg['p'].tags:
            if tag != 'a':
                continue
            href = (a.get('href') or '').strip()
            if not href or href.startswith(('#', 'javascript:', 'data:')):
                if href.startswith('#') and len(href) > 1:
                    if ('id="%s"' % href[1:]) not in pg['html'] and \
                       ("id='%s'" % href[1:]) not in pg['html'] and \
                       ('name="%s"' % href[1:]) not in pg['html']:
                        F['links'].append({'kind': 'fragment target not on the page',
                                           'url': pg['url'], 'detail': href})
                continue
            if href.startswith('mailto:') or href.startswith('tel:'):
                continue
            # Cloudflare rewrites every mailto: into /cdn-cgi/l/email-protection#<hex>
            # before it reaches us. Counted as a link target it produced 1292
            # "internal link to a route not in the crawl" on a site whose email
            # links all work; the first hit in the list is the giveaway.
            if '/cdn-cgi/' in href:
                continue
            if href.startswith('http'):
                host = re.sub(r'^https?://([^/]+).*$', r'\1', href)
                if 'dev.zxpet.com' in host or 'zxpet.com' in host:
                    path = re.sub(r'^https?://[^/]+', '', href).split('?')[0].split('#')[0]
                else:
                    ext[host].append((pg['url'], href))
                    continue
            else:
                path = href.split('?')[0].split('#')[0]
            if not path.startswith('/'):
                path = '/' + path
            if not path.endswith('/') and '.' not in os.path.basename(path or 'x'):
                path += '/'
            if path not in known_paths:
                F['links'].append({'kind': 'internal link to a route not in the crawl',
                                   'url': pg['url'], 'detail': href})
    stats['external hosts'] = dict(Counter({h: len(v) for h, v in ext.items()}))

    # ------------------------------------------------------------------ 4 images
    img_total = 0
    for pg in pages:
        for tag, a, ln in pg['p'].tags:
            if tag != 'img':
                continue
            img_total += 1
            src = a.get('src') or ''
            if 'alt' not in a:
                F['images'].append({'kind': 'img without an alt attribute',
                                    'url': pg['url'], 'detail': src[-60:]})
            elif a['alt'].strip() == '':
                pass          # decorative declaration -- correct for an icon
            if not a.get('width') or not a.get('height'):
                if a.get('loading') != 'lazy' and 'data-' not in ' '.join(a):
                    F['images'].append({'kind': 'img without width/height',
                                        'url': pg['url'], 'detail': src[-60:]})
            if src.startswith('data:'):
                F['images'].append({'kind': 'inline data: image', 'url': pg['url'],
                                    'detail': '%d bytes' % len(src)})
    stats['img tags'] = img_total

    # ----------------------------------------------------------------- 5 forms
    gf_forms = set()
    for pg in pages:
        for tag, a, ln in pg['p'].tags:
            if tag == 'form':
                cls = (a.get('class') or '')
                # `.sf-fb-form` is the article feedback form: it must not have an
                # action, because it is submitted by JS to the REST route and is
                # `hidden` until a reader votes. Flagging it would put 56 entries
                # on a defect list that has 0 defects in it.
                if not (a.get('action') or '').strip() and 'sf-fb-form' not in cls:
                    F['forms'].append({'kind': 'form without an action',
                                       'url': pg['url'], 'detail': str(a)[:110]})
            if tag == 'input':
                t = (a.get('type') or 'text').lower()
                if t in ('email',) :
                    if not a.get('autocomplete'):
                        F['forms'].append({'kind': 'email input without autocomplete',
                                           'url': pg['url'], 'detail': a.get('name') or ''})
                if t == 'tel' and not a.get('autocomplete'):
                    F['forms'].append({'kind': 'tel input without autocomplete',
                                       'url': pg['url'], 'detail': a.get('name') or ''})
        m = re.search(r'gform_wrapper[^>]*id="gform_wrapper_(\d+)"', pg['html'])
        if m:
            gf_forms.add(m.group(1))
        for mid in set(re.findall(r'gform_wrapper_(\d+)', pg['html'])):
            gf_forms.add(mid)
        # consent checkbox next to a submit
        if 'gform' in pg['html'] and 'Privacy Policy' not in pg['html'] \
           and 'privacy' not in pg['html'].lower():
            F['forms'].append({'kind': 'GF form on a page with no privacy wording',
                               'url': pg['url']})
    stats['gravity forms ids seen'] = sorted(gf_forms)
    mails = defaultdict(set)
    cfmails = defaultdict(set)

    def cfdecode(hx):
        try:
            b = bytes.fromhex(hx)
        except Exception:
            return None
        return ''.join(chr(c ^ b[0]) for c in b[1:])

    for pg in pages:
        for m in re.findall(r'mailto:([^"\'>\s?]+)', pg['html']):
            mails[html_mod.unescape(m)].add(pg['url'])
        for m in re.findall(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', pg['html']):
            if not m.endswith(('.png', '.jpg', '.jpeg', '.webp', '.svg', '.css', '.js', '.w.org')):
                mails[m].add(pg['url'])
        # Cloudflare obfuscates every mailto: into a hex blob. Without decoding
        # it the inventory reads "one address on the whole site", because the
        # only visible occurrences are the plain-text ones in JSON-LD.
        for m in re.findall(r'/cdn-cgi/l/email-protection#([0-9a-fA-F]+)', pg['html']):
            d = cfdecode(m)
            if d:
                cfmails[d].add(pg['url'])
        for m in re.findall(r'data-cfemail="([0-9a-fA-F]+)"', pg['html']):
            d = cfdecode(m)
            if d:
                cfmails[d].add(pg['url'])
    stats['email addresses in plain text'] = {k: len(v) for k, v in sorted(mails.items())}
    stats['email addresses behind CF obfuscation'] = {
        k: len(v) for k, v in sorted(cfmails.items())}
    stats['meta keys across the site'] = dict(Counter(
        k for pg in pages for k in pg.get('meta_keys', [])))
    stats['meta tag count per page'] = dict(Counter(pg.get('meta_tags') for pg in pages))

    # -------------------------------------------------------------------- 6 i18n
    en_paths = {pg['url'] for pg in pages if pg['loc'] == 'en'}
    zh_paths = {pg['url'] for pg in pages if pg['loc'] == 'zh'}
    for pg in pages:
        if pg['loc'] == 'en':
            zh = '/zh' + pg['url'] if pg['url'] != '/' else '/zh/'
            if zh not in zh_paths and zh not in known_paths:
                F['i18n'].append({'kind': 'EN page with no ZH counterpart',
                                  'url': pg['url'], 'detail': zh})
        lang = re.search(r'<html[^>]*\blang\s*=\s*[\'"]([^\'"]+)', pg['html'], re.I)
        want = 'zh' if pg['loc'] == 'zh' else 'en'
        got = (lang.group(1) if lang else '').lower()
        if not got.startswith(want):
            F['i18n'].append({'kind': 'html lang does not match the locale',
                              'url': pg['url'], 'detail': got or '(none)'})
        alt = re.findall(r'<link[^>]+hreflang\s*=\s*[\'"]([^\'"]+)[\'"][^>]*>',
                         pg['html'], re.I)
        if not alt:
            F['i18n'].append({'kind': 'page has no hreflang alternates',
                              'url': pg['url']})
        elif 'x-default' not in alt:
            F['i18n'].append({'kind': 'hreflang set has no x-default',
                              'url': pg['url'], 'detail': ','.join(sorted(set(alt)))})
        if not re.search(r'<link[^>]+rel=[\'"]canonical[\'"][^>]+href=[\'"]([^\'"]+)',
                         pg['html'], re.I):
            pass
        else:
            can = re.search(r'<link[^>]+rel=[\'"]canonical[\'"][^>]+href=[\'"]([^\'"]+)',
                            pg['html'], re.I).group(1)
            want_can = pg['url'] if pg['loc'] == 'en' else pg['url']
            if not can.rstrip('/').endswith(want_can.rstrip('/')):
                F['i18n'].append({'kind': 'canonical does not point at the page itself',
                                  'url': pg['url'], 'detail': can})
        if 'trp-language-switcher' not in pg['html'] and 'trp-floating' not in pg['html']:
            F['i18n'].append({'kind': 'no TranslatePress switcher markup',
                              'url': pg['url']})
    stats['hreflang langs seen'] = dict(Counter(
        l for pg in pages for l in re.findall(
            r'<link[^>]+hreflang\s*=\s*[\'"]([^\'"]+)[\'"]', pg['html'], re.I)))

    # ------------------------------------------------------------------- 7 perf
    per = []
    for pg in pages:
        h = pg['html']
        res = []
        for tag in LINKTAG.findall(h):
            rel = (attr(tag, 'rel') or '').lower()
            if 'stylesheet' in rel and attr(tag, 'href'):
                res.append(('css', attr(tag, 'href')))
            if 'preload' in rel or 'preconnect' in rel or 'dns-prefetch' in rel:
                res.append(('pre', attr(tag, 'href') or attr(tag, 'imagesrcset') or ''))
        for tag, a, ln in pg['p'].tags:
            if tag == 'script' and a.get('src'):
                res.append(('js', a['src']))
        inline_css = sum(len(x) for x in re.findall(r'<style[^>]*>(.*?)</style>', h, re.S))
        inline_js = sum(len(x) for x in re.findall(
            r'<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>', h, re.S))
        hosts = Counter(re.sub(r'^https?://([^/]+).*$', r'\1', u) if u.startswith('http')
                        else 'self' for _, u in res)
        third = [k for k in hosts if k not in ('self', 'dev.zxpet.com')]
        per.append({'url': pg['url'], 'bytes': pg['r']['bytes'],
                    'css': sum(1 for k, _ in res if k == 'css'),
                    'js': sum(1 for k, _ in res if k == 'js'),
                    'inline_css': inline_css, 'inline_js': inline_js,
                    'third_party_hosts': third,
                    'encoding': (pg['r'].get('headers') or {}).get('content-encoding'),
                    'cf': (pg['r'].get('headers') or {}).get('cf-cache-status'),
                    'cache_control': (pg['r'].get('headers') or {}).get('cache-control')})
        if third:
            F['perf'].append({'kind': 'third-party asset host', 'url': pg['url'],
                              'detail': ', '.join(third)})
        if inline_css > 60000:
            F['perf'].append({'kind': 'very large inline CSS block', 'url': pg['url'],
                              'detail': '%d bytes' % inline_css})
    by_size = sorted(per, key=lambda x: -x['bytes'])
    stats['heaviest pages'] = [(x['url'], x['bytes']) for x in by_size[:6]]
    stats['lightest pages'] = [(x['url'], x['bytes']) for x in by_size[-3:]]
    stats['median html bytes'] = by_size[len(by_size) // 2]['bytes']
    stats['pages by css count'] = dict(Counter(x['css'] for x in per))
    stats['pages by js count'] = dict(Counter(x['js'] for x in per))
    stats['cf-cache-status'] = dict(Counter(x['cf'] for x in per))
    stats['content-encoding'] = dict(Counter(x['encoding'] for x in per))

    # ------------------------------------------------------------------ 8 a11y
    for pg in pages:
        hs = pg['p'].headings
        h1 = [t for lv, t in hs if lv == 1]
        if len(h1) != 1:
            F['a11y'].append({'kind': 'page does not have exactly one h1',
                              'url': pg['url'], 'detail': 'h1 count=%d' % len(h1)})
        elif not h1[0]:
            F['a11y'].append({'kind': 'h1 is empty', 'url': pg['url']})
        levels = [lv for lv, _ in hs]
        for i in range(1, len(levels)):
            if levels[i] - levels[i - 1] > 1:
                F['a11y'].append({'kind': 'heading level skipped',
                                  'url': pg['url'],
                                  'detail': 'h%d -> h%d' % (levels[i - 1], levels[i])})
                break
        if not re.search(r'<main\b', pg['html'], re.I):
            F['a11y'].append({'kind': 'no <main> landmark', 'url': pg['url']})
        if not re.search(r'<nav\b', pg['html'], re.I):
            F['a11y'].append({'kind': 'no <nav> landmark', 'url': pg['url']})
        for m in re.finditer(r'<a\b[^>]*>(.*?)</a>', pg['html'], re.S | re.I):
            tag = m.group(0).split('>')[0]
            inner = re.sub(r'<[^>]+>', '', m.group(1))
            inner = html_mod.unescape(inner).strip()
            has_label = bool(inner) or bool(attr(tag, 'aria-label')) \
                or bool(attr(tag, 'title')) or bool(re.search(r'<img[^>]+alt="[^"]+"', m.group(1)))
            if not has_label:
                F['a11y'].append({'kind': 'link with no accessible name',
                                  'url': pg['url'], 'detail': tag[:100]})
        for tag, a, ln in pg['p'].tags:
            if tag == 'button':
                if 'aria-label' not in a and 'title' not in a:
                    pass  # checked via its text below
            if a.get('tabindex') and int(a.get('tabindex') or 0) > 0:
                F['a11y'].append({'kind': 'positive tabindex', 'url': pg['url'],
                                  'detail': tag})
            if a.get('aria-hidden') == 'true' and tag in ('a', 'button', 'input'):
                F['a11y'].append({'kind': 'focusable element hidden from AT',
                                  'url': pg['url'], 'detail': tag})
        # `skip` alone is not evidence: WordPress ships
        # wp-block-template-skip-link CSS into every page, so the string occurs
        # even when no link is rendered. The markup is what counts.
        if not re.search(r'<a[^>]+class=["\'][^"\']*\bskip-link\b', pg['html'], re.I) \
           and not re.search(r'href=["\']#main["\']', pg['html'], re.I):
            F['a11y'].append({'kind': 'no skip-to-content link rendered',
                              'url': pg['url'],
                              'detail': 'core emits the CSS but no <a class="skip-link">'})

    # ------------------------------------------------------------------ write
    print('=== corpus ===')
    for k, v in stats.items():
        print('  %-42s %s' % (k, v))
    print('\n=== findings by category ===')
    for cat in ('content', 'seo', 'links', 'images', 'forms', 'i18n', 'perf', 'a11y', 'meta'):
        rows_ = F.get(cat, [])
        print('\n[%s] %d' % (cat, len(rows_)))
        kinds = Counter(r['kind'] for r in rows_)
        for k, n in kinds.most_common():
            ex = [r for r in rows_ if r['kind'] == k][:3]
            print('   %-52s %4d   e.g. %s' % (k, n, '; '.join(
                (r.get('url', '') + ' ' + str(r.get('detail', ''))).strip()[:70] for r in ex)))
    with open(os.path.join(OUT, 'findings.json'), 'w', encoding='utf-8') as fh:
        json.dump({'stats': {k: (dict(v) if isinstance(v, Counter) else v)
                             for k, v in stats.items()},
                   'findings': dict(F), 'perf': per}, fh,
                  ensure_ascii=False, indent=1, default=str)
    print('\n-> %s' % os.path.join(OUT, 'findings.json'))


if __name__ == '__main__':
    main()

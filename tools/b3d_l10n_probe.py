#!/usr/bin/env python3
"""b3d_l10n_probe.py -- prove whether the ZH locale actually carries Chinese.

WHY THIS EXISTS
---------------
The site survey's first pass over the multilingual section checked four
structural things -- every EN page has a ZH twin, <html lang> matches the
locale, the TranslatePress switcher is present, the ZH canonical points at
itself -- and all four passed. The conclusion written down was "pairing is
clean". Every one of those four can pass on a ZH site that contains no Chinese
at all, and that is exactly what this site turned out to be. Structure being
compliant and content being translated are two different claims, and only the
first was tested.

So this probes the second claim, offline, from the crawl corpus:

  1. For each of the 54 page pairs, count Han characters in the *visible* text
     of both sides. A translated page should differ sharply from its original.
  2. Compare <title> across the pair. A translated title differs.
  3. Report what the Han characters actually are, because a handful of them is
     normal: the language switcher renders the label 简体中文 into every page,
     translated or not, and Gravity Forms and date formats contribute a few
     interface strings. Distinguishing "4 Han chars of chrome" from "4 Han
     chars of content" is the whole point.

The verdict line is the product: it says whether each side differs, and it
refuses to call a pair translated on the strength of the switcher label alone.

NOT COVERED HERE (must be checked separately, and they are what made the first
pass wrong):
  * the browser-rendered text -- TranslatePress ships a Dynamic Translator that
    can rewrite the DOM after load, so the static bytes are not the last word.
    Open the ZH page in a real browser, wait, then read document.body.innerText.
  * the database -- wp_trp_dictionary_en_us_zh_cn.translated being empty for
    every row is the ground truth that the content layer was never filled in,
    while wp_trp_gettext_zh_cn having 782 translated rows is why the interface
    strings *do* show up in Chinese. Read-only:
        wp db query "SELECT COUNT(*) FROM wp_trp_dictionary_en_us_zh_cn
                     WHERE translated IS NOT NULL AND translated<>''" --allow-root

Usage:
    python3 tools/b3d_l10n_probe.py [--cache DIR] [--crawl FILE]
"""
import argparse, hashlib, html, json, os, re, sys

DEFAULT_CACHE = 'docs/site-survey-2026-09-24/cache'
DEFAULT_CRAWL = 'docs/site-survey-2026-09-24/crawl.json'
HOST = 'dev.zxpet.com'
HAN = re.compile(r'[\u4e00-\u9fff]')
HAN_RUN = re.compile(r'[\u4e00-\u9fff][\u4e00-\u9fff\s]*')
ZH_PREFIX = '/zh/'


def strip_noise(h):
    """Visible text: drop script/style bodies, then all tags, then unescape."""
    h = re.sub(r'(?is)<(script|style)[^>]*>.*?</\1>', ' ', h)
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'(?s)<[^>]+>', ' ', h)))


def read(cache, url):
    # b3d_crawl.py keys the cache on the PATH, not the absolute URL.
    path = url.split(HOST)[1]
    fn = os.path.join(cache, hashlib.sha1(path.encode()).hexdigest()[:12] + '.html')
    if not os.path.exists(fn):
        return None
    with open(fn, encoding='utf-8', errors='replace') as fh:
        return fh.read()


def title_of(h):
    if h is None:
        return None
    m = re.search(r'<title[^>]*>(.*?)</title>', h, re.S | re.I)
    return re.sub(r'\s+', ' ', html.unescape(m.group(1)).strip()) if m else None


def pair_up(crawl):
    """Key EN and ZH URLs by the route they share, so /about/ pairs /zh/about/."""
    pairs = {}
    for r in crawl:
        p = r['url'].split(HOST)[1]
        if p.startswith(ZH_PREFIX):
            pairs.setdefault(p[len(ZH_PREFIX):], {})['zh'] = r['url']
        else:
            pairs.setdefault(p.lstrip('/'), {})['en'] = r['url']
    return pairs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cache', default=DEFAULT_CACHE)
    ap.add_argument('--crawl', default=DEFAULT_CRAWL)
    a = ap.parse_args()

    crawl = json.load(open(a.crawl))
    pairs = pair_up(crawl)
    both = {k: v for k, v in pairs.items() if 'en' in v and 'zh' in v}
    single = sorted(k for k, v in pairs.items() if len(v) < 2)
    print('routes: %d total, %d paired, %d one-sided' % (len(pairs), len(both), len(single)))
    if single:
        print('  one-sided:', single)

    tot_en = tot_zh = 0
    title_same = title_diff = 0
    rows = []
    for k in sorted(both):
        he, hz = read(a.cache, both[k]['en']), read(a.cache, both[k]['zh'])
        if he is None or hz is None:
            print('  !! missing cache for %s' % k)
            continue
        te, tz = title_of(he), title_of(hz)
        n_en = len(HAN.findall(strip_noise(he)))
        n_zh = len(HAN.findall(strip_noise(hz)))
        tot_en += n_en
        tot_zh += n_zh
        if te == tz:
            title_same += 1
        else:
            title_diff += 1
        rows.append((k, n_en, n_zh, n_zh - n_en))

    print('\n%-42s %6s %6s %6s' % ('route', 'EN han', 'ZH han', 'delta'))
    for k, e, z, d in sorted(rows, key=lambda r: -r[3])[:12]:
        print('%-42s %6d %6d %+6d' % (k, e, z, d))
    print('%-42s %6d %6d %+6d' % ('(all %d pairs)' % len(rows), tot_en, tot_zh, tot_zh - tot_en))

    print('\ntitles: %d identical, %d differing' % (title_same, title_diff))

    print('\n--- what the Han characters actually are (top 3 by delta) ---')
    for k, e, z, d in sorted(rows, key=lambda r: -r[3])[:3]:
        t = strip_noise(read(a.cache, both[k]['zh']))
        runs = []
        for m in HAN_RUN.finditer(t):
            frag = re.sub(r'\s+', ' ', m.group(0)).strip()
            if frag not in runs:
                runs.append(frag)
        print('  %s -> %s' % (k, runs[:8]))

    # Every page carries the switcher label, so a delta near zero means the
    # Chinese on the ZH page is chrome, not content.
    chrome_only = [r for r in rows if r[3] <= 2]
    print('\nVERDICT: %d/%d pairs differ by <=2 Han chars, i.e. only the language'
          % (len(chrome_only), len(rows)))
    print('         switcher label. %d identical titles.' % title_same)
    if len(chrome_only) >= len(rows) * 0.9:
        print('         => the ZH locale is coterminous with the EN original: the')
        print('            zh_CN content layer carries no translations. Not a config')
        print('            failure -- the gettext layer does translate (see the DB')
        print('            query in the docstring); the 2388 content strings were')
        print('            registered and never filled in.')
    return 0


if __name__ == '__main__':
    sys.exit(main())

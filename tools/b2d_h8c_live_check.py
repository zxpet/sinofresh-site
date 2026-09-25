#!/usr/bin/env python3
"""Batch H8c — service-side acceptance of what the dev pull turns on.

Six of these were written by batches H8a and H8b and have only ever been served
from the preflight layer; the pull is what puts them on the install the site
actually answers from. Every check is anchored on a byte that is on the wire —
never on a file in the working tree, which would pass whether or not the pull
happened.

Three of them need saying out loud, because a laxer version would pass on the
unfixed site:

  * Sticky. `position: sticky` sitting in a stylesheet proves nothing; the rule
    can be there and dead (the site shipped exactly that class of defect in
    H7b, where a phone step lived above the rule it meant to override). So the
    check reads the rule AND the element it applies to, and the browser pass is
    what proves it engages.

  * Shelf life. The record's own value and the legacy specs text DISAGREE on
    one live page, which makes it the discriminating case:
    /formulas/joint-support-soft-chews/ prints "24 months" in its specs sheet
    while every copy of the specs themselves says "18 months shelf life", so
    before batch H8a that row read 18. A check that only asked "does some
    number print" is green in both states; this one goes green only when the
    field beats the specs text.

  * Names. An assertion that greps the page for a title string is satisfied by
    <title> and og:title — the h1 could be missing entirely and it would still
    pass. WordPress decodes the entities in those two places and leaves them
    encoded in the body, so a literal-em-dash needle silently tests the head.
    Every name below is therefore read out of the element that is supposed to
    carry it, entity-decoded on both sides.

Run it against the preflight layer to see the after-state before the pull, and
without the header to see what dev actually serves.
"""

import argparse
import base64
import html as html_mod
import json
import re
import ssl
import sys
import urllib.error
import urllib.request

BASE = 'https://dev.zxpet.com'
USER, PASS = 'sfdev', 'VkEws18Kl5V1qp3TpZ6s'

# The two pages the dosage-form split is read from: one whose pool has eight
# real shapes, one whose pool has none of them.
CHEWS = '/formulas/joint-support-soft-chews/'
POWDER = '/formulas/probiotic-powder/'

# (path, h1 as the element must read, the breadcrumb's own crumb)
SUBPAGES = [
    ('/services/oem/', 'OEM Manufacturing \u2014 You Bring the Formula',
     'OEM Manufacturing'),
    ('/services/odm/', 'ODM Development \u2014 We Develop From Your Idea',
     'ODM Development'),
    ('/services/contract-manufacturing/',
     'Contract Manufacturing \u2014 You Own the IP', 'Contract Manufacturing'),
    ('/services/private-label/',
     'Private Label \u2014 Pick From Our Proven Formulas', 'Private Label'),
]
# (href, the card heading's text) — in the order the overview prints them.
CARDS = [('/services/oem/', 'OEM \u2014 You Bring the Formula'),
         ('/services/odm/', 'ODM \u2014 We Develop From Your Idea'),
         ('/services/contract-manufacturing/',
          'Contract Manufacturing \u2014 You Own the IP'),
         ('/services/private-label/',
          'Private Label \u2014 Pick From Our Proven Formulas')]
# The overview's own headings, all eight, named rather than counted: a bare
# count cannot tell a renamed band from a deleted one. Batch 3b added the two
# capability bands in the middle, so this list is a batch-3b artefact as much
# as an H8c one.
OVERVIEW_H2 = ['OEM or ODM \u2014 Choose Your Path',
               'Key Facts: MOQ, Lead Time, Payment & Trade Terms',
               'What We Handle \u2014 R&D, Compliance & Export Documentation',
               'Custom Formulation Capability',
               'How We Work \u2014 From Inquiry to Delivery in 5 Steps',
               'Manufacturing Capability',
               'Frequently Asked Questions',
               'Request a Sample']

# Bytes that only exist after the pull — a rule the batch wrote, or the pool it
# moved, quoted exactly as the stylesheet spells it.
STICKY_RULE = ('\t.sf-fdetail2__media {\n\t\tposition: sticky;\n\t\ttop: 100px;\n'
               '\t\talign-self: start;\n\t}')
FOLD_BASE = '.sf-fdetail-config__fold {\n\tdisplay: none;\n}'
FOLD_PHONE = ('.sf-fdetail-config--js .sf-fdetail-config__list.sf-config-folded\n'
              '\t\t.sf-fdetail-config__group:nth-child(n + 5) {\n\t\tdisplay: none;')
THUMBS_SCROLL = ('.sf-gallery__thumbs {\n\t\tjustify-content: flex-start;\n'
                 '\t\toverflow-x: auto;\n\t\tscroll-snap-type: x mandatory;')
CARD_OVERLAY = (".sf-card__title-link::after {\n\tcontent: '';\n\tposition: absolute;\n"
                "\tinset: 0;")
SHELF_POOL = ['12 months', '18 months', '24 months', '36 months']


def fetch(path, preflight, want_body=True):
    """(status, body, final_url). Never raises on an HTTP status."""
    url = path if path.startswith('http') else BASE + path
    req = urllib.request.Request(url)
    req.add_header('Authorization',
                   'Basic ' + base64.b64encode(
                       ('%s:%s' % (USER, PASS)).encode()).decode())
    req.add_header('Cache-Control', 'no-cache')
    req.add_header('Pragma', 'no-cache')
    req.add_header('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                                 'AppleWebKit/537.36 (KHTML, like Gecko) '
                                 'Chrome/128.0 Safari/537.36')
    if preflight:
        req.add_header('X-SF-Preflight', '1')
    try:
        with urllib.request.urlopen(req, timeout=45,
                                    context=ssl.create_default_context()) as r:
            body = r.read() if want_body else b''
            return r.status, body.decode('utf-8', 'replace'), r.geturl()
    except urllib.error.HTTPError as e:
        return (e.code,
                e.read().decode('utf-8', 'replace') if want_body else '', url)
    except Exception as e:                                   # noqa: BLE001
        return 0, 'TRANSPORT: %s' % e, url


def unesc(s):
    return html_mod.unescape(s or '').strip()


def text_of(html, tag):
    """The text of the FIRST <tag> element, entity-decoded. None if absent."""
    m = re.search(r'<%s\b[^>]*>(.*?)</%s>' % (tag, tag), html or '', re.S)
    return unesc(re.sub(r'<[^>]+>', '', m.group(1))) if m else None


def texts_of(html, tag):
    return [unesc(re.sub(r'<[^>]+>', '', x)) for x in
            re.findall(r'<%s\b[^>]*>(.*?)</%s>' % (tag, tag), html or '', re.S)]


def group(html, key):
    """One configurator group's markup, by its data-sf-config-group key."""
    m = re.search(r'<div class="sf-fdetail-config__group" data-sf-config-group="'
                  + re.escape(key) + r'">(.*?)'
                  r'(?=<div class="sf-fdetail-config__group"|</div></div>\s*</div>|$)',
                  html or '', re.S)
    return m.group(1) if m else None


def group_label(g):
    m = re.search(r'sf-fdetail-config__label">(.*?)</span>', g or '', re.S)
    return unesc(re.sub(r'<[^>]+>', '', m.group(1))) if m else None


def group_options(g, key):
    """The answers a visitor can pick: the radio VALUES, not the visible text.

    The visible text is a picture slot on a dosage form whose library row has no
    attachment yet, so reading spans would return the labels on soft chews and
    the empty-slot text on powders — two different shapes for one question. The
    value attribute is what the control submits, so it is what a customer gets.
    """
    return re.findall(r'<input[^>]*value="([^"]+)"[^>]*data-sf-config-opt="'
                      + re.escape(key) + r'"', g or '')


def group_keys(html):
    return re.findall(r'data-sf-config-group="([a-z-]+)"', html or '')


def group_labels(html):
    return [unesc(re.sub(r'<[^>]+>', '', x)) for x in
            re.findall(r'sf-fdetail-config__label">(.*?)</span>', html or '', re.S)]


def ld_blocks(html):
    out = []
    for raw in re.findall(r'<script type="application/ld\+json">(.*?)</script>',
                          html or '', re.S):
        try:
            out.append(json.loads(raw))
        except ValueError:
            pass
    return out


def ld_node(html, kind):
    for node in ld_blocks(html):
        if node.get('@type') == kind:
            return node
    return None


def main():
    global BASE
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', default=BASE)
    ap.add_argument('--preflight', action='store_true',
                    help='send X-SF-Preflight: 1 (default: what dev serves)')
    ap.add_argument('--expect-ver', default='2.10.82')
    ap.add_argument('--json', metavar='OUT')
    ap.add_argument('--label', default='')
    args = ap.parse_args()

    BASE = args.base.rstrip('/')
    pf = args.preflight
    rows = []
    out = {'label': args.label or ('preflight' if pf else 'live'),
           'base': BASE, 'preflight_header': pf,
           'expect_version': args.expect_ver, 'rows': rows}
    cache = {}

    def page(path):
        if path not in cache:
            cache[path] = fetch(path, pf)
        return cache[path]

    def check(label, ok, detail=None):
        rows.append({'label': label, 'ok': bool(ok), 'detail': detail or {}})
        print('%-5s %s' % ('ok' if ok else 'FAIL', label))
        if detail:
            print('      %s' % json.dumps(detail, ensure_ascii=False)[:230])

    # ---------------------------------------------------------- 1. which bytes
    code, home, _ = page('/')
    m = re.search(r'themes/(sinofresh-theme[a-z-]*)/style\.css\?ver=([0-9.]+)', home)
    theme_dir, served_ver = (m.group(1), m.group(2)) if m else (None, None)
    out['theme_dir'], out['served_version'] = theme_dir, served_ver
    css_code, css = 0, ''
    if m:
        css_code, css, _ = fetch('/wp-content/themes/%s/style.css?ver=%s'
                                 % (theme_dir, served_ver), pf)
    vh = re.search(r'Version:\s*([0-9.]+)', css)
    check('the served stylesheet is %s' % args.expect_ver,
          served_ver == args.expect_ver and css_code == 200
          and vh is not None and vh.group(1) == args.expect_ver,
          {'theme dir': theme_dir, 'page asks for': served_ver,
           'css http': css_code, 'css header says': vh.group(1) if vh else None,
           'stylesheet bytes': len(css)})

    # ------------------------------------------------------ 2. sticky main image
    d_code, d_html, _ = page(CHEWS)
    check('the main image column carries the sticky rule',
          STICKY_RULE in css, {'in stylesheet': STICKY_RULE in css})
    check('...and the detail page still has the element it applies to',
          'sf-fdetail2__media' in d_html,
          {'detail http': d_code,
           'sf-fdetail2__media': d_html.count('sf-fdetail2__media')})

    # ------------------------------------------- 3/4. right column: fold + strip
    check('the phone fold rules are on the wire',
          FOLD_BASE in css and FOLD_PHONE in css,
          {'base rule': FOLD_BASE in css, 'folded rule': FOLD_PHONE in css})
    check('...and config.js is enqueued on the page that uses them',
          'assets/js/config.js?ver=' in d_html,
          {'enqueue': re.findall(r'config\.js\?ver=[0-9.]+', d_html)})
    check('the thumbnail strip is a horizontal scroll box on a phone',
          THUMBS_SCROLL in css,
          {'rule in stylesheet': THUMBS_SCROLL in css,
           'built by script (so the browser pass is what sees it)':
               'sf-gallery__thumbs' not in d_html})

    # --------------------------------------- 5. flavour: one answer, plus a box
    fl = group(d_html, 'flavor')
    if fl is None:
        check('the Flavor group is a single-choice group with a Custom box',
              False, {'group found': False})
    else:
        types = sorted(set(re.findall(r'type="(\w+)"', fl)))
        opts = group_options(fl, 'flavor')
        has_for = 'data-sf-config-custom-for="flavor"' in fl
        has_in = 'data-sf-config-custom-input="flavor"' in fl
        check('the Flavor group is a single-choice group with a Custom box',
              types == ['radio', 'text'] and has_for and has_in
              and opts and opts[-1] == 'Custom',
              {'input types': types, 'custom-for': has_for,
               'custom-input': has_in, 'options': opts})

    # --------------------------------------------- 6. shelf life: the pool wins
    row = re.search(r'Shelf Life</dt><dd[^>]*>([^<]+)<', d_html)
    specs_copy = d_html.count('18 months shelf life')
    check("the shelf-life row prints the record's own value, not the specs text",
          bool(row) and unesc(row.group(1)) == '24 months' and specs_copy > 0,
          {'row prints': unesc(row.group(1)) if row else None,
           'the specs text still says 18 months %d times' % specs_copy:
               'so 24 can only have come from the field',
           'pool': SHELF_POOL})

    # ---------------------------------- 7. the pool follows the dosage form
    p_code, p_html, _ = page(POWDER)
    gp, gc = group(p_html, 'shape'), group(d_html, 'shape')
    p_opts, c_opts = group_options(gp, 'shape'), group_options(gc, 'shape')
    check('the powder page has no group labelled Shape',
          gp is not None and group_label(gp) == 'Appearance'
          and 'Shape' not in group_labels(p_html),
          {'powder group labels': group_labels(p_html)})
    check('...because its answers come from the powder pool',
          all(x in p_opts for x in ('Fine Powder', 'Granules', 'Microencapsulated'))
          and not ({'Bone', 'Paw', 'Star'} & set(p_opts)),
          {'powder options': p_opts})
    check('...while the soft-chew page answers to Shape, with its own pool',
          gc is not None and group_label(gc) == 'Shape'
          and all(x in c_opts for x in ('Bone', 'Star', 'Paw'))
          and 'Fine Powder' not in c_opts,
          {'soft-chew group label': group_label(gc), 'soft-chew options': c_opts})
    cont = group(p_html, 'container')
    cont_opts = group_options(cont, 'container')
    check('Container Type is a packaging format, not a bottle shape',
          all(x in cont_opts for x in ('Jar', 'Foil Pouch', 'Stand-up Pouch'))
          and not ({'Round', 'Square', 'Oval'} & set(cont_opts)),
          {'powder container options': cont_opts, 'groups': group_keys(p_html)})

    # ------------------------------------------------------ 8. the four subpages
    # Each page has to bring its OWN copy of the three nodes the batch says are
    # derived rather than coded: FAQPage and BreadcrumbList off the template's
    # markup, Service off the slug table. Naming the page in the Service node is
    # what that table is for.
    for path, h1, crumb in SUBPAGES:
        code, html, _ = page(path)
        svc_node = ld_node(html, 'Service') or {}
        bc = ld_node(html, 'BreadcrumbList') or {}
        faq = ld_node(html, 'FAQPage') or {}
        items = [x.get('name') for x in (bc.get('itemListElement') or [])]
        qs = [x.get('name') for x in (faq.get('mainEntity') or [])]
        check('%s answers 200 as its own page' % path,
              code == 200 and text_of(html, 'h1') == h1
              and 'sf-breadcrumb--d3' in html
              and '<table class="sf-keyfacts">' in html,
              {'http': code, 'h1': text_of(html, 'h1'),
               'd3': 'sf-breadcrumb--d3' in html,
               'terms': '<table class="sf-keyfacts">' in html})
        check('...and names itself in Service, breadcrumb and FAQ schema',
              svc_node.get('name') == h1 and len(qs) == 3
              and items == ['Home', 'OEM/ODM Services', crumb],
              {'service': svc_node.get('name'), 'breadcrumb': items,
               'faq questions': len(qs)})

    # ------------------------------------------- 9. /services/: whole-card links
    s_code, svc, _ = page('/services/')
    found = [(a, unesc(b)) for a, b in
             re.findall(r'<h3 class="wp-block-heading"><a class="sf-card__title-link" '
                        r'href="([^"]+)">([^<]*)</a></h3>', svc)]
    check('/services/ links all four cards, and only through their headings',
          s_code == 200 and found == CARDS,
          {'http': s_code, 'found': found,
           'anchors carrying that class': svc.count('class="sf-card__title-link"')})
    check('...and the overview still carries its own breadcrumb level, terms table and full heading set',
          'sf-breadcrumb--d2' in svc and 'sf-breadcrumb--d3' not in svc
          and '<table class="sf-keyfacts">' in svc
          and texts_of(svc, 'h2') == OVERVIEW_H2,
          {'d2': 'sf-breadcrumb--d2' in svc, 'd3': 'sf-breadcrumb--d3' in svc,
           'terms': '<table class="sf-keyfacts">' in svc,
           'h2': texts_of(svc, 'h2')})
    check('...and the overlay that makes the whole card the target is in the CSS',
          CARD_OVERLAY in css, {'in stylesheet': CARD_OVERLAY in css})

    ok = all(r['ok'] for r in rows)
    out['ok'], out['passed'], out['total'] = ok, sum(
        1 for r in rows if r['ok']), len(rows)
    print('\n== %s @ %s%s: %d/%d %s'
          % (out['label'], BASE, ' (preflight)' if pf else '', out['passed'],
             out['total'], 'PASS' if ok else 'FAIL'))
    if args.json:
        with open(args.json, 'w', encoding='utf-8') as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
        print('   json -> %s' % args.json)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())

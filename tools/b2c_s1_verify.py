#!/usr/bin/env python3
"""Batch 2C step 1 — 21-page verification of the formula detail pages.

Every assertion is driven by tools/b2c_s1_ground_truth.php output (database +
theme functions on the dev site), never by the rendered HTML itself: comparing
HTML against HTML would only prove the page is self-consistent.

Run:
  python3 tools/b2c_s1_verify.py --truth /tmp/sf_truth.json --base https://dev.zxpet.com
"""
import argparse
import html
import json
import re
import sys
import urllib.request

LD_RE = re.compile(r'<script[^>]*application/ld[+]json[^>]*>(.*?)</script>', re.S)
NAV_RE = re.compile(r'<nav class="sf-breadcrumb([^"]*)"[^>]*>(.*?)</nav>', re.S)
CARD_RE = re.compile(r'<div class="sf-fdetail__card">(.*?)</div>', re.S)
UAE = html.unescape


def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'sf-verify/1.0'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.status, r.read().decode('utf-8', 'replace'), r.geturl()


def text(s):
    return re.sub(r'\s+', ' ', UAE(re.sub(r'<[^>]+>', ' ', s))).strip()


class Checks:
    def __init__(self):
        self.n = 0
        self.fail = []

    def ok(self, cond, label, detail=''):
        self.n += 1
        if not cond:
            self.fail.append(f'{label}: {detail}')
        return bool(cond)

    def eq(self, got, want, label):
        return self.ok(got == want, label, f'got {got!r} want {want!r}')


def ld_blocks(doc):
    out = []
    for raw in LD_RE.findall(doc):
        try:
            j = json.loads(raw.strip())
        except Exception as exc:                                  # noqa: BLE001
            out.append({'@type': f'<unparseable: {exc}>'})
            continue
        out.extend(j if isinstance(j, list) else [j])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--truth', default='/tmp/sf_truth.json')
    ap.add_argument('--base', default='https://dev.zxpet.com')
    args = ap.parse_args()

    truth = json.load(open(args.truth, encoding='utf-8'))
    c = Checks()
    form_totals = {}
    for r in truth:
        form_totals[r['form_slug']] = form_totals.get(r['form_slug'], 0) + 1

    summary = []
    for row in truth:
        slug = row['slug']
        url = f"{args.base}/formulas/{slug}/"
        try:
            status, doc, final = get(url)
        except Exception as exc:                                  # noqa: BLE001
            c.ok(False, f'{slug} fetch', str(exc))
            continue

        c.eq(status, 200, f'{slug} status')
        c.eq(final, url, f'{slug} final url')
        # No PHP diagnostics leaked into the body.
        for needle in ('Fatal error', 'Warning: ', 'Notice: ', 'Deprecated: '):
            c.ok(needle not in doc, f'{slug} no "{needle}"')
        # No leftover placeholder tokens. Template-level HTML comments are
        # emitted into the page source, so a {{token}} or an internal note
        # written in one shows up in production HTML — keep the templates to
        # short structural comments (the convention page-soft-chews.html uses).
        c.ok('{{' not in doc and '}}' not in doc, f'{slug} placeholders resolved',
             str([t for t in re.findall(r'\{\{[^}]{0,30}\}\}', doc)][:5]))
        c.ok('class-before-href' not in doc and 'queried object' not in doc,
             f'{slug} no internal doc comment leaked')
        # Self-closing block residue (the classic kses/editor artefact).
        c.ok('/ -->' not in doc, f'{slug} no self-closing residue')

        # --- assets ---------------------------------------------------------
        c.ok('style.css?ver=2.10.42' in doc, f'{slug} style 2.10.42')
        c.ok('formulas.js?ver=1.1.0' in doc, f'{slug} formulas.js 1.1.0')
        c.ok('configurator.js' not in doc, f'{slug} no configurator.js')
        c.ok('id="configurator"' not in doc, f'{slug} no #configurator')

        # --- hero -----------------------------------------------------------
        c.ok('sf-formula-hero' in doc, f'{slug} hero band')
        c.ok('sf-hero-inner' in doc, f'{slug} inner-hero recipe')
        m = NAV_RE.search(doc)
        if c.ok(bool(m), f'{slug} breadcrumb nav'):
            cls, inner = m.group(1), m.group(2)
            c.ok('sf-breadcrumb--d4' in cls, f'{slug} breadcrumb --d4', cls)
            # anchors: class must precede href on every crumb <a>
            anchors = re.findall(r'<a\s[^>]*>', inner)
            c.eq(len(anchors), 3, f'{slug} 3 breadcrumb anchors')
            for a in anchors:
                c.ok(a.index('class=') < a.index('href='), f'{slug} class-before-href', a)
            crumbs = [text(x) for x in re.findall(r'<a\s[^>]*>(.*?)</a>', inner, re.S)]
            crumbs += [text(x) for x in re.findall(
                r'<span class="sf-breadcrumb__crumb sf-breadcrumb__current"[^>]*>(.*?)</span>', inner, re.S)]
            c.eq(crumbs, ['Home', 'Products', row['form_label'], row['title']],
                 f'{slug} breadcrumb trail')

        b = re.search(r'<button[^>]*class="sf-formula__cta sf-formula__cta--solid"[^>]*>', doc)
        if c.ok(bool(b), f'{slug} K1 hero button'):
            tag = b.group(0)
            # Attribute text is entity-encoded on the wire (&#038; for &); the
            # DOM value is what formulas.js and the contract see, so decode.
            c.eq(UAE(re.search(r'data-formula="([^"]*)"', tag).group(1)), row['title'],
                 f'{slug} data-formula')
            c.eq(UAE(re.search(r'data-form="([^"]*)"', tag).group(1)), row['form_slug'],
                 f'{slug} data-form')
            c.ok('type="button"' in tag, f'{slug} button type')

        h1 = re.search(r'<h1 class="sf-formula-hero__title"[^>]*>(.*?)</h1>', doc, re.S)
        if c.ok(bool(h1), f'{slug} h1'):
            c.eq(text(h1.group(1)), row['title'], f'{slug} h1 text')
        meta = re.search(r'<p class="sf-formula-hero__meta">(.*?)</p>', doc, re.S)
        if c.ok(bool(meta), f'{slug} hero meta'):
            c.eq(text(meta.group(1)), row['meta_line'], f'{slug} hero meta line')
        use = re.search(r'<span class="sf-fcard__use">(.*?)</span>', doc, re.S)
        if c.ok(bool(use), f'{slug} use tag'):
            c.eq(text(use.group(1)), UAE(row['use_name']), f'{slug} use tag verbatim')

        # --- specification cards -------------------------------------------
        cards = [text(x) for x in CARD_RE.findall(doc)]
        labels = re.findall(r'<h3 class="sf-fdetail__label">(.*?)</h3>', doc, re.S)
        values = re.findall(r'<p class="sf-fdetail__value">(.*?)</p>', doc, re.S)
        c.eq(len(cards), 3, f'{slug} three field cards')
        c.eq([text(x) for x in labels],
             ['Ingredients', 'Guaranteed Analysis', 'Standard Specs'], f'{slug} card labels')
        c.eq([text(x) for x in values],
             [row['ingredients'], row['analysis'], row['specs']], f'{slug} card values')
        # h3, not h2: the K3 contract (h2s are the toc-nav anchors).
        c.ok('<h2 class="wp-block-heading">Specification</h2>' in doc, f'{slug} Specification h2')

        # --- long copy band must not exist on an empty record ---------------
        c.ok('sf-fdetail-body' not in doc, f'{slug} body band suppressed')

        # --- related grid ---------------------------------------------------
        sec = re.search(r'<section class="wp-block-group sf-fdetail-more(.*?)</section>', doc, re.S)
        if c.ok(bool(sec), f'{slug} related band'):
            block = sec.group(1)
            cards_in = re.findall(r'<article class="sf-fcard">', block)
            want = min(4, form_totals[row['form_slug']] - 1)
            c.eq(len(cards_in), want, f'{slug} related card count')
            names = [text(x) for x in re.findall(r'<h3 class="sf-fcard__name"[^>]*>(.*?)</h3>', block, re.S)]
            c.ok(row['title'] not in names, f'{slug} self excluded from related', str(names))
            c.ok(f"More {row['form_label']} Formulas" in block, f'{slug} related heading')

        # --- schema ---------------------------------------------------------
        blocks = ld_blocks(doc)
        types = [x.get('@type') for x in blocks]
        c.ok(types.count('Product') == 1, f'{slug} exactly one Product', str(types))
        c.ok('Article' not in types and 'BlogPosting' not in types, f'{slug} no Article', str(types))
        prod = next((x for x in blocks if x.get('@type') == 'Product'), None)
        if c.ok(prod is not None, f'{slug} Product present'):
            c.eq(prod.get('name'), row['title'], f'{slug} Product name')
            c.eq(prod.get('description'), row['description'], f'{slug} Product description')
            c.eq(prod.get('image'), row['image'], f'{slug} Product image')
            c.ok('offers' not in prod, f'{slug} Product has no offers')
            props = prod.get('additionalProperty', [])
            c.eq([(p.get('name'), p.get('value')) for p in props],
                 [('Ingredients', row['ingredients']),
                  ('Guaranteed Analysis', row['analysis']),
                  ('Standard Specs', row['specs'])], f'{slug} additionalProperty')
            c.ok(all(p.get('@type') == 'PropertyValue' for p in props), f'{slug} PropertyValue type')
        bc = next((x for x in blocks if x.get('@type') == 'BreadcrumbList'), None)
        if c.ok(bc is not None, f'{slug} BreadcrumbList present'):
            items = bc.get('itemListElement', [])
            c.eq([(i.get('position'), i.get('name')) for i in items],
                 [(1, 'Home'), (2, 'Products'), (3, row['form_label']), (4, row['title'])],
                 f'{slug} breadcrumb JSON-LD names')
            c.ok('item' not in items[-1], f'{slug} last crumb has no item url')
            c.ok(items[-1].get('item') is None, f'{slug} last crumb item absent')

        summary.append((slug, len(cards), len(re.findall(r'<article class="sf-fcard">', doc))))

    print(f'--- {c.n} assertions, {len(c.fail)} failed ---')
    for f in c.fail:
        print('FAIL', f)
    print(f'--- pages: {len(summary)} ---')
    for s in summary:
        print(f'  {s[0]:34s} fields={s[1]} related={s[2]}')
    return 1 if c.fail else 0


if __name__ == '__main__':
    sys.exit(main())

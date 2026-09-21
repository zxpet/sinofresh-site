#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch G — build a SYNTHETIC candidate capture out of a baseline capture.

The gates are run for real only after a commit has been pushed and the
pre-flight theme installed, and a gate that is discovered to be wrong at that
point has already cost a capture. This tool fabricates the candidate the
batch is supposed to produce, from the baseline bytes, so the gates can be run
and broken first.

It is a second implementation, on purpose: it re-derives everything it needs
from the baseline capture alone (the hero meta's form/MOQ/lead, the
Specification card's specs string) and applies the batch's transform from the
outside. The gate then has to undo it from the inside. Where the two disagree
is where the gate has a bug — which is exactly what F1's smoke run found three
of.

It also builds the failure cases. `--sabotage` produces a candidate that must
be REJECTED, one per gate:

    none         the honest candidate   -> gate must PASS

The negative control is not built here: point the gate's --new-* at the
baseline itself.

usage:
    python3 tools/b2d_g_synth.py --base DIR --out DIR [--sabotage KIND] \\
        [--sabotage-page NAME]
"""
import argparse
import os
import re
import shutil
import sys

DOSAGES = "soft-chews tablets powders pastes drops liquids fish-oil dental-chews".split()
FORMULAS = """bladder-support-powder calcium-phosphorus-tablets calming-soft-chews
digestive-soft-chews ear-care-drops hairball-remedy-paste joint-support-soft-chews
joint-support-tablets liquid-joint-support liquid-skin-coat multivitamin-tablets
natural-cleaning-dental-sticks nutrition-paste oral-care-dental-sticks
plaque-control-dental-chews probiotic-powder pumpkin-digestive-powder
pure-fish-oil-blend skin-coat-soft-chews urinary-care-drops wild-alaskan-salmon-oil
""".split()

LIVE_DIR = '/wp-content/themes/sinofresh-theme/'
PRE_DIR = '/wp-content/themes/sinofresh-theme-preflight/'
VER_FROM, VER_TO = '2.10.53', '2.10.54'

PAD_ATTR = ('style="padding-top:var(--wp--preset--spacing--80);'
            'padding-bottom:var(--wp--preset--spacing--80)"')
SEC_OUTER = ('<section class="wp-block-group sf-fdetail-media '
             'has-bg-light-background-color has-background is-layout-constrained '
             'wp-block-group-is-layout-constrained" ' + PAD_ATTR + '>')
INNER_OPEN = ('<div class="wp-block-group sf-fdetail-media__inner is-layout-flow '
              'wp-block-group-is-layout-flow">')
LEFT_CAND = ('<section id="gallery" class="wp-block-group sf-gallery '
             'sf-fdetail-media__left is-layout-flow wp-block-group-is-layout-flow">')
SIDE_OPEN = ('<aside class="wp-block-group sf-fdetail-media__side is-layout-flow '
             'wp-block-group-is-layout-flow">')
BATCH_COMMENT = ('<!-- Batch G: media + facts, two columns. The background belongs to the\n'
                 '     outer section only; the columns carry none, so the band reads as one\n'
                 '     surface. #gallery, its h2 and all four slides are kept — only the\n'
                 '     nesting changes. -->\n')
GALLERY_MARK = '<!-- B2D-S3: gallery -->'
BLOCK3_MARK = '\n\n<!-- Block 3: long copy'
GALLERY_BASE_OPEN = '<section id="gallery" class="wp-block-group sf-gallery has-bg-light'
MINI_OPEN = '<section class="sf-facts-mini">'


# --- the batch's rules, implemented here as well --------------------------
# Deliberately a second copy: this tool must not import the apply tool's
# literals, or a wrong rule would be applied and undone by the same code.
def specs_parts(specs):
    """unit / pack / shelf out of the one-line sf_formula_specs value."""
    unit = pack = shelf = ''
    rest = []
    for segment in [s.strip() for s in str(specs).split('\u00b7') if s.strip()]:
        if not shelf and re.search(r'\d+\s*months?\s+shelf\s+life', segment, re.I):
            shelf = segment
            continue
        rest.append(segment)
    left = []
    for segment in rest:
        if not pack and re.search(r'\sper\s', segment, re.I):
            pack = segment
            continue
        left.append(segment)
    if left:
        unit = left[0]
    return unit, pack, shelf


def intro_text(name, form_label, moq, lead):
    if form_label:
        text = ('%s is a standard %s formula from the SINO FRESH OEM/ODM range for '
                'private-label pet supplements.' % (name, form_label))
    else:
        text = ('%s is a standard formula from the SINO FRESH OEM/ODM range for '
                'private-label pet supplements.' % name)
    text += (' Produced in a GMP-certified facility in Linyi, China and shipped '
             'with full documentation, it is ready for your own brand.')
    if moq:
        text += ' Minimum order quantity: ' + moq + '.'
    if lead:
        text += ' Lead time: ' + lead + '.'
    return text


def factsheet_html(pairs):
    out = ''
    for label, value in pairs:
        if not value:
            continue
        out += ('<dt class="sf-fdetail-media__term">%s</dt>'
                '<dd class="sf-fdetail-media__value">%s</dd>' % (label, value))
    return '<dl class="sf-fdetail-media__facts">' + out + '</dl>' if out else ''


def transform_page(name, html, pack_rows, failures):
    """Apply the batch to one baseline page."""
    # the pre-flight copy serves the same theme from a differently named
    # directory: every asset URL carries it
    html = html.replace(LIVE_DIR, PRE_DIR)
    html = re.sub(r'(themes/sinofresh-theme-preflight/style\.css\?ver=)'
                  + re.escape(VER_FROM), r'\g<1>' + VER_TO, html)

    slug = name[len('zh__'):] if name.startswith('zh__') else name
    if slug.startswith('products__'):
        # .html included: the key is the dosage form, not the file name (the
        # same missing-suffix bug F1's smoke run found in its own gate)
        form = slug.split('__')[-1].replace('.html', '')
        i = html.find(MINI_OPEN)
        if i < 0:
            failures.append('%s: no .sf-facts-mini band' % name)
            return html
        j = html.find('</section>', i)
        row = ('\n<div class="sf-facts-mini__item">'
               '<span class="sf-facts-mini__label">Packaging</span> '
               '<span class="sf-facts-mini__value" data-label="Packaging formats">'
               '%s</span></div>' % pack_rows[form])
        return html[:j] + row + html[j:]

    if slug.startswith('formulas__'):
        slug = slug.split('__')[-1]
        # the batch drops its own comment between the two markers that were
        # already in the template, which shifts every later offset — so the
        # region is located AFTER the comment goes in, never before.
        html = html.replace(GALLERY_MARK + '\n',
                            GALLERY_MARK + '\n' + BATCH_COMMENT, 1)
        i = html.find(GALLERY_BASE_OPEN)
        j = html.find(BLOCK3_MARK)
        if i < 0 or j < 0:
            failures.append('%s: cannot locate the gallery region' % name)
            return html
        region = html[i:j]
        open_end = region.find('>') + 1
        payload_end = region.rindex('\n\n</section>')
        payload = region[open_end + 2:payload_end]
        meta = re.search(r'<p class="sf-formula-hero__meta">([^<]*)</p>', html)
        h1 = re.search(r'<h1 class="sf-formula-hero__title">([^<]*)</h1>', html)
        mk = re.search(r'data-sf-form="([a-z-]+)"', html)
        specs = re.search(r'<h3 class="sf-fdetail__label">Standard Specs</h3>'
                          r'<p class="sf-fdetail__value">([^<]*)</p>', html)
        if not (meta and h1 and mk and specs):
            failures.append('%s: cannot re-derive the hero/specs data' % name)
            return html
        bits = [b.strip() for b in meta.group(1).split('\u00b7')]
        form_label = bits[0] if bits else ''
        moq = bits[1][len('MOQ '):] if len(bits) > 1 and bits[1].startswith('MOQ ') else ''
        lead = bits[2][len('Lead time '):] if len(bits) > 2 and bits[2].startswith('Lead time ') else ''
        unit, pack, shelf = specs_parts(specs.group(1))
        form = mk.group(1)
        pairs = [('Unit size', unit), ('Pack options', pack), ('Shelf life', shelf),
                 ('Certifications', pack_rows[form + '__certs']),
                 ('Packaging', pack_rows[form + '__pack'])]
        side = ('<p class="sf-fdetail-media__intro">%s</p>'
                % intro_text(h1.group(1), form_label, moq, lead))
        side += factsheet_html(pairs)
        side += ('<a class="sf-fdetail-media__cta" href="/contact/">'
                 'Request Sample</a>')
        new_region = (SEC_OUTER + '\n\n' + INNER_OPEN + '\n\n' + LEFT_CAND + '\n\n'
                      + payload + '\n\n</section>\n\n\n' + SIDE_OPEN + '\n\n'
                      + side + '\n\n</aside>\n\n</div>\n\n</section>\n\n\n')
        return html[:i] + new_region + html[j + 2:]
    return html


def apply_sabotage(kind, out_dir, names, failures):
    """Break exactly one thing, so exactly one gate has to notice."""
    if kind == 'none':
        return
    if kind == 'drop-row':
        p = os.path.join(out_dir, 'products__tablets.html')
        html = open(p, encoding='utf-8').read()
        row = [ln for ln in html.split('\n') if 'data-label="Packaging formats"' in ln][0]
        open(p, 'w', encoding='utf-8').write(html.replace('\n' + row, '', 1))
        print('    sabotage drop-row -> %s loses its new row' % os.path.basename(p))
    elif kind == 'wrong-value':
        p = os.path.join(out_dir, 'products__drops.html')
        html = open(p, encoding='utf-8').read()
        html = html.replace('data-label="Packaging formats">Dropper Bottle',
                            'data-label="Packaging formats">Glass Ampoule', 1)
        open(p, 'w', encoding='utf-8').write(html)
        print('    sabotage wrong-value -> the drops row no longer matches the '
              'configurator')
    elif kind == 'extra-diff':
        p = os.path.join(out_dir, 'about.html')
        if p not in [os.path.join(out_dir, n) for n in names]:
            cands = [n for n in names if not n.startswith(('products__', 'formulas__',
                                                           'zh__'))]
            p = os.path.join(out_dir, sorted(cands)[0])
        html = open(p, encoding='utf-8').read()
        open(p, 'w', encoding='utf-8').write(html.replace('<body', '<body data-x="1"', 1))
        print('    sabotage extra-diff -> %s differs for no reason'
              % os.path.basename(p))
    elif kind == 'missing-aside':
        p = os.path.join(out_dir, 'formulas__calming-soft-chews.html')
        html = open(p, encoding='utf-8').read()
        i = html.find('<aside class="wp-block-group sf-fdetail-media__side')
        j = html.find('</aside>', i) + len('</aside>')
        open(p, 'w', encoding='utf-8').write(html[:i] + html[j:])
        print('    sabotage missing-aside -> %s loses its right column'
              % os.path.basename(p))
    elif kind == 'stray-byte':
        p = os.path.join(out_dir, 'formulas__probiotic-powder.html')
        html = open(p, encoding='utf-8').read()
        open(p, 'w', encoding='utf-8').write(
            html.replace('<h2 class="wp-block-heading">Specification</h2>',
                         '<h2 class="wp-block-heading">Specifications</h2>', 1))
        print('    sabotage stray-byte -> %s changes a heading outside the region'
              % os.path.basename(p))
    elif kind == 'keep-h2':
        # the dot rail's threshold: the batch must not move it. Simulate the
        # mistake of giving the new band an h2 on two dosage pages.
        for form in ('soft-chews', 'tablets'):
            p = os.path.join(out_dir, 'products__%s.html' % form)
            html = open(p, encoding='utf-8').read()
            open(p, 'w', encoding='utf-8').write(
                html.replace(MINI_OPEN, MINI_OPEN + '\n<h2>Core facts</h2>', 1))
        print('    sabotage keep-h2 -> two dosage pages gained a heading in the band')
    elif kind == 'version-only-one':
        p = os.path.join(out_dir, 'products__powders.html')
        html = open(p, encoding='utf-8').read()
        html = html.replace('style.css?ver=' + VER_TO, 'style.css?ver=' + VER_FROM, 1)
        open(p, 'w', encoding='utf-8').write(html)
        print('    sabotage version-only-one -> one page keeps the old token')
    else:
        failures.append('unknown sabotage %r' % kind)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--sabotage', default='none')
    args = ap.parse_args()

    failures = []
    names = sorted(n for n in os.listdir(args.base) if n.endswith('.html'))
    base = {n: open(os.path.join(args.base, n), encoding='utf-8').read()
            for n in names}

    # the packaging option sets, as the batch transcribes them: read out of the
    # dosage pages' rendered configurator, drop the trailing "Custom" option
    pack_rows = {}
    for form in DOSAGES:
        html = base.get('products__%s.html' % form, '')
        # the group's own close is not the first </div> after it — that one
        # belongs to the label block — so the option set is read up to the
        # NEXT group's opening marker, which is where this group ends.
        i = html.find('data-group="packaging"')
        j = html.find('data-group=', i + 10) if i >= 0 else -1
        seg = html[i:j] if i >= 0 and j > 0 else (html[i:] if i >= 0 else '')
        values = re.findall(r'data-value="([^"]+)"', seg)
        if not values:
            failures.append('products__%s: no packaging options on the page' % form)
            continue
        pack_rows[form] = ', '.join(values[:-1]) + ', or custom formats'
    if len(pack_rows) != len(DOSAGES):
        for f in failures:
            print('!! ' + f, file=sys.stderr)
        return 1
    # The two values the formula column reads off the dosage row. Certifications
    # already exists on the baseline; Packaging formats is what this batch adds,
    # so its row value is the option set derived above.
    for form in DOSAGES:
        html = base['products__%s.html' % form]
        m = re.search(r'data-label="Certifications"[^>]*>([^<]*)</span>', html)
        if not m:
            failures.append('%s: no Certifications row in the baseline' % form)
            continue
        pack_rows[form + '__certs'] = m.group(1)
        pack_rows[form + '__pack'] = pack_rows[form]

    if failures:
        for f in failures:
            print('!! ' + f, file=sys.stderr)
        return 1

    if os.path.isdir(args.out):
        shutil.rmtree(args.out)
    os.makedirs(args.out)
    n_facts = n_media = 0
    for name in names:
        out = transform_page(name, base[name], pack_rows, failures)
        if name.startswith(('products__', 'zh__products__')):
            n_facts += 1
        if name.startswith(('formulas__', 'zh__formulas__')):
            n_media += 1
        with open(os.path.join(args.out, name), 'w', encoding='utf-8') as fh:
            fh.write(out)

    apply_sabotage(args.sabotage, args.out, names, failures)

    print('synthetic candidate -> %s' % args.out)
    print('  %d page(s); %d dosage transforms, %d media transforms; %d byte(s) '
          'larger overall' % (len(names), n_facts, n_media,
                              sum(os.path.getsize(os.path.join(args.out, n))
                                  - os.path.getsize(os.path.join(args.base, n))
                                  for n in names)))
    if failures:
        print('FAIL — %d problem(s):' % len(failures), file=sys.stderr)
        for f in failures:
            print('  * %s' % f, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())

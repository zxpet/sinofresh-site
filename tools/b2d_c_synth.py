#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch C — build a SYNTHETIC candidate capture out of a baseline capture.

The gates are run for real only after a commit has been pushed and the
pre-flight theme installed, and a gate discovered to be wrong at that point has
already cost a capture. This tool fabricates the candidate the batch is
supposed to produce, from the baseline bytes, so the gates can be run and
broken first.

It is a second implementation on purpose: it re-derives everything from the
baseline capture alone (the dosage row's Certifications and Packaging formats,
the record's title) and applies the batch's transform from the outside. The
gate then has to undo it from the inside. Where the two disagree is where the
gate has a bug.

What the batch does, in the bytes:

  * 42 pages (21 formulas + 21 /zh/ formulas) gain a section between the closed
    composition block and the "Block 4: related formulas" marker — a core group
    carrying .sf-fdetail .sf-fdetail-faq, a core heading, and the accordion the
    shortcode returns (.sf-faq with nine <details>);
  * the same 42 pages gain one FAQPage <script> in <head>, first among the
    JSON-LD blocks, because the generator's callback is registered before the
    breadcrumb's at the same priority;
  * NOTHING else moves. style.css and functions.php keep the same version
    tokens: the batch ships no CSS change, so ?ver= stays 2.10.54 on both sides.

usage:
    python3 tools/b2d_c_synth.py --base DIR --out DIR [--sabotage KIND] \\
        [--sabotage-page NAME]
"""
import argparse
import html as html_mod
import json
import os
import re
import shutil
import sys

FORMULAS = """bladder-support-powder calcium-phosphorus-tablets calming-soft-chews
digestive-soft-chews ear-care-drops hairball-remedy-paste joint-support-soft-chews
joint-support-tablets liquid-joint-support liquid-skin-coat multivitamin-tablets
natural-cleaning-dental-sticks nutrition-paste oral-care-dental-sticks
plaque-control-dental-chews probiotic-powder pumpkin-digestive-powder
pure-fish-oil-blend skin-coat-soft-chews urinary-care-drops wild-alaskan-salmon-oil
""".split()

LIVE_DIR = '/wp-content/themes/sinofresh-theme/'
PRE_DIR = '/wp-content/themes/sinofresh-theme-preflight/'
VER = '2.10.54'

# --- the rendered section, exactly as the renderer lays it out -------------
# Measured on the baseline: between the composition block's close and the
# "Block 4" marker the page carries FIVE newlines, and the template line that
# holds the comment contributes its own newline like every other line. The
# tool's region is therefore anchored on the comment and ends on the group's
# close; what is left over is the blank line the base already had.
COMPOSITION_MARK = '<!-- B2D-S3: composition -->'
BLOCK4_MARK = '<!-- Block 4: related formulas -->'

BATCH_COMMENT = ('<!-- Batch C: the formula FAQ. The accordion is emitted by the FAQ shortcode\n'
                 '     in the core/html block below, so the nine answers can carry this record\'s\n'
                 '     own values and the FAQPage schema can read the same function instead of\n'
                 '     scanning this file for a details pair. sf-fdetail is on the section only\n'
                 '     for its <=768px inset; the .sf-faq class comes from the div the shortcode\n'
                 '     returns, which is what style.css 13 and 31a both key on. -->\n')

SECTION_OPEN = ('<section class="wp-block-group sf-fdetail sf-fdetail-faq '
                'has-card-white-background-color has-background is-layout-constrained '
                'wp-block-group-is-layout-constrained" '
                'style="padding-top:var(--wp--preset--spacing--80);'
                'padding-bottom:var(--wp--preset--spacing--80)">')
H2 = '<h2 class="wp-block-heading">Frequently Asked Questions</h2>'

# --- the nine pairs, as the batch writes them -----------------------------
QUESTIONS = [
    'Can the active ingredients be changed?',
    'Can the flavour be changed?',
    'Is a gluten-free or grain-free version available?',
    'Is this formula for dogs or for cats?',
    'Can I sample this formula before ordering?',
    'What certifications and documentation do you provide?',
    'Can the packaging and the label be customised?',
    'How should the finished product be stored?',
    'Will you keep my formula and my brand confidential?',
]

FIXED = {
    0: 'Yes. This is a starting point rather than a fixed recipe: we can adjust the levels, '
       'swap one active for another, or add new ones, and the specification and the label are '
       'rewritten to match.',
    1: 'Yes. The flavour profile is chosen with you for your target market, including a '
       'profile you already sell.',
    2: 'Yes. Wheat, gluten and grain carriers can be left out of the recipe, and the change '
       'is recorded in the specification and in the Certificate of Analysis.',
    3: 'Our formulas can be customised for dogs, cats, or both. Tell us your target species '
       'when you enquire and we will adjust the formula, the dosage, and the label accordingly.',
    4: 'Yes. The sample is made to the same specification as the bulk order: sampling takes '
       '3\u20137 working days for a standard formula, and the $200 sampling fee is deducted '
       'from your bulk order.',
    7: 'Store in a cool, dry place, away from direct sunlight. Once opened, keep the container '
       'tightly closed and use within the recommended period.',
    8: 'Yes \u2014 every formula is produced exclusively under your own brand. We never sell '
       'your formula, your artwork, or your customer list to any third party, and we sign an '
       'NDA before sharing any custom formulation details.',
}


def esc_html(text):
    """htmlspecialchars($text, ENT_QUOTES, 'UTF-8')."""
    return (html_mod.escape(text, quote=True)
            .replace('&#x27;', '&#039;'))


def answers(name, certs, pack):
    """The nine answers, with the three data-driven ones filled in."""
    out = []
    out.append(FIXED[0])
    out.append(FIXED[1])
    out.append(FIXED[2])
    out.append(FIXED[3])
    out.append(FIXED[4])
    a = ('Certifications: ' + certs + '. ') if certs else ''
    a += ('Every batch is tested in our QC laboratory and ships with a Certificate of '
          'Analysis, and we support FDA, EU and other target-market documentation.')
    out.append(a)
    a = ('Standard formats for this dosage form: ' + pack + '. ') if pack else ''
    a += 'The label, the carton and the barcode are all produced with your own brand on them.'
    out.append(a)
    out.append(FIXED[7])
    out.append(FIXED[8])
    return out


def faq_div(name, certs, pack):
    """The <div class="sf-faq"> the shortcode returns, one line, no newlines."""
    items = ''
    for i, (q, a) in enumerate(zip(QUESTIONS, answers(name, certs, pack))):
        items += ('<details class="wp-block-details sf-faq__item"%s>'
                  '<summary><h3 class="wp-block-heading">%s</h3>'
                  '<span class="sf-faq__icon" aria-hidden="true"></span></summary>'
                  '<p class="has-text-secondary-color has-text-color">%s</p></details>'
                  % (' open' if i == 0 else '', esc_html(q), esc_html(a)))
    return '<div class="sf-faq">' + items + '</div>'


def region(faq):
    """The span the batch inserts into the page, in RENDERED bytes.

    Block delimiter comments are consumed by the parser and emit nothing, but
    the newline that ended their template line survives — measured on batch G's
    band, which is the same three-block shape. So the region carries a bare
    newline where the wp:group delimiter was, the section tag core rewrites,
    a bare newline where wp:heading was, and no trace of the closing
    delimiters. Two newlines are left at the very end because the template's
    blank line before "Block 4" is not part of the region: the caller restores
    it by removing this span alone.
    """
    return (BATCH_COMMENT
            + '\n'
            + SECTION_OPEN + '\n\n'
            + H2 + '\n\n\n'
            + faq + '\n\n'
            + '</section>\n\n')


def php_json_str(s):
    """PHP's json_encode() string escaping, flags OFF (the zh re-encoder)."""
    out = ['"']
    for ch in s:
        o = ord(ch)
        if ch == '"':
            out.append('\\"')
        elif ch == '\\':
            out.append('\\\\')
        elif ch == '/':
            out.append('\\/')
        elif ch == '\n':
            out.append('\\n')
        elif ch == '\r':
            out.append('\\r')
        elif ch == '\t':
            out.append('\\t')
        elif o < 0x20 or o > 0x7e:
            out.append('\\u%04x' % o)
        else:
            out.append(ch)
    out.append('"')
    return ''.join(out)


def php_json_pretty(data, indent=0):
    """JSON_PRETTY_PRINT, four spaces, PHP's separators.

    Measured, not guessed: EVERY application/ld+json block on the /zh/ pages is
    re-encoded this way — the theme's own compact output included, so the
    localised FAQPage below arrives pretty-printed the same way. The gate has
    to be able to take that multi-line script back out of the page, which is
    why the synthetic candidate reproduces it instead of staying compact.
    """
    pad = '    ' * indent
    if isinstance(data, dict):
        if not data:
            return '{}'
        body = ',\n'.join('%s    %s: %s' % (pad, php_json_str(k),
                                            php_json_pretty(v, indent + 1))
                          for k, v in data.items())
        return '{\n' + body + '\n' + pad + '}'
    if isinstance(data, list):
        if not data:
            return '[]'
        body = ',\n'.join('%s    %s' % (pad, php_json_pretty(v, indent + 1))
                          for v in data)
        return '[\n' + body + '\n' + pad + ']'
    if isinstance(data, bool):
        return 'true' if data else 'false'
    if data is None:
        return 'null'
    if isinstance(data, (int, float)):
        return json.dumps(data)
    return php_json_str(data)


def faqpage_body(pairs):
    return {
        '@context': 'https://schema.org',
        '@type': 'FAQPage',
        'mainEntity': [
            {'@type': 'Question', 'name': q,
             'acceptedAnswer': {'@type': 'Answer', 'text': a}}
            for q, a in pairs
        ],
    }


def faqpage_script(pairs, pretty):
    """One FAQPage <script>, with the localised pages' re-encoding modelled."""
    body = (php_json_pretty(faqpage_body(pairs)) if pretty
            else json.dumps(faqpage_body(pairs), ensure_ascii=False,
                            separators=(',', ':')))
    return '\n<script type="application/ld+json">' + body + '</script>\n'


def transform_page(name, html, values, failures):
    """Apply the batch to one baseline page."""
    # the pre-flight copy serves the same theme from a differently named
    # directory: every asset URL carries it. The version token does NOT move.
    html = html.replace(LIVE_DIR, PRE_DIR)
    slug = name[len('zh__'):] if name.startswith('zh__') else name
    if not slug.startswith('formulas__'):
        return html

    key = slug[len('formulas__'):].replace('.html', '')
    if key not in values:
        failures.append('%s: no dosage row data for %s' % (name, key))
        return html
    certs, pack = values[key]

    i = html.find(COMPOSITION_MARK)
    j = html.find(BLOCK4_MARK)
    if i < 0 or j < 0 or j < i:
        failures.append('%s: cannot locate the FAQ seam' % name)
        return html
    # between the two markers the page carries five newlines; the region goes
    # after the first four of them, so one newline survives as the base blank
    seam = html[i:j]
    if re.fullmatch(r'<!-- B2D-S3: composition -->\n{5}', seam) is None:
        failures.append('%s: the seam is %r, not the measured five newlines'
                        % (name, seam))
        return html
    faq = faq_div(slug, certs, pack)
    html = html[:i] + COMPOSITION_MARK + '\n\n\n\n' + region(faq) + '\n' + html[j:]

    # <head>: the FAQPage script is emitted first among the JSON-LD blocks,
    # in front of the breadcrumb that is already there — the generator's
    # callback is registered ahead of the breadcrumb's at the same priority
    # (measured on the dosage pages, which already emit both). It goes between
    # the two newlines that precede that first script, one on each side.
    i = html.find('<script type="application/ld+json">')
    head_end = html.find('</head>')
    if i < 0 or head_end < 0 or i > head_end or html[i - 2:i] != '\n\n':
        failures.append('%s: the first JSON-LD script is not where it was' % name)
        return html
    html = (html[:i - 1]
            + faqpage_script(list(zip(QUESTIONS, answers(slug, certs, pack))),
                             pretty=name.startswith('zh__'))
            + html[i - 1:])
    return html


def apply_sabotage(kind, out_dir, values, failures):
    """Break exactly one thing, so exactly one gate has to notice.

    `none` is the honest candidate and every gate must pass on it. The rest
    exist to prove each gate can fail: the negative control (pointing the
    gate's --new-* at the baseline) proves only that the gate is not
    unconditionally green.
    """
    KINDS = ('none', 'drop-section', 'drop-schema', 'eight-items', 'reword-fixed',
             'certs-drift', 'extra-page', 'version-bump', 'stray-byte',
             'css-reuse-dropped')
    if kind not in KINDS:
        failures.append('unknown sabotage %r' % kind)
        return
    if kind == 'none':
        return

    def read(p):
        return open(os.path.join(out_dir, p), encoding='utf-8').read()

    def write(p, s):
        open(os.path.join(out_dir, p), 'w', encoding='utf-8').write(s)

    if kind == 'drop-section':
        p = 'formulas__calming-soft-chews.html'
        s = read(p)
        i = s.find(BATCH_COMMENT)
        j = s.find('</section>\n\n', i) + len('</section>\n\n')
        write(p, s[:i] + s[j:])
        print('    sabotage drop-section -> %s keeps its FAQPage but loses the '
              'visible band' % p)
    elif kind == 'drop-schema':
        p = 'formulas__probiotic-powder.html'
        s = read(p)
        m = re.search(r'\n<script type="application/ld\+json">(?:(?!</script>)[\s\S])*?'
                      r'"@type":"FAQPage"(?:(?!</script>)[\s\S])*?</script>\n', s)
        write(p, s[:m.start()] + s[m.end():])
        print('    sabotage drop-schema -> %s keeps the band but loses the schema' % p)
    elif kind == 'eight-items':
        p = 'formulas__skin-coat-soft-chews.html'
        s = read(p)
        m = re.search(r'<details class="wp-block-details sf-faq__item"><summary>'
                      r'<h3 class="wp-block-heading">Will you keep my formula and my '
                      r'brand confidential\?</h3>.*?</details>', s)
        write(p, s[:m.start()] + s[m.end():])
        print('    sabotage eight-items -> %s carries eight questions' % p)
    elif kind == 'reword-fixed':
        p = 'formulas__multivitamin-tablets.html'
        s = read(p)
        needle = 'Yes \u2014 every formula'
        if needle not in s:
            failures.append('reword-fixed: the dictated answer is not where it '
                            'was on %s' % p)
            return
        write(p, s.replace(needle, 'Yes \u2014 every single formula', 1))
        print('    sabotage reword-fixed -> %s rewords a user-dictated answer' % p)
    elif kind == 'certs-drift':
        p = 'formulas__liquid-skin-coat.html'
        s = read(p)
        m = re.search(r'"name":"What certifications and documentation do you '
                      r'provide\?","acceptedAnswer":\{"@type":"Answer","text":"[^"]*"\}',
                      s)
        if not m:
            failures.append('certs-drift: the certification question is not where '
                            'it was on %s' % p)
            return
        write(p, s[:m.start()] + '"name":"What certifications and documentation do you '
                 'provide?","acceptedAnswer":{"@type":"Answer","text":"Certifications: '
                 'ISO 9001 only."}' + s[m.end():])
        print('    sabotage certs-drift -> %s no longer quotes the dosage row' % p)
    elif kind == 'extra-page':
        # A dosage page is not supposed to change at all, so this one is the
        # "the batch leaked onto a page outside its 42" break: the whole band
        # AND its FAQPage script land on a page that already carries a FAQPage
        # of its own. Gate 2 has to see a 43rd page differ, and gate 5 has to
        # see the dosage page's JSON-LD stop being deep-equal.
        p = 'products__tablets.html'
        s = read(p)
        anchor = '<!-- Block 11: Related Dosage Forms -->'
        if anchor not in s:
            failures.append('extra-page: %s carries no Block 11 marker' % p)
            return
        key = 'joint-support-tablets'      # any formula whose form is tablets
        certs, pack = values[key]
        band = region(faq_div(key, certs, pack))
        s = s.replace(anchor, band + anchor, 1)
        i = s.find('<script type="application/ld+json">')
        head_end = s.find('</head>')
        if i < 0 or head_end < 0 or i > head_end or s[i - 2:i] != '\n\n':
            failures.append('extra-page: %s has no JSON-LD seam in its head' % p)
            return
        s = (s[:i - 1]
             + faqpage_script(list(zip(QUESTIONS, answers(key, certs, pack))),
                              pretty=False)
             + s[i - 1:])
        write(p, s)
        print('    sabotage extra-page -> %s (a dosage page) gains the band AND a '
              'second FAQPage' % p)
    elif kind == 'version-bump':
        p = 'formulas__oral-care-dental-sticks.html'
        s = read(p)
        write(p, s.replace('style.css?ver=' + VER, 'style.css?ver=2.10.55', 1))
        print('    sabotage version-bump -> one page moves its cache token')
    elif kind == 'stray-byte':
        p = 'formulas__nutrition-paste.html'
        s = read(p)
        write(p, s.replace('<h2 class="wp-block-heading">Specification</h2>',
                           '<h2 class="wp-block-heading">Specifications</h2>', 1))
        print('    sabotage stray-byte -> %s changes a heading outside the region' % p)
    elif kind == 'css-reuse-dropped':
        p = 'formulas__joint-support-tablets.html'
        s = read(p)
        write(p, s.replace('sf-fdetail sf-fdetail-faq', 'sf-fdetail-faq', 1))
        print('    sabotage css-reuse-dropped -> %s loses the sf-fdetail mobile '
              'inset' % p)


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

    # the two values the batch reads off the dosage page. Which dosage page is
    # read from the formula page's own data-sf-form attribute, never derived
    # from the formula slug: "oral-care-dental-sticks" is a dental-chews
    # record, and the slug would have looked for a page that does not exist.
    form_of = {}
    for name in names:
        slug = name[len('zh__'):] if name.startswith('zh__') else name
        if not slug.startswith('formulas__'):
            continue
        key = slug[len('formulas__'):].replace('.html', '')
        m = re.search(r'data-sf-form="([a-z-]+)"', base[name])
        if not m:
            failures.append('%s: no data-sf-form attribute' % name)
            continue
        form_of[key] = m.group(1)

    values = {}
    for key, form in sorted(form_of.items()):
        page = 'products__%s.html' % form
        html = base.get(page, '')
        if not html:
            failures.append('%s: the capture lacks the dosage page %s'
                            % (key, page))
            continue
        certs = re.search(r'data-label="Certifications"[^>]*>(.*?)</span>', html, re.S)
        pack = re.search(r'data-label="Packaging formats"[^>]*>(.*?)</span>', html, re.S)
        if not certs or not pack:
            failures.append('%s: the dosage page carries no Certifications / '
                            'Packaging formats row' % page)
            continue
        values[key] = (html_mod.unescape(certs.group(1)).strip(),
                       html_mod.unescape(pack.group(1)).strip())
    if failures:
        for f in failures:
            print('!! ' + f, file=sys.stderr)
        return 1

    if os.path.isdir(args.out):
        shutil.rmtree(args.out)
    os.makedirs(args.out)
    n_formula = 0
    for name in names:
        out = transform_page(name, base[name], values, failures)
        slug = name[len('zh__'):] if name.startswith('zh__') else name
        if slug.startswith('formulas__'):
            n_formula += 1
        with open(os.path.join(args.out, name), 'w', encoding='utf-8') as fh:
            fh.write(out)

    apply_sabotage(args.sabotage, args.out, values, failures)

    print('synthetic candidate -> %s' % args.out)
    print('  %d page(s); %d formula transforms; %d byte(s) larger overall'
          % (len(names), n_formula,
             sum(os.path.getsize(os.path.join(args.out, n))
                 - os.path.getsize(os.path.join(args.base, n)) for n in names)))
    if failures:
        print('FAIL \u2014 %d problem(s):' % len(failures), file=sys.stderr)
        for f in failures:
            print('  * %s' % f, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())

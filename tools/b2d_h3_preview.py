#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H3 — render the two new bands locally, in both states, and look at them.

The renderer unit test proves structure; this proves the layout. It matters
because of a gap the server gate cannot close: every field this batch reads is
0/21 on the live database, so the *filled* state of the content band cannot be
seen on the dev site at all — and the empty state, which is what all 42 detail
records serve today, is thin enough that a layout fault would be easy to read as
"there just is not much here yet".

Both states are rendered offline from the shipped function bodies (the same
extraction the unit test uses) and dropped into a page wearing the real
style.css, with the surrounding bands mocked closely enough to answer the two
questions worth answering before a server round trip:

  1. does the content band read as a continuation of the card-white surface
     that starts at the Specification cards, or as a stripe that cuts it?
  2. do the four sampling steps hold one row above 769px, and stack below it?

Output: _backup/b2d-h3-preview-{filled,empty}.html. Nothing here ships: the
files exist to be screenshotted and read.

usage:
    python3 tools/b2d_h3_preview.py [--php PATH]
"""

import argparse
import importlib.util
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BACKUP = os.path.join(ROOT, '_backup')
PHP_SRC = os.path.join(BACKUP, 'b2d-h3-preview.php')

FILLED = {
    'sf_formula_recommended_for': 'Formulated for dogs and cats showing early signs of joint '
        'stiffness, and for brands building a mobility range on a formula that is already '
        'stable in a soft chew.',
    'sf_formula_use_cases': "Daily mobility support\nRecovery support after orthopaedic surgery\n"
        "Senior pets on a long-term maintenance plan",
    'sf_formula_who_for': 'Suited to brands launching their first joint-health SKU, and to '
        'established ranges adding a soft chew alongside a powder or a liquid.',
    'sf_formula_container': 'pouch',
    'sf_formula_packaging_extra': ['Stick pack', 'Sachet', 'Bulk bag'],
    'sf_formula_colors': ['Natural', 'Amber', 'Charcoal'],
    'sf_formula_cartons': [{'count': '60 pcs', 'boxes': '12', 'size': '40 x 30 x 25'},
                           {'count': '120 pcs', 'boxes': '8', 'size': '48 x 34 x 28'}],
}

PRINTER = r"""
$GLOBALS['SF_SINGULAR'] = true;
$GLOBALS['SF_ID']       = 21;
$filled = json_decode('%FILLED%', true);

$GLOBALS['SF_META'] = array();
$out = array('empty' => array(
	'content'  => sinofresh_formula_content(),
	'sampling' => sinofresh_formula_sampling(),
));

$GLOBALS['SF_META'] = $filled;
$out['filled'] = array(
	'content'  => sinofresh_formula_content(),
	'sampling' => sinofresh_formula_sampling(),
);
$out['steps'] = array_column(sinofresh_sampling_steps(), 'title');
echo json_encode($out, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
"""

PALETTE = """
:root{
--wp--preset--color--text-primary:#1C2B24;--wp--preset--color--primary:#1B4D3E;
--wp--preset--color--accent:#1B4D3E;--wp--preset--color--brand-green:#5AB735;
--wp--preset--color--bg-light:#F3F6F4;--wp--preset--color--card-white:#FFFFFF;
--wp--preset--color--border-light:#DCE2DF;--wp--preset--color--border-medium:#C7D0CB;
--wp--preset--color--text-secondary:#5F6B65;--wp--preset--color--cta:#B54E0F;
--wp--preset--font-family--body:-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
--wp--preset--font-family--heading:-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
--wp--style--global--content-size:1200px;
--wp--preset--spacing--80:48px;
}
/* The page sits on a grey backdrop so a card-white band reads as a surface;
   the real page has no such contrast, which is exactly why a stripe that is
   not supposed to be there is easy to miss there and obvious here. */
body{margin:0;background:#E6EAE8;font-family:var(--wp--preset--font-family--body);
font-size:16px;line-height:1.6;color:var(--wp--preset--color--text-primary)}
h1,h2,h3,h4{font-family:var(--wp--preset--font-family--heading);font-weight:600;line-height:1.25;margin:0}
h2{font-size:clamp(26px,3vw,34px);font-weight:700;line-height:1.15;letter-spacing:-0.01em}
h3{font-size:clamp(18px,1.6vw,20px);line-height:1.3}
.wp-block-group{box-sizing:border-box}
/* WordPress generates these from theme.json for every block that names a
   background; the page carries them as real classes. Without them a mocked
   bg-light band computes as transparent and the surface check reads a colour
   change that is an artefact of this file, not of the theme. */
.has-card-white-background-color{background-color:var(--wp--preset--color--card-white)}
.has-bg-light-background-color{background-color:var(--wp--preset--color--bg-light)}
.has-primary-background-color{background-color:var(--wp--preset--color--primary)}
.has-card-white-color{color:var(--wp--preset--color--card-white)}
.has-text-secondary-color{color:var(--wp--preset--color--text-secondary)}
.__pagehead{background:#1C2B24;color:#fff;padding:14px 24px;font:700 12px/1.5 inherit;
letter-spacing:.06em;text-transform:uppercase;position:sticky;top:0;z-index:9}
.__tag{display:inline-block;margin:0 0 10px;padding:2px 8px;border-radius:999px;
background:#1C2B24;color:#fff;font:600 10px/1.6 var(--wp--preset--font-family--body);
letter-spacing:.08em;text-transform:uppercase}
.__tag--flat{background:none;color:#5F6B65;display:block}
"""


def band(tag, inner, cls='', bg='card-white', pad='48px'):
    """A mocked neighbouring band, built from the real classes."""
    return ('<section class="wp-block-group %s has-%s-background-color has-background" '
            'style="padding-top:%s;padding-bottom:%s"><span class="__tag">%s</span>%s</section>'
            % (cls, bg, pad, pad, tag, inner))


def context():
    """The page around the two new bands, so the surface can be judged."""
    spec_card = ('<div class="sf-fdetail__grid sf-fdetail__grid--solo">'
                 '<div class="sf-fdetail__card"><h3 class="sf-fdetail__label">Standard Specs</h3>'
                 '<p class="sf-fdetail__value">2 g soft chew, 60/90/120 per pack, 18 months shelf life</p>'
                 '</div></div>')
    actives = ('<p class="sf-actives__label">Ingredients</p><ul class="sf-actives__ing">'
               '<li class="sf-actives__pill">Glucosamine</li><li class="sf-actives__pill">Chondroitin</li>'
               '<li class="sf-actives__pill">MSM</li><li class="sf-actives__pill">Green-lipped mussel</li>'
               '</ul><p class="sf-actives__label">Guaranteed Analysis</p><dl class="sf-spec-list">'
               '<div class="sf-spec-row"><dt class="sf-spec-term">Crude protein</dt>'
               '<dd class="sf-spec-value">12%</dd></div>'
               '<div class="sf-spec-row"><dt class="sf-spec-term">Glucosamine</dt>'
               '<dd class="sf-spec-value">500 mg</dd></div></dl>')
    faq = ('<div class="sf-faq"><details class="wp-block-details sf-faq__item" open>'
           '<summary><h3 class="wp-block-heading">Can I sample this formula before ordering?</h3>'
           '<span class="sf-faq__icon" aria-hidden="true"></span></summary>'
           '<p class="has-text-secondary-color has-text-color">Yes. The sample is made to the same '
           'specification as the bulk order.</p></details>'
           '<details class="wp-block-details sf-faq__item">'
           '<summary><h3 class="wp-block-heading">Can the flavour be changed?</h3>'
           '<span class="sf-faq__icon" aria-hidden="true"></span></summary>'
           '<p class="has-text-secondary-color has-text-color">Yes.</p></details></div>')
    return {
        'above': (
            band('1 · hero (stub)', '<h1 style="color:#fff">Joint Support Soft Chews</h1>',
                 bg='primary', pad='64px')
            + band('2 · media + parameters (stub)', '<h2>Gallery and the parameter list</h2>'
                   '<p>The two-column band sits here, on bg-light.</p>', cls='sf-fdetail2', bg='bg-light')
            + band('3 · Specification (shipped)', '<h2>Specification</h2>' + spec_card,
                   cls='sf-fdetail')
            + '<section class="sf-fdetail-actives has-card-white-background-color has-background" '
              'style="padding-top:48px;padding-bottom:48px"><div class="sf-fdetail-actives__inner">'
              '<h2 class="sf-fdetail-actives__title">Formula &amp; nutrition</h2>' + actives
            + '</div></section>'
            + '<p class="__tag __tag--flat">4 · Ingredients &amp; composition — empty today, the band '
              'emits nothing, so the surface simply continues</p>'),
        'below': (
            band('6 · FAQ (shipped)', '<h2>Frequently Asked Questions</h2>' + faq,
                 cls='sf-fdetail sf-fdetail-faq')
            + band('8 · More formulas (stub)', '<h2>More Soft Chews Formulas</h2><p>Card grid.</p>',
                   cls='sf-fdetail-more', bg='bg-light')
            + band('9 · closing CTA (stub)', '<h2 style="color:#fff">Ready to Launch Your Product?</h2>',
                   bg='primary', pad='64px')),
    }


def page(title, html):
    return ('<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"/>'
            '<title>%s</title>\n<link rel="stylesheet" href="../sinofresh-theme/style.css"/>\n'
            '<style>%s</style></head><body>\n'
            '<div class="__pagehead">H3 local preview — %s</div>\n%s\n</body></html>'
            % (title, PALETTE, title, html))


def load_unit():
    spec = importlib.util.spec_from_file_location(
        'b2d_h3_render_unit', os.path.join(HERE, 'b2d_h3_render_unit.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def shoot(pages, out_dir, widths):
    """Screenshot each preview at each width. Sequential subprocess calls: a
    shell loop with command substitution drifts between iterations, and the
    viewport must be set AFTER open (open resets it)."""
    os.makedirs(out_dir, exist_ok=True)
    rows = []
    for name, path in pages:
        for w in widths:
            shot = os.path.join(out_dir, '%s-%d.png' % (name, w))
            for argv in (['open', 'file://' + path],
                         ['set', 'viewport', str(w), '900'],
                         ['screenshot', '--full', shot]):
                p = subprocess.run(['agent-browser'] + argv, capture_output=True, text=True)
                if p.returncode != 0:
                    print('  %s %s -> rc=%d %s' % (name, argv[0], p.returncode,
                                                   (p.stderr or p.stdout).strip()[:160]))
            size = os.path.getsize(shot) if os.path.exists(shot) else 0
            rows.append((name, w, size))
            print('  %-8s %5d px  %s  %s' % (name, w, shot, '%d KB' % (size // 1024)))
    subprocess.run(['agent-browser', 'close', '--all'], capture_output=True, text=True)
    return rows


PROBE_JS = r"""
(function () {
  function cs(sel, prop) {
    var el = document.querySelector(sel);
    if (!el) { return null; }
    return getComputedStyle(el).getPropertyValue(prop).trim();
  }
  function box(sel) {
    var el = document.querySelector(sel);
    if (!el) { return null; }
    var r = el.getBoundingClientRect();
    return { w: Math.round(r.width), h: Math.round(r.height), top: Math.round(r.top) };
  }
  var bandSelectors = ['.sf-fdetail', '.sf-fdetail-actives', '.sf-fdetail-content',
                       '.sf-fdetail-faq', '.sf-sampling', '.sf-fdetail-more'];
  var bands = bandSelectors.map(function (s) {
    var el = document.querySelector(s);
    return { sel: s, present: !!el,
             bg: el ? getComputedStyle(el).backgroundColor : null,
             top: el ? Math.round(el.getBoundingClientRect().top) : null };
  });
  var stepCols = cs('.sf-sampling__steps', 'grid-template-columns');
  return {
    bands: bands,
    contentPadding: cs('.sf-fdetail-content', 'padding-top'),
    contentSidePad: cs('.sf-fdetail-content', 'padding-left'),
    blockGap: cs('.sf-fdetail-content__block + .sf-fdetail-content__block', 'margin-top'),
    contentInnerWidth: box('.sf-fdetail-content__inner'),
    headingSize: cs('.sf-fdetail-content__heading', 'font-size'),
    subtitleSize: cs('.sf-fdetail-content__subtitle', 'font-size'),
    proseSize: cs('.sf-fdetail-content__prose', 'font-size'),
    chipRadius: cs('.sf-fdetail-content__chip', 'border-radius'),
    cartonCollapse: cs('.sf-fdetail-content__cartons', 'border-collapse'),
    numBg: cs('.sf-sampling__num', 'background-color'),
    numFg: cs('.sf-sampling__num', 'color'),
    numBox: box('.sf-sampling__num'),
    stepCols: stepCols,
    stepCount: document.querySelectorAll('.sf-sampling__step').length,
    stepsPerRow: (function () {
      var seen = {};
      document.querySelectorAll('.sf-sampling__step').forEach(function (el) {
        seen[Math.round(el.getBoundingClientRect().top)] = 1;
      });
      return Object.keys(seen).length;
    })(),
    samplingBg: cs('.sf-sampling', 'background-color'),
    noteColor: cs('.sf-sampling__note', 'color'),
    h2InContent: document.querySelectorAll('.sf-fdetail-content h2').length,
    h3InSampling: document.querySelectorAll('.sf-sampling h3').length,
    docScrollW: document.documentElement.scrollWidth,
    docClientW: document.documentElement.clientWidth
  };
})()
"""


def probe(url, width, height=900):
    for argv in (['open', url], ['set', 'viewport', str(width), str(height)],
                 ['eval', PROBE_JS]):
        p = subprocess.run(['agent-browser'] + argv, capture_output=True, text=True)
    raw = (p.stdout or '').strip()
    val = json.loads(raw)
    if isinstance(val, str):        # agent-browser prints a JSON string literal
        val = json.loads(val)
    return val


def verify(pages, widths):
    fails, notes = [], []
    filled = dict((n, p) for n, p in pages)['filled']
    url = 'file://' + filled

    a = probe(url, 1440)
    # Every band in the surface list has to actually be on the page, or the
    # "one colour" comparison passes on a subset and proves nothing — which is
    # exactly what happened while two mocks were missing their real classes.
    absent = [b['sel'] for b in a['bands'] if not b['present']]
    if absent:
        fails.append('[white-surface] not on the page: %s — the surface cannot be judged'
                     % absent)
    # ruling 2: the reading surface from the Specification cards to the sampling
    # band is one colour, and the change of colour happens only where it already
    # did — at the related-formulas grid.
    surface = [b for b in a['bands'] if b['sel'] != '.sf-fdetail-more']
    bgs = set(b['bg'] for b in surface if b['present'])
    if bgs != {'rgb(255, 255, 255)'}:
        fails.append('[white-surface] the reading bands are not one colour: %s'
                     % [(b['sel'], b['bg']) for b in a['bands']])
    else:
        notes.append('[white-surface] Specification, Formula & nutrition, content, FAQ and '
                     'sampling are all card-white; only .sf-fdetail-more is bg-light')
    if [b for b in a['bands'] if b['sel'] == '.sf-fdetail-more'][0]['bg'] != 'rgb(243, 246, 244)':
        fails.append('[white-surface] the related grid is no longer the light band')

    if a['contentPadding'] != '48px':
        fails.append('[geometry] content band padding-top is %r, not 48px' % a['contentPadding'])
    if a['blockGap'] != '48px':
        fails.append('[geometry] block-to-block margin is %r, not 48px' % a['blockGap'])
    else:
        notes.append('[geometry] 48px band padding and 48px between blocks, as specified')

    if a['headingSize'] == a['subtitleSize']:
        fails.append('[geometry] the packaging heading is no smaller than the prose headings')
    else:
        notes.append('[geometry] prose headings %s, packaging heading %s'
                     % (a['headingSize'], a['subtitleSize']))
    if a['h2InContent'] != 4:
        fails.append('[structure] %d h2 in the content band, expected 4 flat siblings'
                     % a['h2InContent'])
    else:
        notes.append('[structure] four h2 siblings, one per block — no nesting')

    if a['cartonCollapse'] != 'collapse':
        fails.append('[table] carton table is %r, not collapsed' % a['cartonCollapse'])
    if '999px' not in a['chipRadius']:
        fails.append('[chips] chip radius is %r, not the site pill' % a['chipRadius'])
    if a['docScrollW'] > a['docClientW'] + 1:
        fails.append('[overflow] the page scrolls sideways at 1440 (%d > %d)'
                     % (a['docScrollW'], a['docClientW']))

    # the sampling marker, and the one-to-four row behaviour
    if a['numBg'] != 'rgb(27, 77, 62)':
        fails.append('[marker] the step circle is %r, not the Forest token' % a['numBg'])
    elif a['numFg'] != 'rgb(255, 255, 255)':
        fails.append('[marker] the numeral is %r, not white' % a['numFg'])
    elif a['numBox']['w'] != 44 or a['numBox']['h'] != 44:
        fails.append('[marker] the circle is %sx%s, not 44x44' % (a['numBox']['w'], a['numBox']['h']))
    else:
        notes.append('[marker] 44x44 Forest circle with a white numeral, contrast-safe')
    if a['stepsPerRow'] != 1:
        fails.append('[steps] at 1440px the four steps occupy %d rows' % a['stepsPerRow'])
    else:
        notes.append('[steps] one row of four at 1440px (grid: %s)' % a['stepCols'])

    for w, want_rows in ((1101, 1), (768, 4), (480, 4)):
        b = probe(url, w)
        if b['stepsPerRow'] != want_rows:
            fails.append('[steps] at %dpx the steps occupy %d rows, expected %d'
                         % (w, b['stepsPerRow'], want_rows))
        if b['docScrollW'] > b['docClientW'] + 1:
            fails.append('[overflow] sideways scroll at %dpx (%d > %d)'
                         % (w, b['docScrollW'], b['docClientW']))
        if b['contentSidePad'] not in ('38px', '20px'):
            fails.append('[geometry] %dpx: content side padding is %r' % (w, b['contentSidePad']))
    if not [f for f in fails if f.startswith('[steps]')]:
        notes.append('[steps] still one row at 1101px; stacked 4 rows at 768 and 480')
    if not [f for f in fails if f.startswith('[overflow]')]:
        notes.append('[overflow] no sideways scroll at 1440 / 1101 / 768 / 480')

    # the empty state is what the live records serve: same surface, no headings
    e = probe('file://' + dict((n, p) for n, p in pages)['empty'], 1440)
    if e['h2InContent'] != 1:
        fails.append('[empty] the empty record renders %d h2, expected only the packaging one'
                     % e['h2InContent'])
    else:
        notes.append('[empty] the empty record renders one block — Packaging & Specifications')
    if set(b['bg'] for b in e['bands'] if b['present']) != {'rgb(255, 255, 255)', 'rgb(243, 246, 244)'}:
        fails.append('[empty] the surface changes colour in the empty state')

    subprocess.run(['agent-browser', 'close', '--all'], capture_output=True, text=True)
    print('=' * 72)
    for n in notes:
        print('  ok   ' + n)
    print('-' * 72)
    if fails:
        for f in fails:
            print('  FAIL ' + f)
        print('PREVIEW VERDICT: FAIL — %d problem(s)' % len(fails))
        return 1
    print('PREVIEW VERDICT: PASS — the layout matches the two rulings')
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--php', default=os.path.expanduser(
        '~/Library/Application Support/Local/lightning-services/php-8.2.29+0'
        '/bin/darwin-arm64/bin/php'))
    ap.add_argument('--shots', metavar='DIR',
                    help='screenshot both previews into DIR (via agent-browser)')
    ap.add_argument('--verify', action='store_true',
                    help='measure the rendered geometry in the browser')
    ap.add_argument('--widths', default='1440,1101,768,480')
    args = ap.parse_args()

    u = load_unit()
    # The three list-valued keys reach the renderer as JSON *text*, because that
    # is what get_post_meta() returns for a multi-select or a table field —
    # handing the renderer a PHP array instead produced an Array-to-string
    # warning and an empty sub-block, which is how this was caught.
    filled = dict(FILLED)
    for key in ('sf_formula_packaging_extra', 'sf_formula_colors', 'sf_formula_cartons'):
        filled[key] = json.dumps(filled[key])
    printer = PRINTER.replace('%FILLED%', json.dumps(filled).replace("'", "\\'"))
    src = (u.PREAMBLE + '\n' + u.extract_admin(u.read(u.ADMIN)) + '\n\n'
           + u.extract_region(u.read(u.FUNCTIONS)) + '\n' + printer)
    with open(PHP_SRC, 'w', encoding='utf-8') as fh:
        fh.write(src)
    p = subprocess.run([args.php, PHP_SRC], capture_output=True, text=True)
    os.remove(PHP_SRC)
    if p.returncode != 0 or p.stderr.strip() or 'Warning' in p.stdout:
        sys.stderr.write(p.stdout + p.stderr)
        return 1
    data = json.loads(p.stdout)

    ctx = context()
    written = []
    for state, label in (('filled', 'FILLED — synthetic data, every branch exercised'),
                         ('empty', 'EMPTY — all seven fields 0/21, the live state')):
        body = (ctx['above']
                + '\n<div style="padding:0 24px"><span class="__tag">5 · Detailed content '
                  '(new, H3)</span></div>\n' + data[state]['content']
                + '\n<div style="padding:0 24px"><span class="__tag">7 · Sampling (new, H3)</span></div>\n'
                + data[state]['sampling']
                + '\n' + ctx['below'])
        dest = os.path.join(BACKUP, 'b2d-h3-preview-%s.html' % state)
        with open(dest, 'w', encoding='utf-8') as fh:
            fh.write(page('preview — %s' % label, body))
        written.append(dest)

    for d in written:
        print('wrote %s (%d bytes)' % (d, os.path.getsize(d)))
    print('steps: %s' % ' | '.join(data['steps']))

    if args.shots:
        widths = [int(w) for w in args.widths.split(',') if w.strip()]
        shoot([(os.path.basename(d).replace('b2d-h3-preview-', '').replace('.html', ''), d)
               for d in written], args.shots, widths)
    if args.verify:
        return verify([(os.path.basename(d).replace('b2d-h3-preview-', '').replace('.html', ''), d)
                       for d in written], [1440, 1101, 768, 480])
    return 0


if __name__ == '__main__':
    sys.exit(main())

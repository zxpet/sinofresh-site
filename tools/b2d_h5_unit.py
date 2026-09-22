#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H5 — offline unit test for the schema readers.

Why this exists: three of the four properties this batch adds are invisible on
the gate's own captures.

  * `offers` returns null on all 21 formulas, because sf_formula_price_tiers is
    empty — the gate proves it emits nothing, not that it would emit the right
    thing;
  * `audience` is empty on the four dosage forms whose headline names no
    species, and empty on every formula record, so half the branch is unvisited;
  * the four `.sf-facts-mini` rows are read through a function that used to be
    called with a different argument (`Packaging formats`, not `Packaging`) —
    a typo there yields an empty value, which the schema silently drops, and an
    empty additionalProperty row looks exactly like a page that has none.

So the branches are exercised here, against the real function bodies, extracted
from the shipped files by name and brace matching rather than copied:

    sinofresh-theme/functions.php          the six new readers, verbatim
    sinofresh-theme/inc/formula-admin.php  sf_json_array / sf_json_rows, verbatim

The harness is generated into _backup/ (gitignored) and run with the PHP that
ships inside Local. The WordPress stand-ins are minimal on purpose: this proves
structure, branching and the empty-value rules; the pre-flight gate proves the
bytes WordPress actually serves.

usage:
    python3 tools/b2d_h5_unit.py [--php PATH] [--keep]

exit 0 = every assertion held; 1 = at least one failed (failing labels are
printed and the generated harness is kept for inspection).
"""
import argparse
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
THEME = os.path.join(ROOT, 'sinofresh-theme')
FUNCTIONS = os.path.join(THEME, 'functions.php')
ADMIN = os.path.join(THEME, 'inc', 'formula-admin.php')
OUT = os.path.join(ROOT, '_backup', 'b2d-h5-unit.php')

DEFAULT_PHP = os.path.expanduser(
    '~/Library/Application Support/Local/lightning-services/'
    'php-8.2.29+0/bin/darwin-arm64/bin/php')

# Content anchors, never line numbers: the file gains and loses comment lines
# every batch, and a line-numbered anchor would silently extract the wrong
# function (or nothing) while still reporting success.
H5_START = 'Batch H5 — the readers the schema generators share'
H5_END = '/**\n * Product JSON-LD (schema.org) for the eight dosage-form landing pages.'

NEEDED_FUNCTIONS = [
    'sinofresh_formula_alt_visuals',
    'sinofresh_formula_product_alt',
    'sinofresh_formula_facts_props',
    'sinofresh_formula_audience',
    'sinofresh_formula_related',
    'sinofresh_dosage_related',
    'sinofresh_formula_offers',
    'sinofresh_knows_about',
]
# Pre-existing readers the block above calls; extracted by name from the whole
# file, because they live outside the batch's block.
PREEXISTING = ['sinofresh_formula_spec_cell', 'sinofresh_formula_label']

DOSAGE = ['soft-chews', 'tablets', 'powders', 'pastes', 'drops', 'liquids',
          'fish-oil', 'dental-chews']
LABELS = {'soft-chews': 'Soft Chews', 'tablets': 'Tablets', 'powders': 'Powders',
          'pastes': 'Pastes', 'drops': 'Drops', 'liquids': 'Liquids',
          'fish-oil': 'Fish Oil', 'dental-chews': 'Dental Chews'}


def read(path):
    return open(path, encoding='utf-8').read()


def extract(src, needle):
    """The whole `function NAME(...) { ... }` block, by brace matching.

    Anchored on the function name rather than on line numbers, and raises when
    the name is absent: an extraction that quietly returns '' would make the
    harness fail with a parse error, which reads like a theme bug instead of a
    broken test.
    """
    at = src.find('function ' + needle + '(')
    if at < 0:
        raise SystemExit('functions.php: %s() not found' % needle)
    i = src.find('{', at)
    depth = 0
    while i < len(src):
        if src[i] == '{':
            depth += 1
        elif src[i] == '}':
            depth -= 1
            if depth == 0:
                return src[at:i + 1]
        i += 1
    raise SystemExit('functions.php: unbalanced braces in %s()' % needle)


def build():
    fn = read(FUNCTIONS)
    admin = read(ADMIN)

    a = fn.find(H5_START)
    b = fn.find(H5_END)
    if a < 0 or b < 0 or b < a:
        raise SystemExit('functions.php: the H5 reader block anchors moved')
    block = fn[fn.rfind('/* ---', 0, a):b]

    missing = [n for n in NEEDED_FUNCTIONS if ('function ' + n + '(') not in block]
    if missing:
        raise SystemExit('the H5 block is missing: %s' % ', '.join(missing))

    helpers = '\n\n'.join(extract(fn, n) for n in PREEXISTING)
    json2 = '\n\n'.join(extract(admin, n) for n in ['sf_json_array', 'sf_json_rows'])

    return HARNESS % {
        'theme': THEME,
        'helpers': helpers,
        'json2': json2,
        'block': block,
        'dosage': repr(DOSAGE).replace('[', 'array(').replace(']', ')'),
        'labels': 'array(' + ', '.join("'%s' => '%s'" % kv for kv in LABELS.items()) + ')',
    }


HARNESS = r'''<?php
/* GENERATED by tools/b2d_h5_unit.py — do not edit, do not commit.
   The three payload sections are extracted verbatim from the shipped files. */

/* ---- WordPress stand-ins ------------------------------------------------ */
define('ENT_QUOTES_STUB', true);
class WP_Post { public $ID; public $post_title; public $post_name;
  function __construct($id, $title, $name = '') { $this->ID = $id; $this->post_title = $title; $this->post_name = $name; } }

$GLOBALS['h5_meta'] = array();
$GLOBALS['h5_pages'] = array();
$GLOBALS['h5_queries'] = 0;
$GLOBALS['h5_posts'] = array();

function sanitize_title($s) { return trim(preg_replace('/-+/', '-', preg_replace('/[^a-z0-9]+/', '-', strtolower((string) $s))), '-'); }
function get_stylesheet_directory() { return '%(theme)s'; }
function get_post_meta($id, $key, $single = false) { return isset($GLOBALS['h5_meta'][(int) $id][$key]) ? $GLOBALS['h5_meta'][(int) $id][$key] : ''; }
function get_the_title($p) { return is_object($p) ? $p->post_title : (string) $p; }
function get_permalink($p) { return 'https://dev.zxpet.com/formulas/' . (is_object($p) ? $p->post_name : $p) . '/'; }
function get_page_by_path($path) {
	$GLOBALS['h5_queries']++;
	return isset($GLOBALS['h5_pages'][$path]) ? $GLOBALS['h5_pages'][$path] : null;
}
function get_posts($args) { $GLOBALS['h5_queries']++; return isset($GLOBALS['h5_posts'][json_encode($args)]) ? $GLOBALS['h5_posts'][json_encode($args)] : array(); }
function wp_strip_all_tags($s) { return strip_tags((string) $s); }
function esc_attr($s) { return htmlspecialchars((string) $s, ENT_QUOTES, 'UTF-8'); }
function esc_html($s) { return htmlspecialchars((string) $s, ENT_QUOTES, 'UTF-8'); }
function esc_url($s) { return (string) $s; }
function home_url($p = '/') { return 'https://dev.zxpet.com' . $p; }
function __($s, $d = null) { return $s; }

/* ---- extracted from inc/formula-admin.php ------------------------------- */
%(json2)s

/* ---- extracted from functions.php (pre-existing helpers) ---------------- */
%(helpers)s

/* ---- extracted from functions.php (the batch H5 block) ------------------ */
%(block)s

/* ---- the assertions ----------------------------------------------------- */
$fail = 0; $pass = 0;
function ok($label, $got, $want) {
	global $fail, $pass;
	$g = is_string($got) ? $got : json_encode($got, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
	$w = is_string($want) ? $want : json_encode($want, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
	if ($g === $w) { $pass++; echo "  ok   $label\n"; }
	else { $fail++; echo "  FAIL $label\n       got  $g\n       want $w\n"; }
}

$DOSAGE = %(dosage)s;
$LABEL  = %(labels)s;
foreach ($LABEL as $slug => $name) {
	$GLOBALS['h5_pages']['products/' . $slug] = new WP_Post(100, $name, $slug);
}

echo "== A. sinofresh_formula_facts_props (real templates) ==\n";
$props = sinofresh_formula_facts_props('soft-chews');
ok('soft-chews has 4 rows', count($props), 4);
ok('names in page order', array_column($props, 'name'),
	array('MOQ', 'Lead time', 'Certifications', 'Packaging'));
ok('MOQ value', $props[0]['value'], 'from 500–1,000 units');
ok('lead time value', $props[1]['value'], 'Typically 7–15 working days after packaging is ready');
ok('certifications value', $props[2]['value'], 'FDA, cGMP, ISO 9001, FSSC 22000, HACCP, BRC');
ok('packaging read by data-label, printed by visible label',
	strpos($props[3]['value'], 'Aluminum Stand-up Pouch') === 0, true);
ok('every row is a PropertyValue',
	in_array('PropertyValue', array_column($props, '@type'), true), true);
ok('a form with 4 rows', count(sinofresh_formula_facts_props('dental-chews')), 4);
ok('a real page without the band yields none',
	sinofresh_formula_facts_props('about'), array());
ok('an unknown form yields none', sinofresh_formula_facts_props('no-such-form'), array());

echo "== B. sinofresh_formula_audience (both sources) ==\n";
$types = function ($rows) { return array_column($rows, 'audienceType'); };
ok('soft-chews headline: Dogs & Cats', $types(sinofresh_formula_audience('soft-chews')), array('Dogs', 'Cats'));
ok('dental-chews headline: Dogs only', $types(sinofresh_formula_audience('dental-chews')), array('Dogs'));
ok('powders headline names no species', sinofresh_formula_audience('powders'), array());
ok('liquids headline names no species', sinofresh_formula_audience('liquids'), array());
ok('every entry is an Audience',
	array_column(sinofresh_formula_audience('tablets'), '@type'), array('Audience', 'Audience'));

$GLOBALS['h5_meta'][7] = array('sf_formula_species' => '["Dog","Cat"]');
ok('record wins over the headline', $types(sinofresh_formula_audience('powders', 7)), array('Dog', 'Cat'));
$GLOBALS['h5_meta'][8] = array('sf_formula_species' => '["Dog"]');
ok('a record with one species', $types(sinofresh_formula_audience('soft-chews', 8)), array('Dog'));
$GLOBALS['h5_meta'][9] = array('sf_formula_species' => '[]');
ok('an empty record falls back to the headline', $types(sinofresh_formula_audience('soft-chews', 9)), array('Dogs', 'Cats'));
$GLOBALS['h5_meta'][10] = array('sf_formula_species' => '["Dog","Dog"]');
ok('the record is not de-duplicated (it states its own list)',
	$types(sinofresh_formula_audience('powders', 10)), array('Dog', 'Dog'));
$GLOBALS['h5_meta'][11] = array('sf_formula_species' => 'junk{');
ok('junk record falls back to the headline', $types(sinofresh_formula_audience('tablets', 11)), array('Dogs', 'Cats'));

echo "== C. sinofresh_formula_offers (renderer first) ==\n";
ok('no rows -> null', sinofresh_formula_offers(array()), null);
ok('blank padding -> null', sinofresh_formula_offers(array(array('qty' => '', 'price' => ''))), null);
ok('a qty with no price -> null', sinofresh_formula_offers(array(array('qty' => '500-999 pcs', 'price' => ''))), null);
ok('a word in the price cell -> null', sinofresh_formula_offers(array(array('qty' => '500', 'price' => 'ask us'))), null);
ok('thousands separator is skipped, not misread',
	sinofresh_formula_offers(array(array('qty' => '1', 'price' => '1,200'))), null);
ok('a range is skipped', sinofresh_formula_offers(array(array('qty' => '500', 'price' => '1.20-1.40'))), null);
ok('zero is skipped', sinofresh_formula_offers(array(array('qty' => '500', 'price' => '0'))), null);

$one = sinofresh_formula_offers(array(array('qty' => '500 pcs', 'price' => '1.20')));
ok('one row: type', $one['@type'], 'AggregateOffer');
ok('one row: low = high', array($one['lowPrice'], $one['highPrice']), array(1.2, 1.2));
ok('one row: count', $one['offerCount'], 1);
ok('one row: currency stated', $one['priceCurrency'], 'USD');
ok('one row: minQuantity parsed off the range start', $one['priceSpecification'][0]['minQuantity']['value'], 500);
ok('one row: unitText', $one['priceSpecification'][0]['minQuantity']['unitText'], 'units');
ok('one row: spec is a UnitPriceSpecification', $one['priceSpecification'][0]['@type'], 'UnitPriceSpecification');

$two = sinofresh_formula_offers(array(
	array('qty' => '500-999 pcs', 'price' => '1.20'),
	array('qty' => '1000-4999 pcs', 'price' => '0.95'),
	array('qty' => '', 'price' => ''),
));
ok('two usable rows: low', $two['lowPrice'], 0.95);
ok('two usable rows: high', $two['highPrice'], 1.2);
ok('two usable rows: count ignores the padding row', $two['offerCount'], 2);
ok('two usable rows: minQuantity of the 1,000 tier', $two['priceSpecification'][1]['minQuantity']['value'], 1000);
ok('a currency-prefixed price parses', sinofresh_formula_offers(array(array('price' => '$1.20')))['lowPrice'], 1.2);
ok('a USD-suffixed price parses', sinofresh_formula_offers(array(array('price' => '1.20 USD')))['lowPrice'], 1.2);
ok('a USD-prefixed price parses', sinofresh_formula_offers(array(array('price' => 'USD 1.2')))['lowPrice'], 1.2);
ok('a row with no qty still yields a spec',
	isset(sinofresh_formula_offers(array(array('price' => '2.00')))['priceSpecification'][0]['price']), true);

echo "== D. sinofresh_formula_product_alt (one function, two carriers) ==\n";
$want = array(
	'soft-chews'   => 'SINO FRESH Soft Chews private label pet supplement product — brown star- and bone-shaped chews',
	'tablets'      => 'SINO FRESH Tablets private label pet supplement product — tan speckled round tablets',
	'powders'      => 'SINO FRESH Powders private label pet supplement product — green powder with a metal scoop',
	'pastes'       => 'SINO FRESH Pastes private label pet supplement product — white squeeze tube with a green cap',
	'drops'        => 'SINO FRESH Drops private label pet supplement product — amber glass dropper bottle',
	'liquids'      => 'SINO FRESH Liquids private label pet supplement product — white bottle with a flip-top cap and measuring cup',
	'fish-oil'     => 'SINO FRESH Fish Oil private label pet supplement product — golden oval softgel capsules',
	'dental-chews' => 'SINO FRESH Dental Chews private label pet supplement product — dark ridged stick chews',
);
foreach ($want as $slug => $expect) {
	ok('alt ' . $slug, sinofresh_formula_product_alt($slug), $expect);
}
ok('the alt function and the map agree on 8 forms', count(sinofresh_formula_alt_visuals()), 8);
ok('a form with no clause keeps the old alt',
	sinofresh_formula_product_alt('about'), 'SINO FRESH About private label pet supplement product');

echo "== E. sinofresh_knows_about ==\n";
$ka = sinofresh_knows_about();
ok('ten topics', count($ka), 10);
ok('the eight dosage forms come first', array_slice($ka, 0, 8), array_values($LABEL));
ok('the two service lines', array_slice($ka, 8), array('Pet Supplement OEM/ODM Manufacturing', 'Private Label Pet Supplements'));
ok('no duplicates', count(array_unique($ka)), 10);
$before = $GLOBALS['h5_queries'];
sinofresh_knows_about();
ok('memoised: no second round of page lookups', $GLOBALS['h5_queries'] - $before, 0);

echo "== F. sinofresh_dosage_related (read out of the template) ==\n";
$sib = sinofresh_dosage_related('soft-chews');
ok('seven siblings', count($sib), 7);
ok('never lists itself', in_array('Soft Chews', array_column($sib, 'name'), true), false);
ok('every entry is a Product', array_unique(array_column($sib, '@type')), array('Product'));
ok('carries a name and a url',
	array_keys($sib[0]), array('@type', 'name', 'url'));
ok('order follows the tile grid',
	array_column($sib, 'name'), array('Tablets', 'Powders', 'Pastes', 'Drops', 'Liquids', 'Fish Oil', 'Dental Chews'));
ok('a real page with no tile grid yields none', sinofresh_dosage_related('about'), array());
ok('an unknown form yields none', sinofresh_dosage_related('no-such-form'), array());

echo "== G. sinofresh_formula_related ==\n";
ok('an empty form yields none', sinofresh_formula_related(''), array());
$GLOBALS['h5_posts'][json_encode(array(
	'post_type' => 'sf_formula', 'post_status' => 'publish', 'posts_per_page' => 4,
	'orderby' => array('menu_order' => 'ASC', 'title' => 'ASC'), 'ignore_sticky_posts' => true,
	'no_found_rows' => true,
	'tax_query' => array(array('taxonomy' => 'sf_formula_form', 'field' => 'slug', 'terms' => 'soft-chews')),
	'post__not_in' => array(161),
))] = array(new WP_Post(159, 'Calming Soft Chews', 'calming-soft-chews'));
$rel = sinofresh_formula_related('soft-chews', 161, 4);
ok('returns what the grid query returns', count($rel), 1);
ok('as a Product with a name', array($rel[0]['@type'], $rel[0]['name']), array('Product', 'Calming Soft Chews'));
ok('with the formula permalink', $rel[0]['url'], 'https://dev.zxpet.com/formulas/calming-soft-chews/');

echo "\n";
printf("H5 UNIT: %%s — %%d passed, %%d failed\n", $fail ? 'FAIL' : 'PASS', $pass, $fail);
exit($fail ? 1 : 0);
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--php', default=None)
    ap.add_argument('--keep', action='store_true')
    args = ap.parse_args()

    php = args.php or DEFAULT_PHP
    if not os.path.exists(php):
        found = shutil.which('php')
        if not found:
            raise SystemExit('no PHP found; pass --php PATH')
        php = found

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write(build())

    p = subprocess.run([php, OUT], capture_output=True, text=True)
    sys.stdout.write(p.stdout)
    sys.stderr.write(p.stderr)
    if p.returncode and args.keep:
        print('harness kept at %s' % OUT)
    return p.returncode


if __name__ == '__main__':
    sys.exit(main())

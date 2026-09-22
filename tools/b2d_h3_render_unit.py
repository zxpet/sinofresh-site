#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H3 — offline unit test for the content and sampling renderers.

Why this exists: every meta field the new content band reads is 0/21 on the
live database (the sales team has not started backfilling), so on the gate's
own captures the renderer only ever walks its EMPTY branch. A page-level gate
therefore cannot tell a working renderer from one that returns '' for
everything — both produce identical bytes on all 42 detail records.

So the branches are exercised here instead, against the real function bodies,
extracted from the shipped files rather than copied:

  sinofresh-theme/functions.php          the nine new functions, verbatim
  sinofresh-theme/inc/formula-admin.php  sf_json_array / sf_json_rows, verbatim

The harness is generated into _backup/ (gitignored) and run with the local
PHP that ships inside Local. WordPress stand-ins are minimal on purpose: this
proves structure, branching, escaping and the empty-value rules, while the
pre-flight gate proves the bytes WordPress actually serves.

usage:
    python3 tools/b2d_h3_render_unit.py [--php PATH] [--keep]

exit 0 = every assertion held; 1 = at least one failed (the failing labels are
printed, and the generated harness is kept for inspection).
"""

import argparse
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
THEME = os.path.join(ROOT, 'sinofresh-theme')
OUT = os.path.join(ROOT, '_backup', 'b2d-h3-render-unit.php')

FUNCTIONS = os.path.join(THEME, 'functions.php')
ADMIN = os.path.join(THEME, 'inc', 'formula-admin.php')

# Start and end of the H3 block, by content — never by line number.
START = '/**\n * [sf_formula_content] — the detailed content area (batch H3).'
END = "add_shortcode('sf_formula_sampling', 'sinofresh_formula_sampling');"

# Every function the block must define. The count is asserted, so a rename or
# a partial extraction fails here instead of silently testing half a band.
WANT_FUNCS = [
    'sinofresh_formula_content',
    'sinofresh_formula_content_block',
    'sinofresh_formula_content_spec',
    'sinofresh_formula_content_chips',
    'sinofresh_formula_content_cartons',
    'sinofresh_container_label',
    'sinofresh_formula_storage_line',
    'sinofresh_sampling_steps',
    'sinofresh_formula_sampling',
]

PREAMBLE = r"""<?php
/**
 * WordPress stand-ins, shared by this tool and tools/b2d_h3_preview.py.
 * The shipped function bodies are appended after them, extracted from the
 * theme rather than copied, so neither tool can drift from the code it tests.
 */
$GLOBALS['SF_META']     = array();
$GLOBALS['SF_SINGULAR'] = true;
$GLOBALS['SF_ID']       = 21;

function get_post_meta($post_id, $key, $single = false) {
	return isset($GLOBALS['SF_META'][$key]) ? $GLOBALS['SF_META'][$key] : '';
}
function is_singular($t = '') { return (bool) $GLOBALS['SF_SINGULAR']; }
function get_queried_object_id() { return (int) $GLOBALS['SF_ID']; }
function add_shortcode($tag, $cb) { $GLOBALS['SF_SHORTCODES'][$tag] = $cb; }
function esc_html($v) { return htmlspecialchars((string) $v, ENT_QUOTES, 'UTF-8', false); }
# The container library is option-backed in WordPress; the label set is the
# shipped default (sf_default_containers) plus one custom row, so a slug that is
# in the library and one that is not are both covered.
function sf_container_library() {
	return array(
		array('slug' => 'round',  'label' => 'Round',  'attachment_id' => 0),
		array('slug' => 'pouch',  'label' => 'Pouch',  'attachment_id' => 0),
		array('slug' => 'tube',   'label' => 'Tube',   'attachment_id' => 0),
		array('slug' => 'retort', 'label' => '',       'attachment_id' => 0),
	);
}

"""

ASSERTIONS = r"""
/* ------------------------------------------------------------------ harness */
$GLOBALS['PASS'] = 0; $GLOBALS['FAIL'] = 0; $GLOBALS['LABELS'] = array();
function chk($label, $cond, $extra = '') {
	if ($cond) { $GLOBALS['PASS']++; echo "  ok   $label\n"; return; }
	$GLOBALS['FAIL']++; $GLOBALS['LABELS'][] = $label;
	echo "  FAIL $label" . ($extra !== '' ? "  [$extra]" : '') . "\n";
}
function render($meta) {
	$GLOBALS['SF_META'] = $meta;
	return sinofresh_formula_content();
}
function render_sampling() {
	$GLOBALS['SF_META'] = array();
	return sinofresh_formula_sampling();
}

echo "=== 1. the empty record (the live state: every field 0/21) =========\n";
$html = render(array());
chk('the band still renders (Storage is not a field)', strpos($html, '<section class="sf-fdetail-content">') === 0);
chk('no heading for an empty field', strpos($html, 'Recommended For') === false
	&& strpos($html, 'Use Cases') === false && strpos($html, "Who It's For") === false);
chk('Packaging & Specifications is the only block', substr_count($html, 'sf-fdetail-content__block') === 1);
chk('Storage is the only sub-block', substr_count($html, 'sf-fdetail-content__spec"') === 1);
# Pinned to the literal, never to sinofresh_formula_storage_line()'s own return
# value: comparing the page against the function that produced it passes no
# matter what the function says, which is the one thing this has to catch.
chk('Storage label + the exact line are on the page',
	strpos($html, '>Storage</p>') !== false
	&& strpos($html, '<p class="sf-fdetail-content__prose">Cool, dry place out of direct '
		. 'sunlight; keep the container closed after opening.</p>') !== false);
chk('the storage line is one hardcoded sentence',
	sinofresh_formula_storage_line() === 'Cool, dry place out of direct sunlight; '
		. 'keep the container closed after opening.');
chk('no carton table', strpos($html, '__cartons') === false);
chk('no chips list', strpos($html, '__chips') === false);
chk('exactly one h2', substr_count($html, '<h2') === 1);

echo "=== 2. the three prose blocks ======================================\n";
$html = render(array(
	'sf_formula_recommended_for' => 'For dogs with stiff joints.',
	'sf_formula_who_for'         => 'Brands launching a joint range.',
));
chk('Recommended For renders as a paragraph',
	strpos($html, '<h2 class="sf-fdetail-content__heading">Recommended For</h2>'
		. '<p class="sf-fdetail-content__prose">For dogs with stiff joints.</p>') !== false);
chk('the two prose fields render, in order',
	strpos($html, 'Recommended For') < strpos($html, 'Who It'));
# esc_html() escapes the apostrophe (ENT_QUOTES), as it does for every other
# label the theme renders. What matters is that the heading reads back as
# "Who It's For" once the entity is decoded — asserted both ways.
chk('the label escapes to &#039; and decodes back to an apostrophe',
	strpos($html, '>Who It&#039;s For</h2>') !== false
	&& html_entity_decode('Who It&#039;s For', ENT_QUOTES, 'UTF-8') === "Who It's For");
chk('Use Cases stays absent', strpos($html, 'Use Cases') === false);
chk('two prose h2 plus the packaging h2', substr_count($html, '<h2') === 3);

echo "=== 3. Use Cases: one line reads as a sentence, more read as a list ==\n";
$one = render(array('sf_formula_use_cases' => 'Joint support chews for senior dogs.'));
chk('one line -> paragraph, no bullet',
	strpos($one, '<p class="sf-fdetail-content__prose">Joint support chews for senior dogs.</p>') !== false
	&& strpos($one, '__list') === false);
$many = render(array('sf_formula_use_cases' => "Daily joint support\nPost-surgery recovery\n\nSenior mobility\n"));
chk('three non-empty lines -> an unordered list of three',
	substr_count($many, 'sf-fdetail-content__item') === 3);
chk('blank lines are dropped, not rendered as empty items',
	strpos($many, '<li class="sf-fdetail-content__item"></li>') === false);
chk('items keep their order',
	strpos($many, 'Daily joint support') < strpos($many, 'Post-surgery recovery')
	&& strpos($many, 'Post-surgery recovery') < strpos($many, 'Senior mobility'));
$crlf = render(array('sf_formula_use_cases' => "One\r\nTwo"));
chk('CRLF splits too (two items)', substr_count($crlf, '__item') === 2);
$spaces = render(array('sf_formula_use_cases' => "   \n\t\n"));
chk('a whitespace-only field renders nothing', strpos($spaces, 'Use Cases') === false);

echo "=== 4. Packaging: container, extra packaging, colours ===============\n";
$html = render(array('sf_formula_container' => 'pouch'));
chk('a known slug resolves to the library label',
	strpos($html, '>Pouch</li>') !== false && strpos($html, '>pouch</li>') === false);
chk('its own label is rendered', strpos($html, '>Container Options</p>') !== false);
$html = render(array('sf_formula_container' => 'stand-up'));
chk('an unknown slug falls back to the raw value, not to nothing',
	strpos($html, '>stand-up</li>') !== false);
$html = render(array('sf_formula_container' => 'retort'));
chk('a library row with a blank label falls back to the slug',
	strpos($html, '>retort</li>') !== false);
$html = render(array('sf_formula_container' => ''));
chk('no slug -> no Container Options sub-block',
	strpos($html, 'Container Options') === false);

$html = render(array(
	'sf_formula_packaging_extra' => json_encode(array('Stick pack', 'Sachet')),
	'sf_formula_colors'          => json_encode(array('Natural', '')), 
));
chk('extra packaging renders two chips', substr_count($html, '>Stick pack</li>') === 1
	&& substr_count($html, '>Sachet</li>') === 1);
chk('an empty string inside the array is not a chip',
	substr_count($html, '<li class="sf-fdetail-content__chip">') === 3);
chk('colours render under their own label', strpos($html, '>Color Options</p>') !== false
	&& strpos($html, '>Natural</li>') !== false);
$html = render(array('sf_formula_packaging_extra' => json_encode(array())));
chk('an empty array -> the sub-block disappears, not an empty list',
	strpos($html, 'Additional Packaging') === false);
$html = render(array('sf_formula_colors' => 'not json'));
chk('malformed JSON is treated as absent', strpos($html, 'Color Options') === false);

echo "=== 5. Carton dimensions ==========================================\n";
$rows = json_encode(array(
	array('count' => '60 pcs', 'boxes' => '12', 'size' => '40x30x25'),
	array('count' => '',       'boxes' => '',   'size' => ''),
	array('count' => '',       'boxes' => '24', 'size' => ''),
));
$html = render(array('sf_formula_cartons' => $rows));
chk('a half-filled row is kept', strpos($html, '>24</td>') !== false);
# three input rows: one complete, one fully blank, one half-filled. Two
# survive, so two body rows of three cells under one header row.
chk('a fully blank row is dropped, the other two survive',
	substr_count($html, '<tr>') === 3 && substr_count($html, '<td>') === 6);
chk('the three admin labels are the column headers',
	strpos($html, '>Pack count</th>') !== false && strpos($html, '>Units per carton</th>') !== false
	&& strpos($html, '>Carton size (cm)</th>') !== false);
chk('scoped column headers', substr_count($html, 'scope="col"') === 3);
$html = render(array('sf_formula_cartons' => json_encode(array(array('count' => '', 'boxes' => '', 'size' => '')))));
chk('all-blank rows -> no table and no label',
	strpos($html, 'Carton Dimensions') === false && strpos($html, '__cartons') === false);

echo "=== 6. Escaping ===================================================\n";
$html = render(array('sf_formula_recommended_for' => 'A & B <script>alert(1)</script> "quoted"'));
chk('markup in a prose field is escaped',
	strpos($html, '<script>alert(1)</script>') === false && strpos($html, '&lt;script&gt;') !== false);
chk('the ampersand is escaped', strpos($html, 'A &amp; B') !== false);
$html = render(array('sf_formula_packaging_extra' => json_encode(array('<b>x</b>'))));
chk('markup in a chip is escaped', strpos($html, '<b>x</b>') === false
	&& strpos($html, '&lt;b&gt;x&lt;/b&gt;') !== false);

echo "=== 7. Sameness of the two bands' contracts ========================\n";
$GLOBALS['SF_SINGULAR'] = false;
chk('the content band returns nothing outside a formula', sinofresh_formula_content() === '');
chk('the sampling band returns nothing outside a formula', sinofresh_formula_sampling() === '');
$GLOBALS['SF_SINGULAR'] = true;
$GLOBALS['SF_ID'] = 0;
chk('the content band returns nothing without a queried object', sinofresh_formula_content() === '');
$GLOBALS['SF_ID'] = 21;

echo "=== 8. The sampling band ==========================================\n";
$steps = sinofresh_sampling_steps();
chk('four steps', count($steps) === 4);
chk('every step has a title and a text',
	count(array_filter($steps, function ($s) {
		return trim($s['title']) !== '' && trim($s['text']) !== '';
	})) === 4);
chk('the timeline appears once, in the closing line only',
	substr_count(implode(' ', array_column($steps, 'text')), '3-7') === 0);
$html = render_sampling();
chk('it emits its own section', strpos($html, '<section class="sf-sampling">') === 0);
chk('the heading is the schema name', strpos($html, '<h2 class="sf-sampling__title">How Sampling Works</h2>') !== false);
chk('an ordered list of four steps', substr_count($html, '<li class="sf-sampling__step">') === 4
	&& strpos($html, '<ol class="sf-sampling__steps">') !== false);
chk('the numerals are 1,2,3,4 and are real text',
	strpos($html, '<span class="sf-sampling__num">1</span>') !== false
	&& strpos($html, '<span class="sf-sampling__num">4</span>') !== false);
chk('no aria-hidden on the numeral (it is the only ordering cue)',
	strpos($html, 'aria-hidden') === false);
chk('each step title and text is rendered',
	strpos($html, '>Submit Inquiry</h3>') !== false
	&& strpos($html, '>Sampling &amp; Quality Check</h3>') !== false
	&& strpos($html, 'Our lab produces your sample and runs a full quality check.') !== false);
chk('the closing line carries the timeline',
	strpos($html, '<p class="sf-sampling__note">Typically 3-7 working days.</p>') !== false);
chk('the api contract the HowTo schema reads is this function',
	array_column($steps, 'title') === array('Submit Inquiry', 'Confirm Details',
		'Sampling & Quality Check', 'Ship & Evaluate'));

echo "=== 9. Shortcode registration ======================================\n";
chk('sf_formula_content is registered',
	isset($GLOBALS['SF_SHORTCODES']['sf_formula_content'])
	&& $GLOBALS['SF_SHORTCODES']['sf_formula_content'] === 'sinofresh_formula_content');
chk('sf_formula_sampling is registered',
	isset($GLOBALS['SF_SHORTCODES']['sf_formula_sampling'])
	&& $GLOBALS['SF_SHORTCODES']['sf_formula_sampling'] === 'sinofresh_formula_sampling');

echo "------------------------------------------------------------------------\n";
printf("  %d passed, %d failed\n", $GLOBALS['PASS'], $GLOBALS['FAIL']);
if ($GLOBALS['FAIL']) {
	echo "  FAILING: " . implode(' | ', $GLOBALS['LABELS']) . "\n";
	exit(1);
}
echo "UNIT VERDICT: PASS\n";
"""

# The full harness: stubs, then the two extracted bodies, then the assertions.
STUBS = PREAMBLE + '\n%ADMIN_JSON%\n\n%REGION%\n' + ASSERTIONS


def read(path):
    with open(path, encoding='utf-8') as fh:
        return fh.read()


def extract_region(src):
    i = src.find(START)
    if i < 0:
        raise SystemExit('the H3 block start marker is gone from functions.php')
    j = src.find(END, i)
    if j < 0:
        raise SystemExit('the H3 block end marker is gone from functions.php')
    region = src[i:j + len(END)]
    missing = [f for f in WANT_FUNCS if ('function %s(' % f) not in region]
    if missing:
        raise SystemExit('extracted block is missing: %s' % ', '.join(missing))
    if region.count('\nfunction ') != len(WANT_FUNCS):
        raise SystemExit('extracted block defines %d functions, expected %d'
                         % (region.count('\nfunction '), len(WANT_FUNCS)))
    return region


def extract_admin(src):
    out = []
    for name in ('sf_json_array', 'sf_json_rows'):
        m = re.search(r'/\*\*[^\n]*\n(?:[^\n]*\n)*?function %s\(' % name, src)
        i = src.find('function %s(' % name)
        if i < 0:
            raise SystemExit('inc/formula-admin.php no longer defines %s()' % name)
        j = src.find('\n}', i)
        if j < 0:
            raise SystemExit('could not find the end of %s()' % name)
        out.append(src[i:j + 2])
    return '\n\n'.join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--php', default=os.path.expanduser(
        '~/Library/Application Support/Local/lightning-services/php-8.2.29+0'
        '/bin/darwin-arm64/bin/php'))
    ap.add_argument('--keep', action='store_true')
    ap.add_argument('--negctl', action='store_true',
                    help='mutate the extracted region and require a named failure')
    args = ap.parse_args()

    if not os.path.exists(args.php):
        raise SystemExit('no PHP at %s (pass --php)' % args.php)

    admin = extract_admin(read(ADMIN))
    region = extract_region(read(FUNCTIONS))

    if args.negctl:
        return negctl(admin, region, args.php)

    rc, out = run_harness(admin, region, args.php)
    sys.stdout.write(out)
    if not args.keep and rc == 0 and os.path.exists(OUT):
        os.remove(OUT)
    return rc


def build(admin, region):
    return (STUBS
            .replace('%ADMIN_JSON%', admin)
            .replace('%REGION%', region))


def run_harness(admin, region, php, dest=OUT):
    harness = build(admin, region)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, 'w', encoding='utf-8') as fh:
        fh.write(harness)
    p = subprocess.run([php, '-d', 'error_reporting=E_ALL', dest],
                       capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


# Each control breaks one behaviour the renderer must have, and is aimed at the
# line that actually decides it. That placement matters: with the empty-value
# rule written once in _spec and once in each caller, a mutation of the wrong
# layer changes nothing and would read as a broken control.
NEGCTL = [
    ('empty-prose-field-still-rendered',
     "	if ($value !== '') {\n\t\t$blocks .= sinofresh_formula_content_block('Recommended For',",
     "	if (true) {\n\t\t$blocks .= sinofresh_formula_content_block('Recommended For',", 1,
     'Recommended For would be rendered on a record with no value'),
    ('spec-guard-removed',
     "function sinofresh_formula_content_spec($label, $inner) {\n"
     "\t$inner = (string) $inner;\n\tif (trim($inner) === '') {\n\t\treturn '';\n\t}\n",
     "function sinofresh_formula_content_spec($label, $inner) {\n\t$inner = (string) $inner;\n", 1,
     'an empty chips list would leave its label behind'),
    ('storage-line-emptied',
     "return 'Cool, dry place out of direct sunlight; keep the container closed after opening.';",
     "return '';", 1,
     'the band would collapse, and with it the two guards that keep it whole'),
    ('numeral-not-rendered', ". '<span class=\"sf-sampling__num\">' . (int) $n . '</span>'",
     ". '<span class=\"sf-sampling__num\"></span>'", 1,
     'the step numerals would disappear'),
    ('single-use-case-sent-to-the-list-branch', 'count($items) === 1',
     'count($items) === 99', 1,
     'one use case would render as a one-item bullet list'),
    ('content-shortcode-unregistered',
     "add_shortcode('sf_formula_content', 'sinofresh_formula_content');", '', 1,
     'the content band would never render at all'),
]


def negctl(admin, region, php):
    print('=== negative controls — every mutation must produce a NAMED failure ===')
    missed = []
    for name, find, repl, count, means in NEGCTL:
        if region.count(find) < count:
            print('  %-42s HARNESS STALE — pattern not found' % name)
            missed.append(name)
            continue
        mutated = region.replace(find, repl, count)
        if mutated == region:
            print('  %-42s HARNESS STALE — mutation was a no-op' % name)
            missed.append(name)
            continue
        rc, out = run_harness(admin, mutated, php, dest=OUT + '.neg.php')
        named = [ln.strip() for ln in out.splitlines() if ln.strip().startswith('FAIL ')]
        ok = rc != 0 and bool(named)
        print('  %-42s %s  %s' % (name, 'CAUGHT (as required)' if ok else 'NOT CAUGHT',
                                  (named[0][5:60] if named else 'no named failure')))
        if not ok:
            missed.append(name)
        print('  %-42s    means: %s' % ('', means))
    for stale in (OUT + '.neg.php',):
        if os.path.exists(stale):
            os.remove(stale)
    print('-' * 72)
    print('  %d/%d controls caught' % (len(NEGCTL) - len(missed), len(NEGCTL)))
    if missed:
        print('  MISSED: %s' % missed)
        return 1
    print('NEGCTL VERDICT: PASS')
    return 0


if __name__ == '__main__':
    sys.exit(main())

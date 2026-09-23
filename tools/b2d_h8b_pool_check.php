<?php
/* Batch H8b local check — the pool side of "Shape and Container follow the
 * dosage form".
 *
 * Standalone on purpose: it stubs the three WordPress functions
 * inc/formula-pools.php actually calls and requires nothing else, so a broken
 * stub cannot be mistaken for a broken pool (the batch H7g render harness has
 * to stub ~200 functions to load functions.php, which is why it is a smoke
 * test and not a proof).
 *
 * What it proves, and why each clause is here:
 *
 *   1. every dosage form has a non-empty shape pool ending in Custom — the
 *      renderer drops the whole group when the pool is empty, so an empty pool
 *      is a deleted group, not an empty one;
 *   2. the eight soft-chew shapes do not appear on a powder, a drop, a liquid,
 *      a paste or a fish oil — this is the defect the batch exists to remove,
 *      stated as a negative so it cannot pass by accident;
 *   3. the NAME follows the pool (Appearance / Texture / Form), which is half
 *      the change and the half a byte-diff alone would not explain;
 *   4. the option builder emits labels as values, exactly one marked Custom,
 *      and no images on today's data (both libraries ship every
 *      attachment_id at 0) — "no images" is asserted, not assumed, so the day
 *      an image is uploaded this check tells you the render changed;
 *   5. matching a pool label to a library row is case-insensitive and returns
 *      the picture when there is one.
 *
 * Run: php tools/b2d_h8b_pool_check.php     (exit 0 = all clauses hold)
 */

$ROOT = dirname(__DIR__);

function sanitize_title($s) { return strtolower(preg_replace('/[^A-Za-z0-9]+/', '-', (string) $s)); }
function wp_get_attachment_image_url($id, $size = '') { return 'https://example.test/img-' . (int) $id . '.jpg'; }

require $ROOT . '/sinofresh-theme/inc/formula-pools.php';

$fail = 0;
function ok($label, $cond, $note = '') {
	global $fail;
	if (!$cond) { $fail++; }
	printf("%-4s %s%s\n", $cond ? 'ok' : 'FAIL', $label, $note !== '' ? '  [' . $note . ']' : '');
}

$forms = array_keys(sf_formula_pools());

/* ---- 1. every form answers, and answers with a Custom ---- */
foreach ($forms as $form) {
	$pool = sf_formula_field_pool($form, 'shape');
	ok('shape pool for ' . $form . ' is non-empty', count($pool) > 0);
	ok('  ...and ends in Custom', end($pool) === 'Custom', (string) end($pool));
	ok('  ...and repeats no label', count($pool) === count(array_unique($pool)));
}

/* ---- 2. the soft-chew shapes stay on the soft chews ---- */
foreach (array('Bone', 'Heart', 'Star', 'Paw', 'Cylinder') as $soft) {
	foreach (array('powders', 'drops', 'liquids', 'pastes', 'fish-oil') as $form) {
		ok($soft . ' is not offered on ' . $form, !in_array($soft, sf_formula_field_pool($form, 'shape'), true));
	}
}
/* ...and the reverse: the shapes a soft chew is sold in are all still there. */
foreach (array('Bone', 'Round', 'Square', 'Heart', 'Star', 'Paw', 'Cylinder') as $soft) {
	ok($soft . ' is still offered on soft-chews', in_array($soft, sf_formula_field_pool('soft-chews', 'shape'), true));
}

/* ---- 3. the name follows the pool ---- */
$want_label = array(
	'soft-chews' => 'Shape', 'tablets' => 'Shape', 'dental-chews' => 'Shape',
	'pastes' => 'Texture', 'powders' => 'Appearance', 'drops' => 'Appearance',
	'liquids' => 'Appearance', 'fish-oil' => 'Form',
);
foreach ($want_label as $form => $want) {
	ok($form . ' calls it ' . $want, sf_formula_field_pool_label($form, 'shape') === $want,
		(string) sf_formula_field_pool_label($form, 'shape'));
}

/* ---- 4. the option builder ---- */
$library = array(
	array('slug' => 'bone', 'label' => 'Bone', 'attachment_id' => 0),
	array('slug' => 'custom', 'label' => 'Custom', 'attachment_id' => 0),
);
foreach ($forms as $form) {
	$opts = sf_formula_library_options(sf_formula_field_pool($form, 'shape'), $library);
	$vals = array();
	$marked = 0;
	$images = 0;
	foreach ($opts as $o) {
		$vals[] = $o['value'];
		ok('  option value is its label on ' . $form, $o['value'] === $o['label'], (string) $o['value']);
		if (!empty($o['custom'])) { $marked++; }
		if ($o['image'] !== '') { $images++; }
	}
	ok('  ' . $form . ' marks exactly one Custom', $marked === 1, (string) $marked);
	ok('  ' . $form . ' carries no image on today\'s data', $images === 0, (string) $images);
	ok('  ' . $form . ' option order equals pool order', $vals === sf_formula_field_pool($form, 'shape'));
}

/* ---- 5. label -> picture ---- */
ok('a label no row spells has no picture', sf_formula_pool_option_image($library, 'Fine Powder') === '');
ok('a row with no attachment has no picture', sf_formula_pool_option_image($library, 'bone') === '');
ok('matching ignores case', sf_formula_pool_option_image(
	array(array('slug' => 'bone', 'label' => 'BoNe', 'attachment_id' => 7)), 'bone'
) === 'https://example.test/img-7.jpg');
ok('an empty label matches nothing', sf_formula_pool_option_image($library, '') === '');
ok('a non-array library is not a fatal', sf_formula_pool_option_image(null, 'Bone') === '');

printf("\n%s  %d clause(s) failed\n", $fail === 0 ? 'PASS' : 'FAIL', $fail);
exit($fail === 0 ? 0 : 1);

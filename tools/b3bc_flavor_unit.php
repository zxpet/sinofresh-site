<?php
/**
 * Batch 3b close-out — unit test for the Custom-dedup helper (item 3).
 *
 * This does not re-implement the rule in the test; it lifts the two functions
 * out of sinofresh-theme/functions.php and evals that slice, so what runs
 * here is the shipped source, byte for byte. A test that retyped the helper
 * would pass while the theme kept the bug.
 *
 * The slice is bounded by two markers that are stable across edits: the
 * opener `function sf_formula_custom_option` and the helper's one-tab
 * `\treturn $options;\n}`. The indented `return $options;` inside the helper's
 * foreach is three tabs deep, so it cannot be mistaken for the end.
 *
 * Usage:  php tools/b3bc_flavor_unit.php
 */

$theme = dirname(__DIR__) . '/sinofresh-theme/functions.php';
$src   = file_get_contents($theme);
if ($src === false) {
	fwrite(STDERR, "cannot read $theme\n");
	exit(2);
}

$start = strpos($src, 'function sf_formula_custom_option');
$end   = $start === false ? false : strpos($src, "\treturn \$options;\n}", $start);
if ($start === false || $end === false) {
	fwrite(STDERR, "slice markers not found in functions.php -- the helper moved or was renamed\n");
	exit(2);
}
$end  += strlen("\treturn \$options;\n}");
$slice = substr($src, $start, $end - $start);

/* The slice must contain BOTH functions and nothing but them. If a later edit
   lands a third function between the two, the slice would silently start
   testing more than the helper, so the count is asserted rather than assumed. */
if (substr_count($slice, 'function ') !== 2) {
	fwrite(STDERR, "slice holds " . substr_count($slice, 'function ')
		. " functions, expected 2 -- widen the harness before trusting it\n");
	exit(2);
}
eval($slice);

$fail = 0;
$n    = 0;
function ck($label, $cond, $got) {
	global $fail, $n;
	$n++;
	if ($cond) {
		printf("  PASS  %s\n", $label);
	} else {
		$fail++;
		printf("  FAIL  %s\n        got: %s\n", $label,
			is_string($got) ? $got : json_encode($got));
	}
}

/** What the renderer reads off a list: the word count, and who owns the box. */
function shape($options) {
	$marked = array();
	foreach ($options as $i => $o) {
		if (!empty($o['custom'])) {
			$marked[] = $i;
		}
	}
	$labels = array();
	foreach ($options as $o) {
		$labels[] = $o['label'];
	}
	return array('count' => count($options), 'marked' => $marked, 'labels' => $labels);
}

echo "== the shipped helper, run against the shapes the 5 groups build ==\n";

/* The real record: post 158 / joint-support-soft-chews. Its meta carries
   "Custom" as the 8th flavour, which is what made the page draw nine chips. */
$p158 = array('Chicken', 'Beef', 'Lamb', 'Salmon', 'Peanut Butter', 'Cheese',
	'Mint', 'Custom');
$opts = array();
foreach ($p158 as $f) {
	$opts[] = array('value' => $f, 'label' => $f, 'image' => '', 'note' => '');
}
$s = shape(sf_formula_options_with_custom($opts));
ck('post 158 flavour list: 8 options, not 9', $s['count'] === 8, $s);
ck('post 158 flavour list: exactly one chip owns the box',
	count($s['marked']) === 1, $s['marked']);
ck('post 158 flavour list: that chip is the one spelled Custom',
	isset($s['marked'][0]) && $s['labels'][$s['marked'][0]] === 'Custom', $s);
ck('post 158 flavour list: the record spelling stays, in place',
	$s['labels'] === $p158, $s['labels']);

/* A record that does not spell Custom is untouched but for the appended one. */
$opts = array();
foreach (array('Chicken', 'Beef') as $f) {
	$opts[] = array('value' => $f, 'label' => $f, 'image' => '', 'note' => '');
}
$s = shape(sf_formula_options_with_custom($opts));
ck('plain flavour list: two picks plus one Custom',
	$s['count'] === 3, $s);
ck('plain flavour list: the APPENDED chip is the marked one',
	$s['marked'] === array(2), $s['marked']);

/* Case is not a difference a visitor should see (mirrors the pool reader). */
$opts = array(
	array('value' => 'Chicken', 'label' => 'Chicken', 'image' => '', 'note' => ''),
	array('value' => 'custom', 'label' => 'custom', 'image' => '', 'note' => ''),
);
$s = shape(sf_formula_options_with_custom($opts));
ck('lowercase "custom" is recognised, not duplicated',
	$s['count'] === 2 && $s['marked'] === array(1), $s);

/* The single-value groups (weight, stage) build a one-pick list. */
$opts = array(array('value' => '500 mg', 'label' => '500 mg', 'image' => '', 'note' => ''));
$s = shape(sf_formula_options_with_custom($opts));
ck('single-value group: one pick plus one Custom, marked',
	$s['count'] === 2 && $s['marked'] === array(1), $s);

/* An empty list still gets a Custom, so the group never draws a bare box. */
$s = shape(sf_formula_options_with_custom(array()));
ck('empty list: Custom is appended and marked',
	$s['count'] === 1 && $s['marked'] === array(0), $s);

echo "\n$n checks, $fail failed\n";
exit($fail === 0 ? 0 : 1);

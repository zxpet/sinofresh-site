<?php
/* B2D Step1 — dry run of the two pure parsers behind [sf_formula_actives],
   over the 21 real sf_formula_ingredients / sf_formula_analysis values.
   Standalone (no WordPress): exercises the DROPPED-IN code that ships in
   functions.php, plus a small adversarial probe set.

   Run:  <php> tools/b2d1_parser_dryrun.php

   The fixtures below are the live post meta (Batch2D Step1, verified against
   the DB by HEX dump). The expected render counts at the end are the numbers
   the regression gate asserts per dosage page.
   NOTE: keep BYTE-IDENTICAL to the shipped functions (the two helpers are
   duplicated here on purpose — this file must run without WP loaded). */

/* ------------------------------------------------------------------ helpers */

function sinofresh_formula_split_top_level($value) {
	$value = (string) $value;
	if (trim($value) === '') {
		return array();
	}
	$out   = array();
	$depth = 0;
	$cur   = '';
	$len   = strlen($value);
	for ($i = 0; $i < $len; $i++) {
		$ch = $value[$i];
		if ($ch === '(') {
			$depth++;
		} elseif ($ch === ')') {
			if ($depth > 0) {
				$depth--;
			}
		}
		if ($ch === ',' && $depth === 0) {
			$out[] = trim($cur);
			$cur   = '';
			continue;
		}
		$cur .= $ch;
	}
	$out[] = trim($cur);
	return array_values(array_filter($out, function ($s) { return $s !== ''; }));
}

function sinofresh_formula_analysis_pairs($value) {
	$pairs = array();
	foreach (sinofresh_formula_split_top_level($value) as $part) {
		$pos = strpos($part, "\xE2\x89\xA5"); // U+2265 GREATER-THAN OR EQUAL TO
		if ($pos === false) {
			$pairs[] = array('term' => $part, 'value' => '');
			continue;
		}
		$term  = rtrim(substr($part, 0, $pos));
		$level = ltrim(substr($part, $pos));
		if ($term === '' || $level === '') {
			continue;
		}
		$pairs[] = array('term' => $term, 'value' => $level);
	}
	return $pairs;
}

/* ----------------------------------------------------------------- fixtures */
/* slug \t title \t ingredients \t analysis  — one line per published formula,
   in the order the band renders it (menu_order, title). */

$SF_FIXTURES = array(
	'Plaque Control Dental Chews'      => array('dental-chews', 'Coconut Oil, Parsley, Shiitake Mushroom, Organic Honey', 'Coconut Oil ≥5%'),
	'Oral Care Dental Sticks'          => array('dental-chews', 'Wheat Flour, Wheat Starch, Corn Flour, Glycerin, Natural Flavors, Sodium Tripolyphosphate', 'Crude Protein ≥10%, Crude Fat ≥2%'),
	'Natural Cleaning Dental Sticks'   => array('dental-chews', 'Tapioca (46%), Peas (29%), Vegetable Glycerin (12%), Cheddar Cheese (6%), Hydrolyzed Yeast (4%)', 'Crude Protein ≥8%, Crude Fiber ≥2%'),
	'Ear Care Drops'                   => array('drops', 'Organic Aloe Vera, Tea Tree Oil, Calendula', 'Aloe Vera ≥10%'),
	'Urinary Care Drops'               => array('drops', 'Cranberry Extract, Marshmallow Root, Dandelion', 'Cranberry ≥200mg/ml'),
	'Wild Alaskan Salmon Oil'          => array('fish-oil', 'Wild-caught Salmon Oil, Mixed Tocopherols', 'Omega-3 ≥30%, EPA ≥10%, DHA ≥12%, Omega-6 ≥3%, Omega-9 ≥16%'),
	'Pure Fish Oil Blend'              => array('fish-oil', 'Sardine, Anchovy, Herring, Mackerel Oil', 'Omega-3 ≥35%, EPA ≥18%, DHA ≥12%'),
	'Liquid Joint Support'             => array('liquids', 'Glucosamine Sulfate, MSM, Chondroitin Sulfate, Vitamin C, L-Proline, Grape Seed Extract, CoQ10, Hyaluronic Acid', 'Glucosamine ≥1600mg/oz, MSM ≥1500mg/oz, Chondroitin ≥1200mg/oz'),
	'Liquid Skin & Coat'               => array('liquids', 'Cod Liver Oil, Pollock Oil, Mixed Tocopherols', 'Omega-3 ≥30%, EPA ≥10%, DHA ≥12%'),
	'Hairball Remedy Paste'            => array('pastes', 'Malt Extract (43%), Oils and Fats (30%), Chicken Meal (4%), Yeast, Minerals', 'Crude Fat ≥30%, Crude Fiber ≥5%'),
	'Nutrition Paste'                  => array('pastes', 'Oils and Fats, Milk and Dairy, Malt Extract (12%), Yeast (MOS 1%)', 'Crude Fat ≥25%, Crude Protein ≥5%'),
	'Probiotic Powder'                 => array('powders', 'Inulin, Spinach Extract, Bacillus subtilis DE111, L. acidophilus, L. plantarum, B. coagulans', 'Total microorganisms ≥5 billion CFU/scoop'),
	'Pumpkin Digestive Powder'         => array('powders', '100% Pumpkin Powder (fiber source)', 'Crude Fiber ≥15%'),
	'Bladder Support Powder'           => array('powders', 'Cranberry, D-Mannose, Herbal Blend', 'Cranberry ≥500mg/scoop'),
	'Joint Support Soft Chews'         => array('soft-chews', 'Glucosamine HCl, Chondroitin Sulfate, MSM, Green-lipped Mussel, Chicken Flavor', 'Glucosamine ≥500mg/chew, Chondroitin ≥200mg/chew, MSM ≥100mg/chew'),
	'Calming Soft Chews'               => array('soft-chews', 'L-Tryptophan, Kelp, Ginger Root, Valerian Root, Chamomile, Thiamine', 'L-Tryptophan ≥120mg/chew, Chamomile ≥20mg/chew'),
	'Digestive Soft Chews'             => array('soft-chews', 'Alpha-Amylase, Lipase, Cellulase, Protease, Bacillus coagulans, FOS', 'Total microorganisms ≥1 billion CFU/chew'),
	'Skin & Coat Soft Chews'           => array('soft-chews', 'Marine Fish Oil, Safflower Oil, Coconut Oil, Biotin, Vitamin C, Vitamin E, Kelp', 'Omega-3 ≥50mg/chew, Biotin ≥50mcg/chew'),
	'Joint Support Tablets'            => array('tablets', 'Glucosamine HCl, MSM, Chondroitin, Green-lipped Mussel', 'Glucosamine ≥500mg/tablet, MSM ≥500mg/tablet, Chondroitin ≥200mg/tablet'),
	'Multivitamin Tablets'             => array('tablets', 'Vitamin A, D3, E, B-complex, Zinc, Iron, Methionine, EPA, DHA', 'Vitamin E ≥50 IU/tablet, Zinc ≥5mg/tablet'),
	'Calcium & Phosphorus Tablets'     => array('tablets', 'Dicalcium Phosphate, Dried Yeast, Whey, Hydrolyzed Soy Protein, Vitamin D3', 'Calcium ≥200mg/tablet, Phosphorus ≥100mg/tablet'),
);

/* --------------------------------------------------------------------- run */

echo "== 1. split_top_level vs a naive ', ' split (is the paren awareness needed today?) ==\n";
$diff = 0;
foreach ($SF_FIXTURES as $title => $f) {
	$naive = array_values(array_filter(array_map('trim', explode(', ', $f[1])), function ($s) { return $s !== ''; }));
	if ($naive !== sinofresh_formula_split_top_level($f[1])) {
		$diff++;
		echo "  SPLIT DIFFERS: {$title}\n";
	}
}
echo "  differing rows: {$diff}/" . count($SF_FIXTURES) . "\n";

echo "\n== 2. analysis segments that are malformed ==\n";
$nolevel = 0; $twice = 0;
foreach ($SF_FIXTURES as $title => $f) {
	foreach (sinofresh_formula_split_top_level($f[2]) as $seg) {
		$c = substr_count($seg, "\xE2\x89\xA5");
		if ($c === 0) { $nolevel++; echo "  NO >= : {$title} :: {$seg}\n"; }
		if ($c > 1)   { $twice++;   echo "  TWO >= : {$title} :: {$seg}\n"; }
	}
}
echo "  segments without >=: {$nolevel}   with more than one: {$twice}\n";

echo "\n== 3. pairs with an empty side (must be 0 — those rows are dropped) ==\n";
$bad = 0;
foreach ($SF_FIXTURES as $title => $f) {
	foreach (sinofresh_formula_analysis_pairs($f[2]) as $p) {
		if ($p['term'] === '' || $p['value'] === '') { $bad++; }
	}
}
echo "  bad pairs: {$bad}\n";

echo "\n== 4. expected RENDER COUNTS per dosage page (regression gate) ==\n";
$by_form = array();
foreach ($SF_FIXTURES as $title => $f) {
	$by_form[$f[0]][] = array($title, sinofresh_formula_split_top_level($f[1]), sinofresh_formula_analysis_pairs($f[2]));
}
$forms = array('soft-chews', 'tablets', 'powders', 'pastes', 'drops', 'liquids', 'fish-oil', 'dental-chews');
printf("  %-14s %-6s %-6s %s\n", 'form', 'items', 'pills', 'analysis rows');
$tp = 0; $tr = 0;
foreach ($forms as $slug) {
	$p = 0; $a = 0;
	foreach ($by_form[$slug] as $it) { $p += count($it[1]); $a += count($it[2]); }
	$tp += $p; $tr += $a;
	printf("  %-14s %-6d %-6d %d\n", $slug, count($by_form[$slug]), $p, $a);
}
echo "  TOTAL pills={$tp} analysis_rows={$tr}\n";

echo "\n== 5. adversarial probes (must never throw, never emit an empty <li>/<dd>) ==\n";
$GE = "\xE2\x89\xA5"; // U+2265
$probes = array(
	''                                     => 'empty string',
	'   '                                  => 'whitespace only',
	'a, b, '                               => 'trailing separator',
	',,a,,b'                               => 'empty segments',
	'X (a, b), Y'                          => 'comma inside parens',
	'Z (unclosed, Y, W'                    => 'unclosed paren',
	'Glucosamine ' . $GE . '500mg, MSM'    => 'second segment has no level',
	'Only ' . $GE                          => 'term is the word Only, no level',
	$GE . '5%'                             => 'level but no term',
	'Term ' . $GE                          => 'term but no level',
	'Glucosamine >=500mg, MSM'             => 'ASCII >= (must NOT be treated as a level)',
	"Line\nbreak, Next"                    => 'embedded newline',
	'<script>alert(1)</script>, Ok'        => 'markup in a term',
);
foreach ($probes as $in => $label) {
	$s = sinofresh_formula_split_top_level($in);
	$a = sinofresh_formula_analysis_pairs($in);
	printf("  %-42s split=%-44s pairs=%s\n", $label,
		json_encode($s, JSON_UNESCAPED_UNICODE), json_encode($a, JSON_UNESCAPED_UNICODE));
}
echo "\n  Expected: only 'level but no term' drops its row (empty term). Every other\n"
	. "  case returns a pair with an empty value, which the renderer prints as a\n"
	. "  term-only row — harmless, and unreachable from the real 21 values\n"
	. "  (section 2 above: 0 malformed segments).\n";

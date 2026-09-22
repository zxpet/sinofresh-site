<?php
/**
 * Batch H3 Step 0 — read-only census of the twelve data sources the batch
 * intends to render. Prints one JSON object on stdout. Writes nothing.
 *
 * Why a PHP probe and not `mysql`: the CLI mangles backslashes in JSON meta
 * values (the H1 lesson); reading through get_post_meta() sees the bytes
 * WordPress actually serves. Same reasoning as b2d_h2a_dbprobe.php.
 *
 * The question this answers: for each block H3 promises, is there (a) a
 * registered key, (b) any stored row, (c) any non-empty value among the 21
 * records? A block with (a) but not (b) renders zero bytes today by design
 * ("empty means the whole block is absent"), so the batch's visible effect
 * has to be argued from this table, not assumed.
 *
 * usage: wp eval-file tools/b2d_h3_dataprobe.php --allow-root
 */

if (!defined('ABSPATH')) { fwrite(STDERR, "must run under wp eval-file\n"); exit(1); }

global $wpdb;

$ids = get_posts(array(
	'post_type'   => 'sf_formula',
	'post_status' => 'any',
	'numberposts' => -1,
	'fields'      => 'ids',
	'orderby'     => 'ID',
	'order'       => 'ASC',
));
sort($ids);

/* ---- 1. exhaustive key inventory over the whole post meta table ---------
 * Not restricted to sf_formula: an alternate spelling of a field
 * (e.g. sf_formula_use_case vs _use_cases) would otherwise hide. */
$all = $wpdb->get_results(
	"SELECT meta_key, COUNT(*) AS rows_n,
	        SUM(CASE WHEN meta_value IS NULL OR meta_value = '' THEN 0 ELSE 1 END) AS nonempty_n
	   FROM {$wpdb->postmeta}
	  WHERE meta_key LIKE 'sf_formula%'
	  GROUP BY meta_key
	  ORDER BY meta_key ASC",
	ARRAY_A
);

/* ---- 2. the twelve H3 sources, one row each ---------------------------- */
$h3 = array(
	'Ingredients'          => 'sf_formula_ingredients',
	'Guaranteed Analysis'  => 'sf_formula_analysis',
	'Formula'              => 'sf_formula_specs',
	'Recommended For'      => 'sf_formula_recommended_for',
	'Use Cases'            => 'sf_formula_use_cases',
	"Who It's For"         => 'sf_formula_who_for',
	'Container Options'    => 'sf_formula_container',
	'Additional Packaging' => 'sf_formula_packaging_extra',
	'Color Options'        => 'sf_formula_colors',
	'Shelf Life'           => 'sf_formula_shelf_life',
	'Storage'              => '(hardcoded - no key)',
	'Carton Dimensions'    => 'sf_formula_cartons',
);

$census = array();
foreach ($h3 as $label => $key) {
	if ($key === '(hardcoded - no key)') {
		$census[$label] = array('key' => null, 'present' => null, 'nonempty' => null,
			'note' => 'constant sentence, no record carries it');
		continue;
	}
	$present = 0; $nonempty = 0; $samples = array();
	foreach ($ids as $id) {
		$raw = get_post_meta($id, $key, true);
		if ($raw === '' || $raw === null || $raw === false) { continue; }
		$present++;
		$s = is_string($raw) ? trim($raw) : '';
		if ($s !== '') {
			$nonempty++;
			if (count($samples) < 2) { $samples[] = mb_substr($s, 0, 90); }
		}
	}
	$census[$label] = array(
		'key'      => $key,
		'present'  => $present,
		'nonempty' => $nonempty,
		'of'       => count($ids),
		'samples'  => $samples,
	);
}

/* ---- 3. the keys H2a/H2b already consume, for the duplicate check ------ */
$already = array();
foreach (array('sf_formula_intro','sf_formula_flavors','sf_formula_species',
	'sf_formula_lifestage','sf_formula_price_tiers','sf_formula_lead_time',
	'sf_formula_faq_data','sf_formula_weight','sf_formula_counts','sf_formula_shape',
	'sf_formula_gallery_ids','sf_formula_video_url','sf_formula_source',
	'sf_formula_base','sf_formula_other_ingredients') as $k) {
	$n = 0;
	foreach ($ids as $id) {
		$raw = get_post_meta($id, $k, true);
		if ($raw !== '' && $raw !== null && $raw !== false) { $n++; }
	}
	$already[$k] = $n;
}

/* ---- 4. global library the packaging blocks read ----------------------- */
$containers = function_exists('sf_container_library') ? sf_container_library() : null;
$cert_opt   = get_option('sf_certifications', null);

/* ---- 5. does any record already carry a value for the FAQ the page
 *         prints? (tells us whether H3's HowTo can reuse it) ------------- */
$faq_nonempty = 0;
foreach ($ids as $id) {
	$raw = trim((string) get_post_meta($id, 'sf_formula_faq_data', true));
	if ($raw !== '') { $faq_nonempty++; }
}

echo wp_json_encode(array(
	'formula_ids'        => $ids,
	'formula_count'      => count($ids),
	'sf_formula_keys'    => $all,
	'h3_census'          => $census,
	'already_consumed'   => $already,
	'container_library'  => is_array($containers) ? array(
		'count'  => count($containers),
		'labels' => array_values(array_filter(array_map(function ($c) {
			return isset($c['label']) ? (string) $c['label'] : '';
		}, (array) $containers))),
	) : null,
	'sf_certifications_option' => $cert_opt === null ? null : (is_array($cert_opt) ? count($cert_opt) : 'scalar'),
	'faq_data_nonempty'  => $faq_nonempty,
), JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE) . "\n";

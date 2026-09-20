<?php
/**
 * Read-only: the post meta inventory behind the 21 sf_formula records.
 *
 * Reports every meta key that actually occurs, how many of the 21 records
 * carry a non-empty value for it, and a truncated sample. Also reports
 * post_content length, because [sf_formula_body] gates on it and all 21
 * were empty at the time of the 2D scans.
 *
 * Prints nothing but plain text. Never writes.
 */
global $wpdb;

$ids = $wpdb->get_col(
	"SELECT ID FROM {$wpdb->posts}
	 WHERE post_type = 'sf_formula' AND post_status = 'publish'
	 ORDER BY menu_order ASC, post_title ASC"
);
$ids = array_map('intval', $ids);
$total = count($ids);
echo "PUBLISHED_FORMULAS = {$total}\n";
echo 'IDS = ' . implode(',', $ids) . "\n\n";

echo "--- POST FIELDS ---\n";
printf("%-6s %-34s %-34s %8s %8s\n", 'ID', 'post_title', 'post_name', 'order', 'content');
foreach ($ids as $id) {
	$p = get_post($id);
	printf(
		"%-6d %-34s %-34s %8d %8d\n",
		$id,
		mb_substr($p->post_title, 0, 33),
		$p->post_name,
		(int) $p->menu_order,
		strlen((string) $p->post_content)
	);
}

echo "\n--- META KEYS ---\n";
$keys = $wpdb->get_col($wpdb->prepare(
	"SELECT DISTINCT pm.meta_key
	 FROM {$wpdb->postmeta} pm
	 JOIN {$wpdb->posts} p ON p.ID = pm.post_id
	 WHERE p.post_type = %s AND p.post_status = 'publish'
	 ORDER BY pm.meta_key ASC",
	'sf_formula'
));
printf("%-42s %5s %8s\n", 'meta_key', 'rows', 'nonempty');
foreach ($keys as $key) {
	$rows = 0;
	$nonempty = 0;
	$sample = '';
	foreach ($ids as $id) {
		$vals = get_post_meta($id, $key, false);
		foreach ($vals as $v) {
			$rows++;
			$s = is_scalar($v) ? (string) $v : wp_json_encode($v);
			if (trim($s) !== '') {
				$nonempty++;
				if ($sample === '') {
					$sample = mb_substr(preg_replace('/\s+/', ' ', $s), 0, 70);
				}
			}
		}
	}
	printf("%-42s %5d %8d   %s\n", $key, $rows, $nonempty, $sample);
}

echo "\n--- TARGET KEYS FOR THE SIMPLIFIED PLAN ---\n";
$targets = array(
	'sf_formula_ingredients',
	'sf_formula_analysis',
	'sf_formula_specs',
	'sf_formula_base',
	'sf_formula_other_ingredients',
	'sf_formula_characteristics',
	'sf_formula_recommended_use',
	'sf_formula_warnings',
	'sf_formula_studies',
	'sf_formula_intro_paragraphs',
	'sf_formula_form',
	'sf_formula_use',
	'sf_formula_documents',
	'sf_formula_serving_size',
	'sf_formula_pack_count',
	'sf_formula_shelf_life',
);
foreach ($targets as $key) {
	$present = 0;
	$nonempty = 0;
	foreach ($ids as $id) {
		$raw = get_post_meta($id, $key, true);
		if (metadata_exists('post', $id, $key)) {
			$present++;
		}
		if (trim((string) $raw) !== '') {
			$nonempty++;
		}
	}
	printf(
		"%-36s present=%-3d nonempty=%-3d %s\n",
		$key,
		$present,
		$nonempty,
		$present === 0 ? 'MISSING ENTIRELY' : ''
	);
}

echo "\n--- TAXONOMIES ---\n";
$taxes = get_object_taxonomies('sf_formula');
echo 'taxonomies = ' . ($taxes ? implode(',', $taxes) : '(none)') . "\n";
foreach ($taxes as $tax) {
	foreach ($ids as $id) {
		$terms = wp_get_object_terms($id, $tax, array('fields' => 'names'));
		printf("  %-6d %-18s %s\n", $id, $tax, implode(' | ', $terms));
	}
}

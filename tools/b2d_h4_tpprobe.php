<?php
/**
 * H4 email prerequisite — READ-ONLY view of the TranslatePress rows that hold
 * info@zxpet.com. Answers "is an edit a plain UPDATE, or does it have to go
 * through TranslatePress so the original/dictionary pair stays in sync?"
 */
if (!defined('ABSPATH')) { exit('no ABSPATH'); }
global $wpdb;

echo "=== wp_trp_original_strings ===\n";
foreach ($wpdb->get_results(
	"SELECT * FROM {$wpdb->prefix}trp_original_strings
	  WHERE original LIKE '%info@zxpet.com%'", ARRAY_A) as $r) {
	echo json_encode($r, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE), "\n\n";
}

echo "=== wp_trp_dictionary_en_us_zh_cn ===\n";
foreach ($wpdb->get_results(
	"SELECT * FROM {$wpdb->prefix}trp_dictionary_en_us_zh_cn
	  WHERE original LIKE '%info@zxpet.com%' OR translated LIKE '%info@zxpet.com%'", ARRAY_A) as $r) {
	echo json_encode($r, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE), "\n\n";
}

echo "=== wp_trp_original_meta (which post each original belongs to) ===\n";
foreach ($wpdb->get_results(
	"SELECT * FROM {$wpdb->prefix}trp_original_meta
	  WHERE meta_value LIKE '%info@zxpet.com%'
	     OR original_id IN (SELECT id FROM {$wpdb->prefix}trp_original_strings WHERE original LIKE '%info@zxpet.com%')",
	ARRAY_A) as $r) {
	echo json_encode($r, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE), "\n\n";
}

echo "=== column shapes ===\n";
foreach (array('trp_original_strings', 'trp_dictionary_en_us_zh_cn', 'trp_original_meta') as $t) {
	$n = $wpdb->prefix . $t;
	$c = $wpdb->get_results("SHOW COLUMNS FROM `$n`", ARRAY_A);
	echo $n, ': ', implode(', ', array_map(function ($x) { return $x['Field'] . ' ' . $x['Type']; }, $c)), "\n";
}

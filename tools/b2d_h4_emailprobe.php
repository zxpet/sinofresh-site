<?php
/**
 * H4 / email prerequisite — READ-ONLY data probe.
 *
 * Answers one question: if we change info@zxpet.com to sales@zxpet.com, which
 * rows in the database have to change? It writes nothing: only get_option(),
 * get_posts(), get_post_meta() and $wpdb->get_results() on SELECTs.
 *
 * Run:  wp eval-file tools/b2d_h4_emailprobe.php --allow-root
 */

if (!defined('ABSPATH')) {
	exit('no ABSPATH');
}

global $wpdb;

$needle = 'info@zxpet.com';
$out    = array();

/* 1. The site-settings option that feeds {{sf-email}} and the Organization schema. */
$out['option_sf_contact_email'] = (string) get_option('sf_contact_email', '(absent)');

/* 2. Every option row holding the needle. */
$rows = $wpdb->get_results($wpdb->prepare(
	"SELECT option_name, LENGTH(option_value) AS len
	   FROM {$wpdb->options}
	  WHERE option_value LIKE %s
	  ORDER BY option_name",
	'%' . $wpdb->esc_like($needle) . '%'
), ARRAY_A);
$out['options_hits'] = $rows;

/* 3. Every post row holding the needle, with a true occurrence count. */
$rows = $wpdb->get_results($wpdb->prepare(
	"SELECT ID, post_type, post_status, post_name,
	        (CHAR_LENGTH(post_content) - CHAR_LENGTH(REPLACE(post_content, %s, '')))
	          / CHAR_LENGTH(%s) AS hits,
	        post_content LIKE %s AS hits_excerpt
	   FROM {$wpdb->posts}
	  WHERE post_content LIKE %s OR post_excerpt LIKE %s
	  ORDER BY post_type, ID",
	$needle, $needle, '%' . $wpdb->esc_like($needle) . '%',
	'%' . $wpdb->esc_like($needle) . '%', '%' . $wpdb->esc_like($needle) . '%'
), ARRAY_A);
$out['posts_hits'] = $rows;

/* 4. Post meta. */
$rows = $wpdb->get_results($wpdb->prepare(
	"SELECT post_id, meta_key
	   FROM {$wpdb->postmeta}
	  WHERE meta_value LIKE %s
	  ORDER BY post_id, meta_key",
	'%' . $wpdb->esc_like($needle) . '%'
), ARRAY_A);
$out['postmeta_hits'] = $rows;

/* 5. TranslatePress: dictionaries, originals and gettext. The ZH pages are
      re-serialised from these tables, so a string can live here and nowhere
      else in the theme. */
$tp = array();
foreach ($wpdb->get_col("SHOW TABLES LIKE '{$wpdb->prefix}trp_%'") as $table) {
	$cols = $wpdb->get_col("SHOW COLUMNS FROM `$table`", 0);
	$where = array();
	foreach ($cols as $c) {
		$where[] = "IFNULL(`$c`, '') LIKE '%" . $wpdb->esc_like($needle) . "%'";
	}
	if (!$where) {
		continue;
	}
	$n = (int) $wpdb->get_var("SELECT COUNT(*) FROM `$table` WHERE " . implode(' OR ', $where));
	if ($n > 0) {
		$tp[$table] = $n;
	}
}
$out['translatepress_hits'] = $tp;

/* 6. Nav menus and widgets are posts/options, but check terms for completeness. */
$out['term_hits'] = $wpdb->get_results($wpdb->prepare(
	"SELECT term_id, name FROM {$wpdb->terms} WHERE name LIKE %s OR slug LIKE %s",
	'%' . $wpdb->esc_like($needle) . '%', '%' . $wpdb->esc_like($needle) . '%'
), ARRAY_A);

$out['needle']   = $needle;
$out['replace']  = 'sales@zxpet.com';
$out['wrote']    = 'nothing — read-only probe';
$out['home_url'] = home_url('/');

echo wp_json_encode($out, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE), "\n";

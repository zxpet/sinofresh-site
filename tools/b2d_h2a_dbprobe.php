<?php
/**
 * Batch H2a Step 5 — canonical DB snapshot for the zero-trace check.
 *
 * Read-only. Prints one JSON object on stdout. The orchestrator runs it before
 * and after the admin E2E and diffs the two blobs: the content half must be
 * byte-identical, the edit-lock half must go from "whatever the test left" to
 * zero rows.
 *
 * Why a PHP probe and not `mysql` CLI: the CLI mangles backslashes in JSON
 * meta values (the H1 lesson) — reading through get_post_meta() is the only
 * path that sees the bytes WordPress actually serves.
 *
 * usage: wp eval-file tools/b2d_h2a_dbprobe.php
 */

if (!defined('ABSPATH')) { fwrite(STDERR, "must run under wp eval-file\n"); exit(1); }

global $wpdb;

$ids = get_posts(array(
	'post_type'      => 'sf_formula',
	'post_status'    => 'any',
	'numberposts'    => -1,
	'fields'         => 'ids',
	'orderby'        => 'ID',
	'order'          => 'ASC',
));
sort($ids);

/* ---- 1. every sf_formula meta row, canonically ordered -------------------
 * meta_id is included so a delete+re-insert (same key, same value, new row)
 * is still visible as a change rather than hiding behind an equal value.  */
$rows = $wpdb->get_results(
	"SELECT pm.meta_id, pm.post_id, pm.meta_key, pm.meta_value
	   FROM {$wpdb->postmeta} pm
	   JOIN {$wpdb->posts} p ON p.ID = pm.post_id
	  WHERE p.post_type = 'sf_formula'
	  ORDER BY pm.post_id ASC, pm.meta_key ASC, pm.meta_id ASC",
	ARRAY_A
);

$meta = array();
$edit = array();
foreach ($rows as $r) {
	$rec = array(
		'post_id'  => (int) $r['post_id'],
		'meta_key' => $r['meta_key'],
		'len'      => strlen((string) $r['meta_value']),
		'sha1'     => sha1((string) $r['meta_value']),
	);
	if (strpos($r['meta_key'], '_edit_') === 0) {
		$edit[] = $rec;
	} else {
		$meta[] = $rec;
	}
}

/* ---- 2. the exact bytes of the 21x5 census keys ------------------------- */
$census_keys = array(
	'sf_formula_intro', 'sf_formula_shelf_life', 'sf_formula_lead_time',
	'sf_formula_faq_data', 'sf_formula_source',
);
$census = 0;
$census_blob = array();
foreach ($ids as $id) {
	foreach ($census_keys as $k) {
		$v = get_post_meta($id, $k, true);
		if ($v !== '') { $census++; }
		$census_blob[$id][$k] = sha1((string) $v);
	}
}

/* ---- 3. users ----------------------------------------------------------- */
$users = array();
foreach (get_users(array('fields' => array('ID', 'user_login'))) as $u) {
	$users[] = (int) $u->ID . ':' . $u->user_login;
}
sort($users);

/* ---- 4. post 158's own row, minus the columns a save is allowed to move - */
$post = get_post(158);
$fields = array();
if ($post) {
	foreach (array('post_title', 'post_content', 'post_excerpt', 'post_status',
		'post_name', 'post_parent', 'menu_order', 'post_type', 'comment_status',
		'ping_status', 'post_password', 'guid') as $f) {
		$fields[$f] = sha1((string) $post->$f);
	}
	$fields['post_author'] = (int) $post->post_author;
}

/* ---- 5. the three admin screens the E2E touches read-only ---------------
 * sf_containers and sf_global_faq are registered but were never saved, so the
 * decisive assertion is that they still do not exist after the run.        */
$opts = array();
foreach (array('sf_certifications', 'sf_containers', 'sf_global_faq') as $name) {
	$v = get_option($name, '__ABSENT__');
	$opts[$name] = ($v === '__ABSENT__') ? 'ABSENT' : ('len:' . strlen(wp_json_encode($v)) . ':sha1:' . sha1(wp_json_encode($v)));
}
$opt_totals = $wpdb->get_row("SELECT COUNT(*) AS n, MAX(option_id) AS m FROM {$wpdb->options}", ARRAY_A);

/* Transients are not content: WordPress core (_site_transient_wp_remote_block_
 * patterns_*), Gravity Forms (_transient_GFCache_*) and WP cron all delete and
 * recreate them, so MAX(option_id) walks forward on an idle site too. The
 * invariant that means anything is over the NON-transient rows.            */
$nontrans = $wpdb->get_results(
	"SELECT option_name, option_value FROM {$wpdb->options}
	  WHERE option_name NOT LIKE '\_transient%'
	    AND option_name NOT LIKE '\_site\_transient%'
	  ORDER BY option_name ASC",
	ARRAY_A
);
$nt_rows = array();
foreach ($nontrans as $r) {
	$nt_rows[] = $r['option_name'] . '=' . sha1((string) $r['option_value']);
}
$trans_count = (int) $wpdb->get_var(
	"SELECT COUNT(*) FROM {$wpdb->options}
	  WHERE option_name LIKE '\_transient%' OR option_name LIKE '\_site\_transient%'"
);

/* ---- 6. terms ----------------------------------------------------------- */
$term_counts = array(
	'terms'    => (int) $wpdb->get_var("SELECT COUNT(*) FROM {$wpdb->terms}"),
	'taxonomy' => (int) $wpdb->get_var("SELECT COUNT(*) FROM {$wpdb->term_taxonomy}"),
	'rel_form' => (int) $wpdb->get_var("SELECT COUNT(*) FROM {$wpdb->term_relationships} tr
		JOIN {$wpdb->term_taxonomy} tt ON tt.term_taxonomy_id = tr.term_taxonomy_id
		WHERE tt.taxonomy = 'sf_formula_form'"),
	'rel_use'  => (int) $wpdb->get_var("SELECT COUNT(*) FROM {$wpdb->term_relationships} tr
		JOIN {$wpdb->term_taxonomy} tt ON tt.term_taxonomy_id = tr.term_taxonomy_id
		WHERE tt.taxonomy = 'sf_formula_use'"),
);

$out = array(
	'formula_ids'     => array_map('intval', $ids),
	'formula_count'   => count($ids),
	'meta_rows'       => count($meta),
	'meta_sha'        => sha1(wp_json_encode($meta)),
	'meta'            => $meta,
	'edit_rows'       => $edit,
	'census_105'      => $census,
	'census_blob_sha' => sha1(wp_json_encode($census_blob)),
	'users'           => $users,
	'post158'         => $fields,
	'post158_modified'=> $post ? (string) $post->post_modified_gmt : '',
	'options'         => $opts,
	'option_totals'   => array('rows' => (int) $opt_totals['n'], 'max_id' => (int) $opt_totals['m']),
	'nontransient_rows' => count($nt_rows),
	'nontransient_sha'  => sha1(wp_json_encode($nt_rows)),
	'transient_rows'    => $trans_count,
	'terms'           => $term_counts,
);

echo wp_json_encode($out, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE) . "\n";

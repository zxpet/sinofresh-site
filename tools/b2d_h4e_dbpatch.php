<?php
/**
 * Batch H4e (email prerequisite) — the database half of the swap.
 *
 * Ten rows across three tables:
 *   wp_options                  x1   sf_contact_email
 *   wp_posts                    x3   the three published legal pages
 *   wp_trp_original_strings     x3   the strings TranslatePress extracted
 *   wp_trp_dictionary_en_us_zh_cn x3 the matching dictionary rows
 *
 * Post 36 (a revision of post 3) is left alone: revisions are never served.
 *
 * Rollback. --dry-run writes the ORIGINAL value of every row it is about to
 * touch to _backup/b2d-h4e-db-originals.json, including the whole post_content
 * of the legal pages, because a rollback that reconstructs content from a
 * search-and-replace is not a rollback — post 3 holds two occurrences and the
 * replacement is not the only text on the page. --apply refuses to run unless
 * that snapshot exists and still matches what is in the database, so the file
 * on disk always describes the state being changed.
 *
 * Why this is PHP and not .sql: esc_sql() tokenises every % into a
 * {sha256} placeholder that only the wpdb->query filter removes. A .sql file
 * written from esc_sql() output bakes the token in permanently, and a bare
 * mysqli client never runs the filter. Using the wpdb API for both the read and
 * the write keeps the bytes that WordPress serves and the bytes we compare
 * identical. The snapshot is JSON, not SQL, for the same reason.
 *
 * usage:
 *   wp eval-file tools/b2d_h4e_dbpatch.php --dry-run
 *   wp eval-file tools/b2d_h4e_dbpatch.php --apply
 */
if (!defined('ABSPATH')) { fwrite(STDERR, "must run under wp eval-file\n"); exit(1); }

global $wpdb;

$OLD     = 'info@zxpet.com';
$NEW     = 'sales@zxpet.com';
/* Outside the docroot and therefore not web-reachable, and unlike /tmp it
   survives a reboot — this file is the rollback. */
$SNAP    = '/var/www/dev.zxpet.com/_offroot/b2d-h4e-db-originals.json';

/* wp-cli delivers positional arguments (everything after a bare --) in $args
   and long flags in $assoc_args, but it rejects an undeclared --flag before the
   script ever runs — including after a bare --, which it swallows. So the
   primary switch is the SF_H4E_MODE environment variable, which survives the
   ssh hop and cannot be mis-parsed. The argv shapes still work when they can. */
$argv_like = array_merge((array) $args, array_keys((array) (isset($assoc_args) ? $assoc_args : array())));
$has = function ($flag) use ($argv_like) {
	foreach ($argv_like as $a) {
		if ($a === $flag || ltrim($a, '-') === ltrim($flag, '-')) { return true; }
	}
	return false;
};
$mode   = (string) getenv('SF_H4E_MODE');
$DRY    = ($mode === 'dry-run') || $has('--dry-run');
$APPLY  = ($mode === 'apply')   || $has('--apply');
$REVERT = ($mode === 'revert')  || $has('--revert');
if (getenv('SF_H4E_SNAPSHOT')) { $SNAP = getenv('SF_H4E_SNAPSHOT'); }

if (!$DRY && !$APPLY && !$REVERT) {
	fwrite(STDERR, "set SF_H4E_MODE to dry-run, apply or revert\n");
	exit(2);
}

$LEGAL_POSTS = array(3, 37, 38);   // privacy-policy, cookie-policy, terms
$TP_ORIG_IDS = array(53, 138, 1364);

/* ---------------------------------------------------------------- collect */

function h4e_collect($wpdb, $OLD, $posts, $ids) {
	$out = array('option' => array(), 'posts' => array(), 'trp_orig' => array(),
	             'trp_dict' => array());

	$out['option']['sf_contact_email'] = get_option('sf_contact_email', '');

	foreach ($posts as $id) {
		$row = $wpdb->get_row($wpdb->prepare(
			"SELECT ID, post_content, post_title, post_modified
			   FROM {$wpdb->posts} WHERE ID = %d", $id), ARRAY_A);
		if ($row) { $out['posts'][$id] = $row; }
	}

	foreach ($wpdb->get_results($wpdb->prepare(
		"SELECT id, original FROM {$wpdb->prefix}trp_original_strings
		  WHERE id IN (" . implode(',', array_map('intval', $ids)) . ")
		    AND original LIKE %s",
		'%' . $wpdb->esc_like($OLD) . '%'), ARRAY_A) as $r) {
		$out['trp_orig'][(int) $r['id']] = $r['original'];
	}

	foreach ($wpdb->get_results($wpdb->prepare(
		"SELECT id, original, translated, status
		   FROM {$wpdb->prefix}trp_dictionary_en_us_zh_cn
		  WHERE id IN (" . implode(',', array_map('intval', $ids)) . ")
		    AND (original LIKE %s OR translated LIKE %s)",
		'%' . $wpdb->esc_like($OLD) . '%', '%' . $wpdb->esc_like($OLD) . '%'), ARRAY_A) as $r) {
		$out['trp_dict'][(int) $r['id']] = $r;
	}
	return $out;
}

/* -------------------------------------------------------------- revert path */

if ($REVERT) {
	if (!file_exists($SNAP)) { fwrite(STDERR, "FATAL: no snapshot at $SNAP\n"); exit(3); }
	$snap = json_decode(file_get_contents($SNAP), true);
	if (!is_array($snap)) { fwrite(STDERR, "FATAL: snapshot is not JSON\n"); exit(3); }
	$n = 0;
	update_option('sf_contact_email', $snap['option']['sf_contact_email']);
	$n++;
	foreach ($snap['posts'] as $id => $row) {
		$wpdb->update($wpdb->posts, array('post_content' => $row['post_content']),
			array('ID' => (int) $id));
		$n++;
	}
	foreach ($snap['trp_orig'] as $id => $v) {
		$wpdb->update($wpdb->prefix . 'trp_original_strings',
			array('original' => $v), array('id' => (int) $id));
		$n++;
	}
	foreach ($snap['trp_dict'] as $id => $r) {
		$wpdb->update($wpdb->prefix . 'trp_dictionary_en_us_zh_cn',
			array('original' => $r['original'], 'translated' => $r['translated'],
			      'status' => (int) $r['status']), array('id' => (int) $id));
		$n++;
	}
	echo "REVERTED $n row(s) from $SNAP\n";
	/* Prove it: no needle left, and the old value is back on the option. */
	$left = (int) $wpdb->get_var($wpdb->prepare(
		"SELECT COUNT(*) FROM {$wpdb->posts} WHERE post_content LIKE %s",
		'%' . $wpdb->esc_like($NEW) . '%'));
	echo 'sales@ still in post_content: ' . $left . " (informational)\n";
	echo 'sf_contact_email is now: ' . get_option('sf_contact_email') . "\n";
	exit(0);
}

/* -------------------------------------------------------------------- plan */

$before = h4e_collect($wpdb, $OLD, $LEGAL_POSTS, $TP_ORIG_IDS);
$plan   = array();

$plan[] = array('wp_options', 'sf_contact_email',
	$before['option']['sf_contact_email'],
	str_replace($OLD, $NEW, $before['option']['sf_contact_email']));

foreach ($LEGAL_POSTS as $id) {
	if (!isset($before['posts'][$id])) { $plan[] = array('MISSING', "post $id", '', ''); continue; }
	$c = $before['posts'][$id]['post_content'];
	$hits = substr_count($c, $OLD);
	$plan[] = array('wp_posts', sprintf('ID %d (%s) — %d occurrence(s)',
		$id, $before['posts'][$id]['post_title'], $hits),
		sprintf('%d bytes', strlen($c)),
		sprintf('%d bytes, %d replaced', strlen(str_replace($OLD, $NEW, $c)), $hits));
}

foreach ($TP_ORIG_IDS as $id) {
	$v = isset($before['trp_orig'][$id]) ? $before['trp_orig'][$id] : null;
	$plan[] = array('trp_original_strings', "id $id", $v === null ? 'MISSING' : $v,
		$v === null ? '' : str_replace($OLD, $NEW, $v));
}
foreach ($TP_ORIG_IDS as $id) {
	$r = isset($before['trp_dict'][$id]) ? $before['trp_dict'][$id] : null;
	$plan[] = array('trp_dictionary_en_us_zh_cn', "id $id",
		$r === null ? 'MISSING' : $r['original'],
		$r === null ? '' : str_replace($OLD, $NEW, $r['original']));
}

echo "=== batch H4e database swap ===\n";
echo "needle: $OLD -> $NEW\n\n";
foreach ($plan as $p) {
	printf("  %-28s %-34s %s  ->  %s\n", $p[0], $p[1], $p[2], $p[3]);
}
echo "\nrows in the plan: " . count($plan) . "\n";
echo "post 36 (revision of 3): deliberately NOT touched\n";

if ($DRY) {
	$json = json_encode($before, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
	if (preg_match('/[{][0-9a-f]{64}[}]/', $json)) {
		fwrite(STDERR, "FATAL: placeholder token leaked into the snapshot\n"); exit(4);
	}
	file_put_contents($SNAP, $json);
	echo "\n--dry-run: snapshot of the ORIGINAL values written to $SNAP\n";
	echo "  (" . strlen($json) . " bytes; nothing in the database changed)\n";
	exit(0);
}

/* ------------------------------------------------------------------- apply */

if (!file_exists($SNAP)) {
	fwrite(STDERR, "FATAL: run --dry-run first; no snapshot at $SNAP\n"); exit(5);
}
$snap = json_decode(file_get_contents($SNAP), true);
if ($snap !== $before) {
	fwrite(STDERR, "FATAL: the database has moved since the snapshot — re-run --dry-run\n");
	$where = array();
	if ($snap['option'] !== $before['option']) { $where[] = 'option'; }
	if ($snap['trp_orig'] !== $before['trp_orig']) { $where[] = 'trp_original_strings'; }
	if ($snap['trp_dict'] !== $before['trp_dict']) { $where[] = 'trp_dictionary'; }
	foreach ($before['posts'] as $id => $r) {
		if (!isset($snap['posts'][$id]) || $snap['posts'][$id] !== $r) { $where[] = "post $id"; }
	}
	fwrite(STDERR, "  differs in: " . implode(', ', $where) . "\n");
	exit(6);
}

$failed = 0;

update_option('sf_contact_email', str_replace($OLD, $NEW, $before['option']['sf_contact_email']));
echo "  ok   wp_options.sf_contact_email\n";

foreach ($LEGAL_POSTS as $id) {
	$new = str_replace($OLD, $NEW, $before['posts'][$id]['post_content']);
	$r   = $wpdb->update($wpdb->posts, array('post_content' => $new), array('ID' => $id));
	if ($r === false) { echo "  FAIL wp_posts ID $id\n"; $failed++; continue; }
	/* Read back: substr_count on the stored value, not on $new. */
	$back = $wpdb->get_var($wpdb->prepare(
		"SELECT post_content FROM {$wpdb->posts} WHERE ID = %d", $id));
	$bad = substr_count($back, $OLD);
	printf("  %s wp_posts ID %d (read-back: %d old, %d new)\n",
		($r === 1 && $bad === 0) ? 'ok  ' : 'FAIL', $id, $bad, substr_count($back, $NEW));
	if ($r !== 1 || $bad !== 0) { $failed++; }
}

foreach (array('trp_original_strings', 'trp_dictionary_en_us_zh_cn') as $t) {
	foreach ($TP_ORIG_IDS as $id) {
		$table = $wpdb->prefix . $t;
		$cur   = $wpdb->get_var($wpdb->prepare("SELECT original FROM `$table` WHERE id = %d", $id));
		if ($cur === null) { echo "  FAIL $t id $id not found\n"; $failed++; continue; }
		$r = $wpdb->update($table, array('original' => str_replace($OLD, $NEW, $cur)),
			array('id' => $id));
		$back = $wpdb->get_var($wpdb->prepare("SELECT original FROM `$table` WHERE id = %d", $id));
		printf("  %s %s id %d -> %s\n", ($r === 1 && $back === str_replace($OLD, $NEW, $cur))
			? 'ok  ' : 'FAIL', $t, $id, $back);
		if ($r !== 1 || $back !== str_replace($OLD, $NEW, $cur)) { $failed++; }
	}
}

/* TranslatePress pairing: every original must still have a dictionary row and
   vice versa — the whole point of changing both tables together. */
$n_o = (int) $wpdb->get_var("SELECT COUNT(*) FROM {$wpdb->prefix}trp_original_strings WHERE id IN (" . implode(',', $TP_ORIG_IDS) . ")");
$n_d = (int) $wpdb->get_var("SELECT COUNT(*) FROM {$wpdb->prefix}trp_dictionary_en_us_zh_cn WHERE id IN (" . implode(',', $TP_ORIG_IDS) . ")");
$pair_ok = ($n_o === count($TP_ORIG_IDS) && $n_d === count($TP_ORIG_IDS));
printf("\n  %s TranslatePress pairing: %d originals / %d dictionary rows\n",
	$pair_ok ? 'ok  ' : 'FAIL', $n_o, $n_d);
if (!$pair_ok) { $failed++; }
/* And the two copies of each string must agree. */
foreach ($TP_ORIG_IDS as $id) {
	$a = $wpdb->get_var($wpdb->prepare("SELECT original FROM {$wpdb->prefix}trp_original_strings WHERE id = %d", $id));
	$b = $wpdb->get_var($wpdb->prepare("SELECT original FROM {$wpdb->prefix}trp_dictionary_en_us_zh_cn WHERE id = %d", $id));
	if ($a !== $b) { printf("  FAIL id %d: %s vs %s\n", $id, $a, $b); $failed++; }
}

echo "\nVERDICT: " . ($failed ? "FAIL — $failed row(s) bad" : "PASS — every row written and read back") . "\n";
exit($failed ? 1 : 0);

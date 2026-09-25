<?php
/**
 * Batch H9 — one-off meta migration for post 158 (the only record holding
 * pre-H9 configurator data). Run on dev AFTER the pull, BEFORE any editor
 * touches the record:
 *
 *     wp eval-file /path/to/h9_migrate_158.php --allow-root
 *
 * What it does (idempotent — safe to re-run):
 *   1. Dumps the record's five configurator metas + groups_config to
 *      /root/h9-post158-meta-backup-<date>.json FIRST (the backup is the
 *      rollback; restore by writing those keys back verbatim).
 *   2. Wraps the three legacy STRING values (sf_formula_weight,
 *      sf_formula_shape, sf_formula_container) into JSON arrays — the shape
 *      the H9 admin checkboxes and the H9 front-end readers store and read.
 *      A value already a JSON array is left alone.
 *   3. Rewrites sf_formula_container's out-of-vocabulary "Round" (retired
 *      Site Settings library word, no packaging pool contains it) to
 *      "Plastic Bottle" per the user's ruling E of 2026-09-25.
 *   4. Leaves sf_formula_flavors / sf_formula_counts (already arrays) and
 *      sf_formula_net_content / sf_formula_groups_config (empty = absent)
 *      untouched.
 *   5. Reads every key back and prints PASS/FAIL per key; exit code 1 on
 *      any FAIL so the deploy runbook can stop on it.
 *
 * The front-end readers also accept the legacy plain strings, so a record
 * renders correctly even between the pull and this script — but an admin
 * re-save BEFORE the script would drop the string values (the multi
 * sanitiser intersects against the checkbox list), which is why the runbook
 * orders this script first.
 */

$form_id = 158;

$keys = array(
	'sf_formula_flavors',
	'sf_formula_weight',
	'sf_formula_counts',
	'sf_formula_net_content',
	'sf_formula_shape',
	'sf_formula_container',
	'sf_formula_groups_config',
);

/* ---- 1. Backup (always, even when nothing needs migrating). ------------- */
$backup = array('post_id' => $form_id, 'backed_up_at' => gmdate('c'));
foreach ($keys as $key) {
	$backup[$key] = get_post_meta($form_id, $key, true);
}
$backup_path = '/root/h9-post158-meta-backup-' . gmdate('Ymd-His') . '.json';
$bytes = file_put_contents($backup_path, wp_json_encode($backup, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES));
echo $bytes ? "BACKUP  ok  $backup_path ($bytes bytes)\n" : "BACKUP  FAIL  could not write $backup_path\n";
if (!$bytes) {
	exit(1);
}

/* ---- 2/3. String → array wraps, and the Round → Plastic Bottle rewrite. -- */
$plan = array(
	'sf_formula_weight'    => null, // wrap whatever string is there
	'sf_formula_shape'     => null,
	'sf_formula_container' => null,
);

function h9_as_array($raw) {
	$vals = json_decode((string) $raw, true);
	if (is_array($vals)) {
		return array(null, $vals); // already migrated: no write needed
	}
	$legacy = trim((string) $raw);
	return ($legacy !== '') ? array($legacy) : array();
}

foreach ($plan as $key => $ignore) {
	$raw  = (string) get_post_meta($form_id, $key, true);
	$vals = h9_as_array($raw);
	if ($key === 'sf_formula_container') {
		// Ruling E: the retired library word "Round" becomes a pool value.
		foreach ($vals as $i => $v) {
			if (0 === strcasecmp((string) $v, 'Round')) {
				$vals[$i] = 'Plastic Bottle';
			}
		}
	}
	$current = json_decode($raw, true);
	if (is_array($current) && $current === $vals) {
		echo "MIGRATE skip $key (already an array)\n";
		continue;
	}
	if (!$vals) {
		echo "MIGRATE skip $key (empty)\n";
		continue;
	}
	update_post_meta($form_id, $key, wp_json_encode(array_values($vals)));
	echo "MIGRATE ok   $key: " . $raw . " -> " . wp_json_encode(array_values($vals)) . "\n";
}

/* ---- 5. Read-back verification. ----------------------------------------- */
$fail = 0;
$expect = array(
	'sf_formula_flavors'       => 'array',
	'sf_formula_weight'        => 'array',
	'sf_formula_counts'        => 'array',
	'sf_formula_net_content'   => 'absent-or-array',
	'sf_formula_shape'         => 'array',
	'sf_formula_container'     => 'array-without-Round',
	'sf_formula_groups_config' => 'absent-or-array',
);
foreach ($expect as $key => $rule) {
	$raw  = (string) get_post_meta($form_id, $key, true);
	$vals = json_decode($raw, true);
	$ok   = true;
	if ('array' === $rule) {
		$ok = is_array($vals) && count($vals) > 0;
	} elseif ('absent-or-array' === $rule) {
		$ok = ($raw === '') || is_array($vals);
	} elseif ('array-without-Round' === $rule) {
		$ok = is_array($vals) && count($vals) > 0;
		foreach ($vals as $v) {
			if (0 === strcasecmp((string) $v, 'Round')) {
				$ok = false;
			}
		}
	}
	echo ($ok ? 'VERIFY  ok   ' : 'VERIFY  FAIL ') . $key . ' = ' . ($raw === '' ? '(absent)' : $raw) . "\n";
	if (!$ok) {
		$fail++;
	}
}
echo $fail ? "RESULT  FAIL ($fail)\n" : "RESULT  PASS\n";
exit($fail ? 1 : 0);

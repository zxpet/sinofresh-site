<?php
/**
 * Batch 2C Step 3 — TranslatePress re-collection, READ-ONLY pre-flight probe.
 *
 * Answers, from the live dev database (no writes at all):
 *   1. the exact TP settings that decide whether a sync is even allowed
 *   2. how many dictionary rows carry a real translation today
 *   3. for every string this batch introduced: is it already tracked by TP,
 *      and if so with which id / status / translation
 *   4. what the newest rows are (i.e. what the site registered recently),
 *      so "already there" can be told apart from "added by an earlier batch"
 *
 * Run:  wp eval-file tools/b2c_s3_tp_scope_probe.php --path=<wp-root> --allow-root
 *       add --candidate-file=/tmp/x.txt to also test an arbitrary string list
 *       (one string per line, used for the "every text node on the page" sweep).
 */

global $wpdb;
$p  = $wpdb->prefix;
$T  = array(
	'orig' => $p . 'trp_original_strings',
	'dict' => $p . 'trp_dictionary_en_us_zh_cn',
	'gom'  => $p . 'trp_gettext_original_strings',
	'gtz'  => $p . 'trp_gettext_zh_cn',
	'om'   => $p . 'trp_original_meta',
	'so'   => $p . 'trp_slug_originals',
);

function h($s) {
	return str_replace(array("\r", "\n", "\t"), array('\r', '\n', '\t'), (string) $s);
}

echo "===============================================================\n";
echo " 1) trp_settings — what decides whether a sync can run\n";
echo "===============================================================\n";
$settings = get_option('trp_settings');
$keep = array('default-language', 'translation-languages', 'url-slugs',
              'native_or_english_name', 'with-floating-language-switcher',
              'add-subdirectory-to-default-language', 'force-language-to-custom-links');
foreach ($keep as $k) {
	printf("  %-42s %s\n", $k, isset($settings[$k]) ? h(json_encode($settings[$k])) : '(unset)');
}
echo "\n  -- advanced settings that touch string collection --\n";
$adv = get_option('trp_advanced_settings');
if (is_array($adv)) {
	foreach ($adv as $k => $v) {
		if (preg_match('/string|translat|sync|dynamic|locale|gettext/i', $k)) {
			printf("  %-42s %s\n", $k, h(is_scalar($v) ? $v : json_encode($v)));
		}
	}
} else {
	echo "  (trp_advanced_settings not an array)\n";
}

echo "\n===============================================================\n";
echo " 2) how much real translation exists today\n";
echo "===============================================================\n";
foreach (array('orig', 'dict', 'gom', 'gtz', 'om') as $alias) {
	printf("  %-8s %-42s rows=%s\n", $alias, $T[$alias],
		$wpdb->get_var("SELECT COUNT(*) FROM {$T[$alias]}"));
}
echo "\n  dictionary: status x translated\n";
$rows = $wpdb->get_results("SELECT status,
		COUNT(*) AS n,
		SUM(CASE WHEN translated IS NULL OR translated='' THEN 1 ELSE 0 END) AS empty_tr
	FROM {$T['dict']} GROUP BY status ORDER BY status");
foreach ($rows as $r) {
	printf("    status=%-4s rows=%-6s empty_translated=%-6s filled=%s\n",
		$r->status, $r->n, $r->empty_tr, $r->n - $r->empty_tr);
}
echo "\n  gettext zh_cn: status x filled\n";
$rows = $wpdb->get_results("SELECT status,
		COUNT(*) AS n,
		SUM(CASE WHEN translated IS NULL OR translated='' THEN 1 ELSE 0 END) AS empty_tr
	FROM {$T['gtz']} GROUP BY status ORDER BY status");
foreach ($rows as $r) {
	printf("    status=%-4s rows=%-6s empty_translated=%-6s filled=%s\n",
		$r->status, $r->n, $r->empty_tr, $r->n - $r->empty_tr);
}
echo "\n  gettext originals by domain (top 15)\n";
foreach ($wpdb->get_results("SELECT domain, COUNT(*) n FROM {$T['gom']} GROUP BY domain ORDER BY n DESC LIMIT 15") as $r) {
	printf("    %-40s %s\n", $r->domain, $r->n);
}

echo "\n===============================================================\n";
echo " 3) this batch's strings — already tracked by TP?\n";
echo "===============================================================\n";

$candidates = array(
	'nav'      => array('All Formulas'),
	'dosage'   => array('Browse All Formulas →', 'Browse All Formulas &rarr;'),
	'archive'  => array('Formulas', '21 formulas', 'Showing ', ' of 21 formulas', '21'),
	'chips'    => array('All', 'Soft Chews', 'Tablets', 'Powders', 'Pastes',
	                    'Drops', 'Liquids', 'Fish Oil', 'Dental Chews'),
	'misc'     => array('Reference this formula →', 'Filter formulas by dosage form',
	                    'Explore dosage forms', 'Standard Formulas'),
	'gettext'  => array('%d formula', '%d formulas', '%d article', '%d articles'),
);

/* any extra strings handed in by file (the "every text node" sweep).
   wp eval-file does not guarantee $argv, so the env var is the reliable route. */
$extra = array();
$candfile = getenv('B2C_S3_CAND');
if (!$candfile && isset($GLOBALS['argv'])) {
	foreach ($GLOBALS['argv'] as $a) {
		if (strpos($a, '--candidate-file=') === 0) {
			$candfile = substr($a, strlen('--candidate-file='));
		}
	}
}
if ($candfile && is_readable($candfile)) {
	$extra = array_values(array_filter(array_map('rtrim', file($candfile)), function ($s) {
		return $s !== '';
	}));
}
if (!$extra && $candfile) {
	echo "\n  !! candidate file '$candfile' unreadable or empty\n";
}
if ($extra) {
	$candidates['page_text_nodes'] = $extra;
}

$total = 0; $present = 0;
foreach ($candidates as $group => $list) {
	$quiet = ($group === 'page_text_nodes');
	if (!$quiet) { echo "\n  --- $group ---\n"; }
	$miss = array();
	foreach ($list as $s) {
		$total++;
		$o = $wpdb->get_row($wpdb->prepare(
			"SELECT id FROM {$T['orig']} WHERE original = %s LIMIT 1", $s));
		$d = $wpdb->get_row($wpdb->prepare(
			"SELECT id, status, translated, original_id FROM {$T['dict']} WHERE original = %s ORDER BY id LIMIT 1", $s));
		/* gettext route: the string may live in the gettext tables instead —
		   that is where every string that goes through __()/_e()/_n() ends up. */
		$g = $wpdb->get_row($wpdb->prepare(
			"SELECT id, domain, original_plural FROM {$T['gom']}
			 WHERE original = %s OR original_plural = %s LIMIT 1", $s, $s));
		$gtr = null;
		if ($g) {
			$gtr = $wpdb->get_row($wpdb->prepare(
				"SELECT id, status, translated FROM {$T['gtz']} WHERE original_id = %d LIMIT 1", $g->id));
		}
		$isin = ($o || $d || $g) ? 'IN  ' : 'NEW ';
		if ($o || $d || $g) { $present++; }
		if ($quiet) {
			if (!$o && !$d && !$g) { $miss[] = $s; }
			continue;
		}
		printf("  [%s] %-42s orig=%-7s dict=%-7s status=%-5s | gettext=%-7s domain=%-12s gt_status=%s\n",
			$isin, '"' . h($s) . '"',
			$o ? $o->id : '-', $d ? $d->id : '-',
			$d ? $d->status : '-',
			$g ? $g->id : '-', $g ? $g->domain : '-',
			$gtr ? $gtr->status : '-');
	}
	if ($quiet) {
		printf("\n  page_text_nodes: %d checked, %d not tracked anywhere\n",
			count($list), count($miss));
		echo "  --- the ones missing (these are what a re-collection would add) ---\n";
		foreach ($miss as $s) {
			printf("    [%3d] %s\n", mb_strlen($s), h($s));
		}
		$missfile = '/tmp/b2c_s3_missing.txt';
		file_put_contents($missfile, implode("\n", $miss) . "\n");
		echo "\n  missing list written to $missfile\n";
	}
}
printf("\n  SUMMARY: %d candidates checked, %d already tracked, %d not yet tracked\n",
	$total, $present, $total - $present);

echo "\n===============================================================\n";
echo " 4) newest 30 rows in wp_trp_original_strings (what got added last)\n";
echo "===============================================================\n";
$rows = $wpdb->get_results("SELECT o.id, o.original,
		d.status AS dstatus, d.translated AS dtranslated
	FROM {$T['orig']} o
	LEFT JOIN {$T['dict']} d ON d.original_id = o.id
	ORDER BY o.id DESC LIMIT 30");
foreach ($rows as $r) {
	printf("  id=%-6s status=%-5s %s\n", $r->id, $r->dstatus === null ? 'none' : $r->dstatus,
		'"' . h(mb_substr($r->original, 0, 110)) . '"');
}

echo "\n===============================================================\n";
echo " 5) is the theme text domain 'sinofresh' tracked at all?\n";
echo "===============================================================\n";
foreach (array('sinofresh', 'sinofresh-theme', 'default') as $dom) {
	printf("  domain=%-20s originals=%s\n", $dom,
		$wpdb->get_var($wpdb->prepare("SELECT COUNT(*) FROM {$T['gom']} WHERE domain = %s", $dom)));
}
echo "\n  gettext rows whose original mentions 'formula':\n";
$rows = $wpdb->get_results("SELECT id, original, domain, original_plural FROM {$T['gom']}
	WHERE original LIKE '%formula%' LIMIT 20");
foreach ($rows as $r) {
	printf("    id=%-6s domain=%-14s plural=%-16s \"%s\"\n",
		$r->id, $r->domain, h((string) $r->original_plural), h(mb_substr($r->original, 0, 80)));
}

echo "\n===============================================================\n";
echo " 6) original_meta — the post_id links that drive the TP UI\n";
echo "===============================================================\n";
$rows = $wpdb->get_results("SELECT meta_key, COUNT(*) n FROM {$T['om']} GROUP BY meta_key ORDER BY n DESC");
foreach ($rows as $r) {
	printf("    %-40s %s\n", $r->meta_key, $r->n);
}
echo "\n  slugs tracked:\n";
$rows = $wpdb->get_results("SELECT id, original, type FROM {$T['so']} ORDER BY id DESC LIMIT 10");
foreach ($rows as $r) {
	printf("    id=%-5s type=%-10s %s\n", $r->id, $r->type, h($r->original));
}
echo "\ndone.\n";

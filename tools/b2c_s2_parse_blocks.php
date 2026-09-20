<?php
/**
 * Parse a block template with WordPress' own block parser.
 *
 * Uses wp-includes/class-wp-block-parser.php standalone (no DB, no wp-load):
 * the parser is a pure PHP class, so this runs on any host PHP. It is the
 * authority on whether a template file is a well-formed block tree — the
 * regime where a mis-typed delimiter silently becomes freeform HTML and the
 * block never renders.
 *
 *   php tools/b2c_s2_parse_blocks.php <wp-root> templates/archive-sf_formula.html
 *
 * FAILS when any freeform chunk carries a "<!-- wp:" / "<!-- /wp:" fragment
 * (i.e. a delimiter core refused to parse).
 */
$root = $argv[1] ?? '';
$files = array_slice($argv, 2);
if ($root === '' || !$files) {
	fwrite(STDERR, "usage: php b2c_s2_parse_blocks.php <wp-root> <template...>\n");
	exit(2);
}
require $root . '/wp-includes/class-wp-block-parser.php';

function sf_walk($blocks, &$named, &$free, $depth = 0) {
	foreach ($blocks as $b) {
		if (($b['blockName'] ?? null) === null) {
			$t = trim($b['innerHTML']);
			if ($t !== '') {
				$free[] = ($depth ? 'inner' : 'top') . ':' . substr($t, 0, 60);
			}
		} else {
			$named[] = $b['blockName'];
			sf_walk($b['innerBlocks'], $named, $free, $depth + 1);
		}
	}
}

$fail = false;
foreach ($files as $f) {
	$src = file_get_contents($f);
	$parser = new WP_Block_Parser();
	$blocks = $parser->parse($src);
	$named = array();
	$free  = array();
	sf_walk($blocks, $named, $free);

	$bad = array();
	foreach ($free as $t) {
		if (strpos($t, '<!-- wp:') !== false || strpos($t, '<!-- /wp:') !== false) {
			$bad[] = $t;
		}
	}
	$top = array();
	foreach ($blocks as $b) {
		$top[] = $b['blockName'] === null ? '(freeform)' : $b['blockName'];
	}
	printf("%s\n  blocks=%d  freeform-chunks=%d\n  top-level: %s\n",
		$f, count($named), count($free), implode(' | ', $top));
	if ($bad) {
		$fail = true;
		echo "  FAIL — delimiter text fell through to freeform HTML:\n";
		foreach ($bad as $t) {
			echo "    {$t}\n";
		}
	}
	$counts = array_count_values($named);
	ksort($counts);
	$pairs = array();
	foreach ($counts as $k => $v) {
		$pairs[] = "{$k}×{$v}";
	}
	echo '  ' . implode(', ', $pairs) . "\n";
}
echo $fail ? "\nRESULT: FAIL\n" : "\nRESULT: PASS — every block delimiter parsed as a block\n";
exit($fail ? 1 : 0);

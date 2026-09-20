<?php
/**
 * Web-context probe — ask WordPress what it thinks the CURRENT request is,
 * from a CLI process, without a browser.
 *
 *   php tools/sf_web_ctx_probe.php /formulas/
 *   php tools/sf_web_ctx_probe.php /products/soft-chews/ --json
 *
 * Why this exists: `wp eval` does NOT run the main query. `is_*()` conditionals
 * therefore answer for an empty query — on /formulas/ `wp eval --url=…` reports
 * is_post_type_archive('sf_formula') === false and found_posts === 0, which is a
 * false negative that would send you chasing a non-bug. Injecting REQUEST_URI
 * before wp-load and calling wp() reproduces a live request's query state
 * exactly, so shortcode/template answers here match production.
 *
 * Options: --root=<path> (default: the dev site), --json (single line).
 */

$argv_in = $argv;
array_shift($argv_in);

$root = '/var/www/dev.zxpet.com/public';
$paths = array();
foreach ($argv_in as $a) {
	if (str_starts_with($a, '--root=')) {
		$root = substr($a, 7);
		continue;
	}
	if ($a !== '') {
		$paths[] = $a;
	}
}
if (!$paths) {
	$paths = array('/');
}

define('WP_USE_THEMES', false);

function sf_probe_one($root, $path) {
	$_SERVER['HTTP_HOST']      = parse_url('https://dev.zxpet.com', PHP_URL_HOST);
	$_SERVER['SERVER_NAME']    = $_SERVER['HTTP_HOST'];
	$_SERVER['REQUEST_URI']    = $path;
	$_SERVER['REQUEST_METHOD'] = 'GET';
	$_SERVER['HTTPS']          = 'on';
	$_SERVER['SERVER_PORT']    = '443';

	/* A fresh WP instance per path — reusing the globals would carry the
	   previous path's query state into the next answer (`is_paged` in
	   particular is sticky). */
	$wp = new WP();
	$wp->init();
	$wp->parse_request();
	$wp->query_posts();
	$wp->handle_404();

	$obj = get_queried_object();
	$q   = $GLOBALS['wp_query'];

	return array(
		'path'                  => $path,
		'is_post_type_archive'  => is_post_type_archive('sf_formula'),
		'is_singular_formula'   => is_singular('sf_formula'),
		'is_page'               => is_page(),
		'is_archive'            => is_archive(),
		'is_paged'              => is_paged(),
		'is_404'                => is_404(),
		'queried_class'         => is_object($obj) ? get_class($obj) : gettype($obj),
		'queried_name'          => is_object($obj) && isset($obj->name) ? $obj->name : null,
		'found_posts'           => (int) $q->found_posts,
		'posts_per_page'        => (int) ($q->query_vars['posts_per_page'] ?? 0),
		'cur_form'              => function_exists('sinofresh_formula_current_form')
			? sinofresh_formula_current_form('') : null,
		'archive_link'          => get_post_type_archive_link('sf_formula'),
	);
}

$out = array();
$boot = true;
foreach ($paths as $i => $p) {
	if ($i === 0) {
		require $root . '/wp-load.php';
		$boot = false;
	}
	$out[] = sf_probe_one($root, $p);
}

if (in_array('--json', $argv_in, true)) {
	echo json_encode(count($out) === 1 ? $out[0] : $out, JSON_UNESCAPED_SLASHES), "\n";
} else {
	foreach ($out as $row) {
		echo json_encode($row, JSON_UNESCAPED_SLASHES), "\n";
	}
}

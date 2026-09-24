<?php
/**
 * One case of the /zh/ redirect rule, run against the shipped file.
 *
 * The rule lives inside a WordPress request, but the decision it makes is pure:
 * given publish-languages and a REQUEST_URI, redirect or not. This harness
 * provides the four WordPress functions the file calls, includes the real file,
 * calls the real function, and prints the outcome — so a case that regresses
 * fails here rather than on the wire.
 *
 * A redirect is terminal in production (the function calls exit), so the stub
 * prints and exits too: reaching the trailing NO_REDIRECT line therefore proves
 * the rule declined to act, not merely that the assertion was skipped.
 *
 *   php b3e_zh_redirect_probe.php <case.json> <theme-dir>
 *
 * case.json: {"uri": "...", "method": "GET", "option": {...}|null}
 */

$case = json_decode(file_get_contents($argv[1]), true);
$theme = rtrim($argv[2], '/');

define('ABSPATH', '/tmp/');

$_SERVER['REQUEST_URI']    = $case['uri'];
$_SERVER['REQUEST_METHOD'] = isset($case['method']) ? $case['method'] : 'GET';

function get_option($name) {
	global $sf_case;
	return $sf_case['option'];
}

function home_url($path = '') {
	return 'https://dev.zxpet.com' . $path;
}

function wp_safe_redirect($location, $status = 302, $by = 'WordPress') {
	printf("REDIRECT %d %s\n", $status, $location);
	exit(0);
}

function add_action($hook, $cb, $pri = 10, $args = 1) {
	/* The file registers its hook at include time; this harness calls the
	   function directly so the case exercises the rule, not the wiring. */
}

$sf_case = $case;
require $theme . '/inc/zh-unpublish.php';
sinofresh_redirect_unpublished_zh();
echo "NO_REDIRECT\n";

<?php
/* Batch H19 E2E scaffolding — setup / teardown for tools/h19_admin_e2e.js.
 *
 *   setup:    mints signed admin cookies for user 1 and creates a throwaway
 *             PUBLISHED sf_formula, then writes both to /tmp/h19-e2e.json.
 *             Driving the real editor screen is the point: the picker, the
 *             hidden CSV input and the save round-trip are what is measured,
 *             and none of that can be reached from wp-admin's REST layer
 *             alone.
 *   teardown: deletes that record and destroys the session token the cookies
 *             were minted from, so the credential does not outlive the run.
 *
 * Every credential is generated here, never copied by hand. The record is
 * temporary on purpose: ops is mid-way through filling the real ones, and
 * an E2E that edits live content is an E2E nobody can re-run.
 *
 *   wp eval-file tools/h19_e2e.php setup
 *   wp eval-file tools/h19_e2e.php teardown
 */
$action = isset($args[0]) ? (string) $args[0] : '';

if ($action === 'setup') {
	$uid   = 1;
	$exp   = time() + 1800;
	$token = WP_Session_Tokens::get_instance($uid)->create($exp);

	$pid = wp_insert_post(array(
		'post_type'   => 'sf_formula',
		'post_status' => 'publish',
		'post_title'  => 'H19 E2E (temporary — delete me)',
		'post_name'   => 'h19-e2e-temporary',
	));
	if (!$pid || is_wp_error($pid)) {
		fwrite(STDERR, "insert failed\n");
		exit(1);
	}

	$cfg = array(
		'base'    => parse_url(home_url(), PHP_URL_SCHEME) . '://' . parse_url(home_url(), PHP_URL_HOST),
		'pid'     => (int) $pid,
		'url'     => get_permalink($pid),
		'admin'   => admin_url('post.php?post=' . $pid . '&action=edit'),
		'hash'    => COOKIEHASH,
		'exp'     => $exp,
		'token'   => $token,
		'cookies' => array(
			'sec'       => wp_generate_auth_cookie($uid, $exp, 'secure_auth', $token),
			'auth'      => wp_generate_auth_cookie($uid, $exp, 'auth', $token),
			'logged_in' => wp_generate_auth_cookie($uid, $exp, 'logged_in', $token),
		),
	);
	file_put_contents('/tmp/h19-e2e.json', json_encode($cfg));
	echo "WROTE=/tmp/h19-e2e.json\n";
	echo 'PID=' . $pid . "\n";
	echo 'PERMALINK=' . get_permalink($pid) . "\n";
} elseif ($action === 'teardown') {
	$cfg  = json_decode((string) @file_get_contents('/tmp/h19-e2e.json'), true);
	$pid  = !empty($cfg['pid']) ? (int) $cfg['pid'] : 0;
	$gone = 'n/a';
	if ($pid > 0) {
		wp_delete_post($pid, true);
		$gone = get_post($pid) ? 'no' : 'yes';
	}
	if (!empty($cfg['token'])) {
		WP_Session_Tokens::get_instance(1)->destroy($cfg['token']);
	}
	@unlink('/tmp/h19-e2e.json');
	echo "POST_DELETED={$gone}\n";
} else {
	echo "usage: wp eval-file tools/h19_e2e.php setup|teardown\n";
}

<?php
/**
 * Issue short-lived auth cookies for a read-only wp-admin screenshot.
 * Creates a session token (normal WP behaviour) but no user / password change.
 * Tokens expire in 30 minutes; the caller may destroy them afterwards.
 */
if ( ! defined( 'WP_CLI' ) || ! WP_CLI ) {
	echo "wp-cli only\n";
	exit(1);
}

$user_id = 1;
$exp     = time() + 1800;

$u = get_userdata( $user_id );
if ( ! $u ) {
	echo "ERROR: user 1 not found\n";
	exit(1);
}

echo 'COOKIEHASH=' . COOKIEHASH . "\n";
echo 'USER=' . $u->user_login . ' (ID ' . $user_id . ")\n";
echo 'logged_in=' . wp_generate_auth_cookie( $user_id, $exp, 'logged_in' ) . "\n";
echo 'auth=' . wp_generate_auth_cookie( $user_id, $exp, 'auth' ) . "\n";
echo 'secure_auth=' . wp_generate_auth_cookie( $user_id, $exp, 'secure_auth' ) . "\n";

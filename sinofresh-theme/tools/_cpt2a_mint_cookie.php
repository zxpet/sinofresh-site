<?php
/**
 * Batch 2A verification — mint an admin auth cookie for browser screenshots.
 *
 * Avoids needing the account password: creates a real session token and signs
 * the same cookies wp_signon() would issue. Short-lived (30 min) and the
 * session is destroyed at the end by _cpt2a_destroy_session.php.
 */

require_once '/Users/meng/Local Sites/sinofresh/app/public/wp-load.php';

$user_id    = 1;
$expiration = time() + 1800;
$manager    = WP_Session_Tokens::get_instance($user_id);
$token      = $manager->create($expiration);

/* Record the raw token for _cpt2a_cleanup.php. It has to be the raw value:
   WP_Session_Tokens::get_all() returns hashed verifiers, so its keys cannot be
   fed back into destroy() — see the trap note in the cleanup script. */
file_put_contents('/tmp/_cpt2a_tokens.txt', $token . "\n", FILE_APPEND);

printf("AUTH_NAME=%s\n", AUTH_COOKIE);
printf("AUTH_VALUE=%s\n", wp_generate_auth_cookie($user_id, $expiration, 'auth', $token));
printf("LOGGED_IN_NAME=%s\n", LOGGED_IN_COOKIE);
printf("LOGGED_IN_VALUE=%s\n", wp_generate_auth_cookie($user_id, $expiration, 'logged_in', $token));
printf("EXPIRES=%d\n", $expiration);
printf("SITE=%s\n", home_url('/'));
printf("USER=%s\n", get_userdata($user_id)->user_login);

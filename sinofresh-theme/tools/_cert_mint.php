<?php
/**
 * CLI test helper — mint a certificate download token and print its URL.
 *
 *   php tools/_cert_mint.php <cert> [ttl-seconds]
 *
 * Needs Local's MySQL socket, so run it as:
 *   php -d mysqli.default_socket="$SOCK" tools/_cert_mint.php fda
 *
 * Only used by the E2E flow; the real tokens are minted by the GF Form 5
 * submission handler in functions.php.
 */

$site_root = '/Users/meng/Local Sites/sinofresh/app/public';
require $site_root . '/wp-load.php';

$cert = isset($argv[1]) ? $argv[1] : 'fda';
$ttl  = isset($argv[2]) ? (int) $argv[2] : DAY_IN_SECONDS;

if (!function_exists('sinofresh_cert_mint_token')) {
	fwrite(STDERR, "cert-download.php is not loaded\n");
	exit(1);
}

$token = sinofresh_cert_mint_token($cert, 'test@example.com', $ttl);
if (!$token) {
	fwrite(STDERR, "unknown certificate: {$cert}\n");
	exit(1);
}

echo sinofresh_cert_download_url($cert, $token) . "\n";

<?php
/**
 * SINO FRESH — Gated certificate downloads (Quality page).
 *
 * GET /wp-json/sinofresh/v1/cert-download?cert=fda&token=<40 hex chars>
 *
 * The full-resolution certificate files live OUTSIDE the document root
 * (SF_CERTS_DIR below) so that no URL can reach them — the only way in is a
 * one-time token minted when a visitor submits GF Form 5 (see the
 * gform_after_submission handler in functions.php, which calls
 * sinofresh_cert_mint_token()).
 *
 * Why outside the document root: this stack is nginx (Local dev + the
 * AlmaLinux 9 LEMP production box), where .htaccess is never read. A
 * directory above the web root is the one protection that holds on every
 * server without any per-server configuration.
 *
 * LAUNCH CHECKLIST: on production upload the certificate files to the
 * directory that sits NEXT TO public_html (i.e. public_html/../private-certs/)
 * and ship this file with the theme. If the production layout differs,
 * SF_CERTS_DIR is the single line to adjust.
 */

if (!defined('ABSPATH')) {
	exit;
}

/* Full-resolution certificates: one level above the WordPress root
   (Local: app/private-certs/  ·  production: public_html/../private-certs/). */
if (!defined('SF_CERTS_DIR')) {
	define('SF_CERTS_DIR', dirname(untrailingslashit(ABSPATH)) . '/private-certs/');
}

if (!defined('SF_CERT_TOKEN_PREFIX')) {
	define('SF_CERT_TOKEN_PREFIX', 'sf_cert_');
}

/**
 * Document registry. `file` is relative to SF_CERTS_DIR unless `source` is
 * 'uploads' (the sample COA is a public teaser document, so it stays in the
 * media tree). `download` is the filename the visitor actually receives —
 * ASCII only, so no header encoding games are needed.
 * `haccp` / `brc` have no file yet: the request is still recorded and
 * forwarded, the visitor simply gets no attachment.
 */
function sinofresh_cert_files() {
	return array(
		'fda'        => array(
			'file'     => 'cert-fda.webp',
			'mime'     => 'image/webp',
			'label'    => 'FDA Registration',
			'download' => 'SINO-FRESH-FDA-Registration.webp',
		),
		'cgmp'       => array(
			'file'     => 'cert-cgmp.webp',
			'mime'     => 'image/webp',
			'label'    => 'cGMP Compliance',
			'download' => 'SINO-FRESH-cGMP-Compliance.webp',
		),
		'iso9001'    => array(
			'file'     => 'cert-iso9001.webp',
			'mime'     => 'image/webp',
			'label'    => 'ISO 9001 Certification',
			'download' => 'SINO-FRESH-ISO-9001.webp',
		),
		'iso22000'   => array(
			'file'     => 'cert-iso22000.webp',
			'mime'     => 'image/webp',
			'label'    => 'FSSC 22000 Certification',
			'download' => 'SINO-FRESH-FSSC-22000.webp',
		),
		'haccp'      => array(
			'file'     => '',
			'mime'     => '',
			'label'    => 'HACCP Certificate',
			'download' => '',
		),
		'brc'        => array(
			'file'     => '',
			'mime'     => '',
			'label'    => 'BRC Certificate',
			'download' => '',
		),
		'coa-sample' => array(
			'file'     => '2026/09/coa-sample.pdf',
			'source'   => 'uploads',
			'mime'     => 'application/pdf',
			'label'    => 'Sample Certificate of Analysis',
			'download' => 'SINO-FRESH-COA-Sample.pdf',
		),
	);
}

/** Absolute path of a document, or '' when the document has no file yet. */
function sinofresh_cert_file_path($cert, $spec) {
	if (!is_array($spec) || empty($spec['file'])) {
		return '';
	}
	if (isset($spec['source']) && 'uploads' === $spec['source']) {
		$uploads = wp_upload_dir();
		return trailingslashit($uploads['basedir']) . $spec['file'];
	}
	return trailingslashit(SF_CERTS_DIR) . $spec['file'];
}

/** Human label for a document key (used in emails and the success payload). */
function sinofresh_cert_label($cert) {
	$certs = sinofresh_cert_files();
	return isset($certs[$cert]) ? $certs[$cert]['label'] : '';
}

/**
 * Mint a one-time download token. Called from the GF Form 5 submission
 * handler; also used by the CLI test helper in tools/.
 */
function sinofresh_cert_mint_token($cert, $email = '', $ttl = DAY_IN_SECONDS) {
	$certs = sinofresh_cert_files();
	if (!isset($certs[$cert])) {
		return '';
	}
	$token = substr(hash('sha256', uniqid('sfc', true) . '|' . $cert . '|' . microtime(true) . '|' . wp_salt('auth')), 0, 40);
	set_transient(SF_CERT_TOKEN_PREFIX . $token, array(
		'cert'  => $cert,
		'email' => (string) $email,
		'time'  => time(),
	), (int) $ttl);
	return $token;
}

/** Public download URL for a minted token. */
function sinofresh_cert_download_url($cert, $token) {
	return add_query_arg(
		array('cert' => rawurlencode($cert), 'token' => rawurlencode($token)),
		rest_url('sinofresh/v1/cert-download')
	);
}

add_action('rest_api_init', function () {
	register_rest_route('sinofresh/v1', '/cert-download', array(
		'methods'             => 'GET',
		'permission_callback' => '__return_true',
		'callback'            => 'sinofresh_cert_download_endpoint',
	));
});

function sinofresh_cert_download_endpoint(WP_REST_Request $request) {
	$cert  = sanitize_key((string) $request->get_param('cert'));
	$token = strtolower(preg_replace('/[^a-fA-F0-9]/', '', (string) $request->get_param('token')));

	$certs = sinofresh_cert_files();
	if (!isset($certs[$cert])) {
		return new WP_REST_Response(array('message' => 'Unknown certificate.'), 404);
	}
	if (40 !== strlen($token)) {
		return new WP_REST_Response(array('message' => 'This download link is invalid or has expired.'), 403);
	}

	$grant = get_transient(SF_CERT_TOKEN_PREFIX . $token);
	if (!is_array($grant) || !isset($grant['cert']) || $cert !== $grant['cert']) {
		return new WP_REST_Response(array('message' => 'This download link is invalid or has expired. Please request the document again.'), 403);
	}
	/* One-time: burn the token before streaming, so a replay of the same URL
	   (from the browser history or the email) cannot fetch the file twice. */
	delete_transient(SF_CERT_TOKEN_PREFIX . $token);

	$spec = $certs[$cert];
	$path = sinofresh_cert_file_path($cert, $spec);
	if ('' === $path || !is_readable($path)) {
		return new WP_REST_Response(array('message' => 'The document is temporarily unavailable. Please email info@zxpet.com.'), 404);
	}

	nocache_headers();
	header('Content-Type: ' . $spec['mime']);
	header('Content-Length: ' . filesize($path));
	header('Content-Disposition: attachment; filename="' . $spec['download'] . '"');
	header('X-Robots-Tag: noindex, nofollow');
	readfile($path);
	exit;
}

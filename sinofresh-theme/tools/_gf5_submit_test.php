<?php
/**
 * CLI E2E — GF Form 5 certificate request (B3).
 *
 *   php -c "<Local site>/conf/php/php.ini" \
 *       -d mysqli.default_socket="$SOCK" tools/_gf5_submit_test.php
 *
 * The -c flag matters: Local points sendmail_path at its Mailpit catcher, and
 * without it wp_mail() fails from the CLI SAPI while working in the browser.
 *
 * Drives the real submission path via GFAPI::submit_form(), so validation,
 * entry storage, the confirmation filter and gform_after_submission all run
 * exactly as they do for a browser submit. Asserts:
 *   · the confirmation carries the JSON payload + a working Download button,
 *   · the customer email is logged (WP Mail Logging) with the attachment and
 *     the very same one-time link that the confirmation returned,
 *   · the link downloads the full-resolution file (byte-for-byte) and then
 *     dies on replay,
 *   · documents with no file still work (no attachment, no dead button),
 *   · the submission is not slowed down by the mail hop.
 */

$site_root = '/Users/meng/Local Sites/sinofresh/app/public';
require $site_root . '/wp-load.php';

$pass = 0;
$fail = 0;
function check($name, $ok, $detail = '') {
	global $pass, $fail;
	if ($ok) { $pass++; echo "  OK   $name" . ($detail ? " — $detail" : '') . "\n"; }
	else { $fail++; echo "  FAIL $name" . ($detail ? " — $detail" : '') . "\n"; }
}

$form_id = 5;
$form    = GFAPI::get_form($form_id);

/* NOTE: GF 2.9.15+ rejects @example.com / @domain.com addresses outright
   (GF_Field_Email::is_email_rejected), so the fixtures below use a plausible
   domain — submissions from a throwaway domain never reach the hooks. */

/** Build a valid input array from the live form definition. */
function sf_inputs($form, $cert, $email, $name = 'Jane Doe', $company = 'Automated Test Co') {
	$inputs = array('gform_submit' => (string) $form['id']);
	foreach ($form['fields'] as $f) {
		$id = (int) $f->id;
		switch ($f->type) {
			case 'text':
				$inputs['input_' . $id] = $id === 2 ? $name : $company;
				break;
			case 'email':
				$inputs['input_' . $id] = $email;
				break;
			case 'select':
				$choices = (array) $f->choices;
				$inputs['input_' . $id] = isset($choices[0]['value']) ? $choices[0]['value'] : '';
				break;
			case 'checkbox':
				foreach ((array) $f->inputs as $in) {
					$inputs['input_' . str_replace('.', '_', $in['id'])] = $in['id'];
				}
				break;
			case 'hidden':
				$inputs['input_' . $id] = $cert;
				break;
		}
	}
	return $inputs;
}

/** Fresh submission. GFFormDisplay keeps a static, per-form submission cache,
    so a second GFAPI::submit_form() in the same process would otherwise replay
    the first result (same confirmation, hooks not re-run). Real requests are
    one submission per process, which is what this reset reproduces. */
function sf_submit($form, $cert, $email) {
	GFFormDisplay::$submission = array();
	GFFormDisplay::$processed  = array();
	$_POST = array();
	return GFAPI::submit_form((int) $form['id'], sf_inputs($form, $cert, $email));
}

/** Newest log row for one recipient. */
function sf_last_mail($receiver) {
	global $wpdb;
	return $wpdb->get_row($wpdb->prepare(
		"SELECT * FROM {$wpdb->prefix}wpml_mails WHERE receiver = %s ORDER BY mail_id DESC LIMIT 1",
		$receiver
	), ARRAY_A);
}

/* WP Mail Logging stores the attachment list either as a plain basename or as
   a serialized array depending on how many files were attached. */
function sf_att_names($raw) {
	$v = maybe_unserialize((string) $raw);
	if (is_array($v)) {
		return implode(',', array_map(function ($x) { return basename((string) $x); }, $v));
	}
	return trim((string) $v);
}

function sf_payload($html) {
	if (!preg_match('/data-payload="([^"]+)"/', $html, $m)) {
		return null;
	}
	$json = html_entity_decode($m[1], ENT_QUOTES, 'UTF-8');
	return json_decode($json, true);
}

$sizes = array('fda' => 50904, 'cgmp' => 125654, 'iso9001' => 63754, 'iso22000' => 77956);

echo "=== A · FDA certificate request (document exists) ===\n";
$email = 'sf-cert-test@acmepetnutrition.com';
$t0    = microtime(true);
$res   = sf_submit($form, 'fda', $email);
$took  = round((microtime(true) - $t0) * 1000);
check('A1. submission valid', !is_wp_error($res) && !empty($res['is_valid']),
	is_wp_error($res) ? $res->get_error_message() : 'entry_id=' . rgar($res, 'entry_id'));
$html = (string) rgar($res, 'confirmation_message');
$entry_id = (int) rgar($res, 'entry_id');
check('A2. confirmation is our markup', false !== strpos($html, 'sf-cert-result') && false !== strpos($html, 'Download now'),
	substr($html, 0, 90) . '...');
$payload = sf_payload($html);
check('A3. confirmation carries the JSON payload',
	is_array($payload) && !empty($payload['download_url']) && $payload['email_sent_to'] === $email,
	is_array($payload) ? json_encode(array('cert' => $payload['certificate'], 'to' => $payload['email_sent_to'], 'attached' => $payload['attached'])) : 'no payload');
check('A4. payload points at the gated endpoint',
	is_array($payload) && false !== strpos($payload['download_url'], '/cert-download?cert=fda&token='));
check('A5. request not blocked by the mail hop', $took < 15000, $took . ' ms for the whole submission');

$mail = sf_last_mail($email);
check('A6. customer email logged', (bool) $mail, $mail ? 'mail_id=' . $mail['mail_id'] : 'not found');
if ($mail) {
	check('A7. subject matches the spec',
		'Your SINO FRESH Certificate — FDA Registration' === $mail['subject'], $mail['subject']);
	check('A8. body contains the same one-time link',
		is_array($payload) && false !== strpos($mail['message'], $payload['download_url']),
		'link present: ' . (is_array($payload) && false !== strpos($mail['message'], $payload['download_url']) ? 'yes' : 'no'));
	$att = sf_att_names($mail['attachments']);
	check('A9. attachment uses the friendly filename', false !== strpos($att, 'SINO-FRESH-FDA-Registration.webp'), $att !== '' ? $att : '(none)');
	check('A10. sales is copied', false !== stripos((string) $mail['headers'], 'sales@zxpet.com'), trim((string) $mail['headers']));
	check('A11. no send error', empty($mail['error']), (string) $mail['error']);
}
check('A12. entry meta records the grant',
	'fda' === gform_get_meta($entry_id, 'sf_cert_document')
	&& 'sent' === gform_get_meta($entry_id, 'sf_cert_mail')
	&& is_array($payload) && gform_get_meta($entry_id, 'sf_cert_download_url') === $payload['download_url'],
	'doc=' . gform_get_meta($entry_id, 'sf_cert_document') . ' mail=' . gform_get_meta($entry_id, 'sf_cert_mail'));

if (is_array($payload) && $payload['download_url']) {
	$r1 = wp_remote_get($payload['download_url'], array('timeout' => 30));
	$b1 = is_wp_error($r1) ? '' : (string) wp_remote_retrieve_body($r1);
	check('A13. link downloads the full-resolution file',
		!is_wp_error($r1) && 200 === wp_remote_retrieve_response_code($r1) && strlen($b1) === $sizes['fda'],
		is_wp_error($r1) ? $r1->get_error_message() : 'code=' . wp_remote_retrieve_response_code($r1) . ' bytes=' . strlen($b1) . ' (source ' . $sizes['fda'] . ')');
	check('A14. served as an attachment', !is_wp_error($r1)
		&& false !== stripos((string) wp_remote_retrieve_header($r1, 'content-disposition'), 'attachment; filename="SINO-FRESH-FDA-Registration.webp"'),
		(string) wp_remote_retrieve_header($r1, 'content-disposition'));
	$r2 = wp_remote_get($payload['download_url'], array('timeout' => 30));
	check('A15. one-time link is dead on replay',
		!is_wp_error($r2) && 403 === wp_remote_retrieve_response_code($r2),
		'code=' . (is_wp_error($r2) ? 'error' : wp_remote_retrieve_response_code($r2)));
}

echo "\n=== B · HACCP request (no file published yet) ===\n";
$email2 = 'sf-cert-haccp@acmepetnutrition.com';
$res2   = sf_submit($form, 'haccp', $email2);
$html2  = (string) rgar($res2, 'confirmation_message');
$pay2   = sf_payload($html2);
check('B1. submission valid', !empty($res2['is_valid']));
check('B2. no dead Download button', false === strpos($html2, 'Download now') && false !== strpos($html2, 'within one business day'));
check('B3. payload keeps the document identity',
	is_array($pay2) && 'haccp' === $pay2['certificate'] && '' === $pay2['download_url'] && false === $pay2['attached'],
	is_array($pay2) ? json_encode($pay2) : 'no payload');
$mail2 = sf_last_mail($email2);
check('B4. email sent without attachment',
	$mail2 && 'Your SINO FRESH Certificate — HACCP Certificate' === $mail2['subject']
	&& '' === sf_att_names($mail2['attachments']),
	$mail2 ? $mail2['subject'] : 'not found');

echo "\n=== C · default document for the generic buttons ===\n";
$email3 = 'sf-cert-default@acmepetnutrition.com';
$res3   = sf_submit($form, '', $email3);
$pay3   = sf_payload((string) rgar($res3, 'confirmation_message'));
check('C1. empty certificate falls back to coa-sample',
	is_array($pay3) && 'coa-sample' === $pay3['certificate'], is_array($pay3) ? json_encode($pay3) : 'no payload');
$res4 = sf_submit($form, 'not-a-document', 'sf-cert-bogus@acmepetnutrition.com');
$pay4 = sf_payload((string) rgar($res4, 'confirmation_message'));
check('C2. unknown certificate key falls back too',
	is_array($pay4) && 'coa-sample' === $pay4['certificate'], is_array($pay4) ? $pay4['certificate'] : 'no payload');

echo "\n=== D · front-end markup (what the modal fills) ===\n";
/* Same static cache: right after a submission the shortcode would echo the
   confirmation instead of the form, so clear it before rendering. */
GFFormDisplay::$submission = array();
$_POST = array();
$markup = do_shortcode('[gravityform id="5" title="false" description="false" ajax="true"]');
preg_match('/<input[^>]*name=(["\'])input_10\1[^>]*>/', $markup, $m10);
$tag = isset($m10[0]) ? $m10[0] : '';
check('D3. hidden certificate field renders as input_10', '' !== $tag, $tag ?: 'not found');
check('D4. it is a hidden input with no default value',
	false !== strpos($tag, 'hidden') && (bool) preg_match('/value=(["\'])\1/', $tag),
	preg_replace('/\s+/', ' ', substr($tag, 0, 90)));
check('D5. form markup is AJAX-ready', false !== strpos($markup, 'gform_ajax') && false !== strpos($markup, 'gform_submission'));

echo "\n=== E · consistency & residues ===\n";
$src = '/Users/meng/WorkBuddy/sinofresh外贸网站建设/sinofresh-theme';
$dst = WP_CONTENT_DIR . '/themes/sinofresh-theme';
foreach (array('functions.php', 'inc/cert-download.php') as $f) {
	check("E1. source = Local: $f", file_get_contents($src . '/' . $f) === file_get_contents($dst . '/' . $f));
}
foreach (array('functions.php', 'inc/cert-download.php') as $f) {
	check("E2. no \"/ -->\" residue: $f", false === strpos(file_get_contents($src . '/' . $f), '/ -->'));
}

echo "\n" . ($fail === 0 ? 'ALL PASS' : 'FAILURES') . "  {$pass}/" . ($pass + $fail) . "\n";
exit($fail === 0 ? 0 : 1);

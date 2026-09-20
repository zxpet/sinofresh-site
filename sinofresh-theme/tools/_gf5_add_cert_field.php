<?php
/**
 * CLI — add the `certificate` hidden field to GF Form 5 (Request COA).
 *
 *   php -d mysqli.default_socket="$SOCK" tools/_gf5_add_cert_field.php
 *
 * Idempotent: re-running finds the field and does nothing. The field is what
 * the Quality-page modal fills with fda / cgmp / iso9001 / iso22000 / haccp /
 * brc / coa-sample; inc/cert-download.php maps that value to a document.
 */

$site_root = '/Users/meng/Local Sites/sinofresh/app/public';
require $site_root . '/wp-load.php';

$form_id = 5;
$form    = GFAPI::get_form($form_id);
if (!is_array($form)) {
	fwrite(STDERR, "Form {$form_id} not found\n");
	exit(1);
}

$is_cert_field = function ($field) {
	return 'certificate' === strtolower((string) $field->label)
		|| 'certificate' === strtolower((string) $field->adminLabel)
		|| false !== strpos((string) $field->cssClass, 'sf-cert-field');
};

/* Drop duplicates, keep the first (lowest id) so re-runs are idempotent. */
$seen_cert = false;
$kept      = array();
foreach ($form['fields'] as $field) {
	if ($is_cert_field($field)) {
		if ($seen_cert) {
			echo "removing duplicate certificate field id={$field->id}\n";
			continue;
		}
		$seen_cert = true;
	}
	$kept[] = $field;
}
if (count($kept) !== count($form['fields'])) {
	$form['fields'] = $kept;
	GFAPI::update_form($form);
	$form = GFAPI::get_form($form_id);
}

$existing = null;
foreach ($form['fields'] as $field) {
	if ($is_cert_field($field)) {
		$existing = $field;
		break;
	}
}

if ($existing) {
	echo "already present: id={$existing->id} type={$existing->type} label={$existing->label}\n";
} else {
	$ids = array_map(function ($f) { return (int) $f->id; }, $form['fields']);
	$new_id = max($ids) + 1;
	$form['fields'][] = GF_Fields::create(array(
		'id'                     => $new_id,
		'type'                   => 'hidden',
		'label'                  => 'Certificate',
		'adminLabel'             => 'Certificate',
		'defaultValue'           => '',
		'cssClass'               => 'sf-cert-field',
		'pageNumber'             => 1,
		'allowsPrepopulate'      => true,
		'layoutGridColumnSpan'   => 12,
	));
	$result = GFAPI::update_form($form);
	if (is_wp_error($result)) {
		fwrite(STDERR, 'update_form failed: ' . $result->get_error_message() . "\n");
		exit(1);
	}
	echo "added hidden field id={$new_id} label=Certificate\n";
}

/* --- read back ------------------------------------------------------- */
$after = GFAPI::get_form($form_id);

/* Keep the admin field-id counter ahead of the highest id, otherwise the next
   field added through the form editor would reuse id 10 and shadow this one. */
$max_id = 0;
foreach ($after['fields'] as $f) {
	$max_id = max($max_id, (int) $f->id);
}
if ((int) rgar($after, 'nextFieldId') <= $max_id) {
	$after['nextFieldId'] = $max_id + 1;
	$result = GFAPI::update_form($after);
	echo 'nextFieldId bumped to ' . $after['nextFieldId'] . "\n";
	$after = GFAPI::get_form($form_id);
}

echo "--- form {$form_id} fields after ---\n";
foreach ($after['fields'] as $f) {
	printf("  %-4s %-10s %s%s\n", $f->id, $f->type, $f->label, $f->isRequired ? ' *' : '');
}
echo 'confirmations in meta: ' . count((array) rgar($after, 'confirmations', array())) . "\n";
echo 'notifications in meta: ' . count((array) rgar($after, 'notifications', array())) . "\n";

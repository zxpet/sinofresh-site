<?php
/**
 * Batch2C Step0 probe — dosage still resolver.
 * Run:  wp eval-file /tmp/b2s0_img_probe.php
 */
$slugs = array('soft-chews', 'tablets', 'powders', 'liquids', 'pastes', 'dental-chews', 'drops', 'fish-oil');
foreach ($slugs as $s) {
	$u = sinofresh_formula_card_image($s);
	printf("%-14s %-8s %s\n", $s, ($u === '' ? 'EMPTY' : 'ok'), $u);
}
echo "--- negatives / edge cases ---\n";
foreach (array('no-such-form', '', 'Soft Chews', '../etc/passwd') as $bad) {
	$u = sinofresh_formula_card_image($bad);
	printf("%-18s -> [%s]\n", var_export($bad, true), $u);
}
$ud = wp_upload_dir();
echo "basedir=" . $ud['basedir'] . "\nbaseurl=" . $ud['baseurl'] . "\n";

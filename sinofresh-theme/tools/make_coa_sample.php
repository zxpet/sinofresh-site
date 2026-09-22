<?php
/**
 * One-off generator: the sample Certificate of Analysis PDF shown in the
 * Quality page's COA previewer (and served by its "Download Sample PDF").
 *
 * Run from the theme directory with the Local stack up:
 *   php -d mysqli.default_socket="$SOCK" tools/make_coa_sample.php
 *
 * Output: wp-content/uploads/2026/09/coa-sample.pdf
 *
 * Reuses sinofresh_config_pdf_dompdf() from inc/config-pdf.php, so the sample
 * inherits the same font/subsetting settings as the configurator PDFs.
 * Regenerate (and re-upload) whenever the sample content changes.
 */

$root = '/Users/meng/Local Sites/sinofresh/app/public';
require_once $root . '/wp-load.php';

$esc = 'esc_html';

$rows = array(
	array('Appearance', 'Light brown chew, uniform shape, no foreign matter', 'Visual', 'Conforms', 'PASS'),
	array('Active Ingredient Content (Glucosamine HCl)', '95.0 - 105.0% of label claim', 'HPLC', '98.6% of label claim', 'PASS'),
	array('Moisture', '&le; 10.0%', 'Loss on drying', '6.4%', 'PASS'),
	array('Heavy Metals - Lead (Pb)', '&le; 1.0 mg/kg', 'AAS', '&lt; 0.1 mg/kg', 'PASS'),
	array('Heavy Metals - Arsenic (As)', '&le; 1.0 mg/kg', 'AAS', '&lt; 0.1 mg/kg', 'PASS'),
	array('Heavy Metals - Mercury (Hg)', '&le; 0.1 mg/kg', 'AAS', '&lt; 0.01 mg/kg', 'PASS'),
	array('Heavy Metals - Cadmium (Cd)', '&le; 0.5 mg/kg', 'AAS', '&lt; 0.02 mg/kg', 'PASS'),
	array('Total Plate Count', '&le; 10,000 CFU/g', 'ISO 4833', '320 CFU/g', 'PASS'),
	array('Yeast &amp; Mould', '&le; 100 CFU/g', 'ISO 21527', '&lt; 10 CFU/g', 'PASS'),
	array('Escherichia coli', 'Absent / g', 'ISO 16649', 'Absent', 'PASS'),
	array('Salmonella', 'Absent / 25 g', 'ISO 6579', 'Absent', 'PASS'),
);

$product = array(
	'Product Name'      => 'Soft Chews - Joint Support',
	'Dosage Form'       => 'Soft chew, 4 g',
	'Batch Number'      => 'SF-2026-0915',
	'Production Date'   => 'September 15, 2026',
	'Batch Size'        => '480 kg (120,000 pieces)',
	'Packaging'         => '60-count HDPE bottle, induction seal',
	'Manufactured for'  => 'Sample Brand Co., Ltd.',
	'Manufacturing Site'=> 'Shandong SINO FRESH Pet Food Co., Ltd.',
);

$css = '
	@page { margin: 13mm 15mm; }
	body { font-family: "dejavu sans", helvetica, sans-serif; font-size: 8.5pt; line-height: 1.4; color: #2A2A2A; margin: 0; }
	.hd { overflow: hidden; }
	.hd-logo { display: block; font-size: 14pt; font-weight: bold; color: #1B4D3E; letter-spacing: 1px; float: left; }
	.hd-meta { display: block; font-size: 8pt; color: #6B6B6B; text-align: right; }
	.accent-rule { width: 28px; height: 2px; background: #5AB735; margin: 10px 0 8px; }
	.sample { font-size: 7.5pt; color: #B54E0F; letter-spacing: 1px; font-weight: bold; }
	h1 { font-size: 13pt; color: #1B4D3E; margin: 0 0 3px; }
	.sub { font-size: 8pt; color: #6B6B6B; margin: 0 0 8px; }
	h2 { font-size: 9.5pt; color: #1B4D3E; margin: 10px 0 4px; letter-spacing: 0.5px; }
	table { width: 100%; border-collapse: collapse; }
	table.prod td { border-bottom: 0.5pt solid #E0E5DC; padding: 3pt 2pt; vertical-align: top; }
	td.k { width: 32%; color: #6B6B6B; }
	td.v { font-weight: bold; }
	table.res th { background: #1B4D3E; color: #FFFFFF; font-size: 7.5pt; letter-spacing: 0.6px; text-align: left; padding: 4pt 4pt; }
	table.res td { border-bottom: 0.5pt solid #E0E5DC; padding: 3pt 4pt; vertical-align: top; }
	td.status { color: #1B4D3E; font-weight: bold; white-space: nowrap; }
	.note { margin: 9px 0 0; font-size: 7.5pt; color: #6B6B6B; }
	.sig { width: 100%; margin-top: 12px; }
	.sig td { width: 50%; padding-top: 16px; vertical-align: bottom; }
	.sig-line { border-top: 0.5pt solid #9AA5A0; padding-top: 4pt; font-size: 8pt; color: #6B6B6B; }
	.ft { margin-top: 12px; font-size: 7.5pt; color: #6B6B6B; border-top: 0.5pt solid #E0E5DC; padding-top: 6px; }
';

$html = '<html><head><meta charset="utf-8"><style>' . $css . '</style></head><body>';

$html .= '<div class="hd"><span class="hd-logo">SINO FRESH</span>'
	. '<span class="hd-meta">Certificate of Analysis<br>Batch No. SF-2026-0915<br>Issued September 15, 2026</span></div>';
$html .= '<div class="accent-rule"></div>';
$html .= '<h1>Certificate of Analysis</h1>';
$html .= '<p class="sub"><span class="sample">SAMPLE DOCUMENT - FOR ILLUSTRATION ONLY</span></p>';

$html .= '<h2>PRODUCT IDENTIFICATION</h2><table class="prod">';
foreach ($product as $k => $v) {
	$html .= '<tr><td class="k">' . $esc($k) . '</td><td class="v">' . $esc($v) . '</td></tr>';
}
$html .= '</table>';

$html .= '<h2>TEST RESULTS</h2><table class="res"><thead><tr>'
	. '<th>Test Item</th><th>Specification</th><th>Method</th><th>Result</th><th>Status</th>'
	. '</tr></thead><tbody>';
foreach ($rows as $r) {
	$html .= '<tr><td>' . $esc($r[0]) . '</td><td>' . $esc($r[1]) . '</td><td>' . $esc($r[2]) . '</td><td>' . $esc($r[3]) . '</td><td class="status">' . $esc($r[4]) . '</td></tr>';
}
$html .= '</tbody></table>';

$html .= '<p class="note">This Certificate of Analysis applies only to the batch listed above. Testing was performed in the in-house QC laboratory '
	. 'of the manufacturing site. Batch records and retention samples are kept for two years from the production date.</p>';

$html .= '<table class="sig"><tr>'
	. '<td><div class="sig-line">QC Lead - Quality Control</div></td>'
	. '<td><div class="sig-line">QA Manager - Quality Assurance</div></td>'
	. '</tr></table>';

$html .= '<p class="ft">Shandong SINO FRESH Pet Food Co., Ltd. &middot; Building B3, No. 22 Zhongshan Road, Yihe New Area, Linyi, Shandong, China'
	. ' &middot; www.zxpet.com &middot; sales@zxpet.com' . '</p>';

$html .= '</body></html>';

$pdf = sinofresh_config_pdf_dompdf($html);
if (is_wp_error($pdf)) {
	fwrite(STDERR, 'ERROR: ' . $pdf->get_error_message() . "\n");
	exit(1);
}

$dir = WP_CONTENT_DIR . '/uploads/2026/09';
if (!is_dir($dir)) {
	mkdir($dir, 0755, true);
}
$out = $dir . '/coa-sample.pdf';
file_put_contents($out, $pdf);
echo 'WROTE ' . $out . ' (' . strlen($pdf) . " bytes)\n";

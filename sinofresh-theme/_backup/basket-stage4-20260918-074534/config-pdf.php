<?php
/**
 * SINO FRESH — Configurator PDF summary (dosage pages).
 *
 * POST /wp-json/sinofresh/v1/config-pdf
 * Body JSON: {
 *   slug:    "soft-chews" | ... (required, one of the 8 dosage pages)
 *   config:  { shape, color, flavor, weight, count, packaging, functions, shelf_life }
 *   formula: { name, sections: [{label, value}] } | omitted  (standard formula)
 *   email:   ""            -> stream the PDF back (application/pdf)
 *            "x@y.z"       -> generate + email a copy (cc sales@zxpet.com),
 *                             answer { sent: true, ref, filename }
 * }
 *
 * Dompdf lives in wp-content/vendor/ (composer). NOTE FOR LAUNCH: the vendor/
 * directory is NOT part of the theme — it must be shipped to production too.
 */

if (!defined('ABSPATH')) {
	exit;
}

add_action('rest_api_init', function () {
	register_rest_route('sinofresh/v1', '/config-pdf', array(
		'methods'             => 'POST',
		'permission_callback' => '__return_true',
		'callback'            => 'sinofresh_config_pdf_endpoint',
	));
});

function sinofresh_config_pdf_endpoint(WP_REST_Request $request) {
	$slugs = array(
		'soft-chews' => 'Soft Chews', 'tablets' => 'Tablets', 'powders' => 'Powders',
		'pastes' => 'Pastes', 'drops' => 'Drops', 'liquids' => 'Liquids',
		'fish-oil' => 'Fish Oil', 'dental-chews' => 'Dental Chews',
	);
	$data = $request->get_json_params();
	if (!is_array($data)) {
		return new WP_REST_Response(array('message' => 'Invalid JSON body.'), 400);
	}
	$slug = isset($data['slug']) ? sanitize_key((string) $data['slug']) : '';
	if (!isset($slugs[$slug])) {
		return new WP_REST_Response(array('message' => 'Unknown dosage form slug.'), 400);
	}

	$keys  = array('shape', 'color', 'flavor', 'weight', 'count', 'packaging', 'functions', 'shelf_life');
	$config = array();
	foreach ($keys as $k) {
		$v = isset($data['config'][$k]) ? sanitize_text_field((string) $data['config'][$k]) : '';
		$config[$k] = mb_substr($v, 0, 80);
	}
	if (in_array('', $config, true)) {
		return new WP_REST_Response(array('message' => 'Please complete all configuration options.'), 422);
	}

	/* Standard formula payload: { name, sections: [{label, value}, ...] } */
	$formula = array();
	if (!empty($data['formula']) && is_array($data['formula'])) {
		$name = isset($data['formula']['name']) ? sanitize_text_field((string) $data['formula']['name']) : '';
		if ($name !== '') {
			$formula['name'] = mb_substr($name, 0, 80);
			$formula['sections'] = array();
			if (!empty($data['formula']['sections']) && is_array($data['formula']['sections'])) {
				foreach ($data['formula']['sections'] as $sec) {
					if (!is_array($sec) || !isset($sec['label'], $sec['value'])) {
						continue;
					}
					$formula['sections'][] = array(
						'label' => mb_substr(sanitize_text_field((string) $sec['label']), 0, 60),
						'value' => mb_substr(sanitize_text_field((string) $sec['value']), 0, 400),
					);
				}
			}
		}
	}

	/* Unique reference: SF-YYYYMMDD-XXXX (no lookalikes) */
	$alphabet = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789';
	$rand = '';
	for ($i = 0; $i < 4; $i++) {
		$rand .= $alphabet[random_int(0, strlen($alphabet) - 1)];
	}
	$ref = 'SF-' . gmdate('Ymd') . '-' . $rand;

	$pdf_bytes = sinofresh_config_pdf_render($slugs[$slug], $config, $formula, $ref);
	if (is_wp_error($pdf_bytes)) {
		return new WP_REST_Response(array('message' => $pdf_bytes->get_error_message()), 503);
	}

	$filename = sinofresh_config_pdf_filename($slugs[$slug], $config, $ref);

	/* Email mode: attach and send, answer JSON. */
	$email = isset($data['email']) ? trim((string) $data['email']) : '';
	if ($email !== '') {
		$email = sanitize_email($email);
		if (!is_email($email)) {
			return new WP_REST_Response(array('message' => 'Invalid email address.'), 422);
		}
		$tmp = tempnam(sys_get_temp_dir(), 'sf-pdf-');
		file_put_contents($tmp, $pdf_bytes);
		$subject = 'Your SINO FRESH Configuration Summary (' . $ref . ')';
		$body = "Thank you for configuring a product with SINO FRESH.\n\n"
			. 'Reference: ' . $ref . "\n"
			. 'Dosage form: ' . $slugs[$slug] . "\n\n"
			. "A copy of your configuration summary is attached.\n"
			. "Quote the reference above when you contact us for a faster response.\n\n"
			. "SINO FRESH — zxpet.com";
		$headers = array('Cc: sales@zxpet.com');
		$sent = wp_mail($email, $subject, $body, $headers, array($tmp));
		wp_delete_file($tmp);
		if (!$sent) {
			return new WP_REST_Response(array('message' => 'Email could not be sent. Please try again.'), 502);
		}
		return new WP_REST_Response(array('sent' => true, 'ref' => $ref, 'filename' => $filename), 200);
	}

	/* Download mode: stream the PDF. The REST server JSON-encodes everything
	   returned from a callback, so binary output must be echoed directly. */
	header('Content-Type: application/pdf');
	header('Content-Disposition: attachment; filename="' . $filename . '"');
	header('Cache-Control: no-store');
	header('X-Robots-Tag: noindex');
	echo $pdf_bytes;
	exit;
}

function sinofresh_config_pdf_filename($label, $config, $ref) {
	$fn = $config['functions'] !== '' ? $config['functions'] : 'Custom';
	$fn = str_replace('&', 'and', $fn);
	$name = 'SINO-FRESH-' . str_replace(' ', '-', $label . '-' . $fn) . '-' . $ref . '.pdf';
	return preg_replace('/[^A-Za-z0-9.\-]/', '', $name);
}

/**
 * Render the two-page A4 summary. Returns raw PDF bytes or WP_Error.
 */
function sinofresh_config_pdf_render($label, $config, $formula, $ref) {
	$autoload = WP_CONTENT_DIR . '/vendor/autoload.php';
	if (!file_exists($autoload)) {
		return new WP_Error('dompdf_missing', 'PDF library not installed (wp-content/vendor missing).');
	}
	require_once $autoload;

	$esc = 'esc_html';
	$date = gmdate('F j, Y');
	$formula_base = !empty($formula['name']) ? $formula['name'] . ' (Standard)' : 'Custom';
	$product_title = $label . ' — ' . ($config['functions'] !== '' ? $config['functions'] : 'Custom') . ' Formula';

	/* Config table rows */
	$rows = array(
		'Dosage Form'         => $label,
		'Formula Base'        => $formula_base,
		'Shape'               => $config['shape'],
		'Color'               => $config['color'],
		'Flavor'              => $config['flavor'],
		'Piece Weight'        => $config['weight'],
		'Count per Container' => $config['count'],
		'Packaging'           => $config['packaging'],
		'Function'            => $config['functions'],
		'Shelf Life'          => $config['shelf_life'],
	);
	$tr = '';
	foreach ($rows as $k => $v) {
		$tr .= '<tr><td class="cfg-k">' . call_user_func($esc, $k) . '</td><td class="cfg-v">' . call_user_func($esc, $v) . '</td></tr>';
	}

	/* Formula block: standard shows the label/value sections, custom shows a notice */
	if (!empty($formula['name'])) {
		$fs = '';
		foreach ($formula['sections'] as $sec) {
			$fs .= '<h4 class="sec-h">' . call_user_func($esc, $sec['label']) . '</h4>'
				. '<p class="sec-p">' . call_user_func($esc, $sec['value']) . '</p>';
		}
		$formula_block = '<p class="formula-tag">FORMULA (Standard)</p>'
			. '<p class="formula-name">' . call_user_func($esc, $formula['name']) . '</p>' . $fs;
	} else {
		$formula_block = '<p class="formula-tag">FORMULA</p>'
			. '<p class="formula-name">Custom Formula — to be developed</p>'
			. '<p class="sec-p">Our R&amp;D team will develop a custom formula based on your requirements. Submit an inquiry to proceed.</p>';
	}

	$certs = array('FDA', 'cGMP', 'ISO 9001', 'FSSC 22000', 'HACCP', 'BRC');
	$badge_html = '';
	foreach ($certs as $c) {
		$badge_html .= '<span class="badge">' . call_user_func($esc, $c) . '</span>';
	}

	/* Shared header/footer; $page and $total come from the loop below */
	$page_header = function ($page, $total) use ($esc, $ref, $date) {
		return '<div class="hd"><span class="hd-logo">SINO FRESH</span><span class="hd-meta">Configuration Summary<br>Ref: ' . call_user_func($esc, $ref) . ' &middot; Date: ' . $date . '</span></div>';
	};
	$page_footer = function ($page, $total) use ($esc) {
		$f = $page === $total
			? 'Page ' . $page . ' of ' . $total . ' &middot; Shandong SINO FRESH Pet Food Co., Ltd. &middot; zxpet.com'
			: 'Page ' . $page . ' of ' . $total . ' &middot; zxpet.com';
		return '<div class="ft">' . $f . '</div>';
	};

	$page1 = $page_header(1, 2)
		. '<div class="accent-rule"></div>'
		. '<h1>' . call_user_func($esc, $product_title) . '</h1>'
		. '<table class="cfg">' . $tr . '</table>'
		. '<div class="formula-box">' . $formula_block . '</div>'
		. $page_footer(1, 2);

	$page2 = $page_header(2, 2)
		. '<div class="accent-rule"></div>'
		. '<h2>MANUFACTURING</h2>'
		. '<p class="sec-p">15,000 m&sup2; production facility &middot; ISO 8 cleanroom &middot; 1,000 m&sup2; R&amp;D laboratory &middot; 100+ production &amp; testing equipment</p>'
		. '<h2>CERTIFICATIONS</h2>'
		. '<div class="badges">' . $badge_html . '</div>'
		. '<h2>QUALITY ASSURANCE</h2>'
		. '<ul class="qa"><li>Every batch tested with COA</li><li>Full traceability from raw material</li><li>Retention samples kept per batch</li></ul>'
		. '<h2>NEXT STEPS</h2>'
		. '<p class="sec-p">To proceed with this configuration:</p>'
		. '<ul class="steps">'
		. '<li><strong>Request a sample</strong><br>info@zxpet.com &middot; +86 539 866 9539</li>'
		. '<li><strong>Book a factory tour</strong><br>zxpet.com/factory-tour</li>'
		. '<li><strong>Submit an inquiry</strong><br>zxpet.com/contact</li>'
		. '</ul>'
		. '<p class="ref-note">Quote reference <strong>' . call_user_func($esc, $ref) . '</strong> for faster response.</p>'
		. $page_footer(2, 2);

	$css = '
		@page { margin: 18mm 20mm; }
		/* DejaVu Sans: the Dompdf bundled Unicode face. The Helvetica core
		   font lacks the ≥ and → glyphs (they rendered as 3 / ?). Closest
		   bundled stand-in for the Inter face used on the site. */
		body { font-family: "dejavu sans", helvetica, sans-serif; font-size: 10pt; line-height: 1.5; color: #2A2A2A; margin: 0; }
		.hd { overflow: hidden; }
		.hd-logo { display: block; font-size: 14pt; font-weight: bold; color: #1B4D3E; letter-spacing: 1px; float: left; }
		.hd-meta { display: block; font-size: 8pt; color: #6B6B6B; text-align: right; }
		.ft { margin-top: 18px; font-size: 8pt; color: #6B6B6B; border-top: 0.5pt solid #E0E5DC; padding-top: 6px; }
		.accent-rule { width: 28px; height: 2px; background: #5AB735; margin: 14px 0 10px; }
		h1 { font-size: 14pt; color: #1B4D3E; margin: 0 0 14px; }
		h2 { font-size: 12pt; color: #1B4D3E; margin: 16px 0 6px; letter-spacing: 0.5px; }
		.page-break { page-break-before: always; }
		table.cfg { width: 100%; border-collapse: collapse; margin: 6px 0 14px; }
		table.cfg td { border-bottom: 0.5pt solid #E0E5DC; padding: 4.5pt 2pt; }
		td.cfg-k { width: 42%; color: #6B6B6B; }
		td.cfg-v { font-weight: bold; color: #2A2A2A; }
		.formula-box { margin-top: 10px; }
		.formula-tag { font-size: 8pt; font-weight: bold; letter-spacing: 1.5px; color: #5AB735; margin: 0 0 4px; }
		.formula-name { font-size: 11pt; font-weight: bold; color: #1B4D3E; margin: 0 0 6px; }
		.sec-h { font-size: 10pt; color: #1B4D3E; margin: 8px 0 2px; }
		.sec-p { margin: 2px 0; }
		.badges { margin: 4px 0; }
		.badge { display: inline-block; border: 0.75pt solid #1B4D3E; color: #1B4D3E; font-size: 8pt; font-weight: bold; padding: 2pt 8pt; margin: 0 6pt 6pt 0; }
		ul.qa, ul.steps { margin: 4px 0 0; padding-left: 14pt; }
		ul.qa li, ul.steps li { margin-bottom: 4pt; }
		ul.steps { list-style: none; padding-left: 0; }
		ul.steps li:before { content: "\2192"; color: #5AB735; font-weight: bold; margin-right: 6pt; }
		.ref-note { margin-top: 12px; }
	';

	$html = '<html><head><meta charset="utf-8"><style>' . $css . '</style></head><body>'
		. $page1
		. '<div class="page-break"></div>'
		. $page2
		. '</body></html>';

	try {
		$dompdf = new \Dompdf\Dompdf(array(
			'isRemoteEnabled' => false,
			'chroot'          => WP_CONTENT_DIR,
			/* Ghostscript chokes on Dompdf's subsetted TTF streams; embedding
			   the full font produces files every viewer (and gs) reads. */
			'fontSubsetting'  => false,
		));
		$dompdf->loadHtml($html);
		$dompdf->setPaper('A4', 'portrait');
		$dompdf->render();
		return $dompdf->output();
	} catch (\Throwable $e) {
		return new WP_Error('pdf_render_failed', 'PDF rendering failed: ' . $e->getMessage());
	}
}

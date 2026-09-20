<?php
/**
 * SINO FRESH — Configurator PDF summary (dosage pages).
 *
 * POST /wp-json/sinofresh/v1/config-pdf
 * Body JSON: {
 *   slug:    "soft-chews" | ... (required, one of the 8 dosage pages)
 *   config:  [ { label: "Shape", value: "Bone" }, ... ]  — label/value pairs
 *            built by configurator.js straight from the page markup, so any
 *            dosage form renders correctly (no hardcoded key map). Values
 *            may be "Custom: <buyer text>".
 *   formula: { name, sections: [{label, value}] } | omitted  (standard formula)
 *   email:   ""            -> stream the PDF back (application/pdf)
 *            "x@y.z"       -> generate + email a copy (cc sales@zxpet.com),
 *                             answer { sent: true, ref, filename }
 * }
 * OR basket mode (inquiry basket, stage 4):
 * {
 *   basket: [{ slug, summary: "Dosage Form: X | Key: Value | ...", formula: "name" }, ...]  (1-8)
 *   email:  same dual mode as above
 * }
 * Basket mode renders ONE SF reference across all pages: a summary page,
 * one configuration page per dosage form, and the shared company page.
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

	/* === Basket mode (stage 4): one SF reference for the whole basket ==== */
	$basket_raw = isset($data['basket']) && is_array($data['basket']) ? $data['basket'] : array();
	if ($basket_raw) {
		if (count($basket_raw) > 8) {
			return new WP_REST_Response(array('message' => 'Basket can contain at most 8 items.'), 422);
		}
		$items = array();
		$seen  = array();
		foreach ($basket_raw as $raw_item) {
			if (!is_array($raw_item)) {
				continue;
			}
			$s = isset($raw_item['slug']) ? sanitize_key((string) $raw_item['slug']) : '';
			if (!isset($slugs[$s]) || isset($seen[$s])) {
				continue;
			}
			$seen[$s] = true;
			$items[] = array(
				'label'   => $slugs[$s],
				'pairs'   => sinofresh_config_pdf_parse_summary(isset($raw_item['summary']) ? (string) $raw_item['summary'] : ''),
				'formula' => isset($raw_item['formula']) ? mb_substr(sanitize_text_field((string) $raw_item['formula']), 0, 80) : '',
			);
		}
		if (!$items) {
			return new WP_REST_Response(array('message' => 'No valid basket items.'), 422);
		}

		$ref = sinofresh_config_pdf_ref();
		$pdf_bytes = sinofresh_basket_pdf_render($items, $ref);
		if (is_wp_error($pdf_bytes)) {
			return new WP_REST_Response(array('message' => $pdf_bytes->get_error_message()), 503);
		}
		$filename = 'SINO-FRESH-Basket-' . $ref . '.pdf';

		$email = isset($data['email']) ? trim((string) $data['email']) : '';
		if ($email !== '') {
			$email = sanitize_email($email);
			if (!is_email($email)) {
				return new WP_REST_Response(array('message' => 'Invalid email address.'), 422);
			}
			$tmp = tempnam(sys_get_temp_dir(), 'sf-pdf-');
			file_put_contents($tmp, $pdf_bytes);
			$names = implode(', ', wp_list_pluck($items, 'label'));
			$subject = 'Your SINO FRESH Inquiry Basket Summary (' . $ref . ')';
			$body = "Thank you for configuring products with SINO FRESH.\n\n"
				. 'Reference: ' . $ref . "\n"
				. 'Items in this basket (' . count($items) . '): ' . $names . "\n\n"
				. "A copy of your inquiry basket summary is attached.\n"
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

		header('Content-Type: application/pdf');
		header('Content-Disposition: attachment; filename="' . $filename . '"');
		header('Cache-Control: no-store');
		header('X-Robots-Tag: noindex');
		echo $pdf_bytes;
		exit;
	}
	/* === Single-configuration mode (unchanged) ============================ */

	$slug = isset($data['slug']) ? sanitize_key((string) $data['slug']) : '';
	if (!isset($slugs[$slug])) {
		return new WP_REST_Response(array('message' => 'Unknown dosage form slug.'), 400);
	}

	/* Configuration arrives as label/value pairs straight from the page
	   markup (configurator.js buildConfigPairs). The old hardcoded
	   soft-chews key map rendered empty rows on the other 7 pages. */
	$config = array();
	$raw_cfg = isset($data['config']) && is_array($data['config']) ? $data['config'] : array();
	foreach ($raw_cfg as $pair) {
		if (!is_array($pair) || !isset($pair['label'])) {
			continue;
		}
		$label = trim((string) $pair['label']);
		$value = trim(isset($pair['value']) ? (string) $pair['value'] : '');
		if ($label === '' || $value === '') {
			return new WP_REST_Response(array('message' => 'Please complete all configuration options.'), 422);
		}
		$config[] = array(
			'label' => mb_substr(sanitize_text_field($label), 0, 40),
			'value' => mb_substr(sanitize_text_field($value), 0, 120),
		);
	}
	if (!$config) {
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
	$ref = sinofresh_config_pdf_ref();

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

/* Value of the Function/Functions pair in a label/value config list —
   drives the PDF product title and the download filename. A custom
   function ("Custom: Hip & joint…") contributes its text without the
   "Custom: " prefix, which reads badly in a title/filename. */
function sinofresh_config_pdf_function_value($config_pairs) {
	foreach ($config_pairs as $p) {
		if (strcasecmp($p['label'], 'Function') === 0 || strcasecmp($p['label'], 'Functions') === 0) {
			$v = $p['value'];
			if (stripos($v, 'Custom: ') === 0) {
				$v = trim(mb_substr($v, 8));
			}
			return $v !== '' ? $v : 'Custom';
		}
	}
	return '';
}

function sinofresh_config_pdf_filename($label, $config, $ref) {
	$fn = sinofresh_config_pdf_function_value($config);
	$fn = $fn !== '' ? $fn : 'Custom';
	$fn = str_replace('&', 'and', $fn);
	$name = 'SINO-FRESH-' . str_replace(' ', '-', $label . '-' . $fn) . '-' . $ref . '.pdf';
	return preg_replace('/[^A-Za-z0-9.\-]/', '', $name);
}

/* Unique reference shared by both modes: SF-YYYYMMDD-XXXX (no lookalikes). */
function sinofresh_config_pdf_ref() {
	$alphabet = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789';
	$rand = '';
	for ($i = 0; $i < 4; $i++) {
		$rand .= $alphabet[random_int(0, strlen($alphabet) - 1)];
	}
	return 'SF-' . gmdate('Ymd') . '-' . $rand;
}

/* Basket summaries arrive as "Dosage Form: X | Key: Value | ..." strings
   built by configurator.js. Split into label/value pairs for the tables. */
function sinofresh_config_pdf_parse_summary($summary) {
	$pairs = array();
	foreach (explode('|', sanitize_text_field($summary)) as $chunk) {
		$chunk = trim($chunk);
		$pos = $chunk !== '' ? strpos($chunk, ':') : false;
		if ($pos === false) {
			continue;
		}
		$pairs[] = array(
			'label' => mb_substr(trim(substr($chunk, 0, $pos)), 0, 40),
			'value' => mb_substr(trim(substr($chunk, $pos + 1)), 0, 120),
		);
	}
	return $pairs;
}

/* Shared stylesheet for both renderers. DejaVu Sans: the Dompdf bundled
   Unicode face — the Helvetica core font lacks the ≥ and → glyphs
   (closest bundled stand-in for the Inter face used on the site). */
function sinofresh_config_pdf_css() {
	return '
		@page { margin: 18mm 20mm; }
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
		table.sum { width: 100%; border-collapse: collapse; margin: 6px 0 14px; }
		table.sum td { border-bottom: 0.5pt solid #E0E5DC; padding: 6pt 2pt; vertical-align: top; }
		table.sum tr.sum-head td { color: #6B6B6B; font-size: 8pt; font-weight: bold; letter-spacing: 1px; text-transform: uppercase; border-bottom: 0.75pt solid #1B4D3E; }
		td.sum-n { width: 6%; font-weight: bold; color: #5AB735; }
		td.sum-f { width: 26%; font-weight: bold; color: #1B4D3E; }
		td.sum-v { width: 26%; color: #2A2A2A; }
		td.sum-o { color: #6B6B6B; }
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
}

/* Build the PDF bytes for a full HTML document (shared Dompdf setup). */
function sinofresh_config_pdf_dompdf($html) {
	$autoload = WP_CONTENT_DIR . '/vendor/autoload.php';
	if (!file_exists($autoload)) {
		return new WP_Error('dompdf_missing', 'PDF library not installed (wp-content/vendor missing).');
	}
	require_once $autoload;
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

/* Basket PDF (stage 4): a summary page, one configuration page per dosage
   form, and the shared company page — all under ONE SF reference. */
function sinofresh_basket_pdf_render($items, $ref) {
	$esc = 'esc_html';
	$date = gmdate('F j, Y');
	$total = count($items) + 2;

	$page_header = function ($page) use ($esc, $ref, $date) {
		return '<div class="hd"><span class="hd-logo">SINO FRESH</span><span class="hd-meta">Inquiry Basket Summary<br>Ref: ' . call_user_func($esc, $ref) . ' &middot; Date: ' . $date . '</span></div>';
	};
	$page_footer = function ($page, $total) use ($esc) {
		$f = $page === $total
			? 'Page ' . $page . ' of ' . $total . ' &middot; Shandong SINO FRESH Pet Food Co., Ltd. &middot; zxpet.com'
			: 'Page ' . $page . ' of ' . $total . ' &middot; zxpet.com';
		return '<div class="ft">' . $f . '</div>';
	};

	/* Page 1: summary table across the whole basket. */
	$sum_rows = '';
	foreach ($items as $i => $item) {
		$func = '';
		foreach ($item['pairs'] as $p) {
			if (strcasecmp($p['label'], 'Function') === 0) {
				$func = $p['value'];
				break;
			}
		}
		$sum_rows .= '<tr>'
			. '<td class="sum-n">' . ($i + 1) . '</td>'
			. '<td class="sum-f">' . call_user_func($esc, $item['label']) . '</td>'
			. '<td class="sum-v">' . call_user_func($esc, $func !== '' ? $func : 'Custom') . '</td>'
			. '<td class="sum-o">' . call_user_func($esc, $item['formula'] !== '' ? $item['formula'] . ' (Standard)' : 'Custom') . '</td>'
			. '</tr>';
	}
	$pages = $page_header(1)
		. '<div class="accent-rule"></div>'
		. '<h1>Inquiry Basket Summary</h1>'
		. '<p class="sec-p">' . count($items) . ' dosage forms &middot; configured ' . $date . '</p>'
		. '<table class="sum">'
		. '<tr class="sum-head"><td>#</td><td>Dosage Form</td><td>Function</td><td>Formula Base</td></tr>'
		. $sum_rows
		. '</table>'
		. '<p class="ref-note">Detailed configuration per dosage form on the following pages.</p>'
		. $page_footer(1, $total);

	/* Pages 2..N+1: one configuration page per basket item. */
	$pn = 2;
	foreach ($items as $item) {
		$tr = '';
		foreach ($item['pairs'] as $p) {
			$tr .= '<tr><td class="cfg-k">' . call_user_func($esc, $p['label']) . '</td><td class="cfg-v">' . call_user_func($esc, $p['value']) . '</td></tr>';
		}
		if ($item['formula'] !== '') {
			$fb = '<p class="formula-tag">FORMULA (Standard)</p>'
				. '<p class="formula-name">' . call_user_func($esc, $item['formula']) . '</p>';
		} else {
			$fb = '<p class="formula-tag">FORMULA</p>'
				. '<p class="formula-name">Custom Formula — to be developed</p>'
				. '<p class="sec-p">Our R&amp;D team will develop a custom formula based on your requirements. Submit an inquiry to proceed.</p>';
		}
		$pages .= '<div class="page-break"></div>'
			. $page_header($pn)
			. '<div class="accent-rule"></div>'
			. '<h1>' . call_user_func($esc, $item['label']) . ' — Configuration</h1>'
			. '<table class="cfg">' . $tr . '</table>'
			. '<div class="formula-box">' . $fb . '</div>'
			. $page_footer($pn, $total);
		$pn++;
	}

	/* Final page: company info + next steps (same content as the single summary). */
	$badge_html = '';
	foreach (array('FDA', 'cGMP', 'ISO 9001', 'FSSC 22000', 'HACCP', 'BRC') as $c) {
		$badge_html .= '<span class="badge">' . call_user_func($esc, $c) . '</span>';
	}
	$pages .= '<div class="page-break"></div>'
		. $page_header($pn)
		. '<div class="accent-rule"></div>'
		. '<h2>MANUFACTURING</h2>'
		. '<p class="sec-p">15,000 m&sup2; production facility &middot; ISO 8 cleanroom &middot; 1,000 m&sup2; R&amp;D laboratory &middot; 100+ production &amp; testing equipment</p>'
		. '<h2>CERTIFICATIONS</h2>'
		. '<div class="badges">' . $badge_html . '</div>'
		. '<h2>QUALITY ASSURANCE</h2>'
		. '<ul class="qa"><li>Every batch tested with COA</li><li>Full traceability from raw material</li><li>Retention samples kept per batch</li></ul>'
		. '<h2>NEXT STEPS</h2>'
		. '<p class="sec-p">To proceed with these configurations:</p>'
		. '<ul class="steps">'
		. '<li><strong>Request samples</strong><br>info@zxpet.com &middot; +86 539 866 9539</li>'
		. '<li><strong>Book a factory tour</strong><br>zxpet.com/factory-tour</li>'
		. '<li><strong>Submit an inquiry</strong><br>zxpet.com/contact</li>'
		. '</ul>'
		. '<p class="ref-note">Quote reference <strong>' . call_user_func($esc, $ref) . '</strong> for faster response.</p>'
		. $page_footer($pn, $total);

	$html = '<html><head><meta charset="utf-8"><style>' . sinofresh_config_pdf_css() . '</style></head><body>'
		. $pages
		. '</body></html>';
	return sinofresh_config_pdf_dompdf($html);
}

/**
 * Render the two-page A4 summary. Returns raw PDF bytes or WP_Error.
 */
function sinofresh_config_pdf_render($label, $config, $formula, $ref) {
	$esc = 'esc_html';
	$date = gmdate('F j, Y');
	$formula_base = !empty($formula['name']) ? $formula['name'] . ' (Standard)' : 'Custom';
	$func = sinofresh_config_pdf_function_value($config);
	$product_title = $label . ' — ' . ($func !== '' ? $func : 'Custom') . ' Formula';

	/* Config table rows: fixed identity rows + the label/value pairs sent
	   by the frontend (works for every dosage form). */
	$rows = array(
		array('Dosage Form', $label),
		array('Formula Base', $formula_base),
	);
	foreach ($config as $pair) {
		$rows[] = array($pair['label'], $pair['value']);
	}
	$tr = '';
	foreach ($rows as $row) {
		$tr .= '<tr><td class="cfg-k">' . call_user_func($esc, $row[0]) . '</td><td class="cfg-v">' . call_user_func($esc, $row[1]) . '</td></tr>';
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

	$css = sinofresh_config_pdf_css();

	$html = '<html><head><meta charset="utf-8"><style>' . $css . '</style></head><body>'
		. $page1
		. '<div class="page-break"></div>'
		. $page2
		. '</body></html>';

	return sinofresh_config_pdf_dompdf($html);
}

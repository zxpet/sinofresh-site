<?php
/**
 * SINO FRESH — formula field option pools (batch H1).
 *
 * The publishing form's select pools, transcribed verbatim from the eight
 * dosage pages' configurator groups (page-*.html, data-group/data-value).
 * Batch H1 keeps the configurator alive, so for a while the same option set
 * lives in two shapes: interactive buttons here, HTML buttons in the dosage
 * templates. When batch H2 removes the configurator this file becomes the
 * only copy — which is the point: the pools move from page markup to a
 * single data source.
 *
 * Dimension keys are normalised across dosage forms, because the configurator
 * uses per-form group names for the same underlying question:
 *
 *   shape    shape | texture (pastes) | appearance (powders/drops/liquids)
 *            | product form (fish-oil)
 *   weights  weight | weight_per_piece (dental) | tube_weight (pastes)
 *            | serving_size (powders/liquids) | bottle_size (drops)
 *            | omega3_per_unit (fish-oil)
 *   counts   count | net_weight (powders) | tube_weight (pastes)
 *            | bottle_size (drops/liquids)
 *   flavors  flavor | source (fish-oil — user-approved label swap)
 *   colors   color | none on drops/liquids/fish-oil
 *   packaging packaging
 *
 * Values are verbatim, including the trailing "Custom" every group carries.
 * Frozen per the user's decision on 2026-09-21; a change here is a data
 * decision, not a refactor.
 */

function sf_formula_pools() {
	static $pools = null;
	if (null !== $pools) {
		return $pools;
	}
	$pools = array(
		'soft-chews' => array(
			'shape'     => array('Bone', 'Round', 'Square', 'Heart', 'Star', 'Paw', 'Cylinder', 'Custom'),
			'weights'   => array('0.5g', '1g', '1.5g', '2g', '2.5g', '3g', '4g', '5g', 'Custom'),
			'counts'    => array('30', '60', '90', '120', '150', '180', '250', '500', 'Custom'),
			'flavors'   => array('Chicken', 'Beef', 'Lamb', 'Salmon', 'Peanut Butter', 'Cheese', 'Mint', 'Sweet Potato', 'Pumpkin', 'Blueberry', 'Mixed', 'Unflavored', 'Custom'),
			'colors'    => array('Brown', 'Beige', 'Red', 'Green', 'Yellow', 'Orange', 'Purple', 'Multi-color', 'Custom'),
			'packaging' => array('Aluminum Stand-up Pouch', 'Aluminum Foil Pouch with Zipper', 'Plastic Bottle', 'Jar', 'Blister Pack', 'Box + Foil', 'Custom'),
			'label'     => array('shape' => 'Shape', 'weights' => 'Weight per Piece', 'counts' => 'Count per Bottle', 'flavors' => 'Flavor', 'colors' => 'Color'),
		),
		'tablets' => array(
			'shape'     => array('Round', 'Oval', 'Square', 'Bone', 'Custom'),
			'weights'   => array('250mg', '300mg', '500mg', '750mg', '1000mg', 'Custom'),
			'counts'    => array('60', '90', '120', '180', 'Custom'),
			'flavors'   => array('Chicken', 'Beef', 'Cheese', 'Liver', 'Unflavored', 'Custom'),
			'colors'    => array('White', 'Beige', 'Brown', 'Green', 'Custom'),
			'packaging' => array('Plastic Bottle', 'Jar', 'Blister Pack', 'Foil Pouch', 'Custom'),
			'label'     => array('shape' => 'Shape', 'weights' => 'Weight per Tablet', 'counts' => 'Count per Bottle', 'flavors' => 'Flavor', 'colors' => 'Color'),
		),
		'dental-chews' => array(
			'shape'     => array('Bone', 'Stick', 'Round', 'Spiral', 'Toothbrush', 'Custom'),
			'weights'   => array('10g', '15g', '20g', '25g', '30g', 'Custom'),
			'counts'    => array('14', '24', '28', '30', 'Custom'),
			'flavors'   => array('Mint', 'Chicken', 'Beef', 'Cheese', 'Seaweed', 'Unflavored', 'Custom'),
			'colors'    => array('Green', 'Brown', 'Beige', 'Multi-color', 'Custom'),
			'packaging' => array('Foil Pouch', 'Stand-up Pouch', 'Box', 'Custom'),
			'label'     => array('shape' => 'Shape', 'weights' => 'Weight per Piece', 'counts' => 'Count per Pack', 'flavors' => 'Flavor', 'colors' => 'Color'),
		),
		'pastes' => array(
			'shape'     => array('Smooth Paste', 'Thick Paste', 'Squeezable Gel', 'Custom'),
			'weights'   => array('30g', '35g', '50g', '75g', '100g', 'Custom'),
			'counts'    => array('30g', '35g', '50g', '75g', '100g', 'Custom'),
			'flavors'   => array('Liver', 'Chicken', 'Salmon', 'Unflavored', 'Cheese', 'Custom'),
			'colors'    => array('Brown', 'Beige', 'Green', 'Clear', 'Custom'),
			'packaging' => array('Plastic Tube', 'Metal Tube', 'Aluminum Tube', 'Custom'),
			'label'     => array('shape' => 'Texture', 'weights' => 'Tube Weight', 'counts' => 'Tube Weight', 'flavors' => 'Flavor', 'colors' => 'Color'),
		),
		'powders' => array(
			'shape'     => array('Fine Powder', 'Granules', 'Microencapsulated', 'Custom'),
			'weights'   => array('1g', '2g', '3g', '5g', 'Custom'),
			'counts'    => array('2oz', '4oz', '8oz', '16oz', 'Custom'),
			'flavors'   => array('Unflavored', 'Chicken', 'Beef', 'Cheese', 'Fish', 'Custom'),
			'colors'    => array('White', 'Beige', 'Light Yellow', 'Brown', 'Custom'),
			'packaging' => array('Jar', 'Foil Pouch', 'Stand-up Pouch', 'Custom'),
			'label'     => array('shape' => 'Appearance', 'weights' => 'Serving Size', 'counts' => 'Net Weight', 'flavors' => 'Flavor', 'colors' => 'Color'),
		),
		'drops' => array(
			'shape'     => array('Clear', 'Light Yellow', 'Amber', 'Custom'),
			'weights'   => array('10ml', '20ml', '30ml', '60ml', 'Custom'),
			'counts'    => array('10ml', '20ml', '30ml', '60ml', 'Custom'),
			'flavors'   => array('Unflavored', 'Chicken', 'Beef', 'Fish', 'Mint', 'Custom'),
			'colors'    => array(),
			'packaging' => array('Dropper Bottle', 'Glass Bottle', 'Plastic Bottle', 'Custom'),
			'label'     => array('shape' => 'Appearance', 'weights' => 'Bottle Size', 'counts' => 'Bottle Size', 'flavors' => 'Flavor'),
		),
		'liquids' => array(
			'shape'     => array('Clear', 'Light Color', 'Suspension', 'Custom'),
			'weights'   => array('2.5ml', '5ml', 'By body weight', 'Custom'),
			'counts'    => array('60ml', '100ml', '120ml', '250ml', '500ml', 'Custom'),
			'flavors'   => array('Unflavored', 'Chicken', 'Beef', 'Fish', 'Liver', 'Custom'),
			'colors'    => array(),
			'packaging' => array('Plastic Bottle', 'Glass Bottle', 'Bottle with Cup', 'Custom'),
			'label'     => array('shape' => 'Appearance', 'weights' => 'Serving Size', 'counts' => 'Bottle Size', 'flavors' => 'Flavor'),
		),
		'fish-oil' => array(
			'shape'     => array('Softgel', 'Liquid Oil', 'Pump Bottle', 'Custom'),
			'weights'   => array('200mg', '320mg', '500mg', '1000mg', 'Custom'),
			'counts'    => array('60', '90', '120', '180', 'Custom'),
			'flavors'   => array('Salmon', 'Sardine', 'Anchovy', 'Cod', 'Fish Blend', 'Custom'),
			'colors'    => array(),
			'packaging' => array('Plastic Bottle', 'Glass Bottle', 'Pump Bottle', 'Custom'),
			'label'     => array('shape' => 'Form', 'weights' => 'Omega-3 per Unit', 'counts' => 'Count per Bottle', 'flavors' => 'Source'),
		),
	);
	return $pools;
}

/* --------------------------------------------------------------------------
 * Batch H8a — shelf life becomes a fixed pool.
 *
 * It was a free-text field ("e.g. 18 months") whose value the front end never
 * read: the two rows that print a shelf life parsed it out of sf_formula_specs
 * instead. The batch closes that gap from the field's side — the record now
 * declares one of four answers and the page prints THAT — which is why the
 * pool lives here rather than as a list literal in the admin file: the admin
 * form and the front end have to agree on it, and two literals drift.
 *
 * The strings stored are the strings printed ("18 months"), so the renderer
 * has nothing to compose and the value in the database is the value on the
 * page. Nothing else is accepted: the select cannot produce a fifth answer,
 * and the sanitiser keeps a stale one out.
 * ------------------------------------------------------------------------ */
function sf_formula_shelf_life_pool() {
	return array('12 months', '18 months', '24 months', '36 months');
}

/**
 * A stored shelf-life value as the page prints it. '' when there is none.
 *
 * One repair and no invention: post 158 was saved as "24months" (batch H8a's
 * own survey found 18 records at "24 months", 2 at "18 months" and this one
 * without the space). The missing space is a typo in a free-text field that
 * the pool retires, so the reader normalises it rather than leaving one page
 * in 21 printing a value the admin screen cannot produce. Anything that is
 * not a month count is returned as stored — a reader that rewrote arbitrary
 * text would be a second place that decides what the field means.
 */
function sf_formula_shelf_life_label($raw) {
	$raw = trim(preg_replace('/\s+/', ' ', (string) $raw));
	if ($raw === '') {
		return '';
	}
	if (preg_match('/^(\d+)\s*months?$/i', $raw, $m)) {
		return $m[1] . ' months';
	}
	return $raw;
}

/**
 * The shelf-life line the two front-end rows print, from the record's own
 * fixed pool, falling back to the specs segment while a record has not been
 * re-saved since the pool shipped.
 *
 * The fallback is where batch H8a's "value de-duplication" lives: the segment
 * the specs parser returns is the whole clause ("18 months shelf life"), and
 * both rows already carry the label, so the trailing words are dropped rather
 * than printed twice. It runs only on the fallback because the pool's own
 * strings never contained them.
 */
function sf_formula_shelf_life_line($post_id, $parts = array()) {
	$pool = sf_formula_shelf_life_label(get_post_meta((int) $post_id, 'sf_formula_shelf_life', true));
	if ($pool !== '') {
		return $pool;
	}
	$raw = isset($parts['shelf']) ? trim((string) $parts['shelf']) : '';
	return trim((string) preg_replace('/[\s,–-]*shelf\s*life\.?$/i', '', $raw));
}

/**
 * One dimension's options for one dosage form. Empty array = the form has no
 * such dimension (the field is skipped rather than rendered empty).
 */
function sf_formula_field_pool($form, $dim) {
	$pools = sf_formula_pools();
	$form  = sanitize_title($form);
	return (isset($pools[$form][$dim]) && is_array($pools[$form][$dim])) ? $pools[$form][$dim] : array();
}

/** The per-form display label for a dimension, e.g. "Texture" on pastes. */
function sf_formula_field_pool_label($form, $dim) {
	$pools = sf_formula_pools();
	$form  = sanitize_title($form);
	return (isset($pools[$form]['label'][$dim])) ? $pools[$form]['label'][$dim] : '';
}

/* --------------------------------------------------------------------------
 * Batch H8b — the per-dosage pool, with the Site Settings library serving as
 * the picture.
 *
 * Until this batch the detail page's Shape and Container Type groups took
 * their OPTIONS from the global sf_shapes / sf_containers libraries, while the
 * publishing form's Shape field already asked sf_formula_field_pool() for the
 * dosage form's own list. The two ends therefore disagreed in both
 * directions: a powder page offered "Bone" and "Paw", and the answer the
 * editor had picked there ("Microencapsulated") was not on the page at all.
 *
 * The libraries are not retired — they stay the IMAGE carrier, matched by the
 * label both sides spell. A label the library also carries (Bone, Round,
 * Square … on soft chews; Jar on every form that ships in one) picks up that
 * row's picture; a label only the pool carries (Fine Powder, Thick Paste,
 * Softgel …) returns '' and the picker draws the dashed empty slot it already
 * draws for a slot with no attachment. Matching on the label rather than on a
 * slug is what lets one library serve eight option lists without a second
 * mapping table — and it keeps the "upload the shape images later" path the
 * Site Settings pages promise.
 * ------------------------------------------------------------------------ */

/**
 * The image URL a library row carries for a pool label, or '' when no row
 * spells it (case-insensitively, because the pool and the library are two
 * hand-maintained lists and "Round" vs "round" is not a difference a visitor
 * should ever be able to see).
 *
 * Every attachment_id in both libraries is 0 today, so on the current data
 * this returns '' for every option — the path is here for the pictures the
 * Site Settings pages are still waiting for, not for one the site already has.
 */
function sf_formula_pool_option_image($library, $label) {
	$label = strtolower(trim((string) $label));
	if ($label === '' || !is_array($library)) {
		return '';
	}
	foreach ($library as $row) {
		$row   = (array) $row;
		$spelt = isset($row['label']) ? strtolower(trim((string) $row['label'])) : '';
		if ($spelt !== $label) {
			continue;
		}
		$id = !empty($row['attachment_id']) ? (int) $row['attachment_id'] : 0;
		if ($id <= 0) {
			return '';
		}
		$url = wp_get_attachment_image_url($id, 'medium');
		return $url ? (string) $url : '';
	}
	return '';
}

/**
 * One dosage pool rendered as configurator options.
 *
 * The option's VALUE is the LABEL, and that is the point of the batch: the
 * label is what the publishing form's radio posts (sf_formula_mb_options
 * returns the pool verbatim), what sf_formula_shape stores, and what
 * sinofresh_formula_config_rows() whitelists against. One vocabulary, three
 * readers — so the page cannot offer an answer the editor could not have
 * chosen, or refuse one it could.
 *
 * "Custom" is MARKED rather than appended: every pool already ends in it
 * (batch H1 froze them that way, and the H1 note says a change there is a data
 * decision), and the marker is what turns the entry into the pick that opens
 * batch H8a's text box. Appending a second one would print the word twice.
 */
function sf_formula_library_options($pool, $library) {
	$out = array();
	foreach ((array) $pool as $label) {
		$label = trim((string) $label);
		if ($label === '') {
			continue;
		}
		$option = array(
			'value' => $label,
			'label' => $label,
			'image' => sf_formula_pool_option_image($library, $label),
			'note'  => '',
		);
		if (0 === strcasecmp($label, 'Custom')) {
			$option['custom'] = true;
		}
		$out[] = $option;
	}
	return $out;
}

/**
 * The certification names behind batch H1b's four touch points — one source,
 * three renderers.
 *
 * sf_active_cert_names()        the plain names ("FDA, cGMP, …" line, the
 *                               detail page's certifications row, the batch C
 *                               FAQ answer)
 * sf_render_cert_badges()       the top-bar pill badges (pre-existing,
 *                               functions.php — now fed by the same option)
 * sf_cert_schema_credentials()  the Organization JSON-LD hasCredential array.
 *                               The schema names carry a credential-specific
 *                               suffix ("FDA Registered"), so the map below
 *                               preserves the exact bytes the schema shipped
 *                               with on 2026-09-17. A certification that is
 *                               not in the map renders with its plain name
 *                               and no credentialCategory, so operations can
 *                               add a row without touching this file.
 */
function sf_active_cert_names() {
	$certs  = get_option('sf_certifications', sf_default_certifications());
	$names  = array();
	foreach ($certs as $c) {
		if (!empty($c['active']) && isset($c['name']) && trim((string) $c['name']) !== '') {
			$names[] = trim((string) $c['name']);
		}
	}
	return $names;
}

function sf_cert_schema_credentials() {
	$suffixes = array(
		'FDA'         => array('FDA Registered',       'U.S. Food and Drug Administration'),
		'cGMP'        => array('cGMP Compliant',       'Current Good Manufacturing Practice'),
		'ISO 9001'    => array('ISO 9001 Certified',   'Quality Management System'),
		'FSSC 22000'  => array('FSSC 22000 Certified', 'GFSI Recognized Food Safety System'),
		'HACCP'       => array('HACCP Certified',      'Hazard Analysis Critical Control Point'),
		'BRC'         => array('BRC Certified',        'British Retail Consortium'),
	);
	$out = array();
	foreach (sf_active_cert_names() as $name) {
		if (isset($suffixes[$name])) {
			$out[] = array(
				'@type'              => 'EducationalOccupationalCredential',
				'name'               => $suffixes[$name][0],
				'credentialCategory' => $suffixes[$name][1],
			);
		} else {
			$out[] = array('@type' => 'EducationalOccupationalCredential', 'name' => $name);
		}
	}
	return $out;
}

/**
 * The joined line for {{sf-certifications-line}} and the detail page's
 * certifications row: "FDA, cGMP, ISO 9001, FSSC 22000, HACCP, BRC" — the
 * exact string the dosage pages hard-code today, so the default option set
 * renders byte-identically.
 */
function sf_certifications_line() {
	return implode(', ', sf_active_cert_names());
}

/**
 * The certifications value for the detail page (factsheet row and the batch C
 * FAQ answer): the Site Settings line wins; when operations clear every row
 * the dosage page's hard-coded value keeps the page from going blank.
 */
function sf_formula_certifications_value($form_slug) {
	$line = sf_certifications_line();
	if ($line !== '') {
		return $line;
	}
	return ($form_slug !== '') ? sinofresh_formula_spec_cell($form_slug, 'Certifications') : '';
}

/**
 * One factory fact for the specification sheet — 'sf_factory_origin' (Place of
 * Origin) and 'sf_factory_oem' (OEM / ODM). Batch H7e.
 *
 * Until H7e these two were constants inside sinofresh_formula_specs_table().
 * They are now Site Settings fields, and the defaults are those constants
 * unchanged, so the swap moves WHERE the value comes from without moving the
 * value: every one of the 75 captured pages stays byte-identical, which is the
 * only reason the change can be proved rather than merely asserted.
 *
 * The fallback is read from sf_site_settings_defaults() and not repeated here.
 * Two copies of a default are two chances to disagree, and the copy this would
 * duplicate is the one the settings page itself falls back to — so an admin who
 * clears the field and the renderer that prints it would be reading different
 * strings. An empty stored value also falls back, for the same reason the rest
 * of Site Settings does: clearing a field must not blank 42 pages.
 *
 * Returns '' for a key with no default, which the caller treats as "no row".
 * That is how the empty-means-absent contract reaches a field whose source is
 * an option rather than post meta.
 */
function sf_formula_factory_value($key) {
	$d       = sf_site_settings_defaults();
	$default = isset($d[$key]) ? (string) $d[$key] : '';
	$value   = trim((string) get_option($key, $default));
	return ($value !== '') ? $value : $default;
}

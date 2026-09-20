<?php
/**
 * Batch 2C step 1 — ground truth for the formula detail page.
 *
 * Runs inside WP (wp eval-file) on the dev site and dumps one JSON object per
 * published sf_formula: everything the detail page and its Product JSON-LD are
 * supposed to render, taken from the database and from the theme functions
 * themselves (never from the rendered HTML, or the comparison would be
 * circular).
 *
 * Usage: wp eval-file tools/b2c_s1_ground_truth.php
 */
if (!defined('ABSPATH')) {
	exit(1);
}

$ids = get_posts(array(
	'post_type'      => 'sf_formula',
	'post_status'    => 'publish',
	'posts_per_page' => -1,
	'orderby'        => array('menu_order' => 'ASC', 'title' => 'ASC'),
	'fields'         => 'ids',
));

$out = array();
foreach ($ids as $id) {
	$post = get_post($id);
	$row  = array(
		'id'      => (int) $id,
		'slug'    => $post->post_name,
		'title'   => html_entity_decode(get_the_title($post), ENT_QUOTES, 'UTF-8'),
		'url'     => get_permalink($post),
		'content' => (trim((string) $post->post_content) === '') ? '' : 'non-empty',
	);

	$forms = wp_get_post_terms($id, 'sf_formula_form');
	if (!is_wp_error($forms) && $forms) {
		$row['form_slug']  = $forms[0]->slug;
		$row['form_label'] = sinofresh_formula_label($forms[0]->slug, $forms[0]->name);
	} else {
		$row['form_slug']  = '';
		$row['form_label'] = '';
	}

	$uses = wp_get_post_terms($id, 'sf_formula_use');
	$row['use_name'] = (!is_wp_error($uses) && $uses) ? $uses[0]->name : '';

	foreach (array('ingredients', 'analysis', 'specs', 'source') as $k) {
		$row[$k] = (string) get_post_meta($id, 'sf_formula_' . $k, true);
	}

	$row['moq']       = sinofresh_formula_spec_cell($row['form_slug'], 'MOQ');
	$row['lead_time'] = sinofresh_formula_spec_cell($row['form_slug'], 'Lead time');
	$row['image']     = sinofresh_formula_card_image($row['form_slug']);

	// Expected hero meta line, composed exactly the way the placeholder engine
	// composes it (same order, same separator, same drop-empty rule).
	$bits = array();
	if ($row['form_label'] !== '') { $bits[] = $row['form_label']; }
	if ($row['moq'] !== '')       { $bits[] = 'MOQ ' . $row['moq']; }
	if ($row['lead_time'] !== '') { $bits[] = 'Lead time ' . $row['lead_time']; }
	$row['meta_line'] = implode(' · ', $bits);

	// Expected description, same composition as the Product JSON-LD block.
	$name = $row['title'];
	$description = $row['form_label'] !== ''
		? sprintf('%s — a standard %s formula from the SINO FRESH OEM/ODM range for private-label pet supplements.', $name, $row['form_label'])
		: sprintf('%s — a standard formula from the SINO FRESH OEM/ODM range for private-label pet supplements.', $name);
	if ($row['ingredients'] !== '') { $description .= ' Ingredients: ' . $row['ingredients'] . '.'; }
	if ($row['analysis'] !== '')    { $description .= ' Guaranteed analysis: ' . $row['analysis'] . '.'; }
	if ($row['specs'] !== '')       { $description .= ' Specifications: ' . $row['specs'] . '.'; }
	$row['description'] = $description;

	$out[] = $row;
}

echo wp_json_encode($out, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT), "\n";

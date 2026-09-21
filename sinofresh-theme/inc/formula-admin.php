<?php
/**
 * SINO FRESH — the formula publishing form (batch H1).
 *
 * Phase 1 of the detail-page rebuild: every product carries its own data
 * instead of borrowing the dosage page's. This file is the admin half —
 * meta boxes, sanitising, the phase-1 warning banner, and the two Site
 * Settings subpages (Container Library, Global FAQ). Front-end readers of
 * the new keys land in batch H2; nothing here changes a rendered byte, so
 * style.css and the front-end enqueue versions stay untouched.
 *
 * Native WordPress only: add_meta_box + the Settings API. No ACF, no JS or
 * CSS frameworks — the admin assets under assets/admin/ are vanilla and
 * loaded on this post type's screens and the settings pages only.
 *
 * Required-vs-warning follows the user's frozen list: 18 blocking fields
 * (enforced in phase 2; phase 1 shows the banner), 7 warning fields.
 */

/* --------------------------------------------------------------------------
 * Meta registration. sf_formula_intro was deliberately unregistered before
 * this batch (custom-fields panel was the editing route); it joins the
 * registered set now that the form is the primary editor.
 * ------------------------------------------------------------------------ */
add_action('init', function () {
	$keys = array(
		'sf_formula_intro'            => 'Short introduction shown under the title.',
		'sf_formula_gallery_ids'      => 'JSON array of attachment IDs for the gallery.',
		'sf_formula_video_url'        => 'YouTube URL for the product video.',
		'sf_formula_flavors'          => 'JSON array of flavour options.',
		'sf_formula_weight'           => 'Weight per piece (single choice).',
		'sf_formula_counts'           => 'JSON array of pack counts.',
		'sf_formula_shape'            => 'Shape / texture / appearance (single choice).',
		'sf_formula_species'          => 'JSON array: dog / cat.',
		'sf_formula_lifestage'        => 'Life stage (single choice).',
		'sf_formula_price_tiers'      => 'JSON array of {qty, price} tiers.',
		'sf_formula_recommended_for'  => 'Recommended For copy.',
		'sf_formula_use_cases'        => 'Use Cases copy.',
		'sf_formula_who_for'          => "Who It's For copy.",
		'sf_formula_packaging_extra'  => 'JSON array of extra packaging options.',
		'sf_formula_colors'           => 'JSON array of colour options.',
		'sf_formula_shelf_life'       => 'Shelf life text.',
		'sf_formula_cartons'          => 'JSON array of {count, boxes, size} carton rows.',
		'sf_formula_lead_time'        => 'Lead time text.',
		'sf_formula_container'        => 'Container slug from the global container library.',
		'sf_formula_faq_data'         => 'JSON array of {q, a} product FAQ rows.',
	);
	foreach ($keys as $key => $desc) {
		register_post_meta('sf_formula', $key, array(
			'type'          => 'string',
			'single'        => true,
			'show_in_rest'  => true,
			'description'   => $desc,
			'auth_callback' => function () {
				return current_user_can('edit_posts');
			},
		));
	}
}, 11); // the CPT registers on init 9; meta must come after it

/* --------------------------------------------------------------------------
 * The field specification — one table drives the boxes, the sanitiser, the
 * banner and the phase-2 check. req: 2 = blocking (phase 2), 1 = warning.
 * ------------------------------------------------------------------------ */
function sf_formula_mb_groups() {
	return array(
		'basics'    => array('title' => 'Basics', 'context' => 'normal'),
		'media'     => array('title' => 'Media', 'context' => 'normal'),
		'params'    => array('title' => 'Right-column Parameters', 'context' => 'normal'),
		'detail'    => array('title' => 'Detailed Content', 'context' => 'normal'),
		'packaging' => array('title' => 'Packaging', 'context' => 'normal'),
		'faq'       => array('title' => 'FAQ & Delivery', 'context' => 'normal'),
	);
}

function sf_formula_mb_fields() {
	return array(
		// basics
		array('key' => 'sf_formula_intro', 'label' => 'Introduction', 'group' => 'basics', 'type' => 'textarea', 'req' => 2, 'rows' => 4,
			'hint' => 'One short paragraph under the title. Shown verbatim on the page.'),
		// media
		array('key' => 'sf_formula_gallery_ids', 'label' => 'Gallery images', 'group' => 'media', 'type' => 'gallery', 'req' => 1,
			'hint' => 'Optional. The main photo is the Featured Image panel in the editor.'),
		array('key' => 'sf_formula_video_url', 'label' => 'YouTube URL', 'group' => 'media', 'type' => 'url', 'req' => 1),
		// params — pools resolve per dosage form at render time
		array('key' => 'sf_formula_flavors', 'label' => 'Flavors', 'group' => 'params', 'type' => 'multi', 'req' => 2, 'pool' => 'flavors'),
		array('key' => 'sf_formula_weight', 'label' => 'Weight per piece', 'group' => 'params', 'type' => 'radio', 'req' => 2, 'pool' => 'weights'),
		array('key' => 'sf_formula_counts', 'label' => 'Pack counts', 'group' => 'params', 'type' => 'multi', 'req' => 2, 'pool' => 'counts'),
		array('key' => 'sf_formula_shape', 'label' => 'Shape', 'group' => 'params', 'type' => 'radio', 'req' => 2, 'pool' => 'shape'),
		array('key' => 'sf_formula_species', 'label' => 'Suitable for', 'group' => 'params', 'type' => 'multi', 'req' => 2, 'pool' => array('Dog', 'Cat')),
		array('key' => 'sf_formula_lifestage', 'label' => 'Life stage', 'group' => 'params', 'type' => 'radio', 'req' => 2,
			'pool' => array('Puppy', 'Kitten', 'Adult', 'Senior', 'All Life Stages')),
		array('key' => 'sf_formula_price_tiers', 'label' => 'Tier pricing', 'group' => 'params', 'type' => 'table', 'req' => 2,
			'cols' => array('qty' => 'Min quantity', 'price' => 'Unit price (USD)')),
		// detail
		array('key' => 'sf_formula_ingredients', 'label' => 'Ingredients', 'group' => 'detail', 'type' => 'textarea', 'req' => 2, 'rows' => 3),
		array('key' => 'sf_formula_analysis', 'label' => 'Guaranteed Analysis', 'group' => 'detail', 'type' => 'textarea', 'req' => 2, 'rows' => 3),
		array('key' => 'sf_formula_specs', 'label' => 'Standard Specs', 'group' => 'detail', 'type' => 'textarea', 'req' => 2, 'rows' => 2),
		array('key' => 'sf_formula_recommended_for', 'label' => 'Recommended For', 'group' => 'detail', 'type' => 'textarea', 'req' => 2, 'rows' => 3),
		array('key' => 'sf_formula_use_cases', 'label' => 'Use Cases', 'group' => 'detail', 'type' => 'textarea', 'req' => 2, 'rows' => 3),
		array('key' => 'sf_formula_who_for', 'label' => "Who It's For", 'group' => 'detail', 'type' => 'textarea', 'req' => 2, 'rows' => 3),
		// packaging
		array('key' => 'sf_formula_packaging_extra', 'label' => 'Extra packaging', 'group' => 'packaging', 'type' => 'multi', 'req' => 1, 'pool' => 'packaging'),
		array('key' => 'sf_formula_colors', 'label' => 'Colors', 'group' => 'packaging', 'type' => 'multi', 'req' => 1, 'pool' => 'colors',
			'hint' => 'Not available for this dosage form when no options appear.'),
		array('key' => 'sf_formula_shelf_life', 'label' => 'Shelf life', 'group' => 'packaging', 'type' => 'text', 'req' => 2,
			'hint' => 'e.g. 18 months'),
		array('key' => 'sf_formula_cartons', 'label' => 'Carton dimensions', 'group' => 'packaging', 'type' => 'table', 'req' => 1,
			'cols' => array('count' => 'Pack count', 'boxes' => 'Units per carton', 'size' => 'Carton size (cm)')),
		// faq
		array('key' => 'sf_formula_lead_time', 'label' => 'Lead time', 'group' => 'faq', 'type' => 'text', 'req' => 1),
		array('key' => 'sf_formula_container', 'label' => 'Container Type', 'group' => 'faq', 'type' => 'radio', 'req' => 2, 'pool' => '_containers'),
		array('key' => 'sf_formula_faq_data', 'label' => 'Product FAQ', 'group' => 'faq', 'type' => 'faqtable', 'req' => 1,
			'hint' => 'Questions ship prefilled; fill the answers. Site-wide questions are appended from the Global FAQ.'),
	);
}

/** The dosage form slug of the record being edited ('' before a term is set). */
function sf_formula_record_form($post_id) {
	$terms = wp_get_post_terms($post_id, 'sf_formula_form', array('fields' => 'slugs'));
	return (!is_wp_error($terms) && $terms) ? (string) $terms[0] : '';
}

/** Container options come from the global library, not a dosage pool. */
function sf_formula_container_options() {
	$out  = array();
	foreach (sf_container_library() as $c) {
		if (trim((string) $c['label']) !== '') {
			$out[$c['slug']] = $c['label'];
		}
	}
	return $out;
}

/** Resolve a spec's option list: fixed array, dosage pool, or the library. */
function sf_formula_mb_options($spec, $post_id) {
	if (!isset($spec['pool'])) {
		return array();
	}
	if (is_array($spec['pool'])) {
		return $spec['pool'];
	}
	if ($spec['pool'] === '_containers') {
		return sf_formula_container_options();
	}
	return sf_formula_field_pool(sf_formula_record_form($post_id), $spec['pool']);
}

/* --------------------------------------------------------------------------
 * Meta boxes — six groups, one shared renderer.
 * ------------------------------------------------------------------------ */
add_action('add_meta_boxes', function () {
	foreach (sf_formula_mb_groups() as $slug => $g) {
		add_meta_box('sf-mb-' . $slug, $g['title'], 'sf_formula_render_mb_box', 'sf_formula', $g['context'], 'high',
			array('group' => $slug));
	}
});

function sf_formula_render_mb_box($post, $metabox) {
	$group = $metabox['args']['group'];
	wp_nonce_field('sf_mb_save', 'sf_mb_nonce_' . $group);
	echo '<div class="sf-mb" data-sf-group="' . esc_attr($group) . '">';
	foreach (sf_formula_mb_fields() as $spec) {
		if ($spec['group'] !== $group) {
			continue;
		}
		sf_formula_render_field($spec, $post->ID);
	}
	echo '</div>';
}

function sf_formula_render_field($spec, $post_id) {
	$raw    = get_post_meta($post_id, $spec['key'], true);
	$opts   = sf_formula_mb_options($spec, $post_id);
	$req    = (2 === (int) $spec['req']) ? ' <span class="sf-mb__req" title="Required before publish">*</span>' : '';
	$hid    = ('multi' === $spec['type'] || 'radio' === $spec['type']) && empty($opts);
	echo '<div class="sf-mb__field sf-mb__field--' . esc_attr($spec['type']) . '" data-sf-key="' . esc_attr($spec['key']) . '"' . ($hid ? ' hidden' : '') . '>';
	echo '<span class="sf-mb__label">' . esc_html($spec['label']) . $req . '</span>';
	if (!empty($spec['hint'])) {
		echo '<p class="sf-mb__hint">' . esc_html($spec['hint']) . '</p>';
	}
	switch ($spec['type']) {
		case 'text':
		case 'url':
			printf('<input type="text" class="widefat" name="%s" value="%s" %s/>',
				esc_attr($spec['key']), esc_attr($raw), 'url' === $spec['type'] ? 'placeholder="https://www.youtube.com/watch?v=…"' : '');
			break;
		case 'textarea':
			printf('<textarea class="widefat" rows="%d" name="%s">%s</textarea>',
				(int) $spec['rows'], esc_attr($spec['key']), esc_textarea($raw));
			break;
		case 'multi':
			$sel = sf_json_array($raw);
			foreach ($opts as $o) {
				printf('<label class="sf-mb__opt"><input type="checkbox" name="%s[]" value="%s" %s/> %s</label>',
					esc_attr($spec['key']), esc_attr($o), checked(in_array($o, $sel, true), true, false), esc_html($o));
			}
			break;
		case 'radio':
			foreach ($opts as $o) {
				printf('<label class="sf-mb__opt"><input type="radio" name="%s" value="%s" %s/> %s</label>',
					esc_attr($spec['key']), esc_attr($o), checked($raw, $o, false), esc_html($o));
			}
			break;
		case 'gallery':
			$ids = array_filter(array_map('absint', explode(',', (string) $raw)));
			echo '<input type="hidden" class="sf-mb__gallery-ids" name="' . esc_attr($spec['key']) . '" value="' . esc_attr(implode(',', $ids)) . '"/>';
			echo '<div class="sf-mb__gallery-preview">';
			foreach ($ids as $id) {
				echo wp_get_attachment_image($id, 'thumbnail');
			}
			echo '</div>';
			echo '<button type="button" class="button sf-mb__gallery-add">Choose / update images</button> ';
			echo '<button type="button" class="button-link sf-mb__gallery-clear"' . ($ids ? '' : ' hidden') . '>Remove all</button>';
			break;
		case 'table':
			$rows  = sf_json_rows($raw);
			$cols  = array_keys($spec['cols']);
			echo '<table class="sf-reptable widefat" data-sf-name="' . esc_attr($spec['key']) . '"><thead><tr>';
			foreach ($spec['cols'] as $c) {
				echo '<th>' . esc_html($c) . '</th>';
			}
			echo '<th></th></tr></thead><tbody>';
			foreach ($rows as $r) {
				sf_formula_table_row($spec['key'], $cols, $r);
			}
			echo '</tbody></table>';
			echo '<p><button type="button" class="button sf-reptable__add" data-sf-name="' . esc_attr($spec['key']) . '">+ Add row</button></p>';
			break;
		case 'faqtable':
			$rows = sf_json_rows($raw);
			if (!$rows) {
				$rows = sf_formula_faq_preset();
			}
			echo '<table class="sf-reptable sf-reptable--faq widefat" data-sf-name="' . esc_attr($spec['key']) . '"><thead><tr><th>Question</th><th>Answer</th><th></th></tr></thead><tbody>';
			foreach ($rows as $r) {
				$r = array_merge(array('q' => '', 'a' => ''), (array) $r);
				echo '<tr><td><input type="text" class="widefat" name="' . esc_attr($spec['key']) . '[q][]" value="' . esc_attr($r['q']) . '"/></td>';
				echo '<td><textarea class="widefat" rows="3" name="' . esc_attr($spec['key']) . '[a][]">' . esc_textarea($r['a']) . '</textarea>';
				echo '<p class="sf-mb__hint">Plain text; a &lt;a href="…"&gt; link is allowed.</p></td>';
				echo '<td><button type="button" class="button-link sf-reptable__del">Remove</button></td></tr>';
			}
			echo '</tbody></table>';
			echo '<p><button type="button" class="button sf-reptable__add sf-reptable__add--empty" data-sf-name="' . esc_attr($spec['key']) . '">+ Add row</button></p>';
			break;
	}
	echo '</div>';
}

/** One <tr> of a generic repeatable table. */
function sf_formula_table_row($key, $cols, $row) {
	$row = (array) $row;
	echo '<tr>';
	foreach ($cols as $c) {
		printf('<td><input type="text" class="widefat" name="%s[%s][]" value="%s"/></td>',
			esc_attr($key), esc_attr($c), esc_attr(isset($row[$c]) ? $row[$c] : ''));
	}
	echo '<td><button type="button" class="button-link sf-reptable__del">Remove</button></td></tr>';
}

/** The nine standard questions (batch C), answers left blank on purpose. */
function sf_formula_faq_preset() {
	$qs = array(
		'Can the active ingredients be changed?',
		'Can the flavour be changed?',
		'Is a gluten-free or grain-free version available?',
		'Is this formula for dogs or for cats?',
		'Can I sample this formula before ordering?',
		'What certifications and documentation do you provide?',
		'Can the packaging and the label be customised?',
		'How should the finished product be stored?',
		'Will you keep my formula and my brand confidential?',
	);
	$out = array();
	foreach ($qs as $q) {
		$out[] = array('q' => $q, 'a' => '');
	}
	return $out;
}

/* --------------------------------------------------------------------------
 * Save — sanitise everything the form posts. Phase 1: no blocking, ever;
 * the missing-field banner (below) is informational.
 * ------------------------------------------------------------------------ */
add_action('save_post_sf_formula', function ($post_id) {
	if (defined('DOING_AUTOSAVE') && DOING_AUTOSAVE) {
		return;
	}
	if (!current_user_can('edit_post', $post_id)) {
		return;
	}
	foreach (sf_formula_mb_groups() as $slug => $g) {
		if (!isset($_POST['sf_mb_nonce_' . $slug]) || !wp_verify_nonce($_POST['sf_mb_nonce_' . $slug], 'sf_mb_save')) {
			return; // one box per submit round-trip in the block editor
		}
	}
	$form = sf_formula_record_form($post_id);

	foreach (sf_formula_mb_fields() as $spec) {
		$key = $spec['key'];
		switch ($spec['type']) {
			case 'text':
				update_post_meta($post_id, $key, sanitize_text_field(wp_unslash($_POST[$key] ?? '')));
				break;
			case 'url':
				update_post_meta($post_id, $key, esc_url_raw(wp_unslash($_POST[$key] ?? '')));
				break;
			case 'textarea':
				update_post_meta($post_id, $key, sanitize_textarea_field(wp_unslash($_POST[$key] ?? '')));
				break;
			case 'multi':
				$in   = array_map('sanitize_text_field', (array) wp_unslash($_POST[$key] ?? array()));
				$opts = sf_formula_mb_options($spec, $post_id);
				update_post_meta($post_id, $key, wp_json_encode(array_values(array_intersect($opts, $in))));
				break;
			case 'radio':
				$in   = sanitize_text_field(wp_unslash($_POST[$key] ?? ''));
				$opts = sf_formula_mb_options($spec, $post_id);
				update_post_meta($post_id, $key, in_array($in, $opts, true) ? $in : '');
				break;
			case 'gallery':
				$ids = array_filter(array_map('absint', explode(',', (string) wp_unslash($_POST[$key] ?? ''))));
				update_post_meta($post_id, $key, implode(',', $ids));
				break;
			case 'table':
				$cols  = array_keys($spec['cols']);
				$posts = array();
				foreach ($cols as $c) {
					$posts[$c] = array_map('sanitize_text_field', (array) wp_unslash($_POST[$key][$c] ?? array()));
				}
				$n    = count($posts[$cols[0]]);
				$rows = array();
				for ($i = 0; $i < $n; $i++) {
					$row = array();
					$any = false;
					foreach ($cols as $c) {
						$v        = isset($posts[$c][$i]) ? $posts[$c][$i] : '';
						$row[$c]  = $v;
						$any      = $any || ($v !== '');
					}
					if ($any) {
						$rows[] = $row; // fully-empty rows are dropped, not stored
					}
				}
				update_post_meta($post_id, $key, wp_json_encode(array_values($rows)));
				break;
			case 'faqtable':
				$qs   = array_map('sanitize_text_field', (array) wp_unslash($_POST[$key]['q'] ?? array()));
				$as   = array_map('sf_mb_kses_answer', (array) wp_unslash($_POST[$key]['a'] ?? array()));
				$rows = array();
				$n    = max(count($qs), count($as));
				for ($i = 0; $i < $n; $i++) {
					$q = isset($qs[$i]) ? $qs[$i] : '';
					$a = isset($as[$i]) ? $as[$i] : '';
					if ($q !== '' || $a !== '') {
						$rows[] = array('q' => $q, 'a' => $a);
					}
				}
				update_post_meta($post_id, $key, wp_json_encode(array_values($rows)));
				break;
		}
	}
}, 10, 1);

/** FAQ answers are plain text plus <a href> — nothing else survives. */
function sf_mb_kses_answer($v) {
	return wp_kses((string) $v, array('a' => array('href' => array(), 'title' => array(), 'target' => array())));
}

/** Decode a stored JSON array; junk in, empty array out. */
function sf_json_array($raw) {
	$v = json_decode((string) $raw, true);
	return is_array($v) ? array_values(array_filter($v, 'is_string')) : array();
}

/** Decode a stored JSON row list; junk in, empty array out. */
function sf_json_rows($raw) {
	$v = json_decode((string) $raw, true);
	return is_array($v) ? array_values($v) : array();
}

/* --------------------------------------------------------------------------
 * Phase-1 warning banner — never blocks. Edit screen: this record's gaps.
 * List screen: backfill progress across all 21.
 * ------------------------------------------------------------------------ */
function sf_formula_required_labels() {
	$out = array();
	foreach (sf_formula_mb_fields() as $spec) {
		if (2 === (int) $spec['req']) {
			$out[$spec['key']] = $spec['label'];
		}
	}
	return $out;
}

function sf_formula_missing_required($post_id) {
	$labels  = sf_formula_required_labels();
	$missing = array();
	if (trim(get_the_title($post_id)) === '') {
		$missing[] = 'Title';
	}
	if ((int) get_post_thumbnail_id($post_id) <= 0) {
		$missing[] = 'Featured image (main photo)';
	}
	foreach ($labels as $key => $label) {
		$raw = trim((string) get_post_meta($post_id, $key, true));
		if ($raw === '') {
			$missing[] = $label;
			continue;
		}
		if ($key === 'sf_formula_price_tiers') {
			$ok = false;
			foreach (sf_json_rows($raw) as $r) {
				if (trim((string) ($r['qty'] ?? '')) !== '' && trim((string) ($r['price'] ?? '')) !== '') {
					$ok = true;
					break;
				}
			}
			if (!$ok) {
				$missing[] = $label . ' (one complete row)';
			}
		}
	}
	return array_values(array_unique($missing));
}

add_action('admin_notices', function () {
	$screen = function_exists('get_current_screen') ? get_current_screen() : null;
	if (!$screen) {
		return;
	}
	if ('post' === $screen->base && 'sf_formula' === $screen->post_type) {
		$post_id = (int) (isset($_GET['post']) ? $_GET['post'] : 0);
		if ($post_id <= 0) {
			return;
		}
		$missing = sf_formula_missing_required($post_id);
		if ($missing) {
			echo '<div class="notice notice-warning"><p><strong>Backfill needed (phase 1 — publishing is not blocked yet).</strong> Missing: '
				. esc_html(implode(', ', $missing)) . '</p></div>';
		}
		return;
	}
	if ('edit' === $screen->base && 'sf_formula' === $screen->post_type) {
		$done = $total = 0;
		foreach (get_posts(array('post_type' => 'sf_formula', 'post_status' => 'publish', 'numberposts' => -1, 'fields' => 'ids')) as $id) {
			$total++;
			if (!sf_formula_missing_required($id)) {
				$done++;
			}
		}
		if ($done < $total) {
			echo '<div class="notice notice-warning"><p><strong>Backfill progress: ' . (int) $done . ' / ' . (int) $total
				. ' formulas complete.</strong> Phase-2 blocking switches on when every record is filled.</p></div>';
		}
	}
});

/* --------------------------------------------------------------------------
 * Admin assets — this post type's edit screens and the settings pages only.
 * ------------------------------------------------------------------------ */
add_action('admin_enqueue_scripts', function ($hook) {
	$is_formula = in_array($hook, array('post.php', 'post-new.php'), true)
		&& function_exists('get_current_screen')
		&& get_current_screen()
		&& 'sf_formula' === get_current_screen()->post_type;
	$is_settings = in_array($hook, array('toplevel_page_sf-site-settings',
		'sino-fresh_page_sf-containers', 'sf-site-settings_page_sf-containers',
		'sino-fresh_page_sf-global-faq', 'sf-site-settings_page_sf-global-faq'), true);
	if (!$is_formula && !$is_settings) {
		return;
	}
	$dir = get_template_directory_uri();
	wp_enqueue_style('sf-mb', $dir . '/assets/admin/sf-mb.css', array(), '1.0.0');
	wp_enqueue_script('sf-mb-tables', $dir . '/assets/admin/sf-mb-tables.js', array(), '1.0.0', true);
	if ($is_formula) {
		wp_enqueue_media();
		wp_enqueue_script('sf-mb-precheck', $dir . '/assets/admin/sf-mb-precheck.js', array(), '1.0.0', true);
	}
	if ($is_settings) {
		wp_enqueue_script('sf-site-settings', $dir . '/assets/admin/sf-site-settings.js', array(), '1.0.0', true);
	}
});

/* --------------------------------------------------------------------------
 * Site Settings subpages — Container Library and Global FAQ.
 * ------------------------------------------------------------------------ */
function sf_default_containers() {
	return array(
		array('slug' => 'round',  'label' => 'Round',  'attachment_id' => 0),
		array('slug' => 'square', 'label' => 'Square', 'attachment_id' => 0),
		array('slug' => 'oval',   'label' => 'Oval',   'attachment_id' => 0),
		array('slug' => 'jar',    'label' => 'Jar',    'attachment_id' => 0),
		array('slug' => 'pouch',  'label' => 'Pouch',  'attachment_id' => 0),
		array('slug' => 'tube',   'label' => 'Tube',   'attachment_id' => 0),
		array('slug' => 'custom', 'label' => 'Custom', 'attachment_id' => 0),
	);
}

/** The global container library, with images from the media library. */
function sf_container_library() {
	$opt = get_option('sf_containers', null);
	if (!is_array($opt)) {
		return sf_default_containers();
	}
	$out = array();
	foreach ($opt as $row) {
		$row = (array) $row;
		$out[] = array(
			'slug'          => sanitize_title(isset($row['slug']) ? $row['slug'] : ''),
			'label'         => sanitize_text_field(isset($row['label']) ? $row['label'] : ''),
			'attachment_id' => absint(isset($row['attachment_id']) ? $row['attachment_id'] : 0),
		);
	}
	return $out;
}

add_action('admin_init', function () {
	register_setting('sf_site_settings', 'sf_containers', array(
		'type'              => 'array',
		'sanitize_callback' => function ($v) {
			$out = array();
			foreach ((array) $v as $row) {
				$row = (array) $row;
				$slug = sanitize_title(isset($row['slug']) ? $row['slug'] : '');
				if ($slug === '') {
					continue;
				}
				$out[] = array(
					'slug'          => $slug,
					'label'         => sanitize_text_field(isset($row['label']) ? $row['label'] : ''),
					'attachment_id' => absint(isset($row['attachment_id']) ? $row['attachment_id'] : 0),
				);
			}
			return $out;
		},
	));
	register_setting('sf_site_settings', 'sf_global_faq', array(
		'type'              => 'array',
		'sanitize_callback' => function ($v) {
			$rows = array();
			$qs   = isset($v['q']) && is_array($v['q']) ? $v['q'] : array();
			$as   = isset($v['a']) && is_array($v['a']) ? $v['a'] : array();
			$n    = max(count($qs), count($as));
			for ($i = 0; $i < $n; $i++) {
				$q = sanitize_text_field(isset($qs[$i]) ? $qs[$i] : '');
				$a = sf_mb_kses_answer(isset($as[$i]) ? $as[$i] : '');
				if ($q !== '' || $a !== '') {
					$rows[] = array('q' => $q, 'a' => $a);
				}
			}
			return $rows;
		},
	));
});

add_action('admin_menu', function () {
	add_submenu_page('sf-site-settings', 'Container Library', 'Container Library', 'manage_options', 'sf-containers', 'sf_render_containers_page');
	add_submenu_page('sf-site-settings', 'Global FAQ', 'Global FAQ', 'manage_options', 'sf-global-faq', 'sf_render_global_faq_page');
}, 20); // after the parent menu registers (priority 9) and Social Links (default 10)

/** Row template the tables JS clones for new rows. */
function sf_formula_row_templates_json() {
	$t = array();
	foreach (sf_formula_mb_fields() as $spec) {
		if ('table' === $spec['type']) {
			$t[$spec['key']] = array('cols' => array_keys($spec['cols']));
		}
	}
	return $t;
}

function sf_render_containers_page() {
	if (!current_user_can('manage_options')) {
		return;
	}
	$rows = sf_container_library();
	?>
	<div class="wrap">
		<h1>Container Library</h1>
		<p>The bottle and pack types every product's Container Type field offers. Upload a 400×400 (1:1) photo per type; the label shows under the image.</p>
		<form method="post" action="options.php">
			<?php settings_fields('sf_site_settings'); ?>
			<table class="widefat sf-containers" id="sf-containers">
				<thead><tr><th>Image (400×400)</th><th>Label</th><th>Slug</th><th></th></tr></thead>
				<tbody>
				<?php foreach ($rows as $c) : ?>
					<tr>
						<td class="sf-containers__media">
							<input type="hidden" name="sf_containers[attachment_id][]" value="<?php echo (int) $c['attachment_id']; ?>"/>
							<div class="sf-containers__preview"><?php
								echo $c['attachment_id'] ? wp_get_attachment_image((int) $c['attachment_id'], array(80, 80)) : '';
							?></div>
							<button type="button" class="button sf-containers__pick">Choose</button>
						</td>
						<td><input type="text" class="regular-text" name="sf_containers[label][]" value="<?php echo esc_attr($c['label']); ?>"/></td>
						<td><input type="text" class="regular-text code" name="sf_containers[slug][]" value="<?php echo esc_attr($c['slug']); ?>"/></td>
						<td><button type="button" class="button-link sf-containers__del">Remove</button></td>
					</tr>
				<?php endforeach; ?>
				</tbody>
			</table>
			<p><button type="button" class="button" id="sf-containers-add">+ Add container type</button></p>
			<?php submit_button(); ?>
		</form>
	</div>
	<?php
}

function sf_render_global_faq_page() {
	if (!current_user_can('manage_options')) {
		return;
	}
	$rows = get_option('sf_global_faq', array());
	if (!is_array($rows)) {
		$rows = array();
	}
	?>
	<div class="wrap">
		<h1>Global FAQ</h1>
		<p>Questions every product shares. They are appended after each product's own FAQ on the front end (front-end rendering lands with batch H2).</p>
		<form method="post" action="options.php">
			<?php settings_fields('sf_site_settings'); ?>
			<table class="widefat sf-reptable sf-reptable--faq" data-sf-name="sf_global_faq">
				<thead><tr><th>Question</th><th>Answer</th><th></th></tr></thead>
				<tbody>
				<?php foreach ($rows as $r) : $r = array_merge(array('q' => '', 'a' => ''), (array) $r); ?>
					<tr>
						<td><input type="text" class="widefat" name="sf_global_faq[q][]" value="<?php echo esc_attr($r['q']); ?>"/></td>
						<td><textarea class="widefat" rows="3" name="sf_global_faq[a][]"><?php echo esc_textarea($r['a']); ?></textarea></td>
						<td><button type="button" class="button-link sf-reptable__del">Remove</button></td>
					</tr>
				<?php endforeach; ?>
				</tbody>
			</table>
			<p><button type="button" class="button sf-reptable__add sf-reptable__add--empty" data-sf-name="sf_global_faq">+ Add row</button></p>
			<?php submit_button(); ?>
		</form>
	</div>
	<?php
}

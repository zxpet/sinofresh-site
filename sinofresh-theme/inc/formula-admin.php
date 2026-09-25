<?php
/**
 * SINO FRESH — the formula publishing form (batch H1).
 *
 * Phase 1 of the detail-page rebuild: every product carries its own data
 * instead of borrowing the dosage page's. This file is the admin half —
 * meta boxes, sanitising, the phase-1 warning banner, and the two Site
 * Settings subpages (Container Library, Shape Library, Global FAQ). Front-end readers of
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
		'sf_formula_card_badge'       => 'Card badge overlay: one of sinofresh_formula_card_badges(), or empty for none.',
		'sf_formula_flavors'          => 'JSON array of flavour options.',
		'sf_formula_weight'           => 'Unit Weight options (JSON array, batch H9). Soft chews / tablets / dental chews only.',
		'sf_formula_counts'           => 'JSON array of pack counts (batch H9: the three chew/tablet forms only).',
		'sf_formula_net_content'      => 'Net Content options (JSON array, batch H9). All dosage forms.',
		'sf_formula_shape'            => 'Shape options (JSON array, batch H9).',
		'sf_formula_species'          => 'JSON array: dog / cat.',
		'sf_formula_lifestage'        => 'Life stage options (JSON array, batch H9).',
		'sf_formula_price_tiers'      => 'JSON array of {qty, price} tiers.',
		'sf_formula_recommended_for'  => 'Recommended For copy.',
		'sf_formula_use_cases'        => 'Use Cases copy.',
		'sf_formula_who_for'          => "Who It's For copy.",
		'sf_formula_packaging_extra'  => 'JSON array of extra packaging options.',
		'sf_formula_colors'           => 'JSON array of colour options.',
		'sf_formula_shelf_life'       => 'Shelf life: one value from the fixed pool.',
		'sf_formula_cartons'          => 'JSON array of {count, boxes, size} carton rows.',
		'sf_formula_lead_time'        => 'Lead time text.',
		'sf_formula_container'        => 'Container options (JSON array, batch H9; was a single slug).',
		'sf_formula_faq_data'         => 'JSON array of {q, a} product FAQ rows.',
		'sf_formula_groups_config'    => 'Configurator Display overrides (JSON, batch H9): {group: {show, label, options}}.',
		'sf_param_sample_policy'       => 'Sample Policy line (batch H10 spec sheet).',
		'sf_param_customizable'        => 'Customisation scope line (batch H10 spec sheet).',
		'sf_param_private_label'       => 'Private label availability line (batch H10 spec sheet).',
		'sf_param_payment_terms'       => 'Payment terms line (batch H10 spec sheet).',
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
		'config'    => array('title' => 'Configurator Display', 'context' => 'normal'),
		'detail'    => array('title' => 'Detailed Content', 'context' => 'normal'),
		'packaging' => array('title' => 'Packaging', 'context' => 'normal'),
		/* Batch H10 — the specification-sheet facts: what the product is, what
		   the label says, how it ships. All optional (req 1): the sales desk
		   fills what it can stand behind, and a blank field prints no row. */
		'specsheet' => array('title' => 'Spec Sheet', 'context' => 'normal'),
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
		/* 待办17 — a dropdown, not radios: four answers including "none", and
		   the options come from the same map the card reads (see
		   sinofresh_formula_card_badges()), so the editor can only pick a badge
		   the front end can actually draw. req 1 = optional: most formulas will
		   never carry one, and a banner that asks for a decoration is noise. */
		array('key' => 'sf_formula_card_badge', 'label' => 'Card badge', 'group' => 'media', 'type' => 'select', 'req' => 1,
			'pool' => array_keys(sinofresh_formula_card_badges()), 'empty_label' => '— None —',
			'hint' => 'Optional overlay on the card image: Best Seller (gold), Hot (red), New (blue). Leave as "None" for no badge.'),
		// params — pools resolve per dosage form at render time.
		// Batch H9 — every configurator-fed field is MULTI: the editor ticks
		// which options the record supports, the front end shows exactly that
		// subset, and the customer picks ONE. `config_group` names the
		// configurator group whose Configurator Display row (label / show /
		// option override) drives this field's option list. The hints are
		// Chinese ON PURPOSE and render ONLY inside this metabox
		// (sf_formula_render_field outputs them nowhere else) — front-end
		// bytes are asserted Chinese-free by the H9 gate.
		array('key' => 'sf_formula_flavors', 'label' => 'Flavors', 'group' => 'params', 'type' => 'multi', 'req' => 2, 'pool' => 'flavors', 'config_group' => 'flavor',
			'hint' => '口味：勾选该产品支持的口味，前台客户从中单选一个（可在 Configurator Display 改组名/选项）。'),
		array('key' => 'sf_formula_weight', 'label' => 'Unit Weight', 'group' => 'params', 'type' => 'multi', 'req' => 2, 'pool' => 'weights', 'config_group' => 'weight',
			'applies' => array('soft-chews', 'tablets', 'dental-chews'),
			'hint' => '单件克重，如 2g。仅软咀嚼/片剂/洁齿显示；其它剂型此字段隐藏。勾选支持的规格，客户单选。（158 疑似测试残留：全池值，填内容阶段逐条核对）'),
		array('key' => 'sf_formula_counts', 'label' => 'Counts', 'group' => 'params', 'type' => 'multi', 'req' => 2, 'pool' => 'counts', 'config_group' => 'counts',
			'applies' => array('soft-chews', 'tablets', 'dental-chews'),
			'hint' => '粒数，如 60。仅软咀嚼/片剂/洁齿显示；其它剂型此字段隐藏。（158 疑似测试残留：全池值，填内容阶段逐条核对）'),
		array('key' => 'sf_formula_net_content', 'label' => 'Net Content', 'group' => 'params', 'type' => 'multi', 'req' => 2, 'pool' => 'net_content', 'config_group' => 'net-content',
			'hint' => '净含量，如 120g per bottle。所有剂型显示；粒数信息一并写进净含量文字（鱼油如 60 softgels (60g) per bottle）。'),
		array('key' => 'sf_formula_shape', 'label' => 'Shape', 'group' => 'params', 'type' => 'multi', 'req' => 2, 'pool' => 'shape', 'config_group' => 'shape',
			'hint' => '形状/质地/外观：勾选该剂型支持的选项，前台只显示勾选的，客户单选。（158 疑似测试残留：全池值，填内容阶段逐条核对）'),
		array('key' => 'sf_formula_species', 'label' => 'Suitable for', 'group' => 'params', 'type' => 'multi', 'req' => 2, 'pool' => array('Dog', 'Cat'), 'config_group' => 'species',
			'hint' => '适用宠物：Dog 和 Cat 两项都勾选时，前台会额外出现 "Dog and Cat" 单选项。（158 疑似测试残留：全池值，填内容阶段逐条核对）'),
		array('key' => 'sf_formula_lifestage', 'label' => 'Life stage', 'group' => 'params', 'type' => 'multi', 'req' => 2,
			'pool' => array('Puppy', 'Kitten', 'Adult', 'Senior', 'All Life Stages'), 'config_group' => 'stage',
			'hint' => '生命周期：勾选该产品适用的阶段（可多选），前台客户单选一个。（158 疑似测试残留：全池值，填内容阶段逐条核对）'),
		array('key' => 'sf_formula_price_tiers', 'label' => 'Tier pricing', 'group' => 'params', 'type' => 'table', 'req' => 2,
			'cols' => array('min' => 'Min quantity', 'max' => 'Max quantity', 'price' => 'Unit price (USD)'),
			'hint' => 'Leave Max empty on the top tier: the ladder prints it as "1,000 and up".'),
		array('key' => 'sf_formula_sample_price', 'label' => 'Sample price (USD)', 'group' => 'params', 'type' => 'text', 'req' => 1,
			'hint' => 'e.g. 50 — printed beside "Get Sample" under the price ladder. Leave empty to hide the row.'),
		/* Batch H8a — a fixed pool, not free text. The field was free text and
		   the front end never read it (it parsed the spec sheet instead), so
		   the two could — and did — disagree: post 158 says 24 months here and
		   18 months in sf_formula_specs. The record now declares one of four
		   answers and the page prints THAT, which is why this moved from the
		   Packaging box to the right-column box: it is now a value the visitor
		   reads, like every other field in this group.
		   `keep_unknown` is the migration seam. post 158 was saved as
		   "24months" (no space) before the pool existed, and a fixed list that
		   is the only source of truth would clear it on the next save — a
		   silent edit of a field nobody touched. The flag keeps whatever the
		   record already holds selectable and saveable, so the editor sees the
		   real value and chooses when to canonicalise it. */
		array('key' => 'sf_formula_shelf_life', 'label' => 'Shelf life', 'group' => 'params', 'type' => 'select', 'req' => 2,
			'pool' => sf_formula_shelf_life_pool(), 'empty_label' => '— None —', 'keep_unknown' => true,
			'hint' => 'Printed read-only under the parameters: the customer cannot pick a different one.'),
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
		array('key' => 'sf_formula_cartons', 'label' => 'Carton dimensions', 'group' => 'packaging', 'type' => 'table', 'req' => 1,
			'cols' => array('count' => 'Pack count', 'boxes' => 'Units per carton', 'size' => 'Carton size (cm)')),
		// faq
		array('key' => 'sf_formula_lead_time', 'label' => 'Lead time', 'group' => 'faq', 'type' => 'text', 'req' => 1),
		array('key' => 'sf_formula_container', 'label' => 'Container Type', 'group' => 'faq', 'type' => 'multi', 'req' => 2,
			'pool' => 'packaging', 'config_group' => 'container',
			'hint' => '包装形式：勾选该剂型支持的包装，前台只显示勾选的，客户单选。历史值（如 Round）会保留可选，改存后落入新词汇。'),
		array('key' => 'sf_formula_faq_data', 'label' => 'Product FAQ', 'group' => 'faq', 'type' => 'faqtable', 'req' => 1,
			'hint' => 'Questions ship prefilled; fill the answers. Site-wide questions are appended from the Global FAQ.'),
		// specsheet — batch H10, trimmed by H10b. The formula-copy, label-
		// compliance and logistics fields were removed: that content is
		// product-specific prose the editors write into the body band (Word /
		// Excel paste), not per-field rows. Chinese hints again render in this
		// metabox only; the front end prints the row's LABEL and the value,
		// never the hint.
		array('key' => 'sf_param_sample_policy', 'label' => 'Sample Policy', 'group' => 'specsheet', 'type' => 'text', 'req' => 1,
			'hint' => '样品政策，如 Samples available, freight collect。留空该行不显示。'),
		array('key' => 'sf_param_customizable', 'label' => 'Customizable', 'group' => 'specsheet', 'type' => 'text', 'req' => 1,
			'hint' => '可定制范围，如 Yes — formula, flavor, shape, color and packaging。'),
		array('key' => 'sf_param_private_label', 'label' => 'Private Label', 'group' => 'specsheet', 'type' => 'text', 'req' => 1,
			'hint' => '是否支持贴牌，如 Available。'),
		array('key' => 'sf_param_payment_terms', 'label' => 'Payment Terms', 'group' => 'specsheet', 'type' => 'text', 'req' => 1,
			'hint' => '付款方式（公司政策），如 T/T 30% deposit, balance before shipment。勿编，留空该行不显示。'),
	);
}

/** The dosage form slug of the record being edited ('' before a term is set). */
function sf_formula_record_form($post_id) {
	$terms = wp_get_post_terms($post_id, 'sf_formula_form', array('fields' => 'slugs'));
	return (!is_wp_error($terms) && $terms) ? (string) $terms[0] : '';
}

/** Resolve a spec's option list: fixed array or dosage pool.
 *
 * Batch H8b retired the third source. Until this batch Container Type was
 * `'pool' => '_containers'` — the seven-row Site Settings library, whose rows
 * are Round / Square / Oval / Jar / Pouch / Tube / Custom, i.e. bottle SHAPES
 * rather than packaging formats. The detail page drew the same seven, so the
 * two agreed with each other and disagreed with the question; the pool that
 * answers it has been in formula-pools.php since batch H1 and is per dosage
 * form. The library keeps its other job — being a picture an option can be
 * matched to by label (see sf_formula_pool_option_image()). */
function sf_formula_mb_options($spec, $post_id) {
	if (!isset($spec['pool'])) {
		return array();
	}
	$opts = is_array($spec['pool']) ? $spec['pool'] : sf_formula_field_pool(sf_formula_record_form($post_id), $spec['pool']);
	/* Batch H9 — a Configurator Display option override replaces the pool for
	   its group, and the override list IS the new whitelist (user ruling F,
	   2026-09-25): whatever the editor typed there is what the checkboxes
	   offer and what the front end can show. Empty means "use the pool". */
	if (!empty($spec['config_group'])) {
		$cfg = sf_formula_groups_config($post_id);
		if (isset($cfg[$spec['config_group']]['options']) && is_array($cfg[$spec['config_group']]['options']) && $cfg[$spec['config_group']]['options']) {
			$opts = $cfg[$spec['config_group']]['options'];
		}
	}
	return $opts;
}

/* --------------------------------------------------------------------------
 * Meta boxes — seven groups, one shared renderer (batch H9 adds Configurator
 * Display, which has its own renderer below).
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
	if ('config' === $group) {
		sf_formula_render_config_box($post);
		return;
	}
	echo '<div class="sf-mb" data-sf-group="' . esc_attr($group) . '">';
	foreach (sf_formula_mb_fields() as $spec) {
		if ($spec['group'] !== $group) {
			continue;
		}
		sf_formula_render_field($spec, $post->ID);
	}
	echo '</div>';
}

/* --------------------------------------------------------------------------
 * Configurator Display (batch H9) — per-group show / label / option override.
 *
 * Eight rows, one per configurator group. Storage is ONE meta key
 * (sf_formula_groups_config, JSON): {group: {show: false, label: "...",
 * options: [...]}}. A group whose row is all-default is omitted from the
 * JSON, so "key absent" reads as "pool defaults, group shown" — the same
 * empty-means-absent contract every other meta key here follows.
 *
 * The three fields are read by BOTH ends through sf_formula_groups_config()
 * (formula-pools.php) and sf_formula_group_defaults(): the front end applies
 * them in sinofresh_formula_config_groups(), the publishing form's own
 * checkboxes in sf_formula_mb_options(). One store, two readers, no drift.
 *
 * All Chinese on this screen lives in $row_hints and the row placeholders —
 * neither is ever printed on the front end (the H9 gate asserts the front
 * pages stay Chinese-free).
 * ------------------------------------------------------------------------ */
function sf_formula_config_group_rows() {
	return array(
		'flavor'      => array('name' => '口味（Flavor）', 'hint' => '组名不填用默认（按剂型：Flavor / Source）。选项每行一个，不填用池默认。'),
		'weight'      => array('name' => '单件克重（Unit Weight）', 'hint' => '仅软咀嚼/片剂/洁齿显示，其它剂型整组隐藏。组名不填用池默认（Weight per Piece / Weight per Tablet）。'),
		'counts'      => array('name' => '粒数（Counts）', 'hint' => '仅软咀嚼/片剂/洁齿显示。组名不填用池默认（Count per Bottle / Count per Pack）。'),
		'net-content' => array('name' => '净含量（Net Content）', 'hint' => '所有剂型显示。建议值如 120g per bottle；鱼油把粒数写进净含量，如 60 softgels (60g) per bottle。'),
		'shape'       => array('name' => '形状/质地/外观（Shape）', 'hint' => '组名不填用池默认（Shape / Texture / Appearance / Form）。选项覆盖后即为该组全部选项。'),
		'container'   => array('name' => '包装形式（Container Type）', 'hint' => '选项覆盖后即为该组全部选项；覆盖列表里写什么，前台就显示什么。'),
		'species'     => array('name' => '适用宠物（Suitable For）', 'hint' => '默认 Dog / Cat；后台两项都勾选时前台额外出现 "Dog and Cat"。此组无 Custom 自由文本。'),
		'stage'       => array('name' => '生命周期（Life Stage）', 'hint' => '默认 Puppy / Kitten / Adult / Senior / All Life Stages。此组无 Custom 自由文本。'),
	);
}

function sf_formula_render_config_box($post) {
	$form     = sf_formula_record_form($post->ID);
	$defaults = sf_formula_group_defaults($form);
	$raw      = json_decode((string) get_post_meta($post->ID, 'sf_formula_groups_config', true), true);
	$cfg      = is_array($raw) ? $raw : array();
	echo '<div class="sf-mb sf-cfg" data-sf-group="config">';
	echo '<p class="sf-mb__hint">前台配置器每组「显示开关 / 组名 / 选项列表」。组名与选项不填用默认；填了即覆盖（前后台显示同一个名）。每组对每个剂型独立生效。</p>';
	foreach (sf_formula_config_group_rows() as $gk => $row) {
		$d        = $defaults[$gk];
		$state    = isset($cfg[$gk]) && is_array($cfg[$gk]) ? $cfg[$gk] : array();
		$shown    = !isset($state['show']) || !empty($state['show']);
		$label    = isset($state['label']) && is_string($state['label']) ? $state['label'] : '';
		$options  = isset($state['options']) && is_array($state['options']) ? implode("\n", $state['options']) : '';
		$def_lb   = $d['label'];
		echo '<div class="sf-cfg__row" data-sf-cfg-group="' . esc_attr($gk) . '">';
		if (empty($d['applies'])) {
			echo '<p class="sf-mb__hint"><strong>' . esc_html($row['name']) . '</strong> — 该剂型不显示此组（仅软咀嚼/片剂/洁齿）。</p>';
			echo '</div>';
			continue;
		}
		echo '<p class="sf-cfg__name"><strong>' . esc_html($row['name']) . '</strong></p>';
		echo '<p class="sf-mb__hint">' . esc_html($row['hint']) . '</p>';
		echo '<p class="sf-cfg__controls">';
		echo '<label class="sf-cfg__show"><input type="checkbox" name="sf_groups_config[' . esc_attr($gk) . '][show]" value="1"' . checked($shown, true, false) . '/> 显示此组</label> ';
		echo '<input type="text" class="regular-text" name="sf_groups_config[' . esc_attr($gk) . '][label]" value="' . esc_attr($label) . '" placeholder="组名，默认：' . esc_attr($def_lb) . '"/>';
		echo '</p>';
		echo '<textarea class="widefat sf-cfg__options" rows="' . esc_attr(max(3, min(8, $options ? substr_count($options, "\n") + 1 : 3))) . '" name="sf_groups_config[' . esc_attr($gk) . '][options]" placeholder="选项列表，每行一个；留空用池默认（默认 ' . esc_attr(count($d['options'])) . ' 项）">' . esc_textarea($options) . '</textarea>';
		echo '</div>';
	}
	echo '</div>';
}

/** Persist the Configurator Display rows (batch H9). Runs after the field
 *  loop in the save handler below; the 'config' box's nonce is verified by
 *  that handler's existing all-groups nonce check. */
function sf_formula_save_groups_config($post_id, $form) {
	$in  = isset($_POST['sf_groups_config']) && is_array($_POST['sf_groups_config']) ? wp_unslash($_POST['sf_groups_config']) : array();
	$all = sf_formula_group_defaults($form);
	$out = array();
	foreach (array_keys(sf_formula_config_group_rows()) as $gk) {
		if (empty($all[$gk]['applies'])) {
			continue; // the row was not rendered for this dosage form
		}
		$row   = isset($in[$gk]) && is_array($in[$gk]) ? $in[$gk] : array();
		$show  = !empty($row['show']);
		$label = sanitize_text_field(isset($row['label']) ? $row['label'] : '');
		$opts  = array();
		foreach (preg_split('/\r\n|\r|\n/', (string) (isset($row['options']) ? $row['options'] : '')) as $line) {
			$line = sanitize_text_field($line);
			if ($line !== '') {
				$opts[] = $line;
			}
		}
		$entry = array();
		if (!$show) {
			$entry['show'] = false; // shown is the default; only the off state is stored
		}
		if ($label !== '' && $label !== (string) $all[$gk]['label']) {
			$entry['label'] = $label; // equal-to-default labels are not stored
		}
		if ($opts && $opts !== $all[$gk]['options']) {
			$entry['options'] = $opts;
		}
		if ($entry) {
			$out[$gk] = $entry;
		}
	}
	sf_mb_store($post_id, 'sf_formula_groups_config', wp_json_encode($out, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES));
}

function sf_formula_render_field($spec, $post_id) {
	$raw    = get_post_meta($post_id, $spec['key'], true);
	$opts   = sf_formula_mb_options($spec, $post_id);
	$req    = (2 === (int) $spec['req']) ? ' <span class="sf-mb__req" title="Required before publish">*</span>' : '';
	$hid    = ('multi' === $spec['type'] || 'radio' === $spec['type']) && empty($opts);
	/* Batch H9 — a spec may carry an `applies` list of dosage-form slugs. A
	   record outside the list hides the field entirely (Unit Weight and
	   Counts exist only on the three chew/tablet forms); either this or the
	   empty-options hide below is what "hidden" means. */
	if (!empty($spec['applies'])) {
		$form = sf_formula_record_form($post_id);
		if ($form === '' || !in_array($form, $spec['applies'], true)) {
			$hid = true;
		}
	}
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
			/* `keep_unknown` (batch H8b) does for a radio what batch H8a made it
			   do for the select: show the record's own value even when the pool
			   no longer offers it. Container Type needs it because its
			   vocabulary changed, not because it is optional — post 158 still
			   stores the retired library's "Round", which no dosage pool
			   contains, and without this the editor would open the record, see
			   nothing ticked, and the next save would clear a value nobody
			   touched (the save handler accepts an out-of-pool value only for a
			   spec carrying this flag). */
			if (!empty($spec['keep_unknown']) && '' !== (string) $raw && !in_array($raw, $opts, true)) {
				array_unshift($opts, $raw);
			}
			foreach ($opts as $o) {
				printf('<label class="sf-mb__opt"><input type="radio" name="%s" value="%s" %s/> %s</label>',
					esc_attr($spec['key']), esc_attr($o), checked($raw, $o, false), esc_html($o));
			}
			break;
		case 'select':
			/* The empty option is a stored answer, not a placeholder: it is how
			   a record goes back to having no badge after having had one. Its
			   wording comes from the spec so the type stays reusable. */
			$list = $opts;
			/* `keep_unknown` (batch H8a): show the record's own value even when
			   the pool no longer offers it, so the editor reads what is stored
			   and the form cannot post a value back that the save handler would
			   then drop. See the shelf-life spec for why one field needs this. */
			if (!empty($spec['keep_unknown']) && '' !== (string) $raw && !in_array($raw, $list, true)) {
				array_unshift($list, $raw);
			}
			printf('<select class="sf-mb__select" name="%s"><option value=""%s>%s</option>',
				esc_attr($spec['key']),
				selected($raw, '', false),
				esc_html(isset($spec['empty_label']) ? $spec['empty_label'] : 'None'));
			foreach ($list as $o) {
				printf('<option value="%s"%s>%s</option>',
					esc_attr($o), selected($raw, $o, false), esc_html($o));
			}
			echo '</select>';
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
			/* Empty meta still renders ONE blank row: the table JS clones the
			 * last <tr> and is a no-op on a zero-row tbody, so an empty table
			 * could never receive its first row. Saving drops fully-empty rows
			 * (sf_formula_save_meta), so the blank row is never stored. */
			if (!$rows) {
				$rows = array(array());
			}
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
				sf_mb_store($post_id, $key, sanitize_text_field(wp_unslash($_POST[$key] ?? '')));
				break;
			case 'url':
				sf_mb_store($post_id, $key, esc_url_raw(wp_unslash($_POST[$key] ?? '')));
				break;
			case 'textarea':
				sf_mb_store($post_id, $key, sanitize_textarea_field(wp_unslash($_POST[$key] ?? '')));
				break;
			case 'multi':
				$in   = array_map('sanitize_text_field', (array) wp_unslash($_POST[$key] ?? array()));
				$opts = sf_formula_mb_options($spec, $post_id);
				sf_mb_store($post_id, $key, wp_json_encode(array_values(array_intersect($opts, $in))));
				break;
			case 'radio':
			case 'select':
				$in   = sanitize_text_field(wp_unslash($_POST[$key] ?? ''));
				$opts = sf_formula_mb_options($spec, $post_id);
				/* Batch H8a — a spec may ask to keep a value its pool no longer
				   offers. Without this a fixed list silently clears a field the
				   editor never touched (post 158's shelf life was "24months"
				   before the pool existed), which is a data edit nobody asked
				   for. The value stays selectable until the editor changes it. */
				if (!empty($spec['keep_unknown'])) {
					$prev = trim((string) get_post_meta($post_id, $key, true));
					if ($prev !== '' && !in_array($prev, $opts, true)) {
						$opts[] = $prev;
					}
				}
				sf_mb_store($post_id, $key, in_array($in, $opts, true) ? $in : '');
				break;
			case 'gallery':
				$ids = array_filter(array_map('absint', explode(',', (string) wp_unslash($_POST[$key] ?? ''))));
				sf_mb_store($post_id, $key, implode(',', $ids));
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
				/* update_post_meta() runs wp_unslash() on the value, which would
				 * strip the backslash out of JSON escapes (\" quotes, \uXXXX) and
				 * corrupt the stored JSON — measured 2026-09-21 (an em dash came
				 * back as a literal "u2014"). Store slash-slashed data with
				 * unicode/slashes unescaped, as the core API expects. */
				sf_mb_store($post_id, $key, wp_slash(wp_json_encode(array_values($rows), JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES)));
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
			sf_mb_store($post_id, $key, wp_slash(wp_json_encode(array_values($rows), JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES)));
			break;
		}
	}

	/* Batch H9 — the Configurator Display rows ride the same save round-trip
	   (their nonce is verified by the all-groups check above). */
	sf_formula_save_groups_config($post_id, $form);
}, 10, 1);

/** FAQ answers are plain text plus <a href> — nothing else survives. */
function sf_mb_kses_answer($v) {
	return wp_kses((string) $v, array('a' => array('href' => array(), 'title' => array(), 'target' => array())));
}

/* "Empty means absent": a blank single value and an empty JSON shape delete
 * the key instead of writing '', '[]'. The migration leaves 16 keys
 * intentionally EMPTY for the sales team to fill; a first admin save must
 * not pollute them (measured 2026-09-21: one save wrote '[]' into 7 keys,
 * breaking the key-census invariant). Renderer behavior is unchanged —
 * get_post_meta() returns '' for a missing key either way. */
function sf_mb_store($post_id, $key, $value) {
	$v = (string) $value;
	if ($v === '' || $v === '[]') {
		delete_post_meta($post_id, $key);
		return;
	}
	update_post_meta($post_id, $key, $v);
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
				/* H7i: a complete row is a range start plus a price. The max end
				   is optional by design — the top tier is open-ended — so it is
				   not part of "complete". A legacy qty still counts as the min. */
				$min   = trim((string) ($r['min'] ?? ($r['qty'] ?? '')));
				$price = trim((string) ($r['price'] ?? ''));
				if ($min !== '' && $price !== '') {
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
		/* WP derives a submenu's hook prefix from sanitize_title(menu_title),
		 * not from the menu slug: 'Site Settings' -> 'site-settings', so the
		 * hooks below are site-settings_page_* (recorded live 2026-09-21,
		 * verified with a temporary hook-diag mu-plugin). */
		'site-settings_page_sf-containers', 'site-settings_page_sf-shapes',
		'site-settings_page_sf-global-faq'), true);
	if (!$is_formula && !$is_settings) {
		return;
	}
	$dir = get_template_directory_uri();
	wp_enqueue_style('sf-mb', $dir . '/assets/admin/sf-mb.css', array(), '1.1.0');
	wp_enqueue_script('sf-mb-tables', $dir . '/assets/admin/sf-mb-tables.js', array(), '1.0.0', true);
	if ($is_formula) {
		wp_enqueue_script('sf-mb-precheck', $dir . '/assets/admin/sf-mb-precheck.js', array(), '1.0.1', true);
	}
	if ($is_settings) {
		wp_enqueue_media(); /* the Container Library picks images via wp.media */
		wp_enqueue_script('sf-site-settings', $dir . '/assets/admin/sf-site-settings.js', array(), '1.0.1', true);
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

/* Batch H7g — the shape library. Same shape as the container library on
   purpose: an admin who learned one page can run the other, and the front
   end reads both through the same option/label/attachment_id triple.
   The slugs are permanent because the configurator posts them and the PDF
   endpoint validates against them — renaming a slug orphans the saved
   choice, so "cylinder" stays "cylinder" even if the label is reworded. */
function sf_default_shapes() {
	return array(
		array('slug' => 'bone',     'label' => 'Bone',     'attachment_id' => 0),
		array('slug' => 'round',    'label' => 'Round',    'attachment_id' => 0),
		array('slug' => 'square',   'label' => 'Square',   'attachment_id' => 0),
		array('slug' => 'heart',    'label' => 'Heart',    'attachment_id' => 0),
		array('slug' => 'star',     'label' => 'Star',     'attachment_id' => 0),
		array('slug' => 'paw',      'label' => 'Paw',      'attachment_id' => 0),
		array('slug' => 'cylinder', 'label' => 'Cylinder', 'attachment_id' => 0),
		array('slug' => 'custom',   'label' => 'Custom',   'attachment_id' => 0),
	);
}

/** The global shape library, with images from the media library. */
function sf_shape_library() {
	$opt = get_option('sf_shapes', null);
	if (!is_array($opt)) {
		return sf_default_shapes();
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
	/* Batch H7e reads its fallbacks from the same array the Site Settings page
	   uses, rather than repeating the two strings here: one value, one source,
	   and an admin who clears a field gets the shipped default back instead of
	   a blank row on 42 product pages. */
	$d = sf_site_settings_defaults();
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
	/* Batch H7g — same contract as sf_containers: rows with a slug survive,
	   fully-empty rows are dropped, an absent option falls back to the eight
	   shipped shapes. */
	register_setting('sf_site_settings', 'sf_shapes', array(
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
	/* Batch H9b — the three shared form option lists. One textarea per list;
   every line becomes one <option>. Editing here rewrites the Country,
   Target Market and Interested Dosage Form selects on all four forms at
   once (8 quote, 9 sample, 10 tour, 11 COA) — the 11 copies inside the FF
   field definitions stop being the thing to maintain. A list left empty
   hands control back to Fluent Forms (the form's own options render), so
   clearing a box can never blank a live dropdown. */
function sf_render_form_options_page() {
	if (!current_user_can('manage_options')) {
		return;
	}
	$saved = get_option('sf_form_options', array());
	if (!is_array($saved)) {
		$saved = array();
	}
	$defaults = sinofresh_form_options_defaults();
	$fields   = array(
		'dosage_forms'   => array('Interested Dosage Form', '剂型选项。询盘 / 样品 / 参观 / COA 四个表单同步。每行一项，与 8 个剂型页对应（独立维护，删页面不会联动选项）。'),
		'countries'      => array('Country', '国家选项。四个表单同步。每行一项，最后一项通常保留 Other。'),
		'target_markets' => array('Target Market', '目标市场选项。样品 / 参观 / COA 三个表单同步。每行一项（US / EU / UK / JP / AU / CA / Other）。'),
	);
	?>
	<div class="wrap">
		<h1>Form Options</h1>
		<p>The option lists of the shared selects on the inquiry forms. One edit here updates every form at once.
		<strong>清空某一组＝该组回退为表单内现值</strong>（下拉永远不会被清空）。</p>
		<form method="post" action="options.php">
			<?php settings_fields('sf_site_settings'); ?>
			<table class="form-table" role="presentation">
				<?php foreach ($fields as $key => $meta) : ?>
					<tr>
						<th scope="row"><label for="sf_form_options_<?php echo esc_attr($key); ?>"><?php echo esc_html($meta[0]); ?></label></th>
						<td><textarea name="sf_form_options[<?php echo esc_attr($key); ?>]" id="sf_form_options_<?php echo esc_attr($key); ?>"
							rows="<?php echo max(4, substr_count((string) (isset($saved[$key]) ? $saved[$key] : $defaults[$key]), "\n") + 2); ?>"
							class="large-text code"><?php
							echo esc_textarea(isset($saved[$key]) && is_string($saved[$key]) ? $saved[$key] : $defaults[$key]);
						?></textarea>
						<p class="description"><?php echo esc_html($meta[1]); ?></p></td>
					</tr>
				<?php endforeach; ?>
			</table>
			<?php submit_button(); ?>
		</form>
	</div>
	<?php
}

/* Batch H7e — the two factory facts the spec sheet prints. They had no
	   field anywhere: sinofresh_formula_specs_table() spelled them out as
	   constants, so the only way to change them was a deploy. Same contract as
	   the text fields on the parent page — an emptied field falls back to the
	   shipped default instead of storing "". */
	foreach (array('sf_factory_origin', 'sf_factory_oem') as $key) {
		register_setting('sf_site_settings', $key, array(
			'type'              => 'string',
			'sanitize_callback' => function ($v) use ($d, $key) {
				$v = sanitize_text_field($v);
				return ($v !== '') ? $v : $d[$key];
			},
		));
	}
	/* Batch H10 — the four dosage-form facts, one option, one row per form.
	   An emptied field falls back to the shipped default at READ time
	   (sf_form_facts_value), so storing '' here is safe: it means "use the
	   default" and the page never goes blank. Unknown slugs are dropped so a
	   stale POST cannot plant a row no reader will ever find. */
	register_setting('sf_site_settings', 'sf_form_facts', array(
		'type'              => 'array',
		'sanitize_callback' => function ($v) {
			$d   = sf_form_facts_defaults();
			$out = array();
			foreach ((array) $v as $slug => $row) {
				$slug = sanitize_title($slug);
				if (!isset($d[$slug])) {
					continue;
				}
				$row          = (array) $row;
				$out[$slug] = array(
					'moq'       => sanitize_text_field(isset($row['moq']) ? $row['moq'] : ''),
					'lead'      => sanitize_text_field(isset($row['lead']) ? $row['lead'] : ''),
					'certs'     => sanitize_text_field(isset($row['certs']) ? $row['certs'] : ''),
					'packaging' => sanitize_text_field(isset($row['packaging']) ? $row['packaging'] : ''),
				);
			}
			return $out;
		},
	));
	/* Batch H10 — the seven factory-trust facts. No default-forcing here ON
	   PURPOSE: an emptied field must be able to turn its row OFF (the spec
	   sheet's empty-means-absent contract), which is how operations retires
	   e.g. On-time Delivery without a deploy. The shipped defaults apply only
	   while the option was never saved (sf_formula_trust_value). */
	foreach (array_keys(sf_trust_defaults()) as $key) {
		register_setting('sf_site_settings', $key, array(
			'type'              => 'string',
			'sanitize_callback' => 'sanitize_text_field',
		));
	}
	/* Batch H9b — the three shared form option lists. Each list is stored
	   as one newline-separated string (what the textarea shows). A list the
	   back office empties is an EMPTY override, and the render filter
	   (sinofresh_form_options_list) then lets Fluent Forms print its own
	   stored options — the usual empty-means-absent, so the rollback for a
	   bad edit is clearing the box, and the rollback for everything is
	   deleting the option. Unknown keys are dropped so a stale POST cannot
	   plant a list no field will ever read. */
	register_setting('sf_site_settings', 'sf_form_options', array(
		'type'              => 'array',
		'sanitize_callback' => function ($v) {
			$out = array();
			foreach (array_keys(sinofresh_form_options_defaults()) as $key) {
				$raw  = (is_array($v) && isset($v[$key]) && is_string($v[$key])) ? $v[$key] : '';
				$lines = array();
				foreach (explode("\n", $raw) as $line) {
					$line = trim($line);
					if ($line !== '') {
						$lines[] = sanitize_text_field($line);
					}
				}
				$out[$key] = implode("\n", $lines);
			}
			return $out;
		},
	));
});

add_action('admin_menu', function () {
	add_submenu_page('sf-site-settings', 'Container Library', 'Container Library', 'manage_options', 'sf-containers', 'sf_render_containers_page');
	add_submenu_page('sf-site-settings', 'Shape Library', 'Shape Library', 'manage_options', 'sf-shapes', 'sf_render_shapes_page');
	add_submenu_page('sf-site-settings', 'Global FAQ', 'Global FAQ', 'manage_options', 'sf-global-faq', 'sf_render_global_faq_page');
	/* Batch H7e. No hook for this page in admin_enqueue_scripts(): it has no
	   repeating row for sf-mb-tables.js to clone and no image for wp.media to
	   pick, so the shared admin assets stay off it on purpose. */
	add_submenu_page('sf-site-settings', 'Factory Information', 'Factory Information', 'manage_options', 'sf-factory-info', 'sf_render_factory_info_page');
	/* Batch H10. Same precedent as Factory Information: plain form-table, no
	   shared admin assets. One row per dosage form, four facts per row. */
	add_submenu_page('sf-site-settings', 'Dosage Form Facts', 'Dosage Form Facts', 'manage_options', 'sf-form-facts', 'sf_render_form_facts_page');
	/* Batch H9b. Plain form-table, no shared admin assets — three textareas,
	   one per shared option list. */
	add_submenu_page('sf-site-settings', 'Form Options', 'Form Options', 'manage_options', 'sf-form-options', 'sf_render_form_options_page');
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

/* Batch H7g — same table, same JS, different option name. The pick/add/del
   handlers in sf-site-settings.js were generalized to read the attachment
   input by its [attachment_id] suffix rather than by the sf_containers
   prefix, so this page needs no script of its own. */
function sf_render_shapes_page() {
	if (!current_user_can('manage_options')) {
		return;
	}
	$rows = sf_shape_library();
	?>
	<div class="wrap">
		<h1>Shape Library</h1>
		<p>The eight chew/tablet shapes every product's Shape picker offers. Upload a 400×400 (1:1) photo per shape; the label shows under the image, and an empty slot shows the name in a dashed box until a photo lands.</p>
		<form method="post" action="options.php">
			<?php settings_fields('sf_site_settings'); ?>
			<table class="widefat sf-containers" id="sf-shapes">
				<thead><tr><th>Image (400×400)</th><th>Label</th><th>Slug</th><th></th></tr></thead>
				<tbody>
				<?php foreach ($rows as $s) : ?>
					<tr>
						<td class="sf-containers__media">
							<input type="hidden" name="sf_shapes[attachment_id][]" value="<?php echo (int) $s['attachment_id']; ?>"/>
							<div class="sf-containers__preview"><?php
								echo $s['attachment_id'] ? wp_get_attachment_image((int) $s['attachment_id'], array(80, 80)) : '';
							?></div>
							<button type="button" class="button sf-shapes__pick">Choose</button>
						</td>
						<td><input type="text" class="regular-text" name="sf_shapes[label][]" value="<?php echo esc_attr($s['label']); ?>"/></td>
						<td><input type="text" class="regular-text code" name="sf_shapes[slug][]" value="<?php echo esc_attr($s['slug']); ?>"/></td>
						<td><button type="button" class="button-link sf-containers__del">Remove</button></td>
					</tr>
				<?php endforeach; ?>
				</tbody>
			</table>
			<p><button type="button" class="button" id="sf-shapes-add">+ Add shape</button></p>
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
	/* Empty option still renders ONE blank row: the table JS clones the last
	 * <tr> and no-ops on an empty tbody, so an empty table could never
	 * receive its first row. Saving drops fully-empty rows. */
	if (!$rows) {
		$rows = array(array('q' => '', 'a' => ''));
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

/**
 * Site Settings → Factory Information (batch H7e).
 *
 * Two facts the specification sheet prints on every product page had no home in
 * Site Settings: they were constants inside sinofresh_formula_specs_table().
 * This page gives them one. The defaults are those constants character for
 * character, which is what lets the batch claim that the 75 captured pages are
 * byte-identical before and after the swap — the change is where the value
 * COMES FROM, and a value that does not move is the only honest way to say so.
 *
 * A plain form-table page, and deliberately not listed in the hook array of
 * admin_enqueue_scripts(): nothing here is a repeating row and nothing here
 * picks an image, so sf-mb.css, sf-mb-tables.js, sf-site-settings.js and
 * wp.media() all stay off it. The page is the field, and the field is core's.
 */
function sf_render_factory_info_page() {
	if (!current_user_can('manage_options')) {
		return;
	}
	$d      = sf_site_settings_defaults();
	$origin = get_option('sf_factory_origin', $d['sf_factory_origin']);
	$oem    = get_option('sf_factory_oem', $d['sf_factory_oem']);
	?>
	<div class="wrap">
		<h1>Factory Information</h1>
		<p>Facts every product's specification sheet prints. Clearing a field restores its default.</p>
		<form method="post" action="options.php">
			<?php settings_fields('sf_site_settings'); ?>
			<table class="form-table" role="presentation">
				<tr>
					<th scope="row"><label for="sf_factory_origin">Place of Origin</label></th>
					<td><input name="sf_factory_origin" id="sf_factory_origin" type="text" class="large-text" value="<?php echo esc_attr($origin); ?>">
					<p class="description">The <em>Place of Origin</em> row of each product's specification sheet.</p></td>
				</tr>
				<tr>
					<th scope="row"><label for="sf_factory_oem">OEM / ODM</label></th>
					<td><input name="sf_factory_oem" id="sf_factory_oem" type="text" class="large-text" value="<?php echo esc_attr($oem); ?>">
					<p class="description">The <em>OEM / ODM</em> row of each product's specification sheet.</p></td>
				</tr>
			</table>
			<h2>Factory &amp; Trust</h2>
			<p>Seven facts on the detail page's independent Factory &amp; Trust band. Different contract from the two above:
			<strong>clearing a field turns that row OFF</strong> (nothing prints) — never saved yet shows the shipped default.
			 Annual Capacity, On-time Delivery and Reorder Rate ship empty on purpose: fill a real number or leave them off.</p>
			<table class="form-table" role="presentation">
				<?php foreach (array(
					'sf_trust_factory_size'   => array('Factory Size', '厂区面积，如 15,000㎡（默认取自 factory-tour 页）'),
					'sf_trust_cleanroom'      => array('Cleanroom Class', '洁净等级，如 ISO 8'),
					'sf_trust_capacity'       => array('Annual Capacity', '年产能，如 3,000 tons/year。留空＝该行不显示'),
					'sf_trust_export_markets' => array('Export Markets', '出口市场，如 30+ countries（默认取自 factory-tour 页）'),
					'sf_trust_ontime'         => array('On-time Delivery', '准时交付率，如 98%。留空＝该行不显示'),
					'sf_trust_response'       => array('Response Time', '响应时效，如 Within 24 hours（对外承诺，核对后填）'),
					'sf_trust_reorder'        => array('Reorder Rate', '复购率。留空＝该行不显示'),
				) as $key => $meta) : ?>
				<tr>
					<th scope="row"><label for="<?php echo esc_attr($key); ?>"><?php echo esc_html($meta[0]); ?></label></th>
					<td><input name="<?php echo esc_attr($key); ?>" id="<?php echo esc_attr($key); ?>" type="text" class="large-text"
						value="<?php echo esc_attr(get_option($key, '')); ?>"
						placeholder="<?php echo esc_attr(sf_formula_trust_value($key)); ?>">
					<p class="description"><?php echo esc_html($meta[1]); ?></p></td>
				</tr>
				<?php endforeach; ?>
			</table>
			<?php submit_button(); ?>
		</form>
	</div>
	<?php
}

/**
 * Site Settings → Dosage Form Facts (batch H10).
 *
 * The four facts every product of a dosage form prints — MOQ, Lead time,
 * Certifications, Packaging formats — one row per form. Until H10 they were
 * static HTML inside the eight templates/page-<form>.html files; they are now
 * the sf_form_facts option and the templates carry a marker the block
 * renderer swaps for the band built from it. CHANGE ONE ROW HERE AND ALL
 * EIGHT DOSAGE PAGES MOVE AT ONCE — plus every formula detail page of that
 * form: the hero meta line, the intro clause, the FAQ answer, the spec
 * sheet's MOQ row and the Product JSON-LD all read the same option through
 * sinofresh_formula_spec_cell().
 *
 * An emptied field falls back to the shipped default (the string the template
 * used to hardcode), so the band never goes blank. Certifications keeps its
 * two-layer chain: Site Settings → Certifications wins; this field is only
 * the last resort.
 */
function sf_render_form_facts_page() {
	if (!current_user_can('manage_options')) {
		return;
	}
	$d     = sf_form_facts_defaults();
	$opt   = get_option('sf_form_facts', array());
	$opt   = is_array($opt) ? $opt : array();
	$cols  = array(
		'moq'       => array('MOQ', '起订量，如 from 500 units。8 个剂型页＋所有该剂型详情页同步'),
		'lead'      => array('Lead time', '交期，对外承诺，核对后填'),
		'certs'     => array('Certifications', '留空＝回退默认；Site Settings → Certifications 优先'),
		'packaging' => array('Packaging formats', '包装形式清单，末尾 "or custom formats" 建议保留'),
	);
	?>
	<div class="wrap">
		<h1>Dosage Form Facts</h1>
		<p>The four core facts of each dosage form. <strong>One row edits eight dosage pages at once</strong> (and every
		formula detail page of that form: hero meta, intro, FAQ, spec sheet, JSON-LD). Clearing a field restores its default.</p>
		<form method="post" action="options.php">
			<?php settings_fields('sf_site_settings'); ?>
			<table class="widefat striped" role="presentation">
				<thead><tr>
					<th>Dosage form</th>
					<?php foreach ($cols as $c) : ?><th><?php echo esc_html($c[0]); ?></th><?php endforeach; ?>
				</tr></thead>
				<tbody>
				<?php foreach ($d as $slug => $defaults) : ?>
					<tr>
						<th scope="row"><?php echo esc_html($slug); ?></th>
						<?php foreach ($cols as $fact => $meta) :
							$stored = isset($opt[$slug][$fact]) ? (string) $opt[$slug][$fact] : '';
							$value  = ($stored !== '') ? $stored : $defaults[$fact];
						?>
						<td>
							<input type="text" class="large-text" name="sf_form_facts[<?php echo esc_attr($slug); ?>][<?php echo esc_attr($fact); ?>]"
								value="<?php echo esc_attr($value); ?>">
							<p class="description"><?php echo esc_html($meta[1]); ?>默认：<code><?php echo esc_html($defaults[$fact]); ?></code></p>
						</td>
						<?php endforeach; ?>
					</tr>
				<?php endforeach; ?>
				</tbody>
			</table>
			<?php submit_button(); ?>
		</form>
	</div>
	<?php
}

<?php
add_action('after_setup_theme', function() {
	add_theme_support('wp-block-styles');
	add_theme_support('editor-styles');
	/* Site identity logo: the nav + footer render core/site-logo, so ops can
	   swap the logo PNG from Appearance -> Editor without touching templates. */
	add_theme_support('custom-logo', array(
		'height'      => 60,
		'width'       => 200,
		'flex-height' => true,
		'flex-width'  => true,
	));
});

add_action('wp_enqueue_scripts', function() {
	wp_enqueue_style('sinofresh-style', get_stylesheet_uri(), array(), '2.8.5');
	// Sticky nav: every template renders parts/header.html, so this is site-wide.
	wp_enqueue_script('sinofresh-sticky-header', get_template_directory_uri() . '/assets/js/sticky-header.js', array(), '1.0.0', true);
	wp_enqueue_script('sinofresh-ui-components', get_template_directory_uri() . '/assets/js/ui-components.js', array(), '1.0.0', true);
	// Mobile nav: collapse the overlay's submenus until their chevron is tapped.
	wp_enqueue_script('sinofresh-mobile-nav', get_template_directory_uri() . '/assets/js/mobile-nav.js', array(), '1.1.0', true);
	if (is_front_page()) {
		wp_enqueue_script('sinofresh-hero-slider', get_template_directory_uri() . '/assets/js/hero-slider.js', array(), '1.0.0', true);
	}
});

add_editor_style('style.css');

/* Template-file authority guard.
   The Site Editor stores saved templates as wp_template posts in the DB and
   the DB then SHADOWS the theme files, which has twice swallowed our file
   edits (front-page/header). With this filter, whenever a matching template
   file exists on disk it always wins; DB copies are ignored. Remove this
   filter if you ever want to edit templates from the Site Editor again. */
add_filter('pre_get_block_template', function($pre, $id, $template_type) {
	if ($template_type !== 'wp_template' && $template_type !== 'wp_template_part') {
		return $pre;
	}
	$dir = get_stylesheet();
	if (!str_starts_with($id, $dir . '//')) {
		return $pre;
	}
	$slug = substr($id, strlen($dir) + 2);
	$base = $template_type === 'wp_template' ? 'templates' : 'parts';
	$file = get_stylesheet_directory() . "/{$base}/{$slug}.html";
	if (!file_exists($file)) {
		return $pre;
	}
	$tpl = new WP_Block_Template();
	$tpl->id = $id;
	$tpl->theme = $dir;
	$tpl->slug = $slug;
	$tpl->source = 'theme';
	$tpl->origin = 'theme';
	$tpl->type = $template_type;
	$tpl->wp_id = null;
	$tpl->title = ucfirst($slug);
	$tpl->description = '';
	$tpl->status = 'publish';
	$tpl->has_theme_file = true;
	$tpl->is_custom = false;
	$tpl->modified = null;
	$tpl->content = file_get_contents($file);
	return $tpl;
}, 10, 3);

/* Plural twin of the guard above. The front-end RENDERING path resolves
   templates through get_block_templates() (which merges wp_template posts
   from the DB) and never calls the singular pre_get_block_template filter —
   so a stale DB copy would still shadow the file. This filter rewrites any
   DB-sourced template back to its theme file whenever that file exists. */
add_filter('get_block_templates', function($templates, $query, $template_type) {
	if (!is_array($templates)
		|| ($template_type !== 'wp_template' && $template_type !== 'wp_template_part')) {
		return $templates;
	}
	$base = $template_type === 'wp_template' ? 'templates' : 'parts';
	foreach ($templates as $tpl) {
		if (isset($tpl->source) && $tpl->source === 'custom' && !empty($tpl->slug)) {
			$file = get_stylesheet_directory() . "/{$base}/{$tpl->slug}.html";
			if (file_exists($file)) {
				$tpl->content        = file_get_contents($file);
				$tpl->source         = 'theme';
				$tpl->origin         = 'theme';
				$tpl->has_theme_file = true;
			}
		}
	}
	return $templates;
}, 10, 3);


/**
 * Front-page motion (section reveal + stat count-up).
 *
 * Front page only: the counters live there, and the other templates are
 * reading pages where a reveal on every band would be noise. The script adds
 * its own opt-in classes, so nothing here hides content for a visitor without
 * JS. See assets/js/interactions.js.
 */
add_action('wp_enqueue_scripts', function() {
	if (is_front_page()) {
		wp_enqueue_script('sinofresh-interactions', get_template_directory_uri() . '/assets/js/interactions.js', array(), '1.1.0', true);
	}
});

add_action('wp_enqueue_scripts', function() {
	// Block theme template hierarchy resolves page-{slug}.html by page slug, which
	// does not set the wp_page_template meta — so check the page slug as well.
	$dosage_pages = ['soft-chews', 'tablets', 'powders', 'pastes', 'drops', 'liquids', 'fish-oil', 'dental-chews'];
	$is_dosage_page = is_page($dosage_pages) || is_page_template(array_map(fn($s) => "page-$s", $dosage_pages));
	if ($is_dosage_page) {
		wp_enqueue_style('sinofresh-configurator', get_template_directory_uri() . '/assets/css/configurator.css', array(), '2.3');
		wp_enqueue_script('sinofresh-configurator', get_template_directory_uri() . '/assets/js/configurator.js', array(), '1.7', true);
	}
});

/**
 * Related Articles on single posts (templates/single.html).
 *
 * The related block is a standalone Query Loop (inherit: false), so the
 * `$block->context['query']['inherit']` check does not match it. Two core
 * details shape this implementation:
 *
 *   1. `core/query` is a static block (supports.html === false), so its
 *      className (`sf-related-articles`) is NOT printed on the front end and
 *      cannot be read from the rendered markup.
 *   2. `query_loop_block_query_vars` is only fired from `core/query`'s children
 *      (core/post-template, core/query-no-results, pagination), which inherit
 *      `queryId` through block context — not from the query block itself.
 *
 * So the marked queryId is collected here first, and matched by context in the
 * filter below. Matching on queryId (instead of on a child's attributes) keeps
 * the exclusion consistent for the results list, the "no results" state and any
 * pagination added later.
 */
$sinofresh_related_query_ids = array();

add_filter('render_block_data', function($parsed_block) use (&$sinofresh_related_query_ids) {
	$attrs = isset($parsed_block['attrs']) ? (array) $parsed_block['attrs'] : array();
	if ('core/query' === (isset($parsed_block['blockName']) ? $parsed_block['blockName'] : '')
		&& isset($attrs['queryId'])
		&& isset($attrs['className'])
		&& false !== strpos((string) $attrs['className'], 'sf-related-articles')) {
		$sinofresh_related_query_ids[(int) $attrs['queryId']] = true;
	}
	return $parsed_block;
});

/**
 * Related Articles behaviour:
 *   1. the post being viewed is excluded from its own related list;
 *   2. the list is restricted to the viewed post's categories.
 * Set $sf_match_category to false to fall back to plain "latest posts".
 *
 * Front-end only — the editor preview renders through the REST API and is not
 * affected by this filter.
 */
add_filter('query_loop_block_query_vars', function($query, $block) use (&$sinofresh_related_query_ids) {
	$sf_match_category = true;

	if (!is_singular('post')) {
		return $query;
	}

	$query_id = isset($block->context['queryId']) ? (int) $block->context['queryId'] : 0;
	if (!$query_id || empty($sinofresh_related_query_ids[$query_id])) {
		return $query;
	}

	$post_id = (int) get_queried_object_id();
	if (!$post_id) {
		return $query;
	}

	$exclude = isset($query['post__not_in']) ? (array) $query['post__not_in'] : array();
	$query['post__not_in'] = array_values(array_unique(array_merge($exclude, array($post_id))));

	if ($sf_match_category) {
		$terms = wp_get_post_terms($post_id, 'category', array('fields' => 'ids'));
		if (!is_wp_error($terms) && !empty($terms)) {
			$query['tax_query'] = array(
				array(
					'taxonomy' => 'category',
					'field'    => 'term_id',
					'terms'    => array_map('intval', $terms),
				),
			);
		}
	}

	return $query;
}, 10, 2);

/**
 * FAQPage JSON-LD (schema.org) for pages whose template has a FAQ accordion.
 *
 * The accordion is built from core/details blocks in the theme template files,
 * so the schema is derived from the same source of truth: the current view's
 * template file is scanned for <details><summary>…</summary>…</details> pairs.
 * No SEO plugin on this site outputs FAQPage (checked: no Rank Math / Yoast),
 * and the guard below keeps it that way if one is ever activated.
 */
add_action('wp_head', function() {
	if (is_admin() || defined('REST_REQUEST')) {
		return;
	}
	// If an SEO plugin that emits FAQPage schema is ever installed, stand down.
	if (class_exists('RankMath') || defined('WPSEO_VERSION') || defined('RANK_MATH_VERSION')) {
		return;
	}

	// Resolve the template file for the current view (front page / page slug).
	if (is_front_page()) {
		$candidates = array('front-page');
	} elseif (is_page()) {
		$slug = get_post_field('post_name', get_queried_object_id());
		$candidates = $slug ? array("page-{$slug}", 'page') : array('page');
	} else {
		return;
	}
	$file = '';
	foreach ($candidates as $slug) {
		$try = get_stylesheet_directory() . "/templates/{$slug}.html";
		if (file_exists($try)) { $file = $try; break; }
	}
	if (!$file) {
		return;
	}
	$html = file_get_contents($file);

	// Extract <details> accordions: question = summary text, answer = inner text.
	if (!preg_match_all('/<details[^>]*>(.*?)<\/details>/s', $html, $items, PREG_SET_ORDER)) {
		return;
	}
	$entities = array();
	foreach ($items as $item) {
		if (!preg_match('/<summary>(.*?)<\/summary>/s', $item[1], $sum)) {
			continue;
		}
		$question = trim(str_replace('&nbsp;', ' ', wp_strip_all_tags($sum[1])));
		$answer   = trim(wp_strip_all_tags(preg_replace('/<summary>.*?<\/summary>/s', '', $item[1])));
		if ($question === '' || $answer === '') {
			continue;
		}
		$entities[] = array(
			'@type'          => 'Question',
			'name'           => $question,
			'acceptedAnswer' => array(
				'@type' => 'Answer',
				'text'  => $answer,
			),
		);
	}
	if (count($entities) < 2) {
		return;
	}
	$schema = array(
		'@context'   => 'https://schema.org',
		'@type'      => 'FAQPage',
		'mainEntity' => $entities,
	);
	echo "\n" . '<script type="application/ld+json">'
		. wp_json_encode($schema, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE)
		. "</script>\n";
}, 20);

/**
 * BreadcrumbList JSON-LD (schema.org) — derived from the same source of truth
 * as the visible nav: the current view's template file is scanned for the
 * .sf-breadcrumb <nav>. Same pattern as the FAQPage schema above. Skips the
 * front page and 404. Coexists via a separate <script> tag. Link hrefs are
 * rewritten with home_url() so the schema stays domain/language aware.
 * In single.html the current crumb is the {{TITLE}} placeholder, replaced
 * with the post title at runtime.
 */
/**
 * Visible breadcrumb: swap the {{TITLE}} placeholder in core/html blocks
 * (single.html / page.html nav) for the current post/page title. The schema
 * generator below already does the same replacement for JSON-LD; this covers
 * the visible nav, since wp:html content is otherwise printed verbatim.
 */
add_filter('render_block', function($block_content, $parsed_block) {
	if (is_admin() || defined('REST_REQUEST')) {
		return $block_content;
	}
	if (($parsed_block['blockName'] ?? '') === 'core/html'
		&& strpos($block_content, '{{TITLE}}') !== false) {
		$block_content = str_replace('{{TITLE}}', esc_html(get_the_title()), $block_content);
	}
	return $block_content;
}, 10, 2);

add_action('wp_head', function() {
	if (is_admin() || defined('REST_REQUEST') || is_front_page() || is_404()) {
		return;
	}
	// Resolve the template file for the current view (same rules as FAQPage).
	$html = '';
	if (is_front_page() || is_404()) {
		return;
	} elseif (is_singular('post')) {
		$candidates = array('single');
	} elseif (is_search()) {
		$candidates = array('search');
	} elseif (is_home()) {
		/* Blog listing: the visible breadcrumb lives in the shared
		   parts/blog-index.html part (home.html / page-blog.html only
		   include the part), so resolve the part file directly. */
		$part = get_stylesheet_directory() . '/parts/blog-index.html';
		if (file_exists($part)) {
			$html = file_get_contents($part);
		}
	} elseif (is_page()) {
		$slug = get_post_field('post_name', get_queried_object_id());
		$candidates = $slug ? array("page-{$slug}", 'page') : array('page');
	} else {
		return;
	}
	if ($html === '') {
		$file = '';
		foreach ($candidates as $slug) {
			$try = get_stylesheet_directory() . "/templates/{$slug}.html";
			if (file_exists($try)) { $file = $try; break; }
		}
		if (!$file) {
			return;
		}
		$html = file_get_contents($file);
	}
	if (!preg_match('/<nav class="sf-breadcrumb[^"]*"[^>]*>(.*?)<\/nav>/s', $html, $nav)) {
		return;
	}

	$items = array();
	$pos = 1;
	// Links: Home + middle levels (get an "item" URL).
	if (preg_match_all('/<a[^>]*class="sf-breadcrumb__crumb[^"]*"[^>]*href="([^"]*)"[^>]*>(.*?)<\/a>/s', $nav[1], $links, PREG_SET_ORDER)) {
		foreach ($links as $link) {
			$items[] = array(
				'@type' => 'ListItem',
				'position' => $pos,
				'name' => html_entity_decode(wp_strip_all_tags($link[2]), ENT_QUOTES, 'UTF-8'),
				'item' => home_url($link[1]),
			);
			$pos++;
		}
	}
	// Current page: no item URL. {{TITLE}} = dynamic post title.
	if (preg_match('/<span class="sf-breadcrumb__crumb sf-breadcrumb__current"[^>]*>(.*?)<\/span>/s', $nav[1], $cur)) {
		$name = html_entity_decode(trim(wp_strip_all_tags($cur[1])), ENT_QUOTES, 'UTF-8');
		if (strpos($name, '{{TITLE}}') !== false) {
			$name = get_the_title();
		}
		$items[] = array('@type' => 'ListItem', 'position' => $pos, 'name' => $name);
	}
	if (count($items) < 2) {
		return;
	}

	$schema = array(
		'@context'       => 'https://schema.org',
		'@type'          => 'BreadcrumbList',
		'itemListElement' => $items,
	);
	echo "\n" . '<script type="application/ld+json">'
		. wp_json_encode($schema, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE)
		. "</script>\n";
}, 21);

/* Site favicon (icon extracted from the SINO FRESH logo mark) */
add_action('wp_head', function () {
	$uri = get_template_directory_uri() . '/assets/images';
	echo '<link rel="icon" type="image/png" sizes="32x32" href="' . esc_url($uri . '/favicon-32.png') . '">' . "\n";
	echo '<link rel="icon" type="image/png" sizes="512x512" href="' . esc_url($uri . '/favicon.png') . '">' . "\n";
	echo '<link rel="apple-touch-icon" href="' . esc_url($uri . '/favicon.png') . '">' . "\n";
}, 2);

/**
 * Social links, editable by ops in the dashboard.
 *
 * Implemented with the core Settings API instead of ACF: ACF is not installed
 * on this site and its options-page feature is PRO-only, so a native page is
 * the most stable path (no plugin dependency). The templates carry
 * {{sf-social:network}} tokens inside the icon hrefs; the render_block filter
 * below swaps them for the saved URLs at render time. Unset networks fall
 * back to "#" so nothing ever renders an empty href.
 */
function sf_social_networks() {
	return array(
		'x'          => 'X (Twitter)',
		'youtube'    => 'YouTube',
		'wechat'     => 'WeChat',
		'instagram'  => 'Instagram',
		'tiktok'     => 'TikTok',
		'whatsapp'   => 'WhatsApp (e.g. https://wa.me/8613385397805)',
		'facebook'   => 'Facebook',
		'linkedin'   => 'LinkedIn',
	);
}

/**
 * Site Settings — the basics operations edit without touching code: contact
 * info (top bar + footer + Organization schema) and the certification badges.
 * Native Settings API, no ACF. Registered on admin_menu priority 9 so the
 * item lands above the Social Links menu below.
 */
function sf_site_settings_defaults() {
	return array(
		'sf_contact_email'    => 'info@zxpet.com',
		'sf_working_hours'    => 'Mon–Fri · 9:00–18:00 GMT+8',
		'sf_contact_phone'    => '+86 539 866 9539',
		'sf_contact_address'  => 'No. 22 Zhongshan Road B3, Yihe New District, Linyi, Shandong, China',
		'sf_contact_whatsapp' => '+86 133 8539 7805',
		'sf_copyright_company' => 'Shandong SINO FRESH Pet Food Co., Ltd.',
		'sf_copyright_suffix'  => 'All rights reserved.',
	);
}

function sf_default_certifications() {
	return array(
		array('name' => 'FDA', 'url' => '/quality/', 'active' => true),
		array('name' => 'cGMP', 'url' => '/quality/', 'active' => true),
		array('name' => 'ISO 9001', 'url' => '/quality/', 'active' => true),
		array('name' => 'ISO 22000', 'url' => '/quality/', 'active' => true),
		array('name' => '', 'url' => '', 'active' => false),
		array('name' => '', 'url' => '', 'active' => false),
		array('name' => '', 'url' => '', 'active' => false),
		array('name' => '', 'url' => '', 'active' => false),
	);
}

add_action('admin_menu', function () {
	add_menu_page(
		'Site Settings',
		'Site Settings',
		'manage_options',
		'sf-site-settings',
		'sf_render_site_settings_page',
		'dashicons-admin-settings',
		25 // just above Social Links (26), keeping the two settings pages together
	);
}, 9);

add_action('admin_init', function () {
	$d = sf_site_settings_defaults();
	// Clearing a field would blank the top bar / footer, so an empty submit
	// falls back to the shipped default instead of storing "".
	$text_fields = array('sf_working_hours', 'sf_contact_phone', 'sf_contact_address', 'sf_contact_whatsapp', 'sf_copyright_company', 'sf_copyright_suffix');
	foreach ($text_fields as $key) {
		register_setting('sf_site_settings', $key, array(
			'type'              => 'string',
			'sanitize_callback' => function ($v) use ($d, $key) {
				$v = sanitize_text_field($v);
				return ($v !== '') ? $v : $d[$key];
			},
		));
	}
	register_setting('sf_site_settings', 'sf_contact_email', array(
		'type'              => 'string',
		'sanitize_callback' => function ($v) {
			$v = sanitize_email($v);
			return ($v !== '') ? $v : 'info@zxpet.com';
		},
	));
	register_setting('sf_site_settings', 'sf_certifications', array(
		'type'              => 'array',
		'sanitize_callback' => function ($v) {
			$out = array();
			for ($i = 0; $i < 8; $i++) {
				$row = (isset($v[$i]) && is_array($v[$i])) ? $v[$i] : array();
				$out[$i] = array(
					'name'   => isset($row['name']) ? sanitize_text_field($row['name']) : '',
					'url'    => isset($row['url']) ? esc_url_raw($row['url']) : '',
					'active' => !empty($row['active']),
				);
			}
			return $out;
		},
	));
});

function sf_render_site_settings_page() {
	if (!current_user_can('manage_options')) {
		return;
	}
	$d     = sf_site_settings_defaults();
	$email = get_option('sf_contact_email', $d['sf_contact_email']);
	$hours = get_option('sf_working_hours', $d['sf_working_hours']);
	$phone = get_option('sf_contact_phone', $d['sf_contact_phone']);
	$addr  = get_option('sf_contact_address', $d['sf_contact_address']);
	$wa    = get_option('sf_contact_whatsapp', $d['sf_contact_whatsapp']);
	$certs = get_option('sf_certifications', sf_default_certifications());
	$co_company = get_option('sf_copyright_company', $d['sf_copyright_company']);
	$co_suffix  = get_option('sf_copyright_suffix', $d['sf_copyright_suffix']);
	?>
	<div class="wrap">
		<h1>Site Settings</h1>
		<p>Basics shown in the top bar, the footer and the Organization schema. Clearing a field restores its default.</p>
		<form method="post" action="options.php">
			<?php settings_fields('sf_site_settings'); ?>
			<h2 class="title">Contact Information</h2>
			<table class="form-table" role="presentation">
				<tr>
					<th scope="row"><label for="sf_email">Email</label></th>
					<td><input name="sf_contact_email" id="sf_email" type="email" class="regular-text" value="<?php echo esc_attr($email); ?>"></td>
				</tr>
				<tr>
					<th scope="row"><label for="sf_hours">Working Hours</label></th>
					<td><input name="sf_working_hours" id="sf_hours" type="text" class="regular-text" value="<?php echo esc_attr($hours); ?>"></td>
				</tr>
				<tr>
					<th scope="row"><label for="sf_phone">Phone</label></th>
					<td><input name="sf_contact_phone" id="sf_phone" type="text" class="regular-text" value="<?php echo esc_attr($phone); ?>">
					<p class="description">Shown in the footer; the tel: link is built from this number automatically.</p></td>
				</tr>
				<tr>
					<th scope="row"><label for="sf_wa">WhatsApp</label></th>
					<td><input name="sf_contact_whatsapp" id="sf_wa" type="text" class="regular-text" value="<?php echo esc_attr($wa); ?>">
					<p class="description">Shown in the footer; the wa.me link is built from this number automatically.</p></td>
				</tr>
				<tr>
					<th scope="row"><label for="sf_addr">Address</label></th>
					<td><input name="sf_contact_address" id="sf_addr" type="text" class="large-text" value="<?php echo esc_attr($addr); ?>">
					<p class="description">Shown in the footer and in the Organization schema (streetAddress).</p></td>
				</tr>
			</table>
			<h2 class="title">Certifications</h2>
			<p>Top-bar badges, in order. Leave the name empty to free a slot; “Active” hides the badge without deleting it. A badge with a URL becomes a link.</p>
			<table class="form-table" role="presentation">
				<thead><tr><th>#</th><th>Name</th><th>URL (optional)</th><th>Active</th></tr></thead>
				<tbody>
				<?php for ($i = 0; $i < 8; $i++) :
					$c = isset($certs[$i]) && is_array($certs[$i]) ? $certs[$i] : array('name' => '', 'url' => '', 'active' => false); ?>
				<tr>
					<td><?php echo (int) ($i + 1); ?></td>
					<td><input name="sf_certifications[<?php echo $i; ?>][name]" type="text" class="regular-text" value="<?php echo esc_attr($c['name']); ?>"></td>
					<td><input name="sf_certifications[<?php echo $i; ?>][url]" type="text" class="regular-text" value="<?php echo esc_attr($c['url']); ?>"></td>
					<td><input name="sf_certifications[<?php echo $i; ?>][active]" type="checkbox" value="1" <?php checked(!empty($c['active'])); ?>></td>
				</tr>
				<?php endfor; ?>
				</tbody>
			</table>
			<h2 class="title">Copyright</h2>
			<p>Footer legal line, rendered as “© {year} {company} {suffix}”. The year is generated automatically and rolls over on January 1.</p>
			<table class="form-table" role="presentation">
				<tr>
					<th scope="row"><label for="sf_copyright_company">Company Name</label></th>
					<td><input name="sf_copyright_company" id="sf_copyright_company" type="text" class="large-text" value="<?php echo esc_attr($co_company); ?>">
					<p class="description">The legal company name shown after the © symbol.</p></td>
				</tr>
				<tr>
					<th scope="row"><label for="sf_copyright_suffix">Suffix Text</label></th>
					<td><input name="sf_copyright_suffix" id="sf_copyright_suffix" type="text" class="large-text" value="<?php echo esc_attr($co_suffix); ?>">
					<p class="description">The text after the company name, e.g. “All rights reserved.”</p></td>
				</tr>
			</table>
			<?php submit_button(); ?>
		</form>
	</div>
	<?php
}

/**
 * {{sf-certifications}} — pill badges for the active rows. A row with a URL
 * renders as a link (hover turns brand green), without one as a plain pill.
 */
function sf_render_cert_badges() {
	$certs = get_option('sf_certifications', sf_default_certifications());
	$html  = '';
	foreach ($certs as $c) {
		if (empty($c['active']) || !isset($c['name']) || trim((string) $c['name']) === '') {
			continue;
		}
		$name = esc_html($c['name']);
		$url  = esc_url((string) $c['url']);
		$html .= $url
			? '<a href="' . $url . '" class="sf-cert-badge">' . $name . '</a>'
			: '<span class="sf-cert-badge">' . $name . '</span>';
	}
	return $html;
}

/* Site-settings tokens for the rendered blocks: {{sf-email}} {{sf-hours}}
   {{sf-phone}} {{sf-phone-tel}} {{sf-address}} {{sf-whatsapp}}
   {{sf-whatsapp-link}} {{sf-certifications}}. Runs at the same priority as
   the social-links replacer below; token names do not overlap. */
add_filter('render_block', function ($block_content, $parsed_block) {
	if (!is_string($block_content) || strpos($block_content, '{{sf-') === false) {
		return $block_content;
	}
	$d      = sf_site_settings_defaults();
	$phone  = get_option('sf_contact_phone', $d['sf_contact_phone']);
	$wa     = get_option('sf_contact_whatsapp', $d['sf_contact_whatsapp']);
	$map    = array(
		'{{sf-email}}'         => esc_attr(get_option('sf_contact_email', $d['sf_contact_email'])),
		'{{sf-hours}}'         => esc_html(get_option('sf_working_hours', $d['sf_working_hours'])),
		'{{sf-phone}}'         => esc_html($phone),
		'{{sf-phone-tel}}'     => esc_attr('tel:' . preg_replace('/[^+0-9]/', '', $phone)),
		'{{sf-address}}'       => esc_html(get_option('sf_contact_address', $d['sf_contact_address'])),
		'{{sf-whatsapp}}'      => esc_html($wa),
		'{{sf-whatsapp-link}}' => esc_url('https://wa.me/' . preg_replace('/[^0-9]/', '', $wa)),
		'{{sf-copyright-year}}'   => esc_html(date('Y')),
		'{{sf-copyright-company}}' => esc_html(get_option('sf_copyright_company', $d['sf_copyright_company'])),
		'{{sf-copyright-suffix}}' => esc_html(get_option('sf_copyright_suffix', $d['sf_copyright_suffix'])),
	);
	$block_content = str_replace(array_keys($map), array_values($map), $block_content);
	if (strpos($block_content, '{{sf-certifications}}') !== false) {
		$block_content = str_replace('{{sf-certifications}}', sf_render_cert_badges(), $block_content);
	}
	return $block_content;
}, 20, 2);

add_action('admin_menu', function () {
	add_menu_page(
		'Social Media Links',
		'Social Links',
		'manage_options',
		'social-links',
		function () {
			if (!current_user_can('manage_options')) {
				return;
			}
			$links = get_option('sf_social_links', array());
			?>
			<div class="wrap">
				<h1>Social Media Links</h1>
				<p>Fill in the profile URLs below. The footer icons update automatically — leave a field empty (or “#”) to keep the icon pointing to “#”.</p>
				<form method="post" action="options.php">
					<?php settings_fields('sf_social_links_group'); ?>
					<table class="form-table" role="presentation">
						<?php foreach (sf_social_networks() as $key => $label) : ?>
							<tr>
								<th scope="row"><label for="sf_social_<?php echo esc_attr($key); ?>"><?php echo esc_html($label); ?></label></th>
								<td>
									<input type="text" class="regular-text code" id="sf_social_<?php echo esc_attr($key); ?>"
										name="sf_social_links[<?php echo esc_attr($key); ?>]"
										value="<?php echo esc_attr(isset($links[$key]) ? $links[$key] : '#'); ?>"
										placeholder="https:// … (leave empty for none)"
										spellcheck="false" autocomplete="off" />
								</td>
							</tr>
						<?php endforeach; ?>
					</table>
					<?php submit_button(); ?>
				</form>
			</div>
			<?php
		},
		'dashicons-share',
		26
	);
});

add_action('admin_init', function () {
	register_setting('sf_social_links_group', 'sf_social_links', array(
		'type'              => 'array',
		'sanitize_callback' => function ($in) {
			$out = array();
			foreach (sf_social_networks() as $key => $label) {
				$v = isset($in[$key]) ? trim(wp_unslash((string) $in[$key])) : '';
				if ($v === '' || $v === '#') {
					$out[$key] = '#';
					continue;
				}
				$esc = esc_url_raw($v);
				// accept http(s) URLs only — anything else (garbage, scheme-less
				// text, javascript:) degrades to "#"
				$scheme = $esc ? parse_url($esc, PHP_URL_SCHEME) : false;
				$out[$key] = ($esc && in_array($scheme, array('http', 'https'), true)) ? $esc : '#';
			}
			return $out;
		},
		'default'           => array_fill_keys(array_keys(sf_social_networks()), '#'),
	));
});

/* Swap {{sf-social:network}} tokens in rendered blocks for the configured URLs. */
add_filter('render_block', function ($block_content, $parsed_block) {
	if (is_admin() || defined('REST_REQUEST')) {
		return $block_content;
	}
	if (is_string($block_content) && strpos($block_content, '{{sf-social:') === false) {
		return $block_content;
	}
	return preg_replace_callback('/\{\{sf-social:([a-z0-9_-]+)\}\}/', function ($m) {
		$links = get_option('sf_social_links', array());
		// esc_url FIRST: a stored value with a bad scheme must fall back to
		// "#", never to an empty href.
		$url = esc_url(trim((string) (isset($links[$m[1]]) ? $links[$m[1]] : '')));
		if ($url === '') {
			$url = '#';
		}
		return $url;
	}, $block_content);
}, 20, 2);


/**
 * Product JSON-LD (schema.org) for the eight dosage-form landing pages.
 * Data is parsed from the same template file that renders the page (single
 * source of truth, same pattern as the FAQPage schema): name = hero <h1>,
 * description = hero subtitle, image = hero figure, additionalProperty =
 * the Specifications rows (sf-spec-list, with a fallback parser for the
 * legacy key-facts table). Pages outside the dosage list output nothing;
 * coexists with FAQPage / BreadcrumbList as separate <script> tags.
 */
add_action('wp_head', function () {
	if (is_admin() || defined('REST_REQUEST') || !is_page()) {
		return;
	}
	$dosage_slugs = array('soft-chews', 'tablets', 'powders', 'pastes', 'drops', 'liquids', 'fish-oil', 'dental-chews');
	$slug = get_post_field('post_name', get_queried_object_id());
	if (!$slug || !in_array($slug, $dosage_slugs, true)) {
		return;
	}
	$file = get_stylesheet_directory() . "/templates/page-{$slug}.html";
	if (!file_exists($file)) {
		return;
	}
	$html = file_get_contents($file);

	// name: hero <h1>
	if (!preg_match('/<h1[^>]*>(.*?)<\/h1>/s', $html, $h1)) {
		return;
	}
	$name = html_entity_decode(trim(wp_strip_all_tags($h1[1])), ENT_QUOTES, 'UTF-8');

	// description: hero subtitle (first 18px card-white paragraph)
	$description = '';
	if (preg_match('/<p class="has-card-white-color[^"]*"[^>]*font-size:18px[^>]*>(.*?)<\/p>/s', $html, $d)) {
		$description = html_entity_decode(trim(wp_strip_all_tags($d[1])), ENT_QUOTES, 'UTF-8');
	}

	// image: first <img> in the file (the hero figure) — make absolute
	$image = '';
	if (preg_match('/<img src="([^"]+)"/', $html, $im)) {
		$image = esc_url_raw(home_url($im[1]));
	}

	// additionalProperty: spec rows — sf-spec-list first, legacy table fallback
	$props = array();
	if (preg_match_all('/<span class="sf-spec-term">([^<]+)<\/span><span class="sf-spec-value">([^<]+)<\/span>/', $html, $rows, PREG_SET_ORDER)) {
		foreach ($rows as $r) {
			$props[] = array('@type' => 'PropertyValue', 'name' => html_entity_decode(trim($r[1]), ENT_QUOTES, 'UTF-8'), 'value' => html_entity_decode(trim($r[2]), ENT_QUOTES, 'UTF-8'));
		}
	} elseif (preg_match_all('/flex-basis:35%">\s*<!-- wp:paragraph[^>]*-->\s*<p[^>]*>([^<]+)<\/p>.*?<p class="has-primary-color has-text-color"[^>]*>([^<]+)<\/p>/s', $html, $rows, PREG_SET_ORDER)) {
		foreach ($rows as $r) {
			$props[] = array('@type' => 'PropertyValue', 'name' => html_entity_decode(trim($r[1]), ENT_QUOTES, 'UTF-8'), 'value' => html_entity_decode(trim($r[2]), ENT_QUOTES, 'UTF-8'));
		}
	}

	$schema = array(
		'@context'      => 'https://schema.org',
		'@type'         => 'Product',
		'name'          => $name,
		'description'   => $description,
		'image'         => $image,
		'brand'         => array('@type' => 'Brand', 'name' => 'SINO FRESH'),
		'manufacturer'  => array('@type' => 'Organization', 'name' => 'Shandong SINO FRESH Pet Food Co., Ltd.'),
		'category'      => 'Pet Supplements',
	);
	if ($props) {
		$schema['additionalProperty'] = $props;
	}
	echo "\n" . '<script type="application/ld+json">'
		. wp_json_encode($schema, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE)
		. "</script>\n";
}, 21);

/**
 * Organization JSON-LD (schema.org) — once, site-wide. sameAs is built from
 * the Social Links settings (only real http(s) URLs; "#" placeholders are
 * skipped), and the logo points at the configured Site Logo attachment, so
 * both follow whatever operations configure in wp-admin.
 */
add_action('wp_head', function () {
	if (is_admin() || defined('REST_REQUEST') || is_404()) {
		return;
	}
	$same_as = array();
	foreach (sf_social_networks() as $key => $label) {
		$links = get_option('sf_social_links', array());
		$url = esc_url_raw(trim((string) (isset($links[$key]) ? $links[$key] : '')));
		$scheme = $url ? parse_url($url, PHP_URL_SCHEME) : false;
		if ($url && in_array($scheme, array('http', 'https'), true)) {
			$same_as[] = $url;
		}
	}

	$logo = '';
	$logo_id = (int) get_theme_mod('custom_logo');
	if ($logo_id) {
		$logo = wp_get_attachment_url($logo_id);
	}

	$schema = array(
		'@context'     => 'https://schema.org',
		'@type'        => 'Organization',
		'name'         => 'Shandong SINO FRESH Pet Food Co., Ltd.',
		'alternateName' => 'SINO FRESH',
		'url'          => home_url('/'),
		'email'        => get_option('sf_contact_email', 'info@zxpet.com'),
		'telephone'    => get_option('sf_contact_phone', '+86 539 866 9539'),
		'address'      => array(
			'@type'            => 'PostalAddress',
			'streetAddress'    => get_option('sf_contact_address', 'No. 22 Zhongshan Road B3, Yihe New District, Linyi, Shandong, China'),
			'addressLocality'  => 'Linyi',
			'addressRegion'    => 'Shandong',
			'addressCountry'   => 'CN',
		),
	);
	// Export markets (placeholder list confirmed 2026-09-16; replace with real
	// export data when available). Kept in sync with the front-page map block.
	$schema['areaServed'] = array_map(function ($name) {
		return array('@type' => 'Country', 'name' => $name);
	}, array(
		// North America
		'United States', 'Canada', 'Mexico',
		// Europe
		'United Kingdom', 'Germany', 'France', 'Netherlands', 'Belgium', 'Spain',
		'Italy', 'Portugal', 'Ireland', 'Denmark', 'Sweden', 'Norway', 'Finland',
		'Poland', 'Czech Republic', 'Austria', 'Switzerland',
		// Oceania & Asia
		'Australia', 'New Zealand', 'Japan', 'South Korea', 'Singapore', 'Malaysia',
		'Thailand', 'Vietnam', 'Indonesia', 'Philippines', 'India',
		'United Arab Emirates', 'Saudi Arabia',
	));
	if ($logo) {
		$schema['logo'] = $logo;
	}
	if ($same_as) {
		$schema['sameAs'] = $same_as;
	}
	echo "\n" . '<script type="application/ld+json">'
		. wp_json_encode($schema, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE)
		. "</script>\n";
}, 22);

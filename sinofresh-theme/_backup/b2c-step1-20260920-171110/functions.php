<?php
/* Configurator PDF summary endpoint (POST /wp-json/sinofresh/v1/config-pdf).
   Dompdf itself lives in wp-content/vendor/ — LAUNCH CHECKLIST: vendor/ must
   be shipped with the site or the endpoint answers 503. */
require get_template_directory() . '/inc/config-pdf.php';

/* Gated certificate downloads (GET /wp-json/sinofresh/v1/cert-download).
   Full-resolution certificates live outside the document root — see
   SF_CERTS_DIR in inc/cert-download.php for the production path. */
require get_template_directory() . '/inc/cert-download.php';

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
	wp_enqueue_style('sinofresh-style', get_stylesheet_uri(), array(), '2.10.41');
	// Sticky nav: every template renders parts/header.html, so this is site-wide.
	wp_enqueue_script('sinofresh-sticky-header', get_template_directory_uri() . '/assets/js/sticky-header.js', array(), '1.0.0', true);
	wp_enqueue_script('sinofresh-ui-components', get_template_directory_uri() . '/assets/js/ui-components.js', array(), '1.0.0', true);
	// Mobile nav: collapse the overlay's submenus until their chevron is tapped.
	wp_enqueue_script('sinofresh-mobile-nav', get_template_directory_uri() . '/assets/js/mobile-nav.js', array(), '1.1.0', true);
	// Inquiry basket storage API + header bag/badge/drawer UI — global by design.
	wp_enqueue_script('sinofresh-basket', get_template_directory_uri() . '/assets/js/basket.js', array(), '1.3.0', true);
	// Quote CTA smart scroll: in-page form -> smooth scroll, else native /contact/#quote.
	wp_enqueue_script('sinofresh-quote-cta', get_template_directory_uri() . '/assets/js/quote-cta.js', array(), '1.0.0', true);
	// On-this-page TOC (dot rail on marketing pages, text list on articles) +
	// article extras (progress bar, inline CTA, feedback, print URL). The JS
	// self-selects its mode: body.single-post gets the article feature set,
	// marketing pages keep the dot rail. JS no-ops with < 3 H2s for the TOC.
	if (is_front_page() || is_page(array('quality', 'about', 'services', 'factory-tour', 'soft-chews', 'tablets', 'powders', 'pastes', 'drops', 'liquids', 'fish-oil', 'dental-chews')) || is_singular('post')) {
		wp_enqueue_script('sinofresh-toc-nav', get_template_directory_uri() . '/assets/js/toc-nav.js', array(), '2.0.0', true);
	}
	if (is_front_page()) {
		wp_enqueue_script('sinofresh-hero-slider', get_template_directory_uri() . '/assets/js/hero-slider.js', array(), '1.1.1', true);
	}
});

add_editor_style('style.css');

/* :has() capability probe — must run before first paint so the legacy
   fallback styles (style.css section 30) apply without a flash. Plain ES5:
   the engines this targets are precisely the ones without modern syntax.
   Engines that fail CSS.supports('selector(:has(*))') get html.no-has and
   the mobile layout degrades to plain single-column flow. */
add_action('wp_head', function() {
	echo '<script>(function(){var ok=false;try{ok=!!(window.CSS&&CSS.supports&&CSS.supports("selector(:has(*))"));}catch(e){}if(!ok){document.documentElement.className+=" no-has";}})();</script>' . "\n";
}, 1);

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
		wp_enqueue_script('sinofresh-interactions', get_template_directory_uri() . '/assets/js/interactions.js', array(), '1.2.0', true);
	}
});

/**
 * About page (templates/page-about.html).
 *
 * Our Journey reveal, plus the video poster and the factory lightbox — none of
 * it is needed anywhere else, so the file is loaded on this page only.
 */
add_action('wp_enqueue_scripts', function() {
	if (is_page('about') || is_page_template('page-about')) {
		wp_enqueue_script('sinofresh-about', get_template_directory_uri() . '/assets/js/about.js', array(), '1.3.0', true);
	}
});

/**
 * Certificate viewer on the Quality page (templates/page-quality.html).
 *
 * The certificate thumbnails were anchors that opened the full scan in a new
 * tab. This swaps that for the lightbox the About page already uses — same
 * .sf-lb markup and stylesheet rules, so the component needs no new CSS. The
 * anchors are left in place as the no-JS fallback, so the file is Quality-only.
 */
add_action('wp_enqueue_scripts', function() {
	if (is_page('quality') || is_page_template('page-quality')) {
		wp_enqueue_script('sinofresh-quality', get_template_directory_uri() . '/assets/js/quality.js', array(), '1.1.0', true);
	}
});

/**
 * Certificate request modal (B4) — same page, separate file.
 *
 * quality.js returns early unless the certificate strip exists, so keeping
 * the modal in its own file means the two fail independently. The dialog is
 * marked up in the template (so Form 5 is server-rendered and the pair
 * degrades predictably) and this script only opens, fills and closes it.
 */
add_action('wp_enqueue_scripts', function() {
	if (is_page('quality') || is_page_template('page-quality')) {
		wp_enqueue_script('sinofresh-cert-modal', get_template_directory_uri() . '/assets/js/cert-modal.js', array(), '1.2.0', true);
	}
});

add_action('wp_enqueue_scripts', function() {
	// Block theme template hierarchy resolves page-{slug}.html by page slug, which
	// does not set the wp_page_template meta — so check the page slug as well.
	$dosage_pages = ['soft-chews', 'tablets', 'powders', 'pastes', 'drops', 'liquids', 'fish-oil', 'dental-chews'];
	$is_dosage_page = is_page($dosage_pages) || is_page_template(array_map(fn($s) => "page-$s", $dosage_pages));
	if ($is_dosage_page) {
		wp_enqueue_style('sinofresh-configurator', get_template_directory_uri() . '/assets/css/configurator.css', array(), '2.9');
		wp_enqueue_script('sinofresh-configurator', get_template_directory_uri() . '/assets/js/configurator.js', array(), '2.3', true);
		// Standard Formulas accordion CTAs: copy formula name + scroll to configurator.
		wp_enqueue_script('sinofresh-formulas', get_template_directory_uri() . '/assets/js/formulas.js', array(), '1.0.0', true);
	}
});

/**
 * [sf_explore_chips] — "Explore more dosage forms" cross-sell chips.
 *
 * Sits at the end of the configurator options column on the 8 dosage page
 * templates. Every published child of the Products page (ID 19) is listed
 * in menu_order, so a dosage form added later shows up here automatically
 * without touching a template. The current page stays in the row tagged
 * with aria-current, which keeps the row reading as the full range of
 * forms while marking where the visitor already is.
 *
 * Shortcodes run through do_shortcode() inside get_the_block_template_html()
 * before blocks are parsed, so this works inside the templates' wp:html
 * blocks with no template restructuring.
 */
function sinofresh_explore_chips() {
	$pages = get_pages(array(
		'parent'      => 19,          // Products
		'post_status' => 'publish',
		'sort_column' => 'menu_order',
		'sort_order'  => 'ASC',
	));
	if (!$pages) {
		return '';
	}

	$current_id = (int) get_queried_object_id();
	$chips      = '';
	foreach ($pages as $page) {
		$is_current = (int) $page->ID === $current_id;
		$chips     .= sprintf(
			'<a class="sf-explore__chip%s" href="%s"%s>%s</a>',
			$is_current ? ' is-current' : '',
			esc_url(get_permalink($page)),
			$is_current ? ' aria-current="page"' : '',
			esc_html(get_the_title($page))
		);
	}

	return '<nav class="sf-explore__chips" aria-label="Explore dosage forms">' . $chips . '</nav>';
}
add_shortcode('sf_explore_chips', 'sinofresh_explore_chips');

/**
 * Archive post count (templates/archive.html hero).
 *
 * Block templates run do_shortcode() before do_blocks(), so a raw shortcode
 * inside a wp:html block resolves in templates without extra wiring.
 */
add_shortcode('sf_archive_count', function () {
	global $wp_query;
	$found = isset($wp_query->found_posts) ? (int) $wp_query->found_posts : 0;
	/* translators: %d: number of articles. */
	return esc_html(sprintf(_n('%d article', '%d articles', $found, 'sinofresh'), $found));
});

/**
 * [sf_blog_chips] — blog filter chips, shared by /blog/ and the archive
 * templates (category / tag / date / author / search).
 *
 * Extracted from the five hand-written wp:button blocks in parts/blog-index.html
 * so visitors can switch sections directly from an archive page instead of
 * walking back to /blog/ first. The active chip is decided from the current
 * query (All is the fallback everywhere else), and every chip DOM mirrors the
 * previous rendered output 1:1 — same wp-block-button wrapper, same has-*
 * color classes (which resolve to the theme.json palette variables) and same
 * inline pill styling — so hover, focus and touch behaviour carry over
 * unchanged.
 *
 * The container self-styles its flex layout: the old wp:buttons block relied
 * on a per-instance generated hash class (wp-container-core-buttons-is-layout-…)
 * that a shortcode cannot reproduce. Body carries the sf-blog-chips class so
 * style.css 36a's phone chip-rail rules can target /blog/ and archives with
 * one selector. Shortcodes run inside get_the_block_template_html() before
 * do_blocks(), so a wp:shortcode block in a template or part is enough.
 */
function sinofresh_blog_chips() {
	$active = 'all';
	if (is_category('manufacturing')) {
		$active = 'manufacturing';
	} elseif (is_category('private-label')) {
		$active = 'private-label';
	} elseif (is_category('case-studies')) {
		$active = 'case-studies';
	} elseif (is_tag('formulation')) {
		$active = 'formulation';
	}

	$chips = array(
		'all'           => array('All',           '/blog/'),
		'manufacturing' => array('Manufacturing', '/category/manufacturing/'),
		'private-label' => array('Private Label', '/category/private-label/'),
		'case-studies'  => array('Case Studies',  '/category/case-studies/'),
		'formulation'   => array('Formulation',   '/tag/formulation/'),
	);

	/* inline pill styling shared by every chip (1:1 with the retired blocks) */
	$style = 'border-radius:999px;padding-top:10px;padding-right:22px;padding-bottom:10px;padding-left:22px;font-size:14px;font-weight:600';

	$out = '<div class="wp-block-buttons sf-blog-chips" style="display:flex;flex-wrap:wrap;justify-content:center;gap:var(--wp--preset--spacing--20)">';
	foreach ($chips as $key => $chip) {
		$is_active = ($key === $active);
		/* color classes only: active = primary bg + white text, inactive = bg-light bg + primary text */
		$classes = $is_active
			? 'has-card-white-color has-primary-background-color has-text-color has-background has-custom-font-size wp-element-button'
			: 'has-primary-color has-bg-light-background-color has-text-color has-background has-custom-font-size wp-element-button';
		$out .= sprintf(
			'<div class="wp-block-button"><a class="wp-block-button__link %1$s" style="%2$s" href="%3$s"%4$s>%5$s</a></div>',
			$classes,
			$style,
			esc_url($chip[1]),
			$is_active ? ' aria-current="page"' : '',
			esc_html($chip[0])
		);
	}
	return $out . '</div>';
}
add_shortcode('sf_blog_chips', 'sinofresh_blog_chips');

/* =========================================================================
 * Formula CPT (batch 2A) — sf_formula + 2 taxonomies + 4 meta + grid shortcode
 * -------------------------------------------------------------------------
 * Backing store for the Standard Formulas cards. The eight dosage pages still
 * hard-code 21 <details> blocks plus a hand-written ItemList; batch 2B/2C
 * replace those with [sf_formula_grid] fed by this post type, so nothing here
 * is wired into a template yet.
 *
 * Registration runs on `init` at priority 9, so the types exist before
 * anything queries them; the rewrite guard sits at priority 99, after every
 * permastruct has been added.
 * ========================================================================= */

/**
 * Registers the sf_formula post type, its two taxonomies and its four meta
 * fields.
 *
 * sf_formula_form — dosage form. The term slug MUST equal the dosage page slug
 *   (soft-chews, tablets, …): the {{FORM_HREF}} placeholder resolves to
 *   /products/<slug>/ and [sf_formula_grid] filters on it. public → false, so
 *   terms get no front-end archive and the dosage pages stay the only
 *   browsable entry point.
 * sf_formula_use — functional claim shown as the card eyebrow. Cross-dosage-
 *   form by design (Joint care appears on soft chews, liquids and tablets).
 *
 * The four meta keys carry no leading underscore, so they stay visible in the
 * built-in Custom Fields panel — the same editing route sf_last_reviewed uses.
 * These are the theme's first register_post_meta() calls.
 */
function sinofresh_register_formula_types() {
	register_post_type('sf_formula', array(
		'labels'             => array(
			'name'               => 'Formulas',
			'singular_name'      => 'Formula',
			'menu_name'          => 'Formulas',
			'add_new'            => 'Add New',
			'add_new_item'       => 'Add New Formula',
			'edit_item'          => 'Edit Formula',
			'new_item'           => 'New Formula',
			'view_item'          => 'View Formula',
			'view_items'         => 'View Formulas',
			'all_items'          => 'All Formulas',
			'search_items'       => 'Search Formulas',
			'not_found'          => 'No formulas found.',
			'not_found_in_trash' => 'No formulas found in Trash.',
		),
		'description'        => 'Standard formulas rendered as cards by [sf_formula_grid].',
		'public'             => true,
		'has_archive'        => true,
		'menu_icon'          => 'dashicons-clipboard',
		'menu_position'      => 21,   // measured free: Pages = 20, Comments = 25
		'supports'           => array('title', 'editor', 'thumbnail', 'excerpt', 'revisions', 'page-attributes', 'custom-fields'),
		'taxonomies'         => array('sf_formula_form', 'sf_formula_use'),
		'rewrite'            => array('slug' => 'formulas', 'with_front' => false),
		'show_in_rest'       => true,
		'hierarchical'       => false,
	));

	register_taxonomy('sf_formula_form', 'sf_formula', array(
		'labels'             => array(
			'name'          => 'Dosage Forms',
			'singular_name' => 'Dosage Form',
			'menu_name'     => 'Dosage Forms',
			'all_items'     => 'All Dosage Forms',
			'add_new_item'  => 'Add New Dosage Form',
			'edit_item'     => 'Edit Dosage Form',
			'search_items'  => 'Search Dosage Forms',
		),
		'description'        => 'Dosage form this formula belongs to. The term slug must match the dosage page slug.',
		'hierarchical'       => false,
		'public'             => false,   // no front-end archive for terms
		'publicly_queryable' => false,
		'show_ui'            => true,
		'show_in_rest'       => true,
		'rewrite'            => false,
	));

	register_taxonomy('sf_formula_use', 'sf_formula', array(
		'labels'             => array(
			'name'          => 'Functions',
			'singular_name' => 'Function',
			'menu_name'     => 'Functions',
			'all_items'     => 'All Functions',
			'add_new_item'  => 'Add New Function',
			'edit_item'     => 'Edit Function',
			'search_items'  => 'Search Functions',
		),
		'description'        => 'Functional claim shown as the card eyebrow, e.g. Joint care.',
		'hierarchical'       => false,
		'public'             => false,
		'publicly_queryable' => false,
		'show_ui'            => true,
		'show_in_rest'       => true,
		'rewrite'            => false,
	));

	foreach (array(
		'sf_formula_ingredients' => 'Ingredients list for the formula detail page.',
		'sf_formula_analysis'    => 'Guaranteed Analysis figures for the formula detail page.',
		'sf_formula_specs'       => 'Standard Specs line shown on the card.',
		'sf_formula_source'      => 'Admin-only note recording where this record was migrated from.',
	) as $key => $desc) {
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
}
add_action('init', 'sinofresh_register_formula_types', 9);

/**
 * One-time rewrite flush for the sf_formula permastruct.
 *
 * Nothing on this site hooks after_switch_theme — a dump of
 * $wp_filter['after_switch_theme'] holds only core's _wp_menus_changed and
 * _wp_sidebars_changed — so "flush on theme activation" would never run and
 * /formulas/<slug>/ would 404 forever. This replaces it.
 *
 * The guard reads the stored rules back instead of latching a version flag.
 * flush_rules() defers the real work to wp_loaded, so a flag written at init
 * could latch "done" on a request that then died before the rules were saved,
 * leaving a permanent 404 with no retry. Keying off the rules themselves is
 * self-healing: the flush repeats until a sf_formula route is actually stored,
 * then stops.
 *
 * flush_rewrite_rules(false) is the soft variant — the deferred flush returns
 * before save_mod_rewrite_rules(), which is right for nginx (nothing on this
 * host reads .htaccess).
 */
function sinofresh_formula_flush_rewrite_rules() {
	$rules = get_option('rewrite_rules');
	if (is_array($rules)) {
		foreach ($rules as $rule) {
			if (is_string($rule) && strpos($rule, 'index.php?sf_formula=') !== false) {
				return;
			}
		}
	}
	flush_rewrite_rules(false);
}
add_action('init', 'sinofresh_formula_flush_rewrite_rules', 99);
add_action('after_switch_theme', 'sinofresh_formula_flush_rewrite_rules');

/**
 * Authoritative dosage-form slug for [sf_formula_grid].
 *
 * The queried object is the source of truth, not the URL. On a dosage page
 * that is the page slug; on a formula detail page it is the formula's own
 * sf_formula_form term — the post slug there is the formula, not the form.
 * The request's last path segment is only a fallback, for a render where the
 * queried object is not a post. It needs no language-prefix handling:
 * /zh/products/soft-chews/ still ends in "soft-chews", the same convention
 * configurator.js already uses.
 */
function sinofresh_formula_current_form($form) {
	$form = sanitize_title($form);
	if ($form !== '') {
		return $form;
	}
	$queried = get_queried_object();
	if ($queried instanceof WP_Post) {
		if ($queried->post_type === 'sf_formula') {
			$terms = wp_get_post_terms($queried->ID, 'sf_formula_form', array('fields' => 'slugs'));
			if (!is_wp_error($terms) && $terms) {
				return (string) $terms[0];
			}
		} else {
			return (string) $queried->post_name;
		}
	}
	$uri  = isset($_SERVER['REQUEST_URI']) ? (string) wp_unslash($_SERVER['REQUEST_URI']) : '';
	$path = trim((string) wp_parse_url($uri, PHP_URL_PATH), '/');
	if ($path === '') {
		return '';
	}
	$segments = explode('/', $path);
	return sanitize_title((string) end($segments));
}

/**
 * Display label for a dosage form slug.
 *
 * The dosage page title is authoritative: it is the label the visitor already
 * reads on the page this slug addresses, and it reproduces the eight
 * hand-written JSON-LD names exactly ("Soft Chews", "Fish Oil", …). A
 * caller-supplied fallback and, failing that, a humanized slug come next.
 *
 * The fallback chain is deliberately not "term name first": taxonomy name and
 * slug are independent, so wp_set_object_terms() with a bare string creates a
 * term called "soft-chews", and a term name is therefore not a reliable label.
 *
 * Returns a decoded string — callers escape per context.
 */
function sinofresh_formula_label($slug, $fallback = '') {
	if ($slug === '') {
		return '';
	}
	$page = get_page_by_path('products/' . $slug);
	if ($page instanceof WP_Post) {
		return html_entity_decode(get_the_title($page), ENT_QUOTES, 'UTF-8');
	}
	if ($fallback !== '') {
		return html_entity_decode($fallback, ENT_QUOTES, 'UTF-8');
	}
	return ucwords(str_replace('-', ' ', $slug));
}

/**
 * ItemList name for [sf_formula_grid], matching the hand-written JSON-LD the
 * dosage templates ship today ("Standard Formulas — Soft Chews").
 */
function sinofresh_formula_list_name($form) {
	if ($form === '') {
		return 'Standard Formulas';
	}
	return 'Standard Formulas — ' . sinofresh_formula_label($form);
}

/**
 * Dosage-form still for the [sf_formula_grid] cards.
 *
 * The eight uploads/<yyyy>/<mm>/<form>.webp renders are the same square
 * dosage shots the dosage pages already show in their tile grids, so the
 * card image is derived from the form slug instead of a hand-kept map.
 * The year/month subdirectory is discovered with a glob rather than
 * hardcoded (the uploads tree moves as media is re-imported), and the
 * answer is memoised per form for the request.
 *
 * A form with no file returns '' and the card renders with no media block.
 * The alternative — always emitting <img src=""> — would still cost a
 * request and paint a broken-image icon.
 *
 * Known limitation, deliberate: every card on a dosage page repeats that
 * page's own still. Real formula photography does not exist yet, so the
 * dosage render is the placeholder; swapping it in later is a filter
 * (sinofresh_formula_card_image) or a per-form file, not a rewrite.
 */
function sinofresh_formula_card_image($form) {
	$form = sanitize_title($form);
	if ($form === '') {
		return '';
	}
	static $cache = array();
	if (array_key_exists($form, $cache)) {
		return $cache[$form];
	}
	$cache[$form] = '';

	$uploads = wp_upload_dir();
	if (!empty($uploads['error']) || empty($uploads['basedir'])) {
		return '';
	}
	$base    = trailingslashit($uploads['basedir']);
	$matches = array_merge(
		(array) glob($base . '*/*/' . $form . '.webp'),
		(array) glob($base . $form . '.webp')
	);
	if (!$matches) {
		return '';
	}
	/* Newest upload wins if the same basename exists in two month folders. */
	sort($matches);
	$relative = ltrim(str_replace($base, '', (string) end($matches)), '/');

	$cache[$form] = (string) apply_filters(
		'sinofresh_formula_card_image',
		trailingslashit($uploads['baseurl']) . $relative,
		$form
	);
	return $cache[$form];
}

/**
 * wp_json_encode() for the body of an inline <script>.
 *
 * JSON_UNESCAPED_SLASHES keeps "/" raw, so a title containing "</script"
 * would close the tag early. Escaping the angle bracket of every </script
 * sequence is valid JSON ("<\/script") and closes that hole. The assertion
 * after it is the contract: a payload that still contains a closing tag must
 * never reach the page, so this fails closed and leaves one line in the PHP
 * error log rather than emitting broken markup silently.
 */
function sinofresh_formula_script_json($data) {
	$json = wp_json_encode($data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
	if (!is_string($json) || $json === '') {
		error_log('[sinofresh] sf_formula_grid: JSON payload could not be encoded.');
		return '';
	}
	$json = (string) preg_replace('#</(?=script)#i', '<\\/', $json);
	if (strpos($json, '</script') !== false) {
		error_log('[sinofresh] sf_formula_grid: JSON payload still contained </script after escaping.');
		return '';
	}
	/* K4 — JSON inside <script> must be entity-free. Raw "&" is fine (JSON
	   is not HTML), but "&amp;" means an entity-encoded string (e.g. a term
	   name straight from wp_terms) leaked into the payload. Fail closed. */
	if (strpos($json, '&amp;') !== false) {
		error_log('[sinofresh] sf_formula_grid: JSON payload contained HTML entities (&amp;).');
		return '';
	}
	return $json;
}

/**
 * [sf_formula_grid] — the formula cards for one dosage form.
 *
 * Block templates run do_shortcode() before do_blocks(), so the grid never
 * receives a wp-container-core-* layout class and carries its own container
 * plus column count on the --sf-fgrid-cols custom property.
 *
 * Data contracts — do not break:
 *   K1  every card's primary button keeps class="sf-formula__cta" and
 *       data-formula="<name>"; assets/js/formulas.js binds to that pair and
 *       stores the name under the sessionStorage key configurator.js reads.
 *   K2  the same records are mirrored into <script class="sf-formulas-data">
 *       so configurator.js readFormula() can stop scraping <details> markup
 *       for the three fields (batch 2B switches it over).
 *   K3  card titles are <h3>, never <h2>: toc-nav.js numbers the page from its
 *       <h2> sequence, so a card heading would shift every downstream anchor.
 *   K4  JSON inside <script> is written raw ("&", not "&amp;") — see
 *       sinofresh_formula_script_json().
 *   K7  card anatomy is fixed: .sf-fcard > [.sf-fcard__media]? + .sf-fcard__body
 *       > (.sf-fcard__use, h3.sf-fcard__name, p.sf-fcard__spec, .sf-fcard__actions).
 *       The media block is omitted (not emitted empty) when no still exists;
 *       the copy lives in __body so the image can bleed to the card border
 *       while a text-only card stays visually identical to the 2B one.
 *
 * Attributes:
 *   form     dosage form slug. Default: resolved from the queried object.
 *   use      sf_formula_use slug to narrow to one function. Default: all.
 *   limit    max cards (-1 = all).
 *   columns  grid tracks, clamped to 1–6. Default: 4.
 *   cta      'reference' (default) renders the K1 button; 'none' omits it.
 *            Any other value falls back to 'reference'.
 *   links    'true' (default) links the title and adds "View formula →";
 *            'false'/'0'/'no' render the name as plain text.
 *   empty    only 'hide' is implemented; any other value behaves as 'hide'.
 */
function sinofresh_formula_grid($atts = array()) {
	$atts = shortcode_atts(array(
		'form'    => '',
		'use'     => '',
		'limit'   => -1,
		'columns' => 4,
		'cta'     => 'reference',
		'links'   => 'true',
		'empty'   => 'hide',
	), $atts, 'sf_formula_grid');

	$form    = sinofresh_formula_current_form($atts['form']);
	$use     = sanitize_title($atts['use']);
	$columns = max(1, min(6, (int) $atts['columns']));
	$links   = !in_array(strtolower((string) $atts['links']), array('false', '0', 'no'), true);
	$cta_on  = !in_array(strtolower((string) $atts['cta']), array('none', ''), true);

	$args      = array(
		'post_type'           => 'sf_formula',
		'post_status'         => 'publish',
		'posts_per_page'      => (int) $atts['limit'],
		'orderby'             => array('menu_order' => 'ASC', 'title' => 'ASC'),
		'ignore_sticky_posts' => true,
		'no_found_rows'       => true,
	);
	$tax_query = array();
	if ($form !== '') {
		$tax_query[] = array('taxonomy' => 'sf_formula_form', 'field' => 'slug', 'terms' => $form);
	}
	if ($use !== '') {
		$tax_query[] = array('taxonomy' => 'sf_formula_use', 'field' => 'slug', 'terms' => $use);
	}
	if ($tax_query) {
		$args['tax_query'] = $tax_query;
	}

	$formulas = get_posts($args);
	if (!$formulas) {
		/* `empty` currently implements only the 'hide' mode. */
		return '';
	}

	$cards   = '';
	$items   = array();
	$payload = array();

	foreach ($formulas as $formula) {
		/* One authoritative name string. get_the_title() is entity-encoded
		   ("Skin &amp; Coat"), and the name has to appear verbatim in three
		   places — the <h3> text, the JSON payload and data-formula.
		   Decoding once here and re-escaping per context is what keeps those
		   three identical. */
		$name = html_entity_decode(get_the_title($formula), ENT_QUOTES, 'UTF-8');
		if ($name === '') {
			continue;
		}
		$url = get_permalink($formula);

		$form_slugs = wp_get_post_terms($formula->ID, 'sf_formula_form', array('fields' => 'slugs'));
		$form_slug  = (!is_wp_error($form_slugs) && $form_slugs) ? (string) $form_slugs[0] : '';
		$use_terms  = wp_get_post_terms($formula->ID, 'sf_formula_use');
		$use_name   = (!is_wp_error($use_terms) && $use_terms) ? $use_terms[0]->name : '';
		$ingredients = (string) get_post_meta($formula->ID, 'sf_formula_ingredients', true);
		$analysis    = (string) get_post_meta($formula->ID, 'sf_formula_analysis', true);
		$specs       = (string) get_post_meta($formula->ID, 'sf_formula_specs', true);

		$items[] = array(
			'@type'    => 'ListItem',
			'position' => count($items) + 1,
			'name'     => $name,
			'url'      => $url,
		);

		$payload[] = array(
			'name'     => $name,
			'slug'     => $formula->post_name,
			'url'      => $url,
			'form'     => $form_slug,
			/* K4 — decode before JSON: wp_terms stores "Skin &amp; coat";
			   the .sf-formulas-data payload must carry the raw label. */
			'use'      => wp_specialchars_decode($use_name),
			'sections' => array(
				array('label' => 'Ingredients',         'value' => $ingredients),
				array('label' => 'Guaranteed Analysis', 'value' => $analysis),
				array('label' => 'Standard Specs',      'value' => $specs),
			),
		);

		$actions = '';
		if ($links) {
			$actions .= sprintf('<a class="sf-fcard__more" href="%s">View formula →</a>', esc_url($url));
		}
		if ($cta_on) {
			/* K1 — formulas.js binds clicks on .sf-formula__cta to the
			   sessionStorage key configurator.js later reads back, so
			   data-formula must carry the name verbatim. */
			$actions .= sprintf(
				'<button type="button" class="sf-formula__cta" data-formula="%s">Reference this formula →</button>',
				esc_attr($name)
			);
		}

		$media = '';
		$image = sinofresh_formula_card_image($form_slug);
		if ($image !== '') {
			/* The alt mirrors the dosage-page tile convention exactly
			   ("SINO FRESH Soft Chews private label pet supplement
			   product") so the formula stills are described the same way
			   as the identical renders in the dosage catalogue. */
			$media = sprintf(
				'<figure class="sf-fcard__media"><img src="%s" alt="%s" width="720" height="720" loading="lazy" decoding="async"/></figure>',
				esc_url($image),
				esc_attr(sprintf('SINO FRESH %s private label pet supplement product', sinofresh_formula_label($form_slug)))
			);
		}

		$cards .= sprintf(
			'<article class="sf-fcard">%s<div class="sf-fcard__body"><span class="sf-fcard__use">%s</span><h3 class="sf-fcard__name">%s</h3><p class="sf-fcard__spec">%s</p>%s</div></article>',
			$media,
			/* 2B Stage1 pit #2: term names are entity-encoded in wp_terms
			   ("Skin &amp; coat") — output verbatim so the browser shows
			   "Skin & coat". esc_html() here would double-escape. */
			$use_name,
			$links ? '<a href="' . esc_url($url) . '">' . esc_html($name) . '</a>' : esc_html($name),
			esc_html($specs),
			$actions === '' ? '' : '<div class="sf-fcard__actions">' . $actions . '</div>'
		);
	}

	$json = sinofresh_formula_script_json($payload);
	$list = sinofresh_formula_script_json(array(
		'@context'        => 'https://schema.org',
		'@type'           => 'ItemList',
		'name'            => sinofresh_formula_list_name($form),
		'numberOfItems'   => count($items),
		'itemListElement' => $items,
	));
	if ($json === '' || $list === '') {
		return '';
	}

	return sprintf('<div class="sf-fgrid" style="--sf-fgrid-cols:%d">', $columns)
		. '<script type="application/json" class="sf-formulas-data">' . $json . '</script>'
		. '<script type="application/ld+json">' . $list . '</script>'
		. $cards
		. '</div>';
}
add_shortcode('sf_formula_grid', 'sinofresh_formula_grid');

/**
 * Article pattern library (block patterns).
 *
 * Ten standardized article templates for content operations: editors open
 * the pattern inserter, pick a template and fill the bracketed English
 * placeholders. Structural blocks (TL;DR, short answer, FAQ items, CTA,
 * profile table) carry a lock so the skeleton cannot be broken by accident.
 * Supersedes the previous single "Case Study Skeleton" pattern.
 */
register_block_pattern_category('sinofresh-patterns', array(
	'label' => __('SINO FRESH Article Templates', 'sinofresh'),
));

/* 1. Educational Article ------------------------------------------------- */
register_block_pattern('sinofresh/educational-article', array(
	'title' => __('Educational Article', 'sinofresh'),
	'description' => __('For "What is X?" articles.', 'sinofresh'),
	'categories' => array('sinofresh-patterns'),
	'postTypes' => array('post'),
	'content' => <<<'HTML'
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">TL;DR</h2>
<!-- /wp:heading -->
<!-- wp:list {"lock":{"remove":true,"move":true}} -->
<ul class="wp-block-list"><!-- wp:list-item -->
<li>[TL;DR - 3-5 bullet points]</li>
<!-- /wp:list-item --></ul>
<!-- /wp:list -->
<!-- wp:paragraph {"lock":{"remove":true,"move":true}} -->
<p>[Short answer - 40-80 words: give the direct answer to the article's main question first.]</p>
<!-- /wp:paragraph -->
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">What Is [Topic]?</h2>
<!-- /wp:heading -->
<!-- wp:paragraph -->
<p>[Define the topic in plain English. One or two paragraphs.]</p>
<!-- /wp:paragraph -->
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">Why Does [Topic] Matter?</h2>
<!-- /wp:heading -->
<!-- wp:paragraph -->
<p>[Explain the business or product impact for brand owners and buyers.]</p>
<!-- /wp:paragraph -->
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">How Does [Topic] Work?</h2>
<!-- /wp:heading -->
<!-- wp:paragraph -->
<p>[Explain the mechanism, process or manufacturing logic step by step.]</p>
<!-- /wp:paragraph -->
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">Key Specifications / Standards</h2>
<!-- /wp:heading -->
<!-- wp:table {"hasFixedLayout":true} -->
<figure class="wp-block-table"><table><thead><tr><th>Parameter</th><th>Typical Value / Standard</th><th>Notes</th></tr></thead><tbody>
<tr><td>[Parameter 1]</td><td>[Value or standard]</td><td>[Note]</td></tr>
<tr><td>[Parameter 2]</td><td>[Value or standard]</td><td>[Note]</td></tr>
<tr><td>[Parameter 3]</td><td>[Value or standard]</td><td>[Note]</td></tr>
</tbody></table></figure>
<!-- /wp:table -->
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">Frequently Asked Questions</h2>
<!-- /wp:heading -->
<!-- wp:details {"lock":{"remove":true,"move":true}} -->
<details class="wp-block-details"><summary>[Question 1?]</summary><!-- wp:paragraph -->
<p>[Answer 1.]</p>
<!-- /wp:paragraph --></details>
<!-- /wp:details -->
<!-- wp:details {"lock":{"remove":true,"move":true}} -->
<details class="wp-block-details"><summary>[Question 2?]</summary><!-- wp:paragraph -->
<p>[Answer 2.]</p>
<!-- /wp:paragraph --></details>
<!-- /wp:details -->
<!-- wp:details {"lock":{"remove":true,"move":true}} -->
<details class="wp-block-details"><summary>[Question 3?]</summary><!-- wp:paragraph -->
<p>[Answer 3.]</p>
<!-- /wp:paragraph --></details>
<!-- /wp:details -->
<!-- wp:group {"lock":{"remove":true,"move":true},"className":"sf-article-cta"} -->
<div class="wp-block-group sf-article-cta">
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">Ready to Start Your Project?</h2>
<!-- /wp:heading -->
<!-- wp:paragraph -->
<p>[CTA - 1-2 sentences: invite the reader to send their specification to jsam@zxpet.com for a quotation within 48 hours.]</p>
<!-- /wp:paragraph -->
</div>
<!-- /wp:group -->
HTML,
));

/* 2. Selection Guide ----------------------------------------------------- */
register_block_pattern('sinofresh/selection-guide', array(
	'title' => __('Selection Guide', 'sinofresh'),
	'description' => __('For "How to choose X?" articles.', 'sinofresh'),
	'categories' => array('sinofresh-patterns'),
	'postTypes' => array('post'),
	'content' => <<<'HTML'
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">TL;DR</h2>
<!-- /wp:heading -->
<!-- wp:list {"lock":{"remove":true,"move":true}} -->
<ul class="wp-block-list"><!-- wp:list-item -->
<li>[TL;DR - 3-5 bullet points]</li>
<!-- /wp:list-item --></ul>
<!-- /wp:list -->
<!-- wp:paragraph {"lock":{"remove":true,"move":true}} -->
<p>[Short answer - 40-80 words: state the recommended choice for the most common scenario.]</p>
<!-- /wp:paragraph -->
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">What to Consider When Choosing [Product]</h2>
<!-- /wp:heading -->
<!-- wp:paragraph -->
<p>[One short paragraph framing the decision.]</p>
<!-- /wp:paragraph -->
<!-- wp:list -->
<ul class="wp-block-list"><!-- wp:list-item -->
<li>[Criterion 1, e.g. target market and regulatory requirements]</li>
<!-- /wp:list-item -->
<!-- wp:list-item -->
<li>[Criterion 2, e.g. positioning and price band]</li>
<!-- /wp:list-item -->
<!-- wp:list-item -->
<li>[Criterion 3, e.g. manufacturing complexity and MOQ]</li>
<!-- /wp:list-item --></ul>
<!-- /wp:list -->
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">[Product A] vs [Product B]</h2>
<!-- /wp:heading -->
<!-- wp:table {"hasFixedLayout":true} -->
<figure class="wp-block-table"><table><thead><tr><th>Factor</th><th>[Product A]</th><th>[Product B]</th></tr></thead><tbody>
<tr><td>[Factor 1]</td><td>[Detail]</td><td>[Detail]</td></tr>
<tr><td>[Factor 2]</td><td>[Detail]</td><td>[Detail]</td></tr>
<tr><td>[Factor 3]</td><td>[Detail]</td><td>[Detail]</td></tr>
<tr><td>[Factor 4]</td><td>[Detail]</td><td>[Detail]</td></tr>
</tbody></table></figure>
<!-- /wp:table -->
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">Common Mistakes to Avoid</h2>
<!-- /wp:heading -->
<!-- wp:list -->
<ul class="wp-block-list"><!-- wp:list-item -->
<li>[Mistake 1 and how to avoid it]</li>
<!-- /wp:list-item -->
<!-- wp:list-item -->
<li>[Mistake 2 and how to avoid it]</li>
<!-- /wp:list-item --></ul>
<!-- /wp:list -->
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">Frequently Asked Questions</h2>
<!-- /wp:heading -->
<!-- wp:details {"lock":{"remove":true,"move":true}} -->
<details class="wp-block-details"><summary>[Question 1?]</summary><!-- wp:paragraph -->
<p>[Answer 1.]</p>
<!-- /wp:paragraph --></details>
<!-- /wp:details -->
<!-- wp:details {"lock":{"remove":true,"move":true}} -->
<details class="wp-block-details"><summary>[Question 2?]</summary><!-- wp:paragraph -->
<p>[Answer 2.]</p>
<!-- /wp:paragraph --></details>
<!-- /wp:details -->
<!-- wp:details {"lock":{"remove":true,"move":true}} -->
<details class="wp-block-details"><summary>[Question 3?]</summary><!-- wp:paragraph -->
<p>[Answer 3.]</p>
<!-- /wp:paragraph --></details>
<!-- /wp:details -->
<!-- wp:group {"lock":{"remove":true,"move":true},"className":"sf-article-cta"} -->
<div class="wp-block-group sf-article-cta">
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">Ready to Start Your Project?</h2>
<!-- /wp:heading -->
<!-- wp:paragraph -->
<p>[CTA - 1-2 sentences: invite the reader to request a dosage-form recommendation from SINO FRESH.]</p>
<!-- /wp:paragraph -->
</div>
<!-- /wp:group -->
HTML,
));

/* 3. Comparison Article -------------------------------------------------- */
register_block_pattern('sinofresh/comparison-article', array(
	'title' => __('Comparison Article', 'sinofresh'),
	'description' => __('For "A vs B" comparisons.', 'sinofresh'),
	'categories' => array('sinofresh-patterns'),
	'postTypes' => array('post'),
	'content' => <<<'HTML'
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">TL;DR</h2>
<!-- /wp:heading -->
<!-- wp:list {"lock":{"remove":true,"move":true}} -->
<ul class="wp-block-list"><!-- wp:list-item -->
<li>[TL;DR - 3-5 bullet points]</li>
<!-- /wp:list-item --></ul>
<!-- /wp:list -->
<!-- wp:paragraph {"lock":{"remove":true,"move":true}} -->
<p>[Short answer - 40-80 words: state which option wins in which scenario.]</p>
<!-- /wp:paragraph -->
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">Key Differences at a Glance</h2>
<!-- /wp:heading -->
<!-- wp:table {"hasFixedLayout":true} -->
<figure class="wp-block-table"><table><thead><tr><th>Factor</th><th>[Option A]</th><th>[Option B]</th></tr></thead><tbody>
<tr><td>[Factor 1]</td><td>[Detail]</td><td>[Detail]</td></tr>
<tr><td>[Factor 2]</td><td>[Detail]</td><td>[Detail]</td></tr>
<tr><td>[Factor 3]</td><td>[Detail]</td><td>[Detail]</td></tr>
<tr><td>[Factor 4]</td><td>[Detail]</td><td>[Detail]</td></tr>
</tbody></table></figure>
<!-- /wp:table -->
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">When to Choose [A]</h2>
<!-- /wp:heading -->
<!-- wp:paragraph -->
<p>[2-3 sentences: the scenarios, brand types and budgets where [A] is the better fit.]</p>
<!-- /wp:paragraph -->
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">When to Choose [B]</h2>
<!-- /wp:heading -->
<!-- wp:paragraph -->
<p>[2-3 sentences: the scenarios, brand types and budgets where [B] is the better fit.]</p>
<!-- /wp:paragraph -->
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">Cost and MOQ Comparison</h2>
<!-- /wp:heading -->
<!-- wp:table {"hasFixedLayout":true} -->
<figure class="wp-block-table"><table><thead><tr><th>Item</th><th>[Option A]</th><th>[Option B]</th></tr></thead><tbody>
<tr><td>Typical MOQ</td><td>[MOQ]</td><td>[MOQ]</td></tr>
<tr><td>Unit cost band</td><td>[Range]</td><td>[Range]</td></tr>
<tr><td>Tooling / setup</td><td>[Detail]</td><td>[Detail]</td></tr>
</tbody></table></figure>
<!-- /wp:table -->
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">Frequently Asked Questions</h2>
<!-- /wp:heading -->
<!-- wp:details {"lock":{"remove":true,"move":true}} -->
<details class="wp-block-details"><summary>[Question 1?]</summary><!-- wp:paragraph -->
<p>[Answer 1.]</p>
<!-- /wp:paragraph --></details>
<!-- /wp:details -->
<!-- wp:details {"lock":{"remove":true,"move":true}} -->
<details class="wp-block-details"><summary>[Question 2?]</summary><!-- wp:paragraph -->
<p>[Answer 2.]</p>
<!-- /wp:paragraph --></details>
<!-- /wp:details -->
<!-- wp:details {"lock":{"remove":true,"move":true}} -->
<details class="wp-block-details"><summary>[Question 3?]</summary><!-- wp:paragraph -->
<p>[Answer 3.]</p>
<!-- /wp:paragraph --></details>
<!-- /wp:details -->
<!-- wp:group {"lock":{"remove":true,"move":true},"className":"sf-article-cta"} -->
<div class="wp-block-group sf-article-cta">
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">Ready to Start Your Project?</h2>
<!-- /wp:heading -->
<!-- wp:paragraph -->
<p>[CTA - 1-2 sentences: offer a side-by-side quotation for both options.]</p>
<!-- /wp:paragraph -->
</div>
<!-- /wp:group -->
HTML,
));

/* 4. Case Study ---------------------------------------------------------- */
register_block_pattern('sinofresh/case-study', array(
	'title' => __('Case Study', 'sinofresh'),
	'description' => __('For in-depth client case studies.', 'sinofresh'),
	'categories' => array('sinofresh-patterns'),
	'postTypes' => array('post'),
	'content' => <<<'HTML'
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">TL;DR</h2>
<!-- /wp:heading -->
<!-- wp:list {"lock":{"remove":true,"move":true}} -->
<ul class="wp-block-list"><!-- wp:list-item -->
<li>[Data point 1, e.g. First shipment in 12 weeks]</li>
<!-- /wp:list-item -->
<!-- wp:list-item -->
<li>[Data point 2, e.g. Reorder within 60 days]</li>
<!-- /wp:list-item --></ul>
<!-- /wp:list -->
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">Client Profile</h2>
<!-- /wp:heading -->
<!-- wp:table {"hasFixedLayout":true,"lock":{"remove":true,"move":true},"className":"sf-cs-profile"} -->
<figure class="wp-block-table sf-cs-profile"><table><tbody>
<tr><td>Client type</td><td>[Brand owner / E-commerce seller / Distributor / Veterinary clinic]</td></tr>
<tr><td>Country</td><td>[Country]</td></tr>
<tr><td>Dosage form</td><td>[Soft chews / Tablets / Powders / Pastes / Drops / Liquids]</td></tr>
<tr><td>Partnership model</td><td>[OEM / ODM / Private label]</td></tr>
<tr><td>Timeline</td><td>[Brief to first shipment in N weeks]</td></tr>
</tbody></table></figure>
<!-- /wp:table -->
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">The Challenge</h2>
<!-- /wp:heading -->
<!-- wp:paragraph -->
<p>[2-3 sentences: what the client needed, what was blocking them, why they contacted SINO FRESH.]</p>
<!-- /wp:paragraph -->
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">Our Solution</h2>
<!-- /wp:heading -->
<!-- wp:paragraph -->
<p>[1-2 sentences summarizing how we approached the project.]</p>
<!-- /wp:paragraph -->
<!-- wp:list -->
<ul class="wp-block-list"><!-- wp:list-item -->
<li>[Formulation and flavor development]</li>
<!-- /wp:list-item -->
<!-- wp:list-item -->
<li>[Compliance and export documentation]</li>
<!-- /wp:list-item -->
<!-- wp:list-item -->
<li>[Packaging and private-label branding]</li>
<!-- /wp:list-item --></ul>
<!-- /wp:list -->
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">The Result</h2>
<!-- /wp:heading -->
<!-- wp:paragraph -->
<p>[Outcome paragraph: launch status, reorder behavior, market feedback.]</p>
<!-- /wp:paragraph -->
<!-- wp:list -->
<ul class="wp-block-list"><!-- wp:list-item -->
<li>[Data point 1, e.g. MOQ 500 units]</li>
<!-- /wp:list-item -->
<!-- wp:list-item -->
<li>[Data point 2, e.g. Second order within 60 days]</li>
<!-- /wp:list-item -->
<!-- wp:list-item -->
<li>[Data point 3, e.g. Amazon rating 4.7 after 3 months]</li>
<!-- /wp:list-item --></ul>
<!-- /wp:list -->
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">Products Involved</h2>
<!-- /wp:heading -->
<!-- wp:paragraph -->
<p>[List the dosage forms with links, e.g. <a href="/products/soft-chews/">Soft Chews</a> and <a href="/products/powders/">Powders</a>.]</p>
<!-- /wp:paragraph -->
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">Client Feedback</h2>
<!-- /wp:heading -->
<!-- wp:quote -->
<blockquote class="wp-block-quote"><!-- wp:paragraph -->
<p>[Client quote - 1-2 sentences in their own words.]</p>
<!-- /wp:paragraph --><cite>[First name · Role · Country]</cite></blockquote>
<!-- /wp:quote -->
<!-- wp:group {"lock":{"remove":true,"move":true},"className":"sf-article-cta"} -->
<div class="wp-block-group sf-article-cta">
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">Ready to Start Your Project?</h2>
<!-- /wp:heading -->
<!-- wp:paragraph -->
<p>[CTA - 1-2 sentences: invite the reader to build a similar line with SINO FRESH.]</p>
<!-- /wp:paragraph -->
</div>
<!-- /wp:group -->
HTML,
));

/* 5. Client Story -------------------------------------------------------- */
register_block_pattern('sinofresh/client-story', array(
	'title' => __('Client Story', 'sinofresh'),
	'description' => __('For short client testimonials. Links from the homepage Client Stories cards.', 'sinofresh'),
	'categories' => array('sinofresh-patterns'),
	'postTypes' => array('post'),
	'content' => <<<'HTML'
<!-- wp:heading {"level":1} -->
<h1 class="wp-block-heading">"[Client quote - one sentence in their own words]" — [Alias], [Country]</h1>
<!-- /wp:heading -->
<!-- wp:paragraph {"lock":{"remove":true,"move":true}} -->
<p>[Brand Owner · Country · Dosage form · ODM]</p>
<!-- /wp:paragraph -->
<!-- wp:quote -->
<blockquote class="wp-block-quote"><!-- wp:paragraph -->
<p>[Client quote - 2-3 sentences in their own words.]</p>
<!-- /wp:paragraph --><cite>[Alias], [Role]</cite></blockquote>
<!-- /wp:quote -->
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">Background</h2>
<!-- /wp:heading -->
<!-- wp:paragraph -->
<p>[One short paragraph: who the client is and what they wanted to launch.]</p>
<!-- /wp:paragraph -->
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">The Result</h2>
<!-- /wp:heading -->
<!-- wp:list -->
<ul class="wp-block-list"><!-- wp:list-item -->
<li>[Data point 1, e.g. First order shipped in 10 weeks]</li>
<!-- /wp:list-item -->
<!-- wp:list-item -->
<li>[Data point 2, e.g. Reorder volume +40%]</li>
<!-- /wp:list-item --></ul>
<!-- /wp:list -->
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">Products Involved</h2>
<!-- /wp:heading -->
<!-- wp:paragraph -->
<p>[List the dosage forms with links, e.g. <a href="/products/soft-chews/">Soft Chews</a>.]</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph {"lock":{"remove":true,"move":true}} -->
<p><a href="[full case study URL]">Read the full case study →</a></p>
<!-- /wp:paragraph -->
<!-- wp:group {"lock":{"remove":true,"move":true},"className":"sf-article-cta"} -->
<div class="wp-block-group sf-article-cta">
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">Ready to Start Your Project?</h2>
<!-- /wp:heading -->
<!-- wp:paragraph -->
<p>[CTA - 1-2 sentences: invite the reader to contact SINO FRESH.]</p>
<!-- /wp:paragraph -->
</div>
<!-- /wp:group -->
HTML,
));

/* 6. Technical Deep Dive ------------------------------------------------- */
register_block_pattern('sinofresh/technical-deep-dive', array(
	'title' => __('Technical Deep Dive', 'sinofresh'),
	'description' => __('For technical articles on processes, testing, QC.', 'sinofresh'),
	'categories' => array('sinofresh-patterns'),
	'postTypes' => array('post'),
	'content' => <<<'HTML'
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">TL;DR</h2>
<!-- /wp:heading -->
<!-- wp:list {"lock":{"remove":true,"move":true}} -->
<ul class="wp-block-list"><!-- wp:list-item -->
<li>[TL;DR - 3 bullet points]</li>
<!-- /wp:list-item --></ul>
<!-- /wp:list -->
<!-- wp:paragraph {"lock":{"remove":true,"move":true}} -->
<p>[Short answer - 40-80 words: summarize the technical takeaway.]</p>
<!-- /wp:paragraph -->
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">The Science Behind [Technology]</h2>
<!-- /wp:heading -->
<!-- wp:paragraph -->
<p>[Explain the underlying science or engineering in accessible language.]</p>
<!-- /wp:paragraph -->
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">Key Technical Parameters</h2>
<!-- /wp:heading -->
<!-- wp:table {"hasFixedLayout":true} -->
<figure class="wp-block-table"><table><thead><tr><th>Parameter</th><th>Specification</th><th>Why It Matters</th></tr></thead><tbody>
<tr><td>[Parameter 1]</td><td>[Value / range / standard]</td><td>[Impact on quality or stability]</td></tr>
<tr><td>[Parameter 2]</td><td>[Value / range / standard]</td><td>[Impact on quality or stability]</td></tr>
<tr><td>[Parameter 3]</td><td>[Value / range / standard]</td><td>[Impact on quality or stability]</td></tr>
</tbody></table></figure>
<!-- /wp:table -->
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">How We Implement [Technology] at SINO FRESH</h2>
<!-- /wp:heading -->
<!-- wp:paragraph -->
<p>[One short paragraph introducing the implementation.]</p>
<!-- /wp:paragraph -->
<!-- wp:list -->
<ul class="wp-block-list"><!-- wp:list-item -->
<li>[Implementation step or equipment 1]</li>
<!-- /wp:list-item -->
<!-- wp:list-item -->
<li>[Implementation step or equipment 2]</li>
<!-- /wp:list-item --></ul>
<!-- /wp:list -->
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">Quality Control Points</h2>
<!-- /wp:heading -->
<!-- wp:list -->
<ul class="wp-block-list"><!-- wp:list-item -->
<li>[QC checkpoint 1]</li>
<!-- /wp:list-item -->
<!-- wp:list-item -->
<li>[QC checkpoint 2]</li>
<!-- /wp:list-item --></ul>
<!-- /wp:list -->
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">Frequently Asked Questions</h2>
<!-- /wp:heading -->
<!-- wp:details {"lock":{"remove":true,"move":true}} -->
<details class="wp-block-details"><summary>[Question 1?]</summary><!-- wp:paragraph -->
<p>[Answer 1.]</p>
<!-- /wp:paragraph --></details>
<!-- /wp:details -->
<!-- wp:details {"lock":{"remove":true,"move":true}} -->
<details class="wp-block-details"><summary>[Question 2?]</summary><!-- wp:paragraph -->
<p>[Answer 2.]</p>
<!-- /wp:paragraph --></details>
<!-- /wp:details -->
<!-- wp:group {"lock":{"remove":true,"move":true},"className":"sf-article-cta"} -->
<div class="wp-block-group sf-article-cta">
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">Request Technical Documentation</h2>
<!-- /wp:heading -->
<!-- wp:paragraph -->
<p>[CTA - 1-2 sentences: offer spec sheets, COA samples or process documentation on request.]</p>
<!-- /wp:paragraph -->
</div>
<!-- /wp:group -->
HTML,
));

/* 7. Compliance Guide ---------------------------------------------------- */
register_block_pattern('sinofresh/compliance-guide', array(
	'title' => __('Compliance Guide', 'sinofresh'),
	'description' => __('For market-specific labeling and regulatory guides.', 'sinofresh'),
	'categories' => array('sinofresh-patterns'),
	'postTypes' => array('post'),
	'content' => <<<'HTML'
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">TL;DR</h2>
<!-- /wp:heading -->
<!-- wp:list {"lock":{"remove":true,"move":true}} -->
<ul class="wp-block-list"><!-- wp:list-item -->
<li>[TL;DR - 3-5 bullet points]</li>
<!-- /wp:list-item --></ul>
<!-- /wp:list -->
<!-- wp:paragraph {"lock":{"remove":true,"move":true}} -->
<p>[Short answer - 40-80 words: summarize what [Market] requires in one breath.]</p>
<!-- /wp:paragraph -->
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">Overview of [Market] Regulations</h2>
<!-- /wp:heading -->
<!-- wp:paragraph -->
<p>[Which agency regulates pet supplements, under which framework, and what product category applies.]</p>
<!-- /wp:paragraph -->
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">Required Label Elements</h2>
<!-- /wp:heading -->
<!-- wp:table {"hasFixedLayout":true} -->
<figure class="wp-block-table"><table><thead><tr><th>Label Element</th><th>Requirement</th><th>Notes</th></tr></thead><tbody>
<tr><td>[Element 1, e.g. Ingredient list]</td><td>[Requirement]</td><td>[Note]</td></tr>
<tr><td>[Element 2, e.g. Net quantity]</td><td>[Requirement]</td><td>[Note]</td></tr>
<tr><td>[Element 3, e.g. Feeding directions]</td><td>[Requirement]</td><td>[Note]</td></tr>
<tr><td>[Element 4, e.g. Manufacturer identity]</td><td>[Requirement]</td><td>[Note]</td></tr>
</tbody></table></figure>
<!-- /wp:table -->
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">Claims and Restrictions</h2>
<!-- /wp:heading -->
<!-- wp:table {"hasFixedLayout":true} -->
<figure class="wp-block-table"><table><thead><tr><th>Allowed Claims</th><th>Restricted / Prohibited Claims</th></tr></thead><tbody>
<tr><td>[Allowed claim example]</td><td>[Restricted claim example]</td></tr>
<tr><td>[Allowed claim example]</td><td>[Restricted claim example]</td></tr>
<tr><td>[Allowed claim example]</td><td>[Restricted claim example]</td></tr>
</tbody></table></figure>
<!-- /wp:table -->
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">Documentation Checklist</h2>
<!-- /wp:heading -->
<!-- wp:list -->
<ul class="wp-block-list"><!-- wp:list-item -->
<li>[Document 1, e.g. Certificate of Analysis per batch]</li>
<!-- /wp:list-item -->
<!-- wp:list-item -->
<li>[Document 2, e.g. Ingredient specifications]</li>
<!-- /wp:list-item --></ul>
<!-- /wp:list -->
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">Frequently Asked Questions</h2>
<!-- /wp:heading -->
<!-- wp:details {"lock":{"remove":true,"move":true}} -->
<details class="wp-block-details"><summary>[Question 1?]</summary><!-- wp:paragraph -->
<p>[Answer 1.]</p>
<!-- /wp:paragraph --></details>
<!-- /wp:details -->
<!-- wp:details {"lock":{"remove":true,"move":true}} -->
<details class="wp-block-details"><summary>[Question 2?]</summary><!-- wp:paragraph -->
<p>[Answer 2.]</p>
<!-- /wp:paragraph --></details>
<!-- /wp:details -->
<!-- wp:group {"lock":{"remove":true,"move":true},"className":"sf-article-cta"} -->
<div class="wp-block-group sf-article-cta">
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">Request Compliance Support</h2>
<!-- /wp:heading -->
<!-- wp:paragraph -->
<p>[CTA - 1-2 sentences: offer label review and export documentation support.]</p>
<!-- /wp:paragraph -->
</div>
<!-- /wp:group -->
HTML,
));

/* 8. Buyer's Guide ------------------------------------------------------- */
register_block_pattern('sinofresh/buyers-guide', array(
	'title' => "Buyer's Guide",
	'description' => __('For supplier evaluation and procurement guides.', 'sinofresh'),
	'categories' => array('sinofresh-patterns'),
	'postTypes' => array('post'),
	'content' => <<<'HTML'
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">TL;DR</h2>
<!-- /wp:heading -->
<!-- wp:list {"lock":{"remove":true,"move":true}} -->
<ul class="wp-block-list"><!-- wp:list-item -->
<li>[TL;DR - 3-5 bullet points]</li>
<!-- /wp:list-item --></ul>
<!-- /wp:list -->
<!-- wp:paragraph {"lock":{"remove":true,"move":true}} -->
<p>[Short answer - 40-80 words: the single most important criterion when vetting a manufacturer.]</p>
<!-- /wp:paragraph -->
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">The [N] Key Evaluation Criteria</h2>
<!-- /wp:heading -->
<!-- wp:table {"hasFixedLayout":true} -->
<figure class="wp-block-table"><table><thead><tr><th>Criterion</th><th>What to Look For</th><th>Weight</th></tr></thead><tbody>
<tr><td>[Criterion 1, e.g. Certifications]</td><td>[Evidence to request]</td><td>[High / Medium / Low]</td></tr>
<tr><td>[Criterion 2, e.g. In-house QC lab]</td><td>[Evidence to request]</td><td>[High / Medium / Low]</td></tr>
<tr><td>[Criterion 3, e.g. Export experience]</td><td>[Evidence to request]</td><td>[High / Medium / Low]</td></tr>
</tbody></table></figure>
<!-- /wp:table -->
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">Certifications to Verify</h2>
<!-- /wp:heading -->
<!-- wp:list -->
<ul class="wp-block-list"><!-- wp:list-item -->
<li>[Certification 1, e.g. FDA registration and cGMP compliance]</li>
<!-- /wp:list-item -->
<!-- wp:list-item -->
<li>[Certification 2, e.g. ISO 9001 quality management]</li>
<!-- /wp:list-item --></ul>
<!-- /wp:list -->
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">Questions to Ask Your Potential Manufacturer</h2>
<!-- /wp:heading -->
<!-- wp:list -->
<ul class="wp-block-list"><!-- wp:list-item -->
<li>[Question 1]</li>
<!-- /wp:list-item -->
<!-- wp:list-item -->
<li>[Question 2]</li>
<!-- /wp:list-item -->
<!-- wp:list-item -->
<li>[Question 3]</li>
<!-- /wp:list-item --></ul>
<!-- /wp:list -->
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">Red Flags to Avoid</h2>
<!-- /wp:heading -->
<!-- wp:list -->
<ul class="wp-block-list"><!-- wp:list-item -->
<li>[Red flag 1]</li>
<!-- /wp:list-item -->
<!-- wp:list-item -->
<li>[Red flag 2]</li>
<!-- /wp:list-item --></ul>
<!-- /wp:list -->
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">Frequently Asked Questions</h2>
<!-- /wp:heading -->
<!-- wp:details {"lock":{"remove":true,"move":true}} -->
<details class="wp-block-details"><summary>[Question 1?]</summary><!-- wp:paragraph -->
<p>[Answer 1.]</p>
<!-- /wp:paragraph --></details>
<!-- /wp:details -->
<!-- wp:details {"lock":{"remove":true,"move":true}} -->
<details class="wp-block-details"><summary>[Question 2?]</summary><!-- wp:paragraph -->
<p>[Answer 2.]</p>
<!-- /wp:paragraph --></details>
<!-- /wp:details -->
<!-- wp:group {"lock":{"remove":true,"move":true},"className":"sf-article-cta"} -->
<div class="wp-block-group sf-article-cta">
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">Download Our Capability Overview</h2>
<!-- /wp:heading -->
<!-- wp:paragraph -->
<p>[CTA - 1-2 sentences: offer the factory capability deck or a sample kit.]</p>
<!-- /wp:paragraph -->
</div>
<!-- /wp:group -->
HTML,
));

/* 9. Market Trends ------------------------------------------------------- */
register_block_pattern('sinofresh/market-trends', array(
	'title' => __('Market Trends', 'sinofresh'),
	'description' => __('For industry data and trend analysis.', 'sinofresh'),
	'categories' => array('sinofresh-patterns'),
	'postTypes' => array('post'),
	'content' => <<<'HTML'
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">TL;DR</h2>
<!-- /wp:heading -->
<!-- wp:list {"lock":{"remove":true,"move":true}} -->
<ul class="wp-block-list"><!-- wp:list-item -->
<li>[TL;DR - 3-5 bullet points]</li>
<!-- /wp:list-item --></ul>
<!-- /wp:list -->
<!-- wp:paragraph {"lock":{"remove":true,"move":true}} -->
<p>[Short answer - 40-80 words: the single most actionable trend.]</p>
<!-- /wp:paragraph -->
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">Key Market Data</h2>
<!-- /wp:heading -->
<!-- wp:table {"hasFixedLayout":true} -->
<figure class="wp-block-table"><table><thead><tr><th>Metric</th><th>[Year 1]</th><th>[Year 2]</th><th>Change</th></tr></thead><tbody>
<tr><td>[Metric 1, e.g. Global pet supplement market size]</td><td>[$ value]</td><td>[$ value]</td><td>[% change]</td></tr>
<tr><td>[Metric 2]</td><td>[$ value]</td><td>[$ value]</td><td>[% change]</td></tr>
<tr><td>[Metric 3]</td><td>[$ value]</td><td>[$ value]</td><td>[% change]</td></tr>
</tbody></table></figure>
<!-- /wp:table -->
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">Top Growing Categories</h2>
<!-- /wp:heading -->
<!-- wp:list -->
<ul class="wp-block-list"><!-- wp:list-item -->
<li>[Category 1 with growth rate]</li>
<!-- /wp:list-item -->
<!-- wp:list-item -->
<li>[Category 2 with growth rate]</li>
<!-- /wp:list-item --></ul>
<!-- /wp:list -->
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">Regional Insights</h2>
<!-- /wp:heading -->
<!-- wp:paragraph -->
<p>[Compare [Region A] and [Region B]: demand drivers, channel mix, price sensitivity.]</p>
<!-- /wp:paragraph -->
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">What This Means for Brand Owners</h2>
<!-- /wp:heading -->
<!-- wp:paragraph -->
<p>[2-3 sentences translating the data into product decisions: which dosage form, which market, which claim.]</p>
<!-- /wp:paragraph -->
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">Frequently Asked Questions</h2>
<!-- /wp:heading -->
<!-- wp:details {"lock":{"remove":true,"move":true}} -->
<details class="wp-block-details"><summary>[Question 1?]</summary><!-- wp:paragraph -->
<p>[Answer 1.]</p>
<!-- /wp:paragraph --></details>
<!-- /wp:details -->
<!-- wp:details {"lock":{"remove":true,"move":true}} -->
<details class="wp-block-details"><summary>[Question 2?]</summary><!-- wp:paragraph -->
<p>[Answer 2.]</p>
<!-- /wp:paragraph --></details>
<!-- /wp:details -->
<!-- wp:group {"lock":{"remove":true,"move":true},"className":"sf-article-cta"} -->
<div class="wp-block-group sf-article-cta">
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">Download Full Market Report</h2>
<!-- /wp:heading -->
<!-- wp:paragraph -->
<p>[CTA - 1-2 sentences: offer the full report or a category deep dive on request.]</p>
<!-- /wp:paragraph -->
</div>
<!-- /wp:group -->
HTML,
));

/* 10. Thought Leadership ------------------------------------------------- */
register_block_pattern('sinofresh/thought-leadership', array(
	'title' => __('Thought Leadership', 'sinofresh'),
	'description' => __('For opinion and industry perspective.', 'sinofresh'),
	'categories' => array('sinofresh-patterns'),
	'postTypes' => array('post'),
	'content' => <<<'HTML'
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">TL;DR</h2>
<!-- /wp:heading -->
<!-- wp:list {"lock":{"remove":true,"move":true}} -->
<ul class="wp-block-list"><!-- wp:list-item -->
<li>[TL;DR - 3 bullet points]</li>
<!-- /wp:list-item --></ul>
<!-- /wp:list -->
<!-- wp:paragraph {"lock":{"remove":true,"move":true}} -->
<p>[Short answer - 40-80 words: state the contrarian or expert position in one breath.]</p>
<!-- /wp:paragraph -->
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">The Problem with Current Industry Practices</h2>
<!-- /wp:heading -->
<!-- wp:paragraph -->
<p>[Name the common practice, why it persists, and what it costs brands and pets.]</p>
<!-- /wp:paragraph -->
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">What [Topic] Really Means</h2>
<!-- /wp:heading -->
<!-- wp:paragraph -->
<p>[Reframe the topic: define it the way an informed buyer should.]</p>
<!-- /wp:paragraph -->
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">How We Approach It at SINO FRESH</h2>
<!-- /wp:heading -->
<!-- wp:list -->
<ul class="wp-block-list"><!-- wp:list-item -->
<li>[Practice 1]</li>
<!-- /wp:list-item -->
<!-- wp:list-item -->
<li>[Practice 2]</li>
<!-- /wp:list-item --></ul>
<!-- /wp:list -->
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">What Brand Owners Should Demand</h2>
<!-- /wp:heading -->
<!-- wp:list -->
<ul class="wp-block-list"><!-- wp:list-item -->
<li>[Demand 1]</li>
<!-- /wp:list-item -->
<!-- wp:list-item -->
<li>[Demand 2]</li>
<!-- /wp:list-item --></ul>
<!-- /wp:list -->
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">Frequently Asked Questions</h2>
<!-- /wp:heading -->
<!-- wp:details {"lock":{"remove":true,"move":true}} -->
<details class="wp-block-details"><summary>[Question 1?]</summary><!-- wp:paragraph -->
<p>[Answer 1.]</p>
<!-- /wp:paragraph --></details>
<!-- /wp:details -->
<!-- wp:details {"lock":{"remove":true,"move":true}} -->
<details class="wp-block-details"><summary>[Question 2?]</summary><!-- wp:paragraph -->
<p>[Answer 2.]</p>
<!-- /wp:paragraph --></details>
<!-- /wp:details -->
<!-- wp:group {"lock":{"remove":true,"move":true},"className":"sf-article-cta"} -->
<div class="wp-block-group sf-article-cta">
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">Share Your Perspective</h2>
<!-- /wp:heading -->
<!-- wp:paragraph -->
<p>[CTA - 1-2 sentences: invite the reader to reply with their view or request a consultation.]</p>
<!-- /wp:paragraph -->
</div>
<!-- /wp:group -->
HTML,
));

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
 *   2. posts sharing the viewed post's categories rank first, then posts
 *      sharing at least one of its tags, capped at three.
 *
 * The result reaches WP_Query as an ordered ID list (post__in +
 * orderby=post_in) instead of as a taxonomy restriction, so the query cannot
 * re-rank the list or pad it with unrelated posts. That determinism is what
 * lets the section-hiding filter below trust core's own "no results" state.
 *
 * Front-end only — the editor preview renders through the REST API and is not
 * affected by this filter.
 */
add_filter('query_loop_block_query_vars', function($query, $block) use (&$sinofresh_related_query_ids) {
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

	$sf_limit   = 3;
	$sf_related = array();

	// 1. Same category first.
	$sf_categories = wp_get_post_terms($post_id, 'category', array('fields' => 'ids'));
	if (!is_wp_error($sf_categories) && $sf_categories) {
		$sf_related = get_posts(array(
			'post_type'           => 'post',
			'post_status'         => 'publish',
			'posts_per_page'      => $sf_limit,
			'fields'              => 'ids',
			'post__not_in'        => array($post_id),
			'category__in'        => array_map('intval', $sf_categories),
			'orderby'             => 'date',
			'order'               => 'DESC',
			'ignore_sticky_posts' => true,
			'no_found_rows'       => true,
		));
	}

	// 2. Topped up with posts sharing at least one tag.
	if (count($sf_related) < $sf_limit) {
		$sf_tags = wp_get_post_terms($post_id, 'post_tag', array('fields' => 'ids'));
		if (!is_wp_error($sf_tags) && $sf_tags) {
			$sf_related = array_merge($sf_related, get_posts(array(
				'post_type'           => 'post',
				'post_status'         => 'publish',
				'posts_per_page'      => $sf_limit - count($sf_related),
				'fields'              => 'ids',
				'post__not_in'        => array_merge(array($post_id), $sf_related),
				'tag__in'             => array_map('intval', $sf_tags),
				'orderby'             => 'date',
				'order'               => 'DESC',
				'ignore_sticky_posts' => true,
				'no_found_rows'       => true,
			)));
		}
	}

	$sf_related = array_slice(array_map('intval', $sf_related), 0, $sf_limit);

	$query['post__not_in']        = array();
	$query['tax_query']           = array();
	$query['post__in']            = $sf_related ? $sf_related : array(0);
	$query['orderby']             = 'post__in';
	$query['order']               = 'ASC';
	$query['posts_per_page']      = max(1, count($sf_related));
	$query['ignore_sticky_posts'] = true;

	return $query;
}, 10, 2);

/**
 * Hide the whole "Related Articles" band when nothing is related.
 *
 * The heading and the query sit in the same group, which the theme template
 * marks `sf-related`; returning an empty string for that group removes the
 * heading together with the cards, instead of leaving an orphan H2 over a
 * placeholder line. The marker is core's own no-results wrapper, which only
 * renders when the query came back empty — and that query is deterministic
 * (see above), so the state means "genuinely nothing related".
 */
add_filter('render_block', function($block_content, $parsed_block) {
	if (is_admin() || defined('REST_REQUEST')) {
		return $block_content;
	}
	if ('core/group' !== (isset($parsed_block['blockName']) ? $parsed_block['blockName'] : '')) {
		return $block_content;
	}
	$attrs = isset($parsed_block['attrs']) ? (array) $parsed_block['attrs'] : array();
	if (!isset($attrs['className']) || false === strpos((string) $attrs['className'], 'sf-related')) {
		return $block_content;
	}
	if (false !== strpos($block_content, 'wp-block-query-no-results')) {
		return '';
	}
	return $block_content;
}, 10, 2);

/**
 * Previous / next links (templates/single.html) carry no rel attribute.
 *
 * `get_adjacent_post_link()` hardcodes rel="prev" / rel="next" on the anchor
 * it builds and `core/post-navigation-link` has no attribute to switch it off,
 * so the generated markup is the only interception point. Google retired
 * rel=prev/next as an indexing signal in 2019 — the attributes are dead weight
 * here, and both links stay fully crawlable without them.
 */
foreach (array('previous_post_link', 'next_post_link') as $sf_adjacent_hook) {
	add_filter($sf_adjacent_hook, function($output) {
		return str_replace(array(' rel="prev"', ' rel="next"'), '', $output);
	}, 10, 1);
}

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
/**
 * Placeholder engine for static template HTML.
 *
 * The article template (single.html) is plain wp:html markup, so dynamic
 * values travel as {{...}} placeholders replaced at render time — both for
 * the visible blocks (render_block filter below) and for the BreadcrumbList
 * schema generator, which re-reads the template file from disk. One function
 * for both means the visible breadcrumb, the JSON-LD breadcrumb and the
 * share links can never drift apart.
 *
 * Placeholders:
 *   {{TITLE}}            current post/page title (escaped)
 *   {{ARCHIVE_TITLE}}    current archive label — term name for categories/
 *                        tags/custom taxonomies, search query, or the
 *                        prefix-stripped archive title elsewhere (Archive
 *                        fallback); used by archive.html and search.html
 *   {{MID_HREF}}         middle breadcrumb href — Case Studies archive for
 *                        posts filed under case-studies, else the blog
 *   {{MID_CRUMB}}        matching middle breadcrumb label
 *   {{FORM_CRUMB}}       formula detail pages only — the dosage form name of
 *                        the current sf_formula, from its sf_formula_form term
 *   {{FORM_HREF}}        matching href (/products/<term slug>/), falling back
 *                        to /products/ when the formula carries no term
 *   {{LAST_UPDATED}}     "· Last updated: M j, Y" from the sf_last_reviewed
 *                        custom field, or '' when unset (only posts with a
 *                        real content review show the second date)
 *   {{SHARE_URL}}        current permalink (raw)
 *   {{SHARE_URL_ENC}}    permalink, rawurlencode()d for share endpoints
 *   {{SHARE_TITLE_ENC}}  post title, rawurlencode()d for share endpoints
 */
function sinofresh_template_placeholders($html) {
	$case   = false;
	$last   = '';
	/* sf_formula joins `post` here so {{TITLE}}, {{LAST_UPDATED}} and the
	   share links keep resolving on formula detail pages. $case stays false
	   and $last stays empty for formulas, which is the intended fallback. */
	$post_id = (is_singular('post') || is_singular('sf_formula')) ? (int) get_queried_object_id() : 0;
	if ($post_id) {
		$terms = wp_get_post_terms($post_id, 'category', array('fields' => 'slugs'));
		$case  = !is_wp_error($terms) && in_array('case-studies', $terms, true);
		$reviewed = get_post_meta($post_id, 'sf_last_reviewed', true);
		if ($reviewed && strtotime((string) $reviewed)) {
			$last = '· Last updated: ' . date_i18n('M j, Y', strtotime((string) $reviewed));
		}
	}
	$permalink = is_singular() ? get_permalink() : home_url('/');
	$title     = get_the_title();
	/* Archives (archive.html serves categories, tags, dates, authors): the
	   current crumb is the queried term name; get_the_archive_title() with
	   its default prefixes stripped is the fallback for other archive types. */
	$archive_title = '';
	if (is_category() || is_tag() || is_tax()) {
		$qo = get_queried_object();
		$archive_title = ($qo instanceof WP_Term) ? $qo->name : '';
	} elseif (is_search()) {
		$archive_title = get_search_query();
	} elseif (is_archive()) {
		$archive_title = wp_strip_all_tags(get_the_archive_title());
		$archive_title = trim(preg_replace('/^(?:Category|Tag|Author|Year|Month|Day|Week|Post Format|Classification|Classification|分类|标签|作者|年|月|日)\s*[^:：]*:\s*/iu', '', $archive_title));
	}
	if ($archive_title === '') {
		$archive_title = 'Archive';
	}
	/* Formula detail pages: the middle crumb is the dosage form, so
	   {{FORM_CRUMB}} / {{FORM_HREF}} resolve from the post's sf_formula_form
	   term. The term slug equals the dosage page slug by convention — see
	   sinofresh_register_formula_types() — which is what makes
	   /products/<term slug>/ the correct href. A missing term falls back to
	   the products index, so the crumb degrades to one level rather than
	   disappearing entirely. */
	$form_crumb = '';
	$form_href  = '/products/';
	if (is_singular('sf_formula')) {
		$form_terms = wp_get_post_terms((int) get_queried_object_id(), 'sf_formula_form');
		if (!is_wp_error($form_terms) && $form_terms) {
			$form_crumb = sinofresh_formula_label($form_terms[0]->slug, $form_terms[0]->name);
			$form_href  = '/products/' . $form_terms[0]->slug . '/';
		}
	}
	$map = array(
		'{{TITLE}}'           => esc_html($title),
		'{{ARCHIVE_TITLE}}'   => esc_html($archive_title),
		'{{MID_HREF}}'        => $case ? '/category/case-studies/' : '/blog/',
		'{{MID_CRUMB}}'       => $case ? 'Case Studies' : 'Blog',
		'{{FORM_CRUMB}}'      => esc_html($form_crumb),
		'{{FORM_HREF}}'       => esc_url($form_href),
		'{{LAST_UPDATED}}'    => esc_html($last),
		'{{SHARE_URL}}'       => esc_url($permalink),
		'{{SHARE_URL_ENC}}'   => rawurlencode($permalink),
		'{{SHARE_TITLE_ENC}}' => rawurlencode(html_entity_decode($title, ENT_QUOTES, 'UTF-8')),
	);
	return str_replace(array_keys($map), array_values($map), $html);
}

add_filter('render_block', function($block_content, $parsed_block) {
	if (is_admin() || defined('REST_REQUEST')) {
		return $block_content;
	}
	if (($parsed_block['blockName'] ?? '') === 'core/html'
		&& strpos($block_content, '{{') !== false) {
		$block_content = sinofresh_template_placeholders($block_content);
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
	} elseif (is_singular('sf_formula')) {
		/* Batch 2A wires the branch ahead of the template: 2C adds
		   templates/single-sf_formula.html, and until then this resolves
		   through single.html, so the JSON-LD breadcrumb matches whatever
		   the visitor actually sees. */
		$candidates = array('single-sf_formula', 'single');
	} elseif (is_search()) {
		$candidates = array('search');
	} elseif (is_archive()) {
		/* Categories, tags, dates and authors all fall back to archive.html. */
		$candidates = array('archive');
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
	// Run the same placeholder engine the render path uses, so the {{TITLE}}
	// and {{MID_*}} crumbs resolve identically in the JSON-LD breadcrumb.
	$html = sinofresh_template_placeholders($html);
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
		array('name' => 'FSSC 22000', 'url' => '/quality/', 'active' => true),
		array('name' => 'HACCP', 'url' => '/quality/', 'active' => true),
		array('name' => 'BRC', 'url' => '/quality/', 'active' => true),
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
 * description = the hero's `<!-- sf-schema-desc -->` carrier, image = this
 * form's own upload (resolved by file name, so it can never latch onto a
 * Related tile of a sibling product), additionalProperty = the Specifications
 * rows (sf-spec-list, with a fallback parser for the legacy key-facts table).
 * description / image are dropped when nothing resolves — never emitted empty.
 * Pages outside the dosage list output nothing; coexists with FAQPage /
 * BreadcrumbList as separate <script> tags.
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

	// description: the hero's machine-readable carrier comment. This copy used to
	// live in the hero's 18px subtitle paragraph; the minimal hero removed that
	// paragraph, so the sentence is carried as a comment instead — it stays in the
	// template (single source of truth, nothing hard-coded in PHP) and the schema
	// output is unchanged. The paragraph form stays as a fallback.
	$description = '';
	if (preg_match('/<!--\s*sf-schema-desc:\s*(.*?)\s*-->/s', $html, $d)) {
		$description = html_entity_decode(trim(wp_strip_all_tags($d[1])), ENT_QUOTES, 'UTF-8');
	} elseif (preg_match('/<p class="has-card-white-color[^"]*"[^>]*font-size:18px[^>]*>(.*?)<\/p>/s', $html, $d)) {
		$description = html_entity_decode(trim(wp_strip_all_tags($d[1])), ENT_QUOTES, 'UTF-8');
	}

	// image: this dosage form's own upload, resolved by file name. It used to be
	// "the page's first <img>", which was the hero carousel's first slide — with
	// the carousel gone that heuristic lands on a Related tile, i.e. a sibling
	// product's photo. Resolve by name instead, and prefer no image over a wrong
	// one (the key is dropped when nothing resolves).
	$image   = '';
	$uploads = wp_get_upload_dir();
	$own     = glob(trailingslashit($uploads['basedir']) . '*/*/' . $slug . '.webp');
	if ($own) {
		$image = esc_url_raw($uploads['baseurl'] . substr($own[0], strlen($uploads['basedir'])));
	} elseif (preg_match('#<img src="([^"]*/' . preg_quote($slug, '#') . '\.[a-z0-9]+)"#i', $html, $im)) {
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
		'@context' => 'https://schema.org',
		'@type'    => 'Product',
		'name'     => $name,
	);
	if ($description !== '') {
		$schema['description'] = $description;
	}
	if ($image !== '') {
		$schema['image'] = $image;
	}
	$schema += array(
		'brand'        => array('@type' => 'Brand', 'name' => 'SINO FRESH'),
		'manufacturer' => array('@type' => 'Organization', 'name' => 'Shandong SINO FRESH Pet Food Co., Ltd.'),
		'category'     => 'Pet Supplements',
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
		'@id'          => home_url('/#organization'), // referenced by the Service schema (services page) via provider.@id
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
	// Certifications held (updated 2026-09-17: FSSC 22000 supersedes the old
	// food-safety listing; HACCP and BRC added). Same six credentials are
	// rendered as HTML text in the front-page grid and the quality-page rows.
	$schema['hasCredential'] = array(
		array('@type' => 'EducationalOccupationalCredential', 'name' => 'FDA Registered',       'credentialCategory' => 'U.S. Food and Drug Administration'),
		array('@type' => 'EducationalOccupationalCredential', 'name' => 'cGMP Compliant',       'credentialCategory' => 'Current Good Manufacturing Practice'),
		array('@type' => 'EducationalOccupationalCredential', 'name' => 'ISO 9001 Certified',   'credentialCategory' => 'Quality Management System'),
		array('@type' => 'EducationalOccupationalCredential', 'name' => 'FSSC 22000 Certified', 'credentialCategory' => 'GFSI Recognized Food Safety System'),
		array('@type' => 'EducationalOccupationalCredential', 'name' => 'HACCP Certified',      'credentialCategory' => 'Hazard Analysis Critical Control Point'),
		array('@type' => 'EducationalOccupationalCredential', 'name' => 'BRC Certified',        'credentialCategory' => 'British Retail Consortium'),
	);
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

/**
 * Article JSON-LD (schema.org) for single posts.
 *
 * Built from the post itself (title, excerpt, dates, author, featured image)
 * rather than parsed out of the template, because every field is already
 * available through the post object. The image falls back to the configured
 * Site Logo when a post has no featured image, so the required `image`
 * property is never missing. Runs as its own <script> tag alongside the
 * BreadcrumbList / Organization schema — no key conflicts.
 */
/** sf_last_reviewed as ISO 8601, or '' when unset/unparseable. */
function sinofresh_reviewed_iso($post_id) {
	$reviewed = get_post_meta($post_id, 'sf_last_reviewed', true);
	if (!$reviewed || !strtotime((string) $reviewed)) {
		return '';
	}
	return gmdate('c', strtotime((string) $reviewed));
}

add_action('wp_head', function () {
	if (is_admin() || defined('REST_REQUEST') || !is_singular('post')) {
		return;
	}
	$post_id = (int) get_queried_object_id();
	$post    = $post_id ? get_post($post_id) : null;
	if (!$post) {
		return;
	}

	$permalink = get_permalink($post_id);

	$image = get_the_post_thumbnail_url($post_id, 'full');

	// Publisher logo is the configured Site Logo, never the article image;
	// when a post has no featured image the article `image` falls back to it.
	$logo = '';
	$logo_id = (int) get_theme_mod('custom_logo');
	if ($logo_id) {
		$logo = wp_get_attachment_image_url($logo_id, 'full');
	}
	if (!$image) {
		$image = $logo;
	}

	$sections = wp_get_post_terms($post_id, 'category', array('fields' => 'names'));
	$tags     = wp_get_post_terms($post_id, 'post_tag', array('fields' => 'names'));

	$schema = array(
		'@context'         => 'https://schema.org',
		'@type'            => 'Article',
		'mainEntityOfPage' => array('@type' => 'WebPage', '@id' => $permalink),
		'headline'         => html_entity_decode(get_the_title($post_id), ENT_QUOTES, 'UTF-8'),
		'description'      => html_entity_decode(wp_strip_all_tags(get_the_excerpt($post_id)), ENT_QUOTES, 'UTF-8'),
		'datePublished'    => get_the_date('c', $post_id),
		// sf_last_reviewed (date-only) wins when set: post_modified also moves
		// on unrelated admin touches, so it is not a reliable "content was
		// meaningfully updated" signal — same reason the visible meta row
		// prefers the field.
		'dateModified'     => sinofresh_reviewed_iso($post_id) ?: get_the_modified_date('c', $post_id),
		'author'           => array(
			'@type' => 'Person',
			'name'  => get_the_author_meta('display_name', (int) $post->post_author),
		),
		'publisher'        => array(
			'@type'         => 'Organization',
			'name'          => 'Shandong SINO FRESH Pet Food Co., Ltd.',
			'alternateName' => 'SINO FRESH',
		),
	);
	if ($image) {
		$schema['image'] = $image;
	}
	if ($logo) {
		$schema['publisher']['logo'] = array('@type' => 'ImageObject', 'url' => $logo);
	}
	if (!is_wp_error($sections) && $sections) {
		$schema['articleSection'] = array_values($sections);
	}
	if (!is_wp_error($tags) && $tags) {
		$schema['keywords'] = implode(', ', $tags);
	}
	echo "\n" . '<script type="application/ld+json">'
		. wp_json_encode($schema, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE)
		. "</script>\n";
}, 23);

/* Article feedback endpoint — up/down votes on single posts (toc-nav.js).
   Submits Gravity Forms Form 6 ("Feedback") server-side via GFAPI so no GF
   REST/AJAX endpoint has to be made public and no form embed is needed in
   the article markup. A plain vote is stored with just the vote; an optional
   email/description travels along when the visitor fills the mini form that
   opens on a down-vote. */
add_action('rest_api_init', function () {
	register_rest_route('sinofresh/v1', '/article-feedback', array(
		'methods'             => 'POST',
		'permission_callback' => '__return_true',
		'callback'            => function (WP_REST_Request $req) {
			if (!class_exists('GFAPI')) {
				return new WP_Error('sf_no_form', 'Feedback form unavailable.', array('status' => 503));
			}
			$vote = sanitize_key((string) $req->get_param('vote'));
			if (!in_array($vote, array('up', 'down'), true)) {
				return new WP_Error('sf_bad_vote', 'Invalid vote.', array('status' => 400));
			}
			$post_id = absint($req->get_param('post'));
			$email   = sanitize_email((string) $req->get_param('email'));
			$message = sanitize_textarea_field((string) $req->get_param('message'));
			if ($email && !is_email($email)) {
				return new WP_Error('sf_bad_email', 'Invalid email address.', array('status' => 400));
			}
			/* GFAPI::submit_form() runs the full form pipeline but showed
			 * non-deterministic validation state when driven outside a real
			 * page request (measured: identical payloads flip is_valid between
			 * requests). Form 6 has no notifications, confirmations or
			 * after_submission hooks, so add_entry() is behaviourally
			 * identical here AND deterministic — use it directly. */
			$entry = array(
				'form_id' => 6,
				'ip'      => isset($_SERVER['REMOTE_ADDR']) ? sanitize_text_field(wp_unslash($_SERVER['REMOTE_ADDR'])) : '',
				'1'       => 'General Feedback', // Form 6 field 1 (select) — closest match
				'2'       => 'Article feedback (' . $vote . ')' . ($post_id ? ': ' . get_the_title($post_id) : ''),
				'3'       => $message,
			);
			if ($email) {
				$entry['4'] = $email;
			}
			if ($req->get_param('consent')) {
				$entry['5.1'] = 'I agree to the Privacy Policy';
			}
			$entry_id = GFAPI::add_entry($entry);
			if (is_wp_error($entry_id)) {
				return new WP_Error('sf_gf_add', 'Could not store feedback.', array('status' => 500));
			}
			return array('ok' => true);
		},
	));
});

/* Gravity Forms — WhatsApp fallback hint under Form 2's submit button.
   Form 2 ("Get a Quote") is embedded by 10 templates (front page, contact,
   8 dosage pages), so the hint is injected here once instead of being pasted
   into every template. Scoped to form ID 2 via the per-form filter name —
   Form 3 (sample) and Form 4 (factory tour) must not show it.
   The hint is a full-width flex item: GF's foundation theme renders
   .gform_footer as a wrapping flex row, so `flex-basis:100%` puts it on its
   own line under the button. */
add_filter('gform_submit_button_2', function($button, $form) {
	return $button . '<p class="sf-gf-wa-hint">Prefer WhatsApp? Email us and we\'ll switch to WhatsApp.</p>';
}, 10, 2);

/* --------------------------------------------------------------------
   Security hardening (2026-09-18, audit refs R3 / Y6 / Y8).

   R3 — REST user enumeration. Logged-out requests can no longer list
   users (username + author-URL discovery for credential stuffing).
   Logged-in requests keep the full routes so the block editor and
   admin screens are untouched. /users/me still works for any request
   that carries a valid cookie, since that endpoint requires auth.
   -------------------------------------------------------------------- */
add_filter('rest_endpoints', function ($endpoints) {
	if (is_user_logged_in()) {
		return $endpoints;
	}
	foreach (array_keys($endpoints) as $route) {
		if (strpos($route, '/wp/v2/users') === 0) {
			unset($endpoints[$route]);
		}
	}
	return $endpoints;
});

/* Y6 — stop advertising the WordPress version in <meta name="generator">. */
remove_action('wp_head', 'wp_generator');

/* Y8 — disable the XML-RPC interface entirely (pingbacks included). */
add_filter('xmlrpc_enabled', '__return_false');

/**
 * Service JSON-LD (schema.org) — OEM/ODM Services page only.
 *
 * The provider references the Organization node via @id (stamped by the
 * Organization hook above), so search engines link both entities into one
 * graph. areaServed lists the core export markets. Fields must stay in sync
 * with the visible page copy (H1/hero) — same source of truth rule as the
 * FAQPage hook.
 */
add_action('wp_head', function () {
	if (is_admin() || defined('REST_REQUEST')) {
		return;
	}
	if (!is_page('services')) {
		return;
	}
	$schema = array(
		'@context'    => 'https://schema.org',
		'@type'       => 'Service',
		'name'        => 'Pet Supplement OEM/ODM Manufacturing',
		'description' => 'Contract manufacturing services for pet supplements — OEM, ODM, Contract Manufacturing, and Private Label. 8 dosage forms, flexible MOQ, FDA, cGMP, ISO 9001, FSSC 22000, HACCP, BRC.',
		'serviceType' => 'Pet Supplement Manufacturing',
		'provider'    => array('@id' => home_url('/#organization')),
		'areaServed'  => array('US', 'EU', 'JP', 'KR', 'BR', 'MX'),
	);
	echo "\n" . '<script type="application/ld+json">'
		. wp_json_encode($schema, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE)
		. "</script>\n";
}, 22);

/* --------------------------------------------------------------------
   Certificate gated download — Gravity Forms Form 5 ("Request COA").

   The Quality page's certificate buttons open a modal that fills the hidden
   `certificate` field (id 10) with a document key (fda / cgmp / iso9001 /
   iso22000 / haccp / brc / coa-sample). On submit the visitor gets a
   one-time download token (inc/cert-download.php) in the confirmation,
   and the same document by email with that same link as a fallback.

   Hook order: GF 3.1 resolves the confirmation inside
   GFFormDisplay::process_form() *before* firing gform_after_submission
   (handle_submission() is called first, the action after it). The grant is
   therefore memoised per entry, so whichever hook runs first mints the
   token and the other reuses it — the emailed link and the button in the
   browser are always the exact same one-time token.

   No Gravity Forms settings screen is involved: Form 5 has no confirmation
   or notification configured, and both the confirmation markup and the
   customer email are produced here.
   -------------------------------------------------------------------- */

/** Resolve — and memoise — the download grant for one submission. */
function sinofresh_cert_grant($entry) {
	static $grants = array();

	$entry_id = (int) rgar($entry, 'id');
	if (isset($grants[$entry_id])) {
		return $grants[$entry_id];
	}

	$certs = sinofresh_cert_files();
	$cert  = sanitize_key((string) rgar($entry, '10'));
	if (!isset($certs[$cert])) {
		$cert = 'coa-sample'; // fallback for the page's generic "Request COA" buttons
	}
	$path  = sinofresh_cert_file_path($cert, $certs[$cert]);
	$email = sanitize_email((string) rgar($entry, '3'));
	$token = sinofresh_cert_mint_token($cert, $email);

	$grants[$entry_id] = array(
		'cert'     => $cert,
		'label'    => sinofresh_cert_label($cert),
		'email'    => $email,
		'name'     => trim((string) rgar($entry, '2')),
		'url'      => $token ? sinofresh_cert_download_url($cert, $token) : '',
		'has_file' => ('' !== $path && is_readable($path)),
		'path'     => $path,
		'download' => $certs[$cert]['download'],
	);
	return $grants[$entry_id];
}

/* Confirmation: replaces Form 5's (unconfigured) default message. The markup
   is what the modal shows in its success state; the JSON payload in
   data-payload is what the front-end reads (B4), and the plain <a> keeps the
   form usable with JavaScript disabled. */
add_filter('gform_confirmation_5', function ($confirmation, $form, $entry, $ajax) {
	$g = sinofresh_cert_grant($entry);
	if (empty($g['url'])) {
		return $confirmation;
	}

	$payload = array(
		'download_url'  => $g['has_file'] ? $g['url'] : '',
		'email_sent_to' => $g['email'],
		'certificate'   => $g['cert'],
		'label'         => $g['label'],
		'attached'      => (bool) $g['has_file'],
	);

	$card = '<div class="sf-cert-result" data-payload="' . esc_attr(wp_json_encode($payload)) . '"'
		. ' data-download-url="' . esc_attr($payload['download_url']) . '"'
		. ' data-email-sent-to="' . esc_attr($g['email']) . '">'
		. '<p class="sf-cert-result__title">Request received.</p>';

	if ($g['has_file']) {
		$card .= '<p class="sf-cert-result__note">' . esc_html($g['label'])
			. ' is attached to the email we just sent to <strong>' . esc_html($g['email']) . '</strong>.</p>'
			. '<p class="sf-cert-result__cta"><a class="sf-cert-result__btn" href="' . esc_url($g['url']) . '">Download now</a></p>'
			. '<p class="sf-cert-result__fine">The download link is valid for 24 hours and can be used once.</p>';
	} else {
		$card .= '<p class="sf-cert-result__note">' . esc_html($g['label'])
			. ' is not published on the website — our team will email it to <strong>' . esc_html($g['email'])
			. '</strong> within one business day.</p>';
	}
	$card .= '</div>';

	/* This filter replaces GF's confirmation markup wholesale, and that markup
	   is not only the message: handle_confirmation() builds

	     <div id='gf_{id}' class='gform_anchor'>…</div>
	     <div id='gform_confirmation_wrapper_{id}'>
	       <div id='gform_confirmation_message_{id}'>…message…</div>
	     </div>

	   and the page's inline postback handler depends on both extra nodes. It
	   scrolls with jQuery('#gf_5').offset() and, when the anchor is missing,
	   throws there — which aborted the handler before it cleared
	   gf_submitting_5 (so the next submit was swallowed) and before it
	   announced the message. #gform_confirmation_message_5 is what
	   wp.a11y.speak() reads. The three nodes are rebuilt here around our own
	   card, which is unchanged. */
	return '<div id="gf_5" class="gform_anchor" tabindex="-1"></div>'
		. '<div id="gform_confirmation_wrapper_5" class="gform_confirmation_wrapper">'
		. '<div id="gform_confirmation_message_5" class="gform_confirmation_message">'
		. $card
		. '</div></div>';
}, 10, 4);

/* Customer email + sales copy. The lead must survive a bad customer address,
   so sales always receives a copy — as the Cc of the customer email, or as
   the sole recipient when the address is unusable. */
add_action('gform_after_submission_5', function ($entry, $form) {
	$g = sinofresh_cert_grant($entry);
	if (empty($g['url'])) {
		return;
	}

	$sales    = 'sales@zxpet.com';
	$has_mail = !empty($g['email']) && is_email($g['email']);

	/* Attach under the friendly name the visitor should keep. */
	$attachments = array();
	$tmp_dir     = '';
	if ($g['has_file'] && $g['download']) {
		$tmp_dir  = trailingslashit(get_temp_dir()) . 'sf-cert-' . uniqid();
		$tmp_file = $tmp_dir . '/' . $g['download'];
		if (wp_mkdir_p($tmp_dir) && @copy($g['path'], $tmp_file)) {
			$attachments[] = $tmp_file;
		} else {
			$tmp_dir = '';
		}
	}

	if ($has_mail) {
		$subject = 'Your SINO FRESH Certificate — ' . $g['label'];
		$lines   = array(
			$g['name'] !== '' ? 'Dear ' . $g['name'] . ',' : 'Hello,',
			'',
			'Thank you for your interest in SINO FRESH. '
				. ($attachments
					? $g['label'] . ' is attached to this email.'
					: 'Our team is preparing ' . $g['label'] . ' and will send it to you within one business day.'),
			'',
		);
		if ($g['has_file']) {
			$lines[] = 'You can also download it here (valid for 24 hours, one use):';
			$lines[] = $g['url'];
			$lines[] = '';
		}
		$lines[] = 'If you need anything else — a batch-specific COA, specification sheets or a full compliance package — just reply to this email.';
		$lines[] = '';
		$lines[] = 'Best regards,';
		$lines[] = 'Sales Team';
		$lines[] = 'Shandong SINO FRESH Pet Food Co., Ltd.';
		$lines[] = 'info@zxpet.com · +86 539 866 9539 · zxpet.com';
		$sent    = wp_mail($g['email'], $subject, implode("\n", $lines), array('Cc: ' . $sales), $attachments);
	} else {
		$subject = 'Certificate request without a usable email — ' . $g['label'];
		$lines   = array(
			'A certificate request came in without a usable customer address.',
			'',
			'Company: ' . (string) rgar($entry, '1'),
			'Contact: ' . (string) rgar($entry, '2'),
			'Email on the entry: ' . (string) rgar($entry, '3'),
			'Country: ' . (string) rgar($entry, '4'),
			'Document: ' . $g['label'] . ' (' . $g['cert'] . ')',
			'',
			'Download link: ' . $g['url'],
		);
		$sent    = wp_mail($sales, $subject, implode("\n", $lines), array(), $attachments);
	}

	if ($tmp_dir) {
		foreach ($attachments as $file) {
			wp_delete_file($file);
		}
		@rmdir($tmp_dir);
	}

	/* Visibility from the entry screen: what they asked for, the link that was
	   issued, and whether the mail actually left. */
	gform_update_meta($entry['id'], 'sf_cert_document', $g['cert'], 5);
	gform_update_meta($entry['id'], 'sf_cert_download_url', $g['url'], 5);
	gform_update_meta($entry['id'], 'sf_cert_mail', $sent ? 'sent' : 'failed', 5);
}, 10, 2);

/**
 * 59. Inquiry conversion tracking (GA4 generate_lead).
 *
 * Order matters here: GF 3.1 runs handle_submission() (which builds the
 * confirmation and fires gform_confirmation) BEFORE gform_after_submission,
 * so a payload captured in gform_after_submission would arrive too late.
 * The payload is therefore derived from ($entry, $form) inside the
 * confirmation filters themselves; gform_after_submission only records the
 * same snapshot on $GLOBALS for debugging / other consumers.
 *
 * Scope: forms 2-5 only — the Feedback form 6 is not an inquiry. Form 5's
 * certificate flow lives in versioned hooks above and is untouched; because
 * gf_apply_filters runs 'gform_confirmation' before 'gform_confirmation_5',
 * the script for form 5 is appended by a separate priority-20 listener on
 * the versioned hook, after the cert flow has built its confirmation.
 *
 * The inline script reads sf_cookie_consent (the site's own consent banner
 * storage) and fires gtag('event', 'generate_lead', ...) only when the
 * visitor accepted analytics; without gtag (Local, or GA4 not yet connected)
 * it silently no-ops. No PII is sent: form id, form title, dosage form
 * choice, source page URL.
 */
if (!function_exists('sinofresh_lead_payload')) {
	/**
	 * Build the conversion payload for one lead. The dosage select is field 7
	 * on forms 2/3, 11 on form 4 and 6 on form 5; matching on the label keeps
	 * this alive if ids ever shift.
	 *
	 * @param array $entry GF entry.
	 * @param array $form  GF form.
	 * @return array
	 */
	function sinofresh_lead_payload($entry, $form) {
		$dosage = '';
		foreach ($form['fields'] as $field) {
			if (false !== stripos((string) rgar($field, 'label'), 'Dosage Form')) {
				$dosage = (string) rgar($entry, (string) rgar($field, 'id'));
				break;
			}
		}
		return array(
			'form_id'         => (string) rgar($form, 'id'),
			'form_title'      => (string) rgar($form, 'title'),
			'dosage'          => $dosage,
			'form_source_url' => isset($_SERVER['HTTP_REFERER']) ? esc_url_raw(wp_unslash($_SERVER['HTTP_REFERER'])) : '',
		);
	}
}

if (!function_exists('sinofresh_lead_tracking_script')) {
	/**
	 * Build the consent-gated inline script for one lead. Returns an empty
	 * string when there is nothing to send (not an inquiry form, or a form id
	 * mismatch with the confirmation being filtered).
	 *
	 * @param array $entry   GF entry.
	 * @param array $form    GF form.
	 * @return string
	 */
	function sinofresh_lead_tracking_script($entry, $form) {
		$form_id = (int) rgar($form, 'id');
		if (!in_array($form_id, array(2, 3, 4, 5), true)) {
			return '';
		}
		$json = wp_json_encode(sinofresh_lead_payload($entry, $form));
		return '<script>(function(){try{var c=null;'
			. 'try{c=JSON.parse(localStorage.getItem("sf_cookie_consent")||"null");}catch(e){}'
			. 'if(!c||c.analytics!==true)return;'
			. 'if(typeof window.gtag!=="function")return;'
			. 'window.gtag("event","generate_lead",' . $json . ');'
			. '}catch(e){}})();</script>';
	}
}

add_action('gform_after_submission', function ($entry, $form) {
	if (!in_array((int) rgar($form, 'id'), array(2, 3, 4, 5), true)) {
		return;
	}
	$GLOBALS['sf_lead_payload'] = sinofresh_lead_payload($entry, $form);
}, 10, 2);

add_filter('gform_confirmation', function ($confirmation, $form, $entry, $ajax) {
	/* Form 5 appends after its certificate flow on the versioned hook below. */
	if (5 === (int) rgar($form, 'id') || !is_string($confirmation)) {
		return $confirmation;
	}
	return $confirmation . sinofresh_lead_tracking_script($entry, $form);
}, 10, 4);

/* Form 5: run after the certificate-flow confirmation builder (priority 10) so
   the script is appended to whatever that flow returned, never replacing it. */
add_filter('gform_confirmation_5', function ($confirmation, $form, $entry, $ajax) {
	if (!is_string($confirmation)) {
		return $confirmation;
	}
	return $confirmation . sinofresh_lead_tracking_script($entry, $form);
}, 20, 4);

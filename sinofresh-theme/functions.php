<?php
/* Configurator PDF summary endpoint (POST /wp-json/sinofresh/v1/config-pdf).
   Dompdf itself lives in wp-content/vendor/ — LAUNCH CHECKLIST: vendor/ must
   be shipped with the site or the endpoint answers 503. */
require get_template_directory() . '/inc/config-pdf.php';

/* Gated certificate downloads (GET /wp-json/sinofresh/v1/cert-download).
   Full-resolution certificates live outside the document root — see
   SF_CERTS_DIR in inc/cert-download.php for the production path. */
require get_template_directory() . '/inc/cert-download.php';

/* Batch H1 — the formula publishing form (admin) and its option pools.
   Admin-only for now: nothing here renders a front-end byte. */
require get_template_directory() . '/inc/formula-pools.php';
require get_template_directory() . '/inc/formula-admin.php';

/* Withdrawn ZH locale: 301 the /zh/ URLs while publish-languages holds no
   zh_CN, so no indexed Chinese URL becomes a dead end. Reads the option rather
   than a constant, which is what lets it retire itself once the translations
   exist — see "reattaching ZH" in docs/zh-unpublish-scan-2026-09-24.md. */
require get_template_directory() . '/inc/zh-unpublish.php';

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
	wp_enqueue_style('sinofresh-style', get_stylesheet_uri(), array(), '2.10.81');
	// Sticky nav: every template renders parts/header.html, so this is site-wide.
	wp_enqueue_script('sinofresh-sticky-header', get_template_directory_uri() . '/assets/js/sticky-header.js', array(), '1.0.0', true);
	/* Consent decisions are now versioned + time-boxed and bridged into WP
	   Consent API, so the file itself changed: its own literal moves 1.0.0 ->
	   1.1.0 (static assets are served immutable for a year, so without a
	   changed URL returning browsers would keep the old copy). */
	wp_enqueue_script('sinofresh-ui-components', get_template_directory_uri() . '/assets/js/ui-components.js', array(), '1.2.0', true);
	// Mobile nav: collapse the overlay's submenus until their chevron is tapped.
	wp_enqueue_script('sinofresh-mobile-nav', get_template_directory_uri() . '/assets/js/mobile-nav.js', array(), '1.1.0', true);
	// Quote CTA smart scroll: in-page form -> smooth scroll, else native /contact/#quote.
	wp_enqueue_script('sinofresh-quote-cta', get_template_directory_uri() . '/assets/js/quote-cta.js', array(), '1.0.0', true);
	/* Inquiry dialog (batch H4): the capsule is rendered by [sf_inquiry_button]
	   and the markup by sinofresh_inquiry_modal(), both only on a formula
	   detail page, so the script follows the same condition. Two scripts have
	   already been deleted for being enqueued where they had nothing to do
	   (H2b2), and this one has nothing to do on the other 33 pages. */
	if (is_singular('sf_formula')) {
		wp_enqueue_script('sinofresh-inquiry', get_template_directory_uri() . '/assets/js/inquiry.js', array(), '1.2.0', true);
		/* Batch H7d: the configurator's choices and the dialog's panel are the
		   same list seen twice, so the two scripts are enqueued together and
		   conditionally together — on the other 33 pages there is no band to
		   configure and no dialog to carry a selection into. */
		wp_enqueue_script('sinofresh-config', get_template_directory_uri() . '/assets/js/config.js', array(), '1.4.0', true);
	}
	// On-this-page TOC (dot rail on marketing pages, text list on articles) +
	// article extras (progress bar, inline CTA, feedback, print URL). The JS
	// self-selects its mode: body.single-post gets the article feature set,
	// marketing pages keep the dot rail. JS no-ops with < 3 H2s for the TOC.
	if (is_front_page() || is_page(array('quality', 'about', 'services', 'oem', 'odm', 'contract-manufacturing', 'private-label', 'factory-tour', 'soft-chews', 'tablets', 'powders', 'pastes', 'drops', 'liquids', 'fish-oil', 'dental-chews')) || is_singular('post')) {
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
		wp_enqueue_script('sinofresh-cert-modal', get_template_directory_uri() . '/assets/js/cert-modal.js', array(), '1.3.0', true);
	}
});

add_action('wp_enqueue_scripts', function() {
	// Block theme template hierarchy resolves page-{slug}.html by page slug, which
	// does not set the wp_page_template meta — so check the page slug as well.
	$dosage_pages = ['soft-chews', 'tablets', 'powders', 'pastes', 'drops', 'liquids', 'fish-oil', 'dental-chews'];
	$is_dosage_page = is_page($dosage_pages) || is_page_template(array_map(fn($s) => "page-$s", $dosage_pages));
	// Product gallery: builds the thumbnail strip under the main photo of the
	// formula detail band and drives the [Photos][Video] switch beside it.
	// Step 2 put that band on the eight dosage pages and hung the script there;
	// Step 3 moved the band to the 21 detail pages, so the script follows it.
	// Absent, the band still shows the main photo — that is the no-JS contract,
	// not a fallback path; the switch stays hidden with it.
	if (is_singular('sf_formula')) {
		wp_enqueue_script('sinofresh-formula-gallery', get_template_directory_uri() . '/assets/js/formula-gallery.js', array(), '2.2.0', true);
	}
	// Standard Formulas CTAs (K1): the card grid on the eight dosage pages,
	// the same 21-card grid on the sf_formula archive, and — since batch H7b
	// — only the sibling cards on a formula detail page. It was already
	// independent of the configurator (batch H2b2 deleted that); batch H6 then
	// dropped the scroll target with it, because no template carries an
	// #configurator any more — the handler copies the formula name and does
	// nothing else. H7b moved the detail page's hero CTA to the inquiry dialog,
	// so this file now skips any CTA carrying data-sf-inquiry-open: the script
	// is still enqueued there for the sibling cards, which keep the copy.
	if ($is_dosage_page || is_singular('sf_formula') || is_post_type_archive('sf_formula')) {
		wp_enqueue_script('sinofresh-formulas', get_template_directory_uri() . '/assets/js/formulas.js', array(), '1.3.0', true);
	}
	// Archive-only: the dosage-form filter bar on /formulas/. Nothing else on
	// the site renders [sf_formula_filters], so nothing else pays for it.
	if (is_post_type_archive('sf_formula')) {
		wp_enqueue_script('sinofresh-formula-filter', get_template_directory_uri() . '/assets/js/formula-filter.js', array(), '1.0.0', true);
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
 * Archive post count (templates/archive.html and archive-sf_formula.html hero).
 *
 * Block templates run do_shortcode() before do_blocks(), so a raw shortcode
 * inside a wp:html block resolves in templates without extra wiring.
 *
 * noun picks the counted thing from a closed set: 'article' (default) or
 * 'formula'. The two _n() calls stay literal inside the switch on purpose —
 * a composed msgid ("%d " . $noun) could never be translated, and each arm
 * needs its own translators comment. 2C Step2 added the attribute; until
 * then this was an anonymous closure with no parameters at all, so
 * noun="formula" was silently discarded and the archive said "21 articles".
 * The default keeps /blog/ and every term archive on the original output.
 */
function sinofresh_archive_count($atts = array()) {
	global $wp_query;
	$atts  = shortcode_atts(array('noun' => 'article'), $atts, 'sf_archive_count');
	$found = isset($wp_query->found_posts) ? (int) $wp_query->found_posts : 0;
	switch (sanitize_key($atts['noun'])) {
		case 'formula':
			/* translators: %d: number of formulas. */
			$label = sprintf(_n('%d formula', '%d formulas', $found, 'sinofresh'), $found);
			break;
		default:
			/* translators: %d: number of articles. */
			$label = sprintf(_n('%d article', '%d articles', $found, 'sinofresh'), $found);
			break;
	}
	return esc_html($label);
}
add_shortcode('sf_archive_count', 'sinofresh_archive_count');

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
		'sf_formula_base'        => 'Base / carrier, for the "Ingredients & composition" band on the formula detail page. Empty on all 21 records today.',
		'sf_formula_other_ingredients' => 'Other ingredients, for the "Ingredients & composition" band on the formula detail page. Empty on all 21 records today.',
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
 *
 * The one view where that fallback is wrong is the sf_formula archive itself
 * (2C Step2). /formulas/ queries a WP_Post_Type, so the fallback read the
 * last segment — "formulas", or the page number on /formulas/page/2/ — and
 * the grid filtered on a term that does not exist: zero cards, no error, no
 * way to tell it apart from "no formulas yet". An archive is not a dosage
 * form, so the guard below returns '' and the grid lists all 21.
 */
function sinofresh_formula_current_form($form) {
	$form = sanitize_title($form);
	if ($form !== '') {
		return $form;
	}
	if (is_post_type_archive('sf_formula')) {
		return '';
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
 * 待办17 — the card badge vocabulary. One map, three values, and it is the
 * only place the wording lives: the admin dropdown is built from its keys and
 * the front-end modifier class from its values, so a badge can never be
 * selectable in the editor and unstyled on the card, or vice versa.
 *
 * The stored meta value is the LABEL ("Best Seller"), matching how every other
 * single-choice field in this theme stores its answer (sf_formula_shape,
 * sf_formula_lifestage, … store the term the editor clicked). The class suffix
 * is separate because "Best Seller" is not a class name. An unset, unknown or
 * hand-edited value resolves to NO badge rather than to a badge with an
 * unstyleable class — see sinofresh_formula_card_badge().
 */
function sinofresh_formula_card_badges() {
	return array(
		'Best Seller' => 'best-seller',
		'Hot'         => 'hot',
		'New'         => 'new',
	);
}

/**
 * The badge of one formula, as array('label' => …, 'slug' => …) or array().
 *
 * Whitelist, not passthrough: the meta is editable through the REST API and the
 * custom-fields panel, so a value this theme does not know is dropped here
 * rather than printed as `sf-fcard__badge--<whatever>` in the class attribute.
 * A discarded value is also the reason the caller must treat array() and a
 * missing key identically — the card renders without an overlay, which is the
 * same thing it does for the empty answer "none".
 */
function sinofresh_formula_card_badge($post_id) {
	$map = sinofresh_formula_card_badges();
	$raw = trim((string) get_post_meta($post_id, 'sf_formula_card_badge', true));
	if ($raw === '' || !isset($map[$raw])) {
		return array();
	}
	return array('label' => $raw, 'slug' => $map[$raw]);
}

/**
 * The badge element, or '' when the record has none.
 *
 * $inline is the card-without-a-still placement: the badge sits at the head of
 * __body instead of on an image that does not exist. It is a modifier class
 * rather than a second element so both placements share one colour rule and the
 * E2E can assert "a badge is present" without caring which one it is.
 */
function sinofresh_formula_badge_markup($badge, $inline = false) {
	if (!$badge) {
		return '';
	}
	return sprintf(
		'<span class="sf-fcard__badge sf-fcard__badge--%s%s">%s</span>',
		esc_attr($badge['slug']),
		$inline ? ' sf-fcard__badge--inline' : '',
		esc_html($badge['label'])
	);
}

/**
 * One value of a dosage page's .sf-facts-mini core-facts row, by data-label.
 *
 * The formula detail hero needs the MOQ and the lead time of the dosage form
 * the formula belongs to. Both exist as value spans of the .sf-facts-mini row
 * on /products/<form>/ (batch F1 re-established what the sf-spectable table
 * fed before 2D-E deleted it), so the hero reads them from that template file
 * instead of restating them — same single-source-of-truth rule the FAQPage,
 * BreadcrumbList and Product schema generators follow. Editing the row on
 * the dosage page updates every formula hero of that form.
 *
 * $label is the data-label attribute ("MOQ", "Lead time"), not the visible
 * label text, because data-label is the stable machine-readable twin of the
 * visible label (it also survives a wording change to the row's labels).
 *
 * The lookup is scoped to the .sf-facts-mini block, not the whole page: a
 * second data-label anywhere else on the page must never shadow the value.
 *
 * Returns a decoded string; callers escape per context. Memoised per
 * form+label, and returns '' for anything it cannot resolve so the caller
 * can drop the clause rather than print an empty "MOQ".
 */
function sinofresh_formula_spec_cell($form, $label) {
	$form  = sanitize_title($form);
	$label = (string) $label;
	if ($form === '' || $label === '') {
		return '';
	}
	static $cache = array();
	$key = $form . '|' . $label;
	if (array_key_exists($key, $cache)) {
		return $cache[$key];
	}
	$cache[$key] = '';

	$file = get_stylesheet_directory() . '/templates/page-' . $form . '.html';
	if (!file_exists($file)) {
		return '';
	}
	$html = (string) file_get_contents($file);
	/* Scope to the .sf-facts-mini row (batch F1's replacement for the
	   sf-spectable table): the band's wp:html wrapper is consumed by the
	   renderer, so the template carries the section verbatim. Non-greedy on
	   both spans — the row holds no nested section and the page must never
	   gain one inside it. */
	if (preg_match('/<section class="sf-facts-mini">(.*?)<\/section>/s', $html, $band)
		&& preg_match('/data-label="' . preg_quote($label, '/') . '"[^>]*>(.*?)<\/span>/s', $band[1], $m)) {
		$cache[$key] = html_entity_decode(trim(wp_strip_all_tags($m[1])), ENT_QUOTES, 'UTF-8');
	}
	return $cache[$key];
}

/**
 * The three facts buried in a formula's one-line sf_formula_specs value.
 *
 * The meta is free text with " · " separators, and it is NOT uniform: ten
 * records carry three segments (unit / pack / shelf life), eleven carry two
 * (unit / combined pack-and-shelf-life), so a positional reader takes the
 * shelf life as the pack options on those eleven. Fields are therefore taken
 * by KEY REGEX, never by index:
 *
 *   shelf  the segment matching /\d+ months? shelf life/
 *   pack   of what is left, the segment matching /\sper\s/
 *   unit   the first segment that is left
 *
 * The pack pattern needs the surrounding whitespace. A bare /per (bottle|...)/ 
 * also matches the "per bottle" inside "dropper bottle", measured on this data
 * as two false positives out of twelve hits; /\sper\s/ gives the true ten.
 *
 * Returns '' for anything it cannot find, so callers drop the row rather than
 * print an empty "Pack options". (Decision I: the eleven records without a
 * pack segment show four rows, the ten with one show five. Substituting the
 * packaging formats there would put container names under a quantity label.)
 */
function sinofresh_formula_specs_parts($specs) {
	$parts = array('unit' => '', 'pack' => '', 'shelf' => '');
	$specs = trim((string) $specs);
	if ($specs === '') {
		return $parts;
	}
	$segments = array();
	foreach (explode('·', $specs) as $segment) {
		$segment = trim($segment);
		if ($segment !== '') {
			$segments[] = $segment;
		}
	}
	$rest = array();
	foreach ($segments as $segment) {
		if ($parts['shelf'] === '' && preg_match('/\d+\s*months?\s+shelf\s+life/i', $segment)) {
			$parts['shelf'] = $segment;
			continue;
		}
		$rest[] = $segment;
	}
	$unit = array();
	foreach ($rest as $segment) {
		if ($parts['pack'] === '' && preg_match('/\sper\s/i', $segment)) {
			$parts['pack'] = $segment;
			continue;
		}
		$unit[] = $segment;
	}
	if ($unit) {
		$parts['unit'] = $unit[0];
	}
	return $parts;
}

/**
 * The intro paragraph of a formula's media column.
 *
 * Same wording root as the Product schema's description on this page
 * (wp_head, sf_formula Product): the first sentence is the same sentence, so
 * the visible copy and the structured data cannot drift apart. It is not the
 * same function on purpose — the schema generator's output is covered by the
 * JSON-LD gate, which must stay at zero change, and a shared function would
 * put this batch inside that path.
 *
 * sf_formula_intro (post meta) overrides the whole paragraph when set. That
 * is the slot the 21 real product blurbs go into later; until then every
 * record renders the template, which is why the template must read as a
 * finished sentence rather than a stub.
 *
 * {moq} and {lead_time} are the dosage page's own values (spec_cell is the
 * single source): a missing one drops its clause instead of printing an
 * empty label, the same rule {{FORMULA_META}} follows. Both values are
 * transcribed verbatim, so the sentence is built as "Label: value." rather
 * than "a minimum order of {moq}" — the values already read as clauses
 * ("from 500-1,000 units"), and glueing prepositions on would produce
 * "a minimum order of from 500-1,000 units".
 */
function sinofresh_formula_intro($post_id = 0) {
	$post_id = (int) $post_id;
	if ($post_id <= 0) {
		$post_id = (int) get_queried_object_id();
	}
	if ($post_id <= 0 || get_post_type($post_id) !== 'sf_formula') {
		return '';
	}
	$override = trim((string) get_post_meta($post_id, 'sf_formula_intro', true));
	if ($override !== '') {
		return $override;
	}
	$name = html_entity_decode((string) get_the_title($post_id), ENT_QUOTES, 'UTF-8');
	if ($name === '') {
		return '';
	}
	$form_slug  = '';
	$form_label = '';
	$form_terms = wp_get_post_terms($post_id, 'sf_formula_form');
	if (!is_wp_error($form_terms) && $form_terms) {
		$form_slug  = (string) $form_terms[0]->slug;
		$form_label = sinofresh_formula_label($form_terms[0]->slug, $form_terms[0]->name);
	}
	$text = $form_label !== ''
		? sprintf('%s is a standard %s formula from the SINO FRESH OEM/ODM range for private-label pet supplements.', $name, $form_label)
		: sprintf('%s is a standard formula from the SINO FRESH OEM/ODM range for private-label pet supplements.', $name);
	$text .= ' Produced in a GMP-certified facility in Linyi, China and shipped with full documentation, '
		. 'it is ready for your own brand.';
	if ($form_slug !== '') {
		$moq = sinofresh_formula_spec_cell($form_slug, 'MOQ');
		if ($moq !== '') {
			$text .= ' Minimum order quantity: ' . $moq . '.';
		}
		$lead = sinofresh_formula_spec_cell($form_slug, 'Lead time');
		if ($lead !== '') {
			$text .= ' Lead time: ' . $lead . '.';
		}
	}
	return $text;
}

/**
 * The nine question/answer pairs of a formula's FAQ band (batch C).
 *
 * The dosage pages answer "what about this dosage form"; this band answers
 * "what about THIS formula", so it is a different set of nine. Where the two
 * overlap they share the wording, not merely the meaning: the sampling fee and
 * turnaround, the certification list and the confidentiality promise are the
 * sentences /faq/ already publishes, so the site cannot end up contradicting
 * itself about its own commercial terms.
 *
 * Three answers carry a value, and each value is read from the single source
 * the rest of the page already reads:
 *
 *   Certifications      the dosage page's .sf-facts-mini row, through
 *                       sinofresh_formula_spec_cell() — the {{FORMULA_META}}
 *                       source, not a second copy
 *   Packaging formats   the same row (batch G's fourth item)
 *   the record's title  get_the_title()
 *
 * A value that cannot be resolved drops its clause instead of printing an
 * empty label, the rule {{FORMULA_META}} and sinofresh_formula_intro() follow.
 * That is why the packaging answer is written as an optional LEADING sentence:
 * it has to read as finished with and without the value.
 *
 * sf_formula_faq (post meta) overrides the whole set when it parses to two or
 * more usable pairs. The format is plain text because the slot is edited by
 * hand in wp-admin, one question line with its answer under it, repeated:
 *
 *   Q: question
 *   A: answer, continued on following lines until the next Q:
 *
 * A malformed override falls back to the generated set rather than shipping a
 * half-empty accordion, and says so in the PHP error log. Like
 * sf_formula_intro this key is deliberately left unregistered: the record type
 * supports custom-fields, which is the same editing route the intro uses.
 *
 * Returns RAW (decoded) text, never HTML. sinofresh_formula_faq() escapes it
 * for the page and the FAQPage generator takes it verbatim, which is what
 * keeps the structured data free of HTML entities — and both readers share
 * this one function, so the accordion and the schema cannot drift apart.
 */
function sinofresh_formula_faq_data($post_id = 0) {
	$post_id = (int) $post_id;
	if ($post_id <= 0) {
		$post_id = (int) get_queried_object_id();
	}
	if ($post_id <= 0 || get_post_type($post_id) !== 'sf_formula') {
		return array();
	}

	/* Whole-set override. Answers may run over several lines; a line that is
	   neither Q: nor A: continues the answer it is under, and a Q: with no
	   answer at all is dropped rather than shipped as an empty <details>. */
	$raw = (string) get_post_meta($post_id, 'sf_formula_faq', true);
	if (trim($raw) !== '') {
		$pairs    = array();
		$question = '';
		$answer   = array();
		foreach (preg_split('/\R/u', $raw) as $line) {
			$line = trim((string) $line);
			if ($line === '') {
				continue;
			}
			if (preg_match('/^Q\s*:\s*(.+)$/iu', $line, $m)) {
				if ($question !== '' && $answer) {
					$pairs[] = array('q' => $question, 'a' => implode(' ', $answer));
				}
				$question = trim($m[1]);
				$answer   = array();
				continue;
			}
			if (preg_match('/^A\s*:\s*(.+)$/iu', $line, $m)) {
				$answer[] = trim($m[1]);
				continue;
			}
			if ($question !== '' && $answer) {
				$answer[] = $line;
			}
		}
		if ($question !== '' && $answer) {
			$pairs[] = array('q' => $question, 'a' => implode(' ', $answer));
		}
		if (count($pairs) >= 2) {
			return $pairs;
		}
		error_log(sprintf(
			'[sinofresh] sf_formula_faq: post %d override parsed to %d pair(s), '
			. 'below the two a FAQPage needs; using the generated set.',
			$post_id, count($pairs)
		));
	}

	$name = trim(wp_strip_all_tags((string) get_the_title($post_id)));
	$form_slug  = '';
	$form_terms = wp_get_post_terms($post_id, 'sf_formula_form');
	if (!is_wp_error($form_terms) && $form_terms) {
		$form_slug = (string) $form_terms[0]->slug;
	}
	$certs = sf_formula_certifications_value($form_slug);
	$pack  = $form_slug !== '' ? sinofresh_formula_spec_cell($form_slug, 'Packaging formats') : '';

	$pairs = array();

	$pairs[] = array(
		'q' => 'Can the active ingredients be changed?',
		'a' => 'Yes. This is a starting point rather than a fixed recipe: we can adjust the '
		     . 'levels, swap one active for another, or add new ones, and the specification '
		     . 'and the label are rewritten to match.',
	);

	$pairs[] = array(
		'q' => 'Can the flavour be changed?',
		'a' => 'Yes. The flavour profile is chosen with you for your target market, including '
		     . 'a profile you already sell.',
	);

	$pairs[] = array(
		'q' => 'Is a gluten-free or grain-free version available?',
		'a' => 'Yes. Wheat, gluten and grain carriers can be left out of the recipe, and the '
		     . 'change is recorded in the specification and in the Certificate of Analysis.',
	);

	$pairs[] = array(
		'q' => 'Is this formula for dogs or for cats?',
		'a' => 'Our formulas can be customised for dogs, cats, or both. Tell us your target '
		     . 'species when you enquire and we will adjust the formula, the dosage, and the '
		     . 'label accordingly.',
	);

	$pairs[] = array(
		'q' => 'Can I sample this formula before ordering?',
		'a' => 'Yes. The sample is made to the same specification as the bulk order: sampling '
		     . 'takes 3–7 working days for a standard formula, and the $200 sampling fee '
		     . 'is deducted from your bulk order.',
	);

	$answer = '';
	if ($certs !== '') {
		$answer .= 'Certifications: ' . $certs . '. ';
	}
	$answer .= 'Every batch is tested in our QC laboratory and ships with a Certificate of '
	         . 'Analysis, and we support FDA, EU and other target-market documentation.';
	$pairs[] = array(
		'q' => 'What certifications and documentation do you provide?',
		'a' => $answer,
	);

	$answer = '';
	if ($pack !== '') {
		$answer .= 'Standard formats for this dosage form: ' . $pack . '. ';
	}
	$answer .= 'The label, the carton and the barcode are all produced with your own brand '
	         . 'on them.';
	$pairs[] = array(
		'q' => 'Can the packaging and the label be customised?',
		'a' => $answer,
	);

	$pairs[] = array(
		'q' => 'How should the finished product be stored?',
		'a' => 'Store in a cool, dry place, away from direct sunlight. Once opened, keep the '
		     . 'container tightly closed and use within the recommended period.',
	);

	$pairs[] = array(
		'q' => 'Will you keep my formula and my brand confidential?',
		'a' => 'Yes — every formula is produced exclusively under your own brand. We never '
		     . 'sell your formula, your artwork, or your customer list to any third party, '
		     . 'and we sign an NDA before sharing any custom formulation details.',
	);

	return $pairs;
}

/**
 * [sf_formula_faq] — the accordion itself, inside the template's core/html
 * block (batch C).
 *
 * The <details> sequence is built here rather than written as core/details
 * blocks in the template for the same reason every other dynamic band on this
 * page is: a block template runs do_shortcode() before do_blocks(), so a
 * {{placeholder}} in a block cannot be resolved, while a shortcode reads the
 * record at render time. It also means the nine answers exist once, in
 * sinofresh_formula_faq_data(), and both the page and the FAQPage schema read
 * that one copy instead of two implementations that can disagree.
 *
 * The markup is the dosage pages' own vocabulary — .sf-faq, .sf-faq__item,
 * .sf-faq__icon, wp-block-heading on the question, has-text-secondary-color on
 * the answer — so style.css needs no new rule and the two accordions cannot
 * look different. The first item ships open, as it does there, and the whole
 * sequence is one line: the band is a shortcode, so the renderer's newline
 * arithmetic has nothing to do here.
 *
 * Returns '' outside a formula, and '' if every pair is unusable, so nothing
 * empty is emitted. On a real record the generated set is never empty, so the
 * template's core heading always has an accordion under it.
 */
function sinofresh_formula_faq($post_id = 0) {
	$pairs = sinofresh_formula_faq_data($post_id);
	if (!$pairs) {
		return '';
	}
	$html  = '';
	$first = true;
	foreach ($pairs as $pair) {
		$question = trim((string) $pair['q']);
		$answer   = trim((string) $pair['a']);
		if ($question === '' || $answer === '') {
			continue;
		}
		$html .= sprintf(
			'<details class="wp-block-details sf-faq__item"%s>'
			. '<summary><h3 class="wp-block-heading">%s</h3>'
			. '<span class="sf-faq__icon" aria-hidden="true"></span></summary>'
			. '<p class="has-text-secondary-color has-text-color">%s</p></details>',
			$first ? ' open' : '',
			esc_html($question),
			esc_html($answer)
		);
		$first = false;
	}
	if ($html === '') {
		return '';
	}
	return '<div class="sf-faq">' . $html . '</div>';
}
/* WP hands a shortcode callback its attribute array as the first argument, so
   the id is never read from it: the band only ever renders on the record being
   viewed. */
add_shortcode('sf_formula_faq', function() {
	return sinofresh_formula_faq();
});

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
 *       copies the name to the clipboard. 1.1.0 also mirrored it into
 *       sessionStorage for configurator.js's PDF summary — H2b2 deleted that
 *       reader and left the writer behind, and batch H6 removed the writer.
 *   K2  retired in batch H6 (2.10.61). The records used to be mirrored into
 *       <script class="sf-formulas-data"> so configurator.js readFormula()
 *       could stop scraping <details> markup for the three fields. When
 *       configurator.js went in H2b2 the mirror became a 1.2 KB payload with
 *       no reader, shipped on all 60 grid pages. The ItemList below is the
 *       only JSON this shortcode emits.
 *   K3  card titles are <h3>, never <h2>: toc-nav.js numbers the page from its
 *       <h2> sequence, so a card heading would shift every downstream anchor.
 *   K4  JSON inside <script> is written raw ("&", not "&amp;") — see
 *       sinofresh_formula_script_json().
 *   K7  card anatomy is fixed: .sf-fcard > [.sf-fcard__media]? + .sf-fcard__body
 *       > (.sf-fcard__use, h3.sf-fcard__name, p.sf-fcard__spec, .sf-fcard__actions).
 *       The media block is omitted (not emitted empty) when no still exists;
 *       the copy lives in __body so the image can bleed to the card border
 *       while a text-only card stays visually identical to the 2B one.
 *       H7k refines the media block without moving any of that: the still is
 *       wrapped in a.sf-fcard__imagelink (待办14) and the badge — when the
 *       record has one — is the figure's second child (待办17). The badge is a
 *       SIBLING of the link, never inside it, so "Best Seller" cannot leak into
 *       the link's accessible name. On the no-still branch the badge becomes
 *       the first child of __body with the --inline modifier, because a record
 *       without a still must not lose its badge.
 *
 * Attributes:
 *   form     dosage form slug. Default: resolved from the queried object.
 *   use      sf_formula_use slug to narrow to one function. Default: all.
 *   limit    max cards (-1 = all).
 *   exclude  comma/space separated post IDs to leave out. The formula being
 *            viewed is ALWAYS excluded when the grid renders on its own
 *            single page — see below.
 *   columns  grid tracks, clamped to 1–6. Default: 4.
 *   cta      'reference' (default) renders the K1 button; 'none' omits it.
 *            Any other value falls back to 'reference'.
 *   links    'true' (default) links the title and the still (待办14) and adds
 *            "View formula →"; 'false'/'0'/'no' render the name as plain text
 *            and leave the still unlinked.
 *   empty    only 'hide' is implemented; any other value behaves as 'hide'.
 *
 * Why the current formula is excluded in PHP rather than passed by the
 * template: the related grid on single-sf_formula.html wants
 * exclude="<current id>", but a block template runs do_shortcode() before
 * do_blocks(), so a {{placeholder}} in a shortcode attribute is still the
 * literal token at this point — the template cannot know the ID. Deriving it
 * from the queried object here is both correct and impossible to forget.
 */
function sinofresh_formula_grid($atts = array()) {
	$atts = shortcode_atts(array(
		'form'    => '',
		'use'     => '',
		'limit'   => -1,
		'exclude' => '',
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

	/* Exclusions: the caller's IDs, plus the formula being viewed. Without
	   the latter the "more from this range" grid would list the formula the
	   visitor is already reading. */
	$exclude = preg_split('/[,\s]+/', (string) $atts['exclude'], -1, PREG_SPLIT_NO_EMPTY);
	$exclude = array_map('intval', is_array($exclude) ? $exclude : array());
	if (is_singular('sf_formula')) {
		$exclude[] = (int) get_queried_object_id();
	}
	$exclude = array_values(array_unique(array_filter($exclude)));

	$args      = array(
		'post_type'           => 'sf_formula',
		'post_status'         => 'publish',
		'posts_per_page'      => (int) $atts['limit'],
		'orderby'             => array('menu_order' => 'ASC', 'title' => 'ASC'),
		'ignore_sticky_posts' => true,
		'no_found_rows'       => true,
	);
	if ($exclude) {
		$args['post__not_in'] = $exclude;
	}
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

	$cards = '';
	$items = array();

	foreach ($formulas as $formula) {
		/* One authoritative name string. get_the_title() is entity-encoded
		   ("Skin &amp; Coat"), and the name has to appear verbatim in three
		   places — the <h3> text, the ItemList name and data-formula.
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
		/* Only Standard Specs reaches the card. Ingredients and Guaranteed
		   Analysis were read here for the K2 payload as well; batch H6
		   retired that document, so they are not fetched any more. */
		$specs = (string) get_post_meta($formula->ID, 'sf_formula_specs', true);

		$items[] = array(
			'@type'    => 'ListItem',
			'position' => count($items) + 1,
			'name'     => $name,
			'url'      => $url,
		);

		$actions = '';
		if ($links) {
			$actions .= sprintf('<a class="sf-fcard__more" href="%s">View formula →</a>', esc_url($url));
		}
		if ($cta_on) {
			/* K1 — formulas.js binds clicks on .sf-formula__cta and copies
			   data-formula verbatim into the clipboard, so the name has to
			   reach that attribute undamaged.
			   data-form is the 2C Step2 addition: its only reader was the
			   sessionStorage write batch H6 retired, so nothing reads it
			   now. It stays because H6's declared scope is the dead
			   CSS/PHP/JS, and dropping an attribute off every card is a
			   markup change with a gate of its own. */
			$actions .= sprintf(
				'<button type="button" class="sf-formula__cta" data-formula="%s" data-form="%s">Reference this formula →</button>',
				esc_attr($name),
				esc_attr($form_slug)
			);
		}

		$badge = sinofresh_formula_card_badge($formula->ID);

		/* 待办14 — the still is a link now, like the dosage tiles on
		   /products/ have always been. The card used to carry THREE routes to
		   its own page (title, "View formula →") and the image was the one part
		   that looked clickable and was not. The <a> wraps the <img> only: the
		   badge below it is a separate sibling so its label can never become
		   part of the link's accessible name. aria-label rather than a bare
		   alt: the img already describes the STILL ("… — golden oval softgel
		   capsules"), which is the wrong sentence for a navigation link, so the
		   link says where it goes and the img keeps describing what it shows. */
		$media = '';
		$image = sinofresh_formula_card_image($form_slug);
		if ($image !== '') {
			/* The alt mirrors the dosage-page tile convention exactly so the
			   formula stills are described the same way as the identical
			   renders in the dosage catalogue — one function for both, and
			   batch H5 added the visual clause ("… — golden oval softgel
			   capsules") to the convention. The seven sibling tiles inside
			   each dosage template carry the same string verbatim; the gate
			   asserts the two carriers agree per form. */
			$still = sprintf(
				'<img src="%s" alt="%s" width="720" height="720" loading="lazy" decoding="async"/>',
				esc_url($image),
				esc_attr(sinofresh_formula_product_alt($form_slug))
			);
			/* `links="false"` means "the card is not a route anywhere", so the
			   still has to obey it too — an image link on a card whose title
			   was deliberately left as plain text would be the one link the
			   attribute failed to switch off. */
			if ($links) {
				$still = sprintf(
					'<a class="sf-fcard__imagelink" href="%s" aria-label="%s">%s</a>',
					esc_url($url),
					esc_attr(sprintf('View the %s formula', $name)),
					$still
				);
			}
			$media = sprintf(
				'<figure class="sf-fcard__media">%s%s</figure>',
				$still,
				sinofresh_formula_badge_markup($badge)
			);
		}

		$cards .= sprintf(
			/* data-sf-form is what formula-filter.js reads on /formulas/.
			   K7's element/class order is untouched — the attribute is
			   additive, so every existing .sf-fcard consumer is unaffected.
			   K7 also fixes the media block, so the badge has one home when
			   there IS one (the overlay) and one when there is not (inline at
			   the head of __body, 待办17): a record whose still is missing must
			   not lose its badge silently. */
			'<article class="sf-fcard" data-sf-form="%s">%s<div class="sf-fcard__body">%s<span class="sf-fcard__use">%s</span><h3 class="sf-fcard__name">%s</h3><p class="sf-fcard__spec">%s</p>%s</div></article>',
			esc_attr($form_slug),
			$media,
			$image === '' ? sinofresh_formula_badge_markup($badge, true) : '',
			/* 2B Stage1 pit #2: term names are entity-encoded in wp_terms
			   ("Skin &amp; coat") — output verbatim so the browser shows
			   "Skin & coat". esc_html() here would double-escape. */
			$use_name,
			$links ? '<a href="' . esc_url($url) . '">' . esc_html($name) . '</a>' : esc_html($name),
			esc_html($specs),
			$actions === '' ? '' : '<div class="sf-fcard__actions">' . $actions . '</div>'
		);
	}

	$list = sinofresh_formula_script_json(array(
		'@context'        => 'https://schema.org',
		'@type'           => 'ItemList',
		'name'            => sinofresh_formula_list_name($form),
		'numberOfItems'   => count($items),
		'itemListElement' => $items,
	));
	if ($list === '') {
		return '';
	}

	return sprintf('<div class="sf-fgrid" style="--sf-fgrid-cols:%d">', $columns)
		. '<script type="application/ld+json">' . $list . '</script>'
		. $cards
		. '</div>';
}
add_shortcode('sf_formula_grid', 'sinofresh_formula_grid');

/**
 * Split an "a, b, c" meta value on its top-level commas.
 *
 * The comma is the separator every sf_formula_ingredients value uses, and it
 * can also legitimately appear INSIDE a parenthesised share — "Tapioca (46%),
 * Peas (29%)" separates at depth 0 only. Today all 21 records split identically
 * either way (tools/b2d1_parser_dryrun.php §1), so this is defensive rather
 * than load-bearing: it costs a depth counter and removes a silent wrong split
 * if content ever writes "X (a, b), Y".
 *
 * Byte-wise on purpose: "(" ")" "," are ASCII and every UTF-8 continuation
 * byte is >= 0x80, so multi-byte terms pass through untouched.
 *
 * Returns a trimmed list with empty segments dropped; '' and whitespace give an
 * empty array, never one empty element.
 *
 * Written for the [sf_formula_actives] band, which batch H6 retired; it is
 * still load-bearing — sinofresh_formula_analysis_pairs() below and
 * [sf_formula_detail_actives] both split through it.
 */
function sinofresh_formula_split_top_level($value) {
	$value = (string) $value;
	if (trim($value) === '') {
		return array();
	}
	$out   = array();
	$depth = 0;
	$cur   = '';
	$len   = strlen($value);
	for ($i = 0; $i < $len; $i++) {
		$ch = $value[$i];
		if ($ch === '(') {
			$depth++;
		} elseif ($ch === ')') {
			if ($depth > 0) {
				$depth--;
			}
		}
		if ($ch === ',' && $depth === 0) {
			$out[] = trim($cur);
			$cur   = '';
			continue;
		}
		$cur .= $ch;
	}
	$out[] = trim($cur);
	return array_values(array_filter($out, function ($s) { return $s !== ''; }));
}

/**
 * Turn "Glucosamine ≥500mg/chew, Chondroitin ≥200mg/chew" into term/value pairs
 * for the guaranteed-analysis table.
 *
 * Each segment splits at its FIRST U+2265 (≥), so the level half keeps any
 * further text verbatim ("Omega-3 ≥30%" → term "Omega-3", value "≥30%"). A
 * segment with no ≥ is kept as a term with an empty value — the caller decides
 * — while a value with no subject is dropped here, because that is not a row.
 *
 * Written for the [sf_formula_actives] band, which batch H6 retired;
 * [sf_formula_detail_actives] is its only remaining caller.
 */
function sinofresh_formula_analysis_pairs($value) {
	$pairs = array();
	foreach (sinofresh_formula_split_top_level($value) as $part) {
		$pos = strpos($part, "\xE2\x89\xA5"); // U+2265 GREATER-THAN OR EQUAL TO
		if ($pos === false) {
			$pairs[] = array('term' => $part, 'value' => '');
			continue;
		}
		$term  = rtrim(substr($part, 0, $pos));
		$level = ltrim(substr($part, $pos));
		if ($term === '' || $level === '') {
			continue;
		}
		$pairs[] = array('term' => $term, 'value' => $level);
	}
	return $pairs;
}

/**
 * [sf_formula_gallery form="soft-chews"] — the product-gallery band on the
 * eight dosage pages.
 *
 * The band closes a gap in the page, not a gap in the data: a dosage page
 * described its formulas in detail and never showed the product, so a visitor
 * could read the whole thing without once seeing what that dosage form looks
 * like. The hero above it is a flat colour band with no image, and the only
 * other copy of the dosage's own photo is the formula-card thumbnail,
 * repeated once per card.
 *
 * Four frames, one data source. Slot 1 is the dosage's own photo and the only
 * frame the server renders visible; slots 2-4 ship `hidden`, and
 * formula-gallery.js is what turns them into a thumbnail strip. Nothing here
 * emits an ItemList — the gallery is presentation, not a second copy of the
 * product data.
 *
 * Placeholder notice: slots 2-4 are stock facility photographs, not this
 * product's own line, and every photo in the library still carries an AI
 * watermark. They exist so the band's geometry can be built and verified;
 * the real shoot is a tracked pre-launch item.
 */
function sinofresh_formula_gallery_file_url($filename) {
	$filename = sanitize_file_name($filename);
	if ($filename === '') {
		return '';
	}
	$uploads = wp_upload_dir();
	if (!empty($uploads['error']) || empty($uploads['basedir'])) {
		return '';
	}
	$base    = trailingslashit($uploads['basedir']);
	$matches = array_merge(
		(array) glob($base . '*/*/' . $filename),
		(array) glob($base . $filename)
	);
	if (!$matches) {
		return '';
	}
	/* Newest upload wins if the same basename exists in two month folders. */
	sort($matches);
	return trailingslashit($uploads['baseurl']) . ltrim(str_replace($base, '', (string) end($matches)), '/');
}

/**
 * The YouTube id inside a stored sf_formula_video_url, or '' when there is
 * none to find.
 *
 * The field takes whatever an editor pastes out of the address bar —
 * watch?v=, youtu.be/, /embed/, /shorts/ — and a bare id, because the id is
 * what a person copies when they mean "this video". Anything else (Vimeo, a
 * playlist, a channel) is not a video this band can play, so it is refused
 * rather than half-parsed: no id means no video frame, and since batch H7a no
 * [Video] tab either — the band's switch ships as [Photos] alone.
 */
function sinofresh_formula_video_id($url) {
	$url = trim((string) $url);
	if ($url === '') {
		return '';
	}
	if (preg_match('~(?:youtube\.com/(?:watch\?[^#]*v=|embed/|shorts/)|youtu\.be/)([A-Za-z0-9_-]{6,})~i', $url, $m)) {
		return $m[1];
	}
	if (preg_match('/^[A-Za-z0-9_-]{6,}$/', $url)) {
		return $url;
	}
	return '';
}

/**
 * The gallery's slots for one dosage form.
 *
 * Four dosage-level frames are the backbone and always in this order: the
 * form's own product photo, then the facility band. Since batch H2a a record
 * can add its OWN photos (sf_formula_gallery_ids) and one video
 * (sf_formula_video_url); the six-frame cap is applied strongest-first, so
 * the ranking is product photo > own photos > video > facility frames — see
 * the block inside.
 *
 * `width`/`height` are the photographs' real pixel sizes, read off the
 * uploads folder with getimagesize on the server — not copied from markup
 * elsewhere in this theme, which carries a stale width="800" height="600" on
 * a 720x720 file. They are declared rather than measured per render so the
 * frame is sized before the bytes arrive. **Replacing a photo at a different
 * size means updating its row here**: this table is the only place those
 * numbers live. tools/b2d_s2_dimensions.py asserts every row against the
 * server so the two cannot drift apart unnoticed. (Rows appended from a
 * record's own attachments declare the size WordPress reported for the
 * 'large' rendition, so the same rule holds without a hand-maintained table.)
 */
function sinofresh_formula_gallery_slots($form, $post_id = 0) {
	$form = sanitize_title($form);
	if ($form === '') {
		return array();
	}
	$label = sinofresh_formula_label($form);
	if ($label === '') {
		return array();
	}

	$slots = array(
		array(
			'file'   => $form . '.webp',
			'url'    => sinofresh_formula_card_image($form),
			'width'  => 720,
			'height' => 720,
			/* The same still is described in three places, and this was the
			   third: the card markup [sf_formula_grid] prints, the seven
			   sibling tiles in each dosage template, and this gallery frame.
			   It used to spell the string out a second time here, so after
			   batch H5 the frame kept the bare description while the card
			   gained the visual clause — the same .webp, two different alts,
			   on the same page. The value also lands in data-label and in the
			   stage's aria-label, which is the name a screen reader hears. */
			'alt'    => sinofresh_formula_product_alt($form),
		),
		array(
			'file'   => 'fac-placeholder.webp',
			'url'    => sinofresh_formula_gallery_file_url('fac-placeholder.webp'),
			'width'  => 1100,
			'height' => 733,
			'alt'    => sprintf('%s production line at the SINO FRESH GMP facility in Linyi, China', $label),
		),
		array(
			'file'   => 'fac-packaging.webp',
			'url'    => sinofresh_formula_gallery_file_url('fac-packaging.webp'),
			'width'  => 800,
			'height' => 600,
			'alt'    => sprintf('%s packaging line at the SINO FRESH GMP facility in Linyi, China', $label),
		),
		array(
			'file'   => 'fac-line.webp',
			'url'    => sinofresh_formula_gallery_file_url('fac-line.webp'),
			'width'  => 800,
			'height' => 600,
			'alt'    => sprintf('%s moving along the tray line inside the SINO FRESH GMP facility', $label),
		),
	);

	/* Batch H2a — the record's OWN photos and its video, ranked against the
	   dosage-level four by this order, strongest first:

	       product photo > record's own photos > record's video > facility frames

	   Frame 1 is the dosage backbone's own product photo and always leads;
	   the three facility frames are the fallback that fills whatever room is
	   left. A record that has filled nothing is still exactly the four
	   frames it had before — which is every one of the 21 today, both fields
	   shipping empty, so this list does not move a byte until ops fills them.

	   The cap is six frames. The strip is a strip, not a deck: past six the
	   thumbnails stop being scannable at the 72px column the detail band
	   gives them. Because the list is built strongest-first and then trimmed
	   from the tail, a record with several own photos AND a video keeps the
	   video and drops facility frames. Appending the video last and slicing
	   instead — the first cut of this — would have dropped the video, since
	   it would have been the item at the tail. */
	if ($post_id > 0) {
		$own = array();
		foreach (explode(',', (string) get_post_meta($post_id, 'sf_formula_gallery_ids', true)) as $id) {
			$id = absint($id);
			if ($id <= 0) {
				continue;
			}
			$src = wp_get_attachment_image_src($id, 'large');
			if (!$src) {
				continue;
			}
			$alt = trim((string) get_post_meta($id, '_wp_attachment_image_alt', true));
			$own[] = array(
				'file'   => '',
				'url'    => (string) $src[0],
				/* Real pixels of the chosen size, not the source file's:
			   the frame is sized before the bytes arrive either way, and a
			   declared size that does not match the URL would let the
			   aspect ratio flip once the image lands. */
				'width'  => (int) $src[1],
				'height' => (int) $src[2],
				'alt'    => $alt !== '' ? $alt : sprintf('%s private label pet supplement product photo', $label),
			);
		}

		$video = array();
		$video_id = sinofresh_formula_video_id(get_post_meta($post_id, 'sf_formula_video_url', true));
		if ($video_id !== '') {
			$video[] = array(
				'file'     => '',
				/* The poster is YouTube's own still for that id, so the
				   facade needs no upload and no second asset to keep in step. */
				'url'      => 'https://i.ytimg.com/vi/' . $video_id . '/hqdefault.jpg',
				'width'    => 480,
				'height'   => 360,
				'video_id' => $video_id,
				'alt'      => sprintf('%s product video', $label),
			);
		}

		if ($own || $video) {
			/* Rebuild strongest-first — backbone photo, own photos, video,
			   then the facility band — and trim the tail. */
			$head     = array_slice($slots, 0, 1);
			$facility = array_slice($slots, 1);
			$slots    = array_slice(array_merge($head, $own, $video, $facility), 0, 6);
		}
	}

	/* A slot whose file is missing is dropped rather than rendered as a broken
	   image, and if slot 1 ever went missing the next one becomes the main
	   photo. The band returns '' only once all of them are gone. */
	$out = array();
	foreach ($slots as $slot) {
		if ($slot['url'] !== '') {
			$out[] = $slot;
		}
	}
	return $out;
}

function sinofresh_formula_gallery($atts = array()) {
	$atts = shortcode_atts(array('form' => ''), $atts, 'sf_formula_gallery');
	$form = sinofresh_formula_current_form($atts['form']);

	/* The record's own images and its video are per-post, so the slot list is
	   built for the post being rendered. Off a single formula (the shortcode
	   is generic) there is no post to read, and the dosage-level four stand
	   alone — the pre-H2a behavior. */
	$slots = sinofresh_formula_gallery_slots($form, is_singular('sf_formula') ? (int) get_queried_object_id() : 0);
	if (!$slots) {
		return '';
	}

	$frames = '';
	foreach ($slots as $index => $slot) {
		$n = $index + 1;
		if (!empty($slot['video_id'])) {
			/* A facade, not an iframe: the poster is server-rendered and
			   only the play button carries the id, so a page load costs one
			   image and YouTube's player (≈1MB of JS) is fetched when — and
			   only when — the visitor asks for it. formula-gallery.js swaps
			   this button for the player; without JS the frame still shows
			   the poster and the button does nothing, which is why the
			   button is a real <button> and not a styled link that would
			   navigate away to youtube.com. */
			$frames .= '<figure class="sf-gallery__slide sf-gallery__slide--video"'
				. ' id="sf-gallery-slide-' . esc_attr($form) . '-' . $n . '"'
				. ' data-slot="' . $n . '"'
				. ' data-video-id="' . esc_attr($slot['video_id']) . '"'
				. ' data-label="' . esc_attr($slot['alt']) . '"'
				. ($n === 1 ? '' : ' hidden') . '>'
				. '<button type="button" class="sf-gallery__play">'
				. '<img src="' . esc_url($slot['url']) . '"'
				. ' alt="' . esc_attr($slot['alt']) . '"'
				. ' width="' . (int) $slot['width'] . '" height="' . (int) $slot['height'] . '"'
				. ' loading="lazy" decoding="async">'
				. '<span class="sf-gallery__play-icon" aria-hidden="true"></span>'
				. '<span class="sf-gallery__play-text">Play video</span>'
				. '</button>'
				. '</figure>';
			continue;
		}
		$frames .= '<figure class="sf-gallery__slide" id="sf-gallery-slide-' . esc_attr($form) . '-' . $n . '"'
			. ' data-slot="' . $n . '"'
			. ' data-label="' . esc_attr($slot['alt']) . '"'
			. ($n === 1 ? '' : ' hidden') . '>'
			. '<img src="' . esc_url($slot['url']) . '"'
			. ' alt="' . esc_attr($slot['alt']) . '"'
			. ' width="' . (int) $slot['width'] . '" height="' . (int) $slot['height'] . '"'
			/* Only the main photo is worth fetching early: the others sit
			   behind `hidden` and a click, so eager-loading them would just
			   compete with the hero. No fetchpriority="high" anywhere — the
			   LCP element on these pages is the hero's heading text. */
			. ' loading="' . ($n === 1 ? 'eager' : 'lazy') . '" decoding="async">'
			. '</figure>';
	}

	/* Batch H7a — the [Photos][Video] switch replaces the heading that used to
	   open this band.

	   The heading was "A Closer Look at {name}": on all 42 detail pages it
	   repeated the h1 word for word, differing only by that prefix, and the one
	   job it was ever given — naming the article outline's dot-rail entry — does
	   not apply to a detail page, which carries no dot rail at all. So the slot
	   became the control the media column was missing instead.

	   Why the buttons are serialised here and not built by the script: the two
	   labels are the only translatable strings in the band, and the language
	   layer only sees server-rendered text. A button created in JS is invisible
	   to it — which is the state the strip's own hard-coded "Product photos"
	   label is still in today.

	   [Video] is emitted only when the record actually has one. All 21 are
	   without one at the time of writing, so the bar ships as a lone [Photos];
	   filling sf_formula_video_url in wp-admin makes the second label appear
	   with no code change and no second deploy.

	   Without scripting the whole bar stays hidden — .sf-gallery--js below is
	   added by the script and the stylesheet paints nothing until it is there.
	   A no-JS visitor gets the photo area and no dead controls, the same
	   contract the strip already kept. */
	$has_video = false;
	foreach ($slots as $slot) {
		if (!empty($slot['video_id'])) {
			$has_video = true;
			break;
		}
	}

	$tabs = '<div class="sf-gallery__tabs" role="group" aria-label="' . esc_attr('Product media') . '">'
		. '<button type="button" class="sf-gallery__tab is-active" data-sf-gallery-tab="photos" aria-pressed="true">'
		. esc_html('Photos') . '</button>';
	if ($has_video) {
		$tabs .= '<button type="button" class="sf-gallery__tab" data-sf-gallery-tab="video" aria-pressed="false">'
			. esc_html('Video') . '</button>';
	}
	$tabs .= '</div>';

	/* The stage's aria-label starts as the main photo's alt so the band is
	   named before any script runs, and formula-gallery.js keeps it in step
	   with whichever photo is showing. */
	return '<div class="sf-gallery__inner" data-gallery="' . esc_attr($form) . '">'
		. '<div class="sf-gallery__stage" role="tabpanel" id="sf-gallery-panel-' . esc_attr($form) . '"'
		. ' aria-label="' . esc_attr($slots[0]['alt']) . '">' . $frames
		/* H7g — the preview layer. Empty in the markup, filled by config.js
		   when a Shape or Container thumbnail is chosen; any click on the
		   gallery's own controls hides it again. It adds a node to the stage
		   rather than touching a slide, so the gallery's markup, its slide
		   ids and formula-gallery.js all keep working unchanged. */
		. '<div class="sf-gallery__preview" data-sf-gallery-preview hidden></div>'
		. '</div>'
		. $tabs
		. '</div>';
}
add_shortcode('sf_formula_gallery', 'sinofresh_formula_gallery');

/**
 * [sf_formula_filters] — dosage-form filter bar for archive-sf_formula.html.
 *
 * 2C Step2 renders all 21 formulas on one page and narrows them in the
 * browser (formula-filter.js toggles .is-sf-off on the cards), so the bar is
 * nine <button>s rather than links: a button is the honest control for
 * "narrow what is already on screen". Buttons carry aria-pressed and the
 * container a role="status" line, so the state is announced, not just
 * painted.
 *
 * Order and labels come from the Products children (parent 19, menu_order) —
 * the same source [sf_explore_chips] uses — so the chip row reads in the
 * dosage-page sequence the visitor already knows, and "All" leads. A form
 * with no published formula is skipped instead of rendered as a dead end.
 *
 * Without JavaScript the whole bar is hidden: the CSS hook is the sf-js
 * class the head marker adds to <html> before the body paints. A no-JS
 * visitor gets the plain 21-card list, never a row of buttons that do
 * nothing. (The white band around it collapses to its own padding in that
 * case — deliberately not compensated with :has(), which would need
 * !important to beat the section's inline padding.)
 *
 * The shown-count is a <span> of its own so the script rewrites only the
 * number and the phrase around it stays one translatable string.
 */
function sinofresh_formula_filters() {
	$total = (int) wp_count_posts('sf_formula')->publish;
	if ($total < 1) {
		return '';
	}
	$pages = get_pages(array(
		'parent'      => 19,          // Products — same source as sf_explore_chips
		'post_status' => 'publish',
		'sort_column' => 'menu_order',
		'sort_order'  => 'ASC',
	));

	$buttons = '<button type="button" class="sf-fchip is-active" data-sf-form="all" aria-pressed="true">'
		. esc_html('All') . '</button>';
	foreach ($pages as $page) {
		$slug = (string) $page->post_name;
		$term = get_term_by('slug', $slug, 'sf_formula_form');
		if (!$term instanceof WP_Term || (int) $term->count < 1) {
			continue;
		}
		$buttons .= sprintf(
			'<button type="button" class="sf-fchip" data-sf-form="%s" aria-pressed="false">%s</button>',
			esc_attr($slug),
			esc_html(sinofresh_formula_label($slug, $term->name))
		);
	}

	return '<div class="sf-fchips-wrap">'
		. '<div class="sf-fchips" role="group" aria-label="Filter formulas by dosage form">' . $buttons . '</div>'
		. '<p class="sf-fchips-status" role="status">'
		. sprintf(
			esc_html('Showing %1$s of %2$d formulas'),
			'<span class="sf-fchips-count">' . $total . '</span>',
			$total
		)
		. '</p>'
		. '</div>';
}
add_shortcode('sf_formula_filters', 'sinofresh_formula_filters');

/**
 * /formulas/page/2/, /formulas/page/3/ → 301 to /formulas/.
 *
 * 2C Step2 replaced the paginated blog recipe with a single page holding all
 * 21 cards, so page 2 and 3 would render the same list a second and third
 * time — duplicate content with no way back. page/4 already 404s (the
 * archive never had a fourth page) and handle_404() resets the query flags,
 * so this hook never sees it and the 404 stands.
 *
 * The target is a site-relative path derived from the request, for two
 * independent reasons. get_post_type_archive_link() returns the English
 * /formulas/ on /zh/formulas/page/2/ and would drop the visitor out of the
 * language they were browsing; and home_url() is filtered by TranslatePress
 * to prepend the active language, so home_url('/zh/formulas/') comes back as
 * /zh/zh/formulas/. The path already carries the prefix the visitor asked
 * for, so it goes out untouched.
 */
add_action('template_redirect', function () {
	if (!is_post_type_archive('sf_formula') || !is_paged()) {
		return;
	}
	$uri    = isset($_SERVER['REQUEST_URI']) ? (string) wp_unslash($_SERVER['REQUEST_URI']) : '';
	$path   = (string) wp_parse_url($uri, PHP_URL_PATH);
	$target = preg_replace('#/page/[0-9]+/?$#', '/', $path);
	if (!is_string($target) || $target === $path) {
		return;
	}
	$query = (string) wp_parse_url($uri, PHP_URL_QUERY);
	wp_safe_redirect($target . ($query !== '' ? '?' . $query : ''), 301);
	exit;
});

/**
 * No-JS guard for the filter bar (see [sf_formula_filters]).
 *
 * A class on <html> set by an inline head script is available before the
 * body paints, so a JS-less visitor never sees the bar flash in and stay
 * dead. Emitted only on the archive that renders the bar, which keeps every
 * other template byte-identical.
 */
add_action('wp_head', function () {
	if (!is_post_type_archive('sf_formula')) {
		return;
	}
	echo "<script>document.documentElement.classList.add('sf-js');</script>\n";
}, 1);

/**
 * [sf_formula_detail] — the standard specification of the current formula.
 *
 * One field is rendered: Standard Specs. Ingredients and Guaranteed Analysis
 * are deliberately left out, because the "Formula & nutrition" band below
 * already carries both from the same meta — they were being rendered twice
 * on every detail page. Only the rendering changed: all three meta keys are
 * still written, and the Product JSON-LD builds its additionalProperty from
 * the meta directly, so the machine-readable copy is untouched.
 *
 * The field is read straight from post meta rather than from the grid's
 * JSON: the grid is a sibling band, not this formula's own record, and its
 * K2 payload went in batch H6 anyway. A field with no value is skipped,
 * never rendered as an empty card. When exactly one card is rendered the
 * grid takes the --solo modifier — style.css caps that variant's width, so
 * the cap can never reach a multi-card grid.
 *
 * Framework-free by design: it renders one .sf-fdetail__grid of
 * .sf-fdetail__card boxes and style.css owns the geometry, the same split
 * .sf-fgrid uses (block templates run do_shortcode() before do_blocks(), so
 * a shortcode can never carry a wp-container-core-* layout class).
 *
 * Returns '' outside a single sf_formula, so a stray shortcode in an editor
 * cannot leak another formula's spec into an article.
 */
function sinofresh_formula_detail() {
	if (!is_singular('sf_formula')) {
		return '';
	}
	$post_id = (int) get_queried_object_id();
	if (!$post_id) {
		return '';
	}
	/* One card is the intended state, not a degenerate one: the ⑤ actives
	   band carries Ingredients and Guaranteed Analysis. The loop and the
	   grid stay multi-card so the array can grow again without touching
	   anything downstream; $count only decides the --solo modifier. */
	$fields = array(
		array('label' => 'Standard Specs',      'key' => 'sf_formula_specs'),
	);
	$cards = '';
	$count = 0;
	foreach ($fields as $field) {
		$value = trim((string) get_post_meta($post_id, $field['key'], true));
		if ($value === '') {
			continue;
		}
		$cards .= sprintf(
			'<div class="sf-fdetail__card"><h3 class="sf-fdetail__label">%s</h3><p class="sf-fdetail__value">%s</p></div>',
			esc_html($field['label']),
			esc_html($value)
		);
		$count++;
	}
	if ($cards === '') {
		return '';
	}
	$grid_class = 'sf-fdetail__grid' . ($count === 1 ? ' sf-fdetail__grid--solo' : '');
	return '<div class="' . $grid_class . '">' . $cards . '</div>';
}
add_shortcode('sf_formula_detail', 'sinofresh_formula_detail');

/**
 * [sf_formula_params] — the detail band's parameter rows (batch H2a).
 *
 * Replaces [sf_formula_factsheet], which had exactly one caller (the detail
 * template) and printed five rows. This one printed up to ten until batch H7d
 * split the band in two along the only line that matters to a reader: rows the
 * customer can CHOOSE moved to [sf_formula_config], rows that are facts stayed
 * here. Batch H8a took one more off. The three that stayed:
 *
 *   Shelf life          sf_formula_shelf_life   (the fixed pool, batch H8a)
 *   Certifications      Site Settings sf_certifications, via sf_render_cert_badges()
 *   Lead time           sf_formula_lead_time
 *
 * Shelf life read sf_formula_specs and now reads the record's own field. The
 * two disagreed on post 158 (24 months stored, 18 months in the spec sheet),
 * and a page that states one fact twice with two answers is worse than a page
 * that states it once. sf_formula_shelf_life_line() keeps the spec sheet as
 * the fallback for a record the sales team has not re-saved yet, so no page
 * loses the row while the pool fills up.
 *
 * Packaging left in H8a on the user's instruction: the right column already
 * carries Container Type, and the row restated the dosage form's packaging
 * formats beside it. Nothing was lost from the page — the value comes from the
 * dosage page's own .sf-facts-mini row, which is still there and still what
 * the Product JSON-LD reads (sinofresh_formula_facts_props()), and the
 * record's own sf_formula_packaging_extra list still prints in the body under
 * "Packaging & Specifications → Additional Packaging".
 *
 * The six that left — Flavor, Piece Weight, Pack Size, Suitable For, Life Stage
 * and Quantity & Pricing — are controls there, and each prints this record's own
 * value as its meta line. Keeping them here as well would print every one of
 * those values twice on the same page, which is why this renderer lost rows in a
 * batch that added a renderer.
 *
 * Empty means absent: a row with no value is not rendered at all, so a
 * record that carries only what batch H1a migrated renders the rows it can
 * prove and no others. That is the whole point of shipping the renderer
 * before the data — the sales team fills a field, the row appears, nothing
 * is deployed. It also means the row set differs per record by design, and
 * the gate asserts the presence of the renderer rather than a fixed row
 * count.
 *
 * <dt>/<dd>, not the .sf-spec-term / .sf-spec-value <span> pair — same
 * reason the factsheet gave: that pair feeds the K6 parser, and this list is
 * read by no parser.
 *
 * Certifications reads the Site Settings option (decision A, 2026-09-22) and
 * NOT the dosage page's .sf-facts-mini certifications cell the hero meta
 * still reads: the option is the list an admin can correct without a
 * deploy, and the two are reconciled at gate time — a difference is recorded
 * in the batch report, never silently merged here.
 */
function sinofresh_formula_params() {
	if (!is_singular('sf_formula')) {
		return '';
	}
	$post_id = (int) get_queried_object_id();
	if ($post_id <= 0) {
		return '';
	}
	$parts = sinofresh_formula_specs_parts(trim((string) get_post_meta($post_id, 'sf_formula_specs', true)));

	/* Each cell is already escaped HTML: the badges escape their own values, so
	   the loop below must not escape a second time (a second pass would print
	   &amp;#8211; for "–"). */
	$rows = array();

	/* Batch H7d moved the six rows that are CHOICES over to
	   [sf_formula_config]: Flavor, Piece Weight, Pack Size, Suitable For, Life
	   Stage and Quantity & Pricing are controls now, and each prints the
	   record's own value as its meta line — so leaving them here as well would
	   put every one of those values on the page twice. What stays is the four
	   rows that are not a choice. The split is by "can the customer pick a
	   different one", not by importance. */
	$shelf = sf_formula_shelf_life_line($post_id, $parts);
	if ($shelf !== '') {
		$rows['Shelf life'] = esc_html($shelf);
	}
	$certs = sf_render_cert_badges();
	if (trim($certs) !== '') {
		$rows['Certifications'] = $certs;
	}
	$lead = trim((string) get_post_meta($post_id, 'sf_formula_lead_time', true));
	if ($lead !== '') {
		$rows['Lead time'] = esc_html($lead);
	}

	$html = '';
	foreach ($rows as $label => $cell) {
		$html .= '<dt class="sf-fdetail2__term">' . esc_html($label) . '</dt>'
			. '<dd class="sf-fdetail2__value">' . $cell . '</dd>';
	}
	if ($html === '') {
		return '';
	}
	return '<dl class="sf-fdetail2__params">' . $html . '</dl>';
}
add_shortcode('sf_formula_params', 'sinofresh_formula_params');

/* --------------------------------------------------------------------------
 * Batch H7d — the configurator.
 * ------------------------------------------------------------------------ */

/**
 * Split a pack-size line into its options and their shared tail.
 *
 * "60/90/120 per bottle" is ONE published string describing THREE pack sizes,
 * and a set of three checkboxes needs three values. The tail ("per bottle")
 * is returned separately rather than appended to each option: three options
 * reading "60 per bottle / 90 per bottle / 120 per bottle" is a sentence, and
 * a pack-size control is a row of numbers.
 *
 * A line with no slash is one option and no tail ("1 kg bag"), which is the
 * honest reading — one pack size is a control with one choice, not a control
 * that failed to split.
 *
 * @return array{0: string[], 1: string} Options, then the shared tail.
 */
function sinofresh_formula_pack_parts($pack) {
	$pack = trim((string) $pack);
	if ($pack === '') {
		return array(array(), '');
	}
	/* The numeric run must END where the words begin: group 1 is digits and
	   separators only, group 2 starts with something that is neither. Lazy, so
	   it stops at the first place both halves can match. */
	if (!preg_match('#^([0-9][0-9\s/.,\-+x×]*?)\s+([^0-9/\s].*)$#u', $pack, $m)) {
		return array(array($pack), '');
	}
	$nums = array_values(array_filter(array_map('trim', preg_split('#\s*/\s*#', trim($m[1]))),
		function ($v) {
			return $v !== '';
		}));
	if (count($nums) < 2) {
		return array(array($pack), '');
	}
	return array($nums, trim($m[2]));
}

/**
 * The choice groups for one formula, in print order.
 *
 * ONE PROVIDER, THREE READERS: this array drives the right-column band, tells
 * the endpoint which posted values are values the record actually offers, and
 * tells the dialog which rows a choice replaces. Three readers of one array is
 * the only arrangement in which they cannot disagree about what "Chicken" is
 * called or which pack sizes exist.
 *
 * A group carries:
 *   key      the data attribute, the field name and the posted key
 *   label    the row's name — the same string sinofresh_formula_params() prints
 *   meta     the PRODUCT'S OWN value, as plain text. Printed whether or not the
 *            visitor touches a control, and that is deliberate: it is the no-JS
 *            answer, it is the dialog's fallback, and it is why a group with
 *            neither meta nor options is not emitted at all.
 *   type     'multi'  -> checkboxes     'single' -> radios
 *   style    'chips' | 'image' | 'tiers'
 *   hint     the one-line instruction, or ''
 *   options  value / label / image (url or '') / note (the unit price or tail)
 */
/**
 * The Quantity & Pricing ladder's own formatting (batch H7i).
 *
 * The ladder is read as a price list, so the two halves of a tier are shaped
 * differently: a quantity is a count (thousands separator, no decimals), a
 * price is money (always two decimals, always the same US$ prefix). The admin
 * owns the wording — a tier that is not a plain number is printed exactly as
 * it was typed, so "1000+" or "1,000 (pallet)" survives instead of being
 * flattened into a float.
 */
function sf_tier_number($value) {
	$value = trim((string) $value);
	if ($value === '') {
		return '';
	}
	if (!preg_match('/^[0-9][0-9,]*(\.[0-9]+)?$/', $value)) {
		return $value;
	}
	return number_format((float) str_replace(',', '', $value));
}

/**
 * "10-99" / "100-999" / "≥1,000". An open-ended top tier is what makes the
 * ladder read as a ladder: the last row says "from here up", not "from here
 * to nowhere", which is why the brief's third tier has no max at all.
 */
function sf_tier_range_label($min, $max) {
	$min = sf_tier_number($min);
	$max = sf_tier_number($max);
	if ($min !== '' && $max !== '') {
		return $min . '-' . $max;
	}
	if ($min !== '') {
		return '≥' . $min;
	}
	if ($max !== '') {
		return '≤' . $max;
	}
	return '';
}

/**
 * "US$3.88". One prefix for the whole site: the tier note used to say
 * "USD 3.88 / unit" while the JSON-LD said USD and the ladder's own card says
 * US$, and three spellings of one currency on one page is the kind of drift
 * a reader notices.
 */
function sf_tier_price_label($price) {
	$price = trim((string) $price);
	if ($price === '') {
		return '';
	}
	$bare = trim((string) preg_replace('/^(?:US\$|USD|\$)\s*/i', '', $price));
	if ($bare !== '' && preg_match('/^[0-9][0-9,]*(\.[0-9]+)?$/', $bare)) {
		return 'US$' . number_format((float) str_replace(',', '', $bare), 2, '.', ',');
	}
	return 'US$' . $bare;
}

/**
 * The "Custom" option a choice group may end with (batch H8a).
 *
 * One constructor, because the flag is load-bearing in three places: the
 * renderer draws a text box beside a group that carries one, the endpoint
 * accepts a free-text answer only from a group that carries one, and the two
 * image libraries mark their own Custom row the same way so the shape and
 * container pickers behave exactly like the chips.
 *
 * The option's VALUE stays "Custom". A visitor who picks it and types nothing
 * posts that word and the sales desk reads "Flavor: Custom", which is the
 * honest answer; a visitor who types posts "{text} (custom)" instead — see
 * sinofresh_formula_custom_text().
 */
function sf_formula_custom_option($image = '') {
	return array(
		'value' => 'Custom', 'label' => 'Custom', 'image' => (string) $image, 'note' => '',
		'custom' => true,
	);
}

/**
 * The option list a record-driven group ends with (batch 3b).
 *
 * "Custom" is MARKED rather than appended — the rule
 * sf_formula_library_options() follows for every pool-driven group, and the
 * one the H1 note spells out: appending a second one prints the word twice.
 *
 * The record-driven groups grew their Custom pick a different way: they
 * appended one unconditionally, on the assumption that the record's own list
 * never carries the word. post 158's flavor list does, so its page drew nine
 * chips — the record's own "Custom" with no marker, and the appended one that
 * owns the text box. The unmarked chip was the broken one: picking it checked
 * the radio, opened nothing, and stole the marked chip's tick, so the only
 * answer it could produce was the bare word "Custom" with no flavour in it.
 *
 * Marking the record's own entry settles both halves: the word appears once,
 * and the chip that carries it is the one that opens the box. A record whose
 * list does not already spell Custom is left exactly as it was, so this is a
 * no-op on every page but the one that carried the duplicate.
 */
function sf_formula_options_with_custom($options) {
	foreach ($options as $i => $option) {
		$label = isset($option['label']) ? (string) $option['label'] : '';
		if (0 === strcasecmp($label, 'Custom')) {
			$options[$i]['custom'] = true;
			return $options;
		}
	}
	$options[] = sf_formula_custom_option();
	return $options;
}

/**
 * The text box a group's Custom option reveals (batch H8a).
 *
 * Rendered by the server and `hidden`, then revealed by config.js when the
 * Custom pick is made. Server-rendered for three reasons: the gate can see it
 * in the markup, it is in the tab order without the script having to build it,
 * and with no script at all the group degrades to exactly what it was before
 * the batch — a Custom pick that posts the word "Custom" — rather than to a
 * pick that opens nothing.
 *
 * It is a SIBLING of the option list, not a child of the Custom label. A text
 * input nested in a <label> fights the label's own activation behaviour, so a
 * click on the box would also toggle the radio beside it; outside, the two
 * never touch.
 */
function sf_formula_custom_field($key, $label) {
	return '<div class="sf-fdetail-config__custom" data-sf-config-custom-for="' . esc_attr($key) . '" hidden>'
		. '<input type="text" class="sf-fdetail-config__custom-input"'
		. ' data-sf-config-custom-input="' . esc_attr($key) . '"'
		. ' maxlength="60" autocomplete="off" spellcheck="false"'
		. ' aria-label="' . esc_attr(sprintf('Your own %s', $label)) . '"'
		. ' placeholder="Type your own">'
		. '</div>';
}

/**
 * The visitor's own text, out of the value the page posted (batch H8a).
 *
 * The contract is the page's: a custom answer is posted as "{text} (custom)" —
 * the same string the inquiry is meant to read — so the suffix is both the
 * marker and the check. A value without it is not a custom answer and returns
 * '', and is then dropped exactly as any other unknown value is.
 *
 * The text is sanitised like every other field on the form and capped at 60,
 * because it travels into an email the sales desk reads and into the modal's
 * own summary line.
 */
function sinofresh_formula_custom_text($value) {
	$value = trim((string) $value);
	if (!preg_match('/^(.*?)\s*\(custom\)$/i', $value, $m)) {
		return '';
	}
	$text = trim(sanitize_text_field($m[1]));
	if ($text === '') {
		return '';
	}
	return function_exists('mb_substr') ? mb_substr($text, 0, 60) : substr($text, 0, 60);
}

function sinofresh_formula_config_groups($post_id) {
	$post_id = (int) $post_id;
	if ($post_id <= 0) {
		return array();
	}
	$parts  = sinofresh_formula_specs_parts(trim((string) get_post_meta($post_id, 'sf_formula_specs', true)));
	/* Batch H8b — the dosage form, for the two groups whose options come from
	   a pool rather than from the record. sf_formula_record_form() is the same
	   reader the publishing form uses to resolve those pools, so the page and
	   the editor cannot resolve them differently. */
	$form_slug = function_exists('sf_formula_record_form') ? sf_formula_record_form($post_id) : '';
	$groups = array();

	$flavors = sf_json_array(get_post_meta($post_id, 'sf_formula_flavors', true));
	if ($flavors) {
		$options = array();
		foreach ($flavors as $flavor) {
			$options[] = array('value' => $flavor, 'label' => $flavor, 'image' => '', 'note' => '');
		}
		$options = sf_formula_options_with_custom($options);
		/* H8a — `multi` became `single`, and the hint says so. A flavour is one
		   answer: "Chicken, Beef" is not a product, it is a range, and the
		   sales desk cannot quote from it. Suitable For below stays multi
		   because a formula genuinely is for dogs AND cats. */
		$groups[] = array(
			'key' => 'flavor', 'label' => 'Flavor', 'meta' => implode(', ', $flavors),
			'type' => 'single', 'style' => 'chips',
			'hint' => 'Choose one', 'options' => $options,
		);
	}

	$unit = trim((string) $parts['unit']);
	if ($unit !== '') {
		/* One published weight. A single-choice control with one choice is not
		   a degenerate case here — it is how the row reads as a choice the
		   customer can see, and it is what makes "nothing checked" a state the
		   dialog has to handle. */
		$groups[] = array(
			'key' => 'weight', 'label' => 'Piece Weight', 'meta' => $unit,
			'type' => 'single', 'style' => 'chips', 'hint' => '',
			'options' => sf_formula_options_with_custom(array(
				array('value' => $unit, 'label' => $unit, 'image' => '', 'note' => ''),
			)),
		);
	}

	$pack = trim((string) $parts['pack']);
	if ($pack !== '') {
		list($packs, $pack_tail) = sinofresh_formula_pack_parts($pack);
		if ($packs) {
			$options = array();
			foreach ($packs as $p) {
				$options[] = array('value' => $p, 'label' => $p, 'image' => '', 'note' => '');
			}
			$options = sf_formula_options_with_custom($options);
			$groups[] = array(
				'key' => 'pack', 'label' => 'Pack Size', 'meta' => $pack,
				'type' => 'single', 'style' => 'chips',
				/* TWO STRINGS, because one cannot do both jobs. The hint is
				   what a reader sees beside "60 / 90 / 120"; the unit phrase is
				   what the chosen number has to carry into the inquiry, or the
				   sales desk receives "60, 90" with no unit at all. The first
				   cut printed ONE string to both readers and the page read
				   "Per per bottle" on all 20 pack pages: the splitter's tail
				   already begins with the preposition, because it starts at the
				   first character that is not a digit. */
				'hint' => $pack_tail !== '' ? ucfirst($pack_tail) : 'Choose one',
				'unit_phrase' => $pack_tail,
				'options' => $options,
			);
		}
	}

	$species = sf_json_array(get_post_meta($post_id, 'sf_formula_species', true));
	if ($species) {
		$options = array();
		foreach ($species as $s) {
			$options[] = array('value' => $s, 'label' => $s, 'image' => '', 'note' => '');
		}
		$options = sf_formula_options_with_custom($options);
		$groups[] = array(
			'key' => 'species', 'label' => 'Suitable For', 'meta' => implode(', ', $species),
			'type' => 'multi', 'style' => 'chips',
			'hint' => 'Choose one or more', 'options' => $options,
		);
	}
	$lifestage = trim((string) get_post_meta($post_id, 'sf_formula_lifestage', true));
	if ($lifestage !== '') {
		$groups[] = array(
			'key' => 'stage', 'label' => 'Life Stage', 'meta' => $lifestage,
			'type' => 'single', 'style' => 'chips', 'hint' => '',
			'options' => sf_formula_options_with_custom(array(
				array('value' => $lifestage, 'label' => $lifestage, 'image' => '', 'note' => ''),
			)),
		);
	}

	/* Batch H8b — Shape reads the SAME per-dosage pool the publishing form
	   does, and that is the whole of it.

	   inc/formula-admin.php declares this field as `'pool' => 'shape'`, so a
	   powder's editor can only pick Fine Powder / Granules /
	   Microencapsulated / Custom. This renderer drew sf_shape_library()'s
	   eight soft-chew shapes on all 42 pages regardless — the powder page
	   offered "Bone" and "Paw", and the answer the editor had actually chosen
	   was nowhere on the page. One pool, two readers, and they now agree.

	   The library is not retired: sf_formula_library_options() takes the
	   OPTIONS from the pool and the PICTURES from it, matched by label. Every
	   attachment_id is 0 today, so this changes no pixels — it keeps the
	   "upload the shape images later" path the Site Settings page promises.

	   The group's NAME follows the pool too ("Appearance" on powders and
	   drops and liquids, "Texture" on pastes, "Form" on fish oil), because
	   the pool has always said so and "Shape: Clear" is not a sentence.

	   The record's own sf_formula_shape still gets its word in, verbatim: it
	   is the meta line beside the picker, and it is the same string the spec
	   sheet prints. It never pre-checks the radio — nothing here is checked
	   until the visitor checks it. */
	$shape_label = function_exists('sf_formula_field_pool_label')
		? (string) sf_formula_field_pool_label($form_slug, 'shape') : '';
	if ($shape_label === '') {
		$shape_label = 'Shape';
	}
	$shape_opts = function_exists('sf_formula_library_options')
		? sf_formula_library_options(sf_formula_field_pool($form_slug, 'shape'), sf_shape_library())
		: array();
	if ($shape_opts) {
		$groups[] = array(
			'key' => 'shape', 'label' => $shape_label,
			'meta' => trim((string) get_post_meta($post_id, 'sf_formula_shape', true)),
			'type' => 'single', 'style' => 'image', 'hint' => 'Choose one',
			'options' => $shape_opts,
		);
	}

	/* Batch H8b — Container Type reads the dosage pool too, and renders on
	   every page.

	   Its options were the Site Settings container library, whose rows are
	   "Round / Square / Oval / Jar / Pouch / Tube / Custom" — bottle SHAPES,
	   not containers; "Round" is not a packaging format. The pool that answers
	   this question has existed since batch H1 and is per dosage form
	   (powders: Jar / Foil Pouch / Stand-up Pouch; drops: Dropper Bottle /
	   Glass Bottle / Plastic Bottle; pastes: Plastic Tube / Metal Tube /
	   Aluminum Tube), so the group now says what the buyer is choosing.

	   The old gate went with it: this group used to wait for the record's own
	   sf_formula_container before it rendered, which is why one page in 21
	   drew it. The options no longer depend on the record, so it follows the
	   same rule Shape does. post 158's stored slug "Round" is in no packaging
	   pool; sinofresh_container_label() falls back to the raw value, so the
	   meta line still prints the record's own word rather than dropping a
	   fact, and re-saving that record lands it in the new vocabulary. */
	$container  = trim((string) get_post_meta($post_id, 'sf_formula_container', true));
	$cont_opts  = function_exists('sf_formula_library_options')
		? sf_formula_library_options(sf_formula_field_pool($form_slug, 'packaging'), sf_container_library())
		: array();
	if ($cont_opts) {
		$own = ($container !== '' && function_exists('sinofresh_container_label'))
			? sinofresh_container_label($container) : $container;
		$groups[] = array(
			'key' => 'container', 'label' => 'Container Type', 'meta' => $own,
			'type' => 'single', 'style' => 'image', 'hint' => 'Choose one',
			'options' => $cont_opts,
		);
	}

	/* Batch H7i — the ladder. The admin's row is {min, max, price} (the order's
	   own data shape, replacing the {qty, price} pair), and a legacy qty is read
	   as min so a record that has not been re-saved yet still prints a clean
	   range instead of an empty card. The option's VALUE stays the human label
	   ("10-99") because that is the string the inquiry carries and the endpoint
	   validates against; the price rides along as the option's note, which is
	   what the dialog and the no-JS line print. */
	$tiers = sf_json_rows(get_post_meta($post_id, 'sf_formula_price_tiers', true));
	$tier_opts = array();
	$tier_meta = array();
	foreach ($tiers as $tier) {
		if (!is_array($tier)) {
			continue;
		}
		$min   = trim((string) (isset($tier['min']) ? $tier['min'] : (isset($tier['qty']) ? $tier['qty'] : '')));
		$max   = trim((string) (isset($tier['max']) ? $tier['max'] : ''));
		$price = trim((string) (isset($tier['price']) ? $tier['price'] : ''));
		if ($min === '' && $max === '' && $price === '') {
			continue;
		}
		$range = sf_tier_range_label($min, $max);
		if ($range === '') {
			$range = 'Custom quantity';
		}
		$note = sf_tier_price_label($price) !== '' ? sf_tier_price_label($price) . ' / unit' : '';
		$tier_opts[] = array(
			'value' => $range,
			'label' => $range,
			'note'  => $note,
			'image' => '',
			/* The ladder's own card layout: the price is the headline, the
			   range and the unit are what qualify it. */
			'price_text' => sf_tier_price_label($price),
			'range_text' => $range,
		);
		$tier_meta[] = $range . ($note !== '' ? ' — ' . $note : '');
	}
	if ($tier_opts) {
		/* 待办25 — the ladder heads the column, it does not close it. The brief
		   puts the price directly under the intro and above Flavor: it is the
		   one line a buyer scans for, and at the foot of the list it sat under
		   four choices none of which prices anything. `unshift`, not a second
		   renderer — it is the same group, moved, so the dialog's reprint, the
		   summary line and the no-JS fallback all read it unchanged. */
		array_unshift($groups, array(
			'key' => 'pricing', 'label' => 'Quantity & Pricing', 'meta' => implode(' · ', $tier_meta),
			'type' => 'single', 'style' => 'tiers', 'hint' => 'Choose one',
			'options' => $tier_opts,
			'unit' => 'pieces',
			/* The sample fee is its own meta, not a tier: it is not a quantity
			   break, and a "sample" row inside a price ladder would price one
			   unit of a sample as if it were the product. */
			'sample_price' => sf_tier_price_label(get_post_meta($post_id, 'sf_formula_sample_price', true)),
		));
	}

	return $groups;
}

/**
 * The posted selection, reduced to values this record actually offers.
 *
 * The endpoint's old rule was "the selection panel is rebuilt from the post id,
 * never taken from the request body", and the reason was that a client's copy
 * is a rendering while a posting client could put anything in it. H7d needs the
 * customer's OWN choice in that panel, so the rule is kept in the form that
 * still holds: the request says WHICH options, the server says what they are
 * CALLED. A posted value that is not one of this record's own option values is
 * dropped, so the worst a hand-crafted request can do is choose among the
 * options the page already offered.
 *
 * Batch H8a adds the one exception, and it is bounded so the rule survives it:
 * a group that OFFERS a Custom option accepts a free-text answer as well. The
 * request still cannot name the group's own options, because the custom branch
 * only runs for values the option list rejected, and it only runs at all for a
 * group whose page drew a Custom box. The text is sanitised and capped, and it
 * is stamped "(custom)" so the sales desk can tell a typed answer from a
 * catalogued one.
 *
 * @return array Label => plain-text value, in the groups' print order.
 */
function sinofresh_formula_config_rows($post_id, $posted) {
	$posted = is_array($posted) ? $posted : array();
	$rows   = array();
	foreach (sinofresh_formula_config_groups($post_id) as $group) {
		$key     = $group['key'];
		$allowed = array();
		$labels  = array();
		$custom  = false;
		foreach ($group['options'] as $option) {
			$allowed[] = (string) $option['value'];
			$labels[(string) $option['value']] = $option['label']
				. ($option['note'] !== '' ? ' (' . $option['note'] . ')' : '');
			if (!empty($option['custom'])) {
				$custom = true;
			}
		}
		$want = isset($posted[$key]) ? $posted[$key] : array();
		$want = is_array($want) ? $want : array($want);
		$chosen = array();
		$typed  = array();
		foreach ($want as $value) {
			$value = is_string($value) ? trim($value) : '';
			if ($value === '') {
				continue;
			}
			if (in_array($value, $allowed, true)) {
				if (!in_array($value, $chosen, true)) {
					$chosen[] = $value;
				}
				continue;
			}
			if ($custom) {
				$text = sinofresh_formula_custom_text($value);
				if ($text !== '' && !in_array($text, $typed, true)) {
					$typed[] = $text;
				}
			}
		}
		if (!$chosen && !$typed) {
			continue;
		}
		$text = array();
		foreach ($chosen as $value) {
			$text[] = $labels[$value];
		}
		foreach ($typed as $own) {
			$text[] = $own . ' (custom)';
		}
		$rows[$group['label']] = implode(', ', $text);
		/* The unit the options share is printed with the choice, or "60, 90"
		   arrives at the sales desk with no unit at all. Read from the group's
		   own unit phrase, NOT sliced out of the hint: the hint is display
		   text and is capitalised for the reader, and the two stopped being
		   the same string the day the page read "Per per bottle". */
		if ($group['label'] === 'Pack Size' && !empty($group['unit_phrase'])) {
			$rows[$group['label']] .= ' ' . $group['unit_phrase'];
		}
	}
	return $rows;
}

/**
 * [sf_formula_config] — the right column's choice controls (batch H7d).
 *
 * Seven rows that were plain text become controls: Flavor, Piece Weight, Pack
 * Size, Suitable For, Life Stage, Container Type and Quantity & Pricing. The
 * rows that are NOT choices — Shelf life, Certifications, Lead time — stay
 * text and stay in [sf_formula_params], which is why the two renderers exist
 * side by side rather than one replacing the other.
 *
 * Batch H8a: Flavor and Pack Size became single-choice (one flavour is one
 * answer), and every choice group may now end in a Custom pick that reveals a
 * text box. The box is server-rendered and hidden — see
 * sf_formula_custom_field() — and the answer it collects is the one thing on
 * this form a visitor writes themselves, so the endpoint validates it rather
 * than merely forwarding it (sinofresh_formula_custom_text()).
 *
 * Every group prints its own value as text (`__meta`) whether or not anything
 * is checked. That single decision does three jobs: it is the no-JS answer
 * (nothing is lost when config.js never arrives), it is the dialog's fallback
 * ("nothing checked" still shows the product's specification), and it means
 * the controls are read as "change this" rather than "we do not know this".
 *
 * Nothing here is pre-checked. A visitor who touches nothing posts nothing, and
 * the inquiry carries the record's own values — the behaviour the dialog had
 * before this batch, reached by a different route.
 */
function sinofresh_formula_config() {
	if (!is_singular('sf_formula')) {
		return '';
	}
	$post_id = (int) get_queried_object_id();
	if ($post_id <= 0) {
		return '';
	}
	$groups = sinofresh_formula_config_groups($post_id);
	if (!$groups) {
		return '';
	}

	$html = '';
	foreach ($groups as $group) {
		$key   = (string) $group['key'];
		$type  = $group['type'] === 'single' ? 'radio' : 'checkbox';
		$name  = 'sf-config-' . $key;
		$hint  = trim((string) $group['hint']);

		/* The price ladder is the one group that is not pills (batch H7i). It
		   keeps every property the other groups have — a real radio per tier,
		   the same data-sf-config-opt hook, the same is-on class config.js
		   toggles — and changes only what a tier has to say: a price big
		   enough to compare down a row, the range under it, and a dot at the
		   foot so the chosen break is still a visible pick. The option's own
		   text span is skipped (the price IS the label); config.js falls back
		   to the input's value, which is the range. */
		if ($group['style'] === 'tiers') {
			$unit = trim((string) (isset($group['unit']) ? $group['unit'] : ''));
			$cards = '';
			foreach ($group['options'] as $option) {
				$cards .= '<label class="sf-fdetail-config__opt sf-tier">'
					. '<input class="sf-fdetail-config__input" type="radio"'
					. ' name="' . esc_attr($name) . '" value="' . esc_attr((string) $option['value']) . '"'
					. ' data-sf-config-opt="' . esc_attr($key) . '">'
					. '<span class="sf-tier__price">' . esc_html((string) $option['price_text']) . '</span>'
					. '<span class="sf-tier__range">' . esc_html((string) $option['range_text']) . '</span>'
					. ($unit !== '' ? '<span class="sf-tier__unit">' . esc_html($unit) . '</span>' : '')
					. '<span class="sf-tier__dot" aria-hidden="true"></span>'
					. '</label>';
			}

			/* The sample row. It lives INSIDE the ladder's own block because it
			   is what the buyer asks after reading the breaks, and it is only
			   printed when the record carries a sample fee — a "Get Sample"
			   button with no price beside it is a promise the record has not
			   made. The button is an <a> carrying data-sf-inquiry-open, the same
			   contract the hero and the float capsule use: the dialog when the
			   script is there, /contact/#quote when it is not. */
			$sample = '';
			$sample_price = isset($group['sample_price']) ? (string) $group['sample_price'] : '';
			if ($sample_price !== '') {
				$sample = '<div class="sf-fdetail-config__sample">'
					. '<span class="sf-fdetail-config__sample-icon" aria-hidden="true">'
					. '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"'
					. ' stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" focusable="false">'
					. '<path d="M21 8 12 3 3 8v8l9 5 9-5V8Z"/><path d="m3 8 9 5 9-5"/><path d="M12 13v8"/>'
					. '</svg></span>'
					. '<span class="sf-fdetail-config__sample-label">Sample price</span>'
					. '<span class="sf-fdetail-config__sample-price">' . esc_html($sample_price) . '</span>'
					. '<a class="sf-fdetail-config__sample-cta" href="/contact/#quote" data-sf-inquiry-open'
					. ' data-sf-inquiry-sample="' . esc_attr($sample_price) . '">Get Sample</a>'
					. '</div>';
			}

			$html .= '<div class="sf-fdetail-config__group" data-sf-config-group="' . esc_attr($key) . '">'
				. '<p class="sf-fdetail-config__row">'
				. '<span class="sf-fdetail-config__label">' . esc_html((string) $group['label']) . '</span>'
				. '<span class="sf-fdetail-config__meta">' . esc_html((string) $group['meta']) . '</span>'
				. ($hint !== ''
					? '<span class="sf-fdetail-config__hint">' . esc_html($hint) . '</span>' : '')
				. '</p>'
				. '<div class="sf-fdetail-config__options sf-fdetail-config__tiers" role="group"'
				. ' aria-label="' . esc_attr((string) $group['label']) . '">' . $cards . '</div>'
				. $sample
				. '</div>';
			continue;
		}

		$opts = '';
		$has_custom = false;
		foreach ($group['options'] as $option) {
			$value   = (string) $option['value'];
			$img     = (string) $option['image'];
			$media   = '';
			$in_slot = false;
			$is_custom = !empty($option['custom']);
			if ($is_custom) {
				$has_custom = true;
			}
			if ($group['style'] === 'image') {
				/* An empty library slot degrades to the label, never to a broken
				   image: the Container Library ships with every attachment_id
				   at 0, and a picker that renders seven broken icons because an
				   admin has not uploaded anything yet is worse than a picker
				   that renders seven names. */
				if ($img !== '') {
					$media = '<img class="sf-fdetail-config__img" src="' . esc_url($img) . '" alt="" loading="lazy">';
				} else {
					$in_slot = true;
					/* H7g: the dashed box carries the name itself, centred —
					   the placeholder the brief describes. The separate text
					   span is skipped so the name is written once, and
					   config.js reads the label back out of the box. */
					$media = '<span class="sf-fdetail-config__img sf-fdetail-config__img--empty">'
						. '<span class="sf-fdetail-config__empty-label">' . esc_html((string) $option['label']) . '</span>'
						. '</span>';
				}
			}
			$note = (string) $option['note'];
			$opts .= '<label class="sf-fdetail-config__opt"'
				. ($is_custom ? ' data-sf-config-custom="1"' : '') . '>'
				. '<input class="sf-fdetail-config__input" type="' . esc_attr($type) . '"'
				. ' name="' . esc_attr($name) . '" value="' . esc_attr($value) . '"'
				. ' data-sf-config-opt="' . esc_attr($key) . '">'
				. '<span class="sf-fdetail-config__box" aria-hidden="true"></span>'
				. $media
				. ($in_slot
					? ''
					: '<span class="sf-fdetail-config__text">' . esc_html((string) $option['label']) . '</span>')
				. ($note !== ''
					? '<span class="sf-fdetail-config__note">' . esc_html($note) . '</span>' : '')
				. '</label>';
		}

		$html .= '<div class="sf-fdetail-config__group" data-sf-config-group="' . esc_attr($key) . '">'
			. '<p class="sf-fdetail-config__row">'
			. '<span class="sf-fdetail-config__label">' . esc_html((string) $group['label']) . '</span>'
			. '<span class="sf-fdetail-config__meta">' . esc_html((string) $group['meta']) . '</span>'
			. ($hint !== ''
				? '<span class="sf-fdetail-config__hint">' . esc_html($hint) . '</span>' : '')
			. '</p>'
			. '<div class="sf-fdetail-config__options" role="group"'
			. ' aria-label="' . esc_attr((string) $group['label']) . '">' . $opts . '</div>'
			. ($has_custom ? sf_formula_custom_field($key, (string) $group['label']) : '')
			. '</div>';
	}

	/* The live summary is empty in the markup and filled by config.js: an
	   empty element that says nothing is honest, while a server-rendered
	   "nothing selected yet" would be a claim the server cannot keep once the
	   visitor starts ticking. */
	return '<div class="sf-fdetail-config" data-sf-config>'
		. '<div class="sf-fdetail-config__list">' . $html . '</div>'
		. '<p class="sf-fdetail-config__summary" data-sf-config-summary hidden></p>'
		. '<p class="sf-fdetail-config__note" data-sf-config-note hidden>'
		. 'Your selection is attached to the inquiry.</p>'
		. '</div>';
}
add_shortcode('sf_formula_config', 'sinofresh_formula_config');

/**
 * [sf_formula_specs_table] — the buyer's spec sheet (batch H7c).
 *
 * Twelve rows at the top of the detail page's reading area, before the long
 * copy and the "Formula & nutrition" band that carries Ingredients: what the
 * product IS (dosage form, shape, unit weight, pack size, shelf life), what
 * goes into it (applicable pet, life stage, main ingredients), and what a
 * buyer has to know before asking for a quote (MOQ, certifications, place of
 * origin, OEM/ODM).
 *
 * Twelve, not thirteen. The brief listed Lead Time as a thirteenth row and
 * left it to this renderer to keep or fold. It is dropped rather than merged:
 * it already has a row of its own in the media column's parameter list, and
 * the only cell it could share — MOQ — would put "from 500–1,000 units" beside
 * "Typically 7–15 working days after packaging is ready" as one sentence about
 * quantity. Dropping it costs the page nothing, because the fact is still on
 * the page.
 *
 * Every value comes from a source the page already trusts:
 *
 *   Dosage Form        taxonomy sf_formula_form          (the term's own name)
 *   Applicable Pet     sf_formula_species                (multi, chips)
 *   Life Stage         sf_formula_lifestage              (text)
 *   Shape              sf_formula_shape                  (text)
 *   Unit Weight        sf_formula_specs                  (parsed: unit segment)
 *   Pack Size          sf_formula_specs                  (parsed: "… per …")
 *   Shelf Life         sf_formula_shelf_life            (the fixed pool, H8a;
 *                      the spec sheet's "… shelf life" segment is the
 *                      fallback — see sinofresh_formula_shelf_life_line())
 *   Main Ingredients   sf_formula_ingredients            (the first three)
 *   MOQ                dosage page .sf-facts-mini row    (via spec_cell)
 *   Certifications     Site Settings sf_certifications   (the same reader the
 *                      factsheet row and the batch C FAQ answer use, so the
 *                      three cannot disagree about the credential list)
 *   Place of Origin    Site Settings sf_factory_origin   (batch H7e; the field
 *                      ships with the constant it replaced, so no page moved)
 *   OEM / ODM          Site Settings sf_factory_oem      (batch H7e, same)
 *
 * sf_formula_shape is read although nothing registers it. The field predates
 * the meta registry and exists on one record; WordPress reads an unregistered
 * key without complaint, and registering it here would advertise a publishing
 * field the rest of the form does not offer yet.
 *
 * Main Ingredients stops at three. The "Formula & nutrition" band one screen
 * below prints the whole list as pills, so this row only has to answer "what
 * is this made of" at a glance. The cut is silent on purpose: an "and more"
 * tail would make the table promise a list it then truncates, and the complete
 * list is a band away.
 *
 * Empty means absent, the contract [sf_formula_params] keeps: a row with no
 * value is not rendered at all, so the row set differs per record by design
 * and the gate asserts the renderer rather than a fixed row count. On today's
 * 21 records that drops Applicable Pet and Life Stage everywhere (neither meta
 * key exists yet) and Shape on twenty of them — the first two rows are for the
 * sales team to fill in, not for a deploy.
 *
 * The rows are dealt into two columns by the stylesheet, and the split is made
 * over the rows ACTUALLY rendered rather than over the field list: a record
 * with nine rows gets five and four. Splitting the field list instead would
 * leave a column that lost three fields with a gap under it, which is the
 * opposite of what two columns are for.
 *
 * Returns '' outside a single sf_formula, so a stray shortcode in the editor
 * cannot leak another formula's specification into an article.
 */
function sinofresh_formula_specs_table() {
	if (!is_singular('sf_formula')) {
		return '';
	}
	$post_id = (int) get_queried_object_id();
	if ($post_id <= 0) {
		return '';
	}

	$form_slug = '';
	$form_name = '';
	$form_terms = wp_get_post_terms($post_id, 'sf_formula_form');
	if (!is_wp_error($form_terms) && $form_terms) {
		$form_slug = (string) $form_terms[0]->slug;
		$form_name = (string) $form_terms[0]->name;
	}

	$parts = sinofresh_formula_specs_parts(trim((string) get_post_meta($post_id, 'sf_formula_specs', true)));

	/* Each cell is escaped where it is built — the chip builder escapes its own
	   values — so the row loop below must not escape a second time. */
	$rows = array();

	if ($form_name !== '') {
		$rows['Dosage Form'] = esc_html($form_name);
	}
	$species = sf_json_array(get_post_meta($post_id, 'sf_formula_species', true));
	if ($species) {
		$rows['Applicable Pet'] = sinofresh_formula_specs_table_chips($species);
	}
	$value = trim((string) get_post_meta($post_id, 'sf_formula_lifestage', true));
	if ($value !== '') {
		$rows['Life Stage'] = esc_html($value);
	}
	$value = trim((string) get_post_meta($post_id, 'sf_formula_shape', true));
	if ($value !== '') {
		/* Batch H8b — the row is named whatever the dosage form calls this
		   question, because the picker one screen up is. A powder sheet that
		   said "Shape: Fine Powder" under a picker headed "Appearance" would
		   be this batch contradicting itself. On today's data the label only
		   ever resolves to "Shape" (the one record carrying a value is a soft
		   chew), so this is a no-op in bytes and a correctness fix for the
		   first powder the sales desk fills in. */
		$shape_row = function_exists('sf_formula_field_pool_label')
			? (string) sf_formula_field_pool_label($form_slug, 'shape') : '';
		$rows[($shape_row !== '' ? $shape_row : 'Shape')] = esc_html($value);
	}
	if (trim((string) $parts['unit']) !== '') {
		$rows['Unit Weight'] = esc_html(trim((string) $parts['unit']));
	}
	if (trim((string) $parts['pack']) !== '') {
		$rows['Pack Size'] = esc_html(trim((string) $parts['pack']));
	}
	$shelf = sf_formula_shelf_life_line($post_id, $parts);
	if ($shelf !== '') {
		$rows['Shelf Life'] = esc_html($shelf);
	}
	/* The comma is the separator every sf_formula_ingredients value uses. */
	$ingredients = array();
	foreach (explode(',', (string) get_post_meta($post_id, 'sf_formula_ingredients', true)) as $line) {
		$line = trim($line);
		if ($line !== '') {
			$ingredients[] = $line;
		}
	}
	$ingredients = array_slice($ingredients, 0, 3);
	if ($ingredients) {
		$rows['Main Ingredients'] = sinofresh_formula_specs_table_chips($ingredients);
	}
	$value = ($form_slug !== '') ? sinofresh_formula_spec_cell($form_slug, 'MOQ') : '';
	if (trim((string) $value) !== '') {
		$rows['MOQ'] = esc_html(trim((string) $value));
	}
	$value = sf_formula_certifications_value($form_slug);
	if (trim((string) $value) !== '') {
		$rows['Certifications'] = esc_html(trim((string) $value));
	}
	/* Batch H7e moved both of these out of this function and into Site Settings
	   -> Factory Information. They are read through one reader rather than
	   through get_option() twice, so the fallback is the settings page's own
	   default instead of a second copy living here — and the values those two
	   fields ship with are the constants that used to stand on these two lines,
	   character for character, which is why none of the 75 captured pages
	   moved. The empty-means-absent contract reaches them as well: a row with
	   no value is not rendered at all. */
	$value = sf_formula_factory_value('sf_factory_origin');
	if ($value !== '') {
		$rows['Place of Origin'] = esc_html($value);
	}
	$value = sf_formula_factory_value('sf_factory_oem');
	if ($value !== '') {
		$rows['OEM / ODM'] = esc_html($value);
	}

	if (!$rows) {
		return '';
	}

	$half = (int) ceil(count($rows) / 2);
	$html = '';
	foreach (array(array_slice($rows, 0, $half, true), array_slice($rows, $half, null, true)) as $group) {
		if (!$group) {
			continue;
		}
		$body = '';
		foreach ($group as $label => $cell) {
			$body .= '<div class="sf-fdetail-specs__row">'
				. '<dt class="sf-fdetail-specs__term">' . esc_html($label) . '</dt>'
				. '<dd class="sf-fdetail-specs__value">' . $cell . '</dd>'
				. '</div>';
		}
		$html .= '<dl class="sf-fdetail-specs__group">' . $body . '</dl>';
	}
	return '<section class="sf-fdetail-specs"><div class="sf-fdetail-specs__inner">'
		. $html
		. '</div></section>';
}
add_shortcode('sf_formula_specs_table', 'sinofresh_formula_specs_table');

/** The spec sheet's multi-value rows: chips. '' when nothing is left. */
function sinofresh_formula_specs_table_chips($items) {
	$out = '';
	foreach ((array) $items as $item) {
		$item = trim((string) $item);
		if ($item === '') {
			continue;
		}
		$out .= '<span class="sf-fdetail-specs__chip">' . esc_html($item) . '</span>';
	}
	return $out;
}

/** One chip per value, for the multi-select rows (Flavor, Suitable For). */
function sinofresh_formula_chip_list($items) {
	$out = '';
	foreach ((array) $items as $item) {
		$item = trim((string) $item);
		if ($item === '') {
			continue;
		}
		$out .= '<span class="sf-fdetail2__chip">' . esc_html($item) . '</span>';
	}
	return $out;
}

/**
 * The tier rows as a table, or '' when no row carries anything.
 *
 * A row is kept when either cell has text: a tier list that is half filled
 * still tells a buyer something ("from 500 pcs"), and dropping it would hide
 * the one field the page cannot guess. Fully blank rows are padding from the
 * admin table widget and are what gets dropped.
 *
 * The column headers come from the same labels the admin form shows, so the
 * page and the form cannot disagree about which column is which.
 */
function sinofresh_formula_tier_table($rows) {
	$body = '';
	foreach ((array) $rows as $row) {
		if (!is_array($row)) {
			continue;
		}
		$qty   = trim((string) (isset($row['qty']) ? $row['qty'] : ''));
		$price = trim((string) (isset($row['price']) ? $row['price'] : ''));
		if ($qty === '' && $price === '') {
			continue;
		}
		$body .= '<tr><td class="sf-fdetail2__tier-qty">' . esc_html($qty) . '</td>'
			. '<td class="sf-fdetail2__tier-price">' . esc_html($price) . '</td></tr>';
	}
	if ($body === '') {
		return '';
	}
	return '<table class="sf-fdetail2__tiers"><thead><tr>'
		. '<th scope="col">Min quantity</th><th scope="col">Unit price (USD)</th>'
		. '</tr></thead><tbody>' . $body . '</tbody></table>';
}

/**
 * [sf_formula_body] — the formula's own long-form copy (post_content).
 *
 * A formula is a catalogue record, not an article: all 21 published instances
 * have an empty post_content today, and the brief requires the band to
 * disappear in that state rather than leave an empty padded section behind.
 * A static block template cannot express that — wp:post-content always
 * renders its wrapper, and a {{placeholder}} cannot gate a block because
 * block templates run do_shortcode() before do_blocks(), so placeholders are
 * substituted after the block tree is decided. Hence a shortcode, which is
 * the theme's existing answer for "server-side conditional rendering inside
 * a static template" (see sf_formula_grid).
 *
 * The band markup lives here rather than in the template (with plain
 * .sf-fdetail-body classes, not wp-block-group) for the same reason: an
 * empty band is exactly what must not be emitted. Prose rhythm is in
 * style.css 37b, mirroring 35d for .sf-single-body.
 */
function sinofresh_formula_body() {
	if (!is_singular('sf_formula')) {
		return '';
	}
	$post = get_post((int) get_queried_object_id());
	if (!($post instanceof WP_Post)) {
		return '';
	}
	if (trim((string) $post->post_content) === '') {
		return '';
	}
	$html = (string) apply_filters('the_content', $post->post_content);
	if (trim($html) === '') {
		return '';
	}
	return '<section class="sf-fdetail-body"><div class="sf-fdetail-body__inner">' . $html . '</div></section>';
}
add_shortcode('sf_formula_body', 'sinofresh_formula_body');

/**
 * [sf_formula_detail_actives] — the "Formula & nutrition" band on a formula
 * detail page.
 *
 * The Specification cards above it already print the same two fields as plain
 * text; this band is that record read as data instead of prose — the
 * ingredient list as pills and the guaranteed analysis as the compact
 * term/value grid — so a buyer comparing two formulas can scan levels rather
 * than parse a sentence. Both readings are deliberate: the card is the record,
 * the band is the comparison.
 *
 * Reads post meta directly: the record stays editable in wp-admin while the
 * template does not (authority guard), and there is no longer a JSON mirror
 * to prefer — the grid's K2 payload went in batch H6.
 *
 * Parsing reuses the two helpers the retired [sf_formula_actives] band left
 * behind — sinofresh_formula_split_top_level() and
 * sinofresh_formula_analysis_pairs(). They were written for that band, which
 * batch H6 removed once no template called it; this function is now their
 * only consumer, and the split they implement is unchanged, so the pills and
 * the term/value rows cannot disagree about where an ingredient ends.
 *
 * Emits its own <section> and returns '' when both fields are empty, so the
 * band collapses to zero bytes: no empty padded section, no orphan heading.
 * Same convention as [sf_formula_body] above.
 */
function sinofresh_formula_detail_actives() {
	if (!is_singular('sf_formula')) {
		return '';
	}
	$post_id = (int) get_queried_object_id();
	if (!$post_id) {
		return '';
	}
	$ingredients = trim((string) get_post_meta($post_id, 'sf_formula_ingredients', true));
	$analysis    = trim((string) get_post_meta($post_id, 'sf_formula_analysis', true));
	if ($ingredients === '' && $analysis === '') {
		return '';
	}

	$body  = '';
	$pills = '';
	foreach (sinofresh_formula_split_top_level($ingredients) as $term) {
		$pills .= '<li class="sf-actives__pill">' . esc_html($term) . '</li>';
	}
	if ($pills !== '') {
		$body .= '<p class="sf-actives__label">' . esc_html('Ingredients') . '</p>'
			. '<ul class="sf-actives__ing">' . $pills . '</ul>';
	}

	/* A segment with no level, or with no subject, is not a row — the dry run
	   (tools/b2d1_parser_dryrun.php §2/§3) finds none in the 21 live records,
	   and rendering one would emit an empty <dd>. */
	$rows = '';
	foreach (sinofresh_formula_analysis_pairs($analysis) as $pair) {
		if ($pair['term'] === '' || $pair['value'] === '') {
			continue;
		}
		$rows .= '<div class="sf-spec-row">'
			. '<dt class="sf-spec-term">' . esc_html($pair['term']) . '</dt>'
			. '<dd class="sf-spec-value">' . esc_html($pair['value']) . '</dd>'
			. '</div>';
	}
	if ($rows !== '') {
		$body .= '<p class="sf-actives__label">' . esc_html('Guaranteed Analysis') . '</p>'
			. '<dl class="sf-spec-list">' . $rows . '</dl>';
	}
	if ($body === '') {
		return '';
	}

	return '<section class="sf-fdetail-actives"><div class="sf-fdetail-actives__inner">'
		. '<h2 class="sf-fdetail-actives__title">' . esc_html('Formula & nutrition') . '</h2>'
		. $body
		. '</div></section>';
}
add_shortcode('sf_formula_detail_actives', 'sinofresh_formula_detail_actives');

/**
 * [sf_formula_detail_composition] — the "Ingredients & composition" band.
 *
 * Reads two meta fields that are empty on all 21 records today. They are
 * registered with show_in_rest (see sinofresh_register_formula_types), so the
 * band can be filled from wp-admin without touching this template.
 *
 * Deliberately does NOT fall back to sf_formula_ingredients: that field is
 * free text whose meaning differs per record (an active list on "Ear Care
 * Drops", a percentage bill of materials on "Hairball Remedy Paste") and it
 * is already shown twice on this page above. A third printing of the same
 * string would not be a composition section.
 *
 * Returns '' with no values, so the page carries nothing at all.
 */
function sinofresh_formula_detail_composition() {
	if (!is_singular('sf_formula')) {
		return '';
	}
	$post_id = (int) get_queried_object_id();
	if (!$post_id) {
		return '';
	}
	$rows = '';
	foreach (array(
		'Base'              => 'sf_formula_base',
		'Other ingredients' => 'sf_formula_other_ingredients',
	) as $label => $key) {
		$value = trim((string) get_post_meta($post_id, $key, true));
		if ($value === '') {
			continue;
		}
		$rows .= '<div class="sf-spec-row">'
			. '<dt class="sf-spec-term">' . esc_html($label) . '</dt>'
			. '<dd class="sf-spec-value">' . esc_html($value) . '</dd>'
			. '</div>';
	}
	if ($rows === '') {
		return '';
	}
	return '<section class="sf-fdetail-composition"><div class="sf-fdetail-composition__inner">'
		. '<h2 class="sf-fdetail-composition__title">' . esc_html('Ingredients & composition') . '</h2>'
		. '<dl class="sf-spec-list">' . $rows . '</dl>'
		. '</div></section>';
}
add_shortcode('sf_formula_detail_composition', 'sinofresh_formula_detail_composition');

/**
 * [sf_formula_content] — the detailed content area (batch H3).
 *
 * What it deliberately does NOT print is the point of the batch. The brief
 * asked for six blocks; three of them would have been a second or a fifth
 * printing of a field already on the page:
 *
 *   sf_formula_ingredients   already printed once by ⑤ Formula & nutrition
 *   sf_formula_analysis      already printed once by ⑤ Formula & nutrition
 *   sf_formula_specs         already printed four times (the ④ card plus the
 *                            three H2a parameter rows parsed out of it)
 *   sf_formula_shelf_life    the same fact as the H2a "Shelf life" row
 *
 * The first two are exactly the duplication a previous batch removed on
 * purpose — see sinofresh_formula_detail() above, which records that they
 * "were being rendered twice on every detail page". Printing them again here
 * would undo that; printing specs would take it to five appearances on one
 * page. So this band carries only what the page cannot already prove:
 * Recommended For, Use Cases, Who It's For, and Packaging & Specifications.
 *
 * Shelf life is left out of Packaging & Specifications for the third reason
 * (user ruling, 2026-09-22): sf_formula_shelf_life is 21/21 "18 months" and
 * has never been read on the front end, while the parameter row above derives
 * the same fact from sf_formula_specs. Two sources for one fact drift; the
 * rule here is one source of record per fact, and that source is already
 * upstream. The key stays registered and the dead end is logged for H6.
 *
 * Empty means absent, everywhere: a field with no value contributes zero
 * bytes, never an empty heading or a hollow box. All seven remaining keys are
 * 0/21 today (the sales team has not started backfilling), so on the live 21
 * records this band renders Packaging & Specifications → Storage and nothing
 * else — which is the approved "ship the renderer before the data" mode from
 * batch H2a, not a fault.
 *
 * Storage is the one input that is not a field, which is why the band itself is
 * never empty today: the closing guard is reachable only if Storage stops being
 * static. It is kept for that day — the template relies on this shortcode being
 * able to emit nothing, and that contract should not rest on a hardcoded string
 * staying hardcoded.
 *
 * Background is card-white, the same as the three bands above it, and the
 * heading levels stay flat (four sibling h2s) so the document outline matches
 * the reading order; the group heading takes the smaller 20px class rather
 * than an h3, which would have nested it under "Who It's For". Alternate
 * background stripes were considered and rejected: the three bands above are
 * one continuous "this formula's data" surface by design (style.css 8103).
 */
function sinofresh_formula_content() {
	if (!is_singular('sf_formula')) {
		return '';
	}
	$post_id = (int) get_queried_object_id();
	if ($post_id <= 0) {
		return '';
	}

	$blocks = '';

	$value = trim((string) get_post_meta($post_id, 'sf_formula_recommended_for', true));
	if ($value !== '') {
		$blocks .= sinofresh_formula_content_block('Recommended For',
			'<p class="sf-fdetail-content__prose">' . esc_html($value) . '</p>');
	}

	/* One line of the field is one use case. A single line reads as a
	   sentence, not as a bulleted list of one — same text either way. */
	$items = array();
	foreach (preg_split('/\R/u', (string) get_post_meta($post_id, 'sf_formula_use_cases', true)) as $line) {
		$line = trim((string) $line);
		if ($line !== '') {
			$items[] = $line;
		}
	}
	if ($items) {
		if (count($items) === 1) {
			$blocks .= sinofresh_formula_content_block('Use Cases',
				'<p class="sf-fdetail-content__prose">' . esc_html($items[0]) . '</p>');
		} else {
			$li = '';
			foreach ($items as $item) {
				$li .= '<li class="sf-fdetail-content__item">' . esc_html($item) . '</li>';
			}
			$blocks .= sinofresh_formula_content_block('Use Cases',
				'<ul class="sf-fdetail-content__list">' . $li . '</ul>');
		}
	}

	$value = trim((string) get_post_meta($post_id, 'sf_formula_who_for', true));
	if ($value !== '') {
		$blocks .= sinofresh_formula_content_block("Who It's For",
			'<p class="sf-fdetail-content__prose">' . esc_html($value) . '</p>');
	}

	/* Packaging & Specifications. Container Type contributes one chip: the
	   record's own value, read through sinofresh_container_label() so a value
	   that is a Site Settings library slug prints as its label. Batch H8b made
	   the picker's vocabulary the dosage pool's (labels such as "Pump Bottle")
	   and left this reader alone on purpose — the label it returns for a pool
	   label is the label itself, and for the one legacy slug on record
	   ("Round") it returns the raw word rather than dropping the fact. */
	$specs = '';
	$container = trim((string) get_post_meta($post_id, 'sf_formula_container', true));
	if ($container !== '') {
		$specs .= sinofresh_formula_content_spec('Container Options',
			sinofresh_formula_content_chips(array(sinofresh_container_label($container))));
	}
	$specs .= sinofresh_formula_content_spec('Additional Packaging',
		sinofresh_formula_content_chips(sf_json_array(get_post_meta($post_id, 'sf_formula_packaging_extra', true))));
	$specs .= sinofresh_formula_content_spec('Color Options',
		sinofresh_formula_content_chips(sf_json_array(get_post_meta($post_id, 'sf_formula_colors', true))));
	$specs .= sinofresh_formula_content_spec('Storage',
		'<p class="sf-fdetail-content__prose">' . esc_html(sinofresh_formula_storage_line()) . '</p>');
	$specs .= sinofresh_formula_content_cartons(sf_json_rows(get_post_meta($post_id, 'sf_formula_cartons', true)));

	if ($specs !== '') {
		$blocks .= sinofresh_formula_content_block('Packaging & Specifications',
			'<div class="sf-fdetail-content__specs">' . $specs . '</div>', true);
	}

	if ($blocks === '') {
		return '';
	}
	return '<section class="sf-fdetail-content"><div class="sf-fdetail-content__inner">'
		. $blocks
		. '</div></section>';
}
add_shortcode('sf_formula_content', 'sinofresh_formula_content');

/**
 * One block of the content area: a heading plus already-escaped inner HTML.
 *
 * A formatter with no opinion: every caller decides whether it has content
 * before it calls. There is deliberately no empty-value guard inside — all four
 * call sites test their own field first, so a guard here would be unreachable
 * (and an unreachable guard is one no test can ever fail on). _spec below is
 * the opposite case and does guard, because its value arrives from a builder
 * that returns '' for empty input rather than from a field the caller read.
 *
 * $subtitle picks the 20px group class for "Packaging & Specifications". The
 * element stays <h2>: a smaller size is a visual weight, while <h3> would
 * make the browser (and a crawler) read the packaging group as a child of
 * "Who It's For".
 */
function sinofresh_formula_content_block($label, $inner, $subtitle = false) {
	$class = $subtitle ? 'sf-fdetail-content__subtitle' : 'sf-fdetail-content__heading';
	return '<div class="sf-fdetail-content__block">'
		. '<h2 class="' . $class . '">' . esc_html($label) . '</h2>'
		. (string) $inner
		. '</div>';
}

/**
 * One sub-block of "Packaging & Specifications": a label plus its value.
 * Returns '' on an empty value, so a label never outlives its content.
 */
function sinofresh_formula_content_spec($label, $inner) {
	$inner = (string) $inner;
	if (trim($inner) === '') {
		return '';
	}
	return '<div class="sf-fdetail-content__spec">'
		. '<p class="sf-fdetail-content__label">' . esc_html($label) . '</p>'
		. $inner
		. '</div>';
}

/** Outline chips, the site's existing pill vocabulary; '' when empty. */
function sinofresh_formula_content_chips($values) {
	$chips = '';
	foreach ((array) $values as $value) {
		$value = trim((string) $value);
		if ($value === '') {
			continue;
		}
		$chips .= '<li class="sf-fdetail-content__chip">' . esc_html($value) . '</li>';
	}
	if ($chips === '') {
		return '';
	}
	return '<ul class="sf-fdetail-content__chips">' . $chips . '</ul>';
}

/**
 * Carton rows as a table. A row is kept when any of the three cells has text,
 * and fully blank rows are dropped — the same rule sinofresh_formula_tier_table
 * applies, because both tables are fed by the same admin widget, which always
 * ships one blank row. The column headers are the publishing form's own
 * labels so page and form cannot disagree about which column is which.
 */
function sinofresh_formula_content_cartons($rows) {
	$body = '';
	foreach ((array) $rows as $row) {
		if (!is_array($row)) {
			continue;
		}
		$cells = array();
		$any   = false;
		foreach (array('count', 'boxes', 'size') as $col) {
			$cell    = trim((string) (isset($row[$col]) ? $row[$col] : ''));
			$cells[] = $cell;
			$any     = $any || ($cell !== '');
		}
		if (!$any) {
			continue;
		}
		$body .= '<tr><td>' . esc_html($cells[0]) . '</td><td>' . esc_html($cells[1])
			. '</td><td>' . esc_html($cells[2]) . '</td></tr>';
	}
	if ($body === '') {
		return '';
	}
	return sinofresh_formula_content_spec('Carton Dimensions',
		'<table class="sf-fdetail-content__cartons"><thead><tr>'
		. '<th scope="col">Pack count</th><th scope="col">Units per carton</th>'
		. '<th scope="col">Carton size (cm)</th></tr></thead><tbody>'
		. $body . '</tbody></table>');
}

/**
 * The container library's label for a slug, or the raw value when the slug is
 * not in the library. Falling back to the stored value rather than dropping it
 * is deliberate: a library that was renamed would otherwise silently delete a
 * fact from 21 pages, and the raw slug is at least diagnosable.
 */
function sinofresh_container_label($slug) {
	$slug = (string) $slug;
	foreach (sf_container_library() as $c) {
		if ($c['slug'] === $slug && trim((string) $c['label']) !== '') {
			return (string) $c['label'];
		}
	}
	return $slug;
}

/**
 * The storage line. Not a meta field: it is the same sentence for every
 * product, so a field would only add 21 chances to typo it.
 *
 * Written as a specification value, not as the FAQ answer. The accordion
 * already answers "How should the finished product be stored?" at length; a
 * second full sentence would be the same fact in the same register twice. A
 * terse value next to "Carton Dimensions" is a different reading and adds the
 * one clause the spec row can carry without repeating the paragraph.
 */
function sinofresh_formula_storage_line() {
	return 'Cool, dry place out of direct sunlight; keep the container closed after opening.';
}

/**
 * The four sampling steps — the single source of this copy.
 *
 * Three readers already share this array: the band below ([sf_formula_sampling]),
 * the HowTo JSON-LD in wp_head, and — from batch H4 — the sampling summary
 * inside the inquiry modal. The modal must read this function rather than
 * repeat the strings: the same four steps appear twice on one page's worth of
 * UI, and two hardcoded copies drift the first time a step is reworded.
 *
 * Step 4 deliberately drops the "(typically 3-7 working days)" parenthetical
 * the brief carried: the closing line under the band states the timeline, and
 * the same number twice inside one band is the C1 defect this batch exists to
 * avoid. The HowTo schema carries it as totalTime.
 */
function sinofresh_sampling_steps() {
	return array(
		array(
			'title' => 'Submit Inquiry',
			'text'  => 'Tell us your target formula, flavor, and packaging ideas.',
		),
		array(
			'title' => 'Confirm Details',
			'text'  => "We'll provide a sample spec sheet and a proforma invoice for the sample fee.",
		),
		array(
			'title' => 'Sampling & Quality Check',
			'text'  => 'Our lab produces your sample and runs a full quality check.',
		),
		array(
			'title' => 'Ship & Evaluate',
			'text'  => 'We ship the sample to you. You evaluate it and send us your feedback.',
		),
	);
}

/**
 * [sf_formula_sampling] — "How Sampling Works" on a formula detail page.
 *
 * Static copy, so unlike every other band on this page it cannot collapse:
 * the four steps are the same for all 21 records, and the page is the same
 * without it. It still emits its own <section> from here rather than living
 * in the template, for the reason the whole page is built this way — the
 * template is a static block file, and a band whose geometry style.css owns
 * (four columns, the 44px marker, the stack under 769px) belongs with the
 * other band renderers, not split across two files.
 *
 * The marker is a filled primary-green circle with the numeral in card-white.
 * Not brand-green: #5AB735 carries white text at 2.7:1, which fails AA at
 * this size (the note at style.css 1892 records the same measurement), while
 * the Forest token clears it comfortably.
 *
 * Background is card-white like the bands above it — the same continuous
 * reading surface, each band separated by its own H2. The bg-light band
 * begins after this one, at the related-formulas grid.
 */
function sinofresh_formula_sampling() {
	if (!is_singular('sf_formula')) {
		return '';
	}
	$items = '';
	$n     = 0;
	foreach (sinofresh_sampling_steps() as $step) {
		$n++;
		$items .= '<li class="sf-sampling__step">'
			. '<span class="sf-sampling__num">' . (int) $n . '</span>'
			. '<h3 class="sf-sampling__step-title">' . esc_html($step['title']) . '</h3>'
			. '<p class="sf-sampling__desc">' . esc_html($step['text']) . '</p>'
			. '</li>';
	}
	if ($items === '') {
		return '';
	}
	return '<section class="sf-sampling"><div class="sf-sampling__inner">'
		. '<h2 class="sf-sampling__title">' . esc_html('How Sampling Works') . '</h2>'
		. '<ol class="sf-sampling__steps">' . $items . '</ol>'
		. '<p class="sf-sampling__note">' . esc_html('Typically 3-7 working days.') . '</p>'
		. '</div></section>';
}
add_shortcode('sf_formula_sampling', 'sinofresh_formula_sampling');

/* --------------------------------------------------------------------------
 * Batch H4 — the inquiry path on a formula detail page.
 *
 * A detail page carries NO form. The #inquiry-form anchor lives on the front
 * page, the contact page and the eight dosage pages, each of which embeds
 * Gravity Forms form 2 ("Get a Quote", twelve fields); the detail page's only
 * id is "gallery". Before this batch the ways off a detail page were the two
 * hero buttons — "Reference this formula" (copies the name, formulas.js) and
 * "Build Custom Formula" (/contact/#quote) — plus the float stack's mailto.
 * (Batch H7b later replaced the first of the two: it opens the dialog below
 * instead of copying a name nothing consumed.)
 * This batch adds the low-friction path: a capsule at the top of the existing
 * float stack, revealed once the visitor has reached the parameter band, and
 * a dialog holding a five-field form that posts to the endpoint below.
 *
 * Four decisions (user, 2026-09-22) shape it. All four exist because batch
 * H2b2 deleted the configurator:
 *
 *   1. "Your Selection" is the record being read, not a basket. Nothing called
 *      SFBasket.add() any more — its only caller was configurator.js (batch
 *      H7f has since deleted that API and its UI outright) — and a
 *      detail page has no control to tick, so the dialog renders this
 *      record's own Flavor / Piece Weight / Pack Size / Suitable For /
 *      Life Stage / Quantity & Pricing from the SAME meta the parameter band
 *      reads. One source, two renderings; no second source to drift.
 *      ⚠️ Measured at gate time on the 42 detail pages: Flavor, Suitable For,
 *      Life Stage and the tiers are filled on 0 of them, so the block shows
 *      one row (Piece Weight) today and two on the 20 records that also carry
 *      Pack Size. Same "renderer first, data later" state as the parameter
 *      band (H2a) and the content band (H3), and it fills in without a
 *      deploy.
 *   2. The capsule is the FIRST child of .sf-float-stack. The stack is
 *      bottom-anchored (style.css 3913), so its first child is the top one
 *      and the three buttons already there do not move — the geometry H2b1
 *      measured (100 / 24 / 268 / 16) and H4e re-measured stays put.
 *   3. Mobile keeps the capsule instead of becoming a full-width bottom bar:
 *      that bar would have to be reconciled with the stack, the banner offset
 *      (268px) and the iOS safe area — four more readings — for pages that
 *      already carry a hero CTA on phones.
 *   4. Delivery is one plain-text mail to the address in the sf_contact_email
 *      option. Not a literal (H4e found three hardcoded copies and registered
 *      them as H6 item 10), and not a Gravity Forms entry, which would need a
 *      new form and therefore a database change.
 *
 * Where the markup lives: the dialog is emitted from wp_footer, not from a
 * template, so single-sf_formula.html stays a static block file and the
 * markup that depends on record data sits with the other renderers. What the
 * template does carry is [sf_inquiry_button] inside the float stack — a
 * shortcode rather than a block because a block template cannot be gated by
 * a value (placeholders are substituted after the block tree is decided,
 * whereas do_shortcode runs over the finished output). The shortcode returns
 * '' off a detail page, so although parts/footer.html is on all 75 pages the
 * substantive change lands on exactly the 42 the brief names.
 * ------------------------------------------------------------------------ */

/**
 * The rows the inquiry dialog's "Your Selection" panel shows.
 *
 * Reads the same meta the parameter band reads, in the brief's order, and
 * returns plain text values: the band prints chips and a pricing table, but
 * the dialog is a summary read at a glance, so a chip list becomes one
 * comma-joined line and the tier rows become one line of "qty — price"
 * pairs. Empty means absent — a record that proves nothing renders nothing,
 * the same rule sinofresh_formula_params() follows.
 *
 * @param int $post_id Formula post id.
 * @return array Label => plain text value, in print order.
 */
function sinofresh_inquiry_selection_rows($post_id) {
	$post_id = (int) $post_id;
	if ($post_id <= 0) {
		return array();
	}
	$rows  = array();
	$parts = sinofresh_formula_specs_parts(trim((string) get_post_meta($post_id, 'sf_formula_specs', true)));

	$flavors = sf_json_array(get_post_meta($post_id, 'sf_formula_flavors', true));
	if ($flavors) {
		$rows['Flavor'] = implode(', ', $flavors);
	}
	if (trim((string) $parts['unit']) !== '') {
		$rows['Piece Weight'] = trim((string) $parts['unit']);
	}
	if (trim((string) $parts['pack']) !== '') {
		$rows['Pack Size'] = trim((string) $parts['pack']);
	}
	$species = sf_json_array(get_post_meta($post_id, 'sf_formula_species', true));
	if ($species) {
		$rows['Suitable For'] = implode(', ', $species);
	}
	$lifestage = trim((string) get_post_meta($post_id, 'sf_formula_lifestage', true));
	if ($lifestage !== '') {
		$rows['Life Stage'] = $lifestage;
	}

	$tiers = array();
	foreach (sf_json_rows(get_post_meta($post_id, 'sf_formula_price_tiers', true)) as $tier) {
		if (!is_array($tier)) {
			continue;
		}
		/* H7i: the row is {min, max, price}; a legacy qty reads as min. The
		   row is written the way the ladder's own card prints it, so the spec
		   sheet and the price list cannot disagree about one tier. */
		$min   = trim((string) (isset($tier['min']) ? $tier['min'] : (isset($tier['qty']) ? $tier['qty'] : '')));
		$max   = trim((string) (isset($tier['max']) ? $tier['max'] : ''));
		$price = trim((string) (isset($tier['price']) ? $tier['price'] : ''));
		$range = sf_tier_range_label($min, $max);
		if ($range !== '' && $price !== '') {
			$tiers[] = $range . ' — ' . sf_tier_price_label($price);
		} elseif ($range !== '') {
			$tiers[] = $range;
		} elseif ($price !== '') {
			$tiers[] = sf_tier_price_label($price);
		}
	}
	if ($tiers) {
		$rows['Quantity & Pricing'] = implode(' · ', $tiers);
	}

	return $rows;
}

/**
 * [sf_inquiry_button] — the capsule at the top of the float stack.
 *
 * Emits nothing off a formula detail page. The element is an <a>, not a
 * <button>: the click is upgraded to "open the dialog" by inquiry.js, but the
 * href is the same destination the hero's "Build Custom Formula" uses, so the
 * markup degrades to a working link if the script never arrives (in which
 * case the reveal never happens either, and the page falls back to the two
 * hero CTAs it has always had).
 *
 * `hidden` is set here rather than in CSS so that the no-JS state is
 * "not shown" without a stylesheet having to guess; inquiry.js removes the
 * attribute once the parameter band is reached.
 */
function sinofresh_inquiry_button() {
	if (!is_singular('sf_formula')) {
		return '';
	}
	return '<a class="sf-float-btn sf-float-btn--inquiry" href="/contact/#quote" data-sf-inquiry-open hidden>'
		. '<span class="sf-float-btn__icon" aria-hidden="true">'
		. '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" focusable="false"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5Z"/></svg>'
		. '</span>'
		. '<span class="sf-float-btn__label">Send Inquiry</span></a>';
}
add_shortcode('sf_inquiry_button', 'sinofresh_inquiry_button');

/**
 * The inquiry dialog, emitted on a formula detail page.
 *
 * Hooked to wp_footer at priority 20 so it lands after the float stack that
 * the capsule sits in — the two are the same widget, and reading the markup
 * in source order should read the trigger before the thing it triggers.
 *
 * The form requests nothing it cannot prove: the four anti-spam measures are
 * a honeypot input, a timestamp the script stamps when the dialog opens (a
 * submission inside three seconds is a machine), server-side re-derivation of
 * the selection panel from the post id rather than trusting the posted text,
 * and the endpoint's own validation of every field.
 *
 * The dialog repeats the four sampling steps without restating them: the
 * titles come from sinofresh_sampling_steps(), the same array the visible
 * band and the HowTo schema read, so rewording a step moves all three. Only
 * the titles are printed — the band below already carries the sentences, and
 * the dialog is the three-second read.
 */
function sinofresh_inquiry_modal() {
	if (!is_singular('sf_formula')) {
		return;
	}
	$post_id = (int) get_queried_object_id();
	if ($post_id <= 0) {
		return;
	}
	$selection = sinofresh_inquiry_selection_rows($post_id);

	$panel = '';
	if ($selection) {
		$panel = '<div class="sf-inquiry-modal__card">'
			. '<h3 class="sf-inquiry-modal__sub" id="sf-inquiry-selection">Your Selection</h3>'
			. '<dl class="sf-inquiry-modal__rows">';
		foreach ($selection as $label => $value) {
			$panel .= '<dt class="sf-inquiry-modal__term">' . esc_html($label) . '</dt>'
				. '<dd class="sf-inquiry-modal__value">' . esc_html($value) . '</dd>';
		}
		$panel .= '</dl></div>';
	}

	$steps = '';
	$n     = 0;
	foreach (sinofresh_sampling_steps() as $step) {
		$n++;
		$steps .= '<li class="sf-inquiry-modal__step">'
			. '<span class="sf-inquiry-modal__num" aria-hidden="true">' . (int) $n . '</span>'
			. '<span class="sf-inquiry-modal__step-title">' . esc_html($step['title']) . '</span>'
			. '</li>';
	}
	if ($steps !== '') {
		$steps = '<div class="sf-inquiry-modal__card">'
			. '<h3 class="sf-inquiry-modal__sub" id="sf-inquiry-sampling">How Sampling Works</h3>'
			. '<ol class="sf-inquiry-modal__steps">' . $steps . '</ol>'
			. '<p class="sf-inquiry-modal__note">Typically 3-7 working days.</p>'
			. '</div>';
	}

	$form = '<form class="sf-inquiry-form" novalidate>'
		. '<input type="hidden" name="formula" value="' . (int) $post_id . '">'
		. '<input type="hidden" name="ts" value="0">'
		/* H7d: the configurator writes the visitor's own selection here as JSON,
		   and leaves it empty when nothing was ticked — in which case the
		   endpoint falls back to the record's own values, exactly as this dialog
		   behaved before the batch. The panel above is updated to match by
		   config.js, so the visitor reads the same list the sales desk gets. */
		. '<input type="hidden" name="config" value="">'
		/* Honeypot: off-canvas rather than type="hidden" — a field a human
		   cannot see but a form-filler still fills. aria-hidden plus
		   tabindex="-1" keeps it out of the accessibility tree and the tab
		   order, so it is invisible to assistive tech too. */
		. '<div class="sf-inquiry-form__trap" aria-hidden="true">'
		. '<label for="sf-inquiry-website">Website</label>'
		. '<input type="text" id="sf-inquiry-website" name="website" tabindex="-1" autocomplete="off">'
		. '</div>'
		. '<div class="sf-inquiry-form__grid">'
		. '<p class="sf-inquiry-form__field">'
		. '<label for="sf-inquiry-name">Name <span class="sf-inquiry-form__req" aria-hidden="true">*</span></label>'
		. '<input type="text" id="sf-inquiry-name" name="name" required autocomplete="name">'
		. '</p>'
		. '<p class="sf-inquiry-form__field">'
		. '<label for="sf-inquiry-email">Email <span class="sf-inquiry-form__req" aria-hidden="true">*</span></label>'
		. '<input type="email" id="sf-inquiry-email" name="email" required autocomplete="email">'
		. '</p>'
		. '<p class="sf-inquiry-form__field">'
		. '<label for="sf-inquiry-company">Company</label>'
		. '<input type="text" id="sf-inquiry-company" name="company" autocomplete="organization">'
		. '</p>'
		. '<p class="sf-inquiry-form__field">'
		. '<label for="sf-inquiry-country">Country</label>'
		. '<input type="text" id="sf-inquiry-country" name="country" autocomplete="country-name">'
		. '</p>'
		. '<p class="sf-inquiry-form__field sf-inquiry-form__field--wide">'
		. '<label for="sf-inquiry-message">Message</label>'
		. '<textarea id="sf-inquiry-message" name="message" rows="3"></textarea>'
		. '</p>'
		. '</div>'
		. '<button type="submit" class="sf-inquiry-form__submit">Submit Inquiry</button>'
		. '<p class="sf-inquiry-form__status" role="status" aria-live="polite"></p>'
		. '</form>';

	$title = get_the_title($post_id);

	/* The outer element is the backdrop and the centring box, the panel inside
	   it is the dialog — the shape section 50 gave the certificate dialog, so
	   one backdrop definition serves all three components. role="dialog" sits
	   on the panel rather than the backdrop: the backdrop is not part of the
	   dialog, and a click on it closes rather than interacts. */
	echo "\n" . '<div class="sf-inquiry-modal" hidden>'
		. '<div class="sf-inquiry-modal__panel" role="dialog" aria-modal="true" aria-labelledby="sf-inquiry-title">'
		. '<div class="sf-inquiry-modal__head">'
		. '<h2 class="sf-inquiry-modal__title" id="sf-inquiry-title">Send Inquiry</h2>'
		. '<p class="sf-inquiry-modal__lead">'
		. esc_html($title !== '' ? $title : 'SINO FRESH')
		. '</p>'
		. '<button type="button" class="sf-inquiry-modal__close" aria-label="Close inquiry form">&times;</button>'
		. '</div>'
		. '<div class="sf-inquiry-modal__body">'
		. $panel
		. $steps
		. $form
		. '<div class="sf-inquiry-modal__success" hidden>'
		. '<p class="sf-inquiry-modal__success-title">Thank you — your inquiry is on its way.</p>'
		. '<p class="sf-inquiry-modal__success-note">A member of our sales team will reply within 24 hours.</p>'
		. '</div>'
		. '</div>'
		. '</div>'
		. '</div>' . "\n";
}
/* Priority 5, not 20. wp_print_footer_scripts runs on wp_footer at 20, so a
   dialog echoed at 20 lands *after* its own script tag — and a classic footer
   script executes at parse time, so inquiry.js found no dialog, returned at
   its first guard, and the capsule never appeared. Silent: no console error,
   valid markup, and the byte gate cannot see the ordering at all. The first
   browser pass did. The script is order-independent now as well, but the
   markup still belongs before the scripts that read it. */
add_action('wp_footer', 'sinofresh_inquiry_modal', 5);

/**
 * POST /sinofresh/v1/inquiry — the dialog's endpoint.
 *
 * Public by design, like /article-feedback: the visitor is not logged in and
 * the only thing it can do is send one mail to the site's own address. There
 * is no nonce — a cached page would serve a stale one and reject a legitimate
 * submission — so the four server-side checks below are what stands between
 * the endpoint and a spammer, and every one of them is enforced here rather
 * than in the script.
 *
 * The mail is plain text and single-recipient: the address is the
 * sf_contact_email option, so the site owner changes it in Site Settings and
 * this path follows. The customer is not copied on it — an auto-reply is a
 * separate decision and not part of this batch.
 */
add_action('rest_api_init', function () {
	register_rest_route('sinofresh/v1', '/inquiry', array(
		'methods'             => 'POST',
		'permission_callback' => '__return_true',
		'callback'            => function (WP_REST_Request $req) {
			/* 1. Honeypot. A field a human never sees; anything in it is a
			   form-filler. Rejected loudly rather than answered with a fake
			   success, so the browser pass can prove this check runs. */
			if (trim((string) $req->get_param('website')) !== '') {
				return new WP_Error('sf_inquiry_spam', 'Submission rejected.', array('status' => 400));
			}

			/* 2. Time on form. The script stamps the moment the dialog opened;
			   a machine posts back in well under three seconds. A timestamp in
			   the future is a forged one and counts as too fast. */
			$stamp_ms = (float) $req->get_param('ts');
			$now_ms   = (int) round(microtime(true) * 1000);
			if ($stamp_ms <= 0 || ($now_ms - $stamp_ms) < 3000 || $stamp_ms > $now_ms + 5000) {
				return new WP_Error('sf_inquiry_fast', 'Please take a moment to complete the form.', array('status' => 400));
			}

			/* 3. Fields. */
			$name    = trim((string) sanitize_text_field((string) $req->get_param('name')));
			$email   = trim((string) sanitize_email((string) $req->get_param('email')));
			$company = trim((string) sanitize_text_field((string) $req->get_param('company')));
			$country = trim((string) sanitize_text_field((string) $req->get_param('country')));
			$message = trim((string) sanitize_textarea_field((string) $req->get_param('message')));
			$source  = esc_url_raw((string) $req->get_param('source'));

			if ($name === '') {
				return new WP_Error('sf_inquiry_name', 'Please tell us your name.', array('status' => 400));
			}
			if ($email === '' || !is_email($email)) {
				return new WP_Error('sf_inquiry_email', 'Please enter a valid email address.', array('status' => 400));
			}

			/* 4. The selection panel is rebuilt from the post id, and H7d keeps
			   that rule in the only form that survives the visitor making a
			   choice: the request says WHICH options, the server says what they
			   are CALLED. A posted value that is not one of this record's own
			   option values is dropped, so a hand-crafted request can choose
			   among the options the page already offered and add nothing. An
			   empty selection falls back to the record's own values, which is
			   the behaviour this endpoint had before the batch. */
			$post_id = absint($req->get_param('formula'));
			$product = '';
			$rows    = array();
			$chosen  = array();
			if ($post_id > 0 && 'sf_formula' === get_post_type($post_id) && 'publish' === get_post_status($post_id)) {
				$product = (string) get_the_title($post_id);
				$posted  = $req->get_param('config');
				if (is_string($posted) && $posted !== '') {
					$decoded = json_decode($posted, true);
					$posted  = is_array($decoded) ? $decoded : array();
				}
				$chosen = sinofresh_formula_config_rows($post_id, is_array($posted) ? $posted : array());
				$rows   = $chosen ? $chosen : sinofresh_inquiry_selection_rows($post_id);
			} else {
				$post_id = 0;
			}

			$to = trim((string) get_option('sf_contact_email', ''));
			if ($to === '' || !is_email($to)) {
				$to = 'sales@zxpet.com';
			}

			$lines = array('New inquiry from the website.', '');
			if ($product !== '') {
				$lines[] = 'Formula: ' . $product;
			}
			if ($rows) {
				$lines[] = '';
				/* Named for the sales desk: a line the customer picked and a
				   line the record already said are different kinds of evidence,
				   and the reply has to differ (one is a request, the other a
				   restatement of the specification). */
				$lines[] = $chosen ? 'Selection (chosen by the customer):' : 'Specification:';
				foreach ($rows as $label => $value) {
					$lines[] = '  ' . $label . ': ' . $value;
				}
			}
			$lines[] = '';
			$lines[] = 'Contact:';
			$lines[] = '  Name: ' . $name;
			$lines[] = '  Email: ' . $email;
			if ($company !== '') {
				$lines[] = '  Company: ' . $company;
			}
			if ($country !== '') {
				$lines[] = '  Country: ' . $country;
			}
			if ($message !== '') {
				$lines[] = '';
				$lines[] = 'Message:';
				$lines[] = $message;
			}
			if ($source !== '') {
				$lines[] = '';
				$lines[] = 'Source: ' . $source;
			}

			$subject = '[Inquiry] '
				. ($product !== '' ? $product : 'Website') . ' — ' . $name;

			$sent = wp_mail($to, $subject, implode("\n", $lines));
			if (!$sent) {
				/* Left in the log rather than swallowed: a failed send is the
				   one outcome where a lead is lost, and the visitor is told to
				   try again instead of being shown a false confirmation. */
				error_log('[sf-inquiry] wp_mail() returned false for ' . $to . ' (formula ' . $post_id . ')');
				return new WP_Error('sf_inquiry_mail', 'We could not send that just now. Please try again.', array('status' => 500));
			}

			return array('ok' => true);
		},
	));
});

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

	/* Batch C: the formula detail page's accordion is generated by the
	   [sf_formula_faq] shortcode inside a core/html block, so the template
	   file holds no <details> pair to find — and its {{TITLE}} and
	   {{FORM_CRUMB}} tokens would be read as literal text. The pairs therefore
	   come from the same function the visible block renders from, which is the
	   only arrangement in which the page and the schema cannot disagree. */
	if (is_singular('sf_formula')) {
		$entities = array();
		foreach (sinofresh_formula_faq_data((int) get_queried_object_id()) as $pair) {
			$question = trim((string) $pair['q']);
			$answer   = trim((string) $pair['a']);
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
		if (count($entities) >= 2) {
			$schema = array(
				'@context'   => 'https://schema.org',
				'@type'      => 'FAQPage',
				'mainEntity' => $entities,
			);
			echo "\n" . '<script type="application/ld+json">'
				. wp_json_encode($schema, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE)
				. "</script>\n";
		}

		/* Batch H3: the sampling process as HowTo. Emitted here rather than
		   from a second wp_head callback so it shares this one's stand-down
		   for an SEO plugin that already emits FAQPage/HowTo, and so the two
		   schema blocks on a formula page keep a fixed order. The steps come
		   from sinofresh_sampling_steps() — the same array the visible band
		   renders from, so the page and the structured data cannot drift. */
		$howto_steps = array();
		foreach (sinofresh_sampling_steps() as $i => $step) {
			$howto_steps[] = array(
				'@type'    => 'HowToStep',
				'position' => (int) $i + 1,
				'name'     => $step['title'],
				'text'     => $step['text'],
			);
		}
		if (count($howto_steps) >= 2) {
			$howto = array(
				'@context'  => 'https://schema.org',
				'@type'     => 'HowTo',
				'name'      => 'How Sampling Works',
				'totalTime' => 'P3D',
				'step'      => $howto_steps,
			);
			echo "\n" . '<script type="application/ld+json">'
				. wp_json_encode($howto, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE)
				. "</script>\n";
		}
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
 *   {{FORM_SLUG}}        formula detail pages only — the bare term slug
 *                        (e.g. "soft-chews") for data-form attributes, '' when
 *                        the formula carries no term
 *   {{FORMULA_USE}}      formula detail pages only — the current formula's
 *                        sf_formula_use term name, written VERBATIM (wp_terms
 *                        stores "Skin &amp; coat"; esc_html here would
 *                        double-escape, the same pit 2B Stage1 hit)
 *   {{FORMULA_META}}     formula detail pages only — the hero's one-line meta
 *                        summary, composed here rather than in the template so
 *                        a missing piece can never leave a dangling "· ":
 *                        "<form> · MOQ <value> · Lead time <value>", where
 *                        the two values come from the form's /products/<form>/
 *                        .sf-facts-mini row (sinofresh_formula_spec_cell).
 *                        Falls back to the form label alone, or to ''.
 *   {{FORMULA_INTRO}}    formula detail pages only - the parameters column's
 *                        intro paragraph, already wrapped in its own <p>
 *                        (escaped
 *                        HTML, not escaped text), resolved by
 *                        sinofresh_formula_intro(); '' when it cannot be
 *                        composed, which writes nothing at all
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
		/* Core composes an archive title as "<prefix> <title>" and exposes the
		   prefix to a filter — which is exactly how the query-title block
		   implements showPrefix:false. Suppressing it at the source is the
		   only route that works on /zh/: there the prefix is a gettext
		   string, so TranslatePress hands it back wrapped in its own
		   #!trpst#trp-gettext … #!trpen# markers, which puts "归档：" behind a
		   marker instead of at the start of the string — and zh_CN writes the
		   separator as a full-width colon. Both defeat a post-hoc strip, which
		   is why the breadcrumb kept its "归档： " prefix on every /zh/ archive
		   (the H1 was always clean because the block filters the prefix). */
		add_filter('get_the_archive_title_prefix', '__return_empty_string', 1);
		$archive_title = trim(wp_strip_all_tags(get_the_archive_title()));
		remove_filter('get_the_archive_title_prefix', '__return_empty_string', 1);
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
	$form_slug  = '';
	$formula_use = '';
	$formula_meta = '';
	$formula_intro = '';
	if (is_singular('sf_formula')) {
		$formula_id = (int) get_queried_object_id();
		$form_terms = wp_get_post_terms($formula_id, 'sf_formula_form');
		if (!is_wp_error($form_terms) && $form_terms) {
			$form_crumb = sinofresh_formula_label($form_terms[0]->slug, $form_terms[0]->name);
			$form_href  = '/products/' . $form_terms[0]->slug . '/';
			$form_slug  = (string) $form_terms[0]->slug;
		}
		$use_terms = wp_get_post_terms($formula_id, 'sf_formula_use');
		if (!is_wp_error($use_terms) && $use_terms) {
			$formula_use = (string) $use_terms[0]->name;
		}
		/* The hero meta line: form label plus the form's own MOQ / lead time
		   rows. Composed as a list so an absent row shortens the line instead
		   of printing "MOQ " with nothing after it. */
		$meta_bits = array();
		if ($form_crumb !== '') {
			$meta_bits[] = $form_crumb;
		}
		if ($form_slug !== '') {
			$moq  = sinofresh_formula_spec_cell($form_slug, 'MOQ');
			$lead = sinofresh_formula_spec_cell($form_slug, 'Lead time');
			if ($moq !== '') {
				$meta_bits[] = 'MOQ ' . $moq;
			}
			if ($lead !== '') {
				$meta_bits[] = 'Lead time ' . $lead;
			}
		}
		$formula_meta = implode(' · ', $meta_bits);
		/* Batch G: the media column's intro. Wrapped in its <p> here,
		   which is why the map entry below is escaped HTML and not
		   escaped text like {{FORMULA_META}}. Empty stays empty: no
		   empty <p> is written. Batch H2a moved the class to the
		   second-revision namespace along with the band it sits in —
		   this string is the only place the class lives, the template
		   cannot carry it, so renaming the band means renaming it here
		   too or the paragraph silently loses its styling. */
		$intro = sinofresh_formula_intro($formula_id);
		if ($intro !== '') {
			$formula_intro = '<p class="sf-fdetail2__intro">' . esc_html($intro) . '</p>';
		}
	}
	$map = array(
		'{{TITLE}}'           => esc_html($title),
		'{{ARCHIVE_TITLE}}'   => esc_html($archive_title),
		'{{MID_HREF}}'        => $case ? '/category/case-studies/' : '/blog/',
		'{{MID_CRUMB}}'       => $case ? 'Case Studies' : 'Blog',
		'{{FORM_CRUMB}}'      => esc_html($form_crumb),
		'{{FORM_HREF}}'       => esc_url($form_href),
		'{{FORM_SLUG}}'       => esc_attr($form_slug),
		/* Verbatim, not esc_html: see the docblock and the 2B Stage1 pit. */
		'{{FORMULA_USE}}'     => $formula_use,
		'{{FORMULA_META}}'    => esc_html($formula_meta),
		'{{FORMULA_INTRO}}'   => $formula_intro,
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
	} elseif (is_post_type_archive('sf_formula')) {
		/* 2C Step2: the archive has its own recipe now. Naming it first pins
		   the JSON-LD source to the file that actually renders. Both
		   templates carry the same two-level crumb, so the emitted
		   BreadcrumbList is byte-identical — this only keeps the schema
		   generator in step with the render path if one file is edited. */
		$candidates = array('archive-sf_formula', 'archive');
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
 *
 * Batch H7e added the last two keys. They are not contact details and they do
 * not appear in the top bar or the footer: they are the two factory facts the
 * specification sheet prints on every product page, which were constants in
 * sinofresh_formula_specs_table() until this batch. They live here anyway
 * because this array is the single source of a Site Settings default — the
 * subpage that edits them and the reader that prints them both fall back to
 * the entry below, so the two cannot drift apart.
 */
function sf_site_settings_defaults() {
	return array(
		'sf_contact_email'    => 'sales@zxpet.com',
		'sf_working_hours'    => 'Mon–Fri · 9:00–18:00 GMT+8',
		'sf_contact_phone'    => '+86 539 866 9539',
		'sf_contact_address'  => 'No. 22 Zhongshan Road B3, Yihe New District, Linyi, Shandong, China',
		'sf_contact_whatsapp' => '+86 133 8539 7805',
		'sf_copyright_company' => 'Shandong SINO FRESH Pet Food Co., Ltd.',
		'sf_copyright_suffix'  => 'All rights reserved.',
		/* Batch H7e. The values are the constants they replaced, character for
		   character — including the comma and the space around the slash. */
		'sf_factory_origin'   => 'Linyi, Shandong, China',
		'sf_factory_oem'      => 'Available',
		/* Batch H7j. Not a contact detail and not printed on any page: the
		   slug of the mark the main menu draws on the current item. It lives
		   here for the same reason the two above do — this array is the one
		   place a Site Settings default is written, so the radio group that
		   edits it, the validator that guards it and the reader that turns it
		   into a header class cannot drift apart. */
		'sf_nav_active_style' => 'underline',
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
			return ($v !== '') ? $v : 'sales@zxpet.com';
		},
	));
	/* Batch H7j. The one value on this page that is neither contact nor copy:
	   the mark the main menu draws on the current item. The six slugs are
	   sf_nav_active_styles()' keys — anything else falls back to the default,
	   so a stale option can never emit a header class no rule defines. */
	register_setting('sf_site_settings', 'sf_nav_active_style', array(
		'type'              => 'string',
		'sanitize_callback' => function ($v) use ($d) {
			$all = sf_nav_active_styles();
			$v   = sanitize_key($v);
			return isset($all[$v]) ? $v : $d['sf_nav_active_style'];
		},
	));
	register_setting('sf_site_settings', 'sf_certifications', array(
		'type'              => 'array',
		'sanitize_callback' => function ($v) {
			$out = array();
			/* Batch H1: dynamic rows instead of eight fixed slots. Empty
			   rows collapse out; order is preserved for the badges, the
			   line token, the detail row and the schema. */
			foreach ((array) $v as $row) {
				$row = is_array($row) ? $row : array();
				$name = isset($row['name']) ? sanitize_text_field($row['name']) : '';
				if ($name === '') {
					continue;
				}
				$out[] = array(
					'name'   => $name,
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
				<?php foreach ($certs as $i => $c) :
					$c = is_array($c) ? $c : array('name' => '', 'url' => '', 'active' => false); ?>
				<tr>
					<td><?php echo (int) ($i + 1); ?></td>
					<td><input name="sf_certifications[<?php echo (int) $i; ?>][name]" type="text" class="regular-text" value="<?php echo esc_attr($c['name']); ?>"></td>
					<td><input name="sf_certifications[<?php echo (int) $i; ?>][url]" type="text" class="regular-text" value="<?php echo esc_attr($c['url']); ?>"></td>
					<td><input name="sf_certifications[<?php echo (int) $i; ?>][active]" type="checkbox" value="1" <?php checked(!empty($c['active'])); ?>></td>
					<td><button type="button" class="button-link sf-certs-del">Remove</button></td>
				</tr>
				<?php endforeach; ?>
				</tbody>
			</table>
			<p><button type="button" class="button" id="sf-certs-add">+ Add row</button></p>
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
			<h2 class="title">Appearance</h2>
			<p>Navigation — how the main menu marks the page you are on. The mark is server-rendered, so it is in the page's own HTML before any script runs, and the link also carries aria-current for screen readers.</p>
			<table class="form-table" role="presentation">
				<tr>
					<th scope="row">Current item mark</th>
					<td>
					<?php $nav_style = sf_nav_active_style(); ?>
					<fieldset>
						<legend class="screen-reader-text">Navigation current-item mark</legend>
						<?php foreach (sf_nav_active_styles() as $nav_slug => $nav_label) : ?>
						<label style="display:block;margin:0 0 6px">
							<input type="radio" name="sf_nav_active_style" value="<?php echo esc_attr($nav_slug); ?>" <?php checked($nav_style, $nav_slug); ?>>
							<?php echo esc_html($nav_label); ?>
						</label>
						<?php endforeach; ?>
					</fieldset>
					<p class="description">Drawn on the current page's own item in the top bar, in all four states (normal, hover, current, current + hover). Pages the menu does not contain — the legal pages, the FAQ, the feedback form — get no mark.</p>
					</td>
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
		'{{sf-certifications-line}}' => esc_html(sf_certifications_line()),
	);
	$block_content = str_replace(array_keys($map), array_values($map), $block_content);
	if (strpos($block_content, '{{sf-certifications}}') !== false) {
		$block_content = str_replace('{{sf-certifications}}', sf_render_cert_badges(), $block_content);
	}
	return $block_content;
}, 20, 2);

/* === Navigation: which item is current, and the six ways to mark it ========
   Batch H7j (task 20). The main menu — wp:navigation {"ref":16} in
   parts/header.html — carried NO current-state markup at all: measured across
   all 75 captured paths, not one of its sixteen links carried
   current-menu-item, current_page_item or aria-current, on any page. The
   reason is the block. A navigation block whose `ref` points at a wp_navigation
   post renders that post's own core/navigation-link blocks directly, so
   wp_nav_menu()'s _wp_menu_item_classes_by_context() never runs and nothing
   ever compares a link's URL with the request.

   So the comparison is made here, and what it emits is the class pair the CSS
   in section 63 keys on: sf-nav__link on every link, sf-nav__link.is-active on
   the current one, and the variant class sf-header--nav-<slug> on the header.

   WHICH item is current — the site's own hierarchy decides, not the URL alone.
   The breadcrumb on /formulas/joint-support-soft-chews/ reads
   Home / Products / Soft Chews / Joint Support Soft Chews, so this site places
   the twenty-two formula pages under Products, and the nine links inside the
   Products dropdown (All Formulas plus the eight dosage forms) belong to the
   Products item. The current item is therefore the one TOP-LEVEL item whose
   subtree contains the page: /products/soft-chews/ marks Products, and so does
   /formulas/joint-support-soft-chews/. Measured over the 75 captured paths
   that marks exactly one item on 67 of them, and none on the eight the menu
   genuinely does not contain (/, /privacy-policy/, /terms/, /cookie-policy/,
   /faq/, /feedback/, /cooperation/, /zh/).

   A link INSIDE the dropdown is never marked. The dropdown is a light popup
   (#F3F6F4) and all six marks are drawn white or brand-green for the dark
   Forest bar — the white label alone would be invisible there. So the child
   that legitimately matches the request is pruned back out of the submenu's
   own markup, and that same match is what lights the Products item up.

   The language prefix is not hardcoded anywhere. TranslatePress filters
   home_url() to prepend the active language, so the prefix to strip is
   whatever home_url('/')'s path has beyond "/": "/zh/" under the Chinese tree,
   "" under the English one. The urls being compared are the blocks' own `url`
   attributes, which a probe against the live menu showed are untranslated
   paths (/products/, /formulas/), never absolute URLs.
   ------------------------------------------------------------------------- */

/** The six marks, slug => label. ONE source: the Site Settings radios, the
    validator that guards the option and the header class are all built from
    this array, so a seventh mark is a one-line change here plus its rules. */
function sf_nav_active_styles() {
	return array(
		'underline'  => 'Underline',
		'bg'         => 'Translucent block',
		'thick-line' => 'Thick bottom line (4px)',
		'color'      => 'Brand-green text',
		'left-line'  => 'Left rule',
		'pill'       => 'Green pill',
	);
}

/** The mark the header draws. An option holding anything else — a stale slug,
    a hand-edited value — falls back to the shipped default rather than
    emitting a class no rule defines. */
function sf_nav_active_style() {
	$d   = sf_site_settings_defaults();
	$all = sf_nav_active_styles();
	$v   = (string) get_option('sf_nav_active_style', $d['sf_nav_active_style']);
	return isset($all[$v]) ? $v : $d['sf_nav_active_style'];
}

/** The request path with the active language prefix removed, so it can be
    compared with a link's own `url` attribute. Static: it cannot change inside
    a request, and it is read once per navigation link. */
function sf_nav_request_path() {
	static $path = null;
	if (null !== $path) {
		return $path;
	}
	$uri  = isset($_SERVER['REQUEST_URI']) ? (string) wp_unslash($_SERVER['REQUEST_URI']) : '/';
	$path = (string) wp_parse_url($uri, PHP_URL_PATH);
	$home = (string) wp_parse_url(home_url('/'), PHP_URL_PATH);
	if ('' !== $home && '/' !== $home) {
		$home = '/' . trim($home, '/') . '/';
		if (0 === strpos($path, $home)) {
			$path = '/' . ltrim(substr($path, strlen($home)), '/');
		}
	}
	if ('' === $path) {
		$path = '/';
	}
	return $path;
}

/** Does the request path fall under this menu url? Both sides end in "/" (every
    permalink on this site does), so a plain prefix test is already
    segment-safe. */
function sf_nav_path_under($path, $url) {
	$url = '/' . trim((string) $url, '/') . '/';
	return ($path === $url) || (0 === strpos($path, $url));
}

/** Is the request path this menu url exactly? The difference from the test
    above is what aria-current turns on: a link that points AT the page is
    "page", a link whose section merely CONTAINS the page is "true". The
    first version of this used the prefix test for both and announced
    /products/soft-chews/ as the page Products links to, which it is not —
    that link points at /products/. */
function sf_nav_path_is($path, $url) {
	return ($path === '/' . trim((string) $url, '/') . '/');
}

/** Put sf-nav__link on a link, and — when $active — the is-active class and
    aria-current. Only the FIRST anchor of the fragment is touched: for a
    submenu that is the item's own link, and the links inside its dropdown
    (separate blocks, already rendered into this fragment) must not pick up a
    second mark.

    aria-current is "page" when the item's own url IS the request, and "true"
    when the page merely sits inside the item's subtree — the Products item on
    a dosage page. That is the distinction the ARIA spec draws. */
function sf_nav_mark_link($html, $active, $is_page) {
	if (false === strpos($html, 'class="wp-block-navigation-item__content"')) {
		return $html;
	}
	$cls = 'wp-block-navigation-item__content sf-nav__link';
	$att = '';
	if ($active) {
		$cls .= ' is-active';
		$att = ' aria-current="' . ($is_page ? 'page' : 'true') . '"';
	}
	return preg_replace(
		'/class="wp-block-navigation-item__content"/',
		'class="' . $cls . '"' . $att,
		$html,
		1
	);
}

add_filter('render_block', function ($block_content, $block) {
	if (!is_string($block_content) || !isset($block['blockName'])) {
		return $block_content;
	}
	$name = $block['blockName'];
	if ('core/navigation-link' !== $name && 'core/navigation-submenu' !== $name) {
		return $block_content;
	}
	$url = isset($block['attrs']['url']) ? (string) $block['attrs']['url'] : '';
	if ('' === $url || false === strpos($block_content, 'wp-block-navigation-item__content')) {
		return $block_content;
	}
	$path  = sf_nav_request_path();
	$self  = sf_nav_path_under($path, $url);
	$exact = sf_nav_path_is($path, $url);

	if ('core/navigation-link' === $name) {
		return sf_nav_mark_link($block_content, $self, $exact);
	}

	/* The submenu. Everything after its own </a> is the dropdown; a child that
	   matched the request has already marked itself in there, and that mark is
	   both the signal that this item OWNS the current page and the thing that
	   has to come back out. Split on the first </a>, decide on the head, prune
	   the tail. */
	$cut = strpos($block_content, '</a>');
	if (false === $cut) {
		return sf_nav_mark_link($block_content, $self, $exact);
	}
	$head = substr($block_content, 0, $cut + 4);
	$tail = substr($block_content, $cut + 4);
	$owns = (false !== strpos($tail, ' is-active'));
	$head = sf_nav_mark_link($head, $self || $owns, $exact);
	$tail = str_replace(
		array(
			' sf-nav__link is-active" aria-current="page"',
			' sf-nav__link is-active" aria-current="true"',
			' is-active',
		),
		array(' sf-nav__link"', ' sf-nav__link"', ''),
		$tail
	);
	return $head . $tail;
}, 10, 2);

/* The variant class goes on the header element — the core/group that
   parts/header.html marks with className "sf-header". It is applied as a
   string pass over the rendered fragment rather than through
   render_block_data/className on purpose: the layout support hashes a block's
   attributes into its wp-container-* class, so editing the attribute would
   renumber a container class on all 75 pages for a purely presentational
   change. The anchor requires "wp-block-group sf-header" followed by a quote
   or a space, so a sibling block whose className merely STARTS with those
   characters — the CTA row's is sf-header__cta — can never match. */
add_filter('render_block', function ($block_content, $block) {
	if (!is_string($block_content) || !isset($block['blockName'])
		|| 'core/group' !== $block['blockName']
		|| false === strpos($block_content, 'class="wp-block-group sf-header')) {
		return $block_content;
	}
	return preg_replace(
		'/(<[a-z][a-z0-9]* class="wp-block-group sf-header)(?=[ "])/',
		'$1 sf-header--nav-' . sf_nav_active_style(),
		$block_content,
		1
	);
}, 10, 2);

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

/* ---------------------------------------------------------------------------
 * Batch H5 — the readers the schema generators share with the templates.
 *
 * Adding four schema properties could easily have added four more places
 * where the same fact is written down. Each reader below therefore has exactly
 * one source, most of them a source that already existed:
 *
 *   sinofresh_formula_facts_props()  the dosage page's four .sf-facts-mini
 *                                    rows, through sinofresh_formula_spec_cell()
 *                                    (batch F1's row, so it is the row the page
 *                                    itself displays)
 *   sinofresh_formula_audience()     the species: the record's own
 *                                    sf_formula_species first, the dosage page's
 *                                    own <h1> sentence second
 *   sinofresh_formula_related()      the siblings the visible grid already shows
 *   sinofresh_dosage_related()       the sibling dosage tiles already shown
 *   sinofresh_formula_offers()       the tier table's prices, read as numbers
 *   sinofresh_formula_product_alt()  the card alt, with its visual clause
 *
 * None of them reads the database except through readers that already existed,
 * and every one returns an empty answer rather than a guess when the site does
 * not state the fact — the rule the dosage image resolution already follows
 * ("prefer no image over a wrong one"). A guessed species or a guessed price is
 * worse than an absent property: the first is a claim about animal safety and
 * the second a claim about money.
 * ------------------------------------------------------------------------ */

/**
 * The visual half of a dosage form's product-image alt, one clause per form.
 *
 * H5 target format is "product + dosage form + selling point + visual feature";
 * the first three were already in the alt, the visual feature was not. Each
 * clause below describes the render that actually ships for that form (the
 * uploads/<yyyy>/<mm>/<form>.webp still), read off the file rather than
 * inferred from the form's name — "fish oil" is capsules, not a bottle, and
 * "liquids" is a bottle, not a jar.
 *
 * A form with no entry gets the alt it had before this batch rather than an
 * invented clause.
 */
function sinofresh_formula_alt_visuals() {
	static $map = null;
	if ($map === null) {
		$map = array(
			'soft-chews'   => 'brown star- and bone-shaped chews',
			'tablets'      => 'tan speckled round tablets',
			'powders'      => 'green powder with a metal scoop',
			'pastes'       => 'white squeeze tube with a green cap',
			'drops'        => 'amber glass dropper bottle',
			'liquids'      => 'white bottle with a flip-top cap and measuring cup',
			'fish-oil'     => 'golden oval softgel capsules',
			'dental-chews' => 'dark ridged stick chews',
		);
	}
	return $map;
}

/**
 * The alt of a dosage form's product render, with its visual clause.
 *
 * One function rather than three literals because the same still is described in
 * three places: the card markup [sf_formula_grid] prints, the seven sibling tiles
 * inside each dosage page's template, and the first frame of the detail page's
 * gallery (sinofresh_formula_gallery_slots). The templates are static HTML and
 * cannot call this, so they carry the same string verbatim — the gate asserts the
 * carriers agree per form, which is what keeps them from drifting. The gallery
 * frame was the third carrier and was missed on the first pass; see the note
 * there.
 */
function sinofresh_formula_product_alt($form_slug) {
	$form_slug = sanitize_title($form_slug);
	$base = sprintf(
		'SINO FRESH %s private label pet supplement product',
		sinofresh_formula_label($form_slug)
	);
	$visuals = sinofresh_formula_alt_visuals();
	return isset($visuals[$form_slug]) ? $base . ' — ' . $visuals[$form_slug] : $base;
}

/**
 * The dosage page's four .sf-facts-mini core-facts rows as PropertyValue rows.
 *
 * The generator used to look for .sf-spec-list markup here, which batch H2b1
 * replaced with the .sf-facts-mini row; the regex matched nothing on any of the
 * sixteen dosage pages, so additionalProperty was silently absent on all of
 * them while the formula detail pages (which read post meta) had it. The rows
 * were never missing — only unread. Reading them through
 * sinofresh_formula_spec_cell() keeps the scope to the row itself and keeps the
 * schema, the hero meta and the H3 parameter rows on one source.
 *
 * `name` is the visible label, not the data-label: data-label="Packaging
 * formats" prints as "Packaging", and the schema should say what the page says.
 */
function sinofresh_formula_facts_props($form_slug) {
	$props = array();
	foreach (array(
		'MOQ'            => 'MOQ',
		'Lead time'      => 'Lead time',
		'Certifications' => 'Certifications',
		'Packaging'      => 'Packaging formats',
	) as $name => $data_label) {
		$value = sinofresh_formula_spec_cell($form_slug, $data_label);
		if ($value === '') {
			continue;
		}
		$props[] = array('@type' => 'PropertyValue', 'name' => $name, 'value' => $value);
	}
	return $props;
}

/**
 * Who a product is for, as schema.org Audience entries; empty when unstated.
 *
 * Two sources, in this order:
 *
 *   1. the formula record's own sf_formula_species (a declared multi field
 *      whose pool is Dog / Cat) — the record wins because a formula is what
 *      carries a species claim;
 *   2. the sentence after " for " in the dosage page's own <h1> — "Private
 *      Label Soft Chews for Dogs & Cats" — for the records that have no
 *      species filled in, and for the dosage page itself.
 *
 * Measured at gate time: sf_formula_species is empty on all 21 formulas, and
 * only four of the eight dosage headlines state a species (soft chews, tablets
 * and fish oil say Dogs & Cats; dental chews says Dogs). The four that say
 * nothing therefore get no `audience` — the earlier assumption that all eight
 * forms had a fixed species mapping was not true of this site, and inventing
 * one would put a species claim on a product nobody made it for.
 *
 * "Dog" is normalised to "Dogs" so the two sources cannot produce two spellings
 * of one audience.
 */
function sinofresh_formula_audience($form_slug, $post_id = 0) {
	static $cache = array();
	$form_slug = sanitize_title($form_slug);
	$key = $form_slug . '|' . (int) $post_id;
	if (array_key_exists($key, $cache)) {
		return $cache[$key];
	}
	$cache[$key] = array();

	$types = array();
	if ($post_id) {
		foreach (sf_json_array(get_post_meta($post_id, 'sf_formula_species', true)) as $value) {
			$value = trim((string) $value);
			if ($value !== '') {
				$types[] = $value;
			}
		}
	}
	if (!$types && $form_slug !== '') {
		$file = get_stylesheet_directory() . '/templates/page-' . $form_slug . '.html';
		if (file_exists($file)
			&& preg_match('/<h1[^>]*>(.*?)<\/h1>/s', (string) file_get_contents($file), $m)) {
			$headline = html_entity_decode(trim(wp_strip_all_tags($m[1])), ENT_QUOTES, 'UTF-8');
			/* Only the clause after " for ": the words before it are the
			   product line ("Pet Tablets"), and scanning the whole headline
			   would read a species out of a product name one day. */
			if (preg_match('/\bfor\s+(.+)$/i', $headline, $clause)) {
				if (preg_match_all('/\b(dogs?|cats?|puppies|kittens)\b/i', $clause[1], $words)) {
					foreach ($words[1] as $word) {
						$word = ucfirst(strtolower($word));
						if ($word === 'Dog') {
							$word = 'Dogs';
						} elseif ($word === 'Cat') {
							$word = 'Cats';
						} elseif ($word === 'Puppy') {
							$word = 'Puppies';
						} elseif ($word === 'Kitten') {
							$word = 'Kittens';
						}
						if (!in_array($word, $types, true)) {
							$types[] = $word;
						}
					}
				}
			}
		}
	}

	foreach ($types as $type) {
		$cache[$key][] = array('@type' => 'Audience', 'audienceType' => $type);
	}
	return $cache[$key];
}

/**
 * The sibling formulas of one dosage form, as Product references.
 *
 * The arguments mirror [sf_formula_grid limit="4"] exactly — same taxonomy,
 * same order, same exclusion of the formula being read — because the visible
 * "More {form} Formulas" grid is the related set the visitor can check, and a
 * schema that lists a different four would be a second answer to a question
 * the page already answers. The gate compares the emitted URLs with the URLs of
 * the rendered cards, so a future change to either side fails rather than drifts.
 *
 * Returns Product entries rather than bare URLs: schema.org accepts either, and
 * the name is what a consumer needs to tell two formulas apart.
 */
function sinofresh_formula_related($form_slug, $exclude_id = 0, $limit = 4) {
	$form_slug = sanitize_title($form_slug);
	if ($form_slug === '') {
		return array();
	}
	$args = array(
		'post_type'           => 'sf_formula',
		'post_status'         => 'publish',
		'posts_per_page'      => max(1, (int) $limit),
		'orderby'             => array('menu_order' => 'ASC', 'title' => 'ASC'),
		'ignore_sticky_posts' => true,
		'no_found_rows'       => true,
		'tax_query'           => array(array(
			'taxonomy' => 'sf_formula_form',
			'field'    => 'slug',
			'terms'    => $form_slug,
		)),
	);
	if ($exclude_id) {
		$args['post__not_in'] = array((int) $exclude_id);
	}
	$out = array();
	foreach (get_posts($args) as $formula) {
		$name = html_entity_decode(get_the_title($formula), ENT_QUOTES, 'UTF-8');
		if ($name === '') {
			continue;
		}
		$out[] = array('@type' => 'Product', 'name' => $name, 'url' => get_permalink($formula));
	}
	return $out;
}

/**
 * The seven sibling dosage forms a dosage page's tile grid already links to.
 *
 * The tile order is read out of the template rather than reconstructed from
 * the eight-slug list, so the schema follows the page if the grid is ever
 * reordered. A template with no tile grid yields an empty list.
 */
function sinofresh_dosage_related($form_slug) {
	$form_slug = sanitize_title($form_slug);
	$file = get_stylesheet_directory() . '/templates/page-' . $form_slug . '.html';
	if ($form_slug === '' || !file_exists($file)) {
		return array();
	}
	if (!preg_match_all('#sf-tile__media"><a href="/products/([a-z0-9-]+)/"#', (string) file_get_contents($file), $m)) {
		return array();
	}
	$out = array();
	foreach (array_unique($m[1]) as $sibling) {
		if ($sibling === $form_slug) {
			continue;
		}
		$page = get_page_by_path('products/' . $sibling);
		if (!($page instanceof WP_Post)) {
			continue;
		}
		$name = html_entity_decode(get_the_title($page), ENT_QUOTES, 'UTF-8');
		if ($name === '') {
			continue;
		}
		$out[] = array('@type' => 'Product', 'name' => $name, 'url' => get_permalink($page));
	}
	return $out;
}

/**
 * The tier rows as an AggregateOffer, or null when no row states a number.
 *
 * Renderer first, data later (decision B): sf_formula_price_tiers is empty on
 * all 21 formulas, so this returns null on every page today and the emitted
 * schema is unchanged. It is written now so that filling the tier table in
 * wp-admin is the only step left when operations supply real prices.
 *
 * A price is taken only when the whole cell is a plain decimal, optionally
 * behind a currency symbol ("1.20", "$1.20", "USD 1.20"). Anything else — a
 * range, a bare word, "1,200" — is skipped rather than guessed: parsing
 * "1,200" as 1.2 would publish a price twelve hundred times too low, and a
 * skipped row costs one priceSpecification instead.
 *
 * USD is the currency the tier table's own header declares ("Unit price
 * (USD)"), so the schema states what the page states.
 */
function sinofresh_formula_offers($rows) {
	$prices = array();
	$specs  = array();
	foreach ((array) $rows as $row) {
		if (!is_array($row)) {
			continue;
		}
		$price = trim((string) (isset($row['price']) ? $row['price'] : ''));
		if (!preg_match('/^(?:USD\s*|\$\s*)?([0-9]+(?:\.[0-9]+)?)\s*(?:USD)?$/i', $price, $m)) {
			continue;
		}
		$value = (float) $m[1];
		if ($value <= 0) {
			continue;
		}
		$spec = array(
			'@type'         => 'UnitPriceSpecification',
			'price'         => $value,
			'priceCurrency' => 'USD',
		);
		/* H7i: the tier row is {min, max, price}; both ends travel, because
		   AggregateOffer's priceSpecification can carry the range a buyer
		   actually sees ("100-999") instead of a bare lower bound. A legacy
		   qty still reads as the minimum. */
		$min = trim((string) (isset($row['min']) ? $row['min'] : (isset($row['qty']) ? $row['qty'] : '')));
		$max = trim((string) (isset($row['max']) ? $row['max'] : ''));
		if ($min !== '' && preg_match('/([0-9][0-9,]*)/', $min, $q)) {
			$spec['minQuantity'] = array(
				'@type'    => 'QuantitativeValue',
				'value'    => (int) str_replace(',', '', $q[1]),
				'unitText' => 'units',
			);
		}
		if ($max !== '' && preg_match('/([0-9][0-9,]*)/', $max, $q2)) {
			$spec['maxQuantity'] = array(
				'@type'    => 'QuantitativeValue',
				'value'    => (int) str_replace(',', '', $q2[1]),
				'unitText' => 'units',
			);
		}
		$prices[] = $value;
		$specs[]  = $spec;
	}
	if (!$specs) {
		return null;
	}
	return array(
		'@type'              => 'AggregateOffer',
		'priceCurrency'      => 'USD',
		'lowPrice'           => min($prices),
		'highPrice'          => max($prices),
		'offerCount'         => count($specs),
		'priceSpecification' => $specs,
	);
}


/**
 * The ten topics the Organization schema claims expertise in.
 *
 * Eight of them are the dosage forms, read from the same page titles the
 * navigation and the catalogue use — so renaming a dosage page renames the
 * claim, and the claim can never list a form the site does not offer. The last
 * two are the two service lines the rest of the site already sells ("OEM/ODM
 * manufacturing" and "private label"), stated once here as a fixed pair.
 *
 * Memoised: sinofresh_formula_label() resolves a page by path, and the
 * Organization block runs on every page of the site.
 */
function sinofresh_knows_about() {
	static $list = null;
	if ($list !== null) {
		return $list;
	}
	$list = array();
	foreach (array('soft-chews', 'tablets', 'powders', 'pastes', 'drops', 'liquids', 'fish-oil', 'dental-chews') as $slug) {
		$label = sinofresh_formula_label($slug);
		if ($label !== '') {
			$list[] = $label;
		}
	}
	$list[] = 'Pet Supplement OEM/ODM Manufacturing';
	$list[] = 'Private Label Pet Supplements';
	return $list;
}


/**
 * Product JSON-LD (schema.org) for the eight dosage-form landing pages.
 * Data is parsed from the same template file that renders the page (single
 * source of truth, same pattern as the FAQPage schema): name = hero <h1>,
 * description = the hero's `<!-- sf-schema-desc -->` carrier, image = this
 * form's own upload (resolved by file name, so it can never latch onto a
 * Related tile of a sibling product).
 *
 * Batch H5 added three properties, each on a source the page already has:
 * additionalProperty = the four .sf-facts-mini core-facts rows the band
 * displays (the .sf-spec-list reader that used to be here had been dead since
 * H2b1), audience = the species the <h1> names, isRelatedTo = the seven
 * sibling dosage tiles the page links to. description / image / audience /
 * isRelatedTo are each dropped when nothing resolves — never emitted empty,
 * and never guessed.
 *
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

	// additionalProperty: the page's own .sf-facts-mini core-facts rows (the
	// four visible facts — MOQ, lead time, certifications, packaging formats).
	//
	// Batch H5 replaced the .sf-spec-list reader that used to be here. That
	// reader, and the legacy flex-basis:35% table parser behind it, were dead
	// code: batch H2b1 swapped the dosage pages' spec band for .sf-facts-mini
	// and neither branch matched anything afterwards, so additionalProperty
	// was absent on all sixteen dosage pages without a single error. The two
	// dead parsers are kept below only as a fallback for markup this theme no
	// longer ships; on the current eight templates they cannot match.
	$props = sinofresh_formula_facts_props($slug);
	if (!$props) {
		if (preg_match_all('/<span class="sf-spec-term">([^<]+)<\/span><span class="sf-spec-value">([^<]+)<\/span>/', $html, $rows, PREG_SET_ORDER)) {
			foreach ($rows as $r) {
				$props[] = array('@type' => 'PropertyValue', 'name' => html_entity_decode(trim($r[1]), ENT_QUOTES, 'UTF-8'), 'value' => html_entity_decode(trim($r[2]), ENT_QUOTES, 'UTF-8'));
			}
		} elseif (preg_match_all('/flex-basis:35%">\s*<!-- wp:paragraph[^>]*-->\s*<p[^>]*>([^<]+)<\/p>.*?<p class="has-primary-color has-text-color"[^>]*>([^<]+)<\/p>/s', $html, $rows, PREG_SET_ORDER)) {
			foreach ($rows as $r) {
				$props[] = array('@type' => 'PropertyValue', 'name' => html_entity_decode(trim($r[1]), ENT_QUOTES, 'UTF-8'), 'value' => html_entity_decode(trim($r[2]), ENT_QUOTES, 'UTF-8'));
			}
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
	/* audience: the species the page's own headline names ("… for Dogs & Cats").
	   Four of the eight headlines name one; the other four get no audience
	   rather than a species nobody stated. */
	$audience = sinofresh_formula_audience($slug);
	if ($audience) {
		$schema['audience'] = $audience;
	}
	/* isRelatedTo: the seven sibling dosage forms the tile grid on this very
	   page links to, read out of the template in grid order. */
	$related = sinofresh_dosage_related($slug);
	if ($related) {
		$schema['isRelatedTo'] = $related;
	}
	echo "\n" . '<script type="application/ld+json">'
		. wp_json_encode($schema, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE)
		. "</script>\n";
}, 21);

/**
 * Product JSON-LD (schema.org) for a formula detail page (batch 2C, D4).
 *
 * Built from the formula record itself, not from the template: name = the
 * post title, the three specification fields = post meta, image = the same
 * dosage still the cards and the hero resolve (sinofresh_formula_card_image,
 * by form slug — never "the first <img> on the page", which would latch onto
 * a related card's photo).
 *
 * description is assembled from the record's own fields. An excerpt was not
 * an option: excerpts are empty across all 21 formulas, and so is
 * post_content, so the sentence is generated from the dosage form plus the
 * three spec values, dropping any clause whose field is empty.
 *
 * Batch H5 changed the offers position rather than the price position: the
 * property is now rendered whenever the tier table carries numbers, and the
 * tier table is empty on all 21 formulas, so nothing was emitted by this batch
 * either. The earlier wording ("no offers, a standard formula is not a priced
 * SKU") described a decision about this data; the code now implements a rule
 * about any data — a price is published when operations publish one, and never
 * invented when they have not. Two further properties came from sources the
 * record already has: audience from sf_formula_species (empty today, so the
 * four dosage forms whose headline names a species supply it instead) and
 * isRelatedTo from the siblings the page's own "More … Formulas" grid lists.
 *
 * brand/manufacturer/category stay on the eight dosage-page schemas where
 * they describe the product line; here the subject is one recipe.
 */
add_action('wp_head', function () {
	if (is_admin() || defined('REST_REQUEST') || !is_singular('sf_formula')) {
		return;
	}
	$post_id = (int) get_queried_object_id();
	$post    = get_post($post_id);
	if (!($post instanceof WP_Post)) {
		return;
	}
	$name = html_entity_decode(get_the_title($post), ENT_QUOTES, 'UTF-8');
	if ($name === '') {
		return;
	}

	$form_slug  = '';
	$form_label = '';
	$form_terms = wp_get_post_terms($post_id, 'sf_formula_form');
	if (!is_wp_error($form_terms) && $form_terms) {
		$form_slug  = (string) $form_terms[0]->slug;
		$form_label = sinofresh_formula_label($form_terms[0]->slug, $form_terms[0]->name);
	}

	$ingredients = trim((string) get_post_meta($post_id, 'sf_formula_ingredients', true));
	$analysis    = trim((string) get_post_meta($post_id, 'sf_formula_analysis', true));
	$specs       = trim((string) get_post_meta($post_id, 'sf_formula_specs', true));

	$description = $form_label !== ''
		? sprintf('%s — a standard %s formula from the SINO FRESH OEM/ODM range for private-label pet supplements.', $name, $form_label)
		: sprintf('%s — a standard formula from the SINO FRESH OEM/ODM range for private-label pet supplements.', $name);
	if ($ingredients !== '') {
		$description .= ' Ingredients: ' . $ingredients . '.';
	}
	if ($analysis !== '') {
		$description .= ' Guaranteed analysis: ' . $analysis . '.';
	}
	if ($specs !== '') {
		$description .= ' Specifications: ' . $specs . '.';
	}

	$schema = array(
		'@context'    => 'https://schema.org',
		'@type'       => 'Product',
		'name'        => $name,
		'description' => $description,
	);
	$image = sinofresh_formula_card_image($form_slug);
	if ($image !== '') {
		$schema['image'] = $image;
	}
	$props = array();
	foreach (array(
		'Ingredients'         => $ingredients,
		'Guaranteed Analysis' => $analysis,
		'Standard Specs'      => $specs,
	) as $label => $value) {
		if ($value === '') {
			continue;
		}
		$props[] = array('@type' => 'PropertyValue', 'name' => $label, 'value' => $value);
	}
	if ($props) {
		$schema['additionalProperty'] = $props;
	}
	/* offers: rendered only when the tier table carries numbers (decision B —
	   renderer first, data later). Null on all 21 records today. */
	$offers = sinofresh_formula_offers(sf_json_rows(get_post_meta($post_id, 'sf_formula_price_tiers', true)));
	if ($offers) {
		$schema['offers'] = $offers;
	}
	/* audience: the record's own sf_formula_species first, the dosage page's
	   headline second — same reader the dosage pages use. */
	$audience = sinofresh_formula_audience($form_slug, $post_id);
	if ($audience) {
		$schema['audience'] = $audience;
	}
	/* isRelatedTo: the same four siblings the "More … Formulas" grid below the
	   page lists (same taxonomy, order and exclusion), so the schema and the
	   visible cards cannot disagree. */
	$related = sinofresh_formula_related($form_slug, $post_id, 4);
	if ($related) {
		$schema['isRelatedTo'] = $related;
	}

	echo "\n" . '<script type="application/ld+json">'
		. wp_json_encode($schema, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE)
		. "</script>\n";
}, 22);

/**
 * Organization JSON-LD (schema.org) — once, site-wide. sameAs is built from
 * the Social Links settings (only real http(s) URLs; "#" placeholders are
 * skipped), and the logo points at the configured Site Logo attachment, so
 * both follow whatever operations configure in wp-admin. Batch H5 added
 * knowsAbout (sinofresh_knows_about): the ten topics, the eight dosage forms
 * read from their own page titles plus the two service lines.
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
		'email'        => get_option('sf_contact_email', 'sales@zxpet.com'),
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
	/* Batch H1: the same six credentials, now read from the Site Settings
	   certification rows (sf_cert_schema_credentials() keeps the exact
	   names and order this array shipped with, so the default option set
	   renders byte-identically). */
	$schema['hasCredential'] = sf_cert_schema_credentials();
	/* Batch H5: the ten expertise topics — the eight dosage forms (from the
	   same page titles the catalogue uses) plus the two service lines. */
	$schema['knowsAbout'] = sinofresh_knows_about();
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
   Submits Fluent Forms Form 12 ("Feedback", the Gravity Forms Form 6 twin)
   server-side by writing the submission row directly, so no FF AJAX endpoint
   has to be made public and no form embed is needed in the article markup. A
   plain vote is stored with just the vote; an optional email/description
   travels along when the visitor fills the mini form that opens on a
   down-vote. */
add_action('rest_api_init', function () {
	register_rest_route('sinofresh/v1', '/article-feedback', array(
		'methods'             => 'POST',
		'permission_callback' => '__return_true',
		'callback'            => function (WP_REST_Request $req) {
			if (!function_exists('wpFluent')) {
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
			/* The row is written straight into wp_fluentform_submissions —
			 * the same shape FormHandler::prepareInsertData() produces —
			 * instead of driving the form pipeline: the endpoint runs outside
			 * a real page render (no nonce, no rendered form), and Form 12 has
			 * no notifications, confirmations or submission hooks that a
			 * pipeline run would fire. The response JSON mirrors the form's
			 * field names (feedback_type_1, subject_2, description_3,
			 * email_4, privacy_consent_5) so the FF entries screen renders
			 * these rows exactly like native submissions. */
			$form_data = array(
				'feedback_type_1' => 'General Feedback', // Form 12 field 1 (select) — closest match
				'subject_2'       => 'Article feedback (' . $vote . ')' . ($post_id ? ': ' . get_the_title($post_id) : ''),
				'description_3'   => $message,
			);
			if ($email) {
				$form_data['email_4'] = $email;
			}
			if ($req->get_param('consent')) {
				$form_data['privacy_consent_5'] = array('I agree to the Privacy Policy');
			}

			$previous = wpFluent()->table('fluentform_submissions')
				->where('form_id', 12)
				->orderBy('id', 'DESC')
				->first();
			$serial = $previous ? ((int) $previous->serial_number + 1) : 1;

			$now = current_time('mysql');
			$insert_id = wpFluent()->table('fluentform_submissions')->insertGetId(array(
				'form_id'      => 12,
				'serial_number' => $serial,
				'response'     => wp_json_encode($form_data),
				'source_url'   => $post_id ? get_permalink($post_id) : home_url('/'),
				'status'       => 'unread',
				'ip'           => isset($_SERVER['REMOTE_ADDR']) ? sanitize_text_field(wp_unslash($_SERVER['REMOTE_ADDR'])) : '',
				'created_at'   => $now,
				'updated_at'   => $now,
			));
			if (!$insert_id) {
				return new WP_Error('sf_ff_add', 'Could not store feedback.', array('status' => 500));
			}
			return array('ok' => true);
		},
	));
});

/* Fluent Forms — WhatsApp fallback hint under Form 8's submit button (was
   Gravity Forms Form 2's per-form button filter, removed with GF).
   Form 8 ("Get a Quote") is embedded by 10 templates (front page, contact,
   8 dosage pages), so the hint is injected here once instead of being pasted
   into every template. Scoped to form ID 8 via the per-element render filter
   ($form->id check) — Forms 9 (sample) and 10 (factory tour) must not show it.
   FF's submit "button" element compiles to a wrapper div ending in </div>;
   the hint is appended as a sibling block after it, and style.css gives
   .sf-gf-wa-hint width:100% + centred text so it sits on its own line. */
add_filter('fluentform/rendering_field_html_button', function ($html, $data, $form) {
	if ((int) $form->id !== 8) {
		return $html;
	}
	return $html . '<p class="sf-gf-wa-hint">Prefer WhatsApp? Email us and we\'ll switch to WhatsApp.</p>';
}, 10, 3);

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
 * Service JSON-LD (schema.org) — the OEM/ODM Services page and, since batch
 * H8c, its four cooperation-model detail pages.
 *
 * The provider references the Organization node via @id (stamped by the
 * Organization hook above), so search engines link both entities into one
 * graph. areaServed lists the core export markets. name/description must stay
 * in sync with the visible page copy (H1/hero) — same source of truth rule as
 * the FAQPage hook. The `services` entry is byte-for-byte what this hook has
 * always emitted; the four children were added with their templates, so every
 * page in the family carries a Service node that names the page it sits on.
 */
add_action('wp_head', function () {
	if (is_admin() || defined('REST_REQUEST') || !is_page()) {
		return;
	}
	$copy = array(
		'services'               => array(
			'name'        => 'Pet Supplement OEM/ODM Manufacturing',
			'description' => 'Contract manufacturing services for pet supplements — OEM, ODM, Contract Manufacturing, and Private Label. 8 dosage forms, flexible MOQ, FDA, cGMP, ISO 9001, FSSC 22000, HACCP, BRC.',
		),
		'oem'                    => array(
			'name'        => 'OEM Manufacturing — You Bring the Formula',
			'description' => 'Your formula, your specifications. We manufacture on our lines, test every batch, and deliver finished product with the certificates your market asks for.',
		),
		'odm'                    => array(
			'name'        => 'ODM Development — We Develop From Your Idea',
			'description' => 'You bring a concept, a reference sample or a functional requirement. We take it from concept to finished product.',
		),
		'contract-manufacturing' => array(
			'name'        => 'Contract Manufacturing — You Own the IP',
			'description' => 'For established brands with full specifications. You own the IP, we run the production line.',
		),
		'private-label'          => array(
			'name'        => 'Private Label — Pick From Our Proven Formulas',
			'description' => 'Pick from our proven formulas and launch fast under your own brand. Low MOQ for new brands.',
		),
	);
	$slug = (string) get_post_field('post_name', get_queried_object_id());
	if (!isset($copy[$slug])) {
		return;
	}
	$schema = array(
		'@context'    => 'https://schema.org',
		'@type'       => 'Service',
		'name'        => $copy[$slug]['name'],
		'description' => $copy[$slug]['description'],
		'serviceType' => 'Pet Supplement Manufacturing',
		'provider'    => array('@id' => home_url('/#organization')),
		'areaServed'  => array('US', 'EU', 'JP', 'KR', 'BR', 'MX'),
	);
	echo "\n" . '<script type="application/ld+json">'
		. wp_json_encode($schema, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE)
		. "</script>\n";
}, 22);

/* --------------------------------------------------------------------
   Certificate gated download — Fluent Forms Form 11 ("Request COA",
   the Gravity Forms Form 5 twin; the GF hooks went with GF).

   The Quality page's certificate buttons open a modal that fills the
   hidden `certificate_10` field with a document key (fda / cgmp /
   iso9001 / iso22000 / haccp / brc / coa-sample). On submit the visitor
   gets a one-time download token (inc/cert-download.php) in the
   confirmation, and the same document by email with that same link as
   a fallback.

   Hook order: Fluent Forms resolves the confirmation (the
   fluentform/form_submission_confirmation filter inside
   FormHandler::getReturnData()) BEFORE firing
   fluentform/submission_inserted — the same order GF 3.1 used. The
   grant is memoised per request, so whichever hook runs first mints
   the token and the other reuses it — the emailed link and the button
   in the browser are always the exact same one-time token.

   The confirmation card is deliberately plain HTML. FF post-processes
   the confirmation message with fluentform_sanitize_html() (kses —
   data-* attributes and <script> are stripped) and then runs the
   brace-based ShortCodeParser over it ({"..."} JSON would be eaten),
   so the payload travels as DOM instead of attributes: the download
   URL is the card link's href and the email is the <strong> inside
   the note. cert-modal.js reads exactly those two.

   No FF settings screen is involved: Form 11 keeps its default
   confirmation (the message below replaces messageToShow) and both
   the confirmation markup and the customer email are produced here.
   -------------------------------------------------------------------- */

/** Resolve — and memoise — the download grant for one submission. */
function sinofresh_cert_grant($form_data) {
	static $grant = null;
	if (null !== $grant) {
		return $grant;
	}

	$certs = sinofresh_cert_files();
	$cert  = sanitize_key((string) (isset($form_data['certificate_10']) ? $form_data['certificate_10'] : ''));
	if (!isset($certs[$cert])) {
		$cert = 'coa-sample'; // fallback for the page's generic "Request COA" buttons
	}
	$path  = sinofresh_cert_file_path($cert, $certs[$cert]);
	$email = sanitize_email((string) (isset($form_data['email_3']) ? $form_data['email_3'] : ''));
	$token = sinofresh_cert_mint_token($cert, $email);

	$grant = array(
		'cert'     => $cert,
		'label'    => sinofresh_cert_label($cert),
		'email'    => $email,
		'name'     => trim((string) (isset($form_data['contact_person_2']) ? $form_data['contact_person_2'] : '')),
		'url'      => $token ? sinofresh_cert_download_url($cert, $token) : '',
		'has_file' => ('' !== $path && is_readable($path)),
		'path'     => $path,
		'download' => $certs[$cert]['download'],
	);
	return $grant;
}

/* Confirmation: replaces Form 11's default message. The markup is what the
   modal shows in its success state; the plain <a> keeps the form usable with
   JavaScript disabled. FF hides the form itself (hide_form) and renders this
   message in a .ff-message-success node after it. */
add_filter('fluentform/form_submission_confirmation', function ($confirmation, $form_data, $form) {
	if ((int) $form->id !== 11 || !is_array($confirmation)) {
		return $confirmation;
	}
	$g = sinofresh_cert_grant($form_data);
	if (empty($g['url'])) {
		return $confirmation;
	}

	$card = '<div class="sf-cert-result">'
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

	$confirmation['messageToShow'] = $card;
	return $confirmation;
}, 10, 3);

/* Customer email + sales copy. The lead must survive a bad customer address,
   so sales always receives a copy — as the Cc of the customer email, or as
   the sole recipient when the address is unusable. */
add_action('fluentform/submission_inserted', function ($submission_id, $form_data, $form) {
	if ((int) $form->id !== 11) {
		return;
	}
	$g = sinofresh_cert_grant($form_data);
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
		$lines[] = 'sales@zxpet.com · +86 539 866 9539 · zxpet.com';
		$sent    = wp_mail($g['email'], $subject, implode("\n", $lines), array('Cc: ' . $sales), $attachments);
	} else {
		$subject = 'Certificate request without a usable email — ' . $g['label'];
		$lines   = array(
			'A certificate request came in without a usable customer address.',
			'',
			'Company: ' . (string) (isset($form_data['company_name_1']) ? $form_data['company_name_1'] : ''),
			'Contact: ' . (string) (isset($form_data['contact_person_2']) ? $form_data['contact_person_2'] : ''),
			'Email on the entry: ' . (string) (isset($form_data['email_3']) ? $form_data['email_3'] : ''),
			'Country: ' . (string) (isset($form_data['country_4']) ? $form_data['country_4'] : ''),
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

	/* Visibility from the entries screen: what they asked for, the link that
	   was issued, and whether the mail actually left. */
	if (class_exists('\FluentForm\App\Helpers\Helper')) {
		\FluentForm\App\Helpers\Helper::setSubmissionMeta($submission_id, 'sf_cert_document', $g['cert'], 11);
		\FluentForm\App\Helpers\Helper::setSubmissionMeta($submission_id, 'sf_cert_download_url', $g['url'], 11);
		\FluentForm\App\Helpers\Helper::setSubmissionMeta($submission_id, 'sf_cert_mail', $sent ? 'sent' : 'failed', 11);
	}
}, 10, 3);

/**
 * 59. Inquiry conversion tracking (GA4 generate_lead) — client-side now.
 *
 * This used to ride the GF confirmation filters (forms 2-5) as an inline
 * <script> appended to the message. Fluent Forms sanitizes the confirmation
 * message with kses (script tags stripped), so the tracking moved to the
 * native `fluentform_submission_success` CustomEvent that FF's
 * form-submission.js dispatches on `document` (jQuery signal + DOM event,
 * see cert-modal.js for the same pattern). Scope: forms 8-11 — Form 12
 * (article feedback) is not an inquiry. The event fires before FF resets
 * the form, so the dosage select still holds the visitor's choice.
 *
 * The script reads sf_cookie_consent (the site's own consent banner storage)
 * and fires gtag('event', 'generate_lead', ...) only when the visitor
 * accepted analytics; without gtag (GA4 not yet connected) it silently
 * no-ops. No PII: form id, form title, dosage form choice, source URL.
 */
add_action('wp_footer', function () {
	$titles = array(
		8  => 'Get a Quote',
		9  => 'Request a Sample',
		10 => 'Book a Factory Tour',
		11 => 'Request COA',
	);
	?>
	<script>
	(function () {
		'use strict';
		var titles = <?php echo wp_json_encode($titles); ?>;
		document.addEventListener('fluentform_submission_success', function (e) {
			try {
				var consent = null;
				try { consent = JSON.parse(localStorage.getItem('sf_cookie_consent') || 'null'); } catch (err) {}
				if (!consent || consent.analytics !== true) return;
				if (typeof window.gtag !== 'function') return;
				var form = e.detail && e.detail.form;
				if (!form || !form.id) return;
				var id = String(form.id).replace('fluentform_', '');
				if (!titles[id]) return;
				var dosage = '';
				var sel = form.querySelector('select[name^="interested_dosage_form"]');
				if (sel) dosage = sel.value || '';
				window.gtag('event', 'generate_lead', {
					form_id: id,
					form_title: titles[id],
					dosage: dosage,
					form_source_url: document.referrer || ''
				});
			} catch (err) {}
		});
	})();
	</script>
	<?php
}, 99);

<?php
/* H7g local render harness — stubs the WP surface functions.php touches at
 * load time, then really renders sinofresh_formula_config() and
 * sinofresh_formula_gallery() against a fake post. Structural check only. */

$GLOBALS['__h7g_meta'] = array();

function add_action(...$a) {} function add_filter(...$a) {}
function add_shortcode(...$a) {} function remove_action(...$a) {}
function remove_filter(...$a) {} function add_theme_support(...$a) {}
function register_activation_hook(...$a) {} function register_deactivation_hook(...$a) {}
function load_theme_textdomain(...$a) {} function load_plugin_textdomain(...$a) {}
function register_post_type(...$a) {} function register_taxonomy(...$a) {}
function register_setting(...$a) {} function add_submenu_page(...$a) {}
function add_meta_box(...$a) {} function add_menu_page(...$a) {}
function get_option($k, $d = false) {
    if ($k === 'sf_shapes' || $k === 'sf_containers') return null; // fall back to defaults
    return $d;
}
function get_post_meta($id, $k = '', $single = false) {
    $m = array(
        'sf_formula_shape' => 'Bone',
        'sf_formula_container' => 'pouch',
        'sf_formula_gallery_ids' => '',
        'sf_formula_video_url' => '',
        'sf_formula_lifestage' => 'All life stages',
        'sf_formula_species' => 'Dogs',
        'sf_formula_size' => '',
        'sf_formula_price_tiers' => '[{"min":"10","max":"99","price":"3.88"},'
            . '{"min":"100","max":"999","price":"3.58"},{"min":"1000","max":"","price":"3.28"}]',
        'sf_formula_sample_price' => '50',
    );
    return isset($m[$k]) ? $m[$k] : '';
}
function wp_get_attachment_image_url($id, $size = '') { return ''; }
function wp_get_attachment_image(...$a) { return ''; }
function wp_get_attachment_image_src(...$a) { return false; }
function get_post($id = null) { return null; }
function get_queried_object_id() { return 158; }
function get_queried_object() { return null; }
function is_singular($t = '') { return true; }
function is_admin() { return false; }
function is_front_page() { return false; }
function is_page(...$a) { return false; }
function get_stylesheet_directory() { return '/Users/meng/WorkBuddy/sinofresh外贸网站建设/sinofresh-theme'; }
function get_template_directory() { return '/Users/meng/WorkBuddy/sinofresh外贸网站建设/sinofresh-theme'; }
function get_template_directory_uri() { return ''; }
function get_stylesheet_uri() { return ''; }
function wp_enqueue_style(...$a) {} function wp_enqueue_script(...$a) {}
function esc_url($u) { return $u; } function esc_attr($s) { return htmlspecialchars((string)$s, ENT_QUOTES); }
function esc_html($s) { return htmlspecialchars((string)$s, ENT_QUOTES); }
function esc_textarea($s) { return htmlspecialchars((string)$s, ENT_QUOTES); }
function sanitize_text_field($s) { return trim((string)$s); }
function sanitize_title($s) { return strtolower(preg_replace('/[^A-Za-z0-9]+/', '-', (string)$s)); }
function absint($n) { return abs((int)$n); }
function shortcode_atts($d, $a, $s = '') { return array_merge($d, array_intersect_key((array)$a, $d)); }
function apply_filters($t, $v, ...$a) { return $v; }
function do_action(...$a) {} function did_action(...$a) { return 0; }
function current_user_can(...$a) { return true; }
function wp_next_scheduled(...$a) { return false; }
function wp_schedule_event(...$a) { return true; }
function get_the_title($id = null) { return 'Joint Support Soft Chews'; }
function get_permalink($id = null) { return 'https://x/formulas/joint-support-soft-chews/'; }
function get_the_ID() { return 158; }
function has_post_thumbnail(...$a) { return false; }
function get_post_thumbnail_id($id = null) { return 0; }
function wp_is_mobile() { return false; }
function is_admin_bar_showing() { return false; }
function get_current_screen() { return null; }
function wp_localize_script(...$a) {} function wp_set_script_translations(...$a) {}
function __($s, $d = null) { return $s; } function _e($s, $d = null) { echo $s; }
function esc_html__($s, $d = null) { return esc_html($s); }
function esc_html_e($s, $d = null) { echo esc_html($s); }
function esc_attr__($s, $d = null) { return esc_attr($s); }
function register_rest_route(...$a) {}
class WP_REST_Response { public function __construct(...$a) {} }
class WP_Block_Template {}
function wp_register_style(...$a) {} function wp_register_script(...$a) {}
function admin_url(...$a) { return ''; } function site_url(...$a) { return ''; }
function home_url(...$a) { return ''; } function wp_nonce_field(...$a) {}
function settings_fields(...$a) {} function submit_button(...$a) {}
function selected(...$a) {} function checked(...$a) {}
function get_bloginfo($k = '') { return ''; }
function wp_get_current_user() { return null; }
function get_search_form(...$a) { return ''; }
function register_nav_menus(...$a) {} function wp_get_nav_menu_items(...$a) { return array(); }
function has_nav_menu(...$a) { return false; }
function wp_nav_menu(...$a) { return ''; }
function get_terms(...$a) { return array(); }
function wp_get_post_terms(...$a) { return array(); }
function get_the_term_list(...$a) { return ''; }
function get_taxonomy_labels($t) { return (object)array(); }
function is_wp_error($x) { return false; }
function get_locale() { return 'en_US'; }
function apply_shortcodes($c) { return $c; }
function untrailingslashit($s) { return rtrim((string)$s, '/'); }
function trailingslashit($s) { return rtrim((string)$s, '/') . '/'; }
function wp_upload_dir(...$a) { return array('basedir' => '/tmp/h7g-fac', 'baseurl' => '', 'error' => false); }
function get_post_types(...$a) { return array(); }
function add_editor_style(...$a) {} function add_image_size(...$a) {}
function set_post_thumbnail_size(...$a) {} function add_post_type_support(...$a) {}
function remove_theme_support(...$a) {} function get_theme_support(...$a) { return null; }
function register_taxonomy_for_object_type(...$a) {}
function wp_maybe_load_embeds(...$a) {} function embed_handler_html(...$a) {}
function wp_embed_register_handler(...$a) {}
function get_transient($k) { return false; } function set_transient(...$a) { return true; }
function delete_transient(...$a) {} function wp_cache_flush(...$a) {}
function get_locale2() { return 'en_US'; }
function number_format_i18n($n) { return (string)$n; }
function date_i18n($f, $t = null) { return date($f, $t ?: time()); }
function get_date_from_gmt(...$a) { return ''; }
function get_post_custom($id) { return array(); }
function get_post_custom_values(...$a) { return null; }
function wp_reset_postdata() {} function setup_postdata($p) { return true; }
function have_posts() { return false; } function the_post() {}
function wp_query2() {}
function get_query_var($k, $d = '') { return $d; }
function is_tax(...$a) { return false; } function is_archive() { return false; }
function is_single(...$a) { return false; } function is_home(...$a) { return false; }
function is_search() { return false; } function is_404() { return false; }
function is_feed(...$a) { return false; } function is_preview() { return false; }
function get_body_class(...$a) { return array(); }
function post_type_exists(...$a) { return false; }
function taxonomy_exists(...$a) { return false; }
function get_object_taxonomies(...$a) { return array(); }
function is_sticky(...$a) { return false; }
function wp_get_document_title() { return ''; }
function language_attributes() {} function bloginfo($k = '') {}
function wp_head() {} function wp_footer() {} function wp_body_open() {}
function get_header(...$a) {} function get_footer(...$a) {}
function get_search_query() { return ''; }
function esc_url_raw($u) { return $u; }
function sanitize_email($e) { return $e; } function is_email($e) { return (bool)$e; }
function wp_strip_all_tags($s) { return strip_tags((string)$s); }
function wp_kses($s, $k = array()) { return $s; }
function wp_kses_post($s) { return $s; }
function current_time($t) { return time(); }
function get_posts(...$a) { return array(); }
function get_children(...$a) { return array(); }
function get_attached_media(...$a) { return array(); }
function wp_get_attachment_metadata($id) { return false; }
function get_intermediate_image_sizes() { return array(); }
function wp_calculate_image_sizes(...$a) { return ''; }
function wp_get_attachment_caption($id) { return ''; }
function get_adjacent_post(...$a) { return null; }
function get_the_excerpt($id = null) { return ''; }
function get_the_permalink($id = null) { return ''; }
function get_the_date(...$a) { return ''; }
function get_avatar(...$a) { return ''; }
function get_the_author_meta(...$a) { return ''; }
function count_user_posts(...$a) { return 0; }
function wp_trim_words($t, $n = 55, $m = '…') { return $t; }
function wp_html_excerpt($s, $c, $m = '') { return mb_substr((string)$s, 0, $c); }
function convert_smilies($s) { return $s; }
function do_blocks($s) { return $s; }
function do_meta_boxes(...$a) {} function register_meta(...$a) { return true; }
function register_post_meta(...$a) { return true; }
function get_post_status($id = null) { return 'publish'; }
function get_post_field($f, $id = null) { return ''; }
function wp_is_post_revision($id) { return false; }
function wp_is_post_autosave($id) { return false; }
function add_shortcode2(...$a) {}
function register_block_pattern_category(...$a) {}
function register_block_pattern(...$a) {}
function unregister_block_pattern(...$a) {}
function register_block_type(...$a) {}
function get_block_template(...$a) { return null; }
function get_block_templates(...$a) { return array(); }
function wp_enqueue_block_template_skip_link(...$a) {}
function get_block_editor_settings(...$a) { return array(); }
function current_theme_supports(...$a) { return false; }
function is_post_type_archive(...$a) { return false; }
function get_post_type($id = null) { return 'sf_formula'; }
function get_the_terms(...$a) { return false; }
function wp_parse_url($u, $c = -1) { return parse_url((string)$u, $c); }
function get_post_field2() {}
function sanitize_file_name($f) { return preg_replace('/[^A-Za-z0-9._-]/', '-', (string)$f); }
function wp_unslash($v) { return $v; }
$_SERVER['REQUEST_URI'] = '/formulas/joint-support-soft-chews/';
function get_page_by_path(...$a) { return null; }
function get_pages(...$a) { return array(); }

/* The inc/* files guard with ABSPATH and exit silently — define it first. */
if (!defined('ABSPATH')) {
	define('ABSPATH', '/tmp/');
}

require '/Users/meng/WorkBuddy/sinofresh外贸网站建设/sinofresh-theme/functions.php';

/* ---- render ---- */
$config_html = sinofresh_formula_config();
$gallery_html = sinofresh_formula_gallery();

$n = 0;
function say($label, $value) {
	$GLOBALS['n']++;
	echo ($value ? "ok   " : "FAIL ") . $label . "\n";
}

/* the ladder group */
say('pricing group rendered as the ladder',
    strpos($config_html, 'class="sf-fdetail-config__options sf-fdetail-config__tiers"') !== false
    && strpos($config_html, 'data-sf-config-group="pricing"') !== false);
$cards = substr_count($config_html, 'class="sf-fdetail-config__opt sf-tier"');
say('three tier cards (got ' . $cards . ')', $cards === 3);
preg_match('/data-sf-config-group="pricing"(.*?)$/s', $config_html, $pg);
$pricing = isset($pg[1]) ? $pg[1] : '';
say('prices in ladder order (US$3.88 / US$3.58 / US$3.28)',
    preg_match('/sf-tier__price">US\$3\.88<.*?sf-tier__price">US\$3\.58<.*?sf-tier__price">US\$3\.28</s', $pricing) === 1);
say('ranges 10-99 / 100-999 / the open top tier >=1,000',
    preg_match('/sf-tier__range">10-99<.*?sf-tier__range">100-999<.*?sf-tier__range">≥1,000</s', $pricing) === 1);
say('every card is a radio on the pricing group with the range as its value',
    substr_count($pricing, 'type="radio" name="sf-config-pricing"') === 3
    && substr_count($pricing, 'value="10-99"') === 1
    && substr_count($pricing, 'value="100-999"') === 1
    && substr_count($pricing, 'value="≥1,000"') === 1
    && substr_count($pricing, 'data-sf-config-opt="pricing"') === 3);
/* config.js reads an option's label from __text, then __empty-label, then the
   input's value. A tier card has neither span, so the value has to be the
   label — assert the absence, because its presence would silently change what
   the inquiry carries. */
say('no __text span inside the ladder (the value IS the label)',
    substr_count($pricing, 'sf-fdetail-config__text') === 0);

/* the sample row */
say('sample row: US$50.00 (money keeps two decimals), the open flag and the price travel together',
    strpos($pricing, 'sf-fdetail-config__sample-price">US$50.00<') !== false
    && strpos($pricing, 'data-sf-inquiry-sample="US$50.00"') !== false
    && strpos($pricing, 'data-sf-inquiry-open') !== false
    && strpos($pricing, 'href="/contact/#quote"') !== false);

/* the no-JS answer is still printed */
say('the group still prints its own value line (no-JS answer)',
    strpos($pricing, 'sf-fdetail-config__meta">10-99 — US$3.88 / unit') !== false);
/* The hint has to stay IN THE MARKUP: the gate is a CSS rule keyed on --js,
   so what the no-JS visitor reads is decided here, not there. */
say('the pricing group still prints its hint in the markup',
    strpos($pricing, 'sf-fdetail-config__hint">Choose one<') !== false);

/* the endpoint's own reduction still resolves a tier choice */
$rows = sinofresh_formula_config_rows(158, array('pricing' => '100-999'));
say('the endpoint maps a posted tier to its label AND its unit price',
    isset($rows['Quantity & Pricing'])
    && $rows['Quantity & Pricing'] === '100-999 (US$3.58 / unit)');
say('the endpoint drops a tier this record does not offer',
    sinofresh_formula_config_rows(158, array('pricing' => '5-9')) === array());

/* helpers, both shapes */
say('range: both ends', sf_tier_range_label('10', '99') === '10-99');
say('range: open top tier', sf_tier_range_label('1000', '') === '≥1,000');
say('range: the legacy qty end', sf_tier_range_label('200', '') === '≥200');
say('price: two decimals, one prefix', sf_tier_price_label('3.9') === 'US$3.90');
say('price: an admin who typed the currency keeps it once',
    sf_tier_price_label('USD 50') === 'US$50.00');

/* the JSON-LD offer carries both ends now */
$offer = sinofresh_formula_offers(array(array('min' => '100', 'max' => '999', 'price' => '3.58')));
say('offers: minQuantity 100 and maxQuantity 999',
    is_array($offer) && $offer['priceSpecification'][0]['minQuantity']['value'] === 100
    && $offer['priceSpecification'][0]['maxQuantity']['value'] === 999);

/* the H7g surface this batch must not have disturbed */
say('shape group still there, still 8 options, still before container',
    substr_count($config_html, 'name="sf-config-shape"') === 8
    && strpos($config_html, 'data-sf-config-group="shape"') < strpos($config_html, 'data-sf-config-group="container"'));
say('gallery preview layer still hidden by default',
    strpos($gallery_html, '<div class="sf-gallery__preview" data-sf-gallery-preview hidden>') !== false);

echo "\n" . $GLOBALS['n'] . " checks, all listed above.\n";

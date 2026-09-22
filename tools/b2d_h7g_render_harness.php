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
        'sf_formula_price_tiers' => '',
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

echo "== config: shape group present? ==\n";
var_dump(strpos($config_html, 'data-sf-config-group="shape"') !== false);
echo "== shape group BEFORE container? ==\n";
var_dump(strpos($config_html, 'data-sf-config-group="shape"') < strpos($config_html, 'data-sf-config-group="container"'));
echo "== 8 shape options? ==\n";
var_dump(substr_count($config_html, 'name="sf-config-shape"'));
echo "== empty slot carries the label? ==\n";
var_dump(substr_count($config_html, 'sf-fdetail-config__empty-label'));
echo "== meta line shows the record's shape (Bone)? ==\n";
var_dump(preg_match('/data-sf-config-group="shape".*?sf-fdetail-config__meta">Bone</s', $config_html) === 1);
echo "== no __text beside an empty slot (text count == 0 in shape group)? ==\n";
preg_match('/data-sf-config-group="shape".*?data-sf-config-group="/s', $config_html, $mm);
var_dump(isset($mm[0]) ? substr_count($mm[0], 'sf-fdetail-config__text') : 'NO SHAPE GROUP MATCH');
echo "== container group still present? ==\n";
var_dump(strpos($config_html, 'name="sf-config-container"') !== false);
echo "== gallery preview layer present, hidden? ==\n";
var_dump(strpos($gallery_html, '<div class="sf-gallery__preview" data-sf-gallery-preview hidden>') !== false);
echo "== stage still carries slides? ==\n";
var_dump(substr_count($gallery_html, 'sf-gallery__slide'));

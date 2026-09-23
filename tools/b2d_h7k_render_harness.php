<?php
/* H7k local render harness — 待办14 (the still becomes a link) and 待办17
 * (the card badge + its admin dropdown and sanitiser).
 *
 * WHY THIS FILE EXISTS: the batch's own rule is that the sales team owns all
 * product data, so no record on dev carries a badge and the browser can never
 * render one. The 75-page gate therefore proves the badge ABSENT everywhere
 * (which is correct) and this harness proves the badge is RIGHT when a record
 * has one — markup shape, whitelist, the no-still branch, and the admin
 * control that writes it. Stubs + real functions, same idiom as
 * tools/b2d_h7g_render_harness.php.
 *
 * Run: php tools/b2d_h7k_render_harness.php   (exits non-zero on any FAIL)
 */

$GLOBALS['__k'] = array(
	'meta'     => array(),
	'acts'     => array(),   // hook => callbacks, so the save handler is callable
	'stores'   => array(),   // what update/delete_post_meta received
	'title'    => 'Joint Support Soft Chews',
	'uploads'  => '/tmp/h7k-fac',
	'taxforms' => array(),
	'uses'     => array(),
);

function add_action($hook, $cb = null, $prio = 10, $args = 1) {
	if (is_string($hook)) { $GLOBALS['__k']['acts'][$hook][] = $cb; }
}
function add_filter(...$a) {} function add_shortcode(...$a) {} function remove_action(...$a) {}
function remove_filter(...$a) {} function add_theme_support(...$a) {}
function register_activation_hook(...$a) {} function register_deactivation_hook(...$a) {}
function load_theme_textdomain(...$a) {} function load_plugin_textdomain(...$a) {}
function register_post_type(...$a) {} function register_taxonomy(...$a) {}
function register_setting(...$a) {} function add_submenu_page(...$a) {}
function add_meta_box(...$a) {} function add_menu_page(...$a) {}
function get_option($k, $d = false) {
	if ($k === 'sf_shapes' || $k === 'sf_containers') { return null; }
	return $d;
}
function get_post_meta($id, $k = '', $single = false) {
	return isset($GLOBALS['__k']['meta'][$k]) ? $GLOBALS['__k']['meta'][$k] : '';
}
function update_post_meta($id, $k, $v) {
	$GLOBALS['__k']['meta'][$k] = $v;
	$GLOBALS['__k']['stores'][] = array('write', $k, $v);
	return true;
}
function delete_post_meta($id, $k, $v = '') {
	unset($GLOBALS['__k']['meta'][$k]);
	$GLOBALS['__k']['stores'][] = array('delete', $k, '');
	return true;
}
function wp_get_post_terms($id, $tax = '', $args = array()) {
	if ($tax === 'sf_formula_form') { return $GLOBALS['__k']['taxforms']; }
	if ($tax === 'sf_formula_use') {
		$out = array();
		foreach ($GLOBALS['__k']['uses'] as $n) { $out[] = (object) array('name' => $n, 'slug' => strtolower($n), 'term_id' => 1); }
		return $out;
	}
	return array();
}
function get_posts($args = array()) {
	$n = isset($args['posts_per_page']) ? (int) $args['posts_per_page'] : 1;
	$n = ($n <= 0 || $n > 3) ? 3 : $n;
	$out = array();
	for ($i = 0; $i < $n; $i++) { $out[] = (object) array('ID' => 158 + $i); }
	return $out;
}
function wp_get_attachment_image_url($id, $size = '') { return ''; }
function wp_get_attachment_image(...$a) { return ''; }
function wp_get_attachment_image_src(...$a) { return false; }
function get_post($id = null) { return null; }
function get_queried_object_id() { return 158; }
function get_queried_object() { return null; }
function is_singular($t = '') { return false; }
function is_admin() { return false; }
function is_front_page() { return false; }
function is_page(...$a) { return false; }
function get_stylesheet_directory() { return '/Users/meng/WorkBuddy/sinofresh外贸网站建设/sinofresh-theme'; }
function get_template_directory() { return '/Users/meng/WorkBuddy/sinofresh外贸网站建设/sinofresh-theme'; }
function get_template_directory_uri() { return ''; }
function get_stylesheet_uri() { return ''; }
function wp_enqueue_style(...$a) {} function wp_enqueue_script(...$a) {}
function esc_url($u) { return $u; }
function esc_attr($s) { return htmlspecialchars((string) $s, ENT_QUOTES); }
function esc_html($s) { return htmlspecialchars((string) $s, ENT_QUOTES); }
function esc_textarea($s) { return htmlspecialchars((string) $s, ENT_QUOTES); }
function sanitize_text_field($s) { return trim((string) $s); }
function sanitize_textarea_field($s) { return trim((string) $s); }
function sanitize_title($s) { return strtolower(preg_replace('/[^A-Za-z0-9]+/', '-', (string) $s)); }
function absint($n) { return abs((int) $n); }
function shortcode_atts($d, $a, $s = '') { return array_merge($d, array_intersect_key((array) $a, $d)); }
function apply_filters($t, $v, ...$a) { return $v; }
function do_action(...$a) {}
function did_action(...$a) { return 0; }
function current_user_can(...$a) { return true; }
function wp_verify_nonce(...$a) { return true; }   // the nonce gate itself is asserted elsewhere
function wp_slash($v) { return $v; }
function wp_json_encode($v, $f = 0) { return json_encode($v, $f); }
function wp_next_scheduled(...$a) { return false; }
function wp_schedule_event(...$a) { return true; }
function get_the_title($id = null) { return $GLOBALS['__k']['title']; }
function get_permalink($id = null) {
	$n = is_object($id) ? (int) $id->ID : (int) $id;
	return 'https://x/formulas/slug-' . $n . '/';
}
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
function checked($a, $b = true, $echo = true) { $r = ((string) $a === (string) $b) ? " checked='checked'" : ''; if ($echo) { echo $r; } return $r; }
function selected($a, $b = true, $echo = true) { $r = ((string) $a === (string) $b) ? " selected='selected'" : ''; if ($echo) { echo $r; } return $r; }
function get_bloginfo($k = '') { return ''; }
function wp_get_current_user() { return null; }
function get_search_form(...$a) { return ''; }
function register_nav_menus(...$a) {} function wp_get_nav_menu_items(...$a) { return array(); }
function has_nav_menu(...$a) { return false; }
function wp_nav_menu(...$a) { return ''; }
function get_terms(...$a) { return array(); }
function get_the_term_list(...$a) { return ''; }
function get_taxonomy_labels($t) { return (object) array(); }
function is_wp_error($x) { return false; }
function get_locale() { return 'en_US'; }
function apply_shortcodes($c) { return $c; }
function untrailingslashit($s) { return rtrim((string) $s, '/'); }
function trailingslashit($s) { return rtrim((string) $s, '/') . '/'; }
function wp_upload_dir(...$a) {
	return array('basedir' => $GLOBALS['__k']['uploads'], 'baseurl' => 'https://x/wp-content/uploads', 'error' => false);
}
function get_post_types(...$a) { return array(); }
function add_editor_style(...$a) {} function add_image_size(...$a) {}
function set_post_thumbnail_size(...$a) {} function add_post_type_support(...$a) {}
function remove_theme_support(...$a) {} function get_theme_support(...$a) { return null; }
function register_taxonomy_for_object_type(...$a) {}
function wp_maybe_load_embeds(...$a) {} function embed_handler_html(...$a) {}
function wp_embed_register_handler(...$a) {}
function get_transient($k) { return false; } function set_transient(...$a) { return true; }
function delete_transient(...$a) {} function wp_cache_flush(...$a) {}
function number_format_i18n($n) { return (string) $n; }
function date_i18n($f, $t = null) { return date($f, $t ?: time()); }
function get_date_from_gmt(...$a) { return ''; }
function get_post_custom($id) { return array(); }
function get_post_custom_values(...$a) { return null; }
function wp_reset_postdata() {} function setup_postdata($p) { return true; }
function have_posts() { return false; } function the_post() {}
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
function sanitize_email($e) { return $e; } function is_email($e) { return (bool) $e; }
function wp_strip_all_tags($s) { return strip_tags((string) $s); }
function wp_kses($s, $k = array()) { return $s; }
function wp_kses_post($s) { return $s; }
function current_time($t) { return time(); }
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
function wp_html_excerpt($s, $c, $m = '') { return mb_substr((string) $s, 0, $c); }
function convert_smilies($s) { return $s; }
function do_blocks($s) { return $s; }
function do_meta_boxes(...$a) {} function register_meta(...$a) { return true; }
function register_post_meta(...$a) { return true; }
function get_post_status($id = null) { return 'publish'; }
function get_post_field($f, $id = null) { return ''; }
function wp_is_post_revision($id) { return false; }
function wp_is_post_autosave($id) { return false; }
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
function wp_parse_url($u, $c = -1) { return parse_url((string) $u, $c); }
function sanitize_file_name($f) { return preg_replace('/[^A-Za-z0-9._-]/', '-', (string) $f); }
function wp_unslash($v) { return $v; }
$_SERVER['REQUEST_URI'] = '/formulas/';
function get_page_by_path(...$a) { return null; }
function get_pages(...$a) { return array(); }

/* The inc/* files guard with ABSPATH and exit silently — define it first. */
if (!defined('ABSPATH')) {
	define('ABSPATH', '/tmp/');
}

/* The uploads tree the card image is globbed out of. soft-chews.webp exists;
   tablets.webp deliberately does not, which IS the no-still branch. */
@mkdir($GLOBALS['__k']['uploads'] . '/2026/09', 0777, true);
file_put_contents($GLOBALS['__k']['uploads'] . '/soft-chews.webp', 'x');

require '/Users/meng/WorkBuddy/sinofresh外贸网站建设/sinofresh-theme/functions.php';
/* inc/formula-admin.php comes in with functions.php — requiring it again is a
   redeclare fatal. */

$F = 0;
function check($name, $ok, $detail = '') {
	global $F;
	if (!$ok) { $F++; }
	printf("%-4s %s%s\n", $ok ? 'ok' : 'FAIL', $name, ($ok || $detail === '') ? '' : '  → ' . $detail);
}

/* One grid render. $form picks the still (and therefore the branch). */
function grid($form, $badge, $extra = array()) {
	$GLOBALS['__k']['meta']     = array('sf_formula_card_badge' => $badge);
	$GLOBALS['__k']['taxforms'] = array($form);
	$GLOBALS['__k']['uses']     = array('Skin & coat');
	return sinofresh_formula_grid(array_merge(array('form' => $form, 'limit' => 1), $extra));
}

/* ---------- A. the still is a link, the badge rides beside it ------------- */
$html = grid('soft-chews', 'Best Seller');
check('A the still is wrapped in the card image link',
	strpos($html, '<a class="sf-fcard__imagelink" href="https://x/formulas/slug-158/"') !== false);
check('A the link names its destination, not the still',
	strpos($html, 'aria-label="View the Joint Support Soft Chews formula"') !== false);
preg_match('#<figure class="sf-fcard__media">(.*?)</figure>#s', $html, $fig);
$fig = isset($fig[1]) ? $fig[1] : '';
check('A the img is inside the anchor', (bool) preg_match('#<a[^>]*>\s*<img#', $fig));
check('A the badge is inside the still frame', strpos($fig, 'sf-fcard__badge') !== false);
preg_match('#<a class="sf-fcard__imagelink".*?</a>#s', $fig, $a);
$a = isset($a[0]) ? $a[0] : '';
check('A …and NOT inside the link — its label cannot join the accessible name',
	strpos($a, 'Best Seller') === false);
check('A the label is the stored one and the class is its slug',
	strpos($fig, 'class="sf-fcard__badge sf-fcard__badge--best-seller">Best Seller<') !== false);
check('A the badge follows the link rather than preceding it',
	strpos($fig, '</a><span class="sf-fcard__badge') !== false);
check('A the functional tag is untouched', strpos($html, '<span class="sf-fcard__use">Skin & coat</span>') !== false);
check('A the title link is still there',
	strpos($html, '<h3 class="sf-fcard__name"><a href="https://x/formulas/slug-158/">') !== false);

/* ---------- B/C/D. the three remaining badges and the whitelist ----------- */
foreach (array('Hot' => 'hot', 'New' => 'new') as $label => $slug) {
	$h = grid('soft-chews', $label);
	check("B badge \"$label\" paints as --$slug",
		strpos($h, 'sf-fcard__badge--' . $slug . '">' . $label . '<') !== false);
}
$h = grid('soft-chews', '');
check('C an empty answer renders no badge at all', strpos($h, 'sf-fcard__badge') === false);
$h = grid('soft-chews', 'SALE!!!');
check('C an unknown value is dropped, not printed as a class',
	strpos($h, 'sf-fcard__badge') === false && strpos($h, 'SALE') === false);
$h = grid('soft-chews', ' <script>x</script> ');
check('C markup in the meta cannot reach the page', strpos($h, '<script>') === false);

/* ---------- E. no still: the badge moves into the body -------------------- */
$h = grid('tablets', 'Hot');
check('E no still ⇒ no media block', strpos($h, 'sf-fcard__media') === false);
check('E …and no image link to go with it', strpos($h, 'sf-fcard__imagelink') === false);
check('E the badge survives, in its inline placement',
	strpos($h, '<span class="sf-fcard__badge sf-fcard__badge--hot sf-fcard__badge--inline">Hot</span>') !== false);
check('E …as the FIRST child of __body, before the functional tag',
	(bool) preg_match('#<div class="sf-fcard__body"><span class="sf-fcard__badge[^>]*>Hot</span><span class="sf-fcard__use">#', $h));

/* ---------- F. links="false" switches the still off too ------------------- */
$h = grid('soft-chews', 'New', array('links' => 'false'));
check('F links="false" leaves the still unlinked', strpos($h, 'sf-fcard__imagelink') === false);
check('F …the title too', strpos($h, '<h3 class="sf-fcard__name">Joint Support Soft Chews</h3>') !== false);
check('F …and the badge is unaffected', strpos($h, 'sf-fcard__badge--new') !== false);

/* ---------- G. the admin control ----------------------------------------- */
$spec = null;
foreach (sf_formula_mb_fields() as $s) {
	if ($s['key'] === 'sf_formula_card_badge') { $spec = $s; }
}
check('G the field is declared, optional, in the Media box',
	$spec && $spec['group'] === 'media' && $spec['type'] === 'select' && (int) $spec['req'] === 1,
	json_encode($spec));
check('G its options ARE the badge vocabulary (one source, not a copy)',
	$spec && $spec['pool'] === array_keys(sinofresh_formula_card_badges()));

$GLOBALS['__k']['meta']['sf_formula_card_badge'] = 'Hot';
ob_start();
sf_formula_render_field($spec, 158);
$sel = ob_get_clean();
preg_match_all('#<option value="([^"]*)"([^>]*)>([^<]*)</option>#', $sel, $m, PREG_SET_ORDER);
$opts = array();
foreach ($m as $o) { $opts[$o[1]] = array('sel' => strpos($o[2], 'selected') !== false, 'label' => $o[3]); }
check('G a real <select>, not a group of radios', strpos($sel, '<select class="sf-mb__select"') !== false);
check('G four answers: none + the three badges', count($opts) === 4, json_encode(array_keys($opts)));
check('G the empty answer has its own wording', isset($opts['']) && $opts['']['label'] === '— None —');
check('G the stored value is the selected one',
	isset($opts['Hot']) && $opts['Hot']['sel'] === true
	&& !$opts['New']['sel'] && !$opts['Best Seller']['sel'] && !$opts['']['sel']);

/* ---------- H. the sanitiser --------------------------------------------- */
$save = isset($GLOBALS['__k']['acts']['save_post_sf_formula'][0]) ? $GLOBALS['__k']['acts']['save_post_sf_formula'][0] : null;
check('H the save handler is registered', is_callable($save));
$nonces = array();
foreach (array_keys(sf_formula_mb_groups()) as $g) { $nonces['sf_mb_nonce_' . $g] = 'x'; }

function try_save($save, $nonces, $value, $keys = true) {
	$GLOBALS['__k']['stores'] = array();
	$_POST = $keys ? $nonces : array();
	if ($value !== null) { $_POST['sf_formula_card_badge'] = $value; }
	call_user_func($save, 158);
	foreach (array_reverse($GLOBALS['__k']['stores']) as $s) {
		if ($s[1] === 'sf_formula_card_badge' && $s[0] === 'write') { return $s[2]; }
	}
	return '(deleted)';
}

check('H "Best Seller" is stored verbatim', try_save($save, $nonces, 'Best Seller') === 'Best Seller');
check('H "Hot" likewise', try_save($save, $nonces, 'Hot') === 'Hot');
check('H "New" likewise', try_save($save, $nonces, 'New') === 'New');
check('H a value outside the vocabulary is stored as none',
	try_save($save, $nonces, 'BestSeller') === '(deleted)');
check('H …and so is an injected class fragment',
	try_save($save, $nonces, 'hot" onmouseover="x') === '(deleted)');
check('H choosing none deletes the key rather than writing ""',
	try_save($save, $nonces, '') === '(deleted)');
$GLOBALS['__k']['stores'] = array();
try_save($save, array(), 'Hot');
check('H (nonce gate) an unauthorised round trip writes nothing',
	$GLOBALS['__k']['stores'] === array(), json_encode($GLOBALS['__k']['stores']));

@unlink($GLOBALS['__k']['uploads'] . '/soft-chews.webp');
@rmdir($GLOBALS['__k']['uploads'] . '/2026/09');
@rmdir($GLOBALS['__k']['uploads'] . '/2026');
@rmdir($GLOBALS['__k']['uploads']);

echo $F === 0 ? "\nALL CHECKS PASSED\n" : "\n$F CHECK(S) FAILED\n";
exit($F === 0 ? 0 : 1);

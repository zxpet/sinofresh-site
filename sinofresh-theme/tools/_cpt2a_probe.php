<?php
/* 批次 2A 第一步扫描探针（只读）。
   目的：注册 CPT 之前，把「现有注册面 / rewrite 面 / 内容面」三处现状取全。
   运行：
     php -d mysqli.default_socket=<run>/mysql/mysqld.sock tools/_cpt2a_probe.php
   约束：只 SELECT / 只读 WP API，不写 DB、不改 option。 */

$ROOT = '/Users/meng/Local Sites/sinofresh/app/public';
require_once $ROOT . '/wp-load.php';
if (!function_exists('get_post_types')) { fwrite(STDERR, "WP not loaded\n"); exit(1); }

$line = str_repeat('-', 78);
function sec($t) { echo "\n" . str_repeat('=', 78) . "\n== $t\n" . str_repeat('=', 78) . "\n"; }

/* ---------- 1. 现有 post type / taxonomy 注册面 ---------- */
sec('1. 已注册 post_type（含内置）');
$pts = get_post_types(array(), 'objects');
printf("总计 %d\n", count($pts));
foreach ($pts as $k => $o) {
    $custom = ($o->_builtin ? 'builtin' : 'CUSTOM');
    // 只详列自定义 + 关键内置
    if (!$o->_builtin || in_array($k, array('post', 'page', 'attachment'), true)) {
        printf("  %-24s %-8s public=%-5s archive=%-5s rewrite=%-22s rest=%s\n",
            $k, $custom,
            var_export($o->public, true),
            var_export($o->has_archive, true),
            is_array($o->rewrite) ? ($o->rewrite['slug'] ?? '?') : var_export($o->rewrite, true),
            var_export($o->show_in_rest, true));
    }
}

sec('1b. 已注册 taxonomy（含内置）');
$taxes = get_taxonomies(array(), 'objects');
printf("总计 %d\n", count($taxes));
foreach ($taxes as $k => $o) {
    printf("  %-26s %-8s public=%-5s ui=%-5s objects=%s\n",
        $k, ($o->_builtin ? 'builtin' : 'CUSTOM'),
        var_export($o->public, true), var_export($o->show_ui, true),
        implode(',', (array) $o->object_type));
}

sec('1c. sf_formula / sf_formula_form / sf_formula_use 是否已存在（应为 false）');
foreach (array('sf_formula', 'sf_formula_form', 'sf_formula_use') as $k) {
    printf("  post_type_exists(%-18s) = %s | taxonomy_exists = %s\n",
        $k . ')', var_export(post_type_exists($k), true), var_export(taxonomy_exists($k), true));
}

sec('1d. 已注册 meta（register_meta 面）');
$metas = get_registered_meta_keys('post');
printf("post 对象已注册 meta 数 = %d\n", count($metas));
foreach ($metas as $k => $a) {
    printf("  %-32s type=%-8s single=%-5s rest=%s\n", $k, $a['type'] ?? '?',
        var_export($a['single'] ?? null, true), var_export($a['show_in_rest'] ?? null, true));
}
printf("post_type=sf_formula 已注册 meta 数 = %d（注册前应为 0）\n",
    count(get_registered_meta_keys('post', 'sf_formula')));

/* ---------- 2. rewrite 面 ---------- */
sec('2. rewrite 规则现状');
printf("permalink_structure        = %s\n", var_export(get_option('permalink_structure'), true));
printf("permalink_structure(home)  = %s\n", home_url('/'));
$rules = get_option('rewrite_rules');
printf("rewrite_rules 选项类型     = %s，条目数 = %s\n",
    gettype($rules), is_array($rules) ? count($rules) : 'N/A');
if (is_array($rules)) {
    $with_formulas = array();
    $custom = array();
    foreach ($rules as $re => $q) {
        if (strpos($re, 'formulas') !== false) { $with_formulas[$re] = $q; }
    }
    printf("含 'formulas' 的规则数     = %d\n", count($with_formulas));
    foreach ($with_formulas as $re => $q) { printf("    %-46s -> %s\n", $re, $q); }
    // 抽样看自定义（非 WP 默认）的附件/页面规则
    echo "  --- 抽样 12 条（判断是否默认结构）---\n";
    $i = 0;
    foreach ($rules as $re => $q) { printf("    %-58s -> %s\n", $re, $q); if (++$i >= 12) break; }
    // 是否存在任何 add_rewrite_rule 类自定义（非标准模式）
    $odd = array();
    foreach ($rules as $re => $q) {
        if (strpos($re, 'attachment') === false && strpos($re, 'category') === false
            && strpos($re, 'tag') === false && strpos($re, 'author') === false
            && strpos($re, 'page') === false && strpos($re, 'search') === false
            && strpos($re, 'feed') === false && strpos($re, 'comment') === false
            && strpos($re, 'trackback') === false && strpos($re, 'embed') === false
            && strpos($re, 'wp-json') === false && strpos($re, '(?:.?.+?)?') === false
            && strpos($re, '([^/]+)') === false) {
            $odd[$re] = $q;
        }
    }
    printf("  非标准（疑似自定义）规则数 = %d\n", count($odd));
    foreach ($odd as $re => $q) { printf("    %-58s -> %s\n", $re, $q); }
}
$GLOBALS['wp_rewrite']->init();
printf("wp_rewrite 已注册的 extra permastructs = %s\n",
    var_export(array_keys((array) $GLOBALS['wp_rewrite']->extra_permastructs), true));

/* ---------- 3. 内容面：页面 slug / ID ---------- */
sec('3. 现有页面（8 剂型 + 关键父页）');
$pages = get_posts(array(
    'post_type' => 'page', 'post_status' => array('publish', 'draft'),
    'numberposts' => -1, 'orderby' => 'menu_order', 'order' => 'ASC',
));
printf("页面总数 = %d\n", count($pages));
printf("  %-6s %-26s %-9s %-8s %s\n", 'ID', 'slug', 'status', 'parent', 'permalink');
foreach ($pages as $p) {
    printf("  %-6d %-26s %-9s %-8d %s\n", $p->ID, $p->post_name, $p->post_status,
        $p->post_parent, get_permalink($p));
}
$dosage = array('soft-chews', 'tablets', 'powders', 'pastes', 'drops', 'liquids', 'fish-oil', 'dental-chews');
echo "\n  --- 8 剂型 slug 核对 ---\n";
foreach ($dosage as $s) {
    $o = get_page_by_path($s);
    printf("    %-16s => %s\n", $s,
        $o ? sprintf('ID %d  %s', $o->ID, get_permalink($o)) : '** 缺失 **');
}
$products = get_page_by_path('products');
printf("  products 父页 => %s\n", $products ? sprintf('ID %d', $products->ID) : '缺失');
$kids = get_pages(array('parent' => $products ? $products->ID : 19, 'post_status' => 'publish'));
printf("  products 的 published 子页 = %d 个\n", count($kids));

/* ---------- 4. 现有 postmeta：sf_last_reviewed ---------- */
sec('4. sf_last_reviewed 现状（meta 先例的实际形态）');
global $wpdb;
$n = $wpdb->get_var($wpdb->prepare(
    "SELECT COUNT(*) FROM {$wpdb->postmeta} WHERE meta_key = %s", 'sf_last_reviewed'));
printf("postmeta 中 sf_last_reviewed 行数 = %s\n", var_export($n, true));
printf("register_post_meta 是否注册 'sf_last_reviewed' = %s\n",
    var_export(metadata_exists('post', 0, 'sf_last_reviewed') && isset(get_registered_meta_keys('post')['sf_last_reviewed']), true));
printf("→ 说明：该字段靠 WP 内置「自定义字段」面板读写，主题**未**注册 meta（因此 register_post_meta 在本主题是首次）\n");

/* ---------- 5. 主题 / 环境 ---------- */
sec('5. 主题与环境');
$th = wp_get_theme();
printf("stylesheet       = %s\n", get_stylesheet());
printf("template         = %s\n", get_template());
printf("theme dir        = %s\n", get_stylesheet_directory());
printf("theme version    = %s\n", $th->get('Version'));
printf("WP version       = %s\n", get_bloginfo('version'));
printf("PHP version      = %s\n", PHP_VERSION);
printf("siteurl          = %s\n", get_option('siteurl'));
printf("home             = %s\n", get_option('home'));
printf("blog_public      = %s\n", get_option('blog_public'));
printf("WP_DEBUG         = %s\n", var_export(defined('WP_DEBUG') ? WP_DEBUG : null, true));
printf("WP_DEBUG_LOG     = %s\n", var_export(defined('WP_DEBUG_LOG') ? WP_DEBUG_LOG : null, true));
printf("SAVEQUERIES      = %s\n", var_export(defined('SAVEQUERIES') ? SAVEQUERIES : null, true));
printf("did_action('after_switch_theme') 触发次数 = %d\n", did_action('after_switch_theme'));
printf("after_switch_theme 是否有回调 = %s\n",
    var_export((bool) has_action('after_switch_theme'), true));

sec('5b. 已注册 shortcode');
global $shortcode_tags;
$sf = array();
foreach ($shortcode_tags as $tag => $cb) {
    if (strpos($tag, 'sf_') === 0) { $sf[$tag] = $cb; }
}
printf("sf_* shortcode 数 = %d\n", count($sf));
foreach ($sf as $tag => $cb) {
    printf("  %-22s => %s\n", $tag,
        is_string($cb) ? $cb : (is_array($cb) ? implode('::', $cb) : 'closure'));
}
printf("shortcode 总数 = %d\n", count($shortcode_tags));
printf("sf_formula_grid 是否已存在 = %s\n", var_export(shortcode_exists('sf_formula_grid'), true));

sec('5c. 已注册 block pattern / pattern category');
$pr = WP_Block_Patterns_Registry::get_instance();
$all = $pr->get_all_registered();
printf("pattern 总数 = %d\n", count($all));
$pc = WP_Block_Pattern_Categories_Registry::get_instance();
$cats = $pc->get_all_registered();
printf("pattern 分类 = %s\n", implode(', ', array_column($cats, 'name')));

sec('6. 调试日志状态');
foreach (array(
    WP_CONTENT_DIR . '/debug.log',
    $ROOT . '/debug.log',
) as $f) {
    printf("  %s => %s\n", $f, file_exists($f)
        ? sprintf('存在，%d B，mtime %s', filesize($f), date('Y-m-d H:i:s', filemtime($f)))
        : '不存在');
}

echo "\n" . str_repeat('=', 78) . "\n扫描完成（只读，未写 DB）\n";

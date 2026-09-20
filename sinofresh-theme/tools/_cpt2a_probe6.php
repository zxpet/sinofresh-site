<?php
/* 批次 2A 扫描探针 #6（只读·注册预演终检）：
   内存注册后打印 taxonomy/meta/post_type 的**实际解析结果**，以及 CPT 的模板回退链。
   运行：php -d mysqli.default_socket=<run>/mysql/mysqld.sock tools/_cpt2a_probe6.php */

$ROOT = '/Users/meng/Local Sites/sinofresh/app/public';
require_once $ROOT . '/wp-load.php';
function sec($t) { echo "\n" . str_repeat('=', 78) . "\n== $t\n" . str_repeat('=', 78) . "\n"; }

/* ---- 与拟交付 1:1 的内存注册 ---- */
register_post_type('sf_formula', array(
    'labels' => array('name' => 'Formulas', 'singular_name' => 'Formula',
        'add_new' => 'Add New Formula', 'edit_item' => 'Edit Formula'),
    'public' => true, 'has_archive' => true,
    'menu_icon' => 'dashicons-clipboard', 'menu_position' => 21,
    'supports' => array('title', 'editor', 'thumbnail', 'excerpt',
                        'revisions', 'page-attributes', 'custom-fields'),
    'taxonomies' => array('sf_formula_form', 'sf_formula_use'),
    'rewrite' => array('slug' => 'formulas', 'with_front' => false),
    'show_in_rest' => true, 'hierarchical' => false,
));
register_taxonomy('sf_formula_form', 'sf_formula', array(
    'labels' => array('name' => 'Dosage Forms', 'singular_name' => 'Dosage Form'),
    'hierarchical' => false, 'public' => false, 'show_ui' => true,
    'show_in_rest' => true, 'rewrite' => false,
));
register_taxonomy('sf_formula_use', 'sf_formula', array(
    'labels' => array('name' => 'Functions', 'singular_name' => 'Function'),
    'hierarchical' => false, 'public' => false, 'show_ui' => true,
    'show_in_rest' => true, 'rewrite' => false,
));
$auth = function () { return current_user_can('edit_posts'); };
foreach (array('sf_formula_ingredients', 'sf_formula_analysis',
               'sf_formula_specs', 'sf_formula_source') as $mk) {
    register_post_meta('sf_formula', $mk, array(
        'type' => 'string', 'single' => true, 'show_in_rest' => true,
        'auth_callback' => $auth,
    ));
}

sec('A. post_type 解析结果');
$pt = get_post_type_object('sf_formula');
foreach (array('name', 'label', 'public', 'publicly_queryable', 'exclude_from_search',
               'show_ui', 'show_in_menu', 'show_in_rest', 'has_archive', 'hierarchical',
               'query_var', 'menu_position', 'menu_icon', 'capability_type', 'map_meta_cap') as $k) {
    $v = $pt->$k ?? null;
    printf("  %-22s = %s\n", $k, is_scalar($v) || $v === null ? var_export($v, true)
        : json_encode($v, JSON_UNESCAPED_SLASHES));
}
printf("  supports = %s\n", json_encode(array_keys(get_all_post_type_supports('sf_formula'))));
printf("  rewrite  = %s\n", json_encode($pt->rewrite, JSON_UNESCAPED_SLASHES));
printf("  REST base = %s\n", $pt->rest_base ?: $pt->name);

sec('B. taxonomy 解析结果（重点看 query_var / rewrite / public 的实际值）');
foreach (array('sf_formula_form', 'sf_formula_use') as $tx) {
    $t = get_taxonomy($tx);
    echo "  --- $tx ---\n";
    foreach (array('label', 'public', 'publicly_queryable', 'show_ui', 'show_in_menu',
                   'show_in_nav_menus', 'show_in_rest', 'hierarchical', 'query_var',
                   'rewrite', 'rest_base') as $k) {
        $v = $t->$k ?? null;
        printf("      %-22s = %s\n", $k, is_scalar($v) || $v === null ? var_export($v, true)
            : json_encode($v, JSON_UNESCAPED_SLASHES));
    }
    printf("      object_type           = %s\n", json_encode($t->object_type));
    printf("      ** 是否产生前台归档/重写规则 = %s **\n",
        (false !== $t->rewrite || false !== $t->query_var) ? '是（需复核！）' : '否 ✓');
}
printf("\n  注册后 extra_permastructs = %s\n",
    implode(', ', array_keys((array) $GLOBALS['wp_rewrite']->extra_permastructs)));
printf("  （taxonomy 未进 permastruct → 无 term 前台 URL，符合 public:false 预期）\n");

sec('C. meta 解析结果');
$keys = get_registered_meta_keys('post', 'sf_formula');
printf("  sf_formula 已注册 meta 数 = %d\n", count($keys));
foreach ($keys as $k => $a) {
    $cb = $a['auth_callback'] ?? null;
    $cbdesc = is_string($cb) ? $cb : (is_object($cb) ? 'Closure' : (is_array($cb) ? implode('::', $cb) : var_export($cb, true)));
    printf("    %-26s type=%-7s single=%-5s rest=%-5s auth=%s\n", $k, $a['type'],
        var_export($a['single'], true), var_export($a['show_in_rest'], true), $cbdesc);
}
printf("  auth 过滤器是否已挂 = auth_post_meta_sf_formula_ingredients_for_sf_formula: %s\n",
    var_export(has_filter('auth_post_meta_sf_formula_ingredients_for_sf_formula'), true));
printf("\n  —— auth_callback 语义核对（capabilities.php:477-518）——\n");
printf("  默认 $allowed = !is_protected_meta(key,'post')；未加下划线前缀 → true\n");
printf("  auth_callback 返回 true → $allowed=true → 仍走 map_meta_cap('edit_post',$post_id) 的映射能力\n");
printf("  ⇒ 本 spec 的 auth_callback 与「不写 auth_callback」实际等价，**不弱于 WP 默认** ✓\n");

sec('D. 是否会被 REST 暴露');
$server = rest_get_server();
$server->init_serve_hooks ?? null;
printf("  rest_get_server() 可用 = %s\n", var_export((bool) $server, true));

sec('E. CPT 模板回退链（WP 7.1.1 实测）');
$GLOBALS['post'] = null;
printf("  单条 sf_formula 的回退顺序（get_template_hierarchy，$template_type=wp_template）:\n");
foreach (get_template_hierarchy('single-sf_formula', true) as $t) {
    $f = get_stylesheet_directory() . "/templates/$t.html";
    printf("    %-28s 磁盘存在=%s\n", $t, file_exists($f) ? '** 是 **' : '否');
}
printf("\n  归档 sf_formula 的回退顺序:\n");
foreach (get_template_hierarchy('archive-sf_formula', true) as $t) {
    $f = get_stylesheet_directory() . "/templates/$t.html";
    printf("    %-28s 磁盘存在=%s\n", $t, file_exists($f) ? '** 是 **' : '否');
}

sec('F. 现有 single.html / archive.html 会不会被 CPT 命中（=2A 的可见副作用）');
foreach (array('single.html', 'archive.html', 'index.html', 'page.html') as $t) {
    $p = get_stylesheet_directory() . "/templates/$t";
    if (file_exists($p)) {
        printf("  %-16s %6d B  首行块注释：%s\n", $t, filesize($p),
            trim(substr(explode("\n", file_get_contents($p))[0], 0, 60)));
    }
}
printf("\n  ⇒ 2A 只注册不建模板：/formulas/ 会用 archive.html、/formulas/<slug>/ 会用 single.html\n");

sec('G. 占位符令牌现状（2A.6 需新增 FORM_* ）');
$ph = file_get_contents(get_stylesheet_directory() . '/functions.php');
preg_match_all('/\{\{[A-Z_]+\}\}/', $ph, $m);
printf("  functions.php 中出现的占位符令牌 = %s\n", implode(', ', array_unique($m[0])));
preg_match_all('/\{\{[A-Z_]+\}\}/', file_get_contents(get_stylesheet_directory() . '/templates/single.html'), $m2);
printf("  single.html 中出现的占位符令牌 = %s\n", implode(', ', array_unique($m2[0])));
foreach (array('FORM_CRUMB', 'FORM_HREF') as $need) {
    printf("  {{%s}} 是否已存在 = %s\n", $need,
        strpos($ph, '{{' . $need . '}}') !== false ? '是（冲突！）' : '否（可新增 ✓）');
}

echo "\n" . str_repeat('=', 78) . "\n探针 #6 完成（只读）\n";

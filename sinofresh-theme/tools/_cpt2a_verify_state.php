<?php
/**
 * Batch 2A verification — registration state + rewrite rules (read-only).
 *
 * Prints what WordPress actually registered and generated, not what the
 * source code appears to ask for. Run with the Local PHP + socket:
 *   php -d mysqli.default_socket=<sock> tools/_cpt2a_verify_state.php
 */

require_once '/Users/meng/Local Sites/sinofresh/app/public/wp-load.php';

echo "=== A. 注册结果（WP 实际解析出的属性）===\n";

$pt = get_post_type_object('sf_formula');
if (!$pt) {
    echo "  *** sf_formula 未注册 ***\n";
} else {
    printf("  post_type            = %s\n", $pt->name);
    printf("  labels.name          = %s\n", $pt->labels->name);
    printf("  labels.singular      = %s\n", $pt->labels->singular_name);
    printf("  public               = %s\n", var_export($pt->public, true));
    printf("  publicly_queryable   = %s\n", var_export($pt->publicly_queryable, true));
    printf("  has_archive          = %s\n", var_export($pt->has_archive, true));
    printf("  hierarchical         = %s\n", var_export($pt->hierarchical, true));
    printf("  show_in_rest         = %s\n", var_export($pt->show_in_rest, true));
    printf("  rest_base            = %s\n", var_export($pt->rest_base, true));
    printf("  menu_position        = %s\n", var_export($pt->menu_position, true));
    printf("  menu_icon            = %s\n", var_export($pt->menu_icon, true));
    printf("  rewrite.slug         = %s\n", var_export($pt->rewrite['slug'] ?? null, true));
    printf("  rewrite.with_front   = %s\n", var_export($pt->rewrite['with_front'] ?? null, true));
    printf("  query_var            = %s\n", var_export($pt->query_var, true));
    printf("  supports             = %s\n", implode(',', get_all_post_type_supports('sf_formula')));
    printf("  taxonomies (object)  = %s\n", implode(',', get_object_taxonomies('sf_formula')));
    printf("  published 条数        = %d\n", (int) wp_count_posts('sf_formula')->publish);
}

foreach (array('sf_formula_form', 'sf_formula_use') as $tax) {
    $t = get_taxonomy($tax);
    if (!$t) {
        printf("  *** %s 未注册 ***\n", $tax);
        continue;
    }
    printf("\n  taxonomy %s\n", $tax);
    printf("    labels.name        = %s\n", $t->labels->name);
    printf("    object_type        = %s\n", implode(',', $t->object_type));
    printf("    public             = %s\n", var_export($t->public, true));
    printf("    publicly_queryable = %s\n", var_export($t->publicly_queryable, true));
    printf("    show_ui            = %s\n", var_export($t->show_ui, true));
    printf("    show_in_rest       = %s\n", var_export($t->show_in_rest, true));
    printf("    query_var          = %s\n", var_export($t->query_var, true));
    printf("    rewrite            = %s\n", var_export($t->rewrite, true));
    printf("    term 数            = %d\n", (int) wp_count_terms(array('taxonomy' => $tax, 'hide_empty' => false)));
}

echo "\n=== B. register_post_meta 结果 ===\n";
$keys = get_registered_meta_keys('post', 'sf_formula');
foreach (array('sf_formula_ingredients', 'sf_formula_analysis', 'sf_formula_specs', 'sf_formula_source') as $k) {
    if (!isset($keys[$k])) {
        printf("  %-24s *** 未注册 ***\n", $k);
        continue;
    }
    $m = $keys[$k];
    printf("  %-24s type=%-7s single=%-5s rest=%-5s auth=%s\n",
        $k,
        $m['type'],
        var_export($m['single'], true),
        var_export($m['show_in_rest'], true),
        is_callable($m['auth_callback']) ? 'callable' : var_export($m['auth_callback'], true)
    );
}

echo "\n=== C. rewrite_rules ===\n";
$rules = get_option('rewrite_rules');
printf("  条数 = %d\n", is_array($rules) ? count($rules) : -1);
printf("  sha256(serialize) = %s\n", substr(hash('sha256', serialize($rules)), 0, 6) . '…' . substr(hash('sha256', serialize($rules)), -4));
printf("  含 index.php?sf_formula= = %s\n", (strpos(serialize($rules), 'index.php?sf_formula=') !== false) ? 'YES' : 'NO');
printf("  option sinofresh_rewrite_version = %s\n", var_export(get_option('sinofresh_rewrite_version'), true));

/* Reproduce WP::parse_request()'s outer loop: first pattern wins, patterns are
   matched against the request path with the home path already stripped. With
   home_url() = http://sinofresh.local there is no home path to strip. */
function sf_probe_match($path) {
    global $wp_rewrite;
    $rules = get_option('rewrite_rules');
    if (!is_array($rules)) {
        return array('(no rules)', '(none)');
    }
    $path = ltrim($path, '/');
    foreach ($rules as $match => $query) {
        if (preg_match("#^$match#", $path, $m)) {
            $q = $query;
            $vars = '?' . $q;
            foreach (array_slice($m, 1) as $i => $val) {
                $vars = str_replace('$matches[' . ($i + 1) . ']', $val, $vars);
            }
            return array($match, $q);
        }
    }
    return array('(no match)', '(none)');
}

echo "\n  路径解析（首个命中的规则）:\n";
foreach (array(
    'products/soft-chews/'      => '页面兜底：应为 pagename',
    'formulas/'                 => 'CPT 归档',
    'formulas/test-formula/'    => 'CPT 单篇',
    'formulas/page/2/'          => 'CPT 分页',
    'zh/products/soft-chews/'   => 'TP 前缀（预演，TP 已在 parse_request 前剥离）',
    'about/'                    => '普通页面',
    'blog/'                     => '博客页',
) as $path => $note) {
    list($m, $q) = sf_probe_match($path);
    printf("    %-26s -> %-46s  [%s]\n", $path, $q, $note);
}

echo "\n=== D. shortcode 注册 ===\n";
foreach (array('sf_explore_chips', 'sf_archive_count', 'sf_blog_chips', 'sf_formula_grid') as $sc) {
    printf("  %-20s %s\n", $sc, shortcode_exists($sc) ? 'OK' : '*** 缺失 ***');
}

echo "\n=== E. 后台菜单位置 ===\n";
wp_set_current_user(1);
if (!defined('WP_ADMIN')) {
    define('WP_ADMIN', true);
}
if (!function_exists('add_menu_page')) {
    require_once ABSPATH . 'wp-admin/includes/plugin.php';
}
$GLOBALS['menu']    = array();
$GLOBALS['submenu'] = array();
$GLOBALS['admin_page_hooks'] = array();
require_once ABSPATH . 'wp-admin/menu.php';
$seen = array();
foreach ($GLOBALS['menu'] as $position => $entry) {
    if (empty($entry[2])) {
        continue;
    }
    printf("  \$menu[%-6s] %-28s %s\n", $position, strip_tags($entry[0]), $entry[2]);
    $seen[] = $entry[2];
}
printf("  → sf_formula 出现在 \$menu 中: %s\n", in_array('edit.php?post_type=sf_formula', $seen, true) ? 'YES' : 'NO');

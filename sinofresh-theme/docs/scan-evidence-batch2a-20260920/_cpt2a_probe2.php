<?php
/* 批次 2A 第一步扫描探针 #2（只读·注册预演）。
   在**内存中**注册 sf_formula + 2 taxonomy，推导 WP 会生成的 rewrite 规则顺序，
   并逐条 preg_match 测试目标路径落到哪条规则 —— 全程不写 option、不写 DB。
   运行：php -d mysqli.default_socket=<run>/mysql/mysqld.sock tools/_cpt2a_probe2.php */

$ROOT = '/Users/meng/Local Sites/sinofresh/app/public';
require_once $ROOT . '/wp-load.php';

function sec($t) { echo "\n" . str_repeat('=', 78) . "\n== $t\n" . str_repeat('=', 78) . "\n"; }

/* ---------- A. 注册前：基线规则快照 ---------- */
sec('A. 注册前基线');
$wr = $GLOBALS['wp_rewrite'];
$before = $wr->rewrite_rules();
printf("注册前生成规则数 = %d\n", count($before));
printf("option rewrite_rules 条目数 = %d（生成前，落库态）\n",
    is_array(get_option('rewrite_rules')) ? count(get_option('rewrite_rules')) : -1);
printf("use_verbose_page_rules = %s\n", var_export($wr->use_verbose_page_rules, true));
printf("extra_permastructs(前) = %s\n", implode(', ', array_keys((array) $wr->extra_permastructs)));
printf("extra_rules_top(前) 条数 = %d\n", count((array) $wr->extra_rules_top));

/* ---------- B. 内存注册（与拟交付参数 1:1） ---------- */
sec('B. 内存注册 sf_formula（参数与拟交付一致）');
$args = array(
    'labels' => array('name' => 'Formulas', 'singular_name' => 'Formula'),
    'public' => true,
    'has_archive' => true,
    'menu_icon' => 'dashicons-clipboard',
    'menu_position' => 21,
    'supports' => array('title', 'editor', 'thumbnail', 'excerpt',
                        'revisions', 'page-attributes', 'custom-fields'),
    'taxonomies' => array('sf_formula_form', 'sf_formula_use'),
    'rewrite' => array('slug' => 'formulas', 'with_front' => false),
    'show_in_rest' => true,
    'hierarchical' => false,
);
$res = register_post_type('sf_formula', $args);
printf("register_post_type 返回 = %s\n", is_wp_error($res) ? 'WP_Error: ' . $res->get_error_message() : get_class($res));

register_taxonomy('sf_formula_form', 'sf_formula', array(
    'hierarchical' => false, 'public' => false, 'show_ui' => true,
    'show_in_rest' => true, 'rewrite' => false,
));
register_taxonomy('sf_formula_use', 'sf_formula', array(
    'hierarchical' => false, 'public' => false, 'show_ui' => true,
    'show_in_rest' => true, 'rewrite' => false,
));
printf("post_type_exists(sf_formula) = %s\n", var_export(post_type_exists('sf_formula'), true));
printf("taxonomy_exists(sf_formula_form) = %s / sf_formula_use = %s\n",
    var_export(taxonomy_exists('sf_formula_form'), true),
    var_export(taxonomy_exists('sf_formula_use'), true));
$reg = get_post_type_object('sf_formula');
printf("rewrite 参数 = %s\n", var_export($reg->rewrite, true));
printf("has_archive  = %s\n", var_export($reg->has_archive, true));
printf("query_var    = %s\n", var_export($reg->query_var, true));

/* ---------- C. 生成规则（不落盘） ---------- */
sec('C. 生成规则（rewrite_rules() 只生成不写库）');
$after = $wr->rewrite_rules();
printf("注册后生成规则数 = %d（增量 %+d）\n", count($after), count($after) - count($before));
printf("option rewrite_rules 条目数 = %d（应与注册前相同=未落盘）\n",
    is_array(get_option('rewrite_rules')) ? count(get_option('rewrite_rules')) : -1);
printf("extra_permastructs(后) = %s\n", implode(', ', array_keys((array) $wr->extra_permastructs)));

echo "\n--- 新增/变化的规则（与基线 diff）---\n";
$i = 0;
foreach ($after as $re => $q) {
    if (!array_key_exists($re, $before) || $before[$re] !== $q) {
        printf("  %-58s -> %s\n", $re, $q);
        $i++;
    }
}
printf("  （合计 %d 条新增/变化）\n", $i);

echo "\n--- formulas 相关规则及其在总表中的**序号位置** ---\n";
$pos = 0;
foreach ($after as $re => $q) {
    $pos++;
    if (strpos($re, 'formulas') !== false) {
        printf("  #%-4d %-56s -> %s\n", $pos, $re, $q);
    }
}

/* ---------- D. 路径解析预演 ---------- */
sec('D. 路径解析预演（按规则顺序逐条 preg_match，取首个命中）');
$tests = array(
    'formulas/liquid-joint-support/'          => '配方详情（应为 CPT single）',
    'formulas/'                               => 'CPT 归档',
    'formulas'                                => 'CPT 归档（无斜杠）',
    'formulas/page/2/'                        => 'CPT 归档分页',
    'formulas/feed/'                          => 'CPT 归档 feed',
    'products/soft-chews/'                    => '剂型页（应仍为 pagename）',
    'products/'                               => 'Products 页',
    'blog/'                                   => '博客页',
    'about/'                                  => '普通页',
    'zh/formulas/liquid-joint-support/'       => 'zh 站配方详情（TranslatePress 前缀）',
    '2019/01/01/'                             => '日期归档',
    'category/manufacturing/'                 => '分类归档',
);
foreach ($tests as $path => $label) {
    $matched = null; $k = 0;
    foreach ($after as $re => $q) {
        $k++;
        if (preg_match("#^$re#", $path, $m)) {
            $matched = array('rule' => $re, 'query' => $q, 'idx' => $k, 'm' => $m);
            break;
        }
    }
    if ($matched) {
        $q = $matched['query'];
        $q = preg_replace_callback('/\$matches\[(\d+)\]/', function ($mm) use ($matched) {
            return $matched['m'][(int) $mm[1]] ?? '?';
        }, $q);
        printf("  %-42s -> #%-4d %s\n", $path, $matched['idx'], $q);
        printf("  %-42s    (%s)\n", '', $label);
    } else {
        printf("  %-42s -> ** 无规则命中 ** (%s)\n", $path, $label);
    }
}

/* ---------- E. slug 冲突检查 ---------- */
sec('E. slug 冲突检查');
global $wpdb;
$cand = 'formulas';
printf("page  'formulas' => %s\n", get_page_by_path($cand) ? '** 冲突 **' : 'free');
$p = $wpdb->get_var($wpdb->prepare("SELECT ID FROM {$wpdb->posts} WHERE post_name=%s AND post_type='post' LIMIT 1", $cand));
printf("post  'formulas' => %s\n", $p ? "** 冲突 ** (ID $p)" : 'free');
$t = $wpdb->get_var($wpdb->prepare("SELECT term_id FROM {$wpdb->terms} WHERE slug=%s LIMIT 1", $cand));
printf("term  'formulas' => %s\n", $t ? "** 冲突 ** (term_id $t)" : 'free');

$dosage = array('soft-chews','tablets','powders','pastes','drops','liquids','fish-oil','dental-chews');
echo "\n  8 剂型页完整路径（get_page_by_path 需带父级）：\n";
foreach ($dosage as $s) {
    $o = get_page_by_path("products/$s");
    printf("    products/%-14s => %s\n", $s . '/', $o ? sprintf('ID %d  %s', $o->ID, get_permalink($o)) : '** 缺失 **');
}
echo "\n  拟用 taxonomy term slug 与剂型页 slug 是否同名（供 FORM_CRUMB 映射）：\n";
foreach ($dosage as $s) {
    printf("    term '%s' -> 页面 URL %s\n", $s, get_permalink(get_page_by_path("products/$s")));
}

/* ---------- F. 命名空间/函数名冲突 ---------- */
sec('F. 拟新增的 PHP 符号是否已被占用');
$syms = array('sinofresh_formula_grid', 'sinofresh_register_formula_cpt',
    'sinofresh_formula_form_label', 'sf_formula_grid', 'sf_formula',
    'sinofresh_formula_card_html');
foreach ($syms as $s) {
    printf("  %-34s function_exists=%-6s shortcode_exists=%s\n", $s,
        var_export(function_exists($s), true), var_export(shortcode_exists($s), true));
}
printf("  'sinofresh_template_placeholders' function_exists = %s\n",
    var_export(function_exists('sinofresh_template_placeholders'), true));

echo "\n" . str_repeat('=', 78) . "\n注册预演完成（只读，未写 DB）\n";

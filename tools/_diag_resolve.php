<?php
$root = getenv('HOME') . '/Local Sites/sinofresh/app/public';
$_SERVER['HTTP_HOST'] = 'sinofresh.local';
$_SERVER['REQUEST_URI'] = '/products/';
require $root . '/wp-load.php';
// 复刻 template-loader 的层次
$page = get_page_by_path('products');
global $wp_query;
$wp_query->init();
$wp_query->query(array('page' => '', 'pagename' => 'products'));
$wp_query->queried_object = $page;
$wp_query->queried_object_id = $page->ID;
add_filter('template_include', function($t) {
    echo "template_include -> {$t}\n";
    $h = [];
    // 打印 filter 传入时的层次信息
    return $t;
}, 999);
// 手动跑 template 层次
global $wp_filter;
remove_action('template_redirect', 'redirect_canonical');
$t = locate_template(array('page-products.php', 'page-products', 'page.php'), true, false, array('page-products', 'page-19', 'page', 'singular', 'index'));
echo "locate_template(带 hierarchy) -> {$t}\n";
// 直接问 get_block_templates
$gots = get_block_templates(array('slug__in' => array('page-products', 'page-19', 'page', 'singular', 'index')), 'wp_template');
echo "get_block_templates 命中: ";
foreach ($gots as $g) echo $g->id . "(wp_id=" . ($g->wp_id ?: '-') . ",source=" . ($g->source ?: '-') . ") ";
echo "\n";

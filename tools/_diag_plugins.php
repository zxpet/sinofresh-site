<?php
$root = getenv('HOME') . '/Local Sites/sinofresh/app/public';
require $root . '/wp-load.php';
$active = get_option('active_plugins');
echo "active_plugins: " . implode(', ', $active) . "\n";
$page = get_page_by_path('products');
echo "products 页 ID: " . ($page ? $page->ID : '?') . " | _wp_page_template: " . get_post_meta($page->ID, '_wp_page_template', true) . "\n";
// 页面内容本身是否含这段文字（用户可能改的是页面内容而非模板？不——记录是 wp_template）
echo "页面 post_content 长度: " . strlen($page->post_content) . "\n";

<?php
$root = getenv('HOME') . '/Local Sites/sinofresh/app/public';
require $root . '/wp-load.php';
global $wpdb;
foreach (array(77, 52, 66) as $id) {
  echo "=== ID=$id post_name=" . get_post_field('post_name', $id) . " status=" . get_post_field('post_status', $id) . " ===\n";
  $meta = $wpdb->get_results("SELECT meta_key, meta_value FROM {$wpdb->postmeta} WHERE post_id=$id");
  if (!$meta) echo "  (无 meta)\n";
  foreach ($meta as $m) echo "  {$m->meta_key} = " . substr($m->meta_value, 0, 60) . "\n";
}
// 主题当前 slug
echo "\n主题 slug: " . get_stylesheet() . " / template: " . get_template() . "\n";
// 模拟前台解析：products 页会解析到哪个模板
$templates = array('page-products', 'page-19', 'page', 'singular');
$resolve = resolve_block_template('page-products', $templates, '');
echo "resolve_block_template(page-products) -> id: " . $resolve->id . " | source: " . ($resolve->source ?: '(null)') . " | wp_id: " . ($resolve->wp_id ?: '-') . "\n";

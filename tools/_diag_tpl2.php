<?php
$root = getenv('HOME') . '/Local Sites/sinofresh/app/public';
require $root . '/wp-load.php';
$t = get_post(77);
if (!$t) { echo "ID 77 not found\n"; exit(1); }
echo "=== ID=77 详情 ===\n";
echo "post_type: {$t->post_type}\npost_status: {$t->post_status}\npost_name: {$t->post_name}\n";
echo "wp_theme 状态(theme/origin): " . (get_post_meta(77, 'wp_theme', true) ?: '(无)') . " / " . (get_post_meta(77, 'origin', true) ?: '(无 origin)') . "\n";
file_put_contents('/tmp/tpl77.html', $t->post_content);
echo "内容长度: " . strlen($t->post_content) . " 字节，已存 /tmp/tpl77.html\n";

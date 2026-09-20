<?php
// 只读诊断：wp_template 记录清单 + 最近修改时间
$root = getenv('HOME') . '/Local Sites/sinofresh/app/public';
require $root . '/wp-load.php';

global $wpdb;
$rows = $wpdb->get_results("
  SELECT ID, post_name, post_status, post_type, post_modified, post_author
  FROM {$wpdb->posts}
  WHERE post_type IN ('wp_template','wp_template_part')
  ORDER BY post_modified DESC
  LIMIT 20
");
echo "=== wp_template / wp_template_part 记录（按修改时间倒序）===\n";
foreach ($rows as $r) {
  printf("ID=%-4d name=%-40s status=%-8s modified=%s\n", $r->ID, $r->post_name, $r->post_status, $r->post_modified);
}
if (!count($rows)) echo "(无记录)\n";
// 回收站里也可能有
$trashed = $wpdb->get_results("
  SELECT ID, post_name, post_status, post_modified FROM {$wpdb->posts}
  WHERE post_type='wp_template' AND post_status='trash'
  ORDER BY post_modified DESC LIMIT 10
");
echo "\n=== 回收站中的 wp_template ===\n";
foreach ($trashed as $r) {
  printf("ID=%-4d name=%-40s modified=%s\n", $r->ID, $r->post_name, $r->post_modified);
}
if (!count($trashed)) echo "(无记录)\n";
// 主题文件 vs DB 修改时间参考
$f = get_stylesheet_directory() . '/templates/front-page.html';
echo "\nfront-page.html 文件 mtime: " . date('Y-m-d H:i:s', filemtime($f)) . "\n";

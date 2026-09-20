<?php
/* 批次 2A 扫描探针 #5b（只读）：后台菜单实际占位（动态）。
   避开 wp-admin/includes/admin.php 的 auth_redirect()：直接设当前用户后加载菜单构建器。
   运行：php -d mysqli.default_socket=<run>/mysql/mysqld.sock tools/_cpt2a_probe5b.php */

define('WP_ADMIN', true);
$ROOT = '/Users/meng/Local Sites/sinofresh/app/public';
require_once $ROOT . '/wp-load.php';
wp_set_current_user(1);

require_once ABSPATH . 'wp-admin/includes/menu.php';
require_once ABSPATH . 'wp-admin/menu.php';

function sec($t) { echo "\n" . str_repeat('=', 78) . "\n== $t\n" . str_repeat('=', 78) . "\n"; }

sec('A. 现有后台顶层菜单（按 WP 内部 position 排序）');
global $menu, $submenu;
printf("顶层菜单项数 = %d（含分隔符）\n\n", count($menu));
printf("  %-10s %-30s %-30s\n", 'pos', 'slug', 'title');
ksort($menu, SORT_STRING);
$slugs = array();
foreach ($menu as $k => $item) {
    if (empty($item[0])) { continue; }
    $slugs[] = $item[2];
    printf("  %-10s %-30s %-30s\n", $k, $item[2], substr(wp_strip_all_tags($item[0]), 0, 28));
}

sec('B. position 21 占用判定');
$hit = array();
foreach ($menu as $k => $item) {
    if (empty($item[0])) { continue; }
    if ((int) floor((float) $k) === 21) { $hit[] = wp_strip_all_tags($item[0]) . ' [' . $item[2] . ']'; }
}
printf("  position 21 现有项 = %s\n", $hit ? implode(' / ', $hit) : '** 空 → 可用 **');
echo "\n  邻近位置逐格占用：\n";
foreach (range(17, 27) as $want) {
    $h = array();
    foreach ($menu as $k => $item) {
        if (empty($item[0])) { continue; }
        if ((int) floor((float) $k) === $want) { $h[] = substr(wp_strip_all_tags($item[0]), 0, 20) . '[' . $item[2] . ']'; }
    }
    printf("    %-3d : %s\n", $want, $h ? implode(' | ', $h) : '(空)');
}

sec('C. 现有 CPT 菜单（plugin 注册）');
foreach ($menu as $k => $item) {
    if (empty($item[0])) { continue; }
    if (strpos($item[2], 'edit.php?post_type=') === 0) {
        printf("  pos %-8s %-30s %s\n", $k, $item[2], wp_strip_all_tags($item[0]));
    }
}

sec('D. 结论');
printf("  menu_position=21 → %s\n", $hit ? '** 冲突，需调整 **' : '可用（落在 Pages=20 之后）');
printf("  顶层 slug 列表 = %s\n", implode(', ', $slugs));
echo "\n" . str_repeat('=', 78) . "\n探针 #5b 完成（只读）\n";

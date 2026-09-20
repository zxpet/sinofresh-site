<?php
/* 批次 2A 扫描探针 #5（只读）：后台菜单实际占位（动态）。
   以 WP_ADMIN 上下文加载，取 $menu 的 position 排序，判断 21 是否与现有菜单冲突。
   运行：php -d mysqli.default_socket=<run>/mysql/mysqld.sock tools/_cpt2a_probe5.php */

define('WP_ADMIN', true);
$ROOT = '/Users/meng/Local Sites/sinofresh/app/public';
require_once $ROOT . '/wp-load.php';
require_once ABSPATH . 'wp-admin/includes/admin.php';

function sec($t) { echo "\n" . str_repeat('=', 78) . "\n== $t\n" . str_repeat('=', 78) . "\n"; }

sec('A. 现有后台顶层菜单（按显示顺序，含 WP 内部 position 值）');
require_once ABSPATH . 'wp-admin/menu.php';
global $menu;

printf("顶层菜单项数 = %d\n\n", count($menu));
printf("  %-6s %-28s %-34s %s\n", 'key', 'slug', 'title', '内部 position');
foreach ($menu as $k => $item) {
    if (empty($item[0])) { continue; }
    $title = wp_strip_all_tags($item[0]);
    printf("  %-6s %-28s %-34s %s\n", $k, $item[2], substr($title, 0, 32), $k);
}

sec('B. position=21 是否已被占用');
$pos21 = array();
foreach ($menu as $k => $item) {
    if (empty($item[0])) { continue; }
    // $menu 的键是可排序字符串，核心会把它格式化成 5 位小数；取整数部分比较
    $num = (float) $k;
    if (floor($num) == 21) { $pos21[] = sprintf('%s (%s)', wp_strip_all_tags($item[0]), $item[2]); }
}
printf("  position 21 现有项 = %s\n", $pos21 ? implode(' / ', $pos21) : '** 空，可用 **');

echo "\n  邻近位置占用情况：\n";
foreach (array(19, 20, 21, 22, 23, 24, 25, 26) as $want) {
    $hit = array();
    foreach ($menu as $k => $item) {
        if (empty($item[0])) { continue; }
        if (floor((float) $k) == $want) { $hit[] = wp_strip_all_tags($item[0]) . ' [' . $item[2] . ']'; }
    }
    printf("    %-4d : %s\n", $want, $hit ? implode(' | ', $hit) : '(空)');
}

sec('C. 子菜单：Products 相关（确认无重名）');
global $submenu;
foreach (array('edit.php?post_type=page', 'index.php', 'tools.php') as $parent) {
    if (!isset($submenu[$parent])) { continue; }
    echo "  $parent:\n";
    foreach ($submenu[$parent] as $sm) {
        printf("    %-40s %s\n", wp_strip_all_tags($sm[0]), $sm[2]);
    }
}

sec('D. 结论');
printf("  menu_position=21 → %s\n", $pos21 ? '** 与现有菜单冲突，需改 **' : '可用（紧邻 Pages=20 之后）');
echo "\n" . str_repeat('=', 78) . "\n探针 #5 完成（只读）\n";

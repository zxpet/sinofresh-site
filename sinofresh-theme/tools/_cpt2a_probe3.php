<?php
/* 批次 2A 扫描探针 #3（只读）：TranslatePress URL 机制 + 后台菜单占位 + 错误日志位置。
   运行：php -d mysqli.default_socket=<run>/mysql/mysqld.sock tools/_cpt2a_probe3.php */

$ROOT = '/Users/meng/Local Sites/sinofresh/app/public';
require_once $ROOT . '/wp-load.php';
function sec($t) { echo "\n" . str_repeat('=', 78) . "\n== $t\n" . str_repeat('=', 78) . "\n"; }

sec('A. trp_settings');
$s = get_option('trp_settings');
if (is_array($s)) {
    foreach ($s as $k => $v) {
        printf("  %-30s = %s\n", $k, is_scalar($v) ? var_export($v, true)
            : json_encode($v, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES));
    }
} else { printf("  ** 非数组：%s **\n", gettype($s)); }

sec('B. trp_advanced_settings');
$a = get_option('trp_advanced_settings');
if (is_array($a)) {
    foreach ($a as $k => $v) {
        printf("  %-34s = %s\n", $k, is_scalar($v) ? var_export($v, true)
            : json_encode($v, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES));
    }
} else { printf("  ** 非数组：%s **\n", gettype($a)); }

sec('C. 语言列表 / 机制判定');
foreach (array('trp_languages', 'trp_original_languages', 'WPLANG',
               'trp_plugin_version', 'trp_db_version') as $k) {
    $v = get_option($k);
    printf("  %-24s = %s\n", $k, is_scalar($v) ? var_export($v, true)
        : json_encode($v, JSON_UNESCAPED_SLASHES));
}
printf("  trp 是否存在类 TRP_Url_Converter = %s\n", var_export(class_exists('TRP_Url_Converter'), true));
printf("  home_url('/') = %s\n", home_url('/'));
printf("  get_option('home') = %s\n", get_option('home'));
printf("  强制语言到自定义链接(force-language-to-custom-links) 用值 = %s\n",
    var_export($s['force-language-to-custom-links'] ?? null, true));
printf("  add-subdirectory 用值 = %s ；相对 url 用值 = %s\n",
    var_export($s['add-subdirectory'] ?? null, true),
    var_export($s['url-slugs'] ?? null, true));

sec('D. 语言切换实际 URL（判定 /zh/ 是否为真路径）');
if (function_exists('trp_custom_language_switcher')) {
    echo "  trp_custom_language_switcher 可用\n";
}
$ls = get_posts(array('post_type' => 'language_switcher', 'numberposts' => -1,
                      'post_status' => 'any'));
printf("  language_switcher 记录数 = %d\n", count($ls));
foreach ($ls as $p) {
    printf("    ID %d slug=%s title=%s status=%s\n", $p->ID, $p->post_name, $p->post_title, $p->post_status);
    $meta = get_post_meta($p->ID);
    foreach ($meta as $mk => $mv) {
        printf("      meta %-28s = %s\n", $mk, is_scalar($mv[0] ?? '') ? substr(var_export($mv[0] ?? '', true), 0, 90) : '(complex)');
    }
}

sec('E. 后台菜单位置占位（静态：扫活跃插件声明的 position）');
$active = get_option('active_plugins');
printf("活跃插件 %d 个：\n", count($active));
foreach ($active as $pl) { printf("  - %s\n", $pl); }
$plug_dir = $ROOT . '/wp-content/plugins';
foreach ($active as $pl) {
    $f = $plug_dir . '/' . $pl;
    if (!file_exists($f)) { continue; }
    $src = file_get_contents($f);
    // 找 add_menu_page( ... , <position> )
    if (preg_match_all('/add_menu_page\s*\((.*?)\)\s*;/s', $src, $m)) {
        foreach ($m[1] as $call) {
            $parts = preg_split('/,(?![^()]*\))/', $call);
            $pos = trim(end($parts));
            if (preg_match('/^[0-9]+(\.[0-9]+)?$/', $pos)) {
                printf("  %-60s menu_position=%s\n", basename(dirname($pl)) . '/' . basename($pl), $pos);
            }
        }
    }
    if (preg_match_all('/add_menu_page\s*\((.*?)\)\s*;/s', $src, $m)) {
        foreach ($m[1] as $call) {
            if (strpos($call, 'position') !== false || preg_match('/\b\d{2}\b/', $call)) {
                printf("    [raw] %s\n", preg_replace('/\s+/', ' ', substr($call, 0, 150)));
            }
        }
    }
}
printf("  （参考）WP 核心占用：2 仪表盘 / 4 分隔 / 5 文章 / 10 媒体 / 20 页面 / 25 评论 / 60 外观 / 65 插件 / 70 用户 / 75 工具 / 80 设置 / 99 分隔\n");

sec('F. 错误日志位置');
$cands = array(
    WP_CONTENT_DIR . '/debug.log',
    $ROOT . '/debug.log',
    dirname($ROOT) . '/logs/php/error.log',
    dirname($ROOT) . '/logs/nginx/error.log',
    ini_get('error_log'),
);
foreach ($cands as $f) {
    if (!$f) { printf("  (空) => n/a\n"); continue; }
    printf("  %-62s => %s\n", $f, file_exists($f)
        ? sprintf('存在 %d B, mtime %s', filesize($f), date('Y-m-d H:i:s', filemtime($f)))
        : '不存在');
}
printf("\n  php.ini 相关：\n");
foreach (array('error_log', 'log_errors', 'display_errors', 'error_reporting') as $k) {
    printf("    %-18s = %s\n", $k, var_export(ini_get($k), true));
}
$logsdir = dirname($ROOT) . '/logs';
printf("\n  %s 目录内容 = %s\n", $logsdir, is_dir($logsdir) ? implode(', ', array_slice(scandir($logsdir), 2)) : '不存在');

sec('G. 现有 sf-formulas 区块 / 模板行号（复核扫描报告）');
foreach (array('soft-chews', 'tablets', 'liquids') as $slug) {
    $f = get_stylesheet_directory() . "/templates/page-$slug.html";
    $lines = file($f);
    foreach ($lines as $i => $ln) {
        if (strpos($ln, 'id="formulas"') !== false) {
            printf("  page-%-14s 第 %d 行含 id=\"formulas\"\n", $slug . '.html', $i + 1);
        }
    }
}
echo "\n" . str_repeat('=', 78) . "\n探针 #3 完成（只读）\n";

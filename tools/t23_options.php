<?php
/**
 * 任务 2.3 附带：burst_* option 清理（用 wp_delete_option）
 * 用法: php -d mysqli.default_socket=<sock> tools/t23_options.php [list|delete|verify]
 */
$sock = getenv('SF_SOCK');
if ($sock) { ini_set('mysqli.default_socket', $sock); }

require '/Users/meng/Local Sites/sinofresh/app/public/wp-load.php';
/*
 * ★ 重要事实（本环境实测，WP 7.1.1）：
 *   wp_delete_option() 在全安装中**不存在**——它是旧的 multisite 专用函数，
 *   定义文件 wp-admin/includes/option.php 已从核心移除（现存的是 options.php 复数，与 option API 无关）。
 *   单站点下等价且始终可用的官方 API 是 delete_option()（wp-includes/option.php，由 wp-settings.php 加载）。
 */

global $wpdb;
$act = isset($argv[1]) ? $argv[1] : 'verify';

function burst_rows() {
    global $wpdb;
    return $wpdb->get_results(
        "SELECT option_id, option_name, LENGTH(option_value) AS len, autoload
         FROM {$wpdb->options} WHERE option_name LIKE '%burst%' ORDER BY option_id"
    );
}

function dump_rows($rows, $title) {
    echo $title . ' : ' . count($rows) . " 条\n";
    $sum = 0;
    foreach ($rows as $r) {
        $sum += (int) $r->len;
        printf("  %6d  %-48s len=%-5d %s\n", $r->option_id, $r->option_name, $r->len, $r->autoload);
    }
    echo "  option_value 合计 " . number_format($sum) . " 字符\n";
}

if ($act === 'list' || $act === 'verify') {
    dump_rows(burst_rows(), $act === 'list' ? '=== 当前 burst_* option ===' : '=== 核验：剩余 burst_* option ===');
    if ($act === 'verify') {
        $n = (int) $wpdb->get_var("SELECT COUNT(*) FROM {$wpdb->options} WHERE option_name LIKE '%burst%'");
        echo $n === 0 ? "  ✅ 已清零\n" : "  ❌ 仍剩 {$n} 条\n";
    }
}

if ($act === 'delete') {
    $rows = burst_rows();
    dump_rows($rows, '=== 删除前 burst_* option ===');
    if (!$rows) { echo "无需删除\n"; exit(0); }

    $ok = 0; $fail = [];
    foreach ($rows as $r) {
        $res = delete_option($r->option_name);
        if ($res === true || $res === 1) { $ok++; printf("  DEL %-48s ✅\n", $r->option_name); }
        else { $fail[] = $r->option_name; printf("  DEL %-48s ❌ (%s)\n", $r->option_name, var_export($res, true)); }
    }
    wp_cache_flush();
    echo "\n删除成功 {$ok}/" . count($rows) . ($fail ? '  失败: ' . implode(', ', $fail) : '') . "\n";

    $left = burst_rows();
    dump_rows($left, "\n=== 删除后复查 === ");
    echo count($left) === 0 ? "  ✅ 31 条已全部清空\n" : "  ❌ 仍有残留\n";
}

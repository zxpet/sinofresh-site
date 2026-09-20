<?php
/* 批次 2A 扫描探针 #4（只读）：TP 完整设置面 + 基线快照（文件哈希 / 日志 / rewrite 选项）。
   运行：php -d mysqli.default_socket=<run>/mysql/mysqld.sock tools/_cpt2a_probe4.php */

$ROOT = '/Users/meng/Local Sites/sinofresh/app/public';
$SRC  = '/Users/meng/WorkBuddy/sinofresh外贸网站建设/sinofresh-theme';
require_once $ROOT . '/wp-load.php';
function sec($t) { echo "\n" . str_repeat('=', 78) . "\n== $t\n" . str_repeat('=', 78) . "\n"; }

sec('A. 全部 trp_* option');
global $wpdb;
$rows = $wpdb->get_results(
    "SELECT option_name, LENGTH(option_value) AS len FROM {$wpdb->options}
     WHERE option_name LIKE 'trp%' ORDER BY option_name");
printf("trp* option 数 = %d\n", count($rows));
foreach ($rows as $r) { printf("  %-46s %8s B\n", $r->option_name, $r->len); }

sec('B. 与 CPT 相关的 TP 设置项（明确存在性）');
$s = get_option('trp_settings');
foreach (array('trp-post-types', 'trp-post-type-slugs', 'post-types',
               'trp_custom_post_types', 'translation-languages',
               'url-slugs', 'add-subdirectory-to-default-language') as $k) {
    printf("  trp_settings[%-36s] = %s\n", $k,
        array_key_exists($k, (array) $s) ? json_encode($s[$k], JSON_UNESCAPED_SLASHES) : '** 不存在 **');
}
printf("  option 'trp_post_type_base_slug_translation' = %s\n",
    json_encode(get_option('trp_post_type_base_slug_translation'), JSON_UNESCAPED_SLASHES));
printf("  option 'trp_taxonomy_slug_translation'      = %s\n",
    json_encode(get_option('trp_taxonomy_slug_translation'), JSON_UNESCAPED_SLASHES));
printf("  option 'trp_slug_originals'                 存在=%s\n",
    var_export(false !== get_option('trp_slug_originals'), true));

sec('C. wp_trp_* 数据表');
$tabs = $wpdb->get_col("SHOW TABLES LIKE '{$wpdb->prefix}trp_%'");
printf("wp_trp_* 表数 = %d\n", count($tabs));
foreach ($tabs as $t) {
    $n = $wpdb->get_var("SELECT COUNT(*) FROM `$t`");
    printf("  %-46s %6s 行  (COUNT(*))\n", $t, $n);
}
// slug 相关表内容
foreach (array('trp_slug_originals', 'trp_slug_translations', 'trp_post_type_base_slug_translation') as $t) {
    $full = $wpdb->prefix . $t;
    if (in_array($full, $tabs, true)) {
        $rs = $wpdb->get_results("SELECT * FROM `$full` LIMIT 8", ARRAY_A);
        printf("\n  --- %s 前 8 行 ---\n", $full);
        if (!$rs) { echo "    (空表)\n"; }
        foreach ($rs as $r) { printf("    %s\n", json_encode($r, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES)); }
    }
}

sec('D. 基线：将改动的文件（sha256 / 体积）');
foreach (array('functions.php', 'style.css', 'theme.json') as $f) {
    $p = $SRC . '/' . $f;
    printf("  %-16s %10s B  %s\n", $f, filesize($p), hash_file('sha256', $p));
}
// 与 Local 副本比对
$dst = $ROOT . '/wp-content/themes/sinofresh-theme';
foreach (array('functions.php', 'style.css', 'theme.json') as $f) {
    printf("  %-16s 源码==Local : %s\n", $f,
        (hash_file('sha256', $SRC . '/' . $f) === hash_file('sha256', $dst . '/' . $f)) ? '是' : '** 否 **');
}

sec('E. 基线：rewrite_rules 选项');
$rr = get_option('rewrite_rules');
printf("  rewrite_rules 条目数 = %d\n", is_array($rr) ? count($rr) : -1);
printf("  rewrite_rules sha256 = %s\n", hash('sha256', serialize($rr)));

sec('F. 基线：日志（PHP Web / nginx / wp-content debug）');
$logs = array(
    '/Users/meng/Local Sites/sinofresh/logs/php/error.log'   => 'PHP-FPM error_log（Web 请求的真实日志）',
    '/Users/meng/Local Sites/sinofresh/logs/php/php-fpm.log' => 'PHP-FPM 主日志',
    '/Users/meng/Local Sites/sinofresh/logs/nginx/error.log' => 'nginx 错误日志',
    $ROOT . '/wp-content/debug.log'                          => 'wp-content/debug.log（CLI 残留，非 Web 日志）',
);
foreach ($logs as $f => $desc) {
    if (file_exists($f)) {
        printf("  %-66s %8s B  %s\n", $f, filesize($f), hash('sha256', substr(file_get_contents($f), -4096)));
        printf("  %-66s   mtime %s  | %s\n", '', date('Y-m-d H:i:s', filemtime($f)), $desc);
    } else {
        printf("  %-66s 不存在  | %s\n", $f, $desc);
    }
}

sec('G. 基线：8 剂型页 HTTP 状态（改动前）');
$urls = array();
foreach (array('soft-chews','tablets','powders','pastes','drops','liquids','fish-oil','dental-chews') as $s) {
    $urls["http://sinofresh.local/products/$s/"] = $s;
}
$urls['http://sinofresh.local/']            = 'front';
$urls['http://sinofresh.local/blog/']       = 'blog';
$urls['http://sinofresh.local/legend-blog/']= '(占位)';
foreach ($urls as $u => $label) {
    $ch = curl_init($u);
    curl_setopt_array($ch, array(CURLOPT_RETURNTRANSFER => true, CURLOPT_NOBODY => true,
        CURLOPT_FOLLOWLOCATION => true, CURLOPT_TIMEOUT => 12));
    curl_exec($ch);
    printf("  %-52s %s  (%s)\n", $u, curl_getinfo($ch, CURLINFO_HTTP_CODE), $label);
    curl_close($ch);
}

echo "\n" . str_repeat('=', 78) . "\n探针 #4 完成（只读）\n";

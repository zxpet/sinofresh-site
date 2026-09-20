<?php
/**
 * 诊断：为什么 wp_delete_option 致命错误
 * 用法: php -d mysqli.default_socket=<sock> tools/t23_diag.php
 */
define('WP_DISABLE_FATAL_ERROR_HANDLER', true);
define('WP_DEBUG', true);
define('WP_DEBUG_DISPLAY', true);
ini_set('display_errors', '1');
error_reporting(E_ALL);

$sock = getenv('SF_SOCK');
if ($sock) { ini_set('mysqli.default_socket', $sock); }

require '/Users/meng/Local Sites/sinofresh/app/public/wp-load.php';

global $wpdb;
echo "WP_DEBUG_DISPLAY=" . var_export(WP_DEBUG_DISPLAY, true) . "\n";
echo "wp_using_ext_object_cache=" . var_export(wp_using_ext_object_cache(), true) . "\n";
echo "wp_cache_flush 可调用: " . (function_exists('wp_cache_flush') ? 'yes' : 'no') . "\n";

// 钩子检查：谁挂在 deleted_option 上
global $wp_filter;
foreach (['deleted_option', 'delete_option', 'delete_option_burst_run_activation'] as $h) {
    if (isset($wp_filter[$h])) {
        echo "hook {$h}: " . count($wp_filter[$h]->callbacks) . " 个回调\n";
        foreach ($wp_filter[$h]->callbacks as $pri => $cbs) {
            foreach ($cbs as $id => $cb) {
                $f = $cb['function'];
                $nm = is_string($f) ? $f : (is_array($f) ? (is_object($f[0]) ? get_class($f[0]) : (string) $f[0]) . '::' . $f[1] : (is_object($f) ? get_class($f) : 'closure'));
                echo "   [{$pri}] {$nm}\n";
            }
        }
    } else {
        echo "hook {$h}: 无\n";
    }
}

// 捕获真实致命错误
register_shutdown_function(function () {
    $e = error_get_last();
    echo "\n=== SHUTDOWN ===\n";
    echo 'error_get_last: ' . json_encode($e, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE) . "\n";
});
set_error_handler(function ($no, $str, $file, $line) {
    echo "\n=== PHP NOTICE/WARNING ===\n";
    echo "  [{$no}] {$str}  @ {$file}:{$line}\n";
    return false;
});

// 单个 option 试删
$target = 'burst_run_activation';
$before = $wpdb->get_var($wpdb->prepare("SELECT COUNT(*) FROM {$wpdb->options} WHERE option_name=%s", $target));
echo "\n删除前 {$target} 存在数 = {$before}\n";
echo "调用 wp_delete_option ...\n";
$res = wp_delete_option($target);
echo "返回: " . var_export($res, true) . "\n";
$after = $wpdb->get_var($wpdb->prepare("SELECT COUNT(*) FROM {$wpdb->options} WHERE option_name=%s", $target));
echo "删除后存在数 = {$after}\n";
echo "DONE\n";

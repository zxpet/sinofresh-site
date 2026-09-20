<?php
// 一次性诊断：定位 '%' 被替换成 {sha256} 的确切层级。结果写文件，绕开任何输出层。
$ROOT = getenv('SF_ROOT') ?: ($_SERVER['HOME'] . '/Local Sites/sinofresh/app/public');
require $ROOT . '/wp-load.php';
global $wpdb;

$db_val = $wpdb->get_var("SELECT original FROM wp_trp_gettext_original_strings WHERE id=1096");

$out = [];
$out['php']              = PHP_VERSION;
$out['db_val']           = $db_val;
$out['db_val_hex']       = bin2hex((string) $db_val);
$out['plain']            = '%s Pageviews';
$out['esc_sql_dbval']    = esc_sql($db_val);
$out['real_escape_dbval']= $wpdb->_real_escape($db_val);
$out['escape_dbval']     = $wpdb->_escape($db_val);
$out['esc_sql_plain']    = esc_sql('%s Pageviews');
$out['real_escape_plain']= $wpdb->_real_escape('%s Pageviews');
$out['mysqli_plain']     = mysqli_real_escape_string($wpdb->dbh, '%s Pageviews');
$out['prepare_1arg']     = $wpdb->prepare('SELECT 1');
$out['prepare_s']        = $wpdb->prepare('SELECT %s', '%s Pageviews');
$out['percent_only']     = esc_sql('100% sure');

// 反射：_escape / esc_sql 的定义位置
$r1 = new ReflectionMethod($wpdb, '_escape');
$out['_escape_def'] = $r1->getFileName() . ':' . $r1->getStartLine();
$f = new ReflectionFunction('esc_sql');
$out['esc_sql_def'] = $f->getFileName() . ':' . $f->getStartLine();
$out['db_php_exists'] = file_exists(WP_CONTENT_DIR . '/db.php');
$out['db_php_class']  = $out['db_php_exists'] ? 'yes' : 'no';
$out['dropins'] = array_values(array_filter(scandir(WP_CONTENT_DIR), fn($x) => preg_match('/^(db|object-cache|advanced-cache)\.php$/', $x)));

file_put_contents('/tmp/t245_probe.json',
    json_encode($out, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES));
echo "written\n";

<?php
/**
 * 任务 2.4.2 恢复性验证：证明 rollback-cron.sql 真能把 cron option 还原到清理前状态。
 *
 * 做法（与 2.4.1 的「导入临时库再比对」同构）：
 *   ① 用 SHOW CREATE TABLE 取 wp_options 真实 DDL → 建临时库 sf_restore_chk 并建表
 *   ② 在临时库内写入**清理后**的 cron 值
 *   ③ 执行 rollback-cron.sql（就是那个 UPDATE 语句）
 *   ④ 读回 → 反序列化 → json_encode，与备份的 cron-option-pre.json 逐字节比对
 *   ⑤ 无论成败都 DROP 临时库
 *
 * 用法: php t242_restore.php
 */

$ROOT = getenv('SF_ROOT') ?: ($_SERVER['HOME'] . '/Local Sites/sinofresh/app/public');
require $ROOT . '/wp-load.php';

const CRON_DIR = '/Users/meng/WorkBuddy/sinofresh外贸网站建设/_backup/img-cleanup-20260920-062700/db-burst/cron';
const PRE_JSON = CRON_DIR . '/cron-option-pre.json';
const ROLLBACK = CRON_DIR . '/rollback-cron.sql';
const TMPDB    = 'sf_restore_chk';

global $wpdb;

$socket = ini_get('mysqli.default_socket');
printf("== 任务 2.4.2 恢复性验证 ==\n临时库=%s  socket=%s\n\n", TMPDB, $socket ?: '(php.ini 未设)');

$post_raw = (string) $wpdb->get_var("SELECT option_value FROM {$wpdb->options} WHERE option_name = 'cron'");
$pre_json = trim(file_get_contents(PRE_JSON));
$sql      = trim(file_get_contents(ROLLBACK));
printf("清理后 cron 串: %s B | 备份 pre.json: %s B | 回滚 SQL: %s B\n\n",
    number_format(strlen($post_raw)), number_format(strlen($pre_json)), number_format(strlen($sql)));

$ddl = $wpdb->get_var("SHOW CREATE TABLE {$wpdb->options}", 1);
if (!$ddl) { exit("❌ 无法取得 wp_options DDL\n"); }
$ddl = preg_replace('/\s*AUTO_INCREMENT=\d+/', '', $ddl);

$my = new mysqli('localhost', DB_USER, DB_PASSWORD, '', null, $socket);
if ($my->connect_errno) { exit("❌ 临时连接失败: {$my->connect_error}\n"); }
$my->set_charset('utf8mb4');

$fails = [];
$closed = false;
$cleanup = function () use ($my, &$closed) { if (!$closed) { @$my->query('DROP DATABASE IF EXISTS ' . TMPDB); } };
register_shutdown_function($cleanup);

$my->query('DROP DATABASE IF EXISTS ' . TMPDB);
$my->query('CREATE DATABASE ' . TMPDB);
$my->select_db(TMPDB);
printf("① 临时库已建，DDL 建表: %s\n", $my->query($ddl) ? '✅' : '❌ ' . $my->error);

// ② 灌入清理后的值（模拟「已被清理」的现状）
$stmt = $my->prepare('INSERT INTO ' . $wpdb->options . ' (option_name, option_value, autoload) VALUES (?, ?, ?)');
$stmt->bind_param('sss', $n, $post_raw, $a);
$n = 'cron'; $a = 'on';
printf("② 写入清理后的 cron 值: %s\n", $stmt->execute() ? '✅' : '❌ ' . $stmt->error) ;
$stmt->close();

// ③ 执行回滚 SQL
$ok = $my->multi_query($sql);
while ($my->more_results() && $my->next_result()) { /* 排空 */ }
printf("③ 执行 %s: %s%s\n", basename(ROLLBACK), $ok ? '✅' : '❌', $my->error ? ' ' . $my->error : '');

// ④ 读回比对
$back = $my->query("SELECT option_value FROM " . $wpdb->options . " WHERE option_name='cron'")->fetch_row()[0] ?? null;
if ($back === null) { exit("❌ 回滚后取不到 cron 值\n"); }
$restored_json = json_encode(unserialize($back));
printf("④ 读回 cron 串: %s B（应等于备份的 %s B）\n", number_format(strlen($back)), number_format(strlen($post_raw) < 1 ? 0 : strlen(file_get_contents(CRON_DIR . '/cron-option-raw.txt'))));
printf("   规范化 sha256 比对: %s\n",
    hash('sha256', $back) === hash('sha256', file_get_contents(CRON_DIR . '/cron-option-raw.txt'))
        ? '与备份原始串**逐字节相同** ✅' : '❌ 与备份原始串不同');

$eq = ($restored_json === $pre_json);
printf("   结构 json 比对 vs cron-option-pre.json: %s\n", $eq ? '完全一致 ✅' : '❌ 有差异');

if (!$eq) {
    $a1 = json_decode($pre_json, true); $a2 = json_decode($restored_json, true);
    printf("   备份 hook 数 %d / 还原后 hook 数 %d\n",
        count(array_filter(array_keys($a1), fn($k) => !is_int($k))) + 0, 0);
    // 逐桶 diff
    foreach (array_unique(array_merge(array_keys($a1), array_keys($a2))) as $k) {
        if (!isset($a1[$k]) || !isset($a2[$k]) || $a1[$k] !== $a2[$k]) { printf("   差异键: %s\n", $k); }
    }
    $fails[] = 'json 不一致';
}

// ⑤ 清理
$my->query('DROP DATABASE IF EXISTS ' . TMPDB);
printf("\n⑤ 临时库 %s 已删除: %s\n", TMPDB,
    $my->query("SELECT SCHEMA_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME='" . TMPDB . "'")->num_rows === 0 ? '✅' : '❌');
$closed = true;
$my->close();

printf("\n结论: 备份可恢复性 %s\n", $fails ? '❌ 未通过 → ' . implode('; ', $fails) : '✅ 通过（rollback-cron.sql 可完整还原清理前 cron）');
exit($fails ? 1 : 0);

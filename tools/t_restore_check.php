<?php
/**
 * 通用「option 行改动」恢复性验证（2.4.2 提炼，2.4.3 / 2.4.5 复用）
 *
 * 证明备份里的 rollback SQL 真能把某个 option 还原到改动前状态。
 * 步骤（与 DDL 版「导入临时库逐表 COUNT 比对」同构）：
 *   ① 取 wp_options 真实 DDL（剔 AUTO_INCREMENT）→ 建临时库并建表
 *   ② 灌入**改动后**的值（模拟现状）
 *   ③ **真的执行** rollback SQL
 *   ④ 读回：与备份原始串比 sha256（字节级）＋ 与结构快照比 json（语义级）
 *   ⑤ 无论成败都 DROP 临时库
 *
 * 用法:
 *   php t_restore_check.php --option=<name> --raw=<file> --pre=<file> --rollback=<file> [--tmpdb=<name>]
 */

$ROOT = getenv('SF_ROOT') ?: ($_SERVER['HOME'] . '/Local Sites/sinofresh/app/public');
require $ROOT . '/wp-load.php';

$opt = [];
foreach (array_slice($argv, 1) as $a) {
    if (preg_match('/^--([a-z_]+)=(.*)$/s', $a, $m)) { $opt[$m[1]] = $m[2]; }
}
foreach (['option', 'raw', 'pre', 'rollback'] as $k) {
    if (!isset($opt[$k])) { exit("❌ 缺少 --$k\n"); }
}
$TMPDB = $opt['tmpdb'] ?? 'sf_restore_chk';

global $wpdb;
$socket = ini_get('mysqli.default_socket');
printf("== 恢复性验证（option 行）==\noption=%s  临时库=%s  socket=%s\n\n", $opt['option'], $TMPDB, $socket ?: '(未设)');

$post_raw = $wpdb->get_var($wpdb->prepare(
    "SELECT option_value FROM {$wpdb->options} WHERE option_name = %s", $opt['option']));
if ($post_raw === null) { exit("❌ 现网取不到 " . $opt['option'] . "\n"); }
$bak_raw  = file_get_contents($opt['raw']);
$pre_json = trim(file_get_contents($opt['pre']));
$sql      = trim(file_get_contents($opt['rollback']));

printf("现网（改动后）%s B | 备份原始串 %s B | 结构快照 %s B | 回滚 SQL %s B\n\n",
    number_format(strlen($post_raw)), number_format(strlen($bak_raw)),
    number_format(strlen($pre_json)), number_format(strlen($sql)));

$ddl = $wpdb->get_var("SHOW CREATE TABLE {$wpdb->options}", 1);
if (!$ddl) { exit("❌ 无法取得 wp_options DDL\n"); }
$ddl = preg_replace('/\s*AUTO_INCREMENT=\d+/', '', $ddl);

$my = new mysqli('localhost', DB_USER, DB_PASSWORD, '', null, $socket);
if ($my->connect_errno) { exit("❌ 临时连接失败: {$my->connect_error}\n"); }
$my->set_charset('utf8mb4');
$fails = []; $closed = false;
register_shutdown_function(function () use ($my, &$closed, $TMPDB) {
    if (!$closed) { @$my->query('DROP DATABASE IF EXISTS ' . $TMPDB); }
});

$my->query('DROP DATABASE IF EXISTS ' . $TMPDB);
$my->query('CREATE DATABASE ' . $TMPDB);
$my->select_db($TMPDB);
printf("① 临时库建表: %s\n", $my->query($ddl) ? '✅' : '❌ ' . $my->error);

$stmt = $my->prepare('INSERT INTO ' . $wpdb->options . ' (option_name, option_value, autoload) VALUES (?, ?, ?)');
$stmt->bind_param('sss', $n, $post_raw, $a);
$n = $opt['option']; $a = 'on';
printf("② 写入改动后的值: %s\n", $stmt->execute() ? '✅' : '❌ ' . $stmt->error);
$stmt->close();

$ok = $my->multi_query($sql);
while ($my->more_results() && $my->next_result()) { /* 排空 */ }
printf("③ 执行 %s: %s%s\n", basename($opt['rollback']), $ok ? '✅' : '❌', $my->error ? ' ' . $my->error : '');

$back = $my->query('SELECT option_value FROM ' . $wpdb->options . " WHERE option_name='" . $my->real_escape_string($opt['option']) . "'")->fetch_row()[0] ?? null;
if ($back === null) { $fails[] = '回滚后取不到值'; }
else {
    $byte_eq = hash('sha256', $back) === hash('sha256', $bak_raw);
    printf("④ 读回 %s B | 与备份原始串逐字节相同: %s\n", number_format(strlen($back)), $byte_eq ? '✅' : '❌');
    $sem_eq = (json_encode(unserialize($back)) === $pre_json);
    printf("   与结构快照 deep-equal: %s\n", $sem_eq ? '✅' : '❌');
    if (!$byte_eq) { $fails[] = '字节不一致'; }
    if (!$sem_eq)  { $fails[] = '语义不一致'; }
}

printf("⑤ 临时库删除: %s\n", ($my->query('DROP DATABASE IF EXISTS ' . $TMPDB)
    && $my->query("SELECT SCHEMA_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME='" . $TMPDB . "'")->num_rows === 0) ? '✅' : '❌');
$closed = true; $my->close();

printf("\n结论: 备份可恢复性 %s\n", $fails ? '❌ 未通过 → ' . implode('; ', $fails) : '✅ 通过');
exit($fails ? 1 : 0);

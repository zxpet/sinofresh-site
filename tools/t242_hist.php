<?php
/**
 * 2.4.2 取证：从历史全库 dump 中解读 cron，解释「7 个 → 4 个」的原因。
 * 只读（除可选写出提取到的原始串到 restore_dir 外，不写任何东西）。
 *
 * mysqldump 的字面量会转义 \' \" \\ \n \r 等，且默认 --extended-insert 会把多行
 * 合并在同一条 INSERT 上（元组以 ),( 分隔）—— 故必须按字符逐位解引号，
 * 不能用正则截取（会跨元组）。
 *
 * 用法: php t242_hist.php <dump.sql> [restore_dir]
 */
$f = $argv[1] ?? '';
$restore_dir = $argv[2] ?? '';
if (!is_readable($f)) { exit("不可读: $f\n"); }

// wp-load 只为拿到 wp_get_schedules()（验证 burst 自定义周期是否已随插件消失）
$ROOT = getenv('SF_ROOT') ?: ($_SERVER['HOME'] . '/Local Sites/sinofresh/app/public');
if (is_readable($ROOT . '/wp-load.php')) { require $ROOT . '/wp-load.php'; }

$UNESC = ["'" => "'", '"' => '"', '\\' => '\\', 'n' => "\n", 'r' => "\r",
          't' => "\t", '0' => "\0", 'Z' => "\x1a", 'b' => "\x08", '%' => '\\%', '_' => '\\_'];

$raw = null;
$fh = fopen($f, 'r');
while (($line = fgets($fh)) !== false) {
    $p = strpos($line, ",'cron',");
    if ($p === false) { continue; }
    $i = $p + strlen(",'cron',");
    if ($line[$i] !== "'") { continue; }
    $len = strlen($line); $out = ''; $j = $i + 1; $closed = false;
    while ($j < $len) {
        $c = $line[$j];
        if ($c === '\\') { $n = $line[$j + 1] ?? ''; $out .= $UNESC[$n] ?? $n; $j += 2; continue; }
        if ($c === "'") { $closed = true; break; }
        $out .= $c; $j++;
    }
    if (!$closed) { continue; }
    $raw = $out;
    break;
}
fclose($fh);
if ($raw === null) { exit("未找到 cron 行\n"); }

$crons = @unserialize($raw);
if (!is_array($crons)) { exit("反序列化失败（长度 " . strlen($raw) . "）\n"); }

if ($restore_dir) {
    if (!is_dir($restore_dir)) { mkdir($restore_dir, 0755, true); }
    $dst = rtrim($restore_dir, '/') . '/cron-option-raw.txt';
    file_put_contents($dst, $raw);
    printf("已写出历史原始序列化串 %s B → %s\n", number_format(strlen($raw)), $dst);
}

$now = time();
printf("dump: %s\n", basename($f));
printf("cron 串长度 %s B | 现在 %s UTC\n\n", number_format(strlen($raw)), gmdate('Y-m-d H:i:s', $now));
$n = 0; ksort($crons);
foreach ($crons as $ts => $bucket) {
    if (!is_int($ts) || !is_array($bucket)) { continue; }
    foreach ($bucket as $hook => $events) {
        if (strpos((string) $hook, 'burst') !== 0) { continue; }
        foreach ($events as $sig => $ev) {
            $n++;
            printf("  %-26s @ %s %s  schedule=%-18s interval=%s args=%s\n",
                $hook, gmdate('Y-m-d H:i:s', (int) $ts), $ts < $now ? '【已过期】' : '        ',
                var_export($ev['schedule'] ?? null, true), var_export($ev['interval'] ?? null, true),
                json_encode($ev['args'] ?? null));
        }
    }
}
printf("\nburst 事件合计 %d 个\n", $n);
printf("hook 字符串在序列化串中的出现次数（grep 口径，会重复计数）: %s\n",
    implode(', ', array_map(fn($h) => $h . '×' . substr_count($raw, $h),
        ['burst_daily', 'burst_weekly', 'burst_monthly', 'burst_tour_reminder_cron'])));
printf("→ 循环事件的 hook 名在串中出现两次（键 + schedule 值），故 grep 口径会把 %d 个事件数成 %d\n",
    $n, array_sum(array_map(fn($h) => substr_count($raw, $h),
        ['burst_daily', 'burst_weekly', 'burst_monthly', 'burst_tour_reminder_cron'])));
printf("当前 wp_get_schedules() 是否含 burst_daily/weekly/monthly: %s\n",
    function_exists('wp_get_schedules')
        ? (implode(', ', array_intersect(['burst_daily', 'burst_weekly', 'burst_monthly'], array_keys(wp_get_schedules()))) ?: '否（已随插件卸载消失）')
        : '未加载 WP 环境');

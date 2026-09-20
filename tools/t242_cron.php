<?php
/**
 * 任务 2.4.2：清理 cron option 中的 burst 孤儿事件
 *
 * 背景：burst-statistics 插件已卸载（2026-09-19，见 wp_wpml_mails mail_id 404），
 *       但其注册的 cron 事件仍残留在 `cron` option 中，每次 wp-cron 触发都会
 *       请求一个不存在的 hook —— 纯空转 + 无意义写库。
 *
 * 设计要点（沿用 2.4.1 的加固思路）：
 *   ① 无备份不删：clean 前强制校验备份文件存在且能解析出原始序列化串。
 *   ② 白名单硬编码：只清 EXPECTED 这 4 个 hook；若发现白名单之外的 burst* hook，
 *      不擅自删除，而是**报告并中止**，交人工判定（防「探针结果即执行清单」）。
 *   ③ 只动 burst 相关节点，其余 hook 节点数值级不可变 —— 由「过滤前后非 burst
 *      结构规范化序列化相等」严格证明，而不是靠肉眼。
 *   ④ 备份含三件套：原始序列化串原文 / 可读导出 / 可执行回滚 SQL。
 *
 * 用法（须带 socket，见文件末尾注释）:
 *   php t242_cron.php list
 *   php t242_cron.php backup
 *   php t242_cron.php clean
 *   php t242_cron.php verify
 */

$ROOT = getenv('SF_ROOT') ?: ($_SERVER['HOME'] . '/Local Sites/sinofresh/app/public');
require $ROOT . '/wp-load.php';

const BACKUP_DIR = '/Users/meng/WorkBuddy/sinofresh外贸网站建设/_backup/img-cleanup-20260920-062700/db-burst';
const CRON_DIR   = BACKUP_DIR . '/cron';
const RAW_FILE   = CRON_DIR . '/cron-option-raw.txt';
const PRE_JSON   = CRON_DIR . '/cron-option-pre.json';
const PRETTY     = CRON_DIR . '/cron-option-pretty.txt';
const ROLLBACK   = CRON_DIR . '/rollback-cron.sql';

/** 唯一允许清理的 hook（burst-statistics 注册的 4 个） */
const EXPECTED = ['burst_daily', 'burst_weekly', 'burst_monthly', 'burst_tour_reminder_cron'];

global $wpdb;

/** 读取 cron option 的**原始**序列化串（与 DB 行字节一致，回滚依据） */
function cron_raw(): ?string {
    global $wpdb;
    $v = $wpdb->get_var("SELECT option_value FROM {$wpdb->options} WHERE option_name = 'cron'");
    return $v === null ? null : (string) $v;
}

/** 是否是时间戳桶（cron 数组里数值键 = 时间戳；非数值键如 'version' 保留不动） */
function is_ts($k): bool { return is_int($k) || ctype_digit((string) $k); }

/** 从 cron 结构中收集 burst* hook 明细 */
function collect_burst(array $crons): array {
    $out = [];
    foreach ($crons as $ts => $bucket) {
        if (!is_ts($ts) || !is_array($bucket)) { continue; }
        foreach ($bucket as $hook => $events) {
            if (strpos((string) $hook, 'burst') !== 0) { continue; }
            foreach ((array) $events as $sig => $ev) {
                $out[] = [
                    'timestamp' => (int) $ts,
                    'when'      => gmdate('Y-m-d H:i:s', (int) $ts) . ' UTC',
                    'hook'      => $hook,
                    'sig'       => $sig,
                    'schedule'  => $ev['schedule'] ?? null,
                    'interval'  => $ev['interval'] ?? null,
                    'args'      => $ev['args'] ?? null,
                ];
            }
        }
    }
    return $out;
}

/** 规范化：排序后序列化 —— 用于「其余 hook 未变」的严格比对（含时间戳，会被 wp-cron 扰动） */
function canon(array $crons): string {
    ksort($crons);
    $s = serialize($crons);
    return hash('sha256', $s);
}

/**
 * 去时间戳结构签名 —— 真正的不变量。
 * wp-cron 每跑一轮就会把循环事件的时间戳前移，故含时间戳的比对会假报警；
 * 这里只保留「hook → 各事件的 (schedule, interval, args)」多重集，忽略时间戳。
 */
function struct_sig(array $crons): string {
    $m = [];
    foreach ($crons as $ts => $bucket) {
        if (!is_ts($ts) || !is_array($bucket)) { continue; }
        foreach ($bucket as $hook => $events) {
            foreach ((array) $events as $sig => $ev) {
                $m[$hook][] = serialize([$ev['schedule'] ?? null, $ev['interval'] ?? null, $ev['args'] ?? null]);
            }
        }
    }
    foreach ($m as $h => $v) { sort($v); }
    ksort($m);
    return hash('sha256', serialize($m));
}

$mode = $argv[1] ?? 'list';
printf("== 任务 2.4.2  cron burst 孤儿事件 %s ==\n", strtoupper($mode));
printf("DB=%s  表=%s  autoload=%s\n\n", DB_NAME, $wpdb->options,
    (string) $wpdb->get_var("SELECT autoload FROM {$wpdb->options} WHERE option_name = 'cron'"));

$raw = cron_raw();
$crons = get_option('cron');
if (!is_array($crons)) { exit("❌ cron option 不是数组（值类型: " . gettype($crons) . "）\n"); }

$burst = collect_burst($crons);
$burst_hooks = array_values(array_unique(array_column($burst, 'hook')));

if ($mode === 'list') {
    // 结构统计（所有 hook / 事件）
    $all = []; $ev_total = 0; $buckets = 0;
    foreach ($crons as $ts => $b) {
        if (!is_ts($ts) || !is_array($b)) { continue; }
        $buckets++;
        foreach ($b as $h => $e) { $all[$h] = ($all[$h] ?? 0) + count((array) $e); $ev_total += count((array) $e); }
    }
    printf("cron option: %s B（序列化）| 时间戳桶 %d 个 | hook 去重 %d 个 | 事件总数 %d 个\n",
        number_format(strlen((string) $raw)), $buckets, count($all), $ev_total);
    printf("非时间戳键（原样保留）: %s\n\n",
        implode(', ', array_filter(array_keys($crons), fn($k) => !is_ts($k))) ?: '无');

    echo "── burst* 事件明细 ──\n";
    foreach ($burst as $b) {
        printf("  %-28s @ %s  schedule=%s interval=%s args=%s\n",
            $b['hook'], $b['when'], var_export($b['schedule'], true),
            var_export($b['interval'], true), json_encode($b['args']));
    }
    printf("\nburst* hook 去重: %d 个 → %s\n", count($burst_hooks), implode(', ', $burst_hooks));
    printf("burst* 事件总数: %d 个（用户报 7 个）%s\n", count($burst),
        count($burst) === 7 ? ' ✅' : ' ⚠️ 与预期不符，需人工确认');

    $extra = array_diff($burst_hooks, EXPECTED);
    printf("白名单之外的 burst* hook: %s\n", $extra ? '⚠️ ' . implode(', ', $extra) : '0 个 ✅');
    $missing = array_diff(EXPECTED, $burst_hooks);
    printf("白名单中未出现在 cron 的 hook: %s\n", $missing ? implode(', ', $missing) . '（已自然消失）' : '0 个');

    echo "\n── 全部 hook 清单（证明「其他 hook 保留」的对照基准）──\n";
    $all = [];
    foreach ($crons as $ts => $b) { if (is_ts($ts) && is_array($b)) { foreach ($b as $h => $e) { $all[$h] = ($all[$h] ?? 0) + count((array) $e); } } }
    ksort($all);
    foreach ($all as $h => $n) { printf("  %-42s ×%d%s\n", $h, $n, strpos($h, 'burst') === 0 ? '   ← burst' : ''); }
    printf("\nhook 去重总数: %d\n", count($all));
    exit(0);
}

if ($mode === 'backup') {
    if (!is_dir(CRON_DIR) && !mkdir(CRON_DIR, 0755, true)) { exit("❌ 无法创建 " . CRON_DIR . "\n"); }
    if ($raw === null) { exit("❌ cron option 不存在，无需备份\n"); }

    // ① 原始序列化串（回滚的字节级依据）
    file_put_contents(RAW_FILE, $raw);
    // ② 可读导出
    file_put_contents(PRETTY, "cron option 备份（可读）\n生成时间: " . date('c') . "\n"
        . "原始长度: " . strlen($raw) . " B\n"
        . "规范化 sha256: " . canon($crons) . "\n"
        . "burst* 事件: " . count($burst) . " 个 → " . implode(', ', $burst_hooks) . "\n\n"
        . var_export($crons, true) . "\n");
    // ③ 结构快照（供恢复性验证做 deep-equal）
    file_put_contents(PRE_JSON, json_encode($crons));
    // ④ 回滚 SQL
    $esc = $wpdb->_real_escape($raw);
    file_put_contents(ROLLBACK,
        "-- 任务 2.4.2 回滚：恢复 cron option 到清理前状态\n"
        . "-- 生成: " . date('c') . "  原始长度: " . strlen($raw) . " B\n"
        . "-- 应用: mysql --socket=<sock> -uroot -proot " . DB_NAME . " < rollback-cron.sql\n"
        . "UPDATE `{$wpdb->options}` SET option_value = '{$esc}' WHERE option_name = 'cron';\n"
        . "-- 校验: SELECT LENGTH(option_value) FROM `{$wpdb->options}` WHERE option_name='cron';  -- 应为 " . strlen($raw) . "\n");

    foreach ([RAW_FILE, PRETTY, PRE_JSON, ROLLBACK] as $f) {
        printf("  ✅ %-68s %s B\n", basename($f), number_format(filesize($f)));
    }
    printf("\n备份完成 → %s\n", CRON_DIR);
    printf("规范化 sha256: %s\n", canon($crons));
    exit(0);
}

if ($mode === 'clean') {
    // ① 备份门禁
    if (!is_readable(RAW_FILE) || !is_readable(ROLLBACK)) { exit("❌ 拒绝执行：备份缺失（先跑 backup）\n"); }
    $raw_bak = file_get_contents(RAW_FILE);
    if ($raw_bak !== $raw) {
        exit("❌ 拒绝执行：备份串与当前 DB 值不一致（备份后 cron 已被改动），请重新 backup\n");
    }
    printf("① 备份门禁 ✅  原始串 %s B 与 DB 一致；回滚 SQL %s B\n",
        number_format(strlen($raw)), number_format(filesize(ROLLBACK)));

    // ② 白名单门禁
    $extra = array_diff($burst_hooks, EXPECTED);
    if ($extra) { exit("❌ 拒绝执行：发现白名单之外的 burst* hook → " . implode(', ', $extra) . "，请人工确认后更新白名单\n"); }
    if (!$burst) { exit("ℹ️ 无 burst* 事件可清（已是干净状态）\n"); }
    printf("② 白名单门禁 ✅  待清 hook %d 个 / 事件 %d 个\n", count($burst_hooks), count($burst));

    // ③ 改写
    $before_canon = canon($crons);
    $removed = [];
    $new = $crons;
    foreach ($new as $ts => $bucket) {
        if (!is_ts($ts) || !is_array($bucket)) { continue; }   // 'version' 等非时间戳键原样保留
        foreach (array_keys($bucket) as $hook) {
            if (strpos((string) $hook, 'burst') === 0) {
                foreach ((array) $bucket[$hook] as $sig => $ev) {
                    $removed[] = sprintf('%s @ %s', $hook, gmdate('Y-m-d H:i:s', (int) $ts) . 'Z');
                }
                unset($new[$ts][$hook]);
            }
        }
        if (!$new[$ts]) { unset($new[$ts]); }                  // 空桶清除
    }
    foreach ($removed as $r) { printf("     − %s\n", $r); }

    if (!update_option('cron', $new)) { exit("❌ update_option('cron') 失败：" . $wpdb->last_error . "\n"); }
    printf("③ 已写回 cron ✅  删除事件 %d 个\n", count($removed));

    // ④ 立即复核
    wp_cache_delete('cron', 'options');
    $after = get_option('cron');
    printf("④ 复核: 残留 burst* 事件 %d 个 %s\n", count(collect_burst($after)),
        collect_burst($after) ? '❌' : '✅');
    exit(collect_burst($after) ? 1 : 0);
}

if ($mode === 'verify') {
    printf("① 残留 burst* 事件: %d 个 %s\n", count($burst),
        $burst ? '❌ ' . implode(', ', $burst_hooks) : '✅ 全清');
    $all = [];
    foreach ($crons as $ts => $b) { if (is_ts($ts) && is_array($b)) { foreach ($b as $h => $e) { $all[$h] = ($all[$h] ?? 0) + count((array) $e); } } }
    printf("② 现存 hook 去重 %d 个 / 事件总数 %d 个\n", count($all),
        array_sum(array_map(fn($ts, $b) => is_ts($ts) && is_array($b) ? array_sum(array_map('count', $b)) : 0,
            array_keys($crons), array_values($crons))));
    // 与备份中的「非 burst 结构」严格比对
    if (file_exists(PRE_JSON)) {
        $pre = json_decode(file_get_contents(PRE_JSON), true);
        $strip = function (array $c) { foreach ($c as $ts => $b) { if (!is_ts($ts) || !is_array($b)) continue;
            foreach (array_keys($b) as $h) if (strpos((string) $h, 'burst') === 0) unset($c[$ts][$h]);
            if (!$c[$ts]) unset($c[$ts]); } return $c; };
        $pre_s = $strip($pre);
        $want = struct_sig($pre_s);
        $got  = struct_sig($crons);
        printf("③ 去时间戳结构签名（不变量）: 备份(剔 burst) %s / 现网 %s → %s\n",
            substr($want, 0, 16), substr($got, 0, 16), $want === $got ? '完全一致 ✅' : '❌ 有差异');
        // 明细：hook → 事件数
        $cnt = function (array $c) { $m = []; foreach ($c as $ts => $b) {
            if (!is_ts($ts) || !is_array($b)) continue;
            foreach ($b as $h => $e) { $m[$h] = ($m[$h] ?? 0) + count((array) $e); } } ksort($m); return $m; };
        $a = $cnt($pre_s); $b2 = $cnt($crons);
        $only_a = array_diff_key($a, $b2); $only_b = array_diff_key($b2, $a);
        $cntdiff = array_filter(array_keys($a), fn($k) => isset($b2[$k]) && $a[$k] !== $b2[$k]);
        printf("   非 burst hook: 备份 %d 个 / 现网 %d 个 | 丢失 %s | 新增 %s | 数量变化 %s\n",
            count($a), count($b2), $only_a ? implode(',', array_keys($only_a)) : '0',
            $only_b ? implode(',', array_keys($only_b)) : '0',
            $cntdiff ? implode(',', $cntdiff) : '0');
        printf("④ cron option 大小（含时间戳漂移，非稳定指标）: %s B（清理前）→ %s B（现网）\n",
            number_format(is_readable(RAW_FILE) ? filesize(RAW_FILE) : 0), number_format(strlen((string) cron_raw())));
        printf("   非时间戳键（version 等）保留: %s\n",
            implode(', ', array_filter(array_keys($crons), fn($k) => !is_ts($k))) ?: '无');
        exit(($burst || $want !== $got || $only_a || $only_b) ? 1 : 0);
    }
    exit($burst ? 1 : 0);
}

exit("未知模式: $mode （可用 list / backup / clean / verify）\n");

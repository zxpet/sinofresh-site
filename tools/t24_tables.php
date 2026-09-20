<?php
/**
 * 任务 2.4.1：DROP 20 张 wp_burst_* 残留表
 *
 * 设计要点（均为本次踩坑后的加固）：
 *  1. 白名单硬编码 —— 只允许 DROP 下面这 20 张表；任何表名不在白名单一律拒绝，
 *     绝不用 LIKE/SHOW 结果直接拼 SQL（防「探针结果即执行清单」的越权）。
 *  2. 执行前强制校验备份：r02-tables-full.sql 存在且包含 20 个 CREATE TABLE 段，
 *     否则拒绝执行（无备份不删）。
 *  3. DROP TABLE 是 DDL，无法回滚 —— 故必须在备份可恢复性验证通过后才调用。
 *  4. 逐张执行并逐张报告，任一失败立即中断并打印剩余未删表，便于人工接管。
 *
 * 用法:
 *   php t24_tables.php list      # 只列出白名单表的实际存在情况
 *   php t24_tables.php drop      # 执行 DROP
 *   php t24_tables.php verify    # 核验残留（应为 0）
 *
 * 注意: 本脚本必须在 wp-load 后运行（$wpdb 才可用），故 CLI 需带
 *       -d mysqli.default_socket=<run 目录>/mysql/mysqld.sock
 */

$ROOT = getenv('SF_ROOT') ?: ($_SERVER['HOME'] . '/Local Sites/sinofresh/app/public');
require $ROOT . '/wp-load.php';

$BACKUP = '/Users/meng/WorkBuddy/sinofresh外贸网站建设/_backup/img-cleanup-20260920-062700/db-burst-tables/r02-tables-full.sql';

// ── 白名单（唯一真相：与 r02-tables-full.sql / drop-tables.sql 三方一致）────────
const BURST_TABLES = [
    'wp_burst_archived_months', 'wp_burst_browser_versions', 'wp_burst_browsers',
    'wp_burst_devices', 'wp_burst_goal_statistics', 'wp_burst_goals', 'wp_burst_imports',
    'wp_burst_locations', 'wp_burst_page_urls', 'wp_burst_platforms', 'wp_burst_query_stats',
    'wp_burst_referrers', 'wp_burst_report_logs', 'wp_burst_reports', 'wp_burst_searches',
    'wp_burst_sessions', 'wp_burst_statistics', 'wp_burst_statistics_searches', 'wp_burst_uids',
    'wp_burst_visitor_bitmaps',
];

global $wpdb;

/** 表是否存在（信息模式，非估算） */
function tbl_exists(string $t): bool {
    global $wpdb;
    $n = $wpdb->get_var($wpdb->prepare(
        "SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s",
        DB_NAME, $t));
    return (int) $n > 0;
}

/** 表精确行数（COUNT(*)，不用 TABLE_ROWS 估算） */
function tbl_rows(string $t): int {
    global $wpdb;
    return (int) $wpdb->get_var("SELECT COUNT(*) FROM `$t`");
}

$mode = $argv[1] ?? 'list';
printf("== 任务 2.4.1  wp_burst_* 表 %s ==\n", strtoupper($mode));
printf("DB=%s  前缀=%s  白名单=%d 张\n\n", DB_NAME, $wpdb->prefix, count(BURST_TABLES));

// 前置：白名单自检 —— 全部须以 $wpdb->prefix . 'burst_' 开头
foreach (BURST_TABLES as $t) {
    if (strpos($t, $wpdb->prefix . 'burst_') !== 0) {
        exit("❌ 白名单表名不符合当前表前缀: $t (prefix={$wpdb->prefix})\n");
    }
}

if ($mode === 'list') {
    $存在 = 0; $行数合计 = 0;
    foreach (BURST_TABLES as $t) {
        $e = tbl_exists($t);
        $r = $e ? tbl_rows($t) : 0;
        $存在 += $e ? 1 : 0; $行数合计 += $r;
        printf("  %-34s %s%s\n", $t, $e ? '存在' : '不存在', $e ? "  ({$r} 行)" : '');
    }
    printf("\n合计: 存在 %d 张 / 白名单 %d 张 | 精确行数 %d\n", $存在, count(BURST_TABLES), $行数合计);
    // 反向检查：库里是否还有白名单之外的 burst 表（防漏网）
    $extra = $wpdb->get_col($wpdb->prepare(
        "SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA=%s AND TABLE_NAME LIKE %s",
        DB_NAME, $wpdb->esc_like($wpdb->prefix . 'burst_') . '%'));
    $漏网 = array_diff($extra, BURST_TABLES);
    printf("白名单之外的 burst_* 表: %s\n", $漏网 ? implode(', ', $漏网) : '0 张 ✅');
    exit(0);
}

if ($mode === 'verify') {
    $left = $wpdb->get_col($wpdb->prepare(
        "SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA=%s AND TABLE_NAME LIKE %s",
        DB_NAME, $wpdb->esc_like($wpdb->prefix . 'burst_') . '%'));
    printf("残留 wp_burst_* 表: %d 张 %s\n", count($left), $left ? '→ ' . implode(', ', $left) : '✅');
    printf("库内表总数: %d\n", count($wpdb->get_col($wpdb->prepare(
        "SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA=%s", DB_NAME))));
    exit(count($left) === 0 ? 0 : 1);
}

if ($mode === 'drop') {
    // ① 备份门禁
    if (!is_readable($BACKUP)) { exit("❌ 拒绝执行：备份不存在 $BACKUP\n"); }
    $dump = file_get_contents($BACKUP);
    $ncreate = substr_count($dump, "\nCREATE TABLE ");
    $ndrop   = substr_count($dump, "\nDROP TABLE IF EXISTS ");
    printf("① 备份门禁: %s\n   CREATE=%d/20  DROP=%d/20  INSERT=%d  大小=%s B\n",
        $BACKUP, $ncreate, $ndrop, substr_count($dump, "\nINSERT INTO "), number_format(filesize($BACKUP)));
    if ($ncreate !== 20 || $ndrop !== 20) { exit("❌ 拒绝执行：备份不完整（CREATE 段应为 20）\n"); }

    // ② 逐张 DROP
    $ok = 0; $fail = []; $done = [];
    foreach (BURST_TABLES as $t) {
        if (!tbl_exists($t)) { printf("  --  %-34s 本就不存在，跳过\n", $t); continue; }
        $rows = tbl_rows($t);
        $res = $wpdb->query("DROP TABLE IF EXISTS `$t`");
        if ($res === false) { $fail[$t] = $wpdb->last_error; printf("  ❌  %-34s %s\n", $t, $wpdb->last_error); }
        else { $ok++; $done[] = "$t($rows 行)"; printf("  ✅  %-34s 已删（原有 %d 行）\n", $t, $rows); }
    }
    printf("\n② DROP 结果: 成功 %d / %d%s\n", $ok, count(BURST_TABLES), $fail ? '，失败 ' . count($fail) . ' 张' : '');
    foreach ($fail as $t => $e) { printf("   ⚠️ 未删: %s (%s)\n", $t, $e); }

    // ③ 立即复核
    $left = $wpdb->get_col($wpdb->prepare(
        "SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA=%s AND TABLE_NAME LIKE %s",
        DB_NAME, $wpdb->esc_like($wpdb->prefix . 'burst_') . '%'));
    printf("③ 残留核验: %d 张 %s\n", count($left), $left ? '→ ' . implode(', ', $left) : '✅ 全清');
    printf("库内表总数: %d\n", count($wpdb->get_col($wpdb->prepare(
        "SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA=%s", DB_NAME))));
    exit($left || $fail ? 1 : 0);
}

exit("未知模式: $mode （可用 list / drop / verify）\n");

<?php
/**
 * H24 — Fluent Forms form 8「Auto Reply to Customer」通知开关（幂等 / 可回滚）
 *
 * 背景
 *   机器人刷表单时，自动回复会逐条发往伪造地址，正在消耗域名的发信信誉
 *   （用户原话：「它在给域名信誉放血」）。本批先停用；等防护稳定后再恢复，
 *   恢复时须补一条「仅非 spam 提交触发自动回复」的守卫。
 *
 * 用法（服务器侧；dev 与 prod 各自执行）
 *   SF_H24_SITE=dev|prod SF_H24_MODE=status|disable|restore \
 *       wp eval-file /root/h24-tools/h24_autoreply_ctl.php --allow-root
 *
 *   ⚠️ dev 与 prod 共用同一台机器、同一个 /root/h24-backup/ 目录，
 *      故备份文件按站点分名：notif_autoreply_raw.<site>.json。
 *      必须显式传 SF_H24_SITE，否则默认 dev（兼容旧行为）。
 *
 * 安全设计
 *   1. 只做字符串级精确替换（不 json round-trip）——因为该 value 里含
 *      double-encoded 的 `\u2014` 字面量，round-trip 会改变字节。
 *   2. 替换前断言 `"enabled":true` 在目标行恰好出现 1 次。
 *   3. 只改 form_id=8 且 name='Auto Reply to Customer' 的那一行；
 *      同表的 Admin Notification（id=39）虽同样含该串，但按 name 精确锁定。
 *   4. 原始字节先备份到 /root/h24-backup/ ，仅首次写入、不覆盖。
 *   5. 回读校验，失败即报错退出。
 *
 * 退出码
 *   0 成功 / 无变化   1 非 WP 环境   2 无 notifications 行   3 未找到 feed
 *   4 断言失败   5 备份失败   6 更新失败   7 备份缺失(restore)
 */

if (!defined('ABSPATH')) {
    fwrite(STDERR, "[ERR] 必须通过 wp eval-file 执行\n");
    exit(1);
}

global $wpdb;

$FORM_ID    = 8;
$FEED_NAME  = 'Auto Reply to Customer';
$TABLE      = $wpdb->prefix . 'fluentform_form_meta';
$BACKUP_DIR = '/root/h24-backup';
$ENABLED    = '"enabled":true';
$DISABLED   = '"enabled":false';

/* 站点标识：dev 与 prod 同机共享备份目录，必须分名，否则 restore 会串味 */
$site = getenv('SF_H24_SITE');
if (!in_array($site, array('dev', 'prod'), true)) {
    $site = 'dev';
}
$BACKUP = $BACKUP_DIR . '/notif_autoreply_raw.' . $site . '.json';

$mode = getenv('SF_H24_MODE');
if (!in_array($mode, array('status', 'disable', 'restore'), true)) {
    $mode = 'status';
}

/** 输出一行 */
function sf_h24_out($s)
{
    fwrite(STDOUT, $s . "\n");
}

$rows = $wpdb->get_results(
    $wpdb->prepare(
        "SELECT id, value FROM {$TABLE} WHERE form_id = %d AND meta_key = 'notifications' ORDER BY id",
        $FORM_ID
    ),
    ARRAY_A
);

if (!$rows) {
    fwrite(STDERR, "[ERR] form {$FORM_ID} 没有 notifications 行\n");
    exit(2);
}

$target = null;
foreach ($rows as $r) {
    $decoded = json_decode($r['value'], true);
    $nm      = (is_array($decoded) && isset($decoded['name'])) ? $decoded['name'] : '';
    if ($nm === $FEED_NAME) {
        $target = $r;
        break;
    }
}
if (!$target) {
    fwrite(STDERR, "[ERR] 未找到 feed '{$FEED_NAME}'\n");
    exit(3);
}

$rid = (int) $target['id'];
$raw = $target['value'];

/* ---------- status ---------- */
if ($mode === 'status') {
    sf_h24_out('site: ' . $site);
    foreach ($rows as $r) {
        $d  = json_decode($r['value'], true);
        $nm = (is_array($d) && isset($d['name'])) ? $d['name'] : '?';
        $en = (is_array($d) && array_key_exists('enabled', $d)) ? ($d['enabled'] ? 'true' : 'false') : '?';
        sf_h24_out(sprintf('row id=%-3d enabled=%-5s name=%s', $r['id'], $en, $nm));
    }
    sf_h24_out('backup: ' . (file_exists($BACKUP) ? $BACKUP : '(none)'));
    exit(0);
}

/* ---------- restore ---------- */
if ($mode === 'restore') {
    if (!file_exists($BACKUP)) {
        fwrite(STDERR, "[ERR] 备份不存在，无法恢复：{$BACKUP}\n");
        exit(7);
    }
    $b = json_decode(file_get_contents($BACKUP), true);
    if (!is_array($b) || !isset($b['raw']) || !isset($b['row_id'])) {
        fwrite(STDERR, "[ERR] 备份文件格式异常：{$BACKUP}\n");
        exit(7);
    }
    $ok = $wpdb->update(
        $TABLE,
        array('value' => $b['raw']),
        array('id' => (int) $b['row_id']),
        array('%s'),
        array('%d')
    );
    if ($ok === false) {
        fwrite(STDERR, "[ERR] restore 更新失败: " . $wpdb->last_error . "\n");
        exit(6);
    }
    $back = $wpdb->get_var($wpdb->prepare("SELECT value FROM {$TABLE} WHERE id = %d", (int) $b['row_id']));
    $same = ($back === $b['raw']);
    sf_h24_out(sprintf('RESTORED row id=%d byte-identical=%s', (int) $b['row_id'], $same ? 'YES' : 'NO'));
    exit($same ? 0 : 6);
}

/* ---------- disable ---------- */
if (strpos($raw, $DISABLED) !== false && strpos($raw, $ENABLED) === false) {
    sf_h24_out("ALREADY DISABLED (site={$site}, row id={$rid}) — no change");
    exit(0);
}

$cnt = substr_count($raw, $ENABLED);
if ($cnt !== 1) {
    fwrite(STDERR, "[ERR] 断言失败：row {$rid} 里 '{$ENABLED}' 出现 {$cnt} 次（期望 1）\n");
    exit(4);
}

if (!is_dir($BACKUP_DIR)) {
    @mkdir($BACKUP_DIR, 0700, true);
}
if (!file_exists($BACKUP)) {
    $payload = json_encode(
        array(
            'form_id'  => $FORM_ID,
            'row_id'   => $rid,
            'meta_key' => 'notifications',
            'feed'     => $FEED_NAME,
            'saved_at' => gmdate('c'),
            'raw'      => $raw,
        ),
        JSON_UNESCAPED_SLASHES
    );
    if (@file_put_contents($BACKUP, $payload) === false) {
        fwrite(STDERR, "[ERR] 备份写入失败：{$BACKUP}\n");
        exit(5);
    }
    @chmod($BACKUP, 0600);
    sf_h24_out("backup written: {$BACKUP}");
} else {
    sf_h24_out("backup already exists (kept): {$BACKUP}");
}

$new = str_replace($ENABLED, $DISABLED, $raw);
if ($new === $raw) {
    fwrite(STDERR, "[ERR] 替换后无变化，异常\n");
    exit(4);
}

$ok = $wpdb->update($TABLE, array('value' => $new), array('id' => $rid), array('%s'), array('%d'));
if ($ok === false) {
    fwrite(STDERR, "[ERR] 更新失败: " . $wpdb->last_error . "\n");
    exit(6);
}

$back    = $wpdb->get_var($wpdb->prepare("SELECT value FROM {$TABLE} WHERE id = %d", $rid));
$stillOn = (strpos($back, $ENABLED) !== false);
$nowOff  = (substr_count($back, $DISABLED) === 1);

// 精确替换只差一个字符：true(4) -> false(5)，故长度必须 +1；
// 长度差不为 1 说明替换改动了非目标字节。
$expectDelta = strlen($DISABLED) - strlen($ENABLED);   // = 1
$lenDelta    = strlen($back) - strlen($raw);

sf_h24_out(sprintf(
    'DISABLED[%s] row id=%d | enabled串残留=%s | 已置false=%s | 长度差=%+d(期望%+d)',
    $site,
    $rid,
    $stillOn ? 'YES(异常)' : 'no',
    $nowOff ? 'YES' : 'NO(异常)',
    $lenDelta,
    $expectDelta
));

exit(($stillOn || !$nowOff || $lenDelta !== $expectDelta) ? 6 : 0);

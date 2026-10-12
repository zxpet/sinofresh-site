<?php
/**
 * H24b 附带 bug —— form 8 通知模板（id=39）**改前快照 + 原值备份**
 *
 * 只读 + 一次性备份，不做任何修改。用途：
 *   1. 执行 h24b_fix_notif_placeholder.php apply **之前**，亲手核验原值并落一份备份；
 *   2. apply 之后再跑一次，即可打印「改后值」做对照。
 *
 * 备份格式与 h24b_fix_notif_placeholder.php 的 restore 模式严格一致
 * （{form_id,row_id,feed,anchor,saved_at,raw}），因此可直接用于一条命令回滚。
 *
 *   SF_H24B_SITE=prod wp eval-file /root/h24-tools/h24b_notif_backup.php --allow-root
 */

if (!defined('ABSPATH')) {
    fwrite(STDERR, "[ERR] 必须通过 wp eval-file 执行\n");
    exit(1);
}

global $wpdb;

$site  = (getenv('SF_H24B_SITE') === 'prod') ? 'prod' : 'dev';
$ROW_ID = 39;
$TABLE  = $wpdb->prefix . 'fluentform_form_meta';
$BACKUP = '/root/h24b-backup/notif_placeholder_raw.' . $site . '.json';

$raw = $wpdb->get_var($wpdb->prepare("SELECT value FROM {$TABLE} WHERE id = %d", $ROW_ID));
if ($raw === null) {
    fwrite(STDERR, "[ERR] row {$ROW_ID} 不存在\n");
    exit(2);
}

/* ---------- 备份（仅首次写入，绝不覆盖 —— 保证回滚回到最初那份） ---------- */
$first_anchor = 'Privacy Consent: {inputs.company_name_1}';
if (strpos($raw, $first_anchor) === false) {
    $alt = 'Privacy Consent: {inputs.privacy_consent_11}';
    if (strpos($raw, $alt) !== false) {
        $first_anchor = $alt;
    }
}

if (!is_dir('/root/h24b-backup')) {
    @mkdir('/root/h24b-backup', 0700, true);
}
if (!file_exists($BACKUP)) {
    $payload = json_encode(
        array(
            'form_id'  => 8,
            'row_id'   => $ROW_ID,
            'feed'     => 'Admin Notification',
            'anchor'   => $first_anchor,
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
    echo "BACKUP_WRITTEN {$BACKUP}\n";
} else {
    echo "BACKUP_EXISTS(kept) {$BACKUP}\n";
}
echo 'BACKUP_LEN=' . strlen($raw) . "\n";
echo 'BACKUP_SHA256=' . hash('sha256', $raw) . "\n";

/* ---------- 打印当前值（改前 / 改后通用） ---------- */
$d = json_decode($raw, true);
echo "--- CURRENT LEN = " . strlen($raw) . " ---\n";
echo "--- SUBJECT ---\n" . ((is_array($d) && isset($d['subject'])) ? $d['subject'] : '?') . "\n";
echo "--- MESSAGE ---\n"
    . str_replace(array('<br />', '<br/>', '<br>'), "\n", (string) ((is_array($d) && isset($d['message'])) ? $d['message'] : ''))
    . "\n";

/* ---------- 关键行定位（供报告引用） ---------- */
$lines = preg_split('/<br\s*\/?>/', (string) ((is_array($d) && isset($d['message'])) ? $d['message'] : ''));
foreach ($lines as $ln) {
    if (stripos($ln, 'privacy') !== false || stripos($ln, 'company') !== false) {
        echo 'LINE: ' . trim(preg_replace('/\s+/', ' ', $ln)) . "\n";
    }
}

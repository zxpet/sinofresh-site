<?php
/**
 * H24 — A 组加固设置（A1 蜜罐 + A3 拒绝空提交）幂等 / 可回滚
 *
 * 口径来源：docs/h24-form-antispam-plan-2026-10-12.md §五 A 组
 *   A1 = _fluentform_global_form_settings.misc.honeypotStatus = 'yes'
 *        实现方：FluentForm app/Modules/Form/HoneyPot.php（renderHoneyPot 注入
 *        <input name="item_{formId}__fluent_sf">，verify() 要求该字段"存在且为空"）
 *        ★ 全局开关：开启后对**所有** FF 表单生效（生产共 5 个：8/9/10/11/12）
 *   A3 = form 8 formSettings.restrictions.denyEmptySubmission.enabled = true
 *
 * 用法（服务器侧；dev 与 prod 各自执行）
 *   SF_H24_SITE=prod SF_H24_MODE=status|apply|restore \
 *       wp eval-file /root/h24-tools/h24_prod_settings.php --allow-root
 *
 *   ⚠️ /root/h24-backup/ 为 dev 与 prod 共用（同一台机器）⇒ 备份文件按站点分名：
 *      global_settings_raw.<site>.json / form8_formsettings_raw.<site>.json
 *
 * 安全设计
 *   1. A1 走 get_option/update_option 正道（读-改-写 PHP 数组），并保留原 autoload。
 *   2. A3 只做**字符串级精确替换**（不 JSON round-trip），替换前断言 needle 出现 1 次。
 *   3. 原始字节先备份，**仅首次写入、绝不覆盖**（同名即沿用）。
 *   4. 两处均回读校验：A1 断言"除 honeypotStatus 外逐键 deep-equal"；
 *      A3 断言"长度差 +1 且把新串换回旧串后逐字节 === 原文"。
 *   5. restore 用原始字节直接写回，保证 byte-identical。
 *
 * 退出码
 *   0 成功 / 无变化   1 非 WP 环境   2 option 缺失或非数组   3 formSettings 行缺失
 *   4 断言失败       5 备份失败      6 写入失败          7 备份缺失(restore)
 */

if (!defined('ABSPATH')) {
    fwrite(STDERR, "[ERR] 必须通过 wp eval-file 执行\n");
    exit(1);
}

global $wpdb;

$OPT_KEY    = '_fluentform_global_form_settings';
$FORM_ID    = 8;
$TABLE      = $wpdb->prefix . 'fluentform_form_meta';
$OPT_TABLE  = $wpdb->options;
$BACKUP_DIR = '/root/h24-backup';

/* A3 的精确 needle（来自生产 raw 实测：denyEmptySubmission 对象紧跟 enabled 键） */
$FS_OLD = '"denyEmptySubmission":{"enabled":false';
$FS_NEW = '"denyEmptySubmission":{"enabled":true';

$site = getenv('SF_H24_SITE');
if (!in_array($site, array('dev', 'prod'), true)) {
    $site = 'dev';
}
$BK_OPT = $BACKUP_DIR . '/global_settings_raw.' . $site . '.json';
$BK_FS  = $BACKUP_DIR . '/form8_formsettings_raw.' . $site . '.json';

$mode = getenv('SF_H24_MODE');
if (!in_array($mode, array('status', 'apply', 'restore'), true)) {
    $mode = 'status';
}

function sf_h24s_out($s)
{
    fwrite(STDOUT, $s . "\n");
}

function sf_h24s_backup($path, array $payload, $label)
{
    if (!is_dir(dirname($path))) {
        @mkdir(dirname($path), 0700, true);
    }
    if (file_exists($path)) {
        sf_h24s_out("backup already exists (kept): {$path}");
        return true;
    }
    $json = json_encode($payload, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
    if (@file_put_contents($path, $json) === false) {
        fwrite(STDERR, "[ERR] {$label} 备份写入失败：{$path}\n");
        return false;
    }
    @chmod($path, 0600);
    sf_h24s_out("backup written: {$path}");
    return true;
}

/* ============ 读取现状 ============ */
$opt = get_option($OPT_KEY);
if (!is_array($opt)) {
    fwrite(STDERR, "[ERR] option {$OPT_KEY} 不存在或非数组（实际类型 " . gettype($opt) . "）\n");
    exit(2);
}

$fsRow = $wpdb->get_row(
    $wpdb->prepare(
        "SELECT id, value FROM {$TABLE} WHERE form_id = %d AND meta_key = 'formSettings' ORDER BY id LIMIT 1",
        $FORM_ID
    ),
    ARRAY_A
);
if (!$fsRow) {
    fwrite(STDERR, "[ERR] form {$FORM_ID} 找不到 formSettings 行\n");
    exit(3);
}

$fsId  = (int) $fsRow['id'];
$fsRaw = $fsRow['value'];

$honeyNow = isset($opt['misc']['honeypotStatus']) ? $opt['misc']['honeypotStatus'] : null;
$fsDec    = json_decode($fsRaw, true);
$denyNow  = isset($fsDec['restrictions']['denyEmptySubmission']['enabled'])
    ? $fsDec['restrictions']['denyEmptySubmission']['enabled'] : null;

/* ============ status ============ */
if ($mode === 'status') {
    sf_h24s_out('site: ' . $site);
    sf_h24s_out(sprintf('A1 honeyPotStatus = %s   (期望 yes)', var_export($honeyNow, true)));
    sf_h24s_out(sprintf('A3 denyEmptySubmission.enabled = %s   (期望 true)  [row id=%d, raw %d B]',
        var_export($denyNow, true), $fsId, strlen($fsRaw)));
    sf_h24s_out('backup A1: ' . (file_exists($BK_OPT) ? $BK_OPT : '(none)'));
    sf_h24s_out('backup A3: ' . (file_exists($BK_FS) ? $BK_FS : '(none)'));
    exit(0);
}

/* ============ restore ============ */
if ($mode === 'restore') {
    /* A1：原始字节直接写回 options 表，byte-identical */
    if (!file_exists($BK_OPT)) {
        fwrite(STDERR, "[ERR] A1 备份不存在：{$BK_OPT}\n");
        exit(7);
    }
    $b1 = json_decode(file_get_contents($BK_OPT), true);
    if (!is_array($b1) || !isset($b1['raw'])) {
        fwrite(STDERR, "[ERR] A1 备份格式异常：{$BK_OPT}\n");
        exit(7);
    }
    $ok1 = $wpdb->update($OPT_TABLE, array('option_value' => $b1['raw']), array('option_name' => $OPT_KEY), array('%s'), array('%s'));
    if ($ok1 === false) {
        fwrite(STDERR, "[ERR] A1 restore 写入失败: " . $wpdb->last_error . "\n");
        exit(6);
    }
    wp_cache_delete($OPT_KEY, 'options');
    wp_cache_delete('alloptions', 'options');
    $cur1 = $wpdb->get_var($wpdb->prepare("SELECT option_value FROM {$OPT_TABLE} WHERE option_name = %s", $OPT_KEY));
    $same1 = ($cur1 === $b1['raw']);
    sf_h24s_out(sprintf('RESTORED[%s] A1 byte-identical=%s', $site, $same1 ? 'YES' : 'NO'));

    /* A3：原始字节直接写回 form_meta */
    if (!file_exists($BK_FS)) {
        fwrite(STDERR, "[ERR] A3 备份不存在：{$BK_FS}\n");
        exit(7);
    }
    $b3 = json_decode(file_get_contents($BK_FS), true);
    if (!is_array($b3) || !isset($b3['raw'])) {
        fwrite(STDERR, "[ERR] A3 备份格式异常：{$BK_FS}\n");
        exit(7);
    }
    $ok3 = $wpdb->update($TABLE, array('value' => $b3['raw']), array('id' => $fsId), array('%s'), array('%d'));
    if ($ok3 === false) {
        fwrite(STDERR, "[ERR] A3 restore 写入失败: " . $wpdb->last_error . "\n");
        exit(6);
    }
    $cur3 = $wpdb->get_var($wpdb->prepare("SELECT value FROM {$TABLE} WHERE id = %d", $fsId));
    $same3 = ($cur3 === $b3['raw']);
    sf_h24s_out(sprintf('RESTORED[%s] A3 byte-identical=%s', $site, $same3 ? 'YES' : 'NO'));

    exit(($same1 && $same3) ? 0 : 6);
}

/* ============ apply ============ */
$fail = false;

/* ---- 备份（仅首次） ---- */
$optRaw = $wpdb->get_var($wpdb->prepare("SELECT option_value FROM {$OPT_TABLE} WHERE option_name = %s", $OPT_KEY));
if (!sf_h24s_backup($BK_OPT, array(
    'site' => $site, 'key' => $OPT_KEY, 'saved_at' => gmdate('c'), 'raw' => $optRaw,
), 'A1')) {
    exit(5);
}
if (!sf_h24s_backup($BK_FS, array(
    'site' => $site, 'form_id' => $FORM_ID, 'row_id' => $fsId, 'meta_key' => 'formSettings',
    'saved_at' => gmdate('c'), 'raw' => $fsRaw,
), 'A3')) {
    exit(5);
}

/* ---- A1：读-改-写 ---- */
$before = $opt;
if ($honeyNow === 'yes') {
    sf_h24s_out('A1 ALREADY ENABLED (misc.honeypotStatus = yes) — no change');
} else {
    if (!isset($opt['misc']) || !is_array($opt['misc'])) {
        $opt['misc'] = array();
    }
    $opt['misc']['honeypotStatus'] = 'yes';

    $autoload = $wpdb->get_var($wpdb->prepare("SELECT autoload FROM {$OPT_TABLE} WHERE option_name = %s", $OPT_KEY));
    $autoload = ($autoload === 'yes' || $autoload === 'on' || $autoload === 'auto-on') ? 'yes' : 'no';

    $u1 = update_option($OPT_KEY, $opt, $autoload);
    if ($u1 === false && get_option($OPT_KEY) !== $opt) {
        fwrite(STDERR, "[ERR] A1 update_option 失败\n");
        $fail = true;
    } else {
        $after  = get_option($OPT_KEY);
        $h2     = isset($after['misc']['honeypotStatus']) ? $after['misc']['honeypotStatus'] : null;
        $b      = $before; unset($b['misc']['honeypotStatus']);
        $a      = $after;  unset($a['misc']['honeypotStatus']);
        $others = ($b == $a);
        sf_h24s_out(sprintf('A1 APPLIED[%s] honeypotStatus=%s | 其余键不变=%s | autoload=%s',
            $site, var_export($h2, true), $others ? 'YES' : 'NO(异常)', $autoload));
        if ($h2 !== 'yes' || !$others) {
            $fail = true;
        }
    }
}

/* ---- A3：字符串级精确替换 ---- */
if (strpos($fsRaw, $FS_NEW) !== false && strpos($fsRaw, $FS_OLD) === false) {
    sf_h24s_out('A3 ALREADY ENABLED (denyEmptySubmission.enabled = true) — no change');
} else {
    $cnt = substr_count($fsRaw, $FS_OLD);
    if ($cnt !== 1) {
        fwrite(STDERR, "[ERR] A3 断言失败：needle 在 row {$fsId} 出现 {$cnt} 次（期望 1）\n");
        exit(4);
    }
    $fsNewRaw = str_replace($FS_OLD, $FS_NEW, $fsRaw);
    $u3 = $wpdb->update($TABLE, array('value' => $fsNewRaw), array('id' => $fsId), array('%s'), array('%d'));
    if ($u3 === false) {
        fwrite(STDERR, "[ERR] A3 写入失败: " . $wpdb->last_error . "\n");
        exit(6);
    }
    $back    = $wpdb->get_var($wpdb->prepare("SELECT value FROM {$TABLE} WHERE id = %d", $fsId));
    // 注意方向：A3 是 false(5) -> true(4)，故长度必须 **-1**；
    //（autoreply_ctl 那个脚本是 true->false，才是 +1，不要混）
    $expectD = strlen($FS_NEW) - strlen($FS_OLD);   // = -1
    $lenD    = strlen($back) - strlen($fsRaw);
    $revert  = str_replace($FS_NEW, $FS_OLD, $back);
    $byteEq  = ($revert === $fsRaw);
    $d2      = json_decode($back, true);
    $en2     = isset($d2['restrictions']['denyEmptySubmission']['enabled'])
        ? $d2['restrictions']['denyEmptySubmission']['enabled'] : null;
    sf_h24s_out(sprintf('A3 APPLIED[%s] id=%d | enabled=%s | 长度差=%+d(期望%+d) | 换回旧串后逐字节一致=%s',
        $site, $fsId, var_export($en2, true), $lenD, $expectD, $byteEq ? 'YES' : 'NO(异常)'));
    if ($en2 !== true || $lenD !== $expectD || !$byteEq) {
        $fail = true;
    }
}

exit($fail ? 4 : 0);

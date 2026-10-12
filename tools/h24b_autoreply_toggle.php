<?php
/**
 * H24b/A —— 停用（或恢复）表单的「Auto Reply to Customer」通知 feed
 *
 * 背景（2026-10-12 裁决）
 *   H24 表单机器人防护上线后，form 8 的自动回复已停用（feed 40 enabled=false）。
 *   但 form 9 / 10 / 11 的 Auto Reply feed **仍是 enabled=true**：
 *     form 9  feed 46  to={inputs.email_3}  enabled=true
 *     form 10 feed 52  to={inputs.email_4}  enabled=true
 *     form 11 feed 58  to={inputs.email_3}  enabled=true
 *   （form 12 没有 Auto Reply feed）
 *   裁决：**全停用，与 form 8 一致**；等防护稳定 ≥1 周后 4 个一起恢复，
 *   恢复时统一加「仅非 spam 触发」守卫。
 *
 * 判据（源码级，2026-10-12 实测 fluentform 6.2.14）
 *   FluentForm\App\Services\Integrations\GlobalNotificationManager::getEnabledFeeds()
 *       if ($parsedValue && ArrayHelper::isTrue($parsedValue, 'enabled')) { … }
 *   ⇒ 该 form_meta 行 JSON 里的 `enabled` 是**唯一**的发送开关。
 *   写 false 即停用（同 form 8 现状）。
 *
 * 安全设计
 *   1. 只处理 meta_key='notifications' 且 name 含 'Auto Reply' 的行（按 name 精确识别）。
 *   2. 逐 feed 备份**整行原始 value**，首次写入不覆盖（回滚永远回到最初那份）。
 *   3. 回读断言：`enabled === false`，且**除 enabled 外其它键值逐项相等**（证明只动了开关）。
 *   4. restore 逐字节比对（byte-identical）。
 *   5. 幂等：已是 false 的跳过，不重复备份、不重复写。
 *
 * 用法（服务器侧）
 *   SF_H24B_SITE=prod SF_H24B_MODE=status  wp eval-file … --allow-root
 *   SF_H24B_SITE=prod SF_H24B_MODE=disable wp eval-file … --allow-root
 *   SF_H24B_SITE=prod SF_H24B_MODE=restore wp eval-file … --allow-root   # 一条命令全部恢复
 *   SF_H24B_FORM=9                          # 只处理单个表单
 *   （默认处理 9,10,11）
 *
 * 退出码
 *   0 成功 / 无变化   1 非 WP   2 未找到目标 feed   4 断言失败
 *   5 备份失败   6 更新失败   7 备份缺失或格式异常(restore)
 */

if (!defined('ABSPATH')) { fwrite(STDERR, "[ERR] 必须通过 wp eval-file 执行\n"); exit(1); }

global $wpdb;
$P    = $wpdb->prefix;
$site = (getenv('SF_H24B_SITE') === 'prod') ? 'prod' : 'dev';
$mode = getenv('SF_H24B_MODE');
if (!in_array($mode, array('status', 'disable', 'restore'), true)) { $mode = 'status'; }
$oneForm = (int) getenv('SF_H24B_FORM');
$FORMS   = $oneForm > 0 ? array($oneForm) : array(9, 10, 11);
$BACKUP_DIR = '/root/h24b-backup';
$RC = 0;

function ar_out($s) { echo $s . "\n"; }
function ar_bk($site, $fid, $mid) { return '/root/h24b-backup/autoreply_raw.' . $site . '.' . $fid . '.' . $mid . '.json'; }

/* ================================================================ restore */
if ($mode === 'restore') {
    foreach ($FORMS as $fid) {
        $rows = $wpdb->get_results(
            $wpdb->prepare("SELECT id FROM {$P}fluentform_form_meta WHERE form_id=%d AND meta_key='notifications' ORDER BY id", $fid),
            ARRAY_A
        );
        $hit = 0;
        foreach ($rows as $r) {
            $bk = ar_bk($site, $fid, (int) $r['id']);
            if (!file_exists($bk)) { continue; }
            $b = json_decode(file_get_contents($bk), true);
            if (!is_array($b) || !isset($b['raw'], $b['meta_id'])) {
                fwrite(STDERR, "[ERR] 备份格式异常：{$bk}\n"); $RC = 7; continue;
            }
            $ok = $wpdb->update(
                $P . 'fluentform_form_meta',
                array('value' => $b['raw']),
                array('id' => (int) $b['meta_id']),
                array('%s'), array('%d')
            );
            if ($ok === false) { fwrite(STDERR, "[ERR] form {$fid} restore 失败: " . $wpdb->last_error . "\n"); $RC = 6; continue; }
            $back = (string) $wpdb->get_var($wpdb->prepare("SELECT value FROM {$P}fluentform_form_meta WHERE id=%d", (int) $b['meta_id']));
            $same = ($back === $b['raw']);
            $bd = json_decode($back, true);
            $en  = is_array($bd) && array_key_exists('enabled', $bd) ? var_export($bd['enabled'], true) : '?';
            ar_out(sprintf('RESTORED form %d meta_id=%d enabled=%s byte-identical=%s', $fid, (int) $b['meta_id'], $en, $same ? 'YES' : 'NO'));
            if (!$same) { $RC = 6; }
            $hit++;
        }
        if ($hit === 0) { ar_out("RESTORE form {$fid}: 无备份，跳过"); }
    }
    ar_out('');
    ar_out('===== site=' . $site . ' mode=' . $mode . ' 退出码=' . $RC . ' =====');
    exit($RC);
}

/* ================================================================ status / disable */
foreach ($FORMS as $fid) {
    $fr = $wpdb->get_row($wpdb->prepare("SELECT id,title FROM {$P}fluentform_forms WHERE id=%d", $fid), ARRAY_A);
    if (!$fr) { ar_out("form {$fid}: 不存在，跳过"); continue; }

    $rows = $wpdb->get_results(
        $wpdb->prepare("SELECT id, value FROM {$P}fluentform_form_meta WHERE form_id=%d AND meta_key='notifications' ORDER BY id", $fid),
        ARRAY_A
    );

    $found = 0;
    foreach ($rows as $r) {
        $raw = (string) $r['value'];
        $d   = json_decode($raw, true);
        if (!is_array($d)) { continue; }
        $name = isset($d['name']) ? (string) $d['name'] : '';
        if (stripos($name, 'auto reply') === false) { continue; }   /* 只认 Auto Reply */
        $found++;

        $to   = isset($d['to']) ? (string) $d['to'] : '';
        $en   = array_key_exists('enabled', $d) ? $d['enabled'] : null;
        $isOn = ($en === true || $en === 1 || $en === '1' || $en === 'true');

        ar_out('');
        ar_out(str_repeat('-', 96));
        ar_out(sprintf('form %d [%s] feed meta_id=%d [%s] to=%s', $fid, $fr['title'], (int) $r['id'], $name, $to));
        ar_out('  enabled(改前)=' . var_export($en, true) . '  →  目标=false');

        if ($mode === 'status') {
            ar_out('  状态: ' . ($isOn ? '待停用' : '已停用（无需改动）'));
            continue;
        }

        /* ---------------- disable ---------------- */
        if (!$isOn) {
            ar_out('  状态: 已停用（无需改动）');
            $bk = ar_bk($site, $fid, (int) $r['id']);
            if (file_exists($bk)) { ar_out('  备份: 已存在（保留）' . $bk); }
            continue;
        }

        if (!is_dir($BACKUP_DIR)) { @mkdir($BACKUP_DIR, 0700, true); }
        $bk = ar_bk($site, $fid, (int) $r['id']);
        if (!file_exists($bk)) {
            $payload = json_encode(array(
                'form_id' => $fid, 'meta_id' => (int) $r['id'], 'feed' => $name, 'to' => $to,
                'old_enabled' => $en, 'new_enabled' => false,
                'saved_at' => gmdate('c'), 'raw' => $raw,
            ), JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
            if (@file_put_contents($bk, $payload) === false) {
                fwrite(STDERR, "[ERR] 备份写入失败：{$bk}\n"); $RC = 5; continue;
            }
            @chmod($bk, 0600);
            ar_out('  备份: 写入 ' . $bk);
        } else {
            ar_out('  备份: 已存在（保留）' . $bk);
        }

        $before = $d; unset($before['enabled']);
        $d['enabled'] = false;
        $newVal = json_encode($d, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
        if ($newVal === $raw) { fwrite(STDERR, "[ERR] 替换后无变化，异常\n"); $RC = 4; continue; }

        $ok = $wpdb->update(
            $P . 'fluentform_form_meta',
            array('value' => $newVal),
            array('id' => (int) $r['id']),
            array('%s'), array('%d')
        );
        if ($ok === false) { fwrite(STDERR, "[ERR] 更新失败: " . $wpdb->last_error . "\n"); $RC = 6; continue; }

        /* 回读校验 */
        $back  = (string) $wpdb->get_var($wpdb->prepare("SELECT value FROM {$P}fluentform_form_meta WHERE id=%d", (int) $r['id']));
        $bd    = json_decode($back, true);
        $bEn   = is_array($bd) && array_key_exists('enabled', $bd) ? $bd['enabled'] : 'MISSING';
        $isOff = ($bEn === false);
        $after = is_array($bd) ? $bd : array(); unset($after['enabled']);
        $onlySwitch = ($after == $before);                 /* 除 enabled 外逐项相等（顺序无关） */
        $noTrueLit  = (strpos($back, '"enabled":true') === false);
        $hasFalseLit= (strpos($back, '"enabled":false') !== false);
        $sameKeys   = (array_keys($after) == array_keys($before));

        ar_out(sprintf('  APPLIED | enabled=%s 其余键值不变=%s 键集合一致=%s 无"enabled":true=%s 含"enabled":false=%s',
            var_export($bEn, true), $onlySwitch ? 'YES' : 'NO', $sameKeys ? 'YES' : 'NO',
            $noTrueLit ? 'YES' : 'NO', $hasFalseLit ? 'YES' : 'NO'));

        if (!($isOff && $onlySwitch && $sameKeys && $noTrueLit && $hasFalseLit)) { $RC = 6; }
    }

    if ($found === 0 && $mode === 'status') { ar_out("form {$fid}: 未找到 Auto Reply feed"); }
}

ar_out('');
ar_out('===== site=' . $site . ' mode=' . $mode . ' 退出码=' . $RC . ' =====');
exit($RC);

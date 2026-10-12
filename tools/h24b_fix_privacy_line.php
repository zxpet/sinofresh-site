<?php
/**
 * H24b 附带工作 —— 所有表单通知模板「Privacy Consent 行」修正（幂等 / 逐表单可回滚）
 *
 * 背景（2026-10-12 普查产出）
 *   5 个表单的管理员通知里，「Privacy Consent」这一行**全是坏的**，三种坏法：
 *     form 8  feed 39: Privacy Consent: {inputs.company_name_1}                                  ← 已单独修好
 *     form 9  feed 45: Privacy Consent: {inputs.company_name_1}                                  ← 渲染成公司名
 *     form 10 feed 51: Privacy Consent: {inputs.company_name_1}                                  ← 渲染成公司名
 *     form 11 feed 57: Privacy Consent: {inputs.privacy_consent_9.i_agree_to_the_privacy_policy_9_1}  ← 孤儿，渲染**空白**
 *     form 12 feed 63: Privacy Consent: {inputs.privacy_consent_5.i_agree_to_the_privacy_policy_5_1}  ← 孤儿，渲染**空白**
 *
 *   成因：模板是从 form 8 复制出去的 —— 前两份照抄了公司名占位符（改字段没改值），
 *   后两份用了 FF 界面里「选项级」的 key（`字段.选项key`），而 FF 的 ShortCodeParser
 *   只认 `{inputs.<字段名>}` 与 `{inputs.<字段名>.value}`，带选项后缀的取不到 → 空。
 *
 * 目标形态（2026-10-12 经渲染对照实验定稿）
 *     Privacy Consent: {inputs.<隐私字段>.value}
 *   `.value` 会让 getFormData 直接返回原始输入（不走 checkbox 的 `<ul><li>` 渲染），
 *   因此在「表单内联」与「HTML 邮件」两种分支下都产出干净的单行文本。
 *
 * 安全设计
 *   1. **自动发现**隐私字段：label 含 privacy 且 element 含 checkbox；必须唯一。
 *   2. 每表单只改 message 里 `Privacy Consent:` 那一行（且必须恰好出现 1 次）。
 *   3. 逐表单备份原始 value，仅首次写入不覆盖（回滚永远回到最初那份）。
 *   4. 回读校验：目标串 1 次、旧行 0 次、message 长度差 == strlen(newLine)-strlen(oldLine)，
 *      并做**反替换逐字节比对**（证明只动了那一行）。
 *   5. form 8 已修（无需改动）时，仍确保它有备份：从旧脚本的备份克隆一份。
 *
 * 用法（服务器侧）
 *   SF_H24B_SITE=prod SF_H24B_MODE=status  wp eval-file … --allow-root
 *   SF_H24B_SITE=prod SF_H24B_MODE=apply   wp eval-file … --allow-root
 *   SF_H24B_SITE=prod SF_H24B_MODE=restore wp eval-file … --allow-root      # 一条命令回滚全部
 *   SF_H24B_FORM=9   ……                                                # 只处理单个表单
 *
 * 退出码
 *   0 成功 / 无变化   1 非 WP   2 表单或通知行缺失   3 隐私字段不唯一
 *   4 断言失败   5 备份失败   6 更新失败   7 备份缺失或格式异常(restore)
 */

if (!defined('ABSPATH')) { fwrite(STDERR, "[ERR] 必须通过 wp eval-file 执行\n"); exit(1); }

global $wpdb;
$P = $wpdb->prefix;
$site = (getenv('SF_H24B_SITE') === 'prod') ? 'prod' : 'dev';
$mode = getenv('SF_H24B_MODE');
if (!in_array($mode, array('status', 'apply', 'restore'), true)) { $mode = 'status'; }
$oneForm = (int) getenv('SF_H24B_FORM');
$FORMS   = $oneForm > 0 ? array($oneForm) : array(8, 9, 10, 11, 12);
$BACKUP_DIR = '/root/h24b-backup';
$LINE_TAG   = 'Privacy Consent:';
$RC = 0;

function fp_out($s) { echo $s . "\n"; }

function fp_collect($node, &$acc)
{
    if (!is_array($node)) { return; }
    if (isset($node['attributes']['name']) && is_string($node['attributes']['name']) && $node['attributes']['name'] !== '') {
        $s = (isset($node['settings']) && is_array($node['settings'])) ? $node['settings'] : array();
        $acc[] = array(
            'name'    => (string) $node['attributes']['name'],
            'element' => isset($node['element']) ? (string) $node['element'] : '?',
            'label'   => (isset($s['label']) && $s['label'] !== '') ? (string) $s['label'] : (isset($s['admin_label']) ? (string) $s['admin_label'] : ''),
        );
        return;
    }
    foreach ($node as $v) { if (is_array($v)) { fp_collect($v, $acc); } }
}

/* ================================================================ restore */
if ($mode === 'restore') {
    foreach ($FORMS as $fid) {
        $bk = $BACKUP_DIR . '/notif_privacy_raw.' . $site . '.' . $fid . '.json';
        if (!file_exists($bk)) { fp_out("RESTORE form {$fid}: 无备份，跳过 ({$bk})"); continue; }
        $b = json_decode(file_get_contents($bk), true);
        if (!is_array($b) || !isset($b['raw'], $b['meta_id'])) {
            fwrite(STDERR, "[ERR] 备份格式异常：{$bk}\n"); $RC = 7; continue;
        }
        $ok = $wpdb->update($P . 'fluentform_form_meta', array('value' => $b['raw']), array('id' => (int) $b['meta_id']), array('%s'), array('%d'));
        if ($ok === false) { fwrite(STDERR, "[ERR] form {$fid} restore 失败: " . $wpdb->last_error . "\n"); $RC = 6; continue; }
        $back = (string) $wpdb->get_var($wpdb->prepare("SELECT value FROM {$P}fluentform_form_meta WHERE id=%d", (int) $b['meta_id']));
        $same = ($back === $b['raw']);
        fp_out(sprintf('RESTORED form %d meta_id=%d byte-identical=%s', $fid, (int) $b['meta_id'], $same ? 'YES' : 'NO'));
        if (!$same) { $RC = 6; }
    }
    exit($RC);
}

/* ================================================================ status / apply */
foreach ($FORMS as $fid) {
    $fr = $wpdb->get_row($wpdb->prepare("SELECT id,title,form_fields FROM {$P}fluentform_forms WHERE id=%d", $fid), ARRAY_A);
    if (!$fr) { fp_out("form {$fid}: 不存在，跳过"); continue; }

    $fields = array();
    fp_collect(json_decode((string) $fr['form_fields'], true), $fields);

    $privs = array();
    foreach ($fields as $f) {
        if (stripos($f['label'], 'privacy') !== false && stripos($f['element'], 'checkbox') !== false) {
            $privs[] = $f;
        }
    }
    if (count($privs) !== 1) {
        fwrite(STDERR, sprintf("[ERR] form %d 隐私字段不唯一（%d 个），拒绝处理\n", $fid, count($privs)));
        $RC = 3; continue;
    }
    $priv = $privs[0];
    $wantLine = $LINE_TAG . ' {inputs.' . $priv['name'] . '.value}';

    $rows = $wpdb->get_results(
        $wpdb->prepare("SELECT id, value FROM {$P}fluentform_form_meta WHERE form_id=%d AND meta_key='notifications' ORDER BY id", $fid),
        ARRAY_A
    );

    $touched = 0;
    foreach ($rows as $r) {
        $d = json_decode((string) $r['value'], true);
        if (!is_array($d) || !isset($d['message'])) { continue; }
        $msg = (string) $d['message'];

        $nTag = substr_count($msg, $LINE_TAG);
        if ($nTag === 0) { continue; }
        if ($nTag > 1) {
            fwrite(STDERR, sprintf("[ERR] form %d meta_id=%d 里 '%s' 出现 %d 次，拒绝盲改\n", $fid, $r['id'], $LINE_TAG, $nTag));
            $RC = 4; continue;
        }

        /* 取出该行原文（到 <br 或行尾/串尾为止） */
        if (!preg_match('/' . preg_quote($LINE_TAG, '/') . '([^<\r\n]*)/', $msg, $m)) { continue; }
        $oldLine = $LINE_TAG . $m[1];
        $newLine = $wantLine;
        $nPlace  = substr_count($oldLine, '{inputs.');

        $feedName = isset($d['name']) ? $d['name'] : '?';
        $head = sprintf('form %d [%s] feed meta_id=%d [%s] 隐私字段={inputs.%s}', $fid, $fr['title'], (int) $r['id'], $feedName, $priv['name']);
        fp_out('');
        fp_out(str_repeat('-', 96));
        fp_out($head);
        fp_out('  改前: ' . $oldLine);
        fp_out('  改后: ' . $newLine);

        $bk = $BACKUP_DIR . '/notif_privacy_raw.' . $site . '.' . $fid . '.json';

        if ($oldLine === $newLine) {
            fp_out('  状态: 已修正（无需改动）');
            /* 已修正的表单仍要保证可回滚：apply 时若缺备份，从旧脚本的单行备份克隆 */
            if ($mode === 'apply') {
                $legacy = $BACKUP_DIR . '/notif_placeholder_raw.' . $site . '.json';
                if (!file_exists($bk) && $fid === 8 && file_exists($legacy)) {
                    $L = json_decode(file_get_contents($legacy), true);
                    if (is_array($L) && isset($L['raw']) && (int) $L['row_id'] === (int) $r['id']) {
                        if (!is_dir($BACKUP_DIR)) { @mkdir($BACKUP_DIR, 0700, true); }
                        @file_put_contents($bk, json_encode(array(
                            'form_id' => $fid, 'meta_id' => (int) $r['id'], 'feed' => $feedName,
                            'old_line' => $LINE_TAG . ' {inputs.company_name_1}', 'new_line' => $newLine,
                            'saved_at' => gmdate('c'), 'raw' => $L['raw'],
                            'cloned_from' => $legacy,
                        ), JSON_UNESCAPED_SLASHES));
                        @chmod($bk, 0600);
                        fp_out('  备份: 已从旧备份克隆 → ' . $bk);
                    }
                } elseif (file_exists($bk)) {
                    fp_out('  备份: 已存在 ' . $bk);
                }
            }
            continue;
        }

        /* 断言：该行恰好一个占位符 */
        if ($nPlace !== 1) {
            fwrite(STDERR, sprintf("[ERR] form %d meta_id=%d 该行含 %d 个占位符（期望 1），拒绝盲改\n", $fid, $r['id'], $nPlace));
            $RC = 4; continue;
        }

        if ($mode === 'status') { fp_out('  状态: 待修正'); continue; }

        /* ---------------- apply ---------------- */
        if (!is_dir($BACKUP_DIR)) { @mkdir($BACKUP_DIR, 0700, true); }
        $bk = $BACKUP_DIR . '/notif_privacy_raw.' . $site . '.' . $fid . '.json';
        if (!file_exists($bk)) {
            $payload = json_encode(array(
                'form_id' => $fid, 'meta_id' => (int) $r['id'], 'feed' => $feedName,
                'old_line' => $oldLine, 'new_line' => $newLine,
                'saved_at' => gmdate('c'), 'raw' => (string) $r['value'],
            ), JSON_UNESCAPED_SLASHES);
            if (@file_put_contents($bk, $payload) === false) {
                fwrite(STDERR, "[ERR] 备份写入失败：{$bk}\n"); $RC = 5; continue;
            }
            @chmod($bk, 0600);
            fp_out('  备份: 写入 ' . $bk);
        } else {
            fp_out('  备份: 已存在（保留）' . $bk);
        }

        $newMsg = preg_replace('/' . preg_quote($LINE_TAG, '/') . '[^<\r\n]*/', $newLine, $msg, 1);
        if ($newMsg === $msg) { fwrite(STDERR, "[ERR] 替换后无变化，异常\n"); $RC = 4; continue; }

        $d['message'] = $newMsg;
        $newVal = json_encode($d, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
        $ok = $wpdb->update($P . 'fluentform_form_meta', array('value' => $newVal), array('id' => (int) $r['id']), array('%s'), array('%d'));
        if ($ok === false) { fwrite(STDERR, "[ERR] 更新失败: " . $wpdb->last_error . "\n"); $RC = 6; continue; }

        /* 回读校验 */
        $back = (string) $wpdb->get_var($wpdb->prepare("SELECT value FROM {$P}fluentform_form_meta WHERE id=%d", (int) $r['id']));
        $bd = json_decode($back, true);
        $bmsg = is_array($bd) ? (string) $bd['message'] : '';
        $nNew  = substr_count($bmsg, $newLine);
        $nOld  = substr_count($bmsg, $oldLine);
        $lDelta = strlen($bmsg) - strlen($msg);
        $expDelta = strlen($newLine) - strlen($oldLine);
        $revert = str_replace($newLine, $oldLine, $bmsg);
        $byteEq = ($revert === $msg);

        fp_out(sprintf('  APPLIED | 目标串=%d(期望1) 旧行残留=%d(期望0) 行长差=%+d(期望%+d) 反替换逐字节一致=%s',
            $nNew, $nOld, $lDelta, $expDelta, $byteEq ? 'YES' : 'NO'));

        if (!($nNew === 1 && $nOld === 0 && $lDelta === $expDelta && $byteEq)) { $RC = 6; }
        $touched++;
    }
    if ($touched === 0 && $mode === 'apply') { fp_out("form {$fid}: 无需修改"); }
}

fp_out('');
fp_out('===== site=' . $site . ' mode=' . $mode . ' 退出码=' . $RC . ' =====');
exit($RC);

<?php
/**
 * H24b/B —— 通知模板里「复选框 / 单选」占位符规范化：一律加 `.value`
 *
 * 背景（2026-10-12 普查 R3 规则）
 *   FF 的 ShortCodeParser 对 checkbox/radio 这类多值字段，**裸用** `{inputs.<字段>}`
 *   在 HTML 邮件分支里会渲染成 `<ul><li>…</li></ul>`（不是内联单行），
 *   用「选项级」key `{inputs.<字段>.<选项key>}` 则**取不到值 → 渲染为空**。
 *   实测（同一条真实提交数据，两个渲染分支）：
 *       {inputs.<字段>}                 → <ul style="…"><li>…</li></ul>
 *       {inputs.<字段>.value}           → 干净内联单行  ✅
 *
 *   现存问题（普查只报出 1 处，但脚本按通用规则修，防同类再犯）：
 *       form 11 feed 57（Request COA 的管理员通知）
 *           Document Type: {inputs.document_type_7}   ← 需改
 *
 * 判据（源码级）
 *   FluentForm\App\Services\FormBuilder\ShortCodeParser::getFormData()
 *     `.value` 分支直接返回原始输入，绕开 checkbox 的 `<ul><li>` 渲染。
 *
 * 安全设计
 *   1. **自动发现** checkbox/radio 字段（element 含 checkbox/radio），不写死字段名。
 *   2. 只改 token 形态，不改别的字符。验证用「归一化等值」：
 *         norm($orig) === norm($new)   —— 把所有这类 token 归一成裸形态后必须完全一致
 *      （证明非该类 token 一字未动）+ 断言改后该类 token **全部**为 `.value` 形态。
 *   3. 逐 feed 备份整行原始 value，首次写入不覆盖。
 *   4. restore 逐字节比对（byte-identical）。
 *   5. 幂等：已全部规范化的 feed 跳过，不重复备份、不重复写。
 *
 * 用法（服务器侧）
 *   SF_H24B_SITE=prod SF_H24B_MODE=status  wp eval-file … --allow-root
 *   SF_H24B_SITE=prod SF_H24B_MODE=apply   wp eval-file … --allow-root
 *   SF_H24B_SITE=prod SF_H24B_MODE=restore wp eval-file … --allow-root
 *   SF_H24B_FORM=11                         # 只处理单个表单
 *   （默认处理 8..12）
 *
 * 退出码
 *   0 成功 / 无变化   1 非 WP   2 表单缺失   4 断言失败
 *   5 备份失败   6 更新失败   7 备份缺失或格式异常(restore)
 */

if (!defined('ABSPATH')) { fwrite(STDERR, "[ERR] 必须通过 wp eval-file 执行\n"); exit(1); }

global $wpdb;
$P    = $wpdb->prefix;
$site = (getenv('SF_H24B_SITE') === 'prod') ? 'prod' : 'dev';
$mode = getenv('SF_H24B_MODE');
if (!in_array($mode, array('status', 'apply', 'restore'), true)) { $mode = 'status'; }
$oneForm = (int) getenv('SF_H24B_FORM');
$FORMS   = $oneForm > 0 ? array($oneForm) : array(8, 9, 10, 11, 12);
$BACKUP_DIR = '/root/h24b-backup';
$RC = 0;
/* ⚠️ wp eval-file 不是全局作用域 ⇒ 顶层变量在函数里用 `global` 取不到，一律用常量 */
define('SF_CB_TOKEN_RE', '/\{inputs\.([A-Za-z0-9_\-]+)(?:\.([A-Za-z0-9_\-]+))?\}/');

/* 归一化：把该类 token 一律拆成 [裸形态] —— 用于「非该类 token 一字未动」的等值证明 */
function cb_normalize($text, $keys)
{
    foreach ($keys as $k) {
        $q = preg_quote($k, '/');
        $text = preg_replace('/\{inputs\.' . $q . '\.[A-Za-z0-9_\-]+\}/', '{inputs.' . $k . '}', $text);
        $text = preg_replace('/\{inputs\.' . $q . '\}/', '{inputs.' . $k . '}', $text);
    }
    return $text;
}

/* 找出文本里所有该类 token，返回 [ [token, key, sub], … ]（只列需要改的） */
function cb_offenders($text, $keys)
{
    $out = array();
    if (!preg_match_all(SF_CB_TOKEN_RE, $text, $ms, PREG_SET_ORDER)) { return $out; }
    foreach ($ms as $m) {
        $key = $m[1];
        $sub = isset($m[2]) ? $m[2] : '';
        if (!in_array($key, $keys, true)) { continue; }
        if ($sub === 'value') { continue; }            /* 已是目标形态 */
        $out[] = array('token' => $m[0], 'key' => $key, 'sub' => $sub);
    }
    return $out;
}

/* 应用：把文本里该类 token 全部改写为 {inputs.KEY.value} */
function cb_apply($text, $keys)
{
    foreach ($keys as $k) {
        $q = preg_quote($k, '/');
        $text = preg_replace('/\{inputs\.' . $q . '\.[A-Za-z0-9_\-]+\}/', '{inputs.' . $k . '.value}', $text);
        $text = preg_replace('/\{inputs\.' . $q . '\}/', '{inputs.' . $k . '.value}', $text);
    }
    return $text;
}

/* 断言：改后文本里该类 token 必须**全部**是 .value 形态 */
function cb_all_value($text, $keys)
{
    if (!preg_match_all(SF_CB_TOKEN_RE, $text, $ms, PREG_SET_ORDER)) { return true; }
    foreach ($ms as $m) {
        if (!in_array($m[1], $keys, true)) { continue; }
        if ((isset($m[2]) ? $m[2] : '') !== 'value') { return false; }
    }
    return true;
}

function cb_out($s) { echo $s . "\n"; }
function cb_bk($site, $fid, $mid) { return '/root/h24b-backup/checkbox_ph_raw.' . $site . '.' . $fid . '.' . $mid . '.json'; }

/* ================================================================ restore */
if ($mode === 'restore') {
    foreach ($FORMS as $fid) {
        $rows = $wpdb->get_results(
            $wpdb->prepare("SELECT id FROM {$P}fluentform_form_meta WHERE form_id=%d AND meta_key='notifications' ORDER BY id", $fid),
            ARRAY_A
        );
        $hit = 0;
        foreach ($rows as $r) {
            $bk = cb_bk($site, $fid, (int) $r['id']);
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
            cb_out(sprintf('RESTORED form %d meta_id=%d byte-identical=%s', $fid, (int) $b['meta_id'], $same ? 'YES' : 'NO'));
            if (!$same) { $RC = 6; }
            $hit++;
        }
        if ($hit === 0) { cb_out("RESTORE form {$fid}: 无备份，跳过"); }
    }
    cb_out('');
    cb_out('===== site=' . $site . ' mode=' . $mode . ' 退出码=' . $RC . ' =====');
    exit($RC);
}

/* ================================================================ status / apply */
foreach ($FORMS as $fid) {
    $fr = $wpdb->get_row($wpdb->prepare("SELECT id,title,form_fields FROM {$P}fluentform_forms WHERE id=%d", $fid), ARRAY_A);
    if (!$fr) { cb_out("form {$fid}: 不存在，跳过"); continue; }

    /* 收集 checkbox / radio 字段的短码 key */
    $keys = array();
    $walk = function ($node) use (&$walk, &$keys) {
        if (!is_array($node)) { return; }
        if (isset($node['attributes']['name']) && is_string($node['attributes']['name']) && $node['attributes']['name'] !== '') {
            $el = isset($node['element']) ? (string) $node['element'] : '';
            if (stripos($el, 'checkbox') !== false || stripos($el, 'radio') !== false) {
                $keys[] = (string) $node['attributes']['name'];
            }
            return;
        }
        foreach ($node as $v) { if (is_array($v)) { $walk($v); } }
    };
    $walk(json_decode((string) $fr['form_fields'], true), $keys);
    $keys = array_values(array_unique($keys));

    $rows = $wpdb->get_results(
        $wpdb->prepare("SELECT id, value FROM {$P}fluentform_form_meta WHERE form_id=%d AND meta_key='notifications' ORDER BY id", $fid),
        ARRAY_A
    );

    foreach ($rows as $r) {
        $raw = (string) $r['value'];
        $d   = json_decode($raw, true);
        if (!is_array($d)) { continue; }

        $subjO = isset($d['subject']) ? (string) $d['subject'] : '';
        $msgO  = isset($d['message']) ? (string) $d['message'] : '';

        $badS = cb_offenders($subjO, $keys);
        $badM = cb_offenders($msgO, $keys);
        if (!$badS && !$badM) { continue; }              /* 该 feed 干净 */

        $name = isset($d['name']) ? (string) $d['name'] : '?';
        cb_out('');
        cb_out(str_repeat('-', 96));
        cb_out(sprintf('form %d [%s] feed meta_id=%d [%s]', $fid, $fr['title'], (int) $r['id'], $name));
        foreach (array_merge($badS, $badM) as $o) {
            cb_out(sprintf('  %s: %s  →  {inputs.%s.value}', $o['sub'] === '' ? '裸用' : '选项级', $o['token'], $o['key']));
        }

        if ($mode === 'status') { cb_out('  状态: 待修正'); continue; }

        /* ---------------- apply ---------------- */
        if (!is_dir($BACKUP_DIR)) { @mkdir($BACKUP_DIR, 0700, true); }
        $bk = cb_bk($site, $fid, (int) $r['id']);
        if (!file_exists($bk)) {
            $payload = json_encode(array(
                'form_id' => $fid, 'meta_id' => (int) $r['id'], 'feed' => $name,
                'saved_at' => gmdate('c'), 'raw' => $raw,
            ), JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
            if (@file_put_contents($bk, $payload) === false) {
                fwrite(STDERR, "[ERR] 备份写入失败：{$bk}\n"); $RC = 5; continue;
            }
            @chmod($bk, 0600);
            cb_out('  备份: 写入 ' . $bk);
        } else {
            cb_out('  备份: 已存在（保留）' . $bk);
        }

        $subjN = cb_apply($subjO, $keys);
        $msgN  = cb_apply($msgO, $keys);
        if ($subjN === $subjO && $msgN === $msgO) { fwrite(STDERR, "[ERR] 替换后无变化，异常\n"); $RC = 4; continue; }
        $d['subject'] = $subjN;
        $d['message'] = $msgN;
        $newVal = json_encode($d, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);

        $ok = $wpdb->update(
            $P . 'fluentform_form_meta',
            array('value' => $newVal),
            array('id' => (int) $r['id']),
            array('%s'), array('%d')
        );
        if ($ok === false) { fwrite(STDERR, "[ERR] 更新失败: " . $wpdb->last_error . "\n"); $RC = 6; continue; }

        /* 回读 + 断言 */
        $back = (string) $wpdb->get_var($wpdb->prepare("SELECT value FROM {$P}fluentform_form_meta WHERE id=%d", (int) $r['id']));
        $bd   = json_decode($back, true);
        $subjB = is_array($bd) && isset($bd['subject']) ? (string) $bd['subject'] : '';
        $msgB  = is_array($bd) && isset($bd['message']) ? (string) $bd['message'] : '';

        $allValue = cb_all_value($subjB, $keys) && cb_all_value($msgB, $keys);
        $normEq   = (cb_normalize($subjB, $keys) === cb_normalize($subjO, $keys))
                 && (cb_normalize($msgB,  $keys) === cb_normalize($msgO,  $keys));
        $lenDelta = strlen($msgB) - strlen($msgO);
        /* 期望长度差 = Σ(新 token 长 − 旧 token 长)，按 message 内的出现次数计（subject 单列） */
        $expMsg = 0;
        foreach ($badM as $o) {
            $expMsg += (strlen('{inputs.' . $o['key'] . '.value}') - strlen($o['token'])) * substr_count($msgO, $o['token']);
        }

        cb_out(sprintf('  APPLIED | 全部 .value 形态=%s 非该类 token 一字未动=%s message 长度差=%+d(期望%+d)',
            $allValue ? 'YES' : 'NO', $normEq ? 'YES' : 'NO', $lenDelta, $expMsg));

        if (!($allValue && $normEq && $lenDelta === $expMsg)) { $RC = 6; }
    }
}

cb_out('');
cb_out('===== site=' . $site . ' mode=' . $mode . ' 退出码=' . $RC . ' =====');
exit($RC);

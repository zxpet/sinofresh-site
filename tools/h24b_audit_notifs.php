<?php
/**
 * H24b 附带工作 —— 全部表单「通知模板 ↔ 字段」普查（只读，零写入）
 *
 * 产出四样东西（供对照表文档 + 健康度报告）：
 *   1) 每个表单的字段清单：shortcode key / element / label(options)
 *   2) 每个 notification feed：name / to / enabled / subject / message
 *   3) 逐占位符校验，三类问题：
 *        R1 孤儿     —— 占位符 key 在表单里根本不存在（改字段名后最容易踩）
 *        R2 跨语义   —— message 内同一个字段被用在两个不同标签下（form 8 那个 bug 的特征）
 *        R3 复选框裸用 —— checkbox/radio 没加 .value，HTML 邮件里会渲染成 <ul><li> 而非内联单行
 *   4) 用**构造样本**（非真实提交，零 PII）渲染 subject/message 的邮件实际形态
 *
 * 用法（服务器侧）
 *   SF_H24B_SITE=prod wp eval-file /root/h24-tools/h24b_audit_notifs.php --allow-root
 *   SF_H24B_JSON_OUT=/tmp/notif-audit.json 同上  ⇒ 额外落一份机器可读 JSON
 */

if (!defined('ABSPATH')) { fwrite(STDERR, "[ERR] 必须通过 wp eval-file 执行\n"); exit(1); }

global $wpdb;
$P = $wpdb->prefix;
$site = (getenv('SF_H24B_SITE') === 'prod') ? 'prod' : 'dev';
/**
 * ⚠️ 必须在**独立进程里逐表单**跑：FF 的 FormFieldsParser 把字段定义缓存在静态属性里，
 *    同一进程里连续渲染多个表单时，后一个表单会复用前一个的字段定义 ⇒ 渲染值全错
 *    （实测 form 9 只渲染出 form 8 也有的那几个字段，其余全空）。
 *    传 SF_H24B_FORM=<id> 只处理一个表单；不传时才按下面列表循环（仅字段/占位符校验可信）。
 */
$oneForm = (int) getenv('SF_H24B_FORM');
$want = $oneForm > 0 ? array($oneForm) : array(8, 9, 10, 11, 12);

$out  = array();
$json = array('site' => $site, 'generated_at' => gmdate('c'), 'forms' => array());

function a_out($s) { echo $s . "\n"; }

/** 归一化 shortcode key：去掉 [] 与 . 后比对（多选字段名带 []，占位符写 . 或不写） */
function a_norm($k) { return preg_replace('/[\[\]\.]/', '', (string) $k); }

/** 递归收集叶子字段（含 attributes.name 的节点） */
function a_collect($node, &$acc)
{
    if (!is_array($node)) { return; }
    if (isset($node['attributes']['name']) && is_string($node['attributes']['name']) && $node['attributes']['name'] !== '') {
        $s = isset($node['settings']) && is_array($node['settings']) ? $node['settings'] : array();
        $opts = array();
        foreach (array('advanced_options', 'options') as $ok) {
            if (!empty($s[$ok]) && is_array($s[$ok])) {
                foreach ($s[$ok] as $o) {
                    if (is_array($o) && isset($o['value'])) { $opts[] = (string) $o['value']; }
                    elseif (is_string($o)) { $opts[] = $o; }
                }
                if ($opts) { break; }
            }
        }
        $acc[] = array(
            'name'    => (string) $node['attributes']['name'],
            'element' => isset($node['element']) ? (string) $node['element'] : '?',
            'label'   => isset($s['label']) && $s['label'] !== '' ? (string) $s['label'] : (isset($s['admin_label']) ? (string) $s['admin_label'] : ''),
            'admin'   => isset($s['admin_label']) ? (string) $s['admin_label'] : '',
            'opts'    => $opts,
        );
        return;
    }
    foreach ($node as $v) { if (is_array($v)) { a_collect($v, $acc); } }
}

/** 构造样本值（**不**使用任何真实提交数据） */
function a_sample($f)
{
    $el = $f['element'];
    $isChoice = (bool) preg_match('/checkbox|radio|select/', $el);
    if ($isChoice && !empty($f['opts'])) {
        return $f['opts'][0];
    }
    $lab = $f['label'] !== '' ? $f['label'] : $f['name'];
    return '«' . $lab . '»';
}

$forms = $wpdb->get_results("SELECT id, title, status, form_fields FROM {$P}fluentform_forms ORDER BY id", ARRAY_A);
$byId  = array();
foreach ($forms as $f) { $byId[(int) $f['id']] = $f; }

foreach ($want as $fid) {
    if (!isset($byId[$fid])) { a_out("form {$fid}: 不存在，跳过"); continue; }
    $fr = $byId[$fid];
    $title = $fr['title'];

    $decoded = json_decode((string) $fr['form_fields'], true);
    $fields  = array();
    a_collect($decoded, $fields);

    /* key → 字段（归一化后） */
    $byKey = array();
    $sample = array();
    foreach ($fields as $f) {
        $byKey[a_norm($f['name'])] = $f;
        $sample[$f['name']] = a_sample($f);
    }

    $formObj = wpFluent()->table('fluentform_forms')->find($fid);

    a_out('');
    a_out('==============================================================');
    a_out(sprintf('FORM %d [%s]  status=%s  字段 %d 个', $fid, $title, $fr['status'], count($fields)));
    a_out('==============================================================');

    /* ---------- 1) 字段清单 ---------- */
    a_out('--- 字段（shortcode key / element / label / 选项数）---');
    $jf = array();
    foreach ($fields as $f) {
        a_out(sprintf('  {inputs.%-28s} %-18s %-30s opts=%d', $f['name'], $f['element'], $f['label'], count($f['opts'])));
        $jf[] = array('key' => $f['name'], 'element' => $f['element'], 'label' => $f['label'], 'opts' => $f['opts']);
    }

    /* ---------- 2) 通知 feed ---------- */
    $feeds = $wpdb->get_results(
        $wpdb->prepare("SELECT id, value FROM {$P}fluentform_form_meta WHERE form_id=%d AND meta_key='notifications' ORDER BY id", $fid),
        ARRAY_A
    );

    $jfeeds = array();
    foreach ($feeds as $rowrec) {
        $d = json_decode((string) $rowrec['value'], true);
        if (!is_array($d)) { continue; }
        $fname   = isset($d['name']) ? $d['name'] : '?';
        $subject = isset($d['subject']) ? (string) $d['subject'] : '';
        $message = isset($d['message']) ? (string) $d['message'] : '';
        $to      = isset($d['to']) ? (string) $d['to'] : '';
        $enabled = array_key_exists('enabled', $d) ? $d['enabled'] : null;

        a_out('');
        a_out(sprintf('--- feed meta_id=%s [%s] to=%s enabled=%s ---', $rowrec['id'], $fname, $to, var_export($enabled, true)));

        /* 逐行解析占位符 */
        $lines = preg_split('/<br\s*\/?>|\r\n|\n|\r/i', $message);
        $pfxOf = array();   // normKey => set(prefix)
        $issues = array();
        $jlines = array();

        foreach ($lines as $ln) {
            if (trim($ln) === '') { continue; }
            $prefix = trim(preg_split('/[:：]/u', $ln)[0]);
            if (preg_match_all('/\{inputs\.([A-Za-z0-9_\[\]\.]+)\}/', $ln, $mm, PREG_SET_ORDER)) {
                foreach ($mm as $p) {
                    $raw = $p[1];
                    $hasValue = (substr($raw, -6) === '.value');
                    $key = $hasValue ? substr($raw, 0, -6) : $raw;
                    $key = rtrim(str_replace('[]', '', $key), '.');
                    $norm = a_norm($key);

                    $fld = isset($byKey[$norm]) ? $byKey[$norm] : null;
                    $tag = '';
                    if (!$fld) {
                        $tag = 'R1孤儿';
                        $issues[] = sprintf('R1 孤儿占位符 {inputs.%s} 在「%s」行 —— 表里没有这个字段', $key, $prefix);
                    } else {
                        $pfxOf[$norm][$prefix] = true;
                        if (preg_match('/checkbox|radio/', $fld['element']) && !$hasValue) {
                            $tag = 'R3裸用';
                            $issues[] = sprintf('R3 复选框未加 .value：{inputs.%s}（%s，标签「%s」）—— HTML 邮件会渲染成 <ul><li>',
                                $key, $fld['element'], $prefix);
                        } else {
                            $tag = 'OK';
                        }
                    }
                    a_out(sprintf('    [%s] 行标签「%s」 占位符 {inputs.%s}%s → 字段 %s',
                        $tag, $prefix, $key, $hasValue ? '.value' : '',
                        $fld ? ('{inputs.' . $fld['name'] . '} 「' . $fld['label'] . '」') : '∅'));
                    $jlines[] = array('prefix' => $prefix, 'key' => $key, 'has_value' => $hasValue,
                                      'element' => $fld ? $fld['element'] : null, 'label' => $fld ? $fld['label'] : null);
                }
            }
        }
        /* R2：message 内同一字段出现在两个不同标签下 */
        foreach ($pfxOf as $norm => $set) {
            if (count($set) > 1) {
                $issues[] = sprintf('R2 跨语义复用：{inputs.%s} 同时用在「%s」两个不同标签下（很可能照抄改了字段名却没改值）',
                    $byKey[$norm]['name'], implode('」和「', array_keys($set)));
            }
        }

        /* ---------- 3) 样本渲染（邮件实际形态 isHtml=true）---------- */
        $rSubject = \FluentForm\App\Services\FormBuilder\ShortCodeParser::parse($subject, 0, $sample, $formObj, false, true);
        $rMessage = \FluentForm\App\Services\FormBuilder\ShortCodeParser::parse($message, 0, $sample, $formObj, false, true);
        $rMessagePlain = str_replace(array('<br />', '<br/>', '<br>'), "\n", $rMessage);

        a_out('    subject（原）: ' . $subject);
        a_out('    subject（渲染）: ' . $rSubject);
        a_out('    message（渲染, isHtml=true）:');
        foreach (explode("\n", $rMessagePlain) as $l) { a_out('      | ' . $l); }

        if ($issues) { foreach ($issues as $s) { a_out('    !! ' . $s); } }
        else { a_out('    ✓ 未发现问题'); }

        $jfeeds[] = array(
            'meta_id' => (int) $rowrec['id'], 'name' => $fname, 'to' => $to, 'enabled' => $enabled,
            'subject_raw' => $subject, 'message_raw' => $message,
            'subject_rendered' => $rSubject, 'message_rendered' => $rMessagePlain,
            'lines' => $jlines, 'issues' => $issues,
        );
    }

    $json['forms'][] = array('id' => $fid, 'title' => $title, 'status' => $fr['status'],
                             'fields' => $jf, 'feeds' => $jfeeds);
}

$jout = getenv('SF_H24B_JSON_OUT');
if ($jout) {
    file_put_contents($jout, json_encode($json, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT));
    a_out('');
    a_out('JSON_WRITTEN ' . $jout . ' (' . strlen(json_encode($json)) . ' bytes)');
}

/* 汇总 */
$tot = 0; $bad = 0;
foreach ($json['forms'] as $f) { foreach ($f['feeds'] as $fd) { $tot++; if ($fd['issues']) { $bad++; } } }
a_out('');
a_out(sprintf('===== 汇总：%d 个表单 / %d 个 feed / %d 个 feed 存在问题 =====', count($json['forms']), $tot, $bad));
a_out('SITE=' . $site);

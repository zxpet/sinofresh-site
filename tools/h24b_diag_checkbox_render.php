<?php
/**
 * H24b 诊断：checkbox 占位符在「HTML 邮件分支」下的渲染形态（针对 Document Type）
 *
 * 零污染：只读 DB + 用 FF 自己的 ShortCodeParser 渲染，不发信、不写库。
 *
 * 要回答三个问题：
 *   1. 裸用 {inputs.document_type_7}  在 isHtml=true（HTML 邮件）下是否被包成 <ul><li>？
 *   2. 修后的 {inputs.document_type_7.value} 两个分支下是否都是内联单行？
 *   3. ⚠️ **多选**时 .value 返回什么（数组？逗号连接？"Array"？）—— 这是本次修复的残余风险点。
 *
 * 用法：SF_H24B_SITE=prod wp eval-file /root/h24-tools/h24b_diag_checkbox_render.php --allow-root
 */

if (!defined('ABSPATH')) { fwrite(STDERR, "[ERR] 必须通过 wp eval-file 执行\n"); exit(1); }

$formId = 11;
$KEY    = 'document_type_7';
$out    = array();

$form = wpFluent()->table('fluentform_forms')->find($formId);
if (!$form) { echo "NO FORM {$formId}\n"; exit; }

$sub = wpFluent()->table('fluentform_submissions')
    ->where('form_id', $formId)
    ->orderBy('id', 'DESC')
    ->first();
$subId = $sub ? (int) $sub->id : 0;
$realData = $sub ? json_decode($sub->response, true) : array();

$out[] = '=== form ' . $formId . '  ' . $form->title . ' ===';
$out[] = '最新提交 id=' . $subId . '（若无则用构造数据）';
$out[] = '';

/* ---------- 场景 A：单选（真实提交数据若可用） ---------- */
/* ---------- 场景 B：多选（构造） ---------- */
$scenarios = array();

if (is_array($realData) && array_key_exists($KEY, $realData)) {
    $scenarios['真实提交数据'] = $realData;
}
$base = is_array($realData) ? $realData : array();
$base['company_name_1'] = 'ACME PET NUTRITION LLC';
$base['country_4']      = 'United States';

$s1 = $base; $s1[$KEY] = 'COA Sample';
$scenarios['单选（字符串）'] = $s1;

$s2 = $base; $s2[$KEY] = array('COA Sample');
$scenarios['单选（单元素数组）'] = $s2;

$s3 = $base; $s3[$KEY] = array('COA Sample', 'MSDS');
$scenarios['多选（双元素数组）'] = $s3;

/* 全字段构造（只用于最后「整篇模板」画面，不落库） */
$sFull = array(
    'company_name_1'           => 'ACME PET NUTRITION LLC',
    'contact_person_2'         => 'Jane Doe',
    'country_4'                => 'United States',
    'target_market_5'          => 'North America',
    'email_3'                  => 'buyer@example.com',
    'interested_dosage_form_6' => 'Soft Chews',
    'document_type_7'          => array('COA Sample'),
    'notes_8'                  => 'Please share the latest COA for our audit.',
    'privacy_consent_9'        => array('I agree to the Privacy Policy'),
);

$variants = array(
    '裸用  {inputs.' . $KEY . '}'        => '{inputs.' . $KEY . '}',
    '加值  {inputs.' . $KEY . '.value}'  => '{inputs.' . $KEY . '.value}',
);

foreach ($scenarios as $sName => $data) {
    $out[] = str_repeat('=', 90);
    $out[] = '【场景】' . $sName . '   ' . $KEY . ' = ' . var_export($data[$KEY], true);
    foreach ($variants as $vName => $code) {
        foreach (array(false, true) as $isHtml) {
            $tpl = 'Document Type: ' . $code . '<br />';
            $res = \FluentForm\App\Services\FormBuilder\ShortCodeParser::parse($tpl, $subId, $data, $form, false, $isHtml);
            $hasUl = (stripos($res, '<ul') !== false || stripos($res, '<li') !== false);
            $out[] = sprintf('   [%s | isHtml=%-5s] 含<ul>/<li>=%-3s  渲染 → %s',
                $vName, $isHtml ? 'true' : 'false', $hasUl ? 'YES' : 'no', str_replace(array("\r", "\n"), '', $res));
        }
    }
    $out[] = '';
}

/* ---------- 当前真实模板的 HTML 分支渲染（断言用） ---------- */
$tpl = null;
$rows = wpFluent()->table('fluentform_form_meta')
    ->where('form_id', $formId)->where('meta_key', 'notifications')->get();
foreach ($rows as $r) {
    $v = json_decode($r->value, true);
    if (isset($v['name']) && $v['name'] === 'Admin Notification') { $tpl = $v['message']; break; }
}
if ($tpl !== null) {
    $out[] = str_repeat('=', 90);
    $out[] = '【当前模板 · isHtml=true 全篇渲染】feed meta_id=' . $r->id;
    /* 用带完整必填字段的构造数据（sFull），否则整篇都会渲染为空、拿不到画面 */
    $full = \FluentForm\App\Services\FormBuilder\ShortCodeParser::parse($tpl, $subId, $sFull, $form, false, true);
    $hasUlAny = (stripos($full, '<ul') !== false);
    $out[] = '  全篇含 <ul> = ' . ($hasUlAny ? 'YES ⚠️' : 'no ✓');
    $plain = preg_replace('/<br[^>]*>/i', "\n", $full);
    $plain = preg_replace('/<[^>]+>/', '', $plain);
    $out[] = '  ---- 邮件正文（纯文本）----';
    foreach (explode("\n", trim($plain)) as $ln) { $out[] = '    ' . $ln; }
}

echo implode("\n", $out) . "\n";

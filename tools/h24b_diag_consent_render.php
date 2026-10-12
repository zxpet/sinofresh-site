<?php
/**
 * H24b 诊断：form 8 通知里 {inputs.privacy_consent_11} 为何渲染为空
 *
 * 零污染：只读 DB + 用 FF 自己的 NotificationParser 渲染，不发信、不写库。
 * 用法（服务器侧）：wp eval-file /root/h24-tools/h24b_diag_consent_render.php --allow-root
 */

$formId = 8;
$out = [];

// ---- 1) 最近一条 form 8 提交的 response，看 key 到底叫什么 ----
$sub = wpFluent()->table('fluentform_submissions')
    ->where('form_id', $formId)
    ->orderBy('id', 'DESC')
    ->first();

if (!$sub) {
    echo "NO SUBMISSION for form {$formId}\n";
    exit;
}

$data = json_decode($sub->response, true);
$out[] = '=== submission #' . $sub->id . ' status=' . $sub->status . ' ===';
$keys = array_keys((array) $data);
$out[] = 'data keys(' . count($keys) . '): ' . implode(', ', $keys);

foreach (['privacy_consent_11', 'privacy_consent_11[]', 'privacy_consent', 'company_name_1'] as $k) {
    $out[] = sprintf('  data[%s] = %s', $k, var_export($data[$k] ?? 'MISSING', true));
}

// ---- 2) 表单 schema 里 checkbox 字段的短代码 key ----
$form = wpFluent()->table('fluentform_forms')->find($formId);
$inputs = \FluentForm\App\Modules\Form\FormFieldsParser::getShortCodeInputs(
    $form,
    ['admin_label', 'attributes', 'options', 'raw']
);
$out[] = '=== shortcode-inputs 里 element=input_checkbox 的 key ===';
foreach ($inputs as $k => $f) {
    if (($f['element'] ?? '') === 'input_checkbox') {
        $out[] = sprintf(
            '  KEY[%s] element=%s admin_label=%s',
            $k,
            $f['element'],
            isset($f['admin_label']) ? $f['admin_label'] : '-'
        );
    }
}
$out[] = '  (privacy_consent_11 在 map 中? ' . (isset($inputs['privacy_consent_11']) ? 'YES' : 'NO') . ')';

// ---- 3) 取 Admin Notification 模板 ----
$tpl = null;
$tplId = null;
$rows = wpFluent()->table('fluentform_form_meta')
    ->where('form_id', $formId)
    ->where('meta_key', 'notifications')
    ->get();
foreach ($rows as $r) {
    $v = json_decode($r->value, true);
    if (($v['name'] ?? '') === 'Admin Notification') {
        $tpl = $v['message'];
        $tplId = $r->id;
        break;
    }
}

if ($tpl === null) {
    echo "NO Admin Notification feed\n";
    exit;
}

$out[] = '=== 模板 id=' . $tplId . '，含 Privacy 的行 ===';
foreach (explode("\n", $tpl) as $i => $ln) {
    if (stripos($ln, 'privacy') !== false) {
        $out[] = sprintf('  L%d> %s', $i, $ln);
    }
}

// ---- 4) 用 FF 自己渲染（isUrl=false, provider=false ⇒ 与 NotificationParser 完全同参）----
$parsed = \FluentForm\App\Services\FormBuilder\ShortCodeParser::parse($tpl, $sub->id, $data, $form, false, false);

$pos = stripos($parsed, 'Privacy Consent');
$frag = $pos === false
    ? '(未渲染出 Privacy Consent 字样)'
    : substr($parsed, max(0, $pos - 40), 320);

$out[] = '=== 真实渲染片段（原文，base64 便于逐字节核对）===';
$out[] = 'B64:' . base64_encode($frag);
$out[] = 'RAW> ' . str_replace(["\r", "\n"], ['\\r', '\\n'], substr($frag, 0, 200));

// ---- 5) 单独把该 key 交给渲染过滤器，看它返回什么 ----
$v = $data['privacy_consent_11'] ?? 'MISSING';
$rendered = apply_filters(
    'fluentform/response_render_input_checkbox',
    $v,
    $inputs['privacy_consent_11'] ?? [],
    $formId,
    false
);
$out[] = '=== 直接过 response_render_input_checkbox ===';
$out[] = '  in  = ' . var_export($v, true);
$out[] = '  out = ' . var_export($rendered, true);

// ---- 6) 对照实验：{inputs.privacy_consent_11} vs {inputs.privacy_consent_11.value}
//        分别用 isHtml=false（表单通知）与 isHtml=true（HTML 邮件分支）渲染 ----
$variants = [
    'plain {inputs.privacy_consent_11}'       => '{inputs.privacy_consent_11}',
    'dotvalue {inputs.privacy_consent_11.value}' => '{inputs.privacy_consent_11.value}',
];
foreach ($variants as $label => $code) {
    foreach ([false, true] as $isHtml) {
        $one = \FluentForm\App\Services\FormBuilder\ShortCodeParser::parse(
            'Privacy Consent: ' . $code . '<br />',
            $sub->id,
            $data,
            $form,
            false,
            $isHtml
        );
        $out[] = sprintf('  [%s | isHtml=%s] => %s', $label, $isHtml ? 'true' : 'false', $one);
    }
}

echo implode("\n", $out) . "\n";

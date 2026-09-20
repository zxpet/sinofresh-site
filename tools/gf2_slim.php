<?php
/**
 * Form 2「Get a Quote」精简：删 4 字段 + 6 字段设必填 + Admin 通知删 4 行
 * 用法：php -c <site>/conf/php/php.ini -d mysqli.default_socket=<sock> tools/gf2_slim.php <site_path> [--apply]
 * 不带 --apply 为 dry-run（只打印计划，不写库）
 */
$site  = $argv[1] ?? (getenv('HOME') . '/Local Sites/sinofresh/app/public');
$apply = in_array('--apply', $argv, true);
require_once rtrim($site, '/') . '/wp-load.php';
if (!class_exists('GFAPI')) { fwrite(STDERR, "GFAPI missing\n"); exit(1); }

const DEL      = [4, 6, 8, 9];                 // Phone/WhatsApp, Target Market, Estimated Quantity, Packaging Preference
const REQUIRED = [1, 2, 3, 5, 7, 11];          // Company, Contact, Email, Country, Dosage Form, Privacy Consent
const KEEP     = [12, 7];                      // 绝不能删
const DEL_LINE = [                             // Admin 通知正文待删行（前缀匹配）
    'Phone / WhatsApp:',
    'Target Market:',
    'Estimated Quantity:',
    'Packaging Preference:',
];

$form = GFAPI::get_form(2);
if (!$form) { fwrite(STDERR, "Form 2 not found\n"); exit(1); }

echo "MODE: " . ($apply ? "APPLY（写库）" : "DRY-RUN（只读）") . "\n";
echo "FORM 2 «{$form['title']}»  当前 fields=" . count($form['fields']) . "\n\n";

// ---------- 1. 前置断言：待删字段的 label 必须匹配 ----------
$expect = [4 => 'Phone / WhatsApp', 6 => 'Target Market', 8 => 'Estimated Quantity', 9 => 'Packaging Preference'];
$by_id  = [];
foreach ($form['fields'] as $f) { $by_id[(int)$f->id] = $f; }
$fail = [];
foreach ($expect as $id => $label) {
    if (!isset($by_id[$id]))                 { $fail[] = "field {$id} 不存在"; continue; }
    if (trim((string)$by_id[$id]->label) !== $label) { $fail[] = "field {$id} label 不符: '{$by_id[$id]->label}' != '{$label}'"; }
    if ((string)$by_id[$id]->type === 'hidden')      { $fail[] = "field {$id} 是 hidden，拒绝删除"; }
}
foreach (KEEP as $id) {
    if (!isset($by_id[$id])) { $fail[] = "保留字段 {$id} 不存在"; }
}
// 待删 ID 不得出现在 REQUIRED 里
foreach (DEL as $id) { if (in_array($id, REQUIRED, true)) $fail[] = "字段 {$id} 同时在删除与必填清单中"; }
if ($fail) { echo "❌ 前置断言失败:\n  - " . implode("\n  - ", $fail) . "\n"; exit(1); }
echo "✅ 前置断言通过（4 个待删字段 label 全部匹配，保留字段 12/7 在位）\n\n";

// ---------- 2. 字段删除 + 必填设置 ----------
$new_fields = [];
$removed = $kept = [];
foreach ($form['fields'] as $f) {
    $id = (int)$f->id;
    if (in_array($id, DEL, true)) { $removed[] = "{$id}({$f->type}:{$f->label})"; continue; }
    $want = in_array($id, REQUIRED, true);
    $had  = (bool)$f->isRequired;
    $f->isRequired = $want;
    $flag = ($want !== $had) ? ($want ? ' +必填' : ' -必填') : '';
    $kept[] = "{$id}({$f->label})" . ($want ? '[必填]' : '') . $flag;
    $new_fields[] = $f;
}
echo "删除(" . count($removed) . "): " . implode(', ', $removed) . "\n";
echo "保留(" . count($kept) . "): " . implode(', ', $kept) . "\n\n";
$form['fields'] = $new_fields;

// ---------- 3. Admin 通知正文删行 ----------
$msg_before = $form['notifications']['admin_notification']['message'];
$lines      = preg_split('/\R/', $msg_before);
$lines_out  = [];
$dropped    = [];
foreach ($lines as $ln) {
    $hit = false;
    foreach (DEL_LINE as $p) {
        if (strpos(ltrim($ln), $p) === 0) { $hit = true; $dropped[] = trim($ln); break; }
    }
    if (!$hit) { $lines_out[] = $ln; }
}
$msg_after = implode("\n", $lines_out);
echo "Admin 通知正文删除 " . count($dropped) . " 行:\n";
foreach ($dropped as $d) echo "   - {$d}\n";
if (count($dropped) !== 4) { echo "❌ 预期删 4 行，实际 " . count($dropped) . " 行，终止\n"; exit(1); }
// 断言剩余正文仍含保留字段标签、且不含待删标签
foreach ([1, 2, 3, 5, 7, 10, 11.1] as $n) {
    if (strpos($msg_after, ":{$n}}") === false) { echo "❌ 剩余正文丢失 {{...:{$n}}} 标签，终止\n"; exit(1); }
}
foreach (DEL as $n) {
    if (preg_match('/\{[^{}]*:' . $n . '\}/', $msg_after)) { echo "❌ 剩余正文仍含字段 {$n} 标签，终止\n"; exit(1); }
}
echo "✅ 正文仍含 1/2/3/5/7/10/11.1 标签，无 4/6/8/9 残留\n\n";
$form['notifications']['admin_notification']['message'] = $msg_after;

// ---------- 4. 写库 ----------
if (!$apply) { echo "（dry-run，未写库）\n"; exit(0); }
$r = GFAPI::update_form($form);
if (is_wp_error($r)) { echo "❌ update_form 失败: " . $r->get_error_message() . "\n"; exit(1); }
echo "✅ GFAPI::update_form 返回 true\n";

// ---------- 5. 回读校验 ----------
GFFormsModel::flush_current_form(GFFormsModel::get_form_cache_key(2));
$v = GFAPI::get_form(2);
$ids = array_map(fn($f) => (int)$f->id, $v['fields']);
$reqs = array_map(fn($f) => (int)$f->id . ($f->isRequired ? '=Y' : '=n'), $v['fields']);
echo "\n回读 fields=" . count($v['fields']) . "  ids=[" . implode(',', $ids) . "]\n";
echo "回读 必填: " . implode(' ', $reqs) . "\n";
$del_ok = !array_intersect(DEL, $ids);
$req_ok = true;
foreach ($v['fields'] as $f) {
    $want = in_array((int)$f->id, REQUIRED, true);
    if ((bool)$f->isRequired !== $want) $req_ok = false;
}
echo "待删字段已消失: " . ($del_ok ? '✅' : '❌') . "   必填标记正确: " . ($req_ok ? '✅' : '❌') . "\n";
echo "通知正文行数: " . count(preg_split('/\R/', $v['notifications']['admin_notification']['message'])) . "\n";
exit(($del_ok && $req_ok) ? 0 : 1);

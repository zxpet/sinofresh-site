<?php
/** 只读：列出所有 GF 表单概要 + 电话号码字段分布（判断 gform-phone__* CSS 是否仍需保留） */
$site = $argv[1] ?? (getenv('HOME') . '/Local Sites/sinofresh/app/public');
require_once rtrim($site, '/') . '/wp-load.php';
if (!class_exists('GFAPI')) { fwrite(STDERR, "GFAPI missing\n"); exit(1); }

$forms = GFAPI::get_forms(true, false);   // all, active only
foreach ($forms as $form) {
    echo "==================================================\n";
    echo "Form {$form['id']} «{$form['title']}»  fields=" . count($form['fields']) . "\n";
    $ids = [];
    foreach ($form['fields'] as $f) { $ids[] = sprintf('%s:%s%s', $f->id, $f->type, $f->isRequired ? '(req)' : ''); }
    echo '  ' . implode('  ', $ids) . "\n";
    $has_phone = false; $hidden = [];
    foreach ($form['fields'] as $f) {
        if ($f->type === 'phone') $has_phone = true;
        if ($f->type === 'hidden') $hidden[] = $f->id . ':' . $f->label . ' [' . ($f->cssClass ?? '') . ']';
    }
    echo '  hasPhoneField=' . ($has_phone ? 'YES' : 'no') . "\n";
    if ($hidden) echo '  hidden: ' . implode(' | ', $hidden) . "\n";
}
echo "\nDONE\n";

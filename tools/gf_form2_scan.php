<?php
/**
 * 只读扫描 Gravity Forms Form 2（Get a Quote）
 * 输出：字段清单 / notifications 合并标签引用 / confirmations 引用
 * 用法：
 *   php -c <site>/conf/php/php.ini -d mysqli.default_socket=<sock> tools/gf_form2_scan.php <site_path>
 */
$site = $argv[1] ?? (getenv('HOME') . '/Local Sites/sinofresh/app/public');
require_once rtrim($site, '/') . '/wp-load.php';

if (!class_exists('GFAPI')) {
    fwrite(STDERR, "GFAPI not available\n");
    exit(1);
}

$form = GFAPI::get_form(2);
if (!$form) {
    fwrite(STDERR, "Form 2 not found\n");
    exit(1);
}

echo "========================================\n";
echo "FORM 2 : " . $form['title'] . "  (id={$form['id']})\n";
echo "========================================\n";
echo "date_created : " . $form['date_created'] . "\n";
echo "is_active    : " . var_export($form['is_active'], true) . "\n";
echo "fields count : " . count($form['fields']) . "\n";
echo "\n---- FIELDS ----\n";
printf("%-6s %-16s %-34s %-10s %s\n", 'ID', 'TYPE', 'LABEL', 'REQUIRED', 'EXTRA');
foreach ($form['fields'] as $f) {
    $extra = [];
    if (!empty($f->choices)) {
        $labels = [];
        foreach ($f->choices as $c) {
            $labels[] = (string)$c['text'];
        }
        $extra[] = 'choices=[' . implode(' | ', $labels) . ']';
    }
    if (!empty($f->cssClass)) $extra[] = 'cssClass="' . $f->cssClass . '"';
    if (!empty($f->isHidden)) $extra[] = 'HIDDEN';
    if (!empty($f->visibility)) $extra[] = 'visibility=' . $f->visibility;
    if (isset($f->inputType) && !empty($f->inputType)) $extra[] = 'inputType=' . $f->inputType;
    if (!empty($f->defaultValue)) $extra[] = 'default="' . $f->defaultValue . '"';
    printf(
        "%-6s %-16s %-34s %-10s %s\n",
        $f->id,
        $f->type,
        mb_substr((string)$f->label, 0, 32),
        $f->isRequired ? 'YES' : '-',
        implode(' ', $extra)
    );
}

echo "\n---- NOTIFICATIONS (" . count($form['notifications']) . ") ----\n";
foreach ($form['notifications'] as $id => $n) {
    echo "\n### notification id = {$id}\n";
    echo "  name      : " . ($n['name'] ?? '') . "\n";
    echo "  event     : " . ($n['event'] ?? '') . "\n";
    echo "  to        : " . ($n['to'] ?? '') . "\n";
    echo "  from      : " . (($n['from'] ?? '') ?: '-') . "\n";
    echo "  toType    : " . ($n['toType'] ?? '') . "\n";
    echo "  disabled  : " . (!empty($n['isDisabled']) ? 'YES' : 'no') . "\n";
    echo "  -- subject --\n";
    echo "  " . str_replace("\n", "\n  ", (string)($n['subject'] ?? '')) . "\n";
    echo "  -- message --\n";
    echo "  " . str_replace("\n", "\n  ", (string)($n['message'] ?? '')) . "\n";
    // 列出所有 {..:N} 合并标签
    $merged = [];
    if (preg_match_all('/\{[^{}]*:(\d+)[^{}]*\}/', ($n['subject'] ?? '') . "\n" . ($n['message'] ?? ''), $m, PREG_SET_ORDER)) {
        foreach ($m as $one) $merged[] = $one[0];
    }
    echo "  -- merge tags found --\n";
    echo "  " . (count($merged) ? implode(', ', array_unique($merged)) : '(none)') . "\n";
}

echo "\n---- CONFIRMATIONS (" . count($form['confirmations']) . ") ----\n";
foreach ($form['confirmations'] as $id => $c) {
    echo "\n### confirmation id = {$id}\n";
    echo "  name : " . ($c['name'] ?? '') . "\n";
    echo "  type : " . ($c['type'] ?? '') . "\n";
    if (isset($c['message'])) {
        echo "  -- message --\n  " . str_replace("\n", "\n  ", (string)$c['message']) . "\n";
    }
    if (!empty($c['queryString'])) echo "  queryString : " . $c['queryString'] . "\n";
    if (!empty($c['url'])) echo "  url : " . $c['url'] . "\n";
    if (!empty($c['pageId'])) echo "  pageId : " . $c['pageId'] . "\n";
    $merged = [];
    if (preg_match_all('/\{[^{}]*:(\d+)[^{}]*\}/', json_encode($c), $m, PREG_SET_ORDER)) {
        foreach ($m as $one) $merged[] = $one[0];
    }
    echo "  -- merge tags --\n  " . (count($merged) ? implode(', ', array_unique($merged)) : '(none)') . "\n";
}

echo "\n---- OTHER FORM SETTINGS THAT MAY REFERENCE FIELDS ----\n";
echo "limitEntries       : " . var_export(!empty($form['limitEntries']), true) . "\n";
echo "requireLogin       : " . var_export(!empty($form['requireLogin']), true) . "\n";
echo "saveEnabled        : " . var_export(!empty($form['save']['enabled']), true) . "\n";
echo "personalData       : " . var_export(!empty($form['personalData']['preventIP']), true) . " (preventIP)\n";
if (!empty($form['pagination'])) echo "pagination steps   : " . count($form['pagination']['pages']) . "\n";
if (!empty($form['nextFieldId'])) echo "nextFieldId        : " . $form['nextFieldId'] . "\n";
echo "\nDONE\n";

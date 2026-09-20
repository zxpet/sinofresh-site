<?php
/**
 * 增强扫描 Gravity Forms Form 2（Get a Quote）——只读
 * 覆盖：字段必填/条件逻辑/栅格跨度、全表单对字段 ID 的引用、entry 样例、模板引用
 * 用法：
 *   php -c <site>/conf/php/php.ini -d mysqli.default_socket=<sock> tools/gf2_scan2.php <site_path>
 */
$site = $argv[1] ?? (getenv('HOME') . '/Local Sites/sinofresh/app/public');
require_once rtrim($site, '/') . '/wp-load.php';

if (!class_exists('GFAPI')) { fwrite(STDERR, "GFAPI missing\n"); exit(1); }
$form = GFAPI::get_form(2);
if (!$form) { fwrite(STDERR, "Form 2 not found\n"); exit(1); }

$DEL = [4, 6, 8, 9];          // 计划删除：Phone/WhatsApp, Target Market, Estimated Quantity, Packaging Preference
$KEEP_CRIT = [12, 7];         // 绝不能删：Configuration Summary, Interested Dosage Form

echo "FORM 2 «{$form['title']}»  fields=" . count($form['fields']) . "\n\n";

echo "==== 1. 字段全属性 ====\n";
printf("%-4s %-10s %-24s %-9s %-6s %-6s %-22s %s\n", 'ID', 'TYPE', 'LABEL', 'REQUIRED', 'PAGE', 'SPAN', 'cssClass', 'conditionalLogic');
foreach ($form['fields'] as $f) {
    $cl = '-';
    if (!empty($f->conditionalLogic) && !empty($f->conditionalLogic['enabled'])) {
        $logic = $f->conditionalLogic;
        $rules = [];
        foreach (($logic['rules'] ?? []) as $r) {
            $rules[] = sprintf('field %s %s %s', $r['fieldId'], $r['operator'], is_array($r['value'] ?? null) ? implode('/', $r['value']) : ($r['value'] ?? ''));
        }
        $cl = strtoupper($logic['actionType'] ?? 'show') . ' if ' . implode(' ' . ($logic['logicType'] ?? 'all') . ' ', $rules);
    }
    printf("%-4s %-10s %-24s %-9s %-6s %-6s %-22s %s\n",
        $f->id, $f->type, mb_substr((string)$f->label, 0, 22),
        $f->isRequired ? 'YES' : 'no',
        $f->pageNumber ?? 1,
        $f->layoutGridColumnSpan ?? '-',
        (string)($f->cssClass ?? '-'),
        $cl
    );
}

echo "\n==== 2. 全表单 JSON 中对 4 个待删 ID 的引用 ====\n";
$json = wp_json_encode($form);
foreach ($DEL as $id) {
    $hits = [];
    // 合并标签 {Label:ID}
    if (preg_match_all('/\{[^{}]*:' . $id . '(?:\.[0-9]+)?\}/', $json, $m)) { $hits[] = 'merge:' . implode(',', array_unique($m[0])); }
    // conditionalLogic 的 fieldId
    if (preg_match_all('/"fieldId":"?' . $id . '"?/', $json, $m)) { $hits[] = 'conditionalLogic.fieldId×' . count($m[0]); }
    // 其它裸引用
    if (preg_match_all('/"`?customField`?":' . $id . '/', $json, $m)) { $hits[] = 'customField×' . count($m[0]); }
    printf("  field %-3s → %s\n", $id, $hits ? implode(' ; ', $hits) : '无引用');
}

echo "\n==== 3. 通知 / 自动回复 / 确认 中逐标签归属 ====\n";
$label_of = [];
foreach ($form['fields'] as $f) { $label_of[(string)$f->id] = (string)$f->label; }
$sections = [];
foreach ($form['notifications'] as $nid => $n) {
    $sections["notification:$nid ({$n['name']})"] = ($n['subject'] ?? '') . "\n" . ($n['message'] ?? '');
}
foreach ($form['confirmations'] as $cid => $c) {
    $sections["confirmation:$cid ({$c['name']})"] = wp_json_encode($c);
}
foreach ($sections as $sname => $blob) {
    echo "\n-- $sname --\n";
    if (!preg_match_all('/\{[^{}]*?:(\d+)(?:\.\d+)?\}/', $blob, $m, PREG_SET_ORDER)) { echo "   (无合并标签)\n"; continue; }
    $seen = [];
    foreach ($m as $one) {
        $fid = $one[1];
        $seen[$fid][] = $one[0];
    }
    foreach ($seen as $fid => $tags) {
        $mark = in_array((int)$fid, $DEL, true) ? '❌待删' : (in_array((int)$fid, $KEEP_CRIT, true) ? '★必留' : '·保留');
        printf("   %-6s field %-3s %-24s %s\n", $mark, $fid, $label_of[$fid] ?? '(未知)', implode(', ', array_unique($tags)));
    }
}

echo "\n==== 4. Entries（提交记录）====\n";
$count = GFAPI::count_entries(2);
echo "总条数 : {$count}\n";
if ($count) {
    $entries = GFAPI::get_entries(2, ['status' => 'active'], null, ['offset' => 0, 'page_size' => 3], $total);
    foreach ($entries as $i => $e) {
        echo "\n-- entry #{$e['id']} ({$e['date_created']}) --\n";
        foreach ($form['fields'] as $f) {
            $val = GFFormsModel::get_lead_field_value($e, $f);
            if (is_array($val)) $val = implode(' | ', array_filter($val));
            printf("   field %-3s %-24s = %s\n", $f->id, $f->label, mb_substr((string)$val, 0, 70));
        }
    }
} else {
    echo "（尚无提交记录）\n";
}

echo "\n==== 5. 模板 / 页面中对 Form 2 的引用 ====\n";
$theme = get_stylesheet_directory();
$files = array_merge(glob($theme . '/templates/*.html'), glob($theme . '/parts/*.html'), [$theme . '/functions.php', $theme . '/style.css']);
$hits = 0;
foreach ($files as $file) {
    $c = file_get_contents($file);
    if (preg_match_all('/(gravityform[^\'"]{0,40}|gravityforms[^\'" ]{0,30}|gform[_-][a-z0-9_-]+)/i', $c, $m)) {
        $uniq = array_unique($m[0]);
        echo '  ' . str_replace($theme . '/', '', $file) . ' → ' . implode(', ', array_slice($uniq, 0, 6)) . "\n";
        $hits++;
    }
}
if (!$hits) echo "  （主题文件中无引用）\n";

echo "\n==== 6. 表单渲染相关全局设置 ====\n";
foreach (['cssClass', 'enableHoneypot', 'enableAnimation', 'requiredIndicator', 'labelPlacement', 'descriptionPlacement', 'subLabelPlacement', 'formLayout', 'button'] as $k) {
    if (isset($form[$k])) {
        echo "  $k = " . (is_array($form[$k]) ? wp_json_encode($form[$k]) : var_export($form[$k], true)) . "\n";
    }
}
echo "\nDONE\n";

<?php
/** H24b 探测 v2 —— 摸清 form_fields 的层级与「叶子字段」路径（只读） */
if (!defined('ABSPATH')) { fwrite(STDERR, "[ERR] wp eval-file only\n"); exit(1); }
global $wpdb;
$P = $wpdb->prefix;

$ff  = $wpdb->get_var($wpdb->prepare("SELECT form_fields FROM {$P}fluentform_forms WHERE id=%d", 8));
$arr = json_decode($ff, true);
echo 'json_err=' . json_last_error_msg() . "\n";
echo 'top_type=' . gettype($arr) . "\n";
if (is_array($arr)) {
    echo 'top_keys=' . implode(',', array_map(function ($k) { return $k . '(' . gettype($k) . ')'; }, array_keys($arr))) . "\n";
    foreach ($arr as $k => $v) {
        printf("  key[%s] type=%s", $k, gettype($v));
        if (is_array($v)) { echo ' count=' . count($v) . ' sub_keys=' . implode(',', array_slice(array_keys(reset($v) ?: array()), 0, 12)); }
        echo "\n";
    }
}

/* 递归找出所有带 attributes.name 的叶子字段 */
$leaves = array();
$walk = function ($node, $path) use (&$walk, &$leaves) {
    if (!is_array($node)) { return; }
    if (isset($node['attributes']) && isset($node['attributes']['name'])) {
        $leaves[] = array(
            'path'   => $path,
            'element'=> isset($node['element']) ? $node['element'] : '?',
            'name'   => $node['attributes']['name'],
            'label'  => isset($node['settings']['label']) ? $node['settings']['label'] : '',
            'admin'  => isset($node['settings']['admin_label']) ? $node['settings']['admin_label'] : '',
            'opts'   => isset($node['settings']['advanced_options']) && is_array($node['settings']['advanced_options'])
                        ? count($node['settings']['advanced_options']) : 0,
        );
        return;
    }
    foreach ($node as $k => $v) {
        if (is_array($v)) { $walk($v, $path . '/' . $k); }
    }
};
$walk($arr, '');

echo "\n=== form 8 叶子字段 " . count($leaves) . " 个 ===\n";
foreach ($leaves as $i => $L) {
    printf("%2d %-20s name=%-30s label=%-30s opts=%d\n", $i, $L['element'], $L['name'], $L['label'], $L['opts']);
}

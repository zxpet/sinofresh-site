<?php
/**
 * 导出指定 GF 表单为 JSON 备份到 _backup/
 * 用法：php -d mysqli.default_socket=<sock> tools/gf_dump_form.php <site_path> <dir> <form_id...>
 */
$site = $argv[1];
$dir  = $argv[2];
$ids  = array_slice($argv, 3);
require_once rtrim($site, '/') . '/wp-load.php';
if (!class_exists('GFAPI')) { fwrite(STDERR, "GFAPI missing\n"); exit(1); }
if (!is_dir($dir)) mkdir($dir, 0755, true);
foreach ($ids as $id) {
    $form = GFAPI::get_form((int)$id);
    if (!$form) { echo "form {$id}: NOT FOUND\n"; continue; }
    $file = rtrim($dir, '/') . "/form-{$id}.json";
    file_put_contents($file, json_encode($form, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES));
    echo "form {$id} -> {$file}  (" . filesize($file) . " bytes, fields=" . count($form['fields']) . ")\n";
}

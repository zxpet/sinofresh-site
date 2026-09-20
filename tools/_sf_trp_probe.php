<?php
/* Standard Formulas + CPT 扫描：打印 TranslatePress 关键设置（只读） */
$sock = getenv('HOME') . '/Library/Application Support/Local/run/cVn1NjBpB/mysql/mysqld.sock';
$db = new mysqli('localhost', 'root', 'root', 'local', null, $sock);
if ($db->connect_error) { fwrite(STDERR, "DB fail: " . $db->connect_error . "\n"); exit(1); }

function opt($db, $name) {
    $st = $db->prepare("SELECT option_value FROM wp_options WHERE option_name=? LIMIT 1");
    $st->bind_param('s', $name); $st->execute();
    $r = $st->get_result()->fetch_row();
    return $r ? maybe_unserialize_($r[0]) : null;
}
function maybe_unserialize_($v) { $u = @unserialize($v); return $u === false ? $v : $u; }

echo "=== trp_settings ===\n";
print_r(opt($db, 'trp_settings'));

$adv = opt($db, 'trp_advanced_settings');
echo "\n=== trp_advanced_settings（键 → 值概要）===\n";
foreach ((array) $adv as $k => $v) {
    echo str_pad($k, 46) . ' : ';
    if (is_array($v)) {
        $flat = json_encode($v, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
        echo (strlen($flat) > 200 ? substr($flat, 0, 200) . ' …(' . strlen($flat) . ')' : $flat) . "\n";
    } else {
        echo var_export($v, true) . "\n";
    }
}
echo "\n=== trp_post_type_base_slug_translation ===\n";
print_r(opt($db, 'trp_post_type_base_slug_translation'));
echo "\n=== trp_taxonomy_slug_translation ===\n";
print_r(opt($db, 'trp_taxonomy_slug_translation'));

echo "\n=== trp_* 数据表 ===\n";
$r = $db->query("SHOW TABLES LIKE 'wp_trp%'");
$n = 0;
while ($row = $r->fetch_row()) { echo '  ' . $row[0] . "\n"; $n++; }
if (!$n) { echo "  （无 wp_trp_* 表）\n"; }

echo "\n=== 现有 post 型内容（用于对照 CPT 行为）===\n";
$r = $db->query("SELECT ID, post_type, post_name, post_status FROM wp_posts WHERE post_status='publish' AND post_type IN ('post','page','language_switcher') ORDER BY post_type, ID");
while ($row = $r->fetch_row()) {
    echo sprintf("  %-5s %-20s %-30s %s\n", $row[0], $row[1], $row[2], $row[3]);
}
$db->close();

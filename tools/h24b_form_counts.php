<?php
/**
 * H24b — 各表单「条目状态分布」一览（只读诊断，dev / prod 通用）
 *
 * 用法
 *   wp eval-file /root/h24-tools/h24b_form_counts.php --allow-root
 *
 * 用途
 *   1) 部署前后确认条目分布没被动过（零污染回归）
 *   2) 找出「未读 = 0」的表单 id —— 浏览器空状态断言需要一个真实的无未读表单，
 *      而生产 form 8 长期就是这个状态，dev 上往往是别人，所以脚本把候选打出来。
 *
 * ⚠️ wp eval-file 不在全局作用域 ⇒ 计数一律走 $GLOBALS。
 */

if (!defined('ABSPATH')) {
    fwrite(STDERR, "[ERR] 必须通过 wp eval-file 执行\n");
    exit(1);
}

global $wpdb;

$p = $wpdb->prefix;

// phpcs:ignore WordPress.DB.DirectDatabaseQuery
$rows = $wpdb->get_results(
    "SELECT form_id, status, COUNT(*) AS n FROM {$p}fluentform_submissions GROUP BY form_id, status ORDER BY form_id",
    ARRAY_A
);

$by = array();
foreach ((array) $rows as $r) {
    $by[(int) $r['form_id']][(string) $r['status']] = (int) $r['n'];
}

// phpcs:ignore WordPress.DB.DirectDatabaseQuery
$forms = $wpdb->get_results("SELECT id, title FROM {$p}fluentform_forms ORDER BY id", ARRAY_A);

$empty_unread = array();
$grand        = 0;

fwrite(STDOUT, "form_id | unread | read | spam | trashed | all(Σ−trashed) | title\n");
fwrite(STDOUT, str_repeat('-', 78) . "\n");

foreach ((array) $forms as $f) {
    $id = (int) $f['id'];
    $m  = isset($by[$id]) ? $by[$id] : array();

    $u = isset($m['unread']) ? $m['unread'] : 0;
    $rd = isset($m['read']) ? $m['read'] : 0;
    $sp = isset($m['spam']) ? $m['spam'] : 0;
    $tr = isset($m['trashed']) ? $m['trashed'] : 0;
    $sum = array_sum($m);
    $all = max(0, $sum - $tr);

    $grand += $all;

    fwrite(STDOUT, sprintf(
        "%7d | %6d | %4d | %4d | %7d | %13d | %s\n",
        $id,
        $u,
        $rd,
        $sp,
        $tr,
        $all,
        $f['title']
    ));

    if (0 === $u) {
        $empty_unread[] = $id;
    }
}

fwrite(STDOUT, str_repeat('-', 78) . "\n");
fwrite(STDOUT, sprintf("所有表单 all 合计 = %d\n", $grand));
fwrite(STDOUT, '未读=0 的表单 id（可直接给浏览器空状态断言当夹具）: ' .
    (empty($empty_unread) ? '（无）' : implode(',', $empty_unread)) . "\n");

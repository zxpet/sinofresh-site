<?php
/**
 * H24b/C —— 用 FluentForm 自己的判据，验证「哪些通知 feed 真的会被发送」
 *
 * 目的：停用 Auto Reply 后，不能只看 DB 里的 enabled 字段（那是我们的推断），
 *       要**直接调用 FF 生产路径上用的那个函数**：
 *           FluentForm\App\Services\Integrations\GlobalNotificationManager::getEnabledFeeds()
 *       它是 EmailNotificationActions 在提交时真正用来筛选 feed 的入口，
 *       内部判据是 `ArrayHelper::isTrue($parsedValue, 'enabled')` + checkCondition()。
 *
 * 关键：加**正对照** —— form 8 的 Admin Notification（enabled=true、无条件）
 *       必须出现在结果里，否则说明本次调用本身没跑通（假绿）。
 *
 * 用法
 *   SF_H24B_SITE=prod wp eval-file … --allow-root
 *
 * 退出码  0 全部符合预期 / 1 非 WP / 4 断言失败
 */

if (!defined('ABSPATH')) { fwrite(STDERR, "[ERR] 必须通过 wp eval-file 执行\n"); exit(1); }

global $wpdb;
$P    = $wpdb->prefix;
$site = (getenv('SF_H24B_SITE') === 'prod') ? 'prod' : 'dev';
$RC   = 0;

$FORM_TITLES = array();
$rows = $wpdb->get_results("SELECT id,title FROM {$P}fluentform_forms WHERE id IN (8,9,10,11,12)", ARRAY_A);
foreach ($rows as $r) { $FORM_TITLES[(int) $r['id']] = $r['title']; }

$mgr = new \FluentForm\App\Services\Integrations\GlobalNotificationManager(wpFluentForm());

echo "=========== FF 实际会发送的通知 feed（site={$site}）===========\n";

$allEnabledMetaIds = array();
$perForm = array();

foreach (array(8, 9, 10, 11, 12) as $fid) {
    $feeds = wpFluent()->table('fluentform_form_meta')
        ->where('form_id', $fid)
        ->where('meta_key', 'notifications')
        ->get();

    if (!$feeds) { continue; }

    /* 用空 formData 调 —— 无条件的 feed 应直接通过 enabled 判定 */
    $enabled = $mgr->getEnabledFeeds($feeds, array(), 0);
    $enIds = array();
    foreach ($enabled as $e) { $enIds[] = (int) $e['id']; }

    echo "\nform {$fid} [{$FORM_TITLES[$fid]}]\n";
    foreach ($feeds as $f) {
        $d     = json_decode($f->value, true);
        $name  = isset($d['name']) ? $d['name'] : '?';
        $enRaw = array_key_exists('enabled', $d) ? $d['enabled'] : null;
        $isT   = class_exists('\FluentForm\Framework\Helpers\ArrayHelper')
               ? \FluentForm\Framework\Helpers\ArrayHelper::isTrue($d, 'enabled')
               : (bool) $enRaw;
        $will  = in_array((int) $f->id, $enIds, true);
        printf("  meta_id=%-3d [%-26s] enabled=%-5s isTrue=%-5s → 会被发送=%s\n",
            (int) $f->id, $name, var_export($enRaw, true), $isT ? 'true' : 'false', $will ? 'YES' : 'no');
        if ($will) { $allEnabledMetaIds[] = (int) $f->id; }
    }
    $perForm[$fid] = $enIds;
}

echo "\n--- 断言 ---\n";

/* 正对照：form 8 feed 39（Admin Notification，enabled=true）必须会被发送 */
$pos = in_array(39, $allEnabledMetaIds, true);
echo ($pos ? '  [PASS] ' : '  [FAIL] ')
   . "正对照：form 8 管理员通知(39) 会被发送（证明本次调用有效、不是假绿）\n";
if (!$pos) { $RC = 4; }

/* 核心：三个 Auto Reply feed（46/52/58）必须**不**会被发送 */
$autoIds = array(46, 52, 58);
$bad = array();
foreach ($autoIds as $m) {
    if (in_array($m, $allEnabledMetaIds, true)) { $bad[] = $m; }
}
echo ($bad ? '  [FAIL] ' : '  [PASS] ')
   . 'Auto Reply feed 46/52/58 全部不再发送' . ($bad ? '（仍会发送: ' . implode(',', $bad) . '）' : '') . "\n";
if ($bad) { $RC = 4; }

/* form 8 的 Auto Reply（40）本来就该是关的 */
$b40 = in_array(40, $allEnabledMetaIds, true);
echo ($b40 ? '  [FAIL] ' : '  [PASS] ') . "form 8 Auto Reply feed 40 不发送\n";
if ($b40) { $RC = 4; }

/* 管理员通知（39/45/51/57/63）必须**全部**仍然发送 —— 停用自动回复不能误伤管理员通知 */
$adminIds = array(39, 45, 51, 57, 63);
$miss = array();
foreach ($adminIds as $m) {
    if (!in_array($m, $allEnabledMetaIds, true)) { $miss[] = $m; }
}
echo ($miss ? '  [FAIL] ' : '  [PASS] ')
   . '5 个管理员通知 feed 全部正常发送' . ($miss ? '（缺失: ' . implode(',', $miss) . '）' : '') . "\n";
if ($miss) { $RC = 4; }

echo "\n本批生效的 feed（会被发送）meta_id = " . implode(',', $allEnabledMetaIds) . "\n";
echo "\n===== site={$site} 退出码={$RC} =====\n";
exit($RC);

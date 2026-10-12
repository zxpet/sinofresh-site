<?php
/**
 * H24 — L5 后台复核 / 黑名单 / 告警治理层验收
 *
 * 覆盖用户三条补充中的第 2、3 条：
 *   ② 后台"人工复核"入口：看 spam 列表、能改回正常、能一键加黑名单
 *   ③ 告警阈值（当日 spam > 50 发一封）+ 频率控制（一天最多 1 封）
 *
 * 数据安全：
 *   · 只读断言（菜单/nonce/capability/函数存在）——任何站点都跑
 *   · 写路径验证（造行 → release / 加黑 → 移除 / 告警计数）——仅在 SF_H24_L5_WRITE=1 时跑，
 *     且**自带清理**；告警用 pre_wp_mail 短路，绝不真发信。
 *
 * 用法
 *   SF_H24_SITE=dev  SF_H24_L5_WRITE=1 wp eval-file /root/h24-tools/h24_prod_l5.php --allow-root
 *   SF_H24_SITE=prod                  wp eval-file /root/h24-tools/h24_prod_l5.php --allow-root
 *
 * 退出码：0 全通过 / 4 有 FAIL
 */

if (!defined('ABSPATH')) {
    fwrite(STDERR, "[ERR] 必须通过 wp eval-file 执行\n");
    exit(1);
}

global $wpdb;

$site  = getenv('SF_H24_SITE');
$site  = in_array($site, array('dev', 'prod'), true) ? $site : 'dev';
$write = ('1' === (string) getenv('SF_H24_L5_WRITE'));

$LOG   = $wpdb->prefix . SF_FG_LOG_TABLE;
$SUB   = $wpdb->prefix . 'fluentform_submissions';

$pass = 0;
$fail = 0;

function sf_h24_l5_out($s)
{
    fwrite(STDOUT, $s . "\n");
}

function sf_h24_l5_check($name, $ok, $detail = '')
{
    if ($ok) {
        $GLOBALS['h24_l5_pass'] = (int) ($GLOBALS['h24_l5_pass'] ?? 0) + 1;
        sf_h24_l5_out('  [ OK ] ' . $name . ($detail ? '  | ' . $detail : ''));
    } else {
        $GLOBALS['h24_l5_fail'] = (int) ($GLOBALS['h24_l5_fail'] ?? 0) + 1;
        sf_h24_l5_out('  [FAIL] ' . $name . ($detail ? '  | ' . $detail : ''));
    }
}

$GLOBALS['h24_l5_pass'] = 0;
$GLOBALS['h24_l5_fail'] = 0;

sf_h24_l5_out("== H24 L5 后台复核/黑名单/告警 [site={$site}] write=" . ($write ? 'yes' : 'no') . " ==");

/* =====================================================================
 * A. 只读断言
 * ================================================================== */
sf_h24_l5_out("\n=== A. 只读断言（菜单 / nonce / capability / 函数） ===");

/* A1 菜单注册：触发 admin_menu 后检查全局 $menu */
$menu_slug = '';
do_action('admin_menu');
foreach ((array) $GLOBALS['menu'] as $m) {
    if (isset($m[2]) && 'sf-form-guard' === $m[2]) {
        $menu_slug = $m[2];
        $cap       = isset($m[1]) ? $m[1] : '';
        break;
    }
}
sf_h24_l5_check('后台菜单 sf-form-guard 已注册', '' !== $menu_slug, $menu_slug ?: '(未找到)');

/* A2 渲染回调存在 */
sf_h24_l5_check('复核页渲染函数存在', function_exists('sf_fg_render_admin_page'));
sf_h24_l5_check('release（改回正常）函数存在', function_exists('sf_fg_release_row'));
sf_h24_l5_check('黑名单 增/删/命中 三函数齐备',
    function_exists('sf_fg_blocklist_add') && function_exists('sf_fg_blocklist_remove')
    && function_exists('sf_fg_blocklist_hit'));
sf_h24_l5_check('告警函数存在', function_exists('sf_fg_alert_tick') && function_exists('sf_fg_send_alert'));

/* A3 源码级断言：capability / nonce / referer 检查 */
$raw = @file_get_contents(ABSPATH . 'wp-content/mu-plugins/zz-sf-form-guard.php');
if (is_string($raw) && '' !== $raw) {
    sf_h24_l5_check('菜单使用 manage_options 权限', false !== strpos($raw, "'manage_options'"));
    sf_h24_l5_check('表单提交带 nonce 校验（sf_fg_nonce）', false !== strpos($raw, "wp_nonce_field( 'sf_fg_admin', 'sf_fg_nonce' )"));
    // 注：实现用 wp_verify_nonce（与 check_admin_referer 等价），且顺序为「先判权限、再验 nonce」
    sf_h24_l5_check('后台动作服务端验 nonce（wp_verify_nonce）',
        false !== strpos($raw, 'wp_verify_nonce'));
    sf_h24_l5_check('后台动作先校验 manage_options 权限',
        false !== strpos($raw, "current_user_can( 'manage_options' )"));
} else {
    sf_h24_l5_out('  [SKIP] 读不到 mu-plugin 源码，跳过源码级断言');
}

/* A4 告警阈值常量为 50 */
sf_h24_l5_check('告警阈值常量 = 50', 50 === (int) SF_FG_ALERT_THRESHOLD, (string) SF_FG_ALERT_THRESHOLD);

/* =====================================================================
 * B. 写路径验证（仅在 SF_H24_L5_WRITE=1）
 * ================================================================== */
if (!$write) {
    sf_h24_l5_out("\n=== B. 写路径验证 —— 已跳过（未设 SF_H24_L5_WRITE=1） ===");
    sf_h24_l5_out("\n== 结果：{$GLOBALS['h24_l5_pass']} passed, {$GLOBALS['h24_l5_fail']} failed ==");
    exit(((int) $GLOBALS['h24_l5_fail']) > 0 ? 4 : 0);
}

sf_h24_l5_out("\n=== B. 写路径验证（自带清理） ===");

$now      = current_time('mysql');
$sub_id   = 0;
$log_id   = 0;
$bl_before = sf_fg_blocklist();
$al_before = get_option(SF_FG_ALERT_OPT, null);
$sub_before = (int) $wpdb->get_var("SELECT COUNT(*) FROM {$SUB} WHERE form_id=8");
$log_before = (int) $wpdb->get_var("SELECT COUNT(*) FROM {$LOG}");

try {
    /* ---- B1 造一条 spam 提交 + 审计行（模拟被拦） ---- */
    $serial = (int) $wpdb->get_var("SELECT serial_number FROM {$SUB} WHERE form_id=8 ORDER BY id DESC LIMIT 1") + 1;
    $ok = $wpdb->insert($SUB, array(
        'form_id'       => 8,
        'serial_number' => $serial,
        'response'      => wp_json_encode(array('company_name_1' => 'H24L5TestCo', 'contact_person_2' => 'L5Ton')),
        'source_url'    => site_url('/contact/'),
        'user_id'       => 0,
        'status'        => 'spam',
        'browser'       => 'Chrome',
        'device'        => 'Desktop',
        'ip'            => '203.0.113.99',
        'created_at'    => $now,
        'updated_at'    => $now,
    ));
    $sub_id = $ok ? (int) $wpdb->insert_id : 0;
    sf_h24_l5_check('B1 造 spam 提交行', $sub_id > 0, 'id=' . $sub_id);

    $wpdb->insert($LOG, array(
        'form_id' => 8, 'submission_id' => $sub_id, 'created_at' => $now,
        'ip' => '203.0.113.99', 'edge_ip' => '', 'ua' => 'h24-l5-probe',
        'country' => 'Germany', 'email_domain' => 'example.com', 'score' => 5,
        'signals' => 'S1_shared_suffix,S2_template_message', 'signature' => str_repeat('a', 64),
        'source' => 'score', 'released' => 0, 'released_at' => null,
    ));
    $log_id = (int) $wpdb->insert_id;
    sf_h24_l5_check('B1 造审计行', $log_id > 0, 'id=' . $log_id);

    /* ---- B2 release：改回正常 ---- */
    $r = sf_fg_release_row($log_id);
    sf_h24_l5_check('B2 release 返回 true', (bool) $r);
    $st = $wpdb->get_var($wpdb->prepare("SELECT status FROM {$SUB} WHERE id=%d", $sub_id));
    sf_h24_l5_check('B2 提交行状态 spam -> unread', 'unread' === $st, (string) $st);
    $lg = $wpdb->get_row($wpdb->prepare("SELECT released, released_at FROM {$LOG} WHERE id=%d", $log_id), ARRAY_A);
    sf_h24_l5_check('B2 审计行 released=1', isset($lg['released']) && 1 === (int) $lg['released'],
        json_encode($lg));
    sf_h24_l5_check('B2 审计行 released_at 非空', !empty($lg['released_at']), (string) ($lg['released_at'] ?? ''));

    /* ---- B3 一键加黑名单（IP）+ 命中 + 移除 ---- */
    sf_h24_l5_check('B3 基线黑名单为空', 0 === count($bl_before), (string) count($bl_before));
    $added = sf_fg_blocklist_add('ip', '203.0.113.99', 'h24-l5-probe');
    sf_h24_l5_check('B3 加黑返回 true', (bool) $added);
    sf_h24_l5_check('B3 命中已加黑的 IP', 'ip' === sf_fg_blocklist_hit('203.0.113.99', '', ''),
        sf_fg_blocklist_hit('203.0.113.99', '', ''));
    sf_h24_l5_check('B3 未加黑的 IP 不命中', '' === sf_fg_blocklist_hit('198.51.100.7', '', ''),
        sf_fg_blocklist_hit('198.51.100.7', '', ''));
    sf_h24_l5_check('B3 黑名单长度 +1', count(sf_fg_blocklist()) === count($bl_before) + 1,
        (string) count(sf_fg_blocklist()));
    $removed = sf_fg_blocklist_remove(0);
    sf_h24_l5_check('B3 移除返回 true', (bool) $removed);
    sf_h24_l5_check('B3 移除后长度回基线', count(sf_fg_blocklist()) === count($bl_before),
        (string) count(sf_fg_blocklist()));

    /* ---- B4 告警：阈值触发 + 当天只一封 ---- */
    $GLOBALS['h24_l5_mail'] = 0;
    add_filter('pre_wp_mail', function ($return, $atts) {
        $GLOBALS['h24_l5_mail']++;
        return true;   // 短路：真发信被拦掉，只计数
    }, 10, 2);
    add_filter('sf_fg_alert_threshold', function () { return 1; });   // 降到 1 便于触发

    delete_option(SF_FG_ALERT_OPT);   // 清空当日状态，从 0 开始
    sf_fg_alert_tick();
    $st1 = get_option(SF_FG_ALERT_OPT, array());
    sf_h24_l5_check('B4 首次 tick 触发告警（发 1 封）', 1 === (int) $GLOBALS['h24_l5_mail'],
        'mails=' . $GLOBALS['h24_l5_mail']);
    sf_h24_l5_check('B4 告警状态 sent=true', !empty($st1['sent']), json_encode($st1));

    sf_fg_alert_tick();
    sf_fg_alert_tick();
    sf_h24_l5_check('B4 同日再 tick 不再发信（频率控制，仍为 1 封）',
        1 === (int) $GLOBALS['h24_l5_mail'], 'mails=' . $GLOBALS['h24_l5_mail']);
    $st2 = get_option(SF_FG_ALERT_OPT, array());
    sf_h24_l5_check('B4 计数继续累加（count>=3）', (int) ($st2['count'] ?? 0) >= 3, json_encode($st2));
    sf_h24_l5_check('B4 告警日期为当天', (string) ($st2['date'] ?? '') === wp_date('Y-m-d'), (string) ($st2['date'] ?? ''));

} finally {
    /* ---- 清理 ---- */
    sf_h24_l5_out("\n=== 清理 ===");
    if ($log_id) {
        $wpdb->query($wpdb->prepare("DELETE FROM {$LOG} WHERE id=%d", $log_id));
    }
    if ($sub_id) {
        $wpdb->query($wpdb->prepare("DELETE FROM {$SUB} WHERE id=%d", $sub_id));
    }
    /* 黑名单还原到基线 */
    update_option(SF_FG_BLOCKLIST_OPT, array_values($bl_before), false);
    /* 告警状态还原到基线 */
    if (null === $al_before) {
        delete_option(SF_FG_ALERT_OPT);
    } else {
        update_option(SF_FG_ALERT_OPT, $al_before, false);
    }

    $sub_left = (int) $wpdb->get_var("SELECT COUNT(*) FROM {$SUB} WHERE form_id=8");
    $log_left = (int) $wpdb->get_var("SELECT COUNT(*) FROM {$LOG}");
    $bl_left  = count(sf_fg_blocklist());
    $al_left  = get_option(SF_FG_ALERT_OPT, null);
    sf_h24_l5_out("  提交 {$sub_before}->{$sub_left}  审计 {$log_before}->{$log_left}  黑名单={$bl_left}  告警状态=" .
        (null === $al_left ? '(已删)' : json_encode($al_left)));
    sf_h24_l5_check('清理：提交数回基线', $sub_left === $sub_before, "{$sub_left} vs {$sub_before}");
    sf_h24_l5_check('清理：审计表回基线', $log_left === $log_before, "{$log_left} vs {$log_before}");
    sf_h24_l5_check('清理：黑名单回基线', $bl_left === count($bl_before), (string) $bl_left);
    sf_h24_l5_check('清理：告警状态回基线', $al_left == $al_before,
        null === $al_before ? '(应为已删)' : json_encode($al_left));
}

sf_h24_l5_out("\n== 结果：{$GLOBALS['h24_l5_pass']} passed, {$GLOBALS['h24_l5_fail']} failed ==");
exit(((int) $GLOBALS['h24_l5_fail']) > 0 ? 4 : 0);

<?php
/**
 * H24b — L1/L3/L5 断言（在 WP 上下文内跑，dev / prod 通用）
 *
 * 用法
 *   SF_H24B_SITE=dev  wp eval-file /root/h24-tools/h24b_l1.php --allow-root
 *   SF_H24B_SITE=prod wp eval-file /root/h24-tools/h24b_l1.php --allow-root
 *
 * 覆盖
 *   L1 配置层：常量、FF 兜底阈值、cron 注册、条目默认筛选
 *   L3 决策层：精细限流计数器（bump / 达限 / 过期语义）、被拦计数
 *   L5 治理层：清理任务（幂等 + 真删）、告警正文含行数、自动加黑（构造 50 条）
 *
 * 零污染：所有构造数据都用 RFC5737 测试网段 `203.0.113.77`，跑完即删；
 *         黑名单条目与 transient 一并清理。
 *
 * ⚠️ wp eval-file 不在全局作用域 ⇒ 计数器一律走 $GLOBALS。
 */

if (!defined('ABSPATH')) {
    fwrite(STDERR, "[ERR] 必须通过 wp eval-file 执行\n");
    exit(1);
}

$GLOBALS['h24b_pass'] = 0;
$GLOBALS['h24b_fail'] = 0;
$GLOBALS['h24b_site'] = in_array(getenv('SF_H24B_SITE'), array('dev', 'prod'), true) ? getenv('SF_H24B_SITE') : 'dev';

$TEST_IP = '203.0.113.77'; // RFC 5737 TEST-NET-3

function sf_h24b_check($label, $cond, $detail = '')
{
    if ($cond) {
        $GLOBALS['h24b_pass']++;
        fwrite(STDOUT, sprintf("  PASS  %s%s\n", $label, $detail !== '' ? "  [$detail]" : ''));
    } else {
        $GLOBALS['h24b_fail']++;
        fwrite(STDOUT, sprintf("  FAIL  %s%s\n", $label, $detail !== '' ? "  [$detail]" : ''));
    }
}

fwrite(STDOUT, "=== H24b L1/L3/L5 @ site=" . $GLOBALS['h24b_site'] . " ===\n");

/* =====================================================================
 * L1 配置层
 * =================================================================== */
fwrite(STDOUT, "\n[L1] 配置层\n");

sf_h24b_check('SF_FG_VERSION = 1.2.0', defined('SF_FG_VERSION') && SF_FG_VERSION === '1.2.0', defined('SF_FG_VERSION') ? SF_FG_VERSION : 'undef');
sf_h24b_check('FF 兜底阈值 SF_FG_MAX_SUBMISSIONS = 100', defined('SF_FG_MAX_SUBMISSIONS') && (int) SF_FG_MAX_SUBMISSIONS === 100, (string) (defined('SF_FG_MAX_SUBMISSIONS') ? SF_FG_MAX_SUBMISSIONS : ''));
sf_h24b_check('窗口 SF_FG_MIN_INTERVAL = 3600', defined('SF_FG_MIN_INTERVAL') && (int) SF_FG_MIN_INTERVAL === 3600);
sf_h24b_check('精细限流上限 SF_FG_REAL_MAX_PER_HOUR = 5', defined('SF_FG_REAL_MAX_PER_HOUR') && (int) SF_FG_REAL_MAX_PER_HOUR === 5);
sf_h24b_check('限流窗口 SF_FG_RL_TTL = 3600', defined('SF_FG_RL_TTL') && (int) SF_FG_RL_TTL === 3600);
sf_h24b_check('自动加黑阈值 SF_FG_ABUSE_AUTOBLOCK = 50', defined('SF_FG_ABUSE_AUTOBLOCK') && (int) SF_FG_ABUSE_AUTOBLOCK === 50);
sf_h24b_check('保留期 SF_FG_LOG_RETENTION_DAYS = 90', defined('SF_FG_LOG_RETENTION_DAYS') && (int) SF_FG_LOG_RETENTION_DAYS === 90);

// FF 兜底：滤波器返回 100（CLI 下真实 IP 层视为就绪）。
sf_h24b_check('FF 滤波器 max_submission_count -> 100', (int) sf_fg_filter_max_submissions(5, 8) === 100, (string) sf_fg_filter_max_submissions(5, 8));
sf_h24b_check('FF 滤波器 min_submission_interval -> 3600', (int) sf_fg_filter_min_interval(30, 8) === 3600, (string) sf_fg_filter_min_interval(30, 8));

// 条目列表默认筛选
sf_h24b_check('条目列表默认筛选 = unread', sf_fg_entries_default_type() === 'unread', sf_fg_entries_default_type());

// cron 注册（schedule 挂在 init，本进程已触发过 init）
sf_h24b_check('清理任务已排期 sf_fg_log_cleanup_event', (bool) wp_next_scheduled('sf_fg_log_cleanup_event'));

// Turnstile 仍为未启用（本批刻意跳过项 ①）——确认没有意外启用的路径
sf_h24b_check('Turnstile 仍未启用（① 已跳过）', sf_fg_ts_enabled() === false);

// 关键函数齐备
foreach (array('sf_fg_rl_bump', 'sf_fg_rl_count', 'sf_fg_real_limit_hit', 'sf_fg_abuse_count', 'sf_fg_abuse_maybe_autoblock', 'sf_fg_log_cleanup', 'sf_fg_entries_print_default_filter', 'sf_fg_log_today_count', 'sf_fg_send_429') as $fn) {
    sf_h24b_check('函数存在 ' . $fn, function_exists($fn));
}

/* =====================================================================
 * L3 决策层：精细限流计数器
 * =================================================================== */
fwrite(STDOUT, "\n[L3] 精细限流计数器\n");

sf_fg_rl_reset($TEST_IP);
sf_h24b_check('初始计数为 0', sf_fg_rl_count($TEST_IP) === 0);

$n = 0;
for ($i = 1; $i <= 5; $i++) {
    $n = sf_fg_rl_bump($TEST_IP);
}
sf_h24b_check('连续 5 次后计数 = 5', $n === 5, (string) $n);
sf_h24b_check('第 5 次即达限（>=5）', sf_fg_real_limit_hit($TEST_IP) === true);

// 上限可通过过滤器调整；置 0 = 不限
add_filter('sf_fg_real_max_per_hour', function () {
    return 0;
});
sf_h24b_check('上限置 0 时视为不限', sf_fg_real_limit_hit($TEST_IP) === false);
remove_all_filters('sf_fg_real_max_per_hour');

// 滑窗语义：transient 有 TTL，且值可被清空
sf_h24b_check('transient 键存在且可读', get_transient(sf_fg_rl_key($TEST_IP)) !== false);
sf_fg_rl_reset($TEST_IP);
sf_h24b_check('reset 后计数归零（达限解除）', sf_fg_rl_count($TEST_IP) === 0 && sf_fg_real_limit_hit($TEST_IP) === false);

/* =====================================================================
 * L5 治理层
 * =================================================================== */
fwrite(STDOUT, "\n[L5] 治理层\n");

global $wpdb;
$log_table = $wpdb->prefix . SF_FG_LOG_TABLE;

// ---- 构造 50 条被拦记录（同一测试 IP），验证自动加黑 ----
$base_total = sf_fg_log_total();
for ($i = 0; $i < 50; $i++) {
    $wpdb->insert(
        $log_table,
        array(
            'form_id'       => 8,
            'submission_id' => 0,
            'created_at'    => wp_date('Y-m-d H:i:s', time() - 600),
            'ip'            => $TEST_IP,
            'edge_ip'       => '',
            'ua'            => 'h24b-selftest',
            'country'       => '',
            'email_domain'  => '',
            'score'         => 4,
            'signals'       => 'H24B_SELFTEST',
            'signature'     => '',
            'source'        => 'selftest',
        )
    );
}
sf_h24b_check('构造 50 条审计行后 abuse_count = 50', sf_fg_abuse_count($TEST_IP) === 50, (string) sf_fg_abuse_count($TEST_IP));

$added = sf_fg_abuse_maybe_autoblock($TEST_IP);
sf_h24b_check('自动加黑触发（返回 true）', $added === true);
sf_h24b_check('黑名单里能命中该 IP', sf_fg_blocklist_hit($TEST_IP, '', '') === 'ip');
sf_h24b_check('该 IP 出现在 autoblocked 列表', in_array($TEST_IP, sf_fg_autoblocked(), true));

$again = sf_fg_abuse_maybe_autoblock($TEST_IP);
sf_h24b_check('自动加黑幂等（第二次返回 false）', $again === false);

// 反面对照：只 1 条记录时不应触发（换一个测试 IP）
$TEST_IP2 = '203.0.113.78';
$wpdb->insert($log_table, array('form_id' => 8, 'submission_id' => 0, 'created_at' => current_time('mysql'), 'ip' => $TEST_IP2, 'ua' => 'h24b-selftest', 'score' => 4, 'signals' => 'H24B_SELFTEST', 'source' => 'selftest'));
sf_h24b_check('负对照：仅 1 条时不加黑', sf_fg_abuse_maybe_autoblock($TEST_IP2) === false);

// ---- 告警正文 ----
$GLOBALS['h24b_mail'] = null;
add_filter('pre_wp_mail', function ($return, $atts) {
    $GLOBALS['h24b_mail'] = $atts;
    return true; // 短路，不发真信
}, 10, 2);
sf_fg_send_alert(1);
remove_all_filters('pre_wp_mail');

$msg = isset($GLOBALS['h24b_mail']['message']) ? (string) $GLOBALS['h24b_mail']['message'] : '';
sf_h24b_check('告警正文含「审计表当前行数」', strpos($msg, '审计表当前行数') !== false);
sf_h24b_check('告警正文含「近 24 小时被拦」', strpos($msg, '近 24 小时被拦') !== false);
sf_h24b_check('告警正文列出自动加黑的 IP', strpos($msg, $TEST_IP) !== false);

// ---- 清理任务 ----
// 插一条 100 天前的记录，force 跑一次应把它删掉（新构造的 50 条在 24h 内，保留）
$wpdb->insert($log_table, array('form_id' => 8, 'submission_id' => 0, 'created_at' => wp_date('Y-m-d H:i:s', time() - 100 * 86400), 'ip' => $TEST_IP, 'ua' => 'h24b-selftest-old', 'score' => 4, 'signals' => 'H24B_SELFTEST', 'source' => 'selftest'));
$before = sf_fg_log_total();
$deleted = sf_fg_log_cleanup(true);
$after  = sf_fg_log_total();
sf_h24b_check('清理删除了过期行（>=1）', $deleted >= 1, 'deleted=' . $deleted);
sf_h24b_check('保留期内行未被删（总数只减过期数）', $after === ($before - $deleted), sprintf('%d -> %d', $before, $after));

$state = get_option(SF_FG_CLEANUP_OPT, array());
sf_h24b_check('清理状态已落库（date/deleted/cutoff）', is_array($state) && isset($state['date'], $state['deleted'], $state['cutoff']), wp_json_encode($state));

$del2 = sf_fg_log_cleanup();
sf_h24b_check('同日重复调用返回 0（幂等）', $del2 === 0);

/* =====================================================================
 * L7 条目页总览条（服务端结构 + 计数口径）
 *
 * 为什么要在这里断言「与 DB 相等」，而不是在浏览器侧：
 *   浏览器侧只能拿到一份**跑之前**拍的服务端快照，而 Fluent Forms 在打开单条
 *   详情时会把该条标成 read ⇒ 快照必然有过期风险（实测踩过：unread 3→2）。
 *   所以「等于 DB」放在这里（同一进程内独立再算一遍），浏览器侧只断言
 *   「渲染出来的数字 == 同一响应里 FF 自己算的数字」（跨实现一致，零时差）。
 * =================================================================== */
fwrite(STDOUT, "\n[L7] 条目页总览条（服务端）\n");

$FORM = 8;

// 7a 自建聚合 vs 在同一进程里独立写的原始 SQL
// phpcs:ignore WordPress.DB.DirectDatabaseQuery
$rows = $wpdb->get_results(
    $wpdb->prepare(
        "SELECT status, COUNT(*) AS n FROM {$wpdb->prefix}fluentform_submissions WHERE form_id = %d GROUP BY status",
        $FORM
    ),
    ARRAY_A
);
$truth = array('unread' => 0, 'read' => 0, 'all' => 0, 'spam' => 0, 'trashed' => 0);
$sum   = 0;
foreach ((array) $rows as $r) {
    $sum += (int) $r['n'];
    if (array_key_exists($r['status'], $truth)) {
        $truth[$r['status']] = (int) $r['n'];
    }
}
$truth['all'] = max(0, $sum - $truth['trashed']);

$mine = sf_fg_entry_counts($FORM);
sf_h24b_check('sf_fg_entry_counts() 与独立原始 SQL 一致', count($mine) === 5 && $mine == $truth,
    wp_json_encode($mine) . ' vs ' . wp_json_encode($truth));
sf_h24b_check('不变量 all = 各状态合计 − trashed',
    (int) $mine['all'] === max(0, $sum - (int) $mine['trashed']),
    sprintf('all=%d sum=%d trashed=%d', $mine['all'], $sum, $mine['trashed']));

// 7b 渲染层：真的把这段 HTML 生成出来再看（需要当前用户有 manage_options）
wp_set_current_user(1);
ob_start();
sf_fg_entries_print_default_filter($FORM);
$html = ob_get_clean();

$TABMAP = array('未读' => 'unread', '全部' => 'all', '已读' => 'read', '垃圾' => 'spam', '回收站' => 'trashed');
$pos    = array();
foreach ($TABMAP as $label => $key) {
    $needle = $label . ' (' . (int) $mine[$key] . ')';
    sf_h24b_check(sprintf('总览条入口「%s」渲染且计数为 %d', $label, (int) $mine[$key]),
        strpos($html, $needle) !== false, $needle);
    $pos[] = strpos($html, $label . ' (');
}
$sorted = $pos;
sort($sorted);
sf_h24b_check('总览条顺序 = 未读|全部|已读|垃圾|回收站',
    !in_array(false, $pos, true) && $pos === $sorted, implode(',', array_map('strval', $pos)));

sf_h24b_check('空状态块恒在 DOM 且默认 hidden', strpos($html, 'id="sf-fg-empty" hidden') !== false);
sf_h24b_check('空状态文案含「当前没有未读询盘」', strpos($html, '当前没有未读询盘') !== false);
sf_h24b_check('空状态出口「查看全部 (n)」', strpos($html, '查看全部 (' . (int) $mine['all'] . ')') !== false);
sf_h24b_check('空状态出口「查看垃圾 (n)」', strpos($html, '查看垃圾 (' . (int) $mine['spam'] . ')') !== false);

sf_h24b_check('脚本监听 hashchange（详情页 / FF 下拉切换都能跟随）',
    strpos($html, "addEventListener( 'hashchange', apply )") !== false);
sf_h24b_check('详情页隐藏总览条', strpos($html, 'bar.hidden = isDetail') !== false);
sf_h24b_check('显式 type= 时绝不补默认值', strpos($html, '/[?&]type=/.test( r0 )') !== false);
sf_h24b_check('一次性导航参数 sf_fg_view 会被抹掉', strpos($html, 'sf_fg_view=') !== false);
sf_h24b_check('空状态可见性只有一个判定点（未读=0 且停在未读）',
    strpos($html, "'unread' === eff && UNREAD < 1") !== false);
sf_h24b_check('CSS 显式声明 [hidden]（否则 display:flex 会盖掉 UA 规则）',
    strpos($html, '#sf-fg-bar[hidden]{display:none}') !== false);
sf_h24b_check('总览条刻意不改 FF 的 entry_statuses（升级不被冲掉）',
    strpos($html, 'entry_statuses') === false);

/* =====================================================================
 * 清理（零污染）
 * =================================================================== */
fwrite(STDOUT, "\n[CLEANUP]\n");

$d1 = $wpdb->query($wpdb->prepare("DELETE FROM {$log_table} WHERE ip = %s", $TEST_IP));
$d2 = $wpdb->query($wpdb->prepare("DELETE FROM {$log_table} WHERE ip = %s", $TEST_IP2));
fwrite(STDOUT, sprintf("  删除测试审计行：%d + %d\n", (int) $d1, (int) $d2));

$list = sf_fg_blocklist();
$kept = array();
$removed = 0;
foreach ($list as $entry) {
    if (isset($entry['value']) && ($entry['value'] === $TEST_IP || $entry['value'] === $TEST_IP2)) {
        $removed++;
        continue;
    }
    $kept[] = $entry;
}
if ($removed > 0) {
    update_option(SF_FG_BLOCKLIST_OPT, array_values($kept), false);
}
fwrite(STDOUT, "  移除测试黑名单项：{$removed}（剩余 " . count($kept) . "）\n");

sf_fg_rl_reset($TEST_IP);
sf_fg_rl_reset($TEST_IP2);
fwrite(STDOUT, '  计数 transient 已清理' . "\n");

$final_total = sf_fg_log_total();
sf_h24b_check('清理后审计表回到基线', $final_total === $base_total, sprintf('%d vs %d', $final_total, $base_total));
sf_h24b_check('清理后黑名单无测试项', !in_array($TEST_IP, sf_fg_autoblocked(), true) && sf_fg_blocklist_hit($TEST_IP, '', '') === '');
sf_h24b_check('清理后计数归零', sf_fg_rl_count($TEST_IP) === 0);

fwrite(STDOUT, sprintf(
    "\n===== %d passed, %d failed =====\n",
    $GLOBALS['h24b_pass'],
    $GLOBALS['h24b_fail']
));

exit($GLOBALS['h24b_fail'] > 0 ? 1 : 0);

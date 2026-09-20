<?php
/**
 * 任务 2.4.3：清理 wp_user_roles 中 burst 悬空能力
 *
 * 结构：$roles[role_slug] = ['name'=>…, 'capabilities'=>[cap => bool], …]
 * 说明：WP 把角色存成 wp_options.option_name='wp_user_roles' 的序列化数组，
 *       "悬空能力" = 插件卸载后仍挂在角色上、但已无任何代码去检查的 capability。
 *       它们本身不报错，但会污染能力审计、并给未来的权限判断留下隐患。
 *
 * 设计要点（沿用 2.4.1/2.4.2 加固）：
 *   ① 无备份不删：clean 前校验备份原始串与当前 DB 值一致。
 *   ② 白名单来自**反序列化后的实测结果**，不是 grep 口径 —— 且发现非 burst 命中的
 *      同名能力一律保留，绝不误伤。
 *   ③ 只删 `capabilities` 子数组里的匹配项；角色本身、name、以及其他任何键都不动。
 *   ④ 备份三件套 + 回滚 SQL + 临时库恢复性验证。
 *
 * 用法（CLI 须带 socket）:
 *   php t243_roles.php list | backup | clean | verify
 */

$ROOT = getenv('SF_ROOT') ?: ($_SERVER['HOME'] . '/Local Sites/sinofresh/app/public');
require $ROOT . '/wp-load.php';

const BACKUP_ROOT = '/Users/meng/WorkBuddy/sinofresh外贸网站建设/_backup/img-cleanup-20260920-062700/db-burst';
const ROLES_DIR   = BACKUP_ROOT . '/user-roles';
const RAW_FILE    = ROLES_DIR . '/user-roles-option-raw.txt';
const PRE_JSON    = ROLES_DIR . '/user-roles-pre.json';
const PRETTY      = ROLES_DIR . '/user-roles-pretty.txt';
const ROLLBACK    = ROLES_DIR . '/rollback-user-roles.sql';
const OPT         = 'wp_user_roles';

/** 匹配规则：能力名含 burst（大小写不敏感）视为 burst 残留 */
function is_burst_cap(string $cap): bool { return stripos($cap, 'burst') !== false; }

global $wpdb;

function opt_raw(string $name): ?string {
    global $wpdb;
    $v = $wpdb->get_var($wpdb->prepare(
        "SELECT option_value FROM {$wpdb->options} WHERE option_name = %s", $name));
    return $v === null ? null : (string) $v;
}

/** 收集 burst 能力明细：[role, cap, value] */
function collect_burst(array $roles): array {
    $out = [];
    foreach ($roles as $slug => $def) {
        if (!is_array($def) || !isset($def['capabilities']) || !is_array($def['capabilities'])) { continue; }
        foreach ($def['capabilities'] as $cap => $v) {
            if (is_burst_cap((string) $cap)) { $out[] = ['role' => $slug, 'cap' => $cap, 'value' => $v]; }
        }
    }
    return $out;
}

/** 能力结构签名：role → 能力名（排序）—— 用于「其他能力未被误伤」 */
function cap_sig(array $roles, bool $drop_burst): string {
    $m = [];
    foreach ($roles as $slug => $def) {
        $caps = (is_array($def) && isset($def['capabilities']) && is_array($def['capabilities']))
            ? array_keys($def['capabilities']) : [];
        if ($drop_burst) { $caps = array_values(array_filter($caps, fn($c) => !is_burst_cap((string) $c))); }
        sort($caps);
        $m[$slug] = $caps;
    }
    ksort($m);
    return hash('sha256', serialize($m));
}

/** 全结构规范化（含 name/所有键）—— 严格比对用 */
function canon(array $roles): string {
    $c = $roles;
    foreach ($c as $s => $d) { if (is_array($d) && isset($d['capabilities'])) { ksort($c[$s]['capabilities']); } }
    ksort($c);
    return hash('sha256', serialize($c));
}

$mode = $argv[1] ?? 'list';
printf("== 任务 2.4.3  wp_user_roles burst 悬空能力 %s ==\n", strtoupper($mode));
printf("DB=%s  表=%s  option=%s  autoload=%s\n\n", DB_NAME, $wpdb->options, OPT,
    (string) $wpdb->get_var("SELECT autoload FROM {$wpdb->options} WHERE option_name = '" . OPT . "'"));

$raw   = opt_raw(OPT);
$roles = get_option(OPT);
if (!is_array($roles)) { exit("❌ " . OPT . " 不是数组（" . gettype($roles) . "）\n"); }

$burst      = collect_burst($roles);
$burst_caps = array_values(array_unique(array_column($burst, 'cap')));

if ($mode === 'list') {
    printf("%s: %s B（序列化）| 角色 %d 个\n\n", OPT, number_format(strlen((string) $raw)), count($roles));

    echo "── 角色清单 ──\n";
    foreach ($roles as $slug => $def) {
        $n = (is_array($def) && isset($def['capabilities']) && is_array($def['capabilities']))
            ? count($def['capabilities']) : 0;
        printf("  %-20s capabilities=%3d   其他键: %s\n", $slug, $n,
            implode(', ', array_filter(array_keys((array) $def), fn($k) => $k !== 'capabilities')) ?: '无');
    }

    echo "\n── burst 能力明细（反序列化口径）──\n";
    if (!$burst) { echo "  无\n"; }
    foreach ($burst as $b) {
        printf("  %-20s  %-32s = %s\n", $b['role'], $b['cap'], var_export($b['value'], true));
    }
    printf("\n★ 去重后 burst 能力名: %d 个 → %s\n", count($burst_caps), $burst_caps ? implode(', ', $burst_caps) : '（无）');
    printf("★ 命中条目总数（角色 × 能力）: %d 个\n", count($burst));
    printf("★ MANIFEST-2.4 原记「view_burst_statistics×2 / manage_burst_statistics×1 = 3」%s\n",
        count($burst) === 3 ? '✅ 与实际一致' : '⚠️ 与实际不符 → 需人工确认后再执行');

    // grep 口径对照（演示为什么会误计）
    $g = 0;
    foreach ($burst_caps as $c) { $g += substr_count((string) $raw, $c); }
    printf("   （对照）这些能力名在序列化串中的出现次数合计: %d\n", $g);

    // 交叉核对：其他 option / 元数据里是否还有 burst 痕迹
    echo "\n── 交叉核对：wp_options 中仍含 burst 的 option ──\n";
    $others = $wpdb->get_results($wpdb->prepare(
        "SELECT option_name, LENGTH(option_value) AS len FROM {$wpdb->options}
          WHERE option_value LIKE %s AND option_name <> %s ORDER BY len DESC",
        '%' . $wpdb->esc_like('burst') . '%', OPT));
    printf("  %d 条%s\n", count($others), $others ? ':' : ' ✅');
    foreach ($others as $o) { printf("    %-44s %s B\n", $o->option_name, number_format((int) $o->len)); }
    exit(0);
}

if ($mode === 'backup') {
    if (!is_dir(ROLES_DIR) && !mkdir(ROLES_DIR, 0755, true)) { exit("❌ 无法创建 " . ROLES_DIR . "\n"); }
    if ($raw === null) { exit("❌ " . OPT . " 不存在\n"); }
    file_put_contents(RAW_FILE, $raw);
    file_put_contents(PRETTY, "wp_user_roles 备份（可读）\n生成时间: " . date('c') . "\n"
        . "原始长度: " . strlen($raw) . " B\n规范化 sha256: " . canon($roles) . "\n"
        . "burst 能力: " . count($burst) . " 个条目 / " . count($burst_caps) . " 个名字 → " . implode(', ', $burst_caps) . "\n\n"
        . var_export($roles, true) . "\n");
    file_put_contents(PRE_JSON, json_encode($roles));
    $esc = $wpdb->_real_escape($raw);
    file_put_contents(ROLLBACK,
        "-- 任务 2.4.3 回滚：恢复 " . OPT . " 到清理前状态\n"
        . "-- 生成: " . date('c') . "  原始长度: " . strlen($raw) . " B\n"
        . "-- 应用: mysql --socket=<sock> -uroot -proot " . DB_NAME . " < rollback-user-roles.sql\n"
        . "UPDATE `{$wpdb->options}` SET option_value = '{$esc}' WHERE option_name = '" . OPT . "';\n"
        . "-- 校验: SELECT LENGTH(option_value) FROM `{$wpdb->options}` WHERE option_name='" . OPT . "';  -- 应为 " . strlen($raw) . "\n");
    foreach ([RAW_FILE, PRETTY, PRE_JSON, ROLLBACK] as $f) {
        printf("  ✅ %-48s %s B\n", basename($f), number_format(filesize($f)));
    }
    printf("\n备份完成 → %s\n规范化 sha256: %s\n", ROLES_DIR, canon($roles));
    exit(0);
}

if ($mode === 'clean') {
    if (!is_readable(RAW_FILE) || !is_readable(ROLLBACK)) { exit("❌ 拒绝执行：备份缺失（先跑 backup）\n"); }
    if (file_get_contents(RAW_FILE) !== $raw) {
        exit("❌ 拒绝执行：备份串与当前 DB 值不一致，请重新 backup\n");
    }
    printf("① 备份门禁 ✅  原始串 %s B 与 DB 一致；回滚 SQL %s B\n",
        number_format(strlen($raw)), number_format(filesize(ROLLBACK)));
    if (!$burst) { exit("ℹ️ 无 burst 能力可清（已是干净状态）\n"); }
    printf("② 待清（反序列化口径）: %d 个条目 / %d 个能力名\n", count($burst), count($burst_caps));
    foreach ($burst as $b) { printf("     − %s → %s\n", $b['role'], $b['cap']); }

    $before_other = cap_sig($roles, true);
    $removed = 0; $new = $roles;
    foreach ($new as $slug => $def) {
        if (!is_array($def) || !isset($def['capabilities']) || !is_array($def['capabilities'])) { continue; }
        foreach (array_keys($def['capabilities']) as $cap) {
            if (is_burst_cap((string) $cap)) { unset($new[$slug]['capabilities'][$cap]); $removed++; }
        }
    }
    if (!update_option(OPT, $new)) { exit("❌ update_option 失败：" . $wpdb->last_error . "\n"); }
    printf("③ 已写回 ✅  删除能力条目 %d 个\n", $removed);

    wp_cache_delete(OPT, 'options');
    wp_cache_delete('user_roles', 'options');   // 清掉可能已缓存的能力表
    $after = get_option(OPT);
    printf("④ 复核: 残留 burst 能力 %d 个 %s\n", count(collect_burst($after)),
        collect_burst($after) ? '❌' : '✅');
    printf("   其他能力签名: 清理前 %s / 清理后 %s → %s\n",
        substr($before_other, 0, 16), substr(cap_sig($after, true), 0, 16),
        $before_other === cap_sig($after, true) ? '未误伤 ✅' : '❌ 有变化');
    exit(collect_burst($after) ? 1 : 0);
}

if ($mode === 'verify') {
    printf("① 残留 burst 能力: %d 个 %s\n", count($burst),
        $burst ? '❌ → ' . implode(', ', $burst_caps) : '✅');
    if (file_exists(PRE_JSON)) {
        $pre = json_decode(file_get_contents(PRE_JSON), true);
        $want = cap_sig($pre, true); $got = cap_sig($roles, true);
        printf("② 其他能力（剔 burst）结构签名: 备份 %s / 现网 %s → %s\n",
            substr($want, 0, 16), substr($got, 0, 16), $want === $got ? '完全一致 ✅' : '❌ 有差异');
        // 逐角色能力数对照
        $cnt = function (array $r, bool $drop) {
            $m = []; foreach ($r as $s => $d) {
                $c = (is_array($d) && isset($d['capabilities']) && is_array($d['capabilities'])) ? array_keys($d['capabilities']) : [];
                if ($drop) { $c = array_filter($c, fn($x) => !is_burst_cap((string) $x)); }
                $m[$s] = count($c);
            } ksort($m); return $m;
        };
        $a = $cnt($pre, true); $b = $cnt($roles, true);
        foreach ($a as $s => $n) {
            printf("   %-20s 备份 %3d → 现网 %3d %s\n", $s, $n, $b[$s] ?? 0,
                ($b[$s] ?? -1) === $n ? '✅' : '❌');
        }
        // 角色清单本身是否变化
        printf("③ 角色数: 备份 %d / 现网 %d | 角色名集合 %s\n", count($pre), count($roles),
            array_keys($pre) == array_keys($roles) ? '一致 ✅' : '❌ 有增减');
        printf("④ %s: %s B → %s B（省 %s B）\n", OPT,
            number_format(is_readable(RAW_FILE) ? filesize(RAW_FILE) : 0), number_format(strlen((string) opt_raw(OPT))),
            number_format((is_readable(RAW_FILE) ? filesize(RAW_FILE) : 0) - strlen((string) opt_raw(OPT))));
        exit(($burst || $want !== $got) ? 1 : 0);
    }
    exit($burst ? 1 : 0);
}

exit("未知模式: $mode （list / backup / clean / verify）\n");

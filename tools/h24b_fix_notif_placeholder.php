<?php
/**
 * H24b — form 8 管理员通知占位符笔误修正（幂等 / 可回滚）
 *
 * 问题
 *   `wp_fluentform_form_meta` id=39（form 8「Admin Notification」）的 message 末行写着
 *       Privacy Consent: {inputs.company_name_1}
 *   而 form 8 的「Privacy Consent」是 index 11 的 input_checkbox，
 *   attributes.name = `privacy_consent_11`。⇒ 管理员收到的通知里，
 *   同意声明那一行**重复显示公司名**，看不到访客到底有没有勾选同意。
 *
 * 目标形态（2026-10-12 经 FF 解析器对照实验定稿）
 *       Privacy Consent: {inputs.privacy_consent_11.value}
 *   实测（ShortCodeParser，同一份真实提交数据）：
 *     `{inputs.privacy_consent_11}`       isHtml=false => `I agree to the Privacy Policy`
 *                                         isHtml=true  => `<ul …><li>I agree…</li></ul>`   ← 邮件管道走这条
 *     `{inputs.privacy_consent_11.value}` 两个分支均 => `I agree to the Privacy Policy`
 *   ⇒ 加 `.value` 才能与其余六行一样保持**内联单行**，且不受渲染分支影响。
 *
 * ⚠️ 为什么必须锚定整段字面量
 *   `{inputs.company_name_1}` 在 id=39 的 value 里**共出现 3 次**：
 *     ① subject 里的 `from {inputs.company_name_1}`
 *     ② message 的 `Company: {inputs.company_name_1}`
 *     ③ message 的 `Privacy Consent: {inputs.company_name_1}`   ← 只有这一次要改
 *   所以绝不能用 replace_all / 全局替换，否则会把公司名一起改坏。
 *
 * 用法（服务器侧；dev 与 prod 各自执行）
 *   SF_H24B_SITE=dev|prod SF_H24B_MODE=status|apply|restore \
 *       wp eval-file /root/h24-tools/h24b_fix_notif_placeholder.php --allow-root
 *
 *   ⚠️ dev 与 prod 同机共享 /root/h24b-backup/，备份按站点分名。
 *
 * 安全设计
 *   1. 只做字符串级精确替换（不 json round-trip）——value 里含 `<br \/>` 与
 *      `\u2014` 之类字面量，round-trip 会改变字节。
 *   2. 前置断言：坏形态锚点**恰好命中 1 个且仅出现 1 次**（坏形态含历史 typo 与
 *      中间态两种，见 $BAD）；`{inputs.company_name_1}` 计数须与所选锚点自洽
 *      （typo 锚点 ⇒ 3；中间态锚点 ⇒ 2）；目标形态须 0 次。
 *   3. 原始字节先备份，仅首次写入、不覆盖（回滚永远回到最初那份）。
 *   4. 回读校验：替换后坏锚点应为 0 次，新串应为 1 次，长度差应为
 *      strlen(NEW) - strlen(OLD)；并做**反向替换逐字节比对**。
 *   5. restore 后逐字节比对，不一致即报错退出。
 *
 * 退出码
 *   0 成功 / 无变化   1 非 WP 环境   2 目标行不存在   3 锚点未命中
 *   4 断言失败   5 备份失败   6 更新失败   7 备份缺失/格式异常(restore)
 */

if (!defined('ABSPATH')) {
    fwrite(STDERR, "[ERR] 必须通过 wp eval-file 执行\n");
    exit(1);
}

global $wpdb;

$FORM_ID  = 8;
$FEED_NAME = 'Admin Notification';
$TABLE    = $wpdb->prefix . 'fluentform_form_meta';
$BACKUP_DIR = '/root/h24b-backup';

/* 坏形态候选（顺序 = 优先级：历史 typo 优先于中间态），以及目标形态 */
$BAD = array(
    'Privacy Consent: {inputs.company_name_1}',        // 原始 typo（生产当前状态）
    'Privacy Consent: {inputs.privacy_consent_11}',    // 中间态（dev 首轮已应用）
);
$NEW = 'Privacy Consent: {inputs.privacy_consent_11.value}';

/* 站点标识：dev 与 prod 同机共享备份目录，必须分名 */
$site = getenv('SF_H24B_SITE');
if (!in_array($site, array('dev', 'prod'), true)) {
    $site = 'dev';
}
$BACKUP = $BACKUP_DIR . '/notif_placeholder_raw.' . $site . '.json';

$mode = getenv('SF_H24B_MODE');
if (!in_array($mode, array('status', 'apply', 'restore'), true)) {
    $mode = 'status';
}

function sf_h24b_out($s)
{
    fwrite(STDOUT, $s . "\n");
}

/* ---------- 按 feed 名定位目标行（不写死 id：dev 与 prod 的 id 不一定相同） ---------- */
$rows = $wpdb->get_results(
    $wpdb->prepare(
        "SELECT id, meta_key, value FROM {$TABLE} WHERE form_id = %d AND meta_key = 'notifications' ORDER BY id",
        $FORM_ID
    ),
    ARRAY_A
);
if (!$rows) {
    fwrite(STDERR, "[ERR] form {$FORM_ID} 没有 notifications 行\n");
    exit(2);
}

$row = null;
foreach ($rows as $r) {
    $decoded = json_decode((string) $r['value'], true);
    $nm      = (is_array($decoded) && isset($decoded['name'])) ? (string) $decoded['name'] : '';
    if ($nm === $FEED_NAME) {
        $row = $r;
        break;
    }
}
if (!$row) {
    fwrite(STDERR, "[ERR] 未找到 feed '{$FEED_NAME}'\n");
    exit(2);
}

$ROW_ID = (int) $row['id'];
$raw    = (string) $row['value'];
$nName  = substr_count($raw, '{inputs.company_name_1}');
$nNew   = substr_count($raw, $NEW);

/* 选定坏锚点：候选里**恰好一个**命中，且该候选**恰好出现 1 次** */
$OLD     = '';
$nOld    = 0;
$matched = array();
foreach ($BAD as $cand) {
    $c = substr_count($raw, $cand);
    if ($c > 0) {
        $matched[$cand] = $c;
    }
}
if (count($matched) === 1) {
    $keys = array_keys($matched);
    $OLD  = $keys[0];
    $nOld = $matched[$OLD];
}
/* 与所选锚点自洽的「公司名」期望计数：typo 锚点 3，中间态锚点 2 */
$expectName     = ($OLD === $BAD[0]) ? 3 : (($OLD === $BAD[1]) ? 2 : -1);
$expectBackName = 2; // 两种锚点修好后公司名都剩 2 次（subject + Company 行）

/* ---------- status ---------- */
if ($mode === 'status') {
    $decoded = json_decode($raw, true);
    sf_h24b_out('site: ' . $site);
    sf_h24b_out(sprintf('row id=%d meta_key=%s len=%d', (int) $row['id'], (string) $row['meta_key'], strlen($raw)));
    sf_h24b_out(sprintf('name=%s', (is_array($decoded) && isset($decoded['name'])) ? $decoded['name'] : '?'));
    foreach ($BAD as $i => $cand) {
        sf_h24b_out(sprintf(
            '坏形态[%d] 出现 %d 次%s : %s',
            $i,
            substr_count($raw, $cand),
            ($cand === $OLD) ? '  ← 将以此为锚点' : '',
            $cand
        ));
    }
    sf_h24b_out(sprintf('"{inputs.company_name_1}" 出现 %d 次', $nName));
    sf_h24b_out(sprintf('目标串 "%s" 出现 %d 次（期望 0）', $NEW, $nNew));
    sf_h24b_out('backup: ' . (file_exists($BACKUP) ? $BACKUP : '(none)'));

    $fixed = ($nNew === 1 && $nOld === 0 && count($matched) === 0 && $nName === $expectBackName);
    $ready = ($nNew === 0 && $nOld === 1 && count($matched) === 1 && $nName === $expectName);
    sf_h24b_out('STATE: ' . ($fixed ? '已修正' : ($ready ? '待修正' : '异常')));
    exit(0);
}

/* ---------- restore ---------- */
if ($mode === 'restore') {
    if (!file_exists($BACKUP)) {
        fwrite(STDERR, "[ERR] 备份不存在，无法恢复：{$BACKUP}\n");
        exit(7);
    }
    $b = json_decode(file_get_contents($BACKUP), true);
    if (!is_array($b) || !isset($b['raw'], $b['row_id'])) {
        fwrite(STDERR, "[ERR] 备份文件格式异常：{$BACKUP}\n");
        exit(7);
    }
    $ok = $wpdb->update($TABLE, array('value' => $b['raw']), array('id' => (int) $b['row_id']), array('%s'), array('%d'));
    if ($ok === false) {
        fwrite(STDERR, "[ERR] restore 更新失败: " . $wpdb->last_error . "\n");
        exit(6);
    }
    $back = (string) $wpdb->get_var($wpdb->prepare("SELECT value FROM {$TABLE} WHERE id = %d", (int) $b['row_id']));
    $same = ($back === $b['raw']);
    sf_h24b_out(sprintf('RESTORED[%s] row id=%d byte-identical=%s', $site, (int) $b['row_id'], $same ? 'YES' : 'NO'));
    exit($same ? 0 : 6);
}

/* ---------- apply ---------- */
if ($nNew === 1 && $nOld === 0 && count($matched) === 0) {
    sf_h24b_out("ALREADY FIXED (site={$site}, row id={$ROW_ID}) — no change");
    exit(0);
}

if (count($matched) !== 1 || $nOld !== 1) {
    fwrite(STDERR, sprintf(
        "[ERR] 断言失败：坏锚点命中 %d 个、出现 %d 次（期望 1 个 / 1 次）——内容可能被改过，拒绝盲改\n",
        count($matched),
        $nOld
    ));
    exit(4);
}
if ($nName !== $expectName) {
    fwrite(STDERR, "[ERR] 断言失败：'{inputs.company_name_1}' 出现 {$nName} 次（期望 {$expectName}）\n");
    exit(4);
}
if ($nNew !== 0) {
    fwrite(STDERR, "[ERR] 断言失败：目标串已出现 {$nNew} 次（期望 0）\n");
    exit(4);
}

if (!is_dir($BACKUP_DIR)) {
    @mkdir($BACKUP_DIR, 0700, true);
}
if (!file_exists($BACKUP)) {
    $payload = json_encode(
        array(
            'form_id'  => $FORM_ID,
            'row_id'   => (int) $row['id'],
            'feed'     => $FEED_NAME,
            'anchor'   => $OLD,
            'saved_at' => gmdate('c'),
            'raw'      => $raw,
        ),
        JSON_UNESCAPED_SLASHES
    );
    if (@file_put_contents($BACKUP, $payload) === false) {
        fwrite(STDERR, "[ERR] 备份写入失败：{$BACKUP}\n");
        exit(5);
    }
    @chmod($BACKUP, 0600);
    sf_h24b_out("backup written: {$BACKUP}");
} else {
    sf_h24b_out("backup already exists (kept): {$BACKUP}");
}

$new = str_replace($OLD, $NEW, $raw); // 锚点唯一 ⇒ 等价于单次精确替换
if ($new === $raw) {
    fwrite(STDERR, "[ERR] 替换后无变化，异常\n");
    exit(4);
}

$ok = $wpdb->update($TABLE, array('value' => $new), array('id' => (int) $row['id']), array('%s'), array('%d'));
if ($ok === false) {
    fwrite(STDERR, "[ERR] 更新失败: " . $wpdb->last_error . "\n");
    exit(6);
}

$back     = (string) $wpdb->get_var($wpdb->prepare("SELECT value FROM {$TABLE} WHERE id = %d", (int) $row['id']));
$backOld  = substr_count($back, $OLD);
$backName = substr_count($back, '{inputs.company_name_1}');
$backNew  = substr_count($back, $NEW);
// 反向替换后应与原字节完全一致（最强证据：只动了锚点那一段）。
$revert   = str_replace($NEW, $OLD, $back);
$byteEq   = ($revert === $raw);

$expectDelta = strlen($NEW) - strlen($OLD);
$lenDelta    = strlen($back) - strlen($raw);

sf_h24b_out(sprintf(
    'APPLIED[%s] row id=%d | 锚点=%s | 坏锚点残留=%d(期望0) | 公司名=%d(期望%d) | 目标串=%d(期望1) | 长度差=%+d(期望%+d) | 反替换逐字节一致=%s',
    $site,
    (int) $row['id'],
    $OLD,
    $backOld,
    $backName,
    $expectBackName,
    $backNew,
    $lenDelta,
    $expectDelta,
    $byteEq ? 'YES' : 'NO'
));

exit(
    ($backOld === 0 && $backName === $expectBackName && $backNew === 1 && $lenDelta === $expectDelta && $byteEq)
        ? 0
        : 6
);

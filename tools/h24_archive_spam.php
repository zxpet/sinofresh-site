<?php
/**
 * H24 — 生产 form 8 机器人垃圾：导出存证 + 标 trashed（幂等 / 可回滚 / 零误杀）
 *
 * 背景与依据
 *   扫描报告 docs/scan-form-spam-2026-10-12.md §三 给出机器人画像。经生产侧逐条复核，
 *   零误杀识别规则为下列**析取**（命中 211 / 212，未命中的唯一一条是管理员自己的
 *   键盘乱敲测试 id=2 rwerwer/ghjkk，本脚本刻意不碰它）：
 *     R1  company_name_1 === 'RobertTon'                      （206 条）
 *     R2  contact_person_2 以 'TonGM' 结尾                     （同批主形态）
 *     R3  contact_person_2 以 company_name_1 开头               （CarlosNep/CarlosNepZQ、
 *                                                                DavidBon/DavidBonDS、
 *                                                                Samuelmus/SamuelmusJU 等同构变体）
 *   ⚠️ R3 是「公司名与联系人同前缀」——正是本批防护 S1 信号所抓的形态，
 *      说明机器人会换后缀（Ton → Nep → DS → JU），只能用**结构**识别，不能写死后缀。
 *
 * 重要：本脚本**只改 status，不 DELETE**（用户明确要求）。
 *
 * 用法（服务器侧）
 *   SF_H24_MODE=dry-run wp eval-file /root/h24-tools/h24_archive_spam.php --allow-root
 *   SF_H24_MODE=apply   wp eval-file /root/h24-tools/h24_archive_spam.php --allow-root
 *   SF_H24_MODE=restore wp eval-file /root/h24-tools/h24_archive_spam.php --allow-root
 *
 * 产物（/root/h24-backup/）
 *   prod-form8-archive-<date>.json   全部 212 条快照 + 每条 bot 判定（存证）
 *   prod-form8-status-rollback.json  {id: 原 status}（回滚依据）
 *
 * 退出码：0 成功 1 非 WP 2 无数据 3 apply 前断言失败 4 写入失败 5 回读失败 6 回滚失败
 */

if (!defined('ABSPATH')) {
    fwrite(STDERR, "[ERR] 必须通过 wp eval-file 执行\n");
    exit(1);
}

global $wpdb;

$FORM_ID    = 8;
$TABLE      = $wpdb->prefix . 'fluentform_submissions';
$BACKUP_DIR = '/root/h24-backup';
$ARCHIVE    = $BACKUP_DIR . '/prod-form8-archive-' . gmdate('Y-m-d') . '.json';
$ROLLBACK   = $BACKUP_DIR . '/prod-form8-status-rollback.json';

$mode = getenv('SF_H24_MODE');
if (!in_array($mode, array('dry-run', 'apply', 'restore'), true)) {
    $mode = 'dry-run';
}

// 存证**永不覆盖**：同名已存在则加序号（首次快照最有价值，必须保住）。
if (file_exists($ARCHIVE) && 'restore' !== $mode) {
    $base = preg_replace('/\.json$/', '', $ARCHIVE);
    $i    = 1;
    do {
        $i++;
        $candidate = $base . '-' . $i . '.json';
    } while (file_exists($candidate));
    $ARCHIVE = $candidate;
}

function sf_h24_out($s)
{
    fwrite(STDOUT, $s . "\n");
}

/**
 * 机器人判定（纯结构规则，见文件头 R1/R2/R3）。
 *
 * @param string $response JSON 响应体。
 * @return array{bot:bool,rule:string}
 */
function sf_h24_classify($response)
{
    $d = json_decode($response, true);
    if (!is_array($d)) {
        return array('bot' => false, 'rule' => '');
    }
    $company = isset($d['company_name_1']) ? trim((string) $d['company_name_1']) : '';
    $contact = isset($d['contact_person_2']) ? trim((string) $d['contact_person_2']) : '';

    if ('RobertTon' === $company) {
        return array('bot' => true, 'rule' => 'R1');
    }
    if ('' !== $contact && 'TonGM' === substr($contact, -5)) {
        return array('bot' => true, 'rule' => 'R2');
    }
    if ('' !== $company && '' !== $contact && 0 === strpos($contact, $company)) {
        return array('bot' => true, 'rule' => 'R3');
    }

    return array('bot' => false, 'rule' => '');
}

/* ---------------------------------------------------------------- restore */
if ('restore' === $mode) {
    if (!file_exists($ROLLBACK)) {
        fwrite(STDERR, "[ERR] 回滚文件不存在：{$ROLLBACK}\n");
        exit(6);
    }
    $map = json_decode(file_get_contents($ROLLBACK), true);
    if (!is_array($map) || !$map) {
        fwrite(STDERR, "[ERR] 回滚文件格式异常\n");
        exit(6);
    }
    $n = 0;
    foreach ($map as $id => $st) {
        $ok = $wpdb->update($TABLE, array('status' => $st), array('id' => (int) $id), array('%s'), array('%d'));
        if (false === $ok) {
            fwrite(STDERR, "[ERR] 回滚 id={$id} 失败: " . $wpdb->last_error . "\n");
            exit(6);
        }
        $n++;
    }
    sf_h24_out("RESTORED {$n} 行（status 已还原）");
    exit(0);
}

/* ---------------------------------------------------------------- 取全量 */
$rows = $wpdb->get_results(
    $wpdb->prepare(
        "SELECT id, status, user_id, response, created_at, updated_at,
                ip, browser, device, city, country, source_url
         FROM {$TABLE} WHERE form_id = %d ORDER BY id",
        $FORM_ID
    ),
    ARRAY_A
);

if (!$rows) {
    fwrite(STDERR, "[ERR] form {$FORM_ID} 无提交记录\n");
    exit(2);
}

$archive  = array();
$bot_ids  = array();
$rule_cnt = array('R1' => 0, 'R2' => 0, 'R3' => 0);
$st_cnt   = array();

foreach ($rows as $r) {
    $cls    = sf_h24_classify($r['response']);
    $status = (string) $r['status'];
    $st_cnt[$status] = isset($st_cnt[$status]) ? $st_cnt[$status] + 1 : 1;

    // 存证只留必要字段，避免把整份 HTML/无关列拉进来
    $resp = json_decode($r['response'], true);
    $archive[] = array(
        'id'          => (int) $r['id'],
        'status'      => $status,
        'user_id'     => (int) $r['user_id'],
        'created_at'  => $r['created_at'],
        'updated_at'  => $r['updated_at'],
        'ip'          => $r['ip'],
        'browser'     => $r['browser'],
        'device'      => $r['device'],
        'city'        => $r['city'],
        'country_col' => $r['country'],
        'source_url'  => $r['source_url'],
        'bot'         => $cls['bot'],
        'bot_rule'    => $cls['rule'],
        'fields'      => is_array($resp) ? array(
            'company_name_1'        => isset($resp['company_name_1']) ? $resp['company_name_1'] : null,
            'contact_person_2'      => isset($resp['contact_person_2']) ? $resp['contact_person_2'] : null,
            'email_3'               => isset($resp['email_3']) ? $resp['email_3'] : null,
            'country_5'             => isset($resp['country_5']) ? $resp['country_5'] : null,
            'interested_dosage_form_7' => isset($resp['interested_dosage_form_7']) ? $resp['interested_dosage_form_7'] : null,
            'notes_10'              => isset($resp['notes_10']) ? $resp['notes_10'] : null,
        ) : null,
    );

    if ($cls['bot']) {
        $bot_ids[] = (int) $r['id'];
        $rule_cnt[$cls['rule']]++;
    }
}

sf_h24_out('总行数 = ' . count($rows));
sf_h24_out('机器人命中 = ' . count($bot_ids)
    . '  （R1=' . $rule_cnt['R1'] . ' R2=' . $rule_cnt['R2'] . ' R3=' . $rule_cnt['R3'] . '）');
sf_h24_out('未命中（保留不动）= ' . (count($rows) - count($bot_ids)));
$st_str = array();
foreach ($st_cnt as $k => $v) {
    $st_str[] = "{$k}={$v}";
}
sf_h24_out('status 分布 = ' . implode(' ', $st_str));

/* ---------------------------------------------------------------- 写存证 */
if (!is_dir($BACKUP_DIR)) {
    @mkdir($BACKUP_DIR, 0700, true);
}
$payload = json_encode(
    array(
        'site'        => 'zxpet.com (production)',
        'form_id'     => $FORM_ID,
        'exported_at' => gmdate('c'),
        'rule'        => 'R1 company=RobertTon | R2 contact 以 TonGM 结尾 | R3 contact 以 company 开头',
        'total'       => count($rows),
        'bot_count'   => count($bot_ids),
        'rows'        => $archive,
    ),
    JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE
);
if (false === @file_put_contents($ARCHIVE, $payload)) {
    fwrite(STDERR, "[ERR] 存证写入失败：{$ARCHIVE}\n");
    exit(4);
}
@chmod($ARCHIVE, 0600);
sf_h24_out("存证已写出：{$ARCHIVE}  (" . strlen($payload) . " bytes)");

if ('dry-run' === $mode) {
    sf_h24_out('DRY-RUN 结束（未改任何数据）');
    exit(0);
}

/* ---------------------------------------------------------------- apply */
// 断言：命中数必须 > 0 且 未命中数 >= 0，且命中集合不含 user_id=1 的测试行
$assert_bad = array();
foreach ($rows as $r) {
    if (in_array((int) $r['id'], $bot_ids, true) && (int) $r['user_id'] === 1) {
        $assert_bad[] = (int) $r['id'];
    }
}
if ($assert_bad) {
    fwrite(STDERR, '[ERR] 断言失败：命中集合里出现管理员提交 id=' . implode(',', $assert_bad) . "\n");
    exit(3);
}
if (!$bot_ids) {
    fwrite(STDERR, "[ERR] 断言失败：机器人命中为 0，拒绝执行\n");
    exit(3);
}

// 回滚依据：仅记录将要变更的行（幂等：已 trashed 的跳过）
$rollback = array();
$changed  = 0;
foreach ($rows as $r) {
    $id = (int) $r['id'];
    if (!in_array($id, $bot_ids, true)) {
        continue;
    }
    if ('trashed' === (string) $r['status']) {
        continue; // 已是 trashed，跳过（幂等）
    }
    $rollback[$id] = (string) $r['status'];
    $ok = $wpdb->update($TABLE, array('status' => 'trashed'), array('id' => $id), array('%s'), array('%d'));
    if (false === $ok) {
        fwrite(STDERR, "[ERR] 更新 id={$id} 失败: " . $wpdb->last_error . "\n");
        exit(4);
    }
    $changed++;
}

if ($changed > 0) {
    // 合并到已有回滚文件（支持多次运行）
    $prev = file_exists($ROLLBACK) ? json_decode(file_get_contents($ROLLBACK), true) : array();
    if (!is_array($prev)) {
        $prev = array();
    }
    $merged = $prev + $rollback;
    if (false === @file_put_contents($ROLLBACK, json_encode($merged, JSON_UNESCAPED_SLASHES))) {
        fwrite(STDERR, "[ERR] 回滚文件写入失败：{$ROLLBACK}\n");
        exit(4);
    }
    @chmod($ROLLBACK, 0600);
    sf_h24_out("回滚依据已写出：{$ROLLBACK}（{$changed} 行）");
} else {
    sf_h24_out('无待变更行（全部已是 trashed）');
}

// 回读校验
$after = $wpdb->get_results(
    $wpdb->prepare("SELECT status, COUNT(*) c FROM {$TABLE} WHERE form_id = %d GROUP BY status", $FORM_ID),
    ARRAY_A
);
$line = array();
foreach ($after as $a) {
    $line[] = $a['status'] . '=' . $a['c'];
}
sf_h24_out('回读 status 分布 = ' . implode(' ', $line));

$now_trashed = 0;
foreach ($after as $a) {
    if ('trashed' === $a['status']) {
        $now_trashed = (int) $a['c'];
    }
}
if ($now_trashed < count($bot_ids)) {
    fwrite(STDERR, "[ERR] 回读失败：trashed={$now_trashed} 少于预期 " . count($bot_ids) . "\n");
    exit(5);
}

sf_h24_out("APPLIED：{$changed} 行已标 trashed（累计 {$now_trashed} 行）");
exit(0);

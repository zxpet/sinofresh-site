<?php
/**
 * 任务 2.4.5 —— 清理 TranslatePress `domain='burst-statistics'` 词典行
 *
 * 目标表（2 张，各 4 行，合计 8 行）：
 *   wp_trp_gettext_original_strings  ← 原串表（id 1095-1098）
 *   wp_trp_gettext_en_us             ← en_US 译文表（id 1096-1099，translated='' status=0）
 *
 * 关键设计：
 *   ① **按 `domain` 条件删除**，绝不按 id 硬编码（用户明令）；也绝不按 `original` 字符串删
 *      —— 实测 `Statistics` 在 `burst-statistics` 与 `wp-statistics` 下**各有一行**，
 *         按字符串删会误杀 wp-statistics。
 *   ② 三道门禁：备份门禁（备份产物齐备 + 行数一致）/ 白名单门禁（只允许这 2 张表）/
 *      删除门禁（`$wpdb->delete` 返回行数必须 == 备份行数）。
 *   ③ 恢复性验证：临时库 + 真实 DDL + 灌「删除后状态」→ **真跑回滚 SQL** →
 *      与删除前全表快照比 sha256（字节级）+ deep-equal（语义级）。
 *
 * 用法：
 *   php t245_trp.php list
 *   php t245_trp.php backup
 *   php t245_trp.php clean
 *   php t245_trp.php verify
 *   php t245_trp.php restore      # 临时库真跑回滚，验证可恢复性
 */

$ROOT = getenv('SF_ROOT') ?: ($_SERVER['HOME'] . '/Local Sites/sinofresh/app/public');
require $ROOT . '/wp-load.php';

$MODE = $argv[1] ?? 'list';
$DOMAIN = 'burst-statistics';
// 白名单硬编码：只允许动这两张表
$TABLES = ['wp_trp_gettext_original_strings', 'wp_trp_gettext_en_us'];

$BAK = $_SERVER['HOME'] . '/WorkBuddy/sinofresh外贸网站建设/_backup/img-cleanup-20260920-062700/db-burst/trp';
$SNAP = $BAK . '/pre-snapshot.json';

global $wpdb;
$socket = ini_get('mysqli.default_socket');

/* ────────────────────────── 公共工具 ────────────────────────── */

function cols(string $t): array {
    global $wpdb;
    return array_map(fn($c) => $c->Field, $wpdb->get_results("SHOW COLUMNS FROM `$t`"));
}

/** 全表按 id 升序取回（关联数组） */
function rows_all(string $t): array {
    global $wpdb;
    return $wpdb->get_results("SELECT * FROM `$t` ORDER BY id", ARRAY_A);
}

/** 规范化：列名序 → 值序，行序固定；返回 [sha256, 字节长度, 行数] */
function canon(string $t, array $rows, array $columns): array {
    $buf = '';
    foreach ($rows as $r) {
        $line = [];
        foreach ($columns as $c) { $line[] = $r[$c] ?? null; }
        $buf .= json_encode($line, JSON_UNESCAPED_UNICODE | JSON_INVALID_UTF8_SUBSTITUTE) . "\n";
    }
    return [hash('sha256', $buf), strlen($buf), count($rows)];
}

/** domain 分布签名（用于「其他 domain 未变」的严格比对） */
function domain_sig(string $t): array {
    global $wpdb;
    $rows = $wpdb->get_results("SELECT domain, COUNT(*) c FROM `$t` GROUP BY domain ORDER BY domain", ARRAY_A);
    $buf = '';
    foreach ($rows as $r) { $buf .= $r['domain'] . "\t" . $r['c'] . "\n"; }
    return [hash('sha256', $buf), $buf];
}

/**
 * ★ 生成 SQL 字面量 —— 必须用**裸 mysqli_real_escape_string**，绝不能用 esc_sql() / $wpdb->_real_escape() / $wpdb->prepare()
 *
 * 原因（2.4.5 现场实测的 WP 核心行为）：
 *   `wpdb::_real_escape()` 结尾是 `return $this->add_placeholder_escape( $escaped );`
 *   `add_placeholder_escape()` = `str_replace('%', $this->placeholder_escape(), $query)`
 *   —— 即**故意**把值里每个 `%` 换成 `{sha256}` 令牌，防它被当成 printf 占位符。
 *   而 `$placeholder` 是 `static` 变量：`'{' . hash_hmac('sha256', uniqid(AUTH_SALT,true), AUTH_SALT) . '}'`
 *   → **每个 PHP 进程随机不同**。
 *   还原动作 `remove_placeholder_escape()` 被注册成 `query` **过滤器**（priority 0），
 *   → **只有走 `$wpdb->query()` 的 SQL 才会被还原**。
 *
 *   后果：凡是把 esc_sql 系列的结果 **①落盘成 .sql 文件** 或 **②交给裸 mysqli 执行**，
 *   令牌都不会被还原 → 原样入库 = **静默数据损坏**。
 *   实测：esc_sql('%s Pageviews') → '{8b50ef…}s Pageviews'；裸 mysqli → '%s Pageviews'（干净）。
 */
function sql_lit($v): string {
    global $wpdb;
    if ($v === null) { return 'NULL'; }
    if (is_int($v) || is_float($v)) { return (string) $v; }
    // 裸 mysqli 句柄转义：绕开 wpdb 的 placeholder 令牌机制
    return "'" . mysqli_real_escape_string($wpdb->dbh, (string) $v) . "'";
}

/** 门禁：产物里绝不允许残留 {64hex} 令牌 */
function assert_no_token(string $sql, string $what): void {
    if (preg_match('/\{[0-9a-f]{64}\}/', $sql)) {
        exit("❌ 门禁失败：$what 中残留 placeholder 令牌 `{64hex}` —— 说明误用了 esc_sql 系列\n");
    }
}

/** 由行数组生成 INSERT（显式列名，complete-insert） */
function sql_insert(string $t, array $rows, array $columns): string {
    if (!$rows) { return ''; }
    $cl = '`' . implode('`,`', $columns) . '`';
    $vals = [];
    foreach ($rows as $r) {
        $vs = [];
        foreach ($columns as $c) { $vs[] = sql_lit($r[$c] ?? null); }
        $vals[] = '(' . implode(',', $vs) . ')';
    }
    return "INSERT INTO `$t` ($cl) VALUES\n" . implode(",\n", $vals) . ";\n";
}
function ddl(string $t): string {
    global $wpdb;
    $d = $wpdb->get_var("SHOW CREATE TABLE `$t`", 1);
    return preg_replace('/\s*AUTO_INCREMENT=\d+/', '', (string) $d);
}

/* ────────────────────────── list ────────────────────────── */

if ($MODE === 'list') {
    printf("== 任务 2.4.5  TRP 词典侦察 ==\ndomain = %s\n\n", $DOMAIN);
    $grand = 0;
    foreach ($TABLES as $t) {
        $c = cols($t);
        $tot = (int) $wpdb->get_var("SELECT COUNT(*) FROM `$t`");
        $n   = (int) $wpdb->get_var($wpdb->prepare("SELECT COUNT(*) FROM `$t` WHERE domain LIKE BINARY %s", $DOMAIN));
        $fold= (int) $wpdb->get_var("SELECT COUNT(*) FROM `$t` WHERE domain LIKE '%" . $wpdb->esc_like('burst') . "%'");
        $grand += $n;
        printf("── %s ──\n", $t);
        printf("  列: %s\n", implode(', ', $c));
        printf("  总行数: %s\n", number_format($tot));
        printf("  domain LIKE BINARY '%s' → %d 行\n", $DOMAIN, $n);
        printf("  折叠口径对照 LIKE '%%burst%%' → %d 行 %s\n", $fold, $fold === $n ? '(无折叠干扰 ✅)' : '⚠️ 有差异');

        [$sig] = domain_sig($t);
        printf("  domain 分布签名: %s\n", substr($sig, 0, 16));
        $rows = $wpdb->get_results($wpdb->prepare(
            "SELECT * FROM `$t` WHERE domain LIKE BINARY %s ORDER BY id", $DOMAIN), ARRAY_A);
        foreach ($rows as $r) {
            $prev = '';
            foreach ($c as $k) {
                if (in_array($k, ['id', 'original', 'translated', 'domain', 'status', 'original_id', 'plural_form', 'context', 'lookup_hash'], true)) {
                    $v = (string) ($r[$k] ?? '(null)');
                    if ($k === 'original' || $k === 'translated') { $v = mb_substr($v, 0, 46); }
                    if ($k === 'lookup_hash') { $v = substr($v, 0, 12); }
                    $prev .= $k . '=' . $v . '  ';
                }
            }
            printf("    %s\n", trim($prev));
        }
        echo "\n";
    }
    printf("合计待删: %d 行（记录为 4 + 4 = 8）→ %s\n", $grand, $grand === 8 ? '✅ 一致' : '⚠️ 与记录不符，需停下');
    exit(0);
}

/* ────────────────────────── backup ────────────────────────── */

if ($MODE === 'backup') {
    if (!is_dir($BAK)) { mkdir($BAK, 0755, true); }
    $snap = ['task' => '2.4.5', 'domain' => $DOMAIN, 'time' => date('Y-m-d H:i:s'),
             'db' => DB_NAME, 'tables' => []];
    printf("== 备份（行级 dump + 结构快照 + 全表规范化快照）==\n");
    foreach ($TABLES as $t) {
        $c    = cols($t);
        $all  = rows_all($t);
        $hit  = array_values(array_filter($all, fn($r) => ($r['domain'] ?? null) === $DOMAIN));
        [$h, $len, $n] = canon($t, $all, $c);
        [$dsig, $dtxt] = domain_sig($t);

        // ① 全表快照（恢复性验证的比对基准）
        file_put_contents("$BAK/pre-full-$t.json",
            json_encode(['columns' => $c, 'rows' => $all],
                JSON_UNESCAPED_UNICODE | JSON_INVALID_UTF8_SUBSTITUTE | JSON_PRETTY_PRINT));
        // ② 结构快照
        file_put_contents("$BAK/structure-$t.sql", ddl($t) . ";\n");
        // ③ 行级回滚 SQL（先 DELETE 保证幂等，再完整重插 4 行）
        $sql = "-- 回滚 {$t}：恢复 domain='$DOMAIN' 的 " . count($hit) . " 行\n"
             . "-- 生成于 " . date('Y-m-d H:i:s') . "（删除前快照）\n"
             . "DELETE FROM `$t` WHERE `domain` LIKE BINARY '$DOMAIN';\n"
             . sql_insert($t, $hit, $c);
        assert_no_token($sql, "rollback-$t.sql");
        file_put_contents("$BAK/rollback-$t.sql", $sql);

        $snap['tables'][$t] = [
            'columns' => $c, 'total_rows' => count($all), 'deleted_rows' => count($hit),
            'canon_sha256' => $h, 'canon_bytes' => $len,
            'domain_sig' => $dsig, 'domain_dist' => $dtxt,
            'deleted_ids' => array_map(fn($r) => (int) $r['id'], $hit),
        ];
        printf("  %s\n    总行 %s | 待删 %d 行 | 规范化 sha256 %s | 回滚 SQL %s B\n",
            $t, number_format(count($all)), count($hit), substr($h, 0, 16), strlen($sql));
    }
    file_put_contents($SNAP, json_encode($snap, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT));
    printf("\n快照: %s（%s B）\n", $SNAP, number_format(filesize($SNAP)));

    // 备份门禁：产物齐备 + 待删合计 == 8
    $sum = array_sum(array_column($snap['tables'], 'deleted_rows'));
    $missing = [];
    foreach ($TABLES as $t) {
        foreach (["pre-full-$t.json", "structure-$t.sql", "rollback-$t.sql"] as $f) {
            if (!is_file("$BAK/$f")) { $missing[] = $f; }
        }
    }
    printf("备份门禁: 待删合计 %d %s | 产物缺失 %s\n",
        $sum, $sum === 8 ? '✅' : '❌', $missing ? implode(',', $missing) : '0 ✅');
    exit(($sum === 8 && !$missing) ? 0 : 1);
}

/* ────────────────────────── clean ────────────────────────── */

if ($MODE === 'clean') {
    if (!is_file($SNAP)) { exit("❌ 未找到快照 —— 必须先 backup\n"); }
    $snap = json_decode(file_get_contents($SNAP), true);
    printf("== 清理 ==（按 domain 条件删除，%s）\n", $DOMAIN);
    $total = 0; $fails = [];
    foreach ($TABLES as $t) {
        if (!in_array($t, $TABLES, true)) { $fails[] = "白名单外: $t"; continue; }
        $pre = (int) $snap['tables'][$t]['deleted_rows'];
        // 备份门禁：删除前现网行数必须等于备份时行数（证明无中途漂移）
        $now = (int) $wpdb->get_var($wpdb->prepare("SELECT COUNT(*) FROM `$t` WHERE domain LIKE BINARY %s", $DOMAIN));
        if ($now !== $pre) { $fails[] = "{$t} 现网 {$now} ≠ 备份 {$pre}（状态漂移，中止）"; continue; }

        // ★ 按 domain 删除（$wpdb->delete，非 id 硬编码）
        $res = $wpdb->delete($t, ['domain' => $DOMAIN], ['%s']);
        printf("  %s\n    \$wpdb->delete → %s 行 | last_error: %s | SQL: %s\n",
            $t, var_export($res, true), $wpdb->last_error ?: '(无)', $wpdb->last_query);
        if ($res === false) { $fails[] = "$t delete 返回 false"; continue; }
        if ((int) $res !== $pre) { $fails[] = "$t 删了 $res 行 ≠ 预期 $pre"; continue; }
        $total += (int) $res;
    }
    printf("\n删除合计: %d 行 %s\n", $total, $total === 8 ? '✅' : '❌');
    if ($fails) { echo "❌ 失败：\n  " . implode("\n  ", $fails) . "\n"; exit(1); }
    exit(0);
}

/* ────────────────────────── verify ────────────────────────── */

if ($MODE === 'verify') {
    $snap = json_decode(file_get_contents($SNAP), true);
    printf("== 核验 ==\n");
    $bad = [];
    foreach ($TABLES as $t) {
        $n = (int) $wpdb->get_var($wpdb->prepare("SELECT COUNT(*) FROM `$t` WHERE domain LIKE BINARY %s", $DOMAIN));
        [$dsig] = domain_sig($t);
        $pre = $snap['tables'][$t];
        // 「其他 domain 未变」：剥掉 burst 后的分布必须与备份时逐字节相同
        $post_dist = [];
        foreach (explode("\n", trim(domain_sig($t)[1])) as $l) {
            if ($l === '') { continue; }
            [$d, $c] = explode("\t", $l);
            if ($d !== $DOMAIN) { $post_dist[] = $l; }
        }
        $pre_dist = [];
        foreach (explode("\n", trim($pre['domain_dist'])) as $l) {
            if ($l === '') { continue; }
            [$d, $c] = explode("\t", $l);
            if ($d !== $DOMAIN) { $pre_dist[] = $l; }
        }
        $same = ($post_dist === $pre_dist);
        $tot = (int) $wpdb->get_var("SELECT COUNT(*) FROM `$t`");
        printf("  ① %s\n     残留 domain='%s' → %d 行 %s\n", $t, $DOMAIN, $n, $n === 0 ? '✅' : '❌');
        printf("     其他 domain 分布未变: %s（现 %d 组 / 备份 %d 组）\n", $same ? '✅' : '❌', count($post_dist), count($pre_dist));
        printf("     总行数 %s → %s（应 −%d）\n", number_format($pre['total_rows']), number_format($tot), $pre['deleted_rows']);
        if ($n !== 0) { $bad[] = "$t 仍有残留"; }
        if (!$same) { $bad[] = "$t 其他 domain 分布变化"; }
        if ($tot !== $pre['total_rows'] - $pre['deleted_rows']) { $bad[] = "$t 总行数不符"; }
    }
    // 跨表反查：任何 trp_* 表还有 burst 残留？
    $others = $wpdb->get_col("SHOW TABLES LIKE '{$wpdb->prefix}trp_%'");
    $left = [];
    foreach ($others as $t) {
        $cols = array_column($wpdb->get_results("SHOW COLUMNS FROM `$t`", ARRAY_A), 'Field');
        foreach (['domain', 'original', 'translated'] as $c) {
            if (!in_array($c, $cols, true)) { continue; }
            $k = (int) $wpdb->get_var($wpdb->prepare("SELECT COUNT(*) FROM `$t` WHERE `$c` LIKE BINARY %s", '%' . $DOMAIN . '%'));
            if ($k) { $left[] = "$t.$c = $k"; }
        }
    }
    printf("\n  ② 全库 trp_* 表 burst 残留反查: %s\n", $left ? implode(' | ', $left) : '0 ✅');
    if ($left) { $bad[] = 'trp 残留'; }
    printf("\n结论: %s\n", $bad ? '❌ ' . implode('; ', $bad) : '✅ 核验通过');
    exit($bad ? 1 : 0);
}

/* ────────────────────────── restore（临时库真跑回滚）────────────────────────── */

if ($MODE === 'restore') {
    $snap = json_decode(file_get_contents($SNAP), true);
    $TMPDB = 'sf_restore_chk';
    printf("== 恢复性验证（临时库 %s + 真实 DDL + 真跑回滚 SQL）==\n\n", $TMPDB);
    $my = new mysqli('localhost', DB_USER, DB_PASSWORD, '', null, $socket);
    if ($my->connect_errno) { exit("❌ 临时连接失败: {$my->connect_error}\n"); }
    $my->set_charset('utf8mb4');
    $closed = false;
    register_shutdown_function(function () use ($my, &$closed, $TMPDB) {
        if (!$closed) { @$my->query('DROP DATABASE IF EXISTS ' . $TMPDB); }
    });
    $my->query('DROP DATABASE IF EXISTS ' . $TMPDB);
    $my->query('CREATE DATABASE ' . $TMPDB);
    $my->select_db($TMPDB);
    $fails = [];

    // ① 建表（真实 DDL）
    foreach ($TABLES as $t) {
        $d = file_get_contents("$BAK/structure-$t.sql");
        printf("① 建表 %s: %s\n", $t, $my->query(rtrim(trim($d), ';')) ? '✅' : '❌ ' . $my->error);
    }

    // ② 灌「删除后状态」= 全表快照 减去 domain=burst-statistics 的行
    foreach ($TABLES as $t) {
        $full = json_decode(file_get_contents("$BAK/pre-full-$t.json"), true);
        $c = $full['columns'];
        $post = array_values(array_filter($full['rows'], fn($r) => ($r['domain'] ?? null) !== $DOMAIN));
        $sql = sql_insert($t, $post, $c);
        assert_no_token($sql, "临时库灌入 SQL ($t)");
        $ok = $my->multi_query($sql);
        while ($my->more_results() && $my->next_result()) {}
        $n = (int) ($my->query("SELECT COUNT(*) FROM `$t`")->fetch_row()[0] ?? -1);
        printf("② 灌「删除后状态」 %s: %s（%s 行，应为 %s）\n", $t, ($ok && $n === count($post)) ? '✅' : '❌',
            number_format($n), number_format(count($full['rows']) - $snap['tables'][$t]['deleted_rows']));
        if ($n !== count($post)) { $fails[] = "$t 灌入行数不符"; }
    }

    // ③ 真跑回滚 SQL
    foreach ($TABLES as $t) {
        $sql = file_get_contents("$BAK/rollback-$t.sql");
        $ok = $my->multi_query($sql);
        while ($my->more_results() && $my->next_result()) {}
        printf("③ 执行 rollback-%s.sql: %s%s\n", $t, $ok ? '✅' : '❌', $my->error ? ' ' . $my->error : '');
    }

    // ④ 与删除前全表快照比对（sha256 字节级 + 语义级）
    foreach ($TABLES as $t) {
        $full = json_decode(file_get_contents("$BAK/pre-full-$t.json"), true);
        $c = $full['columns'];
        $rows = [];
        $rs = $my->query("SELECT * FROM `$t` ORDER BY id");
        while ($r = $rs->fetch_assoc()) { $rows[] = $r; }
        [$h, $len, $n] = canon($t, $rows, $c);
        [$ph, $plen, $pn] = [$snap['tables'][$t]['canon_sha256'], $snap['tables'][$t]['canon_bytes'], $snap['tables'][$t]['total_rows']];
        $byte_eq = ($h === $ph);
        $json_eq = (json_encode($rows, JSON_UNESCAPED_UNICODE | JSON_INVALID_UTF8_SUBSTITUTE)
                    === json_encode($full['rows'], JSON_UNESCAPED_UNICODE | JSON_INVALID_UTF8_SUBSTITUTE));
        printf("④ %s\n     读回 %s 行 / %s B | 快照 %s 行 / %s B\n", $t, number_format($n), number_format($len), number_format($pn), number_format($plen));
        printf("     规范化 sha256 逐字节相同: %s（%s ↔ %s）\n", $byte_eq ? '✅' : '❌', substr($h, 0, 16), substr($ph, 0, 16));
        printf("     全表 deep-equal: %s\n", $json_eq ? '✅' : '❌');
        if (!$byte_eq) { $fails[] = "$t 字节不一致"; }
        if (!$json_eq) { $fails[] = "$t 语义不一致"; }
    }

    $drop = $my->query('DROP DATABASE IF EXISTS ' . $TMPDB);
    $gone = $my->query("SELECT SCHEMA_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME='$TMPDB'")->num_rows === 0;
    printf("⑤ 临时库删除: %s\n", ($drop && $gone) ? '✅' : '❌');
    $closed = true; $my->close();

    printf("\n结论: 备份可恢复性 %s\n", $fails ? '❌ 未通过 → ' . implode('; ', $fails) : '✅ 通过（5/5）');
    exit($fails ? 1 : 0);
}

exit("未知子命令 {$MODE}；可用: list / backup / clean / verify / restore\n");

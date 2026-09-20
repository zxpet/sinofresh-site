<?php
/**
 * Batch 2A verification cleanup.
 *
 *  1. Trashes the temporary test formula — wp_trash_post(), never
 *     wp_delete_post(), so the record stays recoverable.
 *  2. Removes the two terms the probe created (see the note in section 3).
 *  3. Destroys the short-lived admin sessions minted for screenshots.
 *
 * ⚠️ Session-token trap (found the hard way while running this):
 *   WP_Session_Tokens::get_all() is keyed by the *hashed* verifier that
 *   WP_User_Meta_Session_Tokens::hash_token() produced, not by the raw token.
 *   Passing one of those keys to destroy() hashes it a second time, so the
 *   lookup misses and destroy() silently does nothing — no error, no warning.
 *   The count staying put is the only symptom.
 *
 *   So this script does both: destroy() by the raw token recorded at mint time
 *   (the API-correct path), and prune any leftover short-lived verifiers
 *   straight out of the session meta, then assert the result.
 *
 * The "short-lived" filter is deliberate: only tokens expiring within the next
 * hour are touched, which selects the 30-minute screenshot sessions and leaves
 * any real logged-in session alone.
 */

require_once '/Users/meng/Local Sites/sinofresh/app/public/wp-load.php';

$USER  = 1;
$SLUG  = 'test-joint-coat-soft-chews';
$TOKENS_FILE = '/tmp/_cpt2a_tokens.txt';

echo "=== 1. 测试配方入回收站 ===\n";
/* Same prefix match as the render check: wp_trash_post() renames the slug to
   "<slug>__trashed", so an exact get_page_by_path() lookup misses a record that
   was already trashed — and get_posts(post_status='any') drops trash too. */
global $wpdb;
$probe_ids = $wpdb->get_col($wpdb->prepare(
    "SELECT ID FROM {$wpdb->posts} WHERE post_type = %s AND post_name LIKE %s ORDER BY ID ASC",
    'sf_formula',
    $wpdb->esc_like($SLUG) . '%'
));
if (!$probe_ids) {
    echo "  未找到 {$SLUG}*（可能已清理过）\n";
} else {
    printf("  找到 %d 条探针记录: %s\n", count($probe_ids), implode(', ', $probe_ids));
    foreach ($probe_ids as $pid) {
        $before_post = get_post($pid);
        printf("  - ID=%d  清理前 status=%s post_name=%s\n", $pid, $before_post->post_status, $before_post->post_name);
        if ($before_post->post_status === 'trash') {
            printf("    已在回收站，跳过（wp_trash_post 不重复执行）\n");
        } else {
            $r = wp_trash_post($pid);
            printf("    wp_trash_post 返回类型 = %s\n", is_wp_error($r) ? 'WP_Error' : gettype($r));
        }
        $after = get_post($pid);
        printf("    清理后 status=%s post_name=%s   meta 保留 %d 条\n",
            $after ? $after->post_status : '(null)',
            $after ? $after->post_name : '-',
            count(get_post_meta($pid)));
    }
}

echo "\n=== 2. 移除探针创建的 term ===\n";
/* The probe assigned terms with a bare string, so wp_set_object_terms() created
   them with name == slug ("soft-chews"). Those are test artifacts, not the
   display labels batch 2B will create ("Soft Chews"), and leaving the slug
   behind would make 2B's wp_insert_term() bail out with term_exists. */
foreach (array('sf_formula_form' => 'soft-chews', 'sf_formula_use' => 'joint-care') as $tax => $slug) {
    $term = get_term_by('slug', $slug, $tax);
    if (!$term) {
        printf("  %-16s / %-12s 不存在，跳过\n", $tax, $slug);
        continue;
    }
    if ((int) $term->count !== 0) {
        printf("  %-16s / %-12s count=%d ≠ 0，**不删**\n", $tax, $slug, $term->count);
        continue;
    }
    $ok = wp_delete_term($term->term_id, $tax);
    printf("  %-16s / %-12s id=%-3d name=%-12s -> wp_delete_term = %s\n",
        $tax, $slug, $term->term_id, $term->name, var_export($ok, true));
}

echo "\n=== 3. 销毁临时截图会话 ===\n";
$now     = time();
$manager = WP_Session_Tokens::get_instance($USER);

/* ⚠️ get_all() is array_values( get_sessions() ) — a numeric-indexed LIST, not
   a verifier-keyed map. Two consequences, both silent:
     · destroy( <index> ) hashes the integer and removes nothing, no warning;
     · any per-session bookkeeping keyed off get_all() keys is meaningless.
   The verifier keys only exist in the session_tokens user meta, so read that
   directly and use get_all() for counts only. */
function sf_sessions_meta($user_id) {
    $sessions = get_user_meta($user_id, 'session_tokens', true);
    return is_array($sessions) ? $sessions : array();
}
function sf_shortlived($sessions, $now) {
    $out = array();
    foreach ($sessions as $verifier => $info) {
        $exp = (int) ($info['expiration'] ?? 0);
        if ($exp > $now && ($exp - $now) <= 3600) {
            $out[$verifier] = $info;
        }
    }
    return $out;
}

$before = sf_sessions_meta($USER);
printf("  session_tokens meta 记录 %d 条，其中 1 小时内到期（临时会话）%d 条\n",
    count($before), count(sf_shortlived($before, $now)));

/* 3a. 公开 API 路径：用铸造时记录下来的**原始** token 调 destroy()。 */
if (file_exists($TOKENS_FILE)) {
    $raw = array_filter(array_map('trim', file($TOKENS_FILE)));
    printf("  铸造时记录到 %d 枚原始 token，逐个 destroy()\n", count($raw));
    foreach ($raw as $t) {
        $manager->destroy($t);
    }
    rename($TOKENS_FILE, $TOKENS_FILE . '.done');
} else {
    printf("  未找到 %s（%s）—— 直接走 verifier 裁剪\n",
        $TOKENS_FILE, file_exists($TOKENS_FILE . '.done') ? '已处理过' : '无记录');
}

/* 3b. 兜底：按 verifier 从 session_tokens meta 里裁掉仍存活的临时会话。
       hash_token() 是单向的，无法由 verifier 反推原始 token，所以按 verifier
       键操作。注意这会绕过 WP 的实例缓存，因此断言必须**重新读 meta**，
       不能读 $manager->get_all()（同一请求内它是陈旧的）。 */
$mid = sf_shortlived(sf_sessions_meta($USER), $now);
if ($mid) {
    printf("  API 路径后仍存活 %d 枚，按 verifier 裁剪\n", count($mid));
    $sessions = sf_sessions_meta($USER);
    foreach (array_keys($mid) as $verifier) {
        printf("    - %s…\n", substr($verifier, 0, 12));
        unset($sessions[$verifier]);
    }
    update_user_meta($USER, 'session_tokens', $sessions);
}

$after = sf_sessions_meta($USER);
$left  = sf_shortlived($after, $now);
printf("  处理后：meta 记录 %d 条，临时会话 %d 条   %s\n",
    count($after), count($left), $left ? '❌ 未清干净' : '✅ 已清空');
printf("  长期会话保留 %d 枚（未被触碰）\n", count($after) - count($left));

echo "\n=== 4. 复核 ===\n";
printf("  sf_formula publish 数 = %d\n", (int) wp_count_posts('sf_formula')->publish);
printf("  sf_formula trash 数   = %d\n", (int) wp_count_posts('sf_formula')->trash);
printf("  term 数: form=%d use=%d   (pre-2A 基线为 0/0)\n",
    (int) wp_count_terms(array('taxonomy' => 'sf_formula_form', 'hide_empty' => false)),
    (int) wp_count_terms(array('taxonomy' => 'sf_formula_use', 'hide_empty' => false)));

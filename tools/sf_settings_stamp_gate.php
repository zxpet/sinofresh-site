<?php
/**
 * H15 门 · 设置页「未提交字段不写」端到端验收（真发 options.php POST）
 *
 * ── v2 修正（v1 的两处错）────────────────────────────────────────────────
 *  1) POST 的 option_page 必须是**选项组**名（sf_site_settings，下划线），
 *     而不是后台**页面** slug（sf-site-settings / sf-shapes，连字符）。
 *     v1 传了页面 slug ⇒ wp-admin/options.php:250
 *       wp_die('错误：选项页面 sf-site-settings 不在允许列表中。')
 *     而 wp_die() 不带 response 参数时**默认响应码就是 500**，于是表现为
 *     「code=500 + WordPress › 错误 页面」。判据：php-fpm 错误日志里查不到任何
 *     fatal —— 这是 wp_die 的特征，不是 PHP 崩溃。别再往 SSL/cookie/Header 上找。
 *     （同一文件第 49 行的 current_user_can 分支 message 是
 *       「抱歉，您不能在此站点管理选项」，拿到哪句就知道卡在哪一步。）
 *  2) 本页「拥有哪些字段」不再手工维护 —— 手工表正是 v1 出错的来源。
 *     改为**真发 HTTP GET 渲染该后台页、解析其中 action 指向 options.php 的表单**，
 *     载荷与真实浏览器提交一致；并自证「GET 200 且确实解析到表单」。
 *
 * 断言：
 *   ① 正向对照：探针路径按提交值落库（证明这次保存**确实执行**；否则②③全是假绿）
 *   ② 本页**不拥有**的组选项逐字节不变（不新建 / 不覆盖 / 不清空）
 *   ③ 本页拥有的其它字段保持原值
 *   ④ Factory & Trust：保存后 sf_formula_trust_value() 的非空项依旧非空（版块不消失）
 *
 * 用法（在站点 docroot 下）：
 *   H15_SLUG=sf-shapes H15_GROUP=sf_site_settings H15_HOST=dev.zxpet.com \
 *   H15_BASIC=sfdev:pass H15_PROBE='sf_shapes[label][0]=H15PROBE' \
 *   wp eval-file tools/sf_settings_stamp_gate.php --url=https://dev.zxpet.com --allow-root
 *
 *   只看字段（不发 POST、零写库）：加 H15_LIST=1
 *
 * 退出码：0 = 全过；1 = 有 FAIL。
 * 副作用：真的改**一个**字段并恢复。恢复路径受保护：
 *   快照里该键不存在 ⇒ delete_option；其余 ⇒ update_option(原值)。
 *   **绝不调用 update_option($k, null)**（v1 就是这么把 sf_copyright_suffix 清空的）。
 */

if (!defined('ABSPATH')) { fwrite(STDERR, "must run via wp eval-file\n"); exit(1); }

/* 主题在 admin_init 里 register_setting —— 不触发就拿不到设置组 */
do_action('admin_init');

$SLUG  = getenv('H15_SLUG') !== false ? getenv('H15_SLUG') : (getenv('H15_PAGE') !== false ? getenv('H15_PAGE') : 'sf-site-settings');
$GROUP = getenv('H15_GROUP') !== false ? getenv('H15_GROUP') : 'sf_site_settings';
$HOST  = getenv('H15_HOST') !== false ? getenv('H15_HOST') : 'dev.zxpet.com';
$BASIC = getenv('H15_BASIC') !== false ? getenv('H15_BASIC') : '';
$PROBE = getenv('H15_PROBE') !== false ? getenv('H15_PROBE') : '';
$LIST  = getenv('H15_LIST') === '1';
$NEG   = getenv('H15_NEG') === '1';

$GLOBALS['sf_h15_fail'] = 0;

function ck($label, $cond, $detail = '') {
	if (!$cond) { $GLOBALS['sf_h15_fail']++; }
	printf("   %-58s %s%s\n", $label, $cond ? 'PASS' : 'FAIL', $detail !== '' ? "   ($detail)" : '');
}

function sf_h15_attr($tag, $attr, $default = '') {
	if (preg_match('~\b' . preg_quote($attr, '~') . '\s*=\s*"([^"]*)"~i', $tag, $m)) {
		return html_entity_decode($m[1], ENT_QUOTES, 'UTF-8');
	}
	if (preg_match("~\b" . preg_quote($attr, '~') . "\s*=\s*'([^']*)'~i", $tag, $m)) {
		return html_entity_decode($m[1], ENT_QUOTES, 'UTF-8');
	}
	if (preg_match('~\b' . preg_quote($attr, '~') . '\b~i', $tag)) { return $default; }
	return $default;
}

/** name="sf_x[a][]" → array('sf_x','a','')   （'' 表示追加） */
function sf_h15_tokens($name) {
	if (!preg_match('~^([^\[]+)(.*)$~', $name, $m)) { return array(); }
	$toks = array($m[1]);
	if ($m[2] !== '') {
		if (preg_match_all('~\[([^\]]*)\]~', $m[2], $t)) { foreach ($t[1] as $x) { $toks[] = $x; } }
	}
	return $toks;
}

function sf_h15_set_path(&$node, $tokens, $value) {
	if (!$tokens) { return; }
	$k = array_shift($tokens);
	if (!$tokens) {
		if ($k === '') { $node[] = $value; } else { $node[$k] = $value; }
		return;
	}
	if ($k === '') {
		$node[] = array();
		$i = count($node) - 1;
		sf_h15_set_path($node[$i], $tokens, $value);
	} else {
		if (!isset($node[$k]) || !is_array($node[$k])) { $node[$k] = array(); }
		sf_h15_set_path($node[$k], $tokens, $value);
	}
}

function sf_h15_get_path($arr, $tokens) {
	$cur = $arr;
	foreach ($tokens as $t) {
		if (!is_array($cur) || !array_key_exists($t, $cur)) { return null; }
		$cur = $cur[$t];
	}
	return $cur;
}

/**
 * 探针读取。
 * ⚠️ tokens[0] 是**选项名**（它对应的是整个 option 值），其余 token 才是值内部的下标。
 * v2 初版忘了剥掉首 token，于是标量探针（如 sf_factory_origin）读回恒为 NULL，
 * 打出假 FAIL —— 数组探针（sf_shapes[label][0]）因为多一层恰好「碰巧」也对，
 * 正好会掩盖这个错，所以标量探针必须留着当哨兵。
 */
function sf_h15_probe_get($optionValue, $tokens) {
	$sub = array_slice($tokens, 1);
	if (!$sub) { return $optionValue; }
	return sf_h15_get_path($optionValue, $sub);
}

/** 从后台页 HTML 里解析 action→options.php 的表单，只收 sf_* 字段 */
function sf_h15_parse_form($html, &$info) {
	$info['form_found'] = false;
	$info['form_count'] = 0;
	if (!preg_match_all('~<form\b[^>]*>.*?</form>~is', $html, $mm)) { return array(); }
	$chunk = '';
	foreach ($mm[0] as $f) {
		if (preg_match('~action\s*=\s*["\'][^"\']*options\.php~i', $f)) { $chunk = $f; break; }
	}
	if ($chunk === '') { return array(); }
	$info['form_count'] = count($mm[0]);
	$info['form_found'] = true;

	$out = array();
	if (preg_match_all('~<input\b[^>]*>~is', $chunk, $im)) {
		foreach ($im[0] as $tag) {
			$name = sf_h15_attr($tag, 'name');
			if ($name === '' || strpos($name, 'sf_') !== 0) { continue; }
			$type = strtolower(sf_h15_attr($tag, 'type', 'text'));
			if ($type === '') { $type = 'text'; }
			if (in_array($type, array('submit', 'button', 'reset', 'file', 'image'), true)) { continue; }
			if (($type === 'checkbox' || $type === 'radio') && !preg_match('~\schecked\b~i', $tag)) { continue; }
			sf_h15_set_path($out, sf_h15_tokens($name), sf_h15_attr($tag, 'value', ''));
		}
	}
	if (preg_match_all('~<textarea\b[^>]*>.*?</textarea>~is', $chunk, $tm)) {
		foreach ($tm[0] as $tag) {
			$name = sf_h15_attr($tag, 'name');
			if ($name === '' || strpos($name, 'sf_') !== 0) { continue; }
			preg_match('~<textarea\b[^>]*>(.*?)</textarea>~is', $tag, $c);
			sf_h15_set_path($out, sf_h15_tokens($name), html_entity_decode($c[1], ENT_QUOTES, 'UTF-8'));
		}
	}
	if (preg_match_all('~<select\b[^>]*>.*?</select>~is', $chunk, $sm)) {
		foreach ($sm[0] as $tag) {
			$name = sf_h15_attr($tag, 'name');
			if ($name === '' || strpos($name, 'sf_') !== 0) { continue; }
			$val = '';
			if (preg_match_all('~<option\b[^>]*>.*?</option>~is', $tag, $om)) {
				foreach ($om[0] as $o) {
					if (preg_match('~\sselected\b~i', $o)) {
						$v = sf_h15_attr($o, 'value', null);
						if ($v === null) { preg_match('~<option\b[^>]*>(.*?)</option>~is', $o, $cc); $v = html_entity_decode(trim($cc[1]), ENT_QUOTES, 'UTF-8'); }
						$val = $v;
						break;
					}
				}
			}
			sf_h15_set_path($out, sf_h15_tokens($name), $val);
		}
	}
	return $out;
}

/**
 * 快照：**绕对象缓存**直读 wp_options 原始字节（option_value）。
 *
 * ⚠️ 为什么必须绕缓存（v2 初版实测踩到，两个后果都很致命）：
 *   保存动作发生在**另一个 PHP 进程**（wp_remote_post → php-fpm），
 *   本进程的 alloptions / options / notoptions 缓存**不会失效**。于是：
 *     ① 用 get_option() 取 $after 会拿到**保存前的旧值** ⇒
 *        「②本页不拥有的字段没变」在**完全没有守卫**时也照样 PASS（假绿）；
 *     ② 恢复路径 update_option($k, $before) 会因为「缓存说当前值已经等于目标值」
 *        在 `$value === $old_value` 处**提前 return，不写库** ⇒ **探针值永久泄漏进库里**。
 *   实测后果：v2 初版把 dev 的 sf_factory_origin 从 'Linyi, Shandong, China'
 *   泄漏成 'H15PROBE'，而②③还是全绿。⇒ 取真值一律直读 wp_options。
 *
 * 返回：option_name => 原始 option_value 字节；不存在用哨兵 "\0__ABSENT__" 区分「不存在」与「空串」。
 */
function sf_h15_snapshot($opts) {
	global $wpdb;
	$s = array();
	foreach ($opts as $o) { $s[$o] = "\0__ABSENT__"; }
	if (!$opts) { return $s; }
	$ph   = implode(',', array_fill(0, count($opts), '%s'));
	$rows = $wpdb->get_results($wpdb->prepare(
		"SELECT option_name, option_value FROM {$wpdb->options} WHERE option_name IN ($ph)", ...$opts));
	foreach ((array) $rows as $r) { $s[$r->option_name] = (string) $r->option_value; }
	return $s;
}

/**
 * autoload 快照：还原时要连 autoload 一起还原，否则会改变 alloptions 的组成。
 */
function sf_h15_autoload_map($opts) {
	global $wpdb;
	$m = array();
	if (!$opts) { return $m; }
	$ph   = implode(',', array_fill(0, count($opts), '%s'));
	$rows = $wpdb->get_results($wpdb->prepare(
		"SELECT option_name, autoload FROM {$wpdb->options} WHERE option_name IN ($ph)", ...$opts));
	foreach ((array) $rows as $r) { $m[$r->option_name] = $r->autoload; }
	return $m;
}

/**
 * 按快照**逐字节**还原 —— 走裸 SQL，绕开 sanitize_option 与「空则删」钩子。
 *
 * ⚠️ 为什么不能只用 update_option() 还原（实测踩到，且后果是静默丢数据）：
 *   数组型选项（sf_global_faq / sf_shapes / sf_containers）的 sanitize 回调
 *   遇到空输入会返回 array()，紧接着 H13 的 delete_option-on-empty 钩子把行删掉。
 *   于是 `update_option($k, array())` 的真实效果是 **delete_option($k)**：
 *   本来值是 a:0:{}（合法的空数组），「还原」之后却变成「不存在」。
 *   实测：sf_global_faq 就这么被本门的恢复路径误删；
 *   字节复核（直读 wp_options）当场把它抓了出来 —— 恢复路径必须自己有断言。
 *   结论：字节级还原只能直接写 option_value，不能让 sanitizer 再表态一次。
 */
function sf_h15_restore($opts, $before, $autoload) {
	global $wpdb;
	$n = 0;
	foreach ($opts as $o) {
		if (!array_key_exists($o, $before)) { continue; }
		if ($before[$o] === "\0__ABSENT__") {
			$wpdb->query($wpdb->prepare("DELETE FROM {$wpdb->options} WHERE option_name = %s", $o));
		} elseif ($wpdb->get_var($wpdb->prepare("SELECT COUNT(*) FROM {$wpdb->options} WHERE option_name = %s", $o))) {
			$wpdb->query($wpdb->prepare(
				"UPDATE {$wpdb->options} SET option_value = %s WHERE option_name = %s", $before[$o], $o));
		} else {
			$al = isset($autoload[$o]) ? $autoload[$o] : 'yes';
			$wpdb->query($wpdb->prepare(
				"INSERT INTO {$wpdb->options} (option_name, option_value, autoload) VALUES (%s, %s, %s)",
				$o, $before[$o], $al));
		}
		wp_cache_delete($o, 'options');
		$n++;
	}
	wp_cache_delete('notoptions', 'options');
	wp_cache_delete('alloptions', 'options');
	return $n;
}

/** 造一个属于同一 session token 的登录态，返回 array(cookie header, uid, tok) */
function sf_h15_auth(&$log) {
	$ids = get_users(array('role' => 'administrator', 'number' => 1, 'fields' => 'ID'));
	if (!$ids) { $log['error'] = '没有管理员账号'; return null; }
	$uid = (int) $ids[0];
	$tok = WP_Session_Tokens::get_instance($uid)->create(time() + 1800);
	$li  = wp_generate_auth_cookie($uid, time() + 1800, 'logged_in', $tok);
	$sec = wp_generate_auth_cookie($uid, time() + 1800, 'secure_auth', $tok);
	$au  = wp_generate_auth_cookie($uid, time() + 1800, 'auth', $tok);
	$_COOKIE[LOGGED_IN_COOKIE] = $li;   // 让本进程取到的 nonce 属于同一个 session token
	wp_set_current_user($uid);
	return array(
		'uid'    => $uid,
		'tok'    => $tok,
		'cookie' => LOGGED_IN_COOKIE . '=' . $li . '; ' . SECURE_AUTH_COOKIE . '=' . $sec . '; ' . AUTH_COOKIE . '=' . $au,
	);
}

function sf_h15_headers($host, $basic, $cookie) {
	$h = array('Host' => $host, 'Cookie' => $cookie);
	if ($basic !== '') { $h['Authorization'] = 'Basic ' . base64_encode($basic); }
	return $h;
}

/* ================================ 主流程 ================================ */
$allowed = apply_filters('allowed_options', array());
$group   = isset($allowed[$GROUP]) ? array_values((array) $allowed[$GROUP]) : array();

echo "== H15 门 v2：设置页「未提交字段不写」 ==\n";
echo "页面 slug={$SLUG}   选项组={$GROUP}   组内选项=" . count($group) . "\n\n";

if (!$group) {
	echo "！设置组为空：admin_init 未注册或 allowed_options 取不到 —— 先修门，不继续。\n";
	exit(1);
}

$al = array();
$auth = sf_h15_auth($al);
if (!$auth) { echo "！{$al['error']}\n"; exit(1); }
$hdrs = sf_h15_headers($HOST, $BASIC, $auth['cookie']);

/* ---- 拿真实后台页（自证 200 + 拿到表单）---- */
$url = 'https://127.0.0.1/wp-admin/admin.php?page=' . rawurlencode($SLUG);
$gi = array();
$r = wp_remote_get($url, array('timeout' => 30, 'sslverify' => false, 'redirection' => 0, 'headers' => $hdrs));
if (is_wp_error($r)) { echo "！GET {$SLUG} 失败：" . $r->get_error_message() . "\n"; exit(1); }
$gi['code'] = wp_remote_retrieve_response_code($r);
$gi['html'] = wp_remote_retrieve_body($r);
echo "   页面 GET：code={$gi['code']}  len=" . strlen($gi['html']) . "\n";

if ($gi['code'] !== 200) {
	echo "！页面 GET 不是 200 —— 先修门（这条通路本身要能自证被服务），不继续。\n";
	exit(1);
}

$body = sf_h15_parse_form($gi['html'], $gi);
echo "   表单：action→options.php " . ($gi['form_found'] ? 'YES' : 'no') . "（页面共 {$gi['form_count']} 个 form）\n";

if (!$gi['form_found']) {
	echo "！该页没有指向 options.php 的表单 —— 不是「会盖章」的设置页，换一页。\n";
	exit(1);
}

$rendered = array_keys($body);
$owned    = array_values(array_intersect($rendered, $group));
$notowned = array_values(array_diff($group, $rendered));
echo "   本页渲染的 sf_* 字段：" . count($rendered) . " 个\n";
echo "   其中属于设置组（本页拥有）：" . count($owned) . " → " . implode(', ', $owned) . "\n";
echo "   组内本页不拥有：" . count($notowned) . " → " . implode(', ', $notowned) . "\n";

if ($LIST) {
	echo "\n-- H15_LIST：仅列举，不发 POST（零写库）--\n";
	/* 同时把**完整 name 属性**打出来：探针路径要按表单真实形状写
	   （例如 sf_shapes[label][0] 而不是入库后的 sf_shapes[0][label]），
	   只看基名会猜错、白跑一轮。 */
	$rawNames = array();
	if (preg_match_all('~\bname\s*=\s*"([^"]+)"~i', $gi['html'], $rn)) {
		foreach ($rn[1] as $n) { if (strpos($n, 'sf_') === 0) { $rawNames[$n] = 1; } }
	}
	echo "   表单里 sf_* 的完整 name（可直接当探针路径用）：\n";
	foreach (array_keys($rawNames) as $n) { echo "     " . $n . "\n"; }
	echo "   基名（=会被 options.php 处理成一项 option）：\n";
	foreach ($rendered as $k) {
		echo "     " . str_pad($k, 26) . " 组内=" . (in_array($k, $group, true) ? 'YES' : 'no') . "\n";
	}
	echo "\n=> 列举完成（未发 POST，未写库）。\n";
	exit(0);
}

$probeToks = array(); $probeVal = ''; $probeBase = '';
if ($PROBE !== '') {
	list($probeName, $probeVal) = array_pad(explode('=', $PROBE, 2), 2, '');
	$probeToks = sf_h15_tokens($probeName);
	$probeBase = $probeToks ? $probeToks[0] : '';
}

ck('本页确实拥有设置组字段（owned 非空）', !empty($owned));
ck('探针基名字段属于本页（否则无法证明保存执行）', $probeBase !== '' && in_array($probeBase, $owned, true),
	"probe={$PROBE}");
if ($PROBE !== '') {
	foreach ($probeToks as $t) { if ($t === '') { echo "！探针路径不允许尾随 []（读回有歧义），改用显式下标。\n"; exit(1); } }
}
if ($probeBase === '' || !in_array($probeBase, $group, true) || !array_key_exists($probeBase, $body)) {
	echo "！探针字段不在组内/不在本页表单里，停止。\n";
	exit(1);
}

$before = sf_h15_snapshot($group);
if (!array_key_exists($probeBase, $before)) { echo "！探针字段不在组内，停止。\n"; exit(1); }

/* ---- 组装载荷：完全按页面渲染值，只把探针路径改成标记值 ---- */
$payload = $body;
sf_h15_set_path($payload, $probeToks, $probeVal);

/* 负向对照：要让守卫**在 web 进程里**被摘掉，光在本进程 remove_all_filters 没用
   （保存是 php-fpm 另一个进程做的，本进程摘钩子对它零影响 ⇒ 会得到「0 项被改动」的
   假结论）。真正生效的做法是把 _h15_neg=1 一起 POST 过去，由临时 mu-plugin
   zz-h15-probe.php 在 web 进程的 admin_init(999) 上摘钩子。 */
if ($NEG) {
	$payload['_h15_neg'] = '1';
	echo "\n   ⚠ H15_NEG=1 负向对照：随 POST 带 _h15_neg=1，由 mu-plugin 在 web 进程内摘守卫\n";
}

$nonce = wp_create_nonce($GROUP . '-options');   // ★ 必须是选项组，不是页面 slug
$payload['option_page']      = $GROUP;
$payload['action']           = 'update';
$payload['_wpnonce']         = $nonce;
$payload['_wp_http_referer'] = '/wp-admin/admin.php?page=' . $SLUG;

$pi = array();
$pr = wp_remote_post('https://127.0.0.1/wp-admin/options.php', array(
	'timeout'     => 30,
	'sslverify'   => false,
	'redirection' => 0,
	'headers'     => $hdrs,
	'body'        => $payload,
));
WP_Session_Tokens::get_instance($auth['uid'])->destroy($auth['tok']);

if (is_wp_error($pr)) {
	echo "！保存请求失败：" . $pr->get_error_message() . "\n";
	exit(1);
}
$pi['code']     = wp_remote_retrieve_response_code($pr);
$pi['location'] = wp_remote_retrieve_header($pr, 'location');
$pi['raw']      = wp_remote_retrieve_body($pr);

echo "   保存请求：code={$pi['code']}  location=" . ($pi['location'] ? $pi['location'] : '(空)') . "\n";
if ($pi['code'] !== 302 && $pi['raw'] !== '') {
	$msg = '';
	if (preg_match('~<div class="wp-die-message">(.*?)</div>~s', $pi['raw'], $mm)) { $msg = trim(strip_tags($mm[1])); }
	echo "   wp_die 消息：" . ($msg !== '' ? $msg : preg_replace('/\s+/', ' ', substr(strip_tags($pi['raw']), 0, 200))) . "\n";
}

ck('保存请求返回 302（未被拒绝）', $pi['code'] === 302, 'code=' . $pi['code']);
ck('重定向带 settings-updated=true', !empty($pi['location']) && strpos($pi['location'], 'settings-updated=true') !== false,
	$pi['location'] ? $pi['location'] : '');

/* ★ 保存是**另一个进程**写的库：本进程对象缓存必须清掉。
   不清的话 get_option() 会返回旧值，④ 与恢复路径都会基于陈旧副本做判断。 */
wp_cache_flush();

$after = sf_h15_snapshot($group);

if (getenv('H15_DEBUG') === '1') {
	echo "\n-- DEBUG：整组 before/after（直读 wp_options）--\n";
	foreach ($group as $o) {
		printf("   %-26s before=%-10s after=%-10s %s\n", $o,
			$before[$o] === "\0__ABSENT__" ? 'ABSENT' : strlen($before[$o]) . 'B',
			$after[$o] === "\0__ABSENT__" ? 'ABSENT' : strlen($after[$o]) . 'B',
			$before[$o] === $after[$o] ? 'same' : 'DIFF');
	}
	echo "   探针原始 after[{$probeBase}] = " . substr(var_export($after[$probeBase], true), 0, 400) . "\n";
	echo "   payload[{$probeBase}] = " . substr(var_export(isset($payload[$probeBase]) ? $payload[$probeBase] : null, true), 0, 400) . "\n";
}

echo "\n-- ① 正向对照：探针路径必须按提交值落库 --\n";
/* ⚠️ 提交形状 ≠ 存储形状：
 *   sf_shapes / sf_containers 的**表单**是平行数组（sf_shapes[label][0]），
 *   而入库后被 sanitize 回调转成**行主序**（[0 => ['label'=>...], 1 => ...]）。
 *   所以探针「读回」不能只按同一路径找下标 —— 会恒为 NULL、打出假 FAIL。
 *   判据改为两步，且都不可省：
 *     ①' 探针值出现在保存后的值里（形状无关）
 *     ①'' 保存前的值里**不含**该标记（排除「本来就有」）
 *   外加 before != after，三者同时成立才算保存真的执行了。 */
$probeNow = maybe_unserialize($after[$probeBase]);
if ($probeNow === "\0__ABSENT__") { $probeNow = null; }
$probeWas = maybe_unserialize($before[$probeBase]);
if ($probeWas === "\0__ABSENT__") { $probeWas = null; }

$pathGot    = sf_h15_probe_get($probeNow, $probeToks);
$nowHasMark = (strpos(maybe_serialize($probeNow), (string) $probeVal) !== false);
$wasHasMark = (strpos(maybe_serialize($probeWas), (string) $probeVal) !== false);
$how        = ((string) $pathGot === (string) $probeVal) ? 'path' : ($nowHasMark ? 'contains' : 'NONE');

if (getenv('H15_DEBUG') === '1') {
	echo '   DEBUG① probeToks=' . json_encode($probeToks)
		. '  afterType=' . gettype($probeNow)
		. '  keys=' . (is_array($probeNow) ? implode(',', array_keys($probeNow)) : '-')
		. '  pathGot=' . var_export($pathGot, true)
		. '  nowHasMark=' . ($nowHasMark ? 'Y' : 'N') . '  wasHasMark=' . ($wasHasMark ? 'Y' : 'N') . "\n";
}

ck("探针 {$PROBE} 已按提交值落库，且保存前不含该标记（证明保存确实执行）",
	$nowHasMark && !$wasHasMark && $after[$probeBase] !== $before[$probeBase],
	'命中方式=' . $how . '  before-md5=' . md5($before[$probeBase]));

echo "\n-- ② 本页不拥有的组选项必须逐字节不变（不新建/不覆盖/不清空）--\n";
$victims = array();
foreach ($notowned as $o) {
	$same = ($before[$o] === $after[$o]);
	if (!$same) { $victims[] = $o; }
	printf("   %-26s [%s] %s\n", $o, $before[$o] === "\0__ABSENT__" ? '不存在' : '存在', $same ? 'unchanged' : 'CHANGED <<<');
}
if ($NEG) {
	/* 负向对照的期望**正好相反**：摘掉守卫后必须看到改动，否则说明本门在空跑 */
	ck('② 负向对照：摘掉守卫后非本页字段确实被改动（证明本门不是空跑）', !empty($victims),
		'changed=' . count($victims) . ' 项：' . implode(',', array_slice($victims, 0, 6)));
} else {
	ck('所有非本页字段逐字节不变（' . count($notowned) . ' 项）', empty($victims),
		$victims ? 'changed: ' . implode(',', $victims) : '');
}

echo "\n-- ③ 本页拥有的其它字段也不应被意外改动 --\n";
/* ⚠️ v3：把「原本不存在 → 保存后按页面渲染值创建」从 FAIL 降级为 INFO。
   原因：options.php 会把**该页表单里渲染出来的每个字段**都写一遍；若某选项原本
   不存在（出厂默认态），页面是用 get_option($k, $默认) 渲染的 ⇒ 提交后该选项被
   **创建**，值 = 管理员在页面上看到的那些值。这是**回填（round-trip）的既定行为**，
   用户可见内容零变化（生产实测：sf_certifications 原本不存在，保存 Site Settings 后
   被创建为 sf_default_certifications() 的 6 行非空内容 —— 与代码默认逐字段相同）。
   判 FAIL 的只剩「**原本存在、保存后变了**」—— 那才是静默改写。
   （v2 把两者混为一谈，会在完全正常时打红，属于门自己的误报。） */
$unexpected = array();   // 原本存在、保存后变了 —— 真 FAIL
$created    = array();   // 原本不存在、保存后被创建 —— INFO（回填副作用，非回归）
foreach ($owned as $o) {
	if ($o === $probeBase) { continue; }
	if ($before[$o] === $after[$o]) { continue; }
	if ($before[$o] === "\0__ABSENT__") { $created[] = $o; } else { $unexpected[] = $o; }
}
if ($NEG) {
	echo "   （负向对照模式：③ 不判定 —— 摘掉守卫后本页字段被写空正是预期副作用）\n";
} else {
	foreach ($created as $o) {
		printf("   %-26s [不存在] → 已按页面渲染值创建（回填副作用，非回归）\n", $o);
	}
	ck('本页其它字段保持原值（原本存在者逐字节不变）', empty($unexpected), $unexpected ? implode(',', $unexpected) : '');
}

echo "\n-- ④ Factory & Trust：保存后非空项依旧非空（版块不消失）--\n";
$tdefs = function_exists('sf_trust_defaults') ? sf_trust_defaults() : array();
$trows = 0; $tblank = array();
foreach ($tdefs as $tk => $td) {
	$eff = sf_formula_trust_value($tk);
	if ($td !== '') {
		$trows++;
		if ($eff === '') { $tblank[] = $tk; }
		printf("   %-26s 出厂=%-18s 现在=%s\n", $tk, var_export($td, true), var_export($eff, true));
	}
}
if ($NEG) {
	echo "   （负向对照模式：④ 不判定）\n";
} else {
	ck("Factory & Trust 四个非空项在保存「{$SLUG}」后仍然非空", empty($tblank),
		$tblank ? 'blanked: ' . implode(',', $tblank) : "非空项={$trows}/4");
}

/* ---- 恢复 ----
   NEG 模式故意把整组选项都搅了（这正是它的意义），所以必须**整组**按快照还原；
   普通模式除了探针字段，还要还原 ③ 里被**回填创建**的字段（v3）——
   否则门会把自己的副作用留在库里（生产实测：跑一次 Site Settings 就多出
   sf_certifications 选项）。还原走裸 SQL（见 sf_h15_restore 的说明）：
   update_option() 会把「还原成空数组」实际执行成 delete_option，字节对不上。
   复核一律**直读 wp_options**。 */
$toRestore = $NEG ? $group : array_values(array_unique(array_merge(array($probeBase), $unexpected, $created)));
$autoload  = sf_h15_autoload_map($toRestore);
sf_h15_restore($toRestore, $before, $autoload);
$restored = sf_h15_snapshot($toRestore);

$bad = array();
foreach ($toRestore as $o) { if ($restored[$o] !== $before[$o]) { $bad[] = $o; } }
if ($NEG) {
	ck('负向对照收尾：整组 ' . count($toRestore) . ' 项已按快照逐字节还原', empty($bad),
		$bad ? 'still-diff: ' . implode(',', $bad) : '');
} else {
	$extra = count($toRestore) - 1;
	ck("探针字段 {$probeBase}" . ($extra > 0 ? " 及 {$extra} 个回填副作用字段" : "")
		. ' 已恢复原值（直读 wp_options 复核，含删除新建项）', empty($bad),
		$bad ? 'still-diff: ' . implode(',', $bad) : ('now-md5=' . md5($restored[$probeBase])));
}
if (!empty($bad)) {
	echo "\n   ‼ 恢复失败：以下选项与保存前不一致，可能已泄漏 —— " . implode(', ', $bad) . "\n";
	foreach ($bad as $o) { echo "      {$o}: before-md5=" . md5($before[$o]) . " now-md5=" . md5($restored[$o]) . "\n"; }
}

$fail = (int) $GLOBALS['sf_h15_fail'];
echo "\n" . ($fail === 0
	? "=> H15 设置页门通过（slug={$SLUG} group={$GROUP}）。\n"
	: "=> H15 设置页门未通过：{$fail} 项 FAIL。\n");
exit($fail === 0 ? 0 : 1);

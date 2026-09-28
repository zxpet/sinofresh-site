<?php
/**
 * H15 门（对照）· sanitize 回调幂等性 —— 修后判据
 *
 * 背景：WP 在选项**不存在**时会把注册的 sanitize 回调**调用两次**
 *       （update_option() 一次 → 委派 add_option() 又一次）。
 *       第二次收到的是第一次的**返回值**。若回调按表单形状读键（平行数组），
 *       第二次就判空 ⇒ 返回 array() ⇒ H13「空则 delete_option」把刚建的行删掉，
 *       而 update_option() 仍返回 true —— 保存静默失效的死锁。
 *       修法＝回调入口的幂等守卫（识别自身输出并原样返回）。
 *
 * 本门断言（全部是「修之后必须成立」的判据）：
 *   A. 幂等：apply(apply(payload)) === apply(payload)
 *   B. 首遍解析正确：行数 == 期望值
 *   C. 守卫不误触发：平行数组（表单）载荷必须仍走解析分支
 *   D. 守卫不误放行：形状像行列表但缺探针键的载荷必须仍走解析分支（负对照）
 *
 * 用法（本脚本放工作区仓库，跑时拷到服务器 /tmp）：
 *   scp tools/sf_sanitize_guard_proof.php root@<host>:/tmp/
 *   ssh root@<host> 'cd /var/www/zxpet-v2 && \
 *     wp eval-file /tmp/sf_sanitize_guard_proof.php --url=https://www.zxpet.com --allow-root'
 *
 * 退出码：0 = 全部通过；1 = 有 FAIL。
 * 安全性：零 DB 写入（只调用注册回调，不调 update_option / add_option / delete_option）。
 */

if (!defined('ABSPATH')) { fwrite(STDERR, "must run via wp eval-file\n"); exit(1); }

do_action('admin_init');

$reg  = get_registered_settings();
$fail = 0;

$pair = array(
	'slug'          => array('soft-chews', 'tablets', 'powders', 'liquids', 'pastes', 'granules', 'capsules', 'sachets'),
	'label'         => array('Soft Chews', 'Tablets', 'Powders', 'Liquids', 'Pastes', 'Granules', 'Capsules', 'Sachets'),
	'attachment_id' => array(349, 0, 0, 0, 0, 0, 0, 0),
);

$cases = array(
	array('opt' => 'sf_shapes',     'expect' => 8, 'payload' => $pair, 'probe' => 'attachment_id'),
	array('opt' => 'sf_containers', 'expect' => 8, 'payload' => $pair, 'probe' => 'attachment_id'),
	array('opt' => 'sf_global_faq', 'expect' => 2, 'probe' => 'q',
	      'payload' => array('q' => array('Q1', 'Q2'), 'a' => array('A1', 'A2'))),
);

echo "== H15 门：sanitize 回调幂等性（修后判据）==\n";
printf("%-16s %-10s %-12s %-16s %s\n", 'option', '首遍', '二遍=首遍?', '首遍行数=期望?', '判定');
echo str_repeat('-', 78) . "\n";

foreach ($cases as $c) {
	$opt = $c['opt'];
	if (empty($reg[$opt]['sanitize_callback'])) {
		printf("%-16s %s\n", $opt, '未注册 sanitize_callback —— FAIL');
		$fail++;
		continue;
	}
	$cb = $reg[$opt]['sanitize_callback'];

	$a = call_user_func($cb, $c['payload']);
	$b = call_user_func($cb, $a);

	$idem  = (serialize($a) === serialize($b));            // A
	$count = (is_array($a) && count($a) === $c['expect']);  // B

	$ok = $idem && $count;
	if (!$ok) { $fail++; }

	printf("%-16s %-10s %-12s %-16s %s\n", $opt,
		(is_array($a) ? count($a) . ' 行' : gettype($a)),
		$idem ? 'yes' : 'NO',
		$count ? 'yes' : 'NO (' . (is_array($a) ? count($a) : 'n/a') . ')',
		$ok ? 'PASS' : 'FAIL');
}

/* C. 守卫不得误触发：平行数组（表单）载荷必须仍被解析成行列表 */
echo "\n== C. 守卫不误触发（表单载荷仍须被解析）==\n";
foreach (array('sf_shapes', 'sf_containers') as $opt) {
	$cb  = $reg[$opt]['sanitize_callback'];
	$out = call_user_func($cb, $pair);
	$mis = (is_array($out) && array_keys($out) === array('slug', 'label', 'attachment_id'));
	$ok  = (!$mis && is_array($out) && count($out) === 8);
	if (!$ok) { $fail++; }
	printf("   %-16s 输出 %d 行，误触发=%s  %s\n", $opt, is_array($out) ? count($out) : -1, $mis ? 'yes' : 'no', $ok ? 'PASS' : 'FAIL');
}

/* D. 负对照：形状像「行列表」但缺探针键 ⇒ 守卫必须不触发，仍走解析（产出 0 行） */
echo "\n== D. 负对照（缺探针键的行列表必须不被放行）==\n";
foreach (array('sf_shapes', 'sf_global_faq') as $opt) {
	$cb    = $reg[$opt]['sanitize_callback'];
	$bogus = array(0 => array('not_the_key' => 'x'));
	$out   = call_user_func($cb, $bogus);
	$pass  = (serialize($out) === serialize($bogus));
	$ok    = (!$pass && is_array($out) && count($out) === 0);
	if (!$ok) { $fail++; }
	printf("   %-16s 输出 %d 行，被误放行=%s  %s\n", $opt, is_array($out) ? count($out) : -1, $pass ? 'yes' : 'no', $ok ? 'PASS' : 'FAIL');
}

echo "\n" . ($fail === 0
	? "=> H15 门通过：3 个表选项回调已幂等，且守卫无误触发 / 无误放行。\n"
	: "=> H15 门未通过：$fail 项 FAIL。\n");
echo "(零 DB 写入：未调用 update_option / add_option / delete_option)\n";

exit($fail === 0 ? 0 : 1);

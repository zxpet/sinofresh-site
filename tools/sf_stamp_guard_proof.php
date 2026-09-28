<?php
/**
 * H15 门（盖章守卫）· 「未提交字段不写」生效性验证
 *
 * 背景：wp-admin/options.php 保存任一设置页时，会遍历**该组全部选项**并逐个写，
 *       本页没有对应字段的选项被写成 NULL
 *       （`$value = null; if ( isset( $_POST[ $option ] ) ) { … }`）。
 *       对「空 = 关掉该行」型读者（7 个 sf_trust_*）＝静默内容消失；
 *       对表选项（sf_shapes / sf_containers / sf_global_faq）＝ NULL 经 sanitize
 *       变 array()，再被 H13「空则 delete_option」钩子删掉整个选项。
 *       修法＝pre_update_option_{$opt} 守卫：未提交且是本组保存时，把旧值交还
 *       update_option()，令其命中 `$value === $old_value` 提前返回（不写、不建行）。
 *
 * 本门断言：
 *   1. 23 个组选项都装上了守卫
 *   2. 模拟盖章（$_POST 无该键）⇒ 过滤器返回旧值（不写）
 *   3. 正向：$_POST 有该键 ⇒ 过滤器原样放行（页面确实拥有的字段照写不误）
 *   4. 决定性：模拟盖章后真的调一次 update_option($opt, null)，选项值必须没变
 *   5. 组外/非本组保存 ⇒ 守卫不介入
 *   6. sf_formula_trust_value() 在「选项不存在」时必须回出厂默认（4 项非空）
 *
 * 用法：
 *   scp tools/sf_stamp_guard_proof.php root@<host>:/tmp/
 *   ssh root@<host> 'cd /var/www/zxpet-v2 && \
 *     wp eval-file /tmp/sf_stamp_guard_proof.php --url=https://www.zxpet.com --allow-root'
 *
 * 退出码：0 = 全部通过；1 = 有 FAIL。
 * 副作用：断言 4 会真的调一次 update_option；本门在结束时把该选项恢复原状
 *        （守卫正常工作时它本就是空操作，不产生任何写入）。
 */

if (!defined('ABSPATH')) { fwrite(STDERR, "must run via wp eval-file\n"); exit(1); }

do_action('admin_init');

$fail = 0;
function sf_gate_ck($label, $ok, $detail = '') {
	global $fail;
	if (!$ok) { $fail++; }
	printf("   %-58s %s%s\n", $label, $ok ? 'PASS' : 'FAIL', $detail !== '' ? "   ($detail)" : '');
}

/* 组选项清单：以 options.php 实际会遍历的那一份为准 */
$allowed = apply_filters('allowed_options', array());
$group   = isset($allowed['sf_site_settings']) ? array_values((array) $allowed['sf_site_settings']) : array();

echo "== H15 门：盖章守卫 ==\n";
echo "组内选项数：" . count($group) . "\n\n";

echo "1) 守卫是否已安装到每个组选项\n";
$missing = array();
foreach ($group as $opt) {
	if (has_filter("pre_update_option_{$opt}") === false) { $missing[] = $opt; }
}
sf_gate_ck('23 个组选项全部装上 pre_update_option 守卫', count($group) === 23 && !$missing,
	$missing ? '缺：' . implode(',', $missing) : count($group) . ' 项');

echo "\n2) 模拟盖章：$_POST 无该键 ⇒ 过滤器必须交还旧值\n";
$probe = 'sf_trust_factory_size';
$old   = get_option($probe, null);
$_POST = array('option_page' => 'sf_site_settings', 'sf_contact_email' => 'sales@zxpet.com');
$back  = apply_filters("pre_update_option_{$probe}", '', $old, $probe);
sf_gate_ck('未提交 ⇒ 过滤器返回旧值（$value === $old_value ⇒ 不写）', $back === $old,
	'old=' . var_export($old, true));

echo "\n3) 正向：$_POST 有该键 ⇒ 必须原样放行（页面拥有的字段照写）\n";
$_POST[$probe] = '15,000㎡';
$pass = apply_filters("pre_update_option_{$probe}", '15,000㎡', $old, $probe);
sf_gate_ck('已提交 ⇒ 过滤器原样放行', $pass === '15,000㎡', 'value=' . $pass);

echo "\n4) 决定性：模拟盖章后真调一次 update_option(\$opt, null)\n";
$before = get_option($probe, null);
$_POST  = array('option_page' => 'sf_site_settings', 'sf_contact_email' => 'sales@zxpet.com');
update_option($probe, null);                     // 与 options.php 完全同形的调用
$after  = get_option($probe, null);
sf_gate_ck('选项值未被创建 / 未被改动', serialize($before) === serialize($after),
	'before=' . var_export($before, true) . ' after=' . var_export($after, true));
/* 自清洁：万一守卫失效真的写进去了，把它恢复原状 */
if ($before === null && get_option($probe, null) !== null) {
	delete_option($probe);
	echo "   （自清洁：已删除被误建的 $probe）\n";
}

echo "\n5) 组外 / 非本组保存 ⇒ 守卫必须不介入\n";
$_POST = array();
$free  = apply_filters("pre_update_option_{$probe}", 'posted-value', $old, $probe);
sf_gate_ck('无 option_page（CLI / cron / 直调）⇒ 放行', $free === 'posted-value');
$_POST = array('option_page' => 'general');
$other = apply_filters("pre_update_option_{$probe}", 'posted-value', $old, $probe);
sf_gate_ck('其它组的保存 ⇒ 放行', $other === 'posted-value');
$_POST = array();

echo "\n6) 出厂默认必须生效（选项不存在时）\n";
$d = sf_trust_defaults();
foreach ($d as $k => $dv) {
	$stored = get_option($k, null);
	$val    = sf_formula_trust_value($k);
	sf_gate_ck("$k：不存在 ⇒ 回默认", $stored === null ? ($val === $dv) : ($val === trim((string) $stored)),
		'default=[' . $dv . '] stored=' . var_export($stored, true) . ' out=[' . $val . ']');
}
$nonEmpty = 0;
foreach ($d as $k => $dv) { if (sf_formula_trust_value($k) !== '') { $nonEmpty++; } }
sf_gate_ck('Factory & Trust 至少 4 行有内容（版块会渲染）', $nonEmpty >= 4, "非空行数=$nonEmpty");

echo "\n" . ($fail === 0 ? "=> H15 盖章守卫门通过。\n" : "=> H15 盖章守卫门未通过：$fail 项 FAIL。\n");
exit($fail === 0 ? 0 : 1);

<?php
/**
 * H15 门 · sf_site_settings 组全选项幂等性普查（纯函数，零写库）
 *
 * 目的：回答「到底有几个选项需要幂等守卫」——把设置组里每个选项的注册回调
 *       各喂两次（WP 在选项不存在时的真实调用序列），逐字节比较两次输出。
 *       这是「报全绿前先证全覆盖」的那一步：避免只修已知的三个、漏掉同型缺陷。
 *
 * 用法（本脚本放在工作区仓库，不随主题部署；跑时拷到服务器 /tmp）：
 *   scp tools/sf_sanitize_idem_sweep.php root@<host>:/tmp/
 *   ssh root@<host> 'cd /var/www/zxpet-v2 && \
 *     wp eval-file /tmp/sf_sanitize_idem_sweep.php --url=https://www.zxpet.com --allow-root'
 *
 * 退出码：0 = 普查完成（清单已产出）；1 = 无法完成。
 * 安全性：零 DB 写入。
 */

if (!defined('ABSPATH')) { fwrite(STDERR, "must run via wp eval-file\n"); exit(1); }

do_action('admin_init');

$reg     = get_registered_settings();
$allowed = apply_filters('allowed_options', array());
$group   = isset($allowed['sf_site_settings']) ? (array) $allowed['sf_site_settings'] : array();

/** 每个选项的「表单原样载荷」。返回 null = 本探针不构造（见下方白名单说明）。 */
function sf_probe_payload($opt) {
	switch ($opt) {
		case 'sf_shapes':
		case 'sf_containers':
			return array(
				'slug'          => array('soft-chews', 'tablets', 'powders', 'liquids', 'pastes', 'granules', 'capsules', 'sachets'),
				'label'         => array('Soft Chews', 'Tablets', 'Powders', 'Liquids', 'Pastes', 'Granules', 'Capsules', 'Sachets'),
				'attachment_id' => array(349, 0, 0, 0, 0, 0, 0, 0),
			);
		case 'sf_global_faq':
			return array('q' => array('Q1', 'Q2'), 'a' => array('A1', 'A2'));
		case 'sf_certifications':
			return array(
				0 => array('name' => 'FDA', 'url' => 'https://fda.gov', 'active' => '1'),
				1 => array('name' => 'cGMP', 'url' => '', 'active' => '1'),
			);
		case 'sf_form_facts':
			return array('soft-chews' => array('moq' => '500 units', 'lead' => '25 days', 'certs' => 'FDA, cGMP', 'packaging' => 'Bulk'));
		case 'sf_form_options':
			return array('dosage_forms' => "Soft Chews\nTablets", 'countries' => "Germany\nFrance", 'target_markets' => "EU\nUS");
		case 'sf_contact_email':
			return 'sales@zxpet.com';
		case 'sf_nav_active_style':
			return 'underline';
		case 'sf_factory_origin':
			return 'Shandong, China';
		case 'sf_factory_oem':
			return 'OEM & ODM';
	}
	if (strpos($opt, 'sf_trust_') === 0) { return 'FDA registered'; }
	return null;   // 6 个纯文本项（sf_working_hours 等）为 string 型 sanitize_text_field，
	               // 天然幂等，见 functions.php:5893；此处不构造载荷、单列说明。
}

printf("%-24s %-12s %-12s %-8s %s\n", 'option', '第1次', '第2次', '幂等', '结论');
echo str_repeat('-', 78) . "\n";

$needGuard = array();
$plainText = array();
$missing   = array();

foreach ($group as $opt) {
	$payload = sf_probe_payload($opt);
	if ($payload === null) { $plainText[] = $opt; continue; }
	if (empty($reg[$opt]['sanitize_callback'])) { $missing[] = $opt; continue; }

	$cb = $reg[$opt]['sanitize_callback'];
	$a  = call_user_func($cb, $payload);
	$b  = call_user_func($cb, $a);
	$fa = is_array($a) ? count($a) . ' 行' : 'len ' . strlen((string) $a);
	$fb = is_array($b) ? count($b) . ' 行' : 'len ' . strlen((string) $b);
	$idem = (serialize($a) === serialize($b));

	printf("%-24s %-12s %-12s %-8s %s\n", $opt, $fa, $fb, $idem ? 'yes' : 'NO',
		$idem ? '无需守卫' : '<<< 需要幂等守卫');

	if (!$idem) { $needGuard[] = $opt; }
}

echo "\n== 结论 ==\n";
echo "  非幂等（需要守卫）: " . ($needGuard ? implode(', ', $needGuard) : '无') . "\n";
echo "  纯文本型（天然幂等，未取载荷）: " . ($plainText ? implode(', ', $plainText) : '无') . "\n";
echo "  未注册回调: " . ($missing ? implode(', ', $missing) : '无') . "\n";
echo "  设置组选项总数: " . count($group) . "\n";
echo "\n(零 DB 写入)\n";

exit(0);

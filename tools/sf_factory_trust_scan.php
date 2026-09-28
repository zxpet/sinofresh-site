<?php
/**
 * H15 验收 ③ · 「Factory & Trust」版块全站扫描
 *
 * 目的：确认每个配方详情页都渲染出 Factory & Trust 版块，且恰好 4 行
 *       （出厂默认有 4 个非空项；Annual Capacity / On-time Delivery / Reorder Rate 出厂为空、不应出行）。
 *
 * 纪律（吃过亏，必须照做）：
 *  ① 逐页自证 **HTTP 200**；
 *  ② 再自证「该有的东西确实在」—— 用规格表 (sf-fdetail-specs) 当锚，
 *     证明短码真的跑了，否则「没有信任带」可能只是拿到了一份空壳；
 *  ③ 判存在一律**锚 markup/元素计数**，绝不锚子串（子串会被注释/JSON-LD 骗过）；
 *  ④ 请求走 loopback + Host 头，绕开 Cloudflare；路径用 parse_url(PATH)，
 *     它本身带前导 `/`，**不要再拼一个 `/`**（否则 //formulas/... → 301 空体，
 *     会把每一页都误判成「版块缺失」）。
 *
 * 用法：
 *   H15_HOST=dev.zxpet.com H15_BASIC=sfdev:pass \
 *   wp eval-file tools/sf_factory_trust_scan.php --url=https://dev.zxpet.com --allow-root
 *
 * 退出码：0 = 全部达标；1 = 有页面不达标。
 */

if (!defined('ABSPATH')) { fwrite(STDERR, "must run via wp eval-file\n"); exit(1); }

$HOST    = getenv('H15_HOST') !== false ? getenv('H15_HOST') : 'dev.zxpet.com';
$BASIC   = getenv('H15_BASIC') !== false ? getenv('H15_BASIC') : '';
$EXPECT  = 4;   // 出厂默认非空项数

$posts = get_posts(array(
	'post_type'      => 'sf_formula',
	'post_status'    => 'publish',
	'posts_per_page' => -1,
	'orderby'        => 'ID',
	'order'          => 'ASC',
));

echo "== H15 验收③：Factory & Trust 全站扫描 ==\n";
echo "host={$HOST}  配方页数=" . count($posts) . "  期望每页行数={$EXPECT}\n\n";

$bad    = array();
$okCnt  = 0;
$rowsSum = 0;

foreach ($posts as $p) {
	$permalink = get_permalink($p);
	$path      = parse_url($permalink, PHP_URL_PATH);
	if (!$path) { $path = '/'; }
	$url = 'https://127.0.0.1' . $path . '?h15scan=' . time();

	$hdr = array('Host' => $HOST);
	if ($BASIC !== '') { $hdr['Authorization'] = 'Basic ' . base64_encode($BASIC); }

	$r = wp_remote_get($url, array('timeout' => 30, 'sslverify' => false, 'redirection' => 3, 'headers' => $hdr));
	if (is_wp_error($r)) {
		$bad[] = sprintf('%-42s WP_Error: %s', $path, $r->get_error_message());
		continue;
	}
	$code = wp_remote_retrieve_response_code($r);
	$html = wp_remote_retrieve_body($r);

	$specs = substr_count($html, 'sf-fdetail-specs');
	$band  = substr_count($html, '<section class="sf-fdetail-trust"');
	$rows  = substr_count($html, 'sf-fdetail-trust__row');

	$why = array();
	if ($code !== 200)        { $why[] = "code={$code}"; }
	if (strlen($html) < 5000) { $why[] = 'body=' . strlen($html) . 'B(疑似空壳)'; }
	if ($specs < 1)           { $why[] = '规格表缺失(短码可能没跑，结论不可信)'; }
	if ($band !== 1)          { $why[] = "信任带 section={$band}"; }
	if ($rows !== $EXPECT)    { $why[] = "信任带行数={$rows}"; }

	if ($why) {
		$bad[] = sprintf('%-42s %s', $path, implode(' / ', $why));
	} else {
		$okCnt++;
		$rowsSum += $rows;
	}
	printf("   %-44s code=%d specs=%-2d band=%d rows=%d %s\n",
		$path, $code, $specs, $band, $rows, $why ? '<<< ' . implode(' / ', $why) : 'OK');
}

echo "\n   达标 " . $okCnt . '/' . count($posts) . " 页   信任带行数合计=" . $rowsSum
	. '（应为 ' . ($okCnt * $EXPECT) . "）\n";

if ($bad) {
	echo "\n   不达标明细：\n";
	foreach ($bad as $b) { echo '     ' . $b . "\n"; }
	echo "\n=> H15 验收③未通过：" . count($bad) . " 页不达标。\n";
	exit(1);
}

echo "\n=> H15 验收③通过：" . count($posts) . " 页全部渲染出 Factory & Trust 版块，每页 " . $EXPECT . " 行。\n";
exit(0);

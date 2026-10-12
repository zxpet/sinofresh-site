<?php
/**
 * ⚠️ 临时测试夹具 —— 只用于 Q4「邮件日志收敛」验收，**用完必须立即删除**。
 * 不属于生产常驻 mu-plugin；不要在 docroot 的 wp-content/mu-plugins/ 里长期留存。
 *
 * 设计约束（H24 零污染范式）
 *   1. 条件式：仅当请求带 `X-SF-Test-Sink` 头时才改写收件人 ⇒ 真实访客的邮件
 *      照常发给 sales@zxpet.com，**完全不受影响**。
 *   2. 可探测：同时回一个 `X-SF-Test-Sink-Armed: 1` 响应头，让部署脚本能在
 *      真正提交询盘**之前**确认「夹具已加载 **且** 自定义头确实送达了 PHP」。
 *      这一步是防呆关键 —— 否则条件不成立时测试邮件会直接落到 sales@ 邮箱。
 *   3. 只改 `to`，不动 from / subject / headers ⇒ 尽量不影响被测链路。
 *
 * 部署（由 tools/h24b_q4_deploy.sh 负责，带 trap 自动删除）
 *   install -o apache -g apache -m 644 tools/fixtures/zz-sf-zz-test-nomail.php \
 *     <docroot>/wp-content/mu-plugins/zz-sf-zz-test-nomail.php
 */

if ( ! empty( $_SERVER['HTTP_X_SF_TEST_SINK'] ) ) {
	// 探针：证明「夹具已加载」且「自定义头到达了 PHP」。
	if ( ! headers_sent() ) {
		header( 'X-SF-Test-Sink-Armed: 1', true );
	}

	add_filter(
		'wp_mail',
		function ( $args ) {
			if ( ! empty( $_SERVER['HTTP_X_SF_TEST_SINK'] ) ) {
				$args['to'] = 'h24b-q4-test@invalid.example';
			}
			return $args;
		},
		99
	);
}

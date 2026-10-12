<?php
/**
 * Plugin Name: SINO FRESH - Real Client IP (Cloudflare-aware)
 * Description: 把 $_SERVER['REMOTE_ADDR'] 统一为访客真实 IP：仅当直连方落在 Cloudflare 官方网段内时才采信 CF-Connecting-IP 改写，其余情况一律不动（本站源站可被公网直连绕过 CF，直连时请求头由攻击者完全控制）。CLI 环境不动。DEV 与生产共用同一文件，无环境开关。
 * Version:     1.0.0
 * Author:      SINO FRESH
 *
 * WHY THIS EXISTS (2026-10-12, batch H24)
 * ---------------------------------------
 * Fluent Forms 的 InteractsWithIPTrait::resolveIp() 不信任任何代理 —— 它的受信代理列表来自
 * config/trustedproxy.php，而该文件在本插件里根本不存在（config/ 下只有 app.php /
 * middleware.php / index.php）—— 于是它记录的永远是 REMOTE_ADDR，也就是 Cloudflare
 * 边缘节点的地址。
 *
 *   实测证据（2026-10-12）：form 8 的 212 条提交只出现 **12 个不同 IP，全部落在 CF 边缘段**，
 *   其中一个（104.23.162.134）独自承载 108 条；同一提交还带 source_url 恒为站点首页。
 *
 * 后果不止于表单：WP Statistics 的访客统计、zz-sf-login-guard 的取证日志、主题自研询盘端点
 * 的 IP 口径，全都按边缘 IP 计数。不修这一条，任何「按 IP 限流 / 取证 / 封禁」都是在按边缘
 * 节点计数 —— 慢速机器人打不到，一旦收紧阈值却会先挡住共用同一边缘节点的真客户。
 *
 * WHY NOT add Fluent Forms' own config/trustedproxy.php
 * ----------------------------------------------------
 * 插件目录里塞文件会被插件升级覆盖，verify-checksums 也会漂（H21 审计要求保持干净）。
 * 在 mu-plugin 层把 REMOTE_ADDR 归一，是「访客是谁」的唯一事实来源，所有消费者一起受益，
 * 且回滚 = 删文件。
 *
 * WHY NOT trust CF-Connecting-IP unconditionally
 * ---------------------------------------------
 * 源站 65.49.215.152 公网可直连（H20/H21 已知遗留，本批不做 C3「只放行 CF 网段」）。
 * 无条件信任该头 = 给攻击者一个免费的白名单 / 嫁祸通道：直连源站并伪造
 * `CF-Connecting-IP: 1.2.3.4` 就能冒充任何 IP。因此只在 REMOTE_ADDR ∈ CF 官方网段时才采信，
 * 与 zz-sf-login-guard 的既有判断同源（本文件把网段表提为共享实现，供 form-guard 复用）。
 *
 * WHERE IT RUNS
 * -------------
 * mu-plugins 按文件名字母序加载。'zz-sf-aa-real-ip.php' 排在 author-guard /
 * login-guard / wps-consent-bridge 之前，因此改写在所有插件与主题之前完成。
 * 副作用核查：login-guard 的 sf_login_guard_client_ip() 在改写后会看到「REMOTE_ADDR = 真实
 * 客户 IP」（通常不在 CF 段）⇒ is_cloudflare() 返回 false ⇒ 直接采用 REMOTE_ADDR，
 * 即真实 IP。结论不变，行为不变。
 *
 * ROLLBACK
 * --------
 * 删除本文件（或改名 .off）即恢复原状；不动数据库、不动插件文件、不动主题。
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/**
 * Cloudflare 官方 IP 网段。
 *
 * 来源：https://www.cloudflare.com/ips-v4 与 https://www.cloudflare.com/ips-v6
 * 复核日期：2026-10-12（与 zz-sf-login-guard v1.1.0 内置副本一致；季度复查）。
 * 2026-10-12 校验：本轮在源站日志里观测到的 12 个边缘地址用 ipaddress 逐一比对，
 * 12/12 全部落在此表内。
 *
 * @return string[] CIDR 列表。
 */
function sf_real_ip_cf_ranges() {
	$ranges = array(
		// IPv4（15 段）
		'173.245.48.0/20',
		'103.21.244.0/22',
		'103.22.200.0/22',
		'103.31.4.0/22',
		'141.101.64.0/18',
		'108.162.192.0/18',
		'190.93.240.0/20',
		'188.114.96.0/20',
		'197.234.240.0/22',
		'198.41.128.0/17',
		'162.158.0.0/15',
		'104.16.0.0/13',
		'104.24.0.0/14',
		'172.64.0.0/13',
		'131.0.72.0/22',
		// IPv6（7 段）
		'2400:cb00::/32',
		'2606:4700::/32',
		'2803:f800::/32',
		'2405:b500::/32',
		'2405:8100::/32',
		'2a06:98c0::/29',
		'2c0f:f248::/32',
	);

	/**
	 * 允许运维在不改文件的前提下追加网段（例如 CF 公布新段）。
	 *
	 * @param string[] $ranges CIDR 列表。
	 */
	return apply_filters( 'sf_real_ip_cf_ranges', $ranges );
}

/**
 * 判断 IP 是否落在 CIDR 内（IPv4 / IPv6 走同一套二进制前缀比较）。
 *
 * @param string $ip   待判 IP。
 * @param string $cidr 形如 104.16.0.0/13 或 2606:4700::/32。
 * @return bool
 */
function sf_real_ip_in_cidr( $ip, $cidr ) {
	if ( false === strpos( $cidr, '/' ) ) {
		return $ip === $cidr;
	}

	list( $net, $bits ) = explode( '/', $cidr, 2 );
	$bits    = (int) $bits;
	$ip_bin  = @inet_pton( (string) $ip );
	$net_bin = @inet_pton( (string) $net );

	if ( false === $ip_bin || false === $net_bin || strlen( $ip_bin ) !== strlen( $net_bin ) ) {
		return false;
	}

	$whole_bytes = intdiv( $bits, 8 );
	$rest_bits   = $bits % 8;

	if ( $whole_bytes > 0 && substr( $ip_bin, 0, $whole_bytes ) !== substr( $net_bin, 0, $whole_bytes ) ) {
		return false;
	}
	if ( 0 === $rest_bits ) {
		return true;
	}

	$mask = chr( ( 0xFF << ( 8 - $rest_bits ) ) & 0xFF );

	return ( substr( $ip_bin, $whole_bytes, 1 ) & $mask ) === ( substr( $net_bin, $whole_bytes, 1 ) & $mask );
}

/**
 * 该 IP 是否来自 Cloudflare 边缘。
 *
 * @param string $ip 直连方 IP。
 * @return bool
 */
function sf_real_ip_is_cloudflare( $ip ) {
	if ( '' === $ip || false === filter_var( $ip, FILTER_VALIDATE_IP ) ) {
		return false;
	}
	foreach ( sf_real_ip_cf_ranges() as $cidr ) {
		if ( sf_real_ip_in_cidr( $ip, $cidr ) ) {
			return true;
		}
	}

	return false;
}

/**
 * 解析「访客是谁」—— 纯函数，无副作用，便于门做表驱动断言。
 *
 * 规则（唯一一条）：只有直连方落在 CF 官方网段内，才看一眼 CF 提供的客户端地址头；
 * 头里的值必须是合法 IP、且与直连方不同；否则一律回落到直连方地址本身。
 *
 * @param string $remote_addr      TCP 对端地址（$_SERVER['REMOTE_ADDR']）。
 * @param string $cf_connecting_ip CF-Connecting-IP 头原文（可能为空、可能是逗号列表）。
 * @param string $true_client_ip   True-Client-IP 头原文（备用头）。
 * @return array{ip:string,source:string,edge:string} source ∈ cf|direct|invalid
 */
function sf_real_ip_resolve( $remote_addr, $cf_connecting_ip = '', $true_client_ip = '' ) {
	$remote_addr = is_string( $remote_addr ) ? trim( $remote_addr ) : '';

	if ( '' === $remote_addr || ! filter_var( $remote_addr, FILTER_VALIDATE_IP ) ) {
		return array(
			'ip'     => '0.0.0.0',
			'source' => 'invalid',
			'edge'   => '',
		);
	}

	// 直连方不是 CF ⇒ 一律不动。头由对方完全控制，采信即等于白名单。
	if ( ! sf_real_ip_is_cloudflare( $remote_addr ) ) {
		return array(
			'ip'     => $remote_addr,
			'source' => 'direct',
			'edge'   => '',
		);
	}

	foreach ( array( $cf_connecting_ip, $true_client_ip ) as $header ) {
		if ( ! is_string( $header ) || '' === trim( $header ) ) {
			continue;
		}
		// 头可能是逗号列表（多级代理），第一个是最靠近客户端的地址。
		$candidate = trim( explode( ',', $header )[0] );
		if ( ! filter_var( $candidate, FILTER_VALIDATE_IP ) ) {
			continue;
		}
		if ( $candidate === $remote_addr ) {
			continue; // 与直连方相同，改写无意义。
		}

		return array(
			'ip'     => $candidate,
			'source' => 'cf',
			'edge'   => $remote_addr,
		);
	}

	// 是 CF 边缘但没给可用的客户端头 ⇒ 退化为边缘地址，不伪造。
	return array(
		'ip'     => $remote_addr,
		'source' => 'direct',
		'edge'   => '',
	);
}

/**
 * 归一 $_SERVER['REMOTE_ADDR']。
 *
 * 幂等：一旦改写（留下 SF_ORIGINAL_REMOTE_ADDR 标记）就不再重复。
 * CLI / WP-CLI 环境下 REMOTE_ADDR 通常不存在，天然不动。
 *
 * @return void
 */
function sf_real_ip_bootstrap() {
	if ( defined( 'SF_REAL_IP_DISABLED' ) && SF_REAL_IP_DISABLED ) {
		return;
	}
	if ( isset( $_SERVER['SF_ORIGINAL_REMOTE_ADDR'] ) ) {
		return; // 已处理。
	}
	if ( 'cli' === PHP_SAPI ) {
		return; // CLI 无直连方，不做猜测。
	}
	if ( ! isset( $_SERVER['REMOTE_ADDR'] ) ) {
		return;
	}

	$resolved = sf_real_ip_resolve(
		(string) $_SERVER['REMOTE_ADDR'],
		isset( $_SERVER['HTTP_CF_CONNECTING_IP'] ) ? (string) $_SERVER['HTTP_CF_CONNECTING_IP'] : '',
		isset( $_SERVER['HTTP_TRUE_CLIENT_IP'] ) ? (string) $_SERVER['HTTP_TRUE_CLIENT_IP'] : ''
	);

	if ( 'cf' !== $resolved['source'] ) {
		return;
	}

	$_SERVER['SF_ORIGINAL_REMOTE_ADDR'] = $resolved['edge'];
	$_SERVER['REMOTE_ADDR']             = $resolved['ip'];
}

sf_real_ip_bootstrap();

/**
 * 访客真实 IP —— 给其他 mu-plugin 共用的读取口。
 *
 * 因为本文件已把 REMOTE_ADDR 归一，这里直接读它即可；若被 SF_REAL_IP_DISABLED 关掉，
 * 返回值就是直连方地址（行为退回改造前，不会更差）。
 *
 * @return string
 */
function sf_real_ip_client_ip() {
	$remote = isset( $_SERVER['REMOTE_ADDR'] ) ? trim( (string) $_SERVER['REMOTE_ADDR'] ) : '';

	return ( '' !== $remote && filter_var( $remote, FILTER_VALIDATE_IP ) ) ? $remote : '0.0.0.0';
}

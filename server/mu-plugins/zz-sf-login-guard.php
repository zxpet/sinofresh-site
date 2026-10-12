<?php
/**
 * Plugin Name: SINO FRESH - Login Guard (password reset throttle)
 * Description: 限制密码重置端点（wp-login.php?action=lostpassword）被滥用：同一真实客户端 IP 在窗口期内最多 N 次请求，超限即锁定时长内直接拒绝（在进入 retrieve_password() 之前就中止，因此不会发出重置邮件）。真实 IP 只在 REMOTE_ADDR 属于 Cloudflare 官方网段时才采信 CF-Connecting-IP —— 本站源站 IP 可被公网直连绕过 Cloudflare，无条件信任该头等于给攻击者一个免费的白名单。DEV 与生产共用同一文件，无环境开关。
 * Version:     1.1.0
 * Author:      SINO FRESH
 *
 * v1.1.0 拦截摘要邮件：每天最多 1 封（wp-cron daily + sent_date 去重），只在当天确实发生
 * 拦截时才发。内容＝拦截次数、来源 IP Top10、发生时间段。状态存选项 sf_login_guard_digest。
 *
 * WHY THIS EXISTS
 *   wp-login.php?action=lostpassword 是匿名可达的，任何脚本只要提交一次表单就能让站点
 *   给账号本人发一封重置邮件 —— 2026-10-04/05 生产站就因此收到 5 封来自陌生 IP 的
 *   "[SINO FRESH] 密码重设"。隐藏登录地址（WPS Hide Login）能挡掉批量扫描器，但挡不住
 *   已经知道新地址的定向请求，所以端点本身必须限流。
 *
 * WHY NOT limit-login-attempts-reloaded
 *   该插件（免费版 3.3.10，源码已核）只挂 authenticate / wp_authenticate_user /
 *   wp_login_failed / xmlrpc_login_error，没有任何 lostpassword 钩子，
 *   它的 lostpassword 字样只出现在 Helpers::detect_gateway() 的请求打标里。
 *   换言之它限不了密码重置次数。
 *
 * WHERE THE MAIL IS SUPPRESSED
 *   wp-includes/user.php: retrieve_password() 在 do_action( 'lostpassword_post', $errors, $user_data )
 *   之后检查 $errors，有错误即 return，不到 wp_mail()。所以给 $errors 加一条错误
 *   ＝ 不发信，且不会泄露"这个用户名存不存在"。
 *
 * TUNING
 *   define 常量为默认值；也可用过滤器临时覆盖：
 *     sf_login_guard_max_attempts / sf_login_guard_window / sf_login_guard_lockout
 *   白名单（永不计数）：sf_login_guard_whitelist 过滤器返回 IP 数组。
 *   计数状态存在选项 sf_login_guard_state（autoload=no），
 *   清空即解除全部封锁：wp option delete sf_login_guard_state
 *
 * @package sinofresh
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/** 窗口期内允许的重置请求次数（第 N+1 次被拦）。 */
if ( ! defined( 'SF_LOGIN_GUARD_MAX_ATTEMPTS' ) ) {
	define( 'SF_LOGIN_GUARD_MAX_ATTEMPTS', 2 );
}
/** 计数窗口，秒。 */
if ( ! defined( 'SF_LOGIN_GUARD_WINDOW' ) ) {
	define( 'SF_LOGIN_GUARD_WINDOW', 300 );
}
/** 超限后的封锁时长，秒。 */
if ( ! defined( 'SF_LOGIN_GUARD_LOCKOUT' ) ) {
	define( 'SF_LOGIN_GUARD_LOCKOUT', 1800 );
}
/** 计数状态选项名。 */
define( 'SF_LOGIN_GUARD_STATE_OPTION', 'sf_login_guard_state' );
/** 日志前缀（落在 vhost error log，不是 web 可访问目录）。 */
define( 'SF_LOGIN_GUARD_LOG_TAG', '[sf-login-guard]' );
/** 状态表最多保留多少条客户端 IP 记录。 */
define( 'SF_LOGIN_GUARD_STATE_MAX_ENTRIES', 500 );

/**
 * Cloudflare 官方 IP 网段（2026-10-06 取自 https://www.cloudflare.com/ips-v4 / ips-v6）。
 * 用来判断"站在我们前面的是不是 CF 边缘"，只有是，才敢采信 CF-Connecting-IP。
 *
 * @return string[] CIDR 列表。
 */
function sf_login_guard_cf_ranges() {
	return array(
		// IPv4
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
		// IPv6
		'2400:cb00::/32',
		'2606:4700::/32',
		'2803:f800::/32',
		'2405:b500::/32',
		'2405:8100::/32',
		'2a06:98c0::/29',
		'2c0f:f248::/32',
	);
}

/**
 * 判断 IP 是否落在 CIDR 内（IPv4 / IPv6 都走同一套二进制前缀比较）。
 *
 * @param string $ip   待判 IP。
 * @param string $cidr 形如 104.16.0.0/13 或 2606:4700::/32。
 * @return bool
 */
function sf_login_guard_ip_in_cidr( $ip, $cidr ) {
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
 * REMOTE_ADDR 是否来自 Cloudflare 边缘。
 *
 * @param string $ip 直连方 IP。
 * @return bool
 */
function sf_login_guard_is_cloudflare( $ip ) {
	if ( '' === $ip || false === filter_var( $ip, FILTER_VALIDATE_IP ) ) {
		return false;
	}
	foreach ( sf_login_guard_cf_ranges() as $cidr ) {
		if ( sf_login_guard_ip_in_cidr( $ip, $cidr ) ) {
			return true;
		}
	}

	return false;
}

/**
 * 真实客户端 IP。
 *
 * 只有在 REMOTE_ADDR 属于 CF 网段时才看 CF-Connecting-IP；否则一律用 REMOTE_ADDR。
 * 原因：本站源站可被公网直连绕过 CF，直连时请求头完全由攻击者控制。
 *
 * @return string
 */
function sf_login_guard_client_ip() {
	$remote = isset( $_SERVER['REMOTE_ADDR'] ) ? trim( (string) $_SERVER['REMOTE_ADDR'] ) : '';

	if ( '' !== $remote && sf_login_guard_is_cloudflare( $remote ) ) {
		foreach ( array( 'HTTP_CF_CONNECTING_IP', 'HTTP_TRUE_CLIENT_IP' ) as $key ) {
			if ( empty( $_SERVER[ $key ] ) ) {
				continue;
			}
			$candidate = trim( explode( ',', (string) $_SERVER[ $key ] )[0] );
			if ( filter_var( $candidate, FILTER_VALIDATE_IP ) ) {
				return $candidate;
			}
		}
	}

	return '' !== $remote ? $remote : '0.0.0.0';
}

/**
 * 是否处于被封锁状态。
 *
 * @param array $entry 状态条目。
 * @param int   $now   当前时间戳。
 * @return int 解封时间戳；0 表示未封锁。
 */
function sf_login_guard_lock_until( $entry, $now ) {
	$lock_until = ( isset( $entry['lock_until'] ) && is_numeric( $entry['lock_until'] ) ) ? (int) $entry['lock_until'] : 0;

	return ( $lock_until > $now ) ? $lock_until : 0;
}

/**
 * 读取计数状态。
 *
 * @return array
 */
function sf_login_guard_get_state() {
	$state = get_option( SF_LOGIN_GUARD_STATE_OPTION, array() );

	return is_array( $state ) ? $state : array();
}

/**
 * 写回计数状态，并做剪枝（过期条目删除、总数封顶）。
 *
 * @param array $state 新状态。
 * @return void
 */
function sf_login_guard_set_state( $state ) {
	$now = time();
	$ttl = (int) apply_filters( 'sf_login_guard_window', SF_LOGIN_GUARD_WINDOW )
		+ (int) apply_filters( 'sf_login_guard_lockout', SF_LOGIN_GUARD_LOCKOUT );

	foreach ( $state as $key => $entry ) {
		$last = ( is_array( $entry ) && isset( $entry['last'] ) && is_numeric( $entry['last'] ) ) ? (int) $entry['last'] : 0;
		if ( ( $now - $last ) > $ttl ) {
			unset( $state[ $key ] );
		}
	}

	if ( count( $state ) > SF_LOGIN_GUARD_STATE_MAX_ENTRIES ) {
		uasort(
			$state,
			function ( $a, $b ) {
				$a_last = ( is_array( $a ) && isset( $a['last'] ) ) ? (int) $a['last'] : 0;
				$b_last = ( is_array( $b ) && isset( $b['last'] ) ) ? (int) $b['last'] : 0;
				return $b_last <=> $a_last;
			}
		);
		$state = array_slice( $state, 0, SF_LOGIN_GUARD_STATE_MAX_ENTRIES, true );
	}

	update_option( SF_LOGIN_GUARD_STATE_OPTION, $state, false );
}

/**
 * 是否针对"忘记密码"端点的请求。
 *
 * @return bool
 */
function sf_login_guard_is_reset_request() {
	$action = isset( $_REQUEST['action'] ) ? (string) $_REQUEST['action'] : '';

	return in_array( $action, array( 'lostpassword', 'retrievepassword' ), true );
}

/**
 * 写一行取证日志（落到 vhost error log）。
 *
 * @param string $message 日志正文。
 * @return void
 */
function sf_login_guard_log( $message ) {
	error_log( SF_LOGIN_GUARD_LOG_TAG . ' ' . $message );
}

/**
 * 生效的阈值（供过滤器临时覆盖与日志自证）。
 *
 * @return array{max:int,window:int,lockout:int}
 */
function sf_login_guard_thresholds() {
	return array(
		'max'     => max( 1, (int) apply_filters( 'sf_login_guard_max_attempts', SF_LOGIN_GUARD_MAX_ATTEMPTS ) ),
		'window'  => max( 1, (int) apply_filters( 'sf_login_guard_window', SF_LOGIN_GUARD_WINDOW ) ),
		'lockout' => max( 1, (int) apply_filters( 'sf_login_guard_lockout', SF_LOGIN_GUARD_LOCKOUT ) ),
	);
}

/**
 * 已封锁的客户端：在任何 action 处理之前就拒绝（GET 与 POST 都拦）。
 *
 * 挂在 login_init（wp-login.php:540，先于 action 分派）⇒ 连重置表单都不会渲染。
 *
 * @return void
 */
function sf_login_guard_block_locked_requests() {
	if ( ! sf_login_guard_is_reset_request() ) {
		return;
	}

	$ip    = sf_login_guard_client_ip();
	$now   = time();
	$state = sf_login_guard_get_state();
	$entry = isset( $state[ $ip ] ) && is_array( $state[ $ip ] ) ? $state[ $ip ] : array();
	$until = sf_login_guard_lock_until( $entry, $now );

	if ( ! $until ) {
		return;
	}

	$tl = sf_login_guard_thresholds();
	sf_login_guard_log(
		sprintf(
			'BLOCKED(locked) ip=%s remote=%s path=%s retry_after=%ds (limit=%d/%ds lock=%ds)',
			$ip,
			isset( $_SERVER['REMOTE_ADDR'] ) ? $_SERVER['REMOTE_ADDR'] : '-',
			isset( $_SERVER['REQUEST_URI'] ) ? preg_replace( '/[^\x20-\x7E]/', '', (string) $_SERVER['REQUEST_URI'] ) : '-',
			$until - $now,
			$tl['max'],
			$tl['window'],
			$tl['lockout']
		)
	);

	header( 'Retry-After: ' . ( $until - $now ) );

	sf_login_guard_digest_record_block( $ip );

	wp_die(
		esc_html__( 'Too many password reset requests from this connection. Please try again later.' ),
		esc_html__( 'Too Many Requests' ),
		array( 'response' => 429 )
	);
}
add_action( 'login_init', 'sf_login_guard_block_locked_requests', 1 );

/**
 * 计数一次重置请求；超限则加错误（＝retrieve_password 直接返回，不发邮件）并上锁。
 *
 * @param WP_Error      $errors    retrieve_password() 的错误容器。
 * @param WP_User|false $user_data 命中的用户对象或 false。
 * @return void
 */
function sf_login_guard_count_attempt( $errors, $user_data ) {
	if ( ! ( $errors instanceof WP_Error ) ) {
		return;
	}

	$ip    = sf_login_guard_client_ip();
	$now   = time();
	$tl    = sf_login_guard_thresholds();
	$state = sf_login_guard_get_state();
	$entry = isset( $state[ $ip ] ) && is_array( $state[ $ip ] ) ? $state[ $ip ] : array();

	$whitelist = apply_filters( 'sf_login_guard_whitelist', array() );
	if ( is_array( $whitelist ) && in_array( $ip, $whitelist, true ) ) {
		sf_login_guard_log( sprintf( 'ALLOW(whitelisted) ip=%s', $ip ) );
		return;
	}

	if ( sf_login_guard_lock_until( $entry, $now ) ) {
		// login_init 已经拦过，这里是兜底（例如插件直接调用 retrieve_password()）。
		$errors->add( 'sf_login_guard', __( 'Too many password reset requests from this connection. Please try again later.' ) );
		return;
	}

	$hits = ( isset( $entry['hits'] ) && is_array( $entry['hits'] ) ) ? $entry['hits'] : array();
	$hits = array_values(
		array_filter(
			$hits,
			function ( $ts ) use ( $now, $tl ) {
				return ( $now - (int) $ts ) < $tl['window'];
			}
		)
	);
	$hits[] = $now;

	$over = count( $hits ) > $tl['max'];

	$state[ $ip ] = array(
		'hits'       => $over ? array() : $hits,
		'last'       => $now,
		'lock_until' => $over ? ( $now + $tl['lockout'] ) : 0,
	);
	sf_login_guard_set_state( $state );

	$user_login = is_object( $user_data ) && isset( $user_data->user_login ) ? $user_data->user_login : '-';

	if ( $over ) {
		sf_login_guard_log(
			sprintf(
				'BLOCKED(threshold) ip=%s remote=%s attempts=%d/%d window=%ds lock=%ds user=%s',
				$ip,
				isset( $_SERVER['REMOTE_ADDR'] ) ? $_SERVER['REMOTE_ADDR'] : '-',
				count( $hits ),
				$tl['max'],
				$tl['window'],
				$tl['lockout'],
				$user_login
			)
		);

		$errors->add(
			'sf_login_guard',
			__( 'Too many password reset requests from this connection. Please try again later.' )
		);

		sf_login_guard_digest_record_block( $ip );

		return;
	}

	sf_login_guard_log(
		sprintf(
			'ALLOW ip=%s remote=%s attempts=%d/%d user=%s',
			$ip,
			isset( $_SERVER['REMOTE_ADDR'] ) ? $_SERVER['REMOTE_ADDR'] : '-',
			count( $hits ),
			$tl['max'],
			$user_login
		)
	);
}
add_action( 'lostpassword_post', 'sf_login_guard_count_attempt', 1, 2 );

/* ---------------------------------------------------------------------------
 * v1.1.0 拦截摘要邮件（每天最多 1 封）
 *
 * 设计约束（对应 H21 任务书）：
 *   - 频率控制：wp-cron daily 事件 + sent_date 去重 ⇒ 无论当天触发多少次拦截、
 *     cron 跑多少遍，一天最多发 1 封。
 *   - 空跑不发：当天没有任何拦截 ⇒ 不发信，避免"又一种邮件骚扰"。
 *   - 内容：拦截次数、来源 IP Top10、发生时间段。
 *   - 收件人：默认 admin_email；可用过滤器 sf_login_guard_digest_recipients 覆盖。
 * ------------------------------------------------------------------------- */

/** 摘要状态选项名（autoload=no）。 */
define( 'SF_LOGIN_GUARD_DIGEST_OPTION', 'sf_login_guard_digest' );
/** 摘要中最多列出的来源 IP 数。 */
define( 'SF_LOGIN_GUARD_DIGEST_MAX_IPS', 10 );
/** 摘要发送时刻（站点本地时区的小时，0-23）。 */
if ( ! defined( 'SF_LOGIN_GUARD_DIGEST_HOUR' ) ) {
	define( 'SF_LOGIN_GUARD_DIGEST_HOUR', 9 );
}

/**
 * 摘要统计的本地日期键（站点时区）。
 *
 * @return string Y-m-d
 */
function sf_login_guard_digest_today() {
	return wp_date( 'Y-m-d' );
}

/**
 * 读取摘要状态。
 *
 * @return array{date:string,blocked:int,ips:array<string,int>,first:int,last:int,sent_date:string}
 */
function sf_login_guard_digest_get() {
	$data = get_option( SF_LOGIN_GUARD_DIGEST_OPTION, array() );

	if ( ! is_array( $data ) ) {
		$data = array();
	}

	return wp_parse_args(
		$data,
		array(
			'date'      => '',
			'blocked'   => 0,
			'ips'       => array(),
			'first'     => 0,
			'last'      => 0,
			'sent_date' => '',
		)
	);
}

/**
 * 记录一次拦截到当日摘要。
 *
 * 跨天时整体清零重新累计（sent_date 也一并清掉）。
 *
 * @param string $ip 被拦截的真实客户端 IP。
 * @return void
 */
function sf_login_guard_digest_record_block( $ip ) {
	$today = sf_login_guard_digest_today();
	$data  = sf_login_guard_digest_get();
	$now   = time();

	if ( $data['date'] !== $today ) {
		$data = array(
			'date'      => $today,
			'blocked'   => 0,
			'ips'       => array(),
			'first'     => $now,
			'last'      => $now,
			'sent_date' => '',
		);
	}

	$data['blocked'] = (int) $data['blocked'] + 1;
	$data['ips']     = is_array( $data['ips'] ) ? $data['ips'] : array();
	$ip              = (string) $ip;
	$data['ips'][ $ip ] = isset( $data['ips'][ $ip ] ) ? (int) $data['ips'][ $ip ] + 1 : 1;

	if ( $data['first'] <= 0 || $now < (int) $data['first'] ) {
		$data['first'] = $now;
	}
	if ( $now > (int) $data['last'] ) {
		$data['last'] = $now;
	}

	update_option( SF_LOGIN_GUARD_DIGEST_OPTION, $data, false );
}

/**
 * 按拦截次数排序取 Top N。
 *
 * @param int $n 最多条数。
 * @return array<int,array{ip:string,count:int}>
 */
function sf_login_guard_digest_top_ips( $n = SF_LOGIN_GUARD_DIGEST_MAX_IPS ) {
	$data = sf_login_guard_digest_get();
	$ips  = (array) $data['ips'];

	arsort( $ips );

	$out = array();
	foreach ( array_slice( $ips, 0, max( 1, (int) $n ), true ) as $ip => $count ) {
		$out[] = array(
			'ip'    => (string) $ip,
			'count' => (int) $count,
		);
	}

	return $out;
}

/**
 * 注册每日摘要 cron（幂等；时刻＝站点本地时间 SF_LOGIN_GUARD_DIGEST_HOUR 点整）。
 *
 * @return void
 */
function sf_login_guard_digest_schedule() {
	if ( wp_next_scheduled( 'sf_login_guard_digest_event' ) ) {
		return;
	}

	$now_local  = current_time( 'timestamp' );
	$today_at_h = mktime( SF_LOGIN_GUARD_DIGEST_HOUR, 0, 0, (int) gmdate( 'n', $now_local ), (int) gmdate( 'j', $now_local ), (int) gmdate( 'Y', $now_local ) );
	$next       = ( $today_at_h > $now_local ) ? $today_at_h : $today_at_h + DAY_IN_SECONDS;

	wp_schedule_event( $next, 'daily', 'sf_login_guard_digest_event' );
}
add_action( 'init', 'sf_login_guard_digest_schedule' );

/**
 * cron 入口：有未发送的拦截批次 ⇒ 发送摘要。
 *
 * 按"批次日期"（data.date）发送与去重：昨天发送之后、当天晚间新增的拦截属于
 * 同一批次（sent_date == date）当天不再补发；其数据会保留到次日报告的时间段里
 * 呈现（时间段取 first/last），不会被清零丢失。
 *
 * @return bool 是否实际发信。
 */
function sf_login_guard_digest_send() {
	$data = sf_login_guard_digest_get();

	// 空批次不发；批次已发过不再发（cron 重复触发/手动重跑都不会多发）。
	if ( (int) $data['blocked'] <= 0 || $data['sent_date'] === $data['date'] ) {
		return false;
	}

	$recipients = apply_filters( 'sf_login_guard_digest_recipients', array( get_option( 'admin_email' ) ) );
	$recipients = array_values( array_filter( (array) $recipients ) );

	if ( empty( $recipients ) ) {
		return false;
	}

	$site  = wp_specialchars_decode( get_bloginfo( 'name' ), ENT_QUOTES );
	$day   = (string) $data['date'];
	$first = (int) $data['first'];
	$last  = max( $first, (int) $data['last'] );

	$lines   = array();
	$lines[] = sprintf( '站点：%s（%s）', $site, home_url( '/' ) );
	$lines[] = sprintf( '统计日期：%s', $day );
	$lines[] = sprintf( '拦截次数：%d 次', (int) $data['blocked'] );
	$lines[] = sprintf( '发生时间段：%s — %s（站点时区）', wp_date( 'H:i:s', $first ), wp_date( 'H:i:s', $last ) );
	$lines[] = '';
	$lines[] = sprintf( '来源 IP Top %d：', SF_LOGIN_GUARD_DIGEST_MAX_IPS );

	$top = sf_login_guard_digest_top_ips();
	if ( empty( $top ) ) {
		$lines[] = '  （无记录）';
	} else {
		$rank = 0;
		foreach ( $top as $row ) {
			$rank++;
			$lines[] = sprintf( '  %2d. %s —— %d 次', $rank, $row['ip'], $row['count'] );
		}
	}

	$lines[] = '';
	$lines[] = '完整取证日志：服务器 vhost error log，前缀 [sf-login-guard]。';
	$lines[] = '限流规则：同一 IP 5 分钟内最多 2 次密码重置请求，超限封锁 30 分钟（SINO FRESH Login Guard v1.1.0）。';

	$subject = sprintf( '[%s] 登录防护日报：%s 拦截 %d 次', $site, $day, (int) $data['blocked'] );
	$sent    = wp_mail( $recipients, $subject, implode( "\n", $lines ) );

	if ( $sent ) {
		$data['sent_date'] = $day;
		update_option( SF_LOGIN_GUARD_DIGEST_OPTION, $data, false );
		sf_login_guard_log( sprintf( 'DIGEST sent date=%s blocked=%d ips=%d', $day, (int) $data['blocked'], count( (array) $data['ips'] ) ) );
	} else {
		sf_login_guard_log( sprintf( 'DIGEST send FAILED date=%s blocked=%d', $day, (int) $data['blocked'] ) );
	}

	return (bool) $sent;
}
add_action( 'sf_login_guard_digest_event', 'sf_login_guard_digest_send' );

/**
 * 摘要去重保护：万一 cron 频道被第三方重复注册同日事件，仍然一天最多 1 封。
 * （真正的兜底在 sf_login_guard_digest_send() 的 sent_date 判断，这里是显式留痕。）
 */

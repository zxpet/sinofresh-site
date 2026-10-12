<?php
/* H24b 后台取证脚手架 —— 为 tools/h24b_admin_shots.js 签发临时 admin 凭据。
 *
 *   setup:    为 user 1 铸一个 30 分钟的 session token，把 host/COOKIEHASH/
 *             三枚签名 cookie/待截图的 admin URL 写进 $SF_H24B_CFG（默认
 *             /tmp/h24b-e2e.json）。不创建任何内容、不改任何 option。
 *   teardown: destroy 该 token（凭据不跨运行存活）并删除 cfg 文件。
 *
 * 为什么不是「每个站点固定一份 JSON」：cookie 是用该站自己的 AUTH_KEY/
 * SALT 与 COOKIEHASH 签的，dev 与 prod 的 hash 不同，必须由目标站自己铸。
 *
 *   SF_H24B_CFG=/tmp/h24b-e2e.dev.json  wp eval-file tools/h24b_admin_shots.php setup
 *   SF_H24B_CFG=/tmp/h24b-e2e.dev.json  wp eval-file tools/h24b_admin_shots.php teardown
 */
$action   = isset( $args[0] ) ? (string) $args[0] : '';
$cfg_path = getenv( 'SF_H24B_CFG' ) ?: '/tmp/h24b-e2e.json';

if ( 'setup' === $action ) {
	$uid     = 1;
	$form_id = (int) ( getenv( 'SF_H24B_FORM_ID' ) ?: 8 );
	$exp     = time() + 1800;
	$token   = WP_Session_Tokens::get_instance( $uid )->create( $exp );

	$main_counts = function_exists( 'sf_fg_entry_counts' ) ? sf_fg_entry_counts( $form_id ) : null;

	/* 空状态夹具：浏览器要断言「未读为空 ⇒ 显示引导并给两个出口」，需要一个真的
	   无未读表单。若主表单自己就是未读 0（生产 form 8 就是），不再另找，避免重复抓。 */
	$empty_id = 0;
	if ( null !== $main_counts && 0 !== (int) $main_counts['unread'] ) {
		global $wpdb;
		// phpcs:ignore WordPress.DB.DirectDatabaseQuery
		$ids = $wpdb->get_col( "SELECT id FROM {$wpdb->prefix}fluentform_forms ORDER BY id" );
		foreach ( (array) $ids as $cid ) {
			$cid = (int) $cid;
			if ( $cid === $form_id ) {
				continue;
			}
			if ( 0 === (int) sf_fg_entry_counts( $cid )['unread'] ) {
				$empty_id = $cid;
				break;
			}
		}
	}

	$cfg = array(
		'base'    => parse_url( home_url(), PHP_URL_SCHEME ) . '://' . parse_url( home_url(), PHP_URL_HOST ),
		'hash'    => COOKIEHASH,
		'exp'     => $exp,
		'uid'     => $uid,
		'token'   => $token,
		'form_id' => $form_id,
		// 服务端真值快照。⚠️ 只作提示用：FF 打开单条详情会把该条标已读 ⇒ 跨运行必然过期。
		// 真正的「等于 DB」断言在 h24b_l1.php 的 [L7]（同一进程内独立复算）。
		'counts'  => $main_counts,
		'empty_form_id' => $empty_id,
		'cookies' => array(
			'sec'       => wp_generate_auth_cookie( $uid, $exp, 'secure_auth', $token ),
			'auth'      => wp_generate_auth_cookie( $uid, $exp, 'auth', $token ),
			'logged_in' => wp_generate_auth_cookie( $uid, $exp, 'logged_in', $token ),
		),
		'urls'    => array(
			'guard'   => admin_url( 'admin.php?page=sf-form-guard' ),
			'entries' => admin_url( 'admin.php?page=fluent_forms&route=entries&form_id=' . $form_id ),
			'entries_empty' => $empty_id
				? admin_url( 'admin.php?page=fluent_forms&route=entries&form_id=' . $empty_id )
				: null,
			'smtp'    => admin_url( 'options-general.php?page=fluent-mail#/logs' ),
			'plugins' => admin_url( 'plugins.php' ),
		),
	);

	if ( false === file_put_contents( $cfg_path, json_encode( $cfg ) ) ) {
		fwrite( STDERR, "cfg 写入失败: {$cfg_path}\n" );
		exit( 1 );
	}
	@chmod( $cfg_path, 0600 );
	echo 'WROTE=' . $cfg_path . "\n";
	echo 'BASE=' . $cfg['base'] . "\n";
	echo 'HASH=' . $cfg['hash'] . "\n";
	echo 'TOKEN=' . $token . "\n";
	echo 'COUNTS=' . wp_json_encode( $main_counts ) . "\n";
	echo 'EMPTY_FORM=' . $empty_id . "\n";
} elseif ( 'teardown' === $action ) {
	$cfg   = json_decode( (string) @file_get_contents( $cfg_path ), true );
	$uid   = ! empty( $cfg['uid'] ) ? (int) $cfg['uid'] : 1;
	$token = ! empty( $cfg['token'] ) ? (string) $cfg['token'] : '';
	if ( '' !== $token ) {
		WP_Session_Tokens::get_instance( $uid )->destroy( $token );
		// 回读确认：destroy 后该 token 必须查不到。
		$still = WP_Session_Tokens::get_instance( $uid )->get( $token );
		echo 'TOKEN_DESTROYED=' . ( null === $still ? 'YES' : 'NO' ) . "\n";
	} else {
		echo "TOKEN_DESTROYED=n/a（cfg 不存在或已被清理）\n";
	}
	@unlink( $cfg_path );
	echo "CFG_REMOVED\n";
} else {
	fwrite( STDERR, "用法: wp eval-file tools/h24b_admin_shots.php setup|teardown\n" );
	exit( 2 );
}

<?php
/**
 * 批次 2B 阶段 1.2：sf_formula 数据迁移（dryrun | write | verify）
 * 用法：wp eval-file cpt2b-migrate.php -- <mode>
 * 数据源：/root/cpt-2b/formulas.json（本地 tools/b2s1_extract_formulas.py 产出）
 * 幂等：按 post_name 前缀 LIKE '<slug>%' 全状态查找（2A 坑：trash 改写 post_name）
 */
if ( ! defined( 'WP_CLI' ) || ! WP_CLI ) { echo "仅限 WP-CLI\n"; exit(1); }
global $wpdb;

$mode    = 'dryrun';
foreach ( (array) $args as $a ) { if ( in_array( $a, array( 'dryrun', 'write', 'verify' ), true ) ) { $mode = $a; } }
// ⛔ 铁律：CLI 无登录用户 → kses 会把 & 等实体双重转义进 term/meta。必须先模拟管理员。
wp_set_current_user( 1 );
if ( ! current_user_can( 'unfiltered_html' ) ) { WP_CLI::error( 'ID1 用户不具备 unfiltered_html，请先核对云端管理员' ); }
// kses 过滤器在 init 时按当时的用户挂载，事后切用户不会重挂 → 必须手动摘除
kses_remove_filters();
$json    = json_decode( file_get_contents( '/root/cpt-2b/formulas.json' ), true );
$records = $json['records'];
$form_titles = $json['form_title_map'];
printf( "模式=%s 记录数=%d\n", $mode, count( $records ) );

/**
 * 按 post_name 前缀查找（含全部状态）。返回 [post_name => [ID, post_title, post_status]]
 */
function sf2b_find_by_name_prefix( $prefix ) {
	global $wpdb;
	$like = $wpdb->esc_like( $prefix ) . '%';
	$rows = $wpdb->get_results( $wpdb->prepare(
		"SELECT ID, post_name, post_title, post_status FROM {$wpdb->posts}
		 WHERE post_type = 'sf_formula' AND post_name LIKE %s",
		$like
	) );
	$out = array();
	foreach ( (array) $rows as $r ) { $out[ $r->post_name ] = array( $r->ID, $r->post_title, $r->post_status ); }
	return $out;
}

function sf2b_ensure_term( $tax, $slug, $name ) {
	$existing = get_term_by( 'slug', $slug, $tax );
	if ( $existing ) {
		if ( sf2b_term_name_decoded( $existing->name ) !== $name ) { // 解码后比原文（WP 以实体存储含&term名）
			wp_update_term( $existing->term_id, $tax, array( 'name' => $name ) );
		}
		return (int) $existing->term_id;
	}
	$res = wp_insert_term( $name, $tax, array( 'slug' => $slug ) );
	if ( is_wp_error( $res ) ) { WP_CLI::error( "term 创建失败 [$tax/$slug]: " . $res->get_error_message() ); }
	return (int) $res['term_id'];
}

function sf2b_term_slug( $label ) {
	return sanitize_title( $label ); // use 标签原文 → slug（如 Skin & coat → skin-coat）
}

// ⛔ WP 内核把含 & 的 term 名以实体形式存储（pre_term_name: wp_filter_kses + _wp_specialchars，
//    default-filters.php L32-36，全网一致行为）。读取侧必须解码后再比原文；前端应原样输出（勿 esc_html）。
function sf2b_term_name_decoded( $name ) {
	return wp_specialchars_decode( $name, ENT_QUOTES );
}

$plan = array(); $created = 0; $updated = 0; $conflicts = array();
foreach ( $records as $r ) {
	$post_name = sanitize_title( $r['name'] );
	$hits      = sf2b_find_by_name_prefix( $post_name );
	// 同名冲突判据：存在同前缀记录但其精确 post_name 属于其他内容（不同 title）
	$exact = isset( $hits[ $post_name ] ) ? $hits[ $post_name ] : null;
	if ( $exact && $exact[1] !== $r['name'] ) {
		$conflicts[] = sprintf( '%s: post_name=%s 已被 ID%d「%s」占用', $r['name'], $post_name, $exact[0], $exact[1] );
		continue;
	}
	$plan[] = array(
		'record' => $r, 'post_name' => $post_name,
		'existing_id' => $exact ? (int) $exact[0] : 0,
		'action' => $exact ? 'update' : 'create',
	);
	if ( $exact ) { $updated++; } else { $created++; }
}

printf( "计划：创建 %d / 更新 %d / 冲突 %d\n", $created, $updated, count( $conflicts ) );
foreach ( $conflicts as $c ) { echo "  ⛔ 冲突: $c\n"; }

// 21 个 post_name 内部唯一性
$names = array_column( $plan, 'post_name' );
if ( count( array_unique( $names ) ) !== count( $names ) ) {
	WP_CLI::error( '计划内 post_name 有重复！' );
}

if ( 'dryrun' === $mode ) {
	foreach ( $plan as $p ) {
		printf( "  [%s] %-14s #%d %s → %s\n",
			$p['action'], $p['record']['dosage_slug'], $p['record']['idx'],
			$p['record']['name'], $p['post_name'] );
	}
	echo "干跑结束，未写库\n"; return;
}

if ( 'write' === $mode ) {
	if ( $conflicts ) { WP_CLI::error( '存在冲突，拒绝写入' ); }
	$written = array();
	foreach ( $plan as $p ) {
		$r    = $p['record'];
		$args = array(
			'post_type'   => 'sf_formula',
			'post_status' => 'publish',
			'post_title'  => $r['name'],
			'post_name'   => $p['post_name'],
			'menu_order'  => $r['idx'],
		);
		if ( $p['existing_id'] ) {
			$args['ID'] = $p['existing_id'];
			$id = wp_update_post( $args, true );
		} else {
			$id = wp_insert_post( $args, true );
		}
		if ( is_wp_error( $id ) ) { WP_CLI::error( "写入失败 [{$r['name']}]: " . $id->get_error_message() ); }
		update_post_meta( $id, 'sf_formula_ingredients', $r['ingredients'] );
		update_post_meta( $id, 'sf_formula_analysis',    $r['analysis'] );
		update_post_meta( $id, 'sf_formula_specs',       $r['specs'] );
		update_post_meta( $id, 'sf_formula_source',      $r['source'] );
		$form_title = $form_titles[ $r['dosage_slug'] ];
		$form_id = sf2b_ensure_term( 'sf_formula_form', $r['dosage_slug'], $form_title );
		$use_id  = sf2b_ensure_term( 'sf_formula_use', sf2b_term_slug( $r['use_label'] ), $r['use_label'] );
		wp_set_object_terms( $id, array( $form_id ), 'sf_formula_form' );
		wp_set_object_terms( $id, array( $use_id ), 'sf_formula_use' );
		$written[] = array( 'id' => $id, 'record' => $r );
	}
	echo "写入完成 " . count( $written ) . " 条\n";
	// 立即回读逐字符比对（第一遍）
	$bad = 0;
	foreach ( $written as $w ) {
		$r = $w['record']; $id = $w['id'];
		$post = get_post( $id );
		$chk = array(
			'title'    => $post->post_title === $r['name'],
			'name'     => $post->post_name === sanitize_title( $r['name'] ),
			'status'   => $post->post_status === 'publish',
			'order'    => (int) $post->menu_order === (int) $r['idx'],
			'ing'      => get_post_meta( $id, 'sf_formula_ingredients', true ) === $r['ingredients'],
			'ana'      => get_post_meta( $id, 'sf_formula_analysis', true ) === $r['analysis'],
			'spec'     => get_post_meta( $id, 'sf_formula_specs', true ) === $r['specs'],
			'src'      => get_post_meta( $id, 'sf_formula_source', true ) === $r['source'],
			'form'     => array_map( 'sf2b_term_name_decoded', wp_get_object_terms( $id, 'sf_formula_form', array( 'fields' => 'names') ) ) === array( $form_titles[ $r['dosage_slug'] ] ),
			'use'      => array_map( 'sf2b_term_name_decoded', wp_get_object_terms( $id, 'sf_formula_use', array( 'fields' => 'names') ) ) === array( $r['use_label'] ),
		);
		foreach ( $chk as $k => $ok ) { if ( ! $ok ) { echo "  ⛔ ID$id {$r['name']} 字段 $k 不符\n"; $bad++; } }
	}
	printf( "回读比对：%s（异常 %d 处）\n", $bad === 0 ? '✅ 21/21 全符' : '❌', $bad );
	return;
}

if ( 'verify' === $mode ) {
	// 独立复核模式：不依赖 write 进程内存
	$bad = 0;
	foreach ( $records as $r ) {
		$post_name = sanitize_title( $r['name'] );
		$hits = sf2b_find_by_name_prefix( $post_name );
		if ( ! isset( $hits[ $post_name ] ) ) { echo "  ⛔ 缺记录: {$r['name']} ($post_name)\n"; $bad++; continue; }
		$id   = $hits[ $post_name ][0];
		$post = get_post( $id );
		$chk = array(
			'title'  => $post->post_title === $r['name'],
			'status' => $post->post_status === 'publish',
			'order'  => (int) $post->menu_order === (int) $r['idx'],
			'ing'    => get_post_meta( $id, 'sf_formula_ingredients', true ) === $r['ingredients'],
			'ana'    => get_post_meta( $id, 'sf_formula_analysis', true ) === $r['analysis'],
			'spec'   => get_post_meta( $id, 'sf_formula_specs', true ) === $r['specs'],
			'src'    => get_post_meta( $id, 'sf_formula_source', true ) === $r['source'],
			'form'   => array_map( 'sf2b_term_name_decoded', wp_get_object_terms( $id, 'sf_formula_form', array( 'fields' => 'names') ) ) === array( $form_titles[ $r['dosage_slug'] ] ),
			'use'    => array_map( 'sf2b_term_name_decoded', wp_get_object_terms( $id, 'sf_formula_use', array( 'fields' => 'names') ) ) === array( $r['use_label'] ),
		);
		foreach ( $chk as $k => $ok ) { if ( ! $ok ) { echo "  ⛔ ID$id {$r['name']} 字段 $k 不符\n"; $bad++; } }
	}
	$total = (int) $wpdb->get_var( "SELECT COUNT(*) FROM {$wpdb->posts} WHERE post_type='sf_formula' AND post_status='publish'" );
	$forms = count( get_terms( array( 'taxonomy' => 'sf_formula_form', 'hide_empty' => false ) ) );
	$uses  = count( get_terms( array( 'taxonomy' => 'sf_formula_use', 'hide_empty' => false ) ) );
	printf( "独立复核：publish=%d / term form=%d / term use=%d / 异常 %d 处 → %s\n",
		$total, $forms, $uses, $bad, ( 21 === $total && 0 === $bad ) ? '✅' : '❌' );
	return;
}

WP_CLI::error( "未知模式 {$mode}（可选 dryrun/write/verify）" );

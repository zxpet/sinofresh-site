<?php
/**
 * 只读前置检查 + WP 标准 API trash DB 模板覆盖记录（ID 77 page-products / ID 7 index）
 * 用法：php -d mysqli.default_socket=$SOCK trash-templates.php [--execute]
 * 不带 --execute 时只打印将要做的操作。
 */
if (PHP_SAPI !== 'cli') { exit("CLI only\n"); }
$EXECUTE = in_array('--execute', $argv, true);

$_SERVER['HTTP_HOST'] = 'sinofresh.local';
$_SERVER['REQUEST_URI'] = '/';
require '/Users/meng/Local Sites/sinofresh/app/public/wp-load.php';

$ids = array( 77, 7 );
foreach ( $ids as $id ) {
	$post = get_post( $id );
	if ( ! $post ) {
		echo "ID {$id}: NOT FOUND\n";
		continue;
	}
	echo "ID {$id}: type={$post->post_type} status={$post->status} name={$post->post_name} len=" . strlen( $post->post_content ) . "\n";
	if ( 'wp_template' !== $post->post_type ) {
		echo "ID {$id}: SKIP (not wp_template)\n";
		continue;
	}
	if ( 'trash' === $post->post_status ) {
		echo "ID {$id}: SKIP (already trashed)\n";
		continue;
	}
	if ( ! $EXECUTE ) {
		echo "ID {$id}: WOULD trash\n";
		continue;
	}
	$result = wp_trash_post( $id );
	if ( $result && 'trash' === $result->post_status ) {
		echo "ID {$id}: TRASHED, new name={$result->post_name}, new status={$result->post_status}\n";
		echo "  trash_meta_status=" . get_post_meta( $id, '_wp_trash_meta_status', true ) . "\n";
		echo "  desired_slug=" . get_post_meta( $id, '_wp_desired_post_slug', true ) . "\n";
	} else {
		echo "ID {$id}: TRASH FAILED\n";
	}
}
echo "done (execute=" . ( $EXECUTE ? 'yes' : 'no' ) . ")\n";

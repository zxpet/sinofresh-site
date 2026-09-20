<?php
/**
 * Read-only: ask TranslatePress's own dictionary API for the strings that the
 * translation interface would render, instead of re-implementing its SQL.
 *
 * The editor reads the regular-string table through
 * TRP_Query::get_string_rows() (includes/queries/class-query.php:483), so a row
 * returned here is a row the interface can show. Nothing is written.
 */

$trp = TRP_Translate_Press::get_trp_instance();
$query = $trp->get_component( 'query' );

foreach ( array( 'Browse All Formulas →' ) as $needle ) {
	$rows = $query->get_string_rows( array(), array( $needle ), 'zh_CN' );
	printf( "query: %s\n", var_export( $needle, true ) );
	printf( "rows : %d\n", count( $rows ) );
	foreach ( $rows as $key => $row ) {
		printf( "  key=%s\n", var_export( $key, true ) );
		printf( "    id=%s original=%s\n",
			isset( $row->id ) ? $row->id : '-',
			isset( $row->original ) ? var_export( $row->original, true ) : '-' );
		printf( "    translated=%s status=%s block_type=%s original_id=%s\n",
			isset( $row->translated ) ? var_export( $row->translated, true ) : '-',
			isset( $row->status ) ? $row->status : '-',
			isset( $row->block_type ) ? $row->block_type : '-',
			isset( $row->original_id ) ? $row->original_id : '-' );
	}
}

/* a couple of neighbours, to show the row is not an oddity */
echo "\nneighbours (same table, ids 1310-1316):\n";
global $wpdb;
$t = $wpdb->prefix . 'trp_dictionary_en_us_zh_cn';
$rows = $wpdb->get_results( "SELECT id, LEFT(original,60) AS o, translated, status, original_id FROM {$t} WHERE id BETWEEN 1310 AND 1316 ORDER BY id" );
foreach ( $rows as $r ) {
	printf( "  %s  %-62s translated=%s status=%s original_id=%s\n",
		$r->id, '[' . $r->o . ']', var_export( $r->translated, true ), $r->status, $r->original_id );
}

echo "\nsettings that decide whether strings are collected:\n";
$s = get_option( 'trp_settings' );
foreach ( array( 'default-language', 'translation-languages', 'manual_translation_only', 'enable_numerals_translation', 'machine_translation_active' ) as $k ) {
	printf( "  %-28s %s\n", $k, isset( $s[ $k ] ) ? var_export( $s[ $k ], true ) : '(unset)' );
}

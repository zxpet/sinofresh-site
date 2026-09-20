<?php
/** Read-only: the three populated meta fields, every record, verbatim. */
global $wpdb;
$ids = $wpdb->get_col("SELECT ID FROM {$wpdb->posts} WHERE post_type='sf_formula' AND post_status='publish' ORDER BY menu_order ASC, post_title ASC");
foreach ($ids as $id) {
	$t = html_entity_decode(get_the_title((int) $id), ENT_QUOTES, 'UTF-8');
	echo "== {$id} :: {$t}\n";
	foreach (array('sf_formula_ingredients', 'sf_formula_analysis', 'sf_formula_specs') as $k) {
		printf("   %-24s %s\n", $k, (string) get_post_meta((int) $id, $k, true));
	}
}

<?php
/**
 * Apply the ZH withdrawal, once, via `wp eval-file`.
 *
 * Two changes and nothing else: zh_CN leaves publish-languages, and the v2
 * floater is switched off. translation-languages is deliberately kept, so the
 * 2388 registered strings stay reachable in the TranslatePress editor for the
 * day the translations are actually written.
 *
 * The read-back is the point of this script rather than an afterthought.
 * class-upgrade.php carries a legacy repair that rewrites publish-languages
 * back to translation-languages when the two are mutual subsets, so the value
 * has to be read out of the option table after the write instead of assumed.
 */

global $wpdb;

$before_settings = get_option('trp_settings');
$before_switch   = get_option('trp_language_switcher_settings');

echo "BEFORE publish-languages     : " . json_encode($before_settings['publish-languages']) . "\n";
echo "BEFORE translation-languages : " . json_encode($before_settings['translation-languages']) . "\n";
echo "BEFORE floater.enabled       : " . var_export($before_switch['floater']['enabled'], true) . "\n";
echo "\n";

$settings = $before_settings;
$settings['publish-languages'] = array('en_US');
update_option('trp_settings', $settings);

$switch = $before_switch;
$switch['floater']['enabled'] = false;
update_option('trp_language_switcher_settings', $switch);

/* Fresh reads, not the in-request cache: an option filter or the upgrade
   repair would only show up here. */
wp_cache_delete('trp_settings', 'options');
wp_cache_delete('trp_language_switcher_settings', 'options');
wp_cache_delete('alloptions', 'options');
$after_settings = get_option('trp_settings');
$after_switch   = get_option('trp_language_switcher_settings');

echo "AFTER  publish-languages     : " . json_encode($after_settings['publish-languages']) . "\n";
echo "AFTER  translation-languages : " . json_encode($after_settings['translation-languages']) . "\n";
echo "AFTER  url-slugs             : " . json_encode($after_settings['url-slugs']) . "\n";
echo "AFTER  default-language      : " . json_encode($after_settings['default-language']) . "\n";
echo "AFTER  floater.enabled       : " . var_export($after_switch['floater']['enabled'], true) . "\n";
echo "AFTER  switch keys           : " . json_encode(array_keys($after_switch)) . "\n";

$table      = $wpdb->prefix . 'trp_dictionary_en_us_zh_cn';
$rows       = (int) $wpdb->get_var("SELECT COUNT(*) FROM {$table}");
$translated = (int) $wpdb->get_var("SELECT COUNT(*) FROM {$table} WHERE translated <> ''");
echo "dictionary rows kept         : {$rows} (non-empty translations: {$translated})\n";
echo "\n";

/* The row count is printed but NOT asserted on: TranslatePress registers a
   string the first time a front-end render meets it, so the total grows every
   time a page under /zh/ is fetched -- it read 2388 at survey time and 2435 by
   the time this ran, and the difference is the crawls in between, not a change
   to what this script does. The claim worth asserting is the one that does not
   move: none of those registered strings has ever been translated. */
$ok = ($after_settings['publish-languages'] === array('en_US'))
   && ($after_settings['translation-languages'] === array('en_US', 'zh_CN'))
   && ($after_settings['url-slugs'] === array('en_US' => 'en', 'zh_CN' => 'zh'))
   && ($after_switch['floater']['enabled'] === false)
   && ($translated === 0);

echo $ok ? "APPLY_OK\n" : "APPLY_CHECK_FAILED\n";

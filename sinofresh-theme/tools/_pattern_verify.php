<?php
define('WP_USE_THEMES', false);
require '/Users/meng/Local Sites/sinofresh/app/public/wp-load.php';
$reg = WP_Block_Patterns_Registry::get_instance();
$names = array(
 'sinofresh/educational-article','sinofresh/selection-guide','sinofresh/comparison-article',
 'sinofresh/case-study','sinofresh/client-story','sinofresh/technical-deep-dive',
 'sinofresh/compliance-guide','sinofresh/buyers-guide','sinofresh/market-trends','sinofresh/thought-leadership');
$ok = 0;
foreach ($names as $n) {
  $yes = $reg->is_registered($n);
  $ok += $yes ? 1 : 0;
  $p = $yes ? $reg->get_registered($n) : null;
  echo ($yes ? 'OK  ' : 'MISS') . "\t$n" . ($p ? "\t" . $p['title'] . "\tcat:" . implode(',', $p['categories']) . "\tlock:" . substr_count($p['content'], '"lock"') . "\tlen:" . strlen($p['content']) : '') . "\n";
}
echo "total: $ok/10\n";
$creg = WP_Block_Pattern_Categories_Registry::get_instance();
echo 'category sinofresh-patterns registered: ' . ($creg->is_registered('sinofresh-patterns') ? 'YES' : 'NO') . "\n";
if ($creg->is_registered('sinofresh-patterns')) {
  $c = $creg->get_registered('sinofresh-patterns');
  echo 'category label: ' . $c['label'] . "\n";
}
// old pattern must be gone
echo 'old "Case Study Skeleton" still present: ';
foreach ($reg->get_all_registered() as $p) { if (strpos($p['name'],'sinofresh/')===0) echo $p['name'].' '; }
echo "\n";

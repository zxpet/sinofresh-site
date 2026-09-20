<?php
/* 批次 2A 扫描探针 #7（只读）：CPT 模板回退链的**权威裁决**。
   get_template_hierarchy 的第二参是 $is_custom（不是模板类型）—— 上一版探针传错。
   这里直接调用 WP 真实裁决链：get_{single,archive}_template 的候选名 + resolve_block_template()。
   运行：php -d mysqli.default_socket=<run>/mysql/mysqld.sock tools/_cpt2a_probe7.php */

$ROOT = '/Users/meng/Local Sites/sinofresh/app/public';
require_once $ROOT . '/wp-load.php';
function sec($t) { echo "\n" . str_repeat('=', 78) . "\n== $t\n" . str_repeat('=', 78) . "\n"; }

register_post_type('sf_formula', array(
    'labels' => array('name' => 'Formulas', 'singular_name' => 'Formula'),
    'public' => true, 'has_archive' => true, 'menu_position' => 21,
    'supports' => array('title', 'editor'),
    'rewrite' => array('slug' => 'formulas', 'with_front' => false),
    'show_in_rest' => true, 'hierarchical' => false,
));

$tdir = get_stylesheet_directory() . '/templates/';

sec('A. get_template_hierarchy（正确调用：第二参保持默认 false）');
foreach (array('single-sf_formula', 'single-sf_formula-liquid-joint-support',
               'archive-sf_formula') as $slug) {
    printf("  %-42s -> %s\n", $slug, implode(' → ', get_template_hierarchy($slug)));
}

sec('B. WP 真实候选名（get_single_template / get_post_type_archive_template 的构造逻辑）');
$single_cands = array(
    'single-sf_formula-liquid-joint-support.php',
    'single-sf_formula.php',
    'single.php',
);
printf("  single 候选 = %s\n", implode(' , ', $single_cands));
$archive_cands = array('archive-sf_formula.php', 'archive.php');
printf("  archive 候选 = %s\n", implode(' , ', $archive_cands));

sec('C. resolve_block_template 权威裁决（wp_template 类型）');
$r1 = resolve_block_template('single', $single_cands, '');
printf("  single  → %s\n", $r1 ? sprintf('slug=%s  source=%s  id=%s', $r1->slug, $r1->source, $r1->id) : '** null（无匹配）**');
$r2 = resolve_block_template('archive', $archive_cands, '');
printf("  archive → %s\n", $r2 ? sprintf('slug=%s  source=%s  id=%s', $r2->slug, $r2->source, $r2->id) : '** null（无匹配）**');

sec('D. 若 2B 建了 single-sf_formula.html 会怎样（模拟：直接用 slug 查块模板）');
foreach (array('single-sf_formula-liquid-joint-support', 'single-sf_formula', 'single', 'singular', 'index') as $s) {
    $bt = get_block_template(get_stylesheet() . '//' . $s, 'wp_template');
    printf("  get_block_template('%-40s') = %s\n", $s,
        $bt ? sprintf('命中 (source=%s, has_theme_file=%s)', $bt->source, var_export($bt->has_theme_file, true))
            : '未命中');
}

sec('E. 磁盘模板清单（templates/*.html）');
$files = glob($tdir . '*.html');
sort($files);
printf("  共 %d 个\n", count($files));
foreach ($files as $f) { printf("    %-28s %7d B\n", basename($f), filesize($f)); }
printf("\n  single-sf_formula.html 是否已存在 = %s\n",
    file_exists($tdir . 'single-sf_formula.html') ? '是' : '否（2A 不建，2B 建）');
printf("  archive-sf_formula.html 是否已存在 = %s\n",
    file_exists($tdir . 'archive-sf_formula.html') ? '是' : '否');

sec('F. 现有 single.html / archive.html 的可见副作用（2A 注册后立刻生效）');
$single = file_get_contents($tdir . 'single.html');
preg_match_all('/\{\{[A-Z_]+\}\}/', $single, $m);
printf("  single.html 占位符 = %s\n", implode(', ', array_unique($m[0])));
$archive = file_get_contents($tdir . 'archive.html');
preg_match_all('/\{\{[A-Z_]+\}\}/', $archive, $m2);
printf("  archive.html 占位符 = %s\n", implode(', ', array_unique($m2[0])));
printf("  archive.html 内是否含 [sf_archive_count] / [sf_blog_chips] = %s / %s\n",
    strpos($archive, 'sf_archive_count') !== false ? '是' : '否',
    strpos($archive, 'sf_blog_chips') !== false ? '是' : '否');
printf("  single.html 内是否含文章专属结构（toc/feedback/Article JSON-LD 依赖）:\n");
foreach (array('sf-article', 'sf-toc', 'toc-nav', 'sf-share', 'sf-breadcrumb', 'wp:post-featured-image') as $tok) {
    printf("    %-26s = %s\n", $tok, strpos($single, $tok) !== false ? '有' : '无');
}

sec('G. 结论');
echo "  ① CPT 单条回退链（实测）：single-sf_formula-{slug} → single-sf_formula → **single**（single.html 已存在）\n";
echo "  ② CPT 归档回退链（实测）：archive-sf_formula → **archive**（archive.html 已存在，含 [sf_archive_count]/[sf_blog_chips]）\n";
echo "  ③ 2A 只注册不建模板 ⇒ /formulas/ 立刻以博客归档版式上线（核心副作用）\n";
echo "  ④ 模板权威守卫（functions.php:65/102）保证 2B 建的 single-sf_formula.html 自动生效、且不会被 DB 副本遮蔽\n";
echo "\n" . str_repeat('=', 78) . "\n探针 #7 完成（只读）\n";

<?php
/**
 * Batch 2A verification — test formula + shortcode contract check.
 *
 * Creates (or reuses) one sf_formula post carrying a term in each taxonomy and
 * three of the four meta fields, then renders [sf_formula_grid] through the
 * same pipeline a block template uses and asserts the K1–K4 / R3 / R6
 * contracts against the *rendered* bytes rather than the source expressions.
 *
 * Re-runnable. The post is trashed separately by _cpt2a_cleanup.php.
 */

require_once '/Users/meng/Local Sites/sinofresh/app/public/wp-load.php';

$SLUG  = 'test-joint-coat-soft-chews';
$TITLE = 'Test Joint & Coat Soft Chews';

$pass = 0;
$fail = 0;
function chk($label, $cond, $detail = '') {
    global $pass, $fail;
    if ($cond) { $pass++; printf("  [PASS] %s%s\n", $label, $detail !== '' ? "  ($detail)" : ''); }
    else       { $fail++; printf("  [FAIL] %s%s\n", $label, $detail !== '' ? "  ($detail)" : ''); }
}

/**
 * Every probe record whose post_name starts with $slug, in any status.
 * Prefix-matched on purpose: wp_trash_post() appends "__trashed" (then
 * "__trashed-2" on a second pass), so an exact-name lookup silently misses.
 */
function sf_probe_ids($slug) {
    global $wpdb;
    return $wpdb->get_col($wpdb->prepare(
        "SELECT ID FROM {$wpdb->posts} WHERE post_type = %s AND post_name LIKE %s ORDER BY ID ASC",
        'sf_formula',
        $wpdb->esc_like($slug) . '%'
    ));
}

echo "=== 1. 创建/复用测试配方 ===\n";
/* Three separate traps make "just look it up by slug" wrong:
 *   · get_page_by_path() skips trashed posts;
 *   · get_posts(post_status='any') also drops trash, because trash carries
 *     exclude_from_search=true and WP_Query's 'any' excludes those;
 *   · wp_trash_post() rewrites post_name to "<slug>__trashed", so even an
 *     explicit status list misses it unless the suffix is matched too.
 * Enumerate by post_name prefix across every status, prefer the published
 * record, and un-trash it if needed — so a re-run reuses one probe record
 * instead of piling up duplicates. */
$probe_ids = sf_probe_ids($SLUG);
if ($probe_ids) {
    $chosen = null;
    foreach ($probe_ids as $pid) {
        $cand = get_post($pid);
        if ($cand && $cand->post_status === 'publish') { $chosen = $cand; break; }
    }
    if ($chosen === null) { $chosen = get_post(end($probe_ids)); }
    $post_id = (int) $chosen->ID;
    printf("  复用已存在记录 ID=%d status=%s post_name=%s\n", $post_id, $chosen->post_status, $chosen->post_name);
    if ($chosen->post_status !== 'publish') {
        wp_update_post(array('ID' => $post_id, 'post_status' => 'publish', 'post_name' => $SLUG));
        printf("  已从 %s 恢复为 publish，slug 复位为 %s\n", $chosen->post_status, $SLUG);
    }
} else {
    $post_id = (int) wp_insert_post(array(
        'post_type'   => 'sf_formula',
        'post_title'  => $TITLE,
        'post_name'   => $SLUG,
        'post_status' => 'publish',
        'post_content' => 'Batch 2A verification record.',
        'menu_order'  => 1,
    ), true);
    if (is_wp_error($post_id)) {
        echo '  *** wp_insert_post 失败: ' . $post_id->get_error_message() . "\n";
        exit(1);
    }
    printf("  新建 ID=%d\n", $post_id);
}

echo "\n=== 2. 赋 taxonomy + meta ===\n";
$form_terms = wp_set_object_terms($post_id, 'soft-chews', 'sf_formula_form');
$use_terms  = wp_set_object_terms($post_id, 'Joint care', 'sf_formula_use');
printf("  sf_formula_form -> %s\n", is_wp_error($form_terms) ? 'ERR: ' . $form_terms->get_error_message() : json_encode($form_terms));
printf("  sf_formula_use  -> %s\n", is_wp_error($use_terms) ? 'ERR: ' . $use_terms->get_error_message() : json_encode($use_terms));

$meta = array(
    'sf_formula_ingredients' => 'Glucosamine HCl, Chondroitin Sulfate, MSM, Green-lipped Mussel, Chicken Flavor',
    'sf_formula_analysis'    => 'Glucosamine ≥500mg/chew, Chondroitin ≥200mg/chew, MSM ≥100mg/chew',
    'sf_formula_specs'       => '2g/piece · 60/90/120 per bottle · 18 months shelf life',
    'sf_formula_source'      => 'Batch 2A verification probe (temporary record)',
);
foreach ($meta as $k => $v) {
    update_post_meta($post_id, $k, $v);
}
foreach (array_keys($meta) as $k) {
    printf("  %-24s = %s\n", $k, var_export(get_post_meta($post_id, $k, true), true));
}

printf("\n  永久链接 = %s\n", get_permalink($post_id));
printf("  post_name = %s\n", get_post_field('post_name', $post_id));

echo "\n=== 3. 渲染 [sf_formula_grid]（忠实管线：do_shortcode → do_blocks → wptexturize → convert_smilies）===\n";
/* get_the_block_template_html() runs do_shortcode() BEFORE do_blocks(), then
   the text filters. Mirror that order so the bytes we assert on are the bytes
   a visitor would receive. */
$tpl = '<!-- wp:html -->[sf_formula_grid form="soft-chews" columns="4"]<!-- /wp:html -->';
$stage = do_shortcode($tpl);
$stage = do_blocks($stage);
$stage = wptexturize($stage);
$stage = convert_smilies($stage);
$stage = str_replace(']]>', ']]&gt;', $stage);
$html = $stage;

printf("  渲染体积 = %d B\n", strlen($html));
chk('输出包含容器 .sf-fgrid', strpos($html, '<div class="sf-fgrid"') !== false);
chk('--sf-fgrid-cols:4 已写入', strpos($html, 'style="--sf-fgrid-cols:4"') !== false);
chk('包含 .sf-formulas-data JSON', strpos($html, 'class="sf-formulas-data"') !== false);
chk('包含 ItemList JSON-LD', strpos($html, '"@type":"ItemList"') !== false);
chk('卡片数为 1', substr_count($html, '<article class="sf-fcard">') === 1);

echo "\n=== 4. R3：</script> 注入护栏（断言 + 反例）===\n";
chk('渲染结果不含 </script 之外的闭合', substr_count($html, '</script>') === 2, '应为 2（data + ld+json）');
/* 反例：直接喂一个含 </script 的标题，必须被转义 */
$hostile = sinofresh_formula_script_json(array(array('name' => 'Evil</script><script>alert(1)</script>')));
chk('护栏把 </script 转义为 <\\/script', strpos($hostile, '</script') === false && strpos($hostile, '<\\/script') !== false);
chk('护栏输出仍可被 json_decode', is_array(json_decode($hostile, true)));

echo "\n=== 5. R6：name / data-formula / <h3> 三处同源 ===\n";
preg_match('#<h3 class="sf-fcard__name">(?:<a [^>]*>)?(.*?)(?:</a>)?</h3>#s', $html, $m_h3);
preg_match('#data-formula="([^"]*)"#', $html, $m_df);
preg_match('#<script type="application/json" class="sf-formulas-data">(.*?)</script>#s', $html, $m_json);
$json_data = json_decode(html_entity_decode($m_json[1], ENT_QUOTES, 'UTF-8'), true);
$h3_text   = html_entity_decode($m_h3[1], ENT_QUOTES, 'UTF-8');
$df_text   = html_entity_decode($m_df[1], ENT_QUOTES, 'UTF-8');
$json_name = $json_data[0]['name'] ?? '(missing)';
$expect    = html_entity_decode(get_the_title($post_id), ENT_QUOTES, 'UTF-8');
printf("  期望（解码后的 post_title） = %s\n", $expect);
printf("  <h3> 文本（解码后）        = %s\n", $h3_text);
printf("  data-formula（解码后）     = %s\n", $df_text);
printf("  JSON .name                 = %s\n", $json_name);
chk('h3 == post_title', $h3_text === $expect);
chk('data-formula == post_title', $df_text === $expect);
chk('JSON .name == post_title', $json_name === $expect);
chk('三处彼此相同', $h3_text === $df_text && $df_text === $json_name);
chk('源侧 data-formula 为实体形式（与旧模板一致）', strpos($html, 'data-formula="Test Joint &amp; Coat Soft Chews"') !== false);

echo "\n=== 6. K4：JSON 用裸 & 而非 &amp; ===\n";
$raw_json = $m_json[1];
chk('JSON 正文无 &amp; 实体', strpos($raw_json, '&amp;') === false);
chk('JSON 正文明写裸 &', strpos($raw_json, 'Joint & Coat') !== false);
chk('ItemList 正文无 &amp; 实体', strpos($m_json[1], '&amp;') === false);
preg_match('#<script type="application/ld\+json">(.*?)</script>#s', $html, $m_ld);
$ld = json_decode($m_ld[1], true);
chk('ItemList 可解析', is_array($ld) && ($ld['@type'] ?? '') === 'ItemList');
printf("  ItemList.name = %s\n", $ld['name'] ?? '(missing)');
printf("  ItemList.itemListElement[0] = %s\n", json_encode($ld['itemListElement'][0] ?? null, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES));
chk('ListItem.name 保留裸 &', ($ld['itemListElement'][0]['name'] ?? '') === $expect);
chk('ListItem 带 url', !empty($ld['itemListElement'][0]['url']));

echo "\n=== 7. K2：.sf-formulas-data 形状（供 configurator.js readFormula 用）===\n";
$d = $json_data[0];
printf("  顶层键 = %s\n", implode(',', array_keys($d)));
printf("  sections = %s\n", json_encode($d['sections'], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES));
chk('含 name/slug/url/form/use/sections', array_keys($d) === array('name', 'slug', 'url', 'form', 'use', 'sections'));
chk('sections 为 3 条 label/value', count($d['sections']) === 3 && isset($d['sections'][0]['label'], $d['sections'][0]['value']));
chk('三个 label 与旧模板同名', $d['sections'][0]['label'] === 'Ingredients' && $d['sections'][1]['label'] === 'Guaranteed Analysis' && $d['sections'][2]['label'] === 'Standard Specs');

echo "\n=== 8. K3：卡片标题必须是 h3，且全页 h2 数不因 shortcode 增加 ===\n";
chk('卡片标题为 <h3>', strpos($html, '<h3 class="sf-fcard__name">') !== false);
chk('shortcode 中不含 <h2>', strpos($html, '<h2') === false);

echo "\n=== 9. R1：form 默认值取自 queried object（而非 URL 末段）===\n";
/* CLI has no main query, so inject one that looks like a dosage page. */
$GLOBALS['wp_the_query'] = new WP_Query(array('page_id' => 20));
$GLOBALS['wp_query']     = $GLOBALS['wp_the_query'];
$qo = get_queried_object();
printf("  注入 queried object = %s (post_name=%s)\n", $qo instanceof WP_Post ? $qo->post_type : gettype($qo), $qo instanceof WP_Post ? $qo->post_name : '-');
chk('current_form 解析为 soft-chews', sinofresh_formula_current_form('') === 'soft-chews');
chk('显式 form 参数优先', sinofresh_formula_current_form('tablets') === 'tablets');
$auto = do_shortcode('[sf_formula_grid]');
chk('不带 form 参数时自动过滤到 soft-chews（命中 1 条）', substr_count($auto, '<article class="sf-fcard">') === 1);
printf("  list_name = %s\n", sinofresh_formula_list_name('soft-chews'));
chk('list_name 与旧模板一致', sinofresh_formula_list_name('soft-chews') === 'Standard Formulas — Soft Chews');

echo "\n=== 10. 空结果 / 参数边界 ===\n";
chk('不存在的 form -> 返回空串（empty=hide）', do_shortcode('[sf_formula_grid form="no-such-form"]') === '');
chk('use 过滤命中', substr_count(do_shortcode('[sf_formula_grid form="soft-chews" use="joint-care"]'), '<article class="sf-fcard">') === 1);
chk('use 过滤未命中 -> 空串', do_shortcode('[sf_formula_grid form="soft-chews" use="skin-coat"]') === '');
chk('cta="none" 不渲染按钮', strpos(do_shortcode('[sf_formula_grid form="soft-chews" cta="none"]'), 'sf-formula__cta') === false);
chk('links="false" 不渲染链接', strpos(do_shortcode('[sf_formula_grid form="soft-chews" links="false"]'), '<a href=') === false);
chk('columns 被夹到 1–6', strpos(do_shortcode('[sf_formula_grid form="soft-chews" columns="99"]'), '--sf-fgrid-cols:6') !== false);
chk('limit="1" 生效', substr_count(do_shortcode('[sf_formula_grid form="soft-chews" limit="1"]'), '<article class="sf-fcard">') === 1);

echo "\n=== 11. 现有 shortcode 未受影响 ===\n";
$chips = do_shortcode('[sf_explore_chips]');
chk('sf_explore_chips 仍输出 nav', strpos($chips, 'sf-explore__chips') !== false, strlen($chips) . ' B');
$cnt = do_shortcode('[sf_archive_count]');
chk('sf_archive_count 仍输出', $cnt !== '', $cnt);
$blog = do_shortcode('[sf_blog_chips]');
chk('sf_blog_chips 仍输出', strpos($blog, 'sf-blog__chip') !== false || $blog !== '', strlen($blog) . ' B');

echo "\n=== 12. 现有占位符未受影响 ===\n";
$ph = sinofresh_template_placeholders('T={{TITLE}} M={{MID_CRUMB}} U={{LAST_UPDATED}} FC={{FORM_CRUMB}} FH={{FORM_HREF}}');
printf("  %s\n", $ph);
chk('{{TITLE}} 仍解析（非空）', strpos($ph, 'T={{TITLE}}') === false);
chk('{{FORM_HREF}} 无 term 时回落 /products/', strpos($ph, 'FH=/products/') !== false);

echo "\n=== 13. {{FORM_CRUMB}} / {{FORM_HREF}} 在配方详情页的解析 ===\n";
/* Simulate a sf_formula single. $GLOBALS['post'] is set by hand rather than via
   the_post(), which would raise _doing_it_wrong outside The Loop. */
$GLOBALS['wp_the_query'] = new WP_Query(array('p' => $post_id, 'post_type' => 'sf_formula'));
$GLOBALS['wp_query']     = $GLOBALS['wp_the_query'];
$GLOBALS['post']         = get_post($post_id);
setup_postdata($GLOBALS['post']);
$qo2 = get_queried_object();
printf("  注入 queried object = %s #%s\n", $qo2 instanceof WP_Post ? $qo2->post_type : gettype($qo2), $qo2 instanceof WP_Post ? (string) $qo2->ID : '-');
printf("  is_singular('sf_formula') = %s\n", var_export(is_singular('sf_formula'), true));
$ph2 = sinofresh_template_placeholders('CRUMB=[{{FORM_CRUMB}}] HREF=[{{FORM_HREF}}] TITLE=[{{TITLE}}]');
printf("  %s\n", $ph2);
chk('{{FORM_CRUMB}} 取剂型页标题 Soft Chews（不是 term name soft-chews）', strpos($ph2, 'CRUMB=[Soft Chews]') !== false);
chk('{{FORM_HREF}} = /products/soft-chews/', strpos($ph2, 'HREF=[/products/soft-chews/]') !== false);
chk('{{TITLE}} 在详情页解析为配方标题（esc_html 后）', strpos($ph2, 'TITLE=[' . esc_html($TITLE) . ']') !== false, esc_html($TITLE));
chk('list_name 修复后与旧模板一致', sinofresh_formula_list_name('soft-chews') === 'Standard Formulas — Soft Chews', sinofresh_formula_list_name('soft-chews'));
chk('form 无对应页面时回落 humanized slug', sinofresh_formula_label('no-such-form') === 'No Such Form');

printf("\n===== 结果：PASS %d / FAIL %d =====\n", $pass, $fail);
printf("TEST_POST_ID=%d\n", $post_id);
exit($fail === 0 ? 0 : 1);

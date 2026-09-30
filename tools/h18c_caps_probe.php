<?php
/**
 * H18c — how many photos can a record actually carry? READ ONLY.
 *
 * The photo ceiling is SEVEN FRAMES, and the HEAD frame is one of them, so
 * "cap = 7" does not mean "seven of your own". This probe injects a synthetic
 * gallery through the get_post_metadata filter (nothing is written), calls the
 * real sinofresh_formula_gallery_slots(), and prints the frame list for each
 * shape: featured image yes/no x own photos 0..7 x video yes/no.
 *
 * Usage: wp eval-file /tmp/h18c-caps.php --allow-root
 */

if (!defined('ABSPATH')) { exit; }

$wpdb = $GLOBALS['wpdb'];

$forms = get_posts(array('post_type' => 'sf_formula', 'numberposts' => 1, 'fields' => 'ids', 'post_status' => 'publish'));
$probe_post = (int) $forms[0];
$terms = wp_get_post_terms($probe_post, 'sf_formula_form', array('fields' => 'slugs'));
$form = $terms ? $terms[0] : 'soft-chews';

$own_pool = array();
foreach (get_posts(array(
    'post_type' => 'attachment', 'post_mime_type' => 'image',
    'numberposts' => 12, 'post_status' => 'inherit', 'fields' => 'ids',
    'orderby' => 'ID', 'order' => 'ASC',
)) as $aid) { $own_pool[] = (int) $aid; }

$own_urls = array();
foreach ($own_pool as $aid) {
    $src = wp_get_attachment_image_src($aid, 'large');
    if ($src) { $own_urls[$aid] = (string) $src[0]; }
}
$pool = array_keys($own_urls);

$before_rows = (int) $wpdb->get_var("SELECT COUNT(*) FROM {$wpdb->postmeta} WHERE meta_key LIKE 'sf_formula_%'");
$before_md5  = (string) $wpdb->get_var("SELECT MD5(GROUP_CONCAT(CONCAT(meta_id,':',meta_key,':',meta_value) ORDER BY meta_id)) FROM {$wpdb->postmeta} WHERE meta_key LIKE 'sf_formula_%'");

echo "post under test : {$probe_post} (form={$form})\n";
echo "own pool        : " . implode(',', $pool) . "\n";
echo "head source     : featured image if set, else the house dosage still ({$form}.webp)\n\n";
echo str_repeat('=', 120) . "\n";
printf("%-5s %-4s %-6s | %-6s %-7s %-5s | %s\n", 'thumb', 'own', 'video', 'photos', 'frames', 'video?', 'own-of-yours rendered / injected');
echo str_repeat('-', 120) . "\n";

$results = array();
foreach (array(0, 1) as $thumb_on) {
    foreach (range(0, 7) as $n) {
        foreach (array(0, 1) as $vid) {
            $gallery = implode(',', array_slice($pool, 0, $n));
            $vid_url = $vid ? 'https://www.youtube.com/watch?v=H18cProbe000' : '';
            $thumb_id = $thumb_on ? $pool[count($pool) - 1] : '';

            $inject = function ($value, $object_id, $meta_key, $single) use ($probe_post, $gallery, $vid_url, $thumb_id, $thumb_on) {
                if ((int) $object_id !== $probe_post) { return $value; }
                if ($meta_key === 'sf_formula_gallery_ids') { return $gallery; }
                if ($meta_key === 'sf_formula_video_url') { return $vid_url; }
                if ($meta_key === '_thumbnail_id') { return $thumb_on ? (string) $thumb_id : $value; }
                return $value;
            };
            add_filter('get_post_metadata', $inject, 10, 4);

            $rb_g = get_post_meta($probe_post, 'sf_formula_gallery_ids', true);
            $rb_v = get_post_meta($probe_post, 'sf_formula_video_url', true);
            $rb_t = get_post_thumbnail_id($probe_post);

            $slots = sinofresh_formula_gallery_slots($form, $probe_post);
            remove_filter('get_post_metadata', $inject, 10);

            $photos = 0; $mine = 0; $has_video = false; $names = array();
            foreach ($slots as $i => $slot) {
                if (!empty($slot['video_id'])) { $has_video = true; $names[] = 'VIDEO'; continue; }
                $photos++;
                $url = (string) $slot['url'];
                $id  = in_array($url, $own_urls, true) ? (int) array_search($url, $own_urls, true) : 0;
                if ($id === 0) {
                    $names[] = ($i === 0 ? 'HEAD(' : 'fac:') . basename(parse_url($url, PHP_URL_PATH)) . ($i === 0 ? ')' : '');
                } elseif ($thumb_on && $id === (int) $thumb_id) {
                    $names[] = 'MY-FEATURED';
                    $mine++;
                } elseif ($id && in_array($id, array_slice($pool, 0, $n), true)) {
                    $names[] = 'own:' . $id;
                    $mine++;
                } else {
                    $names[] = 'fac:' . basename(parse_url($url, PHP_URL_PATH));
                }
            }

            $rb_ok = ($rb_g === $gallery) && ($rb_v === $vid_url) && ((int) $rb_t === (int) ($thumb_on ? $thumb_id : $rb_t));

            printf(
                "%-5s %-4d %-6d | %-6d %-7d %-5s | %d/%d  %s%s\n",
                $thumb_on ? 'yes' : '-', $n, $vid, $photos, count($slots),
                $has_video ? 'yes' : 'no', $mine, $n + $thumb_on, implode(' | ', $names),
                $rb_ok ? '' : '   <-- INJECTION NOT LIVE, IGNORE ROW'
            );
            $results[] = array('thumb' => $thumb_on, 'own' => $n, 'video' => $vid, 'photos' => $photos, 'frames' => count($slots), 'mine' => $mine);
        }
    }
}

echo "\n" . str_repeat('=', 120) . "\n";
$best_no_vid = 0; $best_vid = 0;
foreach ($results as $r) { if ($r['video']) { $best_vid = max($best_vid, $r['mine']); } else { $best_no_vid = max($best_no_vid, $r['mine']); } }
echo "max of-your-own photos, no video : {$best_no_vid}\n";
echo "max of-your-own photos, with video: {$best_vid}\n";
echo "max photo frames (any shape)      : " . max(array_column($results, 'photos')) . "\n";
echo "max total frames (any shape)      : " . max(array_column($results, 'frames')) . "\n";

$after_rows = (int) $wpdb->get_var("SELECT COUNT(*) FROM {$wpdb->postmeta} WHERE meta_key LIKE 'sf_formula_%'");
$after_md5  = (string) $wpdb->get_var("SELECT MD5(GROUP_CONCAT(CONCAT(meta_id,':',meta_key,':',meta_value) ORDER BY meta_id)) FROM {$wpdb->postmeta} WHERE meta_key LIKE 'sf_formula_%'");
echo "\npostmeta rows {$before_rows} -> {$after_rows}   md5 " . ($before_md5 === $after_md5 ? 'IDENTICAL' : 'CHANGED <<< PROBE WROTE') . "\n";

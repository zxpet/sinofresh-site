<?php
/**
 * TEMPORARY FIXTURE — batch H7a's Video path. Installed, verified, removed.
 *
 * WHY THIS EXISTS. Batch H7a replaced the gallery's heading with a
 * [Photos][Video] switch, and the [Video] label is emitted only when the record
 * actually carries a video: `sinofresh_formula_gallery_slots()` reads
 * `get_post_meta($post_id, 'sf_formula_video_url', true)` and sets `$has_video`
 * from what comes back. All 21 formulas are without one, so the bar ships as a
 * lone [Photos] and **the second branch of that function has never been
 * rendered on this site.** A branch that has never run is not a branch that
 * works.
 *
 * The three ways to exercise it were: write the meta (a row in the database, and
 * the batch's own rule is not to touch data), spoof the admin form (a request
 * that could write), or filter the read. This is the third: it supplies the value
 * to ONE post on the way out of the metadata layer. **Nothing here writes
 * anything**, so there is no row to clean up and nothing to roll back — delete
 * the file and the effect is gone. The probe asserts that: `wp_postmeta` row
 * count, `sf_formula_video_url` row count and `MAX(meta_id)` are read before and
 * after and must match.
 *
 * The poster. `sinofresh_formula_gallery_slots()` builds the facade's still as
 * `https://i.ytimg.com/vi/<id>/hqdefault.jpg`. That host is unreachable from
 * the machine that judges this batch, so the frame would render as a broken
 * image and could only be photographed as a hole — which is a fact about a
 * third party's CDN, not about H7a. So the second half of this file points that
 * one URL at a still the site already serves. **Without the buffer the theme's
 * output is untouched**; the rewrite is scoped to this post and this one URL.
 *
 * The id is deliberately not a real video: nothing is embedded and nothing is
 * uploaded. The facade means YouTube's player is fetched only when a visitor
 * presses Play, and the probe does not press it.
 *
 * Install:  scp this file to wp-content/mu-plugins/  (see b2d_h7a_video_probe.py)
 * Remove:   delete it from wp-content/mu-plugins/
 */
if (!defined('ABSPATH')) {
	exit;
}

define('SF_H7A_FIXTURE_POST', 162);          // /formulas/joint-support-tablets/
define('SF_H7A_FIXTURE_ID', 'SFH7AFIXTURE');
define('SF_H7A_FIXTURE_POSTER',
	'https://dev.zxpet.com/wp-content/uploads/2026/09/fac-line.webp');

/* The read that decides whether the [Video] tab exists at all.
   `get_post_meta()` is a thin wrapper over `get_metadata()`, and the filter core
   actually applies is `get_{$meta_type}_metadata` -- for posts,
   `get_post_metadata`. Returning non-null short-circuits the query, which is
   exactly what a fixture wants: no row is read, so none is needed. */
add_filter('get_post_metadata', function ($value, $object_id, $meta_key, $single) {
	if ($meta_key !== 'sf_formula_video_url') {
		return $value;
	}
	if ((int) $object_id !== SF_H7A_FIXTURE_POST) {
		return $value;
	}
	$url = 'https://www.youtube.com/watch?v=' . SF_H7A_FIXTURE_ID;
	return $single ? $url : array($url);
}, 10, 4);

/* The poster rewrite described above. Scoped twice: to this one post, and to
   this one exact URL. */
add_action('template_redirect', function () {
	if (!is_singular('sf_formula') || (int) get_queried_object_id() !== SF_H7A_FIXTURE_POST) {
		return;
	}
	ob_start(function ($html) {
		return str_replace(
			'https://i.ytimg.com/vi/' . SF_H7A_FIXTURE_ID . '/hqdefault.jpg',
			SF_H7A_FIXTURE_POSTER,
			$html);
	});
}, 1);

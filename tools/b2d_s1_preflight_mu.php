<?php
/**
 * B2D Step1 pre-flight switch — TEMPORARY, server-only.
 *
 * This file is uploaded to
 *     /var/www/dev.zxpet.com/public/wp-content/mu-plugins/zz-sf-preflight.php
 * for the duration of one regression run and deleted immediately afterwards.
 * It is NOT part of the theme and never enters the repository's theme tree.
 *
 * Job: a request carrying the header
 *     X-SF-Preflight: 1
 * is served by the copy theme installed at
 *     wp-content/themes/sinofresh-theme-preflight/
 * instead of the live one.
 *
 * Why a header and not a query parameter: WordPress echoes the query string
 * back in a handful of places, so a ?sf-preflight=1 gate shows up in the
 * comparison as a difference that is not one. A request header is invisible
 * to the page.
 *
 * Why BOTH `stylesheet` and `template` are filtered: the copy is a real
 * theme directory, so every enqueued asset URL WordPress builds from the
 * stylesheet URI resolves to the copy's own style.css and JS. Filtering only
 * `template` (the usual "swap the theme" trick) would leave the assets
 * pointing at the live theme — the run would then verify the live files and
 * pass no matter what the copy contained.
 *
 * Diagnostics go to mu-plugins/zz-sf-preflight.log, i.e. next to this file.
 * NOT to /tmp: open_basedir denies that path to the FPM pool, and the write
 * fails silently — a full run with no log and no error.
 */

define('SF_PREFLIGHT_THEME', 'sinofresh-theme-preflight');

function sf_preflight_requested() {
	if (empty($_SERVER['HTTP_X_SF_PREFLIGHT'])) {
		return false;
	}
	return trim((string) $_SERVER['HTTP_X_SF_PREFLIGHT']) === '1';
}

function sf_preflight_swap($name) {
	if (!sf_preflight_requested()) {
		return $name;
	}
	if (!is_dir(WP_CONTENT_DIR . '/themes/' . SF_PREFLIGHT_THEME)) {
		return $name;
	}
	return SF_PREFLIGHT_THEME;
}

add_filter('stylesheet', 'sf_preflight_swap', 99);
add_filter('template', 'sf_preflight_swap', 99);

/* One line per gated request, so the run can prove the gate actually fired. */
add_action('template_redirect', function () {
	if (!sf_preflight_requested()) {
		return;
	}
	$line = sprintf(
		"[%s] uri=%s theme=%s\n",
		gmdate('c'),
		isset($_SERVER['REQUEST_URI']) ? $_SERVER['REQUEST_URI'] : '-',
		get_stylesheet()
	);
	@file_put_contents(__DIR__ . '/zz-sf-preflight.log', $line, FILE_APPEND);
}, 1);

<?php
/**
 * SINO FRESH — withdraw the ZH locale's URLs for as long as it has no translations.
 *
 * The site publishes a zh_CN locale whose dictionary is registered but empty:
 * every row of wp_trp_dictionary_en_us_zh_cn carries an empty `translated`
 * column, so the /zh/ pages serve the English text while claiming to be
 * Chinese. The cost is not cosmetic. Fifty-four pages carried
 * hreflang="zh-CN" pointing at English prose, and <html lang="zh-CN"> over the
 * same; an alternates cluster whose members fail the language test can be
 * discarded whole, which would take the English side's benefit down with it.
 * So zh_CN is out of publish-languages until it is translated.
 *
 * Withdrawing the locale is database state and does not remove the URLs. Each
 * /zh/{path} is therefore 301'd to the English page it was a translation of,
 * so a URL that may already be indexed keeps its weight instead of becoming a
 * dead end. The mapping is per-page and exact: all 54 /zh/ routes have an
 * English counterpart (measured 2026-09-24), so this is a correspondence, not
 * an approximation, and nothing is funnelled to the home page.
 *
 * The rule reads publish-languages rather than hardcoding the prefix, which is
 * what makes it retire itself: put zh_CN back and the redirects stop with no
 * code change. Re-enabling ZH is three steps and this file is deliberately not
 * one of them — see "reattaching ZH" in docs/zh-unpublish-scan-2026-09-24.md.
 *
 * Deliberately NOT gated on is_404(): depending on how TranslatePress answers
 * an unpublished locale the withdrawn URL may come back as a 200 or a 404, and
 * both have to end in the same 301.
 *
 * LAUNCH NOTE: publish-languages is database state, not code, so shipping this
 * theme does not withdraw the locale by itself — both have to travel.
 */

if (!defined('ABSPATH')) {
	exit;
}

/**
 * First path segment of a /zh/ URL that must be left alone.
 *
 * wp-json and feed both answer 200 under /zh/ (measured 2026-09-24), so they
 * are serving something and a 301 would break it. The rest never carry a
 * locale prefix here and would only be reached by a malformed request.
 */
function sinofresh_zh_unpublish_exempt() {
	return array(
		'wp-json',
		'feed',
		'wp-admin',
		'wp-login.php',
		'wp-content',
		'wp-includes',
		'wp-cron.php',
		'xmlrpc.php',
		'cdn-cgi',
	);
}

/**
 * 301 every /zh/{path} to /{path} while zh_CN is unpublished.
 */
function sinofresh_redirect_unpublished_zh() {
	$method = isset($_SERVER['REQUEST_METHOD']) ? strtoupper($_SERVER['REQUEST_METHOD']) : 'GET';
	if ($method !== 'GET' && $method !== 'HEAD') {
		return;
	}

	$settings = get_option('trp_settings');
	$publish  = (is_array($settings) && isset($settings['publish-languages']) && is_array($settings['publish-languages']))
		? array_values($settings['publish-languages'])
		: array();

	/* One language, and it is English: that is the withdrawn state. Anything
	   else — still two languages, or no TranslatePress settings at all — means
	   this rule has nothing to say. */
	if (count($publish) !== 1 || $publish[0] !== 'en_US') {
		return;
	}

	$request = isset($_SERVER['REQUEST_URI']) ? $_SERVER['REQUEST_URI'] : '';
	if ($request === '') {
		return;
	}
	$cut  = strpos($request, '?');
	$path = ($cut === false) ? $request : substr($request, 0, $cut);
	$qs   = ($cut === false) ? '' : substr($request, $cut + 1);

	/* /zh exactly, or /zh/something. /zhxyz/ is a different path. */
	if ($path !== '/zh' && strpos($path, '/zh/') !== 0) {
		return;
	}

	$rest = substr($path, 3);                       /* '/zh/about/' -> '/about/'; '/zh' -> ''; '/zh/' -> '/' */
	$segs = explode('/', ltrim($rest, '/'));
	if ($segs[0] !== '' && in_array(strtolower($segs[0]), sinofresh_zh_unpublish_exempt(), true)) {
		return;
	}

	/* The TranslatePress editor reaches a locale through ?trp-edit-translation.
	   Exempt that request alone, not the whole prefix: without it the ZH editor
	   could never be opened again, and opening it is how the translations that
	   would bring the locale back get written. */
	parse_str($qs, $query);
	if (array_key_exists('trp-edit-translation', $query)) {
		return;
	}

	/* ltrim collapses a malformed '/zh//x' into '/x' rather than handing
	   home_url() a protocol-relative '//x'. */
	$target = '/' . ltrim($rest, '/');
	if ($qs !== '') {
		$target .= '?' . $qs;
	}

	wp_safe_redirect(home_url($target), 301, 'SINO FRESH');
	exit;
}
add_action('template_redirect', 'sinofresh_redirect_unpublished_zh', 1);

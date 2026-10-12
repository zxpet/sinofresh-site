<?php
/**
 * Plugin Name: SINO FRESH Author Guard
 * Description: Stops the WordPress login name leaking to the public web. Every author archive and author-enumeration entry point (?author, ?author_name, /author/<nicename>/) is taken off the air, and the author display name used by feeds, oEmbed and JSON-LD is replaced with the brand name. Admin screens and the block editor are untouched.
 * Version:     1.0.0
 * Author:      SINO FRESH
 *
 * Why this exists (2026-10-06, batch H22)
 * ---------------------------------------
 * The site has a single account and the login name was changed from the
 * guessable default. That change is only worth something if the new name is
 * not discoverable, and it was discoverable in six places:
 *
 *   1. /?author=1            -> 301 -> /author/<nicename>/   (enumeration)
 *   2. /author/<nicename>/    -> 200, <title> carries the name
 *   3. /author/<nicename>/feed/
 *   4. /feed/                 -> <dc:creator><![CDATA[<name>]]>
 *   5. /wp-json/oembed/1.0/embed?url=... -> "author_name":"<name>"
 *   6. post JSON-LD           -> "author":{"@type":"Person","name":"<name>"}
 *
 * This file is a mu-plugin on purpose: the theme's byte baseline is pinned by
 * several acceptance gates, and editing functions.php would force a theme
 * version bump plus a cache-URL change for a security fix that has nothing to
 * do with presentation. Deploying here leaves every theme file untouched.
 *
 * Rollback = delete this file (or rename it to .off); nothing else changes.
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/**
 * The single public-facing byline. Change this one string to rebrand.
 *
 * @return string
 */
function sf_author_guard_public_name() {
	return 'SINO FRESH';
}

/**
 * Should the public filters apply to this request?
 *
 * False inside wp-admin so the profile screen, the users list and the block
 * editor keep showing the real display name — a filter that rewrote those
 * would make the site look like it had lost its own account.
 *
 * @return bool
 */
function sf_author_guard_should_filter() {
	if ( function_exists( 'is_admin' ) && is_admin() ) {
		return false;
	}
	return true;
}

/**
 * Replace a public author name field with the brand name.
 *
 * @param mixed $value Original value.
 * @return mixed
 */
function sf_author_guard_filter_name( $value ) {
	if ( ! sf_author_guard_should_filter() ) {
		return $value;
	}
	return sf_author_guard_public_name();
}

/**
 * get_the_author_meta() applies a dynamic filter per field:
 * get_the_author_{$field}. Covers display_name (JSON-LD, oEmbed) and the
 * login/nickname family in case a future template prints one of them.
 */
foreach ( array( 'display_name', 'nickname', 'first_name', 'last_name', 'user_login', 'user_nicename' ) as $sf_author_guard_field ) {
	add_filter( 'get_the_author_' . $sf_author_guard_field, 'sf_author_guard_filter_name', 99 );
}
unset( $sf_author_guard_field );

/** Feed <dc:creator> goes through get_the_author(), which applies this. */
add_filter( 'the_author', 'sf_author_guard_filter_name', 99 );

/**
 * Any generated link to an author archive points at the front page instead.
 *
 * Defensive: the theme does not currently emit author links, but plugins and
 * future templates do, and a dead link is better than a name.
 *
 * @param string $link Original author archive URL.
 * @return string
 */
function sf_author_guard_author_link( $link ) {
	if ( ! sf_author_guard_should_filter() ) {
		return $link;
	}
	return home_url( '/' );
}
add_filter( 'author_link', 'sf_author_guard_author_link', 99 );

/**
 * oEmbed carries its own author_name / author_url pair; force both.
 *
 * @param array $data oEmbed response data.
 * @return array
 */
function sf_author_guard_oembed_data( $data ) {
	if ( is_array( $data ) ) {
		$data['author_name'] = sf_author_guard_public_name();
		$data['author_url']  = home_url( '/' );
	}
	return $data;
}
add_filter( 'oembed_response_data', 'sf_author_guard_oembed_data', 99 );

/**
 * Take the author archive and the enumeration parameters off the air.
 *
 * Priority 1 so this runs before redirect_canonical (priority 10) — otherwise
 * core answers /?author=1 with a 301 to /author/<nicename>/ and the name is in
 * the Location header before we ever see the request.
 *
 * Feeds get a 404 rather than a redirect: a 301 to an HTML page confuses feed
 * readers and validators, and there is no author feed worth keeping.
 *
 * @return void
 */
function sf_author_guard_block_archives() {
	$is_enumeration = isset( $_GET['author'] ) || isset( $_GET['author_name'] ); // phpcs:ignore WordPress.Security.NonceVerification.Recommended

	if ( ! $is_enumeration && ! is_author() ) {
		return;
	}

	// Never interfere with admin screens, AJAX, cron or REST.
	if ( is_admin() || wp_doing_ajax() || wp_doing_cron() ) {
		return;
	}
	if ( defined( 'REST_REQUEST' ) && REST_REQUEST ) {
		return;
	}
	// A logged-in editor previewing their own archive keeps it.
	if ( is_user_logged_in() && current_user_can( 'edit_posts' ) ) {
		return;
	}

	if ( is_feed() ) {
		status_header( 404 );
		nocache_headers();
		exit;
	}

	wp_safe_redirect( home_url( '/' ), 301 );
	exit;
}
add_action( 'template_redirect', 'sf_author_guard_block_archives', 1 );

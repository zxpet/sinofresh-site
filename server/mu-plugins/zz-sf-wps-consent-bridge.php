<?php
/**
 * Plugin Name: SF - WP Statistics Consent Bridge
 * Description: Surface WP Statistics' "wp_consent_api" consent integration even though
 *              the theme banner is not one of its hard-coded "compatible" banner plugins.
 *
 * WHY THIS EXISTS (WP Statistics 14.16.14):
 *   WpConsentApi::register() (src/Service/Integrations/Plugins/WpConsentApi.php) resets
 *   `consent_integration` to '' on every request unless one of its HARD-CODED banner
 *   plugins is active (Complianz / Cookiebot / CookieYes / ... 12 plugins).
 *   wp-consent-api itself is NOT in that list, and neither is our theme banner --
 *   which implements the WP Consent API correctly (ui-components.js calls
 *   wp_set_consent('statistics'/'marketing')).
 *
 * HOW: override the option AT READ TIME via the `option_wp_statistics` filter, only when
 *   the stored value is ''. Zero DB writes, no plugin files touched (verify-checksums
 *   stays clean), trivially removable once WP Statistics drops the hard-coded list.
 *
 * NOTE: without this, tracker.js initializes unconditionally (consentIntegration.name
 *   === null) and records hits BEFORE any consent decision -- a compliance gap.
 *
 * ALSO NEEDED: wp-consent-api's wp_get_consent_type() is filter-only and defaults to ''.
 *   With '' the API treats consent as GRANTED everywhere (wp_has_consent() returns true
 *   with no cookie, client and server), ignoring our banner's allow/deny cookies.
 *   Declaring 'optin' makes consent cookie-verified: no cookie => deny.
 */

if (!defined('ABSPATH')) exit;

add_filter('option_wp_statistics', function ($value) {
	if (is_array($value) && empty($value['consent_integration'])) {
		$value['consent_integration'] = 'wp_consent_api';
	}
	return $value;
});

add_filter('wp_get_consent_type', function () {
	return 'optin';
});

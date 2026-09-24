#!/usr/bin/env node
/**
 * b3g_consent_unit.js — runs the REAL theme file against a stubbed DOM.
 *
 * Nothing here re-implements the consent logic. The validator, the record
 * shape and the Consent API bridge under test are the bytes of
 * sinofresh-theme/assets/js/ui-components.js that a browser loads, executed
 * in a sandbox; the assertions read what that file actually did. A passing
 * run therefore means the shipped file behaves, not a paraphrase of it.
 *
 * The last block is a negative control: the same run with one guard removed
 * from the source in memory. If the flagged assertions stay green there, they
 * are not measuring the guard at all.
 *
 *   node tools/b3g_consent_unit.js [--source <path>]
 */
'use strict';
const fs = require('fs');
const vm = require('vm');
const path = require('path');

const argv = process.argv.slice(2);
const si = argv.indexOf('--source');
const SRC = si >= 0
	? argv[si + 1]
	: path.join(__dirname, '..', 'sinofresh-theme', 'assets', 'js', 'ui-components.js');
const code = fs.readFileSync(SRC, 'utf8');
const DAYS = 182;
const MS_DAY = 864e5;

let PASSED = 0;
const FAILED = [];
function check(name, ok, detail) {
	if (ok) { PASSED++; console.log('  ok   ' + name); }
	else { FAILED.push(name); console.log('  FAIL ' + name + (detail ? '  -- ' + detail : '')); }
}

function mkClassList() {
	const s = new Set();
	return {
		add: (c) => s.add(c), remove: (c) => s.delete(c), contains: (c) => s.has(c),
		toggle: (c, f) => (f ? s.add(c) : s.delete(c)), _set: s,
	};
}

function mkEl(map) {
	const listeners = {};
	return {
		hidden: true, _map: map || {}, classList: mkClassList(),
		querySelector(sel) { return (this._map && this._map[sel]) || null; },
		addEventListener(t, fn) { (listeners[t] = listeners[t] || []).push(fn); },
		_fire(t) { (listeners[t] || []).forEach((fn) => fn({ target: this, preventDefault() {} })); },
		getAttribute() { return 'false'; }, setAttribute() {},
		closest() { return null; }, nextElementSibling: null,
	};
}

/** Boot the file in a fresh sandbox and hand back what it did. */
function boot(env, source) {
	env = env || {};
	const calls = { setConsent: [], gtag: [], events: [] };

	const btn = { accept: mkEl(), reject: mkEl() };
	const banner = mkEl({
		'.sf-cookie-banner__btn--accept': btn.accept,
		'.sf-cookie-banner__btn--reject': btn.reject,
	});
	const reopen = env.reopen === false ? null : mkEl();

	const store = Object.create(null);
	Object.keys(env.store || {}).forEach((k) => { store[k] = env.store[k]; });

	const bus = {};
	const sandbox = {
		document: {
			querySelector: (sel) => {
				if (sel === '.sf-cookie-banner') return env.banner === false ? null : banner;
				if (sel === '.sf-cookie-preferences') return reopen;
				return null;
			},
			body: { classList: mkClassList() },
			addEventListener: () => {},
		},
		localStorage: {
			getItem: (k) => (k in store ? store[k] : null),
			setItem: (k, v) => { store[k] = String(v); },
			removeItem: (k) => { delete store[k]; },
		},
		CustomEvent: function CustomEvent(type, init) {
			this.type = type; this.detail = (init || {}).detail;
		},
		dispatchEvent: (e) => {
			calls.events.push(e);
			(bus[e.type] || []).forEach((fn) => fn(e));
		},
		addEventListener: (t, fn) => { (bus[t] = bus[t] || []).push(fn); },
		matchMedia: () => ({ matches: false }),
		scrollY: 0,
		requestAnimationFrame: (f) => { f(); return 0; },
		scrollTo: () => {},
	};
	sandbox.window = sandbox;
	if (env.gtag) {
		sandbox.gtag = function () { calls.gtag.push(Array.prototype.slice.call(arguments)); };
	}
	if (env.consentApi) {
		sandbox.wp_set_consent = function () {
			calls.setConsent.push(Array.prototype.slice.call(arguments));
		};
		if (env.apiSaysAllow !== undefined) {
			sandbox.wp_has_consent = () => env.apiSaysAllow;
		}
	}

	vm.createContext(sandbox);
	vm.runInContext(source || code, sandbox, { filename: SRC });

	const record = () => {
		const raw = store.sf_cookie_consent;
		if (raw == null) return null;
		try { return JSON.parse(raw); } catch (e) { return '(unparseable)'; }
	};

	return {
		banner, body: sandbox.document.body, calls, record, reopen,
		click: (which) => btn[which]._fire('click'),
		clickReopen: () => reopen._fire('click'),
		decisionEvent: () => calls.events.filter((e) => e.type === 'sf:consent').pop(),
		gtagState: (i) => {
			const c = calls.gtag[i || 0];
			return c && c[2] ? c[2].analytics_storage : null;
		},
	};
}

const LEGACY = JSON.stringify({ analytics: true, marketing: true, timestamp: Date.now() - 5e8 });
const V2_ALLOW = (exp) => JSON.stringify({
	analytics: true, marketing: true, version: 2,
	timestamp: Date.now() - 1e6, expires: exp,
});

console.log('=== consent decision: version + expiry + Consent API bridge ===');
console.log('    source: ' + SRC);

/* C1 — first visit */
{
	const r = boot();
	check('first visit shows the banner',
		r.banner.hidden === false && r.body.classList.contains('has-cookie-banner'));
	check('first visit writes no record', r.record() === null);
	check('first visit asks the Consent API for nothing', r.calls.setConsent.length === 0);
}

/* C2 — accept */
{
	const r = boot({ gtag: true, consentApi: true });
	r.click('accept');
	const rec = r.record();
	check('accept writes version 2', rec && rec.version === 2, JSON.stringify(rec));
	check('accept writes an expiry ~182 days out',
		!!rec && rec.expires - rec.timestamp === DAYS * MS_DAY);
	check('accept records analytics = true', !!rec && rec.analytics === true);
	check('accept hides the banner and drops the body class',
		r.banner.hidden === true && !r.body.classList.contains('has-cookie-banner'));
	check('accept fires sf:consent with analytics true',
		!!(r.decisionEvent() && r.decisionEvent().detail.analytics));
	check('accept bridges into the Consent API as allow',
		JSON.stringify(r.calls.setConsent) ===
			JSON.stringify([['statistics', 'allow'], ['marketing', 'allow']]),
		JSON.stringify(r.calls.setConsent));
	check('accept updates GA4 consent to granted', r.gtagState() === 'granted');
}

/* C3 — reject */
{
	const r = boot({ gtag: true, consentApi: true });
	r.click('reject');
	check('reject bridges into the Consent API as deny',
		JSON.stringify(r.calls.setConsent) ===
			JSON.stringify([['statistics', 'deny'], ['marketing', 'deny']]),
		JSON.stringify(r.calls.setConsent));
	check('reject updates GA4 consent to denied', r.gtagState() === 'denied');
}

/* C4 — the record expired: it must stop counting for BOTH consumers */
{
	const r = boot({
		store: { sf_cookie_consent: V2_ALLOW(Date.now() - 1000) },
		gtag: true, consentApi: true, apiSaysAllow: true,
	});
	check('an expired record re-asks (banner shown again)', r.banner.hidden === false);
	check('an expired record does not grant GA4', r.calls.gtag.length === 0,
		'gtag calls: ' + r.calls.gtag.length);
	check('an expired record does not re-assert the Consent API', r.calls.setConsent.length === 0);
}

/* C5 — a record from the previous banner shape has no version and no expiry */
{
	const r = boot({ store: { sf_cookie_consent: LEGACY }, gtag: true, consentApi: true, apiSaysAllow: true });
	check('an unversioned record no longer answers the banner',
		r.banner.hidden === false);
	check('an unversioned record does not grant GA4', r.calls.gtag.length === 0,
		'gtag calls: ' + r.calls.gtag.length);
}

/* C6 — a live record, and everything already agrees with it */
{
	const r = boot({
		store: { sf_cookie_consent: V2_ALLOW(Date.now() + 5e9) },
		gtag: true, consentApi: true, apiSaysAllow: true,
	});
	check('a live record keeps the banner closed',
		r.banner.hidden === true && !r.body.classList.contains('has-cookie-banner'));
	check('a live record restores GA4 consent on load', r.gtagState() === 'granted');
	check('a live record rewrites no consent cookie when the API already agrees',
		r.calls.setConsent.length === 0, JSON.stringify(r.calls.setConsent));
}

/* C7 — a live record, but the API's own cookie disagrees (e.g. it expired) */
{
	const r = boot({
		store: { sf_cookie_consent: V2_ALLOW(Date.now() + 5e9) },
		gtag: true, consentApi: true, apiSaysAllow: false,
	});
	check('a disagreeing API cookie is corrected on load',
		JSON.stringify(r.calls.setConsent) ===
			JSON.stringify([['statistics', 'allow'], ['marketing', 'allow']]),
		JSON.stringify(r.calls.setConsent));
}

/* C8 — a live denial */
{
	const r = boot({
		store: { sf_cookie_consent: V2_ALLOW(Date.now() + 5e9) },
		gtag: true, consentApi: true, apiSaysAllow: false,
	});
	check('a live record that allowed is re-asserted as allow', r.calls.setConsent.length === 2);
	{
		const d = boot({
			store: {
				sf_cookie_consent: JSON.stringify({
					analytics: false, marketing: false, version: 2,
					timestamp: Date.now() - 1e6, expires: Date.now() + 5e9,
				}),
			},
			gtag: true, consentApi: true, apiSaysAllow: false,
		});
		check('a live denial keeps the banner closed', d.banner.hidden === true);
		check('a live denial drives GA4 to denied', d.gtagState() === 'denied');
	}
}

/* C9 — a page with no banner at all must still boot cleanly */
{
	let threw = null;
	try { boot({ gtag: true, consentApi: true, banner: false }); } catch (e) { threw = e.message; }
	check('a page without the banner boots without throwing', threw === null, String(threw));
}

/* C10 — the Consent API plugin is not installed */
{
	let threw = null;
	let r = null;
	try { r = boot({ gtag: true, consentApi: false }); r.click('accept'); } catch (e) { threw = e.message; }
	check('accept works when the Consent API is absent', threw === null, String(threw));
	check('accept still writes the record without the Consent API',
		!!(r && r.record() && r.record().version === 2));
}

/* C11 — the footer withdraw entry */
{
	const r = boot({ gtag: true, consentApi: true });
	r.click('accept');
	check('after accepting, the banner is hidden', r.banner.hidden === true);
	r.clickReopen();
	check('the withdraw link re-opens the banner', r.banner.hidden === false,
		'banner.hidden = ' + r.banner.hidden);
	check('and re-adds the body class', r.body.classList.contains('has-cookie-banner'));
	check('the withdraw link cleared the record', r.record() === null, JSON.stringify(r.record()));
	check('the accept button still answers after reopening', (() => {
		r.click('accept'); return r.record() && r.record().version === 2 && r.banner.hidden === true;
	})());
}

/* C12 — the withdraw entry on a page whose banner never showed (no record yet) */
{
	const r = boot({ gtag: true, consentApi: true });
	r.clickReopen();
	check('the withdraw link is harmless before any decision',
		r.banner.hidden === false && r.record() === null);
}

/* C13 — a page without the footer link still boots cleanly */
{
	let threw = null;
	try { boot({ gtag: true, consentApi: true, reopen: false }); } catch (e) { threw = e.message; }
	check('a page without the withdraw link boots without throwing', threw === null, String(threw));
}

/* ---- negative control: both guards deleted from the source, in memory ----
   The two guard lines are what C4 and C5 measure. Delete them and the same
   two situations must flip. If they do not flip, those assertions were never
   measuring the guards. */
console.log('\n=== negative control: both validator guards deleted from the source ===');
{
	const guards = [
		'\t\tif (rec.version !== VERSION) return null;',
		'\t\tif (typeof rec.expires !== "number" || rec.expires <= Date.now()) return null;',
	];
	const missing = guards.filter((g) => code.indexOf(g) < 0);
	check('negative control found both guard lines in the source', missing.length === 0,
		'not found: ' + JSON.stringify(missing));
	if (missing.length === 0) {
		const mutant = guards.reduce((s, g) => s.replace(g, ''), code);
		const legacy = boot(
			{ store: { sf_cookie_consent: LEGACY }, gtag: true, consentApi: true, apiSaysAllow: true },
			mutant);
		const expired = boot(
			{ store: { sf_cookie_consent: V2_ALLOW(Date.now() - 1000) }, gtag: true, consentApi: true, apiSaysAllow: true },
			mutant);
		check('without the guards an unversioned record WOULD be honoured \u2014 so C5 measures the guard',
			legacy.banner.hidden === true, 'banner.hidden = ' + legacy.banner.hidden);
		check('without the guards an expired record WOULD still grant GA4 \u2014 so C4 measures the guard',
			expired.calls.gtag.length > 0, 'gtag calls = ' + expired.calls.gtag.length);
	}
}

console.log('\n' + (FAILED.length ? 'FAILED: ' + FAILED.length : 'all assertions passed') +
	'  (' + PASSED + ' passed)');
process.exit(FAILED.length ? 1 : 0);

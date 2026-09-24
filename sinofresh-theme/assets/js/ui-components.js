/* SINO FRESH floating UI: cookie consent + contact stack + back to top. */
(() => {
	"use strict";
	const KEY = "sf_cookie_consent";
	/* The decision record is versioned and time-boxed.
	   Version: a record made against an older banner does not answer the current one.
	   Expiry: consent that never lapses is not consent.
	   Both are read through ONE validator, so the banner, the GA4 bridge and the
	   Consent API cannot disagree about whether a decision is still in force. */
	const VERSION = 2;
	const DAYS = 182;
	const MS_DAY = 864e5;
	const banner = document.querySelector(".sf-cookie-banner");

	/* The record, but only if it answers the current banner and has not expired. */
	const readDecision = () => {
		let rec = null;
		try {
			rec = JSON.parse(localStorage.getItem(KEY) || "null");
		} catch (e) {
			return null;
		}
		if (!rec || typeof rec !== "object") return null;
		if (rec.version !== VERSION) return null;
		if (typeof rec.expires !== "number" || rec.expires <= Date.now()) return null;
		return rec;
	};

	/* Mirror the decision into the WP Consent API. That plugin is installed and
	   loaded on every page but nothing ever called it. wp_set_consent() is its
	   public entry point: it writes an expiring consent cookie that server-side
	   code reads with wp_has_consent(), and fires wp_listen_for_consent_change. */
	const bridgeConsent = (on) => {
		if (typeof window.wp_set_consent !== "function") return;
		const v = on ? "allow" : "deny";
		window.wp_set_consent("statistics", v);
		window.wp_set_consent("marketing", v);
	};

	if (banner) {
		const saved = readDecision();

		const decide = (on) => {
			const now = Date.now();
			try {
				localStorage.setItem(KEY, JSON.stringify({
					analytics: on, marketing: on,
					version: VERSION, timestamp: now, expires: now + DAYS * MS_DAY
				}));
			} catch (e) {}
			bridgeConsent(on);
			banner.hidden = true;
			document.body.classList.remove("has-cookie-banner");
			dispatchEvent(new CustomEvent("sf:consent", { detail: { analytics: on, marketing: on } }));
		};

		if (!saved) {
			banner.hidden = false;
			document.body.classList.add("has-cookie-banner");
			const on = (sel, fn) => banner.querySelector(sel).addEventListener("click", fn);
			on(".sf-cookie-banner__btn--accept", () => decide(true));
			on(".sf-cookie-banner__btn--reject", () => decide(false));
			on(".sf-cookie-banner__manage", () => decide(false));
		}
	}

	/* GA4 consent mode bridge: mirrors the banner decision into gtag consent
	   state. Site Kit (production) loads gtag with consent default denied; the
	   bridge grants analytics/marketing only after an explicit accept. Runs on
	   load for returning visitors and on every sf:consent decision. */
	const applyGtagConsent = (granted) => {
		if (typeof window.gtag !== "function") return;
		const state = granted ? "granted" : "denied";
		window.gtag("consent", "update", {
			analytics_storage: state,
			ad_storage: state,
			ad_user_data: state,
			ad_personalization: state
		});
	};
	try {
		const prior = readDecision();
		if (prior) {
			applyGtagConsent(prior.analytics === true);
			/* Re-assert into the Consent API only when its own cookie disagrees,
			   so a returning visitor does not get a consent cookie rewritten on
			   every single page view. */
			if (typeof window.wp_has_consent === "function") {
				const granted = prior.analytics === true;
				if (window.wp_has_consent("statistics") !== granted ||
					window.wp_has_consent("marketing") !== granted) {
					bridgeConsent(granted);
				}
			}
		}
	} catch (e) {}
	addEventListener("sf:consent", (e) => {
		applyGtagConsent(!!(e.detail && e.detail.analytics));
	});

	const top = document.querySelector(".sf-float-btn--top");
	if (top) {
		const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
		let queued = false;
		const sync = () => {
			queued = false;
			top.classList.toggle("is-visible", scrollY > 400);
		};
		addEventListener("scroll", () => {
			if (!queued) { queued = true; requestAnimationFrame(sync); }
		}, { passive: true });
		sync();
		top.addEventListener("click", () =>
			scrollTo({ top: 0, behavior: reduce ? "auto" : "smooth" }));
	}
})();

/* Optional-field toggle for Gravity Forms: show/hide the .sf-optional
   fields that follow the toggle button. */
document.addEventListener('click', function (e) {
	var t = e.target.closest('.sf-opt-toggle');
	if (!t) { return; }
	var expanded = t.getAttribute('aria-expanded') === 'true';
	var n = t.closest('.gfield');
	while ((n = n.nextElementSibling)) {
		if (n.classList.contains('sf-optional')) {
			n.classList.toggle('sf-opt-open', !expanded);
		} else if (n.classList.contains('gfield')) {
			break;
		}
	}
	t.setAttribute('aria-expanded', String(!expanded));
});

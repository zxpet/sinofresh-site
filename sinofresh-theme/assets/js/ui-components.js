/* SINO FRESH floating UI: cookie consent + contact stack + back to top. */
(() => {
	"use strict";
	const KEY = "sf_cookie_consent";
	const banner = document.querySelector(".sf-cookie-banner");

	if (banner) {
		let saved = null;
		try { saved = JSON.parse(localStorage.getItem(KEY)); } catch (e) {}

		const decide = (on) => {
			try {
				localStorage.setItem(KEY, JSON.stringify({
					analytics: on, marketing: on, timestamp: Date.now()
				}));
			} catch (e) {}
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
		const prior = JSON.parse(localStorage.getItem(KEY) || "null");
		if (prior) applyGtagConsent(prior.analytics === true);
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

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

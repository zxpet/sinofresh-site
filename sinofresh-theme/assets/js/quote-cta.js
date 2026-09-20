/* Quote CTA smart scroll (global) =========================================
 * Header / footer "Get a Quote" buttons (.sf-quote-cta, href="/contact/").
 * If the current page hosts an inquiry form — #inquiry-form on the home and
 * dosage pages, #quote on /contact/, #booking-form on /factory-tour/ — the
 * click scrolls to it (smooth unless the visitor prefers reduced motion);
 * otherwise the native /contact/ navigation stands and /contact/#quote
 * lands on the form heading via scroll-margin-top.
 * Delegated on document so it also works for buttons inside the footer
 * <details> accordion. No dependencies. */
(function () {
	"use strict";

	var SELECTOR = "a.sf-quote-cta";
	var TARGETS = "#inquiry-form, #quote, #booking-form";

	/* Lazy images below the fold can grow the document while a long smooth
	 * scroll is in flight, and the native animation ends at the position it
	 * computed up front — a few hundred px short. Once the scroll settles,
	 * re-measure and give it another (short) smooth pass; two tries suffice. */
	function settleAndCorrect(el, tries) {
		var last = scrollY, still = 0, n = 0;
		var iv = setInterval(function () {
			n++;
			if (scrollY === last) still++; else { still = 0; last = scrollY; }
			if (still < 3 && n < 40) return;
			clearInterval(iv);
			var margin = parseFloat(getComputedStyle(el).scrollMarginTop) || 0;
			var off = el.getBoundingClientRect().top - margin;
			if (Math.abs(off) > 2 && tries > 0) {
				el.scrollIntoView({ behavior: "smooth", block: "start" });
				settleAndCorrect(el, tries - 1);
			}
		}, 120);
	}

	document.addEventListener("click", function (e) {
		var t = e.target;
		if (!t || !t.closest) return;
		var link = t.closest(SELECTOR);
		if (!link) return;

		var target = document.querySelector(TARGETS);
		if (!target) return; /* no form on this page -> native /contact/#quote */

		e.preventDefault();
		var reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
		target.scrollIntoView({
			behavior: reduce ? "auto" : "smooth",
			block: "start"
		});
		if (!reduce) settleAndCorrect(target, 2);
		/* reflect the destination in the URL without triggering another jump */
		if (target.id && history.replaceState) {
			history.replaceState(null, "", "#" + target.id);
		}
	});

	/* Deep links (e.g. /contact/#quote from a formless page): the browser's
	 * own hash jump fires before fonts/lazy images expand the document, so
	 * the target can end up well below the fold. Re-anchor once on load and
	 * once more shortly after, instant (auto) so reduced motion is honoured. */
	var reanchor = function () {
		if (!/^(#inquiry-form|#quote|#booking-form)$/.test(location.hash)) return;
		var el = document.querySelector(location.hash);
		if (el) el.scrollIntoView({ behavior: "auto", block: "start" });
	};
	window.addEventListener("load", function () {
		reanchor();
		setTimeout(reanchor, 400);
	});
})();

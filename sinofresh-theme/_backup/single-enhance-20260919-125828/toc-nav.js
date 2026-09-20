/*! SINO FRESH — on-this-page dot-rail TOC (toc-nav.js) =====================
 * Loaded only on the whitelisted long pages (functions.php): front page,
 * /quality/, the eight dosage pages, /about/, /services/, /factory-tour/.
 * Scans main-content H2s, injects sf-sec-N ids, renders a fixed dot rail on
 * the right, highlights the section in view via IntersectionObserver and
 * smooth-scrolls on click (same lazy-height correction as quote-cta.js).
 * Hidden below 1100px (CSS); no-ops when fewer than 3 eligible H2s exist.
 * Skipped on the front page (SKIP list): Formulated Clean /
 * From Inquiry to After-Sales / Trusted by 30+ / Ready to Launch — keeps the
 * rail at 9 entries. No dependencies. */
(function () {
	"use strict";

	/* Front-page H2s excluded from the rail (exact/prefix text match). */
	var SKIP = [
		/^formulated clean$/i,
		/^from inquiry to after-sales$/i,
		/^trusted by 30\+/i,
		/^ready to launch your product\?$/i
	];

	/* Lazy images below the fold can grow the document while a long smooth
	 * scroll is in flight, and the native animation ends at the position it
	 * computed up front — a few hundred px short. Once the scroll settles,
	 * re-measure and give it another (short) smooth pass; two tries suffice.
	 * (Same recipe as quote-cta.js — kept local, no shared module.) */
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

	/* Reduced-motion instant jump: crossing the sticky-header sentinel
	 * reflows the page (header leaves the flow), which can shift the target
	 * after scrollIntoView — re-measure and correct with instant scrollTo
	 * (no animation, so reduced motion stays honoured). */
	function correctInstant(el, tries) {
		setTimeout(function () {
			var margin = parseFloat(getComputedStyle(el).scrollMarginTop) || 0;
			var off = el.getBoundingClientRect().top - margin;
			if (Math.abs(off) > 2 && tries > 0) {
				scrollTo(0, scrollY + off);
				correctInstant(el, tries - 1);
			}
		}, 80);
	}

	function init() {
		var main = document.querySelector("main") || document.body;
		var h2s = [];
		var nodes = main.querySelectorAll("h2");
		for (var k = 0; k < nodes.length; k++) {
			var h = nodes[k];
			/* Lightboxes/modals/aria-hidden subtrees never become TOC targets. */
			if (h.closest(".sf-lb, .sf-certmodal, dialog, template, [hidden], [aria-hidden='true']")) continue;
			var cs = getComputedStyle(h);
			if (cs.display === "none" || cs.visibility === "hidden") continue;
			var text = (h.textContent || "").replace(/\s+/g, " ").trim();
			if (!text) continue;
			var skip = false;
			for (var s = 0; s < SKIP.length; s++) {
				if (SKIP[s].test(text)) { skip = true; break; }
			}
			if (skip) continue;
			h2s.push({ el: h, text: text });
		}
		if (h2s.length < 3) return;

		/* Inject anchor ids + scroll offset hook (id kept if one already exists). */
		h2s.forEach(function (item, i) {
			if (!item.el.id) item.el.id = "sf-sec-" + i;
			item.el.classList.add("sf-toc-target");
		});

		/* Build the dot rail. */
		var nav = document.createElement("nav");
		nav.className = "sf-toc";
		nav.setAttribute("aria-label", "On this page");
		var ul = document.createElement("ul");
		var links = [];
		h2s.forEach(function (item) {
			var li = document.createElement("li");
			var a = document.createElement("a");
			a.href = "#" + item.el.id;
			var dot = document.createElement("span");
			dot.className = "sf-toc__dot";
			dot.setAttribute("aria-hidden", "true");
			var label = document.createElement("span");
			label.className = "sf-toc__label";
			label.textContent = item.text;
			a.appendChild(dot);
			a.appendChild(label);
			a.addEventListener("click", function (e) {
				e.preventDefault();
				var reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
				item.el.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
				if (reduce) correctInstant(item.el, 3);
				else settleAndCorrect(item.el, 2);
				setCurrent(h2s.indexOf(item));
				if (history.replaceState) history.replaceState(null, "", "#" + item.el.id);
			});
			li.appendChild(a);
			ul.appendChild(li);
			links.push(a);
		});
		nav.appendChild(ul);
		document.body.appendChild(nav);

		/* Highlight is computed on scroll (rAF-throttled), not via
		 * IntersectionObserver: home sections run 1,000px+ tall, and a fast
		 * or keyboard scroll moves a heading straight from below the band to
		 * above it — the intersection state never changes, so IO callbacks
		 * don't fire (measured). Reading rects at scroll time is
		 * deterministic: the furthest-down heading that crossed the 96px
		 * header line is current. */
		var current = -1;
		function setCurrent(i) {
			if (i === current) return;
			current = i;
			links.forEach(function (a, j) {
				a.parentNode.classList.toggle("is-current", j === current);
				if (j === current) a.setAttribute("aria-current", "true");
				else a.removeAttribute("aria-current");
			});
		}

		/* Scroll choreography: fade below 200px, highlight follow, and force
		 * the last item active at page bottom (short final sections would
		 * otherwise never become current). */
		var queued = false;
		function onScroll() {
			if (queued) return;
			queued = true;
			requestAnimationFrame(function () {
				queued = false;
				nav.classList.toggle("sf-toc--hidden", scrollY < 200);
				var next = -1;
				for (var i = 0; i < h2s.length; i++) {
					if (h2s[i].el.getBoundingClientRect().top <= 97) next = i;
				}
				if (scrollY + innerHeight >= document.documentElement.scrollHeight - 2) {
					next = h2s.length - 1;
				}
				setCurrent(next);
			});
		}
		addEventListener("scroll", onScroll, { passive: true });
		onScroll();
	}

	if (document.readyState === "loading") {
		document.addEventListener("DOMContentLoaded", init);
	} else {
		init();
	}
})();

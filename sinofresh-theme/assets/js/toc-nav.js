/*! SINO FRESH — toc-nav.js 2.0 ============================================
 * One file, two modes, picked from body classes:
 *
 *  1. Marketing pages (default): the fixed dot-rail TOC on the right
 *     (unchanged v1 behaviour — front page, /quality/, dosage pages, ...).
 *
 *  2. Articles (body.single-post): the article feature set —
 *       - text-list TOC on the right (>= 1280px, one line + ellipsis,
 *         hover copy button per entry)
 *       - collapsible "On this page" panel at the top of the article
 *         (< 1280px, default collapsed)
 *       - 3px reading progress bar (brand green) at the very top
 *       - inline CTA after the 2nd section, only when the article body
 *         is 1500+ words (dormant on the current short posts)
 *       - up/down "Was this article helpful?" feedback; down-vote opens a
 *         mini form that POSTs to /wp-json/sinofresh/v1/article-feedback
 *         (stored as a Gravity Forms Form 6 entry); one vote per post is
 *         remembered in localStorage
 *       - print source URL + date injected on beforeprint
 *
 * The TOC needs >= 3 eligible H2s; every other article extra runs
 * regardless. No dependencies, ES5 only.
 *
 * Highlight is computed on scroll (rAF-throttled), not via
 * IntersectionObserver: sections run 1,000px+ tall and a fast scroll moves
 * a heading straight from below the band to above it — the IO state never
 * changes so callbacks don't fire (measured). Reading rects at scroll time
 * is deterministic.
 */
(function () {
	"use strict";

	/* Front-page H2s excluded from the dot rail (exact/prefix text match). */
	var SKIP = [
		/^formulated clean$/i,
		/^from inquiry to after-sales$/i,
		/^trusted by 30\+/i,
		/^ready to launch your product\?$/i
	];

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

	function isArticle() {
		return /(^|\s)single-post(\s|$)/.test(document.body.className);
	}

	/* Collect visible, meaningful H2s under `root`. Lightboxes, modals and
	 * aria-hidden subtrees never become TOC targets. */
	function collectH2s(root, skipList) {
		var out = [];
		var nodes = root.querySelectorAll("h2");
		for (var k = 0; k < nodes.length; k++) {
			var h = nodes[k];
			if (h.closest(".sf-lb, .sf-certmodal, dialog, template, [hidden], [aria-hidden='true']")) continue;
			var cs = getComputedStyle(h);
			if (cs.display === "none" || cs.visibility === "hidden") continue;
			var text = (h.textContent || "").replace(/\s+/g, " ").trim();
			if (!text) continue;
			var skip = false;
			for (var s = 0; s < skipList.length; s++) {
				if (skipList[s].test(text)) { skip = true; break; }
			}
			if (skip) continue;
			out.push({ el: h, text: text });
		}
		return out;
	}

	/* Inject anchor ids + keep existing ones. */
	function anchor(h2s) {
		h2s.forEach(function (item, i) {
			if (!item.el.id) item.el.id = "sf-sec-" + i;
			item.el.classList.add("sf-toc-target");
		});
	}

	/* Shared scroll choreography: rAF-throttled, furthest-down heading that
	 * crossed the 97px header line is current, last item forced at bottom. */
	function bindHighlight(h2s, setCurrent, nav) {
		var queued = false;
		function onScroll() {
			if (queued) return;
			queued = true;
			requestAnimationFrame(function () {
				queued = false;
				if (nav) nav.classList.toggle("sf-toc--hidden", scrollY < 200);
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
		return onScroll;
	}

	function jump(item, after) {
		var reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
		item.el.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
		if (reduce) correctInstant(item.el, 3);
		else settleAndCorrect(item.el, 2);
		if (history.replaceState) history.replaceState(null, "", "#" + item.el.id);
		if (after) after();
	}

	/* -------------------------------------------------------------- toast */
	var toastEl = null, toastTimer = null;
	function toast(msg) {
		if (!toastEl) {
			toastEl = document.createElement("div");
			toastEl.className = "sf-toast";
			toastEl.setAttribute("role", "status");
			document.body.appendChild(toastEl);
		}
		toastEl.textContent = msg;
		toastEl.classList.add("is-visible");
		clearTimeout(toastTimer);
		toastTimer = setTimeout(function () {
			toastEl.classList.remove("is-visible");
		}, 2200);
	}

	function copyText(text, msg) {
		var fallback = function () {
			var ta = document.createElement("textarea");
			ta.value = text;
			ta.setAttribute("readonly", "");
			ta.style.position = "fixed";
			ta.style.opacity = "0";
			document.body.appendChild(ta);
			ta.select();
			try { document.execCommand("copy"); toast(msg); } catch (e) { /* noop */ }
			document.body.removeChild(ta);
		};
		if (navigator.clipboard && navigator.clipboard.writeText) {
			navigator.clipboard.writeText(text).then(function () { toast(msg); }, fallback);
		} else {
			fallback();
		}
	}

	/* ================================================== 1. DOT-RAIL MODE */
	function initRail() {
		var main = document.querySelector("main") || document.body;
		var h2s = collectH2s(main, SKIP);
		if (h2s.length < 3) return;
		anchor(h2s);

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
				jump(item);
				setCurrent(h2s.indexOf(item));
			});
			li.appendChild(a);
			ul.appendChild(li);
			links.push(a);
		});
		nav.appendChild(ul);
		document.body.appendChild(nav);

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
		var onScroll = bindHighlight(h2s, setCurrent, nav);
		onScroll();
	}

	/* =============================================== 2. ARTICLE FEATURES */
	function initArticle() {
		var content = document.querySelector(".sf-single-body .wp-block-post-content");
		var postId = (/(?:^|\s)postid-(\d+)(?:\s|$)/.exec(document.body.className) || [0, 0])[1];

		/* ---------- 2a. Reading progress bar (3px, brand green). ---------- */
		var bar = document.createElement("div");
		bar.className = "sf-progress";
		bar.setAttribute("aria-hidden", "true");
		document.body.appendChild(bar);
		var pQueued = false;
		function progress() {
			if (pQueued) return;
			pQueued = true;
			requestAnimationFrame(function () {
				pQueued = false;
				var max = document.documentElement.scrollHeight - innerHeight;
				var p = max > 0 ? Math.min(1, Math.max(0, scrollY / max)) : 0;
				bar.style.transform = "scaleX(" + p + ")";
			});
		}
		addEventListener("scroll", progress, { passive: true });
		addEventListener("resize", progress);
		progress();

		/* ---------- 2b. Copy-link buttons (hero meta + share row). -------- */
		Array.prototype.forEach.call(document.querySelectorAll(".sf-copy-link, .sf-share-btn--copy"), function (btn) {
			btn.addEventListener("click", function () {
				copyText(location.href, "Link copied");
			});
		});

		/* ---------- 2c. Feedback (up/down + GF Form 6 on down). ----------- */
		var fbBox = document.querySelector(".sf-article-feedback");
		if (fbBox && postId) {
			var stateKey = "sf_fb_" + postId;
			var thanks = fbBox.querySelector(".sf-article-feedback__thanks");
			var form = document.querySelector(".sf-fb-form");
			var errEl = form ? form.querySelector(".sf-fb-form__error") : null;
			var done = false;

			function track(vote) {
				if (typeof window.gtag === "function") {
					window.gtag("event", "article_feedback", { vote: vote, page: location.pathname });
				}
			}
			function send(payload, onOk, onFail) {
				fetch("/wp-json/sinofresh/v1/article-feedback", {
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify(payload)
				}).then(function (r) {
					if (!r.ok) throw new Error(r.status);
					return r.json();
				}).then(onOk).catch(onFail);
			}
			function finish(vote) {
				done = true;
				try { localStorage.setItem(stateKey, vote); } catch (e) { /* private mode */ }
				if (thanks) thanks.hidden = false;
				fbBox.classList.add("is-done");
			}

			var saved = null;
			try { saved = localStorage.getItem(stateKey); } catch (e) { /* private mode */ }
			if (saved) finish(saved);

			Array.prototype.forEach.call(fbBox.querySelectorAll(".sf-fb-btn"), function (btn) {
				btn.addEventListener("click", function () {
					if (done) return;
					var vote = btn.getAttribute("data-vote") === "down" ? "down" : "up";
					track(vote);
					if (vote === "down" && form) {
						form.hidden = false;
						var email = form.querySelector(".sf-fb-form__email");
						if (email) email.focus();
						return;
					}
					send({ vote: vote, post: postId }, function () { finish(vote); }, function () {
						/* Endpoint down: still close the loop for the visitor. */
						finish(vote);
					});
				});
			});

			if (form) {
				var cancel = form.querySelector(".sf-fb-form__cancel");
				if (cancel) cancel.addEventListener("click", function () { form.hidden = true; });
				form.addEventListener("submit", function (e) {
					e.preventDefault();
					if (done) return;
					var email = (form.querySelector(".sf-fb-form__email") || {}).value || "";
					var msg = (form.querySelector(".sf-fb-form__msg") || {}).value || "";
					var consent = !!(form.querySelector(".sf-fb-form__consent-box") || {}).checked;
					if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
						if (errEl) { errEl.textContent = "Please enter a valid email address."; errEl.hidden = false; }
						return;
					}
					var sendBtn = form.querySelector(".sf-fb-form__send");
					if (sendBtn) sendBtn.disabled = true;
					track("down");
					send({ vote: "down", post: postId, email: email, message: msg, consent: consent }, function () {
						form.hidden = true;
						finish("down");
					}, function () {
						if (sendBtn) sendBtn.disabled = false;
						if (errEl) { errEl.textContent = "Something went wrong. Please try again."; errEl.hidden = false; }
					});
				});
			}
		}

		/* ---------- 2d. Print source URL + date. --------------------------- */
		var printed = false;
		addEventListener("beforeprint", function () {
			if (printed) return;
			printed = true;
			var d = document.createElement("div");
			d.className = "sf-print-url";
			var now = new Date();
			d.textContent = "Source: " + location.href + " · Printed on " +
				now.toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" });
			/* Appended to the article body section — NOT .sf-related, which is
			 * display:none in print (it holds the share/feedback UI). */
			var bodySec = document.querySelector(".sf-single-body");
			(bodySec || document.body).appendChild(d);
		});

		/* ---------- 2e. TOC (text list desktop + collapsible mobile). ------ */
		if (!content) return;
		var h2s = collectH2s(content, []);
		if (h2s.length < 3) return;
		anchor(h2s);

		/* Desktop text list. */
		var nav = document.createElement("nav");
		nav.className = "sf-toc sf-toc--text";
		nav.setAttribute("aria-label", "On this page");
		var ul = document.createElement("ul");
		var links = [];
		h2s.forEach(function (item) {
			var li = document.createElement("li");
			var a = document.createElement("a");
			a.className = "sf-toc__link";
			a.href = "#" + item.el.id;
			a.title = item.text;
			a.textContent = item.text;
			var copy = document.createElement("button");
			copy.type = "button";
			copy.className = "sf-toc__copy";
			copy.setAttribute("aria-label", "Copy link to section: " + item.text);
			copy.title = "Copy link to section";
			copy.innerHTML = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>';
			copy.addEventListener("click", function (e) {
				e.preventDefault();
				e.stopPropagation();
				copyText(location.origin + location.pathname + "#" + item.el.id, "Section link copied");
			});
			a.addEventListener("click", function (e) {
				e.preventDefault();
				jump(item);
				setCurrent(h2s.indexOf(item));
			});
			li.appendChild(a);
			li.appendChild(copy);
			ul.appendChild(li);
			links.push(a);
		});
		nav.appendChild(ul);
		document.body.appendChild(nav);

		/* Mobile collapsible panel (mount lives in single.html). */
		var mount = document.querySelector(".sf-mobile-toc");
		if (mount) {
			var toggle = document.createElement("button");
			toggle.type = "button";
			toggle.className = "sf-mobile-toc__toggle";
			toggle.setAttribute("aria-expanded", "false");
			toggle.setAttribute("aria-controls", "sf-mobile-toc-panel");
			toggle.innerHTML = '<span>On this page</span><svg class="sf-mobile-toc__chev" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg>';
			var panel = document.createElement("div");
			panel.className = "sf-mobile-toc__panel";
			panel.id = "sf-mobile-toc-panel";
			panel.hidden = true;
			var mul = document.createElement("ul");
			h2s.forEach(function (item) {
				var li = document.createElement("li");
				var a = document.createElement("a");
				a.href = "#" + item.el.id;
				a.textContent = item.text;
				a.addEventListener("click", function (e) {
					e.preventDefault();
					panel.hidden = true;
					toggle.setAttribute("aria-expanded", "false");
					/* Collapsing the panel reflows the page above the target —
					 * let the layout settle (double rAF) before measuring. */
					requestAnimationFrame(function () {
						requestAnimationFrame(function () { jump(item); });
					});
				});
				li.appendChild(a);
				mul.appendChild(li);
			});
			panel.appendChild(mul);
			toggle.addEventListener("click", function () {
				var open = toggle.getAttribute("aria-expanded") === "true";
				toggle.setAttribute("aria-expanded", open ? "false" : "true");
				panel.hidden = open;
			});
			mount.appendChild(toggle);
			mount.appendChild(panel);
			mount.hidden = false;
		}

		/* Highlight sync (shared rAF calc) drives both lists. */
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
		var onScroll = bindHighlight(h2s, setCurrent, nav);
		onScroll();

		/* ---------- 2f. Inline CTA for long articles (1500+ words). ------- */
		var words = (content.textContent || "").trim().split(/\s+/).filter(Boolean).length;
		if (words >= 1500) {
			var cta = document.createElement("div");
			cta.className = "sf-inline-cta";
			cta.innerHTML = '<p class="sf-inline-cta__title">Launching a supplement line?</p>' +
				'<p class="sf-inline-cta__text">SINO FRESH manufactures soft chews, tablets, powders, pastes and drops for brands worldwide — low MOQs, in-house lab, full compliance support.</p>' +
				'<a class="sf-inline-cta__btn" href="/contact/">Request a Quote</a>';
			var after = h2s[2] ? h2s[2].el : h2s[h2s.length - 1].el;
			after.parentNode.insertBefore(cta, after);
		}
	}

	function init() {
		if (isArticle()) initArticle();
		else initRail();
	}

	if (document.readyState === "loading") {
		document.addEventListener("DOMContentLoaded", init);
	} else {
		init();
	}
})();

/**
 * SINO FRESH — the dosage-page product gallery.
 *
 * One data source: the <figure> frames the [sf_formula_gallery] shortcode
 * renders into .sf-gallery__stage. The thumbnail strip, its accessible names
 * and every switching target are derived from those frames, so replacing a
 * photo later is a one-place edit in functions.php.
 *
 * No library. Four rules hold this together:
 *
 *   1. The main photo is server-rendered, so a visitor without JS still sees
 *      it. Frames 2-4 ship with the `hidden` attribute, which is what keeps
 *      four photos from stacking when this file never runs.
 *   2. Switching a photo only toggles one class and two ARIA attributes. No
 *      DOM is moved, rebuilt or cloned. `hidden` comes off every frame at
 *      init so the cross-fade is possible at all — `display:none` cannot
 *      transition — and `.sf-gallery__slide--off` takes over from there.
 *   3. A pointer drag only counts as a swipe when it is unambiguously
 *      horizontal. Anything else is handed back to the browser untouched, so
 *      a vertical page scroll is never swallowed. The CSS `touch-action:
 *      pan-y pinch-zoom` on the stage is what makes that contract explicit,
 *      and keeping `pinch-zoom` there is deliberate: dropping it would take
 *      pinch-to-zoom away from anyone reading the page on a phone.
 *   4. Enhancements are separable. Without this file: one photo, one heading,
 *      no empty container, no console error.
 */
(function () {
	"use strict";

	/* A drag has to clear both thresholds before it becomes a swipe: 40px of
	   travel, travelling at least 1.5x further across than down. Below either
	   number the gesture is treated as a mis-tap on a photo, not a request to
	   change it. */
	var SWIPE_MIN = 40;
	var SWIPE_RATIO = 1.5;

	function initGallery(root) {
		var inner = root.querySelector(".sf-gallery__inner");
		var stage = root.querySelector(".sf-gallery__stage");
		if (!inner || !stage) return;

		var slides = Array.prototype.slice.call(stage.querySelectorAll(".sf-gallery__slide"));
		if (slides.length < 2) return;

		var slug = inner.getAttribute("data-gallery") || "product";
		var tabs = [];
		var current = 0;

		/* ---------- the thumbnail strip, built from the frames ---------- */
		var tablist = document.createElement("div");
		tablist.className = "sf-gallery__thumbs";
		tablist.setAttribute("role", "tablist");
		tablist.setAttribute("aria-label", "Product photos");

		slides.forEach(function (slide, i) {
			var full = slide.querySelector("img");
			var btn = document.createElement("button");
			btn.type = "button";
			btn.className = "sf-gallery__thumb";
			btn.id = "sf-gallery-tab-" + slug + "-" + (i + 1);
			btn.setAttribute("role", "tab");
			btn.setAttribute("aria-controls", slide.id);
			/* The button carries the name, so the <img> inside it is
			   decorative and must not repeat that name to a screen reader. */
			btn.setAttribute("aria-label", slide.getAttribute("data-label") || "Photo " + (i + 1));

			if (full) {
				var thumb = document.createElement("img");
				thumb.src = full.getAttribute("src");
				thumb.alt = "";
				thumb.width = full.getAttribute("width");
				thumb.height = full.getAttribute("height");
				thumb.loading = "lazy";
				thumb.decoding = "async";
				btn.appendChild(thumb);
			}

			tablist.appendChild(btn);
			tabs.push(btn);
		});
		inner.appendChild(tablist);

		/* ---------- selecting ---------- */
		function select(i, moveFocus) {
			current = (i + slides.length) % slides.length;

			slides.forEach(function (slide, j) {
				var on = j === current;
				slide.classList.toggle("sf-gallery__slide--off", !on);
				/* A frame at opacity 0 is still announced, so it has to be
				   taken out of the accessibility tree explicitly. */
				if (on) {
					slide.removeAttribute("aria-hidden");
				} else {
					slide.setAttribute("aria-hidden", "true");
				}
			});

			tabs.forEach(function (tab, j) {
				var on = j === current;
				tab.setAttribute("aria-selected", on ? "true" : "false");
				/* Roving tabindex: the strip is one tab stop, arrows move
				   within it. */
				tab.tabIndex = on ? 0 : -1;
			});

			var active = slides[current].querySelector("img");
			if (active && active.alt) {
				stage.setAttribute("aria-label", active.alt);
			}

			if (moveFocus) tabs[current].focus();
		}

		/* Hand the frames from the no-JS switch to the class-based one. */
		slides.forEach(function (slide) { slide.hidden = false; });

		/* One listener for the whole strip, not one per button. */
		root.addEventListener("click", function (event) {
			var btn = event.target.closest(".sf-gallery__thumbs .sf-gallery__thumb");
			if (!btn || !root.contains(btn)) return;
			var i = tabs.indexOf(btn);
			if (i !== -1) select(i, false);
		});

		tablist.addEventListener("keydown", function (event) {
			var next = null;
			if (event.key === "ArrowRight") next = current + 1;
			else if (event.key === "ArrowLeft") next = current - 1;
			else if (event.key === "Home") next = 0;
			else if (event.key === "End") next = tabs.length - 1;
			if (next === null) return;
			event.preventDefault();
			select(next, true);
		});

		/* ---------- swipe, as an enhancement only ---------- */
		var startX = 0, startY = 0, axis = "";

		stage.addEventListener("pointerdown", function (event) {
			if (!event.isPrimary) return;
			if (event.pointerType === "mouse" && event.button !== 0) return;
			startX = event.clientX;
			startY = event.clientY;
			axis = "";
			/* Keep receiving moves after the finger leaves the photo. */
			if (stage.setPointerCapture) {
				try { stage.setPointerCapture(event.pointerId); } catch (e) { /* not capturable */ }
			}
		});

		stage.addEventListener("pointermove", function (event) {
			if (!event.isPrimary || !event.buttons || axis !== "") return;
			var dx = event.clientX - startX;
			var dy = event.clientY - startY;
			if (Math.abs(dx) < SWIPE_MIN && Math.abs(dy) < SWIPE_MIN) return;
			/* Lock the axis on the first real movement and never revisit it:
			   a gesture that is not clearly horizontal belongs to the browser,
			   and `touch-action` has already given it the vertical one. */
			axis = Math.abs(dx) > Math.abs(dy) * SWIPE_RATIO ? "x" : "y";
		});

		stage.addEventListener("pointerup", function (event) {
			if (axis !== "x") return;
			axis = "";
			var dx = event.clientX - startX;
			if (Math.abs(dx) >= SWIPE_MIN) select(current + (dx < 0 ? 1 : -1), false);
		});

		function reset() { axis = ""; }
		stage.addEventListener("pointercancel", reset);
		stage.addEventListener("pointerleave", reset);

		select(0, false);
	}

	function boot() {
		var roots = document.querySelectorAll(".sf-gallery");
		for (var i = 0; i < roots.length; i++) initGallery(roots[i]);
	}

	if (document.readyState === "loading") {
		document.addEventListener("DOMContentLoaded", boot);
	} else {
		boot();
	}
})();

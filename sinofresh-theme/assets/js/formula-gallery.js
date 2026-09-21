/**
 * SINO FRESH — the product gallery: thumbnail strip, frame switching, and the
 * video facade. 2.0.0 (batch H2a).
 *
 * One data source: the <figure> frames the [sf_formula_gallery] shortcode
 * renders into .sf-gallery__stage. The thumbnail strip, its accessible names
 * and every switching target are derived from those frames, so replacing a
 * photo later is a one-place edit in functions.php.
 *
 * No library. Five rules hold this together:
 *
 *   1. The main photo is server-rendered, so a visitor without JS still sees
 *      it. Every other frame ships with the `hidden` attribute, which is what
 *      keeps them from stacking when this file never runs.
 *   2. Switching a frame only toggles one class and two ARIA attributes. No
 *      DOM is moved, rebuilt or cloned. `hidden` comes off every frame at
 *      init so the cross-fade is possible at all — `display:none` cannot
 *      transition — and `.sf-gallery__slide--off` takes over from there.
 *   3. A pointer drag only counts as a swipe when it is unambiguously
 *      horizontal. Anything else is handed back to the browser untouched, so
 *      a vertical page scroll is never swallowed. The CSS `touch-action:
 *      pan-y pinch-zoom` on the stage is what makes that contract explicit,
 *      and keeping `pinch-zoom` there is deliberate: dropping it would take
 *      pinch-to-zoom away from anyone reading the page on a phone.
 *   4. The video frame is a facade. The poster is server-rendered and the
 *      player is injected only when someone presses play, so a page load
 *      costs one image and YouTube's script is fetched on demand rather than
 *      on arrival. Without this file the poster and the button are all there
 *      is, and the button leads nowhere — it is a <button>, not a link.
 *   5. Enhancements are separable. Without this file: one photo, one heading,
 *      no empty container, no console error.
 *
 * New in 2.0.0, both additive:
 *   - Hover-to-preview on the strip, bound only where the device reports a
 *     real hover. On a touch screen `mouseenter` is synthesised by the tap
 *     that is about to become a click, so the strip would appear to fire
 *     twice; `matchMedia("(hover: hover)")` is what keeps this a desktop
 *     affordance instead of a bug on phones.
 *   - The video frame: the strip tile is marked as one, and pressing play
 *     swaps the button for the player.
 */
(function () {
	"use strict";

	/* A drag has to clear both thresholds before it becomes a swipe: 40px of
	   travel, travelling at least 1.5x further across than down. Below either
	   number the gesture is treated as a mis-tap on a photo, not a request to
	   change it. */
	var SWIPE_MIN = 40;
	var SWIPE_RATIO = 1.5;

	/* Evaluated once: the input mix of a device does not change mid-session,
	   and this keeps the per-event paths free of a media query. */
	var CAN_HOVER = !!(window.matchMedia && window.matchMedia("(hover: hover)").matches);

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
			var isVideo = slide.classList.contains("sf-gallery__slide--video");

			var btn = document.createElement("button");
			btn.type = "button";
			btn.className = isVideo ? "sf-gallery__thumb sf-gallery__thumb--video" : "sf-gallery__thumb";
			btn.id = "sf-gallery-tab-" + slug + "-" + (i + 1);
			btn.setAttribute("role", "tab");
			btn.setAttribute("aria-controls", slide.id);
			/* The button carries the name, so the <img> inside it is
			   decorative and must not repeat that name to a screen reader.
			   data-label is the frame's own description, and for the video
			   frame it already ends in "product video" — the tile needs no
			   second, written-out label to drift out of step with it. */
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

			/* The stage takes its name from the frame's own description. The
			   <img> alt is the fallback for a frame that somehow carries no
			   data-label. */
			var active = slides[current];
			var name = active.getAttribute("data-label");
			if (!name) {
				var activeImg = active.querySelector("img");
				name = activeImg ? activeImg.alt : "";
			}
			if (name) stage.setAttribute("aria-label", name);

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

		/* Delegated on the strip rather than bound per tile: `mouseover`
		   reaches this from the thumbnail's own <img> too, and `closest`
		   walks that back to the button, so the strip needs one listener
		   whatever its length. `i !== current` is what stops a re-select of
		   the frame already showing. */
		if (CAN_HOVER) {
			tablist.addEventListener("mouseover", function (event) {
				var btn = event.target.closest(".sf-gallery__thumb");
				if (!btn || !tablist.contains(btn)) return;
				var i = tabs.indexOf(btn);
				if (i !== -1 && i !== current) select(i, false);
			});
		}

		tablist.addEventListener("keydown", function (event) {
			var next = null;
			if (event.key === "ArrowRight" || event.key === "ArrowDown") next = current + 1;
			else if (event.key === "ArrowLeft" || event.key === "ArrowUp") next = current - 1;
			else if (event.key === "Home") next = 0;
			else if (event.key === "End") next = tabs.length - 1;
			if (next === null) return;
			event.preventDefault();
			select(next, true);
		});

		/* ---------- the video facade: player on demand ---------- */
		root.addEventListener("click", function (event) {
			var play = event.target.closest(".sf-gallery__play");
			if (!play || !root.contains(play)) return;
			var frame = play.closest(".sf-gallery__slide--video");
			if (!frame || frame.getAttribute("data-loaded") === "1") return;
			var id = frame.getAttribute("data-video-id");
			if (!id) return;

			var box = document.createElement("div");
			box.className = "sf-gallery__embed";

			var iframe = document.createElement("iframe");
			/* youtube-nocookie: the player still works, but YouTube sets no
			   tracking cookies until the video is actually played — and this
			   code only ever runs because someone pressed play. */
			iframe.src = "https://www.youtube-nocookie.com/embed/"
				+ encodeURIComponent(id) + "?autoplay=1&rel=0";
			iframe.title = frame.getAttribute("data-label") || "Product video";
			iframe.setAttribute("allow",
				"accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture");
			iframe.setAttribute("allowfullscreen", "");
			box.appendChild(iframe);

			/* Marks the frame so a second press, or a re-select of the frame,
			   cannot inject a second player. */
			frame.setAttribute("data-loaded", "1");
			play.parentNode.replaceChild(box, play);
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

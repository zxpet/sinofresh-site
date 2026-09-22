/**
 * SINO FRESH — the product gallery: the [Photos][Video] switch, the thumbnail
 * strip and the video facade. 2.1.0 (batch H7a; 2.0.0 was batch H2a).
 *
 * One data source: the <figure> frames the [sf_formula_gallery] shortcode
 * renders into .sf-gallery__stage. The switch's two labels are served by PHP,
 * not built here — they are the band's only translatable strings and the
 * language layer only sees server-rendered text — so this file owns their
 * state and nothing else. The thumbnail strip, its accessible names and every
 * switching target are derived from the frames, so replacing a photo later is
 * a one-place edit in functions.php.
 *
 * No library. Six rules hold this together:
 *
 *   1. The main photo is server-rendered, so a visitor without JS still sees
 *      it. Every other frame ships with the `hidden` attribute, which is what
 *      keeps them from stacking when this file never runs — and the switch
 *      ships hidden as well, painted only once `.sf-gallery--js` is on the
 *      root. Without this file there is no bar, rather than a dead one.
 *   2. The frames are of two kinds and only one of them is a photo. The video
 *      is NOT a strip tile: the strip is the photo picker, its accessible name
 *      says so, and reaching the video is the [Video] button's job. That is
 *      why the strip can be built from a `photos` list while `current` indexes
 *      that list — the two arrays were never mixed, so there is no second
 *      index map to keep in step.
 *   3. Switching a frame only toggles one class and two ARIA attributes. No
 *      DOM is moved, rebuilt or cloned. `hidden` comes off every photo at init
 *      so the cross-fade is possible at all — `display:none` cannot
 *      transition — and `.sf-gallery__slide--off` takes over from there. The
 *      video frame is the deliberate exception: it keeps `hidden` until the
 *      [Video] tab is opened, so a page load never fetches YouTube's poster.
 *   4. A pointer drag only counts as a swipe when it is unambiguously
 *      horizontal. Anything else is handed back to the browser untouched, so
 *      a vertical page scroll is never swallowed. The CSS `touch-action:
 *      pan-y pinch-zoom` on the stage is what makes that contract explicit,
 *      and keeping `pinch-zoom` there is deliberate: dropping it would take
 *      pinch-to-zoom away from anyone reading the page on a phone.
 *   5. The video frame is a facade. The poster is server-rendered and the
 *      player is injected only when someone presses play, so a page load
 *      costs one image and YouTube's script is fetched on demand rather than
 *      on arrival. Without this file the poster and the button are all there
 *      is, and the button leads nowhere — it is a <button>, not a link that
 *      would navigate off to youtube.com.
 *   6. Enhancements are separable. Without this file: one photo, no strip,
 *      no switch, no empty container, no console error.
 *
 * New in 2.1.0, both from the switch:
 *   - The strip is photos-only. It used to carry the video frame as a tile
 *     marked `.sf-gallery__thumb--video`, which meant a tile whose picture was
 *     a video sitting in a list named "Product photos" and a tile that broke
 *     the arrow keys' own model of "the next photo".
 *   - The video frame is reached by a mode, not by a position: opening
 *     [Video] hides the strip and shows the frame, and [Photos] puts the
 *     visitor back on the photo they left, which a position-based model
 *     cannot promise.
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

		var frames = Array.prototype.slice.call(stage.querySelectorAll(".sf-gallery__slide"));
		if (frames.length < 2) return;

		var slug = inner.getAttribute("data-gallery") || "product";

		/* Rule 2: split the frames once, here, and never mix them again. */
		var photos = [];
		var video = null;
		frames.forEach(function (frame) {
			if (frame.classList.contains("sf-gallery__slide--video")) {
				if (!video) video = frame;
			} else {
				photos.push(frame);
			}
		});
		if (!photos.length) return;

		var current = 0;     /* an index into photos, never into frames */
		var mode = "photos"; /* "photos" | "video" */
		var tabs = [];
		var tabBtns = {};

		/* Rule 1: the bar is in the markup, but painted only from here on. */
		root.classList.add("sf-gallery--js");
		Array.prototype.forEach.call(root.querySelectorAll(".sf-gallery__tab"), function (btn) {
			var kind = btn.getAttribute("data-sf-gallery-tab");
			if (kind) tabBtns[kind] = btn;
		});

		/* ---------- the thumbnail strip, built from the photos ---------- */
		var tablist = document.createElement("div");
		tablist.className = "sf-gallery__thumbs";
		tablist.setAttribute("role", "tablist");
		tablist.setAttribute("aria-label", "Product photos");

		photos.forEach(function (slide, i) {
			var full = slide.querySelector("img");

			var btn = document.createElement("button");
			btn.type = "button";
			btn.className = "sf-gallery__thumb";
			btn.id = "sf-gallery-tab-" + slug + "-" + (i + 1);
			btn.setAttribute("role", "tab");
			btn.setAttribute("aria-controls", slide.id);
			/* The button carries the name, so the <img> inside it is
			   decorative and must not repeat that name to a screen reader.
			   data-label is the frame's own description — the same string the
			   stage is named with. */
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

		/* ---------- painting ---------- */
		function show(slide, on) {
			slide.classList.toggle("sf-gallery__slide--off", !on);
			/* A frame at opacity 0 is still announced, so it has to be taken
			   out of the accessibility tree explicitly. */
			if (on) {
				slide.removeAttribute("aria-hidden");
			} else {
				slide.setAttribute("aria-hidden", "true");
			}
		}

		function paint() {
			var onVideo = mode === "video" && !!video;

			photos.forEach(function (slide, j) {
				show(slide, !onVideo && j === current);
			});

			/* Rule 3: the poster stays un-fetched until someone asks for it. */
			if (video) {
				if (onVideo) {
					video.hidden = false;
					show(video, true);
				} else {
					show(video, false);
					video.hidden = true;
				}
			}

			root.classList.toggle("sf-gallery--video", onVideo);

			tabs.forEach(function (tab, j) {
				var on = j === current;
				tab.setAttribute("aria-selected", on ? "true" : "false");
				/* Roving tabindex: the strip is one tab stop, arrows move
				   within it. In video mode the whole strip is display:none, so
				   taking every tile out of the tab order costs nothing — and
				   the selection is kept, so [Photos] returns to the same photo
				   rather than to the first one. */
				tab.tabIndex = (on && !onVideo) ? 0 : -1;
			});

			Object.keys(tabBtns).forEach(function (kind) {
				var on = kind === (onVideo ? "video" : "photos");
				tabBtns[kind].setAttribute("aria-pressed", on ? "true" : "false");
				tabBtns[kind].classList.toggle("is-active", on);
			});

			/* The stage takes its name from the frame's own description. The
			   <img> alt is the fallback for a frame that somehow carries no
			   data-label. */
			var active = onVideo ? video : photos[current];
			if (active) {
				var name = active.getAttribute("data-label");
				if (!name) {
					var img = active.querySelector("img");
					name = img ? img.alt : "";
				}
				if (name) stage.setAttribute("aria-label", name);
			}
		}

		function selectPhoto(i, moveFocus) {
			current = (i + photos.length) % photos.length;
			mode = "photos";
			paint();
			if (moveFocus) tabs[current].focus();
		}

		function selectMode(kind) {
			if (kind === "video" && !video) return;
			if (kind !== "photos" && kind !== "video") return;
			mode = kind;
			paint();
		}

		/* Hand the photos from the no-JS switch to the class-based one. The
		   video frame is left alone on purpose: paint() keeps it `hidden`
		   until the [Video] tab asks for it, which is what stops a page load
		   from fetching YouTube's poster. */
		photos.forEach(function (slide) { slide.hidden = false; });

		/* One listener for the whole band: the switch first, then the strip. */
		root.addEventListener("click", function (event) {
			var tab = event.target.closest(".sf-gallery__tab");
			if (tab && root.contains(tab)) {
				selectMode(tab.getAttribute("data-sf-gallery-tab"));
				return;
			}
			var btn = event.target.closest(".sf-gallery__thumbs .sf-gallery__thumb");
			if (!btn || !root.contains(btn)) return;
			var i = tabs.indexOf(btn);
			if (i !== -1) selectPhoto(i, false);
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
				if (i !== -1 && i !== current) selectPhoto(i, false);
			});
		}

		tablist.addEventListener("keydown", function (event) {
			var next = null;
			if (event.key === "ArrowRight" || event.key === "ArrowDown") next = current + 1;
			else if (event.key === "ArrowLeft" || event.key === "ArrowUp") next = current - 1;
			else if (event.key === "Home") next = 0;
			else if (event.key === "End") next = photos.length - 1;
			if (next === null) return;
			event.preventDefault();
			selectPhoto(next, true);
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

			/* Marks the frame so a second press, or a return to this frame,
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
			if (Math.abs(dx) >= SWIPE_MIN) selectPhoto(current + (dx < 0 ? 1 : -1), false);
		});

		function reset() { axis = ""; }
		stage.addEventListener("pointercancel", reset);
		stage.addEventListener("pointerleave", reset);

		paint();
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

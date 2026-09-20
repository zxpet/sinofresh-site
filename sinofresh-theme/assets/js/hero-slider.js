/*! SINO FRESH hero slider — 4 slides, translateX track, no library.
    Autoplay is a single requestAnimationFrame loop (5s per slide) that also
    drives the .sf-slider-progress bar hugging the stage's bottom edge.
    Pauses on hover/focus and when the tab is hidden; each pause freezes the
    bar in place and playback resumes from that exact position. Arrows, dots
    and touch swipe reset the progress for the new slide. Reduced-motion
    keeps autoplay off entirely (the bar stays hidden via CSS). */
(function () {
	'use strict';
	var root = document.querySelector('.sf-hero-slider');
	if (!root) return;
	var track = root.querySelector('.sf-hero-track');
	var slides = root.querySelectorAll('.sf-slide');
	var n = slides.length;
	if (!track || n < 2) return;

	var DURATION = 5000;
	var bar = root.querySelector('.sf-slider-progress__bar');
	var reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;

	var dots = root.querySelector('.sf-hero-dots');
	for (var k = 0; k < n; k++) {
		var d = document.createElement('button');
		d.type = 'button';
		d.setAttribute('aria-label', 'Go to slide ' + (k + 1));
		d.addEventListener('click', (function (x) { return function () { go(x); restart(); }; })(k));
		dots.appendChild(d);
	}
	var dotsArr = dots.children;

	var i = 0;
	var raf = 0;
	var startTime = 0;       /* performance.now() when the current slide resumed */
	var elapsed = 0;         /* ms played on the current slide */
	var userPaused = false;  /* hover / focus pause */
	var hiddenPaused = false;/* document.hidden pause */

	/* progress bar mirrors elapsed/DURATION; never exceeds 1 */
	function paint() {
		if (!bar) return;
		var p = elapsed / DURATION;
		if (p > 1) p = 1;
		bar.style.transform = 'scaleX(' + p + ')';
	}

	function tick(now) {
		elapsed = now - startTime;
		if (elapsed >= DURATION) {
			go(i + 1);              /* go() resets elapsed for the next slide */
			startTime = performance.now();
		}
		paint();
		raf = requestAnimationFrame(tick);
	}

	/* freeze in place: snapshot lives in `elapsed`, so any resume continues
	   from it via startTime = now - elapsed (idempotent) */
	function pause() {
		if (raf) { cancelAnimationFrame(raf); raf = 0; }
	}

	/* only runs the loop when autoplay is allowed at all (no reduced motion,
	   no hover/focus hold, tab visible) and is not already running */
	function resumeIfRunnable() {
		if (reduced || userPaused || hiddenPaused || raf) return;
		startTime = performance.now() - elapsed;
		raf = requestAnimationFrame(tick);
	}

	function go(x) {
		i = (x + n) % n;
		track.style.transform = 'translateX(-' + i * 100 + '%)';
		for (var k = 0; k < n; k++) {
			var on = k === i;
			slides[k].classList.toggle('is-active', on);
			slides[k].toggleAttribute('inert', !on);
			dotsArr[k].classList.toggle('is-active', on);
		}
		elapsed = 0; /* fresh slide, fresh progress */
	}

	/* manual switch (arrows/dots/swipe): bar resets to 0 for the new slide,
	   whether or not the loop is currently paused */
	function restart() {
		elapsed = 0;
		paint();
		pause();
		resumeIfRunnable();
	}

	root.querySelector('.sf-hero-prev').addEventListener('click', function () { go(i - 1); restart(); });
	root.querySelector('.sf-hero-next').addEventListener('click', function () { go(i + 1); restart(); });
	root.addEventListener('mouseenter', function () { userPaused = true; pause(); });
	root.addEventListener('mouseleave', function () { userPaused = false; resumeIfRunnable(); });
	root.addEventListener('focusin', function () { userPaused = true; pause(); });
	root.addEventListener('focusout', function () { userPaused = false; resumeIfRunnable(); });

	/* tab hidden: freeze; visible again: continue from the frozen position */
	document.addEventListener('visibilitychange', function () {
		if (document.hidden) {
			hiddenPaused = true;
			pause();
		} else {
			hiddenPaused = false;
			resumeIfRunnable();
		}
	});

	/* touch swipe (phones): only mostly-horizontal gestures switch slides so
	   vertical page scrolling is never hijacked (passive, no preventDefault) */
	var x0 = 0, y0 = 0, swiping = false;
	root.addEventListener('touchstart', function (e) {
		x0 = e.touches[0].clientX;
		y0 = e.touches[0].clientY;
		swiping = true;
	}, { passive: true });
	root.addEventListener('touchmove', function (e) {
		if (!swiping) return;
		var dx = e.touches[0].clientX - x0;
		var dy = e.touches[0].clientY - y0;
		if (Math.abs(dx) > Math.abs(dy) && Math.abs(dx) > 14) {
			go(i + (dx < 0 ? 1 : -1));
			restart();
			swiping = false;
		} else if (Math.abs(dy) > Math.abs(dx) && Math.abs(dy) > 14) {
			swiping = false;
		}
	}, { passive: true });
	root.addEventListener('touchend', function () { swiping = false; }, { passive: true });

	go(0);
	if (!reduced) {
		startTime = performance.now();
		raf = requestAnimationFrame(tick);
	}
	/* reduced motion: autoplay and the progress bar stay off entirely */
})();

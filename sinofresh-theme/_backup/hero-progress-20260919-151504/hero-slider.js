/*! SINO FRESH hero slider — 4 slides, translateX track, no library.
    Autoplay 5s, pauses on hover/focus, arrows + dots, touch swipe,
    reduced-motion safe. */
(function () {
	'use strict';
	var root = document.querySelector('.sf-hero-slider');
	if (!root) return;
	var track = root.querySelector('.sf-hero-track');
	var slides = root.querySelectorAll('.sf-slide');
	var n = slides.length;
	if (!track || n < 2) return;

	var dots = root.querySelector('.sf-hero-dots');
	for (var k = 0; k < n; k++) {
		var d = document.createElement('button');
		d.type = 'button';
		d.setAttribute('aria-label', 'Go to slide ' + (k + 1));
		d.addEventListener('click', (function (x) { return function () { go(x); restart(); }; })(k));
		dots.appendChild(d);
	}
	var dotsArr = dots.children;

	var i = 0, timer = null;
	function go(x) {
		i = (x + n) % n;
		track.style.transform = 'translateX(-' + i * 100 + '%)';
		for (var k = 0; k < n; k++) {
			var on = k === i;
			slides[k].classList.toggle('is-active', on);
			slides[k].toggleAttribute('inert', !on);
			dotsArr[k].classList.toggle('is-active', on);
		}
	}
	function stop() { if (timer) { clearInterval(timer); timer = null; } }
	function play() {
		if (!timer && !matchMedia('(prefers-reduced-motion: reduce)').matches)
			timer = setInterval(function () { go(i + 1); }, 5000);
	}
	function restart() { stop(); play(); }

	root.querySelector('.sf-hero-prev').addEventListener('click', function () { go(i - 1); restart(); });
	root.querySelector('.sf-hero-next').addEventListener('click', function () { go(i + 1); restart(); });
	root.addEventListener('mouseenter', stop);
	root.addEventListener('mouseleave', play);
	root.addEventListener('focusin', stop);
	root.addEventListener('focusout', play);

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
	play();
})();

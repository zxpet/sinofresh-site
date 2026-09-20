/*! SINO FRESH product slider — dosage-page hero card carousel, no library.
    Same paradigm as hero-slider.js (translateX track, JS-generated dots,
    autoplay pause on hover/focus, reduced-motion safe) plus touch swipe.
    4s autoplay; dots keep a 32px touch target via an invisible ::after. */
(function () {
	'use strict';
	var root = document.querySelector('.sf-pslider');
	if (!root) return;
	var track = root.querySelector('.sf-pslider__track');
	var slides = root.querySelectorAll('.sf-pslider__slide');
	var n = slides.length;
	if (!track || n < 2) return;

	/* dots: generated like the home hero, hit area enlarged in CSS */
	var dots = root.querySelector('.sf-pslider__dots');
	for (var k = 0; k < n; k++) {
		var d = document.createElement('button');
		d.type = 'button';
		d.setAttribute('aria-label', 'Go to photo ' + (k + 1));
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
			timer = setInterval(function () { go(i + 1); }, 4000);
	}
	function restart() { stop(); play(); }

	root.querySelector('.sf-pslider__prev').addEventListener('click', function () { go(i - 1); restart(); });
	root.querySelector('.sf-pslider__next').addEventListener('click', function () { go(i + 1); restart(); });
	root.addEventListener('mouseenter', stop);
	root.addEventListener('mouseleave', play);
	root.addEventListener('focusin', stop);
	root.addEventListener('focusout', play);

	/* touch swipe: only react to mostly-horizontal gestures so vertical
	   page scrolling is never hijacked (passive listeners, no preventDefault) */
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

/* SINO FRESH — templates/page-about.html behaviour, enqueued on that page only.
   Everything here is progressive: the CSS that hides a milestone only applies
   once this file adds .sf-journey--live, so no-JS and reduced-motion visitors
   see the finished page instead of a section stuck at opacity 0. */
(() => {
	'use strict';

	/* ---------- Our Journey: rail + nodes, revealed once on entry ---------- */
	const initJourney = () => {
		const journey = document.querySelector('.sf-journey');
		if (!journey) return;
		const items = [...journey.querySelectorAll('.sf-journey__item')];
		if (!items.length) return;
		if (!('IntersectionObserver' in window)) return;
		if (window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches) return;

		items.forEach((el, i) => { el.style.transitionDelay = i * 90 + 'ms'; });
		journey.classList.add('sf-journey--live');

		// The stagger belongs to the entrance only. Left in place it would also
		// delay the :hover lift by up to (n-1)*90ms, so drop it once the row has
		// landed — the timeout covers rows the observer never got around to.
		const reveal = (el) => {
			el.classList.add('is-revealed');
			const wait = (parseFloat(el.style.transitionDelay) || 0) + 700;
			setTimeout(() => { el.style.transitionDelay = ''; }, wait);
		};

		const io = new IntersectionObserver((entries) => {
			entries.forEach((e) => {
				if (!e.isIntersecting) return;
				io.unobserve(e.target);              // one-shot: no rewinding on scroll back
				reveal(e.target);
			});
		}, { rootMargin: '0px 0px -12% 0px', threshold: 0.15 });

		items.forEach((el) => io.observe(el));

		// Safety net: if the observer never fires, never leave copy hidden.
		setTimeout(() => items.forEach((el) => reveal(el)), 2500);
	};

	/* ---------- Video: poster first, YouTube player only on click ----------
	   Nothing is fetched from YouTube until the visitor asks for it: no embed
	   script, no thumbnail, no cookies. The ID lives in data-video-id on the
	   button and is read at click time, so it can be filled in later without
	   touching this file. ------------------------------------------------ */
	const initVideo = () => {
		const frame = document.querySelector('.sf-video-cover');
		if (!frame) return;
		const btn = frame.querySelector('.sf-video__play');
		if (!btn) return;

		btn.addEventListener('click', () => {
			const id = (btn.dataset.videoId || '').trim();
			if (!id || id === 'REPLACE_ME') {
				console.warn('[sinofresh] .sf-video__play needs data-video-id (the 11-character YouTube ID); until then the player stays off.');
				return;
			}

			const poster = frame.querySelector('img');
			const player = document.createElement('iframe');
			player.className = 'sf-video__iframe';
			player.src = 'https://www.youtube-nocookie.com/embed/' + encodeURIComponent(id) + '?autoplay=1&rel=0&playsinline=1';
			player.title = (poster && poster.alt) || 'Video player';
			player.setAttribute('allow', 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share');
			player.setAttribute('allowfullscreen', '');
			player.setAttribute('referrerpolicy', 'strict-origin-when-cross-origin');

			frame.appendChild(player);
			frame.classList.add('is-playing');
			player.focus();
		});
	};

	/* ---------- Inside Our Factory: Gallery block + lightbox ---------------
	   The grid is a core Gallery block, so the markup carries no behaviour —
	   these hooks turn each thumbnail into a button for one native dialog.
	   The viewer is built on the first click, so a visitor who never opens a
	   photo pays nothing for it. Arrows wrap, Escape and the backdrop close,
	   focus returns to the thumbnail that opened the dialog, and the
	   zoom-from-thumbnail motion is skipped under prefers-reduced-motion.
	   No library, no plugin: everything below is createElement + Web Animations. */
	const initFactoryLightbox = () => {
		const gallery = document.querySelector('.sf-fac');
		if (!gallery) return;
		const thumbs = [...gallery.querySelectorAll('figure.wp-block-image img')];
		if (!thumbs.length) return;

		const reduce = window.matchMedia ? matchMedia('(prefers-reduced-motion: reduce)') : { matches: false };
		const FIT = 48;                    // the overlay's 24px side padding, doubled
		let box = null, stage = null, big = null, counter = null, index = 0, opener = null, ratio = [4, 3];

		/* Size the stage as the largest box that fits the overlay at the photo's
		   own ratio, so the enlarged photo is as big as it can be without ever
		   being stretched or letterboxed inside a larger box. */
		const fitBox = () => {
			if (!box || !stage) return;
			const availW = Math.min(1100, box.clientWidth - FIT);
			const availH = window.innerHeight - 180;
			const scale = Math.min(availW / ratio[0], availH / ratio[1]);
			stage.style.width = Math.max(140, Math.round(ratio[0] * scale)) + 'px';
		};

		const build = () => {
			box = document.createElement('div');
			box.className = 'sf-lb';
			box.hidden = true;
			box.setAttribute('role', 'dialog');
			box.setAttribute('aria-modal', 'true');
			box.setAttribute('aria-label', 'Factory photo viewer');
			box.innerHTML =
				'<div class="sf-lb__stage"><img class="sf-lb__img" alt="" decoding="async"></div>' +
				'<div class="sf-lb__bar">' +
					'<button class="sf-lb__btn sf-lb__btn--prev" type="button" aria-label="Previous photo"><span aria-hidden="true">&#8249;</span></button>' +
					'<p class="sf-lb__count" aria-hidden="true"></p>' +
					'<button class="sf-lb__btn sf-lb__btn--next" type="button" aria-label="Next photo"><span aria-hidden="true">&#8250;</span></button>' +
					'<button class="sf-lb__btn sf-lb__btn--close" type="button" aria-label="Close viewer"><span aria-hidden="true">&#10005;</span></button>' +
				'</div>';
			document.body.appendChild(box);

			big = box.querySelector('.sf-lb__img');
			stage = box.querySelector('.sf-lb__stage');
			counter = box.querySelector('.sf-lb__count');

			window.addEventListener('resize', () => { if (!box.hidden) fitBox(); });

			box.querySelector('.sf-lb__btn--prev').addEventListener('click', () => step(-1));
			box.querySelector('.sf-lb__btn--next').addEventListener('click', () => step(1));
			box.querySelector('.sf-lb__btn--close').addEventListener('click', () => close());

			// a click anywhere but the photo and the controls is "on the backdrop"
			box.addEventListener('click', (e) => {
				if (e.target === big || e.target.closest('.sf-lb__btn')) return;
				close();
			});

			document.addEventListener('keydown', (e) => {
				if (box.hidden) return;
				if (e.key === 'Escape') { e.preventDefault(); close(); }
				else if (e.key === 'ArrowLeft') { e.preventDefault(); step(-1); }
				else if (e.key === 'ArrowRight') { e.preventDefault(); step(1); }
				else if (e.key === 'Tab') {
					// three buttons, tiny trap so Tab cannot walk out of the dialog
					const b = [...box.querySelectorAll('button')];
					const first = b[0], last = b[b.length - 1];
					if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
					else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
				}
			});
		};

		/* the flip distance between a thumbnail and the enlarged photo */
		const flip = (thumb, reverse) => {
			if (reduce.matches || !thumb) return null;
			const from = thumb.getBoundingClientRect();
			const to = big.getBoundingClientRect();
			if (!from.width || !to.width) return null;
			const dx = (from.left + from.width / 2) - (to.left + to.width / 2);
			const dy = (from.top + from.height / 2) - (to.top + to.height / 2);
			const s = from.width / to.width;
			const framed = 'translate(' + dx + 'px, ' + dy + 'px) scale(' + s + ')';
			return reverse
				? [{ transform: 'none' }, { transform: framed }]
				: [{ transform: framed }, { transform: 'none' }];
		};

		const show = (i, animate) => {
			index = (i + thumbs.length) % thumbs.length;
			const thumb = thumbs[index];

			// ratio and stage size come first: the flip and the photo must both
			// measure a box that is already at its final size
			const tw = +thumb.getAttribute('width') || 0;
			const th = +thumb.getAttribute('height') || 0;
			ratio = tw && th ? [tw, th] : [4, 3];
			if (tw && th) {
				big.width = tw;
				big.height = th;
			} else {
				big.removeAttribute('width');
				big.removeAttribute('height');
			}
			big.style.aspectRatio = ratio[0] + ' / ' + ratio[1];
			fitBox();

			const frames = animate ? flip(thumb, false) : null;
			big.src = thumb.currentSrc || thumb.src;
			big.alt = thumb.alt || '';
			counter.textContent = (index + 1) + ' / ' + thumbs.length;

			[].forEach.call(gallery.querySelectorAll('.is-current'), (el) => el.classList.remove('is-current'));
			(thumb.closest('figure.wp-block-image') || thumb).classList.add('is-current');

			if (frames) big.animate(frames, { duration: 260, easing: 'cubic-bezier(.22,.61,.36,1)' });
		};

		const step = (delta) => show(index + delta, true);

		const open = (i, trigger) => {
			if (!box) build();
			opener = trigger || null;
			big.removeAttribute('src');           // never flash the previous photo
			show(i, false);
			box.classList.remove('is-closing');
			box.hidden = false;
			document.documentElement.classList.add('sf-lb-open');
			box.getBoundingClientRect();          // force layout before the flip measures
			box.classList.add('is-open');
			show(i, true);
			box.querySelector('.sf-lb__btn--close').focus();
		};

		const close = () => {
			if (!box || box.hidden) return;
			const frames = flip(thumbs[index], true);
			const done = () => {
				if (box.hidden) return;
				box.hidden = true;
				box.classList.remove('is-open', 'is-closing');
				document.documentElement.classList.remove('sf-lb-open');
				[].forEach.call(gallery.querySelectorAll('.is-current'), (el) => el.classList.remove('is-current'));
				if (opener) opener.focus();
			};
			box.classList.add('is-closing');
			if (frames) {
				const a = big.animate(frames, { duration: 220, easing: 'ease-in' });
				a.addEventListener('finish', done);
				setTimeout(done, 400);            // if the animation never fires
			} else {
				done();
			}
		};

		thumbs.forEach((thumb, i) => {
			const figure = thumb.closest('figure.wp-block-image') || thumb;
			const label = 'View photo ' + (i + 1) + ' of ' + thumbs.length + (thumb.alt ? ': ' + thumb.alt : '');
			figure.setAttribute('role', 'button');
			figure.setAttribute('tabindex', '0');
			figure.setAttribute('aria-label', label);
			figure.addEventListener('click', () => open(i, figure));
			figure.addEventListener('keydown', (e) => {
				if (e.key === 'Enter' || e.key === ' ' || e.key === 'Spacebar') { e.preventDefault(); open(i, figure); }
			});
		});
	};

	initJourney();
	initVideo();
	initFactoryLightbox();
})();

/* SINO FRESH — templates/page-quality.html behaviour, enqueued on that page only.
   One job: turn the certificate thumbnails into a lightbox instead of a new
   tab. It reuses the .sf-lb markup and styles the About page's factory gallery
   already ships, so nothing new is added to the stylesheet.

   Progressive throughout: the thumbnails stay plain <a href="…cert.webp">
   links until this file swaps them for the viewer, so without JS (or when a
   modifier key asks for a new tab) the certificate still opens — just as a
   full-size image in its own tab, which is exactly what it did before.

   B4.5: the viewer also carries the request line — "Full certificate available
   upon request" — as one <a data-cert> naming the certificate on screen, so
   cert-modal.js opens the request dialog for exactly that document. */
(() => {
	'use strict';

	const strip = document.querySelector('.sf-certdetail');
	if (!strip) return;

	/* Which document a row is about. The row's own download control carries the
	   key (B4.5 put it there); the file name is the fallback so the line still
	   works if that control ever moves. */
	const certKey = (a) => {
		const row = a.closest('.sf-certrow');
		const held = row ? row.querySelector('[data-cert]') : null;
		if (held) return held.getAttribute('data-cert');
		const m = (a.getAttribute('href') || '').match(/cert-([a-z0-9]+?)(?:-thumb)?\.[a-z]{3,4}(?:[?#].*)?$/i);
		return m ? m[1] : '';
	};

	/* Only the rows that actually carry a scan. The HACCP and BRC rows are
	   placeholder divs with no anchor at all, so they drop out here. */
	const items = [...strip.querySelectorAll('.sf-certrow__media a')]
		.map((a) => ({ a: a, img: a.querySelector('img'), cert: certKey(a) }))
		.filter((it) => it.img && /\.(webp|jpe?g|png|gif|avif)([?#].*)?$/i.test(it.a.getAttribute('href') || ''));

	if (items.length < 1) return;

	const reduce = window.matchMedia ? matchMedia('(prefers-reduced-motion: reduce)') : { matches: false };

	let box = null;
	let big = null;
	let stage = null;
	let counter = null;
	let requestLink = null;
	let index = 0;
	let ratio = [8, 11];
	let opener = null;

	const FIT = 48; // breathing room kept on each side of the enlarged scan

	/* The stage is sized per certificate from its own ratio, so the enlarged
	   scan is as large as it can be without being stretched or letterboxed. A
	   shrink-to-fit stage would leave the photo's percentage width resolving
	   against an indefinite box. */
	const fitBox = () => {
		if (!box || !stage) return;
		const availW = Math.min(900, box.clientWidth - FIT);
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
		box.setAttribute('aria-label', 'Certificate viewer');
		box.innerHTML =
			'<div class="sf-lb__stage"><img class="sf-lb__img" alt="" decoding="async"></div>' +
			'<div class="sf-lb__bar">' +
				'<button class="sf-lb__btn sf-lb__btn--prev" type="button" aria-label="Previous certificate"><span aria-hidden="true">&#8249;</span></button>' +
				'<p class="sf-lb__count" aria-hidden="true"></p>' +
				'<button class="sf-lb__btn sf-lb__btn--next" type="button" aria-label="Next certificate"><span aria-hidden="true">&#8250;</span></button>' +
				'<button class="sf-lb__btn sf-lb__btn--close" type="button" aria-label="Close viewer"><span aria-hidden="true">&#10005;</span></button>' +
			'</div>' +
			// href is the no-JavaScript destination; show() fills in data-cert
			'<p class="sf-lb__request"><a class="sf-lb__request-link" href="/contact/#quote">Full certificate available upon request</a></p>';
		document.body.appendChild(box);

		big = box.querySelector('.sf-lb__img');
		stage = box.querySelector('.sf-lb__stage');
		counter = box.querySelector('.sf-lb__count');
		requestLink = box.querySelector('.sf-lb__request-link');

		window.addEventListener('resize', () => { if (!box.hidden) fitBox(); });

		box.querySelector('.sf-lb__btn--prev').addEventListener('click', () => step(-1));
		box.querySelector('.sf-lb__btn--next').addEventListener('click', () => step(1));
		box.querySelector('.sf-lb__btn--close').addEventListener('click', () => close());

		// a click anywhere but the scan and the controls is "on the backdrop"
		box.addEventListener('click', (e) => {
			if (e.target === big || e.target.closest('.sf-lb__btn')) return;
			/* The request line is meant to leave: the certificate dialog needs
			   the whole screen (this viewer is at 99999, the dialog at 10010) and
			   takes focus into its form, so the viewer closes without pulling
			   focus back to the thumbnail and the click falls through to the
			   dialog's own delegate. */
			if (e.target.closest('.sf-lb__request-link')) { close(true); return; }
			close();
		});

		document.addEventListener('keydown', (e) => {
			if (box.hidden) return;
			if (e.key === 'Escape') { e.preventDefault(); close(); }
			else if (e.key === 'ArrowLeft') { e.preventDefault(); step(-1); }
			else if (e.key === 'ArrowRight') { e.preventDefault(); step(1); }
			else if (e.key === 'Tab') {
				// buttons plus the request line, tiny trap so Tab cannot walk out
				const b = [...box.querySelectorAll('.sf-lb__btn, .sf-lb__request-link')];
				const first = b[0], last = b[b.length - 1];
				if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
				else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
			}
		});
	};

	/* the flip distance between a thumbnail and the enlarged scan */
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
		index = (i + items.length) % items.length;
		const thumb = items[index].img;

		// ratio and stage size come first: the flip and the scan must both
		// measure a box that is already at its final size
		const tw = +thumb.getAttribute('width') || 0;
		const th = +thumb.getAttribute('height') || 0;
		ratio = tw && th ? [tw, th] : [8, 11];
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
		counter.textContent = (index + 1) + ' / ' + items.length;
		// the request line always names the certificate that is on screen
		if (requestLink) requestLink.setAttribute('data-cert', items[index].cert);

		items.forEach((it) => it.a.classList.remove('is-current'));
		items[index].a.classList.add('is-current');

		if (frames) big.animate(frames, { duration: 260, easing: 'cubic-bezier(.22,.61,.36,1)' });
	};

	const step = (delta) => show(index + delta, true);

	const openAt = (i, trigger) => {
		if (!box) build();
		opener = trigger || null;
		big.removeAttribute('src');           // never flash the previous scan
		show(i, false);
		box.classList.remove('is-closing');
		box.hidden = false;
		document.documentElement.classList.add('sf-lb-open');
		box.getBoundingClientRect();          // force layout before the flip measures
		box.classList.add('is-open');
		show(i, true);
		box.querySelector('.sf-lb__btn--close').focus();
	};

	/* handOverFocus: the request line closes the viewer to hand the visit to the
	   certificate dialog, which moves focus itself — putting it back on the
	   thumbnail first would fight that. */
	const close = (handOverFocus) => {
		if (!box || box.hidden) return;
		const frames = flip(items[index].img, true);
		const done = () => {
			if (box.hidden) return;
			box.hidden = true;
			box.classList.remove('is-open', 'is-closing');
			document.documentElement.classList.remove('sf-lb-open');
			items.forEach((it) => it.a.classList.remove('is-current'));
			if (opener && !handOverFocus) opener.focus();
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

	items.forEach((it, i) => {
		it.a.setAttribute('aria-label',
			'View certificate ' + (i + 1) + ' of ' + items.length + (it.img.alt ? ': ' + it.img.alt : ''));
		it.a.addEventListener('click', (e) => {
			// a modifier key means "open in a new tab" — leave that alone
			if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0) return;
			e.preventDefault();
			openAt(i, it.a);
		});
	});
})();

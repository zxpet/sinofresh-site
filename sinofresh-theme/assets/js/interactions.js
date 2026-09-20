/* SINO FRESH — front-page motion: section reveal + stat count-up + stat-bar
   stagger. Opt-in from this file, so no-JS / reduced-motion visitors get the
   plain page (never a section stuck at opacity 0). Nothing here listens to
   scroll. */
(() => {
	if (!IntersectionObserver || matchMedia('(prefers-reduced-motion: reduce)').matches) return;

	// One-shot observer.
	const once = (nodes, options, hit) => {
		const io = new IntersectionObserver((entries) => {
			entries.forEach((e) => {
				if (e.isIntersecting) {
					io.unobserve(e.target);
					hit(e.target);
				}
			});
		}, options);
		nodes.forEach((n) => io.observe(n));
	};

	// Desktop only, and only below the fold: the hero holds the LCP element.
	if (matchMedia('(min-width: 768px)').matches) {
		const fold = innerHeight * 0.9;
		const pending = [...document.querySelectorAll('.wp-site-blocks > .wp-block-group')]
			.filter((el) => el.getBoundingClientRect().top > fold);
		if (pending.length) {
			document.documentElement.classList.add('sf-motion');
			pending.forEach((el) => el.classList.add('sf-pending'));
			once(pending, { rootMargin: '0px 0px -10% 0px' }, (el) => el.classList.remove('sf-pending'));
		}
	}

	// Count-up: only the digits move, the tail ("㎡" / "+" / "%") rides along.
	const nums = [...document.querySelectorAll('.sf-num')].map((el) => {
		const m = /[0-9][0-9,]*/.exec(el.textContent);
		const to = m && +m[0].replace(/,/g, '');
		if (!to) return false;
		el.field = { to, head: el.textContent.slice(0, m.index), tail: el.textContent.slice(m.index + m[0].length) };
		el.textContent = el.field.head + '0' + el.field.tail;
		return el;
	}).filter(Boolean);
	if (nums.length) once(nums, { threshold: 0.4 }, count);

	// Stat bar: the ten cells fade in 60ms apart. Skipped when the bar is
	// already on screen, so the first paint is never behind the animation.
	const bar = document.querySelector('.sf-statbar');
	if (bar && bar.getBoundingClientRect().top > innerHeight * 0.9) {
		const cells = [...bar.querySelectorAll('.sf-statbar__cell')];
		cells.forEach((el, i) => (el.style.transitionDelay = i * 60 + 'ms'));
		bar.classList.add('sf-stagger');
		once([bar], { rootMargin: '0px 0px -10% 0px' }, () => bar.classList.add('sf-stagger-in'));
	}

	function count(el) {
		const f = el.field;
		let start;
		requestAnimationFrame(function frame(now) {
			start = start ?? now;
			const p = Math.min((now - start) / 1500, 1);
			el.textContent = f.head + Math.round(f.to * (1 - (1 - p) ** 3)).toLocaleString('en-US') + f.tail;
			if (p < 1) requestAnimationFrame(frame);
		});
	}
})();


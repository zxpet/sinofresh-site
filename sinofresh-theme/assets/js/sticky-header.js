/*! SINO FRESH sticky header — a 100px sentinel at the page top is watched
    with IntersectionObserver (no scroll listeners); once it leaves the
    viewport (scrollY > 100) the nav gets .is-sticky. No library. */
(function () {
	'use strict';
	function init() {
		var sentinel = document.querySelector('.sf-header-sentinel');
		var header = document.querySelector('.sf-header');
		if (!sentinel || !header || !('IntersectionObserver' in window)) return;
		new IntersectionObserver(function (entries) {
			var stuck = !entries[0].isIntersecting;
			header.classList.toggle('is-sticky', stuck);
			/* reserve the bar's in-flow height so the page never jumps */
			header.closest('.wp-block-template-part')
				.classList.toggle('sf-header-stuck', stuck);
		}).observe(sentinel);
	}
	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', init);
	} else {
		init();
	}
})();

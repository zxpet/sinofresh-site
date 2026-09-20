/* Mobile nav enhancements (no library, ~1 kB).
   1) Submenu chevrons. WP 7.1's navigation block hides its submenu chevron
      inside the overlay and expands every submenu by default, so an
      eight-item catalogue nav opens taller than the phone and offers no way
      to close a section. We take the chevron over: on overlay open every
      submenu is marked closed, and tapping the chevron toggles it. The
      aria-expanded attribute drives the CSS in style.css (27c). WP's own
      data-wp-bind only ran at hydration, so the attribute stays ours.
   2) Footer nav columns. They ship with `open` so desktop keeps the
      always-open column (its summary is pointer-events: none there); on a
      phone the three columns start closed. Native <details> throughout, so
      every link stays in the DOM in both states. */
(function () {
	'use strict';

	function init() {
		var nav = document.querySelector('.sf-header .wp-block-navigation');
		if (nav) {
			var overlay = nav.querySelector('.wp-block-navigation__responsive-container');
			if (overlay) {
				/* tap on a chevron toggles its own submenu; the nav listener
				   runs before WP's document-level delegation, so stopPropagation
				   keeps the two from double-firing if WP's binding wakes up. */
				nav.addEventListener('click', function (e) {
					var btn = e.target.closest('.wp-block-navigation__submenu-icon');
					if (!btn || !overlay.classList.contains('is-menu-open')) return;
					e.preventDefault();
					e.stopPropagation();
					var open = btn.getAttribute('aria-expanded') === 'true';
					btn.setAttribute('aria-expanded', open ? 'false' : 'true');
				});

				if ('MutationObserver' in window) {
					new MutationObserver(function () {
						if (!overlay.classList.contains('is-menu-open')) return;
						var toggles = overlay.querySelectorAll(
							'.has-child > .wp-block-navigation__submenu-icon'
						);
						for (var i = 0; i < toggles.length; i++) {
							toggles[i].setAttribute('aria-expanded', 'false');
						}
					}).observe(overlay, { attributes: true, attributeFilter: ['class'] });
				}
			}
		}

		var cols = document.querySelectorAll('.sf-footcol');
		if (cols.length) {
			var phone = window.matchMedia('(max-width: 768px)');
			var sync = function () {
				for (var i = 0; i < cols.length; i++) {
					if (phone.matches) cols[i].removeAttribute('open');
					else cols[i].setAttribute('open', '');
				}
			};
			if (typeof phone.addEventListener === 'function') phone.addEventListener('change', sync);
			sync();
		}
	}

	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', init);
	} else {
		init();
	}
})();

/**
 * Standard Formulas reference buttons (K1).
 *
 * Loaded on the eight dosage pages (the card grid) and on a formula detail
 * page (the hero button). One click copies the formula name and shows a
 * lightweight toast.
 *
 * 1.2.0 — batch H6 deleted the two things batch H2b2 had already orphaned when
 * it removed configurator.js: the sessionStorage write
 * ('sinofresh_formula_' + slug), whose only reader was the configurator's PDF
 * summary, and the #configurator scroll, which no template has carried the id
 * for since. The button is copy-only everywhere now, and reduceMotion went with
 * the scroll — the scroll was its only reader, and .sf-toast already disables
 * its own transition under the same media query in style.css.
 *
 * data-form is still emitted on the markup. H6's declared scope was the dead
 * JS/CSS/PHP, not the attributes, so it stays until the next markup pass;
 * nothing in this file reads it any more.
 *
 * 1.1.0 — (history) the sessionStorage key was taken from data-form first,
 * because on a detail page the last path segment is the FORMULA slug: the
 * 1.0.0 heuristic ("last segment is the dosage form") wrote
 * sinofresh_formula_skin-coat-soft-chews, a key the configurator on
 * /products/soft-chews/ never found.
 *
 * No dependencies. ES5-style IIFE with a textarea copy fallback — the
 * conventions configurator.js used to share with it (deleted in batch H2b2).
 */
(function () {
	'use strict';

	/* --- Toast: one element, reused for every click ---------------------- */
	var toastEl = null;
	var toastTimer = null;

	function showToast(message) {
		if (!toastEl) {
			toastEl = document.createElement('div');
			toastEl.className = 'sf-toast';
			toastEl.setAttribute('role', 'status');
			toastEl.setAttribute('aria-live', 'polite');
			document.body.appendChild(toastEl);
		}
		toastEl.textContent = message;
		/* force a reflow so a repeat click restarts the transition */
		void toastEl.offsetWidth;
		toastEl.classList.add('is-visible');
		if (toastTimer) {
			clearTimeout(toastTimer);
		}
		toastTimer = setTimeout(function () {
			toastEl.classList.remove('is-visible');
		}, 2600);
	}

	/* --- Clipboard with textarea fallback (toc-nav.js copies the same way) ----- */
	function copyText(text, onDone, onFail) {
		if (navigator.clipboard && navigator.clipboard.writeText) {
			navigator.clipboard.writeText(text).then(onDone, onFail);
			return;
		}
		var ta = document.createElement('textarea');
		ta.value = text;
		ta.setAttribute('readonly', '');
		ta.style.position = 'fixed';
		ta.style.opacity = '0';
		document.body.appendChild(ta);
		ta.select();
		try {
			if (document.execCommand('copy')) {
				onDone();
			} else {
				onFail();
			}
		} catch (e) {
			onFail();
		}
		document.body.removeChild(ta);
	}

	/* --- Bind every formula CTA ------------------------------------------ */
	var buttons = document.querySelectorAll('.sf-formula__cta');
	Array.prototype.forEach.call(buttons, function (btn) {
		btn.addEventListener('click', function () {
			var name = btn.getAttribute('data-formula') || '';

			copyText(name, function () {
				showToast('Formula name copied. Paste it in your inquiry.');
			}, function () {
				/* copy unavailable — ask the user to type it instead */
				showToast('Copy unavailable — reference "' + name + '" in your inquiry.');
			});
		});
	});
})();

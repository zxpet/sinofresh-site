/**
 * Standard Formulas (dosage pages only, enqueued beside configurator.js).
 * CTA inside each <details>: copy the formula name, smooth-scroll to the
 * configurator (#configurator), and show a lightweight toast. Copy failure
 * degrades to scroll + a "reference it manually" toast.
 *
 * No dependencies. Additive — mirrors configurator.js conventions
 * (IIFE, ES5-style, reduceMotion respect, textarea fallback).
 */
(function () {
	'use strict';

	var reduceMotion = window.matchMedia
		? window.matchMedia('(prefers-reduced-motion: reduce)').matches
		: false;

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

	/* --- Clipboard with textarea fallback (same shape as configurator.js) */
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

			/* Persist the referenced formula per page so the configurator's
			   PDF summary can render it as the (Standard) formula base. */
			var segments = window.location.pathname.replace(/\/+$/, '').split('/');
			var slug = (segments[segments.length - 1] || '').toLowerCase();
			if (slug && /^[a-z0-9][a-z0-9-]*$/.test(slug)) {
				try {
					sessionStorage.setItem('sinofresh_formula_' + slug, name);
				} catch (e) {
					/* storage unavailable — PDF falls back to "to be developed" */
				}
			}

			copyText(name, function () {
				showToast('Formula name copied. Paste it in your inquiry.');
			}, function () {
				/* copy unavailable — still scroll, ask user to type it */
				showToast('Copy unavailable — reference "' + name + '" in your inquiry.');
			});

			var target = document.getElementById('configurator');
			if (target) {
				target.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'start' });
			}
		});
	});
})();

/**
 * Standard Formulas reference buttons (K1).
 *
 * Loaded on the eight dosage pages (the card grid) and on a formula detail
 * page (the hero button). One click copies the formula name, remembers it for
 * the configurator's PDF summary, and — when this page actually carries a
 * configurator — scrolls to it and shows a lightweight toast. Copy failure
 * degrades to scroll + a "reference it manually" toast.
 *
 * 1.1.0 — the sessionStorage key comes from data-form first. On a detail page
 * the last path segment is the FORMULA slug, so the 1.0.0 heuristic ("last
 * segment is the dosage form") wrote sinofresh_formula_skin-coat-soft-chews
 * and the configurator on /products/soft-chews/ never found it. data-form
 * carries the dosage form slug, which is the key configurator.js reads back.
 * The scroll is skipped entirely when there is no #configurator (detail page),
 * where the button's job is copy-only.
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

			/* Persist the referenced formula per dosage form so the
			   configurator's PDF summary can render it as the (Standard)
			   formula base. data-form wins: on a detail page the URL's last
			   segment is the formula slug, not the dosage form, so the old
			   path heuristic produced a key the configurator never reads. */
			var slug = (btn.getAttribute('data-form') || '').toLowerCase();
			if (!slug) {
				var segments = window.location.pathname.replace(/\/+$/, '').split('/');
				slug = (segments[segments.length - 1] || '').toLowerCase();
			}
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

			/* Detail pages carry no configurator: the button is copy-only
			   there, and the scroll is skipped rather than aimed at nothing. */
			var target = document.getElementById('configurator');
			if (target) {
				target.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'start' });
			}
		});
	});
})();

/**
 * Dosage-form filter for the formula archive (templates/archive-sf_formula.html).
 *
 * Loaded on /formulas/ only. All 21 cards are in the DOM and visible; pressing
 * a chip narrows them in the browser by adding .is-sf-off to the cards that
 * fall outside the selected dosage form. Nothing is fetched and nothing is
 * re-rendered, so the page works as a list first and as a filter second.
 *
 * Class, not hidden attribute: .sf-fcard is display:flex, and an author
 * display rule beats the hidden attribute's UA style — the card would stay
 * painted. The hiding rule lives in style.css 37c.
 *
 * Without JavaScript the bar never appears at all: style.css hides
 * .sf-fchips-wrap under html:not(.sf-js), and the class is set by an inline
 * head script before the body paints. That is deliberately a "JS exists"
 * signal rather than "this script ran" — a visitor with scripting off reads
 * the plain 21-card list instead of nine buttons that do nothing. (Residual
 * case, accepted: scripting on but this file blocked by a cache or an
 * optimiser leaves the bar visible and inert.)
 *
 * The data source is data-sf-form on each .sf-fcard, written by
 * [sf_formula_grid]. No dependencies; mirrors the conventions of the sibling
 * scripts (IIFE, ES5 style, no framework).
 */
(function () {
	'use strict';

	var bar = document.querySelector('.sf-fchips');
	if (!bar) {
		return;
	}
	var wrap = bar.parentNode;

	/* Only cards that declare a form participate. Scoping to .sf-fgrid keeps
	   the filter away from any other card set a future template might add,
	   and the [data-sf-form] test means a stale cached grid — rendered before
	   sub-item 3 added the attribute — is left alone instead of being hidden
	   wholesale. */
	var cards = document.querySelectorAll('.sf-fgrid .sf-fcard[data-sf-form]');

	/* No cards, no filter: with nothing to narrow the nine buttons are dead
	   ends, so the strip steps aside rather than inviting a click. */
	if (!cards.length) {
		wrap.style.display = 'none';
		return;
	}

	var chips = bar.querySelectorAll('.sf-fchip');
	var countEl = wrap.querySelector('.sf-fchips-count');

	function formOf(card) {
		return card.getAttribute('data-sf-form') || '';
	}

	/* The chip a click landed on, walking up from the event target: the
	   handler is delegated to the group, so it also covers a chip whose inner
	   markup grows later. */
	function chipFrom(node) {
		while (node && node !== bar) {
			if (node.classList && node.classList.contains('sf-fchip')) {
				return node;
			}
			node = node.parentNode;
		}
		return null;
	}

	/* One state writer: cards, chip pressed state and the count always change
	   together, so they cannot drift out of step. */
	function apply(form) {
		var shown = 0;
		Array.prototype.forEach.call(cards, function (card) {
			var match = form === 'all' || formOf(card) === form;
			card.classList.toggle('is-sf-off', !match);
			if (match) {
				shown++;
			}
		});
		Array.prototype.forEach.call(chips, function (chip) {
			var on = (chip.getAttribute('data-sf-form') || 'all') === form;
			chip.classList.toggle('is-active', on);
			chip.setAttribute('aria-pressed', on ? 'true' : 'false');
		});
		if (countEl) {
			/* <span> of its own: the sentence around it stays one string. */
			countEl.textContent = String(shown);
		}
	}

	bar.addEventListener('click', function (event) {
		var chip = chipFrom(event.target);
		if (!chip) {
			return;
		}
		apply(chip.getAttribute('data-sf-form') || 'all');
	});
})();

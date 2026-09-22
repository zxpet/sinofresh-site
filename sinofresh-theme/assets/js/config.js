/*
 * SINO FRESH — the right column's configurator (batch H7d).
 *
 * The controls themselves are plain checkboxes and radios emitted by PHP, so
 * this file adds no behaviour a visitor needs: without it every option is still
 * clickable, every group still prints the record's own value as text, and the
 * four non-choice rows are still on the page. What it adds is the three things
 * a form cannot say in markup:
 *
 * 1. A live summary of what has been picked. The element is emitted empty and
 *    `hidden`, so the no-JS page makes no claim about a selection that does not
 *    exist yet.
 * 2. The selection's trip into the dialog. `inquiry.js` posts whatever the form
 *    carries; this file is what puts the choice in the form, as JSON in one
 *    hidden input, and mirrors it into the dialog's panel so the visitor sees
 *    the same list the sales desk will receive. Nothing picked means the input
 *    stays empty and the panel keeps the server-rendered specification — the
 *    dialog falls back to the product, which is what it did before this batch.
 * 3. On a phone, a full-screen drawer. Seven groups of options inline would
 *    push the price and the CTA off the first two screens, so below the
 *    breakpoint the list becomes a drawer behind one button. The button is
 *    created here, which is also why a visitor without this file is never shown
 *    a button that cannot open anything.
 *
 * The endpoint does not trust any of this: it validates every posted value
 * against the options it can derive from the post id and prints the labels
 * itself. A hand-crafted request can choose among the options the page already
 * offered and nothing else.
 */
(function () {
	'use strict';

	var PHONE = '(max-width: 768px)';

	function init() {
		var root = document.querySelector('[data-sf-config]');
		var list = root ? root.querySelector('.sf-fdetail-config__list') : null;
		if (!root || !list) {
			return;
		}
		var summary = root.querySelector('[data-sf-config-summary]');
		var note = root.querySelector('[data-sf-config-note]');
		var modal = document.querySelector('.sf-inquiry-modal');
		var form = modal ? modal.querySelector('.sf-inquiry-form') : null;
		var carrier = form ? form.querySelector('input[name="config"]') : null;
		var panelRows = modal ? modal.querySelector('.sf-inquiry-modal__rows') : null;

		root.classList.add('sf-fdetail-config--js');

		var groups = [].slice.call(root.querySelectorAll('[data-sf-config-group]'));
		/* Kept once, the first time the dialog's panel is overwritten: re-reading
		   it after that would capture the choice instead of the product. Declared
		   here rather than beside its first use, because refresh() runs before
		   that line and would otherwise read an unassigned variable. */
		var serverRows = [];

		/* ------------------------------------------------------------- state */

		/* Read the ticked inputs back out of the DOM, in group order. The DOM is
		   the state: a parallel object would be a second copy to keep in step,
		   and the first thing to go wrong after a back-navigation. */
		function selection() {
			var out = [];
			groups.forEach(function (group) {
				var key = group.getAttribute('data-sf-config-group');
				var labelEl = group.querySelector('.sf-fdetail-config__label');
				var label = labelEl ? labelEl.textContent.trim() : key;
				var picked = [];
				[].slice.call(group.querySelectorAll('.sf-fdetail-config__input')).forEach(function (input) {
					var opt = input.closest('.sf-fdetail-config__opt');
					if (!opt) {
						return;
					}
					opt.classList.toggle('is-on', input.checked);
					if (!input.checked) {
						return;
					}
					var text = opt.querySelector('.sf-fdetail-config__text');
					picked.push({
						value: input.value,
						label: text ? text.textContent.trim() : input.value,
						note: (function () {
							var n = opt.querySelector('.sf-fdetail-config__note');
							return n ? n.textContent.trim() : '';
						})()
					});
				});
				if (picked.length) {
					out.push({ key: key, label: label, picked: picked });
				}
			});
			return out;
		}

		/* The carrier is keyed the way the endpoint reads it: one key per group,
		   an array of values for multi and a single value for single. Sending the
		   labels as well would be sending the server its own words back. */
		function carrierValue(sel) {
			var payload = {};
			sel.forEach(function (group) {
				var values = group.picked.map(function (p) {
					return p.value;
				});
				payload[group.key] = values.length > 1 ? values : values[0];
			});
			return JSON.stringify(payload);
		}

		function summaryText(sel) {
			return sel.map(function (group) {
				var parts = group.picked.map(function (p) {
					return p.label + (p.note ? ' (' + p.note + ')' : '');
				});
				return group.label + ': ' + parts.join(', ');
			}).join(' · ');
		}

		function refresh() {
			var sel = selection();
			var text = summaryText(sel);
			if (summary) {
				summary.textContent = text;
				summary.hidden = text === '';
			}
			if (note) {
				note.hidden = text === '';
			}
			if (carrier) {
				carrier.value = sel.length ? carrierValue(sel) : '';
			}
			/* The dialog's panel is the server's rendering of the product. When
			   the visitor has chosen something, the panel is replaced by the
			   choice — otherwise it is left exactly as the server printed it,
			   which is the fallback the brief asks for. The rows are rebuilt as
			   text, not copied, so nothing from the DOM is re-inserted as HTML. */
			if (panelRows) {
				if (!sel.length) {
					if (panelRows.dataset.sfOwn !== undefined) {
						panelRows.replaceChildren.apply(panelRows, serverRows);
						delete panelRows.dataset.sfOwn;
					}
				} else {
					if (panelRows.dataset.sfOwn === undefined) {
						serverRows = [].slice.call(panelRows.childNodes);
					}
					var frag = document.createDocumentFragment();
					sel.forEach(function (group) {
						var dt = document.createElement('dt');
						dt.className = 'sf-inquiry-modal__term';
						dt.textContent = group.label;
						var dd = document.createElement('dd');
						dd.className = 'sf-inquiry-modal__value';
						dd.textContent = group.picked.map(function (p) {
							return p.label + (p.note ? ' (' + p.note + ')' : '');
						}).join(', ');
						frag.appendChild(dt);
						frag.appendChild(dd);
					});
					panelRows.replaceChildren(frag);
					panelRows.dataset.sfOwn = '1';
				}
			}
		}

		/* Kept once, the first time the panel is overwritten: re-reading it
		   after that would capture the choice instead of the product. */

		root.addEventListener('change', refresh);
		refresh();

		/* ------------------------------------------------------------- drawer */

		var openBtn = document.createElement('button');
		openBtn.type = 'button';
		openBtn.className = 'sf-fdetail-config__open';
		openBtn.textContent = 'Build your specification';
		openBtn.setAttribute('aria-expanded', 'false');
		root.insertBefore(openBtn, list);

		var closeBtn = document.createElement('button');
		closeBtn.type = 'button';
		closeBtn.className = 'sf-fdetail-config__close';
		closeBtn.textContent = 'Done';
		list.appendChild(closeBtn);

		function setOpen(open) {
			root.classList.toggle('sf-fdetail-config--open', open);
			/* The drawer is fixed over the page, so without this the page
			   scrolls behind it and the visitor loses their place. */
			document.body.classList.toggle('sf-config-lock', open);
			openBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
			if (open) {
				closeBtn.focus({ preventScroll: true });
			} else {
				openBtn.focus({ preventScroll: true });
			}
		}
		openBtn.addEventListener('click', function () {
			setOpen(true);
		});
		closeBtn.addEventListener('click', function () {
			setOpen(false);
		});
		document.addEventListener('keydown', function (event) {
			/* One Escape, one thing: inquiry.js closes the dialog on the same
			   key, and a drawer that also snapped shut behind it would look
			   like the second half of a single animation. */
			if (event.key !== 'Escape' || !root.classList.contains('sf-fdetail-config--open')) {
				return;
			}
			if (modal && !modal.hidden) {
				return;
			}
			setOpen(false);
		});
		/* A rotation out of the phone breakpoint while the drawer is open would
		   leave the list in its fixed position with no way back, because the
		   button that closes it is only drawn on a phone. */
		window.addEventListener('resize', function () {
			if (!window.matchMedia(PHONE).matches && root.classList.contains('sf-fdetail-config--open')) {
				setOpen(false);
			}
		});
	}

	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', init);
	} else {
		init();
	}
})();

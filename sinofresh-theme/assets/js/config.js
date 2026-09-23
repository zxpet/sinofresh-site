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
 * 3. On a phone, the fold (batch H7h). Below 480px the list stands inline and
 *    the groups past the fourth wait behind one "View all specs" button — the
 *    ladder and the three groups a buyer asks first stay on the page (batch
 *    H8a moved the cut from the fourth group to the fifth, because H7l had
 *    moved the price to the head of the column and the price is not something
 *    to fold away). The expanded state is kept in sessionStorage, so a visitor
 *    who unfolded once stays unfolded.
 * 4. The Custom box (batch H8a). A group may end in a Custom pick; the text
 *    box under the group ships hidden and is revealed by that pick, and what
 *    it holds is what the inquiry posts — "{text} (custom)".
 * 5. The sliding rows (batch H8a). Shape and Container are one row that
 *    scrolls instead of two that wrap; on a pointer device the rail gets a
 *    pair of arrows, because a scrollbar with no thumb is not an affordance.
 *    The H7d drawer it replaces keeps running at 481-768px, where seven
 *    inline groups still outrun a tablet's viewport; at the phone width the
 *    drawer button is never drawn, so the two interactions never coexist.
 * 4. The sample request (batch H7i, 1.3.0). "Get Sample" under the price
 *    ladder opens the same dialog the Inquiry buttons do; this file only puts
 *    the sentence in the Message field, and only into an empty one. A sample
 *    request is a different errand from a quote, and the sales desk should not
 *    have to infer it from a product name and a price tier.
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

		/* ------------------------------------------ the sample request (H7i) */

		/* The button already opens the dialog: it carries data-sf-inquiry-open,
		   which inquiry.js binds by itself. What is added here is the sentence.
		   Written only into an empty field — a visitor who has typed something
		   keeps it — and never after the form was already submitted, because
		   inquiry.js clears the form on success. */
		var message = form ? form.querySelector('textarea[name="message"]') : null;
		[].slice.call(document.querySelectorAll('[data-sf-inquiry-sample]')).forEach(function (el) {
			el.addEventListener('click', function () {
				if (!message || message.value.trim() !== '') {
					return;
				}
				var title = document.querySelector('.sf-fdetail2__title');
				var price = el.getAttribute('data-sf-inquiry-sample') || '';
				message.value = 'I would like to request a sample'
					+ (title ? ' of ' + title.textContent.trim() : '')
					+ (price ? ' (' + price + ' per sample)' : '') + '.';
			});
		});

		var groups = [].slice.call(root.querySelectorAll('[data-sf-config-group]'));
		/* Kept once, the first time the dialog's panel is overwritten: re-reading
		   it after that would capture the choice instead of the product. Declared
		   here rather than beside its first use, because refresh() runs before
		   that line and would otherwise read an unassigned variable. */
		var serverRows = [];

		/* ------------------------------------------------------------- state */

		function customText(key) {
			var box = root.querySelector('[data-sf-config-custom-input="' + key + '"]');
			return box ? box.value.trim() : '';
		}

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
					/* H7g: an image-style option with no upload carries its name
					   inside the dashed placeholder box instead of a text span,
					   so the label is read from there when the span is absent. */
					var emptyLabel = opt.querySelector('.sf-fdetail-config__empty-label');
					/* H8a — a Custom pick with text in its box answers with that
					   text, not with the word Custom. Read here rather than in the
					   carrier so the summary line, the dialog's panel and the
					   posted value all say the same thing by construction. */
					var own = opt.hasAttribute('data-sf-config-custom') ? customText(key) : '';
					var note = opt.querySelector('.sf-fdetail-config__note');
					picked.push({
						value: own !== '' ? own + ' (custom)' : input.value,
						label: own !== '' ? own + ' (custom)' : (text ? text.textContent.trim()
							: (emptyLabel ? emptyLabel.textContent.trim() : input.value)),
						note: own !== '' ? '' : (note ? note.textContent.trim() : '')
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

		/* -------------------------------------------------- the fold (H7h) */

		/* The button is created here for the reason the drawer's was: a visitor
		   without this file must never be shown a control that does nothing.
		   CSS draws it only at <=480px and only under --js, so on a desktop it
		   is styled out of existence even though the node exists. */
		var FOLD_KEY = 'sf-config-fold';
		var fold = document.createElement('button');
		fold.type = 'button';
		fold.className = 'sf-fdetail-config__fold';
		fold.setAttribute('aria-controls', list.id || 'sf-config-list');
		if (!list.id) {
			list.id = 'sf-config-list';
		}
		list.classList.add('sf-config-folded');
		list.parentNode.insertBefore(fold, list.nextSibling);

		function setFold(open) {
			list.classList.toggle('sf-config-folded', !open);
			fold.setAttribute('aria-expanded', open ? 'true' : 'false');
			fold.textContent = open ? 'Show fewer specs ▴' : 'View all specs ▾';
			try {
				sessionStorage.setItem(FOLD_KEY, open ? 'open' : 'folded');
			} catch (e) { /* private mode: the state just is not kept */ }
		}
		fold.addEventListener('click', function () {
			setFold(list.classList.contains('sf-config-folded'));
		});
		/* A visitor who unfolded earlier in this session stays unfolded — the
		   brief's "保持展开". Everything else starts folded: the first four
		   groups are the summary, the button is the rest. */
		var saved = null;
		try {
			saved = sessionStorage.getItem(FOLD_KEY);
		} catch (e) { /* as above */ }
		setFold(saved === 'open');

		/* ------------------------------------------------- the Custom box (H8a) */

		/* The box ships `hidden` in the markup and is revealed by the pick that
		   owns it. Visibility is derived from the DOM like everything else
		   here, so a back-navigation that restores a tick also restores the
		   box. Focus moves only when that pick is the thing that changed: the
		   change listener below runs on every tick, and grabbing focus on each
		   one would pull the keyboard into a text field the visitor never
		   asked for. */
		function syncCustom(focus) {
			groups.forEach(function (group) {
				var key = group.getAttribute('data-sf-config-group');
				var box = root.querySelector('[data-sf-config-custom-for="' + key + '"]');
				if (!box) {
					return;
				}
				var pick = group.querySelector('.sf-fdetail-config__opt[data-sf-config-custom] .sf-fdetail-config__input');
				var on = !!(pick && pick.checked);
				box.hidden = !on;
				if (on && focus) {
					var input = box.querySelector('[data-sf-config-custom-input]');
					if (input && input.value === '') {
						input.focus();
					}
				}
			});
		}
		root.addEventListener('change', function (e) {
			var t = e.target;
			syncCustom(!!(t && t.closest && t.closest('[data-sf-config-custom]')));
		});
		syncCustom(false);

		/* ------------------------------------------------- the rails (H8a) */

		/* Shape and Container are one scrolling row rather than two wrapped
		   ones. On a pointer device that is a hidden affordance — a track with
		   no thumb is a scrollbar nobody notices — so the rail gets a pair of
		   arrows. They are built only when the row actually overflows, and only
		   here: without this file the row is still a plain scroll container
		   (swipe on touch, drag the track with a pointer), which is why the
		   markup carries the containment and this file only carries the
		   convenience. */
		function railArrow(rail, row, dir, glyph, label) {
			var b = document.createElement('button');
			b.type = 'button';
			b.className = 'sf-fdetail-config__arrow sf-fdetail-config__arrow--' + dir;
			b.textContent = glyph;
			b.setAttribute('aria-label', label);
			b.addEventListener('click', function () {
				row.scrollLeft += (dir === 'next' ? 1 : -1) * row.clientWidth * 0.8;
			});
			rail.appendChild(b);
			return b;
		}
		['shape', 'container'].forEach(function (key) {
			var group = root.querySelector('[data-sf-config-group="' + key + '"]');
			var row = group ? group.querySelector('.sf-fdetail-config__options') : null;
			if (!row) {
				return;
			}
			var rail = document.createElement('div');
			rail.className = 'sf-fdetail-config__rail';
			row.parentNode.insertBefore(rail, row);
			rail.appendChild(row);

			var prev = railArrow(rail, row, 'prev', '\u2039', 'Previous options');
			var next = railArrow(rail, row, 'next', '\u203a', 'More options');

			function sync() {
				var room = row.scrollWidth - row.clientWidth;
				rail.classList.toggle('sf-fdetail-config__rail--scrolls', room > 4);
				prev.disabled = row.scrollLeft <= 1;
				next.disabled = row.scrollLeft >= room - 1;
			}
			row.addEventListener('scroll', sync, { passive: true });
			window.addEventListener('resize', sync);
			sync();
		});

		/* --------------------------------------------- gallery preview (H7g) */

		/* The main image area's three modes. Default is the product gallery;
		   choosing a Shape or Container thumbnail overlays the stage with that
		   library image; clicking any of the gallery's own controls — a
		   thumbnail or the Photos/Video switch — hides the overlay and hands
		   the stage back. The layer adds a node, it does not touch a slide, so
		   formula-gallery.js keeps working unchanged. */
		var stage = document.querySelector('[data-gallery]');
		var preview = stage ? stage.querySelector('[data-sf-gallery-preview]') : null;

		function hidePreview() {
			if (preview && !preview.hidden) {
				preview.hidden = true;
			}
		}

		function showPreview(input) {
			if (!preview) {
				return;
			}
			var opt = input.closest('.sf-fdetail-config__opt');
			var img = opt ? opt.querySelector('img.sf-fdetail-config__img') : null;
			/* An empty library slot has no large image to show: the main area
			   keeps the product gallery. A stretched dashed placeholder where
			   a product photo should be would be a claim about a picture the
			   site does not have. */
			if (!img) {
				hidePreview();
				return;
			}
			var labelEl = opt.querySelector('.sf-fdetail-config__text')
				|| opt.querySelector('.sf-fdetail-config__empty-label');
			var big = document.createElement('img');
			big.src = img.currentSrc || img.src;
			big.alt = labelEl ? labelEl.textContent.trim() : input.value;
			preview.replaceChildren(big);
			preview.hidden = false;
		}

		root.addEventListener('change', function (event) {
			var input = event.target;
			if (!input.matches || !input.matches('.sf-fdetail-config__input[type="radio"]') || !input.checked) {
				return;
			}
			var group = input.closest('[data-sf-config-group]');
			var key = group ? group.getAttribute('data-sf-config-group') : '';
			if (key === 'shape' || key === 'container') {
				showPreview(input);
			}
		});
		if (stage) {
			stage.addEventListener('click', function (event) {
				if (preview && !preview.hidden && !preview.contains(event.target)) {
					hidePreview();
				}
			});
		}

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

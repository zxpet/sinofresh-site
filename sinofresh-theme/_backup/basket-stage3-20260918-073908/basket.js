/*
 * SINO FRESH — Cross-page Inquiry Basket.
 * Stage 1: storage API (window.SFBasket), key sinofresh_basket.
 *   Item shape: { slug, title, summary, formula, addedAt }.
 * Stage 2: global UI — header bag button + count badge, right slide-in
 *   drawer (full width on phones) with the item list, per-item remove,
 *   Clear All (confirm) and Submit Inquiry (jumps to /contact/; the form
 *   fill-in is stage 3). "Download Basket PDF" is a placeholder until
 *   stage 4 wires the multi-item PDF.
 * Every mutation dispatches "sf:basket-change" on document with
 * { count, items } in detail; the UI re-renders from that event, so any
 * future writer (e.g. a quick-add button) updates the badge for free.
 */
(function () {
	'use strict';

	var KEY = 'sinofresh_basket';

	function read() {
		try {
			var raw = sessionStorage.getItem(KEY);
			var parsed = raw ? JSON.parse(raw) : [];
			return Array.isArray(parsed) ? parsed : [];
		} catch (e) {
			return [];
		}
	}

	function save(items) {
		try {
			/* Normalise empty: drop the key instead of storing "[]" so
			   "sessionStorage has no basket key" always means "basket empty". */
			if (items.length) {
				sessionStorage.setItem(KEY, JSON.stringify(items));
			} else {
				sessionStorage.removeItem(KEY);
			}
		} catch (e) {
			/* storage unavailable (private mode) — fail silently */
		}
		document.dispatchEvent(new CustomEvent('sf:basket-change', {
			detail: { count: items.length, items: items }
		}));
	}

	window.SFBasket = {
		/**
		 * Add an item (or replace the entry with the same slug).
		 * addedAt is stamped here when missing. Returns
		 * { updated: bool, count: n } — updated=true when an existing
		 * entry for the slug was replaced.
		 */
		add: function (item) {
			if (!item || !item.slug) {
				return { updated: false, count: this.count() };
			}
			var items = read();
			var updated = false;
			for (var i = 0; i < items.length; i++) {
				if (items[i].slug === item.slug) {
					item.addedAt = items[i].addedAt || item.addedAt || new Date().toISOString();
					items[i] = item;
					updated = true;
					break;
				}
			}
			if (!updated) {
				if (!item.addedAt) {
					item.addedAt = new Date().toISOString();
				}
				items.push(item);
			}
			save(items);
			return { updated: updated, count: items.length };
		},
		remove: function (slug) {
			var items = read();
			var next = items.filter(function (it) { return it.slug !== slug; });
			if (next.length !== items.length) {
				save(next);
			}
			return next.length !== items.length;
		},
		clear: function () {
			var had = read().length > 0;
			try {
				sessionStorage.removeItem(KEY);
			} catch (e) {}
			if (had) {
				document.dispatchEvent(new CustomEvent('sf:basket-change', {
					detail: { count: 0, items: [] }
				}));
			}
			return had;
		},
		getAll: function () {
			return read().slice();
		},
		count: function () {
			return read().length;
		}
	};

	/* === UI: header badge + drawer (stage 2) ============================== */
	var EMPTY_TEXT = "No items yet. Configure a dosage form and click 'Add to Inquiry'.";

	function toast(message) {
		var el = document.querySelector('.sf-toast');
		if (!el) {
			el = document.createElement('div');
			el.className = 'sf-toast';
			el.setAttribute('role', 'status');
			el.setAttribute('aria-live', 'polite');
			document.body.appendChild(el);
		}
		el.textContent = message;
		void el.offsetWidth;
		el.classList.add('is-visible');
		setTimeout(function () {
			el.classList.remove('is-visible');
		}, 2600);
	}

	function renderList(content, emptyClass) {
		var items = read();
		content.innerHTML = '';
		if (!items.length) {
			var empty = document.createElement('p');
			empty.className = emptyClass;
			empty.textContent = EMPTY_TEXT;
			content.appendChild(empty);
			return;
		}
		items.forEach(function (item) {
			var row = document.createElement('div');
			row.className = 'sf-basket-drawer__item';

			var info = document.createElement('div');
			info.className = 'sf-basket-drawer__item-info';

			var title = document.createElement('p');
			title.className = 'sf-basket-drawer__item-title';
			title.textContent = item.title || item.slug;

			var summary = document.createElement('p');
			summary.className = 'sf-basket-drawer__item-summary';
			summary.textContent = item.summary || '';

			info.appendChild(title);
			info.appendChild(summary);

			var rm = document.createElement('button');
			rm.type = 'button';
			rm.className = 'sf-basket-drawer__item-remove';
			rm.setAttribute('aria-label', 'Remove ' + (item.title || item.slug) + ' from basket');
			rm.innerHTML = '&times;';
			rm.addEventListener('click', function () {
				window.SFBasket.remove(item.slug);
			});

			row.appendChild(info);
			row.appendChild(rm);
			content.appendChild(row);
		});
	}

	function initUI() {
		var btn = document.querySelector('.sf-basket-btn');
		var drawer = document.querySelector('.sf-basket-drawer');
		if (!btn || !drawer) {
			return;
		}
		var badge = btn.querySelector('.sf-basket-btn__badge');
		var overlay = document.querySelector('.sf-basket-overlay');
		var content = drawer.querySelector('.sf-basket-drawer__content');
		var closeBtn = drawer.querySelector('.sf-basket-drawer__close');
		var clearBtn = drawer.querySelector('.sf-basket-drawer__clear');
		var pdfBtn = drawer.querySelector('.sf-basket-drawer__pdf');
		var hideTimer = null;

		function syncBadge(count) {
			if (!badge) {
				return;
			}
			badge.hidden = count === 0;
			badge.textContent = count > 99 ? '99+' : String(count);
		}

		/* SFBasket.render() — public hook so external code can force a redraw. */
		window.SFBasket.render = function () {
			renderList(content, 'sf-basket-drawer__empty');
			syncBadge(read().length);
		};
		window.SFBasket.openDrawer = function () {
			if (hideTimer) {
				clearTimeout(hideTimer);
				hideTimer = null;
			}
			window.SFBasket.render();
			overlay.hidden = false;
			drawer.hidden = false;
			requestAnimationFrame(function () {
				overlay.classList.add('is-open');
				drawer.classList.add('is-open');
			});
			document.body.classList.add('sf-basket-lock');
			if (closeBtn) {
				closeBtn.focus();
			}
		};
		window.SFBasket.closeDrawer = function () {
			overlay.classList.remove('is-open');
			drawer.classList.remove('is-open');
			document.body.classList.remove('sf-basket-lock');
			hideTimer = setTimeout(function () {
				overlay.hidden = true;
				drawer.hidden = true;
				hideTimer = null;
			}, 300);
		};

		/* Badge + list follow every mutation, wherever it comes from. */
		document.addEventListener('sf:basket-change', function () {
			window.SFBasket.render();
		});

		btn.addEventListener('click', function () {
			if (drawer.classList.contains('is-open')) {
				window.SFBasket.closeDrawer();
			} else {
				window.SFBasket.openDrawer();
			}
		});
		if (overlay) {
			overlay.addEventListener('click', window.SFBasket.closeDrawer);
		}
		if (closeBtn) {
			closeBtn.addEventListener('click', window.SFBasket.closeDrawer);
		}
		document.addEventListener('keydown', function (event) {
			if (event.key === 'Escape' && drawer.classList.contains('is-open')) {
				window.SFBasket.closeDrawer();
			}
		});

		if (clearBtn) {
			clearBtn.addEventListener('click', function () {
				if (!read().length) {
					return;
				}
				if (window.confirm('Remove all items from your inquiry basket?')) {
					window.SFBasket.clear();
				}
			});
		}

		/* Stage 4 placeholder: visible now, wired to the multi-item PDF later. */
		if (pdfBtn) {
			pdfBtn.addEventListener('click', function () {
				if (!read().length) {
					return;
				}
				toast('Basket PDF is coming soon');
			});
		}

		/* Initial paint (badge on page load with a persisted basket). */
		window.SFBasket.render();
	}

	initUI();
})();

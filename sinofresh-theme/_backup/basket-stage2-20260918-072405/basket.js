/*
 * SINO FRESH — Cross-page Inquiry Basket (stage 1: storage + API).
 * Loaded on the 8 dosage form pages; stage 2 (drawer / badge / submit
 * integration) reuses this global. Storage key: sinofresh_basket.
 * Shape of one item: { slug, title, summary, formula, addedAt }.
 * Every mutation dispatches "sf:basket-change" on document with
 * { count, items } in detail, so badge/listen code stays decoupled.
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
			sessionStorage.setItem(KEY, JSON.stringify(items));
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
})();

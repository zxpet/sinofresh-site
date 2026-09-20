/*
 * SINO FRESH — Cross-page Inquiry Basket.
 * Stage 1: storage API (window.SFBasket), key sinofresh_basket.
 *   Item shape: { slug, title, summary, formula, addedAt }.
 * Stage 2: global UI — header bag button + count badge, right slide-in
 *   drawer (full width on phones) with the item list, per-item remove,
 *   Clear All (confirm) and Submit Inquiry.
 * Stage 4: "Download Basket PDF" posts the whole basket to the shared
 *   config-pdf endpoint; the server renders every dosage form under one
 *   SF reference, with an optional email copy (cc sales@zxpet.com).
 * Stage 3: Submit Inquiry snapshots the basket (sinofresh_basket_pending)
 *   and jumps to /contact/?from=basket; there GF Form 2 is pre-filled
 *   (field 12 multi-item summary, Notes item list, field 7 untouched) with
 *   a dismissible notice; a successful ajax submission clears the basket.
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

	/* === Stage 3: contact-page pre-fill + submit flow =====================
	   Drawer "Submit Inquiry": empty-basket guard → snapshot the basket into
	   sinofresh_basket_pending → jump to /contact/?from=basket. On arrival
	   the GF Form 2 fields are filled from the live basket (pending snapshot
	   as fallback): field 12 gets the numbered multi-item summary (field 7
	   stays untouched per decision B), Notes gets the item list, and a
	   dismissible notice is injected above the form. A successful GF (ajax)
	   submission then clears the submitted basket. */

	function basketItemsForFill() {
		/* Live basket first; fall back to the pending snapshot (e.g. the
		   basket was mutated between the drawer click and page load). */
		var items = read();
		if (items.length) {
			return items;
		}
		try {
			var pending = JSON.parse(sessionStorage.getItem('sinofresh_basket_pending') || 'null');
			if (pending && Array.isArray(pending.items) && pending.items.length) {
				return pending.items;
			}
		} catch (e) {}
		return [];
	}

	var basketFilledOnPage = false;

	function fillFromBasket() {
		var items = basketItemsForFill();
		if (!items.length) {
			return false;
		}
		var f12 = document.querySelector('input[name="input_12"]');
		var f10 = document.querySelector('textarea[name="input_10"]');
		if (!f12 && !f10) {
			return false;
		}

		/* Field 12: "[1] Dosage Form: Soft Chews | Shape: Bone | ..." per
		   item. Append when the field already carries content. */
		var summary = items.map(function (item, index) {
			return '[' + (index + 1) + '] ' + (item.summary || item.title || item.slug);
		}).join('\n');
		if (f12) {
			f12.value = f12.value ? f12.value + '\n' + summary : summary;
		}

		/* Field 10 (Notes): item list, formula reference in brackets. */
		if (f10) {
			var lines = items.map(function (item) {
				return '- ' + (item.title || item.slug) + (item.formula ? ' (' + item.formula + ')' : '');
			});
			var note = 'Items in inquiry basket:\n' + lines.join('\n')
				+ '\n(Please add any other requirements here.)';
			f10.value = f10.value ? f10.value + '\n\n' + note : note;
		}

		basketFilledOnPage = true;

		/* Dismissible notice above the form wrapper. */
		var wrapper = document.querySelector('.gform_wrapper');
		if (wrapper && !document.querySelector('.sf-basket-notice')) {
			var notice = document.createElement('div');
			notice.className = 'sf-basket-notice';
			notice.setAttribute('role', 'status');
			var text = document.createElement('p');
			text.className = 'sf-basket-notice__text';
			text.textContent = items.length > 1
				? items.length + ' items from your inquiry basket have been pre-filled below.'
				: '1 item from your inquiry basket has been pre-filled below.';
			var close = document.createElement('button');
			close.type = 'button';
			close.className = 'sf-basket-notice__close';
			close.setAttribute('aria-label', 'Dismiss notice');
			close.innerHTML = '&times;';
			close.addEventListener('click', function () {
				notice.remove();
			});
			notice.appendChild(text);
			notice.appendChild(close);
			wrapper.parentNode.insertBefore(notice, wrapper);
		}

		/* Consume the snapshot so a reload of /contact/?from=basket cannot
		   double-append the same items. */
		try {
			sessionStorage.removeItem('sinofresh_basket_pending');
		} catch (e) {}
		return true;
	}

	/* Successful GF submission (ajax:true → gform_confirmation_loaded).
	   Bound via jQuery when available (also after DOMContentLoaded, since
	   GF's jQuery may load after this footer script). Only clears the basket
	   when THIS page view pre-filled it — an unrelated quote form submit
	   must not wipe a basket the visitor is still building. */
	function bindConfirmationClear() {
		var handler = function () {
			try {
				sessionStorage.removeItem('sinofresh_basket_pending');
			} catch (e) {}
			if (basketFilledOnPage && read().length) {
				window.SFBasket.clear();
				toast('Your inquiry basket has been submitted');
			}
		};
		var bind = function () {
			if (window.jQuery) {
				window.jQuery(document).on('gform_confirmation_loaded', handler);
			}
		};
		bind();
		document.addEventListener('DOMContentLoaded', bind);
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

		/* Stage 4: basket PDF — POST every item to the shared config-pdf
		   endpoint; the server renders all dosage forms under ONE SF
		   reference (summary page + one page per item + company page). */
		var mailRow = drawer.querySelector('.sf-basket-drawer__mail');

		function requestBasketPdf(email, onDone) {
			var items = read().map(function (it) {
				return {
					slug: it.slug,
					title: it.title || '',
					summary: it.summary || '',
					formula: it.formula || ''
				};
			});
			return fetch('/wp-json/sinofresh/v1/config-pdf', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ basket: items, email: email || '' })
			}).then(function (res) {
				if (email) {
					return res.json().then(function (j) {
						return { json: j, ok: res.ok };
					});
				}
				var disp = res.headers.get('Content-Disposition') || '';
				var nameMatch = disp.match(/filename="([^"]+)"/);
				if (res.ok && /pdf/.test(res.headers.get('Content-Type') || '')) {
					return res.blob().then(function (blob) {
						var url = URL.createObjectURL(blob);
						var a = document.createElement('a');
						a.href = url;
						a.download = nameMatch ? nameMatch[1] : 'SINO-FRESH-Basket.pdf';
						document.body.appendChild(a);
						a.click();
						a.remove();
						setTimeout(function () {
							URL.revokeObjectURL(url);
						}, 4000);
						return { downloaded: true };
					});
				}
				return res.json().then(function (j) {
					return { json: j, ok: res.ok };
				});
			}).catch(function () {
				return { networkError: true };
			}).then(function (result) {
				if (onDone) {
					onDone(result);
				}
				return result;
			});
		}

		if (pdfBtn) {
			var PDF_LABEL = pdfBtn.textContent;
			pdfBtn.addEventListener('click', function () {
				if (!read().length) {
					return;
				}
				pdfBtn.disabled = true;
				pdfBtn.textContent = 'Generating PDF...';
				requestBasketPdf('', function (result) {
					if (result && result.downloaded) {
						toast('Basket PDF downloaded');
						if (mailRow) {
							mailRow.hidden = false;
						}
					} else if (result && result.networkError) {
						toast('PDF generation failed — network error');
					} else {
						toast((result && result.json && result.json.message) || 'PDF generation failed');
					}
					pdfBtn.disabled = false;
					pdfBtn.textContent = PDF_LABEL;
				});
			});
		}

		if (mailRow) {
			var mailInput = mailRow.querySelector('.sf-basket-drawer__mail-input');
			var mailSend = mailRow.querySelector('.sf-basket-drawer__mail-send');
			if (mailInput && mailSend) {
				mailSend.addEventListener('click', function () {
					var email = (mailInput.value || '').trim();
					if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
						toast('Enter a valid email address');
						return;
					}
					var oldLabel = mailSend.textContent;
					mailSend.disabled = true;
					mailSend.textContent = 'Sending...';
					requestBasketPdf(email, function (result) {
						if (result && result.ok && result.json && result.json.sent) {
							toast('Copy sent to ' + email);
							mailRow.hidden = true;
							mailInput.value = '';
						} else if (result && result.networkError) {
							toast('Sending failed — network error');
						} else {
							toast((result && result.json && result.json.message) || 'Sending failed');
						}
						mailSend.disabled = false;
						mailSend.textContent = oldLabel;
					});
				});
			}
		}

		/* Stage 3: Submit Inquiry — guard / snapshot / jump-or-fill. */
		var submitLink = drawer.querySelector('.sf-basket-drawer__submit');
		if (submitLink) {
			submitLink.addEventListener('click', function (event) {
				var items = read();
				if (!items.length) {
					event.preventDefault();
					toast('Your basket is empty');
					return;
				}
				try {
					sessionStorage.setItem('sinofresh_basket_pending',
						JSON.stringify({ items: items, at: Date.now() }));
				} catch (e) {
					/* degrade: plain navigation, contact page just skips fill */
				}
				if (/^\/contact\/?$/i.test(window.location.pathname)) {
					/* Drawer opened on the contact page itself: fill in place. */
					event.preventDefault();
					if (fillFromBasket()) {
						window.SFBasket.closeDrawer();
						var wrapper = document.querySelector('.gform_wrapper');
						if (wrapper) {
							wrapper.scrollIntoView({ behavior: 'smooth', block: 'start' });
						}
						toast(items.length + (items.length > 1 ? ' items' : ' item') + ' pre-filled below');
					}
				} else {
					var href = submitLink.getAttribute('href') || '/contact/';
					submitLink.setAttribute('href', href + (href.indexOf('?') === -1 ? '?' : '&') + 'from=basket');
					/* default anchor navigation proceeds with the new href */
				}
			});
		}

		/* Landing on /contact/?from=basket: auto-fill the quote form. */
		try {
			if (new URLSearchParams(window.location.search).get('from') === 'basket') {
				fillFromBasket();
			}
		} catch (e) {}

		bindConfirmationClear();

		/* Initial paint (badge on page load with a persisted basket). */
		window.SFBasket.render();
	}

	initUI();
})();

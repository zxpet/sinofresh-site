/*
 * SINO FRESH — Dosage Form Configurator logic
 * Requires markup from page-soft-chews.html (.configurator root).
 * - data-group  : dimension key (shape, color, flavor, weight, count, packaging, functions, shelf_life)
 * - data-multi  : "true" = multi select, "false" = single select
 * - data-value  : option value on each .configurator__item button
 * State persists to sessionStorage, scoped per dosage form page:
 * key = "sinofresh_config_<page-slug>"  (e.g. sinofresh_config_soft-chews).
 * All eight dosage pages share this file, so a shared key would leak one
 * page's configuration into another.
 */
(function () {
	'use strict';

	var root = document.querySelector('.configurator');
	if (!root) {
		return;
	}

	/** Slug of the current dosage form page, e.g. "soft-chews". */
	function currentSlug() {
		// 1) permalink: /products/soft-chews/ -> "soft-chews"
		var segments = window.location.pathname.replace(/\/+$/, '').split('/');
		var last = (segments[segments.length - 1] || '').toLowerCase();
		if (/^[a-z0-9][a-z0-9-]*$/.test(last) && last !== 'products') {
			return last;
		}
		// 2) WordPress body class: page-<slug> (skip page-id-*, page-template-*)
		var match = (document.body.className || '').match(/(?:^|\s)page-(?!id-|template|parent|child)([a-z0-9-]+)/i);
		return match ? match[1].toLowerCase() : '';
	}

	var LEGACY_KEY = 'sinofresh_config';
	var SLUG = currentSlug();
	var STORAGE_KEY = SLUG ? LEGACY_KEY + '_' + SLUG : LEGACY_KEY;
	/* Standard formula picked from the Standard Formulas band (formulas.js
	   writes it). Scoped per page like the config itself. */
	var FORMULA_KEY = SLUG ? 'sinofresh_formula_' + SLUG : '';
	var PLACEHOLDER = '\u2014'; // em dash for unselected dimensions

	var groups = Array.prototype.slice.call(root.querySelectorAll('.configurator__group'));
	var summaryRows = {};
	Array.prototype.forEach.call(document.querySelectorAll('.configurator__summary-row[data-group]'), function (row) {
		summaryRows[row.getAttribute('data-group')] = row.querySelector('.configurator__summary-value');
	});

	function isMulti(group) {
		return group.getAttribute('data-multi') === 'true';
	}

	function selectedValues(group) {
		return Array.prototype.map.call(
			group.querySelectorAll('.configurator__item.is-selected'),
			function (btn) {
				return btn.getAttribute('data-value');
			}
		);
	}

	function groupLabel(group) {
		var h4 = group.querySelector('h4');
		return h4 ? h4.textContent.replace(/\s+/g, ' ').trim() : group.getAttribute('data-group');
	}

	function collectConfig() {
		var config = {};
		groups.forEach(function (group) {
			var name = group.getAttribute('data-group');
			var values = selectedValues(group);
			config[name] = isMulti(group) ? values : (values.length ? values[0] : '');
		});
		return config;
	}

	function persist(config) {
		try {
			sessionStorage.setItem(STORAGE_KEY, JSON.stringify(config));
			// The pre-fix shared key is no longer used — drop it so it can never
			// leak into another dosage form page.
			if (STORAGE_KEY !== LEGACY_KEY) {
				sessionStorage.removeItem(LEGACY_KEY);
			}
		} catch (e) {
			/* storage unavailable (private mode) — fail silently */
		}
	}

	/**
	 * Read this page's saved state. Falls back to the legacy shared key once
	 * (so a visitor's current selection is not lost by the fix), migrates the
	 * value to the per-page key and then removes the legacy key.
	 */
	function readState() {
		try {
			var raw = sessionStorage.getItem(STORAGE_KEY);
			if (raw || STORAGE_KEY === LEGACY_KEY) {
				return raw;
			}
			raw = sessionStorage.getItem(LEGACY_KEY);
			if (raw) {
				sessionStorage.setItem(STORAGE_KEY, raw);
				sessionStorage.removeItem(LEGACY_KEY);
			}
			return raw;
		} catch (e) {
			return null;
		}
	}

	/* "Custom" alone tells the buyer nothing — point them at the Notes field. */
	function displayValue(value) {
		return value === 'Custom' ? 'Custom (specify in notes)' : value;
	}

	function formatValue(values) {
		return values.length ? values.map(displayValue).join(', ') : PLACEHOLDER;
	}

	var progressEl = root.querySelector('.configurator__progress');

	function updateProgress(config) {
		if (!progressEl) {
			return;
		}
		var filled = groups.filter(function (group) {
			var v = config[group.getAttribute('data-group')];
			return Array.isArray(v) ? v.length > 0 : !!v;
		}).length;
		progressEl.textContent = filled + ' of ' + groups.length + ' selected';
	}

	function updateSummary(config) {
		Object.keys(summaryRows).forEach(function (name) {
			var el = summaryRows[name];
			if (!el) {
				return;
			}
			var value = config[name];
			el.textContent = Array.isArray(value) ? formatValue(value) : (displayValue(value) || PLACEHOLDER);
		});
	}

	function onChange() {
		var config = collectConfig();
		updateSummary(config);
		updateProgress(config);
		persist(config);
	}

	function restore() {
		var raw = readState();
		if (!raw) {
			return;
		}
		var config;
		try {
			config = JSON.parse(raw);
		} catch (e) {
			return;
		}
		if (!config || typeof config !== 'object') {
			return;
		}
		groups.forEach(function (group) {
			var name = group.getAttribute('data-group');
			var saved = config[name];
			if (saved === undefined || saved === null) {
				return;
			}
			var values = Array.isArray(saved) ? saved : [saved];
			Array.prototype.forEach.call(group.querySelectorAll('.configurator__item'), function (btn) {
				if (values.indexOf(btn.getAttribute('data-value')) !== -1) {
					btn.classList.add('is-selected');
				}
			});
		});
		onChange();
	}

	/* --- Click handling (event delegation) --- */
	root.addEventListener('click', function (event) {
		var btn = event.target.closest('.configurator__item');
		if (!btn || !root.contains(btn)) {
			return;
		}
		var group = btn.closest('.configurator__group');
		if (isMulti(group)) {
			btn.classList.toggle('is-selected');
		} else {
			var wasSelected = btn.classList.contains('is-selected');
			Array.prototype.forEach.call(group.querySelectorAll('.configurator__item.is-selected'), function (b) {
				b.classList.remove('is-selected');
			});
			if (!wasSelected) {
				btn.classList.add('is-selected');
			}
		}
		onChange();
	});

	/** Human-readable summary shared by Submit and Copy. */
	function buildSummaryText() {
		var config = collectConfig();
		return groups.map(function (group) {
			var name = group.getAttribute('data-group');
			var value = config[name];
			var text = Array.isArray(value) ? formatValue(value) : (displayValue(value) || PLACEHOLDER);
			return groupLabel(group) + ': ' + text;
		}).join('\n');
	}

	/* --- Submit Configuration (card button + mobile action bar) --- */
	/**
	 * Locate the hidden field that carries the configuration into the inquiry form.
	 * Gravity Forms renders hidden inputs as name="input_{id}", so we fall back to
	 * the field wrapper class (.sf-config-summary) and then to the field label.
	 * Returns null when no such field exists — the caller then skips filling it.
	 */
	function findSummaryField() {
		var el = document.querySelector('input[name="config_summary"]');
		if (el) {
			return el;
		}
		var wrap = document.querySelector('.sf-config-summary, .gfield--type-hidden.sf-config-summary');
		if (wrap) {
			el = wrap.querySelector('input[type="hidden"]');
			if (el) {
				return el;
			}
		}
		var hiddenFields = document.querySelectorAll('.gfield--type-hidden');
		for (var i = 0; i < hiddenFields.length; i++) {
			var field = hiddenFields[i];
			var text = (field.getAttribute('data-label') || field.textContent || '') + (field.getAttribute('class') || '');
			if (/configuration\s*summary|config_summary/i.test(text)) {
				el = field.querySelector('input[type="hidden"]');
				if (el) {
					return el;
				}
			}
		}
		return null;
	}

	var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
	Array.prototype.forEach.call(root.querySelectorAll('.configurator__submit'), function (submitBtn) {
		submitBtn.addEventListener('click', function () {
			var summary = buildSummaryText();

			// Fill the inquiry form hidden field if present; skip otherwise.
			var hidden = findSummaryField();
			if (hidden) {
				hidden.value = summary;
			}

			// Scroll to the inquiry form section.
			var target = document.getElementById('inquiry-form');
			if (target) {
				target.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'start' });
			}
		});
	});

	/* --- Reset --- */
	/* Bound to EVERY .configurator__reset: the card button and, on phones,
	   the one inside the bottom drawer (same behaviour, two instances). */
	Array.prototype.forEach.call(root.querySelectorAll('.configurator__reset'), function (resetBtn) {
		resetBtn.addEventListener('click', function () {
			if (!window.confirm('Clear all selections?')) {
				return;
			}
			Array.prototype.forEach.call(root.querySelectorAll('.configurator__item.is-selected'), function (b) {
				b.classList.remove('is-selected');
			});
			/* Reset also clears the referenced standard formula so the PDF
			   stops showing "(Standard)" for a wiped configuration. */
			if (FORMULA_KEY) {
				try {
					sessionStorage.removeItem(FORMULA_KEY);
				} catch (e) {}
			}
			onChange();
		});
	});

	/* --- Copy configuration summary --- */
	Array.prototype.forEach.call(root.querySelectorAll('.configurator__copy'), function (copyBtn) {
		var copyLabel = copyBtn.querySelector('.configurator__copy-label');
		var copyTimer = null;
		copyBtn.addEventListener('click', function () {
			var text = buildSummaryText();
			var done = function () {
				copyBtn.classList.add('is-copied');
				if (copyLabel) {
					copyLabel.textContent = 'Copied!';
				}
				if (copyTimer) {
					clearTimeout(copyTimer);
				}
				copyTimer = setTimeout(function () {
					copyBtn.classList.remove('is-copied');
					if (copyLabel) {
						copyLabel.textContent = 'Copy';
					}
				}, 2000);
			};
			if (navigator.clipboard && navigator.clipboard.writeText) {
				navigator.clipboard.writeText(text).then(done, function () {});
			} else {
				var ta = document.createElement('textarea');
				ta.value = text;
				ta.setAttribute('readonly', '');
				ta.style.position = 'fixed';
				ta.style.opacity = '0';
				document.body.appendChild(ta);
				ta.select();
				try {
					document.execCommand('copy');
					done();
				} catch (e) {
					/* clipboard unavailable — fail silently */
				}
				document.body.removeChild(ta);
			}
		});
	});

	/* --- PDF summary (POST /wp-json/sinofresh/v1/config-pdf) --------------
	   "Download PDF Summary" under Submit (summary card) and inside the
	   mobile drawer: validates completeness, streams a 2-page A4 summary
	   with a unique SF-YYYYMMDD-XXXX reference, then offers an optional
	   email copy (server cc's sales@zxpet.com). Two markup instances exist,
	   so every button and mail row is bound and toggled together. */
	var pdfBtns = Array.prototype.slice.call(root.querySelectorAll('.configurator__pdf'));
	if (pdfBtns.length) {
		var PDF_LABEL = pdfBtns[0].textContent;

		function pdfToast(message) {
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

		function readFormula() {
			/* { name, sections:[{label,value}] } for the referenced standard
			   formula, pulled from the Standard Formulas band markup. */
			try {
				var name = FORMULA_KEY ? sessionStorage.getItem(FORMULA_KEY) : '';
				if (!name) {
					return null;
				}
				var items = document.querySelectorAll('.sf-formula__item');
				for (var i = 0; i < items.length; i++) {
					var nameEl = items[i].querySelector('.sf-formula__name');
					if (nameEl && nameEl.textContent.replace(/\s+/g, ' ').trim() === name) {
						var sections = [];
						var labels = items[i].querySelectorAll('.sf-formula__label');
						for (var j = 0; j < labels.length; j++) {
							var val = labels[j].nextElementSibling;
							if (val) {
								sections.push({ label: labels[j].textContent.trim(), value: val.textContent.trim() });
							}
						}
						return { name: name, sections: sections };
					}
				}
				return { name: name, sections: [] };
			} catch (e) {
				return null;
			}
		}

		function configComplete(config) {
			for (var i = 0; i < groups.length; i++) {
				var v = config[groups[i].getAttribute('data-group')];
				if (Array.isArray(v) ? v.length === 0 : !v) {
					return false;
				}
			}
			return true;
		}

		function pdfBusy(busy) {
			Array.prototype.forEach.call(pdfBtns, function (b) {
				b.disabled = busy;
				b.textContent = busy ? 'Generating PDF...' : PDF_LABEL;
			});
		}

		function requestPdf(withEmail, onDone) {
			return fetch('/wp-json/sinofresh/v1/config-pdf', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					slug: SLUG,
					config: collectConfig(),
					formula: readFormula(),
					email: withEmail || ''
				})
			}).then(function (res) {
				if (withEmail) {
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
						a.download = nameMatch ? nameMatch[1] : 'SINO-FRESH-configuration.pdf';
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

		Array.prototype.forEach.call(pdfBtns, function (btn) {
			btn.addEventListener('click', function () {
				var config = collectConfig();
				if (!configComplete(config)) {
					pdfToast('Please complete all configuration options');
					return;
				}
				pdfBusy(true);
				requestPdf('', function (result) {
					if (result && result.downloaded) {
						pdfToast('PDF downloaded');
						Array.prototype.forEach.call(root.querySelectorAll('.configurator__pdf-mail'), function (row) {
							row.hidden = false;
						});
					} else if (result && result.networkError) {
						pdfToast('PDF generation failed — network error');
					} else {
						pdfToast((result && result.json && result.json.message) || 'PDF generation failed');
					}
					pdfBusy(false);
				});
			});
		});

		Array.prototype.forEach.call(root.querySelectorAll('.configurator__pdf-mail'), function (row) {
			var input = row.querySelector('.configurator__pdf-mail-input');
			var send = row.querySelector('.configurator__pdf-mail-send');
			if (!input || !send) {
				return;
			}
			send.addEventListener('click', function () {
				var email = (input.value || '').trim();
				if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
					pdfToast('Enter a valid email address');
					return;
				}
				var oldLabel = send.textContent;
				send.disabled = true;
				send.textContent = 'Sending...';
				requestPdf(email, function (result) {
					if (result && result.ok && result.json && result.json.sent) {
						pdfToast('Copy sent to ' + email);
						row.hidden = true;
						input.value = '';
					} else if (result && result.networkError) {
						pdfToast('Sending failed — network error');
					} else {
						pdfToast((result && result.json && result.json.message) || 'Sending failed');
					}
					send.disabled = false;
					send.textContent = oldLabel;
				});
			});
		});
	}

	restore();
})();

/* Mobile bar+drawer (additive): count, open/close, row refresh after Reset.
   Drawer Reset/Copy/Submit reuse the core handlers above. */
!function(){var b=document.querySelector(".configurator__bar"),d=document.getElementById("configurator-drawer");if(!b||!d)return;var r=document.querySelector(".configurator"),c=b.querySelector(".configurator__bar-count"),n=d.querySelector(".configurator__drawer-content"),t=b.querySelector(".configurator__bar-trigger"),G=r.querySelectorAll(".configurator__group"),R=document.querySelectorAll(".configurator__summary-row[data-group]");function E(){d.classList.remove("is-open"),t.setAttribute("aria-expanded","false"),setTimeout(function(){d.hidden=!0},300)}function s(){for(var f=0,i=0;i<G.length;i++)G[i].querySelector(".is-selected")&&f++;c.textContent=f+" of "+G.length+" selected"}function w(){n.innerHTML="",R.forEach(function(x){n.appendChild(x.cloneNode(!0))})}t.addEventListener("click",function(){w(),d.hidden=!1,requestAnimationFrame(function(){d.classList.add("is-open")}),t.setAttribute("aria-expanded","true")}),d.querySelector(".configurator__drawer-close").addEventListener("click",E),document.addEventListener("click",function(v){d.hidden||d.contains(v.target)||b.contains(v.target)||E()}),d.querySelector(".configurator__drawer-submit").addEventListener("click",E),r.addEventListener("click",function(v){var e=v.target.closest(".configurator__item, .configurator__drawer-reset, .configurator__reset");e&&setTimeout(function(){e.classList.contains("configurator__drawer-reset")&&w(),s()},0)}),s()}();

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

	/* Placeholder copy for the Custom detail input, per dimension key.
	   Dimensions without an entry fall back to the generic text. */
	var CUSTOM_PLACEHOLDERS = {
		shape: 'e.g. 3.5g bone with ridges',
		color: 'e.g. Pantone 186C red',
		flavor: 'e.g. Duck liver',
		functions: 'e.g. Hip & joint + Omega-3',
		packaging: 'e.g. 120g HDPE jar with desiccant',
		shelf_life: 'e.g. 24 months',
		weight: 'e.g. 1.2g per piece',
		count: 'e.g. 90 pieces per bottle',
		weight_per_piece: 'e.g. 3g per piece',
		serving_size: 'e.g. 5g per serving',
		net_weight: 'e.g. 150g per pouch',
		tube_weight: 'e.g. 100g per tube',
		bottle_size: 'e.g. 250ml pump bottle',
		drops_per_dose: 'e.g. 8 drops per dose',
		omega3_per_unit: 'e.g. 500mg EPA+DHA per softgel',
		texture: 'e.g. semi-solid, easy-squeeze',
		appearance: 'e.g. off-white fine powder',
		form: 'e.g. enteric-coated softgel',
		source: 'e.g. wild-caught Peruvian anchovy',
		size: 'e.g. 25mm star-shaped'
	};
	var CUSTOM_FALLBACK_PLACEHOLDER = 'Describe your custom requirement';

	/* One level of entity decoding, applied at the storage boundary. The DOM
	   serializer rewrites "&" to "&amp;" whenever markup is read back, so a
	   value that has been through serialized markup can arrive pre-escaped.
	   Decoding here keeps sessionStorage canonical (raw characters) while the
	   PDF escapes exactly once — otherwise the entity survives one level too
	   many and prints as a literal "&amp;". Single pass on purpose:
	   "&amp;lt;" becomes "&lt;", never "<". */
	var ENTITY_MAP = {
		'&amp;': '&',
		'&lt;': '<',
		'&gt;': '>',
		'&quot;': '"',
		'&#039;': "'",
		'&#39;': "'",
		'&apos;': "'",
		'&nbsp;': ' '
	};
	function decodeEntities(text) {
		return String(text || '').replace(/&(?:amp|lt|gt|quot|apos|nbsp|#0?39);/g, function (m) {
			return ENTITY_MAP[m] !== undefined ? ENTITY_MAP[m] : m;
		});
	}

	/* The Custom detail text must never carry the summary separators
	   (":" and "|" are how the basket summary / PDF split fields), so both
	   are rewritten at input time. Whitespace is normalized on blur. */
	function sanitizeCustom(text) {
		return decodeEntities(String(text || '')).replace(/:/g, ' - ').replace(/\|/g, ' / ');
	}

	var groups = Array.prototype.slice.call(root.querySelectorAll('.configurator__group'));
	var summaryRows = {};
	Array.prototype.forEach.call(document.querySelectorAll('.configurator__summary-row[data-group]'), function (row) {
		summaryRows[row.getAttribute('data-group')] = row.querySelector('.configurator__summary-value');
	});

	/* --- Custom detail inputs ----------------------------------------------
	   Every dimension that carries a Custom chip gets a detail field (all
	   single-line; Functions would use a textarea) inserted under its chip
	   row. It slides open when Custom is selected and stores next to the
	   group value under key "<group>_custom" — saved states from before
	   this field existed simply lack the key and restore unchanged. */
	var customInputs = {};
	Array.prototype.forEach.call(groups, function (group) {
		var name = group.getAttribute('data-group');
		var items = group.querySelector('.configurator__items');
		if (!items || !group.querySelector('.configurator__item[data-value="Custom"]')) {
			return;
		}
		var wrap = document.createElement('div');
		wrap.className = 'configurator__custom';
		var isFunctions = name === 'functions';
		var field = document.createElement(isFunctions ? 'textarea' : 'input');
		if (isFunctions) {
			field.setAttribute('rows', '3');
		} else {
			field.type = 'text';
		}
		field.className = 'configurator__custom-input';
		field.placeholder = CUSTOM_PLACEHOLDERS[name] || CUSTOM_FALLBACK_PLACEHOLDER;
		field.setAttribute('aria-label', groupLabel(group) + ' \u2014 describe your custom requirement');
		wrap.appendChild(field);
		wrap.hidden = true;
		/* Lives INSIDE .configurator__items (a flex-wrap row) as a
		   flex-basis:100% line under the chips — after .items it would be a
		   third child of the group's nowrap flex row and squeeze the chips. */
		items.appendChild(wrap);
		customInputs[name] = field;

		/* Live-save the (separator-filtered) text while typing. */
		field.addEventListener('input', function () {
			onChange();
		});
		/* On blur: normalize whitespace, push the cleaned text back into the
		   field and refresh the summary with the filtered value. */
		field.addEventListener('blur', function () {
			var clean = sanitizeCustom(field.value).replace(/\s+/g, ' ').trim();
			if (clean !== field.value) {
				field.value = clean;
			}
			onChange();
		});
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
			var multi = isMulti(group);
			config[name] = multi ? values : (values.length ? values[0] : '');
			/* Parallel key "<group>_custom" carries the Custom detail text
			   (already separator-filtered by sanitizeCustom on input). Only
			   present when Custom is actually selected in that dimension. */
			var pickedCustom = multi
				? values.indexOf('Custom') !== -1
				: (values.length ? values[0] === 'Custom' : false);
			if (pickedCustom && customInputs[name]) {
				/* Whitespace collapses to single spaces here too: the
				   Functions textarea is multi-line while typing, but the
				   summary / PDF table / basket line are single-line. */
				config[name + '_custom'] = sanitizeCustom(customInputs[name].value)
					.replace(/\s+/g, ' ')
					.trim();
			}
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

	/* Three display states for a Custom selection: nothing typed keeps the
	   old "specify in notes" pointer, typed text shows as "Custom: <text>". */
	function displayValue(config, name, value) {
		if (value === 'Custom') {
			var text = config && config[name + '_custom'] ? config[name + '_custom'] : '';
			return text ? 'Custom: ' + text : 'Custom (specify in notes)';
		}
		return value;
	}

	function formatValue(config, name, values) {
		return values.length
			? values.map(function (v) { return displayValue(config, name, v); }).join(', ')
			: PLACEHOLDER;
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
			el.textContent = Array.isArray(value)
				? formatValue(config, name, value)
				: (displayValue(config, name, value) || PLACEHOLDER);
		});
	}

	/* Open the detail field of every group whose Custom chip is selected,
	   close the others. Runs inside onChange so clicks and restores both
	   stay in sync. The closed field is [hidden] (zero layout footprint —
	   a zero-height flex line would still cost its row gap); opening lifts
	   [hidden] first and adds .is-open two frames later so the max-height
	   transition actually plays.

	   The deferred close is guarded by the LAST intent, not by the class:
	   .is-open only lands ~2 frames after an open, so a close queued by an
	   earlier onChange (e.g. the blur of another field's input) could fire
	   inside that window, see no .is-open yet and hide the field that just
	   opened. Every call therefore cancels the wrap's pending timer and
	   records its intent first. */
	function setCustomOpen(wrap, open) {
		wrap.sfIntent = open;
		if (wrap.sfTimer) {
			clearTimeout(wrap.sfTimer);
			wrap.sfTimer = null;
		}
		if (open) {
			if (wrap.hidden) {
				wrap.hidden = false;
			}
			requestAnimationFrame(function () {
				requestAnimationFrame(function () {
					if (wrap.sfIntent) {
						wrap.classList.add('is-open');
					}
				});
			});
		} else {
			wrap.classList.remove('is-open');
			wrap.sfTimer = setTimeout(function () {
				wrap.sfTimer = null;
				if (!wrap.sfIntent) {
					wrap.hidden = true;
				}
			}, 300);
		}
	}

	function syncCustomInputs(config) {
		Object.keys(customInputs).forEach(function (name) {
			var value = config[name];
			var active = Array.isArray(value)
				? value.indexOf('Custom') !== -1
				: value === 'Custom';
			setCustomOpen(customInputs[name].parentNode, active);
		});
	}

	function onChange() {
		var config = collectConfig();
		updateSummary(config);
		updateProgress(config);
		syncCustomInputs(config);
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
		/* Old saved states have no "<group>_custom" keys — they simply skip
		   the loop below and restore exactly as before. */
		Object.keys(customInputs).forEach(function (name) {
			var saved = config[name + '_custom'];
			if (typeof saved === 'string' && saved) {
				/* A state saved before the decode fix may still hold entities. */
				customInputs[name].value = decodeEntities(saved);
			}
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

	/** Human-readable summary shared by Submit, Copy and the inquiry basket.
	    sep='\n' (default) for the form hidden field / clipboard; sep=' | '
	    for the basket's one-line per-item summary. */
	function buildSummaryText(sep) {
		var config = collectConfig();
		return groups.map(function (group) {
			var name = group.getAttribute('data-group');
			var value = config[name];
			var text = Array.isArray(value)
				? formatValue(config, name, value)
				: (displayValue(config, name, value) || PLACEHOLDER);
			return groupLabel(group) + ': ' + text;
		}).join(sep || '\n');
	}

	/* PDF payload: label/value pairs built straight from the page markup.
	   Labels come from each group's <h4>, values use the same three-state
	   display as the summary card — so the server renders every dosage
	   form correctly without a hardcoded key map (the old map only fit
	   soft-chews and left the other 7 pages with empty rows). */
	function buildConfigPairs() {
		var config = collectConfig();
		return groups.map(function (group) {
			var name = group.getAttribute('data-group');
			var value = config[name];
			return {
				label: groupLabel(group),
				value: Array.isArray(value)
					? formatValue(config, name, value)
					: (displayValue(config, name, value) || PLACEHOLDER)
			};
		});
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

	/* True when every dimension group has at least one selection. Shared by
	   the PDF download and the "Add to Inquiry" basket button. */
	function configComplete(config) {
		for (var i = 0; i < groups.length; i++) {
			var v = config[groups[i].getAttribute('data-group')];
			if (Array.isArray(v) ? v.length === 0 : !v) {
				return false;
			}
		}
		return true;
	}

	/* A selected Custom chip with an empty detail input blocks Submit, the
	   PDF download and the inquiry basket. Returns the dimension key of the
	   first offender (so its input can be focused) or null. */
	function firstEmptyCustom(config) {
		for (var i = 0; i < groups.length; i++) {
			var name = groups[i].getAttribute('data-group');
			var v = config[name];
			var picked = Array.isArray(v) ? v.indexOf('Custom') !== -1 : v === 'Custom';
			if (picked && !(config[name + '_custom'] || '').trim()) {
				return name;
			}
		}
		return null;
	}

	/* Shared reaction to an empty Custom detail: toast + bring the field
	   into view and focus it. */
	function flagEmptyCustom(name) {
		sfToast('Please describe your custom requirement');
		var field = customInputs[name];
		if (field) {
			field.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'center' });
			try {
				field.focus({ preventScroll: true });
			} catch (e) {
				field.focus();
			}
		}
	}

	/* Single shared toast (PDF + basket). Managing the hide timer here means
	   a second toast shown while the first is still up replaces its text and
	   restarts the clock instead of being cut short by the stale timer. */
	var sfToastTimer = null;
	function sfToast(message) {
		var el = document.querySelector('.sf-toast');
		if (!el) {
			el = document.createElement('div');
			el.className = 'sf-toast';
			el.setAttribute('role', 'status');
			el.setAttribute('aria-live', 'polite');
			document.body.appendChild(el);
		}
		if (sfToastTimer) {
			clearTimeout(sfToastTimer);
		}
		el.classList.remove('is-visible');
		el.textContent = message;
		void el.offsetWidth;
		el.classList.add('is-visible');
		sfToastTimer = setTimeout(function () {
			el.classList.remove('is-visible');
			sfToastTimer = null;
		}, 2600);
	}
	Array.prototype.forEach.call(root.querySelectorAll('.configurator__submit'), function (submitBtn) {
		submitBtn.addEventListener('click', function () {
			// Custom selected but not described? Stop before touching the form.
			var missingCustom = firstEmptyCustom(collectConfig());
			if (missingCustom) {
				flagEmptyCustom(missingCustom);
				return;
			}

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
			/* Reset also wipes every Custom detail input. */
			Object.keys(customInputs).forEach(function (name) {
				customInputs[name].value = '';
			});
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

		function readFormula() {
			/* { name, sections:[{label,value}] } for the referenced standard
			   formula. 2B Stage2: prefer the machine-readable JSON mirror
			   (.sf-formulas-data, emitted by the sf_formula_grid shortcode),
			   fall back to scraping the legacy .sf-formula__item markup,
			   and return empty sections when neither is present. */
			try {
				var name = FORMULA_KEY ? sessionStorage.getItem(FORMULA_KEY) : '';
				if (!name) {
					return null;
				}
				var wanted = name.replace(/\s+/g, ' ').trim();

				/* Path 1 — .sf-formulas-data JSON (2A shape: {name, slug,
				   url, form, use, sections[3]{label,value}}). */
				var jsonNodes = document.querySelectorAll('script.sf-formulas-data');
				for (var i = 0; i < jsonNodes.length; i++) {
					var data;
					try {
						data = JSON.parse(jsonNodes[i].textContent || '');
					} catch (pe) {
						data = null;
					}
					if (!data || !data.length) {
						continue;
					}
					for (var k = 0; k < data.length; k++) {
						if (data[k] && typeof data[k].name === 'string'
							&& data[k].name.replace(/\s+/g, ' ').trim() === wanted) {
							return {
								name: name,
								sections: (data[k].sections || []).map(function (s) {
									return { label: String(s.label || ''), value: String(s.value || '') };
								})
							};
						}
					}
				}

				/* Path 2 — legacy DOM scrape (kept until 2B Stage 3 removes
				   the details markup from the dosage templates). */
				var items = document.querySelectorAll('.sf-formula__item');
				for (var j = 0; j < items.length; j++) {
					var nameEl = items[j].querySelector('.sf-formula__name');
					if (nameEl && nameEl.textContent.replace(/\s+/g, ' ').trim() === wanted) {
						var sections = [];
						var labels = items[j].querySelectorAll('.sf-formula__label');
						for (var m = 0; m < labels.length; m++) {
							var val = labels[m].nextElementSibling;
							if (val) {
								sections.push({ label: labels[m].textContent.trim(), value: val.textContent.trim() });
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
					config: buildConfigPairs(),
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
					sfToast('Please complete all configuration options');
					return;
				}
				var missingCustom = firstEmptyCustom(config);
				if (missingCustom) {
					flagEmptyCustom(missingCustom);
					return;
				}
				pdfBusy(true);
				requestPdf('', function (result) {
					if (result && result.downloaded) {
						sfToast('PDF downloaded');
						Array.prototype.forEach.call(root.querySelectorAll('.configurator__pdf-mail'), function (row) {
							row.hidden = false;
						});
					} else if (result && result.networkError) {
						sfToast('PDF generation failed — network error');
					} else {
						sfToast((result && result.json && result.json.message) || 'PDF generation failed');
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
					sfToast('Enter a valid email address');
					return;
				}
				var oldLabel = send.textContent;
				send.disabled = true;
				send.textContent = 'Sending...';
				requestPdf(email, function (result) {
					if (result && result.ok && result.json && result.json.sent) {
						sfToast('Copy sent to ' + email);
						row.hidden = true;
						input.value = '';
					} else if (result && result.networkError) {
						sfToast('Sending failed — network error');
					} else {
						sfToast((result && result.json && result.json.message) || 'Sending failed');
					}
					send.disabled = false;
					send.textContent = oldLabel;
				});
			});
		});
	}

	/* --- Add to Inquiry basket (stage 1: storage + button state) ----------
	   Validates completeness, stores {slug,title,summary,formula} in
	   sessionStorage via window.SFBasket (assets/js/basket.js), and flips
	   every button instance to "Added to Inquiry ✓" for 2s. Adding the same
	   dosage form again replaces its entry and the toast says "updated".
	   Shares the PDF section's .sf-toast element, so the two never overlap. */
	var basketBtns = Array.prototype.slice.call(root.querySelectorAll('.configurator__basket'));
	if (basketBtns.length && window.SFBasket) {
		var BASKET_LABEL = basketBtns[0].textContent;
		var basketTimer = null;

		/** "soft-chews" -> "Soft Chews" for titles and toast copy. */
		function basketTitle() {
			return SLUG.split('-').map(function (word) {
				return word ? word.charAt(0).toUpperCase() + word.slice(1) : word;
			}).join(' ');
		}

		function basketAddedFlash() {
			Array.prototype.forEach.call(basketBtns, function (b) {
				b.classList.add('is-added');
				b.textContent = 'Added to Inquiry ✓';
			});
			if (basketTimer) {
				clearTimeout(basketTimer);
			}
			basketTimer = setTimeout(function () {
				Array.prototype.forEach.call(basketBtns, function (b) {
					b.classList.remove('is-added');
					b.textContent = BASKET_LABEL;
				});
			}, 2000);
		}

		Array.prototype.forEach.call(basketBtns, function (btn) {
			btn.addEventListener('click', function () {
				var config = collectConfig();
				if (!configComplete(config)) {
					sfToast('Please complete all configuration options');
					return;
				}
				var missingCustom = firstEmptyCustom(config);
				if (missingCustom) {
					flagEmptyCustom(missingCustom);
					return;
				}
				var title = basketTitle();
				var formulaName = '';
				try {
					formulaName = FORMULA_KEY ? (sessionStorage.getItem(FORMULA_KEY) || '') : '';
				} catch (e) {}
				var result = window.SFBasket.add({
					slug: SLUG,
					title: title,
					summary: 'Dosage Form: ' + title + ' | ' + buildSummaryText(' | '),
					formula: formulaName
				});
				sfToast(result.updated
					? title + ' configuration updated in your inquiry basket'
					: title + ' added to your inquiry basket');
				basketAddedFlash();
			});
		});
	}

	restore();
})();

/* Mobile bar+drawer (additive): count, open/close, row refresh after Reset.
   Drawer Reset/Copy/Submit reuse the core handlers above. */
!function(){var b=document.querySelector(".configurator__bar"),d=document.getElementById("configurator-drawer");if(!b||!d)return;var r=document.querySelector(".configurator"),c=b.querySelector(".configurator__bar-count"),n=d.querySelector(".configurator__drawer-content"),t=b.querySelector(".configurator__bar-trigger"),G=r.querySelectorAll(".configurator__group"),R=document.querySelectorAll(".configurator__summary-row[data-group]");function E(){d.classList.remove("is-open"),t.setAttribute("aria-expanded","false"),setTimeout(function(){d.hidden=!0},300)}function s(){for(var f=0,i=0;i<G.length;i++)G[i].querySelector(".is-selected")&&f++;c.textContent=f+" of "+G.length+" selected"}function w(){n.innerHTML="",R.forEach(function(x){n.appendChild(x.cloneNode(!0))})}t.addEventListener("click",function(){w(),d.hidden=!1,requestAnimationFrame(function(){d.classList.add("is-open")}),t.setAttribute("aria-expanded","true")}),d.querySelector(".configurator__drawer-close").addEventListener("click",E),document.addEventListener("click",function(v){d.hidden||d.contains(v.target)||b.contains(v.target)||E()}),d.querySelector(".configurator__drawer-submit").addEventListener("click",E),r.addEventListener("click",function(v){var e=v.target.closest(".configurator__item, .configurator__drawer-reset, .configurator__reset");e&&setTimeout(function(){e.classList.contains("configurator__drawer-reset")&&w(),s()},0)}),s()}();

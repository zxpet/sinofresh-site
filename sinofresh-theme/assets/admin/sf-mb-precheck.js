/*
 * SINO FRESH — batch H1 phase-1 precheck (vanilla JS).
 *
 * Phase 1 warns and never blocks: when the editor hits Publish (or Save),
 * this reads the metabox fields straight out of the DOM and lists the gaps
 * in a banner above the boxes. The server-side banner (admin_notices) and,
 * in phase 2, the hard gate remain the authority — this is a convenience
 * pass so operations see the same list before submitting.
 *
 * Optional wp.data notices (WordPress core store) are used when the block
 * editor is present; otherwise the DOM banner covers it.
 */
(function () {
	'use strict';

	function fieldLabel(field) {
		var label = field.querySelector('.sf-mb__label');
		return label ? label.textContent.replace('*', '').trim() : field.getAttribute('data-sf-key');
	}

	function fieldEmpty(field) {
		var inputs = field.querySelectorAll('input[type="text"], input[type="radio"], input[type="checkbox"], textarea');
		if (!inputs.length) { return true; }
		var hasRadio = field.querySelector('input[type="radio"]') || field.querySelector('input[type="checkbox"]');
		if (hasRadio) {
			return !field.querySelector('input:checked');
		}
		for (var i = 0; i < inputs.length; i++) {
			if (String(inputs[i].value).trim() !== '') { return false; }
		}
		return true;
	}

	function missingNow() {
		var out = [];
		var title = document.querySelector('input#title, textarea#post-title-0, textarea#post-title-1');
		if (title && String(title.value).trim() === '') { out.push('Title'); }
		document.querySelectorAll('.sf-mb__field').forEach(function (field) {
			if (!field.querySelector('.sf-mb__req')) { return; }
			if (field.hidden || fieldEmpty(field)) { out.push(fieldLabel(field)); }
		});
		return out;
	}

	function showBanner(list) {
		var old = document.getElementById('sf-mb-precheck-banner');
		if (old) { old.remove(); }
		if (!list.length) { return; }
		var div = document.createElement('div');
		div.className = 'sf-mb-banner';
		div.id = 'sf-mb-precheck-banner';
		div.innerHTML = '<strong>Phase 1 — publishing is not blocked yet.</strong> Still missing: '
			+ list.map(function (t) { return '<span>' + t + '</span>'; }).join(', ')
			+ ' <button type="button" class="button-link" id="sf-mb-precheck-dismiss">dismiss</button>';
		var anchor = document.querySelector('.sf-mb');
		if (anchor && anchor.parentNode) {
			anchor.parentNode.insertBefore(div, anchor);
		} else {
			document.getElementById('wpbody-content').appendChild(div);
		}
	}

	document.addEventListener('click', function (e) {
		if (e.target.id === 'sf-mb-precheck-dismiss') {
			var b = document.getElementById('sf-mb-precheck-banner');
			if (b) { b.remove(); }
		}
	});

	function onPublish() {
		var list = missingNow();
		showBanner(list);
		if (list.length && window.wp && window.wp.data && window.wp.data.dispatch) {
			try {
				window.wp.data.dispatch('core/notices').createWarningNotice(
					'Phase 1: still missing — ' + list.join(', '),
					{ id: 'sf-mb-precheck', isDismissible: true }
				);
			} catch (err) { /* notices store unavailable — the DOM banner covers it */ }
		}
	}

	/* The block editor's publish button and the classic submit button share
	   no reliable class, so listen on the form and match by text. */
	document.addEventListener('click', function (e) {
		var btn = e.target.closest('button, input[type="submit"]');
		if (!btn) { return; }
		var text = (btn.textContent || btn.value || '').trim();
		if (/^(Publish|Update)$/.test(text)) {
			onPublish();
		}
	});
})();

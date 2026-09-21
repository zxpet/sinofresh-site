/*
 * SINO FRESH — batch H1 admin form helpers (vanilla JS, no libraries).
 *
 * Two jobs, both trivial by design:
 *   1. repeatable tables: "+ Add row" clones the table's last <tr>, clears
 *      every input inside it and appends it — so column names and parallel
 *      arrays (name="key[col][]") stay intact, and a moved row keeps its
 *      q/a or col/value pairing because the inputs travel with the <tr>;
 *   2. the gallery field: the WordPress media frame (wp.media, core) fills
 *      the hidden IDs input and the preview strip.
 *
 * Loaded on sf_formula edit screens and the Site Settings subpages only.
 */
(function () {
	'use strict';

	/* --- repeatable rows --------------------------------------------------- */
	function clearRow(tr) {
		tr.querySelectorAll('input[type="text"], input[type="hidden"], textarea').forEach(function (el) {
			if (el.type === 'hidden' && el.name && el.name.indexOf('[attachment_id]') !== -1) {
				el.value = '0';
				return;
			}
			el.value = '';
		});
		tr.querySelectorAll('.sf-containers__preview').forEach(function (p) { p.innerHTML = ''; });
	}

	document.addEventListener('click', function (e) {
		var add = e.target.closest('.sf-reptable__add');
		if (add) {
			var table = document.querySelector('table[data-sf-name="' + add.getAttribute('data-sf-name') + '"]');
			if (!table) { return; }
			var tbody = table.querySelector('tbody');
			var last = tbody.querySelector('tr:last-child');
			var tr;
			if (last) {
				tr = last.cloneNode(true);
				clearRow(tr);
			} else {
				/* Zero rows: nothing to clone. The server always renders one
				   row for generic tables, so this only guards against markup
				   edited by hand. */
				return;
			}
			tbody.appendChild(tr);
			var first = tr.querySelector('input[type="text"], textarea');
			if (first) { first.focus(); }
			return;
		}
		var del = e.target.closest('.sf-reptable__del');
		if (del) {
			var row = del.closest('tr');
			var tbody2 = row && row.parentNode;
			if (row && tbody2 && tbody2.querySelectorAll('tr').length > 1) {
				row.remove();
			} else if (row) {
				clearRow(row); /* never leave a table with zero rows */
			}
		}
	});

	/* --- gallery field ------------------------------------------------------ */
	function frameFor(onSelect) {
		if (!window.wp || !window.wp.media) { return null; }
		var frame = window.wp.media({ title: 'Choose images', multiple: true, library: { type: 'image' } });
		frame.on('select', function () {
			onSelect(frame.state().get('selection').map(function (a) {
				var att = a.toJSON();
				return { id: att.id, thumb: (att.sizes && att.sizes.thumbnail) ? att.sizes.thumbnail.url : att.url };
			}));
		});
		return frame;
	}

	document.addEventListener('click', function (e) {
		var btn = e.target.closest('.sf-mb__gallery-add');
		if (!btn) { return; }
		var field = btn.closest('.sf-mb__field');
		var hidden = field.querySelector('.sf-mb__gallery-ids');
		var preview = field.querySelector('.sf-mb__gallery-preview');
		var frame = frameFor(function (items) {
			hidden.value = items.map(function (i) { return i.id; }).join(',');
			preview.innerHTML = items.map(function (i) {
				return '<img src="' + i.thumb + '" alt="" width="80" height="80"/>';
			}).join('');
			var clear = field.querySelector('.sf-mb__gallery-clear');
			if (clear) { clear.hidden = items.length === 0; }
		});
		if (frame) { frame.open(); }
	});

	document.addEventListener('click', function (e) {
		var btn = e.target.closest('.sf-mb__gallery-clear');
		if (!btn) { return; }
		var field = btn.closest('.sf-mb__field');
		field.querySelector('.sf-mb__gallery-ids').value = '';
		field.querySelector('.sf-mb__gallery-preview').innerHTML = '';
		btn.hidden = true;
	});
})();

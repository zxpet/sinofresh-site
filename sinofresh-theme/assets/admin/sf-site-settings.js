/*
 * SINO FRESH — Site Settings + subpages row helpers (vanilla JS).
 *
 * Batch H1 makes the certifications table dynamic (add/remove rows instead
 * of eight fixed slots), and adds the Container Library page where each row
 * picks an image from the media library. Same clone-and-clear pattern as
 * sf-mb-tables.js, plus a wp.media single-image picker for containers.
 */
(function () {
	'use strict';

	/* --- certifications: dynamic rows -------------------------------------- */
	function certRowIndex(tr) {
		var input = tr.querySelector('input[name^="sf_certifications["]');
		return input ? (parseInt(input.name.match(/sf_certifications\[(\d+)\]/)[1], 10) || 0) : 0;
	}

	/* The certifications table is rendered without an id attribute, so locate
	 * it relative to the "+ Add row" button: <table> immediately precedes the
	 * button's <p>. Never assume #sf-certs-rows — that id does not exist. */
	function certsTbody() {
		var add = document.getElementById('sf-certs-add');
		if (!add) { return null; }
		var table = add.closest('p').previousElementSibling;
		return table ? table.querySelector('tbody') : null;
	}

	function renumberCertRows() {
		var tbody = certsTbody();
		if (!tbody) { return; }
		tbody.querySelectorAll('tr').forEach(function (tr, i) {
			tr.querySelectorAll('input').forEach(function (el) {
				el.name = el.name.replace(/sf_certifications\[\d+\]/, 'sf_certifications[' + i + ']');
			});
			var num = tr.querySelector('td:first-child');
			if (num) { num.textContent = String(i + 1); }
		});
	}

	document.addEventListener('click', function (e) {
		var add = e.target.closest('#sf-certs-add');
		if (add) {
			var tbody = certsTbody();
			var last = tbody && tbody.querySelector('tr:last-child');
			if (!last) { return; }
			var tr = last.cloneNode(true);
			tr.querySelectorAll('input[type="text"]').forEach(function (el) { el.value = ''; });
			tr.querySelectorAll('input[type="checkbox"]').forEach(function (el) { el.checked = false; });
			tbody.appendChild(tr);
			renumberCertRows();
			return;
		}
		var del = e.target.closest('.sf-certs-del');
		if (del) {
			var tbody2 = certsTbody();
			var row = del.closest('tr');
			if (tbody2 && row && tbody2.querySelectorAll('tr').length > 1) {
				row.remove();
				renumberCertRows();
			}
		}
	});

	/* --- container library rows --------------------------------------------- */
	document.addEventListener('click', function (e) {
		var add = e.target.closest('#sf-containers-add');
		if (add) {
			var tbody = document.querySelector('#sf-containers tbody');
			var last = tbody.querySelector('tr:last-child');
			if (!last) { return; }
			var tr = last.cloneNode(true);
			tr.querySelectorAll('input[type="text"]').forEach(function (el) { el.value = ''; });
			tr.querySelector('input[name^="sf_containers[attachment_id]"]').value = '0';
			tr.querySelector('.sf-containers__preview').innerHTML = '';
			tbody.appendChild(tr);
			return;
		}
		var del = e.target.closest('.sf-containers__del');
		if (del) {
			var tbody2 = document.querySelector('#sf-containers tbody');
			var row = del.closest('tr');
			if (row && tbody2.querySelectorAll('tr').length > 1) {
				row.remove();
			} else if (row) {
				row.querySelectorAll('input[type="text"]').forEach(function (el) { el.value = ''; });
			}
		}
	});

	/* single-image picker for one container row */
	document.addEventListener('click', function (e) {
		var pick = e.target.closest('.sf-containers__pick');
		if (!pick || !window.wp || !window.wp.media) { return; }
		var row = pick.closest('tr');
		var frame = window.wp.media({ title: 'Choose container image', multiple: false, library: { type: 'image' } });
		frame.on('select', function () {
			var att = frame.state().get('selection').first().toJSON();
			row.querySelector('input[name^="sf_containers[attachment_id]"]').value = String(att.id);
			var thumb = (att.sizes && att.sizes.thumbnail) ? att.sizes.thumbnail.url : att.url;
			row.querySelector('.sf-containers__preview').innerHTML =
				'<img src="' + thumb + '" alt="" width="80" height="80"/>';
		});
		frame.open();
	});
})();

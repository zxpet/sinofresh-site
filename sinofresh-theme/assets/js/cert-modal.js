/* SINO FRESH — certificate request modal (B4), Quality page only.

   The dialog itself is server-rendered in templates/page-quality.html: the
   shell, the heading and Gravity Forms Form 5 ("Request COA"). This file is
   only the behaviour.

   Every control that carries data-cert="<document key>" opens the dialog and
   writes that key into Form 5's hidden `certificate` field (id 10) — the same
   key inc/cert-download.php maps to a file. Delegated from the document, so
   the certificate rows, the COA buttons and the lightbox footer can be wired
   in any order without coming back here.

   The backdrop, its fade, the z-index stack and the scroll lock are the
   inquiry basket's (style.css section 45 is shared); this file only adds what
   a centred dialog needs on top of that.

   Success state (B4.3): Gravity Forms answers a submission by swapping the
   whole form node for the confirmation markup — the inline iframe postback
   handler does jQuery('#gform_wrapper_5').replaceWith(...). That markup is
   ours (the gform_confirmation_5 filter in functions.php) and carries the
   one-time download URL as JSON in data-payload, because the plain <a> it
   also contains is what a visitor without JavaScript would click. This file
   reads the payload, builds the success card and puts the untouched form back
   when the dialog is opened again.

   That filter also rebuilds the two nodes GF's own confirmation carries and
   its postback handler needs (#gf_5, the anchor it scrolls to, and
   #gform_confirmation_message_5, what it announces), so the handler runs to
   the end — see the comment above the return value in functions.php. */
(() => {
	'use strict';

	const modal = document.querySelector('.sf-certmodal');
	if (!modal) return;

	const panel = modal.querySelector('.sf-certmodal__panel');
	const body = modal.querySelector('.sf-certmodal__body');
	const closeBtn = modal.querySelector('.sf-certmodal__close');
	const lockClass = 'sf-certmodal-lock';

	const FORM_ID = '5';
	const TITLE_ID = 'sf-certmodal-title';

	/* Re-queried on every open: Gravity Forms replaces the whole
	   .gform_wrapper with the confirmation after a submission, so a reference
	   cached at load time can end up detached. */
	const certField = () => modal.querySelector('#input_5_10');
	const formWrapper = () => modal.querySelector('#gform_wrapper_' + FORM_ID);

	/* First real control of the form — the hidden field and the submit button
	   are skipped, so focus lands where the visitor has to type. */
	const firstControl = () => {
		const nodes = modal.querySelectorAll(
			'.gform_wrapper input:not([type="hidden"]):not([type="submit"]):not([type="button"]),'
			+ '.gform_wrapper select:not([hidden]), .gform_wrapper textarea'
		);
		for (let i = 0; i < nodes.length; i++) {
			if (!nodes[i].disabled && nodes[i].offsetParent !== null) return nodes[i];
		}
		return null;
	};

	/* The confirmation markup once Gravity Forms has swapped it in. */
	const resultNode = () => modal.querySelector('[data-payload]');

	/* data-payload is the machine-readable copy of the confirmation
	   (functions.php); the flat data-* attributes next to it are the fallback
	   when that JSON cannot be parsed. Either way the card is built from
	   strings only, never from markup. */
	const parsePayload = () => {
		const node = resultNode();
		if (!node) return null;
		const attr = (name) => node.getAttribute(name) || '';

		let data = null;
		try {
			data = JSON.parse(node.getAttribute('data-payload'));
		} catch (e) {
			data = null;
		}
		if (!data || typeof data !== 'object') data = {};

		const text = (key, fallback) => (typeof data[key] === 'string' && data[key] ? data[key] : fallback);

		const payload = {
			download_url: text('download_url', attr('data-download-url')),
			email_sent_to: text('email_sent_to', attr('data-email-sent-to')),
			certificate: typeof data.certificate === 'string' ? data.certificate : '',
			label: typeof data.label === 'string' ? data.label : '',
			attached: data.attached === true || data.attached === 'true',
		};
		// no file behind the token means nothing was attached, whatever the payload says
		if (!payload.download_url) payload.attached = false;
		if (!payload.email_sent_to && !payload.download_url) return null;
		return payload;
	};

	/* The pristine form, kept because a submission replaces the form node
	   itself — without this copy the second open would have nothing to show.
	   Taken before any submission, and only when the page really does still
	   hold the form: a postback without JavaScript reloads straight into the
	   confirmation. */
	const pristineForm = (() => {
		const node = formWrapper();
		return node && !resultNode() ? node.outerHTML : '';
	})();

	let opener = null;

	/* Icon drawn inline: a check when the file is on its way, an envelope when
	   the team still has to send it. */
	const ICON_CHECK = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
		+ 'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
		+ '<path d="M4.75 12.5l4.75 4.75L19.25 7.5"/></svg>';
	const ICON_MAIL = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
		+ 'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
		+ '<rect x="2.75" y="5.5" width="18.5" height="13" rx="2"/>'
		+ '<path d="M3.5 7.75L12 13.5l8.5-5.75"/></svg>';

	const successCard = (payload) => {
		const card = document.createElement('div');
		card.className = 'sf-certmodal__success';

		const icon = document.createElement('span');
		icon.className = 'sf-certmodal__success-icon';
		icon.innerHTML = payload.download_url ? ICON_CHECK : ICON_MAIL;
		card.appendChild(icon);

		const title = document.createElement('p');
		title.className = 'sf-certmodal__success-title';
		title.textContent = 'Request received';
		card.appendChild(title);

		const note = document.createElement('p');
		note.className = 'sf-certmodal__success-note';
		note.appendChild(document.createTextNode(
			payload.attached ? "We've sent the certificate to " : "We'll email the certificate to "));
		const mail = document.createElement('strong');
		mail.textContent = payload.email_sent_to || 'your email address';
		note.appendChild(mail);
		note.appendChild(document.createTextNode(payload.attached ? '.' : ' shortly.'));
		card.appendChild(note);

		if (payload.download_url) {
			const cta = document.createElement('a');
			cta.className = 'sf-certmodal__success-btn';
			cta.href = payload.download_url;
			// same origin: keeps the token URL from navigating away, and the
			// file name still comes from the response's Content-Disposition
			cta.setAttribute('download', '');
			cta.textContent = 'Download now';
			card.appendChild(cta);
		}

		const fine = payload.attached
			? ['The download link is valid for 24 hours and can be used once.', "We'll contact you within 24 hours."]
			: ["We'll contact you within 24 hours."];
		fine.forEach((line) => {
			const p = document.createElement('p');
			p.className = 'sf-certmodal__success-fine';
			p.textContent = line;
			card.appendChild(p);
		});

		const closeButton = document.createElement('button');
		closeButton.type = 'button';
		closeButton.className = 'sf-certmodal__success-close';
		closeButton.textContent = 'Close';
		closeButton.addEventListener('click', () => close());
		card.appendChild(closeButton);

		return card;
	};

	/* The whole block Gravity Forms swapped in, not just the card: functions.php
	   wraps the card in GF's own anchor (#gf_5), wrapper and message divs so the
	   postback handler can scroll and announce as it expects to. Parking only
	   the card would leave two empty nodes and a duplicate id behind for the
	   next submission, so every node of the block is marked together. */
	const parkConfirmation = () => {
		const card = modal.querySelector('.sf-cert-result');
		if (!card) return;
		card.classList.add('sf-certmodal__stale');

		const wrap = card.closest('.gform_confirmation_wrapper');
		if (!wrap) return;                       // bare card: nothing else to park
		wrap.classList.add('sf-certmodal__stale');

		const anchor = wrap.previousElementSibling;
		if (anchor && anchor.id === 'gf_' + FORM_ID) anchor.classList.add('sf-certmodal__stale');
	};

	const showSuccess = () => {
		const payload = parsePayload();
		if (!payload || modal.classList.contains('is-success')) return;

		modal.classList.add('is-success');
		/* The dialog heading is hidden in this state (style.css), so the card
		   carries the accessible name instead of a hidden h2. */
		panel.removeAttribute('aria-labelledby');
		panel.setAttribute('aria-label', 'Request received');

		// the confirmation markup stays in the DOM — it is the copy a visitor
		// without JavaScript clicks — but never next to the card
		parkConfirmation();

		body.appendChild(successCard(payload));

		/* Gravity Forms clears this flag itself, a few lines after scrolling to
		   #gf_5 — which now exists, so that path no longer throws. Kept as a
		   belt-and-braces reset: a stale flag is what silently swallows the
		   next submission. */
		window['gf_submitting_' + FORM_ID] = false;
	};

	/* Back to a usable form. Runs on open rather than on close so the card is
	   not yanked out from under the closing dialog. */
	const reset = () => {
		if (!modal.classList.contains('is-success')) return;

		modal.classList.remove('is-success');
		panel.removeAttribute('aria-label');
		panel.setAttribute('aria-labelledby', TITLE_ID);

		const card = modal.querySelector('.sf-certmodal__success');
		if (card) card.remove();

		// the parked confirmation block: card, wrapper, message div, anchor
		modal.querySelectorAll('.sf-certmodal__stale').forEach((node) => node.remove());

		// nothing was snapshotted (the page loaded straight into a
		// confirmation): leave the card up rather than empty the panel
		if (!pristineForm || formWrapper()) return;

		const holder = document.createElement('div');
		holder.innerHTML = pristineForm;
		body.appendChild(holder.firstElementChild);

		window['gf_submitting_' + FORM_ID] = false;
		if (window.gform && window.gform.core && window.gform.core.triggerPostRenderEvents) {
			window.gform.core.triggerPostRenderEvents(parseInt(FORM_ID, 10), 1);
		}
	};

	const open = (cert, trigger) => {
		reset();
		opener = trigger || null;

		const field = certField();
		if (field) field.value = cert || '';
		body.scrollTop = 0;

		modal.hidden = false;
		document.body.classList.add(lockClass);

		// one frame between "displayed" and "is-open" so the fade and the rise
		// actually play — same shape as the basket drawer
		requestAnimationFrame(() => {
			modal.classList.add('is-open');
			const target = firstControl() || closeBtn;
			if (target) target.focus({ preventScroll: true });
		});
	};

	const close = () => {
		if (modal.hidden) return;
		modal.classList.remove('is-open');
		modal.hidden = true;
		document.body.classList.remove(lockClass);
		if (opener) opener.focus();
	};

	/* One delegate for every trigger, whether it is an <a> or a <button>. B4.5
	   turned them into <a href="/contact/#quote" data-cert="…"> so a visitor
	   without JavaScript still reaches an inquiry form; the preventDefault only
	   takes effect once this file is running, which is exactly the upgrade.
	   Both element types fire a click on Enter, so keyboard access is native —
	   nothing extra to bind. */
	document.addEventListener('click', (e) => {
		if (!e.target || typeof e.target.closest !== 'function') return;
		const trigger = e.target.closest('[data-cert]');
		if (!trigger) return;
		// a modifier key means "open in a new tab" — leave that alone
		if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0) return;
		e.preventDefault();
		open(trigger.getAttribute('data-cert'), trigger);
	});

	closeBtn.addEventListener('click', close);

	// the backdrop is the dialog element itself — anything inside the panel
	// is a normal click
	modal.addEventListener('click', (e) => {
		if (!panel.contains(e.target)) close();
	});

	document.addEventListener('keydown', (e) => {
		if (modal.hidden || e.key !== 'Escape') return;
		e.preventDefault();
		close();
	});

	/* Two ways in, one handler. The documented signal is the
	   gform_confirmation_loaded event, which the inline postback handler
	   triggers; the observer covers the paths where the confirmation arrives
	   without that handler (no Gravity Forms script at all, or a markup change
	   that stops the event). showSuccess() is idempotent, so both firing is
	   fine. */
	const onConfirmation = () => showSuccess();

	if (window.jQuery) {
		window.jQuery(document).on('gform_confirmation_loaded', onConfirmation);
	}
	new MutationObserver(onConfirmation).observe(body, { childList: true });

	/* Insurance for the one path that can strand a confirmation: the dialog
	   opens on JavaScript but the Gravity Forms bundle never arrives, so the
	   submit becomes a normal POST and the confirmation is rendered into the
	   (still hidden) dialog. If a confirmation is already in the markup on
	   load, this is that page — show it instead of leaving the visitor with a
	   form that looks like it did nothing. */
	if (resultNode()) {
		modal.hidden = false;
		modal.classList.add('is-open');
		document.body.classList.add(lockClass);
		showSuccess();
	}
})();

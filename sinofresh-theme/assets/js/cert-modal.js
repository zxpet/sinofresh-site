/* SINO FRESH — certificate request modal (B4), Quality page only.

   The dialog itself is server-rendered in templates/page-quality.html: the
   shell, the heading and Fluent Forms Form 11 ("Request COA", the Gravity
   Forms Form 5 twin). This file is only the behaviour.

   Every control that carries data-cert="<document key>" opens the dialog and
   writes that key into Form 11's hidden `certificate_10` field — the same
   key inc/cert-download.php maps to a file. Delegated from the document, so
   the certificate rows, the COA buttons and the lightbox footer can be wired
   in any order without coming back here.

   The backdrop, its fade, the z-index stack and the scroll lock are the
   inquiry basket's (style.css section 45 is shared); this file only adds what
   a centred dialog needs on top of that.

   Success state (B4.3): Fluent Forms answers a submission over AJAX and
   renders the confirmation message (functions.php's
   fluentform/form_submission_confirmation filter) in a .ff-message-success
   node after the form, hiding the form itself when the confirmation's
   samePageFormBehavior is "hide_form". The message is deliberately plain
   HTML — FF strips data-* attributes (kses) and brace payloads
   (ShortCodeParser) from confirmations — so the payload is read back from
   the DOM: the one-time download URL is the card link's href and the email
   is the <strong> in the note. This file listens for the native
   `fluentform_submission_success` CustomEvent FF dispatches on `document`,
   builds the success card, and puts the untouched form back when the dialog
   is opened again. A MutationObserver covers paths where the event does not
   arrive; showSuccess() is idempotent, so both firing is fine. */
(() => {
	'use strict';

	const modal = document.querySelector('.sf-certmodal');
	if (!modal) return;

	const panel = modal.querySelector('.sf-certmodal__panel');
	const body = modal.querySelector('.sf-certmodal__body');
	const closeBtn = modal.querySelector('.sf-certmodal__close');
	const lockClass = 'sf-certmodal-lock';

	const FORM_KEY = 'fluentform_11';
	const TITLE_ID = 'sf-certmodal-title';

	/* Re-queried on every open: the form node survives submissions (FF hides
	   it), but reset() may have restored it from a hidden state, so nothing
	   here may be cached from a stale reference. */
	const certField = () => modal.querySelector('[name="certificate_10"]');
	const formWrapper = () => modal.querySelector('#' + FORM_KEY);

	/* First real control of the form — the hidden field and the submit button
	   are skipped, so focus lands where the visitor has to type. */
	const firstControl = () => {
		const nodes = modal.querySelectorAll(
			'.ff-el-form-control'
		);
		for (let i = 0; i < nodes.length; i++) {
			if (!nodes[i].disabled && nodes[i].offsetParent !== null) return nodes[i];
		}
		return null;
	};

	/* The confirmation card once FF has rendered it (functions.php). */
	const resultNode = () => modal.querySelector('.sf-cert-result');

	/* The payload is the card's DOM: the download URL is the CTA link's href,
	   the email is the <strong> inside the note, and "attached" is simply
	   whether the link exists (no file behind the token means nothing was
	   attached — functions.php only renders the link when it is). */
	const parsePayload = () => {
		const card = resultNode();
		if (!card) return null;
		const link = card.querySelector('.sf-cert-result__btn');
		const mail = card.querySelector('.sf-cert-result__note strong');
		const payload = {
			download_url: link ? link.getAttribute('href') || '' : '',
			email_sent_to: mail ? mail.textContent.trim() : '',
			attached: !!link,
		};
		if (!payload.download_url) payload.attached = false;
		if (!payload.email_sent_to && !payload.download_url) return null;
		return payload;
	};

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

	/* FF's message node (the .ff-message-success wrapper around the card) is
	   parked stale — it is the copy a visitor without JavaScript would rely
	   on, but it must never sit next to the success card. The card itself is
	   marked stale too: style.css re-shows a hidden dialog that holds an
	   unclaimed .sf-cert-result (the no-JS postback insurance, and the same
	   rule must not re-open a dialog the visitor just closed). Removed on
	   reset; removing the wrapper takes the card with it. */
	const parkConfirmation = () => {
		const card = modal.querySelector('.sf-cert-result');
		if (card) card.classList.add('sf-certmodal__stale');
		const wrap = modal.querySelector('.ff-message-success');
		if (wrap) wrap.classList.add('sf-certmodal__stale');
	};

	const showSuccess = () => {
		const payload = parsePayload();
		if (!payload || modal.classList.contains('is-success')) return;

		modal.classList.add('is-success');
		/* The dialog heading is hidden in this state (style.css), so the card
		   carries the accessible name instead of a hidden h2. */
		panel.removeAttribute('aria-labelledby');
		panel.setAttribute('aria-label', 'Request received');

		parkConfirmation();

		body.appendChild(successCard(payload));
	};

	/* Back to a usable form. Runs on open rather than on close so the card is
	   not yanked out from under the closing dialog. FF only hides the form
	   (ff_force_hide) — unlike GF it never replaced the node — so restoring
	   is: drop the stale message, unhide, done. The hidden certificate field
	   is cleared so the next open() writes it fresh. */
	const reset = () => {
		if (!modal.classList.contains('is-success')) return;

		modal.classList.remove('is-success');
		panel.removeAttribute('aria-label');
		panel.setAttribute('aria-labelledby', TITLE_ID);

		const card = modal.querySelector('.sf-certmodal__success');
		if (card) card.remove();

		modal.querySelectorAll('.sf-certmodal__stale').forEach((node) => node.remove());

		const form = formWrapper();
		if (form) {
			form.classList.remove('ff_force_hide');
			form.style.display = '';
		}
		const field = certField();
		if (field) field.value = '';
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

	/* Two ways in, one handler. The documented signal is the native
	   fluentform_submission_success CustomEvent, filtered to this form —
	   form-submission.js dispatches it on document for every FF form on the
	   page. The observer covers the paths where the event does not arrive
	   (no FF script, or a markup change); it must watch the subtree, because
	   FF inserts the message node below the form, not as a direct child of
	   the modal body. */
	const onConfirmation = (e) => {
		if (e && e.detail && e.detail.form && e.detail.form.id !== FORM_KEY) return;
		showSuccess();
	};

	document.addEventListener('fluentform_submission_success', onConfirmation);
	new MutationObserver(() => showSuccess()).observe(body, { childList: true, subtree: true });

	/* Insurance for the no-JS-postback edge: if a confirmation is already in
	   the markup on load, show it instead of leaving the visitor with a form
	   that looks like it did nothing. */
	if (resultNode()) {
		modal.hidden = false;
		modal.classList.add('is-open');
		document.body.classList.add(lockClass);
		showSuccess();
	}
})();

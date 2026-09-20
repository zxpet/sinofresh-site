/* B4.3 — certificate modal success state.

   Submits Gravity Forms Form 5 for real (the iframe postback, not a mocked
   payload) and checks what the dialog does with the confirmation:

     1  the dialog switches to the success state
     2  Download now points at the one-time URL and really returns the file
     3  a document with no file (HACCP) shows no download button, and says so
     4  the address the certificate went to is the address that was typed
     5  Close closes the dialog
     6  the markup a visitor without JavaScript clicks is in the postback
     7  375px: the card fits, no sideways scroll
     8  opening it again gives a clean form, and a second request works

   Run:  NODE_PATH=~/.workbuddy/binaries/node/workspace/node_modules \
         node tools/_cert_success_test.js
*/
const { chromium } = require('playwright-core');
const fs = require('fs');
const os = require('os');
const path = require('path');

const BASE = 'http://sinofresh.local/quality/';
const CERTS_DIR = path.join(os.homedir(), 'Local Sites/sinofresh/app/private-certs');

let pass = 0, fail = 0;
const check = (name, ok, note) => {
	if (ok) { pass++; console.log('  ok   ' + name + (note ? '  [' + note + ']' : '')); }
	else { fail++; console.log('  FAIL ' + name + (note ? '  [' + note + ']' : '')); }
};

/* Gravity Forms' postback handler scrolls to #gf_5 and announces
   #gform_confirmation_message_5. B4.3.5 rebuilt both nodes around our
   confirmation, so this error must never appear again — the assertion below
   fails the run if it does. */
const GF_ID_ERROR = "Cannot read properties of undefined (reading 'top')";

const VIEWPORTS = [
	{ label: '1440', width: 1440, height: 900 },
	{ label: '375', width: 375, height: 812 },
];

const CASES = [
	{ cert: 'fda', label: 'FDA Registration', file: 'cert-fda.webp', download: true },
	{ cert: 'haccp', label: 'HACCP Certificate', file: null, download: false },
];

const quietExtras = async (p) => {
	await p.addStyleTag({ content: '.sf-cookie-banner,.sf-float-stack{display:none !important}' });
};

/* An injected stand-in for the certificate row button that B4.5 wires up —
   the data-cert delegation is what is under test, not the markup. */
const armTrigger = (p, cert) => p.evaluate((c) => {
	let b = document.getElementById('sf-test-trigger');
	if (!b) {
		b = document.createElement('button');
		b.id = 'sf-test-trigger';
		b.type = 'button';
		b.style.cssText = 'position:fixed;top:220px;left:24px;z-index:20002;padding:8px 12px';
		document.body.appendChild(b);
	}
	b.setAttribute('data-cert', c);
	b.textContent = c;
}, cert);

const readCard = (p) => p.evaluate(() => {
	const modal = document.querySelector('.sf-certmodal');
	const card = modal.querySelector('.sf-certmodal__success');
	const btn = card && card.querySelector('.sf-certmodal__success-btn');
	const close = card && card.querySelector('.sf-certmodal__success-close');
	const stale = modal.querySelector('.sf-cert-result');
	const rect = card ? card.getBoundingClientRect() : null;
	return {
		success: modal.classList.contains('is-success'),
		open: modal.classList.contains('is-open') && !modal.hidden,
		panelLabel: modal.querySelector('.sf-certmodal__panel').getAttribute('aria-label'),
		labelledby: modal.querySelector('.sf-certmodal__panel').getAttribute('aria-labelledby'),
		headHidden: getComputedStyle(modal.querySelector('.sf-certmodal__head')).display === 'none',
		iconSvg: !!(card && card.querySelector('.sf-certmodal__success-icon svg')),
		iconSize: card ? Math.round(card.querySelector('.sf-certmodal__success-icon').getBoundingClientRect().width) : 0,
		title: card ? card.querySelector('.sf-certmodal__success-title').textContent : '',
		note: card ? card.querySelector('.sf-certmodal__success-note').textContent : '',
		mail: card ? (card.querySelector('.sf-certmodal__success-note strong') || {}).textContent : '',
		hasDownload: !!btn,
		downloadHref: btn ? btn.getAttribute('href') : '',
		downloadAttr: btn ? btn.hasAttribute('download') : false,
		fine: card ? Array.from(card.querySelectorAll('.sf-certmodal__success-fine')).map((n) => n.textContent) : [],
		hasClose: !!close,
		closeHeight: close ? Math.round(close.getBoundingClientRect().height) : 0,
		btnHeight: btn ? Math.round(btn.getBoundingClientRect().height) : 0,
		btnWidth: btn ? Math.round(btn.getBoundingClientRect().width) : 0,
		cardWidth: rect ? Math.round(rect.width) : 0,
		staleParked: !!stale && stale.classList.contains('sf-certmodal__stale'),
		staleVisible: !!stale && getComputedStyle(stale).display !== 'none',
		formBack: !!modal.querySelector('#gform_wrapper_5'),
		submittingFlag: window.gf_submitting_5,
		bodyText: card ? card.textContent.replace(/\s+/g, ' ').trim() : '',
		overflow: document.documentElement.scrollWidth - window.innerWidth,
		bodyLocked: document.body.classList.contains('sf-certmodal-lock'),
	};
});

const fillAndSubmit = async (p, email, company) => {
	await p.fill('#input_5_1', company);
	await p.fill('#input_5_2', 'Dana Reyes');
	await p.fill('#input_5_3', email);
	await p.click('#gform_submit_button_5');
	await p.waitForSelector('.sf-certmodal.is-success', { timeout: 15000 }).catch(() => {});
	await p.waitForTimeout(300);
};

(async () => {
	const browser = await chromium.launch();

	for (const vp of VIEWPORTS) {
		const ctx = await browser.newContext({ viewport: { width: vp.width, height: vp.height }, acceptDownloads: true });
		const p = await ctx.newPage();
		const errors = [];
		let postback = null;

		p.on('pageerror', (e) => errors.push(e.message));
		p.on('response', async (r) => {
			if (r.request().method() === 'POST' && r.url().startsWith(BASE)) {
				try { postback = await r.text(); } catch (e) { /* stream already consumed */ }
			}
		});

		console.log('\n== viewport ' + vp.label + ' ==');

		for (const c of CASES) {
			const email = 'dana.' + c.cert + vp.label + '@acmepetnutrition.com';
			postback = null;

			await p.goto(BASE, { waitUntil: 'load' });
			await quietExtras(p);
			await p.waitForTimeout(2200);
			await armTrigger(p, c.cert);
			await p.click('#sf-test-trigger');
			await p.waitForSelector('.sf-certmodal.is-open', { timeout: 5000 });
			await p.waitForTimeout(250);
			check(vp.label + ' ' + c.cert + ' 0. dialog opened on the trigger, field pre-filled',
				(await p.inputValue('#input_5_10')) === c.cert);

			await fillAndSubmit(p, email, 'Acme Pet Nutrition');

			const s = await readCard(p);
			const tag = vp.label + ' ' + c.cert + ' ';

			check(tag + '1. dialog switched to the success state', s.success === true && s.open === true);
			check(tag + '1b. the form is gone, the confirmation is parked out of sight',
				s.formBack === false && s.staleParked === true && s.staleVisible === false);
			check(tag + '1c. the heading gives way to the card',
				s.headHidden === true && s.panelLabel === 'Request received' && s.labelledby === null);
			check(tag + '1d. icon + title', s.iconSvg === true && s.iconSize === (vp.label === '375' ? 44 : 48) && s.title === 'Request received');
			check(tag + '4. the address shown is the one that was typed',
				s.note.indexOf(email) >= 0 && s.mail === email, s.note);
			check(tag + '4b. copy matches what happened',
				c.download ? s.note.indexOf("We've sent the certificate to") === 0
					: s.note.indexOf("We'll email the certificate to") === 0 && /shortly\.$/.test(s.note));
			check(tag + '3. download button presence follows the payload',
				c.download ? s.hasDownload === true : s.hasDownload === false);
			check(tag + '3b. the 24 hour line', s.fine.join(' | ').indexOf("We'll contact you within 24 hours.") >= 0, s.fine.join(' | '));
			check(tag + '3c. the one-time link note follows the button',
				c.download ? s.fine.some((t) => t.indexOf('valid for 24 hours') >= 0) : s.fine.length === 1);
			check(tag + '5. Close button, 44/48px tall', s.hasClose === true && s.closeHeight === (vp.label === '375' ? 44 : 48));
			check(tag + '8. GF submission flag cleared (its handler died before it could)',
				s.submittingFlag === false, String(s.submittingFlag));
			check(tag + '7. card within the panel, no sideways scroll',
				s.cardWidth > 0 && s.cardWidth <= vp.width && s.overflow <= 1, 'card=' + s.cardWidth + ' overflow=' + s.overflow);

			if (c.download) {
				check(tag + '2. Download now is a full-width link with the download hint',
					s.btnWidth === s.cardWidth && s.btnHeight === (vp.label === '375' ? 44 : 48) && s.downloadAttr === true && /cert-download\?cert=.+&(amp;)?token=[0-9a-f]{40}/.test(s.downloadHref),
					'w=' + s.btnWidth + ' h=' + s.btnHeight);

				/* really fetch it: the bytes must be the certificate on disk */
				const url = s.downloadHref;
				const res = await p.evaluate(async (u) => {
					const r = await fetch(u);
					const b = await r.arrayBuffer();
					let bin = '';
					const bytes = new Uint8Array(b);
					for (let i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
					return { status: r.status, type: r.headers.get('content-type'), disp: r.headers.get('content-disposition'), b64: btoa(bin), len: bytes.length };
				}, url);
				const expected = fs.readFileSync(path.join(CERTS_DIR, c.file));
				const got = Buffer.from(res.b64, 'base64');
				check(tag + '2b. download returns the certificate byte for byte',
					res.status === 200 && got.equals(expected),
					res.status + ' ' + res.type + ' ' + res.len + 'B vs ' + expected.length + 'B');
			}

			const plainLink = /<a class="sf-cert-result__btn" href="[^"]*cert-download[^"]*token=[0-9a-f]{40}[^"]*">Download now<\/a>/.test(postback || '');
			check(tag + '6. the postback carries the plain <a> a visitor without JavaScript clicks',
				c.download ? plainLink === true : (plainLink === false && /is not published on the website/.test(postback || '')),
				(postback ? postback.length + 'B' : 'no postback captured') + ', plain link=' + plainLink);

			/* close, then open again: a clean form, and a second request that works */
			await p.click('.sf-certmodal__success-close');
			await p.waitForTimeout(350);
			const closed = await p.evaluate(() => ({
				hidden: document.querySelector('.sf-certmodal').hidden,
				locked: document.body.classList.contains('sf-certmodal-lock'),
				success: document.querySelector('.sf-certmodal').classList.contains('is-success'),
				card: !!document.querySelector('.sf-certmodal__success'),
			}));
			check(tag + '5b. Close closes the dialog and releases the page',
				closed.hidden === true && closed.locked === false);
			check(tag + '8b. the panel is left alone on close (the swap happens out of sight, on the next open)',
				closed.success === true && closed.card === true);

			await p.click('#sf-test-trigger');
			await p.waitForTimeout(400);
			const reopened = await readCard(p);
			const values = await p.evaluate(() => ({
				company: (document.querySelector('#input_5_1') || {}).value,
				person: (document.querySelector('#input_5_2') || {}).value,
				mail: (document.querySelector('#input_5_3') || {}).value,
				cert: (document.querySelector('#input_5_10') || {}).value,
				back: !!document.querySelector('#gform_wrapper_5'),
			}));
			check(tag + '8c. reopening gives the form back, empty, with the right key',
				reopened.formBack === true && values.back === true && values.company === '' && values.person === ''
					&& values.mail === '' && values.cert === c.cert, JSON.stringify(values));
			check(tag + '8d. the parked confirmation is cleared and the card is gone',
				reopened.staleParked === false && reopened.success === false);

			const second = 'second.' + c.cert + vp.label + '@acmepetnutrition.com';
			await fillAndSubmit(p, second, 'Acme Pet Nutrition');
			const again = await readCard(p);
			check(tag + '8e. a second request goes through on the restored form',
				again.success === true && again.mail === second, again.mail);
			await p.click('.sf-certmodal__success-close');
			await p.waitForTimeout(250);
		}

		/* the one-line CSS fallback for a postback that arrives without our script */
		const reveal = await p.evaluate(() => {
			const modal = document.querySelector('.sf-certmodal');
			modal.hidden = true;
			modal.classList.remove('is-open');
			const fake = document.createElement('div');
			fake.className = 'sf-cert-result';
			fake.setAttribute('data-payload', '{}');
			fake.textContent = 'stub';
			document.querySelector('.sf-certmodal__body').appendChild(fake);
			const unwrapped = getComputedStyle(modal).display;
			fake.classList.add('sf-certmodal__stale');
			const parked = getComputedStyle(modal).display;
			fake.remove();
			return { unwrapped, parked };
		});
		check(vp.label + ' 6b. a confirmation left in the hidden dialog reveals it, a parked one does not',
			reveal.unwrapped === 'flex' && reveal.parked === 'none', JSON.stringify(reveal));

		/* B4.3.5: the confirmation now carries GF's own #gf_5 anchor and
		   wrapper, so the postback handler runs to the end — no page error at
		   all, not even the one that used to abort it. */
		check(vp.label + ' 10. no script errors at all', errors.length === 0, errors.join(' / ') || 'clean');

		await ctx.close();
	}

	await browser.close();
	console.log('\n' + pass + ' passed, ' + fail + ' failed');
	process.exit(fail ? 1 : 0);
})();

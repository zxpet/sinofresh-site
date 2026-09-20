/* B4.3.5 — the confirmation Gravity Forms is handed must carry the nodes GF's
   own postback handler expects.

   handle_confirmation() wraps a message in

     <div id='gf_5' class='gform_anchor'>                     ← the scroll target
     <div id='gform_confirmation_wrapper_5'>
       <div id='gform_confirmation_message_5'>…message…</div>  ← what wp.a11y.speak reads
     </div>

   A gform_confirmation_5 filter replaces all of that, and the page's inline
   handler does jQuery('#gf_5').offset() a few lines before it clears
   gf_submitting_5 — so a confirmation without the anchor threw a TypeError
   there, left the flag set and swallowed the next submission. (The form's own
   markup does contain an anchor, but the handler removes #gform_wrapper_5 with
   the very replaceWith that inserts the confirmation, so it is already
   detached by then.)

   What is checked, per scenario:

     A  with the theme's JavaScript
        1  the rebuilt markup: anchor + wrapper + message div around our card
        2  it is the wrapper's previous sibling, outside the card
        3  the card and its payload are untouched
        4  GF's handler reaches its last line: event fired, message announced
        5  no script error at all (the old TypeError is gone)
        6  the flag is cleared, and a second request really goes through
     B  with cert-modal.js blocked, so nothing but Gravity Forms is running
        1  the handler still completes — event fired, message announced
        2  the flag is cleared by GF itself (only GF is loaded here)
        3  the confirmation is visible in the dialog a visitor would see
        4  its plain <a> downloads the real file, byte for byte
     C  back to a clean form
        1  nothing of the confirmation is left behind: no duplicate #gf_5
        2  the form is back, the certificate field carries the new key

   Run:  NODE_PATH=~/.workbuddy/binaries/node/workspace/node_modules \
         node tools/_cert_gf5_wrap_test.js
*/
const { chromium } = require('playwright-core');
const crypto = require('crypto');
const fs = require('fs');
const os = require('os');
const path = require('path');

const BASE = 'http://sinofresh.local/quality/';
const CERTS_DIR = path.join(os.homedir(), 'Local Sites/sinofresh/app/private-certs');
const EMAIL = 'dana@acmepetnutrition.com';

/* The error this task removes. */
const GF_ID_ERROR = "Cannot read properties of undefined (reading 'top')";
/* Unrelated Gravity Forms quirk, and only reachable in scenario B: GF's
   post-render helper stores #gform_visibility_test_5 on the first postback and
   removes it on a later one. B is synthetic (cert-modal.js is blocked, then the
   dialog is forced open by hand, and the submit follows within the 200ms
   debounce window), so the leftover node can be gone by the time the stored
   reference is used. The real flow never submits that fast. Recorded here, not
   asserted away silently. */
const GF_POSTRENDER_ERROR = "Cannot read properties of null (reading 'removeChild')";

let pass = 0, fail = 0;
const check = (name, ok, note) => {
	if (ok) { pass++; console.log('  ok   ' + name + (note ? '  [' + note + ']' : '')); }
	else { fail++; console.log('  FAIL ' + name + (note ? '  [' + note + ']' : '')); }
};

const sha = (buf) => crypto.createHash('sha256').update(buf).digest('hex');

/* Two side effects of GF's handler sit *after* the scroll line: the jQuery
   event it triggers, and the announcement it makes. Both are evidence the
   handler ran to the end. The announcement is read from the live region rather
   than by wrapping wp.a11y.speak — that property is getter-only, so a spy
   assigned to it silently never runs. */
const armSpies = (p) => p.evaluate(() => {
	window.__confEvents = 0;
	if (window.jQuery) {
		window.jQuery(document).on('gform_confirmation_loaded', () => { window.__confEvents++; });
	}
	['a11y-speak-polite', 'a11y-speak-assertive'].forEach((id) => {
		const n = document.getElementById(id);
		if (n) n.textContent = '';
	});
});

const readSpies = (p) => p.evaluate(() => ({
	events: window.__confEvents,
	spoken: ['a11y-speak-polite', 'a11y-speak-assertive']
		.map((id) => (document.getElementById(id) || {}).textContent || '')
		.filter((t) => t.length > 0),
	submittingFlag: window.gf_submitting_5,
}));

const submit = async (p, cert) => {
	await p.fill('#input_5_1', 'Acme Pet Nutrition');
	await p.fill('#input_5_2', 'Dana Test');
	await p.fill('#input_5_3', EMAIL);
	await p.evaluate((c) => {
		const f = document.querySelector('#input_5_10');
		if (f) f.value = c;
	}, cert);
	await p.click('#gform_submit_button_5');
};

const confirmationIn = (p) => p.evaluate(() => {
	const modal = document.querySelector('.sf-certmodal');
	const wrap = modal.querySelector('#gform_confirmation_wrapper_5');
	const msg = modal.querySelector('#gform_confirmation_message_5');
	const anchor = modal.querySelector('#gf_5');
	const card = modal.querySelector('.sf-cert-result');
	const plain = card && card.querySelector('.sf-cert-result__btn');
	let data = null;
	try { data = JSON.parse(card.getAttribute('data-payload')); } catch (e) { data = null; }

	return {
		anchorCount: modal.querySelectorAll('#gf_5').length,
		wrapCount: modal.querySelectorAll('#gform_confirmation_wrapper_5').length,
		anchorIsGfClass: !!(anchor && anchor.classList.contains('gform_anchor')),
		anchorTabindex: anchor ? anchor.getAttribute('tabindex') : null,
		anchorIsSiblingBefore: !!(anchor && wrap && wrap.previousElementSibling === anchor),
		anchorOutsideCard: !!(anchor && card && !anchor.contains(card) && !wrap.contains(anchor)),
		wrapIsGfClass: !!(wrap && wrap.classList.contains('gform_confirmation_wrapper')),
		msgIsGfClass: !!(msg && msg.classList.contains('gform_confirmation_message')),
		cardInsideMsg: !!(msg && card && card.parentElement === msg),
		payload: data,
		plainHref: plain ? plain.getAttribute('href') : null,
		plainText: plain ? plain.textContent.trim() : null,
		staleCount: modal.querySelectorAll('.sf-certmodal__stale').length,
		success: modal.classList.contains('is-success'),
		cardVisible: !!(card && card.getClientRects().length),
	};
});

const cleanState = (p) => p.evaluate(() => {
	const modal = document.querySelector('.sf-certmodal');
	return {
		anchorCount: modal.querySelectorAll('#gf_5').length,
		/* Gravity Forms renders its own anchor inside the form wrapper, so the
		   check is not "no #gf_5" but "no orphan": every remaining one belongs
		   to the form. */
		anchorsInsideForm: [...modal.querySelectorAll('#gf_5')].every((n) => !!n.closest('#gform_wrapper_5')),
		staleAnchors: modal.querySelectorAll('#gf_5.sf-certmodal__stale').length,
		wrapCount: modal.querySelectorAll('#gform_confirmation_wrapper_5').length,
		msgCount: modal.querySelectorAll('#gform_confirmation_message_5').length,
		staleCount: modal.querySelectorAll('.sf-certmodal__stale').length,
		hasForm: !!modal.querySelector('#gform_wrapper_5'),
		certField: (modal.querySelector('#input_5_10') || {}).value || '',
		emailField: (modal.querySelector('#input_5_3') || {}).value || '',
		successCard: !!modal.querySelector('.sf-certmodal__success'),
	};
});

const waitForConfirmation = async (p) => {
	try {
		await p.waitForFunction(() => !!document.querySelector('.sf-certmodal #gform_confirmation_wrapper_5'),
			null, { timeout: 20000 });
		return true;
	} catch (e) {
		return false;
	}
};

(async () => {
	const browser = await chromium.launch();

	/* ---------------------------------------------------------------- A --- */
	console.log('\n=== A. with the theme JavaScript ===');
	{
		const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
		const p = await ctx.newPage();
		const errors = [];
		p.on('pageerror', (e) => errors.push(e.message));
		await p.goto(BASE, { waitUntil: 'load' });
		await p.waitForTimeout(2200);
		await armSpies(p);

		await p.click('.sf-coa__btn--primary');
		await p.waitForTimeout(400);
		await submit(p, 'fda');
		const arrived = await waitForConfirmation(p);
		await p.waitForTimeout(600);

		check('A0. the confirmation arrived', arrived === true);

		const c = await confirmationIn(p);
		check('A1. GF\u2019s anchor is back: #gf_5 with GF\u2019s own class and tabindex -1',
			c.anchorIsGfClass === true && c.anchorTabindex === '-1',
			JSON.stringify({ cls: c.anchorIsGfClass, ti: c.anchorTabindex }));
		check('A2. it sits outside the card, immediately before the wrapper',
			c.anchorOutsideCard === true && c.anchorIsSiblingBefore === true);
		check('A3. the wrapper and message divs are back, with GF\u2019s own classes',
			c.wrapIsGfClass === true && c.msgIsGfClass === true);
		check('A4. our card is untouched: same node, directly inside the message div',
			c.cardInsideMsg === true);
		check('A5. the payload still parses', !!c.payload && c.payload.certificate === 'fda'
			&& c.payload.email_sent_to === EMAIL, JSON.stringify(c.payload));
		check('A6. the plain <a> the no-JavaScript visitor clicks is still there',
			c.plainText === 'Download now' && /cert-download.*token=[0-9a-f]{40}/.test(c.plainHref || ''),
			(c.plainHref || '').slice(0, 60));
		check('A7. exactly one node per id \u2014 no duplicates', c.anchorCount === 1 && c.wrapCount === 1);

		const s = await readSpies(p);
		check('A8. the postback handler reaches its last line: gform_confirmation_loaded fired',
			s.events >= 1, 'events=' + s.events);
		check('A9. it announced the confirmation \u2014 only reachable past the old throw',
			s.spoken.some((t) => /Request received/.test(t)), JSON.stringify(s.spoken).slice(0, 160));
		check('A10. no script error at all \u2014 the #gf_5 TypeError is gone',
			errors.length === 0, errors.join(' / ') || 'clean');
		check('A11. the flag GF sets on submit is cleared', s.submittingFlag === false, String(s.submittingFlag));
		check('A12. the success state is up', c.success === true);

		/* second request, after the dialog has been closed and reopened */
		await p.click('.sf-certmodal__success-close');
		await p.waitForTimeout(400);
		await p.click('.sf-coa__btn--primary');
		await p.waitForTimeout(400);
		const clean = await cleanState(p);
		check('A13. reopening leaves no orphan anchor, wrapper or message div',
			clean.wrapCount === 0 && clean.msgCount === 0 && clean.staleCount === 0
			&& clean.staleAnchors === 0 && clean.anchorsInsideForm === true,
			JSON.stringify(clean));
		check('A14. and the form is back, empty, with the trigger\u2019s key in the hidden field',
			clean.hasForm === true && clean.certField === 'coa-sample'
			&& clean.emailField === '' && clean.successCard === false, JSON.stringify(clean));

		await armSpies(p);
		await submit(p, 'cgmp');
		const arrived2 = await waitForConfirmation(p);
		await p.waitForTimeout(600);
		const c2 = await confirmationIn(p);
		const s2 = await readSpies(p);
		check('A15. the second request really goes through', arrived2 === true
			&& !!c2.payload && c2.payload.certificate === 'cgmp', JSON.stringify(c2.payload));
		check('A16. again exactly one anchor \u2014 the parked one was removed, not stacked',
			c2.anchorCount === 1 && c2.wrapCount === 1, 'anchors=' + c2.anchorCount);
		check('A17. the handler completed on the second run too',
			s2.events >= 1 && s2.submittingFlag === false && errors.length === 0,
			JSON.stringify({ events: s2.events, flag: s2.submittingFlag, errors: errors.length }));

		await ctx.close();
	}

	/* ---------------------------------------------------------------- B --- */
	console.log('\n=== B. Gravity Forms only (cert-modal.js blocked) ===');
	{
		const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
		await ctx.route('**/cert-modal.js*', (route) => route.abort());
		const p = await ctx.newPage();
		const errors = [];
		p.on('pageerror', (e) => errors.push(e.message));
		await p.goto(BASE, { waitUntil: 'load' });
		await p.waitForTimeout(2400);

		/* the dialog is server-rendered and hidden; if the script really is gone a
		   click on a data-cert control must leave it that way */
		const stillHidden = await p.evaluate(() => {
			const b = document.createElement('button');
			b.type = 'button';
			b.setAttribute('data-cert', 'fda');
			document.body.appendChild(b);
			b.click();
			b.remove();
			const m = document.querySelector('.sf-certmodal');
			return m.hidden === true && !m.classList.contains('is-open');
		});
		check('B0. cert-modal.js really is absent \u2014 a data-cert click does not open the dialog',
			stillHidden === true);

		await p.evaluate(() => {
			const m = document.querySelector('.sf-certmodal');
			m.hidden = false;
			m.classList.add('is-open');
		});
		await p.waitForTimeout(500);
		check('B1. the form is there without our script',
			await p.evaluate(() => !!document.querySelector('#gform_submit_button_5')) === true);

		await armSpies(p);
		await submit(p, 'fda');
		const arrived = await waitForConfirmation(p);
		await p.waitForTimeout(600);

		const s = await readSpies(p);
		check('B2. GF\u2019s handler completes with nothing of ours loaded',
			arrived === true && s.events >= 1, 'events=' + s.events);
		check('B3. it cleared the submitting flag itself \u2014 the bug\u2019s visible symptom',
			s.submittingFlag === false, String(s.submittingFlag));
		check('B4. it announced the message', s.spoken.some((t) => /Request received/.test(t)),
			JSON.stringify(s.spoken).slice(0, 160));
		const real = errors.filter((m) => m !== GF_POSTRENDER_ERROR);
		check('B5. no script error but GF\u2019s unrelated post-render flake',
			real.length === 0 && !errors.includes(GF_ID_ERROR),
			errors.join(' / ') || 'clean');

		const c = await confirmationIn(p);
		check('B6. the confirmation is rendered where the visitor can see it (no-JS state)',
			c.cardVisible === true && c.plainText === 'Download now', JSON.stringify({ visible: c.cardVisible }));

		/* the no-JavaScript download, taken for real through the browser */
		const source = path.join(CERTS_DIR, 'cert-fda.webp');
		const expected = fs.existsSync(source) ? sha(fs.readFileSync(source)) : null;
		const got = await p.evaluate(async (href) => {
			const res = await fetch(href, { credentials: 'same-origin' });
			const buf = await res.arrayBuffer();
			const bytes = new Uint8Array(buf);
			let binary = '';
			for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
			return { status: res.status, len: bytes.length, b64: btoa(binary) };
		}, c.plainHref);
		check('B7. that link downloads the real certificate, byte for byte',
			expected !== null && got.status === 200 && sha(Buffer.from(got.b64, 'base64')) === expected,
			got.status + ' ' + got.len + 'B');

		await ctx.close();
	}

	await browser.close();
	console.log('\n' + pass + ' passed, ' + fail + ' failed');
	process.exit(fail ? 1 : 0);
})();

/* B4.1 + B4.2 E2E — certificate request modal (structure + open logic).
   Run: NODE_PATH=~/.workbuddy/binaries/node/workspace/node_modules \
       node tools/_cert_modal_test.js

   Scope is exactly what B4.1/B4.2 ship: the dialog shell, the shared backdrop
   styles and the [data-cert] open path. The submit/success handling (B4.3),
   the reset-on-close (B4.4) and the certificate-row wiring (B4.5) are NOT
   built yet, so nothing here asserts them.

   The delegated [data-cert] contract is exercised with temporary buttons for
   all seven document keys — that is the interface B4.5 wires the rows to, so
   it is verified before the rows exist. */
const { chromium } = require('playwright-core');

const BASE = 'http://sinofresh.local/quality/';
const KEYS = ['fda', 'cgmp', 'iso9001', 'iso22000', 'haccp', 'brc', 'coa-sample'];
const HIDE_FIXED = '.sf-cookie-banner,.sf-float-stack{display:none !important}';

let pass = 0;
let fail = 0;
const check = (name, ok, detail) => {
	if (ok) { pass++; console.log('PASS ' + name); }
	else { fail++; console.log('FAIL ' + name + ' \u2014 ' + detail); }
};

/* One snapshot of everything the dialog is supposed to expose. */
const read = (p) => p.evaluate(() => {
	const m = document.querySelector('.sf-certmodal');
	if (!m) return { missing: true };
	const panel = m.querySelector('.sf-certmodal__panel');
	const close = m.querySelector('.sf-certmodal__close');
	const title = m.querySelector('.sf-certmodal__title');
	const lead = m.querySelector('.sf-certmodal__lead');
	const body = m.querySelector('.sf-certmodal__body');
	const field = m.querySelector('#input_5_10');
	const submit = m.querySelector('.gform_wrapper input[type="submit"], .gform_wrapper button[type="submit"]');
	const first = m.querySelector('#input_5_1');
	const r = panel ? panel.getBoundingClientRect() : null;
	const mr = m.getBoundingClientRect();
	const pcs = panel ? getComputedStyle(panel) : null;
	const mcs = getComputedStyle(m);

	// widest element inside the dialog: documentElement.scrollWidth cannot be
	// used because html/body clip on the x axis (style.css section 0)
	let widest = 0;
	m.querySelectorAll('*').forEach((el) => {
		const b = el.getBoundingClientRect();
		if (b.width && b.right > widest) widest = b.right;
	});

	return {
		missing: false,
		hidden: m.hasAttribute('hidden'),
		display: mcs.display,
		opacity: mcs.opacity,
		zIndex: mcs.zIndex,
		open: m.classList.contains('is-open'),
		backdrop: { x: Math.round(mr.x), y: Math.round(mr.y), w: Math.round(mr.width), h: Math.round(mr.height) },
		role: panel ? panel.getAttribute('role') : null,
		ariaModal: panel ? panel.getAttribute('aria-modal') : null,
		labelledBy: panel ? panel.getAttribute('aria-labelledby') : null,
		titleId: title ? title.id : null,
		titleText: title ? title.textContent.trim() : null,
		leadText: lead ? lead.textContent.trim() : null,
		closeLabel: close ? close.getAttribute('aria-label') : null,
		closeTag: close ? close.tagName : null,
		bodyHasForm: !!(body && body.querySelector('#gform_wrapper_5')),
		formAction: (() => { const f = m.querySelector('#gform_5'); return f ? f.getAttribute('action') : null; })(),
		fieldPresent: !!field,
		fieldName: field ? field.getAttribute('name') : null,
		fieldValue: field ? field.value : null,
		submitText: submit ? (submit.value || submit.textContent || '').trim() : null,
		submitBg: submit ? getComputedStyle(submit).backgroundColor : null,
		panelWidth: r ? Math.round(r.width) : 0,
		panelCenter: r ? Math.round(r.left + r.width / 2) : 0,
		panelBottom: r ? Math.round(r.bottom) : 0,
		panelTop: r ? Math.round(r.top) : 0,
		radius: pcs ? pcs.borderTopLeftRadius + ' / ' + pcs.borderBottomLeftRadius : null,
		maxHeight: pcs ? pcs.maxHeight : null,
		bodyScrolls: body ? body.scrollHeight > body.clientHeight : false,
		widest,
		active: (() => {
			const a = document.activeElement;
			if (!a) return null;
			if (a.closest && a.closest('[data-cert]')) return 'trigger:' + a.closest('[data-cert]').getAttribute('data-cert');
			return a.id || a.tagName;
		})(),
		lock: document.body.classList.contains('sf-certmodal-lock'),
		bodyOverflow: getComputedStyle(document.body).overflow,
	};

	/* backdrop hit test is done separately below; a fresh read is used there */
});

(async () => {
	const b = await chromium.launch();

	/* ---------------- desktop 1440 ---------------- */
	const dctx = await b.newContext({ viewport: { width: 1440, height: 900 } });
	const dp = await dctx.newPage();
	const errs = [];
	dp.on('console', (m) => { if (m.type() === 'error') errs.push(m.text()); });
	dp.on('pageerror', (e) => errs.push('pageerror: ' + e.message));
	await dp.goto(BASE, { waitUntil: 'load' });
	await dp.addStyleTag({ content: HIDE_FIXED });
	await dp.evaluate(() => document.fonts.ready);
	await dp.waitForTimeout(400);

	console.log('\n=== B4.1 \u00b7 structure (closed) ===');
	let s = await read(dp);
	check('1. .sf-certmodal rendered', !s.missing);
	check('2. starts hidden', s.hidden === true && s.display === 'none', 'hidden=' + s.hidden + ' display=' + s.display);
	check('3. dialog semantics', s.role === 'dialog' && s.ariaModal === 'true' && s.labelledBy === 'sf-certmodal-title', 'role=' + s.role + ' modal=' + s.ariaModal);
	check('4. title carries the aria-labelledby id', s.titleText === 'Request Certificate' && s.titleId === s.labelledBy, s.titleText + ' #' + s.titleId);
	check('5. lead copy', /Fill in the form and we\u2019ll send the certificate to your email\./.test(s.leadText || ''), s.leadText);
	check('6. close control is a labelled button', s.closeTag === 'BUTTON' && !!s.closeLabel, s.closeTag + ' ' + s.closeLabel);
	check('7. Form 5 rendered inside the dialog body', s.bodyHasForm === true);
	check('8. hidden certificate field #input_5_10', s.fieldPresent === true && s.fieldName === 'input_10', s.fieldName);
	check('9. submits through GF ajax (action #gf_5)', /#gf_5$/.test(s.formAction || ''), s.formAction);
	check('10. GF theme applies inside the dialog (submit = CTA orange)', s.submitBg === 'rgb(181, 78, 15)', s.submitBg + ' | "' + s.submitText + '"');
	check('11. backdrop stacks above the whole basket layer (10010)', s.zIndex === '10010', s.zIndex);

	console.log('\n=== B4.2 \u00b7 open ===');
	await dp.click('.sf-coa__btn--primary');       // the one wired control on the page today
	await dp.waitForTimeout(420);
	s = await read(dp);
	check('12. opens on [data-cert] click', s.hidden === false && s.display === 'flex' && s.open === true, 'display=' + s.display + ' open=' + s.open);
	check('13. backdrop faded to opacity 1', s.opacity === '1', s.opacity);
	check('14. backdrop covers the whole viewport', s.backdrop.x === 0 && s.backdrop.y === 0 && s.backdrop.w === 1440 && s.backdrop.h === 900, JSON.stringify(s.backdrop));
	check('15. desktop panel is 520px wide', s.panelWidth === 520, s.panelWidth + 'px');
	check('16. desktop panel is centred', Math.abs(s.panelCenter - 720) <= 1, 'centre ' + s.panelCenter + ' vs 720');
	check('17. panel radius 8px', s.radius === '8px / 8px', s.radius);
	check('18. hidden field pre-filled with the document key', s.fieldValue === 'coa-sample', JSON.stringify(s.fieldValue));
	check('19. body scroll locked', s.lock === true && s.bodyOverflow === 'hidden', 'lock=' + s.lock + ' overflow=' + s.bodyOverflow);
	check('20. focus moved to the first form control', s.active === 'input_5_1', String(s.active));
	check('21. no horizontal overflow while open', s.widest <= 1441, 'right edge ' + s.widest);
	check('22. the form is taller than the body, so the dialog scrolls', s.bodyScrolls === true);

	console.log('\n=== B4.4 \u00b7 close (shell only \u2014 reset lands with B4.4) ===');
	await dp.click('.sf-certmodal__close');
	await dp.waitForTimeout(150);
	s = await read(dp);
	check('23. X closes', s.hidden === true && s.display === 'none', 'display=' + s.display);
	check('24. scroll unlocked on close', s.lock === false && s.bodyOverflow !== 'hidden', s.bodyOverflow);
	check('25. focus returns to the trigger', s.active === 'trigger:coa-sample', String(s.active));

	for (const [name, act] of [
		['26. Esc closes', async () => { await dp.keyboard.press('Escape'); }],
		['27. backdrop click closes', async () => { await dp.mouse.click(6, 6); }],
	]) {
		await dp.click('.sf-coa__btn--primary');
		await dp.waitForTimeout(360);
		const hit = await dp.evaluate(() => document.elementFromPoint(6, 6) === document.querySelector('.sf-certmodal'));
		const opened = (await read(dp)).open;
		await act();
		await dp.waitForTimeout(160);
		const after = await read(dp);
		check(name, hit === true && opened === true && after.hidden === true, 'backdrop hit=' + hit + ' opened=' + opened + ' after=' + after.display);
	}

	console.log('\n=== B4.2 \u00b7 delegated triggers (interface for B4.5) ===');
	await dp.evaluate((keys) => {
		const box = document.createElement('div');
		box.id = 'tmp-cert-triggers';
		box.style.cssText = 'position:fixed;top:120px;left:24px;z-index:20001;display:flex;gap:6px;padding:6px;background:#fff';
		keys.forEach((k) => {
			const btn = document.createElement('button');
			btn.type = 'button';
			btn.id = 'tmp-' + k;
			btn.setAttribute('data-cert', k);
			btn.textContent = k;
			btn.style.cssText = 'padding:8px 10px;font-size:12px';
			box.appendChild(btn);
		});
		document.body.appendChild(box);
	}, KEYS);

	for (const k of KEYS) {
		const hit = await dp.evaluate((id) => {
			const el = document.getElementById(id);
			const r = el.getBoundingClientRect();
			return document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2) === el;
		}, 'tmp-' + k);
		if (!hit) { check('28.' + k + ' trigger reachable', false, 'elementFromPoint missed'); continue; }
		await dp.click('#tmp-' + k);
		await dp.waitForTimeout(360);
		const st = await read(dp);
		check('28.' + k + ' \u2192 open with certificate=' + k,
			st.open === true && st.fieldValue === k,
			'open=' + st.open + ' value=' + JSON.stringify(st.fieldValue));
		await dp.keyboard.press('Escape');
		await dp.waitForTimeout(120);
	}

	const afterAll = await read(dp);
	check('29. every trigger leaves the dialog closed again', afterAll.hidden === true, String(afterAll.display));
	await dp.evaluate(() => { const n = document.getElementById('tmp-cert-triggers'); if (n) n.remove(); });
	check('30. no page/console errors on desktop', errs.length === 0, errs.slice(0, 3).join(' | '));
	await dctx.close();

	/* ---------------- mobile 375 ---------------- */
	console.log('\n=== mobile 375 ===');
	const mctx = await b.newContext({ viewport: { width: 375, height: 700 }, isMobile: true, hasTouch: true });
	const mp = await mctx.newPage();
	const merrs = [];
	mp.on('pageerror', (e) => merrs.push('pageerror: ' + e.message));
	await mp.goto(BASE, { waitUntil: 'load' });
	await mp.addStyleTag({ content: HIDE_FIXED });
	await mp.evaluate(() => document.fonts.ready);
	await mp.waitForTimeout(400);

	await mp.click('.sf-coa__btn--primary');
	await mp.waitForTimeout(420);
	const ms = await read(mp);
	check('31. opens on mobile', ms.open === true && ms.hidden === false, String(ms.display));
	check('32. full-width panel', ms.panelWidth === 375, ms.panelWidth + 'px');
	check('33. bottom-aligned sheet', Math.abs(ms.panelBottom - 700) <= 1, 'bottom ' + ms.panelBottom);
	check('34. square bottom corners, 8px top', ms.radius === '8px / 0px', ms.radius);
	check('35. capped below the viewport top', ms.panelTop >= 56, 'top ' + ms.panelTop + ' maxHeight ' + ms.maxHeight);
	check('36. no horizontal overflow on 375px', ms.widest <= 376, 'right edge ' + ms.widest);
	check('37. first field focusable on mobile', ms.active === 'input_5_1', String(ms.active));

	const inner = await mp.evaluate(() => {
		const body = document.querySelector('.sf-certmodal__body');
		const first = document.querySelector('#input_5_1');
		const r = first.getBoundingClientRect();
		return {
			insideViewport: r.left >= 0 && r.right <= window.innerWidth,
			bodyScrollable: body.scrollHeight > body.clientHeight,
			pageScroll: window.scrollY,
		};
	});
	check('38. form controls stay inside the viewport', inner.insideViewport === true);
	check('39. the long form scrolls inside the sheet', inner.bodyScrollable === true);

	await mp.mouse.wheel(0, 600);
	await mp.waitForTimeout(200);
	const scrolled = await mp.evaluate(() => window.scrollY);
	check('40. page behind stays put while open', scrolled === inner.pageScroll, inner.pageScroll + ' \u2192 ' + scrolled);

	await mp.click('.sf-certmodal__close');
	await mp.waitForTimeout(160);
	const mclosed = await read(mp);
	check('41. X closes on mobile', mclosed.hidden === true && mclosed.lock === false, String(mclosed.display));
	check('42. no page errors on mobile', merrs.length === 0, merrs.slice(0, 2).join(' | '));
	await mctx.close();

	await b.close();
	console.log('\n' + (fail === 0 ? 'ALL PASS' : 'FAILURES') + ' \u2014 ' + pass + '/' + (pass + fail));
	process.exit(fail === 0 ? 0 : 1);
})();

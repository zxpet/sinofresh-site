/* B4.5 — every certificate control on the Quality page is a link.

   Each one is <a href="/contact/#quote" data-cert="…"> rather than a <button>:

     * with JavaScript, cert-modal.js sees the data-cert attribute, takes the
       click and opens the request dialog pre-filled with that document;
     * without it, the href still goes somewhere useful — the inquiry form.

   What is checked:

     1  the inventory: every data-cert control is an <a> pointing at
        /contact/#quote, and all seven document keys are wired
     2  clicking each one opens the dialog with the right key, and does not
        navigate — including by keyboard (Enter)
     3  the four certificate rows kept their own links (thumbnail, official
        website) untouched
     4  without JavaScript the click lands on /contact/#quote and the anchor
        is there
     5  the viewer's request line: it names the certificate on screen, is
        reachable by Tab, and hands over to the dialog
     6  375px: everything still opens, nothing overflows sideways

   Run:  NODE_PATH=~/.workbuddy/binaries/node/workspace/node_modules \
         node tools/_cert_triggers_test.js
*/
const { chromium } = require('playwright-core');

const BASE = 'http://sinofresh.local/quality/';
const FALLBACK = '/contact/#quote';
const KEYS = ['fda', 'cgmp', 'iso9001', 'iso22000', 'haccp', 'brc', 'coa-sample'];

let pass = 0, fail = 0;
const check = (name, ok, note) => {
	if (ok) { pass++; console.log('  ok   ' + name + (note ? '  [' + note + ']' : '')); }
	else { fail++; console.log('  FAIL ' + name + (note ? '  [' + note + ']' : '')); }
};

const inventory = (p) => p.$$eval('[data-cert]', (els) => els.map((e) => ({
	tag: e.tagName,
	cert: e.getAttribute('data-cert'),
	href: e.getAttribute('href'),
	cls: e.className,
	text: (e.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 52),
	where: e.closest('.sf-lb') ? 'viewer' : (e.closest('.sf-certdetail') ? 'rows' : 'page'),
})));

const dialogState = (p) => p.evaluate(() => {
	const m = document.querySelector('.sf-certmodal');
	const f = document.querySelector('#input_5_10');
	return {
		open: !m.hidden && m.classList.contains('is-open'),
		cert: f ? f.value : null,
		focused: document.activeElement ? document.activeElement.id || document.activeElement.tagName : null,
		overflow: document.documentElement.scrollWidth - window.innerWidth,
	};
});

const clickAt = async (p, i) => {
	const loc = p.locator('[data-cert]').nth(i);
	await loc.evaluate((el) => el.scrollIntoView({ block: 'center', behavior: 'instant' }));
	await p.waitForTimeout(140);
	await loc.click();
	await p.waitForTimeout(420);
};

const closeDialog = async (p) => {
	await p.keyboard.press('Escape');
	await p.waitForTimeout(420);
};

const quietExtras = (p) => p.addStyleTag({
	content: '.sf-cookie-banner,.sf-float-stack{display:none !important}',
});

(async () => {
	const browser = await chromium.launch();

	/* ---------------------------------------------------------------- 1440 --- */
	console.log('\n=== 1440: inventory ===');
	const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
	const p = await ctx.newPage();
	const errors = [];
	p.on('pageerror', (e) => errors.push(e.message));
	await p.goto(BASE, { waitUntil: 'load' });
	await p.waitForTimeout(1200);
	await quietExtras(p);

	const inv = await inventory(p);
	check('1. every certificate control is an <a>', inv.every((t) => t.tag === 'A'),
		inv.map((t) => t.tag).join(','));
	check('2. every one of them carries the fallback href ' + FALLBACK,
		inv.every((t) => t.href === FALLBACK), [...new Set(inv.map((t) => t.href))].join(' '));
	check('3. every one of them carries the trigger class',
		inv.every((t) => /\bsf-cert-trigger\b/.test(t.cls)));
	check('4. no <button data-cert> survives', !inv.some((t) => t.tag === 'BUTTON'),
		inv.filter((t) => t.tag === 'BUTTON').length + ' buttons');
	const keys = [...new Set(inv.map((t) => t.cert))].sort();
	check('5. all seven document keys are wired, and nothing else',
		JSON.stringify(keys) === JSON.stringify([...KEYS].sort()), keys.join(','));
	check('6. eight controls on the page before the viewer exists', inv.length === 8, String(inv.length));

	console.log('\n=== 1440: every control opens the dialog with its own key ===');
	for (let i = 0; i < inv.length; i++) {
		const t = inv[i];
		const urlBefore = p.url();
		await clickAt(p, i);
		const s = await dialogState(p);
		check('A' + i + '. "' + t.text + '" \u2192 ' + t.cert,
			s.open === true && s.cert === t.cert && p.url() === urlBefore,
			JSON.stringify({ open: s.open, cert: s.cert, nav: p.url() === urlBefore ? 'none' : p.url() }));
		check('A' + i + 'b. focus lands inside the dialog', !!s.focused && s.focused !== 'BODY', s.focused);
		await closeDialog(p);
	}

	console.log('\n=== 1440: keyboard and neighbours ===');
	{
		const loc = p.locator('[data-cert]').first();
		await loc.evaluate((el) => el.scrollIntoView({ block: 'center', behavior: 'instant' }));
		await p.waitForTimeout(140);
		await loc.focus();
		const urlBefore = p.url();
		await p.keyboard.press('Enter');
		await p.waitForTimeout(420);
		const s = await dialogState(p);
		check('K1. Enter on a focused trigger opens the dialog (no click)',
			s.open === true && s.cert === 'fda' && p.url() === urlBefore, JSON.stringify(s));
		await closeDialog(p);
	}

	{
		const rows = await p.evaluate(() => {
			const out = [];
			document.querySelectorAll('.sf-certrow').forEach((row) => {
				out.push({
					name: (row.querySelector('.sf-certrow__name') || {}).textContent || '',
					links: [...row.querySelectorAll('a')].map((a) => ({
						href: a.getAttribute('href') || '',
						target: a.getAttribute('target') || '',
						cert: a.getAttribute('data-cert'),
					})),
					placeholder: !!row.querySelector('.sf-certrow__media--placeholder'),
				});
			});
			return out;
		});
		const scanned = rows.filter((r) => !r.placeholder);
		check('K2. the four rows with a scan kept their thumbnail link, untouched',
			scanned.length === 4
			&& scanned.every((r) => r.links.some((l) => l.target === '_blank' && /-thumb\.webp$/.test(l.href)))
			&& scanned.every((r) => r.links.some((l) => /^https:\/\//.test(l.href) && l.target === '_blank')),
			scanned.map((r) => r.links.length).join(','));
		check('K3. the download control is the only certificate link in each row',
			rows.every((r) => r.links.filter((l) => l.cert && /^https?/.test(l.href) === false).length === 1),
			rows.map((r) => r.links.filter((l) => l.cert).length).join(','));
	}

	console.log('\n=== 1440: the viewer\u2019s request line ===');
	{
		await p.locator('.sf-certrow__media a').first()
			.evaluate((el) => el.scrollIntoView({ block: 'center', behavior: 'instant' }));
		await p.waitForTimeout(140);
		await p.locator('.sf-certrow__media a').first().click();
		await p.waitForTimeout(700);

		const line = await p.evaluate(() => {
			const lb = document.querySelector('.sf-lb');
			const a = lb && lb.querySelector('.sf-lb__request-link');
			const cs = a ? getComputedStyle(a) : null;
			return {
				exists: !!a,
				text: a ? a.textContent.trim() : null,
				href: a ? a.getAttribute('href') : null,
				cert: a ? a.getAttribute('data-cert') : null,
				visible: !!(a && a.getClientRects().length),
				boxVisible: !!(lb && !lb.hidden),
				bottom: a ? Math.round(a.getBoundingClientRect().bottom) : -1,
				anchor: a ? a.closest('a') !== null : false,
				pointer: cs ? cs.cursor : null,
			};
		});
		check('L1. the viewer shows the request line as a link',
			line.exists === true && line.visible === true && line.text === 'Full certificate available upon request'
			&& line.href === FALLBACK, JSON.stringify(line));
		check('L2. it names the certificate on screen', line.cert === 'fda', String(line.cert));
		check('L3. it sits under the controls, at the bottom of the viewer',
			line.bottom > 0 && line.bottom <= (await p.evaluate(() => window.innerHeight)) + 1,
			'bottom=' + line.bottom);

		/* Tab from the close button must reach it, not walk out of the viewer */
		await p.evaluate(() => document.querySelector('.sf-lb__btn--close').focus());
		await p.keyboard.press('Tab');
		const afterTab = await p.evaluate(() => {
			const el = document.activeElement;
			return { cls: el ? el.className : '', text: el ? el.textContent.trim().slice(0, 40) : '' };
		});
		check('L4. Tab from the last control lands on the request line',
			/Sf-lb__request-link|sf-lb__request-link/.test(afterTab.cls), JSON.stringify(afterTab));

		/* and clicking it hands over to the dialog */
		await p.locator('.sf-lb__request-link').click();
		await p.waitForTimeout(700);
		const s = await dialogState(p);
		const lbGone = await p.evaluate(() => {
			const lb = document.querySelector('.sf-lb');
			return !lb || (lb.hidden === true && getComputedStyle(document.documentElement).overflow !== 'hidden');
		});
		check('L5. clicking it opens the dialog for that certificate',
			s.open === true && s.cert === 'fda', JSON.stringify(s));
		check('L6. the viewer closed behind it', lbGone === true);
		check('L7. focus went into the dialog, not back to the thumbnail',
			await p.evaluate(() => !!document.querySelector('.sf-certmodal').contains(document.activeElement)),
			String(s.focused));
		await closeDialog(p);
	}

	check('Z1. no script errors', errors.length === 0, errors.join(' / ') || 'clean');
	await ctx.close();

	/* ------------------------------------------------------------- no JS --- */
	console.log('\n=== without JavaScript ===');
	{
		const noJs = await browser.newContext({ viewport: { width: 1440, height: 900 }, javaScriptEnabled: false });
		const np = await noJs.newPage();
		await np.goto(BASE, { waitUntil: 'load' });
		const href = await np.$eval('.sf-certrow__links a', (a) => a.getAttribute('href'));
		check('N1. the first control is still a real link', href === FALLBACK, String(href));
		await np.click('.sf-certrow__links a');
		await np.waitForLoadState('load');
		await np.waitForTimeout(400);
		check('N2. it lands on /contact/#quote', np.url().endsWith('/contact/#quote'), np.url());
		const anchor = await np.$eval('#quote', (el) => el.textContent.trim()).catch(() => null);
		check('N3. and the anchor it promises is on that page', anchor === 'Send Us an Inquiry', String(anchor));
		await noJs.close();
	}

	/* ------------------------------------------------------------- 375px --- */
	console.log('\n=== 375px ===');
	{
		const m = await browser.newContext({ viewport: { width: 375, height: 812 } });
		const mp = await m.newPage();
		const merr = [];
		mp.on('pageerror', (e) => merr.push(e.message));
		await mp.goto(BASE, { waitUntil: 'load' });
		await mp.waitForTimeout(1200);
		await quietExtras(mp);

		const minv = await inventory(mp);
		check('M1. same eight controls', minv.length === 8, String(minv.length));
		const results = [];
		for (let i = 0; i < minv.length; i++) {
			await clickAt(mp, i);
			const s = await dialogState(mp);
			results.push(s.open === true && s.cert === minv[i].cert && s.overflow <= 1);
			await closeDialog(mp);
		}
		check('M2. every control opens its dialog, nothing overflows sideways',
			results.every(Boolean), results.map((r) => (r ? 'y' : 'n')).join(''));

		await clickAt(mp, 0);
		const geom = await mp.evaluate(() => {
			const panel = document.querySelector('.sf-certmodal__panel');
			const r = panel.getBoundingClientRect();
			return {
				left: Math.round(r.left), right: Math.round(r.right), w: Math.round(r.width),
				overflow: document.documentElement.scrollWidth - window.innerWidth,
			};
		});
		check('M3. the dialog is a bottom sheet, edge to edge',
			geom.left <= 1 && geom.right >= 374 && geom.overflow <= 1, JSON.stringify(geom));
		check('M4. no script errors on mobile', merr.length === 0, merr.join(' / ') || 'clean');
		await m.close();
	}

	await browser.close();
	console.log('\n' + pass + ' passed, ' + fail + ' failed');
	process.exit(fail ? 1 : 0);
})();

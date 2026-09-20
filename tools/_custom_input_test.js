/* Stage A E2E: Custom detail input + universal PDF mapping.
 * Covers: slide-open UI, three-state summary, sanitize (: |), sessionStorage
 * "<group>_custom" key, Submit/PDF/basket interception, restore, reset,
 * universal label/value PDF payload (soft-chews + liquids), mobile 375.
 */
const { chromium } = require('playwright-core');
const fs = require('fs');

const BASE = 'http://sinofresh.local';
const results = [];
const ok = (name, cond) => {
	results.push((cond ? 'PASS ' : 'FAIL ') + name);
	if (!cond) process.exitCode = 1;
};

async function completeAll(page) {
	const groups = page.locator('.configurator__options .configurator__group');
	const n = await groups.count();
	for (let i = 0; i < n; i++) {
		await groups.nth(i).locator('.configurator__item').first().click();
	}
	return n;
}

(async () => {
	const browser = await chromium.launch();

	/* ---------- Desktop 1440: soft-chews ---------- */
	const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
	const page = await ctx.newPage();
	await page.goto(BASE + '/products/soft-chews/', { waitUntil: 'load' });
	await page.waitForTimeout(800);
	const accept = page.locator('.sf-cookie-banner__btn--accept');
	if (await accept.count() && (await accept.isVisible().catch(() => false))) await accept.click();

	const shapeGroup = page.locator('.configurator__group[data-group="shape"]');
	const shapeCustomBtn = shapeGroup.locator('.configurator__item[data-value="Custom"]');
	const shapeWrap = shapeGroup.locator('.configurator__custom');
	const shapeInput = shapeWrap.locator('.configurator__custom-input');

	// 1. closed by default
	ok('custom wrap exists under items', await shapeWrap.count() === 1);
	ok('custom wrap closed by default', !(await shapeWrap.evaluate((el) => el.classList.contains('is-open'))));

	// 2. click Custom -> opens, summary state 2
	await shapeCustomBtn.click();
	await page.waitForTimeout(350);
	ok('wrap opens on Custom click', await shapeWrap.evaluate((el) => el.classList.contains('is-open')));
	const shapeSum = page.locator('.configurator__summary-row[data-group="shape"] .configurator__summary-value');
	ok('summary state 2: (specify in notes)', (await shapeSum.textContent()).trim() === 'Custom (specify in notes)');
	let stored = await page.evaluate(() => JSON.parse(sessionStorage.getItem('sinofresh_config_soft-chews') || '{}'));
	ok('shape_custom key present (empty) before typing', 'shape_custom' in stored && stored.shape_custom === '');

	// 3. type with separators -> sanitize + three-state summary
	await shapeInput.fill('3.5g bone: ridged | red');
	await shapeInput.blur();
	await page.waitForTimeout(200);
	ok('blur: ":" -> " - "', (await shapeInput.inputValue()) === '3.5g bone - ridged / red');
	ok('summary state 3: Custom: text', (await shapeSum.textContent()).trim() === 'Custom: 3.5g bone - ridged / red');
	stored = await page.evaluate(() => JSON.parse(sessionStorage.getItem('sinofresh_config_soft-chews') || '{}'));
	ok('stored shape_custom filtered', stored.shape_custom === '3.5g bone - ridged / red');

	// 4. empty-custom interception: packaging Custom left empty -> basket + PDF + submit block
	await page.locator('.configurator__group[data-group="packaging"] .configurator__item[data-value="Custom"]').click();
	await completeAll(page); // fills every group with first option (incl. packaging/shape)
	// re-select customs: shape keeps typed text, packaging left empty
	await shapeCustomBtn.click();
	await page.locator('.configurator__group[data-group="packaging"] .configurator__item[data-value="Custom"]').click();
	await page.waitForTimeout(200);

	const basketBtn = page.locator('.configurator__summary .configurator__basket');
	const pdfBtn = page.locator('.configurator__summary .configurator__pdf');
	const submitBtn = page.locator('.configurator__summary .configurator__submit');

	await basketBtn.scrollIntoViewIfNeeded();
	await basketBtn.click();
	await page.waitForTimeout(300);
	ok('basket blocked by empty custom', /describe your custom requirement/i.test(await page.locator('.sf-toast.is-visible').textContent().catch(() => '')));
	ok('basket not stored', await page.evaluate(() => !sessionStorage.getItem('sinofresh_basket')));

	await pdfBtn.click();
	await page.waitForTimeout(300);
	ok('pdf blocked by empty custom', /describe your custom requirement/i.test(await page.locator('.sf-toast.is-visible').textContent().catch(() => '')));
	ok('pdf button not busy', !(await pdfBtn.isDisabled()));

	await submitBtn.click();
	await page.waitForTimeout(300);
	ok('submit blocked by empty custom', /describe your custom requirement/i.test(await page.locator('.sf-toast.is-visible').textContent().catch(() => '')));

	// 5. fill packaging custom -> basket summary carries both custom texts
	const packInput = page.locator('.configurator__group[data-group="packaging"] .configurator__custom-input');
	await packInput.fill('Pillow pouch | matte finish');
	await packInput.blur();
	await page.waitForTimeout(200);
	await basketBtn.click();
	await page.waitForTimeout(300);
	let basket = await page.evaluate(() => JSON.parse(sessionStorage.getItem('sinofresh_basket') || '[]'));
	ok('basket added with customs', basket.length === 1);
	ok('basket summary has filtered customs', basket[0] && /Shape: Custom: 3\.5g bone - ridged \/ red/.test(basket[0].summary) && /Packaging: Custom: Pillow pouch \/ matte finish/.test(basket[0].summary));

	// 6. PDF: capture request body + response bytes (universal pairs payload)
	const pdfReq = page.waitForRequest((r) => r.url().includes('config-pdf'));
	const pdfRes = page.waitForResponse((r) => r.url().includes('config-pdf'));
	await pdfBtn.click();
	const req = await pdfReq;
	const res = await pdfRes;
	const body = req.postDataJSON();
	ok('pdf config is pairs array', Array.isArray(body.config) && body.config.length === 8);
	ok('pairs labels from markup', body.config.map((p) => p.label).join(',') === 'Shape,Color,Flavor,Piece Weight,Count per Container,Packaging,Functions,Shelf Life');
	ok('pairs value custom three-state', body.config[0].value === 'Custom: 3.5g bone - ridged / red' && body.config[5].value === 'Custom: Pillow pouch / matte finish');
	ok('pdf response status 200 + pdf type', res.status() === 200 && (res.headers()['content-type'] || '').includes('pdf'));
	/* Read the bytes back through the same browser fetch path the user's
	   download uses (playwright's res.body() buffer races this stream). */
	const pdfB64 = await page.evaluate(async (payload) => {
		const r = await fetch('/wp-json/sinofresh/v1/config-pdf', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(payload)
		});
		const buf = new Uint8Array(await r.arrayBuffer());
		let bin = '';
		for (let i = 0; i < buf.length; i++) bin += String.fromCharCode(buf[i]);
		return btoa(bin);
	}, body);
	const bytes = Buffer.from(pdfB64, 'base64');
	ok('pdf response is a PDF', bytes.slice(0, 4).toString() === '%PDF');
	fs.writeFileSync('screenshots/custom-stageA-softchews.pdf', bytes);
	ok('pdf bytes non-trivial', bytes.length > 10000);

	// 7. restore after reload
	await page.reload({ waitUntil: 'load' });
	await page.waitForTimeout(800);
	const accept2 = page.locator('.sf-cookie-banner__btn--accept');
	if (await accept2.count() && (await accept2.isVisible().catch(() => false))) await accept2.click();
	const shapeInput2 = page.locator('.configurator__group[data-group="shape"] .configurator__custom-input');
	ok('reload: input value restored', (await shapeInput2.inputValue()) === '3.5g bone - ridged / red');
	ok('reload: wrap open', await page.locator('.configurator__group[data-group="shape"] .configurator__custom').evaluate((el) => el.classList.contains('is-open')));
	ok('reload: summary custom text', (await page.locator('.configurator__summary-row[data-group="shape"] .configurator__summary-value').textContent()).trim() === 'Custom: 3.5g bone - ridged / red');

	// desktop screenshot: expanded input + typed summary
	await page.locator('.configurator__group[data-group="shape"]').scrollIntoViewIfNeeded();
	await page.waitForTimeout(300);
	await page.screenshot({ path: 'screenshots/custom-stageA-desktop.png' });

	// 8. deselect Custom -> wrap closes, key dropped
	await page.locator('.configurator__group[data-group="shape"] .configurator__item[data-value="Bone"]').click();
	await page.waitForTimeout(250);
	ok('deselect closes wrap', !(await page.locator('.configurator__group[data-group="shape"] .configurator__custom').evaluate((el) => el.classList.contains('is-open'))));
	stored = await page.evaluate(() => JSON.parse(sessionStorage.getItem('sinofresh_config_soft-chews') || '{}'));
	ok('deselect drops shape_custom', !('shape_custom' in stored));

	// 9. reset clears inputs
	page.once('dialog', (d) => d.accept());
	await page.locator('.configurator__summary .configurator__reset').click();
	await page.waitForTimeout(300);
	ok('reset clears custom inputs', (await page.locator('.configurator__custom-input').evaluateAll((els) => els.every((e) => e.value === ''))));

	/* ---------- Desktop: liquids (other-page PDF mapping) ---------- */
	const page2 = await ctx.newPage();
	await page2.goto(BASE + '/products/liquids/', { waitUntil: 'load' });
	await page2.waitForTimeout(800);
	const accept3 = page2.locator('.sf-cookie-banner__btn--accept');
	if (await accept3.count() && (await accept3.isVisible().catch(() => false))) await accept3.click();
	await completeAll(page2);
	await page2.locator('.configurator__group[data-group="appearance"] .configurator__item[data-value="Custom"]').click();
	const liqInput = page2.locator('.configurator__group[data-group="appearance"] .configurator__custom-input');
	await liqInput.fill('Clear amber: light haze');
	await liqInput.blur();
	await page2.waitForTimeout(200);
	const req2P = page2.waitForRequest((r) => r.url().includes('config-pdf'));
	const res2P = page2.waitForResponse((r) => r.url().includes('config-pdf'));
	await page2.locator('.configurator__summary .configurator__pdf').click();
	const req2 = await req2P;
	const res2 = await res2P;
	const body2 = req2.postDataJSON();
	ok('liquids: 6 pairs with markup labels', Array.isArray(body2.config) && body2.config.map((p) => p.label).join(',') === 'Appearance,Flavor,Function,Bottle Size,Serving Size,Packaging');
	ok('liquids: custom value carried', body2.config[0].value === 'Custom: Clear amber - light haze');
	const pdfB64b = await page2.evaluate(async (payload) => {
		const r = await fetch('/wp-json/sinofresh/v1/config-pdf', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(payload)
		});
		const buf = new Uint8Array(await r.arrayBuffer());
		let bin = '';
		for (let i = 0; i < buf.length; i++) bin += String.fromCharCode(buf[i]);
		return btoa(bin);
	}, body2);
	const bytes2 = Buffer.from(pdfB64b, 'base64');
	ok('liquids: PDF renders server-side', bytes2.slice(0, 4).toString() === '%PDF' && bytes2.length > 10000);
	fs.writeFileSync('screenshots/custom-stageA-liquids.pdf', bytes2);

	/* ---------- Mobile 375 ---------- */
	const mctx = await browser.newContext({ viewport: { width: 375, height: 720 } });
	const mpage = await mctx.newPage();
	await mpage.goto(BASE + '/products/soft-chews/', { waitUntil: 'load' });
	await mpage.waitForTimeout(800);
	const maccept = mpage.locator('.sf-cookie-banner__btn--accept');
	if (await maccept.count() && (await maccept.isVisible().catch(() => false))) await maccept.click();
	await mpage.locator('.configurator__group[data-group="shape"] .configurator__item[data-value="Custom"]').click();
	await mpage.waitForTimeout(350);
	const mInput = mpage.locator('.configurator__group[data-group="shape"] .configurator__custom-input');
	await mInput.fill('3.5g bone with ridges');
	const overflow = await mpage.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
	ok('mobile: no horizontal overflow', overflow <= 0);
	ok('mobile: input visible & enabled', await mInput.isVisible() && await mInput.isEnabled());
	await mpage.locator('.configurator__group[data-group="shape"]').scrollIntoViewIfNeeded();
	await mpage.waitForTimeout(250);
	await mpage.screenshot({ path: 'screenshots/custom-stageA-mobile.png' });

	console.log(results.join('\n'));
	await browser.close();
})();

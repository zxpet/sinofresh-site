/* Stage B E2E: Custom chips added to the previously missing dimensions
 * (8x functions, soft-chews flavor, pastes texture, dental-chews size).
 * Verifies chip presence/last position, textarea for Functions, slide-open,
 * three-state summary, basket summary + PDF payload, mobile 375, screenshots.
 */
const { chromium } = require('playwright-core');
const fs = require('fs');

const BASE = 'http://sinofresh.local';
const results = [];
const ok = (name, cond) => {
	results.push((cond ? 'PASS ' : 'FAIL ') + name);
	if (!cond) process.exitCode = 1;
};

const PAGES = ['soft-chews', 'tablets', 'powders', 'pastes', 'drops', 'liquids', 'fish-oil', 'dental-chews'];

async function dismissCookies(page) {
	const b = page.locator('.sf-cookie-banner__btn--accept');
	if (await b.count() && await b.isVisible().catch(() => false)) await b.click();
}

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
	const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });

	/* ---------- 1. Every dosage page: functions + listed dimensions have a trailing Custom chip ---------- */
	for (const slug of PAGES) {
		const p = await ctx.newPage();
		await p.goto(BASE + '/products/' + slug + '/', { waitUntil: 'load' });
		await p.waitForTimeout(600);
		const rep = await p.evaluate(() => {
			const out = {};
			document.querySelectorAll('.configurator__options .configurator__group').forEach((g) => {
				const name = g.getAttribute('data-group');
				const chips = g.querySelectorAll('.configurator__items .configurator__item');
				const last = chips[chips.length - 1];
				out[name] = {
					n: chips.length,
					last: last ? last.getAttribute('data-value') : null,
					customCount: g.querySelectorAll('.configurator__item[data-value="Custom"]').length,
					inputTag: g.querySelector('.configurator__custom-input') ? g.querySelector('.configurator__custom-input').tagName : null
				};
			});
			return out;
		});
		ok(slug + ': functions Custom chip last', rep.functions && rep.functions.last === 'Custom' && rep.functions.customCount === 1);
		ok(slug + ': functions detail is a TEXTAREA', rep.functions && rep.functions.inputTag === 'TEXTAREA');
		// every dimension on the page now ends with a Custom chip
		const missing = Object.keys(rep).filter((k) => rep[k].last !== 'Custom');
		ok(slug + ': all ' + Object.keys(rep).length + ' dimensions end with Custom', missing.length === 0);
		// non-functions dimensions stay single-line inputs
		const wrongTag = Object.keys(rep).filter((k) => k !== 'functions' && rep[k].inputTag !== 'INPUT');
		ok(slug + ': other dimensions use single-line input', wrongTag.length === 0);
		if (slug === 'soft-chews' || slug === 'pastes' || slug === 'dental-chews') {
			const key = { 'soft-chews': 'flavor', 'pastes': 'texture', 'dental-chews': 'size' }[slug];
			ok(slug + ': ' + key + ' Custom chip present at end', rep[key] && rep[key].last === 'Custom');
		}
		await p.close();
	}

	/* ---------- 2. Functions textarea: open, multi-line input, summary, basket + PDF ---------- */
	const page = await ctx.newPage();
	await page.goto(BASE + '/products/soft-chews/', { waitUntil: 'load' });
	await page.waitForTimeout(800);
	await dismissCookies(page);
	const fn = page.locator('.configurator__group[data-group="functions"]');
	ok('functions wrap hidden by default', await fn.locator('.configurator__custom').evaluate((el) => el.hidden === true));
	await fn.locator('.configurator__item[data-value="Custom"]').click();
	await page.waitForTimeout(350);
	const fnWrap = fn.locator('.configurator__custom');
	ok('functions wrap slides open', await fnWrap.evaluate((el) => el.classList.contains('is-open') && !el.hidden));
	const fnInput = fn.locator('textarea.configurator__custom-input');
	ok('textarea inside functions wrap', await fnInput.count() === 1);
	const fnSum = page.locator('.configurator__summary-row[data-group="functions"] .configurator__summary-value');
	ok('functions summary state 2', (await fnSum.textContent()).trim() === 'Custom (specify in notes)');

	await fnInput.fill('Hip & joint\nOmega-3: EPA 500mg | DHA 300mg');
	await fnInput.blur();
	await page.waitForTimeout(250);
	ok('textarea sanitized + single-lined', (await fnInput.inputValue()) === 'Hip & joint Omega-3 - EPA 500mg / DHA 300mg');
	ok('functions summary state 3', (await fnSum.textContent()).trim() === 'Custom: Hip & joint Omega-3 - EPA 500mg / DHA 300mg');
	const stored = await page.evaluate(() => JSON.parse(sessionStorage.getItem('sinofresh_config_soft-chews') || '{}'));
	ok('functions_custom stored filtered', stored.functions_custom === 'Hip & joint Omega-3 - EPA 500mg / DHA 300mg');

	// flavor Custom (stage B addition) also drives the summary
	await page.locator('.configurator__group[data-group="flavor"] .configurator__item[data-value="Custom"]').click();
	const flavorInput = page.locator('.configurator__group[data-group="flavor"] .configurator__custom-input');
	await flavorInput.fill('Duck liver');
	await flavorInput.blur();
	await page.waitForTimeout(200);
	ok('flavor summary state 3', (await page.locator('.configurator__summary-row[data-group="flavor"] .configurator__summary-value').textContent()).trim() === 'Custom: Duck liver');

	// complete the rest, add to basket, check summary line + PDF payload
	await completeAll(page);
	await page.locator('.configurator__group[data-group="functions"] .configurator__item[data-value="Custom"]').click();
	await page.locator('.configurator__group[data-group="flavor"] .configurator__item[data-value="Custom"]').click();
	await page.waitForTimeout(250);
	const basketBtn = page.locator('.configurator__summary .configurator__basket');
	await basketBtn.scrollIntoViewIfNeeded();
	await basketBtn.click();
	await page.waitForTimeout(300);
	const basket = await page.evaluate(() => JSON.parse(sessionStorage.getItem('sinofresh_basket') || '[]'));
	ok('basket item stored', basket.length === 1);
	ok('basket summary: functions custom', basket[0] && /Functions: Custom: Hip & joint Omega-3 - EPA 500mg \/ DHA 300mg/.test(basket[0].summary));
	ok('basket summary segments intact (no separator leak)', basket[0] && basket[0].summary.split(' | ').length === 9);

	const pdfReqP = page.waitForRequest((r) => r.url().includes('config-pdf'));
	const pdfResP = page.waitForResponse((r) => r.url().includes('config-pdf'));
	await page.locator('.configurator__summary .configurator__pdf').click();
	const pdfBody = (await pdfReqP).postDataJSON();
	const pdfRes = await pdfResP;
	const fnPair = pdfBody.config.find((x) => x.label === 'Functions');
	const flPair = pdfBody.config.find((x) => x.label === 'Flavor');
	ok('pdf pairs: functions custom value', fnPair && fnPair.value === 'Custom: Hip & joint Omega-3 - EPA 500mg / DHA 300mg');
	ok('pdf pairs: flavor custom value', flPair && flPair.value === 'Custom: Duck liver');
	ok('pdf responded 200 pdf', pdfRes.status() === 200 && (pdfRes.headers()['content-type'] || '').includes('pdf'));
	const b64 = await page.evaluate(async (payload) => {
		const r = await fetch('/wp-json/sinofresh/v1/config-pdf', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
		const buf = new Uint8Array(await r.arrayBuffer());
		let bin = '';
		for (let i = 0; i < buf.length; i++) bin += String.fromCharCode(buf[i]);
		return btoa(bin);
	}, pdfBody);
	const bytes = Buffer.from(b64, 'base64');
	ok('pdf bytes valid', bytes.slice(0, 4).toString() === '%PDF' && bytes.length > 10000);
	fs.writeFileSync('screenshots/custom-stageB-softchews.pdf', bytes);

	/* desktop screenshots: functions textarea open + flavor custom */
	await page.locator('.configurator__group[data-group="functions"]').scrollIntoViewIfNeeded();
	await page.waitForTimeout(300);
	await page.screenshot({ path: 'screenshots/custom-stageB-desktop-functions.png' });
	await page.locator('.configurator__group[data-group="flavor"]').scrollIntoViewIfNeeded();
	await page.waitForTimeout(250);
	await page.screenshot({ path: 'screenshots/custom-stageB-desktop-flavor.png' });

	// pastes texture (single-line, stage B) on its own page
	const p3 = await ctx.newPage();
	await p3.goto(BASE + '/products/pastes/', { waitUntil: 'load' });
	await p3.waitForTimeout(800);
	await dismissCookies(p3);
	await p3.locator('.configurator__group[data-group="texture"] .configurator__item[data-value="Custom"]').click();
	await p3.waitForTimeout(300);
	const texInput = p3.locator('.configurator__group[data-group="texture"] .configurator__custom-input');
	await texInput.fill('Thick paste: 1.2M cps');
	await texInput.blur();
	await p3.waitForTimeout(200);
	ok('texture summary state 3', (await p3.locator('.configurator__summary-row[data-group="texture"] .configurator__summary-value').textContent()).trim() === 'Custom: Thick paste - 1.2M cps');
	ok('texture uses single-line input', await p3.locator('.configurator__group[data-group="texture"] input.configurator__custom-input').count() === 1);
	await p3.close();

	/* ---------- 3. Mobile 375: functions textarea usable, no overflow ---------- */
	const mctx = await browser.newContext({ viewport: { width: 375, height: 720 } });
	const mp = await mctx.newPage();
	await mp.goto(BASE + '/products/dental-chews/', { waitUntil: 'load' });
	await mp.waitForTimeout(800);
	await dismissCookies(mp);
	await mp.locator('.configurator__group[data-group="functions"] .configurator__item[data-value="Custom"]').click();
	await mp.waitForTimeout(350);
	const mta = mp.locator('.configurator__group[data-group="functions"] textarea.configurator__custom-input');
	await mta.fill('Fresh breath + plaque control');
	await mta.blur();
	await mp.waitForTimeout(200);
	ok('mobile: dental functions textarea works', (await mta.inputValue()) === 'Fresh breath + plaque control');
	ok('mobile: banner label reflects custom', (await mp.locator('.configurator__summary-row[data-group="functions"] .configurator__summary-value').count()) >= 1);
	const ov1 = await mp.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
	ok('mobile: no horizontal overflow (functions)', ov1 <= 0);
	await mp.locator('.configurator__group[data-group="functions"]').scrollIntoViewIfNeeded();
	await mp.waitForTimeout(250);
	await mp.screenshot({ path: 'screenshots/custom-stageB-mobile-functions.png' });

	// mobile: size dimension Custom (stage B on dental) + soft-chews flavor
	const mp2 = await mctx.newPage();
	await mp2.goto(BASE + '/products/soft-chews/', { waitUntil: 'load' });
	await mp2.waitForTimeout(800);
	await dismissCookies(mp2);
	await mp2.locator('.configurator__group[data-group="flavor"] .configurator__item[data-value="Custom"]').click();
	await mp2.waitForTimeout(350);
	const mfi = mp2.locator('.configurator__group[data-group="flavor"] .configurator__custom-input');
	await mfi.fill('Duck liver');
	await mfi.blur();
	await mp2.waitForTimeout(200);
	const ov2 = await mp2.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
	ok('mobile: no horizontal overflow (flavor)', ov2 <= 0);
	ok('mobile: flavor summary state 3', (await mp2.locator('.configurator__summary-row[data-group="flavor"] .configurator__summary-value').textContent()).trim() === 'Custom: Duck liver');
	await mp2.locator('.configurator__group[data-group="flavor"]').scrollIntoViewIfNeeded();
	await mp2.waitForTimeout(250);
	await mp2.screenshot({ path: 'screenshots/custom-stageB-mobile-flavor.png' });

	console.log(results.join('\n'));
	await browser.close();
})();

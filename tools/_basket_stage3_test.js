/* Basket stage 3 E2E: drawer Submit Inquiry → /contact/?from=basket →
 * GF field 12 / Notes pre-fill (field 7 untouched) → notice → ajax submit →
 * basket cleared. Plus empty-basket guard and mobile overflow. */
const { chromium } = require('playwright-core');

const BASE = 'http://sinofresh.local';
const results = [];
const ok = (name, cond) => {
	results.push((cond ? 'PASS ' : 'FAIL ') + name);
	if (!cond) process.exitCode = 1;
};

async function completeAndAdd(page, mobile) {
	const groups = page.locator('.configurator__options .configurator__group');
	const n = await groups.count();
	for (let i = 0; i < n; i++) {
		await groups.nth(i).locator('.configurator__item').first().click();
	}
	if (!mobile) {
		await page.locator('.configurator__summary .configurator__basket').click();
		await page.waitForTimeout(200);
		return;
	}
	await page.locator('.configurator__bar-trigger').click();
	await page.waitForTimeout(400);
	await page.locator('#configurator-drawer .configurator__basket').click();
	await page.waitForTimeout(200);
	await page.locator('.configurator__drawer-close').click();
	await page.waitForTimeout(400);
}

(async () => {
	const browser = await chromium.launch();
	const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
	const page = await ctx.newPage();
	page.on('dialog', (d) => d.accept());

	/* 0. empty-basket guard */
	await page.goto(BASE + '/', { waitUntil: 'load' });
	await page.waitForTimeout(600);
	const accept = page.locator('.sf-cookie-banner__btn--accept');
	if (await accept.count()) await accept.click();
	await page.locator('.sf-basket-btn').click();
	await page.waitForTimeout(400);
	await page.locator('.sf-basket-drawer__submit').click();
	await page.waitForTimeout(300);
	ok('empty basket toast', /your basket is empty/i.test(await page.locator('.sf-toast.is-visible').textContent().catch(() => '')));
	ok('still on home page', page.url().replace(/\/$/, '') === BASE);
	await page.keyboard.press('Escape');
	await page.waitForTimeout(400);

	/* 1. build basket: soft-chews + tablets */
	await page.goto(BASE + '/products/soft-chews/', { waitUntil: 'load' });
	await page.waitForTimeout(600);
	await completeAndAdd(page);
	await page.goto(BASE + '/products/tablets/', { waitUntil: 'load' });
	await page.waitForTimeout(600);
	await completeAndAdd(page);
	ok('basket has 2 items', (await page.evaluate(() => JSON.parse(sessionStorage.getItem('sinofresh_basket') || '[]').length)) === 2);

	/* 2. Submit Inquiry → /contact/?from=basket */
	await page.locator('.sf-basket-btn').click();
	await page.waitForTimeout(400);
	await page.locator('.sf-basket-drawer__submit').click();
	await page.waitForURL('**/contact/?from=basket', { timeout: 15000 });
	ok('landed on contact with from=basket', /\/contact\/\?from=basket$/.test(page.url()));

	/* 3. GF fields pre-filled */
	await page.waitForTimeout(500);
	const f12 = await page.locator('input[name="input_12"]').inputValue();
	ok('field 12 has [1] Soft Chews', /\[1\] Dosage Form: Soft Chews \| /.test(f12));
	ok('field 12 has [2] Tablets', /\[2\] Dosage Form: Tablets \| /.test(f12));
	ok('field 12 numbered multi-item format', (f12.match(/\[\d\] /g) || []).length === 2);
	const f10 = await page.locator('textarea[name="input_10"]').inputValue();
	ok('Notes has basket list header', /Items in inquiry basket:/.test(f10));
	ok('Notes lists both items', /- Soft Chews/.test(f10) && /- Tablets/.test(f10));
	ok('Notes has supplement request line', /Please add any other requirements/.test(f10));
	const f7 = await page.locator('select[name="input_7"]');
	ok('field 7 untouched (first option)', await f7.evaluate((el) => el.selectedIndex === 0));
	ok('pending snapshot consumed', await page.evaluate(() => !sessionStorage.getItem('sinofresh_basket_pending')));
	ok('basket retained until submit', (await page.evaluate(() => JSON.parse(sessionStorage.getItem('sinofresh_basket') || '[]').length)) === 2);

	/* 4. notice visible + dismissible */
	const notice = page.locator('.sf-basket-notice');
	ok('notice text "2 items ... pre-filled"', /2 items from your inquiry basket have been pre-filled below\./.test(await notice.textContent()));
	await page.locator('#inquiry-form').scrollIntoViewIfNeeded();
	await page.screenshot({ path: 'screenshots/basket3-contact-filled.png' });
	await notice.locator('.sf-basket-notice__close').click();
	await page.waitForTimeout(200);
	ok('notice dismissible', (await page.locator('.sf-basket-notice').count()) === 0);

	/* 5. submit the form → confirmation → basket cleared */
	await page.locator('input[name="input_1"]').fill('Acme Pet Co');
	await page.locator('input[name="input_2"]').fill('Jane Doe');
	await page.locator('input[name="input_3"]').fill('jane@acme.example');
	await page.locator('select[name="input_5"]').selectOption({ index: 1 });
	await page.locator('select[name="input_7"]').selectOption({ index: 1 });
	await page.locator('input[name="input_11.1"]').check();
	await page.locator('#gform_submit_button_2').click();
	await page.waitForSelector('.gform_confirmation_message', { timeout: 20000 });
	ok('confirmation shown', await page.locator('.gform_confirmation_message').isVisible());
	await page.waitForTimeout(500);
	ok('basket cleared after submit', await page.evaluate(() => !sessionStorage.getItem('sinofresh_basket')));
	ok('badge hidden after submit', await page.locator('.sf-basket-btn__badge').isHidden());
	await page.screenshot({ path: 'screenshots/basket3-contact-confirmed.png' });

	/* 6. mobile 375: full flow, no horizontal overflow */
	const mctx = await browser.newContext({ viewport: { width: 375, height: 720 } });
	const mpage = await mctx.newPage();
	mpage.on('dialog', (d) => d.accept());
	await mpage.goto(BASE + '/products/soft-chews/', { waitUntil: 'load' });
	await mpage.waitForTimeout(600);
	const maccept = mpage.locator('.sf-cookie-banner__btn--accept');
	if (await maccept.count()) await maccept.click();
	await completeAndAdd(mpage, true);
	await mpage.locator('.sf-basket-btn').click();
	await mpage.waitForTimeout(400);
	await mpage.locator('.sf-basket-drawer__submit').click();
	await mpage.waitForURL('**/contact/?from=basket', { timeout: 15000 });
	await mpage.waitForTimeout(500);
	ok('mobile: field 12 filled', /\[1\] Dosage Form: Soft Chews/.test(await mpage.locator('input[name="input_12"]').inputValue()));
	ok('mobile: notice shown', await mpage.locator('.sf-basket-notice').isVisible());
	ok('mobile: no horizontal overflow', await mpage.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1));
	await mpage.locator('#inquiry-form').scrollIntoViewIfNeeded();
	await mpage.screenshot({ path: 'screenshots/basket3-mobile-filled.png' });

	console.log(results.join('\n'));
	await browser.close();
})();

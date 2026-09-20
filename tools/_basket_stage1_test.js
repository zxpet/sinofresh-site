/* Basket stage 1 E2E: add / incomplete toast / duplicate update / cross-page
 * accumulate / drawer instance / button label flash. Accepts the cookie banner
 * (hiding it triggers the body display:none bug). */
const { chromium } = require('playwright-core');

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

	/* ---------- Desktop 1440 ---------- */
	const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
	const page = await ctx.newPage();
	await page.goto(BASE + '/products/soft-chews/', { waitUntil: 'load' });
	await page.waitForTimeout(800);
	const accept = page.locator('.sf-cookie-banner__btn--accept');
	if (await accept.count()) await accept.click();

	const card = page.locator('.configurator__summary');
	await card.scrollIntoViewIfNeeded();
	const basketBtn = page.locator('.configurator__summary .configurator__basket');
	const pdfBtn = page.locator('.configurator__summary .configurator__pdf');

	// layout: row buttons same single-line height, PDF fills the rest
	await card.scrollIntoViewIfNeeded();
	const bb = await basketBtn.boundingBox();
	const pb = await pdfBtn.boundingBox();
	ok('row: pdf starts right of basket (beside, not stacked)', bb && pb && Math.abs(pb.y - bb.y) < 3 && pb.x > bb.x + bb.width);
	ok('row: both single-line height', bb && pb && bb.height < 50 && pb.height < 50 && Math.abs(pb.height - bb.height) < 2);

	// 1. incomplete -> toast, nothing stored
	await basketBtn.click();
	await page.waitForTimeout(300);
	const toastText = await page.locator('.sf-toast.is-visible').textContent().catch(() => '');
	ok('incomplete toast', /complete all configuration/i.test(toastText || ''));
	ok('nothing stored when incomplete', await page.evaluate(() => !sessionStorage.getItem('sinofresh_basket')));

	// 2. complete all groups + add
	const n = await completeAll(page);
	ok('clicked 8 groups', n === 8);
	await card.scrollIntoViewIfNeeded();
	await basketBtn.click();
	await page.waitForTimeout(200);
	ok('button label after add', (await basketBtn.textContent()).trim() === 'Added to Inquiry ✓');
	const toast2 = await page.locator('.sf-toast.is-visible').textContent();
	ok('added toast', /added to your inquiry basket/i.test(toast2 || ''));
	let basket = await page.evaluate(() => JSON.parse(sessionStorage.getItem('sinofresh_basket') || '[]'));
	ok('basket count 1', basket.length === 1);
	ok('item slug soft-chews', basket[0] && basket[0].slug === 'soft-chews');
	ok('summary starts with Dosage Form', basket[0] && /^Dosage Form: Soft Chews \| /.test(basket[0].summary));
	ok('summary has all groups (>=9 segments)', basket[0] && basket[0].summary.split(' | ').length >= 9);
	ok('formula empty (none referenced)', basket[0] && basket[0].formula === '');
	ok('addedAt ISO stamp', basket[0] && !isNaN(Date.parse(basket[0].addedAt)));

	// desktop screenshot: card + toast + button success state
	await card.scrollIntoViewIfNeeded();
	await page.waitForTimeout(150);
	await page.screenshot({ path: 'screenshots/basket-desktop-added.png' });
	await page.waitForTimeout(2100);
	ok('label reverts after 2s', (await basketBtn.textContent()).trim() === 'Add to Inquiry');

	// 3. duplicate -> updated, still 1
	await basketBtn.click();
	await page.waitForTimeout(300);
	basket = await page.evaluate(() => JSON.parse(sessionStorage.getItem('sinofresh_basket') || '[]'));
	ok('duplicate: still count 1', basket.length === 1);
	const toast3 = await page.locator('.sf-toast.is-visible').textContent();
	ok('updated toast', /updated in your inquiry basket/i.test(toast3 || ''));

	// 4. cross-page accumulate on tablets
	await page.goto(BASE + '/products/tablets/', { waitUntil: 'load' });
	await page.waitForTimeout(800);
	await completeAll(page);
	const tBasketBtn = page.locator('.configurator__summary .configurator__basket');
	await tBasketBtn.scrollIntoViewIfNeeded();
	await tBasketBtn.click();
	await page.waitForTimeout(300);
	basket = await page.evaluate(() => JSON.parse(sessionStorage.getItem('sinofresh_basket') || '[]'));
	ok('cross-page: count 2', basket.length === 2);
	ok('cross-page: slugs', basket.map((x) => x.slug).join(',') === 'soft-chews,tablets');
	ok('tablets summary ok', basket[1] && /^Dosage Form: Tablets \| /.test(basket[1].summary));

	/* ---------- Mobile 375 (fresh context = empty basket) ---------- */
	const mctx = await browser.newContext({ viewport: { width: 375, height: 720 } });
	const mpage = await mctx.newPage();
	await mpage.goto(BASE + '/products/soft-chews/', { waitUntil: 'load' });
	await mpage.waitForTimeout(800);
	const maccept = mpage.locator('.sf-cookie-banner__btn--accept');
	if (await maccept.count()) await maccept.click();

	await completeAll(mpage);
	await mpage.locator('.configurator__bar-trigger').click();
	await mpage.waitForTimeout(400);
	const drawerBasket = mpage.locator('#configurator-drawer .configurator__basket');
	ok('drawer has basket button', await drawerBasket.isVisible());
	await drawerBasket.click();
	await mpage.waitForTimeout(300);
	ok('drawer button success label', (await drawerBasket.textContent()).trim() === 'Added to Inquiry ✓');
	const mToast = await mpage.locator('.sf-toast.is-visible').textContent().catch(() => '');
	ok('mobile added toast', /added to your inquiry basket/i.test(mToast || ''));
	const mbasket = await mpage.evaluate(() => JSON.parse(sessionStorage.getItem('sinofresh_basket') || '[]'));
	ok('mobile basket count 1', mbasket.length === 1);
	await mpage.screenshot({ path: 'screenshots/basket-mobile-drawer.png' });

	console.log(results.join('\n'));
	await browser.close();
})();

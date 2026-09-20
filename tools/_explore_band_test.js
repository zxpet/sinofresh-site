/* Task B E2E: "Explore more dosage forms" band on 8 dosage pages. */
const { chromium } = require('playwright-core');

const BASE = 'http://sinofresh.local';
const PAGES = ['soft-chews','dental-chews','tablets','pastes','powders','drops','liquids','fish-oil'];
let passed = 0, failed = 0;
function ok(cond, label) {
	if (cond) { passed++; console.log('  PASS', label); }
	else { failed++; console.log('  FAIL', label); }
}

(async () => {
	const browser = await chromium.launch();

	/* Desktop 1440: band present on all 8 pages, after last group, before summary. */
	const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
	const page = await ctx.newPage();
	for (const slug of PAGES) {
		await page.goto(BASE + '/products/' + slug + '/', { waitUntil: 'load' });
		await page.waitForTimeout(400);
		const n = await page.locator('.sf-explore').count();
		ok(n === 1, slug + ': band present');
		if (n !== 1) continue;
		const order = await page.evaluate(() => {
			const opt = document.querySelector('.configurator__options');
			const gs = opt.querySelectorAll('.configurator__group');
			const last = gs[gs.length - 1];
			const band = opt.querySelector('.sf-explore');
			const summary = document.querySelector('.configurator__summary-col');
			return {
				bandAfterLastGroup: !!(last.compareDocumentPosition(band) & Node.DOCUMENT_POSITION_FOLLOWING),
				bandBeforeSummary: !!(band.compareDocumentPosition(summary) & Node.DOCUMENT_POSITION_FOLLOWING),
				title: band.querySelector('.sf-explore__title').textContent.trim(),
				btn: band.querySelector('.sf-explore__btn').getAttribute('href')
			};
		});
		ok(order.bandAfterLastGroup && order.bandBeforeSummary, slug + ': DOM order group→band→summary-col');
		ok(order.title === 'Explore more dosage forms', slug + ': title');
		ok(order.btn === '/products/', slug + ': btn href /products/');
	}
	// click navigates
	await page.goto(BASE + '/products/soft-chews/', { waitUntil: 'load' });
	await page.waitForTimeout(400);
	const acc = page.locator('.sf-cookie-banner__btn--accept');
	if (await acc.count() && await acc.isVisible()) await acc.click();
	await page.locator('.sf-explore__btn').scrollIntoViewIfNeeded();
	await page.locator('.sf-explore__btn').click();
	await page.waitForLoadState('load');
	ok(/\/products\/?$/.test(new URL(page.url()).pathname), 'button click lands on /products/');
	// geometry: band inside options column, radius 8, padding 40
	await page.goto(BASE + '/products/soft-chews/', { waitUntil: 'load' });
	await page.waitForTimeout(400);
	const geo = await page.evaluate(() => {
		const b = document.querySelector('.sf-explore');
		const cs = getComputedStyle(b);
		return { radius: cs.borderRadius, pad: cs.paddingTop, bg: cs.backgroundColor, w: Math.round(b.getBoundingClientRect().width), optW: Math.round(document.querySelector('.configurator__options').getBoundingClientRect().width) };
	});
	ok(geo.radius === '8px' && geo.pad === '40px', 'desktop radius 8px / padding 40px');
	ok(geo.w <= geo.optW && geo.w > 500, 'band fits options column (w=' + geo.w + '/opt=' + geo.optW + ')');
	await page.locator('.sf-explore').scrollIntoViewIfNeeded();
	await page.waitForTimeout(300);
	await page.screenshot({ path: 'screenshots/explore-desktop.png' });
	await ctx.close();

	/* Mobile 375: compact, full-width button, no horizontal overflow. */
	const mctx = await browser.newContext({ viewport: { width: 375, height: 812 }, isMobile: true, hasTouch: true });
	const mpage = await mctx.newPage();
	await mpage.goto(BASE + '/products/soft-chews/', { waitUntil: 'load' });
	await mpage.waitForTimeout(600);
	const acc2 = mpage.locator('.sf-cookie-banner__btn--accept');
	if (await acc2.count() && await acc2.isVisible()) await acc2.click();
	const mgeo = await mpage.evaluate(() => {
		const b = document.querySelector('.sf-explore');
		const btn = b.querySelector('.sf-explore__btn');
		const cs = getComputedStyle(b);
		return { pad: cs.paddingTop, btnW: Math.round(btn.getBoundingClientRect().width), bW: Math.round(b.getBoundingClientRect().width), overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth };
	});
	ok(mgeo.pad === '24px', 'mobile padding 24px');
	ok(mgeo.btnW >= mgeo.bW - 2 * 24 - 4, 'mobile button full-width of content box (btn=' + mgeo.btnW + '/content=' + (mgeo.bW - 48) + ')');
	ok(mgeo.overflow <= 0, 'no horizontal overflow (delta=' + mgeo.overflow + 'px)');
	await mpage.locator('.sf-explore').scrollIntoViewIfNeeded();
	await mpage.waitForTimeout(300);
	await mpage.screenshot({ path: 'screenshots/explore-mobile.png' });
	await mctx.close();

	await browser.close();
	console.log('\nRESULT: ' + passed + ' passed, ' + failed + ' failed');
	process.exit(failed ? 1 : 0);
})().catch(e => { console.error('FATAL', e); process.exit(1); });

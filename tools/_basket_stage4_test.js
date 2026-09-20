/* Stage 4 E2E: plural/singular notice, basket PDF (download + email copy),
   header CTA dead-anchor fix + contact #quote anchor. */
const { chromium } = require('playwright-core');

const BASE = 'http://sinofresh.local';
let passed = 0, failed = 0;
function ok(cond, label) {
	if (cond) { passed++; console.log('  PASS', label); }
	else { failed++; console.log('  FAIL', label); }
}

async function acceptCookies(page) {
	const acc = page.locator('.sf-cookie-banner__btn--accept');
	if (await acc.count() && await acc.isVisible()) await acc.click();
}

async function completeAndAdd(page, mobile) {
	/* Only click when the group has no selection yet — a restored config
	   must not be toggled off by re-clicking the first item. */
	const groups = page.locator('.configurator__options .configurator__group');
	const n = await groups.count();
	for (let i = 0; i < n; i++) {
		const g = groups.nth(i);
		const sel = await g.locator('.configurator__item.is-selected').count();
		if (!sel) {
			await g.locator('.configurator__item').first().click();
		}
	}
	if (mobile) {
		/* <768px: summary card is hidden — add via the bottom drawer. */
		await page.locator('.configurator__bar-trigger').click();
		await page.waitForTimeout(400);
		await page.locator('#configurator-drawer .configurator__basket').click();
		await page.waitForTimeout(250);
		await page.locator('.configurator__drawer-close').click();
		await page.waitForTimeout(400);
	} else {
		await page.locator('.configurator__summary .configurator__basket').first().click();
		await page.waitForTimeout(250);
	}
}

(async () => {
	const browser = await chromium.launch();

	/* ---------- Desktop 1440 ---------- */
	const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, acceptDownloads: true });
	const page = await ctx.newPage();

	// A1 singular: one item
	await page.goto(BASE + '/products/soft-chews/', { waitUntil: 'load' });
	await page.waitForTimeout(600);
	await acceptCookies(page);
	await completeAndAdd(page, false);
	await page.goto(BASE + '/contact/?from=basket', { waitUntil: 'load' });
	await page.waitForTimeout(800);
	let noticeText = '';
	const notice = page.locator('.sf-basket-notice__text');
	if (await notice.count()) noticeText = (await notice.textContent()).trim();
	ok(noticeText === '1 item from your inquiry basket has been pre-filled below.', 'A1 singular notice: "' + noticeText + '"');
	ok((await page.locator('input[name="input_12"]').inputValue()).startsWith('[1] '), 'field 12 filled (single)');

	// A1 plural: two items
	await page.evaluate(() => sessionStorage.removeItem('sinofresh_basket'));
	await page.goto(BASE + '/products/soft-chews/', { waitUntil: 'load' });
	await page.waitForTimeout(500);
	await completeAndAdd(page, false);
	await page.goto(BASE + '/products/tablets/', { waitUntil: 'load' });
	await page.waitForTimeout(500);
	await completeAndAdd(page, false);
	await page.goto(BASE + '/contact/?from=basket', { waitUntil: 'load' });
	await page.waitForTimeout(800);
	noticeText = (await page.locator('.sf-basket-notice__text').textContent()).trim();
	ok(noticeText === '2 items from your inquiry basket have been pre-filled below.', 'A1 plural notice: "' + noticeText + '"');
	ok((await page.locator('input[name="input_12"]').inputValue()).includes('[2] '), 'field 12 filled (multi)');

	// A3: header CTA href
	const ctaHref = await page.locator('.sf-header__cta .wp-block-button__link').getAttribute('href');
	ok(ctaHref === '/contact/', 'A3 header CTA href = /contact/ (got ' + ctaHref + ')');
	await page.locator('.sf-header__cta .wp-block-button__link').click();
	await page.waitForLoadState('load');
	ok(/\/contact\/?$/.test(new URL(page.url()).pathname), 'A3 CTA click lands on /contact/');
	// A3: #quote anchor exists and hash navigation scrolls to it
	ok(await page.locator('h2#quote').count() === 1, 'A3 h2#quote exists on contact');
	await page.goto(BASE + '/contact/#quote', { waitUntil: 'load' });
	await page.waitForTimeout(900);
	const quoteTop = await page.evaluate(() => document.getElementById('quote').getBoundingClientRect().top);
	ok(quoteTop > -80 && quoteTop < 400, 'A3 #quote scrolled into view (top=' + Math.round(quoteTop) + 'px)');

	// A2: drawer basket PDF (download) + mail row
	await page.evaluate(() => {
		sessionStorage.setItem('sinofresh_basket', JSON.stringify([
			{ slug: 'soft-chews', title: 'Soft Chews', summary: 'Dosage Form: Soft Chews | Shape: Bone | Function: Joint Support', formula: 'Senior Joint Support', addedAt: new Date().toISOString() },
			{ slug: 'tablets', title: 'Tablets', summary: 'Dosage Form: Tablets | Shape: Round | Function: Skin & Coat', formula: '', addedAt: new Date().toISOString() }
		]));
	});
	await page.reload({ waitUntil: 'load' });
	await page.waitForTimeout(600);
	await page.locator('.sf-basket-btn').click();
	await page.waitForTimeout(400);
	const dl = page.waitForEvent('download', { timeout: 30000 });
	await page.locator('.sf-basket-drawer__pdf').click();
	const download = await dl;
	const fname = download.suggestedFilename();
	ok(/^SINO-FRESH-Basket-SF-\d{8}-[A-Z0-9]{4}\.pdf$/.test(fname), 'A2 basket PDF filename: ' + fname);
	ok(await page.locator('.sf-basket-drawer__pdf').textContent() === 'Download Basket PDF', 'A2 button label restored after busy');
	const mailVisible = await page.locator('.sf-basket-drawer__mail').isVisible();
	ok(mailVisible, 'A2 mail row revealed after download');

	// A2: mail row — invalid then valid email
	await page.locator('.sf-basket-drawer__mail-input').fill('not-an-email');
	await page.locator('.sf-basket-drawer__mail-send').click();
	await page.waitForTimeout(300);
	ok(await page.locator('.sf-basket-drawer__mail').isVisible(), 'A2 invalid email keeps row');
	await page.locator('.sf-basket-drawer__mail-input').fill('buyer@example.com');
	await page.locator('.sf-basket-drawer__mail-send').click();
	await page.waitForTimeout(1200);
	const toast = await page.locator('.sf-toast').textContent().catch(() => '');
	ok(/Copy sent to buyer@example\.com/.test(toast || ''), 'A2 email copy sent toast: "' + (toast || '') + '"');
	ok(!(await page.locator('.sf-basket-drawer__mail').isVisible()), 'A2 mail row hidden after send');
	await page.screenshot({ path: 'screenshots/basket4-desktop-drawer-pdf.png' });

	/* ---------- Mobile 375 ---------- */
	const mctx = await browser.newContext({ viewport: { width: 375, height: 812 }, acceptDownloads: true, isMobile: true, hasTouch: true });
	const mpage = await mctx.newPage();
	await mpage.goto(BASE + '/products/soft-chews/', { waitUntil: 'load' });
	await mpage.waitForTimeout(600);
	await acceptCookies(mpage);
	await completeAndAdd(mpage, true);
	await mpage.locator('.sf-basket-btn').click();
	await mpage.waitForTimeout(400);
	ok(await mpage.locator('.sf-basket-drawer').evaluate(el => el.classList.contains('is-open')), 'mobile drawer opens');
	const dl2 = mpage.waitForEvent('download', { timeout: 30000 });
	await mpage.locator('.sf-basket-drawer__pdf').click();
	const dl2res = await dl2;
	ok(/^SINO-FRESH-Basket-/.test(dl2res.suggestedFilename()), 'mobile basket PDF downloads: ' + dl2res.suggestedFilename());

	// mobile contact overflow with notice
	await mpage.goto(BASE + '/products/tablets/', { waitUntil: 'load' });
	await mpage.waitForTimeout(500);
	await completeAndAdd(mpage, true);
	await mpage.goto(BASE + '/contact/?from=basket', { waitUntil: 'load' });
	await mpage.waitForTimeout(800);
	const overflow = await mpage.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
	ok(overflow <= 0, 'mobile contact no horizontal overflow (delta=' + overflow + 'px)');
	await mpage.screenshot({ path: 'screenshots/basket4-mobile-notice.png' });
	await mctx.close();

	await ctx.close();
	await browser.close();
	console.log('\nRESULT: ' + passed + ' passed, ' + failed + ' failed');
	process.exit(failed ? 1 : 0);
})().catch(e => { console.error('FATAL', e); process.exit(1); });

/* Basket stage 2 E2E: header bag + badge, drawer open/close (X, overlay, Esc),
 * empty state, per-item remove, Clear All confirm, cross-page badge persist,
 * mobile full width + no horizontal overflow. */
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
	/* <768px: the summary card is display:none — add via the bottom drawer. */
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

	/* 1. home, empty basket: bag visible, badge hidden */
	await page.goto(BASE + '/', { waitUntil: 'load' });
	await page.waitForTimeout(600);
	const accept = page.locator('.sf-cookie-banner__btn--accept');
	if (await accept.count()) await accept.click();
	const bag = page.locator('.sf-basket-btn');
	ok('bag button visible on home', await bag.isVisible());
	ok('badge hidden at 0', await page.locator('.sf-basket-btn__badge').isHidden());

	/* 2. empty state */
	await bag.click();
	await page.waitForTimeout(400);
	const drawer = page.locator('.sf-basket-drawer');
	ok('drawer opens on bag click', await drawer.isVisible());
	ok('empty state text', /No items yet\. Configure a dosage form/i.test(await page.locator('.sf-basket-drawer__empty').textContent()));
	await page.screenshot({ path: 'screenshots/basket2-desktop-empty.png' });

	/* 3. close via X */
	await page.locator('.sf-basket-drawer__close').click();
	await page.waitForTimeout(400);
	ok('X closes drawer', await drawer.isHidden());

	/* 4. add two items across pages */
	await page.goto(BASE + '/products/soft-chews/', { waitUntil: 'load' });
	await page.waitForTimeout(600);
	await completeAndAdd(page);
	ok('badge shows 1 after add', (await page.locator('.sf-basket-btn__badge').textContent()) === '1');
	ok('badge visible after add', await page.locator('.sf-basket-btn__badge').isVisible());

	await page.goto(BASE + '/products/tablets/', { waitUntil: 'load' });
	await page.waitForTimeout(600);
	ok('badge persists across pages (1)', (await page.locator('.sf-basket-btn__badge').textContent()) === '1');
	await completeAndAdd(page);
	ok('badge shows 2 after second page add', (await page.locator('.sf-basket-btn__badge').textContent()) === '2');

	/* 5. drawer lists both items */
	await page.locator('.sf-basket-btn').click();
	await page.waitForTimeout(400);
	const titles = await page.locator('.sf-basket-drawer__item-title').allTextContents();
	ok('drawer lists 2 items', titles.length === 2);
	ok('item titles', titles.includes('Soft Chews') && titles.includes('Tablets'));
	ok('item summaries present', (await page.locator('.sf-basket-drawer__item-summary').count()) === 2);
	const db = await drawer.boundingBox();
	ok('desktop drawer 400px from right', db && Math.abs(db.x - (1440 - 400)) < 2 && Math.abs(db.width - 400) < 2);
	await page.screenshot({ path: 'screenshots/basket2-desktop-items.png' });

	/* 6. remove single item */
	await page.locator('.sf-basket-drawer__item-remove').first().click();
	await page.waitForTimeout(300);
	ok('remove leaves 1 item', (await page.locator('.sf-basket-drawer__item').count()) === 1);
	ok('badge back to 1', (await page.locator('.sf-basket-btn__badge').textContent()) === '1');
	ok('drawer stays open after remove', await drawer.isVisible());

	/* 7. Esc closes */
	await page.keyboard.press('Escape');
	await page.waitForTimeout(400);
	ok('Esc closes drawer', await drawer.isHidden());

	/* 8. overlay click closes */
	await page.locator('.sf-basket-btn').click();
	await page.waitForTimeout(400);
	await page.locator('.sf-basket-overlay').click({ position: { x: 200, y: 300 } });
	await page.waitForTimeout(400);
	ok('overlay click closes drawer', await drawer.isHidden());

	/* 9. Clear All with confirm */
	await page.locator('.sf-basket-btn').click();
	await page.waitForTimeout(400);
	await page.locator('.sf-basket-drawer__clear').click();
	await page.waitForTimeout(300);
	ok('clear empties list (empty state back)', await page.locator('.sf-basket-drawer__empty').isVisible());
	ok('badge hidden after clear', await page.locator('.sf-basket-btn__badge').isHidden());
	ok('sessionStorage empty', await page.evaluate(() => !sessionStorage.getItem('sinofresh_basket')));

	/* 10. PDF placeholder button no-ops safely */
	await page.goto(BASE + '/products/soft-chews/', { waitUntil: 'load' });
	await page.waitForTimeout(600);
	await page.evaluate(() => {
		sessionStorage.setItem('sinofresh_basket', JSON.stringify([{ slug: 'soft-chews', title: 'Soft Chews', summary: 'Dosage Form: Soft Chews | test', formula: '', addedAt: new Date().toISOString() }]));
		document.dispatchEvent(new CustomEvent('sf:basket-change', { detail: { count: 1, items: [] } }));
	});
	await page.locator('.sf-basket-btn').click();
	await page.waitForTimeout(400);
	await page.locator('.sf-basket-drawer__pdf').click();
	await page.waitForTimeout(300);
	ok('pdf placeholder shows coming-soon toast', /coming soon/i.test(await page.locator('.sf-toast.is-visible').textContent().catch(() => '')));
	await page.keyboard.press('Escape');

	/* ---------- Mobile 375 ---------- */
	const mctx = await browser.newContext({ viewport: { width: 375, height: 720 } });
	const mpage = await mctx.newPage();
	mpage.on('dialog', (d) => d.accept());
	await mpage.goto(BASE + '/products/soft-chews/', { waitUntil: 'load' });
	await mpage.waitForTimeout(600);
	const maccept = mpage.locator('.sf-cookie-banner__btn--accept');
	if (await maccept.count()) await maccept.click();
	await completeAndAdd(mpage, true);
	ok('mobile bag visible', await mpage.locator('.sf-basket-btn').isVisible());
	ok('mobile quote button hidden', !(await mpage.locator('.sf-header__cta .wp-block-button').isVisible()));
	await mpage.locator('.sf-basket-btn').click();
	await mpage.waitForTimeout(400);
	const mdb = await mpage.locator('.sf-basket-drawer').boundingBox();
	ok('mobile drawer full width', mdb && Math.abs(mdb.width - 375) < 2 && mdb.x <= 1);
	ok('no horizontal overflow with drawer open', await mpage.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1));
	await mpage.screenshot({ path: 'screenshots/basket2-mobile-items.png' });
	await mpage.locator('.sf-basket-drawer__close').click();
	await mpage.waitForTimeout(400);
	ok('mobile X closes', await mpage.locator('.sf-basket-drawer').isHidden());

	console.log(results.join('\n'));
	await browser.close();
})();

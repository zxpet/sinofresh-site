/* Factory-tour page: standards band + photo-slot tour route.

   Layout verification + screenshots. The photo slots must already hold the
   final 4:3 frame, so swapping in the real shot never reflows the grid.

   usage:  node tools/_factorytour_shots.js [tag]
*/
const { chromium } = require('playwright-core');

const tag = process.argv[2] || 'after';
const BASE = 'http://sinofresh.local';
const OUT = '../screenshots/';
const HIDE = '.sf-cookie-banner,.sf-float-stack{display:none !important}' +
	'.sf-header,header.wp-block-template-part{position:static !important}';

const run = async (browser, width, height, path, fn) => {
	const ctx = await browser.newContext({ viewport: { width, height }, deviceScaleFactor: 1 });
	const p = await ctx.newPage();
	const errors = [];
	p.on('pageerror', (e) => errors.push(String(e)));
	p.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
	await p.goto(BASE + path, { waitUntil: 'load' });
	await p.addStyleTag({ content: HIDE });
	await p.evaluate(() => document.fonts.ready);
	await p.waitForTimeout(600);
	// pre-scroll: force lazy images in before measuring
	await p.evaluate(async () => {
		const h = document.body.scrollHeight;
		for (let y = 0; y < h; y += 600) { window.scrollTo(0, y); await new Promise((r) => setTimeout(r, 60)); }
		window.scrollTo(0, 0);
	});
	await p.waitForTimeout(400);
	const out = await fn(p);
	await ctx.close();
	return { errors, out };
};

const probe = async (p) => p.evaluate(() => {
	const slots = [...document.querySelectorAll('.sf-photo-slot')];
	const steps = [...document.querySelectorAll('.sf-route__step')].map((e) => e.textContent.trim());
	const nums = [...document.querySelectorAll('.sf-statbar__num')].map((e) => e.textContent.trim());
	const labels = [...document.querySelectorAll('.sf-statbar__label')].map((e) => e.textContent.trim());
	const cells = document.querySelectorAll('.sf-statbar__cell').length;
	const grid = document.querySelector('.sf-statbar__grid');
	const gridCols = grid ? getComputedStyle(grid).gridTemplateColumns.split(' ').length : 0;
	const route = document.querySelector('.sf-route__step')?.closest('.sf-tour-grid');
	const routeCols = route ? getComputedStyle(route).flexDirection : 'n/a';
	const eqRows = [...document.querySelectorAll('.sf-eq-row')].map((r) => ({
		cols: r.querySelectorAll(':scope > .wp-block-column').length,
		cardHeights: [...r.querySelectorAll(':scope > .wp-block-column > .sf-card')].map((k) => Math.round(k.getBoundingClientRect().height)),
	}));
	const rowAligned = eqRows.map((r) => new Set(r.cardHeights).size === 1);
	return {
		slotCount: slots.length,
		slotRatios: slots.map((s) => { const r = s.getBoundingClientRect(); return +(r.width / r.height).toFixed(3); }),
		slotWidths: slots.map((s) => Math.round(s.getBoundingClientRect().width)),
		steps, nums, labels, cells, gridCols, routeCols, eqRows, rowAligned,
		aboutGallery: document.querySelectorAll('.sf-fac__item').length,
		placeholderImgs: document.querySelectorAll('img[src*="fac-placeholder"]').length,
	};
});

(async () => {
	const browser = await chromium.launch();
	const report = {};

	for (const [w, h, name] of [[1440, 900, '1440'], [375, 812, '375']]) {
		const r = await run(browser, w, h, '/factory-tour/', async (p) => {
			await p.screenshot({ path: `${OUT}factorytour-${tag}-full-${name}.png`, fullPage: true });
			// every .sf-eq-row section in document order: standards band, route row 1, route row 2
			const secs = p.locator('section:has(.sf-eq-row)');
			const n = await secs.count();
			for (let i = 0; i < n; i++) {
				const sec = secs.nth(i);
				await sec.scrollIntoViewIfNeeded();
				await p.waitForTimeout(350);
				const box = await sec.boundingBox();
				const over = await sec.evaluate((el) => {
					const last = el.querySelector('.sf-eq-row:last-of-type .sf-tour-card-item:last-child');
					const a = el.getBoundingClientRect(), b = last.getBoundingClientRect();
					return { sectionBottom: Math.round(a.bottom), lastCardBottom: Math.round(b.bottom), overflow: Math.round(b.bottom - a.bottom) };
				});
				console.log(`  [${name}] band#${i} h=${Math.round(box.height)} overflow=${over.overflow}`);
				await sec.screenshot({ path: `${OUT}factorytour-${tag}-band${i}-${name}.png` });
			}
			return probe(p);
		});
		report['factorytour-' + name] = r;
	}

	// about page: 6 photos, 3-column gallery
	const a = await run(browser, 1440, 900, '/about/', async (p) => {
		const g = p.locator('.sf-fac');
		await g.scrollIntoViewIfNeeded();
		await p.waitForTimeout(400);
		await g.screenshot({ path: `${OUT}about-${tag}-gallery-1440.png` });
		return probe(p);
	});
	report['about-1440'] = a;

	console.log(JSON.stringify(report, null, 1));
	await browser.close();
})();

/* Before/after shots of the homepage certification block.

   usage:  node tools/_certbar_shots.js before
           node tools/_certbar_shots.js after
*/
const { chromium } = require('playwright-core');

const tag = process.argv[2] || 'before';
const URL = 'http://sinofresh.local/';
const OUT = '../screenshots/';
const HIDE = '.sf-cookie-banner,.sf-float-stack{display:none !important}';

const run = async (browser, width, height, fn) => {
	const ctx = await browser.newContext({ viewport: { width, height }, deviceScaleFactor: 1 });
	const p = await ctx.newPage();
	await p.goto(URL, { waitUntil: 'load' });
	await p.addStyleTag({ content: HIDE });
	await p.waitForTimeout(1600);
	await fn(p);
	await ctx.close();
};

(async () => {
	const browser = await chromium.launch();

	// desktop: the whole section, top edge to bottom edge, in one frame
	await run(browser, 1440, 900, async (p) => {
		const sec = p.locator('section:has(> .sf-certgrid)');
		await sec.scrollIntoViewIfNeeded();
		await p.waitForTimeout(400);
		await sec.screenshot({ path: OUT + 'certbar-' + tag + '-section-1440.png' });
		console.log('wrote certbar-' + tag + '-section-1440.png');
	});

	// phone
	await run(browser, 375, 812, async (p) => {
		const sec = p.locator('section:has(> .sf-certgrid)');
		await sec.scrollIntoViewIfNeeded();
		await p.waitForTimeout(400);
		await sec.screenshot({ path: OUT + 'certbar-' + tag + '-section-375.png' });
		console.log('wrote certbar-' + tag + '-section-375.png');
	});

	await browser.close();
})();

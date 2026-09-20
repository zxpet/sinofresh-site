/* Before/after shots of the Quality page certificate block.

   usage:  node tools/_cert2col_shots.js before
           node tools/_cert2col_shots.js after
*/
const { chromium } = require('playwright-core');

const tag = process.argv[2] || 'before';
const URL = 'http://sinofresh.local/quality/';
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

const shot = async (p, file) => {
	await p.screenshot({ path: OUT + file });
	console.log('wrote ' + OUT + file);
};

(async () => {
	const browser = await chromium.launch();

	// desktop: the whole block, top edge to bottom edge, in one frame
	await run(browser, 1440, 900, async (p) => {
		const sec = p.locator('section:has(> .sf-certdetail)');
		await sec.scrollIntoViewIfNeeded();
		await p.waitForTimeout(300);
		await sec.screenshot({ path: OUT + 'cert-2col-' + tag + '-section-1440.png' });
		console.log('wrote ' + OUT + 'cert-2col-' + tag + '-section-1440.png');
		await p.evaluate(() => document.querySelector('.sf-certdetail').scrollIntoView({ block: 'start', behavior: 'instant' }));
		await p.waitForTimeout(300);
		await shot(p, 'cert-2col-' + tag + '-viewport-1440.png');
	});

	// desktop 1024 — the tablet breakpoint
	await run(browser, 1024, 900, async (p) => {
		await p.evaluate(() => document.querySelector('.sf-certdetail').scrollIntoView({ block: 'start', behavior: 'instant' }));
		await p.waitForTimeout(300);
		await shot(p, 'cert-2col-' + tag + '-viewport-1024.png');
	});

	// phone
	await run(browser, 375, 812, async (p) => {
		const sec = p.locator('section:has(> .sf-certdetail)');
		await sec.screenshot({ path: OUT + 'cert-2col-' + tag + '-section-375.png' });
		console.log('wrote ' + OUT + 'cert-2col-' + tag + '-section-375.png');
	});

	await browser.close();
})();

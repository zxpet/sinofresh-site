/* Phase 1 delivery shots — the Quality page copy change and the CTA band link.

     rows-a       the first certificate rows: "Request Certificate" (was
                  "Download Certificate (PDF)")
     rows-haccp   the HACCP / BRC rows, same label, same type as the others
     cta-context  the CTA band in the viewport
     cta          the band itself, cropped
     cta-hover    the outline button hovered — it reads as a control
     cta-375      the band at phone width

   Run:  NODE_PATH=~/.workbuddy/binaries/node/workspace/node_modules \
         node tools/_cert_p1_shots.js
*/
const { chromium } = require('playwright-core');

const BASE = 'http://sinofresh.local/quality/';
const OUT = '../screenshots/';
const HIDE = '.sf-cookie-banner,.sf-float-stack{display:none !important}';

const run = async (browser, width, height, fn) => {
	const ctx = await browser.newContext({ viewport: { width, height }, deviceScaleFactor: 2 });
	const p = await ctx.newPage();
	await p.goto(BASE, { waitUntil: 'load' });
	await p.addStyleTag({ content: HIDE });
	await p.waitForTimeout(1800);
	await fn(p);
	await ctx.close();
};

const into = async (p, loc, block) => {
	await loc.evaluate((el, b) => el.scrollIntoView({ block: b, behavior: 'instant' }), block || 'center');
	await p.waitForTimeout(260);
};

const shotEl = async (el, file) => {
	await el.screenshot({ path: OUT + file });
	console.log('wrote ' + OUT + file);
};

const band = (p) => p.locator('.wp-block-group.has-primary-background-color')
	.filter({ hasText: 'Request COA Sample or Book a Factory Tour' }).first();

(async () => {
	const browser = await chromium.launch();

	await run(browser, 1440, 900, async (p) => {
		await into(p, p.locator('.sf-certdetail'), 'start');
		await p.screenshot({ path: OUT + 'certs-p1-rows-a-1440.png' });
		console.log('wrote ' + OUT + 'certs-p1-rows-a-1440.png');
	});

	await run(browser, 1440, 900, async (p) => {
		await into(p, p.locator('.sf-certrow').nth(4));
		await p.screenshot({ path: OUT + 'certs-p1-rows-haccp-1440.png' });
		console.log('wrote ' + OUT + 'certs-p1-rows-haccp-1440.png');
	});

	await run(browser, 1440, 900, async (p) => {
		const b = band(p);
		await into(p, b);
		await p.screenshot({ path: OUT + 'certs-p1-cta-context-1440.png' });
		console.log('wrote ' + OUT + 'certs-p1-cta-context-1440.png');
		await shotEl(b, 'certs-p1-cta-1440.png');
		await b.locator('.wp-block-button.is-style-outline a').hover();
		await p.waitForTimeout(280);
		await shotEl(b, 'certs-p1-cta-hover-1440.png');
	});

	await run(browser, 375, 812, async (p) => {
		await into(p, band(p));
		await p.screenshot({ path: OUT + 'certs-p1-cta-375.png' });
		console.log('wrote ' + OUT + 'certs-p1-cta-375.png');
	});

	await browser.close();
})();

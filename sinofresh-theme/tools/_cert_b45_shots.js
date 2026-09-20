/* B4.5 delivery shots — the certificate controls, driven through the page's own
   links (no injected trigger), so each capture is the real wiring:

     rows          the certificate list with the HACCP/BRC request lines
     row-fda       the FDA row, trigger link hovered
     fda-open      the same link clicked: the request dialog, key already fda
     haccp-open    the HACCP "available upon request" line clicked
     success       a real submission, success state
     viewer        the lightbox with its request line
     cta           the CTA band's Request COA Sample button

   Run:  NODE_PATH=~/.workbuddy/binaries/node/workspace/node_modules \
         node tools/_cert_b45_shots.js
*/
const { chromium } = require('playwright-core');

const BASE = 'http://sinofresh.local/quality/';
const OUT = '../screenshots/';
const HIDE = '.sf-cookie-banner,.sf-float-stack{display:none !important}';

const shot = async (browser, width, height, fn, file) => {
	const ctx = await browser.newContext({ viewport: { width, height }, deviceScaleFactor: 2 });
	const p = await ctx.newPage();
	await p.goto(BASE, { waitUntil: 'load' });
	await p.addStyleTag({ content: HIDE });
	await p.waitForTimeout(1800);
	await fn(p);
	await p.screenshot({ path: OUT + file });
	console.log('wrote ' + OUT + file);
	await ctx.close();
};

/* the on-page control for one document key, scrolled into the middle */
const trigger = (p, cert) => p.locator('[data-cert="' + cert + '"]').first();
const bringIn = async (p, loc) => {
	await loc.evaluate((el) => el.scrollIntoView({ block: 'center', behavior: 'instant' }));
	await p.waitForTimeout(200);
};

(async () => {
	const browser = await chromium.launch();

	await shot(browser, 1440, 900, async (p) => {
		await p.evaluate(() => document.querySelector('.sf-certdetail').scrollIntoView({ block: 'start', behavior: 'instant' }));
		await p.waitForTimeout(250);
	}, 'certs-b45-rows-1440.png');

	await shot(browser, 1440, 900, async (p) => {
		const t = trigger(p, 'fda');
		await bringIn(p, t);
		await t.hover();
		await p.waitForTimeout(200);
	}, 'certs-b45-row-fda-1440.png');

	await shot(browser, 1440, 900, async (p) => {
		const t = trigger(p, 'fda');
		await bringIn(p, t);
		await t.click();
		await p.waitForSelector('.sf-certmodal.is-open', { timeout: 5000 });
		await p.waitForTimeout(500);
	}, 'certs-b45-fda-open-1440.png');

	await shot(browser, 1440, 900, async (p) => {
		const t = trigger(p, 'haccp');
		await bringIn(p, t);
		await t.click();
		await p.waitForSelector('.sf-certmodal.is-open', { timeout: 5000 });
		await p.waitForTimeout(500);
	}, 'certs-b45-haccp-open-1440.png');

	await shot(browser, 1440, 900, async (p) => {
		const t = trigger(p, 'fda');
		await bringIn(p, t);
		await t.click();
		await p.waitForSelector('.sf-certmodal.is-open', { timeout: 5000 });
		await p.fill('#input_5_1', 'Acme Pet Nutrition');
		await p.fill('#input_5_2', 'Dana Reyes');
		await p.fill('#input_5_3', 'dana@acmepetnutrition.com');
		await p.click('#gform_submit_button_5');
		await p.waitForSelector('.sf-certmodal.is-success', { timeout: 15000 });
		await p.waitForTimeout(700);
	}, 'certs-b45-success-1440.png');

	await shot(browser, 1440, 900, async (p) => {
		const thumb = p.locator('.sf-certrow__media a').first();
		await bringIn(p, thumb);
		await thumb.click();
		await p.waitForTimeout(800);
	}, 'certs-b45-viewer-1440.png');

	await shot(browser, 1440, 900, async (p) => {
		const t = trigger(p, 'coa-sample').last();
		await bringIn(p, t);
		await t.click();
		await p.waitForSelector('.sf-certmodal.is-open', { timeout: 5000 });
		await p.waitForTimeout(500);
	}, 'certs-b45-cta-open-1440.png');

	await shot(browser, 375, 812, async (p) => {
		const t = trigger(p, 'fda');
		await bringIn(p, t);
		await t.click();
		await p.waitForSelector('.sf-certmodal.is-open', { timeout: 5000 });
		await p.waitForTimeout(500);
	}, 'certs-b45-fda-open-375.png');

	await shot(browser, 375, 812, async (p) => {
		const t = trigger(p, 'fda');
		await bringIn(p, t);
		await t.click();
		await p.waitForSelector('.sf-certmodal.is-open', { timeout: 5000 });
		await p.fill('#input_5_1', 'Acme Pet Nutrition');
		await p.fill('#input_5_2', 'Dana Reyes');
		await p.fill('#input_5_3', 'dana@acmepetnutrition.com');
		await p.click('#gform_submit_button_5');
		await p.waitForSelector('.sf-certmodal.is-success', { timeout: 15000 });
		await p.waitForTimeout(700);
	}, 'certs-b45-success-375.png');

	await browser.close();
})();

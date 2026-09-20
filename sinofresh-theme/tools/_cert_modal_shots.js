/* Screenshots for the B4.1/B4.2 review.
   Run: NODE_PATH=~/.workbuddy/binaries/node/workspace/node_modules \
       node tools/_cert_modal_shots.js
   Writes screenshots/certmodal-*.png. Viewport shots only — a fullPage
   capture re-lays-out a fixed dialog. */
const { chromium } = require('playwright-core');
const path = require('path');

const BASE = 'http://sinofresh.local/quality/';
const OUT = path.resolve(__dirname, '../../screenshots');
const HIDE = '.sf-cookie-banner,.sf-float-stack{display:none !important}';

(async () => {
	const b = await chromium.launch();

	const dctx = await b.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 });
	const dp = await dctx.newPage();
	await dp.goto(BASE, { waitUntil: 'load' });
	await dp.addStyleTag({ content: HIDE });
	await dp.evaluate(() => document.fonts.ready);
	await dp.waitForTimeout(400);

	await dp.click('.sf-coa__btn--primary');
	await dp.waitForTimeout(600);
	await dp.screenshot({ path: path.join(OUT, 'certmodal-open-1440.png') });
	await dp.locator('.sf-certmodal__panel').screenshot({ path: path.join(OUT, 'certmodal-form-top-1440.png') });

	// bottom of the form: the dialog body scrolls, the heading does not
	await dp.evaluate(() => {
		const body = document.querySelector('.sf-certmodal__body');
		body.scrollTop = body.scrollHeight;
	});
	await dp.waitForTimeout(400);
	await dp.locator('.sf-certmodal__panel').screenshot({ path: path.join(OUT, 'certmodal-form-bottom-1440.png') });
	await dctx.close();

	const mctx = await b.newContext({ viewport: { width: 375, height: 700 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
	const mp = await mctx.newPage();
	await mp.goto(BASE, { waitUntil: 'load' });
	await mp.addStyleTag({ content: HIDE });
	await mp.evaluate(() => document.fonts.ready);
	await mp.waitForTimeout(400);
	await mp.click('.sf-coa__btn--primary');
	await mp.waitForTimeout(600);
	await mp.screenshot({ path: path.join(OUT, 'certmodal-open-375.png') });
	await mp.evaluate(() => {
		const body = document.querySelector('.sf-certmodal__body');
		body.scrollTop = body.scrollHeight;
	});
	await mp.waitForTimeout(400);
	await mp.screenshot({ path: path.join(OUT, 'certmodal-form-bottom-375.png') });
	await mctx.close();

	await b.close();
	console.log('shots written to ' + OUT);
})();

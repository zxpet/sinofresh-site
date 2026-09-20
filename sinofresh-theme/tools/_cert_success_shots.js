/* B4.3 delivery shots — the certificate dialog's success state.

   Real submission per shot: the card is whatever the live postback produced.
   Run:  NODE_PATH=~/.workbuddy/binaries/node/workspace/node_modules \
         node tools/_cert_success_shots.js
*/
const { chromium } = require('playwright-core');

const BASE = 'http://sinofresh.local/quality/';
const OUT = '../screenshots/';

const SHOTS = [
	{ cert: 'fda', file: 'certs-success-fda-1440.png', width: 1440, height: 900 },
	{ cert: 'haccp', file: 'certs-success-haccp-1440.png', width: 1440, height: 900 },
	{ cert: 'fda', file: 'certs-success-fda-375.png', width: 375, height: 812 },
	{ cert: 'haccp', file: 'certs-success-haccp-375.png', width: 375, height: 812 },
];

(async () => {
	const browser = await chromium.launch();

	for (const shot of SHOTS) {
		const ctx = await browser.newContext({ viewport: { width: shot.width, height: shot.height }, deviceScaleFactor: 2 });
		const p = await ctx.newPage();
		await p.goto(BASE, { waitUntil: 'load' });
		await p.addStyleTag({ content: '.sf-cookie-banner,.sf-float-stack{display:none !important}' });
		await p.waitForTimeout(2200);

		await p.evaluate((c) => {
			const b = document.createElement('button');
			b.id = 'sf-shot-trigger';
			b.type = 'button';
			b.setAttribute('data-cert', c);
			b.style.cssText = 'position:fixed;top:220px;left:24px;z-index:20002';
			b.textContent = c;
			document.body.appendChild(b);
		}, shot.cert);
		await p.click('#sf-shot-trigger');
		await p.waitForSelector('.sf-certmodal.is-open', { timeout: 5000 });

		await p.fill('#input_5_1', 'Acme Pet Nutrition');
		await p.fill('#input_5_2', 'Dana Reyes');
		await p.fill('#input_5_3', 'dana@acmepetnutrition.com');
		await p.click('#gform_submit_button_5');
		await p.waitForSelector('.sf-certmodal.is-success', { timeout: 15000 });
		await p.waitForTimeout(600);   // let the fade settle before capturing

		await p.screenshot({ path: OUT + shot.file });
		console.log('wrote ' + OUT + shot.file);
		await ctx.close();
	}

	await browser.close();
})();

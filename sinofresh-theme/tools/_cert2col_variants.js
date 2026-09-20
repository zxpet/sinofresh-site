/* Probe: pick the <=768 card padding / thumbnail that does not grow the block.
   Injects candidate overrides at runtime and measures, so the file is only
   touched once the winner is known. */
const { chromium } = require('playwright-core');

const URL = 'http://sinofresh.local/quality/';
const HIDE = '.sf-cookie-banner,.sf-float-stack{display:none !important}';

const variants = [
	{ name: 'A  pad14/16 thumb88 gap16 (current)', css: '' },
	{
		name: 'B  pad12 thumb88 gap12',
		css: `.sf-certrow{padding:12px}.sf-certrow__media img,.sf-certrow__media--placeholder{width:88px;height:121px}`,
	},
	{
		name: 'C  pad12 thumb76 gap12',
		css: `.sf-certrow{padding:12px}.sf-certrow__media img,.sf-certrow__media--placeholder{width:76px;height:105px}.sf-certrow{gap:12px}`,
	},
	{
		name: 'D  pad12 thumb72 gap12',
		css: `.sf-certrow{padding:12px;gap:12px}.sf-certrow__media img,.sf-certrow__media--placeholder{width:72px;height:99px}`,
	},
	{
		name: 'E  pad14/12 thumb88 gap12',
		css: `.sf-certrow{padding:14px 12px;gap:12px}`,
	},
	{
		name: 'F  pad12 lh tighter',
		css: `.sf-certrow{padding:12px;gap:12px}.sf-certrow__desc{line-height:1.5}`,
	},
];

(async () => {
	const browser = await chromium.launch();
	console.log('before-state reference: detail 1462.5 / section 1750.8 (375px)');
	for (const v of variants) {
		const ctx = await browser.newContext({ viewport: { width: 375, height: 812 }, deviceScaleFactor: 1 });
		const p = await ctx.newPage();
		await p.goto(URL, { waitUntil: 'load' });
		await p.addStyleTag({ content: HIDE });
		if (v.css) await p.addStyleTag({ content: v.css });
		await p.waitForTimeout(900);
		const r = await p.evaluate(() => {
			const d = document.querySelector('.sf-certdetail');
			const sec = d.closest('section');
			const rows = [...document.querySelectorAll('.sf-certrow')].map((el) => {
				const b = el.querySelector('.sf-certrow__body');
				const links = el.querySelector('.sf-certrow__links');
				return {
					h: +el.getBoundingClientRect().height.toFixed(1),
					body: +b.getBoundingClientRect().height.toFixed(1),
					linksH: links ? +links.getBoundingClientRect().height.toFixed(1) : 0,
				};
			});
			return {
				detail: +d.getBoundingClientRect().height.toFixed(1),
				section: +sec.getBoundingClientRect().height.toFixed(1),
				rows,
				overflow: document.documentElement.scrollWidth - innerWidth,
			};
		});
		console.log('\n' + v.name);
		console.log('   detail=' + r.detail + '  section=' + r.section + '  hOverflow=' + r.overflow);
		console.log('   rows: ' + r.rows.map((x) => x.h + '(body ' + x.body + ' links ' + x.linksH + ')').join('  '));
		await ctx.close();
	}
	await browser.close();
})();

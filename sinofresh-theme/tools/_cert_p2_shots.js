/* Phase 2 delivery shots — 4 → 6 certification wording, station-wide.

     p2-hero-soft-chews-1440   dosage page hero, literal `·` badge row
     p2-hero-liquids-1440      dosage page hero, `&middot;` entity badge row
     p2-quality-badge-1440     Quality page hero badge row
     p2-quality-rows-1440      Quality page certificate rows (HACCP / BRC)
     p2-factory-badge-1440     Factory Tour hero badge row (now + ISO 8)
     p2-factory-cleanroom-1440 Factory Tour checklist, cleanroom line
     p2-services-list-1440     Services compliance list (3 + 3)
     p2-topbar-1440            top-bar badge strip, cropped element (every page)

   Run:  NODE_PATH=~/.workbuddy/binaries/node/workspace/node_modules \
         node tools/_cert_p2_shots.js
*/
const { chromium } = require('playwright-core');

const OUT = '../screenshots/';
const HIDE = '.sf-cookie-banner,.sf-float-stack{display:none !important}';

const open = async (browser, url) => {
	const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 });
	const p = await ctx.newPage();
	await p.goto(url, { waitUntil: 'load' });
	await p.addStyleTag({ content: HIDE });
	await p.waitForTimeout(1800);
	return { ctx, p };
};

const into = async (p, loc, block) => {
	await loc.evaluate((el, b) => el.scrollIntoView({ block: b, behavior: 'instant' }), block || 'center');
	await p.waitForTimeout(320);
};

const viewport = async (p, file) => {
	await p.screenshot({ path: OUT + file });
	console.log('wrote ' + OUT + file);
};

const elShot = async (loc, file) => {
	await loc.screenshot({ path: OUT + file });
	console.log('wrote ' + OUT + file);
};

/* The badge row is a plain paragraph in the hero column. Anchoring on the full
   six-name string keeps the top-bar strip out of the match: the strip renders
   its names with no separator text, so it never matches the " · " form. */
const heroRow = (p, text) => p.locator('p').filter({ hasText: text }).first();

const SIX = 'FDA · cGMP · ISO 9001 · FSSC 22000 · HACCP · BRC';

(async () => {
	const browser = await chromium.launch();

	{
		const { ctx, p } = await open(browser, 'http://sinofresh.local/soft-chews/');
		await into(p, heroRow(p, SIX));
		await viewport(p, 'p2-hero-soft-chews-1440.png');
		await ctx.close();
	}

	{
		const { ctx, p } = await open(browser, 'http://sinofresh.local/liquids/');
		await into(p, heroRow(p, SIX));
		await viewport(p, 'p2-hero-liquids-1440.png');
		await ctx.close();
	}

	{
		const { ctx, p } = await open(browser, 'http://sinofresh.local/quality/');
		await into(p, heroRow(p, SIX));
		await viewport(p, 'p2-quality-badge-1440.png');
		await ctx.close();
	}

	{
		const { ctx, p } = await open(browser, 'http://sinofresh.local/quality/');
		await into(p, p.locator('.sf-certrow').nth(4));
		await viewport(p, 'p2-quality-rows-1440.png');
		await ctx.close();
	}

	{
		const { ctx, p } = await open(browser, 'http://sinofresh.local/factory-tour/');
		await into(p, heroRow(p, 'ISO 8 cleanroom'));
		await viewport(p, 'p2-factory-badge-1440.png');
		/* the checklist line is the ✓-prefixed paragraph; the hero prose and the
		   badge row both mention ISO 8, so anchor on the tick. */
		await into(p, p.locator('p').filter({ hasText: '✓' }).filter({ hasText: 'ISO 8 cleanroom' }).first());
		await viewport(p, 'p2-factory-cleanroom-1440.png');
		await ctx.close();
	}

	{
		const { ctx, p } = await open(browser, 'http://sinofresh.local/services/');
		await into(p, p.locator('li').filter({ hasText: 'FDA registration' }).first());
		await viewport(p, 'p2-services-list-1440.png');
		await ctx.close();
	}

	{
		const { ctx, p } = await open(browser, 'http://sinofresh.local/');
		const strip = p.locator('.sf-topbar-badges').first();
		await strip.waitFor({ state: 'visible' });
		await elShot(strip, 'p2-topbar-1440.png');
		await ctx.close();
	}

	await browser.close();
})();

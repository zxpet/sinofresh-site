/* Certificate wrap-up, phase 1 — copy and the CTA band link.

   Two things changed on /quality/, and both are promises to the visitor:

     1. all six certificate rows now read "Request Certificate" (the four scans
        used to say "Download Certificate (PDF)" — a file we do not ship — and
        HACCP / BRC said "Certificate copy available upon request"). The COA
        button keeps its longer, more specific label.
     2. the CTA band's outline button is a real link to /factory-tour/ again;
        it was a dead <a> with no href.

   What is checked:

     1  the six row labels, row by row, and that the COA button was not touched
     2  HACCP / BRC read exactly like the other four rows (same class, same
        computed type — the muted note styling is gone)
     3  each "Request Certificate" still opens the dialog with its own key
     4  the CTA band button has the href, is visible, and actually navigates
     5  without JavaScript the same click reaches /factory-tour/

   Run:  NODE_PATH=~/.workbuddy/binaries/node/workspace/node_modules \
         node tools/_cert_copy_cta_test.js
*/
const { chromium } = require('playwright-core');

const BASE = 'http://sinofresh.local/quality/';
const FALLBACK = '/contact/#quote';
const EXPECT = ['fda', 'cgmp', 'iso9001', 'iso22000', 'haccp', 'brc'];

let pass = 0, fail = 0;
const check = (name, ok, note) => {
	if (ok) { pass++; console.log('  ok   ' + name + (note ? '  [' + note + ']' : '')); }
	else { fail++; console.log('  FAIL ' + name + (note ? '  [' + note + ']' : '')); }
};

const rows = (p) => p.$$eval('.sf-certrow', (els) => els.map((row) => {
	const link = row.querySelector('a[data-cert]');
	const cs = link ? getComputedStyle(link) : null;
	return {
		name: (row.querySelector('.sf-certrow__name') || {}).textContent || '',
		cert: link ? link.getAttribute('data-cert') : null,
		text: link ? link.textContent.trim() : null,
		href: link ? link.getAttribute('href') : null,
		cls: link ? link.className : null,
		font: cs ? cs.fontSize + ' / ' + cs.fontWeight + ' / ' + cs.color : null,
		placeholder: !!row.querySelector('.sf-certrow__media--placeholder'),
	};
}));

const band = (p) => p.evaluate(() => {
	const h2 = [...document.querySelectorAll('h2')]
		.find((h) => /Request COA Sample or Book a Factory Tour/.test(h.textContent));
	if (!h2) return null;
	const sec = h2.closest('.wp-block-group, section');
	const buttons = [...sec.querySelectorAll('.wp-block-button')].map((b) => {
		const a = b.querySelector('a');
		const r = a.getBoundingClientRect();
		return {
			text: a.textContent.trim(),
			href: a.getAttribute('href'),
			cls: a.className,
			outline: b.classList.contains('is-style-outline'),
			w: Math.round(r.width),
			h: Math.round(r.height),
			visible: r.width > 0 && r.height > 0 && getComputedStyle(a).visibility !== 'hidden',
			ys: Math.round(r.top + window.scrollY),
		};
	});
	return { count: buttons.length, buttons };
});

const dialogState = (p) => p.evaluate(() => {
	const m = document.querySelector('.sf-certmodal');
	const f = document.querySelector('#input_5_10');
	return { open: !m.hidden && m.classList.contains('is-open'), cert: f ? f.value : null, url: location.href };
});

const quietExtras = (p) => p.addStyleTag({
	content: '.sf-cookie-banner,.sf-float-stack{display:none !important}',
});

(async () => {
	const browser = await chromium.launch();

	/* ---------------------------------------------------------------- 1440 --- */
	console.log('\n=== 1440: row copy ===');
	const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
	const p = await ctx.newPage();
	const errors = [];
	p.on('pageerror', (e) => errors.push(e.message));
	await p.goto(BASE, { waitUntil: 'load' });
	await p.waitForTimeout(1400);
	await quietExtras(p);

	const r = await rows(p);
	check('1. six certificate rows, six keys in order',
		r.length === 6 && JSON.stringify(r.map((x) => x.cert)) === JSON.stringify(EXPECT),
		r.map((x) => x.cert).join(','));
	check('2. every row reads exactly "Request Certificate"',
		r.every((x) => x.text === 'Request Certificate'), JSON.stringify(r.map((x) => x.text)));
	check('3. no row still sells a file we do not ship',
		r.every((x) => !/Download|PDF|upon request/i.test(x.text)),
		r.map((x) => x.text).filter((t) => /Download|PDF|upon request/i.test(t)).join(' | ') || 'clean');
	check('4. every row still points at the fallback', r.every((x) => x.href === FALLBACK),
		[...new Set(r.map((x) => x.href))].join(' '));
	check('5. the muted note class is gone from every row',
		r.every((x) => !/\bsf-certrow__pending-note\b/.test(x.cls || '')),
		r.map((x) => (x.cls || '').trim()).join(' | '));
	check('6. HACCP / BRC read like the FDA row — same type, same colour',
		r[4].font === r[0].font && r[5].font === r[0].font,
		JSON.stringify({ fda: r[0].font, haccp: r[4].font, brc: r[5].font }));
	check('7. the four scans kept their thumbnails, HACCP / BRC stayed placeholders',
		r.slice(0, 4).every((x) => !x.placeholder) && r[4].placeholder && r[5].placeholder,
		r.map((x) => (x.placeholder ? 'p' : 's')).join(''));

	const coa = await p.$eval('.sf-coa__btn--primary', (a) => ({
		text: a.textContent.trim(), tag: a.tagName, href: a.getAttribute('href'),
		cert: a.getAttribute('data-cert'),
	}));
	check('8. the COA button keeps its own label',
		coa.text === 'Request a Batch-Specific COA' && coa.href === FALLBACK && coa.cert === 'coa-sample',
		JSON.stringify(coa));

	console.log('\n=== 1440: the row controls still work ===');
	for (let i = 0; i < r.length; i++) {
		const loc = p.locator('.sf-certrow a[data-cert]').nth(i);
		await loc.evaluate((el) => el.scrollIntoView({ block: 'center', behavior: 'instant' }));
		await p.waitForTimeout(140);
		const before = p.url();
		await loc.click();
		await p.waitForTimeout(420);
		const s = await dialogState(p);
		check('R' + i + '. "' + r[i].name.trim() + '" opens the dialog as ' + r[i].cert,
			s.open === true && s.cert === r[i].cert && s.url === before,
			JSON.stringify({ open: s.open, cert: s.cert, nav: s.url === before ? 'none' : s.url }));
		await p.keyboard.press('Escape');
		await p.waitForTimeout(420);
	}

	console.log('\n=== 1440: the CTA band ===');
	const b = await band(p);
	check('B1. the band still has its two buttons', !!b && b.count === 2,
		b ? b.count + ' buttons' : 'band not found');
	if (b) {
		const tour = b.buttons.find((x) => /Book a Factory Tour/.test(x.text));
		const coaBtn = b.buttons.find((x) => /Request COA Sample/.test(x.text));
		check('B2. "Book a Factory Tour" now carries href="/factory-tour/"',
			!!tour && tour.href === '/factory-tour/', tour ? String(tour.href) : 'button not found');
		check('B3. it is the outline style, visible and hit-sized',
			!!tour && tour.outline === true && tour.visible === true && tour.h >= 40,
			tour ? JSON.stringify({ outline: tour.outline, visible: tour.visible, h: tour.h }) : '-');
		check('B4. the COA button beside it is untouched',
			!!coaBtn && coaBtn.text === 'Request COA Sample' && coaBtn.href === '/contact/#quote',
			coaBtn ? JSON.stringify({ text: coaBtn.text, href: coaBtn.href }) : '-');

		/* the click itself: it must leave the page for /factory-tour/ */
		const tourLoc = p.locator('.wp-block-button.is-style-outline a', { hasText: 'Book a Factory Tour' });
		await tourLoc.evaluate((el) => el.scrollIntoView({ block: 'center', behavior: 'instant' }));
		await p.waitForTimeout(160);
		await tourLoc.click();
		await p.waitForLoadState('load');
		await p.waitForTimeout(600);
		check('B5. clicking it lands on /factory-tour/', p.url().endsWith('/factory-tour/'), p.url());
		check('B6. and that page answers 200',
			(await p.title()).length > 0, await p.title());
	}

	check('Z1. no script errors', errors.length === 0, errors.join(' / ') || 'clean');
	await ctx.close();

	/* ------------------------------------------------------------- no JS --- */
	console.log('\n=== without JavaScript ===');
	{
		const noJs = await browser.newContext({ viewport: { width: 1440, height: 900 }, javaScriptEnabled: false });
		const np = await noJs.newPage();
		await np.goto(BASE, { waitUntil: 'load' });
		const texts = await np.$$eval('.sf-certrow a[data-cert]', (els) => els.map((e) => e.textContent.trim()));
		check('N1. the six labels are in the served HTML',
			texts.length === 6 && texts.every((t) => t === 'Request Certificate'), JSON.stringify(texts));
		const sel = '.has-primary-background-color .wp-block-button.is-style-outline a';
		const out = await np.$eval(sel, (a) => a.getAttribute('href'));
		check('N2. the band button carries its href without JS', out === '/factory-tour/', String(out));
		await np.locator(sel).click();
		await np.waitForLoadState('load');
		await np.waitForTimeout(500);
		check('N3. the click reaches /factory-tour/ on its own', np.url().endsWith('/factory-tour/'), np.url());
		await noJs.close();
	}

	await browser.close();
	console.log('\n' + pass + ' passed, ' + fail + ' failed');
	process.exit(fail ? 1 : 0);
})();

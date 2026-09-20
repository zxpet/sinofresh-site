/* Probe: measured geometry of the homepage certification section
   (.sf-certgrid + "View Full Certifications" button), so the proposed
   third-party lab icon bar can be sized against real numbers.
   Prints at 1440 / 1024 / 768 / 375. */
const { chromium } = require('playwright-core');

const URL = 'http://sinofresh.local/';
const HIDE = '.sf-cookie-banner,.sf-float-stack{display:none !important}';

const probe = async (browser, width) => {
	const ctx = await browser.newContext({ viewport: { width, height: 900 }, deviceScaleFactor: 1 });
	const p = await ctx.newPage();
	await p.goto(URL, { waitUntil: 'load' });
	await p.addStyleTag({ content: HIDE });
	await p.waitForTimeout(1200);

	const out = await p.evaluate(() => {
		const box = (el) => {
			if (!el) return null;
			const r = el.getBoundingClientRect();
			return { w: +r.width.toFixed(1), h: +r.height.toFixed(1), top: +r.top.toFixed(1), bottom: +r.bottom.toFixed(1) };
		};
		const grid = document.querySelector('.sf-certgrid');
		const section = grid.closest('section');
		const cards = [...grid.querySelectorAll('.sf-certcard')].map((el) => {
			const cs = getComputedStyle(el);
			const seal = el.querySelector('.sf-certcard__seal');
			const sr = seal.getBoundingClientRect();
			return {
				name: el.querySelector('.sf-certcard__name')?.textContent.trim(),
				box: box(el),
				pad: cs.paddingTop + ' ' + cs.paddingRight + ' ' + cs.paddingBottom + ' ' + cs.paddingLeft,
				radius: cs.borderRadius + ' / ' + cs.borderTopWidth + ' ' + cs.borderTopColor,
				bg: cs.backgroundColor,
				sealCss: cs.padding, // placeholder, overwritten below
				seal: { w: +sr.width.toFixed(1), h: +sr.height.toFixed(1) },
				sealAttr: seal.getAttribute('width') + 'x' + seal.getAttribute('height') + ' vb=' + seal.getAttribute('viewBox'),
				issuer: el.querySelector('.sf-certcard__issuer')?.textContent.trim(),
			};
		});
		const gridCs = getComputedStyle(grid);
		const buttonsWrap = section.querySelector('.wp-block-buttons');
		const btn = section.querySelector('.wp-block-button__link');
		const paragraphs = [...section.querySelectorAll(':scope > p')].map((e) => ({
			t: e.textContent.trim().slice(0, 60), h: box(e).h, mt: getComputedStyle(e).marginTop, mb: getComputedStyle(e).marginBottom,
		}));
		const h2 = section.querySelector('h2');
		const directKids = [...section.children].map((e) => ({
			cls: (e.className || '').toString().slice(0, 46),
			tag: e.tagName,
			h: box(e).h,
			mt: getComputedStyle(e).marginTop,
			mb: getComputedStyle(e).marginBottom,
		}));
		return {
			viewport: { w: innerWidth, h: innerHeight },
			section: { ...box(section), pad: getComputedStyle(section).paddingTop + ' ' + getComputedStyle(section).paddingBottom, mt: getComputedStyle(section).marginTop, bg: getComputedStyle(section).backgroundColor },
			sectionParent: section.parentElement.className.toString().slice(0, 60),
			h2: { t: h2.textContent.trim(), h: box(h2).h, mb: getComputedStyle(h2).marginBottom },
			eyebrow: box(section.querySelector('.sf-eyebrow'))?.h,
			paragraphs,
			grid: { ...box(grid), cols: gridCs.gridTemplateColumns, gap: gridCs.rowGap + ' / ' + gridCs.columnGap, mt: gridCs.marginTop },
			cards,
			buttonsWrap: { ...box(buttonsWrap), mt: getComputedStyle(buttonsWrap).marginTop },
			btn: { ...box(btn), label: btn.textContent.trim(), h: getComputedStyle(btn).height, pad: getComputedStyle(btn).padding, radius: getComputedStyle(btn).borderRadius },
			gapGridToButton: +(buttonsWrap.getBoundingClientRect().top - grid.getBoundingClientRect().bottom).toFixed(1),
			gapButtonToSectionEnd: +(section.getBoundingClientRect().bottom - btn.getBoundingClientRect().bottom).toFixed(1),
			directKids,
		};
	});
	await ctx.close();
	return { width, ...out };
};

(async () => {
	const browser = await chromium.launch();
	for (const w of [1440, 1024, 768, 375]) {
		const r = await probe(browser, w);
		console.log('\n================ viewport ' + w + ' ================');
		console.log('section      ' + JSON.stringify(r.section));
		console.log('parent       ' + r.sectionParent);
		console.log('eyebrow h    ' + r.eyebrow);
		console.log('h2           ' + JSON.stringify(r.h2));
		r.paragraphs.forEach((x) => console.log('  p          ' + JSON.stringify(x)));
		console.log('grid         ' + JSON.stringify(r.grid));
		r.cards.forEach((x) => console.log('  card ' + (x.name || '').padEnd(20) + ' box=' + JSON.stringify(x.box) + ' seal=' + x.seal.w + 'x' + x.seal.h + ' (' + x.sealAttr + ')'));
		console.log('  card padding      ' + r.cards[0].pad);
		console.log('  card radius/border ' + r.cards[0].radius);
		console.log('  card bg            ' + r.cards[0].bg);
		console.log('buttonsWrap  ' + JSON.stringify(r.buttonsWrap));
		console.log('btn          ' + JSON.stringify(r.btn));
		console.log('gap grid->btn        = ' + r.gapGridToButton);
		console.log('gap btn->section end = ' + r.gapButtonToSectionEnd);
		console.log('-- direct children of section --');
		r.directKids.forEach((x) => console.log('   ' + (x.tag + ' ' + x.cls).padEnd(52) + ' h=' + x.h + ' mt=' + x.mt + ' mb=' + x.mb));
	}
	await browser.close();
})();

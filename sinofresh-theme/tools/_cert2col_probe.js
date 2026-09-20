/* Probe: measured geometry of the Quality page certificate section.
   Prints per-row and section boxes at 1440 / 900 / 375 so the 2-column
   redesign can be sized against real numbers rather than the CSS. */
const { chromium } = require('playwright-core');

const URL = 'http://sinofresh.local/quality/';
const HIDE = '.sf-cookie-banner,.sf-float-stack{display:none !important}';

const probe = async (browser, width) => {
	const ctx = await browser.newContext({ viewport: { width, height: 900 }, deviceScaleFactor: 1 });
	const p = await ctx.newPage();
	await p.goto(URL, { waitUntil: 'load' });
	await p.addStyleTag({ content: HIDE });
	await p.waitForTimeout(1500);

	const out = await p.evaluate(() => {
		const box = (el) => {
			const r = el.getBoundingClientRect();
			return { w: +r.width.toFixed(1), h: +r.height.toFixed(1), top: +r.top.toFixed(1) };
		};
		const detail = document.querySelector('.sf-certdetail');
		const rows = [...document.querySelectorAll('.sf-certrow')].map((el, i) => {
			const media = el.querySelector('.sf-certrow__media');
			const img = el.querySelector('.sf-certrow__media img');
			const body = el.querySelector('.sf-certrow__body');
			const cs = getComputedStyle(el);
			const mcs = getComputedStyle(media);
			return {
				i,
				name: el.querySelector('.sf-certrow__name')?.textContent.trim(),
				row: box(el),
				media: box(media),
				body: box(body),
				cols: cs.gridTemplateColumns,
				gap: cs.columnGap + ' / ' + cs.rowGap,
				pad: cs.paddingTop + ' ' + cs.paddingBottom,
				placeholder: media?.classList.contains('sf-certrow__media--placeholder') || false,
				img: img ? { ...box(img), natural: img.naturalWidth + 'x' + img.naturalHeight, src: img.getAttribute('src') } : null,
				mediaMinH: mcs.minHeight,
				bodyH: body ? +body.getBoundingClientRect().height.toFixed(1) : 0,
			};
		});
		const sec = detail.closest('section');
		return {
			viewport: { w: innerWidth, h: innerHeight },
			section: box(sec),
			sectionPad: getComputedStyle(sec).paddingTop + ' ' + getComputedStyle(sec).paddingBottom,
			headings: [...sec.querySelectorAll('h2, section > p')].slice(0, 2).map((e) => ({ tag: e.tagName, t: e.textContent.trim().slice(0, 40), h: box(e).h })),
			detail: { ...box(detail), marginTop: getComputedStyle(detail).marginTop },
			rows,
		};
	});
	await ctx.close();
	return { width, ...out };
};

(async () => {
	const browser = await chromium.launch();
	for (const w of [1440, 900, 375]) {
		const r = await probe(browser, w);
		console.log('\n================ viewport ' + w + ' ================');
		console.log('section ' + JSON.stringify(r.section) + '  pad=' + r.sectionPad);
		console.log('head    ' + JSON.stringify(r.headings));
		console.log('detail  ' + JSON.stringify(r.detail));
		r.rows.forEach((x) => {
			console.log(
				'  #' + x.i + ' ' + (x.name || '').padEnd(20) +
				' row=' + JSON.stringify(x.row) +
				' media=' + JSON.stringify(x.media) +
				' body=' + x.bodyH +
				(x.placeholder ? ' [placeholder]' : '') +
				(x.img ? ' img=' + JSON.stringify(x.img) : '')
			);
			console.log('       cols=' + x.cols + '   gap=' + x.gap + '   pad=' + x.pad + '   mediaMinH=' + x.mediaMinH);
		});
		const sum = r.rows.reduce((a, x) => a + x.row.h, 0);
		console.log('  rows sum = ' + sum.toFixed(1) + '   detail h = ' + r.detail.h);
	}
	await browser.close();
})();

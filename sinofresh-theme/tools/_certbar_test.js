/* E2E: homepage third-party testing bar (.sf-certbar).
   Covers: placement (below cards, above button), 5 capsules in order,
   centering, capsule styling, unchanged button, section height budget
   (baseline 783.3px + <=120px), mobile wrap + no overflow. */
const { chromium } = require('playwright-core');

const URL = 'http://sinofresh.local/';
const HIDE = '.sf-cookie-banner,.sf-float-stack{display:none !important}';
const BASE_SECTION_H = 783.3; // measured before the bar was added (1440)
const BUDGET = 120;

let pass = 0, fail = 0;
const check = (id, ok, detail) => {
	if (ok) { pass++; console.log('  PASS  ' + id + '  ' + (detail || '')); }
	else { fail++; console.log('  FAIL  ' + id + '  ' + (detail || '')); }
};

const grab = async (page) => page.evaluate(() => {
	const box = (el) => { const r = el.getBoundingClientRect(); return { w: +r.width.toFixed(1), h: +r.height.toFixed(1), top: +r.top.toFixed(1), bottom: +(r.top + r.height).toFixed(1), left: +r.left.toFixed(1), cx: +(r.left + r.width / 2).toFixed(1) }; };
	const bar = document.querySelector('.sf-certbar');
	const grid = document.querySelector('.sf-certgrid');
	const section = bar.closest('section');
	const logos = bar.querySelector('.sf-certbar__logos');
	const items = [...bar.querySelectorAll('.sf-certbar__item')];
	const cs = (el) => getComputedStyle(el);
	const btn = section.querySelector('.wp-block-button__link');
	return {
		bar: box(bar),
		gridBottom: grid.getBoundingClientRect().bottom,
		sameSection: section === grid.closest('section'),
		label: bar.querySelector('.sf-certbar__label')?.textContent.trim(),
		labelStyle: (() => { const c = cs(bar.querySelector('.sf-certbar__label')); return { size: c.fontSize, weight: c.fontWeight, color: c.color }; })(),
		sub: bar.querySelector('.sf-certbar__sub')?.textContent.trim(),
		subStyle: (() => { const c = cs(bar.querySelector('.sf-certbar__sub')); return { size: c.fontSize, color: c.color, mt: c.marginTop }; })(),
		logos: box(logos),
		logosStyle: (() => { const c = cs(logos); return { justify: c.justifyContent, wrap: c.flexWrap, gap: c.rowGap + '/' + c.columnGap, mt: c.marginTop }; })(),
		items: items.map((el) => ({ t: el.textContent.trim(), ...box(el), style: (() => { const c = cs(el); return { fs: c.fontSize, radius: c.borderRadius, border: c.borderTopWidth + ' ' + c.borderTopColor, bg: c.backgroundColor, color: c.color, pad: c.paddingTop + ' ' + c.paddingRight, white: c.whiteSpace }; })() })),
		aria: bar.getAttribute('aria-label'),
		btn: { label: btn.textContent.trim(), href: btn.getAttribute('href'), ...box(btn) },
		section: box(section),
		contentCx: (() => { const g = grid.getBoundingClientRect(); return +(g.left + g.width / 2).toFixed(1); })(),
		overflowX: document.documentElement.scrollWidth - document.documentElement.clientWidth,
	};
});

(async () => {
	const browser = await chromium.launch();

	// ---------- desktop 1440 ----------
	{
		const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });
		const p = await ctx.newPage();
		await p.goto(URL, { waitUntil: 'load' });
		await p.addStyleTag({ content: HIDE });
		await p.waitForTimeout(1200);
		const r = await grab(p);

		check('D1 bar inside the same section as the card grid', r.sameSection);
		check('D2 bar sits below the cards', r.bar.top >= r.gridBottom, 'bar.top=' + r.bar.top + ' grid.bottom=' + r.gridBottom);
		check('D3 bar sits above the button', r.bar.bottom !== undefined && r.btn.top > r.bar.bottom, 'btn.top=' + r.btn.top);
		check('D4 label text', r.label === 'Third-Party Testing Accepted', r.label);
		check('D5 sub text', r.sub === 'We support testing by major third-party laboratories', r.sub);
		check('D6 aria-label', r.aria === 'Third-party testing partners accepted', r.aria);
		check('D7 five capsules, exact order', r.items.length === 5 && r.items.map((x) => x.t).join('|') === 'SGS|Intertek|Bureau Veritas|Eurofins|TÜV', r.items.map((x) => x.t).join('|'));
		check('D8 one row on desktop (no wrap)', new Set(r.items.map((x) => x.top)).size === 1, 'tops=' + [...new Set(r.items.map((x) => x.top))].join(','));
		check('D9 capsule row centered', Math.abs(r.logos.cx - r.contentCx) <= 8, 'logos.cx=' + r.logos.cx + ' content.cx=' + r.contentCx);
		const s = r.items[0].style;
		check('D10 capsule styling', s.fs === '13px' && s.radius === '999px' && s.border === '1px rgb(220, 226, 223)' && s.bg === 'rgb(255, 255, 255)' && s.color === 'rgb(27, 77, 62)', JSON.stringify(s));
		check('D11 label styling', r.labelStyle.size === '14px' && r.labelStyle.weight === '600' && r.labelStyle.color === 'rgb(27, 77, 62)', JSON.stringify(r.labelStyle));
		check('D12 sub styling', r.subStyle.size === '13px' && r.subStyle.color === 'rgb(107, 107, 107)' && r.subStyle.mt === '4px', JSON.stringify(r.subStyle));
		check('D13 logos flex centered/wrap/gap16/mt16', r.logosStyle.justify === 'center' && r.logosStyle.wrap === 'wrap' && r.logosStyle.gap === '16px/16px' && r.logosStyle.mt === '16px', JSON.stringify(r.logosStyle));
		check('D14 bar margin-top 28px', (await p.$eval('.sf-certbar', (el) => getComputedStyle(el).marginTop)) === '28px');
		check('D15 button unchanged (label + href)', r.btn.label === 'View Full Certifications →' && r.btn.href === '/quality/#certifications', r.btn.label + ' -> ' + r.btn.href);
		const gapBtn = +(r.btn.top - r.bar.bottom).toFixed(1);
		check('D16 gap bar->button still 32px (buttons margin untouched)', Math.abs(gapBtn - 32) <= 1.5, 'gap=' + gapBtn);
		check('D17 section height budget <= baseline+120', r.section.h <= BASE_SECTION_H + BUDGET, 'h=' + r.section.h + ' baseline=' + BASE_SECTION_H + ' delta=' + (r.section.h - BASE_SECTION_H).toFixed(1));
		check('D18 no horizontal overflow at 1440', r.overflowX <= 0, 'overflow=' + r.overflowX);
		await ctx.close();
	}

	// ---------- phone 375 ----------
	{
		const ctx = await browser.newContext({ viewport: { width: 375, height: 812 }, deviceScaleFactor: 1 });
		const p = await ctx.newPage();
		await p.goto(URL, { waitUntil: 'load' });
		await p.addStyleTag({ content: HIDE });
		await p.waitForTimeout(1200);
		const r = await grab(p);

		check('M1 capsules present (5)', r.items.length === 5, r.items.length);
		check('M2 capsules wrap to multiple rows', new Set(r.items.map((x) => x.top)).size >= 2, 'rows=' + new Set(r.items.map((x) => x.top)).size);
		check('M3 mobile item font 12px', r.items.every((x) => x.style.fs === '12px'), r.items[0].style.fs);
		check('M4 mobile logos gap 10px', r.logosStyle.gap === '10px/10px', r.logosStyle.gap);
		check('M5 label stays 14px on mobile', r.labelStyle.size === '14px', r.labelStyle.size);
		check('M6 no horizontal overflow at 375', r.overflowX <= 0, 'overflow=' + r.overflowX);
		check('M7 button still below bar', r.btn.top > r.bar.bottom, 'btn.top=' + r.btn.top);
		await ctx.close();
	}

	console.log('\nRESULT: ' + pass + ' passed, ' + fail + ' failed');
	await browser.close();
	process.exit(fail ? 1 : 0);
})();

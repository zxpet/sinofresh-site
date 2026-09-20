/* Certifications 2-up card grid — layout acceptance.

   Assertions:
     1440  six cards, two per row (three row tops), 588px wide, equal height
           thumbnails still 120x167, card frame present, section <= 950px
     1024  still two per row, no overflow
     375   one per row, frame present, no horizontal overflow
     all   the DOM the lightbox and the modal depend on is untouched

   Run:  NODE_PATH=~/.workbuddy/binaries/node/workspace/node_modules \
         node tools/_cert_2col_test.js
*/
const { chromium } = require('playwright-core');

const URL = 'http://sinofresh.local/quality/';
const HIDE = '.sf-cookie-banner,.sf-float-stack{display:none !important}';

let pass = 0;
let fail = 0;
const ok = (cond, label, extra) => {
	if (cond) {
		pass++;
		console.log('  ok   ' + label + (extra !== undefined ? '  [' + JSON.stringify(extra) + ']' : ''));
	} else {
		fail++;
		console.log('  FAIL ' + label + (extra !== undefined ? '  [' + JSON.stringify(extra) + ']' : ''));
	}
};

const measure = (p) =>
	p.evaluate(() => {
		const detail = document.querySelector('.sf-certdetail');
		const sec = detail.closest('section');
		const dcs = getComputedStyle(detail);
		const rows = [...document.querySelectorAll('.sf-certrow')].map((el) => {
			const r = el.getBoundingClientRect();
			const cs = getComputedStyle(el);
			const img = el.querySelector('.sf-certrow__media img');
			const ir = img ? img.getBoundingClientRect() : null;
			return {
				left: Math.round(r.left),
				top: Math.round(r.top),
				w: Math.round(r.width),
				h: Math.round(r.height),
				radius: cs.borderTopLeftRadius,
				border: cs.borderTopWidth + ' ' + cs.borderTopStyle,
				bg: cs.backgroundColor,
				pad: cs.paddingTop + '/' + cs.paddingRight,
				display: cs.display,
				imgW: ir ? Math.round(ir.width) : null,
				imgH: ir ? Math.round(ir.height) : null,
				placeholder: el.querySelector('.sf-certrow__media--placeholder') !== null,
				hasTrigger: el.querySelector('a[data-cert]') !== null,
				mediaAnchor: null,
			};
		});
		// the lightbox's own hook list, in document order
		const lbItems = [...detail.querySelectorAll('.sf-certrow__media a')].map((a) => a.getAttribute('href'));
		return {
			gridCols: dcs.gridTemplateColumns,
			gridDisplay: dcs.display,
			detailH: Math.round(detail.getBoundingClientRect().height),
			sectionH: Math.round(sec.getBoundingClientRect().height),
			rows,
			lbItems,
			overflow: document.documentElement.scrollWidth - innerWidth,
		};
	});

const run = async (browser, width, height, fn) => {
	const ctx = await browser.newContext({ viewport: { width, height }, deviceScaleFactor: 1 });
	const p = await ctx.newPage();
	const errs = [];
	p.on('pageerror', (e) => errs.push(String(e)));
	await p.goto(URL, { waitUntil: 'load' });
	await p.addStyleTag({ content: HIDE });
	await p.waitForTimeout(1400);
	await fn(p, errs);
	await ctx.close();
};

(async () => {
	const browser = await chromium.launch();

	// ---- 1440 -----------------------------------------------------------
	await run(browser, 1440, 900, async (p, errs) => {
		const m = await measure(p);
		console.log('\n== 1440 ==');
		ok(m.gridDisplay === 'grid', '1. the block is a grid', m.gridDisplay);
		ok(/repeat\(2/.test(m.gridCols.split(' ').length === 2 ? 'repeat(2' : m.gridCols) || m.gridCols.split(' ').length === 2,
			'2. two columns resolve', m.gridCols);
		ok(m.rows.length === 6, '3. six certificates', m.rows.length);

		const tops = [...new Set(m.rows.map((r) => r.top))];
		ok(tops.length === 3, '4. three rows of two', tops);
		ok(m.rows.filter((r) => r.top === tops[0]).length === 2, '5. row one holds two cards',
			m.rows.filter((r) => r.top === tops[0]).map((r) => r.w));

		const w = m.rows[0].w;
		ok(Math.abs(w - 588) <= 2, '6. card width ~588px', w);
		const heights = m.rows.map((r) => r.h);
		ok(new Set(heights).size === 1, '7. cards are equal height', heights);
		ok(m.rows.every((r) => Math.abs(r.w - w) <= 1), '8. all cards the same width',
			m.rows.map((r) => r.w));

		ok(m.rows.every((r) => r.radius === '6px'), '9. 6px radius on every card',
			[...new Set(m.rows.map((r) => r.radius))]);
		ok(m.rows.every((r) => r.border === '1px solid'), '10. 1px hairline frame',
			[...new Set(m.rows.map((r) => r.border))]);
		ok(m.rows.every((r) => r.bg !== 'rgba(0, 0, 0, 0)'), '11. card-white fill present',
			[...new Set(m.rows.map((r) => r.bg))]);
		ok(m.rows[0].pad === '16px/18px', '12. desktop card padding 16px / 18px', m.rows[0].pad);

		const scans = m.rows.filter((r) => !r.placeholder);
		ok(scans.length === 4, '13. four scanned certificates', scans.length);
		ok(scans.every((r) => r.imgW === 120 && r.imgH === 167), '14. thumbnails still 120x167',
			scans.map((r) => r.imgW + 'x' + r.imgH));
		ok(m.rows.filter((r) => r.placeholder).length === 2, '15. HACCP / BRC still placeholders', 2);

		ok(m.sectionH <= 950, '16. section height <= 950px', m.sectionH);
		ok(m.detailH < 700, '17. the row list is under 700px', m.detailH);

		ok(m.lbItems.length === 4, '18. the lightbox still finds four scans', m.lbItems.length);
		ok(m.rows.every((r) => r.hasTrigger), '19. every card keeps its request trigger', 6);
		ok(errs.length === 0, '20. no script errors', errs);

		// the old separator must not draw a line across the grid gutter
		const sep = await p.evaluate(() => {
			const rows = [...document.querySelectorAll('.sf-certrow')];
			const cs = getComputedStyle(rows[1]);
			return cs.borderTopColor + ' vs ' + cs.borderBottomColor;
		});
		ok(sep.split(' vs ')[0] === sep.split(' vs ')[1], '21. separator colour matches the frame', sep);
	});

	// ---- 1024 -----------------------------------------------------------
	await run(browser, 1024, 900, async (p, errs) => {
		const m = await measure(p);
		console.log('\n== 1024 ==');
		const tops = [...new Set(m.rows.map((r) => r.top))];
		ok(tops.length === 3, '22. still three rows of two', tops);
		ok(new Set(m.rows.map((r) => r.h)).size === 1, '23. equal heights at the tablet width',
			m.rows.map((r) => r.h));
		ok(m.overflow <= 0, '24. no horizontal overflow', m.overflow);
		ok(errs.length === 0, '25. no script errors', errs);
	});

	// ---- 375 ------------------------------------------------------------
	await run(browser, 375, 812, async (p, errs) => {
		const m = await measure(p);
		console.log('\n== 375 ==');
		const tops = [...new Set(m.rows.map((r) => r.top))];
		ok(tops.length === 6, '26. six stacked rows', tops.length);
		ok(new Set(m.rows.map((r) => r.left)).size === 1, '27. one column (all lefts equal)',
			[...new Set(m.rows.map((r) => r.left))]);
		ok(m.rows.every((r) => r.radius === '6px' && r.border === '1px solid'), '28. frame kept on a phone',
			m.rows[0].radius + ' ' + m.rows[0].border);
		ok(m.rows[0].pad === '12px/12px', '29. phone padding 12px', m.rows[0].pad);
		ok(m.overflow <= 0, '30. no horizontal overflow', m.overflow);

		const scans = m.rows.filter((r) => !r.placeholder);
		ok(scans.every((r) => r.imgW === 88 && r.imgH === 123), '31. thumbnail still 88x123 on a phone',
			scans.map((r) => r.imgW + 'x' + r.imgH));
		ok(m.rows.every((r) => r.hasTrigger), '32. every phone card keeps its trigger', 6);
		ok(errs.length === 0, '33. no script errors', errs);
	});

	// ---- behaviour: lightbox + modal, at both widths ---------------------
	for (const width of [1440, 375]) {
		await run(browser, width, 900, async (p, errs) => {
			console.log('\n== behaviour ' + width + ' ==');
			await p.evaluate(() => document.querySelector('.sf-certdetail').scrollIntoView({ block: 'start' }));
			await p.waitForTimeout(200);

			// lightbox opens from the first thumbnail
			await p.locator('.sf-certrow__media a').first().click();
			await p.waitForTimeout(600);
			const lbOpen = await p.evaluate(() => {
				const lb = document.querySelector('.sf-lb');
				return lb ? !lb.hidden && getComputedStyle(lb).display !== 'none' : false;
			});
			ok(lbOpen, '34.' + width + ' the lightbox opens from a card thumbnail', lbOpen);

			const next = await p.evaluate(() => {
				const btns = [...document.querySelectorAll('.sf-lb button, .sf-lb__btn')];
				const b = btns.find((x) => /next/i.test(x.getAttribute('aria-label') || x.className || ''));
				return !!b;
			});
			ok(next, '35.' + width + ' the viewer still exposes prev/next', next);

			// step forward once, confirm the counter moved
			const counter = () =>
				p.evaluate(() => {
					const c = document.querySelector('.sf-lb__count, .sf-lb [class*="count"]');
					return c ? c.textContent.trim() : '';
				});
			const before = await counter();
			await p.evaluate(() => {
				const btns = [...document.querySelectorAll('.sf-lb button, .sf-lb__btn')];
				const b = btns.find((x) => /next/i.test(x.getAttribute('aria-label') || x.className || ''));
				if (b) b.click();
			});
			await p.waitForTimeout(450);
			const after = await counter();
			ok(before !== '' && after !== before, '36.' + width + ' next moves to the following scan',
				before + ' -> ' + after);

			await p.keyboard.press('Escape');
			await p.waitForTimeout(400);
			const lbClosed = await p.evaluate(() => {
				const lb = document.querySelector('.sf-lb');
				return lb ? lb.hidden : true;
			});
			ok(lbClosed, '37.' + width + ' Esc closes the viewer', lbClosed);

			// request modal opens from a card link
			await p.locator('.sf-certrow a[data-cert]').first().click();
			await p.waitForTimeout(700);
			const modal = await p.evaluate(() => {
				const m = document.querySelector('.sf-certmodal');
				const hidden = m ? m.hidden : true;
				const field = document.querySelector('#input_5_10');
				return { hidden, value: field ? field.value : null };
			});
			ok(!modal.hidden, '38.' + width + ' Request Certificate opens the dialog', modal.hidden);
			ok(modal.value === 'fda', '39.' + width + ' the hidden field names the certificate', modal.value);

			await p.keyboard.press('Escape');
			await p.waitForTimeout(400);
			ok(errs.length === 0, '40.' + width + ' no script errors', errs);
		});
	}

	await browser.close();
	console.log('\n' + pass + ' passed, ' + fail + ' failed');
	process.exit(fail ? 1 : 0);
})();

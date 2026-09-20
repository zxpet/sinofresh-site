/* Regression guard for the shared backdrop rules.
   Run: NODE_PATH=~/.workbuddy/binaries/node/workspace/node_modules \
       node tools/_cert_basket_regression.js

   B4.1 folded `.sf-certmodal` into the inquiry basket's backdrop rules
   (style.css section 45) and into the reduced-motion block, so the basket has
   to be re-proved on the same page the dialog now lives on: geometry, z-index
   stacking, scroll lock and both close paths. Twelve checks, nothing about
   the certificate dialog itself. */
const { chromium } = require('playwright-core');

const BASE = 'http://sinofresh.local/quality/';
const HIDE_FIXED = '.sf-cookie-banner,.sf-float-stack{display:none !important}';

let pass = 0;
let fail = 0;
const check = (name, ok, detail) => {
	if (ok) { pass++; console.log('PASS ' + name); }
	else { fail++; console.log('FAIL ' + name + ' \u2014 ' + detail); }
};

const state = (p) => p.evaluate(() => {
	const o = document.querySelector('.sf-basket-overlay');
	const d = document.querySelector('.sf-basket-drawer');
	const or = o.getBoundingClientRect();
	const dr = d.getBoundingClientRect();
	return {
		overlayHidden: o.hasAttribute('hidden'),
		overlayOpen: o.classList.contains('is-open'),
		overlayOpacity: getComputedStyle(o).opacity,
		overlayRect: [Math.round(or.x), Math.round(or.y), Math.round(or.width), Math.round(or.height)].join(','),
		drawerHidden: d.hasAttribute('hidden'),
		drawerOpen: d.classList.contains('is-open'),
		drawerRight: Math.round(dr.right),
		drawerWidth: Math.round(dr.width),
		lock: document.body.classList.contains('sf-basket-lock'),
		items: document.querySelectorAll('.sf-basket-drawer__item').length,
		badge: (() => { const b = document.querySelector('.sf-basket-btn__badge'); return b ? (b.hidden ? 'hidden' : b.textContent) : 'none'; })(),
	};
});

(async () => {
	const b = await chromium.launch();

	for (const vp of [{ width: 1440, height: 900, label: 'desktop' }, { width: 375, height: 700, label: 'mobile' }]) {
		const ctx = await b.newContext({ viewport: { width: vp.width, height: vp.height } });
		const p = await ctx.newPage();
		await p.goto(BASE, { waitUntil: 'load' });
		await p.addStyleTag({ content: HIDE_FIXED });
		await p.evaluate(() => {
			sessionStorage.setItem('sinofresh_basket', JSON.stringify([
				{ slug: 'soft-chews', title: 'Soft Chews', summary: 'Joint Support | Chicken', formula: '', addedAt: Date.now() },
			]));
		});
		await p.reload({ waitUntil: 'load' });
		await p.evaluate(() => document.fonts.ready);
		await p.waitForTimeout(400);

		console.log('\n=== basket on ' + vp.label + ' ===');
		let s = await state(p);
		check(vp.label + ' 1. overlay + drawer start hidden', s.overlayHidden === true && s.drawerHidden === true);
		check(vp.label + ' 2. badge reflects the seeded item', s.badge === '1', s.badge);

		await p.click('.sf-basket-btn');
		await p.waitForTimeout(420);
		s = await state(p);
		check(vp.label + ' 3. drawer opens', s.drawerOpen === true && s.drawerHidden === false && s.overlayOpen === true);
		check(vp.label + ' 4. overlay covers the whole viewport', s.overlayRect === '0,0,' + vp.width + ',' + vp.height, s.overlayRect);
		check(vp.label + ' 5. overlay fully opaque', s.overlayOpacity === '1', s.overlayOpacity);
		check(vp.label + ' 6. drawer width ' + (vp.width === 1440 ? '400px' : 'full width'), s.drawerWidth === (vp.width === 1440 ? 400 : 375), s.drawerWidth + 'px');
		check(vp.label + ' 7. drawer flush to the right edge', s.drawerRight === vp.width, s.drawerRight);
		check(vp.label + ' 8. item listed', s.items === 1, String(s.items));
		check(vp.label + ' 9. body scroll locked', s.lock === true);

		// both components on the same page: the dialog must still open on top
		// (the hidden dialog's close button must also be inert — clicked
		// through the DOM because it is not visible to a real pointer)
		const noop = await p.evaluate(() => {
			document.querySelector('.sf-certmodal__close').click();
			const m = document.querySelector('.sf-certmodal');
			return { hidden: m.hasAttribute('hidden'), open: m.classList.contains('is-open') };
		});
		check(vp.label + ' 10. closed dialog ignores its own close button', noop.hidden === true && noop.open === false, JSON.stringify(noop));
		await p.evaluate(() => {
			const btn = document.createElement('button');
			btn.id = 'tmp-cert';
			btn.setAttribute('data-cert', 'fda');
			btn.style.cssText = 'position:fixed;top:200px;left:24px;z-index:20001';
			btn.textContent = 'x';
			document.body.appendChild(btn);
		});
		await p.click('#tmp-cert');
		await p.waitForTimeout(400);
		const both = await p.evaluate(() => {
			const m = document.querySelector('.sf-certmodal');
			const panel = m.querySelector('.sf-certmodal__panel');
			const d = document.querySelector('.sf-basket-drawer');
			const pr = panel.getBoundingClientRect();
			const dr = d.getBoundingClientRect();
			// a point on the backdrop, never inside the panel, taken from the
			// panel's own box so it holds on both viewports
			const px = pr.left > 20 ? pr.left - 10 : Math.round(window.innerWidth / 2);
			const py = pr.top > 20 ? pr.top - 10 : Math.round(window.innerHeight / 2);
			const overDrawer = document.elementFromPoint(dr.left + dr.width / 2, dr.top + dr.height / 2);
			return {
				certOpen: m.classList.contains('is-open'),
				basketStillOpen: d.classList.contains('is-open'),
				backdropHit: document.elementFromPoint(px, py) === m,
				drawerCovered: !d.contains(overDrawer),
				probe: px + ',' + py,
			};
		});
		check(vp.label + ' 11. dialog opens while the basket holds its state', both.certOpen === true && both.basketStillOpen === true, JSON.stringify(both));
		check(vp.label + ' 12. dialog paints above the drawer', both.backdropHit === true && both.drawerCovered === true,
			'backdrop@' + both.probe + '=' + both.backdropHit + ' drawerCovered=' + both.drawerCovered);
		await p.evaluate(() => { document.querySelector('.sf-certmodal__close').click(); });

		await p.keyboard.press('Escape');
		await p.waitForTimeout(420);
		s = await state(p);
		check(vp.label + ' 13. Esc closes the drawer and clears the lock', s.drawerHidden === true && s.overlayHidden === true && s.lock === false,
			'drawer=' + s.drawerHidden + ' overlay=' + s.overlayHidden + ' lock=' + s.lock);
		await ctx.close();
	}

	await b.close();
	console.log('\n' + (fail === 0 ? 'ALL PASS' : 'FAILURES') + ' \u2014 ' + pass + '/' + (pass + fail));
	process.exit(fail === 0 ? 0 : 1);
})();

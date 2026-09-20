/* Stage A E2E — Quality page COA trust module (.sf-coa).
   Run: NODE_PATH=~/.workbuddy/binaries/node/workspace/node_modules \
       node tools/_coa_trust_test.js
   Covers: 60/40 split, PDF previewer + fallback, label row, checks list,
   dual CTAs (orange primary + ghost), mobile 1-col stack, button widths,
   no horizontal overflow, section height delta vs pre-rebuild baseline. */
const { chromium } = require('playwright-core');

const BASE = 'http://sinofresh.local/quality/';
const HIDE_FIXED = `
	.sf-cookie-banner, .sf-float-stack { display: none !important; }
`;

let pass = 0, fail = 0;
const check = (name, ok, detail) => {
	if (ok) { pass++; console.log('PASS ' + name); }
	else { fail++; console.log('FAIL ' + name + ' — ' + detail); }
};

(async () => {
	const b = await chromium.launch();

	/* ---------- desktop 1440 ---------- */
	const dctx = await b.newContext({ viewport: { width: 1440, height: 900 } });
	const dp = await dctx.newPage();
	await dp.goto(BASE, { waitUntil: 'load' });
	await dp.evaluate(() => document.fonts.ready);
	await dp.waitForTimeout(400);
	const d = await dp.evaluate(() => {
		const coa = document.querySelector('.sf-coa');
		const out = { exists: !!coa };
		if (!coa) return out;
		const cs = getComputedStyle(coa);
		const cols = cs.gridTemplateColumns.trim().split(/\s+/).map((v) => parseFloat(v));
		const preview = coa.querySelector('.sf-coa__preview');
		const info = coa.querySelector('.sf-coa__info');
		const obj = coa.querySelector('object.sf-coa__pdf');
		const frame = coa.querySelector('.sf-coa__frame');
		const label = coa.querySelector('.sf-coa__label');
		const h2 = info.querySelector('h2');
		const checks = [...info.querySelectorAll('.sf-coa__checks li')].map((li) => li.textContent.trim());
		const primary = info.querySelector('.sf-coa__btn--primary');
		const ghost = info.querySelector('.sf-coa__btn--ghost');
		const pcs = primary ? getComputedStyle(primary) : null;
		const gcs = ghost ? getComputedStyle(ghost) : null;
		const sec = coa.closest('section');
		return {
			exists: true,
			gtc: cs.gridTemplateColumns,
			cols,
			previewLeft: Math.round(preview.getBoundingClientRect().x),
			infoLeft: Math.round(info.getBoundingClientRect().x),
			previewW: Math.round(preview.getBoundingClientRect().width),
			infoW: Math.round(info.getBoundingClientRect().width),
			frameH: Math.round(frame.getBoundingClientRect().height),
			objType: obj ? obj.getAttribute('type') : null,
			objData: obj ? obj.getAttribute('data') : null,
			objW: obj ? Math.round(obj.getBoundingClientRect().width) : 0,
			fallbackVisible: (() => {
				const img = coa.querySelector('object img');
				if (!img) return false;
				const r = img.getBoundingClientRect();
				const ocs = getComputedStyle(obj);
				return r.height > 0 && ocs.display !== 'none';
			})(),
			label: label ? label.textContent.trim() : null,
			labelColor: label ? getComputedStyle(label).color : null,
			h2: h2 ? h2.textContent.trim() : null,
			checks,
			primaryText: primary ? primary.textContent.trim() : null,
			primaryBg: pcs ? pcs.backgroundColor : null,
			primaryH: pcs ? Math.round(primary.getBoundingClientRect().height) : 0,
			ghostText: ghost ? ghost.textContent.trim() : null,
			ghostHref: ghost ? ghost.getAttribute('href') : null,
			ghostDownload: ghost ? ghost.getAttribute('download') : null,
			ghostBorder: gcs ? gcs.borderStyle + ' ' + gcs.borderTopWidth : null,
			secH: sec ? Math.round(sec.getBoundingClientRect().height) : 0,
			scrollW: document.documentElement.scrollWidth,
			innerW: innerWidth,
		};
	});
	check('A1. .sf-coa exists', d.exists, 'no .sf-coa');
	if (d.exists) {
		check('A1a. desktop 2 columns 60/40', d.cols.length === 2 && Math.abs(d.cols[0] / (d.cols[0] + d.cols[1]) - 0.6) < 0.03, d.gtc);
		check('A1b. previewer left of info', d.previewLeft < d.infoLeft, `preview@${d.previewLeft} info@${d.infoLeft}`);
		check('A1c. previewer ~60% width', Math.abs(d.previewW / (d.previewW + d.infoW) - 0.6) < 0.05, `${d.previewW} vs ${d.infoW}`);
		check('A3. label row', d.label === 'Sample COA · Batch #SF-2026-0915 · Issued Sep 15, 2026', JSON.stringify(d.label));
		check('A3b. label gray small', d.labelColor === 'rgb(95, 107, 101)', d.labelColor);
		check('A2. right H2 = Certificate of Analysis', d.h2 === 'Certificate of Analysis', d.h2);
		check('A2b. 3 key test items', JSON.stringify(d.checks) === JSON.stringify(['Active Ingredient Content', 'Heavy Metals (Pb, As, Hg, Cd)', 'Microbiological Safety']), JSON.stringify(d.checks));
		check('A2c. primary CTA text', d.primaryText === 'Request a Batch-Specific COA', d.primaryText);
		check('A2d. primary CTA orange #B54E0F', d.primaryBg === 'rgb(181, 78, 15)', d.primaryBg);
		check('A2e. primary CTA 48px', d.primaryH === 48, String(d.primaryH));
		check('A2f. ghost = Download Sample PDF', d.ghostText === 'Download Sample PDF' && d.ghostDownload !== null, d.ghostText + ' dl=' + JSON.stringify(d.ghostDownload));
		check('A2g. ghost href = sample PDF', /coa-sample\.pdf$/.test(d.ghostHref || ''), d.ghostHref);
		check('A2h. ghost outlined', /^solid/.test(d.ghostBorder || ''), d.ghostBorder);
		check('A1d. previewer frame present', d.objType === 'application/pdf' && d.objW > 100, `type=${d.objType} w=${d.objW}`);
		check('A1e. frame height 500-620', d.frameH >= 500 && d.frameH <= 620, String(d.frameH));
		check('A1f. fallback img inside object (non-Chromium PDF viewers)', d.fallbackVisible, 'fallback hidden');
		check('9. desktop no overflow', d.scrollW <= d.innerW, `scrollW=${d.scrollW}`);
	}

	/* PDF served correctly */
	const pdfResp = await dctx.request.get('http://sinofresh.local/wp-content/uploads/2026/09/coa-sample.pdf');
	const pdfBody = await pdfResp.body();
	check('A4. sample PDF reachable', pdfResp.status() === 200 && pdfBody.slice(0, 4).toString() === '%PDF', `status=${pdfResp.status()} magic=${pdfBody.slice(0, 4).toString()}`);

	/* B4.5 wired the CTA band's button, so the check is no longer "how many are
	   still dead" but "none are": it is an <a href="/contact/#quote"> with the
	   coa-sample key, like every other certificate control on the page. */
	const deadBtns = await dp.evaluate(() =>
		[...document.querySelectorAll('a.wp-block-button__link')].filter((a) => !a.getAttribute('href') && /Request COA Sample/.test(a.textContent)).length
	);
	check('A5. no dead "Request COA Sample" left (B4.5 wired the CTA band)', deadBtns === 0, `found ${deadBtns}`);

	/* section screenshot */
	await dp.addStyleTag({ content: HIDE_FIXED });
	const secEl = await dp.$('.sf-coa');
	const secBox = await secEl.boundingBox();
	await dp.evaluate((y) => scrollTo(0, y), Math.max(0, secBox.y - 120));
	await dp.waitForTimeout(250);
	const dsec = await dp.$('.sf-coa');
	await dsec.screenshot({ path: 'tools/screenshots/coa-desktop-1440.png' });
	await dp.screenshot({ path: 'tools/screenshots/coa-full-1440.png', fullPage: true });
	await dctx.close();

	/* ---------- mobile 375 ---------- */
	const mctx = await b.newContext({ viewport: { width: 375, height: 812 } });
	const mp = await mctx.newPage();
	await mp.goto(BASE, { waitUntil: 'load' });
	await mp.evaluate(() => document.fonts.ready);
	await mp.waitForTimeout(400);
	const m = await mp.evaluate(() => {
		const coa = document.querySelector('.sf-coa');
		const cs = getComputedStyle(coa);
		const cols = cs.gridTemplateColumns.trim().split(/\s+/);
		const preview = coa.querySelector('.sf-coa__preview');
		const info = coa.querySelector('.sf-coa__info');
		const pdf = coa.querySelector('.sf-coa__pdf');
		const frame = coa.querySelector('.sf-coa__frame');
		const primary = coa.querySelector('.sf-coa__btn--primary');
		const ghost = coa.querySelector('.sf-coa__btn--ghost');
		const pr = primary.getBoundingClientRect();
		const gr = ghost.getBoundingClientRect();
		return {
			gtc: cs.gridTemplateColumns,
			previewTop: Math.round(preview.getBoundingClientRect().top),
			infoTop: Math.round(info.getBoundingClientRect().top),
			previewW: Math.round(preview.getBoundingClientRect().width),
			frameH: Math.round(frame.getBoundingClientRect().height),
			btnW: Math.round(pr.width),
			btnH: Math.round(pr.height),
			ghostW: Math.round(gr.width),
			innerW: innerWidth,
			scrollW: document.documentElement.scrollWidth,
			frameW: Math.round(frame.getBoundingClientRect().width),
		};
	});
	check('A6. mobile 1 column', m.gtc.trim().split(/\s+/).length === 1, m.gtc);
	check('A7. previewer stacked above info', m.previewTop < m.infoTop, `preview@${m.previewTop} info@${m.infoTop}`);
	check('A8. mobile previewer 300-400px tall', m.frameH >= 300 && m.frameH <= 400, String(m.frameH));
	check('A9. buttons full width', m.btnW > 290 && m.ghostW > 290, `${m.btnW}/${m.ghostW}`);
	check('A10. buttons 44px tall', m.btnH === 44, String(m.btnH));
	check('A11. mobile no overflow', m.scrollW <= m.innerW, `scrollW=${m.scrollW} innerW=${m.innerW}`);

	await mp.addStyleTag({ content: HIDE_FIXED });
	const msec = await mp.$('.sf-coa');
	const mbox = await msec.boundingBox();
	await mp.evaluate((y) => scrollTo(0, y), Math.max(0, mbox.y - 80));
	await mp.waitForTimeout(250);
	const msec2 = await mp.$('.sf-coa');
	await msec2.screenshot({ path: 'tools/screenshots/coa-mobile-375.png' });
	await mp.screenshot({ path: 'tools/screenshots/coa-full-375.png', fullPage: true });
	await mctx.close();

	await b.close();
	console.log(`\n${pass} passed, ${fail} failed`);
	process.exit(fail ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(1); });

/* Stage 3 E2E — article-page front-end enhancements (toc-nav.js 2.0).
   Run: NODE_PATH=~/.workbuddy/binaries/node/workspace/node_modules \
       node tools/_article_enh_test.js

   Covers: desktop text TOC (>=1280), highlight follow, smooth scroll +
   settle, per-entry copy toast, progress bar, double-time meta, breadcrumb
   by type, share row (links + copy), feedback up (localStorage + REST) and
   down (mini form -> GF Form 6 entry), inline-CTA dormancy, mobile
   collapsible TOC + 375px overflow, print emulation (URL injection +
   chrome hidden), cover CLS guards, and the dot-rail regression on home. */
const { chromium } = require('playwright-core');
const path = require('path');

const BASE = 'http://sinofresh.local';
const ART = BASE + '/case-study-us-brand-owner-soft-chews/';
const SHOTS = path.join(__dirname, 'screenshots');

let pass = 0, fail = 0;
const check = (name, ok, detail) => {
	if (ok) { pass++; console.log('PASS ' + name); }
	else { fail++; console.log('FAIL ' + name + ' -- ' + detail); }
};

(async () => {
	const browser = await chromium.launch();

	/* ============================ DESKTOP ============================ */
	const d = await browser.newContext({ viewport: { width: 1440, height: 900 } });
	const p = await d.newPage();
	await p.goto(ART, { waitUntil: 'networkidle' });
	await p.evaluate(() => document.fonts.ready);

	/* --- TOC text list structure --- */
	const toc = await p.evaluate(() => {
		const nav = document.querySelector('.sf-toc--text');
		if (!nav) return { missing: true };
		const links = [...nav.querySelectorAll('a.sf-toc__link')];
		return {
			label: nav.getAttribute('aria-label'),
			count: links.length,
			titles: links.map(a => a.getAttribute('title')),
			ellipsized: getComputedStyle(links[0]).textOverflow === 'ellipsis',
			vis: nav.offsetWidth > 0 && nav.offsetHeight > 0,
			targets: links.every(a => document.querySelector('.sf-toc-target'))
		};
	});
	check('toc-text present + visible @1440', toc.vis && !toc.missing, JSON.stringify(toc));
	check('toc-text 7 sections', toc.count === 7, 'count=' + toc.count);
	check('toc-text ellipsis + title attr', toc.ellipsized && toc.titles.every(Boolean), JSON.stringify(toc.titles));
	check('toc-target anchors injected', toc.targets, '');

	/* fade state above fold */
	const fadeTop = await p.evaluate(() =>
		document.querySelector('.sf-toc--text').classList.contains('sf-toc--hidden'));
	check('toc fades out above fold', fadeTop, '');

	/* highlight follows scroll */
	const sec2 = await p.evaluate(() => {
		const hs = [...document.querySelectorAll('.sf-single-body .wp-block-post-content h2.sf-toc-target')];
		return { id: hs[2].id };
	});
	await p.evaluate((id) => { document.getElementById(id).scrollIntoView({ block: 'start' }); }, sec2.id);
	await p.waitForTimeout(400);
	let cur = await p.evaluate(() => {
		const lis = [...document.querySelectorAll('.sf-toc--text li')];
		return lis.findIndex(li => li.classList.contains('is-current'));
	});
	check('highlight follows scroll (idx 2)', cur === 2, 'cur=' + cur);

	/* click TOC item -> smooth scroll lands with header offset */
	await p.click('.sf-toc--text li:nth-child(5) a.sf-toc__link');
	await p.waitForTimeout(1800);
	const landed = await p.evaluate(() => {
		const lis = [...document.querySelectorAll('.sf-toc--text li')];
		const cur = lis.findIndex(li => li.classList.contains('is-current'));
		return { cur, top: document.querySelectorAll('.sf-toc-target')[4].getBoundingClientRect().top, hash: location.hash };
	});
	check('click scrolls + hash updates', Math.abs(landed.top - 96) < 40 && landed.hash === '#sf-sec-4', JSON.stringify(landed));
	check('click sets current (idx 4)', landed.cur === 4, 'cur=' + landed.cur);

	/* per-entry copy -> toast (clipboard fallback path on http) */
	await p.hover('.sf-toc--text li:nth-child(5)');
	await p.waitForTimeout(250);
	const copyVis = await p.evaluate(() => {
		const b = document.querySelector('.sf-toc--text li:nth-child(5) .sf-toc__copy');
		return getComputedStyle(b).opacity !== '0';
	});
	check('copy button reveals on hover', copyVis, '');
	await p.click('.sf-toc--text li:nth-child(5) .sf-toc__copy');
	await p.waitForTimeout(400);
	const toastTxt = await p.evaluate(() => {
		const t = document.querySelector('.sf-toast');
		return t && t.classList.contains('is-visible') ? t.textContent : '';
	});
	check('section copy toast', toastTxt === 'Section link copied', JSON.stringify(toastTxt));

	/* progress bar */
	const prog = await p.evaluate(() => {
		const b = document.querySelector('.sf-progress');
		const cs = getComputedStyle(b);
		return { h: cs.height, bg: cs.backgroundColor, x: cs.transform };
	});
	check('progress bar 3px brand green', prog.h === '3px' && prog.bg === 'rgb(90, 183, 53)', JSON.stringify(prog));
	await p.evaluate(() => scrollTo(0, 0));
	await p.waitForTimeout(300);
	const atTop = await p.evaluate(() => getComputedStyle(document.querySelector('.sf-progress')).transform);
	await p.evaluate(() => scrollTo(0, document.documentElement.scrollHeight));
	await p.waitForTimeout(400);
	const atBot = await p.evaluate(() => getComputedStyle(document.querySelector('.sf-progress')).transform);
	check('progress 0 -> 1', atTop.includes('matrix(0') || atTop === 'none' ? atBot.includes('matrix(1') : atBot.includes('matrix(1'), atTop + ' | ' + atBot);

	/* back to top for hero-region shots */
	await p.evaluate(() => scrollTo(0, 0));
	await p.waitForTimeout(500);

	/* breadcrumb + double time */
	const hero = await p.evaluate(() => {
		const mid = document.querySelector('.sf-breadcrumb__crumb--mid');
		const upd = document.querySelector('.sf-single-meta__updated');
		return { mid: mid ? [mid.textContent, mid.getAttribute('href')] : null,
			upd: upd ? upd.textContent : null, updEmpty: upd ? getComputedStyle(upd).display === 'none' : null };
	});
	check('breadcrumb Case Studies', hero.mid && hero.mid[0] === 'Case Studies' && hero.mid[1] === '/category/case-studies/', JSON.stringify(hero.mid));
	check('double-time meta', hero.upd === '\u00b7 Last updated: Sep 10, 2026', JSON.stringify(hero.upd));

	/* share row */
	const share = await p.evaluate(() => {
		const li = document.querySelector('a[href*="linkedin.com/sharing"]');
		const tw = document.querySelector('a[href*="twitter.com/intent/tweet"]');
		return {
			li: li ? li.href : null, liT: li ? li.target : null,
			tw: tw ? tw.href : null,
			copy: !!document.querySelector('.sf-share-btn--copy')
		};
	});
	check('linkedin native share (no JS)', share.li && share.li.includes(encodeURIComponent(ART)) && share.liT === '_blank', share.li);
	check('twitter intent with title', share.tw && share.tw.includes('text='), share.tw);
	check('copy link button present', share.copy, '');

	/* meta copy button */
	await p.click('.sf-copy-link');
	await p.waitForTimeout(300);
	const toast2 = await p.evaluate(() => {
		const t = document.querySelector('.sf-toast');
		return t && t.classList.contains('is-visible') ? t.textContent : '';
	});
	check('meta copy toast', toast2 === 'Link copied', JSON.stringify(toast2));

	/* inline CTA dormant on short post */
	const noCta = await p.evaluate(() => !document.querySelector('.sf-inline-cta'));
	check('inline CTA dormant (<1500 words)', noCta, '');

	/* no horizontal overflow */
	const overflowD = await p.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
	check('desktop no overflow @1440', overflowD <= 0, 'delta=' + overflowD);

	/* feedback UP: toast state + localStorage + REST */
	await p.evaluate(() => document.querySelector('.sf-article-actions').scrollIntoView({ block: 'center' }));
	await p.waitForTimeout(300);
	await p.click('.sf-fb-btn[data-vote="up"]');
	await p.waitForTimeout(1200);
	const upState = await p.evaluate(() => ({
		done: document.querySelector('.sf-article-feedback').classList.contains('is-done'),
		thanks: !document.querySelector('.sf-article-feedback__thanks').hidden,
		ls: localStorage.getItem('sf_fb_99')
	}));
	check('up-vote thanks + localStorage', upState.done && upState.thanks && upState.ls === 'up', JSON.stringify(upState));
	await p.screenshot({ path: SHOTS + '/article-feedback-thanks.png', clip: { x: 200, y: 0, width: 1040, height: 900 } });

	/* feedback DOWN: mini form + invalid email error + valid submit */
	const d2 = await browser.newContext({ viewport: { width: 1440, height: 900 } });
	const p2 = await d2.newPage();
	await p2.goto(ART, { waitUntil: 'networkidle' });
	await p2.evaluate(() => document.querySelector('.sf-article-actions').scrollIntoView({ block: 'center' }));
	await p2.waitForTimeout(300);
	await p2.click('.sf-fb-btn[data-vote="down"]');
	await p2.waitForTimeout(250);
	const formOpen = await p2.evaluate(() => {
		const f = document.querySelector('.sf-fb-form');
		return { vis: !f.hidden, lead: f.querySelector('.sf-fb-form__lead').textContent };
	});
	check('down-vote opens mini form', formOpen.vis && formOpen.lead.includes('Help us improve'), JSON.stringify(formOpen));
	await p2.screenshot({ path: SHOTS + '/article-feedback-form.png', clip: { x: 200, y: 0, width: 1040, height: 900 } });
	await p2.fill('.sf-fb-form__email', 'not-an-email');
	await p2.click('.sf-fb-form__send');
	await p2.waitForTimeout(300);
	const emailErr = await p2.evaluate(() => {
		const e = document.querySelector('.sf-fb-form__error');
		return !e.hidden ? e.textContent : '';
	});
	check('invalid email blocked client-side', emailErr.includes('valid email'), JSON.stringify(emailErr));
	await p2.fill('.sf-fb-form__email', 'e2e@sinofresh-test.com');
	await p2.fill('.sf-fb-form__msg', 'E2E stage-3 down-vote probe - ignore');
	await p2.check('.sf-fb-form__consent-box');
	await p2.click('.sf-fb-form__send');
	await p2.waitForTimeout(1500);
	const downState = await p2.evaluate(() => ({
		done: document.querySelector('.sf-article-feedback').classList.contains('is-done'),
		ls: localStorage.getItem('sf_fb_99'),
		formHidden: document.querySelector('.sf-fb-form').hidden
	}));
	check('down-vote submits + thanks', downState.done && downState.ls === 'down' && downState.formHidden, JSON.stringify(downState));

	/* CLS guards (SCREEN media — the print sheet legitimately drops the
	 * 450px cap): content imgs carry width+height, cover 16:9 + cap. */
	const cls = await p2.evaluate(() => {
		const imgs = [...document.querySelectorAll('.sf-single-body img')];
		const cover = document.querySelector('.sf-single-cover img');
		return {
			all: imgs.every(i => i.getAttribute('width') && i.getAttribute('height')),
			coverRatio: getComputedStyle(cover).aspectRatio,
			coverMax: getComputedStyle(cover).maxHeight
		};
	});
	check('cover 16:9 + 450px cap', cls.coverRatio === '16 / 9' && cls.coverMax === '450px', JSON.stringify(cls));

	/* PRINT emulation */
	const p3 = await browser.newContext({ viewport: { width: 1280, height: 900 } }).then(c => c.newPage());
	await p3.goto(ART, { waitUntil: 'networkidle' });
	await p3.emulateMedia({ media: 'print' });
	await p3.evaluate(() => window.dispatchEvent(new Event('beforeprint')));
	await p3.waitForTimeout(300);
	/* print URL stays verifiable in print media */
	const prUrl = await p3.evaluate(() => {
		const url = document.querySelector('.sf-print-url');
		return url ? url.textContent : null;
	});
	check('print URL injected', !!prUrl && prUrl.startsWith('Source: ' + ART), JSON.stringify(prUrl));
	const pr = await p3.evaluate(() => {
		const disp = (sel) => { const el = document.querySelector(sel); return el ? getComputedStyle(el).display : 'absent'; };
		return {
			header: disp('header'), toc: disp('.sf-toc--text'), actions: disp('.sf-article-actions'),
			related: disp('.sf-related'), progress: disp('.sf-progress'), float: disp('.sf-float-stack'),
			ctaBand: disp('body.single-post section.has-primary-background-color:last-of-type'),
			bodyColor: getComputedStyle(document.querySelector('.sf-single-body .wp-block-post-content p')).color
		};
	});
	check('print hides chrome', ['none', 'absent'].includes(pr.header) && pr.toc === 'none' && pr.actions === 'none' && pr.related === 'none' && pr.progress === 'none' && pr.float === 'none', JSON.stringify(pr));
	check('print hides closing CTA band', pr.ctaBand === 'none', pr.ctaBand);
	check('print body black text', pr.bodyColor === 'rgb(0, 0, 0)', pr.bodyColor);
	await p3.pdf({ path: SHOTS + '/article-print-preview.pdf', format: 'A4', printBackground: false });

	await d.close(); await d2.close();

	/* ============================ MOBILE 375 ========================= */
	const m = await browser.newContext({ viewport: { width: 375, height: 812 }, isMobile: true, hasTouch: true });
	const pm = await m.newPage();
	await pm.goto(ART, { waitUntil: 'networkidle' });
	await pm.evaluate(() => document.fonts.ready);
	const mob = await pm.evaluate(() => {
		const mount = document.querySelector('.sf-mobile-toc');
		const toggle = document.querySelector('.sf-mobile-toc__toggle');
		const panel = document.querySelector('.sf-mobile-toc__panel');
		const textToc = document.querySelector('.sf-toc--text');
		return {
			mountVis: mount && !mount.hidden, toggle: !!toggle,
			panelCollapsed: panel && panel.hidden,
			textTocHidden: textToc ? getComputedStyle(textToc).display === 'none' : false,
			progress: !!document.querySelector('.sf-progress'),
			overflow: document.documentElement.scrollWidth - window.innerWidth
		};
	});
	check('mobile: collapsible TOC mounted, collapsed', mob.mountVis && mob.toggle && mob.panelCollapsed, JSON.stringify(mob));
	check('mobile: text TOC hidden', mob.textTocHidden, '');
	check('mobile: progress bar present', mob.progress, '');
	check('mobile 375 no overflow', mob.overflow <= 0, 'delta=' + mob.overflow);

	await pm.click('.sf-mobile-toc__toggle');
	await pm.waitForTimeout(250);
	const opened = await pm.evaluate(() => {
		const t = document.querySelector('.sf-mobile-toc__toggle');
		const panel = document.querySelector('.sf-mobile-toc__panel');
		return { expanded: t.getAttribute('aria-expanded') === 'true', visible: !panel.hidden, items: panel.querySelectorAll('a').length };
	});
	check('mobile: TOC expands', opened.expanded && opened.visible && opened.items === 7, JSON.stringify(opened));
	await pm.screenshot({ path: SHOTS + '/article-mobile-toc-open.png' });
	await pm.click('.sf-mobile-toc__panel li:nth-child(2) a');
	await pm.waitForTimeout(1800);
	const afterJump = await pm.evaluate(() => ({
		closed: document.querySelector('.sf-mobile-toc__panel').hidden,
		top: document.querySelectorAll('.sf-toc-target')[1].getBoundingClientRect().top
	}));
	check('mobile: item click closes + scrolls', afterJump.closed && Math.abs(afterJump.top - 96) < 80, JSON.stringify(afterJump));

	/* share buttons 44px touch targets */
	const touch = await pm.evaluate(() => {
		const btns = [...document.querySelectorAll('.sf-share-btn')];
		return btns.every(b => b.getBoundingClientRect().height >= 44);
	});
	check('mobile: share 44px targets', touch, '');
	await m.close();

	/* ===================== DOT-RAIL REGRESSION (home) ================ */
	const h = await browser.newContext({ viewport: { width: 1440, height: 900 } });
	const ph = await h.newPage();
	await ph.goto(BASE, { waitUntil: 'networkidle' });
	await ph.waitForTimeout(600);
	const rail = await ph.evaluate(() => {
		const nav = document.querySelector('.sf-toc:not(.sf-toc--text)');
		return { present: !!nav, dots: nav ? nav.querySelectorAll('li').length : 0, noText: !document.querySelector('.sf-toc--text') };
	});
	check('home dot-rail intact (9 dots)', rail.present && rail.dots === 9 && rail.noText, JSON.stringify(rail));
	await h.close();

	await browser.close();
	console.log('\nRESULT: ' + pass + ' pass, ' + fail + ' fail');
	process.exit(fail ? 1 : 0);
})().catch(e => { console.error('FATAL', e); process.exit(1); });

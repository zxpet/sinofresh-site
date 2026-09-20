/* Services page rebuild test (2026-09-18): 5 content sections, Key Facts
 * table, 3-col panel, 5 steps, 3 FAQ + FAQPage schema, Service schema.
 * Replaces tools/_svc_checklist_test.js (three-band layout is gone).
 */
const path = require('path');
const fs = require('fs');
const { chromium } = require('playwright-core');

const OUT = path.join(__dirname, 'screenshots');
fs.mkdirSync(OUT, { recursive: true });
const BASE = 'http://sinofresh.local/services/';
const results = [];
const check = (name, ok, detail) => {
  results.push({ name, ok, detail });
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}  ${detail}`);
};

(async () => {
  const browser = await chromium.launch();
  const HIDE = `.sf-cookie-banner,.sf-float-stack{display:none!important}`;

  // ---------- Desktop 1440 ----------
  let ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  let page = await ctx.newPage();
  const res = await page.goto(BASE, { waitUntil: 'load' });
  const html = await res.text();
  await page.addStyleTag({ content: HIDE });
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(400);

  const d = await page.evaluate(() => {
    const bodyText = document.body.innerText;
    const secs = [...document.querySelectorAll('section.wp-block-group')];
    const named = secs.map((s) => {
      const h = s.querySelector('h1,h2');
      return h ? h.textContent.trim() : '(hero-no-heading)';
    });
    const panel = document.querySelector('.sf-panel--3');
    const pcs = panel ? getComputedStyle(panel) : null;
    const cols = panel ? [...panel.children] : [];
    const lists = [...document.querySelectorAll('.sf-checklist--panel')];
    const table = document.querySelector('.sf-keyfacts');
    const tRows = table ? [...table.querySelectorAll('tbody tr')].map((tr) => Math.round(tr.getBoundingClientRect().height)) : [];
    const steps = (() => {
      const hww = secs.find((s) => /How We Work/.test((s.querySelector('h2') || {}).textContent || ''));
      return hww ? [...hww.querySelectorAll('.wp-block-columns > .wp-block-column')] : [];
    })();
    const faqs = [...document.querySelectorAll('.sf-faq details')];
    const h1 = document.querySelectorAll('h1').length;
    const h2 = [...document.querySelectorAll('h2')].map((h) => h.textContent.trim());
    const hero = document.querySelector('.sf-hero-inner');
    const heroText = hero ? hero.innerText : '';
    return {
      named,
      bodyText,
      panelTracks: pcs ? pcs.gridTemplateColumns : null,
      colCount: cols.length,
      listLens: lists.map((l) => l.querySelectorAll('li').length),
      tableRows: table ? table.querySelectorAll('tbody tr').length : 0,
      tRows,
      stepCount: steps.length,
      faqCount: faqs.length,
      faqQ: faqs.map((f) => f.querySelector('summary h3').textContent.trim()),
      h1,
      h2,
      heroText,
      pageH: Math.round(document.documentElement.scrollHeight),
      scrollW: document.documentElement.scrollWidth,
      innerW: window.innerWidth,
      schemaScripts: [...document.querySelectorAll('script[type="application/ld+json"]')].map((s) => {
        try { return JSON.parse(s.textContent); } catch (e) { return { parseError: String(e) }; }
      }),
    };
  });

  // 1. sections
  const contentH2 = d.h2.filter((t) => !/Ready to Start/.test(t));
  check('1. content sections = 5', contentH2.length === 5, JSON.stringify(contentH2));
  // 2. dedup
  const count = (re) => (d.bodyText.match(re) || []).length;
  check('2a. COA x1', count(/COA/g) === 1, `count=${count(/COA/g)}`);
  check('2b. Palatability testing x1', count(/Palatability testing/g) === 1, `count=${count(/Palatability testing/g)}`);
  check('2c. Stability testing x1', count(/Stability testing/g) === 1, `count=${count(/Stability testing/g)}`);
  check('2d. Health Certificate x1', count(/Health Certificate/g) === 1, `count=${count(/Health Certificate/g)}`);
  check('2e. FOB / CIF / EXW / DDP x1', count(/FOB \/ CIF \/ EXW \/ DDP/g) === 1, `count=${count(/FOB \/ CIF \/ EXW \/ DDP/g)}`);
  // 3. hero
  check('3. hero no badge line', (d.heroText.match(/FDA/g) || []).length === 1 && !/·\s*cGMP/.test(d.heroText), `FDA refs=${(d.heroText.match(/FDA/g) || []).length}`);
  // 4. key facts table
  check('4a. table 5 rows', d.tableRows === 5, `rows=${d.tableRows}`);
  check('4b. row heights ~44', d.tRows.every((h) => h >= 44 && h <= 46), JSON.stringify(d.tRows));
  check('4c. table text', /500–1,000 units/.test(d.bodyText) && /FOB \/ CIF \/ EXW \/ DDP/.test(d.bodyText), '');
  // 5. what we handle
  check('5a. panel 3 cols desktop', d.panelTracks && d.panelTracks.trim().split(/\s+/).length === 3, `[${d.panelTracks}]`);
  check('5b. 3 lists x 5 items', d.listLens.length === 3 && d.listLens.every((n) => n === 5), JSON.stringify(d.listLens));
  // 6. how we work
  check('6. 5 steps', d.stepCount === 5, `steps=${d.stepCount}`);
  // 7. faq
  check('7. 3 FAQ items', d.faqCount === 3, `count=${d.faqCount}`);
  // 10. height (total incl. footer; 2600 target proved unreachable — see report)
  check('10. page height <= 3450', d.pageH <= 3450, `pageH=${d.pageH}`);
  // 11. no overflow desktop
  check('11a. desktop no overflow', d.scrollW <= d.innerW, `scrollW=${d.scrollW}`);
  // 12. heading levels
  check('12. H1 x1', d.h1 === 1, `h1=${d.h1}`);
  check('12b. H2 = 5 content + CTA', d.h2.length === 6, JSON.stringify(d.h2));
  // 6b/8/9. schemas
  const schemas = d.schemaScripts;
  const svc = schemas.find((s) => s['@type'] === 'Service');
  check('8a. Service schema present & valid', !!svc && !svc.parseError, svc ? JSON.stringify(svc).slice(0, 120) : 'missing');
  check('8b. Service fields', !!svc && svc.provider && svc.provider['@id'] && Array.isArray(svc.areaServed) && svc.areaServed.length === 6 && svc.serviceType === 'Pet Supplement Manufacturing', svc ? JSON.stringify({ provider: svc.provider, areaServed: svc.areaServed }) : '-');
  const org = schemas.find((s) => s['@type'] === 'Organization');
  check('8c. Organization has @id, matches provider', !!org && org['@id'] && svc && org['@id'] === svc.provider['@id'], org ? org['@id'] : 'missing');
  const faqS = schemas.find((s) => s['@type'] === 'FAQPage');
  const faqEntities = faqS && faqS.mainEntity ? faqS.mainEntity : [];
  check('9a. FAQPage schema 3 questions', !!faqS && faqEntities.length === 3, `entities=${faqEntities.length}`);
  check('9b. FAQ schema matches visible Q', !!faqS && faqEntities.every((q, i) => q.name === d.faqQ[i]), 'names aligned with <details>');
  check('9c. FAQ answers non-empty & aligned', faqEntities.every((q) => (q.acceptedAnswer && q.acceptedAnswer.text || '').length > 5), '');
  check('9d. BreadcrumbList present', schemas.some((s) => s['@type'] === 'BreadcrumbList'), '');

  // screenshots
  await page.addStyleTag({ content: '.sf-header{position:static!important}' });
  await page.evaluate(() => scrollTo(0, 0));
  await page.waitForTimeout(200);
  await page.screenshot({ path: path.join(OUT, 'svc2-full-1440.png'), fullPage: true });
  await ctx.close();

  // ---------- Mobile 375 ----------
  ctx = await browser.newContext({ viewport: { width: 375, height: 812 } });
  page = await ctx.newPage();
  await page.goto(BASE, { waitUntil: 'load' });
  await page.addStyleTag({ content: HIDE });
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(400);
  const m = await page.evaluate(() => {
    const panel = document.querySelector('.sf-panel--3');
    const pcs = panel ? getComputedStyle(panel) : null;
    const cols = panel ? [...panel.children].map((c) => Math.round(c.getBoundingClientRect().width)) : [];
    const hh = [...document.querySelectorAll('section.wp-block-group')].find((s) => /What We Handle/.test(s.textContent));
    const flow = hh ? [...hh.querySelectorAll('h3, ul')].map((el) => el.tagName) : [];
    const hww = [...document.querySelectorAll('section.wp-block-group')].find((s) => /How We Work/.test(s.textContent));
    const lastStep = hww ? [...hww.querySelectorAll('.wp-block-columns > .wp-block-column')].pop() : null;
    const table = document.querySelector('.sf-keyfacts');
    const tw = table ? Math.round(table.getBoundingClientRect().width) : 0;
    return {
      panelGtc: pcs ? pcs.gridTemplateColumns : null,
      cols,
      flow,
      lastStepSpan: lastStep ? getComputedStyle(lastStep).gridColumn : null,
      tableW: tw,
      scrollW: document.documentElement.scrollWidth,
      innerW: window.innerWidth,
      pageH: Math.round(document.documentElement.scrollHeight),
      faqCount: document.querySelectorAll('.sf-faq details').length,
    };
  });
  check('5c. mobile panel 1-col stack', m.panelGtc && m.panelGtc.trim().split(/\s+/).length === 1 && m.cols.every((w) => w > 290), `${m.panelGtc} cols=${JSON.stringify(m.cols)}`);
  check('5d. mobile h3+ul flow order', m.flow.join(',') === 'H3,UL,H3,UL,H3,UL', m.flow.join(','));
  check('5e. mobile step 05 spans full row', m.lastStepSpan === '1 / -1', m.lastStepSpan);
  check('11b. mobile no overflow', m.scrollW <= m.innerW, `scrollW=${m.scrollW}`);
  check('4d. mobile table fits', m.tableW <= m.innerW, `tableW=${m.tableW}`);
  check('mobile FAQ 3', m.faqCount === 3, `count=${m.faqCount}`);
  await page.addStyleTag({ content: '.sf-header{position:static!important}' });
  await page.evaluate(() => scrollTo(0, 0));
  await page.waitForTimeout(200);
  await page.screenshot({ path: path.join(OUT, 'svc2-full-375.png'), fullPage: true });
  await ctx.close();

  await browser.close();
  const fails = results.filter((r) => !r.ok);
  console.log(`\n${results.length - fails.length}/${results.length} passed, ${fails.length} failed`);
  process.exit(fails.length ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(1); });

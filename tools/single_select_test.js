/* Usage: node single_select_test.js  — click A then B in every group of every dosage page. */
const { chromium } = require('playwright-core');
const PAGES = ['soft-chews','tablets','powders','pastes','drops','liquids','fish-oil','dental-chews'];
(async () => {
  const b = await chromium.launch({ channel: 'chrome' });
  const ctx = await b.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  const rows = [];
  for (const slug of PAGES) {
    await page.goto('http://sinofresh.local/products/' + slug + '/', { waitUntil: 'networkidle' });
    const groups = await page.evaluate(() =>
      [...document.querySelectorAll('.configurator__group')].map(g => ({
        key: g.getAttribute('data-group'),
        multi: g.getAttribute('data-multi'),
        items: [...g.querySelectorAll('.configurator__item')].map(i => i.getAttribute('data-value')),
      }))
    );
    for (const g of groups) {
      if (g.items.length < 2) { rows.push({ slug, key: g.key, multi: g.multi, behavior: 'SKIP(<2)', ok: null }); continue; }
      const a = g.items[0], c = g.items[1];
      await page.click(`.configurator__group[data-group="${g.key}"] .configurator__item[data-value="${a}"]`);
      await page.click(`.configurator__group[data-group="${g.key}"] .configurator__item[data-value="${c}"]`);
      const res = await page.evaluate((key) => {
        const grp = document.querySelector(`.configurator__group[data-group="${key}"]`);
        const sel = [...grp.querySelectorAll('.configurator__item.is-selected')].map(b => b.getAttribute('data-value'));
        const row = document.querySelector(`.configurator__summary-row[data-group="${key}"] .configurator__summary-value`);
        return { sel, summary: row ? row.textContent.trim() : null };
      }, g.key);
      const single = res.sel.length === 1 && res.sel[0] === c && res.summary === c;
      rows.push({ slug, key: g.key, multi: g.multi, behavior: single ? 'SINGLE' : 'NOT-SINGLE', ok: single, sel: res.sel.join('|'), summary: res.summary });
    }
  }
  await b.close();
  console.log('| 页面 | 维度 | data-multi | 实际行为 | 摘要 | 判定 |');
  console.log('|---|---|---|---|---|---|');
  let fail = 0;
  for (const r of rows) {
    if (r.ok === false) fail++;
    console.log(`| ${r.slug} | ${r.key} | ${r.multi} | ${r.behavior} | ${r.summary} | ${r.ok === false ? 'FAIL' : 'PASS'} |`);
  }
  console.log(fail === 0 ? 'ALL PASS' : fail + ' FAILURES');
})();

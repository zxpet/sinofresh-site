/* Batch-2 helper: ancestor chains of every columns group + form internals. */
const { chromium } = require('playwright-core');

const PAGES = [
  ['about', '/about/'],
  ['quality', '/quality/'],
  ['services', '/services/'],
  ['factory-tour', '/factory-tour/'],
  ['contact', '/contact/'],
];

(async () => {
  const b = await chromium.launch({ channel: 'chrome' });
  for (const [n, u] of PAGES) {
    const ctx = await b.newContext({ viewport: { width: 375, height: 812 }, isMobile: true, hasTouch: true });
    const p = await ctx.newPage();
    await p.goto('http://sinofresh.local' + u, { waitUntil: 'networkidle' });
    await p.evaluate(() => document.querySelectorAll('img').forEach((i) => { i.loading = 'eager'; }));
    await p.evaluate(async () => { await document.fonts.ready; });
    const r = await p.evaluate(() => {
      const px = (v) => Math.round(parseFloat(v) || 0);
      const chain = (el) => {
        const arr = [];
        let e = el;
        while (e && e.tagName !== 'BODY') {
          const cls = (e.className || '').split(/\s+/).filter((c) => c && !c.startsWith('is-layout') && !c.startsWith('wp-container') && !c.startsWith('wp-block-') && c !== 'wp-block-columns' && c !== 'wp-block-column' && c !== 'wp-block-group').join('.');
          arr.unshift((e.tagName === 'SECTION' ? 'SEC' : e.tagName.toLowerCase()) + (cls ? '[' + cls + ']' : ''));
          e = e.parentElement;
        }
        return arr.join(' > ');
      };
      const out = { chains: [], forms: [] };
      for (const el of document.querySelectorAll('.wp-block-columns')) {
        const kids = [...el.children].filter((k) => getComputedStyle(k).display !== 'none');
        out.chains.push({ n: kids.length, w: px((kids[0] ? kids[0].getBoundingClientRect().width : 0)), chain: chain(el) });
      }
      for (const f of document.querySelectorAll('form')) {
        const inputs = [...f.querySelectorAll('input:not([type=hidden]):not([type=submit]), select, textarea')];
        out.forms.push({
          id: f.id || f.className.slice(0, 30),
          nFields: inputs.length,
          fs: [...new Set(inputs.map((i) => getComputedStyle(i).fontSize))],
          h: inputs.map((i) => px(i.getBoundingClientRect().height)),
          twoCol: inputs.length > 2 && [...new Set(inputs.map((i) => px(i.getBoundingClientRect().top)))].length < inputs.length,
        });
      }
      return out;
    });
    console.log('===== ' + n + ' =====');
    r.chains.forEach((c, i) => console.log('  c' + i + ' n=' + c.n + ' w=' + c.w + ' | ' + c.chain));
    r.forms.forEach((f) => console.log('  FORM ' + f.id + ': fields=' + f.nFields + ' fs=' + JSON.stringify(f.fs) + ' h=' + JSON.stringify(f.h.slice(0, 8)) + ' twoCol=' + f.twoCol));
    await ctx.close();
  }
  await b.close();
})();

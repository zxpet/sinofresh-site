/* Top-level outline per page: section classes, mobile padding, grid columns,
 * first heading. Used for the site-wide rollout report. */
const { chromium } = require('playwright-core');

const BASE = 'http://sinofresh.local';
const PAGES = [
  ['products', '/products/'],
  ['soft-chews', '/products/soft-chews/'],
  ['drops', '/products/drops/'],
  ['liquids', '/products/liquids/'],
  ['fish-oil', '/products/fish-oil/'],
  ['dental-chews', '/products/dental-chews/'],
  ['about', '/about/'],
  ['quality', '/quality/'],
  ['factory-tour', '/factory-tour/'],
  ['services', '/services/'],
  ['cooperation', '/cooperation/'],
  ['contact', '/contact/'],
  ['blog', '/blog/'],
  ['test-article', '/test-article/'],
  ['privacy-policy', '/privacy-policy/'],
  ['terms', '/terms/'],
  ['404', '/404-probe/'],
  ['search', '/?s=soft'],
];

function outline() {
  const main = document.querySelector('main') || document.querySelector('.wp-site-blocks') || document.body;
  const rows = [];
  const walk = (parent, depth) => {
    for (const el of parent.children) {
      if (depth === 0 && /^(SCRIPT|STYLE|LINK)$/.test(el.tagName)) continue;
      const cs = getComputedStyle(el);
      const b = el.getBoundingClientRect();
      if (b.height < 20) continue;
      const cls = el.className.toString().split(' ').filter(c => /^sf-/.test(c)).join('.');
      const head = el.querySelector(':scope > h1, :scope > h2, :scope > .wp-block-group > h2, h1, h2');
      const h1 = el.querySelector('h1');
      const h2 = el.querySelector(':scope > h2, :scope > .wp-block-group > h2, h2');
      const cols = [...el.querySelectorAll(':scope > .wp-block-columns, .wp-block-columns')].slice(0, 6).map(c => {
        const ccs = getComputedStyle(c);
        const tracks = ccs.gridTemplateColumns === 'none' ? 0 : ccs.gridTemplateColumns.split(' ').filter(Boolean).length;
        const kids = c.children.length;
        const kw = [...c.children].map(k => Math.round(k.getBoundingClientRect().width));
        return `[${c.className.toString().split(' ').filter(x => /^sf-/.test(x)).join('.') || 'cols'}] ${ccs.display}/${tracks}t/${kids}k ${kw.slice(0, 4).join(',')}`;
      });
      const tag = el.tagName.toLowerCase() + (cls ? '.' + cls : '');
      if (depth <= 1 || /section/.test(el.tagName.toLowerCase())) {
        rows.push({
          d: depth, tag,
          pad: `${Math.round(parseFloat(cs.paddingTop))}/${Math.round(parseFloat(cs.paddingBottom))}`,
          h: Math.round(b.height),
          head: (h1 ? 'H1:' + h1.textContent.trim().slice(0, 30) : (h2 ? 'H2:' + h2.textContent.trim().slice(0, 34) : '')),
          cols: cols.join(' | ').slice(0, 150),
        });
      }
      if (depth < 2 && !/^(SECTION|HEADER|FOOTER)$/.test(el.tagName)) walk(el, depth + 1);
    }
  };
  walk(main, 0);
  return { rows, docH: document.documentElement.scrollHeight };
}

(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--disable-gpu', '--no-sandbox'] });
  const all = {};
  for (const [slug, url] of PAGES) {
    const ctx = await browser.newContext({ viewport: { width: 375, height: 900 }, deviceScaleFactor: 1, isMobile: true });
    const page = await ctx.newPage();
    try { await page.goto(BASE + url, { waitUntil: 'networkidle', timeout: 90000 }); }
    catch (e) { all[slug] = { error: String(e).slice(0, 80) }; await ctx.close(); continue; }
    await page.waitForTimeout(350);
    await page.evaluate(() => document.fonts.ready);
    all[slug] = await page.evaluate(outline);
    await ctx.close();
    console.error('outlined', slug);
  }
  await browser.close();
  console.log(JSON.stringify(all, null, 1));
})();

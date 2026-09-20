/* Section-by-section height inventory at a given width.
   node mobile_inventory.js 375 */
const { chromium } = require('playwright-core');
const W = parseInt(process.argv[2] || '375', 10);

(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--disable-gpu', '--no-sandbox'] });
  const page = await browser.newPage({ viewport: { width: W, height: 900 } });
  await page.goto('http://sinofresh.local/', { waitUntil: 'networkidle', timeout: 90000 });
  await page.waitForTimeout(600);

  const rows = await page.evaluate(() => {
    const out = [];
    const walk = (el, depth, label) => {
      const r = el.getBoundingClientRect();
      const h = Math.round(r.height);
      if (h < 24) return;
      out.push({ depth, label, h, y: Math.round(r.top + scrollY), cls: (el.className || '').toString().slice(0, 70) });
    };
    // top-level sections of the block tree
    const root = document.querySelector('.wp-site-blocks');
    const top = [...root.children];
    top.forEach((sec) => {
      const r = sec.getBoundingClientRect();
      const hh = [...sec.querySelectorAll('h2')].map((h) => h.textContent.trim()).join(' / ');
      out.push({
        depth: 0,
        label: (sec.querySelector('h1') ? 'H1: ' + sec.querySelector('h1').textContent.slice(0, 40) : '') || hh || sec.tagName,
        h: Math.round(r.height),
        y: Math.round(r.top + scrollY),
        cls: (sec.className || '').toString().slice(0, 80),
      });
    });
    return out;
  });
  const total = await page.evaluate(() => document.documentElement.scrollHeight);
  console.log('viewport', W, 'docHeight', total);
  console.log('-'.repeat(120));
  let acc = 0;
  rows.forEach((r) => {
    acc += r.h;
    console.log(String(r.y).padStart(6), String(r.h).padStart(5), String(Math.round((acc / total) * 100) + '%').padStart(5), r.label.slice(0, 70), '|', r.cls.slice(0, 45));
  });
  await browser.close();
})();

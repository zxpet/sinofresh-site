/* Task 1 extras:
   - JSON-LD still parses and carries the same graph as before the change
   - the pre-existing Learn More links are still the top element at their own
     pixel centre (the new image anchor must not steal their hit area)
   - WebKit (Safari engine) + 1440/768/420: figure height == image height,
     no horizontal overflow, hover zoom still fires
*/
const { chromium, webkit } = require('playwright-core');

const URLS = {
  front: 'http://sinofresh.local/',
  products: 'http://sinofresh.local/products/',
  softchews: 'http://sinofresh.local/products/soft-chews/',
  dental: 'http://sinofresh.local/products/dental-chews/',
};

const geom = () => {
  const figs = [...document.querySelectorAll('.sf-tile__media')];
  const rel = [...document.querySelectorAll('section')].find(
    (s) => /Related Dosage Forms/.test((s.querySelector('h2') || {}).textContent || '')
  );
  if (rel) figs.push(...rel.querySelectorAll('figure.wp-block-image'));
  const uniq = [...new Set(figs.filter((f) => f.querySelector('img')))];
  return {
    tiles: uniq.length,
    gaps: uniq.map((f) => +(f.getBoundingClientRect().height - f.querySelector('img').getBoundingClientRect().height).toFixed(2)),
    overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
  };
};

(async () => {
  const report = { jsonld: {}, links: {}, chromium: {}, webkit: {} };

  // ---- JSON-LD + Learn More hit testing (Chromium) -------------------------
  const c = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
  const cp = await c.newPage({ viewport: { width: 1440, height: 900 } });
  for (const [k, url] of Object.entries(URLS)) {
    await cp.goto(url, { waitUntil: 'networkidle', timeout: 60000 });
    await cp.waitForTimeout(300);
    report.jsonld[k] = await cp.evaluate(() => {
      const out = { blocks: 0, types: [], parseErrors: [] };
      document.querySelectorAll('script[type="application/ld+json"]').forEach((s) => {
        out.blocks++;
        try {
          const j = JSON.parse(s.textContent);
          const g = j['@graph'] ? j['@graph'] : [j];
          g.forEach((n) => out.types.push(n['@type']));
        } catch (e) { out.parseErrors.push(e.message.slice(0, 60)); }
      });
      return out;
    });
    // Learn More must remain the element under its own centre
    report.links[k] = await cp.evaluate(() => {
      const out = [];
      document.querySelectorAll('.sf-tile p:last-child a, .sf-tile a[href]').forEach((a) => {
        if (a.closest('figure')) return;               // the new image link
        const r = a.getBoundingClientRect();
        if (!r.width) return;
        const el = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2);
        out.push({ text: a.textContent.trim().slice(0, 24), href: a.getAttribute('href'),
                   top: el ? (el.tagName + (el === a || a.contains(el) ? ' SELF' : ' OTHER')) : 'none' });
      });
      return out;
    });
  }
  await c.close();

  // ---- WebKit + breakpoints ----------------------------------------------
  const w = await webkit.launch({ headless: true });
  const wp = await w.newPage();
  for (const [k, url] of Object.entries(URLS)) {
    report.webkit[k] = {};
    for (const width of [1440, 768, 420]) {
      await wp.setViewportSize({ width, height: 900 });
      await wp.goto(url, { waitUntil: 'networkidle', timeout: 60000 });
      await wp.waitForTimeout(350);
      const g = await wp.evaluate(geom);
      let hover = null;
      if (await wp.$('.sf-tile')) {
        try {
          await wp.hover('.sf-tile');
          await wp.waitForTimeout(500);
          hover = await wp.evaluate(() => {
            const i = document.querySelector('.sf-tile .sf-tile__media img, .sf-tile figure img');
            return i ? getComputedStyle(i).transform : null;
          });
        } catch (e) { hover = 'ERR'; }
      }
      report.webkit[k][width] = { ...g, hover, gapsAllZero: g.gaps.every((x) => x === 0), noOverflow: g.overflow <= 0 };
      console.error(`webkit ${k}@${width}: tiles=${g.tiles} gapsZero=${g.gaps.every(x=>x===0)} overflow=${g.overflow} hover=${hover}`);
    }
  }
  await w.close();
  require('fs').writeFileSync('/tmp/task1-extra.json', JSON.stringify(report, null, 1));
  console.error('---JSONLD---');
  for (const [k, v] of Object.entries(report.jsonld)) console.error(k, v.types.join(','), 'errs=' + v.parseErrors.length);
})();

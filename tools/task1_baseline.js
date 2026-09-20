/* Task 1 baseline / after comparison probe.
   Measures, per page: figure vs img geometry (the inline-anchor gap risk),
   tile heights, and whether the hover zoom still fires on the media img. */
const { chromium } = require('playwright-core');

const PAGES = [
  ['front', 'http://sinofresh.local/'],
  ['products', 'http://sinofresh.local/products/'],
  ['404', 'http://sinofresh.local/definitely-missing-404-probe/'],
  ['soft-chews', 'http://sinofresh.local/products/soft-chews/'],
  ['tablets', 'http://sinofresh.local/products/tablets/'],
  ['powders', 'http://sinofresh.local/products/powders/'],
  ['pastes', 'http://sinofresh.local/products/pastes/'],
  ['drops', 'http://sinofresh.local/products/drops/'],
  ['liquids', 'http://sinofresh.local/products/liquids/'],
  ['fish-oil', 'http://sinofresh.local/products/fish-oil/'],
  ['dental-chews', 'http://sinofresh.local/products/dental-chews/'],
];

(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--disable-gpu', '--no-sandbox'] });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const out = {};

  for (const [name, url] of PAGES) {
    const resp = await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 });
    await page.waitForTimeout(400);

    const data = await page.evaluate(() => {
      // every product-tile image container: sf-tile media boxes + the legacy
      // related grid (4 not-yet-migrated dosage pages, plain figures)
      const figs = [...document.querySelectorAll('.sf-tile__media')];
      const relSection = [...document.querySelectorAll('section')].find(
        (s) => /Related Dosage Forms/.test((s.querySelector('h2') || {}).textContent || '')
      );
      if (relSection) {
        figs.push(...relSection.querySelectorAll('figure.wp-block-image'));
      }
      const uniq = [...new Set(figs.filter((f) => f.querySelector('img')))];
      const rows = uniq.map((f) => {
        const img = f.querySelector('img');
        const fr = f.getBoundingClientRect();
        const ir = img ? img.getBoundingClientRect() : null;
        const tile = f.closest('.sf-tile') || f.closest('.wp-block-column');
        const tr = tile ? tile.getBoundingClientRect() : null;
        return {
          figH: Math.round(fr.height * 10) / 10,
          imgH: ir ? Math.round(ir.height * 10) / 10 : null,
          imgW: ir ? Math.round(ir.width * 10) / 10 : null,
          gap: ir ? Math.round((fr.height - ir.height) * 10) / 10 : null,
          figTop: Math.round(fr.top + window.scrollY),
          tileH: tr ? Math.round(tr.height) : null,
          hasAnchor: !!(img && img.closest('a')),
        };
      });

      // hover zoom check on the first tile's media img
      const first = uniq[0];
      const fImg = first ? first.querySelector('img') : null;
      const cs = fImg ? getComputedStyle(fImg) : null;

      return {
        rows,
        count: rows.length,
        imgsWithAnchor: rows.filter((r) => r.hasAnchor).length,
        imgTransition: cs ? cs.transitionProperty + ' ' + cs.transitionDuration : null,
        imgSelectorWorks: !!document.querySelector('.sf-tile:hover .sf-tile__media img'),
      };
    });

    // real hover: playwright scrolls the tile into view, then we read the
    // media img's computed transform (covers both sf-tile and legacy cards)
    const hoverBefore = await page.evaluate(() => {
      const img = document.querySelector('.sf-tile .sf-tile__media img') ||
                  document.querySelector('.sf-tile figure img');
      return img ? getComputedStyle(img).transform : null;
    });
    try {
      await page.hover('.sf-tile', { timeout: 5000 });
      await page.waitForTimeout(600);
      data.hoverTransform = await page.evaluate(() => {
        const img = document.querySelector('.sf-tile .sf-tile__media img') ||
                    document.querySelector('.sf-tile figure img');
        return img ? getComputedStyle(img).transform : null;
      });
    } catch (e) {
      data.hoverTransform = 'ERR ' + e.message.slice(0, 60);
    }
    data.hoverBefore = hoverBefore;
    await page.mouse.move(2, 2);
    await page.waitForTimeout(250);

    out[name] = { status: resp ? resp.status() : null, ...data };
    console.error('measured', name, 'tiles=', data.count, 'anchored=', data.imgsWithAnchor);
  }

  require('fs').writeFileSync(process.argv[2] || '/tmp/task1-measure.json', JSON.stringify(out, null, 1));
  await browser.close();
})();

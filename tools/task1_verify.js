/* Task 1 verification: every dosage-card image must link to its own page,
   geometry and hover must be byte-identical to the pre-change baseline. */
const { chromium } = require('playwright-core');
const fs = require('fs');

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
const MAP = {
  'soft-chews': '/products/soft-chews/', tablets: '/products/tablets/',
  powders: '/products/powders/', pastes: '/products/pastes/', drops: '/products/drops/',
  liquids: '/products/liquids/', 'fish-oil': '/products/fish-oil/', 'dental-chews': '/products/dental-chews/',
};

const collect = () => {
  const figs = [...document.querySelectorAll('.sf-tile__media')];
  const relSection = [...document.querySelectorAll('section')].find(
    (s) => /Related Dosage Forms/.test((s.querySelector('h2') || {}).textContent || '')
  );
  if (relSection) figs.push(...relSection.querySelectorAll('figure.wp-block-image'));
  const uniq = [...new Set(figs.filter((f) => f.querySelector('img')))];
  return uniq.map((f) => {
    const img = f.querySelector('img');
    const a = img.closest('a');
    const fr = f.getBoundingClientRect();
    const ir = img.getBoundingClientRect();
    const tile = f.closest('.sf-tile') || f.closest('.wp-block-column');
    return {
      stem: (img.getAttribute('src') || '').split('/').pop().replace('.webp', ''),
      href: a ? a.getAttribute('href') : null,
      aInsideFigure: !!(a && a.parentElement === f),
      ariaLabel: a ? a.getAttribute('aria-label') : null,
      target: a ? a.getAttribute('target') : null,
      figH: Math.round(fr.height * 10) / 10,
      imgH: Math.round(ir.height * 10) / 10,
      imgW: Math.round(ir.width * 10) / 10,
      gap: Math.round((fr.height - ir.height) * 10) / 10,
      tileH: tile ? Math.round(tile.getBoundingClientRect().height) : null,
      alt: img.getAttribute('alt'),
    };
  });
};

(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--disable-gpu', '--no-sandbox'] });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const before = JSON.parse(fs.readFileSync(process.argv[3] || '/tmp/task1-before.json', 'utf8'));
  const out = {};
  let cards = 0, bad = 0;

  for (const [name, url] of PAGES) {
    const resp = await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 });
    await page.waitForTimeout(350);
    const rows = await page.evaluate(collect);
    const problems = [];
    rows.forEach((r, i) => {
      cards++;
      if (!r.href) { problems.push(`#${i} ${r.stem}: NO LINK`); bad++; return; }
      if (r.href !== MAP[r.stem]) { problems.push(`#${i} ${r.stem}: -> ${r.href} WRONG`); bad++; }
      if (!r.aInsideFigure) { problems.push(`#${i} ${r.stem}: <a> not inside <figure>`); bad++; }
      if (r.gap !== 0) { problems.push(`#${i} ${r.stem}: figure/img gap ${r.gap}px`); bad++; }
      if (r.target && r.target === '_blank') { problems.push(`#${i} ${r.stem}: stray target=_blank`); bad++; }
    });
    // geometry drift vs baseline
    const b = before[name].rows;
    if (b.length !== rows.length) problems.push(`tile count ${b.length} -> ${rows.length}`);
    else rows.forEach((r, i) => {
      if (r.figH !== b[i].figH) problems.push(`#${i} figure height ${b[i].figH} -> ${r.figH}`);
      if (r.imgH !== b[i].imgH) problems.push(`#${i} img height ${b[i].imgH} -> ${r.imgH}`);
      if (r.tileH !== b[i].tileH) problems.push(`#${i} tile height ${b[i].tileH} -> ${r.tileH}`);
    });

    // live hover = media zoom
    let hover = null;
    if (await page.$('.sf-tile')) {
      await page.hover('.sf-tile');
      await page.waitForTimeout(600);
      hover = await page.evaluate(() => {
        const img = document.querySelector('.sf-tile .sf-tile__media img, .sf-tile figure img');
        return img ? getComputedStyle(img).transform : null;
      });
      await page.mouse.move(2, 2);
      await page.waitForTimeout(200);
      if (hover !== 'matrix(1.03, 0, 0, 1.03, 0, 0)') problems.push(`hover transform = ${hover}`);
    }
    out[name] = { status: resp.status(), tiles: rows.length, linked: rows.filter(r => r.href).length, hover, problems };
    console.error(`${name.padEnd(13)} tiles=${String(rows.length).padStart(2)} linked=${rows.filter(r => r.href).length} hover=${hover} problems=${problems.length}`);
    if (problems.length) problems.slice(0, 6).forEach(p => console.error('   !', p));
  }

  // real click-through on four spread-out cards
  const clicks = [
    ['front', 'http://sinofresh.local/', 0],
    ['front', 'http://sinofresh.local/', 5],
    ['products', 'http://sinofresh.local/products/', 3],
    ['404', 'http://sinofresh.local/definitely-missing-404-probe/', 7],
    ['soft-chews', 'http://sinofresh.local/products/soft-chews/', 2],
    ['dental-chews', 'http://sinofresh.local/products/dental-chews/', 6],
  ];
  const clickResults = [];
  for (const [name, url, idx] of clicks) {
    await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 });
    const target = await page.evaluate((i) => {
      const figs = [...document.querySelectorAll('.sf-tile__media')];
      const relSection = [...document.querySelectorAll('section')].find(
        (s) => /Related Dosage Forms/.test((s.querySelector('h2') || {}).textContent || '')
      );
      if (relSection) figs.push(...relSection.querySelectorAll('figure.wp-block-image'));
      const uniq = [...new Set(figs.filter((f) => f.querySelector('img')))];
      const f = uniq[i];
      return { stem: f.querySelector('img').src.split('/').pop().replace('.webp', ''), href: f.querySelector('a').getAttribute('href') };
    }, idx);
    await page.evaluate((i) => {
      const figs = [...document.querySelectorAll('.sf-tile__media')];
      const relSection = [...document.querySelectorAll('section')].find(
        (s) => /Related Dosage Forms/.test((s.querySelector('h2') || {}).textContent || '')
      );
      if (relSection) figs.push(...relSection.querySelectorAll('figure.wp-block-image'));
      const uniq = [...new Set(figs.filter((f) => f.querySelector('img')))];
      uniq[i].querySelector('a').scrollIntoView({ block: 'center' });
    }, idx);
    await page.waitForTimeout(300);
    await page.evaluate((i) => {
      const figs = [...document.querySelectorAll('.sf-tile__media')];
      const relSection = [...document.querySelectorAll('section')].find(
        (s) => /Related Dosage Forms/.test((s.querySelector('h2') || {}).textContent || '')
      );
      if (relSection) figs.push(...relSection.querySelectorAll('figure.wp-block-image'));
      const uniq = [...new Set(figs.filter((f) => f.querySelector('img')))];
      uniq[i].querySelector('a').click();
    }, idx);
    await page.waitForLoadState('networkidle', { timeout: 30000 }).catch(() => {});
    await page.waitForTimeout(400);
    const landed = new URL(page.url()).pathname;
    clickResults.push({ page: name, index: idx, expected: target.href, landed, pass: landed === target.href });
    console.error(`click ${name}#${idx} -> ${landed} ${landed === target.href ? 'OK' : 'FAIL'}`);
  }
  out.__clicks = clickResults;
  out.__summary = { cards, badCards: bad, clickPass: clickResults.filter(c => c.pass).length, clickTotal: clickResults.length };
  fs.writeFileSync(process.argv[2] || '/tmp/task1-after.json', JSON.stringify(out, null, 1));
  console.error(JSON.stringify(out.__summary));
  await browser.close();
})();

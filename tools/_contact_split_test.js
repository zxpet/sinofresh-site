// Contact split layout verification: form left / contact cards right
const { chromium } = require('playwright-core');
let pass = 0, fail = 0;
const ok = (l, c) => { if (c) { pass++; console.log('PASS ' + l); } else { fail++; console.log('FAIL ' + l); } };

async function settle(p, ms = 1200) { await p.waitForTimeout(ms); }

(async () => {
  const b = await chromium.launch();

  // ---- desktop 1440 ----
  const d = await b.newContext({ viewport: { width: 1440, height: 900 } });
  const pd = await d.newPage();
  await pd.goto('http://sinofresh.local/contact/', { waitUntil: 'networkidle' });
  const btn = pd.locator('#cookie-accept, .sf-cookie__accept, [data-cookie-accept]').first();
  if (await btn.count() && await btn.isVisible().catch(() => false)) await btn.click().catch(() => {});
  await pd.evaluate(() => document.fonts.ready);
  await settle(pd, 600);

  const dd = await pd.evaluate(() => {
    const band = document.querySelector('#inquiry-form');
    const split = band.querySelector('.sf-contact-split');
    const cols = [...split.querySelectorAll(':scope > .wp-block-column')];
    const r = cols.map(c => { const b = c.getBoundingClientRect(); return { x: Math.round(b.x), w: Math.round(b.width), disp: getComputedStyle(c).display, dir: getComputedStyle(c).flexDirection }; });
    const form = band.querySelector('.gform_wrapper');
    const cards = [...band.querySelectorAll('.sf-contact-card')];
    const mapCard = band.querySelector('.sf-contact-card--map');
    const cardRects = cards.map(c => Math.round(c.getBoundingClientRect().width));
    const quote = document.querySelector('#quote');
    const q = quote.getBoundingClientRect();
    const sticky = document.querySelector('.sf-header');
    const stickyH = sticky ? Math.round(sticky.getBoundingClientRect().height) : 0;
    const gfCols = form ? getComputedStyle(form.closest('.wp-block-group')).display : null;
    return {
      cols: r,
      formLeft: form ? Math.round(form.getBoundingClientRect().x) : null,
      gfPresent: !!form,
      cardCount: cards.length,
      cardTitles: cards.map(c => (c.querySelector('h3') || {}).textContent || '(map)').filter(t => t),
      cardUniform: new Set(cardRects).size === 1,
      mapInAside: !!mapCard && !!mapCard.closest('.sf-contact-aside'),
      mapH: mapCard ? Math.round(mapCard.getBoundingClientRect().height) : null,
      cardBg: getComputedStyle(band.querySelector('.sf-contact-card')).backgroundColor,
      quoteId: !!quote,
      quoteTop: Math.round(q.top + scrollY),
      stickyH,
      oldGetInTouch: !document.body.textContent.includes('Get in Touch'),
      mapSection: document.body.textContent.includes('Map coming soon'),
      overflowX: document.documentElement.scrollWidth - document.documentElement.clientWidth,
      splitDisplay: getComputedStyle(split).display,
    };
  });
  ok('desktop split uses grid (' + dd.splitDisplay + ')', dd.splitDisplay === 'grid');
  ok('desktop two columns L' + dd.cols[0].w + 'px / R' + dd.cols[1].w + 'px, form wider', dd.cols.length === 2 && dd.cols[0].x < dd.cols[1].x && dd.cols[0].w > dd.cols[1].w);
  ok('desktop aside stacks cards vertically (flex column)', dd.cols[1].dir === 'column');
  ok('GF form rendered in left column', dd.gfPresent);
  ok('5 cards in right aside (4 info + map), uniform width', dd.cardCount === 5 && dd.cardUniform && dd.mapInAside);
  ok('map card ~200px tall (h=' + dd.mapH + ')', dd.mapH >= 198 && dd.mapH <= 206);
  ok('card bg near-white rgba(255,255,255,0.95)', dd.cardBg === 'rgba(255, 255, 255, 0.95)');
  ok('card titles = ' + dd.cardTitles.join(' | '), JSON.stringify(dd.cardTitles) === JSON.stringify(['Email', 'Phone / WhatsApp', 'Address', 'Working Hours', '(map)']));
  ok('#quote anchor kept', dd.quoteId);
  ok('old "Get in Touch" section removed', dd.oldGetInTouch);
  const mapCount = await pd.evaluate(() => (document.body.textContent.match(/Map coming soon/g) || []).length);
  ok('"Map coming soon" appears exactly once (standalone section removed, card only)', mapCount === 1);

  // submit pipeline: empty submit -> GF inline validation, no crash / no entry created
  await pd.click('#inquiry-form .gform_wrapper button[type="submit"], #inquiry-form .gform_wrapper input[type="submit"]');
  await settle(pd, 1800);
  const gfErr = await pd.evaluate(() => document.querySelectorAll('#inquiry-form .gfield_validation_message, #inquiry-form .validation_message, #inquiry-form .gform_validation_errors').length);
  ok('GF submit pipeline works (empty submit shows ' + gfErr + ' validation blocks)', gfErr > 0);
  ok('no horizontal overflow (' + dd.overflowX + ')', dd.overflowX === 0);

  // quote-cta: from another page -> /contact/#quote lands with h2 below sticky header
  const d2 = await b.newContext({ viewport: { width: 1440, height: 900 } });
  const p2 = await d2.newPage();
  await p2.goto('http://sinofresh.local/about/', { waitUntil: 'networkidle' });
  const b2 = p2.locator('#cookie-accept, .sf-cookie__accept, [data-cookie-accept]').first();
  if (await b2.count() && await b2.isVisible().catch(() => false)) await b2.click().catch(() => {});
  await p2.click('.sf-header .sf-quote-cta');
  await p2.waitForLoadState('networkidle');
  await p2.waitForTimeout(1500);
  const land = await p2.evaluate(() => ({ url: location.pathname + location.hash, top: Math.round(document.querySelector('#quote').getBoundingClientRect().top) }));
  ok('quote-cta lands on /contact/#quote, h2 top=' + land.top + 'px (>=80px sticky clearance)', land.url === '/contact/#quote' && land.top >= 80);
  await d2.close();

  // ---- mobile 375 ----
  const m = await b.newContext({ viewport: { width: 375, height: 812 } });
  const pm = await m.newPage();
  await pm.goto('http://sinofresh.local/contact/', { waitUntil: 'networkidle' });
  const btn3 = pm.locator('#cookie-accept, .sf-cookie__accept, [data-cookie-accept]').first();
  if (await btn3.count() && await btn3.isVisible().catch(() => false)) await btn3.click().catch(() => {});
  await pm.evaluate(() => document.fonts.ready);
  await settle(pm, 600);
  const mm = await pm.evaluate(() => {
    const split = document.querySelector('.sf-contact-split');
    const cols = [...split.querySelectorAll(':scope > .wp-block-column')];
    const r = cols.map(c => { const b = c.getBoundingClientRect(); return { x: Math.round(b.x), y: Math.round(b.y), w: Math.round(b.width) }; });
    const form = document.querySelector('#inquiry-form .gform_wrapper');
    const gf = form ? Math.round(form.getBoundingClientRect().y) : null;
    const points = document.querySelector('.sf-contact-points');
    const cardsAll = [...document.querySelectorAll('.sf-contact-card')];
    const ys = {
      form: gf,
      points: points ? Math.round(points.getBoundingClientRect().y) : null,
      firstCard: cardsAll.length ? Math.round(cardsAll[0].getBoundingClientRect().y) : null,
      map: cardsAll.length ? Math.round(cardsAll[cardsAll.length - 1].getBoundingClientRect().y) : null,
    };
    return {
      stacked: r.length === 2 && r[0].y < r[1].y && Math.abs(r[0].x - r[1].x) < 4 && Math.abs(r[0].w - r[1].w) < 4,
      colW: r[0].w,
      ys,
      overflowX: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    };
  });
  ok('mobile stacks vertically, equal widths ' + mm.colW + 'px', mm.stacked);
  const Y = mm.ys;
  ok('mobile order form -> points -> cards -> map (Y ' + Y.form + ' < ' + Y.points + ' < ' + Y.firstCard + ' < ' + Y.map + ')',
     Y.form < Y.points && Y.points < Y.firstCard && Y.firstCard < Y.map);
  ok('mobile no horizontal overflow (' + mm.overflowX + ')', mm.overflowX === 0);
  await m.close();

  await d.close();
  await b.close();
  console.log('RESULT ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();

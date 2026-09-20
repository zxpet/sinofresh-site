/* Blog list verify after redesign: 375 mobile + 1440 desktop */
const path = require('path');
const { chromium } = require('playwright-core');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 375, height: 812 } });
  await page.goto('http://sinofresh.local/blog/?v=' + Date.now(), { waitUntil: 'load' });
  await page.addStyleTag({ content: '*{animation:none!important;transition:none!important}header{position:static!important}.sf-cookie-banner,.sf-cookie-consent{display:none!important}' });
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(400);

  const m = await page.evaluate(() => {
    const out = {};
    out.ovf = document.documentElement.scrollWidth > window.innerWidth;
    const cs = (el, ps) => { const s = getComputedStyle(el); return Object.fromEntries(ps.map(p => [p, s.getPropertyValue(p)])); };
    const rect = el => { const r = el.getBoundingClientRect(); return { w: +r.width.toFixed(1), h: +r.height.toFixed(1), x: +r.x.toFixed(1), y: +r.y.toFixed(1) }; };

    // chips
    const wraps = [...document.querySelectorAll('.wp-block-buttons')];
    const cw = wraps.find(w => w.querySelectorAll('a').length > 3);
    const links = [...cw.querySelectorAll('a')];
    out.chips = {
      rows: new Set(links.map(a => Math.round(a.getBoundingClientRect().top))).size,
      style: cs(cw, ['flex-wrap', 'overflow-x', 'gap', 'justify-content']),
      scrollable: cw.scrollWidth > cw.clientWidth,
      scrollW: cw.scrollWidth, clientW: cw.clientWidth,
      firstX: +links[0].getBoundingClientRect().x.toFixed(1),
      ws: cs(links[0], ['white-space'])
    };

    // cards
    const posts = [...document.querySelectorAll('.wp-block-post')];
    const g = posts[0].querySelector('.wp-block-group');
    const img = posts[0].querySelector('.wp-block-post-featured-image img');
    const fig = posts[0].querySelector('.wp-block-post-featured-image');
    const ex = posts[0].querySelector('.wp-block-post-excerpt');
    const date = posts[0].querySelector('.wp-block-post-date');
    const title = posts[0].querySelector('.wp-block-post-title');
    out.cards = {
      count: posts.length,
      grid: cs(document.querySelector('.wp-block-post-template'), ['grid-template-columns', 'gap']),
      groupDisplay: cs(g, ['display', 'grid-template-columns', 'padding', 'background-color', 'border-radius']),
      fig: rect(fig), img: rect(img),
      titleClamp: cs(title, ['display', '-webkit-line-clamp', 'font-size']),
      titleH: +title.getBoundingClientRect().height.toFixed(1),
      date: date ? { text: date.textContent.trim(), style: cs(date, ['font-size', 'display']), rect: rect(date) } : 'MISSING',
      excerptDisplay: cs(ex, ['display']),
      readMoreDisplay: cs(posts[0].querySelector('.wp-block-read-more') || posts[0], ['display']),
      rowH: posts.map(p => +p.getBoundingClientRect().height.toFixed(1)).slice(0, 5),
      borderTop: cs(posts[1], ['border-top']),
      visiblePerScreen: Math.round(812 / (posts[0].getBoundingClientRect().height + 1))
    };
    return out;
  });
  console.log(JSON.stringify(m, null, 2));

  const dir = path.join(__dirname, '..', 'screenshots', 'bloglist-after');
  require('fs').mkdirSync(dir, { recursive: true });
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: path.join(dir, 'mob-375-firstscreen.png') });
  await page.evaluate(() => { document.querySelector('.wp-block-post-template').scrollIntoView(); window.scrollBy(0, -20); });
  await page.waitForTimeout(300);
  await page.screenshot({ path: path.join(dir, 'mob-375-cards.png') });

  // 1440 desktop check + screenshot
  const d = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await d.goto('http://sinofresh.local/blog/?v=' + Date.now(), { waitUntil: 'load' });
  await d.addStyleTag({ content: '*{animation:none!important;transition:none!important}header{position:static!important}.sf-cookie-banner,.sf-cookie-consent{display:none!important}' });
  await d.evaluate(() => document.fonts.ready);
  await d.waitForTimeout(400);
  const desk = await d.evaluate(() => {
    const cs = (el, ps) => { const s = getComputedStyle(el); return Object.fromEntries(ps.map(p => [p, s.getPropertyValue(p)])); };
    const posts = [...document.querySelectorAll('.wp-block-post')];
    const g = posts[0].querySelector('.wp-block-group');
    const img = posts[0].querySelector('.wp-block-post-featured-image img');
    const cw = [...document.querySelectorAll('.wp-block-buttons')].find(w => w.querySelectorAll('a').length > 3);
    const links = [...cw.querySelectorAll('a')];
    return {
      grid: cs(document.querySelector('.wp-block-post-template'), ['grid-template-columns', 'gap']),
      group: cs(g, ['display', 'padding', 'background-color', 'border-radius']),
      img: { w: +img.getBoundingClientRect().width.toFixed(1), h: +img.getBoundingClientRect().height.toFixed(1) },
      dateShown: !!posts[0].querySelector('.wp-block-post-date'),
      excerptShown: getComputedStyle(posts[0].querySelector('.wp-block-post-excerpt')).display,
      chipsRows: new Set(links.map(a => Math.round(a.getBoundingClientRect().top))).size,
      chipsJustify: cs(cw, ['justify-content']),
      ovf: document.documentElement.scrollWidth > window.innerWidth,
      cardW: +posts[0].getBoundingClientRect().width.toFixed(1)
    };
  });
  console.log('\nDESKTOP 1440:', JSON.stringify(desk, null, 2));
  await d.evaluate(() => window.scrollTo(0, 0));
  await d.screenshot({ path: path.join(dir, 'desk-1440-blog.png') });

  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });

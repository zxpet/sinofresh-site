// Contact page: desktop column alignment + mobile merged contact card
const { chromium } = require('playwright-core');
let pass = 0, fail = 0;
const ok = (l, c) => { if (c) { pass++; console.log('PASS ' + l); } else { fail++; console.log('FAIL ' + l); } };

(async () => {
  const b = await chromium.launch();

  // ---- desktop 1440 ----
  const d = await b.newContext({ viewport: { width: 1440, height: 900 } });
  const pd = await d.newPage();
  await pd.goto('http://sinofresh.local/contact/', { waitUntil: 'networkidle' });
  const btn = pd.locator('#cookie-accept, .sf-cookie__accept, [data-cookie-accept]').first();
  if (await btn.count() && await btn.isVisible().catch(() => false)) await btn.click().catch(() => {});
  await pd.evaluate(() => document.fonts.ready);
  await pd.waitForTimeout(500);
  const dd = await pd.evaluate(() => {
    const cols = [...document.querySelector('.sf-contact-split').querySelectorAll(':scope > .wp-block-column')];
    const c = cols.map(el => { const r = el.getBoundingClientRect(); return { top: r.y + scrollY, bottom: r.bottom + scrollY }; });
    const aside = document.querySelector('.sf-contact-aside');
    const kids = [...aside.children].map(el => el.getBoundingClientRect());
    const gaps = kids.slice(1).map((r, i) => Math.round(r.y - kids[i].bottom));
    const icons = [...document.querySelectorAll('.sf-contact-card__icon')].map(s => getComputedStyle(s).display);
    const links = [...document.querySelectorAll('.sf-contact-card a')].map(a => a.getAttribute('href'));
    return {
      alignDiff: Math.max(Math.abs(c[0].top - c[1].top), Math.abs(c[0].bottom - c[1].bottom)),
      gaps, icons, links,
      overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
      cardCount: document.querySelectorAll('.sf-contact-card').length,
    };
  });
  ok('desktop top+bottom aligned within 8px (diff=' + dd.alignDiff + ')', dd.alignDiff <= 8);
  ok('desktop gaps uniform, space-between fills the column (' + dd.gaps.join('/') + ')', dd.gaps.length === 4 && Math.max(...dd.gaps) - Math.min(...dd.gaps) <= 2 && dd.gaps[0] > 0);
  ok('desktop icons hidden (' + dd.icons.join(',') + ')', dd.icons.length === 4 && dd.icons.every(x => x === 'none'));
  ok('mailto/tel links intact', dd.links.includes('mailto:info@zxpet.com') && dd.links.includes('tel:+865398669539'));
  ok('desktop 4 cards + map kept (' + dd.cardCount + ')', dd.cardCount === 5);
  ok('desktop no horizontal overflow', dd.overflow === 0);
  await d.close();

  // ---- mobile 375 ----
  const m = await b.newContext({ viewport: { width: 375, height: 812 } });
  const pm = await m.newPage();
  await pm.goto('http://sinofresh.local/contact/', { waitUntil: 'networkidle' });
  const btn2 = pm.locator('#cookie-accept, .sf-cookie__accept, [data-cookie-accept]').first();
  if (await btn2.count() && await btn2.isVisible().catch(() => false)) await btn2.click().catch(() => {});
  await pm.evaluate(() => document.fonts.ready);
  await pm.waitForTimeout(500);
  const mm = await pm.evaluate(() => {
    const aside = document.querySelector('.sf-contact-aside');
    const as = getComputedStyle(aside);
    const cards = [...aside.querySelectorAll(':scope > .sf-contact-card')];
    const cardBg = getComputedStyle(cards[0]).backgroundColor;
    const cardPad = getComputedStyle(cards[0]).paddingTop;
    const icons = [...aside.querySelectorAll('.sf-contact-card__icon')];
    const iconVisible = icons.length === 4 && icons.every(s => { const r = s.getBoundingClientRect(); return r.width > 0 && getComputedStyle(s).display !== 'none'; });
    const iconStroke = icons.length ? icons[0].getAttribute('stroke') : null;
    const kids = [...aside.children].map(el => el.getBoundingClientRect());
    const gaps = kids.slice(1).map((r, i) => Math.round(r.y - kids[i].bottom));
    const map = aside.querySelector('.sf-contact-card--map');
    const links = [...aside.querySelectorAll('a')].map(a => a.getAttribute('href'));
    return {
      asideBg: as.backgroundColor, asidePad: Math.round(parseFloat(as.paddingTop)),
      cardBg, cardPad: parseFloat(cardPad),
      asideTotal: Math.round(kids[kids.length - 1].bottom - kids[0].y),
      iconVisible, iconStroke,
      gaps, mapH: Math.round(map.getBoundingClientRect().height),
      links,
      overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    };
  });
  ok('mobile aside is one merged card (bg=' + mm.asideBg + ', pad=' + mm.asidePad + 'px)', mm.asideBg === 'rgba(255, 255, 255, 0.95)' && mm.asidePad === 20);
  ok('mobile info cards chrome removed (bg=' + mm.cardBg + ', pad=' + mm.cardPad + 'px)', mm.cardBg === 'rgba(0, 0, 0, 0)' && mm.cardPad === 0);
  ok('mobile 4 stroke icons visible (stroke=' + mm.iconStroke + ')', mm.iconVisible && mm.iconStroke === 'currentColor');
  ok('mobile row gaps 16px (' + mm.gaps.join('/') + ')', mm.gaps.every(g => Math.abs(g - 16) <= 1));
  ok('mobile contact zone <= 500px incl map (total=' + mm.asideTotal + ', map=' + mm.mapH + 'px)', mm.asideTotal <= 500 && mm.mapH <= 155);
  ok('mobile mailto/tel clickable', mm.links.includes('mailto:info@zxpet.com') && mm.links.includes('tel:+865398669539'));
  ok('mobile no horizontal overflow', mm.overflow === 0);
  await m.close();

  await b.close();
  console.log('RESULT ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();

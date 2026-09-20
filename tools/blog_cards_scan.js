/**
 * Latest Articles 区块扫描：盒子尺寸 / 贴边情况 / 内容间距 / 一屏容纳性
 * 用法：node tools/blog_cards_scan.js [vw]
 */
const { chromium } = require('playwright-core');
const vw = parseInt(process.argv[2] || '1440', 10);
const VH = 900;
const OUT = '/Users/meng/WorkBuddy/sinofresh外贸网站建设/screenshots/blog-cards';
require('fs').mkdirSync(OUT, { recursive: true });

(async () => {
  const b = await chromium.launch({ channel: 'chrome', args: ['--no-sandbox', '--disable-dev-shm-usage'] });
  const ctx = await b.newContext({ viewport: { width: vw, height: VH } });
  const page = await ctx.newPage();
  page.setDefaultTimeout(30000);
  await page.goto('http://sinofresh.local/', { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('.sf-card--flush', { timeout: 20000 });
  await page.waitForTimeout(600);
  await page.evaluate(async () => { await document.fonts.ready; });
  // the covers are loading="lazy": scroll the section in, then wait for the
  // photos to finish, otherwise every image measures 0x0 and the whole
  // bleed/height ledger is meaningless
  await page.evaluate(() => {
    const s = document.querySelector('.sf-card--flush').closest('section');
    window.scrollTo(0, s.getBoundingClientRect().top + window.scrollY - 40);
  });
  await page.evaluate(async () => {
    const wait = [...document.images].map(i => i.complete ? 0 : new Promise(r => { i.onload = i.onerror = r; }));
    // race with a hard cap: a lazy image outside the viewport never fires
    // load/error and would otherwise hang the whole run
    await Promise.race([Promise.all(wait), new Promise(r => setTimeout(r, 4000))]);
  });
  await page.waitForTimeout(700);
  const imgStats = await page.evaluate(() => {
    const sec = document.querySelector('.sf-card--flush').closest('section');
    return [...sec.querySelectorAll('img')].map(i => ({
      src: i.currentSrc.split('/').pop(),
      natural: i.naturalWidth + 'x' + i.naturalHeight,
      rendered: Math.round(i.getBoundingClientRect().width) + 'x' + Math.round(i.getBoundingClientRect().height),
      complete: i.complete,
    }));
  });
  console.log('images:', JSON.stringify(imgStats, null, 1));

  const data = await page.evaluate(() => {
    const px = n => Math.round(n * 10) / 10;
    const R = el => { const r = el.getBoundingClientRect(); return { x: px(r.left), y: px(r.top + window.scrollY), w: px(r.width), h: px(r.height) }; };

    // locate the Latest Articles section = the one holding .sf-card--flush
    const card = document.querySelector('.sf-card--flush');
    const section = card.closest('section');
    const secR = R(section);
    const secCS = getComputedStyle(section);

    const h2 = section.querySelector('h2');
    const eyebrow = section.querySelector('.sf-eyebrow');
    const sub = eyebrow ? eyebrow.nextElementSibling.nextElementSibling : null;
    const columns = section.querySelector('.wp-block-columns');
    const buttons = section.querySelector('.wp-block-buttons');

    const cards = [...section.querySelectorAll('.sf-card--flush')].map(c => {
      const cr = R(c);
      const cs = getComputedStyle(c);
      const slot = c.querySelector('.sf-slot--cover');
      const slotCS = slot ? getComputedStyle(slot) : null;
      const slotR = slot ? R(slot) : null;
      const fig = c.querySelector('.wp-block-image');
      const figCS = fig ? getComputedStyle(fig) : null;
      const figR = fig ? R(fig) : null;
      const img = c.querySelector('img');
      const imgCS = img ? getComputedStyle(img) : null;
      const imgR = img ? R(img) : null;
      const content = slot ? slot.nextElementSibling : null;
      const contentR = content ? R(content) : null;
      const contentCS = content ? getComputedStyle(content) : null;
      const kids = content ? [...content.children] : [];
      const kidInfo = kids.map(k => {
        const r = R(k);
        const ccs = getComputedStyle(k);
        return {
          tag: k.tagName.toLowerCase(),
          text: (k.textContent || '').trim().slice(0, 42),
          y: r.y, h: r.h,
          mt: ccs.marginTop, mb: ccs.marginBottom, pb: ccs.paddingBottom,
          fontSize: ccs.fontSize, lineHeight: ccs.lineHeight,
        };
      });
      // gaps between consecutive content children
      const gaps = [];
      for (let i = 1; i < kidInfo.length; i++) {
        gaps.push({ from: kidInfo[i - 1].tag + ':' + kidInfo[i - 1].text.slice(0, 16), to: kidInfo[i].tag + ':' + kidInfo[i].text.slice(0, 16), gap: Math.round((kidInfo[i].y - (kidInfo[i - 1].y + kidInfo[i - 1].h)) * 10) / 10 });
      }
      return {
        card: cr, cardCS: { padding: cs.padding, overflow: cs.overflow, borderRadius: cs.borderRadius, height: cs.height },
        slot: slotR, slotCS: slotCS ? { aspectRatio: slotCS.aspectRatio, display: slotCS.display, placeItems: slotCS.placeItems, borderRadius: slotCS.borderRadius, overflow: slotCS.overflow, padding: slotCS.padding, alignItems: slotCS.alignItems, justifyContent: slotCS.justifyContent } : null,
        figure: figR, figureCS: figCS ? { margin: figCS.margin, width: figCS.width, display: figCS.display, alignItems: figCS.alignItems, justifyContent: figCS.justifyContent, marginTop: figCS.marginTop } : null,
        img: imgR, imgCS: imgCS ? { width: imgCS.width, height: imgCS.height, aspectRatio: imgCS.aspectRatio, objectFit: imgCS.objectFit, borderRadius: imgCS.borderRadius, display: imgCS.display } : null,
        // bleed check: how far the image sits inside the card edges
        bleed: (slotR && imgR && figR) ? {
          slotVsCard: { top: Math.round((slotR.y - cr.y) * 10) / 10, left: Math.round((slotR.x - cr.x) * 10) / 10, rightGap: Math.round((cr.x + cr.w - slotR.x - slotR.w) * 10) / 10 },
          figVsSlot: { top: Math.round((figR.y - slotR.y) * 10) / 10, left: Math.round((figR.x - slotR.x) * 10) / 10, rightGap: Math.round((slotR.x + slotR.w - figR.x - figR.w) * 10) / 10 },
          imgVsSlot: { top: Math.round((imgR.y - slotR.y) * 10) / 10, left: Math.round((imgR.x - slotR.x) * 10) / 10, rightGap: Math.round((slotR.x + slotR.w - imgR.x - imgR.w) * 10) / 10, bottomGap: Math.round((slotR.y + slotR.h - imgR.y - imgR.h) * 10) / 10 },
        } : null,
        content: contentR, contentCS: contentCS ? { padding: contentCS.padding } : null,
        contentKids: kidInfo,
        contentGaps: gaps,
        slotBottomToFirstText: (slotR && kidInfo.length) ? Math.round((kidInfo[0].y - (slotR.y + slotR.h)) * 10) / 10 : null,
      };
    });

    const btnCS = buttons ? getComputedStyle(buttons) : null;
    const btnR = buttons ? R(buttons) : null;
    const lastCardBottom = cards.length ? Math.max(...cards.map(c => c.card.y + c.card.h)) : null;
    const columnsR = columns ? R(columns) : null;

    return {
      viewport: { w: window.innerWidth, h: window.innerHeight },
      section: { rect: secR, padding: secCS.padding, bg: secCS.backgroundColor },
      eyebrow: eyebrow ? R(eyebrow) : null,
      h2: h2 ? { rect: R(h2), fontSize: getComputedStyle(h2).fontSize, marginTop: getComputedStyle(h2).marginTop, marginBottom: getComputedStyle(h2).marginBottom } : null,
      sub: sub ? { rect: R(sub), text: sub.textContent.trim().slice(0, 50) } : null,
      columns: { rect: columnsR, marginTop: columns ? getComputedStyle(columns).marginTop : null, gap: columns ? getComputedStyle(columns).gap : null },
      cards,
      buttons: { rect: btnR, marginTop: btnCS ? btnCS.marginTop : null, marginBlockStart: btnCS ? btnCS.marginBlockStart : null },
      // 一屏容纳性
      fit: {
        spanFromSectionTopToButtonBottom: (secR && btnR) ? Math.round((btnR.y + btnR.h - secR.y) * 10) / 10 : null,
        spanFromH2TopToButtonBottom: (h2 && btnR) ? Math.round((btnR.y + btnR.h - (h2.getBoundingClientRect().top + window.scrollY)) * 10) / 10 : null,
        viewportH: window.innerHeight,
        lastCardBottomToButtonTop: (lastCardBottom && btnR) ? Math.round((btnR.y - lastCardBottom) * 10) / 10 : null,
      },
    };
  });

  console.log(JSON.stringify(data, null, 2));
  require('fs').writeFileSync(OUT + '/scan-' + vw + '.json', JSON.stringify(data, null, 2));
  await b.close();
  console.log('\nJSON -> screenshots/blog-cards/scan-' + vw + '.json');
})().catch(e => { console.error('FATAL', e.message); process.exit(1); });

/**
 * o1_oem_scan.js — 全站 OEM/ODM 服务板块扫描
 * 1440px 下逐页找出含 OEM / ODM / Cooperation / Partnership / Engagement 的区块，
 * 报告位置(第几屏)、高度、结构、模式卡数量与标题、卡片类名、是否等高、是否有图/图标/CTA。
 */
const { chromium } = require('playwright-core');
const EXEC = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';

const PAGES = [
  ['home', '/'],
  ['about', '/about/'],
  ['quality', '/quality/'],
  ['factory-tour', '/factory-tour/'],
  ['products', '/products/'],
  ['services', '/services/'],
  ['cooperation', '/cooperation/'],
  ['blog', '/blog/'],
  ['contact', '/contact/'],
  ['faq', '/faq/'],
  ['soft-chews', '/products/soft-chews/'],
  ['tablets', '/products/tablets/'],
  ['powders', '/products/powders/'],
  ['pastes', '/products/pastes/'],
  ['drops', '/products/drops/'],
  ['liquids', '/products/liquids/'],
  ['fish-oil', '/products/fish-oil/'],
  ['dental-chews', '/products/dental-chews/'],
  ['privacy', '/privacy-policy/'],
  ['cookie', '/cookie-policy/'],
  ['terms', '/terms/'],
  ['single', '/test-article/'],
  ['search', '/?s=oem'],
];

(async () => {
  const b = await chromium.launch({ executablePath: EXEC, headless: true });
  const ctx = await b.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });
  const p = await ctx.newPage();
  const out = {};

  for (const [slug, url] of PAGES) {
    try {
      await p.goto('http://sinofresh.local' + url, { waitUntil: 'networkidle', timeout: 45000 });
      await p.evaluate(async () => { if (document.fonts) await document.fonts.ready; });
      const r = await p.evaluate(() => {
        const px = (v) => Math.round(parseFloat(v) || 0);
        const sections = [...document.querySelectorAll('.wp-site-blocks > .wp-block-group, main > .wp-block-group, body > .wp-block-group')];
        const VH = window.innerHeight;
        const rows = [];
        sections.forEach((el, i) => {
          const txt = (el.textContent || '');
          if (!/OEM|ODM|Cooperation Model|Partnership|Engagement type/i.test(txt)) return;
          const rect = el.getBoundingClientRect();
          const top = Math.round(rect.top + window.scrollY);
          const h2 = [...el.querySelectorAll(':scope > h2, :scope > * > h2')].map((x) => x.textContent.trim());
          const eyebrow = [...el.querySelectorAll(':scope > .sf-eyebrow, :scope > * > .sf-eyebrow')].map((x) => x.textContent.trim());
          // 模式卡：列内 group（或直接 group）
          const cols = [...el.querySelectorAll('.wp-block-columns > .wp-block-column')];
          const cards = cols.map((c) => {
            const g = c.querySelector(':scope > .wp-block-group') || c.firstElementChild;
            if (!g) return null;
            const gr = g.getBoundingClientRect();
            const cr = c.getBoundingClientRect();
            const h3 = g.querySelector('h3');
            const img = g.querySelector('img');
            const a = g.querySelector('a');
            return {
              title: h3 ? h3.textContent.trim() : null,
              cls: (g.getAttribute('class') || '').replace(/\s+/g, ' ').trim().slice(0, 100),
              colCls: (c.getAttribute('class') || '').replace(/\s+/g, ' ').trim().slice(0, 90),
              w: Math.round(cr.width), colH: Math.round(cr.height),
              cardH: Math.round(gr.height),
              padTop: px(getComputedStyle(g).paddingTop), padLeft: px(getComputedStyle(g).paddingLeft),
              radius: getComputedStyle(g).borderRadius,
              bg: getComputedStyle(g).backgroundColor,
              hasImg: !!img, hasLink: !!a,
              hasIcon: !!g.querySelector('svg,[class*="icon"],.sf-ico'),
              ps: [...g.querySelectorAll(':scope > p')].length,
              pH: [...g.querySelectorAll(':scope > p')].map((x) => Math.round(x.getBoundingClientRect().height)),
              shadow: getComputedStyle(g).boxShadow.slice(0, 60),
              border: getComputedStyle(g).borderTopWidth + ' ' + getComputedStyle(g).borderTopStyle,
            };
          }).filter(Boolean);
          const btns = [...el.querySelectorAll('.wp-block-button a')].map((x) => x.textContent.trim());
          const imgs = [...el.querySelectorAll(':scope img, :scope * img')].length;
          rows.push({
            idx: i, top, h: Math.round(rect.height),
            vp: +(top / VH).toFixed(2),
            h2, eyebrow,
            cls: (el.getAttribute('class') || '').replace(/\s+/g, ' ').trim().slice(0, 130),
            colsCount: el.querySelectorAll('.wp-block-columns').length,
            cardCount: cards.length, cards: cards.slice(0, 8),
            btns, imgs,
            sectionPad: px(getComputedStyle(el).paddingTop) + '/' + px(getComputedStyle(el).paddingLeft),
          });
        });
        return { url: location.pathname, docH: document.documentElement.scrollHeight, vh: VH, rows };
      });
      out[slug] = r;
      console.error('done ' + slug + ' (' + r.rows.length + ')');
    } catch (e) {
      out[slug] = { error: String(e).slice(0, 120) };
      console.error('ERR ' + slug + ' ' + String(e).slice(0, 80));
    }
  }
  await b.close();
  console.log(JSON.stringify(out, null, 1));
})().catch((e) => { console.error(e); process.exit(1); });

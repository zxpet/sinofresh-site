/* 批次 1（修订版）扫描 —— 桌面 1440 实测
   输出：Hero 详情 / 逐区块 top+height / 配方数 / FAQ 数 / tile 数 / 全页 id 清单
   Usage: node tools/_b1r_scan.js  -> /tmp/b1s/scan.json
   只读，不改任何文件。 */
const fs = require('fs');
const pw = require('/Users/meng/.workbuddy/binaries/node/workspace/node_modules/playwright-core');
const CHROME = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';

const SLUGS = ['soft-chews', 'tablets', 'powders', 'pastes', 'drops', 'liquids', 'fish-oil', 'dental-chews'];
const OUT = '/tmp/b1s';
fs.mkdirSync(OUT, { recursive: true });

async function accept(p) {
  const r = p.locator('button:has-text("Reject Non-Essential")');
  if (await r.count()) await r.first().click({ force: true }).catch(() => {});
}

/* 诚实量法：先整页预滚动逼出全部懒加载图片，再等所有 img complete。
   否则首访问页的 below-the-fold 图片未加载 → 高度塌陷，产生假差异
   （实测 soft-chews 首访 related tile 140px vs 等图后 350px）。 */
async function warmImages(page) {
  await page.evaluate(async () => {
    const H = document.documentElement.scrollHeight;
    for (let y = 0; y < H + 900; y += 600) {
      scrollTo(0, y);
      await new Promise((r) => setTimeout(r, 70));
    }
    scrollTo(0, 0);
  });
  await page.waitForTimeout(300);
  await page.evaluate(() => Promise.all(Array.from(document.images).map((i) => (i.complete ? 0 : new Promise((r) => { i.onload = i.onerror = r; setTimeout(r, 2000); })))));
  await page.waitForTimeout(250);
  await page.evaluate(() => scrollTo(0, 0));
  await page.waitForTimeout(250);
}

function probe() {
  const R = (el) => {
    if (!el) return null;
    const r = el.getBoundingClientRect();
    return { top: Math.round(r.top + scrollY), h: Math.round(r.height), w: Math.round(r.width) };
  };
  const q = (s) => document.querySelector(s);

  /* ---- Hero ---- */
  const hero = q('.sf-hero-inner');
  const h1 = hero && hero.querySelector('h1');
  const ps = hero ? Array.from(hero.querySelectorAll(':scope .wp-block-column:first-child > p')) : [];
  const btns = hero ? Array.from(hero.querySelectorAll('a.wp-block-button__link')).map((a) => ({
    text: a.textContent.trim(), href: a.getAttribute('href'),
    cls: String(a.getAttribute('class') || '').replace('wp-block-button__link', '').trim(),
    h: Math.round(a.getBoundingClientRect().height),
  })) : [];
  const slides = hero ? hero.querySelectorAll('.sf-pslider__slide') : [];
  const slideImgs = hero ? Array.from(hero.querySelectorAll('.sf-pslider__slide img')).map((i) => ({
    src: i.getAttribute('src'), alt: i.getAttribute('alt'), w: i.getAttribute('width'), h: i.getAttribute('height'),
    loading: i.getAttribute('loading'),
  })) : [];
  const sliderBox = R(hero && hero.querySelector('.sf-pslider'));
  const heroCols = hero ? Array.from(hero.querySelectorAll(':scope > .wp-block-columns > .wp-block-column')).map((c) => R(c)) : [];

  /* ---- 逐区块 ---- */
  const secs = Array.from(document.querySelectorAll('.wp-site-blocks > .wp-block-group, .wp-site-blocks > section')).map((s) => {
    const inner = s.querySelector('h2, h3');
    return {
      id: s.id || null,
      cls: String(s.getAttribute('class') || '').replace('wp-block-group', '').trim().slice(0, 60),
      top: Math.round(s.getBoundingClientRect().top + scrollY),
      h: Math.round(s.getBoundingClientRect().height),
      bg: getComputedStyle(s).backgroundColor,
      firstHeading: inner ? inner.textContent.trim().slice(0, 48) : null,
    };
  });

  /* ---- 组件计数 ---- */
  const count = (s) => document.querySelectorAll(s).length;
  const formulaItems = Array.from(document.querySelectorAll('.sf-formula__item')).map((d) => ({
    name: (d.querySelector('.sf-formula__name') || {}).textContent,
    use: (d.querySelector('.sf-formula__use') || {}).textContent,
    labels: Array.from(d.querySelectorAll('.sf-formula__label')).map((l) => l.textContent.trim()),
    open: d.open,
  }));

  return {
    url: location.pathname,
    docHeight: document.documentElement.scrollHeight,
    hero: {
      h: hero ? Math.round(hero.getBoundingClientRect().height) : null,
      top: hero ? Math.round(hero.getBoundingClientRect().top + scrollY) : null,
      h1: h1 ? h1.textContent.trim() : null,
      h1Size: h1 ? getComputedStyle(h1).fontSize : null,
      subtitle: ps[0] ? ps[0].textContent.trim() : null,
      compliance: ps[1] ? ps[1].textContent.trim() : null,
      paraCount: ps.length,
      buttons: btns,
      slideCount: slides.length,
      slideImgs,
      sliderBox,
      cols: heroCols,
      bg: hero ? getComputedStyle(hero).backgroundColor : null,
      padTop: hero ? getComputedStyle(hero).paddingTop : null,
      padBottom: hero ? getComputedStyle(hero).paddingBottom : null,
    },
    sections: secs,
    counts: {
      formulaItems: count('.sf-formula__item'),
      faqItems: count('.sf-faq__item'),
      relatedTiles: count('.sf-related-grid .sf-tile'),
      relatedGridBlocks: document.querySelectorAll('.sf-related-grid').length,
      relatedGridColumns: Array.from(document.querySelectorAll('.sf-related-grid')).map((g) => g.querySelectorAll(':scope > .wp-block-column').length),
      dosageGridBlocks: document.querySelectorAll('.sf-dosage-grid').length,
      dosageTiles: count('.sf-dosage-grid .sf-tile'),
      exploreChips: count('.sf-explore__chip'),
      configGroups: count('.configurator__group'),
      howWeWorkSteps: count('.sf-steps, .wp-block-columns .wp-block-column h3'),
    },
    formulas: formulaItems,
    ids: Array.from(document.querySelectorAll('[id]')).map((e) => ({ id: e.id, tag: e.tagName })),
    scrollMargins: ['#inquiry-form', '#formulas', '#configurator'].map((s) => {
      const el = document.querySelector(s);
      return { sel: s, exists: !!el, smt: el ? getComputedStyle(el).scrollMarginTop : null };
    }),
    htmlScrollPadding: getComputedStyle(document.documentElement).scrollPaddingTop,
    foldPresent: !!document.querySelector('.configurator__fold'),
    foldOpen: (() => { const f = document.querySelector('.configurator__fold'); return f ? f.open : null; })(),
  };
}

(async () => {
  const browser = await pw.chromium.launch({ executablePath: CHROME, headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  const result = {};
  for (const s of SLUGS) {
    await page.goto(`http://sinofresh.local/products/${s}/`, { waitUntil: 'load', timeout: 45000 });
    await accept(page);
    await page.waitForTimeout(300);
    await warmImages(page);
    result[s] = await page.evaluate(probe);
    console.log(`  ${s}: hero=${result[s].hero.h}px doc=${result[s].docHeight}px secs=${result[s].sections.length} formulas=${result[s].counts.formulaItems} faq=${result[s].counts.faqItems} tiles=${result[s].counts.relatedTiles}`);
  }
  await browser.close();
  fs.writeFileSync(`${OUT}/scan.json`, JSON.stringify(result, null, 2));
  console.log('OK -> ' + OUT + '/scan.json');
})();

/* 批次 1 扫描 —— 渲染几何测量（只读，不改站点）
 * 8 剂型页桌面 1440：section 序、各 section 高度、配置器/Formulas 关键高度
 * liquids 页移动 375：同项 + 底部 bar / drawer 状态
 * 输出：/tmp/b1/geometry.json
 */
const fs = require('fs');
const pw = require('/Users/meng/.workbuddy/binaries/node/workspace/node_modules/playwright-core');
const CHROME = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';

const PAGES = ['soft-chews','tablets','powders','pastes','drops','liquids','fish-oil','dental-chews']
  .map(s => `/products/${s}/`);

async function acceptCookies(page) {
  const reject = page.locator('button:has-text("Reject Non-Essential")');
  if (await reject.count()) await reject.first().click({ force: true }).catch(() => {});
}

async function measure(page, url) {
  await page.goto('http://sinofresh.local' + url, { waitUntil: 'load', timeout: 45000 });
  await acceptCookies(page);
  await page.evaluate(async () => {
    const s = Math.round(innerHeight * 0.8);
    for (let y = 0; y < document.body.scrollHeight; y += s) { scrollTo(0, y); await new Promise(r => setTimeout(r, 60)); }
    scrollTo(0, 0); await new Promise(r => setTimeout(r, 150));
  });
  const landedUrl = page.url();
  return await page.evaluate((curUrl) => {
    const out = { url: curUrl, hasMain: !!document.querySelector('main'), mainTag: null, sections: [], cfg: {}, fm: {}, hero: {}, anchors: {} };
    const m = document.querySelector('main');
    if (m) out.mainTag = m.tagName + '.' + (m.className || '');
    // 顶层区块：所有非 header/footer 内的 section
    Array.from(document.querySelectorAll('section')).filter(el => !el.closest('header,footer')).forEach((el, i) => {
      const r = el.getBoundingClientRect();
      out.sections.push({
        idx: i + 1,
        id: el.id || '',
        cls: (el.className || '').split(' ').filter(c => !c.startsWith('is-layout') && !c.endsWith('is-layout-constrained')).join(' '),
        top: Math.round(r.top + scrollY),
        h: Math.round(r.height),
      });
    });
    const c = document.querySelector('.configurator');
    if (c) {
      const r = c.getBoundingClientRect();
      const oEl = c.querySelector('.configurator__options');
      const sEl = c.querySelector('.configurator__summary-col');
      const sIn = c.querySelector('.configurator__summary');
      out.cfg = {
        h: Math.round(r.height),
        optionsH: oEl ? Math.round(oEl.getBoundingClientRect().height) : -1,
        summaryColH: sEl ? Math.round(sEl.getBoundingClientRect().height) : -1,
        summaryH: sIn ? Math.round(sIn.getBoundingClientRect().height) : -1,
        groups: c.querySelectorAll('.configurator__group').length,
        items: c.querySelectorAll('.configurator__item').length,
        barDisplay: document.querySelector('.configurator__bar') ? getComputedStyle(document.querySelector('.configurator__bar')).display : 'n/a',
        mobilebarDisplay: document.querySelector('.configurator__mobilebar') ? getComputedStyle(document.querySelector('.configurator__mobilebar')).display : 'n/a',
        drawerHidden: document.getElementById('configurator-drawer') ? document.getElementById('configurator-drawer').hidden : null,
        summarySticky: sIn ? getComputedStyle(sIn).position : 'n/a',
      };
    }
    const fs2 = document.querySelector('.sf-formulas');
    if (fs2) {
      const r = fs2.getBoundingClientRect();
      const d = fs2.querySelector('details');
      const open = fs2.querySelector('details[open]');
      out.fm = {
        h: Math.round(r.height),
        details: fs2.querySelectorAll('details').length,
        anyOpen: !!open,
        firstSummaryH: d ? Math.round(d.querySelector('summary').getBoundingClientRect().height) : 0,
        firstDetailH: d ? Math.round(d.getBoundingClientRect().height) : 0,
      };
    }
    const h1 = document.querySelector('.sf-hero-inner h1') || document.querySelector('h1');
    if (h1) {
      const hs = document.querySelector('.sf-hero-inner');
      out.hero = {
        h: hs ? Math.round(hs.getBoundingClientRect().height) : 0,
        h1: h1.textContent.trim(),
        buttons: Array.from(document.querySelectorAll('.sf-hero-inner a.wp-block-button__link')).map(a => ({
          text: a.textContent.trim(), href: a.getAttribute('href'), cls: a.className.replace(/wp-block-button__link|has-text-color|has-background|wp-element-button|has-.*-color/g, '').trim(),
        })),
        sliderSlides: document.querySelectorAll('.sf-hero-inner .sf-pslider__slide').length,
      };
    }
    ['#inquiry-form', '#configurator', '.sf-formulas', '.sf-hero-inner'].forEach(sel => {
      const el = document.querySelector(sel);
      if (el) out.anchors[sel] = { id: el.id || '', scrollMarginTop: getComputedStyle(el).scrollMarginTop, top: Math.round(el.getBoundingClientRect().top + scrollY) };
    });
    out.htmlScrollPaddingTop = getComputedStyle(document.documentElement).scrollPaddingTop;
    const hd = document.querySelector('.sf-header');
    out.headerH = hd ? Math.round(hd.getBoundingClientRect().height) : 0;
    out.docH = document.body.scrollHeight;
    return out;
  }, landedUrl);
}

(async () => {
  fs.mkdirSync('/tmp/b1', { recursive: true });
  const browser = await pw.chromium.launch({ executablePath: CHROME, headless: true });
  const res = { desktop: {}, mobile: {} };

  const ctxD = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const pd = await ctxD.newPage();
  for (const u of PAGES) {
    try { res.desktop[u] = await measure(pd, u); }
    catch (e) { res.desktop[u] = { error: String(e).slice(0, 200) }; }
  }
  await ctxD.close();

  const ctxM = await browser.newContext({ viewport: { width: 375, height: 812 }, isMobile: true, hasTouch: true });
  const pm = await ctxM.newPage();
  for (const u of ['/products/liquids/', '/products/dental-chews/']) {
    try { res.mobile[u] = await measure(pm, u); }
    catch (e) { res.mobile[u] = { error: String(e).slice(0, 200) }; }
  }
  await ctxM.close();

  await browser.close();
  fs.writeFileSync('/tmp/b1/geometry.json', JSON.stringify(res, null, 1));
  console.log('OK -> /tmp/b1/geometry.json');
})();

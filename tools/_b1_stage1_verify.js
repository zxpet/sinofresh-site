/* 批次 1 / 阶段 1 核验 —— 8 剂型页
 * 桌面 1440 + 移动 375：Hero 三按钮 / 速览表 5 字段 / TOC sf-sec-N / 配置器几何
 * 输出：/tmp/b1/stage1.json
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
  const t0 = Date.now();
  const resp = await page.goto('http://sinofresh.local' + url, { waitUntil: 'load', timeout: 45000 });
  const status = resp ? resp.status() : 0;
  await acceptCookies(page);
  await page.evaluate(async () => {
    const s = Math.round(innerHeight * 0.8);
    for (let y = 0; y < document.body.scrollHeight; y += s) { scrollTo(0, y); await new Promise(r => setTimeout(r, 60)); }
    scrollTo(0, 0); await new Promise(r => setTimeout(r, 150));
  });
  const out = await page.evaluate(() => {
    const o = { status: 0, sections: [], hero: {}, table: {}, cfg: {}, toc: [], dead: [], errors: [] };
    o.bodyHTML = document.body.innerHTML;
    o.docH = document.body.scrollHeight;
    o.headerH = (document.querySelector('.sf-header') || {getBoundingClientRect:()=>({height:0})}).getBoundingClientRect().height | 0;

    Array.from(document.querySelectorAll('section')).filter(el => !el.closest('header,footer')).forEach((el, i) => {
      const r = el.getBoundingClientRect();
      o.sections.push({ idx: i + 1, id: el.id || '', cls: (el.className||'').split(' ').filter(c=>!c.startsWith('is-layout')&&!c.endsWith('is-layout-constrained')).join(' '), top: Math.round(r.top + scrollY), h: Math.round(r.height) });
    });

    const hero = document.querySelector('.sf-hero-inner');
    if (hero) {
      o.hero.h = Math.round(hero.getBoundingClientRect().height);
      o.hero.buttons = Array.from(hero.querySelectorAll('a.wp-block-button__link')).map(a => {
        const cs = getComputedStyle(a);
        const wrap = a.closest('.wp-block-button');
        return { text: a.textContent.trim(), href: a.getAttribute('href'), cls: (wrap.className||''),
                 bg: cs.backgroundColor, color: cs.color, border: cs.borderTopWidth + ' ' + cs.borderTopStyle,
                 deco: cs.textDecorationLine, display: cs.display,
                 box: (()=>{const r=a.getBoundingClientRect(); return Math.round(r.width)+'x'+Math.round(r.height);})() };
      });
      o.hero.rows = new Set(Array.from(hero.querySelectorAll('a.wp-block-button__link')).map(a => Math.round(a.getBoundingClientRect().top))).size;
    }

    const t = document.querySelector('.sf-spectable__table');
    if (t) {
      const cs = getComputedStyle(t);
      o.table = {
        found: true,
        caption: (t.querySelector('caption')||{}).textContent || '',
        heads: Array.from(t.querySelectorAll('thead th')).map(x => x.textContent.trim()),
        headBg: t.querySelector('thead th') ? getComputedStyle(t.querySelector('thead th')).backgroundColor : 'n/a',
        headColor: t.querySelector('thead th') ? getComputedStyle(t.querySelector('thead th')).color : 'n/a',
        rows: t.querySelectorAll('tbody tr').length,
        cells: Array.from(t.querySelectorAll('tbody td')).map(x => ({ label: x.getAttribute('data-label') || '', value: x.textContent.trim() })),
        display: cs.display,
        headDisplay: getComputedStyle(t.querySelector('thead')).display,
        h: Math.round(t.getBoundingClientRect().height),
        bandH: Math.round(document.querySelector('.sf-spectable').getBoundingClientRect().height),
      };
    } else { o.table = { found: false }; }

    const c = document.querySelector('.configurator');
    if (c) o.cfg = {
      h: Math.round(c.getBoundingClientRect().height),
      groups: c.querySelectorAll('.configurator__group').length,
      items: c.querySelectorAll('.configurator__item').length,
      barDisplay: getComputedStyle(document.querySelector('.configurator__bar')).display,
      drawerHidden: document.getElementById('configurator-drawer').hidden,
      summarySticky: getComputedStyle(document.querySelector('.configurator__summary')).position,
      mobilebarDisplay: getComputedStyle(document.querySelector('.configurator__mobilebar')).display,
      summaryVisible: getComputedStyle(document.querySelector('.configurator__summary')).display,
    };

    Array.from(document.querySelectorAll('h2')).forEach(h => {
      if (h.closest('.sf-lb, .sf-certmodal, dialog, template, [hidden]')) return;
      if (getComputedStyle(h).display === 'none') return;
      const txt = (h.textContent||'').replace(/\s+/g,' ').trim();
      if (!txt) return;
      o.toc.push({ id: h.id || '', cls: h.className, text: txt, smt: getComputedStyle(h).scrollMarginTop });
    });

    o.dead = Array.from(document.querySelectorAll('a[href="#"]')).map(a => a.textContent.trim());
    ['#formulas', '#configurator', '#inquiry-form'].forEach(sel => {
      const el = document.querySelector(sel);
      o['anchor' + sel] = el ? { id: el.id, smt: getComputedStyle(el).scrollMarginTop, top: Math.round(el.getBoundingClientRect().top + scrollY) } : null;
    });
    o.htmlScrollPaddingTop = getComputedStyle(document.documentElement).scrollPaddingTop;
    delete o.bodyHTML;
    return o;
  });
  out.status = status;
  out.ms = Date.now() - t0;
  const html = await page.content();
  const PAT = /Fatal error|Parse error|Warning:|Notice:|Deprecated:|critical error/i;
  const m = html.match(new RegExp(PAT.source, 'gi'));
  out.phpErrors = m ? m.slice(0, 5) : [];
  return out;
}

(async () => {
  fs.mkdirSync('/tmp/b1', { recursive: true });
  const browser = await pw.chromium.launch({ executablePath: CHROME, headless: true });
  const res = { desktop: {}, mobile: {} };
  const ctxD = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const pd = await ctxD.newPage();
  for (const u of PAGES) {
    try { res.desktop[u] = await measure(pd, u); } catch (e) { res.desktop[u] = { error: String(e).slice(0, 200) }; }
  }
  await ctxD.close();
  const ctxM = await browser.newContext({ viewport: { width: 375, height: 812 }, isMobile: true, hasTouch: true });
  const pm = await ctxM.newPage();
  for (const u of PAGES) {
    try { res.mobile[u] = await measure(pm, u); } catch (e) { res.mobile[u] = { error: String(e).slice(0, 200) }; }
  }
  await ctxM.close();
  await browser.close();
  fs.writeFileSync('/tmp/b1/stage1.json', JSON.stringify(res, null, 1));
  console.log('OK -> /tmp/b1/stage1.json');
})();

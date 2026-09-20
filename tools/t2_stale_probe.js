/* 任务2 陈旧副本探针
 * mode=net   : 加载多页，记录全部请求 URL 与状态码，交叉比对 15 个陈旧文件名
 * mode=shots : 首页 + 剂型页截图（1440 / 375）
 */
const fs = require('fs');
const path = require('path');
const pw = require('/Users/meng/.workbuddy/binaries/node/workspace/node_modules/playwright-core');
const CHROME = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';

const STALE = ['basket.js','configurator.css','configurator.js','footer.html','formulas.js',
  'front-page.html','header.html','hero-slider.js','page-dental-chews.html','page-drops.html',
  'page-fish-oil.html','page-liquids.html','page-soft-chews.html'];

const URLS = ['/', '/products/soft-chews/', '/products/dental-chews/', '/about/', '/quality/',
  '/blog/', '/contact/', '/factory-tour/', '/services/', '/products/'];

const mode = process.argv[2];
const outDir = process.argv[3];

async function acceptCookies(page) {
  const reject = page.locator('button:has-text("Reject Non-Essential")');
  if (await reject.count()) await reject.first().click({ force: true }).catch(() => {});
}

async function scrollAll(page) {
  await page.evaluate(async () => {
    const s = Math.round(innerHeight * 0.8);
    for (let y = 0; y < document.body.scrollHeight; y += s) { scrollTo(0, y); await new Promise(r => setTimeout(r, 80)); }
    scrollTo(0, 0);
  });
  await page.waitForTimeout(1000);
  await page.evaluate(() => document.fonts.ready);
}

(async () => {
  const b = await pw.chromium.launch({ executablePath: CHROME, headless: true });

  if (mode === 'net') {
    const ctx = await b.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await ctx.newPage();
    const all = new Map();      // url -> {status, type, pages:Set}
    const bad = [];             // 4xx/5xx 或 failed
    page.on('request', r => { if (!all.has(r.url())) all.set(r.url(), { status: '?', type: r.resourceType(), pages: new Set() }); });
    page.on('response', r => { const e = all.get(r.url()); if (e) { e.status = r.status(); if (r.status() >= 400) bad.push(`${r.status()} ${r.url()}`); } });
    page.on('requestfailed', r => { bad.push(`FAILED ${r.failure() && r.failure().errorText} ${r.url()}`); });

    const perPage = {};
    for (const u of URLS) {
      const seen = new Set();
      const onReq = r => { seen.add(r.url()); const e = all.get(r.url()); if (e) e.pages.add(u); };
      page.on('request', onReq);
      await page.goto('http://sinofresh.local' + u, { waitUntil: 'networkidle' });
      await acceptCookies(page);
      await scrollAll(page);
      await page.waitForTimeout(600);
      perPage[u] = seen;
      page.off('request', onReq);
    }

    const urls = [...all.keys()];
    console.log(`=== 采集 ${URLS.length} 页，共 ${urls.length} 个唯一请求 URL ===`);
    const hits = urls.filter(u => STALE.some(n => u.endsWith('/' + n)));
    console.log(`\n=== 15 个陈旧文件名的请求命中（应为 0） ===`);
    console.log(hits.length ? hits.map(h => '  HIT ' + h).join('\n') : '  命中 0 ✅（浏览器从未请求过这些文件）');
    console.log(`\n=== 非 2xx / failed 请求（应为 0） ===`);
    console.log(bad.length ? [...new Set(bad)].map(x => '  ' + x).join('\n') : '  0 ✅');
    console.log(`\n=== 根级请求（URL 路径段 <= 1 且非 /wp-* /assets/ /inc/ 的资源） ===`);
    const rootRes = urls.filter(u => {
      const p = new URL(u).pathname;
      return /^\/[A-Za-z0-9_.-]+\.(js|css|html)$/.test(p) && !/^\/(wp-|assets\/)/.test(p);
    });
    console.log(rootRes.length ? rootRes.map(x => '  ' + x).join('\n') : '  0 ✅');
    fs.writeFileSync('/tmp/t2_req_urls.txt', urls.join('\n'));
    console.log('\nDONE');
  }

  if (mode === 'shots') {
    fs.mkdirSync(outDir, { recursive: true });
    const targets = [
      { url: '/', tag: 'home', w: 1440, h: 900 },
      { url: '/products/soft-chews/', tag: 'soft-chews', w: 1440, h: 900 },
    ];
    for (const t of targets) {
      const ctx = await b.newContext({ viewport: { width: t.w, height: t.h } });
      const page = await ctx.newPage();
      await page.addInitScript(() => { try { localStorage.setItem('sf_cookie_consent', JSON.stringify({ necessary: true, analytics: false, marketing: false })); } catch (e) {} });
      await page.goto('http://sinofresh.local' + t.url, { waitUntil: 'networkidle' });
      await acceptCookies(page);
      await scrollAll(page);
      await page.addStyleTag({ content: 'header{position:static!important}' });
      await page.evaluate(() => scrollTo(0, 0));
      await page.waitForTimeout(500);
      await page.screenshot({ path: path.join(outDir, `${t.tag}-top-1440.png`) });
      await page.screenshot({ path: path.join(outDir, `${t.tag}-full-1440.png`), fullPage: true });
      console.log('shot:', t.tag);
      await ctx.close();
    }
    // 375
    for (const t of [{ url: '/products/soft-chews/', tag: 'soft-chews' }]) {
      const ctx = await b.newContext({ viewport: { width: 375, height: 812 } });
      const page = await ctx.newPage();
      await page.addInitScript(() => { try { localStorage.setItem('sf_cookie_consent', JSON.stringify({ necessary: true, analytics: false, marketing: false })); } catch (e) {} });
      await page.goto('http://sinofresh.local' + t.url, { waitUntil: 'networkidle' });
      await scrollAll(page);
      await page.screenshot({ path: path.join(outDir, `${t.tag}-top-375.png`) });
      console.log('shot:', t.tag, '375');
      await ctx.close();
    }
    console.log('DONE');
  }

  await b.close();
})();

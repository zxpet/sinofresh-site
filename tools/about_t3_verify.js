const path = require('path');
const fs = require('fs');
const pw = require('/Users/meng/.workbuddy/binaries/node/workspace/node_modules/playwright-core');
const CHROME = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';
const OUT = '/Users/meng/Workbuddy/sinofresh外贸网站建设/screenshots/about-t3';
const URL = 'http://sinofresh.local/about/';

const geometry = () => {
  const cover = document.querySelector('.sf-video-cover');
  const img = cover.querySelector('img');
  const btn = cover.querySelector('.sf-video__play');
  const cr = cover.getBoundingClientRect(), ir = img.getBoundingClientRect(), br = btn.getBoundingClientRect();
  const cs = getComputedStyle(cover);
  return {
    cover: { w: +cr.width.toFixed(1), h: +cr.height.toFixed(1), ratio: +(cr.width / cr.height).toFixed(3), padding: cs.padding, minHeight: cs.minHeight, display: cs.display },
    poster: { w: +ir.width.toFixed(1), h: +ir.height.toFixed(1), natW: img.naturalWidth, natH: img.naturalHeight, fit: getComputedStyle(img).objectFit, loading: img.getAttribute('loading'), fp: img.getAttribute('fetchpriority'), complete: img.complete, fills: Math.abs(ir.width - cr.width) < 1.5 && Math.abs(ir.height - cr.height) < 1.5 },
    button: { w: +br.width.toFixed(1), h: +br.height.toFixed(1), type: btn.type, label: btn.getAttribute('aria-label'), id: btn.dataset.videoId },
    iframes: document.querySelectorAll('.sf-video-iframe, iframe').length,
    playing: cover.classList.contains('is-playing')
  };
};

(async () => {
  const b = await pw.chromium.launch({ executablePath: CHROME, headless: true });
  fs.mkdirSync(OUT, { recursive: true });
  const report = {};

  for (const w of [1440, 375]) {
    const ctx = await b.newContext({ viewport: { width: w, height: 900 } });
    const page = await ctx.newPage();
    const yt = [];
    const warnings = [];
    page.on('request', (r) => { if (/youtube|ytimg|googlevideo|doubleclick|gstatic/.test(r.url())) yt.push(r.url().slice(0, 80)); });
    page.on('console', (m) => { if (m.type() === 'warning') warnings.push(m.text().slice(0, 120)); });
    await page.addInitScript(() => {
      window.__lcp = [];
      window.__cls = 0;
      new PerformanceObserver((l) => { for (const e of l.getEntries()) window.__lcp.push({ t: Math.round(e.startTime), size: e.size, tag: e.element ? e.element.tagName + '.' + (e.element.className || '').split(' ')[0] : '?' }); }).observe({ type: 'largest-contentful-paint', buffered: true });
      new PerformanceObserver((l) => { for (const e of l.getEntries()) if (!e.hadRecentInput) window.__cls += e.value; }).observe({ type: 'layout-shift', buffered: true });
    });
    await page.goto(URL, { waitUntil: 'load' });
    await page.waitForTimeout(1500);

    const before = await page.evaluate(geometry);
    const perf = await page.evaluate(() => ({ lcp: window.__lcp.slice(-2), cls: +window.__cls.toFixed(4) }));
    const ytBefore = yt.length;

    // 关闭 cookie 横幅后截图（海报态 / hover 态）
    const rej = page.locator('button:has-text("Reject Non-Essential")');
    if (await rej.count()) await rej.first().click({ force: true }).catch(() => {});
    await page.locator('.sf-video-cover').scrollIntoViewIfNeeded();
    await page.waitForTimeout(400);
    await page.locator('.sf-video-cover').screenshot({ path: path.join(OUT, `video_poster_${w}.png`), animations: 'disabled' });
    await page.locator('.sf-video__play').hover();
    await page.waitForTimeout(400);
    await page.locator('.sf-video-cover').screenshot({ path: path.join(OUT, `video_hover_${w}.png`) });

    // 1) 占位 ID：点击不应产生 iframe
    await page.locator('.sf-video__play').click();
    await page.waitForTimeout(500);
    const placeholderClick = await page.evaluate(() => ({ iframes: document.querySelectorAll('iframe').length, playing: document.querySelector('.sf-video-cover').classList.contains('is-playing') }));
    const ytAfterPlaceholder = yt.length;

    // 2) 真实 ID（测试用）：点击应原地替换
    const boxBefore = await page.evaluate(() => { const r = document.querySelector('.sf-video-cover').getBoundingClientRect(); return { t: +r.top.toFixed(1), w: +r.width.toFixed(1), h: +r.height.toFixed(1) }; });
    await page.evaluate(() => { document.querySelector('.sf-video__play').dataset.videoId = 'dqT-UlYlg1s'; });
    await page.locator('.sf-video__play').click();
    await page.waitForTimeout(1200);
    const afterClick = await page.evaluate(() => {
      const cover = document.querySelector('.sf-video-cover');
      const f = cover.querySelector('iframe');
      const r = cover.getBoundingClientRect();
      return {
        coverMoved: { t: +r.top.toFixed(1), w: +r.width.toFixed(1), h: +r.height.toFixed(1) },
        iframe: f ? { src: f.src, title: f.title, allow: f.getAttribute('allow'), fs: f.hasAttribute('allowfullscreen'), w: Math.round(f.getBoundingClientRect().width), h: Math.round(f.getBoundingClientRect().height) } : null,
        played: cover.classList.contains('is-playing'),
        posterVisible: getComputedStyle(cover.querySelector('.wp-block-image')).display,
        btnVisible: getComputedStyle(cover.querySelector('.sf-video__play')).display,
        cls: +window.__cls.toFixed(4)
      };
    });
    await page.locator('.sf-video-cover').screenshot({ path: path.join(OUT, `video_playing_${w}.png`) });

    // 3) 键盘可达性（新开页面，用 Enter 触发）
    const page2 = await ctx.newPage();
    await page2.goto(URL, { waitUntil: 'load' });
    await page2.evaluate(() => { document.querySelector('.sf-video__play').dataset.videoId = 'dqT-UlYlg1s'; });
    await page2.locator('.sf-video__play').focus();
    const focusedTag = await page2.evaluate(() => document.activeElement.className);
    await page2.keyboard.press('Enter');
    await page2.waitForTimeout(900);
    const keyboard = await page2.evaluate(() => ({ iframes: document.querySelectorAll('iframe').length, playing: document.querySelector('.sf-video-cover').classList.contains('is-playing') }));

    report[w] = { before, perf, ytRequestsBeforeClick: ytBefore, placeholderClick, ytAfterPlaceholder, boxBefore, afterClick, keyboard: { focusedTag, ...keyboard }, warnings: warnings.slice(0, 2) };
    await ctx.close();
  }
  await b.close();
  fs.writeFileSync('/Users/meng/Workbuddy/sinofresh外贸网站建设/tools/_about_t3.json', JSON.stringify(report, null, 1));
  console.log(JSON.stringify(report, null, 1));
})();

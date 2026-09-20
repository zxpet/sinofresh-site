/* 批次 1 扫描 —— TOC / 锚点机制探针（只读）
 * 检查剂型页 toc-nav.js 是否生成 TOC、是否动态给 H2 加 id 与 scroll-margin-top
 * 输出：控制台 + /tmp/b1/toc.json
 */
const fs = require('fs');
const pw = require('/Users/meng/.workbuddy/binaries/node/workspace/node_modules/playwright-core');
const CHROME = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';

(async () => {
  fs.mkdirSync('/tmp/b1', { recursive: true });
  const browser = await pw.chromium.launch({ executablePath: CHROME, headless: true });
  const out = {};
  for (const [label, url, vp] of [
    ['desktop', 'http://sinofresh.local/products/liquids/', { width: 1440, height: 900 }],
    ['mobile', 'http://sinofresh.local/products/liquids/', { width: 375, height: 812 }],
  ]) {
    const ctx = await browser.newContext({ viewport: vp, isMobile: label === 'mobile', hasTouch: label === 'mobile' });
    const page = await ctx.newPage();
    await page.goto(url, { waitUntil: 'load', timeout: 45000 });
    const r = page.locator('button:has-text("Reject Non-Essential")');
    if (await r.count()) await r.first().click({ force: true }).catch(() => {});
    await page.waitForTimeout(1200);
    out[label] = await page.evaluate(() => {
      const toc = document.querySelector('.sf-toc');
      const h2s = Array.from(document.querySelectorAll('h2')).map(h => ({
        text: h.textContent.trim().slice(0, 46),
        id: h.id || '',
        cls: h.className,
        scrollMarginTop: getComputedStyle(h).scrollMarginTop,
        parentId: (h.closest('section') || {}).id || '',
        parentMargin: h.closest('section') ? getComputedStyle(h.closest('section')).scrollMarginTop : '',
      }));
      const tocLinks = toc ? Array.from(toc.querySelectorAll('a')).map(a => ({ href: a.getAttribute('href'), text: (a.getAttribute('aria-label') || a.textContent || '').trim().slice(0, 40), cls: a.className })) : [];
      return {
        tocExists: !!toc,
        tocDisplay: toc ? getComputedStyle(toc).display : 'n/a',
        tocLinks,
        h2s,
        tocTargets: Array.from(document.querySelectorAll('.sf-toc-target')).map(e => ({ tag: e.tagName, id: e.id, cls: e.className.slice(0, 80), smt: getComputedStyle(e).scrollMarginTop })),
        heroButtons: Array.from(document.querySelectorAll('.sf-hero-inner a.wp-block-button__link')).map(a => ({ text: a.textContent.trim(), href: a.getAttribute('href'), cls: a.className })),
        headerH: document.querySelector('.sf-header') ? Math.round(document.querySelector('.sf-header').getBoundingClientRect().height) : 0,
      };
    });
    await ctx.close();
  }
  await browser.close();
  fs.writeFileSync('/tmp/b1/toc.json', JSON.stringify(out, null, 1));
  console.log(JSON.stringify(out, null, 1));
})();

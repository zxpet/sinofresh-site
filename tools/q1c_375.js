const { chromium } = require('playwright-core');
const EXEC = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';
const PAGES = ['/quality/', '/', '/services/', '/products/soft-chews/'];
(async () => {
  const b = await chromium.launch({ executablePath: EXEC, headless: true });
  const ctx = await b.newContext({ viewport: { width: 375, height: 812 }, deviceScaleFactor: 2 });
  const p = await ctx.newPage();
  for (const u of PAGES) {
    await p.goto('http://sinofresh.local' + u, { waitUntil: 'networkidle', timeout: 45000 });
    await p.evaluate(async () => { if (document.fonts) await document.fonts.ready; });
    const r = await p.evaluate(() => {
      const f = document.querySelector('.sf-faq');
      const doc = document.documentElement;
      const over = [];
      document.querySelectorAll('body *').forEach(el => {
        const rc = el.getBoundingClientRect();
        if (rc.width > 0 && (rc.right > window.innerWidth + 1 || rc.left < -1)) {
          const cls = (el.className || '').toString().slice(0, 40);
          over.push((el.tagName || '').toLowerCase() + '.' + cls + ' L' + Math.round(rc.left) + ' R' + Math.round(rc.right));
        }
      });
      const cert = document.querySelector('.sf-certrow');
      const certMedia = document.querySelector('.sf-certrow__media');
      const img = document.querySelector('.sf-certrow__media img');
      return {
        url: location.pathname,
        faqW: f ? Math.round(f.getBoundingClientRect().width) : null,
        docW: doc.scrollWidth, winW: window.innerWidth,
        hasHOverflow: doc.scrollWidth > window.innerWidth,
        overCount: over.length, over: over.slice(0, 6),
        certRowH: cert ? Math.round(cert.getBoundingClientRect().height) : null,
        certMediaW: certMedia ? Math.round(certMedia.getBoundingClientRect().width) : null,
        certImgRendered: img ? Math.round(img.getBoundingClientRect().width) + 'x' + Math.round(img.getBoundingClientRect().height) : null,
        docH: doc.scrollHeight
      };
    });
    console.log(JSON.stringify(r));
  }
  await b.close();
})().catch(e => { console.error(e); process.exit(1); });

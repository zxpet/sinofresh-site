/* 任务1 证书灯箱功能验证：/quality/ 与 /about/，打开后实测 z-index 必须仍是 99999 */
const pw = require('/Users/meng/.workbuddy/binaries/node/workspace/node_modules/playwright-core');
const CHROME = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';

const PAGES = [
  { url: '/quality/', sel: '.sf-certrow__media a' },
  { url: '/about/', sel: '.sf-fac a, .sf-fac img' },
];

(async () => {
  const br = await pw.chromium.launch({ executablePath: CHROME, headless: true });
  for (const t of PAGES) {
    const ctx = await br.newContext({ viewport: { width: 1440, height: 900 } });
    const p = await ctx.newPage();
    const errs = [];
    p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
    p.on('pageerror', e => errs.push('pageerror: ' + e.message));
    await p.addInitScript(() => { try { localStorage.setItem('sf_cookie_consent', JSON.stringify({ necessary: true, analytics: false, marketing: false })); } catch (e) {} });
    await p.goto('http://sinofresh.local' + t.url, { waitUntil: 'networkidle' });
    await p.evaluate(async () => { for (let y = 0; y < document.body.scrollHeight; y += 700) { scrollTo(0, y); await new Promise(r => setTimeout(r, 70)); } });
    await p.waitForTimeout(800);

    const triggers = await p.locator(t.sel).count();
    let out = { triggerCount: triggers };
    if (triggers) {
      await p.locator(t.sel).first().scrollIntoViewIfNeeded();
      await p.waitForTimeout(300);
      await p.locator(t.sel).first().click({ force: true }).catch(e => { out.clickErr = e.message; });
      await p.waitForTimeout(900);
      out.after = await p.evaluate(() => {
        const nodes = [...document.querySelectorAll('body *')];
        const vis = nodes.filter(e => {
          const s = getComputedStyle(e); const r = e.getBoundingClientRect();
          const z = parseInt(s.zIndex, 10);
          return s.position === 'fixed' && r.width > innerWidth * 0.5 && r.height > innerHeight * 0.5 && (isNaN(z) ? false : z >= 1000);
        }).map(e => ({
          cls: (e.className && e.className.toString().slice(0, 40)) || e.tagName,
          z: getComputedStyle(e).zIndex,
          opacity: getComputedStyle(e).opacity,
          display: getComputedStyle(e).display,
          visible: e.getBoundingClientRect().width > 0 && getComputedStyle(e).opacity !== '0',
          bodyClass: document.body.className.slice(0, 60),
        }));
        const lb = document.querySelector('.sf-lb');
        return {
          overlays: vis,
          lbExists: !!lb,
          lbZ: lb ? getComputedStyle(lb).zIndex : null,
          lbOpacity: lb ? getComputedStyle(lb).opacity : null,
        };
      });
      await p.keyboard.press('Escape');
      await p.waitForTimeout(500);
      out.afterEsc = await p.evaluate(() => {
        const lb = document.querySelector('.sf-lb');
        return { lbOpacity: lb ? getComputedStyle(lb).opacity : null, bodyClass: document.body.className.slice(0, 40) };
      });
    }
    out.consoleErrors = errs.length;
    out.errs = errs.slice(0, 3);
    console.log('=== ' + t.url + ' ===');
    console.log(JSON.stringify(out, null, 1));
    await ctx.close();
  }
  await br.close();
})();

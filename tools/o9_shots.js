/**
 * o9_shots.js — OEM/ODM 四卡板块截图（1440 / 1024 / 375）
 */
const { chromium } = require('playwright-core');
const EXEC = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';
const OUT = '/Users/meng/WorkBuddy/sinofresh外贸网站建设/screenshots/';
const OFF = 'header.wp-block-template-part, header { position: static !important; } .sf-lb{display:none!important} .sf-cookie-banner, [class*="cookie-banner"] { display: none !important; }';

const T = [
  ['home', '/', 'OEM & ODM Services'],
  ['services', '/services/', 'OEM or ODM \u2014 Choose Your Path'],
];

(async () => {
  const b = await chromium.launch({ executablePath: EXEC, headless: true });
  for (const w of [1440, 1024, 375]) {
    const ctx = await b.newContext({ viewport: { width: w, height: 900 }, deviceScaleFactor: 1 });
    const p = await ctx.newPage();
    for (const t of T) {
      await p.goto('http://sinofresh.local' + t[1], { waitUntil: 'networkidle', timeout: 45000 });
      await p.evaluate(async () => { if (document.fonts) await document.fonts.ready; });
      await p.addStyleTag({ content: OFF });
      await p.evaluate(() => { const c = document.querySelector('#cookie-law-info-bar, .cli-modal, [id*="cookie"]'); if (c) c.style.display = 'none'; });
      const el = p.locator('.wp-site-blocks > .wp-block-group').filter({ has: p.locator('h2', { hasText: t[2] }) }).first();
      await el.scrollIntoViewIfNeeded();
      await p.waitForTimeout(250);
      const f = OUT + 'oem_' + w + '_' + t[0] + '.png';
      await el.screenshot({ path: f });
      console.log('shot ' + f);
    }
    await ctx.close();
  }
  await b.close();
})().catch((e) => { console.error(e); process.exit(1); });

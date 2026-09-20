// 补拍：Form 2 提交区（按钮 + WhatsApp 提示行）特写 + 整卡截图
const { chromium } = require('playwright-core');
const EXEC = '/Users/meng/.agent-browser/browsers/chrome-153.0.8010.36/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';
const OUT = '/Users/meng/WorkBuddy/sinofresh外贸网站建设/screenshots/gf-form2';
const INIT_CSS = `document.addEventListener('DOMContentLoaded',function(){var s=document.createElement('style');s.textContent='.sf-header{position:static!important}.sf-cookie-banner{display:none!important}';document.head.appendChild(s);});`;

(async () => {
  const b = await chromium.launch({ executablePath: EXEC, headless: true });
  for (const [tag, vp] of [['desktop', { width: 1440, height: 900 }], ['mobile', { width: 375, height: 812 }]]) {
    const ctx = await b.newContext({ viewport: vp, deviceScaleFactor: 2 });
    await ctx.addInitScript(INIT_CSS);
    const page = await ctx.newPage();
    await page.goto('http://sinofresh.local/', { waitUntil: 'load', timeout: 30000 });
    await page.waitForSelector('.gform_wrapper .gform_fields', { timeout: 20000 });
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(400);
    const footer = await page.$('.gform_footer');
    await footer.scrollIntoViewIfNeeded();
    await page.waitForTimeout(300);
    await footer.screenshot({ path: `${OUT}/after-footer-${tag}.png`, animations: 'disabled' });
    // 整卡（含表单外框）
    const card = await page.$('.gform_wrapper');
    await card.scrollIntoViewIfNeeded();
    await page.waitForTimeout(300);
    await card.screenshot({ path: `${OUT}/after-full-${tag}.png`, animations: 'disabled' });
    console.log('OK', tag);
    await ctx.close();
  }
  await b.close();
})().catch(e => { console.error('FATAL', e.message); process.exit(1); });

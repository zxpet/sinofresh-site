// Form 2 测试提交：1) 空提交 → 必填拦截；2) 有效提交 → 确认文案出现
const { chromium } = require('playwright-core');
const EXEC = '/Users/meng/.agent-browser/browsers/chrome-153.0.8010.36/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';
const INIT_CSS = `document.addEventListener('DOMContentLoaded',function(){var s=document.createElement('style');s.textContent='.sf-cookie-banner{display:none!important}';document.head.appendChild(s);});`;

(async () => {
  const b = await chromium.launch({ executablePath: EXEC, headless: true });
  const ctx = await b.newContext({ viewport: { width: 1440, height: 900 } });
  await ctx.addInitScript(INIT_CSS);
  const page = await ctx.newPage();
  page.setDefaultTimeout(25000);
  await page.goto('http://sinofresh.local/', { waitUntil: 'load', timeout: 30000 });
  await page.waitForSelector('.gform_wrapper form', { timeout: 20000 });

  // ---- 测试 1：空提交 → 必填拦截 ----
  await page.click('#gform_submit_button_2');
  await page.waitForSelector('.gform_validation_error', { timeout: 15000 });
  await page.waitForTimeout(800);
  const errs = await page.evaluate(() => {
    const summary = document.querySelector('.gform_submission_error, .validation_error');
    const fields = [...document.querySelectorAll('.gfield.gfield_error')].map(el => {
      const l = el.querySelector('.gfield_label, legend');
      const msg = el.querySelector('.gfield_validation_message, .validation_message');
      return (l ? l.textContent.replace(/\s+/g, ' ').replace('(Required)', '').trim() : '?') + ' ← ' + (msg ? msg.textContent.replace(/\s+/g, ' ').trim().slice(0, 60) : '?');
    });
    return { summary: summary ? summary.textContent.replace(/\s+/g, ' ').trim().slice(0, 120) : null, fields };
  });
  console.log('【测试1 空提交】验证错误出现 ✅');
  console.log('  摘要:', errs.summary);
  errs.fields.forEach(f => console.log('   -', f));

  // ---- 测试 2：有效提交 ----
  await page.fill('#input_2_1', 'QA Test Trading Co., Ltd.');
  await page.fill('#input_2_2', 'QA Bot');
  await page.fill('#input_2_3', 'qa.bot@test-trading-co.com');
  // 5/7 用默认选中值（United States / Soft Chews）
  await page.fill('#input_2_10', 'Automated QA submission — please ignore.');
  await page.check('#choice_2_11_1');
  await page.click('#gform_submit_button_2');
  // ajax 提交：等确认文案
  await page.waitForFunction(() => document.body.textContent.includes('Thank you. We will respond within 24 hours.'), { timeout: 20000 });
  console.log('【测试2 有效提交】确认文案出现 ✅');
  const confirmText = await page.evaluate(() => {
    const c = document.querySelector('.gform_confirmation_message, .gform_wrapper');
    return c ? c.textContent.replace(/\s+/g, ' ').trim().slice(0, 200) : '';
  });
  console.log('  确认区:', confirmText.slice(0, 160));
  await b.close();
})().catch(e => { console.error('FATAL', e.message); process.exit(1); });

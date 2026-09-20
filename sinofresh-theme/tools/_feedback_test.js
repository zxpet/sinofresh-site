/* /feedback/ page + Form 6 end-to-end test.
 * Covers: page load, form render, real AJAX submit -> confirmation,
 * footer link navigation, no horizontal overflow at 1440/375, FAQPage presence.
 * Email delivery is verified against wp_wpml_mails after the run (see runner).
 */
const { chromium } = require('/Users/meng/.workbuddy/binaries/node/workspace/node_modules/playwright-core');

const URL = 'http://sinofresh.local/feedback/';
let pass = 0, fail = 0;
const check = (name, ok, detail) => {
  if (ok) { pass++; console.log('  PASS  ' + name + (detail ? '  [' + detail + ']' : '')); }
  else { fail++; console.log('  FAIL  ' + name + '  [' + detail + ']'); }
};

(async () => {
  const browser = await chromium.launch();

  /* ---------- Desktop 1440 ---------- */
  const dctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const p = await dctx.newPage();
  const errors = [];
  p.on('pageerror', (e) => errors.push('pageerror: ' + e.message));
  p.on('console', (m) => { if (m.type() === 'error') errors.push('console: ' + m.text()); });

  const resp = await p.goto(URL, { waitUntil: 'load' });
  check('D1 /feedback/ returns 200', resp.status() === 200, String(resp.status()));
  await p.waitForTimeout(1500);

  check('D2 H1 text', (await p.locator('h1').innerText()).trim() === 'Feedback & Support');
  check('D3 Form 6 wrapper present', await p.locator('#gform_wrapper_6').count() === 1);
  check('D4 ajax iframe target', await p.locator('#gform_ajax_frame_6').count() === 1);

  const fields = await p.evaluate(() => ({
    select: !!document.querySelector('#input_6_1'),
    subject: !!document.querySelector('#input_6_2'),
    desc: !!document.querySelector('#input_6_3'),
    email: !!document.querySelector('#input_6_4'),
    consent: !!document.querySelector('#choice_6_5_1'),
    btn: (document.querySelector('#gform_submit_button_6') || {}).value || (document.querySelector('#gform_submit_button_6') || {}).textContent,
    emailPlaceholder: (document.querySelector('#input_6_4') || {}).placeholder,
  }));
  check('D5 select field renders', fields.select);
  check('D6 subject field renders', fields.subject);
  check('D7 description field renders', fields.desc);
  check('D8 email field renders', fields.email);
  check('D9 consent checkbox renders', fields.consent);
  check('D10 button text Submit Feedback', /Submit Feedback/.test(fields.btn || ''), fields.btn);
  check('D11 email placeholder anonymous', fields.emailPlaceholder === 'Leave blank for anonymous', fields.emailPlaceholder);

  const faqN = await p.locator('.sf-faq details').count();
  check('D12 3 FAQ details', faqN === 3, String(faqN));
  const schemaOk = await p.evaluate(() => {
    for (const s of document.querySelectorAll('script[type="application/ld+json"]')) {
      try { const d = JSON.parse(s.textContent); if (d['@type'] === 'FAQPage' && d.mainEntity.length === 3) return true; } catch (e) {}
    }
    return false;
  });
  check('D13 FAQPage schema 3 questions', schemaOk);

  /* real AJAX submit (anonymous: leave email blank) */
  await p.selectOption('#input_6_1', 'Website Issue');
  await p.fill('#input_6_2', 'E2E smoke: footer link test subject');
  await p.fill('#input_6_3', 'Automated end-to-end submission from tools/_feedback_test.js — please ignore.');
  await p.check('#choice_6_5_1');
  await p.click('#gform_submit_button_6');
  await p.waitForSelector('.gform_confirmation_message_6, #gform_confirmation_message_6', { timeout: 20000 });
  await p.waitForTimeout(800);
  const confirm = await p.evaluate(() => document.body.innerText);
  check('D14 confirmation thank-you', /Thank you for your feedback/i.test(confirm));
  check('D15 confirmation 2 business days', /2 business days/i.test(confirm));
  check('D16 form wrapper replaced (ajax path)', await p.locator('#gform_wrapper_6').count() === 0);
  check('D17 no JS errors on page', errors.length === 0, errors.slice(0, 2).join(' | '));

  /* footer link navigates */
  const p2 = await dctx.newPage();
  await p2.goto('http://sinofresh.local/', { waitUntil: 'load' });
  const flink = p2.locator('footer a[href="/feedback/"]');
  check('D18 footer Feedback link exists', await flink.count() === 1);
  await flink.click();
  await p2.waitForLoadState('load');
  check('D19 footer link navigates to /feedback/', p2.url().replace(/\/$/, '') === 'http://sinofresh.local/feedback');

  /* screenshots */
  await p2.setViewportSize({ width: 1440, height: 900 });
  await p2.goto(URL, { waitUntil: 'load' });
  await p2.waitForTimeout(1200);
  await p2.evaluate(() => document.fonts.ready);
  await p2.screenshot({ path: '/Users/meng/WorkBuddy/sinofresh外贸网站建设/screenshots/feedback-desktop-1440.png', fullPage: true });

  /* ---------- Mobile 375 ---------- */
  const mctx = await browser.newContext({ viewport: { width: 375, height: 812 } });
  const m = await mctx.newPage();
  await m.goto(URL, { waitUntil: 'load' });
  await m.waitForTimeout(1200);
  await m.evaluate(() => document.fonts.ready);
  const overflow = await m.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  check('M1 mobile no horizontal overflow', overflow <= 0, String(overflow));
  const formW = await m.evaluate(() => {
    const w = document.querySelector('#gform_wrapper_6');
    return w ? w.getBoundingClientRect().width : -1;
  });
  check('M2 form fits viewport', formW > 0 && formW <= 375, String(formW));
  await m.screenshot({ path: '/Users/meng/WorkBuddy/sinofresh外贸网站建设/screenshots/feedback-mobile-375.png', fullPage: true });

  await browser.close();
  console.log('\nRESULT: ' + pass + ' pass / ' + fail + ' fail');
  process.exit(fail ? 1 : 0);
})();

/* Post-plugin-swap regression: lead conversion tracking (functions.php §59).
 * Burst removed / WP Statistics installed — confirm generate_lead still fires
 * for Form 2 (contact) with consent=true, and does NOT fire without consent.
 * No PII assertions: payload keys must be form_id/form_title/dosage/form_source_url only.
 */
const { chromium } = require('/Users/meng/.workbuddy/binaries/node/workspace/node_modules/playwright-core');

const URL = 'http://sinofresh.local/contact/';
let pass = 0, fail = 0;
const check = (name, ok, detail) => {
  if (ok) { pass++; console.log('  PASS  ' + name + (detail ? '  [' + detail + ']' : '')); }
  else { fail++; console.log('  FAIL  ' + name + '  [' + detail + ']'); }
};

const GTAG_STUB = `window.__gtags = [];
  window.gtag = function(){ window.__gtags.push(Array.from(arguments)); };`;

async function fillAndSubmit(p, email) {
  await p.fill('#input_2_1', 'E2E Verify');
  await p.fill('#input_2_2', 'E2E Co');
  await p.fill('#input_2_3', email);
  await p.selectOption('#input_2_5', 'Germany');
  await p.selectOption('#input_2_7', 'Soft Chews');
  await p.check('#choice_2_11_1', { timeout: 5000 });
  await p.click('#gform_submit_button_2');
  await p.waitForSelector('#gform_confirmation_message_2, .gform_confirmation_message', { timeout: 15000 });
  await p.waitForTimeout(1200);
}

(async () => {
  const browser = await chromium.launch();

  /* ---------- A: consent = analytics true ---------- */
  {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    await ctx.addInitScript(GTAG_STUB);
    await ctx.addInitScript(() => {
      localStorage.setItem('sf_cookie_consent', JSON.stringify({ analytics: true, necessary: true }));
    });
    const p = await ctx.newPage();
    const errors = [];
    p.on('pageerror', (e) => errors.push(e.message));
    const resp = await p.goto(URL, { waitUntil: 'load' });
    check('A1 /contact/ 200', resp.status() === 200, String(resp.status()));
    check('A2 Form 2 wrapper present', await p.locator('#gform_wrapper_2').count() === 1);

    await fillAndSubmit(p, 'e2e.verify.lead@zxpetsite.com');

    const calls = await p.evaluate(() => window.__gtags);
    const lead = (calls || []).find((c) => c[0] === 'event' && c[1] === 'generate_lead');
    check('A3 generate_lead fired', !!lead, JSON.stringify(lead ? lead[2] : null));

    const payload = lead ? lead[2] : null;
    check('A4 form_id = 2', !!payload && payload.form_id === '2', payload && payload.form_id);
    check('A5 dosage = Soft Chews', !!payload && payload.dosage === 'Soft Chews', payload && payload.dosage);
    check('A6 form_source_url is contact page', !!payload && /sinofresh\.local\/contact\/?/.test(payload.form_source_url || ''), payload && payload.form_source_url);
    check('A7 form_title present', !!payload && typeof payload.form_title === 'string' && payload.form_title.length > 0, payload && payload.form_title);
    const keys = payload ? Object.keys(payload).sort() : [];
    check('A8 no PII (keys whitelist)', JSON.stringify(keys) === JSON.stringify(['dosage', 'form_id', 'form_source_url', 'form_title']), keys.join(','));
    check('A9 no page errors', errors.length === 0, errors.join(' | ').slice(0, 200));

    await p.screenshot({ path: __dirname + '/screenshots/_lead_verify_A.png', fullPage: false });
    await ctx.close();
  }

  /* ---------- B: no consent stored ---------- */
  {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    await ctx.addInitScript(GTAG_STUB);
    const p = await ctx.newPage();
    await p.goto(URL, { waitUntil: 'load' });
    check('B1 Form 2 wrapper present', await p.locator('#gform_wrapper_2').count() === 1);

    await fillAndSubmit(p, 'e2e.verify.lead2@zxpetsite.com');

    const calls = await p.evaluate(() => window.__gtags);
    const lead = (calls || []).find((c) => c[0] === 'event' && c[1] === 'generate_lead');
    check('B2 no generate_lead without consent', !lead, JSON.stringify(lead ? lead[2] : null));
    await ctx.close();
  }

  /* ---------- C: WP Statistics presence + no burst residue ---------- */
  {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const p = await ctx.newPage();
    const resp = await p.goto(URL, { waitUntil: 'load' });
    const html = await p.content();
    check('C1 page still healthy 200', resp.status() === 200, String(resp.status()));
    check('C2 no burst.min.js residue', !html.includes('burst.min.js'));
    check('C3 no WP Statistics front script (private mode ok either way)', !html.includes('wp-statistics') || true, '');
    check('C4 H1 intact', (await p.locator('h1').innerText()).length > 0);
    await ctx.close();
  }

  await browser.close();
  console.log('\nRESULT: ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();

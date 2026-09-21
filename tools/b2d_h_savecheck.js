#!/usr/bin/env node
/* Batch H1 Step 3 addendum — targeted save-path check on the PREFLIGHT copy.
 *
 * Proves the wp_slash() fix (70b1c65) on the REAL admin save path, which the
 * byte-level gates cannot: log in as the temp admin, edit post 158's FAQ
 * table (with X-SF-Preflight: 1 so wp-admin runs the candidate theme), save
 * an em dash + an <a href> answer, and let the orchestrating side assert the
 * DB bytes afterwards.
 *
 * Screen anatomy (measured): WP 7.1 block editor, fullscreen mode. The
 * classic metaboxes render into .edit-post-layout__metaboxes, whose liner is
 * display:none whenever the bottom "Meta Boxes" panel is collapsed — a pure
 * UI state that flaps with user preferences. The save path being tested does
 * not care: Gutenberg's metabox sync serializes the CURRENT DOM values of the
 * inputs at save time, so setting .value programmatically exercises the exact
 * same form POST and the exact same save handler as typing. Visibility is a
 * test-ergonomics problem, not a product one — so we set values via JS and
 * never depend on the panel state.
 *
 * usage:
 *   NODE_PATH=<workspace>/node_modules node tools/b2d_h_savecheck.js
 *   (password read from /tmp/sf-e2e-pass.txt, created by the caller)
 */
const { chromium } = require('playwright-core');
const fs = require('fs');

const BASE = 'https://dev.zxpet.com';
const POST_ID = 158;
const PASS = fs.readFileSync('/tmp/sf-e2e-pass.txt', 'utf8').trim();
const OUT = '/Users/meng/WorkBuddy/sinofresh外贸网站建设/screenshots/b2d-h-savecheck';
fs.mkdirSync(OUT, { recursive: true });

const A1 = 'Yes \u2014 every formula is produced exclusively under your own brand.';
const A2 = 'See our <a href="https://example.com">profile</a> for details.';

(async () => {
  const fails = [];
  const ck = (ok, label) => { console.log((ok ? 'PASS' : 'FAIL') + ' ' + label); if (!ok) fails.push(label); };

  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({
    viewport: { width: 1440, height: 1080 },
    deviceScaleFactor: 2,
    httpCredentials: { username: 'sfdev', password: 'VkEws18Kl5V1qp3TpZ6s' },
    extraHTTPHeaders: { 'X-SF-Preflight': '1' },
  });
  const page = await ctx.newPage();
  const jsErrors = [];
  page.on('pageerror', e => jsErrors.push(String(e)));

  const openEditor = async () => {
    await page.goto(BASE + '/wp-admin/post.php?post=' + POST_ID + '&action=edit',
      { waitUntil: 'commit', timeout: 90000 });
    await page.waitForSelector('.sf-reptable--faq', { state: 'attached', timeout: 60000 });
    await page.waitForTimeout(3000); // let the editor chrome settle
    await page.keyboard.press('Escape').catch(() => {}); // dismiss welcome guide if any
  };
  const readAnswers = () => page.evaluate(() =>
    [...document.querySelectorAll('textarea[name="sf_formula_faq_data[a][]"]')].map(t => t.value));
  const readQuestions = () => page.evaluate(() =>
    [...document.querySelectorAll('input[name="sf_formula_faq_data[q][]"]')].map(t => t.value));

  // ---- pass 1: login, verify served theme, fill answers, save ----
  await page.goto(BASE + '/wp-login.php', { waitUntil: 'domcontentloaded' });
  await page.fill('#user_login', 'sf-e2e');
  await page.fill('#user_pass', PASS);
  await page.click('#wp-submit');
  await page.waitForURL('**/wp-admin/**', { timeout: 30000 });
  ck(true, 'logged in as sf-e2e');

  await openEditor();

  // assert the candidate copy is actually serving wp-admin (lesson: assert WHICH bytes)
  const html = await page.content();
  ck(html.includes('sinofresh-theme-preflight/assets/admin/sf-mb-'), 'wp-admin served by PRELIGHT copy (sf-mb asset URL)');
  ck(!html.includes('themes/sinofresh-theme/assets/admin/sf-mb-'), 'no live-theme admin asset URL');

  const qs = await readQuestions();
  let as = await readAnswers();
  ck(qs.length === 9, '9 preset questions in DOM (got ' + qs.length + ')');
  ck(as.length === 9, '9 answer rows in DOM (got ' + as.length + ')');
  ck(as[0] === '', 'row 1 answer empty before edit');

  await page.evaluate(([a1, a2]) => {
    const fire = (el) => el.dispatchEvent(new Event('input', { bubbles: true }));
    const tas = document.querySelectorAll('textarea[name="sf_formula_faq_data[a][]"]');
    tas[0].value = a1; fire(tas[0]);
    tas[1].value = a2; fire(tas[1]);
  }, [A1, A2]);
  as = await readAnswers();
  ck(as[0] === A1, 'row 1 answer set with TRUE em dash');
  ck(as[1] === A2, 'row 2 answer set with <a href>');

  await page.screenshot({ path: OUT + '/before-save.png', fullPage: true });

  // save through the block editor (metabox sync runs inside this save)
  const saveBtn = page.getByRole('button', { name: 'Save', exact: true }).first();
  await saveBtn.click();
  await page.waitForSelector('.components-snackbar', { timeout: 60000 });
  const snack = await page.locator('.components-snackbar').innerText().catch(() => '');
  ck(/updated|saved/i.test(snack), 'editor snackbar: "' + snack.trim() + '"');
  await page.waitForTimeout(2000); // let the metabox iframe sync finish

  // ---- pass 2: reopen and read back what the server round-tripped ----
  await openEditor();
  const back = await readAnswers();
  ck(back[0] === A1, 'reloaded UI row 1 == em dash text');
  ck(back[1] === A2, 'reloaded UI row 2 == <a href> text');
  ck(back.length === 9, 'still 9 rows after save');

  await page.screenshot({ path: OUT + '/after-save.png', fullPage: true });

  ck(jsErrors.length === 0, 'zero page JS errors' + (jsErrors.length ? ': ' + jsErrors.join(' | ') : ''));

  await browser.close();
  console.log(fails.length ? 'RESULT: ' + fails.length + ' FAIL' : 'RESULT: ALL PASS');
  process.exit(fails.length ? 1 : 0);
})().catch(e => { console.error('FATAL', e); process.exit(2); });

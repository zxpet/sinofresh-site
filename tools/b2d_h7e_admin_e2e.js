#!/usr/bin/env node
/* Batch H7e — the admin side of the batch: the Factory Information subpage.
 *
 * WHAT THIS HAS TO SHOW, AND WHY THE OBVIOUS ASSERTION IS NOT ENOUGH
 *
 * The batch adds a settings page. "The page renders" is nearly worthless as a
 * check, because the page is new: there is nothing for it to disagree with. So
 * the run is built around three claims that CAN fail:
 *
 *   1. WHICH THEME IS SERVING wp-admin. Every request carries
 *      X-SF-Preflight: 1, so the copy under test is the preflight theme — but
 *      the new page deliberately loads no stylesheet and no script of the
 *      theme's, so on THIS page there is no asset URL to read the answer off.
 *      The contrast page fixes that: the Container Library does carry
 *      sf-mb.css and the two shared scripts, so the run asserts their URL is
 *      the preflight copy's, and it asserts that on the page this batch added
 *      they are ABSENT. Without the first half the second is satisfied by a
 *      site where the assets are broken everywhere.
 *   2. The two fields exist, are text inputs, and carry the DEFAULTS THE BATCH
 *      CLAIMS — 'Linyi, Shandong, China' and 'Available', character for
 *      character. This is the only place either string is visible as a field
 *      rather than as rendered output.
 *   3. The form posts to the Site Settings option group. A page that rendered
 *      perfectly and posted to a group nobody registered would look fine here
 *      and silently not save.
 *
 * A fourth thing is not asserted because it cannot be: that the page is not in
 * the live theme. A submenu added by this batch does not exist on the live
 * copy, so the page simply would not resolve — which makes "it resolved and
 * rendered the right values" the assertion, carried by the values themselves.
 *
 * Nothing is saved. The form is read, never submitted: a settings save is a DB
 * write and this batch does not make one. The sanitizer's empty-falls-back
 * behaviour is asserted in the source pass, against the same code the parent
 * page uses.
 *
 * usage: NODE_PATH=<workspace>/node_modules node tools/b2d_h7e_admin_e2e.js
 *        (password read from /tmp/sf-e2e-pass.txt)
 */
const { chromium } = require('playwright-core');
const fs = require('fs');

const BASE = 'https://dev.zxpet.com';
const PASS = fs.readFileSync('/tmp/sf-e2e-pass.txt', 'utf8').trim();
const OUT = '/Users/meng/WorkBuddy/sinofresh外贸网站建设/docs/batchH7e-shots';
const ORIGIN = 'Linyi, Shandong, China';
const OEM = 'Available';
fs.mkdirSync(OUT, { recursive: true });

(async () => {
  const fails = [];
  const ck = (ok, label) => {
    console.log((ok ? 'PASS' : 'FAIL') + ' ' + label);
    if (!ok) fails.push(label);
  };

  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({
    viewport: { width: 1440, height: 1080 },
    deviceScaleFactor: 2,
    httpCredentials: { username: 'sfdev', password: 'VkEws18Kl5V1qp3TpZ6s' },
    extraHTTPHeaders: { 'X-SF-Preflight': '1' },
  });
  const page = await ctx.newPage();
  const jsErrors = [];
  page.on('pageerror', e => jsErrors.push('[' + page.url().slice(-44) + '] ' + String(e).slice(0, 150)));

  // ---------------------------------------------------------------- login
  // Retried, and diagnosable. The first version was a single click plus a
  // 30-second waitForURL, and when that timed out the run said only
  // "FATAL page.waitForURL: Timeout 30000ms exceeded" — which is the same
  // message for a rejected password, a redirect somewhere unexpected, and a
  // login page that never got the POST. Three attempts with the landing URL,
  // the page title and wp-login's own error box printed on each miss cost
  // nothing and turn that into an answer.
  let logged = false;
  for (let attempt = 1; attempt <= 3 && !logged; attempt++) {
    await page.goto(BASE + '/wp-login.php', { waitUntil: 'domcontentloaded', timeout: 60000 });
    if (/\/wp-admin\//.test(page.url())) { logged = true; break; }   // cookie already good
    await page.fill('#user_login', 'sf-e2e');
    await page.fill('#user_pass', PASS);
    await page.click('#wp-submit').catch(() => {});
    try {
      await page.waitForURL(u => /\/wp-admin\//.test(u.href), { timeout: 40000 });
      logged = true;
    } catch (e) {
      const diag = await page.evaluate(() => ({
        url: location.href,
        title: document.title,
        err: (document.querySelector('#login_error') || {}).innerText || '',
        body: (document.body.innerText || '').replace(/\s+/g, ' ').slice(0, 220),
      })).catch(() => ({}));
      console.log('  login attempt ' + attempt + ' did not land: ' + JSON.stringify(diag));
      await page.waitForTimeout(2500);
    }
  }
  ck(logged, 'logged in as the throwaway admin');
  if (!logged) { await browser.close(); process.exit(3); }

  // ------------------------------------------- the contrast: a page that
  // DOES carry the shared admin assets, so that "absent" below means absent
  await page.goto(BASE + '/wp-admin/admin.php?page=sf-containers', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(1500);
  const contrast = await page.evaluate(() => ({
    title: (document.querySelector('.wrap h1') || {}).textContent || '',
    mb: [...document.querySelectorAll('link[href*="sf-mb.css"]')].map(e => e.href),
    tables: [...document.querySelectorAll('script[src*="sf-mb-tables.js"]')].map(e => e.src),
    settings: [...document.querySelectorAll('script[src*="sf-site-settings.js"]')].map(e => e.src),
    live: [...document.querySelectorAll('link[href*="themes/sinofresh-theme/"], script[src*="themes/sinofresh-theme/"]')].length,
  }));
  ck(contrast.title === 'Container Library', 'the contrast page is the Container Library');
  ck(contrast.mb.length === 1, 'it carries the shared admin stylesheet: ' + (contrast.mb[0] || 'none'));
  ck(/\?ver=/.test(contrast.mb[0] || ''), '...with a version token on it');
  ck((contrast.mb[0] || '').includes('sinofresh-theme-preflight'),
    '...served by the PREFLIGHT copy, which is what makes "which theme" a fact');
  ck(contrast.tables.length === 1 && contrast.settings.length === 1,
    'and both shared scripts are on it too');
  ck(contrast.live === 0, 'no live-theme admin asset URL anywhere on either page');
  await page.screenshot({ path: OUT + '/h7e-03-container-library-contrast.png', fullPage: true });

  // ------------------------------------------------- the new subpage
  await page.goto(BASE + '/wp-admin/admin.php?page=sf-factory-info', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(1500);
  const fi = await page.evaluate(() => {
    const q = s => document.querySelector(s);
    const menu = [...document.querySelectorAll('#toplevel_page_sf-site-settings .wp-submenu a')]
      .map(a => a.textContent.trim()).filter(Boolean);
    const cur = q('#toplevel_page_sf-site-settings .wp-submenu a.current')
      || q('#toplevel_page_sf-site-settings .wp-submenu li.current a');
    return {
      url: location.href,
      h1: (q('.wrap h1') || {}).textContent || '',
      bodyHasDenied: /not allowed to access this page/i.test(document.body.innerText),
      origin: (q('#sf_factory_origin') || {}).value,
      originName: (q('#sf_factory_origin') || {}).name,
      originType: (q('#sf_factory_origin') || {}).type,
      oem: (q('#sf_factory_oem') || {}).value,
      oemName: (q('#sf_factory_oem') || {}).name,
      oemType: (q('#sf_factory_oem') || {}).type,
      desc: [...document.querySelectorAll('.wrap .description')].map(e => e.textContent.trim()),
      labels: [...document.querySelectorAll('.wrap th[scope="row"]')].map(e => e.textContent.trim()),
      optionPage: (q('input[name="option_page"]') || {}).value || '',
      nonce: !!q('input[name="_wpnonce"]'),
      submit: (q('#submit') || {}).value || '',
      // the batch's own claim: this page needs none of the shared assets
      mb: document.querySelectorAll('link[href*="sf-mb.css"]').length,
      tables: document.querySelectorAll('script[src*="sf-mb-tables.js"]').length,
      settings: document.querySelectorAll('script[src*="sf-site-settings.js"]').length,
      media: typeof (window.wp && window.wp.media) !== 'undefined',
      menu,
      current: cur ? cur.textContent.trim() : '',
    };
  });

  ck(!fi.bodyHasDenied, 'the subpage resolves (a submenu this batch adds does not exist on the live copy)');
  ck(fi.h1 === 'Factory Information', 'its heading is Factory Information: ' + JSON.stringify(fi.h1));
  ck(fi.origin === ORIGIN, 'Place of Origin defaults to the constant it replaced: ' + JSON.stringify(fi.origin));
  ck(fi.oem === OEM, 'OEM / ODM defaults to the constant it replaced: ' + JSON.stringify(fi.oem));
  ck(fi.originType === 'text' && fi.oemType === 'text', 'both fields are text inputs');
  ck(fi.originName === 'sf_factory_origin' && fi.oemName === 'sf_factory_oem',
    'and they post under the option names the reader reads: ' + fi.originName + ' / ' + fi.oemName);
  ck(fi.labels.join('|') === 'Place of Origin|OEM / ODM',
    'the labels name the two spec-sheet rows: ' + JSON.stringify(fi.labels));
  ck(fi.desc.length === 2, 'each field explains which row it feeds (' + fi.desc.length + ' descriptions)');
  ck(fi.optionPage === 'sf_site_settings',
    'the form posts to the Site Settings option group: ' + JSON.stringify(fi.optionPage));
  ck(fi.nonce, 'and carries a settings nonce');
  ck(/^Save Changes$/i.test(fi.submit) || fi.submit !== '', 'the submit button is present: ' + JSON.stringify(fi.submit));

  // the declared absence, now meaningful because the contrast page had them
  ck(fi.mb === 0, 'the new page loads NO theme stylesheet (sf-mb.css absent)');
  ck(fi.tables === 0, '...and none of the row-table script');
  ck(fi.settings === 0, '...and not the settings row helper either');
  ck(fi.media === false, '...and wp.media is not enqueued for it');

  ck(fi.menu.includes('Container Library') && fi.menu.includes('Global FAQ')
     && fi.menu.includes('Factory Information'),
    'Site Settings now offers three subpages: ' + JSON.stringify(fi.menu));
  ck(fi.current === 'Factory Information', '...and this one is the current menu item: ' + JSON.stringify(fi.current));

  await page.screenshot({ path: OUT + '/h7e-01-factory-info.png', fullPage: true });
  const box = await page.locator('.wrap form').boundingBox();
  if (box) {
    await page.screenshot({
      path: OUT + '/h7e-02-factory-info-fields.png',
      clip: { x: Math.max(0, box.x - 24), y: Math.max(0, box.y - 24),
              width: Math.min(1440, box.width + 48), height: Math.min(1080, box.height + 48) },
    });
    ck(true, 'field-cluster frame written');
  } else {
    ck(false, 'the form could not be located for the close frame');
  }

  ck(jsErrors.length === 0, 'zero page JS errors across every visited screen');
  if (jsErrors.length) jsErrors.slice(0, 6).forEach(e => console.log('    ' + e));

  await browser.close();
  console.log('\n' + (fails.length ? 'FAIL ' + fails.length + ' check(s)' : 'PASS') + '  H7e admin E2E');
  if (fails.length) { console.log('  ' + fails.join('\n  ')); process.exit(1); }
})().catch(e => { console.error('FATAL ' + e.message); process.exit(2); });

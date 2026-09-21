#!/usr/bin/env node
/* Batch H2a Step 5 — full admin E2E against the CANDIDATE (preflight copy).
 *
 * Adapted from tools/b2d_h_admin_e2e.js (batch H1 Step 4). Two differences:
 *
 *   a) every request carries X-SF-Preflight: 1, so wp-admin runs the candidate
 *      theme — the exact bytes batch H2a/H2c propose — instead of the live one.
 *      Provenance is asserted, never assumed (the H1 lesson: assert WHICH bytes).
 *   b) the client-side precheck banner is now expected to FIRE on Save. Batch
 *      H1 measured it absent (its regex read /^(Publish|Update)$/ and WP 7.1
 *      labels the block editor button "Save"); batch H2c added "Save" to the
 *      set. So this run is the positive half of a before/after pair, and it
 *      carries its own negative control.
 *
 * Checks:
 *   1. wp-admin served by the preflight copy, precheck asset at ver 1.0.1
 *   2. six metabox groups render on a sf_formula edit screen
 *   3. exactly three repeatable tables + the FAQ table (9 preset rows), add/del
 *   4. H2c negative control — a decoy button ("Preview") must NOT raise the banner
 *   5. H2c positive — the real Save button MUST raise it
 *   6. the server-side banner (the authority) still shows after the save
 *   7. Site Settings certifications: dynamic row add/remove (no save)
 *   8. Container Library: wp.media frame opens/closes cleanly
 *   9. Global FAQ subpage: rows render, add/delete works (no save)
 *  10. zero page JS errors across every visited screen
 *
 * Everything is DOM-only (no settings save) except the single Save click on
 * post 158, whose values are unchanged, so the rewrite is byte-identical; the
 * orchestrator diffs the DB before/after and clears _edit_lock/_edit_last.
 *
 * usage: NODE_PATH=<workspace>/node_modules node tools/b2d_h2a_admin_e2e.js
 *        (password read from /tmp/sf-e2e-pass.txt)
 */
const { chromium } = require('playwright-core');
const fs = require('fs');

const BASE = 'https://dev.zxpet.com';
const POST_ID = 158;
const PASS = fs.readFileSync('/tmp/sf-e2e-pass.txt', 'utf8').trim();
const OUT = '/Users/meng/WorkBuddy/sinofresh外贸网站建设/screenshots/b2d-h2a-admin-e2e';
fs.mkdirSync(OUT, { recursive: true });

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
  page.on('pageerror', e => jsErrors.push('[' + page.url().slice(-48) + '] ' + String(e).slice(0, 160)));

  await page.goto(BASE + '/wp-login.php', { waitUntil: 'domcontentloaded' });
  await page.fill('#user_login', 'sf-e2e');
  await page.fill('#user_pass', PASS);
  await page.click('#wp-submit');
  await page.waitForURL('**/wp-admin/**', { timeout: 30000 });
  ck(true, 'logged in as sf-e2e');

  // ---------- 1 + 2 + 3: formula editor ----------
  await page.goto(BASE + '/wp-admin/post.php?post=' + POST_ID + '&action=edit',
    { waitUntil: 'commit', timeout: 90000 });
  await page.waitForSelector('.sf-reptable--faq', { state: 'attached', timeout: 60000 });
  await page.waitForTimeout(3000);
  await page.keyboard.press('Escape').catch(() => {});
  await page.waitForTimeout(1500);
  await page.waitForSelector('script[src*="sf-mb-precheck.js"]', { state: 'attached', timeout: 30000 }).catch(() => {});

  // ---- 1. assert WHICH bytes are serving wp-admin ----
  const html = await page.content();
  ck(html.includes('sinofresh-theme-preflight/assets/admin/sf-mb-'),
    'wp-admin served by the PREFLIGHT copy (candidate), not the live theme');
  ck(!html.includes('themes/sinofresh-theme/assets/admin/sf-mb-'),
    'no live-theme admin asset URL on the page');
  const asset = await page.evaluate(() => {
    const s = [...document.querySelectorAll('script[src*="sf-mb-precheck.js"]')].map(e => e.getAttribute('src'));
    return s[0] || '';
  });
  ck(/\?ver=1\.0\.1$/.test(asset), 'precheck asset is the H2c revision: ' + asset);
  console.log('  precheck src:', asset);

  // ---- 2. six metabox groups ----
  for (const g of ['basics', 'media', 'params', 'detail', 'packaging', 'faq']) {
    ck(await page.locator('#sf-mb-' + g).count() === 1, 'metabox group renders: ' + g);
  }

  // ---- 3. tables ----
  const tblInfo = await page.evaluate(() =>
    [...document.querySelectorAll('.sf-reptable')].map(t => ({
      cls: (t.className.match(/sf-reptable--[a-z]+/) || ['?'])[0],
      name: t.dataset.sfName,
      rows: t.querySelectorAll('tbody tr').length,
    })));
  const faq = tblInfo.find(t => t.cls === 'sf-reptable--faq');
  const others = tblInfo.filter(t => t.cls !== 'sf-reptable--faq');
  ck(faq && faq.rows === 9, 'FAQ table renders 9 preset rows (got ' + (faq ? faq.rows : 'none') + ')');
  ck(tblInfo.length === 3 && others.length === 2,
    'exactly 3 repeatable tables: ' + others.map(t => t.name).join(',') + ' + faq (got ' + tblInfo.length + ')');
  console.log('  tables:', JSON.stringify(tblInfo));

  // FAQ 9 -> 10 -> 9
  await page.evaluate(() => {
    document.querySelector('button.sf-reptable__add[data-sf-name="sf_formula_faq_data"]').click();
  });
  const faq10 = await page.locator('.sf-reptable--faq tbody tr').count();
  await page.evaluate(() => {
    const rows = document.querySelectorAll('.sf-reptable--faq tbody tr');
    rows[rows.length - 1].querySelector('.sf-reptable__del').click();
  });
  const faq9 = await page.locator('.sf-reptable--faq tbody tr').count();
  ck(faq10 === 10 && faq9 === 9, 'FAQ add/del rows: 9->10->9 (got ' + faq10 + '->' + faq9 + ')');

  // the two generic tables (price_tiers, cartons)
  for (let i = 0; i < others.length; i++) {
    const name = others[i].name;
    const before = others[i].rows;
    await page.evaluate((s) => {
      document.querySelector('button.sf-reptable__add[data-sf-name="' + s + '"]').click();
    }, name);
    const after = await page.evaluate((s) =>
      document.querySelector('.sf-reptable[data-sf-name="' + s + '"]').querySelectorAll('tbody tr').length, name);
    await page.evaluate((s) => {
      const rows = document.querySelectorAll('.sf-reptable[data-sf-name="' + s + '"] tbody tr');
      rows[rows.length - 1].querySelector('.sf-reptable__del').click();
    }, name);
    const back = await page.evaluate((s) =>
      document.querySelector('.sf-reptable[data-sf-name="' + s + '"]').querySelectorAll('tbody tr').length, name);
    ck(after === before + 1 && back === before, name + ' add/del: ' + before + '->' + after + '->' + back);
  }
  await page.screenshot({ path: OUT + '/01-editor-metaboxes.png', fullPage: true });

  // ---- 4 + 5. H2c: the precheck banner on Save ----
  // Watch for the banner node from now on; Gutenberg may re-render the metabox
  // area after the save completes, so a one-shot query could miss it.
  await page.evaluate(() => {
    window.__sfBannerText = null;
    window.__sfBannerAt = 0;
    const mo = new MutationObserver(() => {
      const b = document.getElementById('sf-mb-precheck-banner');
      if (b && window.__sfBannerText === null) {
        window.__sfBannerText = (b.innerText || '').trim();
        window.__sfBannerAt = Date.now();
      }
    });
    mo.observe(document.documentElement, { childList: true, subtree: true });
  });

  const bannerBefore = await page.locator('#sf-mb-precheck-banner').count();
  ck(bannerBefore === 0, 'precheck banner absent before any submit click (got ' + bannerBefore + ')');

  // negative control: same document-level click listener, non-matching text.
  await page.evaluate(() => {
    const b = document.createElement('button');
    b.type = 'button';
    b.textContent = 'Preview';
    b.id = 'sf-e2e-decoy';
    document.body.appendChild(b);
    b.click();
  });
  await page.waitForTimeout(700);
  const decoyBanner = await page.evaluate(() => window.__sfBannerText);
  ck(decoyBanner === null, 'NEGATIVE CONTROL: a "Preview" button raises no banner (gate is text-based)');

  // positive: the real Save button
  await page.waitForSelector('.editor-post-publish-button', { state: 'attached', timeout: 60000 });
  await page.waitForTimeout(1500);
  const saveText = await page.evaluate(() =>
    (document.querySelector('.editor-post-publish-button').textContent || '').trim());
  console.log('  save button textContent: "' + saveText + '"');
  await page.evaluate(() => { document.querySelector('.editor-post-publish-button').click(); });
  // the banner is built synchronously inside the click handler
  await page.waitForFunction(() => window.__sfBannerText !== null, { timeout: 15000 }).catch(() => {});
  const bannerText = await page.evaluate(() => window.__sfBannerText);
  ck(bannerText !== null, 'H2c POSITIVE: the precheck banner fires on the block editor Save button');
  if (bannerText) { console.log('  banner: "' + bannerText.replace(/\n/g, ' ').slice(0, 160) + '"'); }
  await page.screenshot({ path: OUT + '/02-precheck-banner.png', fullPage: true });

  // ---- 6. the save completes and the server-side banner is the authority ----
  await page.waitForSelector('.components-snackbar', { timeout: 60000 });
  const snack = await page.locator('.components-snackbar').innerText().catch(() => '');
  ck(/updated|saved/i.test(snack), 'save snackbar: "' + snack.trim() + '"');
  await page.waitForTimeout(2500);

  await page.reload({ waitUntil: 'commit', timeout: 90000 });
  await page.waitForSelector('.notice-warning, .sf-reptable--faq', { state: 'attached', timeout: 60000 });
  await page.waitForTimeout(3000);
  const notice = await page.locator('.notice-warning').innerText().catch(() => '');
  ck(/Backfill needed/i.test(notice),
    'server-side missing-required banner after save: "' + notice.replace(/\n/g, ' ').slice(0, 140) + '"');

  // ---- 9b. zero-write, UI side: the empty keys are still empty after a save ----
  const empties = await page.evaluate(() => {
    const keys = ['sf_formula_flavors', 'sf_formula_species', 'sf_formula_lifestage'];
    const out = {};
    keys.forEach(k => {
      const boxes = [...document.querySelectorAll('input[name="' + k + '[]"]')];
      out[k] = { boxes: boxes.length, checked: boxes.filter(b => b.checked).length };
    });
    const radios = ['sf_formula_weight', 'sf_formula_lifestage'];
    radios.forEach(k => {
      const r = [...document.querySelectorAll('input[type="radio"][name="' + k + '"]')];
      if (r.length) { out[k] = { boxes: r.length, checked: r.filter(x => x.checked).length }; }
    });
    const tier = [...document.querySelectorAll('.sf-reptable[data-sf-name="sf_formula_price_tiers"] tbody tr')];
    out.sf_formula_price_tiers = {
      boxes: tier.length,
      filled: tier.filter(tr => [...tr.querySelectorAll('input')].some(i => i.value.trim() !== '')).length,
    };
    return out;
  });
  console.log('  param field state after save:', JSON.stringify(empties));
  const noneChecked = Object.values(empties).every(v => v.checked === undefined || v.checked === 0);
  ck(noneChecked, 'no param choice became checked across the save');
  ck(empties.sf_formula_price_tiers.filled === 0, 'tier table has no filled row after the save');
  await page.screenshot({ path: OUT + '/03-editor-after-save.png', fullPage: true });

  // ---------- 7. Site Settings certifications ----------
  await page.goto(BASE + '/wp-admin/admin.php?page=sf-site-settings', { waitUntil: 'commit', timeout: 90000 });
  await page.waitForSelector('#sf-certs-add', { state: 'attached', timeout: 60000 });
  await page.waitForSelector('script[src*="sf-site-settings.js"]', { state: 'attached', timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(2500);
  const certRows = () => page.evaluate(() => {
    const add = document.getElementById('sf-certs-add');
    const table = add.closest('p').previousElementSibling;
    return table.querySelectorAll('tr').length;
  });
  const certsBefore = await certRows();
  ck(certsBefore >= 8, 'certifications table renders (rows=' + certsBefore + ', expect >=8 seeded)');
  await page.locator('#sf-certs-add').click();
  const certsAdd = await certRows();
  ck(certsAdd === certsBefore + 1, 'certs add row: ' + certsBefore + '->' + certsAdd);
  await page.locator('.sf-certs-del').last().click();
  const certsBack = await certRows();
  ck(certsBack === certsBefore, 'certs del row: back to ' + certsBack + ' (no save clicked)');
  await page.screenshot({ path: OUT + '/04-site-settings.png', fullPage: true });

  // ---------- 8. Container Library media picker ----------
  await page.goto(BASE + '/wp-admin/admin.php?page=sf-containers', { waitUntil: 'commit', timeout: 90000 });
  await page.waitForSelector('#sf-containers-add', { state: 'attached', timeout: 60000 });
  await page.waitForSelector('script[src*="sf-site-settings.js"]', { state: 'attached', timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(2500);
  const pickCount = await page.evaluate(() => document.querySelectorAll('.sf-containers__pick').length);
  console.log('  container pick buttons:', pickCount);
  if (pickCount > 0) {
    await page.evaluate(() => { document.querySelector('.sf-containers__pick').click(); });
    await page.waitForSelector('.media-modal', { timeout: 20000 });
    ck(true, 'wp.media frame opens for the container image');
    await page.screenshot({ path: OUT + '/05-container-media.png', fullPage: true });
    await page.locator('.media-modal button.media-modal-close').first().click();
    await page.waitForTimeout(1200);
    // the legacy .media-modal child keeps display:block — the wrapper hides
    const closed = await page.evaluate(() => {
      let el = document.querySelector('.media-modal');
      if (!el) { return true; }
      while (el && el !== document.documentElement) {
        if (getComputedStyle(el).display === 'none') { return true; }
        el = el.parentElement;
      }
      return false;
    });
    ck(closed, 'media frame closes cleanly (ancestor chain hidden)');
  } else {
    ck(false, 'container image picker button not found (selector changed)');
  }

  // ---------- 9. Global FAQ subpage ----------
  await page.goto(BASE + '/wp-admin/admin.php?page=sf-global-faq', { waitUntil: 'commit', timeout: 90000 });
  await page.waitForSelector('.sf-reptable', { state: 'attached', timeout: 60000 });
  await page.waitForTimeout(2000);
  const gq = await page.locator('.sf-reptable tbody tr').count();
  ck(gq >= 1, 'Global FAQ renders rows (got ' + gq + ')');
  await page.locator('.sf-reptable__add').first().click();
  const gqAdd = await page.locator('.sf-reptable tbody tr').count();
  await page.locator('.sf-reptable__del').last().click();
  const gqBack = await page.locator('.sf-reptable tbody tr').count();
  ck(gqAdd === gq + 1 && gqBack === gq, 'Global FAQ add/del: ' + gq + '->' + gqAdd + '->' + gqBack + ' (no save)');
  await page.screenshot({ path: OUT + '/06-global-faq.png', fullPage: true });

  // ---------- 10. JS errors ----------
  ck(jsErrors.length === 0, 'zero page JS errors across all screens' + (jsErrors.length ? ': ' + jsErrors.join(' | ') : ''));

  await browser.close();
  console.log(fails.length ? 'RESULT: ' + fails.length + ' FAIL' : 'RESULT: ALL PASS');
  process.exit(fails.length ? 1 : 0);
})().catch(e => { console.error('FATAL', e); process.exit(2); });

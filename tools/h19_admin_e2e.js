#!/usr/bin/env node
/* Batch H19 — browser E2E for the Gallery images picker, against the LIVE
 * dev theme. This is the half a gate cannot do: the picker is a wp.media
 * frame driven by clicks, and the reported fault ("每次只能选一张，选第二张
 * 就替换掉第一张") only exists as a sequence of clicks.
 *
 * What it proves, in order:
 *   A. the editor screen hands the browser the FIXED bundle — the script
 *      tag's own src is read, then THAT EXACT URL is re-fetched in-page, so
 *      the bytes checked are the bytes the browser was given (through the
 *      real host, not off disk);
 *   B. four PLAIN clicks in the grid leave four thumbnails selected. Before
 *      the fix every one of those clicks left exactly one;
 *   C. the confirm button fills the hidden field with all four ids;
 *   D. the editor's own Save round-trips them — after a real reload the
 *      field still holds four ids and the preview strip shows four images;
 *   E. the published record's front end renders them.
 *
 * The record is a throwaway published sf_formula created by
 * tools/h19_e2e.php setup; teardown deletes it and destroys the session.
 *
 * usage: NODE_PATH=<workspace>/node_modules node tools/h19_admin_e2e.js
 *        (reads /tmp/h19-e2e.json written by tools/h19_e2e.php setup)
 */
const { chromium } = require('playwright-core');
const fs = require('fs');

const CFG = JSON.parse(fs.readFileSync('/tmp/h19-e2e.json', 'utf8'));
const HOST = new URL(CFG.base).hostname;
const WANT_VER = process.env.H19_VER || '1.2.0';
const SHOTS = '/Users/meng/WorkBuddy/sinofresh外贸网站建设/docs/h19-shots';
fs.mkdirSync(SHOTS, { recursive: true });

let fails = 0;
const results = [];
const ck = (ok, label, detail) => {
  results.push({ ok, label, detail: String(detail === undefined ? '' : detail).slice(0, 300) });
  console.log((ok ? 'PASS ' : 'FAIL ') + label +
    (ok || detail === undefined ? '' : ' — ' + String(detail).slice(0, 300)));
  if (!ok) fails++;
};

(async () => {
  const browser = await chromium.launch({ headless: true });
  /* dev sits behind the staging Basic Auth lock. Without it every request
     answers 401 and each selector simply finds nothing — the failure mode
     that reads like "the element is missing" rather than "not authorised",
     so the login is checked by status code below, not by luck. */
  const basic = (process.env.H19_BASIC || 'sfdev:VkEws18Kl5V1qp3TpZ6s');
  const bp = basic.indexOf(':');
  const ctx = await browser.newContext({
    viewport: { width: 1440, height: 1000 },
    httpCredentials: bp === -1 ? undefined
      : { username: basic.slice(0, bp), password: basic.slice(bp + 1) },
  });
  await ctx.addCookies([
    { name: 'wordpress_sec_' + CFG.hash, value: CFG.cookies.sec, domain: HOST, path: '/', secure: true, httpOnly: true },
    { name: 'wordpress_' + CFG.hash, value: CFG.cookies.auth, domain: HOST, path: '/', secure: true, httpOnly: true },
    { name: 'wordpress_logged_in_' + CFG.hash, value: CFG.cookies.logged_in, domain: HOST, path: '/', secure: true, httpOnly: true },
  ]);
  const page = await ctx.newPage();
  const errors = [];
  page.on('pageerror', e => errors.push(String(e).slice(0, 200)));

  const fieldIds = () => page.evaluate(() => {
    const i = document.querySelector('.sf-mb__gallery-ids');
    return i ? i.value : null;
  });
  const previewN = () => page.evaluate(() => {
    const i = document.querySelector('.sf-mb__gallery-ids');
    if (!i) { return -1; }
    return i.closest('.sf-mb__field').querySelectorAll('.sf-mb__gallery-preview img').length;
  });

  /* ---------- A. the editor is served the fixed bundle ---------- */
  const adminRes = await page.goto(CFG.admin, { waitUntil: 'domcontentloaded', timeout: 120000 });
  ck(adminRes && adminRes.status() === 200,
    'A0 the editor screen answered 200 (not the staging lock\'s 401 page)',
    'status=' + (adminRes && adminRes.status()) + ' title=' + (await page.title()));
  await page.waitForSelector('.sf-mb__gallery-ids', { state: 'attached', timeout: 90000 });

  const jsSrc = await page.evaluate(() => {
    const s = document.querySelector('script[src*="assets/admin/sf-mb-tables.js"]');
    return s ? s.src : '';
  });
  ck(jsSrc.indexOf('?ver=' + WANT_VER) !== -1,
    'A1 the editor screen requests sf-mb-tables.js at the new version', jsSrc);

  /* the exact URL the browser was handed, fetched in-page: goes through the
     real host and its cache, not through a shell curl */
  const served = await page.evaluate(async (u) => {
    const r = await fetch(u, { cache: 'no-store' });
    const t = await r.text();
    return {
      status: r.status, len: t.length,
      hasAdd: t.indexOf("multiple: 'add'") !== -1,
      hasTrue: t.indexOf('multiple: true') !== -1,
    };
  }, jsSrc);
  ck(served.status === 200 && served.len > 0,
    'A2 that URL answers for the browser', JSON.stringify(served));
  ck(served.hasAdd && !served.hasTrue,
    'A3 the bytes the browser receives carry the accumulating multi-select',
    JSON.stringify(served));

  /* ---------- baseline ---------- */
  const beforeIds = await fieldIds();
  const beforePreview = await previewN();
  ck(beforePreview === 0 && (beforeIds === '' || beforeIds === null),
    'A4 the throwaway record starts with no gallery images',
    `ids=${JSON.stringify(beforeIds)} preview=${beforePreview}`);

  /* ---------- B. four plain clicks ---------- */
  await page.evaluate(() => document.querySelector('.sf-mb__gallery-add').click());
  await page.waitForSelector('.media-frame', { state: 'visible', timeout: 30000 });
  await page.waitForTimeout(2500);

  // the frame may open on the Upload tab (Library defaults content:'upload');
  // only the library tab lists existing attachments
  if (await page.locator('.media-frame .attachments .attachment').count() === 0) {
    await page.evaluate(() => {
      const items = Array.from(document.querySelectorAll('.media-frame .media-menu-item'));
      const lib = items.find(e => /media library/i.test(e.textContent));
      if (lib) { lib.click(); }
    });
    await page.waitForSelector('.media-frame .attachments .attachment', { state: 'visible', timeout: 30000 });
    await page.waitForTimeout(2000);
  }

  const avail = await page.evaluate(() => Array.from(
    document.querySelectorAll('.media-frame .attachments .attachment'))
    .slice(0, 8).map(e => e.dataset.id));
  ck(avail.length >= 4, 'B0 the library lists at least four attachments', avail.join(','));

  for (let i = 0; i < 4 && i < avail.length; i++) {
    await page.locator('.media-frame .attachments .attachment[data-id="' + avail[i] + '"]').click({ timeout: 20000 });
    await page.waitForTimeout(350);
    const n = await page.locator('.media-frame .attachments .attachment.selected').count();
    ck(n === i + 1,
      `B${i + 1} plain click #${i + 1} leaves ${i + 1} thumbnail(s) selected` +
      (i === 0 ? '' : ' — the reported bug left exactly 1'),
      'selected=' + n);
  }
  await page.screenshot({ path: SHOTS + '/admin-modal-4-selected.png' }).catch(() => {});
  const modalSelected = await page.locator('.media-frame .attachments .attachment.selected').count();

  /* ---------- C. confirm fills the hidden field ---------- */
  // the admin here runs a Chinese locale, so match core's own class first
  // (media-button-select) and only then fall back to wording
  const confirmed = await page.evaluate(() => {
    const cls = document.querySelector(
      '.media-frame button.media-button-select, .media-frame button.media-button-insert');
    if (cls) { cls.click(); return cls.textContent.trim(); }
    const b = Array.from(document.querySelectorAll('.media-frame button'))
      .find(x => /^(select|insert|选择|插入)/i.test((x.textContent || '').trim()));
    if (b) { b.click(); return b.textContent.trim(); }
    return null;
  });
  ck(confirmed !== null, 'C0 the modal confirm button was found', String(confirmed));
  await page.waitForTimeout(1500);
  const modalGone = await page.locator('.media-frame').count() === 0
    || !(await page.locator('.media-frame').first().isVisible());
  ck(modalGone, 'C0b the modal closed, so nothing is left overlaying the editor');

  const picked = ((await fieldIds()) || '').split(',').filter(Boolean);
  ck(picked.length === modalSelected,
    `C1 the hidden field holds all ${modalSelected} picked ids (not just the first)`,
    'field=' + JSON.stringify(await fieldIds()));
  ck(avail.slice(0, 4).every(id => picked.indexOf(id) !== -1),
    'C2 the field holds the exact ids that were clicked', picked.join(','));
  const cPreview = await previewN();
  ck(cPreview === picked.length,
    'C3 the preview strip shows one image per stored id',
    `preview=${cPreview} ids=${picked.length}`);

  /* the file each picked id points at, size suffix stripped, so the front
     end can be checked for the same pictures rather than just a count */
  const stem = (u) => String(u).split('/').pop().replace(/-\d+x\d+(\.[A-Za-z0-9]+)$/, '$1');
  const pickedStems = await page.evaluate(() => {
    const i = document.querySelector('.sf-mb__gallery-ids');
    return Array.from(i.closest('.sf-mb__field').querySelectorAll('.sf-mb__gallery-preview img'))
      .map(im => im.getAttribute('src'));
  });
  const wantStems = pickedStems.map(stem);
  ck(wantStems.length === picked.length,
    'C4 the preview gave one source per picked id', JSON.stringify(pickedStems));

  /* ---------- D. the editor's own Save round-trips them ---------- */
  const saveBtn = '.editor-post-publish-button__button, button.editor-post-publish-button';
  await page.waitForSelector(saveBtn, { state: 'visible', timeout: 60000 });
  try {
    await page.click(saveBtn, { timeout: 20000 });
  } catch (e) {
    // Gutenberg's header button can sit under its own sticky toolbar
    await page.evaluate(() => {
      const b = document.querySelector('.editor-post-publish-button__button')
        || document.querySelector('button.editor-post-publish-button');
      if (b) { b.click(); }
    });
  }
  await page.waitForTimeout(1500);
  // a pre-publish panel can interpose for unpublished posts; ours is published
  const panelBtn = page.locator('.editor-post-publish-panel button.editor-post-publish-button__button');
  if (await panelBtn.count()) { await panelBtn.first().click(); }
  /* Gutenberg saves the metabox form through a hidden iframe of its own, so
     the record is only written once that round-trip finishes */
  await page.waitForTimeout(9000);
  await page.screenshot({ path: SHOTS + '/admin-after-save.png' }).catch(() => {});

  await page.reload({ waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.waitForSelector('.sf-mb__gallery-ids', { state: 'attached', timeout: 90000 });
  const afterIds = ((await fieldIds()) || '').split(',').filter(Boolean);
  const afterPreview = await previewN();
  ck(afterIds.length === picked.length && afterIds.every(id => picked.indexOf(id) !== -1),
    'D1 after a real reload the editor reads back every id',
    `after=${afterIds.join(',')} before=${picked.join(',')}`);
  ck(afterPreview === afterIds.length,
    'D2 after the reload the preview strip still shows them all',
    `preview=${afterPreview} ids=${afterIds.length}`);

  /* ---------- D3. measured, not asserted: what a REOPEN arrives with -----
     The picker is built fresh on every click, so this records how many of
     the stored images a reopened frame carries. Reported as a measurement
     (NOTE, not PASS/FAIL) because it describes the field's own design rather
     than something this batch changed — but it is measured, not inferred
     from the code, because that is exactly how the original fault hid. */
  let reopenPre = null;
  try {
    await page.evaluate(() => document.querySelector('.sf-mb__gallery-add').click());
    await page.waitForSelector('.media-frame', { state: 'visible', timeout: 30000 });
    await page.waitForTimeout(2000);
    if (await page.locator('.media-frame .attachments .attachment').count() === 0) {
      await page.evaluate(() => {
        const i = Array.from(document.querySelectorAll('.media-frame .media-menu-item'))
          .find(e => /媒体库|media library/i.test(e.textContent));
        if (i) { i.click(); }
      });
      await page.waitForSelector('.media-frame .attachments .attachment', { state: 'visible', timeout: 30000 });
      await page.waitForTimeout(1500);
    }
    reopenPre = await page.locator('.media-frame .attachments .attachment.selected').count();
    // close via the modal's own button (a second Escape can blank the page)
    await page.evaluate(() => {
      const c = document.querySelector('.media-frame .media-modal-close');
      if (c) { c.click(); }
    });
    await page.waitForTimeout(1200);
  } catch (e) { reopenPre = 'error: ' + String(e).slice(0, 100); }
  console.log('NOTE a reopened picker arrives with ' + reopenPre + ' of the '
    + afterIds.length + ' stored image(s) pre-selected (0 means the button '
    + 'replaces the set rather than adding to it)');

  /* ---------- E. the front end renders them ---------- */
  const res = await page.goto(CFG.url, { waitUntil: 'domcontentloaded', timeout: 90000 });
  await page.waitForTimeout(2500);
  const fe = await page.evaluate(() => ({
    status: document.title,
    slides: document.querySelectorAll('.sf-gallery__slide').length,
    thumbs: document.querySelectorAll('.sf-gallery__thumbs .sf-gallery__thumb').length,
    srcs: Array.from(document.querySelectorAll('.sf-gallery__slide img')).map(i => i.src),
  }));
  ck(res && res.status() === 200, 'E1 the published record answers 200', res && res.status());
  ck(fe.slides >= afterIds.length,
    `E2 the front end renders at least ${afterIds.length} gallery frames`,
    JSON.stringify(fe));
  const feStems = fe.srcs.map(stem);
  const missing = wantStems.filter(s => feStems.indexOf(s) === -1);
  ck(missing.length === 0,
    'E3 every picture that was picked is rendered on the front end',
    `missing=${JSON.stringify(missing)} have=${JSON.stringify(feStems)}`);
  await page.screenshot({ path: SHOTS + '/front-end-gallery.png', fullPage: false }).catch(() => {});

  ck(errors.length === 0, 'F1 no page JS errors during the run', errors.join(' | '));

  fs.writeFileSync('/tmp/h19-e2e-result.json', JSON.stringify({
    pid: CFG.pid, url: CFG.url, picked, beforeIds, fe, fails,
    results,
  }, null, 2));
  console.log('\nRESULT_JSON=/tmp/h19-e2e-result.json');
  console.log(`--e2e: ${results.length - fails} passed, ${fails} failed`);
  await browser.close();
  process.exit(fails ? 1 : 0);
})().catch(e => {
  console.log('FATAL ' + String(e).slice(0, 400));
  console.log(`--e2e: ${results.length - fails} passed, ${fails + 1} failed`);
  process.exit(1);
});

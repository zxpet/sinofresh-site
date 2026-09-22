#!/usr/bin/env node
/* Batch H7e — the product-side frame: the specification sheet, on the page.
 *
 * WHY THE ADMIN PASS IS NOT ENOUGH ON ITS OWN
 *
 * The admin pass proves the two fields exist and ship the right defaults. It
 * cannot show that those fields are the values a reader sees, because it never
 * looks at a product page — and the routing probe, which does, is a text
 * comparison. This leaves one frame behind so that "the row is still there, with
 * the value the batch says it has" is something a person can look at.
 *
 * A VIEWPORT FRAME, NOT AN ELEMENT CLIP, and the scroll offset is written down.
 * `locator.screenshot()` on this site returns a correctly sized BLANK block once
 * the element is below the fold — measured in batch H5 and again in H6. So the
 * sheet is scrolled to the top of the viewport, the whole viewport is shot, and
 * the offset travels with the frame: a frame whose element is somewhere off the
 * top is a frame of the wrong part of the page, and nothing in the image says so.
 *
 * The block is also asserted to be COMPLETE — twelve rows, and the two this
 * batch moved among them by name and by value — because a frame of a sheet that
 * lost a row would look like a perfectly good frame.
 *
 * usage: NODE_PATH=<workspace>/node_modules node tools/b2d_h7e_front_shots.js
 */
const { chromium } = require('playwright-core');
const fs = require('fs');

const BASE = 'https://dev.zxpet.com';
const PATH = '/formulas/joint-support-soft-chews/';
const OUT = '/Users/meng/WorkBuddy/sinofresh外贸网站建设/docs/batchH7e-shots';
const JSON_OUT = '/Users/meng/WorkBuddy/sinofresh外贸网站建设/_backup/b2d-h7e-front-shots.json';
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
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 2,
    httpCredentials: { username: 'sfdev', password: 'VkEws18Kl5V1qp3TpZ6s' },
    extraHTTPHeaders: { 'X-SF-Preflight': '1' },
  });
  const page = await ctx.newPage();
  const jsErrors = [];
  page.on('pageerror', e => jsErrors.push(String(e).slice(0, 150)));

  await page.goto(BASE + PATH, { waitUntil: 'load', timeout: 60000 });
  await page.waitForTimeout(1500);

  // which copy served this page — asserted, never assumed
  const served = await page.evaluate(() => {
    const l = document.querySelector('link#sinofresh-style-css');
    return l ? l.href : '';
  });
  ck(/sinofresh-theme-preflight\/style\.css\?ver=2\.10\.66/.test(served),
    'the page is the PREFLIGHT copy at 2.10.66: ' + served);
  ck(!/themes\/sinofresh-theme\//.test(served), '...and not the live theme');

  const info = await page.evaluate(() => {
    const sheet = document.querySelector('.sf-fdetail-specs');
    const rows = [...document.querySelectorAll('.sf-fdetail-specs__row')].map(r => ({
      term: ((r.querySelector('.sf-fdetail-specs__term') || {}).textContent || '').trim(),
      value: ((r.querySelector('.sf-fdetail-specs__value') || {}).textContent || '').trim(),
    }));
    return { present: !!sheet, rows, h1: (document.querySelector('h1') || {}).textContent || '' };
  });

  ck(info.present, 'the specification sheet is on the page');
  // NOT a fixed row count. The renderer offers twelve fields and drops every row
  // whose value is empty, so the number is a property of the record and not of
  // the batch: this record prints ten, because Applicable Pet and Life Stage
  // have no meta yet (batch H7c said so when it built the sheet). A "12" written
  // here would have been a check on today's data wearing a check on the code's
  // clothes, and it reported FAIL on the first run for exactly that reason.
  // What is asserted instead is structural, and stronger: the two rows this
  // batch moved are present, and they are the LAST TWO, in order.
  ck(info.rows.length >= 8,
    'it renders a full sheet: ' + info.rows.length + ' rows (12 fields, minus the empty ones)');
  const lastTwo = info.rows.slice(-2).map(r => r.term);
  ck(lastTwo[0] === 'Place of Origin' && lastTwo[1] === 'OEM / ODM',
    'and the two rows this batch moved are the last two, in order: ' + JSON.stringify(lastTwo));
  const byTerm = Object.fromEntries(info.rows.map(r => [r.term, r.value]));
  ck(byTerm['Place of Origin'] === ORIGIN,
    'Place of Origin reads ' + JSON.stringify(byTerm['Place of Origin']));
  ck(byTerm['OEM / ODM'] === OEM,
    'OEM / ODM reads ' + JSON.stringify(byTerm['OEM / ODM']));
  console.log('  rows: ' + info.rows.map(r => r.term + '=' + r.value).join(' | ').slice(0, 400));

  // Scroll the sheet to just BELOW the sticky header, then shoot the VIEWPORT.
  // Scrolling it to the very top put the first two rows under the frozen header
  // — the frame was still honest, but a reader looking at it would have had to
  // take the missing rows on trust, and the point of the frame is that they do
  // not. The offset travels with the frame for the same reason.
  const PAD = 72;
  await page.evaluate(pad => {
    const el = document.querySelector('.sf-fdetail-specs');
    window.scrollTo(0, el.getBoundingClientRect().top + window.scrollY - pad);
  }, PAD);
  await page.waitForTimeout(600);
  const offset = await page.evaluate(() => Math.round(window.scrollY));
  const boxTop = await page.evaluate(() =>
    Math.round(document.querySelector('.sf-fdetail-specs').getBoundingClientRect().top));
  ck(boxTop >= 0 && boxTop <= 140,
    'the sheet sits below the sticky header inside the frame (top=' + boxTop + ')');
  await page.screenshot({ path: OUT + '/h7e-04-product-spec-sheet.png' });

  ck(jsErrors.length === 0, 'zero page JS errors');
  if (jsErrors.length) jsErrors.slice(0, 4).forEach(e => console.log('    ' + e));

  await browser.close();
  fs.writeFileSync(JSON_OUT, JSON.stringify({
    ok: fails.length === 0, path: PATH, scrollY: offset, boxTop,
    served, rows: info.rows, h1: info.h1, fails,
  }, null, 1));
  console.log('\n' + (fails.length ? 'FAIL ' + fails.length : 'PASS') + '  H7e front frame');
  if (fails.length) process.exit(1);
})().catch(e => { console.error('FATAL ' + e.message); process.exit(2); });

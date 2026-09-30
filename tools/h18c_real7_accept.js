/*
 * H18c acceptance 3 — a REAL record with seven of its own photos AND a video.
 *
 * The rest of the acceptance pushes the rail to seven tiles by cloning nodes in
 * the browser. This one does it with real data, because the two ceilings exist
 * precisely for the shape "seven photos plus a video": a plain frame cap would
 * have merged head + own + video + facility and sliced eight PHOTOS, cutting the
 * video off the end instead of a facility frame.
 *
 * Record 158 (joint-support-soft-chews) already carries a video and no own
 * photos. This sets seven own photos, reads the rendered page at 1440, then puts
 * the record back exactly as it was — snapshot first, restore from the snapshot,
 * and re-render to prove the restore took.
 *
 * Usage:
 *   NODE_PATH=/Users/meng/.workbuddy/binaries/node/workspace/node_modules \
 *   /Users/meng/.workbuddy/binaries/node/versions/22.22.2-3/bin/node \
 *     tools/h18c_real7_accept.js
 */
const { chromium } = require('playwright');
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const DEV = 'https://dev.zxpet.com';
const SSH = 'root@65.49.215.152';
const WP_ROOT = '/var/www/dev.zxpet.com/public';
const PID = 158;
const KEY = 'sf_formula_gallery_ids';
const SEVEN = '53,96,102,104,106,108,110';   /* seven real uploads, none of them a facility still */
const OUT = path.join(__dirname, '..', 'docs', 'h18c-shots');
const TILE = 72, SEVEN_H = 7 * TILE + 6 * 8 + 8;

let pass = 0, fail = 0;
const ck = (name, ok, detail) => {
  if (ok) { pass++; console.log(`  [PASS] ${name}`); }
  else { fail++; console.log(`  [FAIL] ${name}\n         ${typeof detail === 'string' ? detail : JSON.stringify(detail)}`); }
};

const ssh = (cmd) => execSync(`ssh -o ConnectTimeout=15 ${SSH} ${JSON.stringify(cmd)}`,
  { encoding: 'utf8', timeout: 180000 }).trim();

const metaGet = (key) => {
  const v = ssh(`cd ${WP_ROOT} && wp post meta get ${PID} ${key} --allow-root 2>/dev/null || true`);
  return v.split('\n').filter((l) => !/^(Success|Warning|Error)/.test(l.trim()))
          .join('\n').trim();
};

const probe = () => {
  const rail = document.querySelector('.sf-fdetail2__media .sf-gallery__thumbs');
  const slides = Array.from(document.querySelectorAll('.sf-fdetail2__media .sf-gallery__stage .sf-gallery__slide'));
  const tiles = rail ? Array.from(rail.querySelectorAll('.sf-gallery__thumb')) : [];
  const names = slides.map((s) => {
    if (s.classList.contains('sf-gallery__slide--video')) { return 'VIDEO'; }
    const img = s.querySelector('img');
    return img ? img.getAttribute('src').split('/').pop().split('?')[0] : '?';
  });
  const stage = document.querySelector('.sf-fdetail2__media .sf-gallery__stage');
  const r = rail ? rail.getBoundingClientRect() : null;
  return {
    slides: slides.length,
    tiles: tiles.length,
    names,
    gap: rail ? getComputedStyle(rail).rowGap : null,
    railH: r ? +r.height.toFixed(2) : null,
    railClientH: rail ? rail.clientHeight : null,
    railScrollH: rail ? rail.scrollHeight : null,
    stageH: stage ? +stage.getBoundingClientRect().height.toFixed(2) : null,
  };
};

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch();
  const ctx = await browser.newContext({
    viewport: { width: 1440, height: 1100 }, deviceScaleFactor: 1,
    httpCredentials: { username: 'sfdev', password: 'VkEws18Kl5V1qp3TpZ6s' },
    userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
  });
  const page = await ctx.newPage();
  const url = `${DEV}/formulas/joint-support-soft-chews/`;

  /* ---- snapshot, so the restore cannot guess ---- */
  const snapshot = metaGet(KEY);
  console.log(`\n== snapshot ==\n  ${KEY} was: ${snapshot === '' ? '(absent)' : snapshot}`);
  ck('the record starts with no own photos (the snapshot is empty)', snapshot === '', { snapshot });

  /* declared out here on purpose: the finally block below has to compare the
     restored page against the pre-change one, and a const inside try is not
     visible there (block scoping — it crashed the first run). */
  let before2 = null;

  try {
    /* ---- 1. before ---- */
    console.log('\n== 1. as shipped (video only) ==');
    await page.goto(url, { waitUntil: 'load', timeout: 60000 });
    await page.waitForTimeout(600);
    before2 = await page.evaluate(probe);
    console.log(`  slides=${before2.slides} tiles=${before2.tiles} gap=${before2.gap} rail=${before2.railH} :: ${before2.names.join(' | ')}`);
    ck('1 as shipped: five frames / four tiles / 12px rail (unchanged by H18c)',
       before2.slides === 5 && before2.tiles === 4 && before2.gap === '12px' && Math.abs(before2.railH - 332) < 0.6, before2);

    /* ---- 2. seven own photos + the video ---- */
    console.log('\n== 2. seven own photos + the video ==');
    ssh(`cd ${WP_ROOT} && wp post meta update ${PID} ${KEY} '${SEVEN}' --allow-root`);
    const after = metaGet(KEY);
    ck('the write landed', after === SEVEN, { after });
    await page.goto(url, { waitUntil: 'load', timeout: 60000 });
    await page.waitForTimeout(900);
    const d = await page.evaluate(probe);
    console.log(`  slides=${d.slides} tiles=${d.tiles} gap=${d.gap} rail=${d.railH} :: ${d.names.join(' | ')}`);
    await page.locator('.sf-fdetail2__media .sf-gallery__inner').screenshot({ path: path.join(OUT, 'j-158-real-7-photos-plus-video.png') });

    ck('2 eight frames render (seven photos + the video)', d.slides === 8, { slides: d.slides, names: d.names });
    ck('2 the video survives at seven photos (the old slice cut it)',
       d.names.includes('VIDEO') && d.names.filter((n) => n !== 'VIDEO').length === 7, d.names);
    ck('2 the video keeps its declared position (after the own photos)',
       d.names[d.names.length - 1] === 'VIDEO', d.names);
    ck('2 seven tiles, because the video is not a thumbnail',
       d.tiles === 7 && d.names.filter((n) => n !== 'VIDEO').length === d.tiles, { tiles: d.tiles, slides: d.slides });
    ck('2 the seventh tile switches the rail to the 8px gap', d.gap === '8px', { gap: d.gap });
    ck('2 the rail builds to exactly 560px and does not scroll or clip',
       Math.abs(d.railH - SEVEN_H) < 0.6 && d.railClientH === d.railScrollH,
       { railH: d.railH, expected: SEVEN_H, clientH: d.railClientH, scrollH: d.railScrollH });
    ck('2 seven tiles sit inside the main photo at 1440',
       d.railH <= d.stageH + 0.01, { railH: d.railH, stageH: d.stageH });
  } finally {
    /* ---- 3. restore, whatever happened above ---- */
    console.log('\n== 3. restore ==');
    if (snapshot === '') {
      ssh(`cd ${WP_ROOT} && wp post meta delete ${PID} ${KEY} --allow-root`);
    } else {
      ssh(`cd ${WP_ROOT} && wp post meta update ${PID} ${KEY} '${snapshot}' --allow-root`);
    }
    await page.goto(url, { waitUntil: 'load', timeout: 60000 });
    await page.waitForTimeout(900);
    const back = await page.evaluate(probe);
    console.log(`  slides=${back.slides} tiles=${back.tiles} gap=${back.gap} rail=${back.railH} :: ${back.names.join(' | ')}`);
    ck('3 the record is byte-for-byte where it started (5 frames / 4 tiles / 12px / 332px)',
       back.slides === 5 && back.tiles === 4 && back.gap === '12px' && Math.abs(back.railH - 332) < 0.6
       && back.names.join('|') === before2.names.join('|'),
       { back, was: before2 });
    ck('3 the meta row is gone again', metaGet(KEY) === '', { now: metaGet(KEY) });
    await ctx.close();
    await browser.close();
  }

  console.log(`\nVERDICT: ${fail === 0 ? 'PASS' : 'FAIL'} — ${pass} passed, ${fail} failed`);
  process.exit(fail ? 1 : 0);
})();

/*
 * H18c — acceptance geometry. READ ONLY (tile counts above the real ones are
 * cloned in the browser's own DOM; nothing is written anywhere).
 *
 * Three questions, all measured rather than reasoned:
 *
 *   A. ZERO DRIFT. All 21 formula records carry four photos. With the :has()
 *      scoping the 8px gap must NOT reach them: every rail must still measure
 *      a 12px gap and a 332px height at 1440. A styling change that quietly
 *      re-pitched 21 pages would be the exact drift this batch promised not to
 *      cause.
 *
 *   B. SEVEN TILES. At 1101 / 1200 / 1240 / 1440 the rail is pushed to seven
 *      tiles: the gap must become 8px, the rail must stay inside the main photo
 *      where the geometry allows it, and where it cannot it must grow the grid
 *      row WITHOUT clipping, scrolling, or overlapping the switch below it.
 *
 *   C. THE PHONE. At 375 the strip is display:none and the dots carry the
 *      position, so a seventh photo costs nothing but one more dot.
 *
 * Every run also asserts WHICH stylesheet dev served: the stylesheet must
 * contain the :has() rule and its md5 is recorded. A stale symlink or a cached
 * copy would otherwise let the run compare old bytes and print an all-green
 * lie. The "is the rule inside the min-width:1101 block" question needs brace
 * parsing and lives in tools/h18c_gate.py --source instead.
 *
 * Usage:
 *   NODE_PATH=/Users/meng/.workbuddy/binaries/node/workspace/node_modules \
 *   /Users/meng/.workbuddy/binaries/node/versions/22.22.2-3/bin/node \
 *     tools/h18c_geometry.js [out.json]
 */
const { chromium } = require('playwright');
const { execSync } = require('child_process');
const fs = require('fs');
const crypto = require('crypto');

/* Overridable so the same assertions can be pointed at production:
     H18C_BASE=https://www.zxpet.com H18C_USER= H18C_PASS= \
     H18C_WP_ROOT=/var/www/zxpet-v2 node tools/h18c_geometry.js out.json
   The defaults are dev. */
const DEV = process.env.H18C_BASE || 'https://dev.zxpet.com';
const USER = process.env.H18C_USER !== undefined ? process.env.H18C_USER : 'sfdev';
const PASS = process.env.H18C_PASS !== undefined ? process.env.H18C_PASS : 'VkEws18Kl5V1qp3TpZ6s';
const SSH = 'root@65.49.215.152';
const WP_ROOT = process.env.H18C_WP_ROOT || '/var/www/dev.zxpet.com/public';
const UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36';
const TILE = 72, GAP_SEVEN = 8, PAD = 8;      /* 4px top + 4px bottom padding */
const SEVEN_H = 7 * TILE + 6 * GAP_SEVEN + PAD; /* 560 */
const WIDE = [1440, 1240, 1200, 1101];

let pass = 0, fail = 0;
const rows = [];
const ck = (name, ok, detail) => {
  rows.push({ name, ok: !!ok, detail });
  if (ok) { pass++; console.log(`  [PASS] ${name}`); }
  else { fail++; console.log(`  [FAIL] ${name}\n         ${typeof detail === 'string' ? detail : JSON.stringify(detail)}`); }
};

function slugs() {
  const out = execSync(
    `ssh -o ConnectTimeout=15 ${SSH} "cd ${WP_ROOT} && wp post list --post_type=sf_formula ` +
    `--post_status=publish --field=post_name --orderby=ID --order=ASC --allow-root"`,
    { encoding: 'utf8', timeout: 120000 });
  return out.split('\n').map((s) => s.trim()).filter(Boolean);
}

/* Runs INSIDE the page — every constant it needs arrives via the cfg argument,
   because a serialised function has no closure over Node's scope. */
function probe(cfg) {
  const T = cfg.tile;
  const rail = document.querySelector('.sf-fdetail2__media .sf-gallery__thumbs');
  const stage = document.querySelector('.sf-fdetail2__media .sf-gallery__stage');
  const tabs = document.querySelector('.sf-fdetail2__media .sf-gallery__tabs');
  const band = document.querySelector('.sf-fdetail2__inner');
  const link = document.querySelector('link[href*="sinofresh-theme/style.css"]');
  const out = {
    stylesheet: link ? link.getAttribute('href') : null,
    hasSupport: !!(window.CSS && CSS.supports && CSS.supports('selector(:has(*))')),
    stage: stage ? { w: +stage.getBoundingClientRect().width.toFixed(2),
                     h: +stage.getBoundingClientRect().height.toFixed(2) } : null,
  };
  if (!rail) { out.noRail = true; return out; }

  const cs = getComputedStyle(rail);
  out.rail = {
    dir: cs.flexDirection, gap: cs.rowGap, overflowY: cs.overflowY,
    clientH: rail.clientHeight, scrollH: rail.scrollHeight,
    h: +rail.getBoundingClientRect().height.toFixed(2),
  };
  const base = Array.from(rail.querySelectorAll('.sf-gallery__thumb'));
  out.tiles = base.length;
  if (base.length >= 2) {
    const a = base[0].getBoundingClientRect(), b = base[1].getBoundingClientRect();
    out.pitch = cs.flexDirection === 'column' ? +(b.top - a.top).toFixed(2) : +(b.left - a.left).toFixed(2);
    out.gapMeasured = cs.flexDirection === 'column' ? +(b.top - a.bottom).toFixed(2) : +(b.left - a.right).toFixed(2);
  }
  if (base.length >= 7 || !base.length) { return out; }

  const clones = [];
  let i = 0;
  while (rail.querySelectorAll('.sf-gallery__thumb').length < 7) {
    const c = base[i % base.length].cloneNode(true);
    c.id = c.id + '-g7-' + i;
    c.setAttribute('aria-selected', 'false');
    c.setAttribute('tabindex', '-1');
    rail.appendChild(c);
    clones.push(c);
    i++;
  }
  const all = Array.from(rail.querySelectorAll('.sf-gallery__thumb'));
  const lastR = all[all.length - 1].getBoundingClientRect();
  const railR = rail.getBoundingClientRect();
  const tabsR = tabs ? tabs.getBoundingClientRect() : null;
  const bandR = band ? band.getBoundingClientRect() : null;
  const g = getComputedStyle(rail);
  out.seven = {
    n: all.length,
    gap: g.rowGap,
    railH: +railR.height.toFixed(2),
    stageH: stage ? +stage.getBoundingClientRect().height.toFixed(2) : null,
    overhang: stage ? +(railR.height - stage.getBoundingClientRect().height).toFixed(2) : null,
    lastTileBottom: +lastR.bottom.toFixed(2),
    railBottom: +railR.bottom.toFixed(2),
    railClientH: rail.clientHeight, railScrollH: rail.scrollHeight,
    tabsTop: tabsR ? +tabsR.top.toFixed(2) : null,
    bandBottom: bandR ? +bandR.bottom.toFixed(2) : null,
    docH: document.documentElement.scrollHeight,
  };
  clones.forEach((c) => c.remove());
  out.restored = rail.querySelectorAll('.sf-gallery__thumb').length;
  return out;
}

(async () => {
  const browser = await chromium.launch();
  const report = { widths: {}, records: {}, sheetMd5: null };

  const open = async (width, slug) => {
    const opts = {
      viewport: { width, height: 1000 }, deviceScaleFactor: 1, userAgent: UA,
    };
    if (USER) { opts.httpCredentials = { username: USER, password: PASS }; }
    const ctx = await browser.newContext(opts);
    const page = await ctx.newPage();
    const resp = await page.goto(`${DEV}/formulas/${slug}/`, { waitUntil: 'load', timeout: 60000 });
    await page.waitForTimeout(900);
    return { ctx, page, status: resp ? resp.status() : null };
  };
  const cfg = { tile: TILE };
  const run = (page) => page.evaluate(probe, cfg);

  /* ---- which stylesheet is dev actually serving? ---- */
  console.log('== served stylesheet ==');
  let status = null;
  {
    const r = await open(1440, 'joint-support-soft-chews');
    status = r.status;
    /* guard: prove it is the served page and not a 401 shell */
    ck('dev serves the record page (HTTP 200, stage present)',
       r.status === 200 && !!(await r.page.$('.sf-fdetail2__media .sf-gallery__stage')), { status: r.status });
    const href = await r.page.evaluate(() => {
      const l = document.querySelector('link[href*="sinofresh-theme/style.css"]');
      return l ? l.getAttribute('href') : null;
    });
    const body = await (await r.page.request.get(href)).text();
    report.sheetUrl = href;
    report.sheetMd5 = crypto.createHash('md5').update(body, 'utf8').digest('hex');
    report.sheetBytes = body.length;
    ck('the served style.css carries the H18c :has() rule',
       body.includes('.sf-gallery__thumbs:has(.sf-gallery__thumb:nth-child(7))'),
       { md5: report.sheetMd5, bytes: body.length, href });
    ck('the served style.css still declares the shipped version',
       /\?ver=2\.10\.88/.test(href || ''), { href });
    await r.ctx.close();
  }

  /* ---- A. zero drift across every record ---- */
  console.log('\n== A. zero drift: every formula record at 1440 keeps a 12px / 332px rail ==');
  const all = slugs();
  report.recordCount = all.length;
  const bad = [];
  for (const slug of all) {
    const r = await open(1440, slug);
    const d = await run(r.page);
    await r.ctx.close();
    report.records[slug] = { tiles: d.tiles, gap: d.rail && d.rail.gap, h: d.rail && d.rail.h,
                             pitch: d.pitch, gapMeasured: d.gapMeasured, has: d.hasSupport, status: r.status };
    if (!(d.tiles === 4 && d.rail && d.rail.gap === '12px' && Math.abs(d.rail.h - 332) < 0.6 && d.gapMeasured === 12)) {
      bad.push({ slug, tiles: d.tiles, gap: d.rail && d.rail.gap, h: d.rail && d.rail.h, gapMeasured: d.gapMeasured });
    }
  }
  ck('A the sweep covered all 21 records', all.length === 21, { n: all.length });
  ck('A every record: 4 tiles, 12px gap (8px rule did NOT reach them), 332px rail',
     bad.length === 0, { drifted: bad });

  /* ---- B. seven tiles at four desktop widths ---- */
  console.log('\n== B. seven tiles: inside the main photo where it fits, row-growth where it cannot ==');
  for (const w of WIDE) {
    const r = await open(w, 'joint-support-soft-chews');
    const d = await run(r.page);
    await r.ctx.close();
    report.widths[w] = d;
    const s = d.seven;
    if (!s) { ck(`B ${w}: seven-tile probe produced data`, false, d); continue; }
    const expectFit = (d.stage.h >= SEVEN_H - 0.01);
    console.log(`  -- ${w}: stage ${d.stage.h}  rail@7 ${s.railH}  overhang ${s.overhang}  gap ${s.gap}  tabsTop ${s.tabsTop}`);
    ck(`B ${w}: the seventh tile switches the rail to the 8px gap`, s.gap === '8px', { gap: s.gap });
    ck(`B ${w}: seven tiles build to exactly 560px with no clipping and no scrollbar`,
       Math.abs(s.railH - SEVEN_H) < 0.6 && s.railClientH === s.railScrollH,
       { railH: s.railH, expected: SEVEN_H, clientH: s.railClientH, scrollH: s.railScrollH });
    ck(`B ${w}: the [Photos][Video] switch never overlaps the rail`,
       s.tabsTop !== null && s.railBottom <= s.tabsTop + 0.01, { railBottom: s.railBottom, tabsTop: s.tabsTop });
    ck(`B ${w}: the rail stays inside the band`, s.bandBottom !== null && s.railBottom <= s.bandBottom + 0.01,
       { railBottom: s.railBottom, bandBottom: s.bandBottom });
    ck(`B ${w}: ${expectFit ? 'seven tiles sit inside the main photo' : 'seven tiles overhang only by the accepted amount'}`,
       expectFit ? s.overhang <= 0.01 : (s.overhang > 0 && s.overhang < 90),
       { overhang: s.overhang, stageH: s.stageH, railH: s.railH, wants: expectFit ? '<=0' : '0<o<90' });
    ck(`B ${w}: the DOM is restored to the four real tiles`, d.restored === 4, { restored: d.restored });
  }

  /* ---- C. the phone ---- */
  console.log('\n== C. the phone (375) ==');
  {
    const r = await open(375, 'joint-support-soft-chews');
    const d = await r.page.evaluate(() => {
      const rail = document.querySelector('.sf-fdetail2__media .sf-gallery__thumbs');
      const dots = document.querySelector('.sf-fdetail2__media .sf-gallery__dots');
      return {
        stripDisplay: rail ? getComputedStyle(rail).display : null,
        dotsDisplay: dots ? getComputedStyle(dots).display : null,
        dots: dots ? dots.querySelectorAll('.sf-gallery__dot').length : 0,
        dotsW: dots ? +dots.getBoundingClientRect().width.toFixed(2) : null,
      };
    });
    await r.ctx.close();
    report.phone = d;
    ck('C 375: the strip is display:none, so a seventh tile costs no layout', d.stripDisplay === 'none', d);
    ck('C 375: the dots carry the position', d.dotsDisplay === 'flex' && d.dots === 4, d);
    ck('C 375: the dot row is nowhere near the 299px content width', d.dotsW > 0 && d.dotsW <= 300, d);
  }

  await browser.close();
  console.log(`\nVERDICT: ${fail === 0 ? 'PASS' : 'FAIL'} — ${pass} passed, ${fail} failed`);
  console.log(`stylesheet md5 ${report.sheetMd5} (${report.sheetBytes} bytes), ${report.recordCount} records swept`);
  if (process.argv[2]) { fs.writeFileSync(process.argv[2], JSON.stringify(report, null, 1)); console.log(`json -> ${process.argv[2]}`); }
  process.exit(fail ? 1 : 0);
})();

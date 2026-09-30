/*
 * H18c — READ-ONLY geometry probe: how many thumbnails does the formula gallery
 * rail actually hold, per breakpoint?
 *
 * Nothing is written: no DB call, no admin request. The "what if there were 7"
 * question is answered by cloning the existing thumbnail <button> nodes inside
 * the browser's own DOM (memory only, discarded when the page closes), then
 * re-measuring. That is stronger evidence than arithmetic, because it lets the
 * real layout answer — including whether a taller rail pushes the rest of the
 * page down.
 *
 * Run:
 *   NODE_PATH=/Users/meng/.workbuddy/binaries/node/workspace/node_modules \
 *   /Users/meng/.workbuddy/binaries/node/versions/22.22.2-3/bin/node \
 *     tools/h18c_gallery_capacity_probe.js
 *
 * Output: a JSON blob on stdout + a readable table on stderr.
 */
const { chromium } = require('playwright');

const DEV = 'https://dev.zxpet.com';
const SLUG = 'joint-support-soft-chews'; // ID 158 — the one record with a video
const USER = 'sfdev';
const PASS = 'VkEws18Kl5V1qp3TpZ6s';
/* The four widths the report asks for, plus the ones the geometry actually
   turns on. 1440 == 1280 because the band caps at max-width 1200; and the
   vertical rail's capacity is NOT constant across its own range (>=1101), so
   the 1200-1260 band is swept to find where 7 stops fitting. */
const WIDTHS = [1440, 1280, 1260, 1240, 1237, 1200, 1101, 1024, 768, 375];
const COUNTS = [5, 6, 7, 8, 9];

/* Runs inside the page. Restores the DOM itself before returning. */
function measure(labels) {
  const out = {};
  const rail = document.querySelector('.sf-fdetail2__media .sf-gallery__thumbs')
            || document.querySelector('.sf-gallery__thumbs');
  const stage = document.querySelector('.sf-fdetail2__media .sf-gallery__stage')
             || document.querySelector('.sf-gallery__stage');
  const inner = document.querySelector('.sf-fdetail2__media .sf-gallery__inner');
  const tabs = document.querySelector('.sf-fdetail2__media .sf-gallery__tabs');
  const dots = document.querySelector('.sf-fdetail2__media .sf-gallery__dots');
  const media = document.querySelector('.sf-fdetail2__media');

  if (!stage) { return { error: 'no .sf-gallery__stage in the served document' }; }

  const R = (el) => { const r = el.getBoundingClientRect();
    return { w: +r.width.toFixed(2), h: +r.height.toFixed(2), top: +r.top.toFixed(2), left: +r.left.toFixed(2) }; };
  const cs = (el) => getComputedStyle(el);

  out.url = location.href;
  out.host = location.hostname;
  out.path = location.pathname;
  out.title = document.title;
  out.stage = R(stage);
  out.stageAspect = cs(stage).aspectRatio;
  out.stageMaxW = cs(stage).maxWidth;

  /* why 1440 and 1280 come out identical: the band, and the site container
     above it, stop growing past their max-width. Measure both so the report
     can say which one does the capping. */
  const band = document.querySelector('.sf-fdetail2__inner');
  const wrap = document.querySelector('.wp-site-blocks, .entry-content, main');
  out.band = band ? { rect: R(band), width: cs(band).width, cols: cs(band).gridTemplateColumns } : null;
  out.wrap = wrap ? { tag: wrap.tagName + '.' + (wrap.className || '').split(' ')[0], rect: R(wrap) } : null;
  out.inner = inner ? R(inner) : null;

  if (rail) {
    const s = cs(rail);
    out.rail = {
      display: s.display, direction: s.flexDirection,
      rowGap: s.rowGap, columnGap: s.columnGap,
      padTop: s.paddingTop, padBottom: s.paddingBottom, padLeft: s.paddingLeft, padRight: s.paddingRight,
      overflowX: s.overflowX, overflowY: s.overflowY,
      maxHeight: s.maxHeight, height: s.height,
      alignContent: s.alignContent, flexWrap: s.flexWrap,
      clientH: rail.clientHeight, scrollH: rail.scrollHeight,
      clientW: rail.clientWidth, scrollW: rail.scrollWidth,
      rect: R(rail),
    };
  } else {
    out.rail = null;
  }

  const tiles = rail ? Array.from(rail.querySelectorAll('.sf-gallery__thumb')) : [];
  out.tileCount = tiles.length;
  out.tiles = tiles.map((t) => {
    const r = R(t);
    const s = cs(t);
    return { w: r.w, h: r.h, top: r.top, left: r.left, flexBasis: s.flexBasis };
  });

  const col = out.rail && out.rail.direction === 'column';
  /* pitch = centre-to-centre or edge-to-edge distance between consecutive tiles */
  if (tiles.length >= 2) {
    const a = tiles[0].getBoundingClientRect();
    const b = tiles[1].getBoundingClientRect();
    out.pitch = col ? +(b.top - a.top).toFixed(2) : +(b.left - a.left).toFixed(2);
    out.gapMeasured = col ? +(b.top - a.bottom).toFixed(2) : +(b.left - a.right).toFixed(2);
  } else {
    out.pitch = null; out.gapMeasured = null;
  }

  /* the rail as it stands today, in whatever direction it runs */
  out.railNaturalH = rail ? rail.scrollHeight : null;

  /* ---- synthetic growth: clone tiles, re-measure, then restore ---- */
  const templates = tiles.slice();
  const clones = [];
  out.growth = {};
  if (rail && templates.length) {
    const baseCount = tiles.length;
    for (const n of labels) {
      while (tiles.length + clones.length < n && templates.length) {
        const src = templates[(tiles.length + clones.length) % templates.length];
        const c = src.cloneNode(true);
        c.id = c.id + '-probe' + clones.length;
        c.setAttribute('aria-selected', 'false');
        c.setAttribute('tabindex', '-1');
        rail.appendChild(c);
        clones.push(c);
      }
      const all = Array.from(rail.querySelectorAll('.sf-gallery__thumb'));
      const last = all[all.length - 1];
      const row = {};
      row.n = all.length;
      row.railClientH = rail.clientHeight;
      row.railScrollH = rail.scrollHeight;
      row.railRectH = +rail.getBoundingClientRect().height.toFixed(2);
      row.railClientW = rail.clientWidth;
      row.railScrollW = rail.scrollWidth;
      row.overflowY = cs(rail).overflowY;
      row.overflowX = cs(rail).overflowX;
      row.lastTileRight = last ? +last.getBoundingClientRect().right.toFixed(2) : null;
      row.lastTileBottom = last ? +last.getBoundingClientRect().bottom.toFixed(2) : null;
      row.railRight = +rail.getBoundingClientRect().right.toFixed(2);
      row.railBottom = +rail.getBoundingClientRect().bottom.toFixed(2);
      row.lastTileClippedX = last ? +(last.getBoundingClientRect().right - rail.getBoundingClientRect().right).toFixed(2) : null;
      row.lastTileClippedY = last ? +(last.getBoundingClientRect().bottom - rail.getBoundingClientRect().bottom).toFixed(2) : null;
      row.stageH = +stage.getBoundingClientRect().height.toFixed(2);
      row.stageTop = +stage.getBoundingClientRect().top.toFixed(2);
      row.railTop = +rail.getBoundingClientRect().top.toFixed(2);
      row.railExceedsStageBy = +(rail.getBoundingClientRect().height - stage.getBoundingClientRect().height).toFixed(2);
      row.innerH = inner ? +inner.getBoundingClientRect().height.toFixed(2) : null;
      row.tabsTop = tabs ? +tabs.getBoundingClientRect().top.toFixed(2) : null;
      row.dotsTop = dots ? +dots.getBoundingClientRect().top.toFixed(2) : null;
      row.mediaH = media ? +media.getBoundingClientRect().height.toFixed(2) : null;
      row.docH = document.documentElement.scrollHeight;
      row.tileH = last ? +last.getBoundingClientRect().height.toFixed(2) : null;
      out.growth[n] = row;
    }
    clones.forEach((c) => c.remove());
    out.restoredCount = rail.querySelectorAll('.sf-gallery__thumb').length;
    out.restoredRailH = rail.getBoundingClientRect().height;
  }

  /* dots (the <=480px indicator that replaces the strip) */
  out.dots = dots ? {
    display: cs(dots).display, count: dots.querySelectorAll('.sf-gallery__dot').length,
    gap: cs(dots).gap, rect: R(dots),
  } : null;
  out.railDisplayed = rail ? cs(rail).display !== 'none' : false;
  return out;
}

(async () => {
  const browser = await chromium.launch();
  const results = {};
  const notes = [];

  for (const width of WIDTHS) {
    const ctx = await browser.newContext({
      viewport: { width, height: 1000 },
      deviceScaleFactor: 1,
      httpCredentials: { username: USER, password: PASS },
      userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    });
    const page = await ctx.newPage();
    const url = `${DEV}/formulas/${SLUG}/`;
    const resp = await page.goto(url, { waitUntil: 'load', timeout: 60000 });
    await page.waitForTimeout(1200);
    const data = await page.evaluate(measure, COUNTS);
    data.httpStatus = resp ? resp.status() : null;
    if (data.error || data.host !== 'dev.zxpet.com' || !data.stage) {
      notes.push(`viewport ${width}: PAGE GUARD FAILED — ${JSON.stringify({ err: data.error, host: data.host, path: data.path, title: data.title })}`);
    }
    results[width] = data;
    await ctx.close();
  }

  await browser.close();
  process.stdout.write(JSON.stringify({ slug: SLUG, widths: results, notes }, null, 1) + '\n');
  /* ---- readable digest on stderr ---- */
  const out = [];
  /* Capacity is read OFF THE MEASUREMENTS, not off a formula: for a column the
     largest n whose rail height is still <= the stage height, for a row the
     largest n whose last tile still ends inside the box. An arithmetic guess
     here once produced "5" for a viewport where 6 plainly fit. */
  const capacity = (d) => {
    if (!d || !d.growth) { return null; }
    if (!d.railDisplayed) { return 'no strip (dots)'; }
    const col = d.rail && d.rail.direction === 'column';
    let best = null;
    for (const n of COUNTS) {
      const g = d.growth[n];
      if (!g) { continue; }
      const fits = col ? (g.railRectH <= g.stageH + 0.01)
                       : (g.lastTileClippedX <= 0.01 && g.lastTileClippedY <= 0.01);
      /* Column: slack = how much of the stage height is left under the last
         tile. Row: slack = the gap between the last tile's right edge and the
         box's right edge — POSITIVE means blank space, which is the direction
         the report reads it in. */
      if (fits) { best = { n: g.n, slack: col ? +(g.stageH - g.railRectH).toFixed(2)
                                              : +(-g.lastTileClippedX).toFixed(2) }; }
      else { break; }
    }
    return best ? `${best.n} (slack ${best.slack}px)` : 'none';
  };

  out.push(`PROBE: dev.zxpet.com/formulas/${SLUG}/ — READ ONLY (DOM-clone simulation, no DB write)`);
  out.push('viewport | stage w×h | rail | tile | pitch | tiles | railH | railH−stageH | capacity');
  out.push('---------|-----------|------|------|-------|-------|-------|--------------|---------');
  for (const w of WIDTHS) {
    const d = results[w];
    if (!d || !d.stage) { out.push(`${w} | PAGE GUARD FAILED`); continue; }
    const dir = d.rail ? d.rail.direction : 'n/a';
    const tile = d.tiles && d.tiles[0] ? `${d.tiles[0].w}×${d.tiles[0].h}` : '-';
    const railH = d.rail ? d.rail.rect.h : null;
    out.push([
      w,
      `${d.stage.w}×${d.stage.h}`,
      d.railDisplayed ? dir : 'HIDDEN',
      tile,
      d.pitch,
      d.tileCount,
      railH,
      railH !== null ? +(railH - d.stage.h).toFixed(2) : null,
      capacity(d),
    ].join(' | '));
  }
  out.push('');
  for (const w of WIDTHS) {
    const d = results[w];
    if (!d || !d.growth) continue;
    out.push(`--- viewport ${w} (rail ${d.railDisplayed ? d.rail.direction : 'hidden'}) ---`);
    for (const n of COUNTS) {
      const g = d.growth[n];
      if (!g) continue;
      out.push(`  n=${g.n}  railH=${g.railRectH}  stageH=${g.stageH}  over-stage=${g.railExceedsStageBy}` +
        `  tabsTop=${g.tabsTop}  mediaH=${g.mediaH}  docH=${g.docH}` +
        `  scrollW/clientW=${g.railScrollW}/${g.railClientW}  clipX=${g.lastTileClippedX}  clipY=${g.lastTileClippedY}`);
    }
  }
  if (notes.length) { out.push(''); out.push('NOTES: ' + notes.join(' || ')); }
  process.stderr.write(out.join('\n') + '\n');
  process.exit(notes.length ? 1 : 0);
})();

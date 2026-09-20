const { chromium } = require('playwright-core');
const OUT = '/Users/meng/WorkBuddy/sinofresh外贸网站建设/screenshots/statbar-merge';
const mode = process.argv[2] || 'after';

const consent = async (p) => {
  await p.goto('http://sinofresh.local/', { waitUntil: 'domcontentloaded' });
  await p.evaluate(() => localStorage.setItem('sf_cookie_consent', JSON.stringify({ necessary: true, marketing: false })));
  await p.reload({ waitUntil: 'domcontentloaded' });
  await p.evaluate(() => document.fonts.ready);
};

(async () => {
  const b = await chromium.launch({ channel: 'chrome' });

  if (mode === 'before') {
    for (const W of [1440, 375]) {
      const ctx = await b.newContext({ viewport: { width: W, height: 900 }, isMobile: W < 500 });
      const p = await ctx.newPage();
      await consent(p);
      await p.waitForTimeout(900);
      const r = await p.evaluate(() => {
        const H = (s) => { const e = document.querySelector(s); return e ? Math.round(e.getBoundingClientRect().height) : null; };
        return { docH: document.documentElement.scrollHeight, snap: H('.sf-snapshot'),
                 glance: H(document.querySelectorAll('.sf-stats')[0].closest('section')) };
      });
      console.log('BEFORE W=' + W, JSON.stringify(r));
      await ctx.close();
    }
    await b.close();
    return;
  }

  // ---------- 1. layout metrics across the breakpoints ----------
  for (const W of [1440, 1280, 1200, 1024, 900, 768, 600, 420, 375]) {
    const ctx = await b.newContext({ viewport: { width: W, height: 900 }, isMobile: W < 500 });
    const p = await ctx.newPage();
    await consent(p);
    await p.waitForTimeout(800);
    const r = await p.evaluate(() => {
      const bar = document.querySelector('.sf-statbar');
      const grid = document.querySelector('.wp-block-columns.sf-statbar__grid');
      const cells = [...grid.querySelectorAll(':scope > .sf-statbar__cell')];
      const cs = getComputedStyle(grid);
      const num = cells[5].querySelector('.sf-statbar__num');
      const lab = cells[0].querySelector('.sf-statbar__label');
      const dot = getComputedStyle(cells[0], '::before');
      let cellOver = [];
      cells.forEach((c, i) => { if (c.scrollWidth > c.clientWidth + 1) cellOver.push(i + 1); });
      const labOver = cells.map((c, i) => {
        const l = c.querySelector('.sf-statbar__label');
        const r2 = document.createRange(); r2.selectNodeContents(l);
        const lines = [...r2.getClientRects()].filter((x) => x.height > 2).length;
        return lines > 1 ? (i + 1) + ':' + lines : null;
      }).filter(Boolean);
      const numLines = (() => { const r3 = document.createRange(); r3.selectNodeContents(num);
        return [...r3.getClientRects()].filter((x) => x.height > 2).length; })();
      return {
        secH: Math.round(bar.getBoundingClientRect().height),
        gridH: Math.round(grid.getBoundingClientRect().height),
        cols: cs.gridTemplateColumns.split(' ').length,
        rows: new Set(cells.map((c) => Math.round(c.getBoundingClientRect().top))).size,
        cells: cells.length,
        numFs: getComputedStyle(num).fontSize, labFs: getComputedStyle(lab).fontSize,
        numLines, labWrap: labOver, cellOver,
        dot: dot.content === 'none' ? 'none' : dot.width + ' ' + dot.backgroundColor + ' r' + dot.borderRadius,
        panelBg: cs.backgroundColor, panelBorder: cs.borderTopWidth,
        ov: document.documentElement.scrollWidth - document.documentElement.clientWidth,
        docH: document.documentElement.scrollHeight,
      };
    });
    console.log('W=' + W, JSON.stringify(r));
    await ctx.close();
  }

  // ---------- 2. desktop shots + hover + stagger ----------
  const ctx = await b.newContext({ viewport: { width: 1440, height: 900 } });
  const p = await ctx.newPage();
  await consent(p);

  // (a) reveal sequence: park just above the bar, then step in
  const top = await p.evaluate(() => {
    const b2 = document.querySelector('.sf-statbar');
    return Math.round(b2.getBoundingClientRect().top + window.scrollY);
  });
  await p.evaluate((y) => scrollTo(0, y - innerHeight + 40), top);
  await p.waitForTimeout(400);
  const barBox = await p.evaluate(() => {
    const b3 = document.querySelector('.sf-statbar');
    const r = b3.getBoundingClientRect();
    return { y: Math.round(r.top + scrollY), h: Math.round(r.height) };
  });
  await p.screenshot({ path: OUT + '/reveal1-1440-before.png', clip: { x: 0, y: barBox.y, width: 1440, height: barBox.h }, fullPage: true });

  await p.evaluate((y) => scrollTo(0, y - 120), top);
  await p.waitForTimeout(200);
  const opa = await p.evaluate(() => [...document.querySelectorAll('.sf-statbar__cell')].map((c) => +(getComputedStyle(c).opacity)));
  await p.screenshot({ path: OUT + '/reveal2-1440-mid.png', clip: { x: 0, y: barBox.y, width: 1440, height: barBox.h }, fullPage: true });
  await p.waitForTimeout(1400);
  const opaEnd = await p.evaluate(() => [...document.querySelectorAll('.sf-statbar__cell')].map((c) => +(getComputedStyle(c).opacity)));
  const stagger = await p.evaluate(() => ({
    stag: document.querySelector('.sf-statbar').classList.contains('sf-stagger'),
    done: document.querySelector('.sf-statbar').classList.contains('sf-stagger-in'),
    delays: [...document.querySelectorAll('.sf-statbar__cell')].map((c) => c.style.transitionDelay),
    figures: [...document.querySelectorAll('.sf-statbar__num')].map((n) => n.textContent),
    fields: [...document.querySelectorAll('.sf-statbar__num')].map((n) => (n.field ? n.field.to : null)),
  }));
  console.log('STAGGER mid opacity', JSON.stringify(opa));
  console.log('STAGGER end opacity', JSON.stringify(opaEnd));
  console.log('STAGGER', JSON.stringify(stagger));
  await p.screenshot({ path: OUT + '/after-1440-statbar.png', clip: { x: 0, y: barBox.y, width: 1440, height: barBox.h }, fullPage: true });

  // (b) hover the "15,000㎡" cell (6th) and the first cell
  for (const [idx, name] of [[5, 'hover-cell6'], [0, 'hover-cell1']]) {
    await p.locator('.sf-statbar__cell').nth(idx).hover();
    await p.waitForTimeout(320);
    const h = await p.evaluate((i) => {
      const c = document.querySelectorAll('.sf-statbar__cell')[i];
      const n = c.querySelector('.sf-statbar__num');
      return { numTransform: getComputedStyle(n).transform, color: getComputedStyle(n).color,
               cellTransform: getComputedStyle(c).transform };
    }, idx);
    console.log(name, JSON.stringify(h));
    if (idx === 5) await p.screenshot({ path: OUT + '/hover-1440-statbar.png', clip: { x: 0, y: barBox.y, width: 1440, height: barBox.h }, fullPage: true });
  }
  await p.mouse.move(5, 5);
  await ctx.close();

  // ---------- 3. tablet 768 + phone 375/420 shots ----------
  for (const W of [768, 420, 375]) {
    const c2 = await b.newContext({ viewport: { width: W, height: 900 }, isMobile: W < 500 });
    const p2 = await c2.newPage();
    await consent(p2);
    await p2.evaluate(() => { const b4 = document.querySelector('.sf-statbar'); b4.scrollIntoView({ block: 'center' }); });
    await p2.waitForTimeout(1800);
    const box = await p2.evaluate(() => {
      const b5 = document.querySelector('.sf-statbar');
      const r = b5.getBoundingClientRect();
      return { y: Math.round(r.top + scrollY), h: Math.round(r.height) };
    });
    await p2.screenshot({ path: `${OUT}/${mode}-${W}-statbar.png`, clip: { x: 0, y: box.y, width: W, height: box.h }, fullPage: true });
    console.log('phone/tablet shot W=' + W, JSON.stringify(box));
    await c2.close();
  }

  // ---------- 4. reduced motion ----------
  const rm = await b.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const pr = await rm.newPage();
  await consent(pr);
  await pr.evaluate(() => document.querySelector('.sf-statbar').scrollIntoView({ block: 'center' }));
  await pr.waitForTimeout(600);
  await pr.locator('.sf-statbar__cell').nth(5).hover();
  await pr.waitForTimeout(250);
  const rmv = await pr.evaluate(() => {
    const bar = document.querySelector('.sf-statbar');
    const cells = [...document.querySelectorAll('.sf-statbar__cell')];
    const n = cells[5].querySelector('.sf-statbar__num');
    return { stag: bar.classList.contains('sf-stagger'), opac: cells.map((c) => +getComputedStyle(c).opacity),
             numTransform: getComputedStyle(n).transform, figures: [...document.querySelectorAll('.sf-statbar__num')].map((x) => x.textContent),
             secPending: document.querySelector('.sf-statbar').classList.contains('sf-pending') };
  });
  console.log('REDUCED-MOTION', JSON.stringify(rmv));
  await rm.close();

  // ---------- 5. no-JS sanity ----------
  const nj = await b.newContext({ viewport: { width: 1440, height: 900 }, javaScriptEnabled: false });
  const pn = await nj.newPage();
  await pn.goto('http://sinofresh.local/', { waitUntil: 'domcontentloaded' });
  await pn.waitForTimeout(600);
  const njv = await pn.evaluate(() => {
    const cells = [...document.querySelectorAll('.sf-statbar__cell')];
    return { cells: cells.length, opac: cells.map((c) => +getComputedStyle(c).opacity),
             figures: [...document.querySelectorAll('.sf-statbar__num')].map((x) => x.textContent) };
  }).catch(() => 'n/a (no JS context)');
  console.log('NO-JS', JSON.stringify(njv));
  await nj.close();

  await b.close();
})();

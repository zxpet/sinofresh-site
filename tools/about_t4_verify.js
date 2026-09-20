/* Task 4 verification: Core Values — five boxes on one height, both widths.
   Writes tools/_about_t4.json */
const fs = require('fs');
const pw = require('/Users/meng/.workbuddy/binaries/node/workspace/node_modules/playwright-core');
const CHROME = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';
const OUT = {};

const PROBE = () => {
  const secs = [...document.querySelectorAll('.wp-site-blocks > *')];
  const sec = secs.find(s => { const h = s.querySelector('h2'); return h && /core values/i.test(h.textContent); });
  const cols = sec.querySelector('.wp-block-columns');
  const colEls = [...cols.children];
  const cards = colEls.map(c => c.querySelector(':scope > .wp-block-group'));
  const topRows = new Map();
  colEls.forEach((c, i) => { const t = Math.round(c.getBoundingClientRect().top); topRows.set(t, (topRows.get(t) || []).concat(i)); });
  const heights = cards.map(c => +c.getBoundingClientRect().height.toFixed(1));
  const bottoms = cards.map(c => +c.getBoundingClientRect().bottom.toFixed(1));
  const widths = cards.map(c => +c.getBoundingClientRect().width.toFixed(1));
  return {
    sectionH: +sec.getBoundingClientRect().height.toFixed(1),
    colsDisplay: getComputedStyle(cols).display,
    colDisplay: getComputedStyle(colEls[0]).display,
    cardFlex: getComputedStyle(cards[0]).flex,
    cardAlignSelf: getComputedStyle(cards[0]).alignSelf,
    colH: colEls.map(c => +c.getBoundingClientRect().height.toFixed(1)),
    cardH: heights, cardBottom: bottoms, cardWidth: widths,
    sameHeight: new Set(heights).size === 1,
    maxSpread: +(Math.max(...heights) - Math.min(...heights)).toFixed(1),
    sameBottom: new Set(bottoms.map(b => b.toFixed(0))).size === 1,
    sameWidth: new Set(widths.map(w => w.toFixed(0))).size === 1,
    rows: [...topRows.entries()].map(([t, i]) => t + ':' + i.join(',')),
    sections: secs.map(s => { const h2 = s.querySelector('h2'); return (h2 ? h2.textContent.trim() : (s.tagName + ' ' + (s.className || '').split(' ').slice(0, 2).join(' '))).slice(0, 22) + '=' + s.getBoundingClientRect().height.toFixed(1); }),
    docH: document.documentElement.scrollHeight,
    hScroll: document.documentElement.scrollWidth - document.documentElement.clientWidth
  };
};

(async () => {
  const b = await pw.chromium.launch({ executablePath: CHROME, headless: true });
  for (const w of [1440, 375]) {
    const ctx = await b.newContext({ viewport: { width: w, height: 900 } });
    const page = await ctx.newPage();
    await page.goto('http://sinofresh.local/about/', { waitUntil: 'networkidle' });
    const reject = page.locator('button:has-text("Reject Non-Essential")');
    if (await reject.count()) await reject.first().click({ force: true }).catch(() => { });
    await page.evaluate(async () => { const s = Math.round(innerHeight * 0.8); for (let y = 0; y < document.body.scrollHeight; y += s) { scrollTo(0, y); await new Promise(r => setTimeout(r, 70)); } scrollTo(0, 0); });
    await page.waitForTimeout(1100);
    OUT[w] = await page.evaluate(PROBE);
    await ctx.close();
  }
  await b.close();
  fs.writeFileSync('/Users/meng/WorkBuddy/sinofresh外贸网站建设/tools/_about_t4.json', JSON.stringify(OUT, null, 1));
  console.log('done');
})();

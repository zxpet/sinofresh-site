/* Configurator chrome probe (phone) — batch 1.
   node cfg_probe.js before|after  -> prints metrics for the 8 dosage pages */
const { chromium } = require('playwright-core');

const LABEL = process.argv[2] || 'before';
const PAGES = [
  ['soft-chews', '/products/soft-chews/'],
  ['tablets', '/products/tablets/'],
  ['powders', '/products/powders/'],
  ['pastes', '/products/pastes/'],
  ['drops', '/products/drops/'],
  ['liquids', '/products/liquids/'],
  ['fish-oil', '/products/fish-oil/'],
  ['dental-chews', '/products/dental-chews/'],
];

const collect = () => {
  const px = (v) => Math.round(parseFloat(v) || 0);
  const g = (s) => document.querySelector(s);
  const m = (s) => {
    const el = g(s);
    if (!el) return null;
    const cs = getComputedStyle(el);
    const b = el.getBoundingClientRect();
    return {
      h: px(b.height),
      w: px(b.width),
      top: px(b.top + window.scrollY),
      pos: cs.position,
      bottom: cs.bottom,
      z: cs.zIndex,
      disp: cs.display,
      ov: cs.overflow,
      minH: cs.minHeight,
      pad: `${px(cs.paddingTop)}/${px(cs.paddingBottom)}`,
      fs: cs.fontSize,
    };
  };
  const all = (s) => [...document.querySelectorAll(s)].map((el) => px(el.getBoundingClientRect().height));
  return {
    present: !!g('.configurator'),
    configurator: m('.configurator'),
    options: m('.configurator__options'),
    summaryCol: m('.configurator__summary-col'),
    summary: m('.configurator__summary'),
    progress: m('.configurator__progress'),
    note: m('.configurator__note'),
    submit: m('.configurator__submit:not(.configurator__submit--bar)'),
    mobilebar: m('.configurator__mobilebar'),
    barSubmit: m('.configurator__submit--bar'),
    reset: m('.configurator__reset'),
    copy: m('.configurator__copy'),
    itemHeights: all('.configurator__item').slice(0, 6),
    groupHeights: all('.configurator__group'),
    rowHeights: all('.configurator__summary-row').slice(0, 3),
    docH: document.documentElement.scrollHeight,
  };
};

(async () => {
  const browser = await chromium.launch({ channel: 'chrome' });
  const out = {};
  for (const [name, url] of PAGES) {
    const ctx = await browser.newContext({ viewport: { width: 375, height: 812 }, isMobile: true, hasTouch: true });
    const page = await ctx.newPage();
    await page.goto('http://sinofresh.local' + url, { waitUntil: 'networkidle', timeout: 60000 });
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(300);
    out[name] = await page.evaluate(collect);
    await ctx.close();
  }
  await browser.close();
  console.log(`--- ${LABEL} ---`);
  for (const [k, v] of Object.entries(out)) {
    if (!v.present) {
      console.log(`${k}: NO CONFIGURATOR`);
      continue;
    }
    const g = (x, f) => (x == null ? '-' : typeof f === 'function' ? f(x) : x);
    console.log(
      `${k}: summary h=${v.summary.h} pos=${v.summary.pos} maxH=${v.summary.minH} ovf=${v.summary.ov} | opts h=${v.options.h} | bar=${v.mobilebar ? v.mobilebar.disp + '/' + v.mobilebar.h : 'absent'} | submit=${v.submit ? v.submit.h : '-'} reset=${v.reset ? v.reset.h : '-'} copy=${v.copy ? v.copy.h : '-'} item=${v.itemHeights[0]} note=${v.note ? v.note.h : '-'} docH=${v.docH}`
    );
  }
})();

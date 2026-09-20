/* Batch-2 probe for about/quality/factory-tour/services/contact.
 *
 *   node batch1_probe.js before   -> screenshots/batch1-before.json
 *   node batch1_probe.js after    -> screenshots/batch1-after.json
 *
 * Reports, per page:
 *   - at 375 / 420 / 768 : document height, horizontal overflow, every
 *     .wp-block-columns (class, visible column count, display, tracks /
 *     flex direction, per-column w/h), every top-level section (class,
 *     padding, height) and the configurator chrome metrics.
 *   - at 1440            : document height + per-section geometry fingerprint
 *     used for the desktop regression diff.
 *
 * Determinism: images are forced eager and fonts/images awaited before any
 * measurement (see MEMORY.md — otherwise lazy 0x0 boxes and woff2 timing
 * produce phantom diffs).
 */
const { chromium } = require('playwright-core');
const fs = require('fs');
const path = require('path');

const LABEL = process.argv[2] || 'before';
const BASE = 'http://sinofresh.local';

const PAGES = [
  ['about', '/about/', 'batch2'],
  ['quality', '/quality/', 'batch2'],
  ['factory-tour', '/factory-tour/', 'batch2'],
  ['services', '/services/', 'batch2'],
  ['contact', '/contact/', 'batch2'],
];

const MOBILE = [
  [375, 812, '375'],
  [420, 900, '420'],
  [768, 1024, '768'],
];

async function settle(page) {
  await page.evaluate(() => {
    document.querySelectorAll('img').forEach((i) => {
      i.loading = 'eager';
      i.decoding = 'sync';
    });
  });
  await page.evaluate(async () => {
    if (document.fonts && document.fonts.ready) await document.fonts.ready;
  });
  await page.evaluate(async () => {
    const imgs = [...document.querySelectorAll('img')];
    await Promise.all(
      imgs.map((i) =>
        i.complete && i.naturalWidth
          ? Promise.resolve()
          : new Promise((r) => {
              i.addEventListener('load', r, { once: true });
              i.addEventListener('error', r, { once: true });
              setTimeout(r, 4000);
            })
      )
    );
    window.scrollTo(0, document.body.scrollHeight);
  });
  await page.waitForTimeout(350);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(250);
}

function mobileCollect() {
  const px = (v) => Math.round(parseFloat(v) || 0);
  const doc = document.documentElement;

  const cols = [...document.querySelectorAll('.wp-block-columns')].map((el, i) => {
    const cs = getComputedStyle(el);
    const kids = [...el.children].filter((c) => {
      const k = getComputedStyle(c);
      return k.display !== 'none';
    });
    const sec = el.closest('section');
    return {
      i,
      cls: el.className.replace(/\s+/g, ' ').trim(),
      section: sec ? sec.className.replace(/\s+/g, ' ').trim().slice(0, 60) : null,
      display: cs.display,
      tracks: cs.gridTemplateColumns,
      dir: cs.flexDirection,
      wrap: cs.flexWrap,
      n: kids.length,
      widths: kids.map((k) => px(k.getBoundingClientRect().width)),
      heights: kids.map((k) => px(k.getBoundingClientRect().height)),
      tops: kids.map((k) => px(k.getBoundingClientRect().top)),
      h: px(el.getBoundingClientRect().height),
    };
  });

  const sections = [...document.querySelectorAll('section')].map((el, i) => {
    const cs = getComputedStyle(el);
    return {
      i,
      cls: el.className.replace(/\s+/g, ' ').trim().slice(0, 70),
      pt: px(cs.paddingTop),
      pb: px(cs.paddingBottom),
      mt: px(cs.marginTop),
      h: px(el.getBoundingClientRect().height),
      heading: (() => {
        const h = el.querySelector('h1,h2,h3');
        return h ? h.textContent.replace(/\s+/g, ' ').trim().slice(0, 70) : null;
      })(),
    };
  });

  // configurator chrome
  const cfg = (() => {
    const form = document.querySelector('.sf-configurator, form[id^="sf-config"], .sf-cfg');
    if (!form) return null;
    const btnHeights = [...form.querySelectorAll('button, input[type="button"], a.sf-cfg__reset')]
      .map((b) => ({
        label: (b.textContent || b.value || '').replace(/\s+/g, ' ').trim().slice(0, 24),
        h: px(b.getBoundingClientRect().height),
        cls: b.className.replace(/\s+/g, ' ').trim().slice(0, 40),
      }))
      .filter((b) => b.h);
    const summary = form.querySelector('.sf-cfg__summary, .sf-summary, aside');
    const submit = form.querySelector('[type="submit"], button.sf-cfg__submit');
    return {
      found: true,
      buttons: btnHeights,
      summaryH: summary ? px(summary.getBoundingClientRect().height) : null,
      summaryTop: summary ? px(summary.getBoundingClientRect().top) : null,
      summaryPos: summary ? getComputedStyle(summary).position : null,
      submitH: submit ? px(submit.getBoundingClientRect().height) : null,
    };
  })();

  const offenders = [...document.querySelectorAll('section, .wp-block-columns')]
    .filter((el) => {
      const cs = getComputedStyle(el);
      return px(cs.paddingTop) >= 56 || px(cs.paddingBottom) >= 56;
    })
    .map((el) => ({
      cls: el.className.replace(/\s+/g, ' ').trim().slice(0, 60),
      pt: px(getComputedStyle(el).paddingTop),
      pb: px(getComputedStyle(el).paddingBottom),
    }));

  return {
    docH: doc.scrollHeight,
    docW: doc.clientWidth,
    scrollW: doc.scrollWidth,
    overflowX: doc.scrollWidth - doc.clientWidth,
    heroInner: (() => {
      const h = document.querySelector('.sf-hero-inner');
      if (!h) return null;
      const cs = getComputedStyle(h);
      return { pt: px(cs.paddingTop), pb: px(cs.paddingBottom), mt: px(cs.marginTop), mb: px(cs.marginBottom) };
    })(),
    cols,
    sections,
    cfg,
    offenders,
  };
}

function desktopCollect() {
  const px = (v) => Math.round(parseFloat(v) || 0);
  const doc = document.documentElement;
  return {
    docH: doc.scrollHeight,
    sections: [...document.querySelectorAll('section')].map((el, i) => {
      const b = el.getBoundingClientRect();
      return {
        i,
        cls: el.className.replace(/\s+/g, ' ').trim().slice(0, 60),
        h: px(b.height),
        w: px(b.width),
        top: px(b.top + window.scrollY),
      };
    }),
    cols: [...document.querySelectorAll('.wp-block-columns')].map((el, i) => ({
      i,
      cls: el.className.replace(/\s+/g, ' ').trim().slice(0, 60),
      h: px(el.getBoundingClientRect().height),
      w: px(el.getBoundingClientRect().width),
      tracks: getComputedStyle(el).gridTemplateColumns,
    })),
  };
}

(async () => {
  const browser = await chromium.launch({ channel: 'chrome' });
  const out = { label: LABEL, pages: {} };

  for (const [name, url, kind] of PAGES) {
    const rec = { url, kind, viewports: {}, jsErrors: [] };
    for (const [w, h, tag] of MOBILE) {
      const ctx = await browser.newContext({
        viewport: { width: w, height: h },
        deviceScaleFactor: 1,
        isMobile: w <= 768,
        hasTouch: w <= 768,
      });
      const page = await ctx.newPage();
      page.on('pageerror', (e) => rec.jsErrors.push(String(e).slice(0, 160)));
      const resp = await page.goto(BASE + url, { waitUntil: 'networkidle', timeout: 60000 });
      rec.status = resp ? resp.status() : null;
      await settle(page);
      rec.viewports[tag] = await page.evaluate(mobileCollect);
      await ctx.close();
    }
    // desktop fingerprint
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });
    const page = await ctx.newPage();
    await page.goto(BASE + url, { waitUntil: 'networkidle', timeout: 60000 });
    await settle(page);
    rec.viewports['1440'] = await page.evaluate(desktopCollect);
    await ctx.close();
    out.pages[name] = rec;
    console.error(`  ${name}: 375=${rec.viewports['375'].docH} 420=${rec.viewports['420'].docH} 768=${rec.viewports['768'].docH} 1440=${rec.viewports['1440'].docH}`);
  }

  await browser.close();
  const dest = path.resolve(__dirname, '..', 'screenshots', `batch2-${LABEL}.json`);
  fs.writeFileSync(dest, JSON.stringify(out, null, 1));
  console.error(`written ${dest}`);
})();

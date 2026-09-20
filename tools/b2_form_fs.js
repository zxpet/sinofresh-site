const { chromium } = require('playwright-core');
(async () => {
  const b = await chromium.launch({ channel: 'chrome' });
  const ctx = await b.newContext({ viewport: { width: 375, height: 900 }, isMobile: true, hasTouch: true });
  const p = await ctx.newPage();
  await p.goto('http://sinofresh.local/factory-tour/', { waitUntil: 'networkidle' });
  const r = await p.evaluate(() => {
    const out = [];
    for (const el of document.querySelectorAll('.gform_fields input:not([type=hidden]):not([type=submit]), .gform_fields select, .gform_fields textarea')) {
      const fs = getComputedStyle(el).fontSize;
      out.push({ tag: el.tagName, type: el.type || '', cls: (el.className || '').slice(0, 40), fs, inline: el.getAttribute('style') || null, parentCls: (el.parentElement.className || '').slice(0, 44) });
    }
    return out;
  });
  r.forEach((x) => console.log(x.tag + '[' + x.type + '] fs=' + x.fs + ' cls=' + x.cls + ' parent=' + x.parentCls + (x.inline ? ' INLINE=' + x.inline : '')));
  await b.close();
})();

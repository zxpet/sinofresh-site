// Gravity Forms Form 2 probe: rendered field inventory + geometry + screenshots.
// Usage: node gf2_probe.js <tag>   (tag = before | after)
const { chromium } = require('playwright-core');
const fs = require('fs');
const path = require('path');

const EXEC = '/Users/meng/.agent-browser/browsers/chrome-153.0.8010.36/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';
const tag = process.argv[2] || 'probe';
const OUT = '/Users/meng/WorkBuddy/sinofresh外贸网站建设/screenshots/gf-form2';
const PAGES = [
  ['home', 'http://sinofresh.local/'],
  ['contact', 'http://sinofresh.local/contact/'],
  ['soft-chews', 'http://sinofresh.local/soft-chews/'],
  ['factory-tour', 'http://sinofresh.local/factory-tour/'],
];
// addStyleTag breaks screenshot stability detection on this site -> addInitScript
const INIT_CSS = `
  document.addEventListener('DOMContentLoaded', function () {
    var s = document.createElement('style');
    s.id = 'sf-shot-css';
    s.textContent = '.sf-header{position:static!important}.sf-cookie-banner{display:none!important}';
    document.head.appendChild(s);
  });
`;

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const b = await chromium.launch({ executablePath: EXEC, headless: true });
  const report = {};

  for (const vp of [{ width: 1440, height: 900 }, { width: 375, height: 812 }]) {
    const ctx = await b.newContext({ viewport: vp, deviceScaleFactor: 2 });
    await ctx.addInitScript(INIT_CSS);
    const page = await ctx.newPage();
    page.setDefaultTimeout(25000);

    for (const [name, url] of PAGES) {
      const key = `${name}@${vp.width}`;
      try {
        await page.goto(url, { waitUntil: 'load', timeout: 30000 });
        await page.waitForSelector('.gform_wrapper .gform_fields', { timeout: 20000 });
        await page.evaluate(() => document.fonts.ready);
        await page.waitForTimeout(500);

        const info = await page.evaluate(() => {
          const w = document.querySelector('.gform_wrapper');
          const form = w && w.querySelector('form');
          const formId = form ? (form.getAttribute('data-formid') || '') : '';
          const fields = [...document.querySelectorAll('.gform_fields > .gfield')].map(el => {
            const lab = el.querySelector('.gfield_label, legend');
            const ctrl = el.querySelector('input,select,textarea');
            const cls = (el.className || '').toString();
            const wMatch = cls.match(/gfield--width-(\w+)/);
            const tMatch = cls.match(/gfield--type-(\w+)/);
            const b = el.getBoundingClientRect();
            return {
              id: (el.id || '').replace('field_2_', '').replace('field_', ''),
              type: tMatch ? tMatch[1] : '?',
              width: wMatch ? wMatch[1] : 'auto',
              label: lab ? lab.textContent.replace(/\s+/g, ' ').trim().slice(0, 34) : '',
              name: ctrl ? ctrl.getAttribute('name') : '',
              hidden: cls.includes('gfield--type-hidden') || (ctrl && ctrl.type === 'hidden'),
              top: +(b.top + scrollY).toFixed(1),
              h: +b.height.toFixed(1),
              left: +b.left.toFixed(1),
              w: +b.width.toFixed(1),
            };
          });
          // row grouping by top (visual rows)
          const rows = {};
          fields.filter(f => !f.hidden).forEach(f => { const k = Math.round(f.top); (rows[k] = rows[k] || []).push(f.id + ':' + f.width); });
          const footer = document.querySelector('.gform_footer');
          const btn = document.querySelector('.gform_button, #gform_submit_button_2');
          const below = [];
          if (btn) {
            let n = btn.closest('.gform_footer');
            while (n && n.nextElementSibling) { n = n.nextElementSibling; below.push((n.className || '').toString().slice(0, 50) + ' | ' + n.textContent.replace(/\s+/g, ' ').trim().slice(0, 60)); if (below.length > 3) break; }
          }
          return {
            formId,
            wrapperH: w ? +w.getBoundingClientRect().height.toFixed(1) : null,
            wrapperW: w ? +w.getBoundingClientRect().width.toFixed(1) : null,
            footerH: footer ? +footer.getBoundingClientRect().height.toFixed(1) : null,
            fieldCount: fields.filter(f => !f.hidden).length,
            totalCount: fields.length,
            cols: getComputedStyle(document.querySelector('.gform_fields')).gridTemplateColumns,
            fields,
            rows: Object.keys(rows).sort((a, b) => a - b).map(k => rows[k].join(' + ')),
            buttonText: btn ? btn.textContent.trim() : '',
            nodesBelowButton: below,
            hint: (() => {
              const el = document.querySelector('.sf-gf-wa-hint');
              if (!el) return null;
              const cs = getComputedStyle(el);
              const hb = el.getBoundingClientRect();
              const bb = btn ? btn.getBoundingClientRect() : null;
              return {
                text: el.textContent.trim(),
                fontSize: cs.fontSize,
                color: cs.color,
                textAlign: cs.textAlign,
                display: cs.display,
                w: +hb.width.toFixed(1),
                h: +hb.height.toFixed(1),
                gapFromButton: bb ? +(hb.top - bb.bottom).toFixed(1) : null,
                lines: (() => { const r = document.createRange(); r.selectNodeContents(el); return new Set([...r.getClientRects()].map(x => Math.round(x.top))).size; })(),
              };
            })(),
            required: {
              classes: document.querySelectorAll('.gform_fields .gfield_contains_required').length,
              aria: document.querySelectorAll('.gform_fields [aria-required="true"]').length,
              labels: [...document.querySelectorAll('.gform_fields .gfield_contains_required')].map(el => {
                const l = el.querySelector('.gfield_label, legend');
                return l ? l.textContent.replace(/\s+/g, ' ').replace('(Required)', '').trim() : '?';
              }),
            },
            overflow: {
              docW: document.documentElement.scrollWidth,
              clientW: document.documentElement.clientWidth,
              overflowPx: document.documentElement.scrollWidth - document.documentElement.clientWidth,
              offscreen: [...document.querySelectorAll('.gform_wrapper *')].filter(el => {
                const r = el.getBoundingClientRect();
                return r.width > 0 && (r.right > document.documentElement.clientWidth + 1 || r.left < -1);
              }).slice(0, 5).map(el => (el.tagName + '.' + (el.className || '').toString().split(' ')[0] + ' right=' + el.getBoundingClientRect().right.toFixed(0))),
            },
          };
        });
        report[key] = info;

        const el = await page.$('.gform_wrapper');
        await el.screenshot({ path: path.join(OUT, `${tag}-${name}-${vp.width}.png`), animations: 'disabled', timeout: 20000 });
        const h = info.hint;
        console.log(`OK   ${key}  fields=${info.fieldCount}(visible)/${info.totalCount}  wrapperH=${info.wrapperH}  req=${info.required.classes}  hint=${h ? h.fontSize + '/' + h.color + '/gap' + h.gapFromButton + 'px/lines' + h.lines : 'null'}  ovf=${info.overflow.overflowPx}px`);
      } catch (e) {
        console.log(`FAIL ${key}: ${e.message.split('\n')[0]}`);
      }
    }
    await ctx.close();
  }
  await b.close();
  fs.writeFileSync(path.join(OUT, `${tag}-report.json`), JSON.stringify(report, null, 2));
  console.log('\n--- rows (desktop home) ---');
  const h = report['home@1440'];
  if (h) {
    console.log('formId=' + h.formId + ' 可见字段=' + h.fieldCount + ' gridCols=' + h.cols + ' 按钮=' + JSON.stringify(h.buttonText));
    h.rows.forEach(r => console.log('  ' + r));
    console.log('必填(' + h.required.classes + '): ' + h.required.labels.join(' | '));
    console.log('提示行:', JSON.stringify(h.hint, null, 0));
    console.log('移动端 375 首页 title: ' + JSON.stringify(report['home@375'] && report['home@375'].overflow));
  }
})().catch(e => { console.error('FATAL', e.message); process.exit(1); });

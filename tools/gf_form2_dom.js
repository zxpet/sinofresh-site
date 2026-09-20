/**
 * 扫描前台 Form 2 的实际 DOM 结构 + 拍改前截图
 * 用法：node tools/gf_form2_dom.js <tag>
 */
const { chromium } = require('playwright-core');
const path = require('path');
const fs = require('fs');
const tag = process.argv[2] || 'before';
const OUT = '/Users/meng/WorkBuddy/sinofresh外贸网站建设/screenshots/gf-form2';
fs.mkdirSync(OUT, { recursive: true });

const PAGES = [
  ['home', 'http://sinofresh.local/'],
  ['contact', 'http://sinofresh.local/contact/'],
  ['soft-chews', 'http://sinofresh.local/products/soft-chews/'],
];

async function preroll(page) {
  await page.evaluate(async () => {
    await document.fonts.ready;
    const h = document.documentElement.scrollHeight;
    for (let y = 0; y < h; y += 700) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 50)); }
    window.scrollTo(0, 0);
    await Promise.all([...document.images].map(i => i.complete ? 0 : new Promise(r => { i.onload = i.onerror = r; })));
  });
  await page.waitForTimeout(300);
}

async function readForm(page) {
  return await page.evaluate(() => {
    const w = document.querySelector('form.gform_wrapper, .gform_wrapper form');
    if (!w) return { error: 'no gform_wrapper' };
    const form = w.closest('.gform_wrapper') || w;
    const fields = [...form.querySelectorAll('.gform_fields > .gfield')].map(li => {
      const lab = li.querySelector('.gfield_label');
      const inp = li.querySelector('input,select,textarea');
      const cs = getComputedStyle(li);
      const r = li.getBoundingClientRect();
      return {
        id: li.id,
        type: (li.className.match(/gfield--type-(\w+)/) || [])[1] || '?',
        label: lab ? lab.textContent.trim() : '(no label)',
        width: (li.className.match(/gfield--width-(\w+)/) || [])[1] || 'auto',
        inputName: inp ? inp.getAttribute('name') : null,
        display: cs.display,
        box: { w: Math.round(r.width), h: Math.round(r.height), top: Math.round(r.top + window.scrollY) },
      };
    });
    const wrap = form.getBoundingClientRect();
    const listEl = form.querySelector('.gform_fields');
    const listCS = listEl ? getComputedStyle(listEl) : null;
    return {
      formId: form.id,
      visibleFieldCount: fields.filter(f => f.display !== 'none' && !f.id.includes('field_12')).length,
      totalFieldCount: fields.length,
      listLayout: listCS ? { display: listCS.display, gridTemplateColumns: listCS.gridTemplateColumns, columnGap: listCS.columnGap, rowGap: listCS.rowGap, flexWrap: listCS.flexWrap } : null,
      wrapperBox: { w: Math.round(wrap.width), h: Math.round(wrap.height), top: Math.round(wrap.top + window.scrollY) },
      fields,
    };
  });
}

async function rowGrouping(page) {
  // 按 top 值把字段分行，确认双栏配对
  return await page.evaluate(() => {
    const form = document.querySelector('.gform_wrapper form, form.gform_wrapper');
    if (!form) return null;
    const items = [...form.querySelectorAll('.gform_fields > .gfield')]
      .filter(li => getComputedStyle(li).display !== 'none')
      .map(li => {
        const lab = li.querySelector('.gfield_label');
        const r = li.getBoundingClientRect();
        return { label: lab ? lab.textContent.trim() : '?', top: Math.round(r.top), left: Math.round(r.left), w: Math.round(r.width) };
      });
    const rows = [];
    items.forEach(it => {
      const row = rows.find(rw => Math.abs(rw[0].top - it.top) < 6);
      if (row) row.push(it); else rows.push([it]);
    });
    return rows.map(rw => rw.map(x => x.label + '(' + x.w + 'px)'));
  });
}

async function shoot(page, name, ok = {}) {
  // networkidle never settles on this site (GF ajax + lazy assets) -> use
  // domcontentloaded then explicitly wait for the form markup to appear.
  await page.goto(PAGES.find(p => p[0] === name)[1], { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForSelector('.gform_wrapper .gform_fields', { timeout: 15000 });
  await preroll(page);
  const data = await readForm(page);
  const rows = await rowGrouping(page);
  data.rowGrouping = rows;
  const r = data.wrapperBox;
  if (r && r.w > 0) {
    const h = Math.min(r.h + 40, 2000);
    await page.screenshot({
      path: path.join(OUT, `${tag}-${name}-${page.viewportSize().width}-form.png`),
      clip: { x: 0, y: Math.max(0, r.top - 20), width: page.viewportSize().width, height: h },
      fullPage: true,
    });
  } else {
    // 回退：整段包含 gform 的 section
    await page.screenshot({ path: path.join(OUT, `${tag}-${name}-${page.viewportSize().width}-form.png`), fullPage: true });
  }
  return data;
}

(async () => {
  const out = {};
  const b = await chromium.launch({ channel: 'chrome', args: ['--no-sandbox', '--disable-dev-shm-usage'] });
  const ctx = await b.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  for (const [name] of PAGES) out[name + '_1440'] = await shoot(page, name);
  await ctx.close();

  const mctx = await b.newContext({ viewport: { width: 375, height: 812 }, isMobile: true, hasTouch: true });
  const m = await mctx.newPage();
  for (const [name] of PAGES) out[name + '_375'] = await shoot(m, name);
  await mctx.close();
  await b.close();

  fs.writeFileSync(path.join(OUT, `${tag}-dom.json`), JSON.stringify(out, null, 2));
  for (const k of Object.keys(out)) {
    const d = out[k];
    if (d.error) { console.log(k, 'ERROR', d.error); continue; }
    console.log(`\n### ${k}  form=${d.formId}  visibleFields=${d.visibleFieldCount}  total=${d.totalFieldCount}  wrapper=${d.wrapperBox.w}x${d.wrapperBox.h}`);
    console.log('  layout:', JSON.stringify(d.listLayout));
    d.fields.forEach(f => console.log(`   [${f.id}] ${f.width.padEnd(6)} ${f.type.padEnd(9)} ${f.label}  (${f.box.w}x${f.box.h})`));
    console.log('  rows:');
    (d.rowGrouping || []).forEach((rw, i) => console.log(`    r${i}: ${rw.join('  +  ')}`));
  }
  console.log('\ndone', tag);
})().catch(e => { console.error('FATAL', e); process.exit(1); });

// q1b: Quality 页现状扫描（DOM + 尺寸）
const { chromium } = require('playwright-core');
const EXEC = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';

(async () => {
  const browser = await chromium.launch({ executablePath: EXEC, headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  await page.goto('http://sinofresh.local/quality/', { waitUntil: 'networkidle', timeout: 45000 });
  await page.evaluate(async () => { if (document.fonts) await document.fonts.ready; });

  const SECTIONS = [
    { name: 'Certifications', sel: '.sf-certdetail' },
    { name: 'QC Lab', sel: 'section:nth-of-type(3)' },
    { name: 'QC Steps', sel: 'section:nth-of-type(4)' },
    { name: 'COA', sel: 'section:nth-of-type(5)' },
    { name: 'Palatability', sel: 'section:nth-of-type(6)' },
  ];

  const out = await page.evaluate(() => {
    const res = {};
    const sections = Array.from(document.querySelectorAll('main section, body section')).filter(s => !s.closest('header,footer'));
    res.sections = sections.map((s, i) => {
      const r = s.getBoundingClientRect();
      const h2 = s.querySelector('h2');
      return {
        i: i + 1,
        h2: h2 ? h2.textContent.trim().slice(0, 46) : null,
        cls: s.className.replace(/wp-block-group|has-[a-z-]*-background-color|has-background|is-layout-constrained|wp-container-core-group-is-layout-\w+|wp-block-group-is-layout-constrained/g, '').trim(),
        top: Math.round(r.top + scrollY),
        h: Math.round(r.height)
      };
    });

    // 证书行
    const rows = Array.from(document.querySelectorAll('.sf-certrow'));
    res.cert = {
      containerW: document.querySelector('.sf-certdetail') ? Math.round(document.querySelector('.sf-certdetail').getBoundingClientRect().width) : null,
      count: rows.length,
      rows: rows.map(tr => {
        const mr = tr.querySelector('.sf-certrow__media');
        const br = tr.querySelector('.sf-certrow__body');
        const img = tr.querySelector('img');
        const rr = tr.getBoundingClientRect();
        return {
          name: tr.querySelector('.sf-certrow__name')?.textContent.trim(),
          rowH: Math.round(rr.height),
          mediaW: Math.round(mr.getBoundingClientRect().width),
          mediaH: Math.round(mr.getBoundingClientRect().height),
          bodyW: Math.round(br.getBoundingClientRect().width),
          imgNatural: img ? img.naturalWidth + 'x' + img.naturalHeight : (tr.className.includes('placeholder') ? 'placeholder' : 'none'),
          imgRendered: img ? Math.round(img.getBoundingClientRect().width) + 'x' + Math.round(img.getBoundingClientRect().height) : null,
          hasLink: !!mr.querySelector('a'),
          hasDownload: !!br.querySelector('a[download]'),
          isCard: (() => { const cs = getComputedStyle(mr); return cs.backgroundImage + '|' + cs.backgroundColor + '|' + cs.borderRadius + '|' + cs.boxShadow; })()
        };
      })
    };

    // QC Lab
    const labSec = Array.from(document.querySelectorAll('section')).find(s => s.querySelector('h2')?.textContent.includes('In-House QC'));
    if (labSec) {
      const cols = Array.from(labSec.querySelectorAll('.wp-block-column'));
      res.qcLab = {
        secH: Math.round(labSec.getBoundingClientRect().height),
        colCount: cols.length,
        cols: cols.map(c => {
          const img = c.querySelector('img');
          const grp = c.querySelector('.wp-block-group');
          return {
            h: Math.round(c.getBoundingClientRect().height),
            grpBg: grp ? getComputedStyle(grp).backgroundColor : null,
            grpPad: grp ? getComputedStyle(grp).paddingTop + '/' + getComputedStyle(grp).paddingLeft : null,
            grpHasBack: grp ? grp.className.includes('has-background') : null,
            h3: c.querySelector('h3')?.textContent.trim(),
            img: img ? img.getAttribute('src').split('/').pop() : null,
            alt: img ? img.getAttribute('alt') : null,
            imgRendered: img ? Math.round(img.getBoundingClientRect().width) + 'x' + Math.round(img.getBoundingClientRect().height) : null
          };
        })
      };
    }

    // QC Steps
    const stSec = Array.from(document.querySelectorAll('section')).find(s => s.querySelector('h2')?.textContent.includes('Every Step'));
    if (stSec) {
      res.qcSteps = {
        secH: Math.round(stSec.getBoundingClientRect().height),
        colGroups: stSec.querySelectorAll(':scope .wp-block-columns').length,
        items: Array.from(stSec.querySelectorAll('.wp-block-column')).map(c => ({
          h: Math.round(c.getBoundingClientRect().height),
          num: c.querySelector('p')?.textContent.trim(),
          h3: c.querySelector('h3')?.textContent.trim(),
          img: c.querySelector('img') ? c.querySelector('img').getAttribute('src').split('/').pop() : null,
          imgRendered: c.querySelector('img') ? Math.round(c.querySelector('img').getBoundingClientRect().width) + 'x' + Math.round(c.querySelector('img').getBoundingClientRect().height) : null,
          cardBg: c.querySelector('.wp-block-group') ? getComputedStyle(c.querySelector('.wp-block-group')).backgroundColor : null
        }))
      };
    }

    // Palatability
    const palSec = Array.from(document.querySelectorAll('section')).find(s => s.querySelector('h2')?.textContent.includes('Palatability'));
    if (palSec) {
      res.pal = {
        secH: Math.round(palSec.getBoundingClientRect().height),
        items: Array.from(palSec.querySelectorAll('.wp-block-column')).map(c => ({
          h: Math.round(c.getBoundingClientRect().height),
          num: c.querySelector('p')?.textContent.trim(),
          h3: c.querySelector('h3')?.textContent.trim(),
          hasImg: !!c.querySelector('img')
        }))
      };
    }
    res.docH = document.documentElement.scrollHeight;
    return res;
  });

  console.log(JSON.stringify(out, null, 1));
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });

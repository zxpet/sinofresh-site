// Site Settings v2.8.0: admin page + desktop/mobile topbar-footer screenshots
const { chromium } = require('playwright-core');
const OUT = 'screenshots/site-settings-2800';
const fs = require('fs');
fs.mkdirSync(OUT, { recursive: true });

(async () => {
  const b = await chromium.launch({ channel: 'chrome' });

  // --- admin ---
  const actx = await b.newContext({ viewport: { width: 1280, height: 1000 } });
  const ap = await actx.newPage();
  await ap.goto('http://sinofresh.local/wp-login.php', { waitUntil: 'domcontentloaded' });
  await ap.fill('#user_login', 'qa_temp');
  await ap.fill('#user_pass', 'QaTemp!2026');
  await ap.click('#wp-submit');
  await ap.waitForLoadState('domcontentloaded');
  await ap.goto('http://sinofresh.local/wp-admin/admin.php?page=sf-site-settings', { waitUntil: 'domcontentloaded' });
  await ap.waitForTimeout(800);
  const admin = await ap.evaluate(() => ({
    title: document.querySelector('h1') && document.querySelector('h1').textContent,
    menuOrder: [...document.querySelectorAll('#adminmenu a')].filter(a => /Site Settings|Social Links/.test(a.textContent)).map(a => a.textContent.trim()),
    emailVal: document.querySelector('#sf_email') && document.querySelector('#sf_email').value,
    hoursVal: document.querySelector('#sf_hours') && document.querySelector('#sf_hours').value,
    phoneVal: document.querySelector('#sf_phone') && document.querySelector('#sf_phone').value,
    waVal: document.querySelector('#sf_wa') && document.querySelector('#sf_wa').value,
    certRows: document.querySelectorAll('input[name^="sf_certifications"][name$="[name]"]').length,
    certChecked: document.querySelectorAll('input[name^="sf_certifications"][name$="[active]"]:checked').length,
    cert1Name: document.querySelector('input[name="sf_certifications[0][name]"]') && document.querySelector('input[name="sf_certifications[0][name]"]').value,
  }));
  console.log('ADMIN:', JSON.stringify(admin));
  await ap.screenshot({ path: `${OUT}/admin-site-settings.png`, fullPage: true });
  await actx.close();

  // --- desktop ---
  const dctx = await b.newContext({ viewport: { width: 1440, height: 900 } });
  const dp = await dctx.newPage();
  await dp.goto('http://sinofresh.local/', { waitUntil: 'networkidle' });
  const d = await dp.evaluate(() => {
    const top = document.querySelector('.sf-topbar');
    const badges = [...top.querySelectorAll('.sf-cert-badge')];
    const b0 = badges[0].getBoundingClientRect();
    return {
      badges: badges.map(x => x.textContent),
      badgeH: Math.round(b0.height),
      badgeTags: badges.map(x => x.tagName),
      topbarH: Math.round(top.getBoundingClientRect().height),
    };
  });
  console.log('DESKTOP TOPBAR:', JSON.stringify(d));
  await dp.screenshot({ path: `${OUT}/desktop-topbar.png`, clip: { x: 0, y: 0, width: 1440, height: 90 } });
  const dfoot = await dp.evaluate(() => Math.round(document.querySelector('.sf-footcontact').getBoundingClientRect().top + scrollY));
  await dp.screenshot({ path: `${OUT}/desktop-footer.png`, fullPage: true, clip: { x: 0, y: Math.max(0, dfoot - 160), width: 1440, height: 420 } });
  await dctx.close();

  // --- mobile 375 ---
  const mctx = await b.newContext({ viewport: { width: 375, height: 720 }, isMobile: true });
  const mp = await mctx.newPage();
  await mp.goto('http://sinofresh.local/', { waitUntil: 'networkidle' });
  const m = await mp.evaluate(() => {
    const top = document.querySelector('.sf-topbar');
    const email = top.querySelector('.sf-topbar__email').getBoundingClientRect();
    return {
      topbarH: Math.round(top.getBoundingClientRect().height),
      leftGroupHidden: getComputedStyle(top.querySelector('.sf-topbar-left')).display === 'none',
      overflowX: document.documentElement.scrollWidth > document.documentElement.clientWidth,
    };
  });
  console.log('MOBILE:', JSON.stringify(m));
  await mp.screenshot({ path: `${OUT}/mobile-topbar-375.png`, clip: { x: 0, y: 0, width: 375, height: 120 } });
  await b.close();
})().catch(e => { console.error(e); process.exit(1); });

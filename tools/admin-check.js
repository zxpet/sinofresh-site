/* Admin verification: Social Links page round-trip + Site Editor logo entry. */
const { chromium } = require('playwright-core');
const fs = require('fs');
const OUT = '/Users/meng/WorkBuddy/sinofresh外贸网站建设/screenshots/round6';

(async () => {
  const [user, pass] = fs.readFileSync('/tmp/sf_qa_creds.txt', 'utf8').trim().split('\n');
  const browser = await chromium.launch({ headless: true, args: ['--disable-gpu', '--no-sandbox'] });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 });

  // login
  await page.goto('http://sinofresh.local/wp-login.php', { waitUntil: 'domcontentloaded' });
  await page.fill('#user_login', user);
  await page.fill('#user_pass', pass);
  await page.click('#wp-submit');
  await page.waitForURL('**/wp-admin/**');
  console.log('logged in');

  // 1) Social Links menu page
  await page.goto('http://sinofresh.local/wp-admin/admin.php?page=social-links', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(400);
  await page.screenshot({ path: OUT + '/admin-social-links.png', fullPage: true });
  // fill YouTube with a test URL and save
  const yt = page.locator('#sf_social_youtube');
  await yt.fill('https://www.youtube.com/@sinofresh');
  await page.click('#submit');
  await page.waitForTimeout(800);
  await page.waitForTimeout(400);
  await page.screenshot({ path: OUT + '/admin-social-links-saved.png', fullPage: true });
  const savedVal = await page.locator('#sf_social_youtube').inputValue();
  console.log('saved youtube value:', savedVal);

  // 2) Site Editor: Header part -> logo block (site identity replace entry)
  await page.goto('http://sinofresh.local/wp-admin/site-editor.php?p=%2Fheader&postType=wp_template_part&postId=sinofresh-theme%2F%2Fheader', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(3500);
  await page.screenshot({ path: OUT + '/admin-site-editor-header.png' });
  // try to click the logo in the editor canvas iframe
  const frame = page.frames().find(f => f.url().includes('post.php') || f.url().includes('canvas') || true);
  let clicked = false;
  for (const f of page.frames()) {
    try {
      const logo = await f.$('.sf-logo img, .custom-logo, [class*="site-logo"] img');
      if (logo) {
        await logo.click();
        clicked = true;
        console.log('clicked logo in frame', f.url().slice(0, 80));
        break;
      }
    } catch (e) {}
  }
  await page.waitForTimeout(1200);
  await page.screenshot({ path: OUT + '/admin-site-editor-logo-selected.png' });
  console.log('logo clicked:', clicked);

  await browser.close();
})();

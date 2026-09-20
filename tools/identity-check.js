/* Explore Site Editor: Identity panel -> logo replace entry. */
const { chromium } = require('playwright-core');
const fs = require('fs');
const OUT = '/Users/meng/WorkBuddy/sinofresh外贸网站建设/screenshots/round6';

(async () => {
  const [user, pass] = fs.readFileSync('/tmp/sf_qa_creds.txt', 'utf8').trim().split('\n');
  const browser = await chromium.launch({ headless: true, args: ['--disable-gpu', '--no-sandbox'] });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 });
  await page.goto('http://sinofresh.local/wp-login.php', { waitUntil: 'domcontentloaded' });
  await page.fill('#user_login', user);
  await page.fill('#user_pass', pass);
  await page.click('#wp-submit');
  await page.waitForURL('**/wp-admin/**');

  await page.goto('http://sinofresh.local/wp-admin/site-editor.php', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(4000);
  // click "Identity" in the sidebar
  const identity = page.getByText('Identity', { exact: true }).first();
  await identity.click();
  await page.waitForTimeout(3000);
  await page.screenshot({ path: OUT + '/admin-site-identity.png' });
  console.log('identity panel shot');
  await browser.close();
})();

/* Pattern library admin verification (iframe-aware):
 * 1. temp admin login
 * 2. post-new.php -> close welcome modal -> open inserter -> Patterns tab
 *    -> category filter -> insert Educational Article
 * 3. verify skeleton + locks via wp.data (main frame)
 * 4. screenshots
 */
const { chromium } = require('playwright-core');

const BASE = 'http://sinofresh.local';
const USER = 'sf_pattern_shooter';
const PASS = 'Sf!Shooter2026x';

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  const results = [];
  const check = (name, cond) => { results.push([cond ? 'PASS' : 'FAIL', name]); };

  // login
  await page.goto(BASE + '/wp-login.php', { waitUntil: 'load' });
  await page.fill('#user_login', USER);
  await page.fill('#user_pass', PASS);
  await page.click('#wp-submit');
  await page.waitForLoadState('load');
  check('login succeeded', !page.url().includes('wp-login.php'));

  // new post
  await page.goto(BASE + '/wp-admin/post-new.php', { waitUntil: 'load', timeout: 45000 });
  await page.locator('button[aria-label="Block Inserter"]').first().waitFor({ state: 'attached', timeout: 45000 });
  // close welcome modal(s): Escape until no overlay remains
  for (let i = 0; i < 6; i++) {
    const overlay = page.locator('.components-modal__screen-overlay');
    if (!(await overlay.count()) || !(await overlay.first().isVisible())) break;
    await page.keyboard.press('Escape');
    await page.waitForTimeout(500);
  }
  check('welcome modal closed', !(await page.locator('.components-modal__screen-overlay').count()));

  // editor canvas iframe present?
  const canvas = page.frameLocator('iframe[name="editor-canvas"]');
  const canvasOk = await page.locator('iframe[name="editor-canvas"]').count();
  check('editor canvas iframe present', canvasOk > 0);

  // open block inserter
  const inserterBtn = page.locator('button[aria-label="Block Inserter"], button[aria-label="Toggle block inserter"]').first();
  await inserterBtn.waitFor({ state: 'visible', timeout: 15000 });
  await inserterBtn.click();
  await page.waitForSelector('.block-editor-inserter__menu, .block-editor-inserter__main-area', { timeout: 15000 });
  await page.waitForTimeout(800);

  // Patterns tab
  const tab = page.getByRole('tab', { name: /Patterns/ }).first();
  await tab.click();
  await page.waitForTimeout(1000);

  // category sidebar item (WP 7.1 uses a list, not a select)
  let catApplied = false;
  const catItem = page.locator('.block-editor-inserter__menu button:has-text("SINO FRESH Article Templates"), .block-editor-inserter__panel button:has-text("SINO FRESH Article Templates")').first();
  if (await catItem.count()) {
    await catItem.click({ timeout: 5000 });
    catApplied = true;
    await page.waitForTimeout(1200);
  }
  check('category item clickable and applied', catApplied);
  await page.screenshot({ path: '/tmp/patterns/inserter-patterns-tab.png' });

  // search pattern
  const search = page.locator('.block-editor-inserter__search input').first();
  await search.fill('Educational Article');
  await page.waitForTimeout(1000);
  const hit = page.locator('.block-editor-block-patterns-list__item:has-text("Educational Article")').first();
  const listed = (await hit.count()) > 0;
  check('Educational Article pattern listed', listed);
  await page.screenshot({ path: '/tmp/patterns/inserter-search.png' });

  // insert
  if (listed) { await hit.click(); await page.waitForTimeout(2000); }

  // verify inserted blocks via wp.data (main frame)
  const state = await page.evaluate(() => {
    const sel = wp.data.select('core/block-editor');
    const blocks = sel.getBlocks();
    const flat = [];
    const walk = (bs) => bs.forEach(b => { flat.push(b); walk(b.innerBlocks); });
    walk(blocks);
    const h2 = flat.filter(b => b.name === 'core/heading').map(b => b.attributes.content);
    const locked = flat.filter(b => b.attributes && b.attributes.lock && b.attributes.lock.remove).map(b => b.name);
    return {
      total: flat.length,
      headings: h2,
      lockedCount: locked.length,
      lockedNames: [...new Set(locked)],
      hasDetails: flat.some(b => b.name === 'core/details'),
      hasTable: flat.some(b => b.name === 'core/table'),
      hasList: flat.some(b => b.name === 'core/list'),
    };
  });
  check('blocks inserted (' + state.total + ')', state.total >= 15);
  check('TL;DR heading present', state.headings.some(h => h && h.includes('TL;DR')));
  check('What Is / Why / How headings present', ['What Is', 'Why Does', 'How Does'].every(t => state.headings.some(h => h && h.includes(t))));
  check('FAQ heading present', state.headings.some(h => h && h.includes('Frequently Asked Questions')));
  check('details blocks present', state.hasDetails);
  check('table present', state.hasTable);
  check('locked blocks >= 6', state.lockedCount >= 6);
  check('locked names include core/list + core/details + core/group', ['core/list', 'core/details', 'core/group'].every(n => state.lockedNames.includes(n)));
  console.log('inserted state:', JSON.stringify(state));

  await page.screenshot({ path: '/tmp/patterns/editor-inserted.png' });

  for (const [s, n] of results) console.log(s + '  ' + n);
  const fails = results.filter(r => r[0] === 'FAIL').length;
  console.log(fails === 0 ? 'ALL PASS' : fails + ' FAILURES');
  await browser.close();
  process.exit(fails === 0 ? 0 : 1);
})();

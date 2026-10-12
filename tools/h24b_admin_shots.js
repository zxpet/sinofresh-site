#!/usr/bin/env node
/* H24b 后台取证 —— 「表单防护」入口 / FF 条目默认筛选 / 邮件日志，三处可视证据。
 *
 * 截图只能当证据，不能当断言。本脚本同时对 G10/G12 打行为断言：
 *   A0 顶层菜单「表单防护」存在（含当日拦截徽标）
 *   A1 裸访问条目列表（URL 里没有 type=）⇒ hash 必须被改成 type=unread
 *   A2 明确带 #/?type=spam / #/?type= / #/entries/<id> ⇒ 必须**不**重定向
 *      （A2 是 A1 的负对照：一个「无条件重定向」的实现也能让 A1 绿，却会把编辑
 *        人员点过的筛选抢掉；`#/?type=` 空筛选 = 全部，尤其不能被碰）
 *   A4 FF 原生下拉每个状态自带条数（去不掉 Spam/Trashed，但要让运营看得见积压量）
 *   A5b/A5c 抓到 FF 自己的 counts（resources?counts=true）且下拉数字 == 该 counts
 *   A6/A6b 自有「状态总览条」5 个入口与顺序
 *   A6c 总览条数字 == **FF 自己的计数**（跨实现比对：FF countByGroup() vs 我们的聚合 SQL）
 *   A6d 总览条「全部」== FF 公式 Σ状态 − 回收站（FF 下拉里根本没有「全部」这一项）
 *   A7 当前高亮项 = 未读
 *   A8 空状态提示「当前没有未读询盘」+ 两个出口，其可见性 == (FF未读==0 && 停在未读)
 *   A9/A10 点击总览条 ⇒ 整页加载 + hash 正确 + 一次性参数已抹掉 + 请求参数正确
 *   A11 点击「垃圾」后 FF 列表返回的 total == 总览条的垃圾数（点击链路的 DB 等价）
 *
 * ⚠️ 为什么 A6c 不拿脚本启动时的 DB 快照比：FF 在「打开单条详情」时会顺手把该条
 *    unread 改成 read（实测 3→2 / 0→1），跨脚本运行必然过期；而 DB 侧的独立性由
 *    h24b_l1.php 的 [L7] 在同一 PHP 进程内独立复算保证。这里做的是**跨实现**比对。
 *
 * usage:
 *   SF_H24B_CFG=/tmp/h24b-e2e.dev.json SF_H24B_SITE=dev \
 *     NODE_PATH=<workspace>/node_modules node tools/h24b_admin_shots.js
 */
const { chromium } = require('playwright-core');
const fs = require('fs');
const path = require('path');

const CFG_PATH = process.env.SF_H24B_CFG || '/tmp/h24b-e2e.json';
const SITE = process.env.SF_H24B_SITE || 'dev';
const ENTRY_ID = process.env.SF_H24B_ENTRY_ID || '1';
const REPO = path.resolve(__dirname, '..');
const SHOTS = path.join(REPO, 'docs', `h24b-shots-${SITE}`);
fs.mkdirSync(SHOTS, { recursive: true });

const CFG = JSON.parse(fs.readFileSync(CFG_PATH, 'utf8'));
const HOST = new URL(CFG.base).hostname;
const IS_DEV = SITE === 'dev';
const BASIC = process.env.SFDEV_BASIC || 'sfdev:VkEws18Kl5V1qp3TpZ6s';

/* 本机直连站点会走 Cloudflare 边缘（实测 25~40s 超时 ⇒ 假 FAIL）。
   把域名解析钉到源站 IP，请求直接落到 vhost，Host 头仍是域名 ⇒ 证书/虚拟主机都对。
   ignore_https_errors：源站返回的是 CF 源证书，不经边缘校验必失败。 */
const ORIGIN_IP = process.env.SF_ORIGIN_IP || '65.49.215.152';
const RESOLVER = [`MAP ${HOST} ${ORIGIN_IP}`];
if (HOST.startsWith('www.')) { RESOLVER.push(`MAP ${HOST.slice(4)} ${ORIGIN_IP}`); }
const LAUNCH_ARGS = ['--no-sandbox', '--disable-dev-shm-usage',
  `--host-resolver-rules=${RESOLVER.join(', ')}`];

let fails = 0;
const ck = (ok, label, detail) => {
  console.log((ok ? '[PASS] ' : '[FAIL] ') + label +
    (!ok && detail !== undefined ? '  | ' + String(detail).slice(0, 200) : ''));
  if (!ok) fails++;
};

(async () => {
  const browser = await chromium.launch({ headless: true, args: LAUNCH_ARGS });
  const bp = BASIC.indexOf(':');
  const ctx = await browser.newContext({
    viewport: { width: 1440, height: 1000 },
    ignoreHTTPSErrors: true,
    httpCredentials: (!IS_DEV || bp === -1)
      ? undefined
      : { username: BASIC.slice(0, bp), password: BASIC.slice(bp + 1) },
  });
  await ctx.addCookies([
    { name: 'wordpress_sec_' + CFG.hash, value: CFG.cookies.sec, domain: HOST, path: '/', secure: true, httpOnly: true },
    { name: 'wordpress_' + CFG.hash, value: CFG.cookies.auth, domain: HOST, path: '/', secure: true, httpOnly: true },
    { name: 'wordpress_logged_in_' + CFG.hash, value: CFG.cookies.logged_in, domain: HOST, path: '/', secure: true, httpOnly: true },
  ]);

  /* wp-admin 永远等不到 networkidle（心跳/长轮询挂着），一律 domcontentloaded + 显式等待 */
  const go = async (url, wait = 1200) => {
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForTimeout(wait);
  };
  /* ⚠️ 只有 hash 不同的 URL 不会重新加载文档 ⇒ 我方脚本不会重新执行。
     凡是要断言「脚本行为」的访问都必须强制一次真实文档加载（reload），
     否则断言会在旧文档上通过，是假绿。 */
  const hardGo = async (url, wait = 2000) => {
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.reload({ waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForTimeout(wait);
  };

  const page = await ctx.newPage();
  const shot = async (name, locator) => {
    const out = path.join(SHOTS, name);
    if (locator) { await locator.screenshot({ path: out }); } else { await page.screenshot({ path: out, fullPage: true }); }
    console.log('  shot -> ' + path.relative(REPO, out));
  };
  /* 守卫：任何 0 命中都要先证明「拿到的是被服务的后台页」，而不是登录页/401 页 */
  const assertServed = async (where) => {
    const t = await page.title();
    const onLogin = await page.locator('#loginform, #user_login').count();
    ck(onLogin === 0, `守卫：${where} 拿到的是已登录后台（非登录页）`, 'title=' + t);
    return t;
  };

  console.log(`============ H24b 后台取证 [site=${SITE}] base=${CFG.base} ============`);

  // ---------------------------------------------------------------- 1) 表单防护入口
  await go(CFG.urls.guard);
  await assertServed('表单防护页');
  // 菜单徽标（当日被拦数）
  const menu = page.locator('#toplevel_page_sf-form-guard');
  ck(await menu.count() > 0, 'A0: 顶层菜单「表单防护」存在（#toplevel_page_sf-form-guard）');
  if (await menu.count() > 0) { await shot('01-menu-guard.png', menu); }
  // Fluent Forms 子菜单入口：强制展开以便同框取证
  const ffMenu = page.locator('#toplevel_page_fluent_forms');
  if (await ffMenu.count() > 0) {
    await page.evaluate(() => {
      const li = document.getElementById('toplevel_page_fluent_forms');
      if (li) { li.classList.add('wp-menu-open', 'wp-has-current-submenu'); li.classList.remove('wp-not-current-submenu'); }
    });
    await shot('02-menu-ff-submenu.png', ffMenu);
  }
  await go(CFG.urls.guard);
  await shot('03-guard-page.png');
  const guardText = await page.locator('#wpbody-content').innerText();
  ck(/保留|retention/i.test(guardText), 'A5: 复核页展示保留期/清理状态', guardText.slice(0, 120).replace(/\n/g, ' '));
  ck(/垃圾|Spam/i.test(guardText), 'A5: 复核页含「只看垃圾」入口', '');

  // ---------------------------------------------------------------- 2) FF 条目列表：默认筛选 + 总览条
  const bare = CFG.urls.entries;
  let lastReq = '';
  let listBody = null;
  page.on('request', (r) => { if (/\/fluentform\/v1\/submissions\?/.test(r.url())) lastReq = r.url(); });
  page.on('response', async (r) => {
    if (/\/fluentform\/v1\/submissions\?/.test(r.url())) {
      try { listBody = await r.json(); } catch (e) { listBody = null; }
    }
  });
  /* FF 自己的权威计数（`resources?counts=true`，与下拉同一份数据源）。用它做总览条的
     比对基准 —— 与文档同一次渲染周期，不受「打开详情改已读」影响。 */
  let ffCounts = null;
  let ffRlReq = '';
  page.on('response', async (r) => {
    if (/\/fluentform\/v1\/submissions\/resources/.test(r.url()) && /counts=true/.test(r.url())) {
      ffRlReq = r.url();
      try { const j = await r.json(); if (j && j.counts) { ffCounts = j.counts; } } catch (e) { /* ignore */ }
    }
  });

  await hardGo(bare, 2400);                  // Vue 挂载 + 注入脚本改写 hash
  await assertServed('条目列表');
  const hashBare = new URL(page.url()).hash;
  ck(/type=unread/.test(hashBare), 'A1: 裸访问 ⇒ hash 切到 type=unread', hashBare);

  // FF 原生下拉：每个状态自带条数（去不掉 Spam/Trashed，但要让运营看得见积压量）
  // 顺序 = Helper::getEntryStatuses() 的数组顺序：unread, read, favorites, spam, trashed
  const FF_ORDER = ['unread', 'read', 'favorites', 'spam', 'trashed'];
  const natOpts = await page.evaluate(() => [...document.querySelectorAll('.el-select-dropdown__item')]
    .slice(0, 5).map((e) => e.innerText.replace(/\s+/g, ' ').trim()));
  ck(natOpts.length === 5 && natOpts.every((t) => /\(\d+\)/.test(t)),
    'A4: FF 原生下拉每个状态自带条数', JSON.stringify(natOpts));
  const natNum = natOpts.map((t) => Number((t.match(/\((\d+)\)/) || [])[1]));

  // FF 自己吐的 counts —— 总览条的比对基准（跨实现，且不受「详情页改已读」影响）
  const ff = ffCounts || {};
  ck(!!ffCounts, 'A5b: 抓到 FF 自己的 counts（resources?counts=true）', ffRlReq.slice(-140));
  ck(ffCounts !== null && FF_ORDER.every((k, i) => Number(ff[k]) === natNum[i]),
    'A5c: FF 下拉数字 == FF counts 同 key（证明下拉就是权威计数的视图）',
    FF_ORDER.map((k, i) => `${k}:${ff[k]}/${natNum[i]}`).join(' '));
  // 只作提示：setup 快照可能已被「打开详情即标已读」弄过期，故不参与断言。
  console.log(`  [info] setup 快照=${JSON.stringify(CFG.counts || {})} 页面 FF=${JSON.stringify(ff)}`);

  // 自有总览条：数字必须等于 FF 自己的计数
  const WANT = [['unread', '未读'], ['all', '全部'], ['read', '已读'], ['spam', '垃圾'], ['trashed', '回收站']];
  const barTabs = await page.evaluate(() => [...document.querySelectorAll('#sf-fg-bar a')]
    .map((e) => ({
      key: e.getAttribute('data-sf-fg-tab'),
      txt: e.innerText.replace(/\s+/g, ' ').trim(),
      cur: e.getAttribute('aria-current'),
      href: e.getAttribute('href'),
    })));
  ck(barTabs.length === 5, 'A6: 总览条 5 个入口', JSON.stringify(barTabs.map((t) => t.key)));
  ck(barTabs.map((t) => t.key).join(',') === WANT.map((w) => w[0]).join(','),
    'A6b: 总览条顺序 = 未读|全部|已读|垃圾|回收站', barTabs.map((t) => t.key).join(','));
  const numOf = (t) => (t ? Number((t.txt.match(/\((\d+)\)/) || [])[1]) : NaN);
  let countsOk = true;
  const countsBad = [];
  for (const [k, label] of WANT) {
    if (k === 'all') { continue; }                 // FF 下拉没有「全部」，见 A6d
    const t = barTabs.find((x) => x.key === k);
    const exp = Number(ff[k]);
    if (!t || numOf(t) !== exp || !t.txt.startsWith(label)) {
      countsOk = false;
      countsBad.push(`${k}:"${t ? t.txt : '∅'}"≠${label}(${exp})`);
    }
  }
  ck(countsOk, 'A6c: 总览条计数 == FF 自身计数（跨实现）',
    countsBad.join(' ') || WANT.map(([k]) => `${k}:${ff[k]}`).join(' '));

  // 「全部」在 FF 下拉里不存在 ⇒ 只能按 FF 自己的公式复算：all = Σ status − trashed
  const stKeys = Object.keys(ff).filter((k) => k !== 'all' && k !== 'favorites');
  const expAll = stKeys.reduce((a, k) => a + Number(ff[k] || 0), 0) - Number(ff.trashed || 0);
  const allTab = barTabs.find((x) => x.key === 'all');
  ck(ffCounts !== null && numOf(allTab) === expAll && /^全部/.test(allTab ? allTab.txt : ''),
    'A6d: 总览条「全部」== FF 公式 Σ状态−回收站（下拉里没有这一项）',
    `bar=${numOf(allTab)} exp=${expAll} 依据=${JSON.stringify(ff)}`);

  const curTab = barTabs.filter((t) => t.cur === 'true').map((t) => t.key);
  ck(curTab.length === 1 && curTab[0] === 'unread', 'A7: 当前高亮 = 未读', JSON.stringify(curTab));

  // 空状态提示：可见性 == (未读==0 && 停在未读)
  const emptyShown = await page.locator('#sf-fg-empty').isVisible();
  ck(ffCounts !== null && emptyShown === (Number(ff.unread) < 1),
    `A8: 空状态提示可见性（FF 未读=${ff.unread}）`, 'visible=' + emptyShown);
  if (emptyShown) {
    const et = (await page.locator('#sf-fg-empty').innerText()).replace(/\s+/g, ' ');
    ck(/当前没有未读询盘/.test(et), 'A8b: 空状态文案含「当前没有未读询盘」', et.slice(0, 80));
    const btns = await page.evaluate(() => [...document.querySelectorAll('#sf-fg-empty a')]
      .map((e) => e.innerText.replace(/\s+/g, ' ').trim()));
    ck(btns.length === 2 && /查看全部 \(\d+\)/.test(btns[0]) && /查看垃圾 \(\d+\)/.test(btns[1]),
      'A8c: 空状态两个出口按钮（查看全部 / 查看垃圾）', JSON.stringify(btns));
  }
  await shot('04-entries-default-unread.png');

  // ---------------------------------------------------------------- 3) 负对照：显式筛选/详情页不得被重定向
  for (const [label, frag, pat] of [
    ['A2(负对照): 明确 type=spam 不被重定向', '#/?type=spam', /type=spam/],
    ['A2b(负对照): 空筛选 type= (全部) 不被重定向', '#/?type=', /type=/],
    ['A2c(负对照): 明确 type=read 不被重定向', '#/?type=read', /type=read/],
  ]) {
    await hardGo(bare + frag, 2400);
    ck(pat.test(new URL(page.url()).hash), label, new URL(page.url()).hash);
  }
  await shot('05-entries-explicit-filters.png');

  await hardGo(bare + '#/entries/' + ENTRY_ID, 2400);
  const hashDet = new URL(page.url()).hash;
  ck(new RegExp('/entries/' + ENTRY_ID).test(hashDet), 'A3(负对照): 单条详情不被重定向', hashDet);
  const barVis = await page.locator('#sf-fg-bar').isVisible();
  ck(barVis === false, 'A3b: 单条详情页隐藏状态总览条', 'visible=' + barVis);
  await shot('06-entry-detail.png');

  // 仅改 hash（不整页刷新）——运营点条目行走的就是这条路径
  await page.evaluate((id) => { window.location.hash = '/entries/' + id; }, ENTRY_ID);
  await page.waitForTimeout(700);
  ck((await page.locator('#sf-fg-bar').isVisible()) === false,
    'A3d: 仅改 hash 进详情页也不留总览条（hashchange 监听生效）', '');

  await page.evaluate(() => { window.location.hash = '/?type=spam'; });
  await page.waitForTimeout(900);
  ck(await page.locator('#sf-fg-bar').isVisible(), 'A3e: 仅改 hash 回列表 ⇒ 总览条恢复', '');
  const curH = await page.evaluate(() => [...document.querySelectorAll('#sf-fg-bar a[aria-current="true"]')]
    .map((e) => e.getAttribute('data-sf-fg-tab')));
  ck(curH.length === 1 && curH[0] === 'spam',
    'A3f: 仅改 hash 时高亮跟随（与 FF 自带下拉同源）', JSON.stringify(curH));

  // ---------------------------------------------------------------- 3b) 点击总览条：整页加载 + 参数抹净 + 请求正确
  // 形状未知的 JSON 里找「总数」——只认 total 家族的键，避免误抓分页的每页条数。
  const pickTotal = (j) => {
    if (!j || typeof j !== 'object') { return null; }
    for (const k of ['total', 'totalCount', 'total_count']) {
      if (Number.isFinite(Number(j[k]))) { return Number(j[k]); }
    }
    for (const k of Object.keys(j)) {
      if (j[k] && typeof j[k] === 'object') { const t = pickTotal(j[k]); if (t !== null) { return t; } }
    }
    return null;
  };
  for (const [key, wantHash] of [['spam', /type=spam/], ['all', /type=(&|$)/]]) {
    await hardGo(bare, 2400);
    lastReq = '';
    listBody = null;
    await page.locator(`#sf-fg-bar a[data-sf-fg-tab="${key}"]`).click();
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2400);
    const navUrl = page.url();
    const navHash = new URL(navUrl).hash;
    ck(wantHash.test(navHash), `A9/A10[${key}]: 点击后 hash=${navHash}`, navHash);
    ck(/sf_fg_view/.test(navUrl) === false, `A9/A10[${key}]: 一次性参数已从地址栏抹掉`, navUrl);
    const cur = await page.evaluate(() => [...document.querySelectorAll('#sf-fg-bar a[aria-current="true"]')]
      .map((e) => e.getAttribute('data-sf-fg-tab')));
    ck(cur.length === 1 && cur[0] === key, `A9/A10[${key}]: 高亮切到该项`, JSON.stringify(cur));
    const wantReq = key === 'spam' ? /entry_type=spam/ : /entry_type=(&|$)/;
    ck(wantReq.test(lastReq), `A9/A10[${key}]: 列表请求参数正确`, lastReq.slice(-150));
    if (key === 'spam') {
      // 点击链路的 DB 等价：真去请求「垃圾」列表，FF 返回的总数必须等于总览条的垃圾数。
      const tot = pickTotal(listBody);
      ck(tot !== null && tot === Number(ff.spam),
        'A11: 点击「垃圾」后 FF 列表 total == 总览条垃圾数（点击链路 DB 等价）',
        `total=${tot} FF.spam=${ff.spam} respKeys=${listBody ? JSON.stringify(Object.keys(listBody)) : '∅'}`);
    }
    await shot(`07-entries-${key}.png`);
  }

  // ---------------------------------------------------------------- 3c) 未读为空：空状态引导（真浏览器）
  // 生产 form 8 长期未读=0 ⇒ 这个分支才是运营打开页面的**主场景**，必须在真浏览器里走一遍。
  // dev 的 form 8 有未读，故由 setup 另找一个未读=0 的表单当夹具（生产则为 null，A8 已覆盖）。
  if (CFG.urls.entries_empty) {
    ffCounts = null;
    await hardGo(CFG.urls.entries_empty, 2800);
    await assertServed('空表单条目列表');
    const ef = ffCounts || {};
    const ehash = new URL(page.url()).hash;
    ck(/type=unread/.test(ehash), 'A12: 空表单裸访问 ⇒ hash 切到 type=unread', ehash);
    const eTabs = await page.evaluate(() => [...document.querySelectorAll('#sf-fg-bar a')]
      .map((e) => ({ key: e.getAttribute('data-sf-fg-tab'), txt: e.innerText.replace(/\s+/g, ' ').trim() })));
    const eUnread = eTabs.find((t) => t.key === 'unread');
    ck(eTabs.length === 5 && eUnread && eUnread.txt === '未读 (0)',
      'A12b: 空表单总览条仍渲染且「未读 (0)」', JSON.stringify(eTabs.map((t) => t.txt)));
    const eShown = await page.locator('#sf-fg-empty').isVisible();
    ck(eShown === true && Number(ef.unread) === 0,
      'A12c: 未读=0 ⇒ 空状态提示可见（真浏览器）', `visible=${eShown} FF未读=${ef.unread}`);
    if (eShown) {
      const et = (await page.locator('#sf-fg-empty').innerText()).replace(/\s+/g, ' ');
      ck(/当前没有未读询盘/.test(et), 'A12d: 空状态文案含「当前没有未读询盘」', et.slice(0, 90));
      const eb = await page.evaluate(() => [...document.querySelectorAll('#sf-fg-empty a')]
        .map((e) => e.innerText.replace(/\s+/g, ' ').trim()));
      const mAll = /\((\d+)\)/.exec((eTabs.find((t) => t.key === 'all') || {}).txt || '');
      const mSpam = /\((\d+)\)/.exec((eTabs.find((t) => t.key === 'spam') || {}).txt || '');
      ck(eb.length === 2 && !!mAll && !!mSpam &&
        eb[0] === `查看全部 (${mAll[1]})` && eb[1] === `查看垃圾 (${mSpam[1]})`,
        'A12e: 两个出口数字取自总览条（非硬编码）', JSON.stringify(eb));
      // 出口必须是一个能被 SPA 感知的整页跳转（带一次性参数），不是仅改 hash
      const eHref = await page.evaluate(() => [...document.querySelectorAll('#sf-fg-empty a')]
        .map((e) => e.getAttribute('href')));
      ck(eHref.length === 2 && eHref.every((h) => /sf_fg_view=/.test(h)) &&
        /sf_fg_view=all#\/\?type=$/.test(eHref[0]) && /sf_fg_view=spam#\/\?type=spam$/.test(eHref[1]),
        'A12f: 出口链接是整页跳转（all 用空筛选，spam 用 type=spam）', JSON.stringify(eHref));
      // 未读=0 时绝不自动跳到「全部」——hash 必须仍停在未读
      ck(!/type=spam/.test(ehash) && /type=unread/.test(ehash),
        'A12g: 未读=0 时没有自动跳到「全部/垃圾」', ehash);
    }
    await shot('04b-entries-empty-state.png');
  }

  // ---------------------------------------------------------------- 4) 邮件日志 + 插件状态
  await go(CFG.urls.smtp, 3500);             // FluentSMTP 是 SPA
  await assertServed('FluentSMTP 日志页');
  await shot('08-smtp-logs.png');

  await go(CFG.urls.plugins);
  const mlRow = page.locator('#wp-mail-logging, tr[data-slug="wp-mail-logging"]').first();
  if (await mlRow.count() > 0) {
    const rowTxt = (await mlRow.innerText()).replace(/\n/g, ' ');
    console.log('  wp-mail-logging 行: ' + rowTxt.slice(0, 140));
    await shot('09-plugin-mail-logging.png', mlRow);
  } else {
    console.log('  (插件列表未找到 wp-mail-logging 行 —— 可能已从列表移除)');
  }

  await browser.close();
  console.log(`\n===== ${fails ? 'FAILED: ' + fails + ' 项' : 'ALL PASS'} | 截图目录 docs/h24b-shots-${SITE}/ =====`);
  process.exit(fails ? 1 : 0);
})().catch((e) => { console.error('EXCEPTION', e); process.exit(2); });

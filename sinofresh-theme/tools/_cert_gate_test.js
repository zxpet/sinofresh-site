/**
 * E2E — certificate gating (B1 file protection + B2 REST endpoint).
 *
 *   NODE_PATH=~/.workbuddy/binaries/node/workspace/node_modules \
 *   node tools/_cert_gate_test.js
 *
 * Verifies, against the running Local site:
 *   · the full-resolution certificates live outside the document root and no
 *     URL reaches them (the .htaccess approach is dead on nginx),
 *   · the public teasers still render the page,
 *   · /cert-download enforces token validity: unknown cert 404, missing /
 *     bogus / expired / replayed token 403, valid token streams the real file
 *     with an attachment disposition.
 * Tokens are minted through the same helper the GF handler uses (CLI helper),
 * so the test never invents a parallel code path.
 */

const { execFileSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const SITE = 'http://sinofresh.local';
const APP = '/Users/meng/Local Sites/sinofresh/app';
const PUBLIC = APP + '/public';
const WPC = PUBLIC + '/wp-content';
const SRC = '/Users/meng/WorkBuddy/sinofresh外贸网站建设/sinofresh-theme';
const DST = WPC + '/themes/sinofresh-theme';
const PHP = process.env.HOME + '/Library/Application Support/Local/lightning-services/php-8.2.29+0/bin/darwin-arm64/bin/php';
const SOCK = process.env.HOME + '/Library/Application Support/Local/run/cVn1NjBpB/mysql/mysqld.sock';

let pass = 0; let fail = 0;
function check(name, ok, detail = '') {
  if (ok) { pass++; console.log(`  \u2713 ${name}${detail ? ' \u2014 ' + detail : ''}`); }
  else { fail++; console.log(`  \u2717 ${name}${detail ? ' \u2014 ' + detail : ''}`); }
}

function mint(cert, ttl) {
  const args = ['-d', `mysqli.default_socket=${SOCK}`, 'tools/_cert_mint.php', cert];
  if (ttl) args.push(String(ttl));
  return execFileSync(PHP, args, { cwd: SRC, encoding: 'utf8' }).trim().split('\n').pop();
}

async function status(url) {
  const r = await fetch(url, { redirect: 'manual' });
  return { code: r.status, type: r.headers.get('content-type'), disp: r.headers.get('content-disposition'), len: Number(r.headers.get('content-length') || 0) };
}

(async () => {
  console.log('\n=== B1 \u00b7 file protection ===');
  const certs = ['cert-fda.webp', 'cert-cgmp.webp', 'cert-iso9001.webp', 'cert-iso22000.webp'];
  const sizes = { 'cert-fda.webp': 50904, 'cert-cgmp.webp': 125654, 'cert-iso9001.webp': 63754, 'cert-iso22000.webp': 77956 };
  for (const f of certs) {
    const p = path.join(APP, 'private-certs', f);
    const ok = fs.existsSync(p) && fs.statSync(p).size === sizes[f];
    check(`1a. private-certs/${f} (${sizes[f]}B)`, ok, fs.existsSync(p) ? fs.statSync(p).size + 'B' : 'missing');
  }
  check('3. wp-content/uploads-private deleted', !fs.existsSync(path.join(WPC, 'uploads-private')));
  check('3b. no .htaccess reliance left', !fs.existsSync(path.join(WPC, 'uploads-private', '.htaccess')));

  const unreachable = [
    '/wp-content/uploads-private/certs/cert-fda.webp',
    '/wp-content/uploads-private/.htaccess',
    '/private-certs/cert-fda.webp',
    '/wp-content/uploads/2026/09/cert-fda.webp',
    '/wp-content/../private-certs/cert-fda.webp',
  ];
  for (const u of unreachable) {
    const s = await status(SITE + u);
    check(`2. unreachable ${u}`, s.code !== 200, `HTTP ${s.code}`);
  }
  const teasers = ['cert-fda', 'cert-cgmp', 'cert-iso9001', 'cert-iso22000'];
  for (const t of teasers) {
    const s = await status(`${SITE}/wp-content/uploads/2026/09/${t}-thumb.webp`);
    check(`2b. teaser reachable ${t}-thumb.webp`, s.code === 200 && s.type === 'image/webp');
  }

  console.log('\n=== B2 \u00b7 REST endpoint token enforcement ===');
  const EP = SITE + '/wp-json/sinofresh/v1/cert-download';
  let s = await status(`${EP}?cert=fda`);
  check('4a. route registered, missing token -> 403', s.code === 403, `HTTP ${s.code}`);
  s = await status(`${EP}?cert=fda&token=${'0'.repeat(40)}`);
  check('5a. bogus token -> 403', s.code === 403, `HTTP ${s.code}`);
  s = await status(`${EP}?cert=bogus&token=${'0'.repeat(40)}`);
  check('5b. unknown cert -> 404', s.code === 404, `HTTP ${s.code}`);
  s = await status(`${EP}?cert=fda&token=abc`);
  check('5c. short token -> 403', s.code === 403, `HTTP ${s.code}`);
  // token minted for fda must not unlock another document
  s = await status(`${EP}?cert=cgmp&token=${mint('fda').split('token=')[1]}`);
  check('5d. token bound to its own cert -> 403', s.code === 403, `HTTP ${s.code}`);

  console.log('\n=== B2 \u00b7 valid token downloads the real file ===');
  const expect = { fda: 'cert-fda.webp', cgmp: 'cert-cgmp.webp', iso9001: 'cert-iso9001.webp', iso22000: 'cert-iso22000.webp' };
  for (const [cert, file] of Object.entries(expect)) {
    const url = mint(cert);
    const r = await fetch(url);
    const buf = Buffer.from(await r.arrayBuffer());
    const src = fs.readFileSync(path.join(APP, 'private-certs', file));
    check(`5e. ${cert}: 200 + bytes identical to private-certs/${file}`,
      r.status === 200 && buf.equals(src), `HTTP ${r.status} ${buf.length}B`);
    check(`5f. ${cert}: attachment + no-store`,
      /^attachment; filename="SINO-FRESH-/.test(r.headers.get('content-disposition') || '') && /no-store/.test(r.headers.get('cache-control') || ''),
      (r.headers.get('content-disposition') || '') + ' | ' + (r.headers.get('cache-control') || ''));
    const replay = await status(url);
    check(`5g. ${cert}: one-time token, replay -> 403`, replay.code === 403, `HTTP ${replay.code}`);
  }
  // sample COA is a public teaser document, sourced from the media tree
  const coa = await fetch(mint('coa-sample'));
  check('5h. coa-sample streams the PDF from uploads', coa.status === 200 && (coa.headers.get('content-type') || '').includes('pdf'),
    `HTTP ${coa.status} ${coa.headers.get('content-type')}`);
  // documents with no file yet: token accepted, file reported unavailable
  const hac = await fetch(mint('haccp'));
  check('5i. haccp (no file yet) -> 404 with contact hint', hac.status === 404 && /unavailable/.test(await hac.text()), `HTTP ${hac.status}`);

  console.log('\n=== B2 \u00b7 expiry ===');
  const short = mint('fda', 1);
  await new Promise((r) => setTimeout(r, 2200));
  s = await status(short);
  check('6. expired token (ttl 1s) -> 403', s.code === 403, `HTTP ${s.code}`);

  console.log('\n=== consistency ===');
  for (const f of ['functions.php', 'inc/cert-download.php']) {
    const a = fs.readFileSync(path.join(SRC, f));
    const b = fs.readFileSync(path.join(DST, f));
    check(`7. source = Local: ${f}`, a.equals(b));
  }
  for (const f of ['functions.php', 'inc/cert-download.php', 'templates/page-quality.html']) {
    const txt = fs.readFileSync(path.join(SRC, f), 'utf8');
    check(`7b. no "/ -->" residue: ${f}`, !txt.includes('/ -->'));
  }

  console.log(`\n${fail === 0 ? '\u2713 ALL PASS' : '\u2717 FAILURES'}  ${pass}/${pass + fail}\n`);
  process.exit(fail === 0 ? 0 : 1);
})();

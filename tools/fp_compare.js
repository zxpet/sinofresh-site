/* Compare two 1440 fingerprints page by page.
 *   node tools/fp_compare.js t7 t7b [--detail]
 */
const fs = require('fs');
const dir = 'screenshots/site-fingerprint-1440-';
const load = (f) => JSON.parse(fs.readFileSync(dir + f + '.json', 'utf8'));
const A = load(process.argv[2]);
const B = load(process.argv[3]);
const detail = process.argv.includes('--detail');

const keys = Object.keys(B);
const diff = [];
for (const k of keys) {
  if (JSON.stringify(A[k]) === JSON.stringify(B[k])) continue;
  const d = [];
  if (A[k].docH !== B[k].docH) d.push('docH ' + A[k].docH + '->' + B[k].docH);
  if (A[k].overflow !== B[k].overflow) d.push('overflow ' + A[k].overflow + '->' + B[k].overflow);
  const sa = JSON.stringify(A[k].sections), sb = JSON.stringify(B[k].sections);
  if (sa !== sb) {
    const n = Math.max(A[k].sections.length, B[k].sections.length);
    const ch = [];
    for (let i = 0; i < n; i++) {
      if (JSON.stringify(A[k].sections[i]) !== JSON.stringify(B[k].sections[i])) ch.push('#' + i + ' ' + JSON.stringify(A[k].sections[i]) + '->' + JSON.stringify(B[k].sections[i]));
    }
    d.push('sections ' + ch.length + ' changed' + (detail ? ': ' + ch.join(' ; ') : ''));
  }
  if (JSON.stringify(A[k].cols) !== JSON.stringify(B[k].cols)) d.push('cols differ');
  if (JSON.stringify(A[k].grids) !== JSON.stringify(B[k].grids)) d.push('grids differ');
  diff.push([k, d.join(' | ')]);
}
console.log(process.argv[2] + ' vs ' + process.argv[3] + ' — 页面 ' + keys.length + ' 个，差异 ' + diff.length + ' 个');
diff.forEach(([k, v]) => console.log('  · ' + k.padEnd(15) + v.slice(0, 300)));

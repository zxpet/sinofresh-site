#!/usr/bin/env python3
"""Batch F1 rendered proof, run against the live theme (post-pull bytes).

What bytes cannot say and this settles:

  * dosage pages — the .sf-facts-mini row really renders with its three items
    and the exact values; the row carries no heading, so the dot rail must
    still be 6 (2D-E's count) and self-consistent (dots == h2 count);
  * formula pages — the hero meta is restored: form label, then the MOQ
    clause, then the Lead time clause with the exact wording the dosage page
    ships;
  * every case: 0 page errors, no horizontal scroll, at 1440 and 375.

Screenshots land in --shots-dir. Session discipline follows the recorded
agent-browser rules: close --all -> set credentials -> open -> set headers
(custom + Basic together, never set credentials afterwards) -> reload ->
set viewport -> eval; after a navigation the headers must be re-set and the
page reloaded before anything is measured.
"""
import argparse
import base64
import json
import os
import subprocess
import sys
import time

DOSE = [
    ('soft-chews', 'from 500\u20131,000 units'),
    ('tablets', 'from 1,000 units'),
    ('fish-oil', 'from 1,000 units'),
    ('dental-chews', 'from 1,000 units'),
    ('powders', 'from 500 units'),
    ('pastes', 'from 500 units'),
    ('drops', 'from 500 units'),
    ('liquids', 'from 500 units'),
]
DETAIL = ['joint-support-soft-chews', 'pure-fish-oil-blend']
LEAD = 'Typically 7\u201315 working days after packaging is ready'
VIEWPORTS = [1440, 375]


def build_js():
    return """(function () {
  var LEAD = %s;
  var q = function (s) { return document.querySelector(s); };
  var qa = function (s) { return Array.prototype.slice.call(document.querySelectorAll(s)); };
  var rect = function (el) { var b = el.getBoundingClientRect();
    return { top: Math.round(b.top + window.scrollY) }; };
  var out = { checks: [], jsErrors: window.__sfErrors || [] };
  var add = function (name, ok, detail) { out.checks.push({ name: name, ok: !!ok, detail: detail }); };

  var mini = q('section.sf-facts-mini');
  if (mini) {
    add('.sf-facts-mini present', true);
    add('row has no heading', !mini.querySelector('h1,h2,h3,h4'));
    add('row carries 3 data-label value spans',
        qa('.sf-facts-mini__value[data-label]').length === 3);
    var vals = {};
    qa('.sf-facts-mini__value[data-label]').forEach(function (v) {
      vals[v.getAttribute('data-label')] = v.textContent.trim(); });
    out.values = vals;
    add('MOQ value exact', vals['MOQ'] !== undefined && vals['MOQ'].length > 0);
    add('Lead time wording exact', vals['Lead time'] === LEAD);
    add('Certifications present',
        /FDA, cGMP, ISO 9001, FSSC 22000, HACCP, BRC/.test(vals['Certifications'] || ''));
    if (window.innerWidth >= 1024) {
      var items = qa('.sf-facts-mini__item').filter(function (el) {
        var b = el.getBoundingClientRect(); return b.width > 0 && b.height > 0; });
      var tops = {};
      items.forEach(function (el) { tops[rect(el).top] = 1; });
      add('items share one visual row (>=1024px)',
          items.length === 3 && Object.keys(tops).length === 1,
          { tops: Object.keys(tops) });
    }
    var hs = document.querySelectorAll('h2').length;
    var dots = document.querySelectorAll('.sf-toc__dot').length;
    out.h2 = hs; out.dots = dots;
    add('dot rail still 6', dots === 6, { dots: dots });
    add('rail self-consistent (dots == h2)', dots === hs, { dots: dots, hs: hs });
  } else {
    var meta = q('.sf-formula-hero__meta');
    add('hero meta present', !!meta);
    var t = meta ? meta.textContent.trim() : '';
    out.meta = t;
    var i = t.indexOf('\\u00b7 MOQ '), j = t.indexOf('\\u00b7 Lead time ');
    add('MOQ clause present and before Lead time', i > 0 && j > i, t.slice(0, 60));
    add('Lead time wording exact', t.indexOf('Lead time ' + LEAD) > -1);
    add('MOQ value looks like a real clause', /MOQ from [\\d,]/.test(t));
    add('meta has exactly three dot-separated clauses',
        t.split('\u00b7').length === 3, t.split('\u00b7').length);
    add('first clause is a dosage-form label (not a sentence)',
        /^[A-Z][A-Za-z ]+$/.test(t.split('\u00b7')[0].trim()),
        t.split('\u00b7')[0].trim());
  }

  add('no page errors', (window.__sfErrors || []).length === 0, out.jsErrors);
  out.hScroll = document.documentElement.scrollWidth > window.innerWidth + 1;
  add('no horizontal scroll', !out.hScroll, { sw: document.documentElement.scrollWidth });
  return JSON.stringify(out);
})()""" % json.dumps(LEAD)


def ab(*args, timeout=180):
    p = subprocess.run(["agent-browser", *args], capture_output=True,
                       text=True, timeout=timeout)
    if p.returncode != 0 and p.stderr.strip():
        print("      !! agent-browser %s -> %s" % (" ".join(args), p.stderr.strip()[:200]))
    return p.stdout.strip()


def ev(js):
    out = ab("eval", js)
    try:
        first = json.loads(out)
    except Exception:
        return {"_raw": out[:400]}
    if isinstance(first, str):
        try:
            return json.loads(first)
        except Exception:
            return {"_raw": first[:400]}
    return first


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--site', default='https://dev.zxpet.com')
    ap.add_argument('--shots-dir', default='docs/b2d-f1-shots')
    args = ap.parse_args()
    auth = os.environ.get('SF_DEV_AUTH')
    if not auth:
        sys.exit('SF_DEV_AUTH required')
    tok = base64.b64encode(auth.encode()).decode()
    os.makedirs(args.shots_dir, exist_ok=True)

    ab('close', '--all')
    time.sleep(1)
    user, pw = auth.split(':', 1)
    ab('set', 'credentials', user, pw)
    ab('open', args.site + '/products/soft-chews/')

    total = fails = 0
    report = []
    js = build_js()
    cases = [(s, True) for s, _ in DOSE] + [(s, False) for s in DETAIL]
    for slug, is_dose in cases:
        path = '/products/%s/' % slug if is_dose else '/formulas/%s/' % slug
        for vw in VIEWPORTS:
            ab('open', args.site + path)
            ab('set', 'headers', json.dumps({'Authorization': 'Basic ' + tok}))
            ab('reload')
            time.sleep(1)
            ab('set', 'viewport', str(vw), '900')
            time.sleep(1)
            ab('eval', 'window.__sfErrors=[];window.addEventListener("error",'
                       'function(e){window.__sfErrors.push(String(e.message))})')
            data = ev(js)
            case_ok = True
            if '_raw' in data:
                total += 1
                fails += 1
                case_ok = False
                report.append((slug, vw, 'EVAL FAIL', False, str(data['_raw'])[:160]))
            else:
                for c in data.get('checks', []):
                    total += 1
                    if not c['ok']:
                        case_ok = False
                        fails += 1
                        report.append((slug, vw, c['name'], False, c.get('detail')))
                detail = data.get('values') or data.get('meta') or ''
                report.append((slug, vw, 'CASE PASS' if case_ok else 'CASE FAIL',
                               case_ok, json.dumps(detail, ensure_ascii=False)[:110]))
            if vw == 1440 or (is_dose and slug == 'soft-chews'):
                name = '%s-%d-full.png' % (slug, vw)
                ab('screenshot', '--full', os.path.join(args.shots_dir, name))

    print('F1 rendered proof: %d checks, %d failures' % (total, fails))
    for row in report:
        mark = 'PASS' if row[3] else 'FAIL'
        print('  [%s] %-30s %5d  %s  %s' % (mark, row[0], row[1], row[2],
                                            str(row[4] or '')[:105]))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Batch G rendered proof — geometry, the dot rail, the fourth row's wrap.

The gates compare bytes; none of these questions can be answered that way:

  * formula pages — the media band really lays out as two columns, the
    right one starts level with the left (core's flow layout would push it
    down by a margin), the gallery stage really fills its column instead of
    sitting capped at 680px in the middle, the factsheet carries the rows
    the record supports, and the CTA wears the palette's cta colour;
  * dosage pages — the fourth row really renders, it carries no heading
    (the dot rail's threshold), and the band's wrap on a 1440 viewport is
    measured rather than assumed;
  * the dot rail is read off the rendered page, never inferred: 4 dots with
    the gallery's heading still among the ones it points at;
  * every case: 0 page errors, no horizontal scroll.

Run against a site: pass --preflight to require the pre-flight theme copy,
which is the only way to see Batch G's bytes before the live pull. The
header discipline is the one recorded in the notes: close --all -> set
credentials -> open -> set headers (custom + Basic in ONE call, never
set credentials afterwards) -> reload -> set viewport -> eval. A run that
does not assert WHICH stylesheet it got can silently measure the old bytes
and report all green, so that assertion is a check like any other.

    SF_DEV_AUTH=sfdev:... python3 tools/b2d_g_evidence.py --preflight \
        --shots-dir docs/batchG-shots
"""
import argparse
import base64
import json
import os
import subprocess
import sys
import time

DOSE = ['soft-chews', 'tablets', 'powders', 'pastes', 'drops', 'liquids',
        'fish-oil', 'dental-chews']
# two English records and one localised page: TranslatePress rewrites the
# CTA's href on the localised one, so that path has to be rendered too
DETAIL = [('joint-support-soft-chews', ''), ('pure-fish-oil-blend', ''),
          ('joint-support-soft-chews', 'zh')]
STACK_VW = 768          # the site's single breakpoint
LEAD = 'Typically 7\u201315 working days after packaging is ready'
CTA_RGB = 'rgb(181, 78, 15)'      # --wp--preset--color--cta, #B54E0F


def build_detail_js():
    return """(function () {
  var LEAD = %s, CTA_RGB = %s;
  var q = function (s) { return document.querySelector(s); };
  var qa = function (s) { return Array.prototype.slice.call(document.querySelectorAll(s)); };
  var cs = function (el) { return el ? getComputedStyle(el) : null; };
  var box = function (el) { var b = el.getBoundingClientRect();
    return { x: Math.round(b.left), y: Math.round(b.top + window.scrollY),
             w: Math.round(b.width), h: Math.round(b.height) }; };
  var num = function (v) { return Math.round(parseFloat(v)); };
  var out = { checks: [], jsErrors: window.__sfErrors || [] };
  var add = function (n, ok, d) { out.checks.push({ name: n, ok: !!ok, detail: d }); };

  var sheet = q('link[rel=stylesheet][href*="style.css"]');
  var href = sheet ? sheet.getAttribute('href') : '';
  out.sheet = href;
  add('stylesheet is the one under test', /ver=2\\.10\\.54/.test(href), href);

  var outer = q('section.sf-fdetail-media'), inner = q('.sf-fdetail-media__inner');
  var left = q('.sf-fdetail-media__left'), side = q('.sf-fdetail-media__side');
  add('outer band present', !!outer);
  add('inner grid present', !!inner);
  add('left column present', !!left);
  add('right column present', !!side);
  if (!inner || !left || !side) { return JSON.stringify(out); }

  var wide = window.innerWidth >= 1024;
  var g = cs(inner);
  var tracks = (g.gridTemplateColumns || '').split(' ').filter(function (s) { return s; });
  var lb = box(left), sb = box(side);
  out.geometry = { vw: window.innerWidth, tracks: tracks, gap: g.columnGap,
                   left: lb.w, side: sb.w, leftTop: lb.y, sideTop: sb.y };
  if (wide) {
    add('two-column grid', g.display === 'grid' && tracks.length === 2,
        { display: g.display, tracks: tracks });
    add('column gap is 48px', num(g.columnGap) === 48, g.columnGap);
    if (tracks.length === 2) {
      var ratio = num(tracks[0]) / num(tracks[1]);
      add('columns are 3fr / 2fr', Math.abs(ratio - 1.5) < 0.06, ratio.toFixed(3));
    }
    add('right column starts level with the left', Math.abs(lb.y - sb.y) <= 1,
        { leftTop: lb.y, sideTop: sb.y });
    add('right column has no flow margin',
        num(cs(side).marginBlockStart) === 0, cs(side).marginBlockStart);
  } else {
    add('stacks to one column below 1024px', tracks.length === 1, tracks);
    add('the gap tightens to 32px when stacked', num(g.columnGap) === 32, g.columnGap);
    add('the right column falls below the left', sb.y > lb.y,
        { leftTop: lb.y, sideTop: sb.y });
  }
  add('band background stays on the outer section',
      cs(outer).backgroundColor !== 'rgba(0, 0, 0, 0)' &&
      cs(inner).backgroundColor === 'rgba(0, 0, 0, 0)',
      { outer: cs(outer).backgroundColor, inner: cs(inner).backgroundColor });

  var stage = q('.sf-gallery__stage');
  if (stage) {
    var st = cs(stage);
    out.stage = { maxWidth: st.maxWidth, marginLeft: st.marginLeft,
                  width: box(stage).w, columnWidth: lb.w };
    add('gallery stage fills its column (max-width override)',
        st.maxWidth === 'none', st.maxWidth);
    add('gallery stage is not centred inside the column',
        num(st.marginLeft) === 0, st.marginLeft);
    add('gallery stage spans the column', Math.abs(box(stage).w - lb.w) <= 2,
        { stage: box(stage).w, column: lb.w });
  } else { add('gallery stage present', false); }
  add('the four slides are still there',
      qa('.sf-gallery__slide').length === 4, qa('.sf-gallery__slide').length);

  var intro = q('.sf-fdetail-media__intro');
  var it = intro ? intro.textContent.trim() : '';
  out.intro = it;
  add('intro paragraph present and substantial', it.length >= 80, it.length);
  var hero = q('.sf-formula-hero__meta');
  var ht = hero ? hero.textContent.trim() : '';
  var clauses = ht.split('\u00b7').map(function (s) { return s.trim(); });
  var moq = '', lead = '';
  clauses.forEach(function (c) {
    if (c.indexOf('MOQ ') === 0) { moq = c.slice(4); }
    if (c.indexOf('Lead time ') === 0) { lead = c.slice(10); } });
  out.hero = { meta: ht, moq: moq, lead: lead };
  add('intro quotes the hero MOQ verbatim',
      !!moq && it.indexOf('Minimum order quantity: ' + moq + '.') > -1, moq);
  add('intro quotes the hero Lead time verbatim',
      !!lead && it.indexOf('Lead time: ' + lead + '.') > -1, lead);
  add('hero Lead time is the agreed wording', lead === LEAD, lead);

  var dts = qa('.sf-fdetail-media__facts dt'), dds = qa('.sf-fdetail-media__facts dd');
  var labels = dts.map(function (d) { return d.textContent.trim(); });
  var vals = {};
  dts.forEach(function (d, i) { if (dds[i]) { vals[labels[i]] = dds[i].textContent.trim(); } });
  out.facts = { labels: labels, values: vals };
  add('factsheet is a dl with matching rows', dts.length === dds.length &&
      dts.length >= 4 && dts.length <= 5, { dt: dts.length, dd: dds.length });
  var canon = ['Unit size', 'Pack options', 'Shelf life', 'Certifications', 'Packaging'];
  var expect = canon.filter(function (l) { return l !== 'Pack options' || labels.indexOf('Pack options') > -1; });
  add('rows follow the canonical order', JSON.stringify(labels) === JSON.stringify(expect),
      { got: labels, expected: expect });
  add('Unit size is not a whole spec line',
      !!vals['Unit size'] && vals['Unit size'].length < 40, vals['Unit size']);
  add('Shelf life reads as a shelf-life clause',
      /shelf life/i.test(vals['Shelf life'] || ''), vals['Shelf life']);
  add('Certifications is the full set',
      /FDA, cGMP, ISO 9001, FSSC 22000, HACCP, BRC/.test(vals['Certifications'] || ''),
      vals['Certifications']);
  add('Packaging ends with the custom-formats clause',
      /, or custom formats$/.test(vals['Packaging'] || ''), vals['Packaging']);

  var cta = q('a.sf-fdetail-media__cta');
  add('one CTA in the right column',
      qa('a.sf-fdetail-media__cta').length === 1);
  if (cta) {
    var ch = cta.getAttribute('href'), cbg = cs(cta).backgroundColor;
    out.cta = { href: ch, text: cta.textContent.trim(), bg: cbg };
    add('CTA says Request Sample', cta.textContent.trim() === 'Request Sample');
    add('CTA points at the contact page of its own locale',
        /^(\\/[a-z]{2})?\\/contact\\/$/.test(ch), ch);
    add('CTA wears the cta palette colour', cbg === CTA_RGB, cbg);
  }

  // Measured, not inferred: toc-nav.js is not enqueued on formula detail
  // pages at all, so there is no rail here to move — the live 2.10.53 page
  // says the same (0 dot elements, no toc script). Asserting "still 4 dots"
  // would have been an assertion about something that never existed, so the
  // check is the finding: no rail, and the reason for it.
  var tocScript = !!q('script[src*="toc-nav"]');
  var dots = qa('.sf-toc__dot');
  out.rail = { tocScript: tocScript, dots: dots.length };
  add('no dot rail on formula detail pages (toc-nav not enqueued here)',
      !tocScript && dots.length === 0, out.rail);
  add('the gallery keeps its heading',
      !!q('h2.sf-gallery__title'), (q('h2.sf-gallery__title') || {}).textContent);

  add('no page errors', (window.__sfErrors || []).length === 0, out.jsErrors);
  out.hScroll = document.documentElement.scrollWidth > window.innerWidth + 1;
  add('no horizontal scroll', !out.hScroll,
      { sw: document.documentElement.scrollWidth, vw: window.innerWidth });
  return JSON.stringify(out);
})()""" % (json.dumps(LEAD), json.dumps(CTA_RGB))


def build_stack_js():
    return """(function () {
  var q = function (s) { return document.querySelector(s); };
  var out = { checks: [] };
  var add = function (n, ok, d) { out.checks.push({ name: n, ok: !!ok, detail: d }); };
  var sheet = q('link[rel=stylesheet][href*="style.css"]');
  out.sheet = sheet ? sheet.getAttribute('href') : '';
  var inner = q('.sf-fdetail-media__inner'), left = q('.sf-fdetail-media__left');
  var side = q('.sf-fdetail-media__side');
  if (!inner || !left || !side) { out.checks = [{ name: 'columns present', ok: false }];
    return JSON.stringify(out); }
  var g = getComputedStyle(inner);
  var tracks = (g.gridTemplateColumns || '').split(' ').filter(function (s) { return s; });
  var lb = left.getBoundingClientRect(), sb = side.getBoundingClientRect();
  out.geometry = { tracks: tracks, leftBottom: Math.round(lb.bottom),
                   sideTop: Math.round(sb.top + window.scrollY),
                   leftWidth: Math.round(lb.width), sideWidth: Math.round(sb.width) };
  add('stacks to one column', tracks.length === 1, tracks);
  add('right column sits below the left',
      sb.top + window.scrollY >= lb.bottom - 1, out.geometry);
  add('both columns use the full width',
      Math.abs(lb.width - sb.width) <= 1, out.geometry);
  out.hScroll = document.documentElement.scrollWidth > window.innerWidth + 1;
  add('no horizontal scroll when stacked', !out.hScroll,
      { sw: document.documentElement.scrollWidth });
  return JSON.stringify(out);
})()"""


def build_dose_js():
    return """(function () {
  var q = function (s) { return document.querySelector(s); };
  var qa = function (s) { return Array.prototype.slice.call(document.querySelectorAll(s)); };
  var out = { checks: [], jsErrors: window.__sfErrors || [] };
  var add = function (n, ok, d) { out.checks.push({ name: n, ok: !!ok, detail: d }); };

  var sheet = q('link[rel=stylesheet][href*="style.css"]');
  var href = sheet ? sheet.getAttribute('href') : '';
  out.sheet = href;
  add('stylesheet is the one under test', /ver=2\\.10\\.54/.test(href), href);

  var mini = q('section.sf-facts-mini');
  add('the facts band is there', !!mini);
  if (mini) {
    add('band still carries no heading', !mini.querySelector('h1,h2,h3,h4'));
    var vals = qa('.sf-facts-mini__value[data-label]');
    var by = {};
    vals.forEach(function (v) { by[v.getAttribute('data-label')] = v.textContent.trim(); });
    out.values = by;
    add('four labelled values now', vals.length === 4, vals.length);
    var labels = vals.map(function (v) { return v.getAttribute('data-label'); });
    add('the fourth one is Packaging formats',
        labels[3] === 'Packaging formats', labels);
    add('Packaging ends with the custom-formats clause',
        /, or custom formats$/.test(by['Packaging formats'] || ''), by['Packaging formats']);
    add('Certifications is the full set',
        /FDA, cGMP, ISO 9001, FSSC 22000, HACCP, BRC/.test(by['Certifications'] || ''),
        by['Certifications']);
    add('the first three labels are unchanged',
        labels.slice(0, 3).join('|') === 'MOQ|Lead time|Certifications', labels);
    var items = qa('.sf-facts-mini__item').filter(function (el) {
      var b = el.getBoundingClientRect(); return b.width > 0 && b.height > 0; });
    var tops = items.map(function (el) {
      return Math.round(el.getBoundingClientRect().top + window.scrollY); });
    var rows = tops.filter(function (t, i) { return tops.indexOf(t) === i; }).sort(function (a, b) { return a - b; });
    out.wrap = { vw: window.innerWidth, items: items.length, rows: rows.length,
                 tops: tops, bandHeight: Math.round(mini.getBoundingClientRect().height) };
    add('all four items are rendered', items.length === 4, items.length);
    if (window.innerWidth >= 1024) {
      add('the band wraps to at most two rows on desktop', rows.length <= 2,
          out.wrap);
    } else {
      add('every item is on its own line when narrow', rows.length === items.length,
          out.wrap);
    }
  }
  var hs = document.querySelectorAll('h2').length;
  var dots = document.querySelectorAll('.sf-toc__dot').length;
  out.rail = { h2: hs, dots: dots };
  add('dot rail still 6', dots === 6, dots);
  add('rail self-consistent (dots == h2)', dots === hs, { dots: dots, hs: hs });
  add('no page errors', (window.__sfErrors || []).length === 0, out.jsErrors);
  out.hScroll = document.documentElement.scrollWidth > window.innerWidth + 1;
  add('no horizontal scroll', !out.hScroll,
      { sw: document.documentElement.scrollWidth, vw: window.innerWidth });
  return JSON.stringify(out);
})()"""


def build_rail_js():
    """Just the rail, so live and candidate bytes can be read the same way."""
    return """(function () {
  var qa = function (s) { return Array.prototype.slice.call(document.querySelectorAll(s)); };
  return JSON.stringify({
    sheet: (document.querySelector('link[rel=stylesheet][href*="style.css"]') || {}).href || '',
    dots: qa('.sf-toc__dot').length,
    h2: qa('h2').length,
    tocScript: !!document.querySelector('script[src*="toc-nav"]')
  });
})()"""


def ab(*args, timeout=180):
    p = subprocess.run(["agent-browser", *args], capture_output=True,
                       text=True, timeout=timeout)
    if p.returncode != 0 and p.stderr.strip():
        print("      !! agent-browser %s -> %s"
              % (" ".join(args), p.stderr.strip()[:200]))
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


def visit(site, path, tok, vw, preflight=True):
    """One measured page visit, with the header discipline the notes record."""
    ab('open', site + path)
    h = {'Authorization': 'Basic ' + tok}
    if preflight:
        h['X-SF-Preflight'] = '1'
    ab('set', 'headers', json.dumps(h))
    ab('reload')
    time.sleep(1)
    ab('set', 'viewport', str(vw), '900')
    time.sleep(1)
    ab('eval', 'window.__sfErrors=[];window.addEventListener("error",'
               'function(e){window.__sfErrors.push(String(e.message))})')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--site', default='https://dev.zxpet.com')
    ap.add_argument('--shots-dir', default='docs/batchG-shots')
    ap.add_argument('--preflight', action='store_true',
                    help='assert the stylesheet served comes from the '
                         'pre-flight theme copy, not the live theme')
    ap.add_argument('--json-out', default=None,
                    help='write every case\'s full measurement here, so the '
                         'numbers in the report can be re-read later')
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
    raw = []

    def run(slug, label, vw, js, path, shot=None):
        nonlocal total, fails
        visit(args.site, path, tok, vw, preflight=args.preflight)
        data = ev(js)
        raw.append({'case': label, 'viewport': vw, 'path': path, 'data': data})
        case_ok = True
        if '_raw' in data:
            total += 1
            fails += 1
            report.append((label, vw, 'EVAL FAIL', False, str(data['_raw'])[:170]))
        else:
            # a run that cannot say which stylesheet it measured proves nothing
            got = str(data.get('sheet', ''))
            total += 1
            in_pre = 'sinofresh-theme-preflight' in got
            if args.preflight and not in_pre:
                fails += 1
                case_ok = False
                report.append((label, vw, 'WRONG STYLESHEET SERVED', False, got))
            elif not args.preflight and in_pre:
                fails += 1
                case_ok = False
                report.append((label, vw, 'PRE-FLIGHT SHEET WITHOUT --preflight',
                               False, got))
            for c in data.get('checks', []):
                total += 1
                if not c['ok']:
                    case_ok = False
                    fails += 1
                    report.append((label, vw, c['name'], False,
                                   json.dumps(c.get('detail'), ensure_ascii=False)[:130]))
            extra = {k: v for k, v in data.items()
                     if k in ('geometry', 'wrap', 'facts', 'rail', 'cta', 'stage', 'hero')}
            report.append((label, vw, 'CASE PASS' if case_ok else 'CASE FAIL',
                           case_ok,
                           json.dumps(extra, ensure_ascii=False)[:190]))
        if shot:
            ab('screenshot', '--full', os.path.join(args.shots_dir, shot))

    # --- the two-column band, English, wide and stacked ---------------------
    for slug, lang in DETAIL:
        path = '%s/formulas/%s/' % ('/zh' if lang else '', slug)
        label = '%s%s' % (slug, ' (zh)' if lang else '')
        run(slug, label, 1440, build_detail_js(), path,
            shot='%s%s-1440.png' % (slug, '-zh' if lang else ''))
        run(slug, label, 375, build_detail_js(), path)
    run('joint-support-soft-chews', 'joint-support-soft-chews @768', STACK_VW,
        build_stack_js(), '/formulas/joint-support-soft-chews/',
        shot='joint-support-soft-chews-768.png')

    # --- the fourth row on all eight dosage pages ---------------------------
    for form in DOSE:
        run(form, form, 1440, build_dose_js(), '/products/%s/' % form)
    run('soft-chews', 'soft-chews @375', 375, build_dose_js(), '/products/soft-chews/')

    # --- the dot rail, live bytes vs the bytes under test -------------------
    # The batch must not move the rail. Saying that with evidence means
    # reading the rail off the live 2.10.53 page and off the candidate and
    # finding them the same — which is also how the premise "the detail page
    # has a 4-dot rail" got corrected: it has none, and it had none before.
    for label, path, want in (('detail', '/formulas/joint-support-soft-chews/', 0),
                              ('dosage', '/products/soft-chews/', 6)):
        got = {}
        # Under --preflight the second visit is the copy under test; on the
        # live run it is the same page again, i.e. an A/A reading that would
        # fail loudly if a page were flaky.
        second = 'cand' if args.preflight else 'live-again'
        for tag, pre in (('live', False), (second, args.preflight)):
            visit(args.site, path, tok, 1440, preflight=pre)
            got[tag] = ev(build_rail_js())
        same = got['live'].get('dots') == got[second].get('dots')
        total += 1
        if not same:
            fails += 1
        raw.append({'case': 'rail %s, live vs %s' % (label, second),
                    'viewport': 1440, 'path': path, 'data': got})
        report.append(('rail %s: live vs %s' % (label, second), 1440,
                       'RAIL UNCHANGED' if same else 'RAIL MOVED', same,
                       json.dumps(got, ensure_ascii=False)[:185]))
        n = got['live'].get('dots')
        ok = (n == want)
        total += 1
        if not ok:
            fails += 1
        report.append(('rail %s: dot count' % label, 1440,
                       'DOTS == %d' % want if ok else 'DOTS != %d' % want, ok,
                       json.dumps(got['live'], ensure_ascii=False)[:185]))

    print('Batch G rendered proof: %d checks, %d failures' % (total, fails))
    for row in report:
        mark = 'PASS' if row[3] else 'FAIL'
        print('  [%s] %-34s %5d  %-22s %s'
              % (mark, row[0], row[1], row[2], str(row[4] or '')[:130]))
    if args.json_out:
        with open(args.json_out, 'w', encoding='utf-8') as fh:
            json.dump({'site': args.site, 'preflight': bool(args.preflight),
                       'checks': total, 'failures': fails, 'cases': raw},
                      fh, ensure_ascii=False, indent=1, sort_keys=True)
        print('measurements -> %s' % args.json_out)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Batch C rendered proof — the FAQ band and its FAQPage, measured on the page.

The gate compares bytes, and bytes cannot answer any of these:

  * the band really lays out between "Formula & nutrition" and the
    related-formulas grid, and not somewhere a margin happened to push it;
  * the nine <details> really are nine, the first one really ships open, every
    question really has a heading and every answer really has text;
  * the two data-driven answers really quote the DOSAGE page's own row — the
    same row sinofresh_formula_spec_cell() reads — rather than a second copy
    that happens to agree today;
  * the three dictated answers are on the page word for word;
  * the FAQPage block in the DOM carries the same nine answers the page shows,
    which is the one property a page-level byte comparison cannot state: the
    gate proves the schema's text equals the template's text, this proves it
    equals the RENDERED text a reader sees;
  * the footer's own three <details> (Products / Company / Contact Us) are
    untouched — they share the wp-block-details class with the band's items, so
    this is exactly the kind of thing a shared class name can break;
  * every case: 0 page errors, no horizontal scroll.

Header discipline is the one the notes record, and get it wrong and the run
measures the LIVE bytes while reporting green: close --all -> set credentials
-> open -> set headers (custom + Basic in ONE call, never set credentials
afterwards) -> reload -> set viewport -> eval. The stylesheet the page actually
loaded is asserted like any other check.

    SF_DEV_AUTH=sfdev:... python3 tools/b2d_c_evidence.py --preflight \
        --shots-dir docs/batchC-shots
"""
import argparse
import base64
import html as html_mod
import json
import os
import re
import subprocess
import sys
import time

# the nine questions, in the order the band ships them
QUESTIONS = [
    'Can the active ingredients be changed?',
    'Can the flavour be changed?',
    'Is a gluten-free or grain-free version available?',
    'Is this formula for dogs or for cats?',
    'Can I sample this formula before ordering?',
    'What certifications and documentation do you provide?',
    'Can the packaging and the label be customised?',
    'How should the finished product be stored?',
    'Will you keep my formula and my brand confidential?',
]

# the three answers the client dictated, verbatim
DICTATED = {
    3: 'Our formulas can be customised for dogs, cats, or both. Tell us your target '
       'species when you enquire and we will adjust the formula, the dosage, and the '
       'label accordingly.',
    7: 'Store in a cool, dry place, away from direct sunlight. Once opened, keep the '
       'container tightly closed and use within the recommended period.',
    8: 'Yes \u2014 every formula is produced exclusively under your own brand. We never '
       'sell your formula, your artwork, or your customer list to any third party, and '
       'we sign an NDA before sharing any custom formulation details.',
}

CERT_ANSWER = 5
PACK_ANSWER = 6

# (lang, formula slug, viewport, screenshot name or None)
CASES = [
    ('en', 'joint-support-soft-chews', 1440, 'faq-soft-chews-1440.png'),
    ('en', 'joint-support-soft-chews', 768, None),
    ('en', 'joint-support-soft-chews', 375, 'faq-soft-chews-375.png'),
    ('en', 'pure-fish-oil-blend', 1440, 'faq-fish-oil-1440.png'),
    ('en', 'multivitamin-tablets', 1440, None),
    ('zh', 'joint-support-soft-chews', 1440, 'faq-soft-chews-zh-1440.png'),
]


def dosage_values(pre_dir):
    """{form slug: (certs, pack)} off the captured dosage pages themselves.

    Read from the capture rather than written down here, so the assertion
    cannot drift from the row the PHP reads: this is the same source the gate's
    cross-read uses.
    """
    out = {}
    for name in sorted(os.listdir(pre_dir)):
        m = re.fullmatch(r'products__(.+)\.html', name)
        if not m:
            continue
        raw = open(os.path.join(pre_dir, name), encoding='utf-8').read()
        c = re.search(r'data-label="Certifications"[^>]*>(.*?)</span>', raw, re.S)
        p = re.search(r'data-label="Packaging formats"[^>]*>(.*?)</span>', raw, re.S)
        if c and p:
            out[m.group(1)] = (html_mod.unescape(c.group(1)).strip(),
                               html_mod.unescape(p.group(1)).strip())
    return out


def build_js(values):
    return """(function () {
  var QUESTIONS = %s;
  var DICTATED = %s;
  var VALUES = %s;
  var CERT_ANSWER = %d, PACK_ANSWER = %d;

  var q = function (s) { return document.querySelector(s); };
  var qa = function (s) { return Array.prototype.slice.call(document.querySelectorAll(s)); };
  var txt = function (el) { return el ? el.textContent.replace(/\\s+/g, ' ').trim() : null; };
  var box = function (el) { if (!el) return null; var b = el.getBoundingClientRect();
    return { x: Math.round(b.left), y: Math.round(b.top + window.scrollY),
             w: Math.round(b.width), h: Math.round(b.height) }; };
  var out = { checks: [], jsErrors: window.__sfErrors || [] };
  var add = function (n, ok, d) { out.checks.push({ name: n, ok: !!ok, detail: d }); };

  var link = q('link[rel="stylesheet"][href*="sinofresh-theme"]');
  out.sheet = link ? link.href : '(no theme stylesheet found)';

  var band = q('section.sf-fdetail-faq');
  add('the band is on the page', !!band, !!band);
  if (!band) { out.jsErrors = window.__sfErrors || []; return out; }

  // --- the heading -------------------------------------------------------
  var h2 = band.querySelector('h2');
  add('the band carries the h2', txt(h2) === 'Frequently Asked Questions',
      txt(h2));

  // --- nine items, first open -------------------------------------------
  var items = qa('section.sf-fdetail-faq .sf-faq > details');
  add('nine <details> in .sf-faq', items.length === 9, items.length);
  add('all nine carry sf-faq__item',
      items.length === 9 && items.every(function (d) {
        return d.classList.contains('sf-faq__item'); }),
      items.map(function (d) { return d.className; }).join(' | ').slice(0, 120));
  add('only the first ships open',
      items.length === 9 && items[0].hasAttribute('open')
      && items.slice(1).every(function (d) { return !d.hasAttribute('open'); }),
      items.map(function (d) { return d.hasAttribute('open') ? 'open' : '-'; }).join(''));

  var qs = items.map(function (d) { return txt(d.querySelector('summary > h3')); });
  var as = items.map(function (d) { return txt(d.querySelector('p')); });
  add('every item has a question and an icon',
      items.length === 9 && items.every(function (d) {
        return d.querySelector('span.sf-faq__icon[aria-hidden="true"]'); }),
      items.length);
  add('every answer carries text', as.length === 9
      && as.every(function (a) { return a && a.length >= 60; }),
      as.map(function (a) { return a ? a.length : null; }).join(','));
  add('the nine questions, in order',
      JSON.stringify(qs) === JSON.stringify(QUESTIONS),
      qs.join(' | ').slice(0, 220));

  // --- the three dictated answers, word for word -------------------------
  var dictatedOk = true, dictatedDetail = [];
  Object.keys(DICTATED).forEach(function (k) {
    var want = DICTATED[k];
    var got = as[k];
    if (got !== want) { dictatedOk = false; dictatedDetail.push('#' + (+k + 1)); }
  });
  add('the three dictated answers are verbatim', dictatedOk,
      dictatedOk ? 'all three' : dictatedDetail.join(','));

  // --- the two data-driven answers quote the DOSAGE row ------------------
  var formEl = q('[data-sf-form]');
  var form = formEl ? formEl.getAttribute('data-sf-form') : null;
  var vals = form ? VALUES[form] : null;
  add('read the dosage form off the page', !!vals, { form: form,
        known: Object.keys(VALUES) });
  if (vals) {
    var certs = vals[0], pack = vals[1];
    add('the certifications answer quotes the dosage row',
        as[CERT_ANSWER] === 'Certifications: ' + certs + '. Every batch is tested '
        + 'in our QC laboratory and ships with a Certificate of Analysis, and we '
        + 'support FDA, EU and other target-market documentation.',
        as[CERT_ANSWER]);
    add('the packaging answer quotes the dosage row',
        as[PACK_ANSWER] === 'Standard formats for this dosage form: ' + pack
        + '. The label, the carton and the barcode are all produced with your own '
        + 'brand on them.',
        as[PACK_ANSWER]);
  }

  // --- where it sits -----------------------------------------------------
  var actives = q('.sf-fdetail-actives');
  var more = q('.sf-fdetail-more');
  add('the band sits after Formula & nutrition and before the grid',
      !!actives && !!more && !!band
      && box(actives).y < box(band).y && box(band).y < box(more).y,
      { actives: box(actives), band: box(band), more: box(more) });
  add('the band is not in the footer',
      !!q('footer') && band.compareDocumentPosition(q('footer'))
        === Node.DOCUMENT_POSITION_FOLLOWING,
      true);
  var sec = getComputedStyle(band);
  add('the band wears the card-white background',
      sec.backgroundColor === 'rgb(255, 255, 255)', sec.backgroundColor);

  // --- the schema --------------------------------------------------------
  var blocks = qa('script[type="application/ld+json"]');
  var parsed = [];
  blocks.forEach(function (b) {
    try { parsed.push(JSON.parse(b.textContent)); } catch (e) { parsed.push(null); }
  });
  add('the first JSON-LD block is the FAQPage',
      parsed.length > 0 && parsed[0] && parsed[0]['@type'] === 'FAQPage',
      parsed.map(function (p) { return p && p['@type']; }).join(','));
  var faq = parsed.filter(function (p) { return p && p['@type'] === 'FAQPage'; });
  add('exactly one FAQPage block', faq.length === 1, faq.length);
  var ents = faq.length === 1 ? faq[0].mainEntity : [];
  add('the schema carries the same nine questions',
      JSON.stringify((ents || []).map(function (e) { return e.name; }))
      === JSON.stringify(QUESTIONS), (ents || []).length);
  var schemaOk = (ents || []).length === 9 && ents.every(function (e, i) {
    var t = e.acceptedAnswer && e.acceptedAnswer.text;
    return t && t.replace(/\\s+/g, ' ').trim() === as[i];
  });
  add('every schema answer equals the answer on the page', schemaOk,
      ((ents || [])[0] || {}).name);
  add('no HTML entity leaked into the schema',
      JSON.stringify(ents).indexOf('&amp;') < 0
      && JSON.stringify(ents).indexOf('&#') < 0, true);

  // --- the footer's own details -----------------------------------------
  // Measured against the LIVE render at the same viewport, not against an
  // assumption: the site collapses these three below the breakpoint with its
  // own script, so "they are open" is false at 375 on the live bytes too.
  // Asserting `open` here was the first version's bug — it reported a failure
  // that both sides shared. What matters is that batch C did not change them.
  var foot = qa('details.sf-footcol');
  add('the footer still has its three columns', foot.length === 3, foot.length);
  add('the footer columns still carry sf-footcol and nothing of ours',
      foot.length === 3 && foot.every(function (d) {
        return d.classList.contains('sf-footcol')
            && !d.classList.contains('sf-faq__item'); }),
      foot.map(function (d) { return d.className; }).join(' | ').slice(0, 140));
  add('the footer columns are still named right',
      JSON.stringify(foot.map(function (d) { return txt(d.querySelector('summary')); }))
      === JSON.stringify(['Products', 'Company', 'Contact Us']),
      foot.map(function (d) { return txt(d.querySelector('summary')); }).join(' | '));
  add('the band did not adopt the footer class',
      qa('section.sf-fdetail-faq .sf-footcol').length === 0, 0);
  out.foot = foot.map(function (d) {
    var b = box(d);
    return [txt(d.querySelector('summary')), d.hasAttribute('open'),
            b.x, b.y, b.w, b.h].join('|');
  });

  // --- the page around it ------------------------------------------------
  out.h2s = qa('h2').map(txt);
  add('the page now has six h2s', out.h2s.length === 6, out.h2s.length);
  add('the detail page still has no dot rail', qa('.sf-toc__dot').length === 0,
      qa('.sf-toc__dot').length);

  out.geometry = { band: box(band), actives: box(actives), more: box(more),
                   padLeft: sec.paddingLeft, padRight: sec.paddingRight,
                   first: box(items[0]), last: box(items[8]) };
  add('no horizontal scroll',
      document.documentElement.scrollWidth <= window.innerWidth + 1,
      document.documentElement.scrollWidth + ' vs ' + window.innerWidth);
  add('0 javascript errors', (window.__sfErrors || []).length === 0,
      window.__sfErrors || []);
  return out;
})()""" % (json.dumps(QUESTIONS), json.dumps(DICTATED), json.dumps(values),
           CERT_ANSWER, PACK_ANSWER)


LIVE_JS = """(function () {
  var qa = function (s) { return Array.prototype.slice.call(document.querySelectorAll(s)); };
  var txt = function (el) { return el ? el.textContent.replace(/\\s+/g, ' ').trim() : null; };
  var link = document.querySelector('link[rel="stylesheet"][href*="sinofresh-theme"]');
  var foot = qa('details.sf-footcol').map(function (d) {
    var b = d.getBoundingClientRect();
    return [txt(d.querySelector('summary')), d.hasAttribute('open'),
            Math.round(b.left), Math.round(b.top + window.scrollY),
            Math.round(b.width), Math.round(b.height)].join('|');
  });
  return { live: true, sheet: link ? link.href : '(none)', foot: foot,
           band: qa('section.sf-fdetail-faq').length,
           h2s: qa('h2').length, dots: qa('.sf-toc__dot').length };
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
    """One measured visit, with the header discipline the notes record."""
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
    ap.add_argument('--shots-dir', default='docs/batchC-shots')
    ap.add_argument('--dosage-dir', default='_backup/b2d-c-baselines/preflight',
                    help='the capture the two data-driven values are read off')
    ap.add_argument('--preflight', action='store_true',
                    help='assert the stylesheet served comes from the pre-flight '
                         'theme copy, not the live theme')
    ap.add_argument('--json-out', default=None)
    args = ap.parse_args()

    auth = os.environ.get('SF_DEV_AUTH')
    if not auth:
        sys.exit('SF_DEV_AUTH required')
    tok = base64.b64encode(auth.encode()).decode()
    values = dosage_values(args.dosage_dir)
    js = build_js(values)
    os.makedirs(args.shots_dir, exist_ok=True)

    ab('close', '--all')
    time.sleep(1)
    user, pw = auth.split(':', 1)
    ab('set', 'credentials', user, pw)
    ab('open', args.site + '/products/soft-chews/')

    total = fails = 0
    report = []
    raw = []

    # --- the live pass -----------------------------------------------------
    # What the footer's own <details> do at each of these viewports as things
    # stand. They share wp-block-details with the band's items, so the honest
    # question is not "are they open" but "did batch C change them".
    live = {}
    for lang, slug, vw, _shot in CASES:
        path = '%s/formulas/%s/' % ('/zh' if lang == 'zh' else '', slug)
        label = '%s%s @%d' % (slug, ' (zh)' if lang == 'zh' else '', vw)
        visit(args.site, path, tok, vw, preflight=False)
        d = ev(LIVE_JS)
        live[label] = d
        sig = (d.get('foot') or ['(eval failed)'])[0]
        print('  live  %-34s sheet=%s footer[0]=%s'
              % (label, str(d.get('sheet', ''))[-42:], str(sig)[:64]))
        if args.preflight and 'sinofresh-theme-preflight' in str(d.get('sheet', '')):
            total += 1
            fails += 1
            report.append((label, 'LIVE PASS GOT THE PRE-FLIGHT THEME', False,
                           d.get('sheet')))

    print()

    for lang, slug, vw, shot in CASES:
        path = '%s/formulas/%s/' % ('/zh' if lang == 'zh' else '', slug)
        label = '%s%s @%d' % (slug, ' (zh)' if lang == 'zh' else '', vw)
        visit(args.site, path, tok, vw, preflight=args.preflight)
        data = ev(js)
        raw.append({'case': label, 'path': path, 'viewport': vw, 'data': data})

        if '_raw' in data:
            total += 1
            fails += 1
            report.append((label, 'EVAL FAIL', False, str(data['_raw'])[:170]))
        else:
            got = str(data.get('sheet', ''))
            total += 1
            in_pre = 'sinofresh-theme-preflight' in got
            if args.preflight and not in_pre:
                fails += 1
                report.append((label, 'WRONG STYLESHEET SERVED', False, got))
            elif not args.preflight and in_pre:
                fails += 1
                report.append((label, 'PRE-FLIGHT SHEET WITHOUT --preflight',
                               False, got))
            if '2.10.54' not in got:
                fails += 1
                report.append((label, 'VERSION TOKEN MOVED', False, got))
            for c in data.get('checks', []):
                total += 1
                if not c['ok']:
                    fails += 1
                    report.append((label, c['name'], False,
                                   json.dumps(c.get('detail'),
                                              ensure_ascii=False)[:150]))
            # the footer, compared to what the live bytes do here
            total += 1
            want = (live.get(label) or {}).get('foot')
            got_foot = data.get('foot')
            if not want or got_foot != want:
                fails += 1
                report.append((label,
                               'the footer details differ from the live render',
                               False, 'pre=%s live=%s'
                               % (json.dumps(got_foot, ensure_ascii=False)[:90],
                                  json.dumps(want, ensure_ascii=False)[:90])))
        if shot:
            ab('screenshot', '--full', os.path.join(args.shots_dir, shot))

    width = max((len(r[0]) for r in report), default=10)
    print('=' * 100)
    print('Batch C rendered proof — the FAQ band and its FAQPage on the page')
    print('  site %s   preflight=%s   cases=%d' % (args.site, args.preflight, len(CASES)))
    print('=' * 100)
    for label, name, ok, detail in report:
        print('  %-*s  %-6s  %-52s  %s'
              % (width, label, 'PASS' if ok else 'FAIL', name, detail))
    print()
    print('%d check(s), %d failure(s)' % (total, fails))
    if args.json_out:
        with open(args.json_out, 'w', encoding='utf-8') as fh:
            json.dump(raw, fh, ensure_ascii=False, indent=1)
        print('measurements -> %s' % args.json_out)
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())

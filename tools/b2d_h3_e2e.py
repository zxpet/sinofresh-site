#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H3 — the browser end-to-end pass (E1-E7).

Same launch discipline as H2b1/H2b2, for the same measured reasons: a shell loop
drifts between iterations, `set headers` and `set credentials` each rebuild the
browser context, and the init-script mechanism only takes effect on the command
that *boots* the browser — which is `set credentials`, not `open`. The only
workable order is

    close --all -> set credentials -> open <origin>
                -> set headers{Authorization + X-SF-Preflight} -> errors --clear
                -> open <url> -> reload -> set viewport -> eval/screenshot

Every capture asserts it is looking at the pre-flight copy, not the live theme
(a wrong order does not error — it silently compares the live bytes and reports
green). The assertion is the stylesheet href, which must name the copy's
directory and carry the version this batch ships.

What each step is for:

E1  The two bands exist, sit in the template's order, and their headings keep
    the document outline: the content band's group heading stays an h2 (the
    "flat h2" design), and only the sampling band introduces h3s — its four
    step titles. Measured on both languages, because the two bands render from
    the same shortcodes and a language-specific failure would be invisible in
    the other.

E2  The page and its structured data cannot drift. The four steps are read out
    of the rendered DOM and out of the page's own HowTo JSON-LD and compared
    one by one. This is the browser-side twin of the gate's parsed-JSON check:
    the gate proves the served bytes came from sinofresh_sampling_steps(), and
    this proves the browser agrees with them.

E3  "One continuous card-white reading surface" is a claim about what a reader
    sees, so it is measured as such: for every band from Specification to the
    sampling band, walk up to the first ancestor that actually paints a colour,
    and require the same opaque colour. The bg-light band that opens the light
    tail is required to differ — otherwise the assertion would hold on a page
    where nothing was white at all.

E4  The marker: 44x44, circular, primary background, card-white numeral — read
    from computed style rather than from the stylesheet, so a variable that
    fails to resolve shows up.

E5  Responsive behaviour. The four-step row is declared as four columns on
    desktop and one column at <=768px, and the band's inset changes at 1240px
    and 768px. Both boundaries are probed on the pixel where they flip, and no
    viewport may scroll sideways.

E6  The invariants this batch must not have disturbed, all in one place: a
    formula detail page carries no point rail (its script is not enqueued), the
    hero CTA is present, the floating buttons are present.

E7  The FAQ accordion still opens, with a real mouse and a hit test rather than
    a synthetic click, because the failure this catches is an overlay covering
    the summary — which a synthetic click would not notice.

usage:
    b2d_h3_e2e.py --out DIR [--auth user:pass]
"""

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOST = 'https://dev.zxpet.com'
PRE = '/wp-content/themes/sinofresh-theme-preflight'
STYLE_HREF = '/sinofresh-theme-preflight/style.css?ver=2.10.57'

# The palette, from theme.json. Assertions compare against these rather than
# against whatever the browser reports first.
PRIMARY = 'rgb(27, 77, 62)'          # --wp--preset--color--primary   #1B4D3E
BRAND_GREEN = 'rgb(90, 183, 53)'     # --wp--preset--color--brand-green #5AB735
CARD_WHITE = 'rgb(255, 255, 255)'    # --wp--preset--color--card-white #FFFFFF
BG_LIGHT = 'rgb(243, 246, 244)'      # --wp--preset--color--bg-light   #F3F6F4
TEXT_SECONDARY = 'rgb(95, 107, 101)'  # --wp--preset--color--text-secondary

PAGES = [('/formulas/joint-support-soft-chews/', 'EN'),
         ('/zh/formulas/joint-support-soft-chews/', 'ZH')]

STEP_TITLES = ['Submit Inquiry', 'Confirm Details', 'Sampling & Quality Check',
               'Ship & Evaluate']

# (width, height, expected columns, expected left padding, label)
VIEWPORTS = [(1440, 1000, 4, '0px', 'desktop'),
             (1241, 1000, 4, '0px', 'just above the 1240 boundary'),
             (1240, 1000, 4, '38px', 'the 1240 boundary itself'),
             (1101, 1000, 4, '38px', 'just above 1100'),
             (1024, 1000, 4, '38px', 'tablet landscape'),
             (769, 1000, 4, '38px', 'just above the 768 boundary'),
             (768, 1000, 1, '20px', 'the 768 boundary itself'),
             (480, 900, 1, '20px', 'phone')]

MEASURE = r"""
(() => {
  const cs = el => getComputedStyle(el);
  const q = (s, r) => (r || document).querySelector(s);
  const qa = (s, r) => [...(r || document).querySelectorAll(s)];

  // The colour a reader actually sees behind this element: walk up to the first
  // ancestor that paints something opaque. Computing only the element's own
  // background would call a transparent band "transparent" and say nothing.
  const effBg = el => {
    let n = el;
    while (n && n !== document.documentElement) {
      const m = cs(n).backgroundColor.match(/rgba?\(([^)]+)\)/);
      if (m) {
        const p = m[1].split(',').map(x => parseFloat(x));
        const a = p.length > 3 ? p[3] : 1;
        if (a > 0) return (p.length > 3 && a < 1)
          ? 'rgba(' + p[0] + ', ' + p[1] + ', ' + p[2] + ', ' + a + ')'
          : 'rgb(' + p[0] + ', ' + p[1] + ', ' + p[2] + ')';
      }
      n = n.parentElement;
    }
    return 'none';
  };
  const rect = el => {
    const r = el.getBoundingClientRect();
    return {top: Math.round(r.top + scrollY), left: Math.round(r.left + scrollX),
            w: Math.round(r.width), h: Math.round(r.height)};
  };
  const band = el => el ? {
    cls: String(el.className).split(/\s+/).filter(c => c.startsWith('sf-')
         || c.startsWith('has-')).join('.'),
    effBg: effBg(el), padTop: cs(el).paddingTop, padLeft: cs(el).paddingLeft,
    padBottom: cs(el).paddingBottom, box: rect(el)
  } : null;

  const spec     = qa('section.sf-fdetail').filter(s => !s.classList.contains('sf-fdetail-faq'))[0] || null;
  const actives  = q('.sf-fdetail-actives');
  const content  = q('.sf-fdetail-content');
  const faq      = q('.sf-fdetail-faq');
  const sampling = q('.sf-sampling');
  const more     = q('.sf-fdetail-more');
  const media    = q('.sf-fdetail2');

  const steps = qa('.sf-sampling__step');
  const nums  = qa('.sf-sampling__num');
  const ncs   = nums[0] ? cs(nums[0]) : null;
  const nb    = nums[0] ? rect(nums[0]) : null;

  // Positions of the steps: same top => same row.
  const tops = steps.map(li => rect(li).top);
  const rows = [...new Set(tops)].length;
  const firstRow = tops.length ? tops.filter(t => t === tops[0]).length : 0;

  let schema = null;
  for (const s of qa('script[type="application/ld+json"]')) {
    try { const o = JSON.parse(s.textContent);
          if (o && o['@type'] === 'HowTo') schema = o; } catch (e) {}
  }
  const txt = (el) => el ? el.textContent.replace(/\s+/g, ' ').trim() : null;
  const domSteps = steps.map(li => ({
    title: txt(q('.sf-sampling__step-title', li)),
    text: txt(q('.sf-sampling__desc', li))
  }));
  const schemaSteps = schema ? schema.step.map(s => ({title: s.name, text: s.text})) : null;

  const cHead = content ? qa('h1,h2,h3,h4', content).map(h => ({
    tag: h.tagName.toLowerCase(), cls: String(h.className),
    text: txt(h)})) : [];
  const sHead = sampling ? qa('h1,h2,h3,h4', sampling).map(h => ({
    tag: h.tagName.toLowerCase(), cls: String(h.className),
    text: txt(h)})) : [];

  const styleLink = q('link[rel="stylesheet"][href*="sinofresh-theme"]');

  return {
    href: location.href,
    lang: document.documentElement.lang,
    sheet: styleLink ? styleLink.getAttribute('href') : null,
    viewportW: innerWidth,
    docScrollWidth: document.documentElement.scrollWidth,
    bodyScrollWidth: document.body.scrollWidth,
    h1Count: document.querySelectorAll('h1').length,
    bands: {
      media: band(media), spec: band(spec), actives: band(actives),
      content: band(content), faq: band(faq), sampling: band(sampling),
      more: band(more)
    },
    order: [
      ['media', media], ['spec', spec], ['actives', actives], ['content', content],
      ['faq', faq], ['sampling', sampling], ['more', more]
    ].map(([k, el]) => [k, el ? rect(el).top : -1]),
    counts: {
      contentBlocks: qa('.sf-fdetail-content__block').length,
      contentSpecs: qa('.sf-fdetail-content__spec').length,
      contentChips: qa('.sf-fdetail-content__chip').length,
      contentCartons: qa('.sf-fdetail-content__cartons').length,
      contentH2: content ? content.querySelectorAll('h2').length : -1,
      contentH3: content ? content.querySelectorAll('h3').length : -1,
      samplingSections: qa('.sf-sampling').length,
      samplingH2: sampling ? sampling.querySelectorAll('h2').length : -1,
      samplingH3: sampling ? sampling.querySelectorAll('h3').length : -1,
      steps: steps.length,
      nums: nums.length,
      note: qa('.sf-sampling__note').length,
      contentLabels: qa('.sf-fdetail-content__label').map(e => txt(e)),
      contentHeadings: cHead,
      samplingHeadings: sHead,
      faqItems: qa('.sf-fdetail-faq details').length,
      faqOpen: qa('.sf-fdetail-faq details[open]').length,
      pageDetails: qa('details').length,
      gridCards: qa('.sf-fgrid a, .sf-fgrid .sf-fgrid__card').length,
      toc: qa('.sf-toc').length,
      quoteCta: qa('.sf-quote-cta').length,
      heroBuild: qa('.sf-formula-hero__build').length,
      floatBtns: qa('.sf-float-btn').length,
      heroH2: qa('h2').filter(h => /^Build Your /.test(txt(h) || '')).length
    },
    num: nb ? {w: nb.w, h: nb.h, radius: ncs.borderRadius, bg: ncs.backgroundColor,
               color: ncs.color, fontSize: ncs.fontSize, fontWeight: ncs.fontWeight}
            : null,
    stepLayout: {rows: rows, firstRow: firstRow, tops: tops,
                 titleFontSize: steps[0] ? cs(q('.sf-sampling__step-title', steps[0])).fontSize : null,
                 titleWeight: steps[0] ? cs(q('.sf-sampling__step-title', steps[0])).fontWeight : null,
                 titleTag: steps[0] && q('.sf-sampling__step-title', steps[0])
                           ? q('.sf-sampling__step-title', steps[0]).tagName.toLowerCase() : null,
                 descFontSize: steps[0] ? cs(q('.sf-sampling__desc', steps[0])).fontSize : null,
                 descColor: steps[0] ? cs(q('.sf-sampling__desc', steps[0])).color : null,
                 numMarginTop: nums[0] ? cs(nums[0]).marginTop : null},
    noteStyle: (() => { const n = q('.sf-sampling__note');
                        return n ? {color: cs(n).color, fontWeight: cs(n).fontWeight,
                                    fontSize: cs(n).fontSize, text: txt(n)} : null; })(),
    domSteps: domSteps, schemaSteps: schemaSteps,
    schemaName: schema ? schema.name : null,
    schemaTotalTime: schema ? schema.totalTime : null,
    samplingTitle: sampling ? txt(q('.sf-sampling__title', sampling)) : null,
    contentHeadingText: content ? txt(q('.sf-fdetail-content__heading, .sf-fdetail-content__subtitle', content)) : null,
    contentHeadingTag: content && q('.sf-fdetail-content__heading, .sf-fdetail-content__subtitle', content)
                       ? q('.sf-fdetail-content__heading, .sf-fdetail-content__subtitle', content).tagName.toLowerCase() : null
  };
})()
"""

HIT = r"""
(() => {
  const faq = document.querySelector('.sf-fdetail-faq');
  if (!faq) return {found: false, why: 'no FAQ band'};
  const all = [...faq.querySelectorAll('details')];
  // A closed one: clicking an already-open answer would close it, which is
  // correct behaviour but not what this step is here to prove.
  const target = all.filter(d => !d.open)[0];
  if (!target) return {found: false, why: 'every FAQ answer is already open', items: all.length};
  const s = target.querySelector('summary');
  if (!s) return {found: false, why: 'no summary'};
  s.scrollIntoView({block: 'center', behavior: 'instant'});
  const r = s.getBoundingClientRect();
  const x = Math.round(r.left + r.width / 2), y = Math.round(r.top + r.height / 2);
  const hit = document.elementFromPoint(x, y);
  const outside = [...document.querySelectorAll('details')].filter(d => !faq.contains(d));
  return {found: true, x: x, y: y, w: Math.round(r.width), h: Math.round(r.height),
          hitTag: hit ? hit.tagName.toLowerCase() : null,
          hitIsSummary: hit === s || s.contains(hit),
          items: all.length,
          openBefore: all.filter(d => d.open).length,
          targetIndex: all.indexOf(target),
          allDetails: document.querySelectorAll('details').length,
          outside: outside.length,
          outsideOpen: outside.filter(d => d.open).length};
})()
"""

# Re-validate the SAME coordinates after the mouse moved. If the layout shifted
# the anchor, the click would land on a different element — and the earlier
# reading, taken before the move, would still say the hit was clean.
REHIT = r"""
(function (x, y) {
  const faq = document.querySelector('.sf-fdetail-faq');
  const all = [...faq.querySelectorAll('details')];
  const t = all.filter(d => !d.open)[0];
  const s = t ? t.querySelector('summary') : null;
  const hit = document.elementFromPoint(x, y);
  return {hitIsSummary: !!(s && (hit === s || s.contains(hit))),
          hitTag: hit ? hit.tagName.toLowerCase() : null};
})(%d, %d)
"""

AFTER = r"""
(() => {
  const faq = document.querySelector('.sf-fdetail-faq');
  const all = [...faq.querySelectorAll('details')];
  const outside = [...document.querySelectorAll('details')].filter(d => !faq.contains(d));
  return {open: all.filter(d => d.open).length, items: all.length,
          allDetails: document.querySelectorAll('details').length,
          outside: outside.length, outsideOpen: outside.filter(d => d.open).length};
})()
"""


def run(args, timeout=180, env=None):
    e = dict(os.environ)
    e.update(env or {})
    p = subprocess.run(args, capture_output=True, text=True, timeout=timeout, env=e)
    return p.returncode, (p.stdout or '').strip(), (p.stderr or '').strip()


def ev(script, timeout=180, env=None):
    """agent-browser eval prints a JSON string literal: decode twice."""
    enc = base64.b64encode(script.encode('utf-8')).decode('ascii')
    rc, out, err = run(['agent-browser', 'eval', '-b', enc], timeout, env)
    if rc != 0:
        raise RuntimeError('eval failed: %s %s' % (out, err))
    try:
        first = json.loads(out)
    except Exception:
        return out
    if isinstance(first, str):
        try:
            return json.loads(first)
        except Exception:
            return first
    return first


class E2E(object):
    def __init__(self, args):
        self.args = args
        self.fails = []
        self.notes = []
        self.rows = {}
        self.env = None

    def fail(self, msg):
        self.fails.append(msg)
        print('   FAIL %s' % msg)

    def ok(self, msg):
        self.notes.append(msg)
        print('   ok   %s' % msg)

    def attach(self):
        b64 = base64.b64encode(self.args.auth.encode('utf-8')).decode('ascii')
        self.env = None
        run(['agent-browser', 'close', '--all'])
        user, _, pw = self.args.auth.partition(':')
        rc, out, err = run(['agent-browser', 'set', 'credentials', user, pw])
        if rc != 0:
            raise SystemExit('FATAL set credentials: %s %s' % (out, err))
        rc, out, err = run(['agent-browser', 'open', HOST + '/'])
        if rc != 0:
            raise SystemExit('FATAL open: %s %s' % (out, err))
        hdrs = json.dumps({'Authorization': 'Basic ' + b64, 'X-SF-Preflight': '1'})
        run(['agent-browser', 'set', 'headers', hdrs])
        run(['agent-browser', 'errors', '--clear'])

    def goto(self, path, w, h, tag):
        url = HOST + path + '?sfcap=%s%s%s' % (tag, time.strftime('%H%M%S'), w)
        run(['agent-browser', 'open', url], env=self.env)
        run(['agent-browser', 'reload'], env=self.env)
        run(['agent-browser', 'set', 'viewport', str(w), str(h)], env=self.env)
        time.sleep(0.6)
        probe = ev(MEASURE, env=self.env)
        got = probe.get('viewportW')
        if got is None or abs(got - w) > 2:
            raise SystemExit('FATAL the viewport did not take: asked %d, innerWidth is '
                             '%s. agent-browser takes `set viewport <w> <h>` as TWO '
                             'arguments; a single "WxH" argument is accepted and '
                             'silently ignored, so every width would measure the same '
                             'layout.' % (w, got))
        sheet = probe.get('sheet') or ''
        if 'sinofresh-theme-preflight' not in sheet or 'ver=2.10.57' not in sheet:
            raise SystemExit('FATAL not the pre-flight copy of this batch — got %r. A wrong '
                             'header order silently serves the live theme.' % sheet)
        return probe

    def errors(self):
        rc, out, _ = run(['agent-browser', 'errors'], env=self.env)
        txt = out.strip()
        if not txt or txt.lower() in ('no errors', 'none', '[]'):
            return []
        try:
            return json.loads(txt)
        except Exception:
            return [txt]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--auth', default=os.environ.get('SF_DEV_AUTH', 'sfdev:VkEws18Kl5V1qp3TpZ6s'))
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    e = E2E(args)
    e.attach()

    # ------------------------------------------------------------------ E1 --
    print('E1  the two bands: presence, order, document outline')
    for path, lang in PAGES:
        p = e.goto(path, 1440, 1000, 'e1' + lang)
        e.rows['E1_' + lang] = p
        b, c = p['bands'], p['counts']
        if b['content'] is None:
            e.fail('%s: no .sf-fdetail-content' % lang)
        if b['sampling'] is None:
            e.fail('%s: no .sf-sampling' % lang)
        if b['content'] and b['sampling']:
            ok_order = ([k for k, _ in p['order']] ==
                        ['media', 'spec', 'actives', 'content', 'faq', 'sampling', 'more'])
            tops = [t for _, t in p['order']]
            if not ok_order or tops != sorted(tops) or -1 in tops:
                e.fail('%s: band order wrong: %s' % (lang, p['order']))
            else:
                e.ok('%s: order media < spec < actives < content < faq < sampling < more' % lang)
            if c['contentH3'] != 0 or c['contentH2'] < 1:
                e.fail('%s: content band has %d h2 / %d h3 (want >=1 and 0)'
                       % (lang, c['contentH2'], c['contentH3']))
            elif p['contentHeadingTag'] != 'h2':
                e.fail('%s: the group heading is <%s>, not h2' % (lang, p['contentHeadingTag']))
            else:
                e.ok('%s: content band group heading is h2, no h3 (%d block(s), %d spec(s))'
                     % (lang, c['contentBlocks'], c['contentSpecs']))
            if c['contentLabels']:
                e.ok('%s: content band labels %s' % (lang, c['contentLabels']))
            if c['steps'] != 4 or c['samplingH3'] != 4 or c['samplingH2'] != 1:
                e.fail('%s: sampling band has %d steps / %d h2 / %d h3 (want 4/1/4)'
                       % (lang, c['steps'], c['samplingH2'], c['samplingH3']))
            else:
                e.ok('%s: sampling band is 1 h2 title + 4 h3 steps' % lang)
            if p['samplingTitle'] != 'How Sampling Works':
                e.fail('%s: sampling title %r' % (lang, p['samplingTitle']))
            titles = [s['title'] for s in p['domSteps']]
            if titles != STEP_TITLES:
                e.fail('%s: step titles %s' % (lang, titles))
            else:
                e.ok('%s: the four step titles are the declared ones' % lang)
            if c['note'] != 1:
                e.fail('%s: %d .sf-sampling__note (want 1)' % (lang, c['note']))
            else:
                e.ok('%s: exactly one note line states the turnaround' % lang)

    # ------------------------------------------------------------------ E2 --
    print('E2  the page and its HowTo schema cannot drift')
    for path, lang in PAGES:
        p = e.rows.get('E1_' + lang) or e.goto(path, 1440, 1000, 'e2' + lang)
        if p['schemaSteps'] is None:
            e.fail('%s: no HowTo JSON-LD on the page' % lang)
            continue
        if p['domSteps'] != p['schemaSteps']:
            e.fail('%s: the DOM steps and the schema steps differ:\n      dom=%s\n      sch=%s'
                   % (lang, p['domSteps'], p['schemaSteps']))
        else:
            e.ok('%s: all 4 steps agree between the DOM and the JSON-LD, title and text' % lang)
        if p['schemaTotalTime'] != 'P3D':
            e.fail('%s: totalTime %r' % (lang, p['schemaTotalTime']))
        if p['schemaName'] != 'How Sampling Works':
            e.fail('%s: schema name %r' % (lang, p['schemaName']))
        if p['noteStyle'] and p['noteStyle']['text'] != 'Typically 3-7 working days.':
            e.fail('%s: the note reads %r' % (lang, p['noteStyle']['text']))

    # ------------------------------------------------------------------ E3 --
    print('E3  one continuous white reading surface')
    for path, lang in PAGES:
        p = e.rows.get('E1_' + lang) or e.goto(path, 1440, 1000, 'e3' + lang)
        b = p['bands']
        white = [b[k]['effBg'] for k in ('spec', 'actives', 'content', 'faq', 'sampling')]
        if len(set(white)) != 1:
            e.fail('%s: the reading surface is not one colour: %s'
                   % (lang, dict(zip(('spec', 'actives', 'content', 'faq', 'sampling'), white))))
        elif white[0] != CARD_WHITE:
            e.fail('%s: the reading surface is %s, not card-white %s' % (lang, white[0], CARD_WHITE))
        else:
            e.ok('%s: spec -> actives -> content -> FAQ -> sampling are all %s' % (lang, CARD_WHITE))
        above, below = b['media']['effBg'], b['more']['effBg']
        if above != BG_LIGHT or below != BG_LIGHT:
            e.fail('%s: the light bands around it are %s / %s, want %s (otherwise "all one '
                   'colour" would hold on a page with no white at all)'
                   % (lang, above, below, BG_LIGHT))
        else:
            e.ok('%s: the gallery band above and the related grid below are both bg-light %s'
                 % (lang, BG_LIGHT))

    # ------------------------------------------------------------------ E4 --
    print('E4  the step marker and the step type')
    for path, lang in PAGES:
        p = e.rows.get('E1_' + lang) or e.goto(path, 1440, 1000, 'e4' + lang)
        n, sl = p['num'], p['stepLayout']
        if not n:
            e.fail('%s: no .sf-sampling__num' % lang)
        else:
            if (n['w'], n['h']) != (44, 44) or n['radius'] not in ('50%', '22px'):
                e.fail('%s: marker is %dx%d radius %s (want 44x44 circular)'
                       % (lang, n['w'], n['h'], n['radius']))
            if n['bg'] != PRIMARY:
                e.fail('%s: marker background %s, want primary %s (brand-green would be '
                       '2.7:1 on white)' % (lang, n['bg'], PRIMARY))
            if n['color'] != CARD_WHITE:
                e.fail('%s: marker numeral colour %s' % (lang, n['color']))
            if (n['fontSize'], n['fontWeight']) != ('16px', '700'):
                e.fail('%s: marker type %s/%s' % (lang, n['fontSize'], n['fontWeight']))
            if n['bg'] == PRIMARY and n['color'] == CARD_WHITE and (n['w'], n['h']) == (44, 44):
                e.ok('%s: 44x44 circular, primary %s background, card-white numeral' % (lang, PRIMARY))
        if sl['titleTag'] != 'h3':
            e.fail('%s: step title is <%s>, want h3' % (lang, sl['titleTag']))
        if sl['titleFontSize'] != '17px':
            e.fail('%s: step title is %s, want 17px' % (lang, sl['titleFontSize']))
        if sl['descColor'] != TEXT_SECONDARY:
            e.fail('%s: step copy colour %s, want text-secondary %s'
                   % (lang, sl['descColor'], TEXT_SECONDARY))
        else:
            e.ok('%s: h3 17px titles, step copy in text-secondary' % lang)
        if p['noteStyle'] and p['noteStyle']['color'] != PRIMARY:
            e.fail('%s: the note colour %s' % (lang, p['noteStyle']['color']))

    # ------------------------------------------------------------------ E5 --
    print('E5  responsive: the row, the inset, and no sideways scroll')
    for path, lang in PAGES:
        before = len(e.fails)
        for w, h, want_cols, want_pad, label in VIEWPORTS:
            p = e.goto(path, w, h, 'e5%s%d' % (lang, w))
            e.rows['E5_%s_%d' % (lang, w)] = p
            sl, b = p['stepLayout'], p['bands']
            if sl['firstRow'] != want_cols:
                e.fail('%s @%d (%s): %d steps in the first row, want %d (tops %s)'
                       % (lang, w, label, sl['firstRow'], want_cols, sl['tops']))
            if b['sampling']['padLeft'] != want_pad:
                e.fail('%s @%d (%s): sampling inset %s, want %s'
                       % (lang, w, label, b['sampling']['padLeft'], want_pad))
            if p['docScrollWidth'] > p['viewportW'] + 1:
                e.fail('%s @%d: the page scrolls sideways (%d > %d)'
                       % (lang, w, p['docScrollWidth'], p['viewportW']))
        if len(e.fails) == before:
            e.ok('%s: 4 columns down to 769px, 1 column from 768px, insets 0/38/20px, '
                 'no sideways scroll at any of the 8 viewports' % lang)

    # ------------------------------------------------------------------ E6 --
    print('E6  the invariants this batch must not have disturbed')
    for path, lang in PAGES:
        p = e.rows.get('E1_' + lang) or e.goto(path, 1440, 1000, 'e6' + lang)
        c = p['counts']
        if c['toc'] != 0:
            e.fail('%s: the detail page carries %d point rails' % (lang, c['toc']))
        if c['quoteCta'] < 1:
            e.fail('%s: the hero CTA is gone' % lang)
        if c['floatBtns'] < 2:
            e.fail('%s: only %d floating buttons' % (lang, c['floatBtns']))
        if c['heroH2'] != 0:
            e.fail('%s: the "Build Your ..." h2 is back (%d)' % (lang, c['heroH2']))
        if c['toc'] == 0 and c['quoteCta'] >= 1 and c['floatBtns'] >= 2:
            e.ok('%s: no point rail, hero CTA present, %d floating buttons, no configurator h2'
                 % (lang, c['floatBtns']))

    # ------------------------------------------------------------------ E7 --
    print('E7  the FAQ accordion still opens, with a real mouse')
    for path, lang in PAGES:
        p = e.rows.get('E1_' + lang) or e.goto(path, 1440, 1000, 'e7' + lang)
        c = p['counts']
        if p['h1Count'] != 1:
            e.fail('%s: %d h1 on the page' % (lang, p['h1Count']))
        if c['gridCards'] < 2:
            e.fail('%s: the related grid has %d cards' % (lang, c['gridCards']))
        if c['faqItems'] != 9:
            e.fail('%s: %d FAQ answers inside the FAQ band, want 9' % (lang, c['faqItems']))
        if c['faqOpen'] != 1:
            e.fail('%s: %d FAQ answers start open, want exactly 1 (the block opens its first)'
                   % (lang, c['faqOpen']))
        e.goto(path, 1440, 1000, 'e7b' + lang)
        h = ev(HIT, env=e.env)
        time.sleep(0.3)
        if not h.get('found'):
            e.fail('%s: nothing to click in the FAQ (%s)' % (lang, h))
            continue
        if not h.get('hitIsSummary'):
            e.fail('%s: the summary is covered at its own centre by <%s> — a real click would '
                   'miss' % (lang, h.get('hitTag')))
            continue
        run(['agent-browser', 'mouse', 'move', str(h['x']), str(h['y'])], env=e.env)
        time.sleep(0.2)
        again = ev(REHIT % (h['x'], h['y']), env=e.env)
        if not again.get('hitIsSummary'):
            e.fail('%s: after the mouse moved the hit test changed to <%s>'
                   % (lang, again.get('hitTag')))
            continue
        run(['agent-browser', 'mouse', 'down'], env=e.env)
        time.sleep(0.05)
        run(['agent-browser', 'mouse', 'up'], env=e.env)
        time.sleep(0.5)
        a = ev(AFTER, env=e.env)
        if a.get('open') == h['openBefore'] + 1:
            e.ok('%s: a real click on FAQ answer %d opened it (%d -> %d of %d); the %d footer '
                 'accordions stayed put (%d open)'
                 % (lang, h['targetIndex'], h['openBefore'], a['open'], a['items'],
                    h['outside'], a['outsideOpen']))
        else:
            e.fail('%s: FAQ answer %d did not open (%d -> %s)'
                   % (lang, h['targetIndex'], h['openBefore'], a))
        if (a.get('allDetails') != h['allDetails']
                or a.get('outsideOpen') != h['outsideOpen']
                or a.get('outside') != h['outside']):
            e.fail('%s: the footer accordions moved (%s open -> %s, page-wide %s -> %s)'
                   % (lang, h['outsideOpen'], a.get('outsideOpen'),
                      h['allDetails'], a.get('allDetails')))
        if c['gridCards'] >= 2 and p['h1Count'] == 1 and c['faqItems'] == 9:
            e.ok('%s: 9 answers in the FAQ band, %d related cards, one h1'
                 % (lang, c['gridCards']))

    # ------------------------------------------------------------- console --
    print('console errors')
    errs = e.errors()
    if errs:
        e.fail('the browser reported %d console error(s): %s' % (len(errs), errs[:3]))
    else:
        e.ok('no console errors on any page visited')

    res = {'fails': e.fails, 'notes': e.notes, 'rows': e.rows}
    with open(os.path.join(args.out, 'e2e.json'), 'w', encoding='utf-8') as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1, default=str)
    print('-' * 72)
    print('VERDICT: %s — %d ok, %d FAIL'
          % ('PASS' if not e.fails else 'FAIL', len(e.notes), len(e.fails)))
    return 1 if e.fails else 0


if __name__ == '__main__':
    sys.exit(main())

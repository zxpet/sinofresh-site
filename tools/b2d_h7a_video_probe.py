#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H7a — the Video path, exercised once and put back.

WHAT WAS NEVER TESTED. H7a replaced the gallery's heading with a [Photos][Video]
switch. The [Video] label is emitted only when the record carries a video, all 21
formulas are without one, and so **the second half of that renderer has never run
on this site**. A branch that has never executed is not a branch that works, and
no page captured by the byte gate can say anything about it: every page the gate
sees takes the other path.

So the read is filtered, not the data written —
`tools/b2d_h7a_video_fixture.php` is a mu-plugin that supplies
`sf_formula_video_url` to one post on the way out of the metadata layer. The
discipline this file exists to enforce is the other half: **install, verify,
remove, and prove the removal.** A fixture left behind on a dev box becomes a
difference nobody remembers making, which is the failure mode that costs a whole
afternoon three batches later. So the removal is in a `finally`, and it is
followed by three checks that it actually happened: the mu-plugins listing is
back to its four files, the page has lost the Video tab, and the database moved
by nothing at all.

What is asserted, in the theme's own terms:

  * the bar ships as a lone [Photos] (1 tab), and with the fixture as
    [Photos][Video] (2 tabs, `aria-pressed` true/false, `is-active` on Photos);
  * the frames go from 4 to 5, and the new one is
    `.sf-gallery__slide--video` carrying `data-video-id="SFH7AFIXTURE"` — i.e.
    the id travelled through `sinofresh_formula_video_id()` intact;
  * clicking [Video] reveals that frame and hides the photo frames, flips
    `aria-pressed` both ways, and moves the stage's `aria-label` to the video's
    own alt;
  * it stays a **facade**: no `<iframe>` is created and not one request goes to
    `youtube.com` or `i.ytimg.com`, before or after the click. That is the
    promise the markup makes (`Play video` is a `<button>`, "YouTube's player is
    fetched when — and only when — the visitor asks for it"), and the probe
    never presses Play.
  * and the database is untouched, read as `wp_postmeta` row count,
    `sf_formula_video_url` row count and `MAX(meta_id)` before and after.

usage:
    b2d_h7a_video_probe.py [--want-ver 2.10.67] [--shots DIR]
"""
import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

import importlib.util


def _load(name, fname):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, fname))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


h7b = _load('h7b_e2e', 'b2d_h7b_e2e.py')
# The mask set, for the one comparison that has to survive a live CDN.
h6 = _load('h6_confine', 'b2d_h6_confine.py')

SSH = 'root@65.49.215.152'
DOCROOT = '/var/www/dev.zxpet.com/public'
MU_DIR = DOCROOT + '/wp-content/mu-plugins'
FIXTURE_LOCAL = os.path.join(HERE, 'b2d_h7a_video_fixture.php')
FIXTURE_NAME = 'b2d_h7a_video_fixture.php'
MU_EXPECTED = ['zz-sf-dev-lockdown.php', 'zz-sf-preflight.log',
               'zz-sf-preflight.log.prev', 'zz-sf-preflight.php']

TARGET = '/formulas/joint-support-tablets/'
FIXTURE_ID = 'SFH7AFIXTURE'
FIXTURE_POSTER = 'https://dev.zxpet.com/wp-content/uploads/2026/09/fac-line.webp'
AUTH = h7b.DEFAULT_AUTH

GALLERY = """
(()=>{
 const g=document.querySelector('.sf-gallery');
 if(!g) return {present:false};
 const box=e=>{const r=e.getBoundingClientRect();
   return {w:Math.round(r.width),h:Math.round(r.height),
           top:Math.round(r.top+scrollY),left:Math.round(r.left)};};
 const tabs=[].slice.call(g.querySelectorAll('.sf-gallery__tab'));
 const slides=[].slice.call(g.querySelectorAll('.sf-gallery__slide'));
 /* Visibility is TWO mechanisms, and reading only one of them reports four
    frames as visible when one is. The server ships every frame after the first
    with `hidden`; at init the script takes `hidden` off all the PHOTO frames and
    controls them with `.sf-gallery__slide--off` instead, deliberately leaving
    the video frame on `hidden` until its tab is chosen. So "visible" is "neither
    --off nor hidden", and the four `hidden` attributes this reads before any
    click are the photos' leftovers, not a second gallery. */
 const off=s=>s.classList.contains('sf-gallery__slide--off')||s.hasAttribute('hidden');
 const vis=slides.filter(s=>!off(s));
 const vids=slides.filter(s=>s.classList.contains('sf-gallery__slide--video'));
 const stage=g.querySelector('.sf-gallery__stage');
 const res=performance.getEntriesByType('resource').map(r=>r.name);
 return {
  present:true,
  jsHooked: g.classList.contains('sf-gallery--js'),
  galleryTop: box(g).top,
  galleryBox: box(g),
  tabCount: tabs.length,
  tabLabels: tabs.map(t=>t.textContent.trim()),
  tabState: tabs.map(t=>t.getAttribute('data-sf-gallery-tab')+':'
    +(t.getAttribute('aria-pressed')==='true'?'pressed':'released')
    +(t.classList.contains('is-active')?':active':':idle')),
  slideCount: slides.length,
  videoSlides: vids.length,
  videoId: vids.length? vids[0].getAttribute('data-video-id') : null,
  videoHidden: vids.length? vids[0].hasAttribute('hidden') : null,
  videoBox: vids.length? box(vids[0]) : null,
  visibleSlots: vis.map(s=>s.getAttribute('data-slot')),
  visibleCount: vis.length,
  stageLabel: stage? stage.getAttribute('aria-label') : null,
  playTag: (()=>{const b=g.querySelector('.sf-gallery__play');return b?b.tagName:null;})(),
  playText: (()=>{const b=g.querySelector('.sf-gallery__play-text');return b?b.textContent.trim():null;})(),
  posterSrc: (()=>{const i=g.querySelector('.sf-gallery__slide--video img');
    return i?i.getAttribute('src'):null;})(),
  posterLoaded: (()=>{const i=g.querySelector('.sf-gallery__slide--video img');
    return i? (i.complete && i.naturalWidth>0) : null;})(),
  iframes: document.querySelectorAll('iframe').length,
  thirdParty: res.filter(n=>/youtube\\.com|ytimg\\.com|ytimg|googlevideo/.test(n)),
  h1: document.querySelectorAll('h1').length
 };})()
"""


def run(cmd, timeout=180):
    import subprocess
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return p.returncode, (p.stdout or '').strip(), (p.stderr or '').strip()


def ssh(cmd, timeout=90):
    return run(['ssh', '-o', 'ConnectTimeout=8', SSH, cmd], timeout)


def mu_list():
    rc, out, err = ssh('ls -1 %s' % MU_DIR)
    if rc != 0:
        raise SystemExit('FATAL could not list mu-plugins: %s' % (err or out))
    return sorted(out.split())


def db_trace():
    """(postmeta rows, sf_formula_video_url rows, MAX(meta_id)).

    Three numbers rather than a dump: the first says nothing was added, the
    second says the fixture did not become a row, the third says nothing was
    added and deleted either (a delete leaves the AUTO_INCREMENT behind).
    """
    q = ("SELECT (SELECT COUNT(*) FROM wp_postmeta), "
         "(SELECT COUNT(*) FROM wp_postmeta WHERE meta_key='sf_formula_video_url'), "
         "(SELECT COALESCE(MAX(meta_id),0) FROM wp_postmeta);")
    rc, out, err = ssh('cd %s && wp db query "%s" --allow-root --skip-column-names' % (DOCROOT, q))
    if rc != 0 or not out:
        raise SystemExit('FATAL db trace failed: %s' % (err or out))
    vals = out.split()
    return tuple(int(v) for v in vals[:3])


def fetch_page(want_ver):
    """(bytes, error) -- the page AS THE PREFLIGHT COPY serves it."""
    rc, out, err = run(['curl', '-s', '-u', AUTH, '-H', 'X-SF-Preflight: 1',
                        h7b.HOST + TARGET], 120)
    if rc != 0 or not out:
        return None, (err or 'empty response')
    if 'sinofresh-theme-preflight' not in out or ('ver=%s' % want_ver) not in out:
        return None, 'served the wrong copy from %s' % TARGET
    return out, None


def count(html, needle):
    return html.count(needle)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--want-ver', default='2.10.67')
    ap.add_argument('--shots', default=None)
    ap.add_argument('--keep', action='store_true',
                    help='leave the fixture installed (debugging only; the '
                         'default is to always remove it)')
    args = ap.parse_args()

    shots = args.shots or os.path.join(ROOT, 'docs', 'batchH7a-shots')
    fails = []

    def check(label, cond, detail=''):
        print('  %s  %-62s %s' % ('ok  ' if cond else 'FAIL', label, detail))
        if not cond:
            fails.append(label)
        return bool(cond)

    print('== before: the box as it was found ==')
    mu_before = mu_list()
    check('mu-plugins holds exactly its four standing files',
          mu_before == MU_EXPECTED, repr(mu_before))
    db_before = db_trace()
    print('   db: postmeta=%d  sf_formula_video_url=%d  max_meta_id=%d' % db_before)

    plain, why = fetch_page(args.want_ver)
    if plain is None:
        raise SystemExit('FATAL %s' % why)
    check('without the fixture the bar is a lone [Photos]',
          count(plain, 'data-sf-gallery-tab="video"') == 0 and
          count(plain, 'data-sf-gallery-tab="photos"') == 1,
          'video tabs=%d photos tabs=%d'
          % (count(plain, 'data-sf-gallery-tab="video"'),
             count(plain, 'data-sf-gallery-tab="photos"')))
    check('and four frames, none of them a video',
          count(plain, '<figure class="sf-gallery__slide') == 4 and
          count(plain, 'sf-gallery__slide--video') == 0,
          'slides=%d video=%d' % (count(plain, '<figure class="sf-gallery__slide'),
                                  count(plain, 'sf-gallery__slide--video')))

    installed = False
    try:
        print('== install ==')
        rc, out, err = run(['scp', '-o', 'ConnectTimeout=8', FIXTURE_LOCAL,
                            '%s:%s/%s' % (SSH, MU_DIR, FIXTURE_NAME)], 120)
        if rc != 0:
            raise SystemExit('FATAL scp: %s' % (err or out))
        installed = True
        mu_now = mu_list()
        check('the fixture is the fifth file in mu-plugins',
              mu_now == sorted(MU_EXPECTED + [FIXTURE_NAME]), repr(mu_now))
        db_during = db_trace()
        check('installing it wrote nothing to the database',
              db_during == db_before, '%r vs %r' % (db_during, db_before))

        html, why = fetch_page(args.want_ver)
        if html is None:
            raise SystemExit('FATAL %s' % why)
        check('the bar now carries a [Video] label',
              count(html, 'data-sf-gallery-tab="video"') == 1,
              'video tabs=%d' % count(html, 'data-sf-gallery-tab="video"'))
        check('with aria-pressed released, Photos pressed',
              'data-sf-gallery-tab="video" aria-pressed="false"' in html and
              'data-sf-gallery-tab="photos" aria-pressed="true"' in html)
        check('a fifth frame appears, and it is the video facade',
              count(html, '<figure class="sf-gallery__slide') == 5 and
              count(html, 'sf-gallery__slide--video') == 1,
              'slides=%d' % count(html, '<figure class="sf-gallery__slide'))
        check('carrying the id the fixture supplied',
              'data-video-id="%s"' % FIXTURE_ID in html)
        check('and the poster is the still the fixture pointed it at',
              FIXTURE_POSTER in html and 'i.ytimg.com' not in html)
        check('the frame is a <button> facade and the page has no iframe',
              '<button type="button" class="sf-gallery__play">' in html and
              count(html, '<iframe') == 0,
              'iframes=%d' % count(html, '<iframe'))

        print('== the browser pass ==')
        r = h7b.Runner(AUTH, shots)
        r.attach()
        r.goto(TARGET, 'h7a-video', args.want_ver)
        st = h7b.ev(GALLERY) or {}

        check('the gallery is on the page and the script has hooked it',
              st.get('present') is True and st.get('jsHooked') is True,
              'present=%r jsHooked=%r' % (st.get('present'), st.get('jsHooked')))
        check('two tabs, [Photos] then [Video]',
              st.get('tabCount') == 2 and st.get('tabLabels') == ['Photos', 'Video'],
              'labels=%r' % (st.get('tabLabels'),))
        check('Photos starts pressed and active, Video released and idle',
              st.get('tabState') == ['photos:pressed:active', 'video:released:idle'],
              repr(st.get('tabState')))
        check('five frames, exactly one of them the video',
              st.get('slideCount') == 5 and st.get('videoSlides') == 1,
              'slides=%r video=%r' % (st.get('slideCount'), st.get('videoSlides')))
        check('the id survived sinofresh_formula_video_id()',
              st.get('videoId') == FIXTURE_ID, 'id=%r' % st.get('videoId'))
        check('the video frame starts hidden',
              st.get('videoHidden') is True)
        check('and only the main photo is showing',
              st.get('visibleSlots') == ['1'] and st.get('visibleCount') == 1,
              'visible=%r' % (st.get('visibleSlots'),))
        check('the play control is a real <button>, not a link off-site',
              st.get('playTag') == 'BUTTON' and st.get('playText') == 'Play video',
              'tag=%r text=%r' % (st.get('playTag'), st.get('playText')))
        # The still IS fetched at page load -- "a page load costs one image" is
        # what the renderer's own note says -- and the facade's promise is about
        # YouTube's PLAYER, not its thumbnail. So this asserts the still arrived,
        # and the next two assert that nothing else did.
        check('the poster is the fixture still and it rendered',
              st.get('posterSrc') == FIXTURE_POSTER and st.get('posterLoaded') is True,
              'src=%r loaded=%r' % (st.get('posterSrc'), st.get('posterLoaded')))
        check('no iframe on the page at all', (st.get('iframes') or 0) == 0,
              'iframes=%r' % st.get('iframes'))
        check('and nothing has been fetched from YouTube',
              (st.get('thirdParty') or []) == [],
              '%r' % (st.get('thirdParty'),))
        check('still exactly one h1', st.get('h1') == 1, 'h1=%r' % st.get('h1'))

        r.scroll(max(0, (st.get('galleryTop') or 0) - 40))
        r.shot('h7a-01-gallery-photos.png')

        box, why = r.click('.sf-gallery__tab[data-sf-gallery-tab="video"]')
        check('the [Video] tab is hittable where it is drawn', box is not None, why)
        time.sleep(0.7)
        v = h7b.ev(GALLERY) or {}
        check('[Video] becomes pressed and active, [Photos] released',
              v.get('tabState') == ['photos:released:idle', 'video:pressed:active'],
              repr(v.get('tabState')))
        check('the video frame is revealed, with a real box',
              v.get('videoHidden') is False and
              (v.get('videoBox') or {}).get('w', 0) > 100 and
              (v.get('videoBox') or {}).get('h', 0) > 100,
              'hidden=%r box=%r' % (v.get('videoHidden'), v.get('videoBox')))
        check('and it takes over as the only visible frame',
              v.get('visibleSlots') == ['2'],
              'visible=%r' % (v.get('visibleSlots'),))
        check('the stage is renamed to the video\'s own alt',
              (v.get('stageLabel') or '').endswith('product video'),
              'stage=%r' % v.get('stageLabel'))
        check('still no iframe — the facade held',
              (v.get('iframes') or 0) == 0, 'iframes=%r' % v.get('iframes'))
        check('and still nothing fetched from YouTube',
              (v.get('thirdParty') or []) == [], '%r' % (v.get('thirdParty'),))
        # The still is lazy, so it arrives once the frame stops being hidden.
        # Polled rather than slept on: the claim is "it renders", not "it renders
        # within 700ms".
        loaded = False
        for _ in range(10):
            v2 = h7b.ev(GALLERY) or {}
            if v2.get('posterLoaded'):
                loaded = True
                break
            time.sleep(0.4)
        check('and the revealed frame is a real render, not an empty box',
              loaded, 'poster loaded=%r after the reveal' % loaded)
        r.shot('h7a-02-gallery-video.png')

        box, why = r.click('.sf-gallery__tab[data-sf-gallery-tab="photos"]')
        check('the [Photos] tab takes it back', box is not None, why)
        time.sleep(0.7)
        back = h7b.ev(GALLERY) or {}
        check('the bar is back where it started',
              back.get('tabState') == ['photos:pressed:active', 'video:released:idle'] and
              back.get('visibleSlots') == ['1'],
              '%r visible=%r' % (back.get('tabState'), back.get('visibleSlots')))
        check('and the harness stayed on the served page', r.on_page(), r.where_str())
        run(['agent-browser', 'close', '--all'])

    finally:
        print('== remove ==')
        if installed and not args.keep:
            rc, out, err = ssh('rm -f %s/%s' % (MU_DIR, FIXTURE_NAME))
            if rc != 0:
                print('  FAIL  the fixture could not be removed: %s' % (err or out))
                fails.append('fixture removal')
        elif installed:
            print('   ..   --keep: the fixture is STILL INSTALLED at %s/%s'
                  % (MU_DIR, FIXTURE_NAME))

    if installed and not args.keep:
        mu_after = mu_list()
        check('mu-plugins is back to exactly its four standing files',
              mu_after == MU_EXPECTED, repr(mu_after))
        db_after = db_trace()
        check('and the database never moved',
              db_after == db_before, '%r vs %r' % (db_after, db_before))
        after, why = fetch_page(args.want_ver)
        if after is None:
            print('  FAIL  post-check fetch: %s' % why)
            fails.append('post-check fetch')
        else:
            check('the bar is a lone [Photos] again',
                  count(after, 'data-sf-gallery-tab="video"') == 0 and
                  count(after, 'data-sf-gallery-tab="photos"') == 1,
                  'video tabs=%d' % count(after, 'data-sf-gallery-tab="video"'))
            check('four frames again, no video',
                  count(after, '<figure class="sf-gallery__slide') == 4 and
                  count(after, 'sf-gallery__slide--video') == 0,
                  'slides=%d' % count(after, '<figure class="sf-gallery__slide'))
            check('and the page renders as it did before the fixture',
                  h6.mask(after) == h6.mask(plain),
                  'the fixture left no trace in the render' if
                  h6.mask(after) == h6.mask(plain)
                  else 'the render differs from the pre-fixture capture under '
                       'the same mask set')

    print('\n%s  batch H7a Video path: the branch ran, and the box is as it was'
          % ('PASS' if not fails else 'FAIL'))
    if fails:
        for f in fails:
            print('   FAIL %s' % f)
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch 2D step 3 — the four-item quick check, on /formulas/ear-care-drops/.

Deliberately standalone and short. The full E2E harness (`b2d_s3_browser.py`)
has five self-inflicted bugs on the record (networkidle never returns, a stale
agent-browser daemon, a doubled BASE prefix in the URL, a scroll-snap assertion
that looked for "snap" inside the *value* of scroll-snap-type, and a consent
banner judged by DOM presence instead of by its layout box). This is the cheap
manual substitute for it: three browser checks here, and the fourth — that a
no-JS visitor still gets the main image — is a plain curl, kept as
docs/b2d-step3-shots/quickcheck-ear-care-drops.html.

Checks
  1. thumbnail click — click thumb 2 with a real mouse and see the main frame
     become frame 2's image.
  2. 375px — document must not be horizontally scrollable.
  3. no-JS main image — see the curl, not this file.
  4. keyboard — focus a thumb and let ArrowRight / ArrowLeft move the band.

Two traps this file has already fallen into, both fixed here:
  * the thumbnail ids are NOT the page slug. formula-gallery.js builds them
    from `inner[data-gallery]`, which holds the DOSAGE FORM slug — "drops" for
    /formulas/ear-care-drops/. Assuming the page slug made every click and
    keyboard check report a miss on a page whose strip worked fine; the prefix
    is now read off the markup.
  * the 375px measurement used to be taken over whatever the sections above had
    left on screen, and one run measured a page that was not there yet —
    reporting "no overflow" from an empty DOM. It now reloads at 375 and
    asserts readyState and the thumb count in the same eval as the numbers.

The viewport is asserted alongside the measurement for the same reason: a
measurement taken at the wrong width is an empty check, and `open` has been
observed to reset the viewport on this box.

    python3 tools/b2d_s3_quickcheck.py
"""
import json
import os
import subprocess
import sys
import time

BASE = "https://dev.zxpet.com"
# Credentials come from $SF_DEV_AUTH, falling back to the dev pair — the same
# convention b2d_s3_fetch.py already uses. Kept behind one name here rather
# than typed twice, so the dev pair can be swept out of the repo in one pass
# once the staging host is retired.
_auth = os.environ.get("SF_DEV_AUTH") or "sfdev:VkEws18Kl5V1qp3TpZ6s"
USER, PASS = _auth.split(":", 1)
PAGE = "/formulas/ear-care-drops/"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOTS = os.path.join(ROOT, "docs", "b2d-step3-shots")

results = []


def ab(*args, timeout=180):
    p = subprocess.run(["agent-browser", *args], capture_output=True, text=True,
                       timeout=timeout)
    if p.returncode != 0 and p.stderr.strip():
        print("      !! agent-browser %s -> %s" % (" ".join(args), p.stderr.strip()[:200]))
    return p.stdout.strip()


def ev(js):
    out = (ab("eval", js) or "").strip()
    if not out:
        return None
    out = out.splitlines()[-1].strip()
    try:
        out = json.loads(out)
    except Exception:
        return out
    if isinstance(out, str):
        s = out.strip()
        if s[:1] in '{["':
            try:
                out = json.loads(s)
            except Exception:
                pass
    return out


def check(name, expected, actual):
    ok = expected == actual
    results.append(ok)
    print("  [%s] %-52s expect=%r got=%r"
          % ("PASS" if ok else "FAIL", name, expected, actual))
    return ok


def frame():
    """Which frame shows, and which file it resolves to."""
    return ev("""JSON.stringify((function(){
      var st=document.querySelector('.sf-gallery__stage');
      if(!st) return {slot:null, file:null};
      var on=st.querySelector('.sf-gallery__slide:not(.sf-gallery__slide--off)');
      if(!on) return {slot:null, file:null};
      var img=on.querySelector('img');
      return {slot:on.getAttribute('data-slot'),
              file:(img?img.getAttribute('src'):'').split('/').pop().split('?')[0]};
    })())""") or {}


def click_thumb(n, slug):
    """Real mouse click on a thumbnail, validated against elementFromPoint.

    A lazy image that reflows, or a fixed overlay, moves the target out from
    under coordinates that were right a moment earlier and the click then lands
    on something else with no error anywhere.
    """
    sel = "#sf-gallery-tab-%s-%d" % (slug, n)
    ev("(function(){var el=document.querySelector(%s);"
       "if(el)el.scrollIntoView({block:'center',behavior:'instant'});})()" % json.dumps(sel))
    time.sleep(0.4)
    box = ev("""JSON.stringify((function(){
      var el=document.querySelector(%s);
      if(!el) return {missing:true};
      var r=el.getBoundingClientRect();
      var x=Math.round((r.left+r.right)/2), y=Math.round((r.top+r.bottom)/2);
      var hit=document.elementFromPoint(x,y);
      return {x:x, y:y, hit:hit?(hit.tagName+'#'+hit.id):null,
              reachable:!!(hit&&(hit===el||el.contains(hit)))};
    })())""" % json.dumps(sel)) or {}
    if not box.get("reachable"):
        print("      !! click_thumb(%d): not reachable — %r" % (n, box))
        return False
    ab("mouse", "move", str(box["x"]), str(box["y"]))
    ab("mouse", "down")
    ab("mouse", "up")
    time.sleep(0.45)
    return True


def main():
    os.makedirs(SHOTS, exist_ok=True)
    ab("set", "credentials", USER, PASS)

    # ---------------------------------------------------- 1. thumbnail click
    print("=== 1. thumbnail click at 1440x900 ===")
    ab("set", "viewport", "1440", "900")
    ab("open", BASE + PAGE)
    time.sleep(2.5)
    f = frame()
    print("       initial:", json.dumps(f, ensure_ascii=False))
    check("starts on frame 1 (drops.webp)", ("1", "drops.webp"),
          (f.get("slot"), f.get("file")))
    # The thumb ids are NOT the page slug. formula-gallery.js builds them as
    # "sf-gallery-tab-" + inner[data-gallery] + "-" + n, and data-gallery holds
    # the DOSAGE FORM (taxonomy) slug — "drops" here, while the page is
    # /formulas/ear-care-drops/. Hardcoding the page slug made every thumb and
    # keyboard check in the first run report a miss on a page whose strip was
    # working; read the prefix off the markup instead of assuming it.
    slug = ev("""(function(){var i=document.querySelector('.sf-gallery__inner');
                   return i?i.getAttribute('data-gallery'):null;})()""")
    print("       thumb id prefix (data-gallery):", slug)
    check("the strip is 4 thumbs", 4,
          ev("document.querySelectorAll('.sf-gallery__thumb').length"))
    clicked = click_thumb(2, slug)
    f2 = frame()
    print("       after clicking thumb 2:", json.dumps(f2, ensure_ascii=False))
    check("clicking thumb 2 switches the main image", ("2", "fac-placeholder.webp"),
          (f2.get("slot"), f2.get("file")))
    if not clicked:
        print("      !! the click above was scripted, not a real mouse click")
    ab("screenshot", os.path.join(SHOTS, "05-quickcheck-thumb2-1440.png"))

    # ------------------------------------------------------------- 4. keyboard
    print("\n=== 4. keyboard ===")
    ev("(function(){var t=document.getElementById('sf-gallery-tab-%s-1');"
       "if(t)t.focus();})()" % slug)
    print("       focused:", ev("(document.activeElement&&document.activeElement.id)||null"))
    # Normalise to frame 1 first. An arrow key moves relative to whatever is
    # showing, and the click section above left the band on frame 2 — so the
    # first run read the perfectly correct move 2 -> 3 as a failure because the
    # expectation (1 -> 2) had been written for the wrong starting state.
    ab("press", "Home")
    time.sleep(0.4)
    check("keyboard starts from frame 1", "1", frame().get("slot"))
    ab("press", "ArrowRight")
    time.sleep(0.4)
    check("ArrowRight moves to frame 2", "2", frame().get("slot"))
    ab("press", "ArrowRight")
    time.sleep(0.4)
    check("ArrowRight moves to frame 3", "3", frame().get("slot"))
    ab("press", "ArrowLeft")
    time.sleep(0.4)
    check("ArrowLeft moves back to frame 2", "2", frame().get("slot"))
    ab("press", "Home")
    time.sleep(0.4)
    check("Home returns to frame 1", "1", frame().get("slot"))

    # ---------------------------------------------------------------- 2. 375px
    print("\n=== 2. 375px horizontal overflow ===")
    # Reload at the narrow width rather than reflowing whatever the sections
    # above left behind, and read the load state in the same eval as the
    # measurement: a measurement taken against a page that is not there yet
    # reports "no overflow" for a reason that has nothing to do with the CSS.
    ab("set", "viewport", "375", "667")
    ab("open", BASE + PAGE)
    time.sleep(2.5)
    m = ev("""JSON.stringify((function(){
      var de=document.documentElement;
      var r=document.querySelector('.sf-gallery');
      var b=document.querySelector('.sf-cookie-banner');
      var shown=false, bbox=null;
      if(b){var rb=b.getBoundingClientRect(), cs=getComputedStyle(b);
            shown=(cs.display!=='none'&&cs.visibility!=='hidden'&&rb.width>0&&rb.height>0);
            bbox=[Math.round(rb.width), Math.round(rb.height)];}
      var s=r?r.querySelector('.sf-gallery__thumbs'):null;
      return {innerWidth:innerWidth, ready:document.readyState,
              thumbs:r?r.querySelectorAll('.sf-gallery__thumb').length:-1,
              scrollWidth:de.scrollWidth, clientWidth:de.clientWidth,
              bodyScrollWidth:document.body.scrollWidth,
              overflow:de.scrollWidth>de.clientWidth,
              bannerShown:shown, bannerBox:bbox,
              strip:s?{client:s.clientWidth, scroll:s.scrollWidth}:null};
    })())""") or {}
    print("       measured:", json.dumps(m, ensure_ascii=False))
    check("the page is fully loaded at 375", "complete", m.get("ready"))
    check("the viewport really is 375 wide", 375, m.get("innerWidth"))
    check("at 375 the strip exists (4 thumbs)", 4, m.get("thumbs"))
    check("document.scrollWidth == clientWidth", True,
          m.get("scrollWidth") == m.get("clientWidth") and not m.get("overflow"))
    ab("screenshot", os.path.join(SHOTS, "06-quickcheck-375.png"))
    ab("close")

    bad = results.count(False)
    print("\n" + "=" * 74)
    print("%s  quick check: %d checks, %d failed"
          % ("PASS" if not bad else "FAIL", len(results), bad))
    print("=" * 74)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

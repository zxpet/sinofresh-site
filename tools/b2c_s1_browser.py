#!/usr/bin/env python3
"""Batch 2C step 1 — in-browser verification + delivery screenshots.

What HTML alone cannot prove:
  * the K1 button's DOM attribute values after entity decoding ("Liquid Skin &
    Coat", not "&#038;"),
  * that pressing it does NOT jump the page: the detail page has no
    #configurator, and formulas.js 1.1.0 must simply skip the scroll,
  * the hero band tone is the inner-page one (#2E6B54, .sf-hero-inner) and not
    the nav tone,
  * the phone breadcrumb folds Home + Products behind a "left arrow" on the
    form crumb (::before content is not in the HTML),
  * the specification grid resolves to 3 tracks on desktop and 1 on a phone.

Interaction uses a real mouse (scrollIntoView -> elementFromPoint hit test ->
move -> re-check -> down/up): a lazy-loaded image or a reflowing overlay moves
the anchor between measuring and clicking, and a plain click() would succeed
while the mouse path is broken.

Run: python3 tools/b2c_s1_browser.py
"""
import json
import os
import subprocess
import sys
import time

HOST = "https://dev.zxpet.com"
SLUG = "liquid-skin-coat"          # title contains "&": exercises entity handling
TITLE = "Liquid Skin & Coat"
FORM = "liquids"
FORM_LABEL = "Liquids"
OUT = "/Users/meng/WorkBuddy/sinofresh外贸网站建设/screenshots/batch2c-step1"
STICKY = 70
os.makedirs(OUT, exist_ok=True)

fails = []


def check(cond, label, detail=""):
    print(("  PASS  " if cond else "  FAIL  ") + label + (f"   {detail}" if not cond else ""))
    if not cond:
        fails.append(label)


def run(*a, timeout=180):
    r = subprocess.run(["agent-browser", *a], capture_output=True, text=True, timeout=timeout)
    return (r.stdout + r.stderr).strip()


def js_val(expr):
    out = run("eval", expr)
    for _ in range(3):
        try:
            v = json.loads(out)
        except Exception:
            break
        if isinstance(v, str):
            out = v
            continue
        return v
    return out


def settle():
    js_val("(()=>{const h=document.body.scrollHeight;"
           "for(let y=0;y<h;y+=700)window.scrollTo(0,y);window.scrollTo(0,0);return 'ok';})()")
    for _ in range(40):
        try:
            if int(str(js_val("(()=>String([...document.images].filter(i=>!i.complete).length))()")).strip()) == 0:
                break
        except Exception:
            break
        time.sleep(0.5)
    time.sleep(0.8)


def dismiss_cookie_banner():
    if "clicked" in js_val("(()=>{const b=document.querySelector('.sf-cookie-banner__btn--reject');"
                           "if(!b)return 'absent';b.click();return 'clicked';})()"):
        time.sleep(1.0)
        run("reload")
        run("wait", "--load", "networkidle")
        time.sleep(0.8)
        print("  cookie banner: dismissed + reloaded")


def real_click(sel):
    """Hit-tested mouse click. Returns a dict describing what happened."""
    return js_val("""(()=>{
      const el=document.querySelector(%s);
      if(!el) return {ok:false,why:'no element'};
      el.scrollIntoView({block:'center'});
      const r=el.getBoundingClientRect();
      const x=r.left+r.width/2, y=r.top+r.height/2;
      const hit=document.elementFromPoint(x,y);
      return {ok:true,x:x,y:y,hit:hit===el||el.contains(hit),tag:hit?hit.className:String(hit)};
    })()""" % json.dumps(sel))


print(f"== {SLUG} desktop 1440x900 ==")
run("open", f"{HOST}/formulas/{SLUG}/")
run("set", "viewport", "1440", "900")
run("wait", "--load", "networkidle")
dismiss_cookie_banner()
settle()

# --- hero ---------------------------------------------------------------
check(js_val("(()=>document.querySelector('h1')?document.querySelector('h1').textContent:'')()") == TITLE,
      "h1 text (entity-decoded)")
check(js_val("(()=>{const s=getComputedStyle(document.querySelector('.sf-formula-hero'));"
             "return s.backgroundColor})()") == "rgb(46, 107, 84)",
      "hero tone is inner-page #2E6B54",
      str(js_val("(()=>getComputedStyle(document.querySelector('.sf-formula-hero')).backgroundColor)()")))
meta = js_val("(()=>document.querySelector('.sf-formula-hero__meta').textContent)()")
check(meta.startswith(f"{FORM_LABEL} · MOQ ") and "Lead time" in meta, "hero meta line", meta)

# --- K1 -----------------------------------------------------------------
k1 = js_val("""(()=>{const b=document.querySelector('.sf-formula__cta');
  return b?{df:b.getAttribute('data-formula'),dform:b.getAttribute('data-form'),
            cls:b.className,type:b.type}:null})()""")
check(bool(k1), "K1 button exists")
if k1:
    check(k1["df"] == TITLE, "data-formula decoded to the real title", repr(k1["df"]))
    check(k1["dform"] == FORM, "data-form is the dosage slug", repr(k1["dform"]))
    check("sf-formula__cta" in k1["cls"], "K1 class intact", k1["cls"])
    check(k1["type"] == "button", "type=button", k1["type"])

# --- grid / cards -------------------------------------------------------
grid = js_val("""(()=>{const g=document.querySelector('.sf-fdetail__grid');
  return {cols:getComputedStyle(g).gridTemplateColumns.split(' ').length,
          cards:document.querySelectorAll('.sf-fdetail__card').length,
          w:Math.round(document.querySelector('.sf-fdetail__card').getBoundingClientRect().width),
          labels:[...document.querySelectorAll('.sf-fdetail__label')].map(e=>e.textContent),
          values:[...document.querySelectorAll('.sf-fdetail__value')].map(e=>e.textContent)}})()""")
check(grid["cards"] == 3, "three specification cards", str(grid["cards"]))
check(grid["cols"] == 3, "desktop grid is 3 tracks", str(grid["cols"]))
check(grid["labels"] == ["Ingredients", "Guaranteed Analysis", "Standard Specs"],
      "card labels", str(grid["labels"]))
check(len(grid["values"]) == 3 and all(grid["values"]), "card values non-empty", str(grid["values"])[:80])
check(js_val("(()=>document.documentElement.outerHTML.includes('sf-fdetail-body')?'yes':'no')()") == "no",
      "long-copy band absent on an empty record")

# --- K1 press: toast, and NO scroll ------------------------------------
before = js_val("(()=>window.scrollY)()")
hit = real_click(".sf-formula__cta")
check(hit.get("hit"), "button is the hit-test target", str(hit.get("tag"))[:60])
if hit.get("hit"):
    run("mouse", "move", str(int(hit["x"])), str(int(hit["y"])))
    again = js_val("""(()=>{const el=document.elementFromPoint(%d,%d);
      return el&&(el.classList.contains('sf-formula__cta')||el.closest('.sf-formula__cta'))?'ok':'moved'})()"""
                   % (int(hit["x"]), int(hit["y"])))
    check(again == "ok", "anchor did not move between measure and press", str(again))
    run("mouse", "down")
    run("mouse", "up")
    time.sleep(1.2)
    toast = js_val("(()=>{const t=document.querySelector('.sf-toast');return t?t.textContent:''})()")
    check(TITLE in toast, "toast names the formula (copy ran)", toast)
    after = js_val("(()=>window.scrollY)()")
    check(abs(after - before) <= 2, "no scroll on a page without #configurator",
          f"{before} -> {after}")

# --- screenshots --------------------------------------------------------
for name, off in (("hero", 0), ("spec", 420), ("related", 900)):
    js_val(f"(()=>{{const r=document.querySelector('.sf-formula-hero').getBoundingClientRect();"
           f"window.scrollTo(0,window.scrollY+r.top-{STICKY}+{off});return 'ok';}})()")
    time.sleep(0.7)
    p = os.path.join(OUT, f"b2c-s1-{SLUG}-1440-{name}.png")
    run("screenshot", p)
    print(f"  {os.path.basename(p)}  {os.path.getsize(p)//1024}KB")

print(f"== {SLUG} phone 375x812 ==")
run("set", "viewport", "375", "812")
run("reload")
run("wait", "--load", "networkidle")
settle()

fold = js_val("""(()=>{const nav=document.querySelector('.sf-breadcrumb--d4');
  const vis=el=>el?getComputedStyle(el).display!=='none':null;
  const form=nav.querySelector('.sf-breadcrumb__crumb--form');
  return {home:vis(nav.querySelector('.sf-breadcrumb__crumb--home')),
          products:vis(nav.querySelector('.sf-breadcrumb__crumb--products')),
          sepH:vis(nav.querySelector('.sf-breadcrumb__sep--home')),
          sepP:vis(nav.querySelector('.sf-breadcrumb__sep--products')),
          form:vis(form), arrow:getComputedStyle(form,'::before').content,
          cur:nav.querySelector('.sf-breadcrumb__current').textContent}})()""")
check(fold["home"] is False and fold["products"] is False, "Home + Products hidden on a phone", str(fold))
check(fold["sepH"] is False and fold["sepP"] is False, "their separators hidden too", str(fold))
check(fold["form"] is True and fold["arrow"] not in ("none", "normal", ""),
      "form crumb keeps its left arrow", str(fold["arrow"]))
check(fold["cur"] == TITLE, "current crumb still the formula", str(fold["cur"]))

m = js_val("""(()=>{const g=document.querySelector('.sf-fdetail__grid');
  const c=document.querySelector('.sf-fdetail__card').getBoundingClientRect();
  const h=document.querySelector('.sf-formula-hero').getBoundingClientRect();
  const t=document.querySelector('.sf-formula-hero__title');
  return {cols:getComputedStyle(g).gridTemplateColumns.split(' ').length,
          cw:Math.round(c.width), heroPad:getComputedStyle(document.querySelector('.sf-formula-hero')).paddingLeft,
          h1:getComputedStyle(t).fontSize, heroH:Math.round(h.height)}})()""")
check(m["cols"] == 1, "phone grid is one column", str(m["cols"]))
check(m["cw"] > 300, "card fills the phone column", str(m["cw"]))
check(m["heroPad"] == "20px", "hero inset 20px (rule 27s)", m["heroPad"])

for name, sel, off in (("hero", ".sf-formula-hero", 0), ("spec", ".sf-fdetail", 0),
                       ("related", ".sf-fdetail-more", 0), ("related2", ".sf-fdetail-more", 700)):
    js_val(f"(()=>{{const r=document.querySelector('{sel}').getBoundingClientRect();"
           f"window.scrollTo(0,window.scrollY+r.top-{STICKY}+{off});return 'ok';}})()")
    time.sleep(0.7)
    p = os.path.join(OUT, f"b2c-s1-{SLUG}-375-{name}.png")
    run("screenshot", p)
    print(f"  {os.path.basename(p)}  {os.path.getsize(p)//1024}KB")

run("close")
print(f"--- {len(fails)} failed ---")
for f in fails:
    print("FAIL", f)
sys.exit(1 if fails else 0)

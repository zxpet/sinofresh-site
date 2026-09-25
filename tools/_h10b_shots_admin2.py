#!/usr/bin/env python3
"""H10b admin shot, take 2: expand the Meta Boxes drawer, then frame Spec Sheet."""
import json
import subprocess

AB = "agent-browser"
OUT = "/Users/meng/WorkBuddy/sinofresh外贸网站建设/docs/h10b-shots"


def run(*args, timeout=90):
    cmd = [AB] + [str(a) for a in args]
    p = subprocess.run(cmd, capture_output=True, timeout=timeout)
    out = (p.stdout or b"").decode("utf-8", "replace").strip()
    if p.returncode != 0:
        print("  !!", args[:2], (p.stderr or b"").decode("utf-8", "replace")[:200])
    return out


def ev(js):
    raw = run("eval", js, "--json")
    try:
        val = json.loads(raw)
        if isinstance(val, dict):
            val = val.get("data", {}).get("result", val)
        return json.loads(val) if isinstance(val, str) else val
    except Exception:
        return raw


g = ev("JSON.stringify({url: location.pathname + location.search, user: (document.querySelector('.display-name')||{}).textContent||''})")
print("guard:", str(g)[:150])
if not (isinstance(g, dict) and str(g.get("url", "")).startswith("/wp-admin/post.php")):
    raise SystemExit("GUARD FAILED — session lost")

# expand the Meta Boxes drawer if collapsed
r = ev("""
(function(){
  var t = Array.from(document.querySelectorAll('button, .components-panel__body-toggle, h2, [class*=toggle]'))
    .find(function(e){ return e.textContent.indexOf('Meta Boxes') !== -1; });
  if (t) { t.click(); return 'clicked'; }
  return 'not-found';
})()
""")
print("meta boxes toggle:", r)
run("wait", "1200")

m = ev("""
var h = Array.from(document.querySelectorAll('h2,h3')).find(function(e){return e.textContent.trim()==='Spec Sheet';});
if (!h) { JSON.stringify({found:false}); }
else {
  h.scrollIntoView({block:'start'}); window.scrollBy(0,-60);
  var box = h.closest('.postbox') || h.parentElement;
  var labels = Array.from(box.querySelectorAll('.sf-mb__label')).map(function(e){return e.textContent.trim();});
  JSON.stringify({found:true, labels:labels, top: h.getBoundingClientRect().top});
}
""")
print("specsheet:", json.dumps(m, ensure_ascii=False))
if not (isinstance(m, dict) and m.get("found") and len(m.get("labels", [])) == 4):
    raise SystemExit("GUARD FAILED — 4 fields not visible")
run("wait", "500")
print("shot ->", run("screenshot", "%s/h10b-admin-specsheet-1440.png" % OUT)[:120])

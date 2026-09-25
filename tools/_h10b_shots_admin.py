#!/usr/bin/env python3
"""H10b admin screenshot: Spec Sheet metabox (4 fields) on the preflight copy."""
import base64
import json
import subprocess
import sys

AB = "agent-browser"
BASIC = "Basic " + base64.b64encode(b"sfdev:VkEws18Kl5V1qp3TpZ6s").decode()
OUT = "/Users/meng/WorkBuddy/sinofresh外贸网站建设/docs/h10b-shots"
LOGIN = "https://dev.zxpet.com/wp-login.php"
EDITOR = "https://dev.zxpet.com/wp-admin/post.php?post=158&action=edit"
USER = "tmpshot10b"
PASS = "Tmp10b!shotZx9"


def run(*args, timeout=120):
    cmd = [AB] + [str(a) for a in args]
    p = subprocess.run(cmd, capture_output=True, timeout=timeout)
    out = (p.stdout or b"").decode("utf-8", "replace").strip()
    err = (p.stderr or b"").decode("utf-8", "replace").strip()
    if p.returncode != 0:
        print("  !! rc=%s %s %s" % (p.returncode, args[:2], err[:200]))
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


print("close --all")
run("close", "--all")
run("set", "credentials", "sfdev", "VkEws18Kl5V1qp3TpZ6s")
print("open wp-login")
run("open", LOGIN)
run("set", "headers", json.dumps({"X-SF-Preflight": "1", "Authorization": BASIC}))
run("reload")
run("fill", "#user_login", USER)
run("fill", "#user_pass", PASS)
run("click", "#wp-submit")
run("wait", "2500")

print("open editor")
run("open", EDITOR)
run("set", "headers", json.dumps({"X-SF-Preflight": "1", "Authorization": BASIC}))
run("reload")
run("wait", "3000")

g = ev("JSON.stringify({url: location.pathname + location.search, user: (document.querySelector('.display-name')||{}).textContent || ''})")
print("guard:", str(g)[:200])
if not (isinstance(g, dict) and str(g.get("url", "")).startswith("/wp-admin/post.php")):
    print("GUARD FAILED — not in the editor")
    sys.exit(1)

# welcome modal: click its close button once (never Escape twice)
ev("var b=document.querySelector('.components-modal__header button'); if (b) { b.click(); } 'ok'")
run("wait", "800")

# scroll the Spec Sheet metabox into view and measure its fields
m = ev("""
var h = Array.from(document.querySelectorAll('h2,h3')).find(function(e){return e.textContent.trim()==='Spec Sheet';});
if (!h) { JSON.stringify({found:false}); }
else {
  h.scrollIntoView({block:'start'}); window.scrollBy(0,-60);
  var box = h.closest('.postbox') || h.parentElement;
  var labels = Array.from(box.querySelectorAll('.sf-mb__label')).map(function(e){return e.textContent.trim();});
  JSON.stringify({found:true, labels:labels});
}
""")
print("specsheet metabox:", json.dumps(m, ensure_ascii=False))
if not (isinstance(m, dict) and m.get("found") and len(m.get("labels", [])) == 4):
    print("GUARD FAILED — specsheet group does not show exactly 4 fields")
    sys.exit(1)
run("wait", "400")
p = run("screenshot", "%s/h10b-admin-specsheet-1440.png" % OUT)
print("shot ->", str(p)[:120])

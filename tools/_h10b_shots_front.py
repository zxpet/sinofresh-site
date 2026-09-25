#!/usr/bin/env python3
"""H10b front-end screenshots via agent-browser — PREFLIGHT copy (X-SF-Preflight: 1)."""
import base64
import json
import subprocess
import sys

AB = "agent-browser"
BASIC = "Basic " + base64.b64encode(b"sfdev:VkEws18Kl5V1qp3TpZ6s").decode()
URL = "https://dev.zxpet.com/formulas/natural-cleaning-dental-sticks/"
OUT = "/Users/meng/WorkBuddy/sinofresh外贸网站建设/docs/h10b-shots"


def run(*args, timeout=90):
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
print("set credentials")
run("set", "credentials", "sfdev", "VkEws18Kl5V1qp3TpZ6s")
print("open", URL)
run("open", URL, timeout=120)
print("set headers (X-SF-Preflight + Basic in ONE call)")
run("set", "headers", json.dumps({
    "X-SF-Preflight": "1",
    "Authorization": BASIC,
}))
print("reload")
run("reload", timeout=120)

g = ev("JSON.stringify({p: location.pathname, ver: (document.querySelector('link[id*=sinofresh-style]')||{}).href || '', groups: Array.from(document.querySelectorAll('.sf-fdetail-specs__gtitle')).map(e=>e.textContent)})")
print("guard:", str(g)[:300])
ok = isinstance(g, dict) and g.get("p", "").startswith("/formulas/")
if not ok:
    print("GUARD FAILED")
    sys.exit(1)
if g.get("groups") != ["Core Parameters", "Product Specifications"]:
    print("GUARD FAILED — preflight copy is not serving the H10b layout:", g.get("groups"))
    sys.exit(1)

for w, h, name in ((1440, 900, "h10b-front-specs-1440.png"), (375, 812, "h10b-front-specs-375.png")):
    run("set", "viewport", w, h)
    run("scrollintoview", ".sf-fdetail-specs")
    ev("document.querySelector('.sf-fdetail-specs').scrollIntoView({block:'start'}); window.scrollBy(0,-70); 'ok'")
    run("wait", "400")
    p = run("screenshot", "%s/%s" % (OUT, name))
    print("shot", name, "->", str(p)[:120])

m = ev("JSON.stringify({coreRows: Array.from(document.querySelectorAll('.sf-fdetail-specs__group--core .sf-fdetail-specs__term')).map(e=>e.textContent), specRows: Array.from(document.querySelectorAll('.sf-fdetail-specs__group--specs .sf-fdetail-specs__term')).map(e=>e.textContent), packaging: !!document.querySelector('.sf-fdetail-specs__group--packaging'), ver: (document.querySelector('link[id*=sinofresh-style]')||{}).href || ''})")
print("metrics:", json.dumps(m, ensure_ascii=False))

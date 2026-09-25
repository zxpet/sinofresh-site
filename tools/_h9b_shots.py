#!/usr/bin/env python3
"""H9b screenshots — admin Form Options page + front-end form (preflight copy).

Order per the memory lessons: close --all → set credentials → open wp-login →
set headers (custom + Basic in ONE call) → reload → form login → work.
Guard after every nav: we are on the served page, not a 401.
"""
import base64
import json
import subprocess
import time

SHOTS = "/Users/meng/WorkBuddy/sinofresh外贸网站建设/docs/h9b-shots"
BASIC = "Basic " + base64.b64encode(b"sfdev:VkEws18Kl5V1qp3TpZ6s").decode()


def run(*a, timeout=90):
    p = subprocess.run(["agent-browser"] + [str(x) for x in a],
                       capture_output=True, timeout=timeout)
    return (p.stdout or b"").decode("utf-8", "replace").strip()


def ev(js):
    raw = run("eval", js, "--json")
    try:
        v = json.loads(raw)
        if isinstance(v, dict) and "data" in v:
            v = v["data"]
        if isinstance(v, dict) and "result" in v:
            v = v["result"]
        if isinstance(v, str):
            v = json.loads(v)
        return v
    except Exception:
        return raw


def guard(marker, what):
    got = ev("JSON.stringify({u: location.href.slice(0,80), t: document.title.slice(0,60), ok: !!document.body && document.body.innerHTML.indexOf('%s') !== -1})" % marker)
    print("guard[%s]: %s" % (what, got))
    return isinstance(got, dict) and got.get("ok")


print("== reset ==")
run("close", "--all")
print(run("set", "credentials", "sfdev", "VkEws18Kl5V1qp3TpZ6s")[:80])
print(run("open", "https://dev.zxpet.com/wp-login.php")[:80])
print(run("set", "headers", json.dumps({
    "X-SF-Preflight": "1",
    "Authorization": BASIC,
}))[:80])
run("reload")
time.sleep(2)

# wp-login: fill and submit
ev("var u=document.querySelector('#user_login'); var p=document.querySelector('#user_pass');"
   "if(u&&p){u.value='tmpshot9b'; p.value='Tmp9b!shotZx7'; document.querySelector('#wp-submit').click(); 'submitted';} else 'no-form'")
time.sleep(4)
print("after login:", run("where")[:120])

print("== admin Form Options ==")
run("open", "https://dev.zxpet.com/wp-admin/admin.php?page=sf-form-options")
time.sleep(3)
if guard("Form Options", "admin page"):
    ev("var h=document.querySelector('.wrap h1'); if(h) h.scrollIntoView({block:'start'}); window.scrollBy(0,-30); 'ok'")
    run("wait", "400")
    print("shot admin:", run("screenshot", SHOTS + "/h9b-admin-form-options-1440.png")[:100])

print("== front contact form ==")
run("open", "https://dev.zxpet.com/contact/")
run("set", "headers", json.dumps({"X-SF-Preflight": "1", "Authorization": BASIC}))
run("reload")
run("set", "viewport", 1440, 900)
time.sleep(3)
if guard("fluent_form", "contact"):
    ev("var f=document.querySelector('.ff-el-input--label label'); if(f){f.scrollIntoView({block:'center'}); 'ok';} else 'no-form'")
    run("wait", "400")
    print("shot front:", run("screenshot", SHOTS + "/h9b-front-contact-form-1440.png")[:100])

print("== front 375 ==")
run("set", "viewport", 375, 720)
time.sleep(2)
ev("var f=document.querySelector('.ff-el-input--label label'); if(f){f.scrollIntoView({block:'center'}); 'ok';} else 'no-form'")
run("wait", "400")
print("shot 375:", run("screenshot", SHOTS + "/h9b-front-contact-form-375.png")[:100])

#!/usr/bin/env python3
"""b3g_ui_postpull.py -- postpull gate for the consent UI batch (9cd750d, now live).

The consent-batch postpull gate (b3g_consent_postpull.py) pins the OLD state by
design: it FAILS on "ui-components 1.1.0" and on "Manage Preferences still
present" once the UI batch is pulled. This gate pins the NEW live state.

Asserts on live (dev.zxpet.com, logged out, no preflight header):
  U1  ui-components.js is requested at ver=1.2.0 and answers 200
  U2  Manage Preferences is GONE from the banner markup (element count, not substring)
  U3  footer carries the Cookie Preferences withdraw link
  U4  withdraw flow: with a live decision, clicking the link re-opens the banner
      and clears the record; the accept button then still works
  U5  version token in style.css is 2.10.80 (the batch's bump)

Run:  python3 tools/b3g_ui_postpull.py
"""
import json
import subprocess
import sys
import time

USER, PASS = "sfdev", "VkEws18Kl5V1qp3TpZ6s"
URL = "https://dev.zxpet.com/about/"

FAILED = []
PASSED = [0]


def check(name, ok, detail=""):
    if ok:
        PASSED[0] += 1
        print("  ok   " + name)
    else:
        FAILED.append(name)
        print("  FAIL " + name + (("  -- " + str(detail)) if detail else ""))


def ab(*args):
    p = subprocess.run(["agent-browser", *args], capture_output=True, text=True)
    return (p.stdout or "") + (p.stderr or "")


def ev(js):
    out = ab("eval", js).strip()
    try:
        v = json.loads(out)
    except Exception:
        return out
    if isinstance(v, str):
        try:
            return json.loads(v)
        except Exception:
            return v
    return v


GUARD = """(() => {
  const css = [...document.querySelectorAll('link[rel=stylesheet]')]
    .map(l => l.getAttribute('href') || '').filter(h => h.includes('sinofresh-theme'));
  const js = [...document.querySelectorAll('script[src]')]
    .map(s => s.getAttribute('src') || '').filter(s => s.includes('ui-components'));
  return { path: location.pathname, css: css, js: js,
           manage: document.querySelectorAll('.sf-cookie-banner__manage').length,
           withdraw: !!document.querySelector('a.sf-cookie-preferences'),
           banner: !!document.querySelector('.sf-cookie-banner') };
})()"""

STATE = """(() => {
  const b = document.querySelector('.sf-cookie-banner');
  let rec = null;
  try { rec = JSON.parse(localStorage.getItem('sf_cookie_consent') || 'null'); } catch (e) {}
  return { hidden: b ? b.hidden : null, version: rec ? rec.version : null,
           analytics: rec ? rec.analytics : null };
})()"""

CLEAR = """(() => {
  localStorage.removeItem('sf_cookie_consent');
  for (const c of ['wp_consent_statistics', 'wp_consent_marketing']) {
    document.cookie = c + '=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/';
  }
  return 'cleared';
})()"""

print("=== consent UI batch postpull (live) ===")

# --- U1/U2/U3 from the served HTML ----------------------------------------
p = subprocess.run(["curl", "-sk", "-u", f"{USER}:{PASS}",
                    "-A", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                    URL], capture_output=True, text=True)
html = p.stdout
check("U1a ui-components 1.2.0 is requested", "ui-components.js?ver=1.2.0" in html,
      [l for l in html.split('"') if "ui-components" in l][:1])
check("U2 Manage Preferences is gone (markup count 0)",
      html.count('sf-cookie-banner__manage') == 0, html.count('sf-cookie-banner__manage'))
check("U3 footer carries the Cookie Preferences link",
      'class="sf-cookie-preferences"' in html, None)

# --- browser: withdraw flow ------------------------------------------------
ab("close", "--all")
ab("set", "credentials", USER, PASS)
ab("open", URL)
time.sleep(3)
g = ev(GUARD)
check("guard: real site, banner present",
      bool(g.get("css")) and g.get("path") == "/about/" and g.get("banner"), g)
check("U1b served script is 1.2.0", any("ui-components.js?ver=1.2.0" in s for s in g.get("js") or []), g.get("js"))
check("U2b banner has no manage button", g.get("manage") == 0, g.get("manage"))

# make a live decision, then withdraw it via the footer link
ev("localStorage.setItem('sf_cookie_consent', JSON.stringify("
   "{analytics:true, marketing:true, version:2, timestamp:Date.now(), "
   "expires:Date.now()+180*864e5})); 'seeded'")
ab("reload")
time.sleep(2)
s = ev(STATE)
check("seed: banner closed with a live record",
      s.get("hidden") is True and s.get("version") == 2, s)
ev("document.querySelector('a.sf-cookie-preferences').click(); 'clicked'")
time.sleep(1)
s = ev(STATE)
check("U4a withdraw: banner re-opens", s.get("hidden") is False, s)
check("U4b withdraw: record cleared", s.get("version") is None, s)
s = ev("(function(){var b=document.querySelector('.sf-cookie-banner__btn--accept');"
       "if(!b)return 'no-button'; b.click(); return 'clicked';})()")
s2 = ev(STATE)
check("U4c re-accept still answers after reopening",
      s == 'clicked' and s2.get("version") == 2 and s2.get("analytics") is True, (s, s2))

ev(CLEAR)
ab("close", "--all")

# --- U5 version token -------------------------------------------------------
p = subprocess.run(["curl", "-sk", "-u", f"{USER}:{PASS}",
                    "https://dev.zxpet.com/wp-content/themes/sinofresh-theme/style.css"],
                   capture_output=True, text=True)
first = p.stdout[:2000]  # token lives in the header comment, not line 1
check("U5 style.css token is 2.10.80", "Version: 2.10.80" in first, first[:120])

print()
print(("FAILED: %d" % len(FAILED)) if FAILED else "all assertions passed (%d)" % PASSED[0])
sys.exit(1 if FAILED else 0)

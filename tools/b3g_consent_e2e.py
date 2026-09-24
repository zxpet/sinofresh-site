#!/usr/bin/env python3
"""b3g_consent_e2e.py — browser E2E for the consent batch, on the PREFLIGHT copy.

What the offline gate (tools/b3g_consent_unit.js) cannot show is that the file
actually runs in a browser: that the banner renders, that the button's click
handler fires, and that the Consent API bridge really writes its cookie. That is
all this does.

The site is reached with `X-SF-Preflight: 1` plus Basic auth in ONE `set headers`
call: agent-browser rebuilds the browser context for each of `set credentials`
and `set headers`, so whichever is set second wipes the first, and `open` drops
custom headers while `reload` keeps them.

    python3 tools/b3g_consent_e2e.py
"""
import json
import subprocess
import sys

USER, PASS = "sfdev", "VkEws18Kl5V1qp3TpZ6s"
import base64
BASIC = base64.b64encode(f"{USER}:{PASS}".encode()).decode()
URL = "https://dev.zxpet.com/about/"
HEADERS = json.dumps({"X-SF-Preflight": "1", "Authorization": "Basic " + BASIC})
VIEWPORT = (1440, 900)

FAILED = []
PASSED = [0]


def check(name, ok, detail=""):
    if ok:
        PASSED[0] += 1
        print("  ok   " + name)
    else:
        FAILED.append(name)
        print("  FAIL " + name + (("  -- " + str(detail)) if detail else ""))


def ab(*args, allow_fail=False):
    p = subprocess.run(["agent-browser", *args], capture_output=True, text=True)
    if p.returncode and not allow_fail:
        print("  (agent-browser %s -> rc=%d) %s" % (" ".join(args[:2]), p.returncode,
                                                    (p.stderr or "").strip()[:200]))
    return (p.stdout or "") + (p.stderr or "")


def ev(js):
    """agent-browser eval prints a JSON string literal, so decode twice."""
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


STATE = """(() => {
  const b = document.querySelector('.sf-cookie-banner');
  let rec = null;
  try { rec = JSON.parse(localStorage.getItem('sf_cookie_consent') || 'null'); } catch (e) {}
  return {
    hidden: b ? b.hidden : null,
    body: document.body.classList.contains('has-cookie-banner'),
    version: rec ? rec.version : null,
    analytics: rec ? rec.analytics : null,
    expiresInDays: rec && rec.expires ? Math.round((rec.expires - Date.now()) / 864e5) : null,
    consentCookie: /wp_consent_statistics=([^;]+)/.exec(document.cookie)?.[1] || null
  };
})()"""

GUARD = """(() => {
  const css = [...document.querySelectorAll('link[rel=stylesheet]')]
    .map(l => l.getAttribute('href') || '').filter(h => h.includes('sinofresh-theme'));
  const js = [...document.querySelectorAll('script[src]')]
    .map(s => s.getAttribute('src') || '').filter(s => s.includes('ui-components'));
  return { path: location.pathname, title: document.title,
           w: innerWidth, h: innerHeight, css: css, js: js };
})()"""

print("=== consent E2E on the preflight copy ===")
ab("close", "--all")
ab("open", URL)                      # lands on 401: no credentials yet
ab("set", "headers", HEADERS)
ab("reload")
ab("set", "viewport", str(VIEWPORT[0]), str(VIEWPORT[1]))

g = ev(GUARD)
check("the stylesheet is the preflight copy",
      any("-preflight" in h for h in (g.get("css") or [])), g.get("css"))
check("the candidate script is the one enqueued (ver=1.1.0)",
      any("ui-components.js?ver=1.1.0" in s for s in (g.get("js") or [])), g.get("js"))
check("the viewport emulation actually applied",
      g.get("w") == VIEWPORT[0] and g.get("h") == VIEWPORT[1], (g.get("w"), g.get("h")))
check("the page is /about/ of the real site", g.get("path") == "/about/", g.get("path"))

# --- 1. no record -> the banner shows -------------------------------------
ev("localStorage.removeItem('sf_cookie_consent'); "
   "document.cookie='wp_consent_statistics=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/'; true")
ab("reload")
s = ev(STATE)
check("first visit: the banner is shown", s.get("hidden") is False, s)
check("first visit: the body carries the banner class", s.get("body") is True, s)
check("first visit: no decision stored", s.get("version") is None, s)

# --- 2. accept -------------------------------------------------------------
ev("document.querySelector('.sf-cookie-banner__btn--accept').click(); true")
s = ev(STATE)
check("accept: the record is version 2", s.get("version") == 2, s)
check("accept: analytics recorded true", s.get("analytics") is True, s)
check("accept: the record expires about 182 days out",
      s.get("expiresInDays") in (181, 182), s.get("expiresInDays"))
check("accept: the banner is hidden", s.get("hidden") is True, s)
check("accept: the Consent API cookie was written as allow",
      s.get("consentCookie") == "allow", s.get("consentCookie"))

# --- 3. a record that expired must stop counting ---------------------------
ev("localStorage.setItem('sf_cookie_consent', JSON.stringify("
   "{analytics:true, marketing:true, version:2, timestamp:Date.now()-200*864e5, "
   "expires:Date.now()-864e5})); "
   "document.cookie='wp_consent_statistics=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/'; true")
ab("reload")
s = ev(STATE)
check("an expired record: the banner is shown again", s.get("hidden") is False, s)

# --- 4. a record from the previous banner shape must not count either ------
ev("localStorage.setItem('sf_cookie_consent', "
   "JSON.stringify({analytics:true, marketing:true, timestamp:Date.now()})); true")
ab("reload")
s = ev(STATE)
check("an unversioned (legacy) record: the banner is shown again",
      s.get("hidden") is False, s)

# --- 5. reject -------------------------------------------------------------
ev("document.querySelector('.sf-cookie-banner__btn--reject').click(); true")
s = ev(STATE)
check("reject: the record is version 2 and denied",
      s.get("version") == 2 and s.get("analytics") is False, s)
check("reject: the Consent API cookie was written as deny",
      s.get("consentCookie") == "deny", s.get("consentCookie"))

# --- 6. a live record keeps it closed across a reload ----------------------
ab("reload")
s = ev(STATE)
check("a live record survives a reload and keeps the banner closed",
      s.get("hidden") is True and s.get("body") is False, s)

# --- 7. the withdrawn-locale rule is untouched by this batch ---------------
# Through the public host: an earlier version of this step curled 127.0.0.1 from
# the workstation, which is not the server, and reported 000 as a failure.
p = subprocess.run(["curl", "-sS", "-o", "/dev/null", "-w", "%{http_code} %{redirect_url}",
                    "-u", f"{USER}:{PASS}", "https://dev.zxpet.com/zh/about/"],
                   capture_output=True, text=True).stdout
check("the ZH rule still replies with a redirect", p.startswith("301"), p)
check("and still points at the English page", p.strip().endswith("/about/"), p)

ab("close", "--all")
print()
print(("FAILED: %d" % len(FAILED)) if FAILED else "all assertions passed (%d)" % PASSED[0])
sys.exit(1 if FAILED else 0)

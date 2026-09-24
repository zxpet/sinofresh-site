#!/usr/bin/env python3
"""b3g_wps_consent_gate.py -- gate for the WP Statistics consent integration.

What changed (2026-09-24, option + mu-plugin, no theme code):
  1. server/mu-plugins/zz-sf-wps-consent-bridge.php surfaces
     consent_integration=wp_consent_api at read time -- WP Statistics 14.16.x
     otherwise resets it on every request because our theme banner is not one of
     its hard-coded "compatible" banner plugins (WpConsentApi::getCompatiblePlugins()).
  2. the same mu-plugin filters wp_get_consent_type to 'optin' -- the WP Consent
     API defaults that filter to '', and '' means wp_has_consent() returns true
     everywhere with no cookie at all (client JS and server PHP alike).

The three behaviors this gate must keep true:
  G1  HTML delivers consentIntegration.name === "wp_consent_api",
      isWpConsentApiActive === true, and -- cookieless request --
      status.has_consent === false (proves the optin filter is live).
  G2  a fresh, consent-less browser session loads tracker.js but sends
      NO request to /wp-json/wp-statistics/.
  G3  clicking Accept All makes the hit appear WITHOUT a reload, and writes
      wp_consent_statistics=allow.

Run:  python3 tools/b3g_wps_consent_gate.py
"""
import json
import subprocess
import sys
import time

USER, PASS = "sfdev", "VkEws18Kl5V1qp3TpZ6s"
URL = "https://dev.zxpet.com/"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")  # default curl UA is
# bot-classified by CF: the injected tracker object comes back missing and the
# gate would silently test nothing. (Same family as "string seen != item there".)

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


GUARD = """(() => {
  const css = [...document.querySelectorAll('link[rel=stylesheet]')]
    .map(l => l.getAttribute('href') || '').filter(h => h.includes('sinofresh-theme'));
  return { path: location.pathname, css: css,
           banner: !!document.querySelector('.sf-cookie-banner') };
})()"""

NET = """(() => {
  const urls = performance.getEntriesByType('resource').map(e => e.name);
  return {
    hits: urls.filter(u => u.includes('/wp-json/wp-statistics/')),
    tracker: urls.filter(u => u.includes('wp-statistics/assets/js/tracker.js')),
    hasConsent: typeof window.wp_has_consent === 'function'
      ? window.wp_has_consent('statistics') : 'n/a',
    consentCookie: /wp_consent_statistics=([^;]+)/.exec(document.cookie)?.[1] || null
  };
})()"""

CLEAR = """(() => {
  localStorage.removeItem('sf_cookie_consent');
  for (const c of ['wp_consent_statistics', 'wp_consent_marketing']) {
    document.cookie = c + '=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/';
  }
  return 'cleared';
})()"""

print("=== WP Statistics consent gate ===")

# --- G1: the served HTML carries the integration --------------------------
time.sleep(1.2)  # be gentle with dev: >=1.2s between fetches
p = subprocess.run(["curl", "-sk", "-u", f"{USER}:{PASS}", "-A", UA,
                    "-H", "Accept: text/html", URL],
                   capture_output=True, text=True)
html = p.stdout
import re
m_name = re.search(r'"consentIntegration":\{"name":([^,}]+)', html)
m_active = re.search(r'"isWpConsentApiActive":(true|false)', html)
m_sc = re.search(r'"consentIntegration":\{[^}]*"has_consent":(true|false)', html)
check("G1a HTML names the wp_consent_api integration",
      bool(m_name) and m_name.group(1) == '"wp_consent_api"', m_name.group(1) if m_name else "no match")
check("G1b HTML flags the integration active",
      bool(m_active) and m_active.group(1) == "true", m_active.group(1) if m_active else "no match")
check("G1c cookieless server-side has_consent is false (optin filter live)",
      bool(m_sc) and m_sc.group(1) == "false", m_sc.group(1) if m_sc else "no match")
check("G1d tracker.js is still served", "wp-statistics-tracker-js" in html, None)

# --- G2: consent-less session must not send a hit -------------------------
ab("close", "--all")
ab("set", "credentials", USER, PASS)
ab("open", URL)
time.sleep(3)
g = ev(GUARD)
check("guard: the page is the real site", bool(g.get("css")) and g.get("path") == "/", g)
n = ev(NET)
check("G2a fresh session: no consent cookie", n.get("consentCookie") is None, n.get("consentCookie"))
check("G2b fresh session: client wp_has_consent is false",
      n.get("hasConsent") is False, n.get("hasConsent"))
check("G2c fresh session: tracker.js IS loaded (gate is meaningful)",
      len(n.get("tracker") or []) == 1, n.get("tracker"))
check("G2d fresh session: ZERO hit requests", len(n.get("hits") or []) == 0, n.get("hits"))

# --- G3: accepting fires the hit without a reload -------------------------
s = ev("document.querySelector('.sf-cookie-banner__btn--accept').click(); 'clicked'")
time.sleep(2.5)
n = ev(NET)
check("G3a accept: the Consent API cookie flipped to allow",
      n.get("consentCookie") == "allow", n.get("consentCookie"))
check("G3b accept: exactly one hit fired, no reload needed",
      len(n.get("hits") or []) == 1, n.get("hits"))
check("G3c accept: client wp_has_consent is now true",
      n.get("hasConsent") is True, n.get("hasConsent"))

# --- leave dev as we found it: no consent record ---------------------------
ev(CLEAR)
ab("close", "--all")

print()
print(("FAILED: %d" % len(FAILED)) if FAILED else "all assertions passed (%d)" % PASSED[0])
sys.exit(1 if FAILED else 0)

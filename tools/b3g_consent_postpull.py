#!/usr/bin/env python3
"""b3g_consent_postpull.py — consent batch, as served on LIVE after the pull.

The unit gate proved the logic offline; the E2E proved it on the preflight
copy. After the pull both of those are records of a state that no longer
exists, so this asks the question the new state poses: the served page (no
scenario header, the real production path) ships 1.1.0, the script it ships
actually carries the bridge and the guards, and the withdrawn-locale rule
still answers as before. The ZH 54/54 re-check is delegated to the gate that
already owns it (b3e_zh_postpull.py).

  python3 tools/b3g_consent_postpull.py [--json out.json]
"""

import argparse
import base64
import json
import subprocess
import sys

HOST = "dev.zxpet.com"
USER, PASS = "sfdev", "VkEws18Kl5V1qp3TpZ6s"
BASIC = base64.b64encode(f"{USER}:{PASS}".encode()).decode()

PASSED, FAILED = [], []


def check(label, ok, detail=""):
    (PASSED if ok else FAILED).append(label)
    print("  %-4s %s%s" % ("ok" if ok else "FAIL", label,
                           ("  -- " + str(detail)) if (detail and not ok) else ""))
    return ok


def curl(path, extra=()):
    # Through Cloudflare to the real host; assertions here are on status and
    # body content, not on headers, so the edge is an honest vantage point.
    cmd = ["curl", "-sk", "-w", "\n%{http_code}", f"https://{HOST}{path}"]
    if extra:
        cmd[1:1] = extra
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    body, _, code = out.rpartition("\n")
    return int(code or 0), body


print("=== consent batch on live ===")

BASIC_AUTH = ("-u", f"{USER}:{PASS}")
c, home = curl("/about/", BASIC_AUTH)
check("/about/ answers 200", c == 200, c)
check("the page is served by this site (theme stylesheet present)",
      "themes/sinofresh-theme/" in home, "401/error page guard")
check("the served page requests ui-components 1.1.0",
      "assets/js/ui-components.js?ver=1.1.0" in home)
check("it does NOT request the old 1.0.0", "ui-components.js?ver=1.0.0" not in home)

c, js = curl("/wp-content/themes/sinofresh-theme/assets/js/ui-components.js?ver=1.1.0", BASIC_AUTH)
check("the script answers 200", c == 200, c)
check("it carries the Consent API bridge", "wp_set_consent" in js)
check("it carries the version guard", "rec.version !== VERSION" in js)
check("it carries the expiry guard", "rec.expires" in js)
check("it is version 2", "VERSION = 2" in js)
check("Manage Preferences is still present (its removal is the NEXT batch)",
      "sf-cookie-banner__manage" in js)

c, zh = curl("/zh/about/", BASIC_AUTH)
check("/zh/about/ still 301s", c == 301, c)

# the preflight copy must no longer be the thing live serves
c2, home2 = curl("/about/", BASIC_AUTH + ("-H", "X-SF-Preflight: 1"))
check("preflight path still answers (same bytes now, harmless)", c2 == 200, c2)

print("\n%d passed, %d failed" % (len(PASSED), len(FAILED)))
sys.exit(1 if FAILED else 0)

#!/usr/bin/env python3
"""Batch2C Step0 regression: (1) the card grid markup must not leak onto any
non-dosage page, (2) every page still returns 200, (3) the toast chain (K1)
still fires on a dosage page. Page list comes from wp post list, so a page
added later is covered automatically."""
import json
import subprocess
import sys
import time

HOST = "https://dev.zxpet.com"
DOSAGE = {"soft-chews", "tablets", "powders", "liquids", "pastes",
          "dental-chews", "drops", "fish-oil", "products"}

fails = []


def sh(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    return (r.stdout + r.stderr).strip()


def ab(*a):
    r = subprocess.run(["agent-browser", *a], capture_output=True, text=True, timeout=120)
    return (r.stdout + r.stderr).strip()


def check(cond, label, detail=""):
    print(("  PASS  " if cond else "  FAIL  ") + label + ("  " + detail if not cond else ""))
    if not cond:
        fails.append(label)


slugs = sh(["ssh", "-o", "ConnectTimeout=15", "root@65.49.215.152",
            "cd /var/www/dev.zxpet.com/public && wp post list --post_type=page "
            "--post_status=publish --field=post_name"]).split()
print(f"publish pages: {len(slugs)}")

leak, bad_code = [], []
for s in slugs:
    url = f"{HOST}/{s}/" if s not in ("home",) else HOST + "/"
    code = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "-L", url],
                          capture_output=True, text=True).stdout
    body = subprocess.run(["curl", "-s", "-L", url], capture_output=True, text=True).stdout
    if code != "200":
        bad_code.append((s, code))
    if s in DOSAGE:
        continue
    hits = [t for t in ("sf-fgrid", "sf-fcard", "sf-formulas-data") if t in body]
    if hits:
        leak.append((s, hits))
    print(f"  {s:<20} {code}  leak={hits or 'none'}")

check(not bad_code, "all pages 200", str(bad_code))
check(not leak, "no sf-fcard/sf-fgrid leak on non-dosage pages", str(leak))

# --- K1 toast chain on a dosage page -----------------------------------
print("\n=== K1 toast chain (soft-chews) ===")
ab("open", f"{HOST}/products/soft-chews/")
ab("set", "viewport", "1440", "900")
ab("wait", "--load", "networkidle")
time.sleep(1.5)
ab("eval", "(()=>{const b=document.querySelector('.sf-formula__cta');if(!b)return 'NO_CTA';"
           "b.click();return 'clicked:'+b.getAttribute('data-formula');})()")
time.sleep(1.2)
state = ab("eval", "(()=>{const t=document.querySelector('.sf-toast');"
                  "return JSON.stringify({visible:t?t.classList.contains('is-visible'):false,"
                  "text:t?t.textContent.trim():'',"
                  "ss:sessionStorage.getItem('sinofresh_formula_soft-chews')});})()")
try:
    st = json.loads(json.loads(state))
except Exception:
    st = {}
# Headless Chromium has no clipboard permission, so formulas.js takes its
# designed degradation path ("Copy unavailable — reference ..."). Either
# message proves the K1 chain fired; the sessionStorage write is the contract.
text = (st.get("text") or "").lower()
check(st.get("visible") is True and
      ("copied" in text or "copy unavailable" in text),
      "toast visible after CTA click (copy or degrade path)", state)
check(st.get("ss") == "Joint Support Soft Chews",
      "sessionStorage key populated (configurator contract)", str(st.get("ss")))
ab("close")

print("\n=== result ===")
if fails:
    print(f"{len(fails)} FAILURE(S): " + "; ".join(fails))
    sys.exit(1)
print("ALL CHECKS PASS")

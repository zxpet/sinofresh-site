#!/usr/bin/env python3
"""H18 evidence screenshots.

  A) dev admin, formula editor — the new Media-box Frame 2/3/4 controls
  B) dev front end — the gallery with all three slots empty (the four frames)
  C) dev front end — frame 2 taken over by the record's own photo
  D) dev front end — after the slot is cleared again (byte-clean restore)

The admin session is a short-lived auth cookie issued by WP-CLI (no password
is entered, no user is created); the session token is destroyed at the end.
Basic auth on dev comes from `set credentials`, so no custom header is needed
and the context is never rebuilt mid-run.
"""
import base64
import json
import re
import subprocess
from pathlib import Path

AB = "agent-browser"
ROOT = Path("/Users/meng/WorkBuddy/sinofresh外贸网站建设")
OUT = ROOT / "docs" / "h18-shots"
BASIC = base64.b64encode(b"sfdev:VkEws18Kl5V1qp3TpZ6s").decode()
ORIGIN = "https://dev.zxpet.com/"
EDITOR = "https://dev.zxpet.com/wp-admin/post.php?post=159&action=edit"
FRONT = "https://dev.zxpet.com/formulas/calming-soft-chews/"
SERVER = "root@65.49.215.152"
WP_ROOT = "/var/www/dev.zxpet.com/public"
HELPER = "/var/www/dev.zxpet.com/site-repo/tools/b2s3_admin_cookies.php"

OUT.mkdir(parents=True, exist_ok=True)
PASS = FAIL = 0


def ck(name, ok, detail=""):
    global PASS, FAIL
    if ok:
        PASS += 1
    else:
        FAIL += 1
    print(("  [PASS] " if ok else "  [FAIL] ") + name + ((" — " + detail) if detail and not ok else ""))


def ssh(script, timeout=120):
    return subprocess.run(["ssh", SERVER, "bash -s"], input=script,
                          capture_output=True, text=True, timeout=timeout).stdout


def run(*args, timeout=150):
    p = subprocess.run([AB] + [str(a) for a in args], capture_output=True, timeout=timeout)
    out = (p.stdout or b"").decode("utf-8", "replace").strip()
    err = (p.stderr or b"").decode("utf-8", "replace").strip()
    if p.returncode != 0:
        print("  !! rc=%s %s %s" % (p.returncode, args[:2], err[:180]))
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


def shot(name):
    run("screenshot", str(OUT / name))
    p = OUT / name
    ck("screenshot %s written" % name, p.exists() and p.stat().st_size > 8000,
       "size=%s" % (p.stat().st_size if p.exists() else "missing"))


def gallery_frames():
    return ev("""
var s = document.getElementById('gallery');
if (!s) { JSON.stringify({found:false}); }
else {
  s.scrollIntoView({block:'center'});
  var imgs = Array.from(s.querySelectorAll('.sf-gallery__slide img')).map(function(i){return i.src.split('/').pop().split('?')[0];});
  JSON.stringify({found:true, n:imgs.length, imgs:imgs});
}
""")


# ------------------------------------------------------------------ session
out = ssh("cd %s && wp eval-file %s --allow-root\n" % (WP_ROOT, HELPER))
c = {}
for line in out.splitlines():
    for k in ("COOKIEHASH", "logged_in", "auth", "secure_auth"):
        if line.startswith(k + "="):
            c[k] = line.split("=", 1)[1].strip()
if len(c) != 4:
    print("FATAL — could not issue an admin session:", out[-400:])
    raise SystemExit(1)
hash_ = c["COOKIEHASH"]
token = c["logged_in"].split("|")[2]
print("issued admin session (hash %s…, token %s…)" % (hash_[:8], token[:8]))

run("close", "--all")
run("set", "credentials", "sfdev", "VkEws18Kl5V1qp3TpZ6s")
run("open", ORIGIN)
for name, val in (("wordpress_logged_in_" + hash_, c["logged_in"]),
                  ("wordpress_sec_" + hash_, c["secure_auth"]),
                  ("wordpress_" + hash_, c["auth"])):
    run("cookies", "set", name, val, "--url", ORIGIN, "--domain", "dev.zxpet.com",
        "--path", "/", "--secure")

# ------------------------------------------------------------------ A: admin
print("== A: dev admin, Media box on a formula editor ==")
run("open", EDITOR)
run("wait", "3500")
g = ev("JSON.stringify({url: location.pathname, title: document.title})")
print("  guard:", str(g)[:140])
ck("admin session reached the editor (not a login screen)",
   isinstance(g, dict) and str(g.get("url", "")).startswith("/wp-admin/post.php"),
   "got %r" % (g,))
if isinstance(g, dict) and str(g.get("url", "")).startswith("/wp-admin/post.php"):
    # tall viewport so Frame 2/3/4 land in one frame (set AFTER open: open resets it)
    run("set", "viewport", "1440", "2000")
    run("wait", "600")
    ev("var b=document.querySelector('.components-modal__header button'); if (b) { b.click(); } 'ok'")
    run("wait", "900")
    m = ev("""
var h = Array.from(document.querySelectorAll('h2,h3')).find(function(e){ return e.textContent.trim() === 'Media'; });
if (!h) { JSON.stringify({found:false}); }
else {
  var box = h.closest('.postbox') || h.parentElement;
  box.id = 'h18-mediabox';   /* element-screenshot anchor */
  var labels = Array.from(box.querySelectorAll('.sf-mb__label')).map(function(e){return e.textContent.trim();});
  var slots = Array.from(box.querySelectorAll('.sf-mb__image-id')).map(function(e){return e.getAttribute('name');});
  /* land the shot on Frame 2 itself so all three slots are on screen —
     scrolling to the box heading leaves them below the fold */
  var f2 = Array.from(box.querySelectorAll('.sf-mb__label')).find(function(e){return e.textContent.trim() === 'Frame 2';});
  /* scrollIntoView walks every ancestor scroll container (the admin scrolls
     its own skeleton, not the window) — manual scrollTo on one container
     misses the others and the shot lands wherever the rest left it */
  if (f2) { f2.scrollIntoView({block: 'start', behavior: 'instant'}); }
  JSON.stringify({found:true, labels:labels, slots:slots,
    adds: box.querySelectorAll('.sf-mb__image-add').length,
    clears: box.querySelectorAll('.sf-mb__image-clear').length});
}
""")
    print("  media box:", json.dumps(m, ensure_ascii=False))
    ck("Media box shows Frame 2 / Frame 3 / Frame 4",
       isinstance(m, dict) and all(x in m.get("labels", []) for x in ("Frame 2", "Frame 3", "Frame 4")),
       "labels=%s" % (m.get("labels") if isinstance(m, dict) else m))
    ck("the three slots carry the right input names",
       isinstance(m, dict) and m.get("slots") == ["sf_formula_frame2_id", "sf_formula_frame3_id", "sf_formula_frame4_id"],
       "slots=%s" % (m.get("slots") if isinstance(m, dict) else m))
    ck("each slot has a Choose-image and a Remove control",
       isinstance(m, dict) and m.get("adds") == 3 and m.get("clears") == 3,
       "adds=%s clears=%s" % (m.get("adds"), m.get("clears")))
    run("wait", "600")
    # WP 6.x collapses the metabox pane to a ~79px strip inside the block
    # editor; grow it, scroll the pane to the Media box, then shoot the box
    # element (window scrolling is a dead end in the editor skeleton)
    ev("""
var l = document.querySelector('.edit-post-meta-boxes-main__liner');
var m = document.querySelector('.edit-post-meta-boxes-main');
if (l) { l.style.height = '2600px'; }
if (m) { m.style.height = 'auto'; m.style.overflowY = 'auto'; m.style.flexShrink = '0'; }
var h = Array.from(document.querySelectorAll('h2,h3')).find(function(e){ return e.textContent.trim() === 'Media'; });
var box = h.closest('.postbox');
box.id = 'h18-mediabox';
l.scrollTop = box.getBoundingClientRect().top - l.getBoundingClientRect().top + l.scrollTop - 8;
'ok'
""")
    run("wait", "900")
    run("screenshot", "#h18-mediabox", str(OUT / "a-admin-media-frames.png"))
    p = OUT / "a-admin-media-frames.png"
    ck("screenshot a-admin-media-frames.png written", p.exists() and p.stat().st_size > 8000,
       "size=%s" % (p.stat().st_size if p.exists() else "missing"))

# ------------------------------------------------------------------ B: empty
print("== B: dev front end, all three slots empty ==")
run("set", "viewport", "1280", "900")
run("open", FRONT)
run("wait", "2500")
b = gallery_frames()
print("  gallery:", json.dumps(b, ensure_ascii=False))
ck("all-empty gallery renders the four dosage frames",
   isinstance(b, dict) and b.get("n") == 4, str(b))
run("wait", "600")
shot("b-front-all-empty.png")

# ------------------------------------------------------------------ C: override
print("== C: dev front end, frame 2 taken over ==")
ssh("cd %s && wp post meta update 159 sf_formula_frame2_id 53 --allow-root\n" % WP_ROOT)
run("reload")
run("wait", "2500")
cf = gallery_frames()
print("  gallery:", json.dumps(cf, ensure_ascii=False))
ck("frame 2 now shows the record's own photo, frames 1/3/4 unchanged",
   isinstance(cf, dict) and cf.get("n") == 4
   and cf.get("imgs", [None])[0] == "soft-chews.webp"
   and cf.get("imgs", [None, None])[2] == "fac-packaging.webp"
   and cf.get("imgs", [None, None, None, None])[3] == "fac-line.webp",
   str(cf))
run("wait", "600")
shot("c-front-frame2-override.png")

# ------------------------------------------------------------------ D: restore
print("== D: dev front end, slot cleared again ==")
ssh("cd %s && wp post meta delete 159 sf_formula_frame2_id --allow-root\n" % WP_ROOT)
run("reload")
run("wait", "2500")
df = gallery_frames()
print("  gallery:", json.dumps(df, ensure_ascii=False))
ck("clearing the slot restores the stock frame (same as B)",
   isinstance(df, dict) and df.get("imgs") == (b.get("imgs") if isinstance(b, dict) else None),
   "got %s want %s" % (df, b))
run("wait", "600")
shot("d-front-slot-cleared.png")

leftover = ssh("cd %s && wp db query \"SELECT COUNT(*) FROM wp_postmeta WHERE meta_key LIKE 'sf_formula_frame%%'\" --allow-root\n" % WP_ROOT)
tail = leftover.strip().splitlines()[-1].strip() if leftover.strip() else ""
ck("no sf_formula_frame% rows left behind", tail == "0", "query tail: %r" % tail)

ssh("cd %s && wp eval 'WP_Session_Tokens::get_instance(1)->destroy(\"%s\"); echo \"session destroyed\\n\";' --allow-root\n"
    % (WP_ROOT, token))
print("\nscreenshots: %d ok, %d failed" % (PASS, FAIL))
raise SystemExit(1 if FAIL else 0)

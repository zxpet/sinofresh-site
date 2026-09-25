#!/usr/bin/env python3
"""H11 gate — detail-page body band swap + article-feedback fixes.

What changed in H11:
  1. The four structured bands on the formula detail page (Specification
     cards, Formula & nutrition, Ingredients & composition, Recommended/
     Packaging) were removed from templates/single-sf_formula.html. The
     record's own post_content — already rendered by [sf_formula_body] —
     is the page's editable prose band; the sales desk pastes Word/Excel
     content into the block editor and it shows. The renderers stay
     registered so an editor can paste a shortcode back into the body.
  2. The /article-feedback endpoint now dispatches
     fluentform/submission_inserted after its straight insert, so Form 12's
     Admin Notification (sales@) actually fires — every vote since the GF
     migration was stored but never mailed.
  3. The endpoint gained the inquiry endpoint's 60s-per-IP transient damper
     (key prefix sf_afb_rl_, real 429) and records the client's address
     through the same CF-Connecting-IP helper the inquiry endpoint uses.

Modes:
  --source      static assertions on the working tree (no server)
  --preflight   behaviour against the preflight copy (X-SF-Preflight: 1)
  --live        same behaviour after the pull

Mail hygiene: the gate rewrites Form 12's notification recipient to an
example.invalid sink for its runtime and restores the original in finally,
so no gate-driven mail reaches sales@. The throttle transients the gate
creates are deleted before the run ends. 158's post_content is used for
the body-band probe and restored (byte for byte) after.
"""

import argparse
import base64
import json
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

# This machine flaps between IPv6 and the VPN's IPv4 exit across requests,
# which splits "same IP" assertions across two throttle buckets — force IPv4
# (sec1; the wrapper must replace a positional family, not duplicate it).
_orig_getaddrinfo = socket.getaddrinfo


def _ipv4_only(host, port, *args, **kwargs):
    kwargs.pop("family", None)
    if args:
        return _orig_getaddrinfo(host, port, socket.AF_INET, *args[1:], **kwargs)
    return _orig_getaddrinfo(host, port, family=socket.AF_INET, **kwargs)


socket.getaddrinfo = _ipv4_only

ROOT = "/Users/meng/WorkBuddy/sinofresh外贸网站建设"
THEME = ROOT + "/sinofresh-theme"
HOST = "https://dev.zxpet.com"
SERVER = "root@65.49.215.152"
WP_ROOT = "/var/www/dev.zxpet.com/public"
AUTH = "Basic " + base64.b64encode(b"sfdev:VkEws18Kl5V1qp3TpZ6s").decode()
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
SINK = "sf-gate-sink@example.invalid"   # invalid TLD: wp_mail accepts, nothing real is delivered

FAILED = []
PASSED = 0


def check(name, ok, detail=None):
    global PASSED
    if ok:
        PASSED += 1
        print("  ok   %s" % name)
    else:
        FAILED.append((name, detail))
        print("  FAIL %s   %s" % (name, detail if detail is not None else ""))


def read(path):
    with open(THEME + "/" + path, encoding="utf-8") as fh:
        return fh.read()


def fetch(path, preflight=False, method="GET", payload=None):
    req = urllib.request.Request(HOST + path, method=method)
    req.add_header("Authorization", AUTH)
    req.add_header("User-Agent", UA)
    if preflight:
        req.add_header("X-SF-Preflight", "1")
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        req.add_header("Content-Type", "application/json")
    req.add_header("Accept-Encoding", "identity")
    try:
        with urllib.request.build_opener().open(req, data=data, timeout=30) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")


def wp(*args):
    """One wp-cli call on dev. Args are shell-quoted."""
    quoted = " ".join("'" + a.replace("'", "'\\''") + "'" for a in args)
    cmd = ["ssh", SERVER, "cd %s && wp %s --allow-root" % (WP_ROOT, quoted)]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if out.returncode != 0:
        raise RuntimeError("wp %s failed: %s" % (" ".join(args), out.stderr[-400:]))
    return out.stdout.strip()


def wp_php(code):
    """Run a PHP snippet from a temp file (wp eval quoting does not survive
    two shells) and return stdout."""
    subprocess.run(["ssh", SERVER, "cat > /tmp/h11-snippet.php"],
                   input=code.encode(), check=True, timeout=30)
    out = wp("eval-file", "/tmp/h11-snippet.php")
    wp("eval", "unlink('/tmp/h11-snippet.php');")
    return out


# The strip function mirrors h9_gate's: comments must not count as "the code
# says this" — every judgement below reads the live statement, not prose.
def strip_php_comments(src):
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    src = re.sub(r"(?m)^\s*//.*$", " ", src)
    src = re.sub(r"(?m)^\s*#(?!/).*$", " ", src)
    return src


def source_mode():
    tpl = read("templates/single-sf_formula.html")
    fn = strip_php_comments(read("functions.php"))

    print("== SOURCE S1 — the four bands are gone from the template ==")
    for name, token in [
        ("Specification cards ([sf_formula_detail])", "[sf_formula_detail]"),
        ("Formula & nutrition ([sf_formula_detail_actives])", "[sf_formula_detail_actives]"),
        ("Ingredients & composition ([sf_formula_detail_composition])", "[sf_formula_detail_composition]"),
        ("Recommended/Packaging ([sf_formula_content])", "[sf_formula_content]"),
    ]:
        check("%s removed from the template" % name, token not in tpl)
    check("the Specification heading is gone", "<h2 class=\"wp-block-heading\">Specification</h2>" not in tpl)
    check("post_content band [sf_formula_body] stays (the editable area)", "[sf_formula_body]" in tpl)
    # the renderers must remain registered — an editor can paste one back
    check("renderers stay registered in functions.php",
          all(t in fn for t in ["add_shortcode('sf_formula_detail'",
                                "add_shortcode('sf_formula_detail_actives'",
                                "add_shortcode('sf_formula_detail_composition'",
                                "add_shortcode('sf_formula_content'"]))

    print("== SOURCE S2 — article-feedback: throttle, IP, dispatch ==")
    check("throttle key sf_afb_rl_ present", "sf_afb_rl_" in fn)
    check("set_transient with 60s TTL", re.search(r"set_transient\(\$rl_key, 1, 60\)", fn) is not None)
    check("over-limit answers 429 sf_feedback_rate",
          "sf_feedback_rate" in fn and "'status' => 429" in fn)
    # ordering inside the endpoint: throttle before the insert
    rl = fn.find("sf_afb_rl_")
    ins = fn.find("'fluentform_submissions')->insertGetId")
    check("throttle is taken before the DB insert", 0 < rl < ins)
    disp = fn.find("do_action('fluentform/submission_inserted'")
    check("submission_inserted dispatch exists", disp > 0)
    check("dispatch is after the insert (not before)", disp > ins)
    check("submission ip uses the CF-Connecting-IP helper",
          re.search(r"'ip'\s*=>\s*sinofresh_inquiry_client_ip\(\)", fn) is not None)
    check("stale 'no notifications' claim is gone from the endpoint comment",
          "Form 12 has\n\t\t\t\t * no notifications" not in read("functions.php"))

    print("== SOURCE S3 — front end stays CJK-free in code ==")
    vis = strip_php_comments(read("functions.php"))
    vis = re.sub(r"'hint' => '[^']*'", "''", vis)  # admin-only hints are allowed CJK
    check("no CJK ideographs outside admin hints",
          re.search(r"[\u4e00-\u9fff]", vis) is None)
    check("no CJK in the template", re.search(r"[\u4e00-\u9fff]", tpl) is None)


def one_formula_id():
    out = wp("post", "list", "--post_type=sf_formula", "--post_status=publish",
             "--posts_per_page=1", "--orderby=ID", "--order=ASC", "--field=ID")
    return out.splitlines()[0].strip()


def formula_url(post_id):
    slug = wp_php('<?php echo get_post_field("post_name", %d);' % int(post_id)).strip()
    return "/formulas/%s/" % slug


def set_form12_sink():
    """Rewrite Form 12's notification recipient to the sink and stash the
    original on the server for the restore.

    Guard: if the live recipient is already the sink, a previous gate run
    died before its finally ran and the state is poisoned — refuse to run
    rather than back up the sink into the restore file (that is how the
    2026-09-25 "restored to sink" red happened).
    """
    cur = wp_php(('<?php\n'
                  '$meta = wpFluent()->table("fluentform_form_meta")->where("form_id", 12)->where("meta_key", "notifications")->first();\n'
                  '$v = json_decode($meta->value, true); echo $v["to"];')).strip()
    if cur == SINK:
        raise RuntimeError(
            "Form 12 recipient is already the sink (%s): a previous gate run "
            "was killed before restore_form12(). Fix the DB recipient first, "
            "then re-run." % SINK)
    wp_php(("<?php\n"
            "$meta = wpFluent()->table('fluentform_form_meta')->where('form_id', 12)->where('meta_key', 'notifications')->first();\n"
            "$v = json_decode($meta->value, true);\n"
            "file_put_contents('/tmp/h11-f12-notif-bak.json', $meta->value);\n"
            "$v['sendTo']['email'] = '%s'; $v['to'] = '%s';\n"
            "wpFluent()->table('fluentform_form_meta')->where('id', $meta->id)->update(['value' => wp_json_encode($v)]);\n"
            "echo 'sink-set';" % (SINK, SINK)))


def restore_form12():
    wp_php(("<?php\n"
            "$bak = file_get_contents('/tmp/h11-f12-notif-bak.json');\n"
            "if ($bak) { wpFluent()->table('fluentform_form_meta')->where('form_id', 12)->where('meta_key', 'notifications')->update(['value' => $bak]); unlink('/tmp/h11-f12-notif-bak.json'); echo 'restored'; }"))


def clear_afb_transients():
    wp_php(("<?php\n"
            "global $wpdb;\n"
            "$like = '%sf_afb_rl_%';\n"
            "$wpdb->query($wpdb->prepare(\"DELETE FROM {$wpdb->options} WHERE option_name LIKE %s OR option_name LIKE %s\", $like, $like));\n"
            "echo 'cleared';"))


def latest_ff12_mail():
    out = wp_php(('<?php\n'
                  'global $wpdb;\n'
                  '$r = $wpdb->get_row("SELECT receiver, subject, LEFT(message, 500) AS msg FROM {$wpdb->prefix}wpml_mails ORDER BY mail_id DESC LIMIT 1");\n'
                  'echo $r ? json_encode(["to" => $r->receiver, "subject" => $r->subject, "msg" => $r->msg]) : "";'))
    try:
        return json.loads(out)
    except Exception:
        return {}


def ff12_log_tail():
    out = wp_php(('<?php\n'
                  'global $wpdb;\n'
                  '$rows = $wpdb->get_results("SELECT component, title, description FROM {$wpdb->prefix}fluentform_logs ORDER BY id DESC LIMIT 4");\n'
                  'echo json_encode($rows);'))
    try:
        return json.loads(out)
    except Exception:
        return []


def behaviour_mode(preflight):
    label = "PREFLIGHT" if preflight else "LIVE"
    print("== %s P1 — the four bands are gone; sheet/FAQ/body survive ==" % label)
    pid = one_formula_id()
    detail = formula_url(pid)
    status, html = fetch(detail, preflight)
    check("detail page served (%s)" % detail, status == 200)
    check("Specification cards band gone", "sf-fdetail__grid" not in html and "sf-fdetail__card" not in html)
    check('"Specification" heading gone', ">Specification</h2>" not in html)
    check("Formula & nutrition band gone", "sf-fdetail-actives" not in html)
    check("Recommended/Packaging band gone", "sf-fdetail-content" not in html)
    # survivors: the H10 sheet, the FAQ, JSON-LD, the trust band
    check("H10 spec sheet still renders", "sf-fdetail-specs" in html)
    check("three group headings still render",
          all(t in html for t in ["Core Parameters", "Product Specifications", "Packaging &amp; Logistics"]))
    check("FAQ band still renders", "sf-fdetail-faq" in html)
    check("trust band still renders", "sf-fdetail-trust" in html)
    check("Product JSON-LD still present", '"@type":"Product"' in html or 'Product"' in html)
    check("empty post_content renders no hollow body band", "sf-fdetail-body" not in html)
    time.sleep(1.3)

    print("== %s P2 — the editable band: post_content flows through [sf_formula_body] ==" % label)
    orig = wp_php(('<?php echo get_post_field("post_content", %d);' % int(pid)))
    try:
        probe = "<h2>Gate probe</h2><p>Pasted prose for the H11 band check.</p>"
        wp_php(('<?php wp_update_post(["ID" => %d, "post_content" => %s]); echo "set";'
                % (int(pid), json.dumps(probe))))
        status, html = fetch(detail, preflight)
        band = re.search(r'<section class="sf-fdetail-body">.*?</section>', html, re.S)
        check("filled post_content renders as the body band",
              band is not None and "Gate probe" in band.group(0))
        check("pasted markup keeps its heading structure",
              band is not None and "<h2" in band.group(0))
    finally:
        wp_php(('<?php wp_update_post(["ID" => %d, "post_content" => %s]); echo "restored";'
                % (int(pid), json.dumps(orig))))
        status, html = fetch(detail, preflight)
        check("post_content restored: band gone again", "sf-fdetail-body" not in html)
    time.sleep(1.3)

    print("== %s P3 — article-feedback: dispatch, throttle, IP ==" % label)
    clear_afb_transients()
    set_form12_sink()
    try:
        # a real post id so the subject line carries a title
        post_id = wp_php('<?php $p = get_posts(["numberposts" => 1, "post_status" => "publish", "fields" => "ids"]); echo $p ? $p[0] : "";').strip() or "1"
        before_log = ff12_log_tail()
        s1, b1 = fetch("/wp-json/sinofresh/v1/article-feedback", preflight,
                       method="POST", payload={"vote": "up", "post": int(post_id)})
        check("first vote accepted", s1 == 200 and b1.strip().startswith("{"),
              "status=%s body=%s" % (s1, b1[:80]))
        time.sleep(1.0)
        mail = latest_ff12_mail()
        check("notification went to the sink (Form 12 fired)",
              mail.get("to", "").startswith("sf-gate-sink@"), "got to=%s" % mail.get("to"))
        check("subject carries the vote", "Article feedback" in mail.get("subject", ""),
              "subject=%s" % mail.get("subject"))
        check("FF log records the send (EmailNotification, form 12)",
              any("EmailNotification" == r.get("component") for r in ff12_log_tail()),
              "log tail changed: %s" % ("yes" if ff12_log_tail() != before_log else "no"))
        iprow = wp_php(('<?php\n'
                        'global $wpdb;\n'
                        '$r = $wpdb->get_var("SELECT ip FROM {$wpdb->prefix}fluentform_submissions WHERE form_id = 12 ORDER BY id DESC LIMIT 1");\n'
                        'echo $r;'))
        try:
            my_ip = json.loads(urllib.request.urlopen("https://api.ipify.org?format=json", timeout=15).read())["ip"]
        except Exception:
            my_ip = ""
        check("submission ip is the visitor address, not the edge",
              iprow and iprow.strip() != "" and (not my_ip or my_ip in iprow),
              "ip=%s expected-mine=%s" % (iprow, my_ip))
        s2, b2 = fetch("/wp-json/sinofresh/v1/article-feedback", preflight,
                       method="POST", payload={"vote": "up", "post": int(post_id)})
        check("second vote within 60s answers 429", s2 == 429, "status=%s body=%s" % (s2, b2[:80]))
        clear_afb_transients()
        s3, b3 = fetch("/wp-json/sinofresh/v1/article-feedback", preflight,
                       method="POST", payload={"vote": "down", "post": int(post_id)})
        check("after the slot expires the vote goes through", s3 == 200, "status=%s" % s3)
    finally:
        restore_form12()
        clear_afb_transients()
    # the sink restore must be verified, not assumed
    val = wp_php(('<?php\n'
                  '$meta = wpFluent()->table("fluentform_form_meta")->where("form_id", 12)->where("meta_key", "notifications")->first();\n'
                  '$v = json_decode($meta->value, true); echo $v["to"];'))
    check("Form 12 notification recipient restored to sales@", val.strip() == "sales@zxpet.com", "got %s" % val)

    print("== %s P4 — gate hygiene ==" % label)
    n = wp_php(('<?php\n'
                'global $wpdb;\n'
                'echo (int) $wpdb->get_var("SELECT COUNT(*) FROM {$wpdb->options} WHERE option_name LIKE \'%sf_afb_rl_%\'");'))
    check("no throttle transients left", n.strip() == "0", "count=%s" % n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", action="store_true")
    ap.add_argument("--preflight", action="store_true")
    ap.add_argument("--live", action="store_true")
    args = ap.parse_args()
    if args.source:
        source_mode()
    if args.preflight or args.live:
        behaviour_mode(preflight=args.preflight and not args.live)
    print("\n%d passed, %d failed" % (PASSED, len(FAILED)))
    for name, detail in FAILED:
        print("  FAILED: %s   %s" % (name, detail if detail is not None else ""))
    sys.exit(1 if FAILED else 0)


if __name__ == "__main__":
    main()

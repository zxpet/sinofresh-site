#!/usr/bin/env python3
"""Go-live P2 pre-verify gate — the NEW production stack, before the vhost swap.

What it verifies
----------------
The runbook's P2: the freshly built stack (/var/www/zxpet-v2 + DB zxpet_prod)
is exercised through a TEMPORARY loopback vhost on 127.0.0.1:8080 whose
ServerName is www.zxpet.com. The two live vhosts are not touched, so the old
production site keeps serving whatever it served before.

Requests carry:
    Host: www.zxpet.com
    X-Forwarded-Proto: https     (the temp vhost maps it to HTTPS=on, so WP
                                  does not canonical-redirect to the live host)

Modes
-----
  (default)      read-only assertions only
  --with-mail    additionally exercise the inquiry endpoint's happy path, which
                 sends ONE real email to the site's own address. Off by default
                 because the SMTP account is rate-limited by the provider and
                 repeated sends trip its anti-abuse ("system busy").

The temp vhost must exist:
    /etc/httpd/conf.d/zz-temp-v2-preverify.conf   (Listen 127.0.0.1:8080)

Exit code = number of failed checks.
"""

import argparse
import subprocess
import sys

SERVER = "root@65.49.215.152"
V2 = "/var/www/zxpet-v2"
DB = "zxpet_prod"
HOST = "www.zxpet.com"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
EXPECT_THEME_VER = "2.10.88"
AI_AGENTS = ["GPTBot", "ClaudeBot", "PerplexityBot", "Google-Extended"]

_results = []


def check(name, ok, detail=""):
    _results.append((name, bool(ok), detail))
    line = ("PASS  " if ok else "FAIL  ") + name
    if detail and not ok:
        line += "  — " + detail
    print(line)
    return ok


def ssh(cmd, timeout=180):
    r = subprocess.run(["ssh", SERVER, cmd], capture_output=True, text=True,
                       errors="replace", timeout=timeout)
    return r.stdout


def curl(path, want_body=True):
    """Fetch path from the temp vhost; returns (status, headers, body).

    With want_body=False the body is never transferred back (it may be binary:
    an image, a stylesheet), so no decoding can fail on it.
    """
    tail = '; echo; cat /tmp/p2h.txt' if not want_body \
        else '; echo; cat /tmp/p2h.txt; echo "===BODY==="; cat /tmp/p2b.txt'
    cmd = ('curl -sk -D /tmp/p2h.txt -o /tmp/p2b.txt -w "%%{http_code}" '
           '-H "Host: %s" -H "X-Forwarded-Proto: https" -A "%s" '
           '"http://127.0.0.1:8080%s"%s' % (HOST, UA, path, tail))
    out = ssh(cmd)
    head, _, body = out.partition("===BODY===")
    lines = head.strip().split("\n")
    status = lines[0].strip() if lines else ""
    headers = "\n".join(lines[1:])
    return status, headers, body if want_body else ""


def wp(cli):
    return ssh("wp --path=%s %s --allow-root 2>/dev/null" % (V2, cli))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--with-mail", action="store_true",
                    help="also POST a valid inquiry (sends one real email)")
    args = ap.parse_args()

    print("=" * 72)
    print("Go-live P2 pre-verify  (temp vhost 127.0.0.1:8080 -> %s, DB %s)" % (V2, DB))
    print("=" * 72)

    # --- 1. reachability + homepage identity -------------------------------
    status, headers, home = curl("/")
    check("homepage 200 via temp vhost", status == "200", "got %s" % status)
    check("canonical is https://www.zxpet.com/",
          '<link rel="canonical" href="https://www.zxpet.com/" />' in home)
    check("no WWW-Authenticate header", "www-authenticate" not in headers.lower())
    check("no X-Robots-Tag header", "x-robots-tag" not in headers.lower())
    check("noindex meta present (blog_public=0)",
          "noindex" in home.lower() and 'name=\'robots\'' in home)
    check("theme stylesheet ver=%s" % EXPECT_THEME_VER,
          "sinofresh-theme/style.css?ver=%s" % EXPECT_THEME_VER in home)
    check("no dev.zxpet.com in rendered HTML", "dev.zxpet.com" not in home)

    # --- 2. robots.txt -----------------------------------------------------
    status, _, robots = curl("/robots.txt")
    check("robots.txt serves 200", status == "200", "got %s" % status)
    check("robots.txt disallows everything", "User-agent: *" in robots and "Disallow: /" in robots)
    for a in AI_AGENTS:
        check("robots.txt names %s" % a, ("User-agent: %s" % a) in robots)
    check("robots.txt has no stale Sitemap line promising content", "Sitemap:" not in robots)

    # --- 3. every published page, post and formula record ------------------
    urls = []
    for pt in ("page", "post", "sf_formula"):
        out = wp("post list --post_type=%s --post_status=publish --field=url" % pt)
        urls += [u.strip() for u in out.splitlines() if u.strip()]
    bad = []
    for u in urls:
        p = u.replace("https://www.zxpet.com", "") or "/"
        st, _, _ = curl(p, want_body=False)
        if st != "200":
            bad.append("%s -> %s" % (p, st))
    check("all %d published URLs return 200" % len(urls), not bad, "; ".join(bad[:5]))

    # --- 4. uploads imagery referenced by the pages ------------------------
    import re
    pages_probe = ["/", "/about/", "/quality/", "/products/soft-chews/"]
    imgs = set()
    for p in pages_probe:
        _, _, html = curl(p)
        for attr in (r'src="', r'data-src="'):
            imgs |= set(re.findall(attr + r'(https://www\.zxpet\.com/wp-content/uploads/[^"]+)"', html))
        for srcset in re.findall(r'srcset="([^"]+)"', html):
            for cand in srcset.split(","):
                u = cand.strip().split(" ")[0]
                if u.startswith("https://www.zxpet.com/wp-content/uploads/"):
                    imgs.add(u)
    imgs = sorted(imgs)
    bad = []
    for u in imgs:
        st, _, _ = curl(u.replace("https://www.zxpet.com", ""), want_body=False)
        if st != "200":
            bad.append("%s -> %s" % (u, st))
    check("all %d uploads images across 4 pages return 200" % len(imgs), not bad, "; ".join(bad[:3]))

    # --- 5. REST + admin surface ------------------------------------------
    st, _, _ = curl("/wp-json/", want_body=True)
    check("/wp-json/ 200", st == "200", "got %s" % st)
    st, _, _ = curl("/wp-login.php")
    check("/wp-login.php 200", st == "200", "got %s" % st)
    st, _, _ = curl("/wp-admin/", want_body=False)
    check("/wp-admin/ redirects to login (302)", st == "302", "got %s" % st)

    # --- 6. stack identity + lockdown wiring ------------------------------
    check("DB in use is %s" % DB, wp("eval 'echo DB_NAME;'").strip() == DB)
    check("home option is https://www.zxpet.com",
          wp("option get home").strip() == "https://www.zxpet.com")
    check("siteurl option is https://www.zxpet.com",
          wp("option get siteurl").strip() == "https://www.zxpet.com")
    check("blog_public stays 0 (noindex phase)", wp("option get blog_public").strip() == "0")
    check("active theme is sinofresh-theme",
          wp("theme list --status=active --field=name").strip() == "sinofresh-theme")
    got_mu = wp("eval 'echo implode(\",\", array_keys(get_mu_plugins()));'").strip()
    check("only the consent-bridge mu-plugin is deployed",
          got_mu == "zz-sf-wps-consent-bridge.php", "mu-plugins: %s" % got_mu)
    check("dev-lockdown mu-plugin is NOT deployed", "dev-lockdown" not in got_mu)

    consent = wp("eval 'echo get_option(\"wp_statistics\")[\"consent_integration\"];'").strip()
    check("WP Statistics consent_integration = wp_consent_api", consent == "wp_consent_api",
          "got %r" % consent)
    ctype = wp("eval 'echo function_exists(\"wp_get_consent_type\") ? wp_get_consent_type() : \"\";'").strip()
    check("wp_get_consent_type() = optin", ctype == "optin", "got %r" % ctype)
    hcons = wp("eval 'echo function_exists(\"wp_has_consent\") && wp_has_consent(\"statistics\") ? \"1\" : \"0\";'").strip()
    check("wp_has_consent('statistics') is false before consent", hcons == "0", "got %r" % hcons)

    # --- 7. no stale dev URLs left in the database ------------------------
    leftovers = ssh(
        "mysql -N -B %s -e \"SELECT COUNT(*) FROM wp_options WHERE option_value LIKE '%%dev.zxpet.com%%';\""
        % DB).strip()
    posts = ssh(
        "mysql -N -B %s -e \"SELECT COUNT(*) FROM wp_posts WHERE post_content LIKE '%%dev.zxpet.com%%' OR guid LIKE '%%dev.zxpet.com%%';\""
        % DB).strip()
    check("no dev.zxpet.com in wp_options", leftovers == "0", "rows: %s" % leftovers)
    check("no dev.zxpet.com in wp_posts", posts == "0", "rows: %s" % posts)

    # --- 8. inquiry endpoint negative paths -------------------------------
    # Timestamps must be computed AT THE MOMENT of each POST: the gate walks
    # dozens of URLs first, so a value captured at the top would be minutes old
    # by the time the "too fast" probe runs and the probe would look honest.
    import time

    def post(payload_fn, ip):
        cmd = ('curl -sk -o /tmp/p2r.txt -w "%%{http_code}" -X POST '
               '-H "Host: %s" -H "X-Forwarded-Proto: https" '
               '-H "Content-Type: application/json" -H "CF-Connecting-IP: %s" '
               '-A "%s" --data-binary @- '
               '"http://127.0.0.1:8080/wp-json/sinofresh/v1/inquiry"; echo; cat /tmp/p2r.txt'
               % (HOST, ip, UA))
        r = subprocess.run(["ssh", SERVER, cmd], input=payload_fn(),
                           capture_output=True, text=True, errors="replace", timeout=120)
        out = r.stdout.strip().split("\n")
        return out[0].strip(), "\n".join(out[1:])

    def ms(offset):
        return int(time.time() * 1000) + offset

    st, body = post(lambda: '{"website":"http://spam","ts":%d,"name":"Bot","email":"bot@example.com",'
                            '"message":"x"}' % ms(-6000), "198.51.100.10")
    check("inquiry honeypot rejected (400)", st == "400" and "sf_inquiry_spam" in body,
          "%s %s" % (st, body[:80]))

    st, body = post(lambda: '{"website":"","ts":%d,"name":"Fast","email":"fast@example.com",'
                            '"message":"x"}' % ms(0), "198.51.100.11")
    check("inquiry forged/fast timestamp rejected (400)",
          st == "400" and "sf_inquiry_fast" in body, "%s %s" % (st, body[:80]))

    st, body = post(lambda: '{"website":"","ts":%d,"name":"","email":"x@example.com",'
                            '"message":"x"}' % ms(-6000), "198.51.100.12")
    check("inquiry missing name rejected (400)",
          st == "400" and "sf_inquiry_name" in body, "%s %s" % (st, body[:80]))

    if args.with_mail:
        print("-" * 72)
        print("--with-mail: this POST sends ONE real email to the site's own address")
        st, body = post(lambda: '{"website":"","ts":%d,"name":"P2 gate","email":"p2-gate@example.com",'
                                '"company":"SINO FRESH QA","country":"CN",'
                                '"message":"P2 gate happy-path probe","source":"https://www.zxpet.com/"}' % ms(-6000),
                        "198.51.100.13")
        check("inquiry happy path accepted (200 ok:true)", st == "200" and '"ok":true' in body,
              "%s %s" % (st, body[:120]))
        st, body = post(lambda: '{"website":"","ts":%d,"name":"Again","email":"p2-gate2@example.com",'
                                '"message":"x"}' % ms(-6000), "198.51.100.13")
        check("inquiry throttle kicks in on second send (429)",
              st == "429" and "sf_inquiry_rate" in body, "%s %s" % (st, body[:120]))
        logged = ssh("mysql -N -B %s -e \"SELECT status FROM wp_fsmpt_email_logs ORDER BY id DESC LIMIT 1;\"" % DB).strip()
        check("mail transport reported the send as sent", logged == "sent", "last log status: %r" % logged)
    else:
        print("(skipped: inquiry happy path / throttle / SMTP send — rerun with --with-mail)")
        print("(note: the honeypot/fast/name probes above already ran; they burn no "
              "rate-limit slot and send no mail)")

    # --- summary -----------------------------------------------------------
    fails = [r for r in _results if not r[1]]
    print("=" * 72)
    print("P2 pre-verify: %d checks, %d passed, %d failed" % (len(_results), len(_results) - len(fails), len(fails)))
    for n, _, d in fails:
        print("  FAIL %s  — %s" % (n, d))
    print("=" * 72)
    return len(fails)


if __name__ == "__main__":
    sys.exit(main())

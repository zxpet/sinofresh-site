#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
H24b 精细限流 HTTP 验收（dev / prod 通用，受控、可清理、零残留）

验证三件事：
  ① 真实提交会计数：同一 IP 第 5 次之后（第 6 次）返回 429
  ② spam 不占配额：被拦的提交不会让真实计数增加
  ③ 达限后 429 发生在评分之前（不落库、不写审计、不发信）

两种运行模式
  dev  —— 全链路：真的连发 5 条真人询盘把计数打满，第 6 条应 429（dev 邮件被无条件黑洞，无外发风险）
  prod —— 受控：先发 1 条**机器人**载荷（spam 路径本来就不发信）验证②，再用 wp eval 把计数预置为 5
          验证①③。全程不产生任何真实邮件。

为什么 prod 不能跑全链路
  5 条真人询盘会触发 5 封管理员通知到 sales@zxpet.com。生产上不得为了测试污染收件箱，
  而 H24 那套「条件式邮件隔离」夹具本批并未常驻。故 prod 用预置计数的方式等价验证。

用法（服务器侧）
  SF_H24B_SITE=dev  python3 /root/h24-tools/h24b_rl_e2e.py
  SF_H24B_SITE=prod python3 /root/h24-tools/h24b_rl_e2e.py
  附加 --keep 可跳过清理（排查用）
"""
import base64
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse

SITE = os.environ.get("SF_H24B_SITE", "dev")
if SITE == "dev":
    WP_PATH = "/var/www/dev.zxpet.com/public"
    HOST = "dev.zxpet.com"
    AUTH = "Basic " + base64.b64encode(
        ("%s:%s" % (os.environ.get("SFDEV_USER", "sfdev"),
                    os.environ.get("SFDEV_PASS", "VkEws18Kl5V1qp3TpZ6s"))).encode()).decode()
else:
    WP_PATH = "/var/www/zxpet-v2"
    HOST = "www.zxpet.com"
    AUTH = None

BASE = "http://127.0.0.1"
CLIENT_IP = "127.0.0.1"          # loopback 请求：直连方不是 CF 边缘 ⇒ 真实 IP = REMOTE_ADDR
LIMIT = 5
KEEP = "--keep" in sys.argv
FAILS = []

UA_HUMAN = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
UA_BOT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36")


def log(s):
    print(s, flush=True)


def check(name, ok, detail=""):
    log(("  [PASS] " if ok else "  [FAIL] ") + name + (("  | " + detail) if detail else ""))
    if not ok:
        FAILS.append(name)


def headers():
    h = ["-H", "Host: " + HOST]
    if AUTH:
        h += ["-H", "Authorization: " + AUTH]
    return h


def curl_get(path):
    p = subprocess.run(["curl", "-s", "-m", "60"] + headers() + [BASE + path], capture_output=True)
    return p.stdout.decode("utf-8", "replace")


def curl_post(path, body, ua=UA_HUMAN):
    p = subprocess.run(
        ["curl", "-s", "-m", "60", "-o", "/tmp/h24b_rl_body.txt", "-w", "%{http_code}"]
        + headers() + ["-H", "User-Agent: " + ua,
                       "-H", "Content-Type: application/x-www-form-urlencoded",
                       "--data-binary", body, BASE + path],
        capture_output=True)
    code = p.stdout.decode("utf-8", "replace").strip()
    try:
        with open("/tmp/h24b_rl_body.txt", "rb") as f:
            return code, f.read().decode("utf-8", "replace")
    except OSError:
        return code, ""


def wp1(sql):
    p = subprocess.run(["wp", "db", "query", sql, "--allow-root", "--skip-column-names",
                        "--path=" + WP_PATH], capture_output=True, text=True)
    v = p.stdout.strip()
    return v.split("\n")[0].strip() if v else ""


def wp_eval(code):
    p = subprocess.run(["wp", "eval", code, "--allow-root", "--path=" + WP_PATH],
                       capture_output=True, text=True)
    return p.stdout.strip()


def build_body(nonce, token, bot=False):
    if bot:
        fields = [
            ("company_name_1", "RobertTon"),
            ("contact_person_2", "Ton"),
            ("email_3", "robertton@gmail.com"),
            ("country_5", "United States"),
            ("interested_dosage_form_7", "Soft Chews"),
            ("notes_10", "Price?"),
            ("privacy_consent_11[]", "I agree to the Privacy Policy"),
            ("configuration_summary_12", ""),
            ("item_8__fluent_sf", ""),
            ("_fluentform_8_fluentformnonce", nonce),
            ("_wp_http_referer", "/contact/"),
        ]
    else:
        fields = [
            ("company_name_1", "H24b Rate Test Ltd"),
            ("contact_person_2", "Test Contact"),
            ("email_3", "h24b-rl-test@invalid.example"),
            ("country_5", "United Kingdom"),
            ("interested_dosage_form_7", "Soft Chews"),
            ("notes_10",
             "Hello, we are validating a rate-limit change on our own website. "
             "This message is long enough to stay out of the short-message signal, "
             "mentions no price question, and is submitted by the site operator."),
            ("privacy_consent_11[]", "I agree to the Privacy Policy"),
            ("configuration_summary_12", ""),
            ("item_8__fluent_sf", ""),
            ("sf_fg_t", token),
            ("_fluentform_8_fluentformnonce", nonce),
            ("_wp_http_referer", "/contact/"),
        ]
    inner = urllib.parse.urlencode(fields)
    return urllib.parse.urlencode({"action": "fluentform_submit", "form_id": "8", "data": inner})


log("============ H24b 精细限流 HTTP 验收 [site=%s] ============" % SITE)

# ------------------------------------------------------------------ 0 基线
log("\n=== 0. 基线快照 ===")
b_sub = int(wp1("SELECT COUNT(*) FROM wp_fluentform_submissions WHERE form_id=8"))
b_submax = int(wp1("SELECT COALESCE(MAX(id),0) FROM wp_fluentform_submissions WHERE form_id=8"))
b_fs = int(wp1("SELECT COUNT(*) FROM wp_fsmpt_email_logs"))
b_fsmax = int(wp1("SELECT COALESCE(MAX(id),0) FROM wp_fsmpt_email_logs"))
b_spam = int(wp1("SELECT COUNT(*) FROM wp_sf_form_spam_log"))
b_spammax = int(wp1("SELECT COALESCE(MAX(id),0) FROM wp_sf_form_spam_log"))
b_mail = int(wp1("SELECT COUNT(*) FROM wp_wpml_mails"))
b_mailmax = int(wp1("SELECT COALESCE(MAX(mail_id),0) FROM wp_wpml_mails"))
log("  submissions(form8)=%d (max id %d) | fsmpt=%d (max %d) | spam_log=%d (max %d) | wpml=%d (max %d)"
    % (b_sub, b_submax, b_fs, b_fsmax, b_spam, b_spammax, b_mail, b_mailmax))

# 限流相关状态清零（幂等起点）
wp_eval("sf_fg_rl_reset('%s');" % CLIENT_IP)
c0 = wp_eval("echo sf_fg_rl_count('%s');" % CLIENT_IP)
check("起点：真实计数已清零", c0 == "0", "count=%s" % c0)

# ------------------------------------------------------------------ 1 抓页面
log("\n=== 1. GET /contact/ 取 nonce 与计时 token ===")
html = curl_get("/contact/")
m_tok = re.search(r'var\s+TOKEN\s*=\s*"([^"]*)"', html)
m_non = re.search(r'name="_fluentform_8_fluentformnonce"\s+value="([^"]*)"', html)
token = m_tok.group(1) if m_tok else ""
nonce = m_non.group(1) if m_non else ""
log("  页面 %d 字节  token=%s  nonce=%s"
    % (len(html), (token[:20] + "...") if token else "(NONE)", nonce or "(NONE)"))
check("页面含签名计时 token", bool(token))
check("页面含 form nonce", bool(nonce))

try:
    # -------------------------------------------------------------- 2 spam 不占配额
    log("\n=== 2. 机器人载荷：被拦且不占配额、不发信 ===")
    code, resp = curl_post("/wp-admin/admin-ajax.php", build_body(nonce, token, bot=True), UA_BOT)
    log("  HTTP %s | %s" % (code, resp[:160].replace("\n", " ")))
    check("机器人载荷 HTTP 200（伪装成功）", code == "200", code)

    a_spam = int(wp1("SELECT COUNT(*) FROM wp_sf_form_spam_log"))
    check("审计表 +1（确认确实走了被拦路径）", a_spam == b_spam + 1, "%d -> %d" % (b_spam, a_spam))
    a_fs = int(wp1("SELECT COUNT(*) FROM wp_fsmpt_email_logs"))
    a_mail = int(wp1("SELECT COUNT(*) FROM wp_wpml_mails"))
    check("被拦提交零发信（FluentSMTP）", a_fs == b_fs, "%d -> %d" % (b_fs, a_fs))
    check("被拦提交零发信（wp-mail-logging）", a_mail == b_mail, "%d -> %d" % (b_mail, a_mail))

    ca = wp_eval("echo sf_fg_rl_count('%s');" % CLIENT_IP)
    check("★ spam 不占配额：真实计数仍为 0", ca == "0", "count=%s" % ca)

    if SITE == "dev":
        # ---------------------------------------------------------- 3a 全链路：打满 5 次
        log("\n=== 3a. [dev] 连发 %d 条真人询盘把计数打满 ===" % LIMIT)
        for i in range(1, LIMIT + 1):
            cb, rb = curl_post("/wp-admin/admin-ajax.php", build_body(nonce, token, bot=False), UA_HUMAN)
            cnt = wp_eval("echo sf_fg_rl_count('%s');" % CLIENT_IP)
            log("    第 %d 次: HTTP %s | 计数=%s" % (i, cb, cnt))
            check("第 %d 次未被限流（HTTP 200）" % i, cb == "200", cb)
            check("第 %d 次计数增至 %d" % (i, i), cnt == str(i), cnt)
            time.sleep(1)
    else:
        # ---------------------------------------------------------- 3b prod：预置计数
        log("\n=== 3b. [prod] 预置真实计数为 %d（等价于已连发 %d 条真人询盘）===" % (LIMIT, LIMIT))
        wp_eval("for($i=0;$i<%d;$i++){ sf_fg_rl_bump('%s'); }" % (LIMIT, CLIENT_IP))
        cnt = wp_eval("echo sf_fg_rl_count('%s');" % CLIENT_IP)
        check("预置后计数 = %d" % LIMIT, cnt == str(LIMIT), cnt)

    # -------------------------------------------------------------- 4 达限 → 429
    log("\n=== 4. 达限后再提交一次 ⇒ 应 429（且发生在评分之前）===")
    b_sub2 = int(wp1("SELECT COUNT(*) FROM wp_fluentform_submissions WHERE form_id=8"))
    b_spam2 = int(wp1("SELECT COUNT(*) FROM wp_sf_form_spam_log"))
    code, resp = curl_post("/wp-admin/admin-ajax.php", build_body(nonce, token, bot=True), UA_BOT)
    log("  HTTP %s | %s" % (code, resp[:200].replace("\n", " ")))
    check("★ 达限返回 HTTP 429", code == "429", code)
    check("响应含 restricted 错误体", "restricted" in resp, resp[:160])

    a_sub2 = int(wp1("SELECT COUNT(*) FROM wp_fluentform_submissions WHERE form_id=8"))
    a_spam2 = int(wp1("SELECT COUNT(*) FROM wp_sf_form_spam_log"))
    check("429 时未落库（不新增 submission）", a_sub2 == b_sub2, "%d -> %d" % (b_sub2, a_sub2))
    check("429 时未写审计（不新增 spam_log）", a_spam2 == b_spam2, "%d -> %d" % (b_spam2, a_spam2))

    # -------------------------------------------------------------- 5 解除后恢复
    log("\n=== 5. 清掉计数后应恢复正常 ===")
    wp_eval("sf_fg_rl_reset('%s');" % CLIENT_IP)
    cnt = wp_eval("echo sf_fg_rl_count('%s');" % CLIENT_IP)
    check("计数归零", cnt == "0", cnt)
    cdb, rdb = curl_post("/wp-admin/admin-ajax.php", build_body(nonce, token, bot=True), UA_BOT)
    check("解除后不再 429", cdb != "429", cdb)

finally:
    # -------------------------------------------------------------- 清理
    log("\n=== CLEANUP ===")
    if KEEP:
        log("  --keep 已指定，跳过清理")
    else:
        wp_eval("sf_fg_rl_reset('%s');" % CLIENT_IP)
        d1 = wp1("DELETE FROM wp_fluentform_submissions WHERE form_id=8 AND id > %d AND ip LIKE '%%%s%%'"
                 % (b_submax, CLIENT_IP))
        d2 = wp1("DELETE FROM wp_sf_form_spam_log WHERE id > %d AND ip LIKE '%%%s%%'" % (b_spammax, CLIENT_IP))
        d3 = wp1("DELETE FROM wp_fsmpt_email_logs WHERE id > %d AND (`to` LIKE '%%h24b-rl-test@invalid.example%%' "
                 "OR `to` LIKE '%%h24-test@invalid.example%%')" % b_fsmax)
        d4 = wp1("DELETE FROM wp_wpml_mails WHERE mail_id > %d AND (receiver = 'h24b-rl-test@invalid.example' "
                 "OR receiver = 'h24-test@invalid.example')" % b_mailmax)
        log("  清理：submissions=%s spam_log=%s fsmpt=%s wpml=%s 计数已 reset" % (d1, d2, d3, d4))

        a_sub = int(wp1("SELECT COUNT(*) FROM wp_fluentform_submissions WHERE form_id=8"))
        a_fs = int(wp1("SELECT COUNT(*) FROM wp_fsmpt_email_logs"))
        a_spam = int(wp1("SELECT COUNT(*) FROM wp_sf_form_spam_log"))
        a_mail = int(wp1("SELECT COUNT(*) FROM wp_wpml_mails"))
        check("submissions 回基线", a_sub == b_sub, "%d vs %d" % (a_sub, b_sub))
        check("fsmpt 回基线", a_fs == b_fs, "%d vs %d" % (a_fs, b_fs))
        check("spam_log 回基线", a_spam == b_spam, "%d vs %d" % (a_spam, b_spam))
        check("wpml 回基线", a_mail == b_mail, "%d vs %d" % (a_mail, b_mail))
        check("计数回零", wp_eval("echo sf_fg_rl_count('%s');" % CLIENT_IP) == "0")

log("\n===== %s =====" % ("ALL PASS" if not FAILS else ("FAILED: " + ", ".join(FAILS))))
sys.exit(1 if FAILS else 0)

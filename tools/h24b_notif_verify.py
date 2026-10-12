#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
H24b 附带 bug 修正 —— **真通知**端到端验证（生产，受控、可清理）

流程
  1) 走真实访客路径提交 form 8 一次（测试数据）
  2) 管理员通知**真发**到 sales@zxpet.com（这是本脚本唯一的外发副作用，用户已批准）
  3) 从 FluentSMTP 日志读回该封邮件的 HTML 正文 → 转纯文本
  4) 断言「Privacy Consent」那一行显示的是**勾选值**，而不是公司名 / 不是空白
  5) 清理测试提交（保留邮件日志行 —— 它是真实投递的证据）

用法（服务器侧）
  SF_H24B_SITE=prod python3 /root/h24-tools/h24b_notif_verify.py [--keep]
"""
import base64
import html as htmlmod
import os
import re
import subprocess
import sys
import time
import urllib.parse

SITE = os.environ.get("SF_H24B_SITE", "prod")
if SITE == "dev":
    WP_PATH = "/var/www/dev.zxpet.com/public"
    HOST = "dev.zxpet.com"
    AUTH = "Basic " + base64.b64encode(b"sfdev:VkEws18Kl5V1qp3TpZ6s").decode()
else:
    WP_PATH = "/var/www/zxpet-v2"
    HOST = "www.zxpet.com"
    AUTH = None

BASE = "http://127.0.0.1"
CLIENT_IP = "127.0.0.1"
KEEP = "--keep" in sys.argv
FAILS = []

COMPANY = "H24B Notif Verify (TEST)"
CONTACT = "Site Operator"
# 用 IANA 保留域 example.com：既能精确标记「本次测试产生的行」，又永远不会真投递到第三方。
EMAIL = "verify@example.com"
MASK = "%%%s%%" % EMAIL
CONSENT = "I agree to the Privacy Policy"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


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


def curl_post(path, body):
    p = subprocess.run(
        ["curl", "-s", "-m", "60", "-o", "/tmp/h24b_nv_body.txt", "-w", "%{http_code}"]
        + headers() + ["-H", "User-Agent: " + UA,
                       "-H", "Content-Type: application/x-www-form-urlencoded",
                       "--data-binary", body, BASE + path],
        capture_output=True)
    code = p.stdout.decode("utf-8", "replace").strip()
    try:
        with open("/tmp/h24b_nv_body.txt", "rb") as f:
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


def fetch_body_b64(mid):
    code = ('echo base64_encode($GLOBALS["wpdb"]->get_var('
            '$GLOBALS["wpdb"]->prepare("SELECT body FROM wp_fsmpt_email_logs WHERE id=%d", '
            + str(int(mid)) + ')));')
    return wp_eval(code)


def html_to_text(s):
    # ⚠️ FF 的邮件 HTML 用 `<br style="-webkit-text-size-adjust:none;">` 换行，
    #    只匹配裸 `<br>` 会把整篇正文挤成一行（断言随即全错）。
    s = re.sub(r'(?i)<br[^>]*>', "\n", s)
    s = re.sub(r'(?i)</(p|div|tr|li|h[1-6]|table|td|th)[^>]*>', "\n", s)
    s = re.sub(r'<[^>]+>', '', s)
    s = htmlmod.unescape(s)
    s = re.sub(r'[ \t]+', ' ', s)
    s = re.sub(r'\n\s*\n+', "\n", s)
    return s.strip()


def build_body(nonce, token):
    inner = urllib.parse.urlencode([
        ("company_name_1", COMPANY),
        ("contact_person_2", CONTACT),
        ("email_3", EMAIL),
        ("country_5", "United States"),   # 必须是该 select 字段的合法选项值，否则 FF 校验返回 423
        ("interested_dosage_form_7", "Soft Chews"),
        ("notes_10",
         "Internal end-to-end verification submitted by the site operator to confirm the admin "
         "notification template renders the privacy consent line correctly. Please ignore this message."),
        ("privacy_consent_11[]", CONSENT),
        ("configuration_summary_12", ""),
        ("item_8__fluent_sf", ""),
        ("sf_fg_t", token),
        ("_fluentform_8_fluentformnonce", nonce),
        ("_wp_http_referer", "/contact/"),
    ])
    return urllib.parse.urlencode({"action": "fluentform_submit", "form_id": "8", "data": inner})


log("============ H24b 通知占位符修正：真通知端到端验证 [site=%s] ============" % SITE)
if SITE != "prod":
    log("[WARN] 非生产站点：dev 邮件被无条件黑洞，不会真外发。")

# ------------------------------------------------------------------ 0 基线
b_sub = int(wp1("SELECT COUNT(*) FROM wp_fluentform_submissions WHERE form_id=8"))
b_submax = int(wp1("SELECT COALESCE(MAX(id),0) FROM wp_fluentform_submissions WHERE form_id=8"))
b_fs = int(wp1("SELECT COUNT(*) FROM wp_fsmpt_email_logs"))
b_fsmax = int(wp1("SELECT COALESCE(MAX(id),0) FROM wp_fsmpt_email_logs"))
b_spam = int(wp1("SELECT COUNT(*) FROM wp_sf_form_spam_log"))
b_spammax = int(wp1("SELECT COALESCE(MAX(id),0) FROM wp_sf_form_spam_log"))
log("\n=== 0. 基线 === submissions=%d(max %d) fsmpt=%d(max %d) spam_log=%d(max %d)"
    % (b_sub, b_submax, b_fs, b_fsmax, b_spam, b_spammax))

wp_eval("sf_fg_rl_reset('%s');" % CLIENT_IP)

# ------------------------------------------------------------------ 1 抓页面
log("\n=== 1. GET /contact/ 取 nonce 与计时 token ===")
page = curl_get("/contact/")
m_tok = re.search(r'var\s+TOKEN\s*=\s*"([^"]*)"', page)
m_non = re.search(r'name="_fluentform_8_fluentformnonce"\s+value="([^"]*)"', page)
token = m_tok.group(1) if m_tok else ""
nonce = m_non.group(1) if m_non else ""
check("页面含签名计时 token", bool(token), (token[:18] + "...") if token else "(NONE)")
check("页面含 form nonce", bool(nonce), nonce or "(NONE)")

new_sub_id = 0
try:
    # -------------------------------------------------------------- 2 真提交
    log("\n=== 2. 提交一次测试数据（真实访客路径）===")
    code, resp = curl_post("/wp-admin/admin-ajax.php", build_body(nonce, token))
    log("  HTTP %s | %s" % (code, resp[:200].replace("\n", " ")))
    check("提交返回 HTTP 200", code == "200", code)
    check("返回体为成功（未被表单防护拦下）", '"success":true' in resp.replace(" ", ""), resp[:160])

    # ⚠️ 绝不能拿 MAX(id) 当「自己创建的行」——生产上攻击者随时在刷，会误删别人的记录。
    #    一律按本测试独有的邮箱精确定位。
    mine = int(wp1("SELECT COUNT(*) FROM wp_fluentform_submissions WHERE form_id=8 AND response LIKE '%s'" % MASK))
    check("落库 +1（按测试邮箱精确定位）", mine >= 1, "count=%d" % mine)
    my_audit = int(wp1("SELECT COUNT(*) FROM wp_sf_form_spam_log WHERE email_domain='example.com'"))
    check("未被判为垃圾（本测试邮箱在审计表为零）", my_audit == 0, "count=%d" % my_audit)

    # -------------------------------------------------------------- 3 等邮件
    log("\n=== 3. 等待管理员通知（最多 30s）===")
    new_mail_id = 0
    for i in range(15):
        time.sleep(2)
        # 按本测试独有的公司名定位（生产随时可能有别的提交进来）
        mid = wp1("SELECT id FROM wp_fsmpt_email_logs WHERE id > %d "
                  "AND subject LIKE '%%H24B Notif Verify%%' ORDER BY id DESC LIMIT 1" % b_fsmax)
        if mid:
            new_mail_id = int(mid)
            break
    check("FluentSMTP 日志新增 1 封（真发信）", new_mail_id > 0, "mail id=%s" % new_mail_id)

    if new_mail_id:
        meta = wp1("SELECT CONCAT(`to`,' | ',`from`,' | ',subject,' | ',status) "
                   "FROM wp_fsmpt_email_logs WHERE id=%d" % new_mail_id)
        log("  邮件: " + meta)
        check("收件人 = 管理员 sales@zxpet.com", "sales@zxpet.com" in meta, meta)
        check("发送状态 = sent", "| sent" in meta, meta)

        b64 = fetch_body_b64(new_mail_id)
        raw_html = base64.b64decode(b64).decode("utf-8", "replace") if b64 else ""
        text = html_to_text(raw_html)
        with open("/tmp/h24b_notif_body.txt", "w", encoding="utf-8") as f:
            f.write(text)

        log("\n  ---- 邮件正文（纯文本，节选）----")
        for ln in text.split("\n"):
            if ln.strip():
                log("    | " + ln.strip())
        log("  ---------------------------------")

        consent_line = ""
        for ln in text.split("\n"):
            if "Privacy Consent" in ln:
                consent_line = ln.strip()
        company_line = ""
        for ln in text.split("\n"):
            if ln.strip().startswith("Company"):
                company_line = ln.strip()

        check("★ 邮件里 Privacy Consent 行 = 勾选值",
              consent_line == "Privacy Consent: " + CONSENT, consent_line or "(未找到该行)")
        check("★ 该行**不再**显示公司名",
              "Privacy Consent: " + COMPANY not in text and COMPANY not in consent_line, consent_line)
        check("★ 该行非空",
              bool(consent_line) and consent_line.rstrip().endswith(CONSENT), consent_line)
        check("Company 行仍正常显示公司名", COMPANY in company_line, company_line)
finally:
    # -------------------------------------------------------------- 4 清理
    log("\n=== 4. 清理（保留邮件日志行作为投递证据）===")
    if KEEP:
        log("  --keep 指定，跳过清理")
    else:
        wp_eval("sf_fg_rl_reset('%s');" % CLIENT_IP)
        wp1("DELETE FROM wp_fluentform_submission_meta WHERE response_id IN "
            "(SELECT id FROM wp_fluentform_submissions WHERE form_id=8 AND response LIKE '%s')" % MASK)
        d = wp1("DELETE FROM wp_fluentform_submissions WHERE form_id=8 AND response LIKE '%s'" % MASK)
        left = int(wp1("SELECT COUNT(*) FROM wp_fluentform_submissions WHERE form_id=8 AND response LIKE '%s'" % MASK))
        log("  删除本次测试 submission（按测试邮箱定位；删除后残留=%d）" % left)
        check("测试行已清理干净", left == 0, "残留 %d" % left)
        check("限流计数回零", wp_eval("echo sf_fg_rl_count('%s');" % CLIENT_IP) == "0")

log("\n===== %s =====" % ("ALL PASS" if not FAILS else ("FAILED: " + ", ".join(FAILS))))
sys.exit(1 if FAILS else 0)

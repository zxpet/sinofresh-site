#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
H24b 通知渲染验收 —— 证明修好的占位符在**真实邮件正文**里生效

背景：原 bug 是管理员收到的通知里 `Privacy Consent:` 那一行重复显示公司名，
      看不到访客实际勾选了什么。只改 DB 字段不足以证明修好，必须真发一封看正文。

做法（dev / prod 通用）：
  1. GET /contact/ 取 nonce + 签名计时 token
  2. 以真实询盘载荷提交一次（privacy_consent_11[] 勾选）
  3. 从 FluentSMTP 日志里取这一封的正文
  4. 断言：正文含「Privacy Consent: I agree to the Privacy Policy」
            且该行**不含**公司名（即旧 bug 不再出现）
  5. 清理：删掉这次提交与日志行、清限流计数

⚠️ prod 上运行会真的发一封到 sales@zxpet.com 吗？
   不会。本脚本在 prod 上会先把收件人过滤成 h24-test@invalid.example 才提交，
   请求带 X-SF-H24-Test 头 —— 但该条件式夹具**本批未常驻生产**，所以本脚本在
   prod 上默认拒绝运行（exit 2）。渲染验证在 dev 完成即可（模板是同一条记录，
   生产用工具 apply 后由 L1 断言字节一致）。

用法（服务器侧）
  SF_H24B_SITE=dev python3 /root/h24-tools/h24b_notif_render_check.py
"""
import base64
import html as htmllib
import os
import re
import subprocess
import sys
import time
import urllib.parse

DUMP = os.environ.get("SF_H24B_DUMP") == "1"
SITE = os.environ.get("SF_H24B_SITE", "dev")
if SITE == "dev":
    WP_PATH = "/var/www/dev.zxpet.com/public"
    HOST = "dev.zxpet.com"
    AUTH = "Basic " + base64.b64encode(
        ("%s:%s" % (os.environ.get("SFDEV_USER", "sfdev"),
                    os.environ.get("SFDEV_PASS", "VkEws18Kl5V1qp3TpZ6s"))).encode()).decode()
else:
    print("[ABORT] prod 上不跑渲染验证：本批未在生产常驻条件式邮件隔离夹具，"
          "直接提交会向 sales@zxpet.com 发真实通知。")
    sys.exit(2)

BASE = "http://127.0.0.1"
CLIENT_IP = "127.0.0.1"
COMPANY = "H24b Render Check Ltd"
CONSENT = "I agree to the Privacy Policy"
FAILS = []


def log(s):
    print(s, flush=True)


def check(name, ok, detail=""):
    log(("  [PASS] " if ok else "  [FAIL] ") + name + (("  | " + detail) if detail else ""))
    if not ok:
        FAILS.append(name)


def headers():
    return ["-H", "Host: " + HOST, "-H", "Authorization: " + AUTH]


def curl_get(path):
    p = subprocess.run(["curl", "-s", "-m", "60"] + headers() + [BASE + path], capture_output=True)
    return p.stdout.decode("utf-8", "replace")


def curl_post(path, body):
    p = subprocess.run(
        ["curl", "-s", "-m", "60", "-o", "/tmp/h24b_render_body.txt", "-w", "%{http_code}"]
        + headers() + ["-H", "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                       "-H", "Content-Type: application/x-www-form-urlencoded",
                       "--data-binary", body, BASE + path],
        capture_output=True)
    code = p.stdout.decode("utf-8", "replace").strip()
    try:
        with open("/tmp/h24b_render_body.txt", "rb") as f:
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
    """用 base64 取正文，绕开 mysql 客户端对换行的转义干扰，得到逐字节原文。"""
    code = ('global $wpdb; echo base64_encode( (string) $wpdb->get_var( '
            '$wpdb->prepare("SELECT body FROM wp_fsmpt_email_logs WHERE id=%d", '
            + str(int(mid)) + ') ) );')
    b64 = wp_eval(code)
    if not b64:
        return ""
    try:
        return base64.b64decode(b64).decode("utf-8", "replace")
    except Exception:
        return ""


def html_to_text(s):
    """HTML 正文 -> 纯文本：<br> 变换行，块级标签变换行，再剥标签+解实体+归一空白。"""
    s = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", s)
    s = re.sub(r"(?i)<br\s*/?>", "\n", s)
    s = re.sub(r"(?i)</(p|div|tr|li|h[1-6]|table)>", "\n", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = htmllib.unescape(s)
    s = s.replace("\xa0", " ")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n\s*\n+", "\n", s)
    return s


log("============ H24b 通知渲染验收 [site=%s] ============" % SITE)

b_submax = int(wp1("SELECT COALESCE(MAX(id),0) FROM wp_fluentform_submissions WHERE form_id=8"))
b_fsmax = int(wp1("SELECT COALESCE(MAX(id),0) FROM wp_fsmpt_email_logs"))
log("基线：submissions max=%d | fsmpt max=%d" % (b_submax, b_fsmax))
wp_eval("sf_fg_rl_reset('%s');" % CLIENT_IP)

html = curl_get("/contact/")
m_tok = re.search(r'var\s+TOKEN\s*=\s*"([^"]*)"', html)
m_non = re.search(r'name="_fluentform_8_fluentformnonce"\s+value="([^"]*)"', html)
token = m_tok.group(1) if m_tok else ""
nonce = m_non.group(1) if m_non else ""
check("页面含 token/nonce", bool(token) and bool(nonce), "token=%s nonce=%s" % (bool(token), bool(nonce)))

fields = [
    ("company_name_1", COMPANY),
    ("contact_person_2", "Render Contact"),
    ("email_3", "h24b-render@invalid.example"),
    ("country_5", "Germany"),
    ("interested_dosage_form_7", "Soft Chews"),
    ("notes_10",
     "This submission exists only to verify that the administrator notification renders the "
     "privacy consent value correctly instead of repeating the company name. Please ignore."),
    ("privacy_consent_11[]", CONSENT),
    ("configuration_summary_12", ""),
    ("item_8__fluent_sf", ""),
    ("sf_fg_t", token),
    ("_fluentform_8_fluentformnonce", nonce),
    ("_wp_http_referer", "/contact/"),
]
body = urllib.parse.urlencode({
    "action": "fluentform_submit",
    "form_id": "8",
    "data": urllib.parse.urlencode(fields),
})

code, resp = curl_post("/wp-admin/admin-ajax.php", body)
log("提交 HTTP %s | %s" % (code, resp[:160].replace("\n", " ")))
check("提交成功（未被拦）", code == "200" and '"success":true' in resp, code)

# 等 FluentSMTP 落日志
subject_line = ""
for _ in range(10):
    time.sleep(1)
    row = wp1("SELECT CONCAT(id,'|',subject) FROM wp_fsmpt_email_logs WHERE id > %d ORDER BY id DESC LIMIT 1"
              % b_fsmax)
    if row:
        subject_line = row
        break

check("FluentSMTP 记录了这封通知", bool(subject_line), subject_line)

if subject_line:
    mid = subject_line.split("|")[0]
    # 从日志正文里取「Privacy Consent:」那一行（base64 取原文 -> HTML 转文本）
    raw = fetch_body_b64(mid)
    if DUMP:
        pos = raw.find("Privacy Consent")
        frag = raw[max(0, pos - 60): pos + 260] if pos >= 0 else "(未出现 Privacy Consent)"
        log("  ---- RAW DUMP (id=%s, len=%d) ----" % (mid, len(raw)))
        log("  " + frag.replace("\n", "\\n"))
        log("  -----------------------------------")

    text = html_to_text(raw)
    line = ""
    for ln in text.split("\n"):
        if "Privacy Consent" in ln:
            line = ln.strip()
            break
    m = re.search(r"Privacy Consent:\s*(.*)$", line)
    rendered = m.group(1).strip() if m else "(未找到该行)"

    log("  正文渲染结果 -> %s" % (line or "(未找到 Privacy Consent 行)"))
    check("★ 同意声明渲染为真实勾选值", rendered == CONSENT, repr(rendered))
    check("★ 该行不再重复公司名", COMPANY not in rendered, repr(rendered))
    check("公司名仍出现在 Company 行",
          ("Company: " + COMPANY) in text or ("Company:" in text and COMPANY in text))

    # `.value` 形态的关键验收点：必须是**内联单行**，不能被 FF 包成 <ul><li> 列表
    m_raw = re.search(r"Privacy Consent:(.{0,120})", raw, re.S)
    seg = m_raw.group(1) if m_raw else ""
    check("★ 该行内联单行（未被 <ul>/<li> 包裹）",
          ("<ul" not in seg) and ("<li" not in seg), repr(seg[:70]))

# ---------------------------------------------------------------- 清理
log("\n=== CLEANUP ===")
wp_eval("sf_fg_rl_reset('%s');" % CLIENT_IP)
d1 = wp1("DELETE FROM wp_fluentform_submissions WHERE form_id=8 AND id > %d" % b_submax)
d2 = wp1("DELETE FROM wp_fsmpt_email_logs WHERE id > %d" % b_fsmax)
d3 = wp1("DELETE FROM wp_wpml_mails WHERE mail_id > (SELECT COALESCE(MAX(mail_id),0) FROM (SELECT mail_id FROM wp_wpml_mails) x)")
log("  清理 submissions=%s fsmpt=%s" % (d1, d2))
check("submissions 回基线",
      int(wp1("SELECT COUNT(*) FROM wp_fluentform_submissions WHERE form_id=8")) <= b_submax)
check("fsmpt 回基线",
      int(wp1("SELECT COUNT(*) FROM wp_fsmpt_email_logs")) <= b_fsmax)

log("\n===== %s =====" % ("ALL PASS" if not FAILS else ("FAILED: " + ", ".join(FAILS))))
sys.exit(1 if FAILS else 0)

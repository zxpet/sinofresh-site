#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
H24 dev —— 真人路径端到端（正向）

模拟真实客户在 /contact/ 填表提交 form 8，断言：
  A. HTTP 200 + {"success":true}
  B. wp_fluentform_submissions 新增 1 行，status = unread（未被当成 spam）
  C. wp_wpml_mails 新增恰好 1 行（仅 Admin Notification；Auto Reply 已停用）
  D. wp_sf_form_spam_log 零新增（我方拦截器不该碰真人提交）

用法（服务器侧）：
  python3 /root/h24-tools/h24_e2e_real.py            # 跑并清理
  python3 /root/h24-tools/h24_e2e_real.py --keep     # 跑但保留数据
"""
import base64
import os
import re
import subprocess
import sys
import time
import urllib.parse

DEV = "/var/www/dev.zxpet.com/public"
BASE = "http://127.0.0.1"
HOST = "dev.zxpet.com"
# dev Basic 凭据：环境变量优先（SFDEV_USER / SFDEV_PASS），回退到项目内部已知值。
AUTH = "Basic " + base64.b64encode(
    ("%s:%s" % (os.environ.get("SFDEV_USER", "sfdev"),
                os.environ.get("SFDEV_PASS", "VkEws18Kl5V1qp3TpZ6s"))).encode()).decode()
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

KEEP = "--keep" in sys.argv
FAILS = []


def log(s):
    print(s, flush=True)


def check(name, ok, detail=""):
    log(("  [PASS] " if ok else "  [FAIL] ") + name + (("  | " + detail) if detail else ""))
    if not ok:
        FAILS.append(name)


def curl_get(path):
    p = subprocess.run(
        ["curl", "-s", "-m", "60",
         "-H", "Host: " + HOST, "-H", "Authorization: " + AUTH,
         BASE + path],
        capture_output=True)
    return p.stdout.decode("utf-8", "replace")


def curl_post(path, body, ua=UA):
    """返回 (http_code, body)"""
    p = subprocess.run(
        ["curl", "-s", "-m", "60",
         "-o", "/tmp/h24_e2e_body.txt",
         "-w", "%{http_code}",
         "-H", "Host: " + HOST, "-H", "Authorization: " + AUTH,
         "-H", "User-Agent: " + ua,
         "-H", "Content-Type: application/x-www-form-urlencoded",
         "--data-binary", body,
         BASE + path],
        capture_output=True)
    code = p.stdout.decode("utf-8", "replace").strip()
    try:
        with open("/tmp/h24_e2e_body.txt", "rb") as f:
            return code, f.read().decode("utf-8", "replace")
    except OSError:
        return code, ""


def wp(sql):
    p = subprocess.run(
        ["wp", "db", "query", sql, "--allow-root", "--skip-column-names"],
        cwd=DEV, capture_output=True, text=True)
    return p.stdout.strip()


def wp1(sql):
    v = wp(sql)
    return v.split("\n")[0].strip() if v else ""


# ---------------------------------------------------------------- 0 基线
log("=== 0. 基线 ===")
b_sub = int(wp1("SELECT COUNT(*) FROM wp_fluentform_submissions WHERE form_id=8"))
# 注意：wp-mail-logging 已 inactive，实际邮件日志在 FluentSMTP 的 wp_fsmpt_email_logs。
b_mail = int(wp1("SELECT COUNT(*) FROM wp_wpml_mails"))
b_mailmax = int(wp1("SELECT COALESCE(MAX(mail_id),0) FROM wp_wpml_mails"))
b_fs = int(wp1("SELECT COUNT(*) FROM wp_fsmpt_email_logs"))
b_fsmax = int(wp1("SELECT COALESCE(MAX(id),0) FROM wp_fsmpt_email_logs"))
b_spam = int(wp1("SELECT COUNT(*) FROM wp_sf_form_spam_log"))
log("  submissions(form8)=%d" % b_sub)
log("  fsmpt_email_logs=%d (max %d)   [权威邮件日志]" % (b_fs, b_fsmax))
log("  wp_wpml_mails=%d (max %d)      [历史表，mail-logging 已停用]" % (b_mail, b_mailmax))
log("  spam_log=%d" % b_spam)

# ---------------------------------------------------------------- 1 抓页面
log("\n=== 1. 抓 /contact/ 取 nonce 与签名计时 token ===")
html = curl_get("/contact/")
m_tok = re.search(r'var\s+TOKEN\s*=\s*"([^"]*)"', html)
m_non = re.search(r'name="_fluentform_8_fluentformnonce"\s+value="([^"]*)"', html)
token = m_tok.group(1) if m_tok else ""
nonce = m_nonce = m_non.group(1) if m_non else ""
log("  page bytes=%d  token=%s  nonce=%s"
    % (len(html), (token[:24] + "...") if token else "(NONE)", nonce or "(NONE)"))
check("页面含签名计时 token", bool(token))
check("页面含 form nonce", bool(nonce))
check("页面含蜜罐字段", "item_8__fluent_sf" in html)

# ---------------------------------------------------------------- 2 模拟真人填表耗时
log("\n=== 2. 等待 5 秒（模拟真人填表，避开 S6 快提交信号） ===")
time.sleep(5)

# ---------------------------------------------------------------- 3 提交
fields = [
    ("company_name_1", "Green Paws Nutrition Ltd"),
    ("contact_person_2", "Michael Brown"),
    ("email_3", "michael.brown@greenpawsnutrition.co.uk"),
    ("country_5", "United Kingdom"),
    ("interested_dosage_form_7", "Soft Chews"),
    ("notes_10",
     "Hello, we operate a pet specialty retail chain with 45 stores across the UK. "
     "We are looking for a private label partner for soft chews and tablets. "
     "Could you please share your MOQ for 10000 units, lead time and FOB pricing? "
     "We plan to launch in Q3 and would need samples first."),
    ("privacy_consent_11[]", "I agree to the Privacy Policy"),
    ("configuration_summary_12", ""),
    ("item_8__fluent_sf", ""),            # 蜜罐：真人留空
    ("sf_fg_t", token),                   # 合法签名计时值
    ("_fluentform_8_fluentformnonce", nonce),
    ("_wp_http_referer", "/contact/"),
]
inner = urllib.parse.urlencode(fields)
body = urllib.parse.urlencode({"action": "fluentform_submit", "form_id": "8", "data": inner})

log("\n=== 3. POST 提交（真人形态） ===")
code, resp = curl_post("/wp-admin/admin-ajax.php", body)
log("  HTTP %s" % code)
log("  body: %s" % resp[:300].replace("\n", " "))
check("HTTP 200", code == "200", code)
try:
    import json as _j
    jd = _j.loads(resp)
    ok_json = bool(jd.get("success"))
except Exception:
    ok_json = False
    jd = {}
check("响应 success=true", ok_json, str(jd)[:160])

# ---------------------------------------------------------------- 4 落库
log("\n=== 4. 落库核对 ===")
a_sub = int(wp1("SELECT COUNT(*) FROM wp_fluentform_submissions WHERE form_id=8"))
log("  submissions(form8): %d -> %d" % (b_sub, a_sub))
check("submissions 新增 1 行", a_sub == b_sub + 1, "%d -> %d" % (b_sub, a_sub))

last = wp1("SELECT CONCAT(id,'|',status,'|',IFNULL(LEFT(response,0),'')) "
           "FROM wp_fluentform_submissions WHERE form_id=8 ORDER BY id DESC LIMIT 1")
log("  最新行 id|status = %s" % last)
new_id = int(last.split("|")[0]) if last else 0
new_status = last.split("|")[1] if "|" in last else "?"
check("最新行 status=unread（非 spam/trashed）", new_status == "unread", new_status)

# ---------------------------------------------------------------- 5 邮件
log("\n=== 5. 邮件核对（Auto Reply 已停用，应只 1 封 Admin Notification） ===")
a_fs = int(wp1("SELECT COUNT(*) FROM wp_fsmpt_email_logs"))
a_fsmax = int(wp1("SELECT COALESCE(MAX(id),0) FROM wp_fsmpt_email_logs"))
log("  fsmpt_email_logs: %d -> %d   (max %d -> %d)" % (b_fs, a_fs, b_fsmax, a_fsmax))
delta = a_fs - b_fs
check("邮件新增恰好 1 行", delta == 1, "delta=%d" % delta)

if delta > 0:
    log("  --- 新增邮件明细 ---")
    rows = wp("SELECT id, `to`, subject, status FROM wp_fsmpt_email_logs "
              "WHERE id > %d ORDER BY id" % b_fsmax)
    for line in rows.split("\n"):
        if line.strip():
            log("    " + line)
    subj_all = wp("SELECT GROUP_CONCAT(subject SEPARATOR ' || ') FROM wp_fsmpt_email_logs "
                  "WHERE id > %d" % b_fsmax)
    has_autoreply = "We've received your inquiry" in subj_all
    check("新增邮件中不含自动回复", not has_autoreply, subj_all[:120])
    has_admin = "New Inquiry:" in subj_all
    check("新增邮件中含管理员通知", has_admin, subj_all[:120])
    # 收件人应是隔离地址（证明 dev 测试不会触达真实邮箱）
    st = wp1("SELECT COUNT(*) FROM wp_fsmpt_email_logs WHERE id > %d "
             "AND `to` LIKE '%%h24-test@invalid.example%%'" % b_fsmax)
    check("收件人已被 dev 邮件隔离改写", st == str(delta), "%s of %d" % (st, delta))
    # 全部 status=sent
    sent = wp1("SELECT COUNT(*) FROM wp_fsmpt_email_logs WHERE id > %d AND status='sent'" % b_fsmax)
    check("新增邮件 status=sent", sent == str(delta), "%s of %d" % (sent, delta))

# 历史表（mail-logging 已停用）不应被写入
a_mail = int(wp1("SELECT COUNT(*) FROM wp_wpml_mails"))
check("历史表 wp_wpml_mails 保持不动（插件已停用）", a_mail == b_mail,
      "%d -> %d" % (b_mail, a_mail))

# ---------------------------------------------------------------- 6 拦截日志
log("\n=== 6. 拦截日志核对（真人提交不应被记录） ===")
a_spam = int(wp1("SELECT COUNT(*) FROM wp_sf_form_spam_log"))
log("  spam_log: %d -> %d" % (b_spam, a_spam))
check("spam 日志零新增", a_spam == b_spam, "%d -> %d" % (b_spam, a_spam))

# ---------------------------------------------------------------- 7 清理
if not KEEP:
    log("\n=== 7. 清理测试数据 ===")
    if new_id:
        wp("DELETE FROM wp_fluentform_submissions WHERE id=%d" % new_id)
        wp("DELETE FROM wp_fluentform_entry_details WHERE submission_id=%d" % new_id)
        wp("DELETE FROM wp_fluentform_submission_meta WHERE response_id=%d" % new_id)
    wp("DELETE FROM wp_fsmpt_email_logs WHERE id > %d" % b_fsmax)
    c_sub = int(wp1("SELECT COUNT(*) FROM wp_fluentform_submissions WHERE form_id=8"))
    c_fs = int(wp1("SELECT COUNT(*) FROM wp_fsmpt_email_logs"))
    log("  清理后 submissions=%d (基线 %d)  fsmpt_logs=%d (基线 %d)"
        % (c_sub, b_sub, c_fs, b_fs))
    check("submissions 回到基线", c_sub == b_sub, "%d vs %d" % (c_sub, b_sub))
    check("邮件日志回到基线", c_fs == b_fs, "%d vs %d" % (c_fs, b_fs))
else:
    log("\n=== 7. --keep：保留测试数据（new_id=%d） ===" % new_id)

# ---------------------------------------------------------------- 结论
log("\n" + "=" * 52)
if FAILS:
    log("真人路径 E2E：**FAIL** (%d 项) -> %s" % (len(FAILS), ", ".join(FAILS)))
    sys.exit(1)
log("真人路径 E2E：**全部通过**")
sys.exit(0)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
H24 dev —— 机器人路径端到端（反向用例）

模拟机器人（不跑 JS、陈旧 UA、模式化内容）提交 form 8，断言：
  A. HTTP 200 + success=true（对外无感，不暴露拦截）
  B. 落库 1 行，status = spam
  C. 邮件零新增（fsmpt 权威表）—— 被拦不发任何信（管理员通知 + 自动回复都不发）
  D. FF 集成日志零新增（证明压根没走 Fluent Forms 的通知流程）
  E. 审计日志 +1，score >= 阈值，signals 含预期

用法（服务器侧）：
  python3 /root/h24-tools/h24_e2e_bot.py
  python3 /root/h24-tools/h24_e2e_bot.py --keep
"""
import base64
import os
import json
import re
import subprocess
import sys
import urllib.parse

DEV = "/var/www/dev.zxpet.com/public"
BASE = "http://127.0.0.1"
HOST = "dev.zxpet.com"
# dev Basic 凭据：环境变量优先（SFDEV_USER / SFDEV_PASS），回退到项目内部已知值。
AUTH = "Basic " + base64.b64encode(
    ("%s:%s" % (os.environ.get("SFDEV_USER", "sfdev"),
                os.environ.get("SFDEV_PASS", "VkEws18Kl5V1qp3TpZ6s"))).encode()).decode()
# 机器人 UA：主版本严重滞后 + 声明 Windows 10 ⇒ 命中 S4（S4 只记录、不计分）
BOT_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36")

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


def curl_post(path, body, ua):
    p = subprocess.run(
        ["curl", "-s", "-m", "60",
         "-o", "/tmp/h24_bot_body.txt", "-w", "%{http_code}",
         "-H", "Host: " + HOST, "-H", "Authorization: " + AUTH,
         "-H", "User-Agent: " + ua,
         "-H", "Content-Type: application/x-www-form-urlencoded",
         "--data-binary", body,
         BASE + path],
        capture_output=True)
    code = p.stdout.decode("utf-8", "replace").strip()
    try:
        with open("/tmp/h24_bot_body.txt", "rb") as f:
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
b_fs = int(wp1("SELECT COUNT(*) FROM wp_fsmpt_email_logs"))
b_fsmax = int(wp1("SELECT COALESCE(MAX(id),0) FROM wp_fsmpt_email_logs"))
b_fflog = int(wp1("SELECT COUNT(*) FROM wp_fluentform_logs"))
b_spam = int(wp1("SELECT COUNT(*) FROM wp_sf_form_spam_log"))
b_spam_max = int(wp1("SELECT COALESCE(MAX(id),0) FROM wp_sf_form_spam_log"))
log("  submissions(form8)=%d  fsmpt=%d(max %d)  fflogs=%d  spam_log=%d"
    % (b_sub, b_fs, b_fsmax, b_fflog, b_spam))

# ---------------------------------------------------------------- 1 取 nonce
log("\n=== 1. 抓 /contact/ 取 nonce（机器人会带 nonce，但不跑 JS 故无计时字段） ===")
html = curl_get("/contact/")
m_non = re.search(r'name="_fluentform_8_fluentformnonce"\s+value="([^"]*)"', html)
nonce = m_non.group(1) if m_non else ""
log("  nonce=%s" % (nonce or "(NONE)"))

# ---------------------------------------------------------------- 2 提交
fields = [
    ("company_name_1", "RobertTon"),
    ("contact_person_2", "Ton"),
    ("email_3", "robertton@gmail.com"),
    ("country_5", "United States"),
    ("interested_dosage_form_7", "Soft Chews"),
    ("notes_10", "Price?"),
    ("privacy_consent_11[]", "I agree to the Privacy Policy"),
    ("configuration_summary_12", ""),
    ("item_8__fluent_sf", ""),        # 蜜罐留空
    # 无 sf_fg_t：机器人不跑 JS
    ("_fluentform_8_fluentformnonce", nonce),
    ("_wp_http_referer", "/contact/"),
]
inner = urllib.parse.urlencode(fields)
body = urllib.parse.urlencode({"action": "fluentform_submit", "form_id": "8", "data": inner})

log("\n=== 2. POST 提交（机器人形态：陈旧 UA / 无计时字段 / 模式化内容） ===")
code, resp = curl_post("/wp-admin/admin-ajax.php", body, BOT_UA)
log("  HTTP %s" % code)
log("  body: %s" % resp[:300].replace("\n", " "))
check("HTTP 200", code == "200", code)
try:
    jd = json.loads(resp)
    ok_json = bool(jd.get("success"))
except Exception:
    jd = {}
    ok_json = False
check("响应 success=true（对外无感）", ok_json, str(jd)[:160])
low = resp.lower()
check("响应不泄露拦截措辞",
      ("spam" not in low) and ("block" not in low) and ("reject" not in low),
      resp[:120])

# ---------------------------------------------------------------- 3 落库
log("\n=== 3. 落库核对（应标 spam） ===")
a_sub = int(wp1("SELECT COUNT(*) FROM wp_fluentform_submissions WHERE form_id=8"))
log("  submissions(form8): %d -> %d" % (b_sub, a_sub))
check("submissions 新增 1 行", a_sub == b_sub + 1, "%d -> %d" % (b_sub, a_sub))
last = wp1("SELECT CONCAT(id,'|',status) FROM wp_fluentform_submissions "
           "WHERE form_id=8 ORDER BY id DESC LIMIT 1")
new_id = int(last.split("|")[0]) if last else 0
new_status = last.split("|")[1] if "|" in last else "?"
log("  最新行 id|status = %s" % last)
check("最新行 status=spam", new_status == "spam", new_status)

# ---------------------------------------------------------------- 4 邮件
log("\n=== 4. 邮件核对（被拦 ⇒ 一封都不该发） ===")
a_fs = int(wp1("SELECT COUNT(*) FROM wp_fsmpt_email_logs"))
log("  fsmpt_email_logs: %d -> %d" % (b_fs, a_fs))
check("邮件零新增", a_fs == b_fs, "%d -> %d" % (b_fs, a_fs))
if a_fs > b_fs:
    log("  --- 意外新增的邮件 ---")
    log(wp("SELECT id, `to`, subject, status FROM wp_fsmpt_email_logs WHERE id > %d" % b_fsmax))

# ---------------------------------------------------------------- 5 FF 集成日志
log("\n=== 5. FF 集成日志（应零新增，证明没走插件通知流程） ===")
a_fflog = int(wp1("SELECT COUNT(*) FROM wp_fluentform_logs"))
log("  fflogs: %d -> %d" % (b_fflog, a_fflog))
check("FF 集成日志零新增", a_fflog == b_fflog, "%d -> %d" % (b_fflog, a_fflog))

# ---------------------------------------------------------------- 6 审计日志
log("\n=== 6. 审计日志核对（应 +1 且成案） ===")
a_spam = int(wp1("SELECT COUNT(*) FROM wp_sf_form_spam_log"))
log("  spam_log: %d -> %d" % (b_spam, a_spam))
check("审计日志 +1", a_spam == b_spam + 1, "%d -> %d" % (b_spam, a_spam))

if a_spam > b_spam:
    row = wp1("SELECT CONCAT(score,'|',signals,'|',ip,'|',LEFT(ua,30),'|',source) "
              "FROM wp_sf_form_spam_log ORDER BY id DESC LIMIT 1")
    log("  score|signals|ip|ua|source = %s" % row)
    parts = row.split("|")
    score = int(parts[0]) if parts and parts[0].isdigit() else -1
    signals = parts[1] if len(parts) > 1 else ""
    sig_list = signals.split(",")
    check("score >= 4（达到阈值）", score >= 4, "score=%d" % score)
    check("signals 含 S1_shared（公司名/联系人同后缀）",
          any(s.startswith("S1_shared") for s in sig_list), signals)
    check("signals 含 S2（模板化内容）", "S2_template_message" in sig_list, signals)
    check("signals 含 S2b（短消息）", "S2b_short_message" in sig_list, signals)
    check("signals 记录了陈旧 UA（S4_note）", "S4_note_stale_ua" in sig_list, signals)
    # 关键不变量：S4 只记录、不计分 ⇒ 去掉 S4 后的理论分仍应等于实际分。
    # 已知 S1=3 + S2=1 + S2b=1 = 5，无 S4 分项 ⇒ score 必须恰好 5。
    check("S4 未参与计分（score 恰为 5）", score == 5, "score=%d" % score)
    # source 标签：按评分成案应为 'score'（黑名单成案则为 'blocklist:xxx'）
    src = parts[4] if len(parts) > 4 else ""
    check("source 标签 = 'score'", src == "score", src)

# ---------------------------------------------------------------- 7 清理
if not KEEP:
    log("\n=== 7. 清理测试数据 ===")
    if new_id:
        wp("DELETE FROM wp_fluentform_submissions WHERE id=%d" % new_id)
        wp("DELETE FROM wp_fluentform_entry_details WHERE submission_id=%d" % new_id)
        wp("DELETE FROM wp_fluentform_submission_meta WHERE response_id=%d" % new_id)
    wp("DELETE FROM wp_sf_form_spam_log WHERE id > %d" % b_spam_max)
    c_sub = int(wp1("SELECT COUNT(*) FROM wp_fluentform_submissions WHERE form_id=8"))
    c_spam = int(wp1("SELECT COUNT(*) FROM wp_sf_form_spam_log"))
    c_fs = int(wp1("SELECT COUNT(*) FROM wp_fsmpt_email_logs"))
    log("  清理后 submissions=%d (基线 %d)  spam_log=%d (基线 %d)  fsmpt=%d (基线 %d)"
        % (c_sub, b_sub, c_spam, b_spam, c_fs, b_fs))
    check("submissions 回到基线", c_sub == b_sub, "%d vs %d" % (c_sub, b_sub))
    check("spam_log 回到基线", c_spam == b_spam, "%d vs %d" % (c_spam, b_spam))
    check("邮件日志回到基线", c_fs == b_fs, "%d vs %d" % (c_fs, b_fs))
else:
    log("\n=== 7. --keep：保留（new_id=%d） ===" % new_id)

log("\n" + "=" * 52)
if FAILS:
    log("机器人路径 E2E：**FAIL** (%d 项) -> %s" % (len(FAILS), ", ".join(FAILS)))
    sys.exit(1)
log("机器人路径 E2E：**全部通过**")
sys.exit(0)

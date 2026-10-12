#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
H24 dev —— Turnstile「降级可用性」端到端

用户关切（修订第 1 条）：
  「Turnstile 加载失败时，表单仍能提交（走蜜罐+计时兜底），不能变成『客户填不了表』」

做法：用 Cloudflare 官方**公开测试凭据**（always-pass）临时启用 Turnstile，然后
  1) 证明启用后页面确实会注入 widget 挂载点（TS_KEY 非空）
  2) 证明**不带** turnstile token 的真客户提交仍被放行（S7=absent ⇒ 0 分，不是 fail）
  3) 证明提交走通全链路（200 / 入库 unread / 恰好 1 封管理员通知）

测试凭据（CF 官方文档，非真实密钥，无风险）：
  sitekey 1x00000000000000000000AA     secret 1x0000000000000000000000000000000AA

安全：原 option 值先备份，finally 中无条件还原（原本不存在则删除）。

用法（服务器侧）：
  python3 /root/h24-tools/h24_turnstile_degraded.py
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
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
OPT = "_fluentform_turnstile_details"
TEST_KEYS = {"siteKey": "1x00000000000000000000AA",
             "secretKey": "1x0000000000000000000000000000000AA"}

FAILS = []


def log(s):
    print(s, flush=True)


def check(name, ok, detail=""):
    log(("  [PASS] " if ok else "  [FAIL] ") + name + (("  | " + detail) if detail else ""))
    if not ok:
        FAILS.append(name)


def sh(args, inp=None):
    return subprocess.run(args, cwd=DEV, capture_output=True, text=True, input=inp)


def wp(sql):
    p = sh(["wp", "db", "query", sql, "--allow-root", "--skip-column-names"])
    return p.stdout.strip()


def wp1(sql):
    v = wp(sql)
    return v.split("\n")[0].strip() if v else ""


def wp_eval(php):
    p = sh(["wp", "eval", php, "--allow-root"])
    return (p.stdout + p.stderr).strip()


def curl_get(path):
    p = subprocess.run(["curl", "-s", "-m", "60", "-H", "Host: " + HOST,
                        "-H", "Authorization: " + AUTH, BASE + path], capture_output=True)
    return p.stdout.decode("utf-8", "replace")


def curl_post(path, body):
    p = subprocess.run(
        ["curl", "-s", "-m", "60", "-o", "/tmp/h24_ts_body.txt", "-w", "%{http_code}",
         "-H", "Host: " + HOST, "-H", "Authorization: " + AUTH,
         "-H", "User-Agent: " + UA,
         "-H", "Content-Type: application/x-www-form-urlencoded",
         "--data-binary", body, BASE + path], capture_output=True)
    try:
        with open("/tmp/h24_ts_body.txt", "rb") as f:
            return p.stdout.decode().strip(), f.read().decode("utf-8", "replace")
    except OSError:
        return p.stdout.decode().strip(), ""


def ts_key_in_page():
    html = curl_get("/contact/")
    m = re.search(r'var\s+TS_KEY\s*=\s*"([^"]*)"', html)
    return (m.group(1) if m else None), html


# ---------------------------------------------------------------- 0 基线与备份
log("=== 0. 备份原 option ===")
orig = wp_eval("$v = get_option('%s'); echo is_array($v) ? wp_json_encode($v) : '__NONE__';" % OPT)
log("  原值: %s" % orig[:160])

b_sub = int(wp1("SELECT COUNT(*) FROM wp_fluentform_submissions WHERE form_id=8"))
b_submax = int(wp1("SELECT COALESCE(MAX(id),0) FROM wp_fluentform_submissions"))
b_fs = int(wp1("SELECT COUNT(*) FROM wp_fsmpt_email_logs"))
b_fsmax = int(wp1("SELECT COALESCE(MAX(id),0) FROM wp_fsmpt_email_logs"))
b_spam = int(wp1("SELECT COUNT(*) FROM wp_sf_form_spam_log"))
log("  基线: submissions=%d fsmpt=%d spam_log=%d" % (b_sub, b_fs, b_spam))

key_before, _ = ts_key_in_page()
log("  启用前页面 TS_KEY = %r" % key_before)
check("启用前 TS_KEY 为空（未配置即不注入）", key_before == "", repr(key_before))

new_id = 0
try:
    # ------------------------------------------------------------ 1 启用测试凭据
    log("\n=== 1. 写入 Cloudflare 官方测试凭据 ===")
    php = ("update_option('%s', array('siteKey'=>'%s','secretKey'=>'%s')); "
           "echo 'ok';" % (OPT, TEST_KEYS["siteKey"], TEST_KEYS["secretKey"]))
    log("  %s" % wp_eval(php))

    key_on, _ = ts_key_in_page()
    log("  启用后页面 TS_KEY = %r" % key_on)
    check("启用后 TS_KEY 已注入", key_on == TEST_KEYS["siteKey"], repr(key_on))

    # ------------------------------------------------------------ 2 服务端可达性
    log("\n=== 2. 源站 -> challenges.cloudflare.com 可达性 ===")
    for i in (1, 2, 3):
        p = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-m", "20",
             "-w", "code=%{http_code} tls=%{time_appconnect}s ttfb=%{time_starttransfer}s total=%{time_total}s",
             "https://challenges.cloudflare.com/turnstile/v0/api.js"], capture_output=True, text=True)
        log("  try%d: %s" % (i, p.stdout.strip()))

    # ------------------------------------------------------------ 3 不带 token 提交
    log("\n=== 3. 真客户提交（不带 turnstile token ⇒ 模拟脚本加载失败的降级场景） ===")
    nonce = (re.search(r'name="_fluentform_8_fluentformnonce"\s+value="([^"]*)"',
                       curl_get("/contact/")) or [None, ""])[1]
    fields = [
        ("company_name_1", "Green Paws Nutrition Ltd"),
        ("contact_person_2", "Michael Brown"),
        ("email_3", "michael.brown@greenpawsnutrition.co.uk"),
        ("country_5", "United Kingdom"),
        ("interested_dosage_form_7", "Soft Chews"),
        ("notes_10", "Hello, we are a retailer with 45 stores in the UK. "
                     "Please share MOQ for 10000 units, lead time and FOB pricing."),
        ("privacy_consent_11[]", "I agree to the Privacy Policy"),
        ("configuration_summary_12", ""),
        ("item_8__fluent_sf", ""),
        ("_fluentform_8_fluentformnonce", nonce),
        ("_wp_http_referer", "/contact/"),
        # 注意：不带 cf-turnstile-response
    ]
    body = urllib.parse.urlencode({
        "action": "fluentform_submit", "form_id": "8",
        "data": urllib.parse.urlencode(fields)})
    code, resp = curl_post("/wp-admin/admin-ajax.php", body)
    log("  HTTP %s  %s" % (code, resp[:160].replace("\n", " ")))
    check("降级场景下提交成功（200）", code == "200", code)
    try:
        ok_json = bool(json.loads(resp).get("success"))
    except Exception:
        ok_json = False
    check("响应 success=true", ok_json, resp[:120])

    a_sub = int(wp1("SELECT COUNT(*) FROM wp_fluentform_submissions WHERE form_id=8"))
    check("已入库 1 行", a_sub == b_sub + 1, "%d -> %d" % (b_sub, a_sub))
    last = wp1("SELECT CONCAT(id,'|',status) FROM wp_fluentform_submissions "
               "WHERE form_id=8 ORDER BY id DESC LIMIT 1")
    new_id = int(last.split("|")[0]) if last else 0
    st = last.split("|")[1] if "|" in last else "?"
    check("status=unread（未被误判为 spam）", st == "unread", st)

    a_fs = int(wp1("SELECT COUNT(*) FROM wp_fsmpt_email_logs"))
    check("恰好 1 封管理员通知", a_fs == b_fs + 1, "%d -> %d" % (b_fs, a_fs))
    a_spam = int(wp1("SELECT COUNT(*) FROM wp_sf_form_spam_log"))
    check("未被拦截（spam 日志零新增）", a_spam == b_spam, "%d -> %d" % (b_spam, a_spam))

finally:
    # ------------------------------------------------------------ 4 无条件还原
    log("\n=== 4. 还原原 option ===")
    if orig == "__NONE__":
        log("  %s" % wp_eval("delete_option('%s'); echo 'deleted';" % OPT))
    else:
        log("  %s" % wp_eval("update_option('%s', json_decode('%s', true)); echo 'restored';"
                            % (OPT, orig.replace("'", "\\'"))))
    key_after, _ = ts_key_in_page()
    log("  还原后页面 TS_KEY = %r" % key_after)
    check("还原后 TS_KEY 回到空", key_after == "", repr(key_after))

    # 清理测试数据
    log("\n=== 5. 清理测试数据 ===")
    if new_id:
        wp("DELETE FROM wp_fluentform_submissions WHERE id=%d" % new_id)
        wp("DELETE FROM wp_fluentform_entry_details WHERE submission_id=%d" % new_id)
        wp("DELETE FROM wp_fluentform_submission_meta WHERE response_id=%d" % new_id)
    wp("DELETE FROM wp_fsmpt_email_logs WHERE id > %d" % b_fsmax)
    wp("DELETE FROM wp_fluentform_logs WHERE parent_source_id=8 AND created_at >= CURDATE()")
    c_sub = int(wp1("SELECT COUNT(*) FROM wp_fluentform_submissions WHERE form_id=8"))
    c_fs = int(wp1("SELECT COUNT(*) FROM wp_fsmpt_email_logs"))
    log("  清理后 submissions=%d (基线 %d)  fsmpt=%d (基线 %d)" % (c_sub, b_sub, c_fs, b_fs))
    check("submissions 回到基线", c_sub == b_sub, "%d vs %d" % (c_sub, b_sub))
    check("邮件日志回到基线", c_fs == b_fs, "%d vs %d" % (c_fs, b_fs))

log("\n" + "=" * 52)
if FAILS:
    log("Turnstile 降级 E2E：**FAIL** (%d) -> %s" % (len(FAILS), ", ".join(FAILS)))
    sys.exit(1)
log("Turnstile 降级 E2E：**全部通过**")
sys.exit(0)

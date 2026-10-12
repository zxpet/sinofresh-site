#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
H24 dev —— 限流端到端

dev 上真实 IP 层就绪（loopback 非 CF 边缘）⇒ 我方 filter 收紧为
  max=3 次 / interval=3600 秒
Fluent Forms 的限流是**实时查表**：count(status != trashed AND ip=X AND created_at >= now-1h) >= max ⇒ 429。

因此连发 4 次干净的真客户形态提交，断言：
  第 1~3 次 HTTP 200
  第 4 次 HTTP 429，且响应体含 Too Many Requests

并加正向对照：换一个「IP」不成（FF 按 ip 计数），改为断言——被限流后
我们的拦截器不受影响（机器人路径另有一条，见 h24_e2e_bot.py）。

用法（服务器侧）：
  python3 /root/h24-tools/h24_e2e_ratelimit.py
  python3 /root/h24-tools/h24_e2e_ratelimit.py --keep
"""
import base64
import os
import json
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
N = 4  # 阈值 3 ⇒ 第 4 次应被限流


def log(s):
    print(s, flush=True)


def check(name, ok, detail=""):
    log(("  [PASS] " if ok else "  [FAIL] ") + name + (("  | " + detail) if detail else ""))
    if not ok:
        FAILS.append(name)


def curl_get(path):
    p = subprocess.run(
        ["curl", "-s", "-m", "60", "-H", "Host: " + HOST,
         "-H", "Authorization: " + AUTH, BASE + path],
        capture_output=True)
    return p.stdout.decode("utf-8", "replace")


def curl_post(path, body, ua=UA):
    p = subprocess.run(
        ["curl", "-s", "-m", "60",
         "-o", "/tmp/h24_rl_body.txt", "-w", "%{http_code}",
         "-H", "Host: " + HOST, "-H", "Authorization: " + AUTH,
         "-H", "User-Agent: " + ua,
         "-H", "Content-Type: application/x-www-form-urlencoded",
         "--data-binary", body, BASE + path],
        capture_output=True)
    code = p.stdout.decode("utf-8", "replace").strip()
    try:
        with open("/tmp/h24_rl_body.txt", "rb") as f:
            return code, f.read().decode("utf-8", "replace")
    except OSError:
        return code, ""


def wp(sql):
    p = subprocess.run(["wp", "db", "query", sql, "--allow-root", "--skip-column-names"],
                       cwd=DEV, capture_output=True, text=True)
    return p.stdout.strip()


def wp1(sql):
    v = wp(sql)
    return v.split("\n")[0].strip() if v else ""


# ---------------------------------------------------------------- 0 基线
log("=== 0. 基线 ===")
b_sub = int(wp1("SELECT COUNT(*) FROM wp_fluentform_submissions WHERE form_id=8"))
b_submax = int(wp1("SELECT COALESCE(MAX(id),0) FROM wp_fluentform_submissions"))
b_fs = int(wp1("SELECT COUNT(*) FROM wp_fsmpt_email_logs"))
b_fsmax = int(wp1("SELECT COALESCE(MAX(id),0) FROM wp_fsmpt_email_logs"))
log("  submissions(form8)=%d (max %d)  fsmpt=%d (max %d)" % (b_sub, b_submax, b_fs, b_fsmax))

# 0b 直读 filter 接线（CLI 下 real_ip_ready=true ⇒ 应为 3 / 3600）
log("\n=== 0b. 限流阈值 filter 直读 ===")
p = subprocess.run(["wp", "eval",
                    "echo apply_filters('fluentform/max_submission_count', 5, 8) . '|' . "
                    "apply_filters('fluentform/min_submission_interval', 30, 8);",
                    "--allow-root"], cwd=DEV, capture_output=True, text=True)
log("  max|interval = %s" % p.stdout.strip())
check("max 被收紧为 3", p.stdout.strip().startswith("3|"), p.stdout.strip())
check("interval 被收紧为 3600", p.stdout.strip().endswith("|3600"), p.stdout.strip())

# ---------------------------------------------------------------- 1 抓 nonce
html = curl_get("/contact/")
nonce = (re.search(r'name="_fluentform_8_fluentformnonce"\s+value="([^"]*)"', html) or [None, ""])[1]


def build_body():
    """干净的真客户形态请求体（长 notes + 国别/邮箱域一致 + 蜜罐留空 + 无计时字段）。"""
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
    ]
    return urllib.parse.urlencode({
        "action": "fluentform_submit",
        "form_id": "8",
        "data": urllib.parse.urlencode(fields),
    })


# ---------------------------------------------------------------- 2 连发
log("\n=== 2. 连发 %d 次真客户形态提交（阈值 3 / 3600s） ===" % N)
codes = []
t0 = time.time()
for i in range(1, N + 1):
    elapsed = time.time() - t0
    code, resp = curl_post("/wp-admin/admin-ajax.php", build_body())
    codes.append(code)
    log("  第 %d 次 (t+%.1fs): HTTP %s  %s" % (i, elapsed, code, resp[:110].replace("\n", " ")))

log("")
for i, c in enumerate(codes[:3], 1):
    check("第 %d 次放行（200）" % i, c == "200", c)
check("第 4 次被限流（429）", codes[3] == "429", codes[3])

if codes[3] == "429":
    body4 = curl_post("/wp-admin/admin-ajax.php", build_body())[1]
    check("429 响应体含 Too Many Requests",
          "too many requests" in body4.lower(), body4[:120].replace("\n", " "))

# ---------------------------------------------------------------- 3 落库/邮件
log("\n=== 3. 落库与邮件核对（限流未写入第 4 次） ===")
a_sub = int(wp1("SELECT COUNT(*) FROM wp_fluentform_submissions WHERE form_id=8"))
a_fs = int(wp1("SELECT COUNT(*) FROM wp_fsmpt_email_logs"))
log("  submissions: %d -> %d    fsmpt: %d -> %d" % (b_sub, a_sub, b_fs, a_fs))
check("恰好新增 3 行提交（第 4 次被挡）", a_sub == b_sub + 3, "%d -> %d" % (b_sub, a_sub))
check("恰好新增 3 封邮件", a_fs == b_fs + 3, "%d -> %d" % (b_fs, a_fs))

# ---------------------------------------------------------------- 4 清理
if not KEEP:
    log("\n=== 4. 清理测试数据 ===")
    wp("DELETE FROM wp_fluentform_submissions WHERE id > %d" % b_submax)
    wp("DELETE FROM wp_fluentform_entry_details WHERE submission_id > %d" % b_submax)
    wp("DELETE FROM wp_fluentform_submission_meta WHERE response_id > %d" % b_submax)
    wp("DELETE FROM wp_fsmpt_email_logs WHERE id > %d" % b_fsmax)
    wp("DELETE FROM wp_fluentform_logs WHERE parent_source_id=8 AND created_at >= CURDATE()")
    c_sub = int(wp1("SELECT COUNT(*) FROM wp_fluentform_submissions WHERE form_id=8"))
    c_fs = int(wp1("SELECT COUNT(*) FROM wp_fsmpt_email_logs"))
    log("  清理后 submissions=%d (基线 %d)  fsmpt=%d (基线 %d)" % (c_sub, b_sub, c_fs, b_fs))
    check("submissions 回到基线", c_sub == b_sub, "%d vs %d" % (c_sub, b_sub))
    check("邮件日志回到基线", c_fs == b_fs, "%d vs %d" % (c_fs, b_fs))
else:
    log("\n=== 4. --keep：保留数据 ===")

log("\n" + "=" * 52)
if FAILS:
    log("限流 E2E：**FAIL** (%d 项) -> %s" % (len(FAILS), ", ".join(FAILS)))
    sys.exit(1)
log("限流 E2E：**全部通过**")
sys.exit(0)

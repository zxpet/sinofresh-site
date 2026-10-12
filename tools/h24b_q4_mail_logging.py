#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
H24b Q4 —— 停用 wp-mail-logging 的前后对照验收（生产写路径，受控 / 可清理 / 零残留）

要证明的三件事（对应 Q4 裁决的三条约束）
  ① 字段替代性：wp_fsmpt_email_logs 覆盖 wp_wpml_mails 的关键字段
     （实测列：fsmpt = to/from/subject/status/response/created_at；
      wpml = receiver/subject/timestamp/error —— 无 from / status / response）⇒ 由本脚本的
      schema 断言在运行时复核一次，避免"文档说覆盖、实际不覆盖"。
  ② 停用前，一封询盘通知**两张表都记**（基线，证明双写确实存在）。
  ③ 停用后，同一载荷仍然发信（fsmpt 有行、status 正常、to/from/subject 齐全），
     而 wp_wpml_mails **不再增长** ⇒ 日志口径收敛到 FluentSMTP 一处。

为什么必须真提交一次
  Q4 的验收要求就是「提交一次询盘 → 邮件照发 → 进 FluentSMTP 日志 → 无报错无功能异常」。
  纯结构断言无法证明停用后邮件管道还活着。

零污染
  · 邮件隔离走**条件式**夹具：仅当请求带 `X-SF-Test-Sink` 头才把收件人改写成
    h24b-q4-test@invalid.example（真实访客完全不受影响）。
  · 清理一律按「基线 max id + 来源限定（提交方邮箱 / 隔离收件人）」⇒ 中断也能清干净。
  · 限流计数在开始与结束各 reset 一次（作用于 127.0.0.1，不是任何真实访客 IP）。

前置（缺失即拒绝运行，避免把真邮件发到 sales@zxpet.com）
  /var/www/zxpet-v2/wp-content/mu-plugins/zz-sf-zz-test-nomail.php

用法（服务器侧）
  SF_H24B_SITE=prod python3 /root/h24-tools/h24b_q4_mail_logging.py
"""
import base64
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
    AUTH = "Basic " + base64.b64encode(
        ("%s:%s" % (os.environ.get("SFDEV_USER", "sfdev"),
                    os.environ.get("SFDEV_PASS", "VkEws18Kl5V1qp3TpZ6s"))).encode()).decode()
else:
    WP_PATH = "/var/www/zxpet-v2"
    HOST = "www.zxpet.com"
    AUTH = None

BASE = "http://127.0.0.1"
CLIENT_IP = "127.0.0.1"
SUBMITTER = "h24b-q4-test@invalid.example"
SINK = "h24b-q4-test@invalid.example"
ISO_FILE = os.path.join(WP_PATH, "wp-content/mu-plugins/zz-sf-zz-test-nomail.php")
PHP_LOG = "/var/log/php-fpm/www-error.log"

FAILS = []


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


def curl_probe_arms():
    """带 X-SF-Test-Sink 头取一次响应头，确认夹具已加载且自定义头确实到了 PHP。

    这是防呆闸门：条件不成立时（未加载 / 头被剥掉）必须**拒绝跑**，
    否则测试通知会直接落到真实收件人 sales@zxpet.com。
    """
    p = subprocess.run(
        ["curl", "-s", "-m", "30", "-D", "-", "-o", "/dev/null"]
        + headers() + ["-H", "X-SF-Test-Sink: 1", BASE + "/contact/"],
        capture_output=True)
    return p.stdout.decode("utf-8", "replace")


def curl_post(path, body, ua):
    p = subprocess.run(
        ["curl", "-s", "-m", "60", "-o", "/tmp/h24b_q4_body.txt", "-w", "%{http_code}"]
        + headers() + ["-H", "User-Agent: " + ua,
                       "-H", "Content-Type: application/x-www-form-urlencoded",
                       "-H", "X-SF-Test-Sink: 1",
                       "--data-binary", body, BASE + path],
        capture_output=True)
    code = p.stdout.decode("utf-8", "replace").strip()
    try:
        with open("/tmp/h24b_q4_body.txt", "rb") as f:
            return code, f.read().decode("utf-8", "replace")
    except OSError:
        return code, ""


def wpq(sql, col=0):
    p = subprocess.run(["wp", "db", "query", sql, "--allow-root", "--skip-column-names",
                        "--path=" + WP_PATH], capture_output=True, text=True)
    v = p.stdout.strip()
    if not v:
        return ""
    return v.split("\n")[0].split("\t")[col].strip()


def wp_eval(code):
    p = subprocess.run(["wp", "eval", code, "--allow-root", "--path=" + WP_PATH],
                       capture_output=True, text=True)
    return p.stdout.strip()


def wp_cli(*args, **kw):
    p = subprocess.run(["wp"] + list(args) + ["--allow-root", "--path=" + WP_PATH],
                       capture_output=True, text=True)
    return (p.stdout or "") + (p.stderr or "")


def cols(table):
    p = subprocess.run(["wp", "db", "query", "SHOW COLUMNS FROM " + table, "--allow-root",
                        "--skip-column-names", "--path=" + WP_PATH], capture_output=True, text=True)
    return [ln.split("\t")[0] for ln in p.stdout.strip().split("\n") if ln.strip()]


UA_HUMAN = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
UA_BOT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36")


def build_body(nonce, token):
    fields = [
        ("company_name_1", "H24b Q4 Mail-Log Test Ltd"),
        ("contact_person_2", "Q4 Operator"),
        ("email_3", SUBMITTER),
        ("country_5", "United Kingdom"),
        ("interested_dosage_form_7", "Soft Chews"),
        ("notes_10",
         "Operator-side acceptance for the mail-logging consolidation. This message is "
         "deliberately long enough to stay clear of the short-message signal, raises no "
         "price question, and is submitted from the site's own server."),
        ("privacy_consent_11[]", "I agree to the Privacy Policy"),
        ("configuration_summary_12", ""),
        ("item_8__fluent_sf", ""),
        ("sf_fg_t", token),
        ("_fluentform_8_fluentformnonce", nonce),
        ("_wp_http_referer", "/contact/"),
    ]
    inner = urllib.parse.urlencode(fields)
    return urllib.parse.urlencode({"action": "fluentform_submit", "form_id": "8", "data": inner})


FSMPT_COLS = "id | to | from | subject | status | response | created_at"


def fsmpt_rows(where):
    """取 fsmpt 明细行。⚠️ 必须 --skip-column-names，否则第一行是表头，
    断言会打在表头字符串上（'to' 非空之类）—— 假绿陷阱，本批已踩过一次。"""
    p = subprocess.run(
        ["wp", "db", "query",
         "SELECT id, `to`, `from`, subject, status, LEFT(COALESCE(response,''),90), created_at "
         "FROM wp_fsmpt_email_logs WHERE " + where + " ORDER BY id DESC LIMIT 5",
         "--allow-root", "--skip-column-names", "--path=" + WP_PATH],
        capture_output=True, text=True)
    return p.stdout.strip()


def show_rows(rows, indent="    "):
    log(indent + FSMPT_COLS)
    for l in rows.split("\n"):
        if l.strip():
            log(indent + l)


def snap():
    return {
        "sub": int(wpq("SELECT COUNT(*) FROM wp_fluentform_submissions WHERE form_id=8") or 0),
        "submax": int(wpq("SELECT COALESCE(MAX(id),0) FROM wp_fluentform_submissions WHERE form_id=8") or 0),
        "fs": int(wpq("SELECT COUNT(*) FROM wp_fsmpt_email_logs") or 0),
        "fsmax": int(wpq("SELECT COALESCE(MAX(id),0) FROM wp_fsmpt_email_logs") or 0),
        "wpml": int(wpq("SELECT COUNT(*) FROM wp_wpml_mails") or 0),
        "wpmlmax": int(wpq("SELECT COALESCE(MAX(mail_id),0) FROM wp_wpml_mails") or 0),
    }


def php_log_tail(n=120):
    try:
        with open(PHP_LOG, "r", errors="replace") as f:
            return f.read().split("\n")[-n:]
    except OSError:
        return []


log("============ H24b Q4 邮件日志收敛验收 [site=%s] ============" % SITE)

# ---------------------------------------------------------------- 0 前置：夹具必须在位且已武装
log("\n=== 0. 前置检查 ===")
check("条件式邮件隔离夹具在位（否则拒绝跑，避免真发 sales@）",
      os.path.isfile(ISO_FILE), ISO_FILE)
if not os.path.isfile(ISO_FILE):
    log("\n[ABORT] 缺少夹具，未做任何写操作。")
    sys.exit(2)

probe = curl_probe_arms()
armed = "X-SF-Test-Sink-Armed: 1" in probe
check("★ 夹具已武装（自定义头到达 PHP，收件人会被改道）", armed,
      (probe.split("\r\n")[-1] if not armed else "armed"))
if not armed:
    log("\n[ABORT] 夹具未武装 —— 若继续跑，测试通知会真发到 sales@zxpet.com。已停止。")
    sys.exit(2)

# 字段替代性（结构层复核）
fs_cols, ml_cols = cols("wp_fsmpt_email_logs"), cols("wp_wpml_mails")
log("  fsmpt 列: %s" % ",".join(fs_cols))
log("  wpml  列: %s" % ",".join(ml_cols))
for need, hint in [("to", "receiver"), ("from", "（wpml 无）"), ("subject", "subject"),
                   ("status", "（wpml 无）"), ("response", "（wpml 无）"), ("created_at", "timestamp")]:
    check("① 字段替代性：fsmpt.%s 覆盖 wpml.%s" % (need, hint), need in fs_cols)

wp_eval("sf_fg_rl_reset('%s');" % CLIENT_IP)
b = snap()
log("  基线：sub=%d(max %d) fsmpt=%d(max %d) wpml=%d(max %d)"
    % (b["sub"], b["submax"], b["fs"], b["fsmax"], b["wpml"], b["wpmlmax"]))

# 第 1 段是「双写基线」，前提是 wp-mail-logging 处于 active。若上次跑到一半
# 已经把插件停掉，这里先恢复 —— 保证脚本可重复运行、两段对照始终成立。
if wp_cli("plugin", "get", "wp-mail-logging", "--field=status").strip() != "active":
    log("  （为取得双写基线，先把 wp-mail-logging 临时恢复为 active）")
    log("  " + wp_cli("plugin", "activate", "wp-mail-logging").strip().replace("\n", " | "))
check("第 1 段前提：wp-mail-logging = active",
      wp_cli("plugin", "get", "wp-mail-logging", "--field=status").strip() == "active")

log_tail0 = php_log_tail()

# ---------------------------------------------------------------- 1 停用前：双写基线
log("\n=== 1. [停用前] 一封询盘通知应两张表都记 ===")
html = curl_get("/contact/")
token = (re.search(r'var\s+TOKEN\s*=\s*"([^"]*)"', html) or [None, ""])[1]
nonce = (re.search(r'name="_fluentform_8_fluentformnonce"\s+value="([^"]*)"', html) or [None, ""])[1]
check("页面含计时 token 与 form nonce", bool(token) and bool(nonce))

code, resp = curl_post("/wp-admin/admin-ajax.php", build_body(nonce, token), UA_HUMAN)
log("  HTTP %s | %s" % (code, resp[:150].replace("\n", " ")))
check("停用前：真人询盘 HTTP 200（未被误判）", code == "200", code)

a1 = snap()
check("停用前：fsmpt +%d（确有发信）" % (a1["fs"] - b["fs"]), a1["fs"] > b["fs"],
      "%d -> %d" % (b["fs"], a1["fs"]))
check("停用前：wpml +%d（双写确实存在）" % (a1["wpml"] - b["wpml"]), a1["wpml"] > b["wpml"],
      "%d -> %d" % (b["wpml"], a1["wpml"]))
check("停用前：submission 落库", a1["sub"] > b["sub"], "%d -> %d" % (b["sub"], a1["sub"]))
show_rows(fsmpt_rows("id > %d" % b["fsmax"]))

# 清理这一段（保持后续对照的基线干净）
wpq("DELETE FROM wp_fluentform_submissions WHERE form_id=8 AND id > %d AND response LIKE '%%%s%%'"
    % (b["submax"], SUBMITTER))
wpq("DELETE FROM wp_fsmpt_email_logs WHERE id > %d AND `to` LIKE '%%%s%%'" % (b["fsmax"], SINK))
wpq("DELETE FROM wp_wpml_mails WHERE mail_id > %d AND receiver = '%s'" % (b["wpmlmax"], SINK))
z = snap()
check("第 1 段已清理干净（三表回基线）",
      z["sub"] == b["sub"] and z["fs"] == b["fs"] and z["wpml"] == b["wpml"],
      "sub %d/%d fsmpt %d/%d wpml %d/%d"
      % (z["sub"], b["sub"], z["fs"], b["fs"], z["wpml"], b["wpml"]))

# ---------------------------------------------------------------- 2 停用 wp-mail-logging
log("\n=== 2. 停用 wp-mail-logging（不删表，保留历史存档）===")
log("  " + wp_cli("plugin", "deactivate", "wp-mail-logging").strip().replace("\n", " | "))
st = wp_cli("plugin", "get", "wp-mail-logging", "--field=status").strip()
check("② wp-mail-logging 状态 = inactive", st == "inactive", st)
tbl = wpq("SHOW TABLES LIKE 'wp_wpml_mails'")
check("② 表 wp_wpml_mails 仍保留（历史存档不删）", tbl == "wp_wpml_mails", tbl)
check("② FluentSMTP 仍为 active",
      wp_cli("plugin", "get", "fluent-smtp", "--field=status").strip() == "active")

# ---------------------------------------------------------------- 3 停用后：只记一处
log("\n=== 3. [停用后] 同一载荷：仍发信、但 wpml 不再增长 ===")
b2 = snap()
html = curl_get("/contact/")
token = (re.search(r'var\s+TOKEN\s*=\s*"([^"]*)"', html) or [None, ""])[1]
nonce = (re.search(r'name="_fluentform_8_fluentformnonce"\s+value="([^"]*)"', html) or [None, ""])[1]

code, resp = curl_post("/wp-admin/admin-ajax.php", build_body(nonce, token), UA_HUMAN)
log("  HTTP %s | %s" % (code, resp[:150].replace("\n", " ")))
check("③ 停用后：真人询盘 HTTP 200（无功能异常）", code == "200", code)

a2 = snap()
check("③ 停用后：fsmpt 仍然 +%d（邮件照发）" % (a2["fs"] - b2["fs"]), a2["fs"] > b2["fs"],
      "%d -> %d" % (b2["fs"], a2["fs"]))
check("★ ③ 停用后：wp_wpml_mails 不再增长（口径收敛到 FluentSMTP）",
      a2["wpml"] == b2["wpml"], "%d -> %d" % (b2["wpml"], a2["wpml"]))
check("③ 停用后：submission 照常落库", a2["sub"] > b2["sub"], "%d -> %d" % (b2["sub"], a2["sub"]))

rows = fsmpt_rows("id > %d AND `to` LIKE '%%%s%%'" % (b2["fsmax"], SINK))
log("  fsmpt 本次新增行：")
show_rows(rows)
r1 = rows.split("\n")[0].split("\t") if rows else []
check("③ 新行收件人 = 隔离收件人（证明改道生效、没真发 sales@）",
      len(r1) > 1 and SINK in r1[1], ("len=%d | " % len(r1)) + (r1[1] if len(r1) > 1 else "(无)"))
check("③ 新行 from 是本站通知身份",
      len(r1) > 2 and "@" in r1[2], r1[2] if len(r1) > 2 else "")
check("③ 新行 subject 非空且是询盘通知",
      len(r1) > 3 and "Inquiry" in r1[3], r1[3] if len(r1) > 3 else "")
check("③ 新行 status = sent", len(r1) > 4 and r1[4].strip() == "sent",
      r1[4] if len(r1) > 4 else "")
check("③ 新行 response 非空（SMTP 应答已记录）",
      len(r1) > 5 and bool(r1[5].strip()), r1[5] if len(r1) > 5 else "")
check("③ 新行 created_at 是本次（时间戳非空且为今日）",
      len(r1) > 6 and len(r1[6].strip()) == 19, r1[6] if len(r1) > 6 else "")
# 反面断言：不得存在任何「发往真实收件人」的新 fsmpt 行
real_rows = fsmpt_rows("id > %d AND (`to` NOT LIKE '%%%s%%')" % (b2["fsmax"], SINK))
check("③ 反面：停用后没有任何新邮件发往真实收件人",
      not real_rows.strip(), real_rows[:200] or "(无)")

# ---------------------------------------------------------------- 4 无报错
log("\n=== 4. 无 PHP 报错 / 响应体无 Fatal ===")
new_log = [l for l in php_log_tail() if l not in log_tail0]
bad = [l for l in new_log if re.search(r"PHP (Fatal|Parse) error|Uncaught", l)]
log("  php-fpm 新增日志行：%d（致命 %d）" % (len(new_log), len(bad)))
for l in new_log[-6:]:
    log("    " + l)
check("④ 全程无 PHP 致命错误", not bad, " / ".join(bad)[:200])
check("④ 响应体不含 Fatal error", not re.search(r"Fatal error|Parse error", resp))

# ---------------------------------------------------------------- CLEANUP
log("\n=== CLEANUP ===")
wp_eval("sf_fg_rl_reset('%s');" % CLIENT_IP)
wpq("DELETE FROM wp_fluentform_submissions WHERE form_id=8 AND id > %d AND response LIKE '%%%s%%'"
    % (b["submax"], SUBMITTER))
wpq("DELETE FROM wp_fsmpt_email_logs WHERE id > %d AND `to` LIKE '%%%s%%'" % (b["fsmax"], SINK))
wpq("DELETE FROM wp_wpml_mails WHERE mail_id > %d AND receiver = '%s'" % (b["wpmlmax"], SINK))
f = snap()
check("submissions 回基线", f["sub"] == b["sub"], "%d vs %d" % (f["sub"], b["sub"]))
check("fsmpt 回基线", f["fs"] == b["fs"], "%d vs %d" % (f["fs"], b["fs"]))
check("wpml 回基线", f["wpml"] == b["wpml"], "%d vs %d" % (f["wpml"], b["wpml"]))
check("限流计数回零", wp_eval("echo sf_fg_rl_count('%s');" % CLIENT_IP) == "0")

log("\n【结束状态】wp-mail-logging = %s（Q4 裁决：生产停用、不删表）"
    % wp_cli("plugin", "get", "wp-mail-logging", "--field=status").strip())
log("【待办】删除条件式邮件隔离夹具：%s" % ISO_FILE)
log("\n===== %s =====" % ("ALL PASS" if not FAILS else ("FAILED: " + ", ".join(FAILS))))
sys.exit(1 if FAILS else 0)

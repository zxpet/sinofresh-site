#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
H24 写路径验收（L4）—— dev / prod 通用，受控、可清理、零残留

为什么需要这一层：
  L3 只验证了评分函数。要证明"真能拦、拦了真不发信、真人真能收到通知"，
  必须走一次真实的 HTTP 提交链。生产环境不能留痕，所以本脚本：
    1) 跑之前必须已装好邮件隔离 mu-plugin（否则拒绝运行）
    2) 用**基线 max id 快照**做清理（不是记具体 id），中断也能清干净
    3) 结尾断言所有表回到基线

前置（生产）：
  cat > /var/www/zxpet-v2/wp-content/mu-plugins/zz-sf-zz-test-nomail.php <<'PHP'
  <?php
  add_filter('wp_mail', function ($a) { $a['to'] = 'h24-test@invalid.example'; return $a; }, 99);
  PHP

用法（服务器侧）：
  SF_H24_SITE=prod python3 /root/h24-tools/h24_prod_l4.py
  SF_H24_SITE=prod python3 /root/h24-tools/h24_prod_l4.py --keep
"""
import base64
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse

SITE = os.environ.get("SF_H24_SITE", "prod")
if SITE == "dev":
    WP_PATH = "/var/www/dev.zxpet.com/public"
    HOST = "dev.zxpet.com"
    # dev Basic 凭据：环境变量优先（SFDEV_USER / SFDEV_PASS），回退到项目内部已知值。
    AUTH = "Basic " + base64.b64encode(
        ("%s:%s" % (os.environ.get("SFDEV_USER", "sfdev"),
                    os.environ.get("SFDEV_PASS", "VkEws18Kl5V1qp3TpZ6s"))).encode()).decode()
else:
    WP_PATH = "/var/www/zxpet-v2"
    HOST = "www.zxpet.com"
    AUTH = None

BASE = "http://127.0.0.1"
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
    p = subprocess.run(["curl", "-s", "-m", "60"] + headers() + [BASE + path],
                       capture_output=True)
    return p.stdout.decode("utf-8", "replace")


def curl_post(path, body, ua=UA_HUMAN):
    p = subprocess.run(
        ["curl", "-s", "-m", "60", "-o", "/tmp/h24_l4_body.txt", "-w", "%{http_code}"]
        + headers() + ["-H", "User-Agent: " + ua,
                       "-H", "X-SF-H24-Test: 1",     # 触发条件式邮件隔离
                       "-H", "Content-Type: application/x-www-form-urlencoded",
                       "--data-binary", body, BASE + path],
        capture_output=True)
    code = p.stdout.decode("utf-8", "replace").strip()
    try:
        with open("/tmp/h24_l4_body.txt", "rb") as f:
            return code, f.read().decode("utf-8", "replace")
    except OSError:
        return code, ""


def wp(sql):
    p = subprocess.run(["wp", "db", "query", sql, "--allow-root", "--skip-column-names",
                        "--path=" + WP_PATH], capture_output=True, text=True)
    return p.stdout.strip()


def wp1(sql):
    v = wp(sql)
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
            # 机器人不带 sf_fg_t
            ("_fluentform_8_fluentformnonce", nonce),
            ("_wp_http_referer", "/contact/"),
        ]
    else:
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
            ("item_8__fluent_sf", ""),
            ("sf_fg_t", token),
            ("_fluentform_8_fluentformnonce", nonce),
            ("_wp_http_referer", "/contact/"),
        ]
    inner = urllib.parse.urlencode(fields)
    return urllib.parse.urlencode({"action": "fluentform_submit", "form_id": "8", "data": inner})


log("==================== H24 L4 写路径验收 [site=%s] ====================" % SITE)

# ---------------------------------------------------------------- 前置：邮件隔离必须已装
iso_file = os.path.join(WP_PATH, "wp-content/mu-plugins/zz-sf-zz-test-nomail.php")
if not os.path.exists(iso_file):
    log("[ABORT] 邮件隔离 mu-plugin 不存在：%s" % iso_file)
    log("        生产上直接跑会向真实邮箱发信，拒绝执行。")
    sys.exit(2)
log("邮件隔离：已装 (%s)" % iso_file)

# ---------------------------------------------------------------- 0 基线
log("\n=== 0. 基线快照 ===")
b_sub = int(wp1("SELECT COUNT(*) FROM wp_fluentform_submissions WHERE form_id=8"))
b_submax = int(wp1("SELECT COALESCE(MAX(id),0) FROM wp_fluentform_submissions WHERE form_id=8"))
b_fs = int(wp1("SELECT COUNT(*) FROM wp_fsmpt_email_logs"))
b_fsmax = int(wp1("SELECT COALESCE(MAX(id),0) FROM wp_fsmpt_email_logs"))
b_spam = int(wp1("SELECT COUNT(*) FROM wp_sf_form_spam_log"))
b_spammax = int(wp1("SELECT COALESCE(MAX(id),0) FROM wp_sf_form_spam_log"))
b_fflogmax = int(wp1("SELECT COALESCE(MAX(id),0) FROM wp_fluentform_logs"))
b_mail = int(wp1("SELECT COUNT(*) FROM wp_wpml_mails"))
b_mailmax = int(wp1("SELECT COALESCE(MAX(mail_id),0) FROM wp_wpml_mails"))
# wp-mail-logging 在生产是 active、在 dev 是 inactive —— 断言必须据此自适应
p = subprocess.run(["wp", "plugin", "is-active", "wp-mail-logging", "--allow-root",
                    "--path=" + WP_PATH], capture_output=True, text=True)
MAIL_LOG_ACTIVE = (p.returncode == 0)
log("  submissions(form8)=%d (max id %d)" % (b_sub, b_submax))
log("  fsmpt_email_logs=%d (max id %d)   [FluentSMTP 邮件日志]" % (b_fs, b_fsmax))
log("  spam_log=%d (max id %d)" % (b_spam, b_spammax))
log("  fluentform_logs max id=%d        [FF 集成日志]" % b_fflogmax)
log("  wp_wpml_mails=%d (max mail_id %d)  [wp-mail-logging %s]"
    % (b_mail, b_mailmax, "ACTIVE→应同步增长" if MAIL_LOG_ACTIVE else "inactive→应不动"))

# ---------------------------------------------------------------- 1 抓页面
log("\n=== 1. GET /contact/ 取 nonce 与签名计时 token ===")
html = curl_get("/contact/")
m_tok = re.search(r'var\s+TOKEN\s*=\s*"([^"]*)"', html)
m_non = re.search(r'name="_fluentform_8_fluentformnonce"\s+value="([^"]*)"', html)
token = m_tok.group(1) if m_tok else ""
nonce = m_non.group(1) if m_non else ""
log("  页面 %d 字节  token=%s  nonce=%s"
    % (len(html), (token[:20] + "...") if token else "(NONE)", nonce or "(NONE)"))
check("页面含签名计时 token", bool(token))
check("页面含 form nonce", bool(nonce))
check("页面含蜜罐字段", "item_8__fluent_sf" in html)

new_subs = []
new_spam = []

try:
    # ---------------------------------------------------------------- 2 机器人路径
    log("\n=== 2. 机器人路径（反向用例：应被拦、不入库、不发信） ===")
    code, resp = curl_post("/wp-admin/admin-ajax.php", build_body(nonce, token, bot=True), UA_BOT)
    log("  HTTP %s | body: %s" % (code, resp[:220].replace("\n", " ")))
    check("HTTP 200（伪装成功，不给机器人反馈）", code == "200", code)
    try:
        jd = json.loads(resp)
        ok_json = bool(jd.get("success"))
    except Exception:
        jd, ok_json = {}, False
    check("响应 success=true", ok_json, str(jd)[:160])
    low = resp.lower()
    check("响应不泄露拦截语义",
          not any(w in low for w in ("spam", "block", "reject", "forbidden")),
          resp[:120])

    a_sub = int(wp1("SELECT COUNT(*) FROM wp_fluentform_submissions WHERE form_id=8"))
    check("被拦提交以 status=spam 落库（用户要求：直接落库标 spam）",
          a_sub == b_sub + 1, "%d -> %d" % (b_sub, a_sub))
    srow = wp1("SELECT CONCAT(id,'|',status,'|',ip) FROM wp_fluentform_submissions "
               "WHERE form_id=8 ORDER BY id DESC LIMIT 1")
    log("  机器人落库行 id|status|ip = %s" % srow)
    check("机器人落库行 status=spam", srow.split("|")[1:2] == ["spam"], srow)

    a_fs = int(wp1("SELECT COUNT(*) FROM wp_fsmpt_email_logs"))
    check("被拦提交零发信（FluentSMTP 表）", a_fs == b_fs, "%d -> %d" % (b_fs, a_fs))
    a_mail = int(wp1("SELECT COUNT(*) FROM wp_wpml_mails"))
    check("被拦提交零发信（wp-mail-logging 表）", a_mail == b_mail, "%d -> %d" % (b_mail, a_mail))
    a_fflogmax = int(wp1("SELECT COALESCE(MAX(id),0) FROM wp_fluentform_logs"))
    check("FF 集成日志零新增（被拦不触发通知链）",
          a_fflogmax == b_fflogmax, "max id %d -> %d" % (b_fflogmax, a_fflogmax))

    a_spam = int(wp1("SELECT COUNT(*) FROM wp_sf_form_spam_log"))
    check("审计表 +1", a_spam == b_spam + 1, "%d -> %d" % (b_spam, a_spam))

    row = wp1("SELECT CONCAT_WS('|', score, signals, source, ip, ua, country, email_domain) "
              "FROM wp_sf_form_spam_log ORDER BY id DESC LIMIT 1")
    log("  审计行: %s" % row)
    parts = row.split("|")
    if len(parts) >= 7:
        check("审计 score >= 阈值(4)", int(parts[0]) >= 4, parts[0])
        check("审计含 S1_shared_suffix", "S1_shared_suffix" in parts[1], parts[1])
        check("审计 source=score", parts[2] == "score", parts[2])
        check("审计记录了 ua", len(parts[4]) > 20, "%d 字节" % len(parts[4]))
        check("审计记录了 country/email_domain", parts[5] != "" or parts[6] != "",
              "%s / %s" % (parts[5], parts[6]))
    new_spam.append(row)

    # ---------------------------------------------------------------- 3 真人路径
    log("\n=== 3. 真人路径（正向用例：应入库、应通知、不应被拦） ===")
    log("  等待 5 秒（模拟真人填表，避开 S6 过快信号）")
    time.sleep(5)
    html2 = curl_get("/contact/")
    m2 = re.search(r'var\s+TOKEN\s*=\s*"([^"]*)"', html2)
    m2n = re.search(r'name="_fluentform_8_fluentformnonce"\s+value="([^"]*)"', html2)
    tok2 = m2.group(1) if m2 else token
    non2 = m2n.group(1) if m2n else nonce

    code, resp = curl_post("/wp-admin/admin-ajax.php", build_body(non2, tok2, bot=False))
    log("  HTTP %s | body: %s" % (code, resp[:220].replace("\n", " ")))
    check("HTTP 200", code == "200", code)
    try:
        jd = json.loads(resp)
        ok_json = bool(jd.get("success"))
    except Exception:
        jd, ok_json = {}, False
    check("响应 success=true", ok_json, str(jd)[:160])

    a_sub = int(wp1("SELECT COUNT(*) FROM wp_fluentform_submissions WHERE form_id=8"))
    check("真人提交入库（累计 +2：机器 1 + 真人 1）",
          a_sub == b_sub + 2, "%d -> %d" % (b_sub, a_sub))
    last = wp1("SELECT CONCAT(id,'|',status,'|',ip) FROM wp_fluentform_submissions "
               "WHERE form_id=8 ORDER BY id DESC LIMIT 1")
    log("  新行 id|status|ip = %s" % last)
    check("新行 status=unread（未被判 spam）", last.split("|")[1:2] == ["unread"], last)
    check("新行 ip 来自 loopback（供清理精准定位）",
          "127.0.0.1" in last or last.rstrip().endswith("|::1"), last)

    a_fs = int(wp1("SELECT COUNT(*) FROM wp_fsmpt_email_logs"))
    delta = a_fs - b_fs
    log("  邮件 %d -> %d (delta=%d)" % (b_fs, a_fs, delta))
    check("恰好 1 封邮件（仅管理员通知）", delta == 1, "delta=%d" % delta)
    if delta > 0:
        subj = wp("SELECT GROUP_CONCAT(subject SEPARATOR ' || ') FROM wp_fsmpt_email_logs "
                  "WHERE id > %d" % b_fsmax)
        log("  主题: %s" % subj[:180])
        check("不含自动回复", "We've received your inquiry" not in subj, subj[:100])
        check("含管理员通知 'New Inquiry:'", "New Inquiry:" in subj, subj[:100])
        iso = wp1("SELECT COUNT(*) FROM wp_fsmpt_email_logs WHERE id > %d "
                  "AND `to` LIKE '%%h24-test@invalid.example%%'" % b_fsmax)
        check("收件人已被隔离改写（未触达真实邮箱）", iso == str(delta), "%s of %d" % (iso, delta))
        sent = wp1("SELECT COUNT(*) FROM wp_fsmpt_email_logs WHERE id > %d AND status='sent'"
                   % b_fsmax)
        check("新增邮件 status=sent", sent == str(delta), "%s of %d" % (sent, delta))

    a_spam = int(wp1("SELECT COUNT(*) FROM wp_sf_form_spam_log"))
    check("真人提交未新增审计行（应仍只有机器人那条）",
          a_spam == b_spam + 1, "%d（应仍为 %d）" % (a_spam, b_spam + 1))

    a_mail = int(wp1("SELECT COUNT(*) FROM wp_wpml_mails"))
    if MAIL_LOG_ACTIVE:
        check("wp-mail-logging 表同步 +1（该插件在生产为 active）",
              a_mail == b_mail + 1, "%d -> %d" % (b_mail, a_mail))
    else:
        check("wp-mail-logging 表保持不动（该插件未启用）",
              a_mail == b_mail, "%d -> %d" % (b_mail, a_mail))

    # ---------------------------------------------------------------- 4 限流
    log("\n=== 4. 限流（同一 IP 窗口内连续提交，期望第 4 次起 429） ===")
    th = wp_eval("echo apply_filters('fluentform/max_submission_count',5,8).'|'."
                 "apply_filters('fluentform/min_submission_interval',30,8);")
    mx, iv = (th.split("|") + ["", ""])[:2]
    log("  生效阈值 = %s 次 / %s 秒" % (mx, iv))
    check("阈值被收紧为 3/3600", th == "3|3600", th)

    cur = int(wp1("SELECT COUNT(*) FROM wp_fluentform_submissions WHERE form_id=8 "
                  "AND status <> 'trashed' AND ip LIKE '%%127.0.0.1%%' "
                  "AND created_at >= NOW() - INTERVAL %s SECOND" % (iv or "3600")))
    log("  当前窗口内同 IP 计数 = %d" % cur)

    passed, got429 = 0, False
    for i in range(1, 9):
        html3 = curl_get("/contact/")
        t3 = (re.search(r'var\s+TOKEN\s*=\s*"([^"]*)"', html3) or [None, token])[1]
        n3 = (re.search(r'name="_fluentform_8_fluentformnonce"\s+value="([^"]*)"', html3) or [None, nonce])[1]
        code, resp = curl_post("/wp-admin/admin-ajax.php", build_body(n3, t3, bot=False))
        log("    #%d -> HTTP %s | %s" % (i, code, resp[:110].replace("\n", " ")))
        if code == "429" or "Too Many Requests" in resp:
            got429 = True
            break
        if code == "200":
            passed += 1
    check("出现 429 限流", got429, "通过 %d 次后" % passed)
    check("通过的次数 = 阈值 - 已有计数",
          passed == max(0, int(mx or 0) - cur),
          "passed=%d, 阈值=%s, 已有=%d" % (passed, mx, cur))

finally:
    # ---------------------------------------------------------------- 5 清理（精准：只删本次测试自身的痕迹）
    if KEEP:
        log("\n=== 5. --keep：保留测试数据（跳过清理） ===")
    else:
        log("\n=== 5. 清理测试数据（按 IP=127.0.0.1 + 隔离收件人精准定位） ===")
        # 只删来自 loopback 的测试提交，绝不触碰测试窗口内真实访客的数据
        ids = wp("SELECT id FROM wp_fluentform_submissions WHERE form_id=8 AND id > %d "
                 "AND ip LIKE '%%127.0.0.1%%'" % b_submax)
        idlist = [x.strip() for x in ids.split("\n") if x.strip().isdigit()]
        if idlist:
            in_sql = ",".join(idlist)
            wp("DELETE FROM wp_fluentform_entry_details WHERE submission_id IN (%s)" % in_sql)
            wp("DELETE FROM wp_fluentform_submission_meta WHERE response_id IN (%s)" % in_sql)
            wp("DELETE FROM wp_fluentform_submissions WHERE id IN (%s)" % in_sql)
        log("  删除测试提交 %d 条: %s" % (len(idlist), ",".join(idlist) or "(无)"))

        # 邮件：只删收件人是隔离地址的（两张邮件日志表都要清）
        wp("DELETE FROM wp_fsmpt_email_logs WHERE id > %d "
           "AND `to` LIKE '%%h24-test@invalid.example%%'" % b_fsmax)
        wp("DELETE FROM wp_wpml_mails WHERE mail_id > %d "
           "AND receiver = 'h24-test@invalid.example'" % b_mailmax)
        # 审计表：只删 loopback 来源
        wp("DELETE FROM wp_sf_form_spam_log WHERE id > %d "
           "AND ip LIKE '%%127.0.0.1%%'" % b_spammax)

        c_sub = int(wp1("SELECT COUNT(*) FROM wp_fluentform_submissions WHERE form_id=8"))
        c_fs = int(wp1("SELECT COUNT(*) FROM wp_fsmpt_email_logs"))
        c_spam = int(wp1("SELECT COUNT(*) FROM wp_sf_form_spam_log"))
        c_mail = int(wp1("SELECT COUNT(*) FROM wp_wpml_mails"))
        log("  submissions %d -> %d (基线 %d)" % (b_sub, c_sub, b_sub))
        log("  fsmpt_logs  %d -> %d (基线 %d)" % (b_fs, c_fs, b_fs))
        log("  spam_log    %d -> %d (基线 %d)" % (b_spam, c_spam, b_spam))
        log("  wpml_mails  %d -> %d (基线 %d)" % (b_mail, c_mail, b_mail))
        check("submissions 回到基线", c_sub == b_sub, "%d vs %d" % (c_sub, b_sub))
        check("邮件日志(fsmpt) 回到基线", c_fs == b_fs, "%d vs %d" % (c_fs, b_fs))
        check("审计表回到基线", c_spam == b_spam, "%d vs %d" % (c_spam, b_spam))
        check("邮件日志(wpml) 回到基线", c_mail == b_mail, "%d vs %d" % (c_mail, b_mail))

log("\n" + "=" * 56)
if FAILS:
    log("L4 写路径验收 [%s]：**FAIL** (%d 项) -> %s" % (SITE, len(FAILS), ", ".join(FAILS)))
    sys.exit(1)
log("L4 写路径验收 [%s]：**全部通过**" % SITE)
sys.exit(0)

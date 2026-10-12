#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H24 gate — 表单机器人防护（真实 IP + 评分式拦截 + 零发信 + 审计 + 告警）。

本批给生产站装上两枚 mu-plugin：
  server/mu-plugins/zz-sf-aa-real-ip.php   统一真实 IP（只在 CF 边缘直连时才采信 CF-Connecting-IP）
  server/mu-plugins/zz-sf-form-guard.php   评分式内容规则 + 拦截落库标 spam + 审计表 + 告警 + 后台复核

本 gate 钉死的契约（每一条都对应一处「naive 实现会做错」的地方）：

  G1  不写死机器人字样。规则必须由**结构信号**组合而成；源码里出现 'RobertTon' /
      'TonGM' 这类具体值即判失败（用户的明确要求：模式化，不硬编码）。
  G2  被拦的提交**一封信都不发**。拦截路径必须早于 Fluent Forms 的处理器（优先级 < 10），
      且该路径内不得出现 wp_mail —— 这是「即使防护被绕过也不会塞满邮箱」的落点。
  G3  真客户不受影响。同一套代码下，真人形态必须放行、入库 status=unread、恰好 1 封管理员通知。
      G2 与 G3 互为负对照：只满足其中一条的实现是残的。
  G4  陈旧 UA（S4）只记录、不计分。老旧的办公电脑是真实存在的，单凭 UA 判垃圾会误伤。
  G5  Turnstile 是增强层不是门槛：脚本加载失败 / 未带 token 一律 0 分，只有
      带着 token 却被判 fail 才给 4 分。用户的底线是「不能变成客户填不了表」。
  G6  真实 IP 只在直连方属于 Cloudflare 官方网段时才采信转发头；否则一律不动（防直连伪造）。
      限流阈值随之前置条件收紧：真实 IP 不可信时退回插件默认，绝不按边缘 IP 收紧（那会先挡真客户）。
  G7  告警有频率控制：当天 >= 阈值发一封，一天最多一封（先落标记再发信，防并发重复）。

Modes
  --source            对 server/mu-plugins/ 的静态断言（含上面全部结构契约）
  --live              对 dev 树的行为断言（通过 ssh 驱动服务器上已交付的 E2E 脚本）
  --source --root DIR 对指定目录跑 source 断言（供负对照使用）

负对照
  1. `git worktree add --detach <tmp> HEAD` 后 `--source --root <tmp>`：HEAD 里没有
     zz-sf-form-guard.php，G1/G2/G4… 应**集体转红**。全绿说明 gate 没在看东西。
  2. --live 里 G2 与 G3 互为正反例：机器人形态零发信 + 真人形态一封通知，缺一不成。
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MU = REPO / "server" / "mu-plugins"
REAL_IP = "zz-sf-aa-real-ip.php"
FORM_GUARD = "zz-sf-form-guard.php"

SERVER = "root@65.49.215.152"
DEV_ROOT = "/var/www/dev.zxpet.com/public"
TOOLS = "/root/h24-tools"

PASS, FAIL = 0, 0


def check(name, ok, detail=""):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"[PASS] {name}")
    else:
        FAIL += 1
        print(f"[FAIL] {name}" + (f" — {detail}" if detail else ""))


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def code_lines(text: str) -> str:
    """剥离注释后的源码。

    本文件的文档块每行以 ' * ' 开头，注释行以 '//' / '/*' 开头；逐行跳过即可。
    之所以不能直接正则删 /* */，是因为文件里含 'https://…' 这类带 // 的字面量。
    """
    out, in_block = [], False
    for ln in text.split("\n"):
        s = ln.strip()
        if in_block:
            if "*/" in s:
                in_block = False
            continue
        if s.startswith("/*"):
            if "*/" not in s:
                in_block = True
            continue
        if s.startswith("//") or s.startswith("*"):
            continue
        out.append(ln)
    return "\n".join(out)


def sh(args, timeout=180):
    p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def ssh(cmd, timeout=300):
    return sh(["ssh", "-o", "ConnectTimeout=20", SERVER, cmd], timeout=timeout)


# ==========================================================================
# --source
# ==========================================================================
def source_gate(root: Path):
    real_ip = root / REAL_IP
    guard = root / FORM_GUARD

    # --- 存在性 ---------------------------------------------------------
    check("H24: 真实 IP 层文件存在", real_ip.is_file(), str(real_ip))
    check("H24: 表单防护文件存在", guard.is_file(), str(guard))
    if not (real_ip.is_file() and guard.is_file()):
        return

    ri = read(real_ip)
    fg = read(guard)
    ri_code = code_lines(ri)
    fg_code = code_lines(fg)

    # --- G1 不写死机器人字样（只看代码，注释里的举例不算） ----------------
    bad_literals = ["RobertTon", "TonGM", "CarlosNep", "Samuelmus", "DavidBon"]
    hits = [b for b in bad_literals if b in fg_code or b in ri_code]
    check("G1: 代码里不含任何具体机器人字样（模式化，不硬编码）",
          not hits, "命中: " + ", ".join(hits))

    # 结构信号必须存在（否则只是「没写死」而什么都没做）
    for fn in ("sf_fg_signal_shared_fragment", "sf_fg_signal_template_message",
               "sf_fg_signal_short_message", "sf_fg_signal_country_mismatch",
               "sf_fg_signal_disposable_email", "sf_fg_signal_too_fast"):
        check(f"G1: 结构信号 {fn}() 存在", f"function {fn}(" in fg)

    # 同后缀判定必须分档（3/1/0），不是布尔
    m = re.search(r"function sf_fg_signal_shared_fragment\((.*?)\n\}", fg, re.S)
    ok_scale = bool(m) and len(re.findall(r"return\s+\d", m.group(1))) >= 2
    check("G1: 同后缀信号返回分档值（非布尔）", ok_scale)
    # 通用词豁免必须存在（家族企业 Nordic Pet AB / Anna Nordic 不能误伤）
    check("G1: 存在通用词豁免表 sf_fg_generic_words()", "function sf_fg_generic_words(" in fg)

    # --- G2 拦截路径零发信 -------------------------------------------------
    check("G2: 拦截钩子挂 nopriv 且优先级 5（早于插件默认 10）",
          bool(re.search(r"add_action\(\s*'wp_ajax_nopriv_fluentform_submit'\s*,\s*'sf_fg_intercept'\s*,\s*5", fg)))
    check("G2: 拦截钩子同样挂已登录分支",
          bool(re.search(r"add_action\(\s*'wp_ajax_fluentform_submit'\s*,\s*'sf_fg_intercept'\s*,\s*5", fg)))

    # intercept 函数体内不得出现 wp_mail / notify
    m = re.search(r"function sf_fg_intercept\(\)\s*\{(.*?)\n\}", fg, re.S)
    body = m.group(1) if m else ""
    check("G2: sf_fg_intercept() 内不含 wp_mail", body and "wp_mail" not in body)
    check("G2: sf_fg_intercept() 内不含邮件通知调用",
          body and ("notify" not in body and "Notification" not in body))

    # store_spam 也必须是纯落库
    m = re.search(r"function sf_fg_store_spam\(.*?\)\s*\{(.*?)\n\}", fg, re.S)
    sbody = m.group(1) if m else ""
    check("G2: sf_fg_store_spam() 内不含 wp_mail", sbody and "wp_mail" not in sbody)

    # 拦截后必须直接给出「通用成功」响应并终止，不再落回插件
    check("G2: 拦截后返回通用成功响应（对外无感）",
          "wp_send_json_success" in body and "sf_fg_success_message" in fg)
    check("G2: 成功文案不出现 spam/block 字样",
          not re.search(r"success_message[^\n]*\b(spam|block|reject)", fg, re.I))

    # --- G3 真人放行（结构侧：未命中必须 return 交回插件） -------------------
    check("G3: 未达阈值时 return（交回 Fluent Forms）",
          bool(re.search(r"if\s*\(\s*''\s*===\s*\$hit\s*&&\s*\$score\['score'\]\s*<\s*\$threshold\s*\)\s*\{\s*return;", fg)))

    # --- G4 陈旧 UA 只记录不计分 -------------------------------------------
    check("G4: 存在 S4_note_stale_ua 记录点", "S4_note_stale_ua" in fg)
    # 精确取出该 if 块，断言块内不含任何加分
    m = re.search(r"if\s*\(\s*sf_fg_signal_stale_ua\([^)]*\)\s*\)\s*\{(.*?)\}", fg, re.S)
    blk = m.group(1) if m else ""
    check("G4: S4 的 if 块取出成功", bool(m), "未匹配到 sf_fg_signal_stale_ua 的 if 块")
    check("G4: S4 的 if 块内不含 $score（只记录不计分）",
          bool(blk) and "$score" not in blk, blk.strip()[:80])
    # 且 docblock 明示永不参与成案
    check("G4: 源码注明 S4 不参与成案", "S4" in fg and ("不计分" in fg or "不参与成案" in fg))

    # --- G5 Turnstile 只作信号 ---------------------------------------------
    m = re.search(r"function sf_fg_signal_turnstile\([^)]*\)\s*\{(.*?)\n\}", fg, re.S)
    tbody = m.group(1) if m else ""
    check("G5: sf_fg_signal_turnstile() 存在", bool(m), "未匹配到函数体")
    # 唯一给分的写法：'fail' === $state ? 4 : 0
    check("G5: 仅 'fail' 命中时给 4 分（三元形态）",
          "=== $state" in tbody and "? 4 : 0" in tbody, tbody.strip()[:80])
    check("G5: 除 'fail' 外一律 0 分（无可达的其它 return）",
          tbody.count("return") == 1, "return 次数=%d" % tbody.count("return"))
    check("G5: 前端脚本 onerror 静默（降级不报错、不阻塞）",
          "script.onerror" in fg and "什么都不做" in fg)
    check("G5: 状态机 sf_fg_ts_state() 覆盖 disabled/absent/ok/fail/degraded 五态",
          all(s in fg for s in ("'disabled'", "'absent'", "'ok'", "'fail'", "'degraded'")))
    check("G5: 官方降级点 fluentform/disable_captcha 已挂", "fluentform/disable_captcha" in fg)
    check("G5: 我方 Turnstile 不注册 FF 原生字段（避免 422 硬拒）",
          "fluentform/render_turnstile" not in fg)

    # --- G6 真实 IP 采信前置条件 -------------------------------------------
    check("G6: 存在 CF 网段表 sf_real_ip_cf_ranges()", "function sf_real_ip_cf_ranges(" in ri)
    check("G6: 存在直连方判定 sf_real_ip_is_cloudflare()", "function sf_real_ip_is_cloudflare(" in ri)
    m = re.search(r"function sf_real_ip_resolve\((.*?)\n\}", ri, re.S)
    rbody = m.group(1) if m else ""
    check("G6: resolve() 返回三态 source（cf/direct/invalid）",
          "'cf'" in rbody and "'direct'" in rbody and "'invalid'" in rbody)
    check("G6: 仅在直连方是 CF 时才读转发头",
          "is_cloudflare" in rbody and ("CF-Connecting-IP" in ri or "HTTP_CF_CONNECTING_IP" in ri))
    # 限流阈值必须**门槛式**返回（不可信即退回插件默认）
    m = re.search(r"function sf_fg_filter_max_submissions\((.*?)\n\}", fg, re.S)
    fbody = m.group(1) if m else ""
    check("G6: 限流 filter 前置检查真实 IP 就绪",
          "sf_fg_real_ip_ready()" in fbody and "return $max" in fbody)
    check("G6: 就绪时才收紧（SF_FG_MAX_SUBMISSIONS）", "SF_FG_MAX_SUBMISSIONS" in fbody)

    # --- G7 告警频率控制 ----------------------------------------------------
    m = re.search(r"function sf_fg_alert_tick\((.*?)\n\}", fg, re.S)
    abody = m.group(1) if m else ""
    check("G7: 存在告警阈值常量", "SF_FG_ALERT_THRESHOLD" in fg)
    check("G7: 告警按天去重（先落标记再发信）",
          "sent" in abody and abody.find("update_option") != -1
          and (abody.find("update_option") < abody.find("sf_fg_send_alert") if "sf_fg_send_alert" in abody else False))

    # --- 审计表 / 后台复核 --------------------------------------------------
    check("H24: 审计表名单独一张（sf_form_spam_log）", "sf_form_spam_log" in fg)
    check("H24: 审计表用 dbDelta 建（可迁移）", "dbDelta" in fg)
    check("H24: 审计行含 IP/UA/时间/签名",
          all(k in fg for k in ("'ip'", "'ua'", "'created_at'", "'signature'")))
    check("H24: 后台复核页存在", "add_menu_page" in fg and "sf-form-guard" in fg)
    check("H24: 后台动作校验 nonce", "wp_verify_nonce" in fg or "check_admin_referer" in fg)
    check("H24: 后台动作校验 manage_options", "manage_options" in fg)
    check("H24: 支持「改回正常」（release）", "sf_fg_release_row" in fg)
    check("H24: 支持「一键加黑名单」", "sf_fg_blocklist_add" in fg)

    # --- 加载顺序 ----------------------------------------------------------
    check("H24: 真实 IP 层文件名以 zz-sf-aa- 开头（字母序最先加载）",
          REAL_IP.startswith("zz-sf-aa-"))


# ==========================================================================
# --live
# ==========================================================================
def live_gate():
    # 前置：交付的三个 E2E 脚本必须在位
    rc, out = ssh(f"ls {TOOLS}/h24_e2e_real.py {TOOLS}/h24_e2e_bot.py "
                  f"{TOOLS}/h24_e2e_ratelimit.py {TOOLS}/h24_turnstile_degraded.py 2>&1")
    check("L0: 四个 E2E 脚本已在服务器就位", rc == 0, out.strip()[:200])

    # L1 机器人形态：拦截 + 零发信（G2）
    rc, out = ssh(f"cd {DEV_ROOT} && python3 {TOOLS}/h24_e2e_bot.py 2>&1")
    check("L1: 机器人路径 E2E 全绿（拦截/零发信/审计）", rc == 0, out.strip()[-220:])

    # L2 真人形态：放行 + 恰一封通知（G3）
    rc, out = ssh(f"cd {DEV_ROOT} && python3 {TOOLS}/h24_e2e_real.py 2>&1")
    check("L2: 真人路径 E2E 全绿（放行/一封通知/未误判）", rc == 0, out.strip()[-220:])

    # L3 限流：阈值被收紧为 3/3600 且第 4 次 429（G6）
    rc, out = ssh(f"cd {DEV_ROOT} && python3 {TOOLS}/h24_e2e_ratelimit.py 2>&1")
    check("L3: 限流 E2E 全绿（3/3600 + 第 4 次 429）", rc == 0, out.strip()[-220:])

    # L4 Turnstile 降级：不带 token 仍可提交且不误判（G5）
    rc, out = ssh(f"cd {DEV_ROOT} && python3 {TOOLS}/h24_turnstile_degraded.py 2>&1")
    check("L4: Turnstile 降级 E2E 全绿（无 token 仍可提交）", rc == 0, out.strip()[-220:])

    # L5 结构：审计表存在且列齐
    rc, out = ssh(f"cd {DEV_ROOT} && wp db query \"SHOW COLUMNS FROM wp_sf_form_spam_log\" --allow-root 2>&1")
    for col in ("form_id", "submission_id", "ip", "ua", "score", "signals", "signature", "source"):
        check(f"L5: 审计表含列 {col}", col in out)


# ==========================================================================
def main():
    ap = argparse.ArgumentParser(description="H24 form-antispam gate")
    ap.add_argument("--source", action="store_true")
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--root", default=None,
                    help="source 断言的 mu-plugins 目录（负对照用）")
    a = ap.parse_args()

    if not a.source and not a.live:
        a.source = True

    if a.source:
        root = Path(a.root).resolve() if a.root else MU
        print(f"== --source (root={root}) ==")
        source_gate(root)
    if a.live:
        print("== --live ==")
        live_gate()

    print(f"\n== {PASS} passed, {FAIL} failed ==")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()

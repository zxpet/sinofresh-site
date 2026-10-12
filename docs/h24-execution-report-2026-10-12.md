# H24 执行报告 — 独立站表单机器人询盘防护（dev → 生产）

- 日期：2026-10-12 ｜ 方案依据：`docs/h24-form-antispam-plan-2026-10-12.md`（拍板：**选 B** + 六条修订 + 三条补充）
- 站点：`www.zxpet.com`（生产 `/var/www/zxpet-v2`）｜ `dev.zxpet.com`（`/var/www/dev.zxpet.com/public`）｜ 同机 `65.49.215.152`
- 结论：**dev 与生产双侧分层验收全绿**；生产已生效；存量 211 条已归档；自动回复已停用；4 张相关表测试后全部回基线

---

## 一、一句话结论

给「Get a Quote」等 5 个 Fluent Forms 表单装上了一层**评分制内容防护 + 真实 IP 限流**（mu-plugin，2 个文件、共约 80 KB），使机器人提交**落库标 spam 但一封邮件都不发**；真人提交路径**逐项实测未被误伤**；并配齐了用户要求的**审计表 / 后台人工复核 / 告警频率控制**三件治理设施。

## 二、生产变更清单（逐项可独立回滚）

| # | 变更 | 落地值 | 回滚方式 |
|---|---|---|---|
| 1 | 新增 mu-plugin `zz-sf-aa-real-ip.php` | 9209 B，md5 `e148de98…` | `rm` 即失效（备份在 `/root/h24-backup/prod-mu-plugins-20261012T023810Z.tar.gz`） |
| 2 | 新增 mu-plugin `zz-sf-form-guard.php` | 71156 B，md5 `2a344b5c…` | 同上 |
| 3 | 建审计表 `wp_sf_form_spam_log` | 15 列，与 dev 完全一致，`db_version=1.0.0` | `DROP TABLE`（无外键依赖） |
| 4 | A1 蜜罐开启 | `_fluentform_global_form_settings.misc.honeypotStatus = 'yes'` | `SF_H24_SITE=prod SF_H24_MODE=restore wp eval-file …/h24_prod_settings.php`（已实测 byte-identical） |
| 5 | A3 拒绝空提交 | form 8 `formSettings.restrictions.denyEmptySubmission.enabled = true` | 同上（同一个脚本一并回滚） |
| 6 | 停用自动回复 | form 8 `notifications` id=40 `enabled=false` | `SF_H24_SITE=prod SF_H24_MODE=restore …/h24_autoreply_ctl.php`（已实测 byte-identical） |
| 7 | 存量归档 | form 8：`read=1 / trashed=211`（**不 DELETE**） | `…/h24_archive_spam.php SF_H24_MODE=restore`（回滚清单 211 条） |

**三方 md5 一致**：本地 ↔ 服务器暂存 ↔ 生产安装位，两个 mu-plugin 均逐字节一致。

**备份位置**：`/root/h24-backup/`（服务器）+ `_backup/h24-prop-stock-2026-10-12/`（本地）
- `prod-mu-plugins-20261012T023810Z.tar.gz` — 改前 mu-plugins 全量
- `prod-form8-archive-2026-10-12.json`（106 573 B）/ `-original.json`（144 954 B）/ `prod-form8-status-rollback.json`（211 条）
- `global_settings_raw.prod.json` / `form8_formsettings_raw.prod.json` / `notif_autoreply_raw.prod.json`（+ dev 同名三份）

## 三、分层验收结果

设计原则：**副作用从零到有**分层，生产只做受控写测试。

| 层 | 内容 | dev | 生产 |
|---|---|---|---|
| L0 | 静态门 `h24_gate.py --source`（G1–G7 + H24 契约） | **47/47** | 同源字节一致 |
| L1 | 配置层：插件加载 / 蜜罐 / 拒绝空提交 / 自动回复 / 限流 `3\|3600` / 审计表 | ✅ | ✅ 与 dev 一致 |
| L2 | 渲染层：4 页蜜罐字段 + guard 脚本 + 签名 token；CF `DYNAMIC` 不缓存 HTML | ✅ | ✅ 4/4 页 |
| L3 | 决策层：评分函数表驱动（真人 3 / 机器人 2 / S4 不计分 / Turnstile / 快提交） | **9/9** | **9/9** |
| L4 | 写路径层：真实 HTTP 提交全链路（拦 / 放 / 限流 / 清理） | ✅ | **全绿 rc=0** |
| L5 | 治理层：后台复核 / release / 黑名单 / 告警阈值与频率 | **32/32** | **10/10** |

### L4 生产实测要点

```
机器人（截断 UA=Chrome/109 + Win10、无计时字段、RobertTon/Ton/robertton@gmail.com/Price?）
  HTTP 200 · success=true · 响应不含 spam/block/reject 字样（伪装成功）
  submissions status=spam（直接落库标 spam —— 用户要求）
  FluentSMTP 440→440 · wp-mail-logging 453→453 · FF 集成日志 428→428   ← 零发信
  审计行 score=5 | signals=S1_shared_suffix,S2_template_message,S2b_short_message,S4_note_stale_ua
        source=score | ip=127.0.0.1 | ua=111B | country=United States | email_domain=gmail.com

真人（完整字段 + 蜜罐留空 + 有效签名 token + 等待 5 s）
  HTTP 200 · success=true · 入库 status=unread
  恰好 1 封 "New Inquiry: Soft Chews from Green Paws Nutrition Ltd (United Kingdom)"
  无自动回复 · 收件人=隔离地址 · status=sent · 审计表零新增

限流
  apply_filters('fluentform/max_submission_count',5,8) = 3 ／ min_submission_interval = 3600
  窗口内已有 2 → 第 2 次请求即 429 {"errors":{"restricted":["Too Many Requests."]}}
  （证明计数键是真实 IP：loopback 下 REMOTE_ADDR 非 CF 网段 ⇒ 归一到访客 IP 后才收紧）

清理（基线快照 + 来源限定）
  submissions 213→213 · fsmpt 440→440 · spam_log 1→1 · wpml_mails 453→453
```

### L2 渲染层明细（生产）

| 页面 | 表单 | 蜜罐字段 | guard 脚本 | 结果 |
|---|---|---|---|---|
| `/contact/` | form 8 | `item_8__fluent_sf` | ✅ | 200 |
| `/quality/` | form 11 | `item_11__fluent_sf` | ✅ | 200 |
| `/factory-tour/` | form 10 | `item_10__fluent_sf` | ✅ | 200 |
| `/services/` | form 9 | `item_9__fluent_sf` | ✅ | 200 |

注入脚本实测内容（`var FIELD = "sf_fg_t"` / `var TOKEN = "<ts>.<hmac-sha256>"` / `var TS_KEY = ""`），`TS_KEY` 为空时 Turnstile 分支直接 return、**不发任何请求**。

## 四、新增工具（均落在 `tools/`，已同步 `/root/h24-tools/`）

| 文件 | 用途 | 站点 |
|---|---|---|
| `h24_gate.py` | 双半场门：`--source`（47 项静态契约）/ `--live`（驱动 dev E2E + 审计表校验）+ 负对照 | dev/生产 |
| `h24_prod_settings.php` | A1 蜜罐 + A3 拒绝空提交（status/apply/restore，幂等、按站点分名备份） | dev + prod |
| `h24_autoreply_ctl.php` | 自动回复开关（`SF_H24_SITE` 分站点备份，避免 dev/prod 串味） | dev + prod |
| `h24_archive_spam.php` | 存量归档（dry-run/apply/restore，零误杀结构规则） | prod |
| `h24_prod_l3.php` | L3 决策层：评分函数表驱动断言 | dev + prod |
| `h24_prod_l4.py` | L4 写路径：真实 HTTP 提交（条件式邮件隔离 + 快照清理） | dev + prod |
| `h24_prod_l5.php` | L5 治理层：复核入口 / release / 黑名单 / 告警 | dev（含写）+ prod（只读） |
| `h24_e2e_real.py` / `h24_e2e_bot.py` / `h24_e2e_ratelimit.py` / `h24_turnstile_degraded.py` | dev 侧四个 E2E（上一轮已交付） | dev |

### 常用命令

```bash
# 静态门（本地）
python3 tools/h24_gate.py --source

# 生产配置状态
ssh root@65.49.215.152 "SF_H24_SITE=prod SF_H24_MODE=status wp --allow-root --path=/var/www/zxpet-v2 eval-file /root/h24-tools/h24_prod_settings.php"

# 生产只读治理层断言
ssh root@65.49.215.152 "SF_H24_SITE=prod wp --allow-root --path=/var/www/zxpet-v2 eval-file /root/h24-tools/h24_prod_l5.php"

# 生产写路径验收（需先装条件式邮件隔离夹具，脚本会拒绝在无夹具时运行）
ssh root@65.49.215.152 "SF_H24_SITE=prod python3 /root/h24-tools/h24_prod_l4.py"
```

## 五、运行期发现（须进运维手册）

1. **`wp-mail-logging` 在生产为 `active`**（此前「已废弃」结论有误）⇒ 生产同一封邮件**两张表都记**；dev 该插件为 `inactive`。凡「零发信」举证，**生产必须两表同查**。`wp_wpml_mails` 收件人列名是 `receiver`、主键 `mail_id`。
2. **审计表要在部署阶段主动预热**（`sf_fg_maybe_install()` 只挂 `admin_init` + 拦截惰性调用），否则首次拦截会在请求路径里跑 dbDelta。
3. **生产尚未经历「装上防护后的真实机器人流量」**：最新真实垃圾提交为本地时间 10-12 06:37，比部署（10:38）早 1 分钟 ⇒ 拦截效果目前由构造用例（L3/L4）证明，需 24h/72h 观察窗复核。
4. **拦截器绕过 FF 限流**（设计取舍）：被拦提交不进入 FF ⇒ 不消耗其配额。零发信不受影响，但需观察 spam 表增速。
5. **生产写测试零污染范式**：条件式邮件隔离（`X-SF-H24-Test` 头）+ 基线 max id 快照 + 来源限定清理（`ip LIKE '127.0.0.1'` / `receiver='h24-test@invalid.example'`）+ `trap EXIT` 保证夹具删除。**测试窗口内真实访客数据不受任何影响。**

## 六、本轮修正的自身失误（留档以免重犯）

| 现象 | 根因 | 处置 |
|---|---|---|
| L4 首跑「被拦提交不入库」FAIL | 我按错误记忆写断言；实际设计是**落库标 spam**（用户明确要求） | 改为断言 `status=spam` + 零发信 + 审计 +1 |
| L4 首跑「历史表保持不动」FAIL | 沿用 dev 结论（dev 该插件 inactive），生产实为 active | 断言改为按插件状态自适应；清理补 `wp_wpml_mails` |
| A3 长度差期望 `+1` 得 `-1` | `false`(5) → `true`(4) 是 **-1**（`autoreply_ctl` 是 true→false 才 +1） | 改为按 needle 实长计算 |
| L5 输出「0 passed, 0 failed」 | `wp eval-file` 非全局作用域，`global $pass` 取不到 | 改用 `$GLOBALS['h24_l5_pass']` |
| L5「后台动作走 check_admin_referer」FAIL | 实现用 `wp_verify_nonce`（等价且顺序正确） | 断言改写为 `wp_verify_nonce` + 权限前置 |
| L4 首轮遗留 2 条 `wp_wpml_mails` 记录 | 清理清单漏了该表 | 已定点删除（`receiver='h24-test@invalid.example'`），表回 453 |

## 七、遗留（详见方案文档 §十六）

1. **恢复自动回复 + 「仅非 spam 触发」守卫**（待防护稳定 ≥ 1 周）
2. **C 组边缘加固**（Sam 面板 WAF 规则 / 提交端点限速 / 源站只放行 CF 网段 —— 需独立窗口 + 自动回滚保险）
3. **DMARC `p=none` → `p=quarantine`**（待 SPF/DKIM 100% 通过；计划见方案 §十五）
4. **观察窗**：24h / 72h / 7d 读 spam 表增速与真询盘量
5. **`wp-mail-logging` 口径统一**（决定生产中该插件去留）
6. **管理通知模板占位符笔误**（通知 id=39 的 `Privacy Consent` 用错字段，单独小改）
7. **4 个 mu-plugin 纳入 git**（本批已一并提交）

## 八、附：dev 侧夹具变更

`/var/www/dev.zxpet.com/public/wp-content/mu-plugins/` 下原临时文件 `zz-sf-zz-test-nomail.php`（注释写着 "Delete after the test"）已**转正**为 `zz-sf-dev-mail-sink.php`：
- dev 为**无条件**黑洞（dev 站任何邮件都不该外发）
- 注释中明确标注**依赖方**（`tools/h24_e2e_real.py` 等的「收件人已被隔离改写」断言），并说明删除时的迁移路径
- 生产侧**无**任何邮件夹具残留（已核验 0 个）

dev 侧同时清掉了 `sf_fg_alert_state` 的测试残留。

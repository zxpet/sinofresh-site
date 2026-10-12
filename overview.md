# H24b 执行总结 — 表单机器人防护·八项修订 + 通知模板全修 + 收尾两项（dev + 生产全绿）

> 批次：H24b（承接 H24，同日 2026-10-12）。H24 本体见 `docs/h24-execution-report-2026-10-12.md`。
> **结论：八项中六项落地并全量验收（Turnstile 按裁决延后）；通知模板缺陷普查后 5 个表单全部修复；收尾两项 —— 自动回复全停用 + `Document Type` 占位符修复 —— 已完成，普查 5 表单 9 feed 0 问题。**

## 一、H24b 八项修订（主体）

1. **限流改造**（`zz-sf-form-guard.php` v1.1.0 → **v1.2.0**）：自建计数只统计真实提交、**5 次/3600 秒**、spam 被拦路径结构性不占配额；FF 原有限流保留作兜底（100/3600）。
2. **审计表治理**：90 天保留期 + 每日 cron（部署期预热）；同 IP 24h ≥50 自动加黑；告警带「当前行数 / 近 24h 被拦 / 加黑 IP」。
3. **后台可用性**：顶层菜单「表单防护」+ FF 子菜单入口；**FF 条目页状态总览条**（未读/全部/已读/垃圾/回收站带计数、裸访问默认未读、未读=0 空状态引导、详情页让位、hashchange 跟随），零耦合 FF 原生下拉。
4. **Q4 日志口径收敛**：生产停用 `wp-mail-logging`（表 454 行保留），dev/生产统一；实测停用后邮件照发且只记 `wp_fsmpt_email_logs`。
5. **配套工具链**：限流 E2E、通知渲染级验收、后台 47 项行为断言 + 21 张截图（已打码 PII）、Q4 前后对照脚本、截图打码器。

## 二、通知模板「Privacy Consent」行全量修复（5 个表单，纯 DB 内容）

普查发现这一行**5 个表单全是坏的**，三种坏法：

| 表单 | 改前 | 症状 | 改后 |
|---|---|---|---|
| 8 Get a Quote | `{inputs.company_name_1}` | 显示成公司名 | `{inputs.privacy_consent_11.value}` |
| 9 Request a Sample | `{inputs.company_name_1}` | 显示成公司名 | `{inputs.privacy_consent_12.value}` |
| 10 Book a Factory Tour | `{inputs.company_name_1}` | 显示成公司名 | `{inputs.privacy_consent_14.value}` |
| 11 Request COA | `{inputs.privacy_consent_9.i_agree_..._1}` | **完全空白**（孤儿 key） | `{inputs.privacy_consent_9.value}` |
| 12 Feedback | `{inputs.privacy_consent_5.i_agree_..._1}` | **完全空白**（孤儿 key） | `{inputs.privacy_consent_5.value}` |

根因：模板从 form 8 复制出去 —— 前两份照抄了公司名占位符（改了字段没改值），后两份用了 FF「选项级」key（`ShortCodeParser` 只认 `{inputs.<字段>}` / `.value`）。

**真通知端到端验证**：真实访客路径提交 → 通知真发到 `sales@zxpet.com`（FluentSMTP id 449，`status=sent`）→ 正文 `Privacy Consent: I agree to the Privacy Policy` ✅。

**字段对照表文档**：`docs/form-notification-fields-2026-10-12.md`（714 行 / 25.9 KB，脚本生成）。
**运维手册同步**：`WP Mail Log` 实际 **8 处** + 快速卡 1 处 → 全部改 FluentSMTP，三件产物重建。

## 三、收尾两项（Sam：两件一次定完）

### 1. 自动回复全停用（form 9/10/11，与 form 8 一致）

| feed | 表单 | 改前 md5 / len | 改后 md5 / len |
|---|---|---|---|
| 46 | 9 Request a Sample | `96560c82…` / 835 | `5e080c3a…` / 823 |
| 52 | 10 Book a Factory Tour | `9cf0e277…` / 840 | `8b900da1…` / 828 |
| 58 | 11 Request COA | `7be5be54…` / 806 | `9ac867e8…` / 794 |
| 40 | 8 Get a Quote（**本轮未触碰**） | `2bdbea0d…` / 794 | `2bdbea0d…` / 794 |

判据来自 **FF 源码本身**：`GlobalNotificationManager::getEnabledFeeds()`（L258）用 `ArrayHelper::isTrue($parsedValue,'enabled')` 过滤 ⇒ `enabled=false` 的 feed **进不了候选集、彻底不发**。dev 与生产侧改前/改后 md5 **逐字一致**。

**零发信硬验证**（`tools/h24b_check_enabled_feeds.php` 直调 FF 自己的函数）：

```
[PASS] 正对照：form 8 管理员通知(39) 会被发送（证明本次调用有效、不是假绿）
[PASS] Auto Reply feed 46/52/58 全部不再发送
[PASS] form 8 Auto Reply feed 40 不发送
[PASS] 5 个管理员通知 feed 全部正常发送
本批生效的 feed（会被发送）meta_id = 39,45,51,57,63
```

⚠️ 一个必须记住的陷阱：改后长度是 **−12 字节**，而 `true→false` 本应 **+1** —— 差额来自 FF 原生 JSON 里的 `\/`（转义斜杠）被 `json_encode(JSON_UNESCAPED_SLASHES)` 规范成 `/`（每处 −2B）。**长度差不能作依据**，所以做了「同规则重排后逐字节相等」的规范性等价证明（4/4 True）⇒ 除目标键外零变化。

### 2. form 11 `Document Type` 占位符修复

`{inputs.document_type_7}` → **`{inputs.document_type_7.value}`**（meta_id 57，`195b5f07…/830` → `1fd41ef0…/836`）。

**checkbox 渲染实测（四格 × 三场景）**：裸用 `{inputs.X}` + 数组（真实提交的 checkbox 就是数组）+ `isHtml=true` ⇒ 渲染成 `<ul><li>…</li></ul>`；`.value` 在**全部场景**都是内联单行，多选输出 `COA Sample, MSDS`（逗号连接，**永不出现 `Array`**）。改后整篇 HTML 邮件 `全篇含 <ul> = no ✓`。

### 3. 普查重跑

```
=== 5 个表单 / 9 个 feed / 0 个 feed 存在问题 ===
```

## 四、关键数字

| 门 | dev | 生产 |
|---|---|---|
| `h24_gate.py --source` | **64 / 0**（负对照 47/17 转红） | — |
| `h24_gate.py --live` | **23 / 0**（含 L8–L11） | — |
| `h24b_l1.php`（L1/L3/L5/L7） | 62 / 0 | 62 / 0 |
| 限流 E2E | ALL PASS | ALL PASS（429 / 不落库 / 零残留） |
| 后台行为断言 + 截图 | 47 项 / 11 张 | 43 项 / 10 张 |
| Q4 前后对照 | — | ALL PASS |
| 真通知验证 | — | ALL PASS（邮件正文已核对） |
| 通知模板普查 | 5 表单 / 0 问题 | 5 表单 / 0 问题 |
| FF `getEnabledFeeds()` 零发信验证 | 4/4 PASS | 4/4 PASS |

**本批门禁增强**：L0 脚本清单 11→14；**L9 补上漏掉的 R3 计数**（正是本批那处 bug 的规则）；新增 **L10**（直调 FF `getEnabledFeeds()`，`rc==0` + 4×`[PASS]` + 无 `[FAIL]`）；新增 **L11**（`h24b_fix_checkbox_value.php --status` 的「待修正」计数须为 0）。

## 五、⚠️ 上一批的操作失误（如实报告，本轮已裁决归档）

上批写清理逻辑时我用了 `MAX(id)` 当作「本次测试创建的记录 id」。测试提交因 `country_5` 取值非法被 FF 校验拒（**未落库**），脚本仍按 `MAX(id)=247` 删除 ⇒ **误删攻击者（80.94.95.202）一条 spam 入库记录**。

- **影响极低**：本身是垃圾询盘；**拦截证据完整保留**（审计表 id=79 含 ip/ua/email_domain/score/signals）；复核页对该行只做 `update ... WHERE id=247` ⇒ 0 行、不报错。
- MySQL binlog 未开启无法精确恢复；**未伪造数据**，保留现状并如实记录。
- **根因已修**：清理改为按「本次测试独有邮箱」精确定位。
- **Sam 裁决**：**接受、不追究** —— 只要审计 id=79 证据没丢即可，清理逻辑改成精确定位已足够。

## 六、观察窗数据（当日快照 2026-10-12 13:50 CST）

- 审计表 `rows_total=26`、`max_id=82`（区间 10:49:18→13:41:32）；被拦 IP Top **80.94.95.202 共 26 次**（自动加黑阈值 24h≥50 **未触发**）。
- form 8：`read=1 / spam=25 / trashed=211`（unread=0）。
- 邮件按日：`2026-10-12 auto_reply=22 其他=23`、`2026-10-11 auto_reply=121 其他=121`。
- ⚠️ **两个记录坑**（命令已重跑验证并写入报告）：① 10-12 的 22 封 auto_reply **全在 H24 上线 10:38 之前** ⇒ 不是异常；② `created_at` 是**上海墙上时间**，配 `NOW()`（UTC 会话）做 24h 过滤会**错位 8 小时** ⇒ 改用**按 `max_id` 增量** + **按日 `DATE(created_at)` 统计**。

## 七、遗留 / 待办

- **恢复自动回复（有明确时点与条件）**：防护稳定 **≥1 周**（约 **10-19**）后，form **8/9/10/11 四个一起**恢复，且**必须统一加「仅非 spam 触发」守卫**。
- **Turnstile 启用**（Sam 延后）：等 CF sitekey/secret；CSP 三处需补 `challenges.cloudflare.com`（现 Report-Only）。
- **C 组边缘加固**：独立窗口（源站仍可直连绕过 CF；WAF 规则／提交端点限速／源站只放行 CF 网段）。
- **DMARC `p=none`→`p=quarantine`**：硬约束 —— SPF/DKIM 未 100% 通过前不升档。
- **观察窗** 24h（10-13）/ 72h（10-15）/ 7d（10-19）按报告 §8.6 命令记录。
- **手册仍有版本号疑似过期**（B2 技术栈表写 WP 7.1.2 / 主题 2.10.89，实际 7.1.3 / 2.10.90）。
- mu-plugin 文件头 `Version:` 仍未随行 bump；FF 6.2.14 → 6.2.15 未评估。

## 八、产物清单

- **生产**：`zz-sf-form-guard.php` v1.2.0（md5 `7c31e25d…`）；5 个表单通知模板已修（form 8/9/10/11/12）；**4 个表单自动回复全停用**（feed 40/46/52/58）
- **本批新增工具**：`tools/h24b_autoreply_toggle.php`、`tools/h24b_fix_checkbox_value.php`、`tools/h24b_check_enabled_feeds.php`、`tools/h24b_diag_checkbox_render.php`
- `tools/`（上批）：`h24b_fix_privacy_line.php`、`h24b_audit_notifs.php`、`h24b_notif_verify.py`、`h24b_notif_body_check.py`、`h24b_build_field_map.py`、`h24b_form_counts.php`、`h24b_l1.php`、`h24b_rl_e2e.py`、`h24b_notif_render_check.php`、`h24b_admin_shots.{php,js}`、`h24b_q4_*`、`h24b_redact_shots.py`、`h24_gate.py`（L8–L11）
- `docs/`：`h24b-execution-report-2026-10-12.md`（含 §七 收尾 + **§八 本批**）、`form-notification-fields-2026-10-12.md`、`h24b-plan-2026-10-12.md`、`change-log.md`（#10 / #11 / **#12**）、`ops-manual-v1.{md,docx,pdf}`、`ops-manual-quick-ref.pdf`
- **备份**：`/root/h24b-backup/`（`notif_privacy_raw.*`、**`autoreply_raw.{prod,dev}.*`**、**`checkbox_ph_raw.{prod,dev}.*`**，chmod 0600）；本地 `_backup/`（手册三件旧版 + form 8 原值）

### 回滚命令

```bash
# ① 自动回复（4 个表单，byte-identical 比对后写回）
cd /var/www/zxpet-v2 && SF_H24B_SITE=prod SF_H24B_FORM=9,10,11 \
  wp eval-file /root/h24-tools/h24b_autoreply_toggle.php --allow-root   # 加 SF_H24B_MODE=restore

# ② Document Type 复选框占位符
cd /var/www/zxpet-v2 && SF_H24B_SITE=prod SF_H24B_MODE=restore \
  wp eval-file /root/h24-tools/h24b_fix_checkbox_value.php --allow-root

# ③ 通知「Privacy Consent」行（5 个表单）
cd /var/www/zxpet-v2 && SF_H24B_SITE=prod SF_H24B_MODE=restore \
  wp eval-file /root/h24-tools/h24b_fix_privacy_line.php --allow-root
```

# H24b 执行总结 — 表单机器人防护·八项修订 + 附加修复收尾（dev + 生产全绿）

> 批次：H24b（承接 H24，同日 2026-10-12）。H24 本体见 `docs/h24-execution-report-2026-10-12.md`。
> **结论：八项中六项落地并全量验收；Turnstile 按裁决延后；通知占位符已修好并用真通知验证 —— 且普查发现是 5 个表单同一处缺陷，已全部修复。**

## 一、H24b 八项修订（主体）

1. **限流改造**（`zz-sf-form-guard.php` v1.1.0 → **v1.2.0**）：自建计数只统计真实提交、**5 次/3600 秒**、spam 被拦路径结构性不占配额；FF 原有限流保留作兜底（100/3600）。
2. **审计表治理**：90 天保留期 + 每日 cron（部署期预热）；同 IP 24h ≥50 自动加黑；告警带「当前行数 / 近 24h 被拦 / 加黑 IP」。
3. **后台可用性**：顶层菜单「表单防护」+ FF 子菜单入口；**FF 条目页状态总览条**（未读/全部/已读/垃圾/回收站带计数、裸访问默认未读、未读=0 空状态引导、详情页让位、hashchange 跟随），零耦合 FF 原生下拉。
4. **Q4 日志口径收敛**：生产停用 `wp-mail-logging`（表 454 行保留），dev/生产统一；实测停用后邮件照发且只记 `wp_fsmpt_email_logs`。
5. **配套工具链**：限流 E2E、通知渲染级验收、后台 47 项行为断言 + 21 张截图（已打码 PII）、Q4 前后对照脚本、截图打码器。

## 二、附加修复收尾（Sam 批准「顺手修掉」）

6. **通知「Privacy Consent」行全量修复（5 个表单，纯 DB 内容）** —— 普查发现这一行**5 个表单全是坏的**，三种坏法：

   | 表单 | 改前 | 症状 | 改后 |
   |---|---|---|---|
   | 8 Get a Quote | `{inputs.company_name_1}` | 显示成公司名 | `{inputs.privacy_consent_11.value}` |
   | 9 Request a Sample | `{inputs.company_name_1}` | 显示成公司名 | `{inputs.privacy_consent_12.value}` |
   | 10 Book a Factory Tour | `{inputs.company_name_1}` | 显示成公司名 | `{inputs.privacy_consent_14.value}` |
   | 11 Request COA | `{inputs.privacy_consent_9.i_agree_..._1}` | **完全空白**（孤儿 key） | `{inputs.privacy_consent_9.value}` |
   | 12 Feedback | `{inputs.privacy_consent_5.i_agree_..._1}` | **完全空白**（孤儿 key） | `{inputs.privacy_consent_5.value}` |

   根因：模板从 form 8 复制出去 —— 前两份照抄了公司名占位符（改了字段没改值），后两份用了 FF「选项级」key（`ShortCodeParser` 只认 `{inputs.<字段>}` / `.value`，带选项后缀取不到）。

7. **真通知端到端验证**（Sam 约束①）：真实访客路径提交 → 管理员通知真发到 `sales@zxpet.com`（FluentSMTP id 449，`status=sent`）→ 邮件正文 `Privacy Consent: I agree to the Privacy Policy` ✅，5 项断言全 PASS；测试数据按邮箱精确定位清理干净。

8. **字段对照表文档**（新增）：`docs/form-notification-fields-2026-10-12.md`（690 行 / 24.7 KB，脚本生成）—— 5 个表单的字段清单 / 通知 feed / 主题与正文（原文+渲染）/ 占位符映射。

9. **运维手册同步**：`WP Mail Log` 实际出现 **8 处**（不止两处）+ 快速卡 1 处，全部改为 **FluentSMTP（Tools → Fluent SMTP → Email Logs）**；三件产物（docx / pdf / 速查卡）已重建，避免 md 与 pdf 静默分叉。

10. **门禁防回退**：`h24_gate.py --live` 新增 **L8**（5 表单隐私行形态）、**L9**（普查无 R1 孤儿 / R2 跨语义）。

## 三、关键数字

| 门 | dev | 生产 |
|---|---|---|
| `h24_gate.py --source` | **64 / 0**（负对照 47/17 转红） | — |
| `h24_gate.py --live` | **21 / 0**（含新增 L8/L9） | — |
| `h24b_l1.php`（L1/L3/L5/L7） | 62 / 0 | 62 / 0 |
| 限流 E2E | ALL PASS | ALL PASS（429 / 不落库 / 零残留） |
| 后台行为断言 + 截图 | 47 项 / 11 张 | 43 项 / 10 张 |
| Q4 前后对照 | — | ALL PASS |
| **真通知验证** | — | **ALL PASS**（邮件正文已核对） |
| 通知模板普查 | 5 表单 / 0 问题 | 5 表单 / 0 问题 |

## 四、⚠️ 需要你知道的一处操作失误（如实报告）

写清理逻辑时我用了 `MAX(id)` 当作「本次测试创建的记录 id」。测试提交其实因 `country_5` 取值非法被 FF 校验拒（**未落库**），脚本仍按 `MAX(id)=247` 删除 —— **误删了攻击者（80.94.95.202）的一条 spam 入库记录**。

- **影响极低**：本身是垃圾询盘；**拦截证据完整保留**（审计表 id=79 含 ip/ua/email_domain/score/signals）；后台复核页对该行只做 `update ... WHERE id=247` ⇒ update 0 行，不报错、不影响功能。
- MySQL binlog 未开启，无法精确恢复原文；**我没有伪造数据**，保留现状并如实记录。
- **根因已修**：清理一律按「本次测试独有邮箱」精确定位，并删除了遗留的按 id 删除分支；重跑全 PASS、零残留。

## 五、观察窗数据（今日快照）

- 攻击者 **80.94.95.202** 当日触发 **24 次**全部被拦（自动加黑阈值 24h≥50，未触发），时间跨度 10:49→13:22。
- 管理员通知今日 44 封、**全部在 10:38（H24 上线）之前**；自动回复最后一封 06:37 < 10:38 ⇒ 两条「归零」结论在 v1.2.0 上继续成立。

## 六、遗留 / 待办

- **Turnstile 启用**（用户延后）：等 CF sitekey/secret；CSP 三处需补 `challenges.cloudflare.com`。
- **C 组边缘加固**：等 24h 观察窗（源站仍可直连绕过 CF）。
- **恢复自动回复 + 仅非 spam 触发守卫**：等防护稳定 ≥1 周。
- ⚠️ **form 9/10/11 的自动回复 feed 仍是 `enabled=true`**（form 8 已停用）—— 目前它们没被真实提交过所以没发过信；恢复自动回复时需一并决定这四个表单的口径。
- **form 11 的 `Document Type` 复选框未加 `.value`**（R3 提示级，非 bug）：HTML 邮件里会渲染成 `<ul><li>` 而非内联；本轮按「只修 Privacy Consent」未动，待你决定。
- **手册仍有其他版本号疑似过期**（如 B2 技术栈表写 WP 7.1.2 / 主题 2.10.89，实际 7.1.3 / 2.10.90）—— 本轮只改了邮件日志相关内容，未扩大范围。
- mu-plugin 文件头 `Version:` 仍未随行 bump；FF 6.2.14 → 6.2.15 未评估。

## 七、产物清单

- **生产**：`zz-sf-form-guard.php` v1.2.0（md5 `7c31e25d…`）；5 个表单通知模板已修（form 8/9/10/11/12）
- `tools/`：`h24b_fix_privacy_line.php`（通用修复+回滚）、`h24b_audit_notifs.php`（普查）、`h24b_notif_verify.py`（真通知验证）、`h24b_notif_body_check.py`（离线复核）、`h24b_build_field_map.py`（文档生成）、`h24b_form_counts.php`、`h24b_l1.php`、`h24b_rl_e2e.py`、`h24b_notif_render_check.py`、`h24b_admin_shots.{php,js}`、`h24b_fix_notif_placeholder.php`、`h24b_q4_*`、`h24b_redact_shots.py`、`h24_gate.py`（L8/L9）
- `docs/`：`h24b-execution-report-2026-10-12.md`（含 §七 收尾）、`form-notification-fields-2026-10-12.md`、`h24b-plan-2026-10-12.md`、`change-log.md`（#10、#11）、`ops-manual-v1.{md,docx,pdf}`、`ops-manual-quick-ref.pdf`
- **备份**：`/root/h24b-backup/notif_privacy_raw.{prod,dev}.{8,9,10,11,12}.json`；本地 `_backup/`（手册三件旧版 + form 8 原值）

### 一条命令回滚（5 个表单）

```bash
cd /var/www/zxpet-v2 && SF_H24B_SITE=prod SF_H24B_MODE=restore \
  wp eval-file /root/h24-tools/h24b_fix_privacy_line.php --allow-root
```

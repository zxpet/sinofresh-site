# H24b 执行总结 — 表单机器人防护·八项补充修订（dev + 生产全绿）

> 批次：H24b（承接 H24，同日 2026-10-12）。H24 本体见 `docs/h24-execution-report-2026-10-12.md`。
> **结论：八项中六项落地并全量验收通过；Turnstile 按裁决延后；通知占位符按裁决留待下批（只读侦查完成、工具就绪）。**

## 做了什么

1. **限流改造**（mu-plugin `zz-sf-form-guard.php` v1.1.0 → **v1.2.0**）：自建计数只统计真实提交、**5 次/3600 秒**、spam 被拦路径结构性不占配额；FF 原有限流保留作兜底（覆写 100/3600 秒）→ 真客户多次咨询不再被挡。
2. **审计表治理**：90 天保留期 + 每日 cron（部署期已预热）；同 IP 24h ≥50 条自动进黑名单；告警正文带「审计表当前行数 / 近 24h 被拦 / 自动加黑 IP」。
3. **后台可用性**：顶层菜单「表单防护」（当日被拦徽标）+ FF 子菜单入口；**FF 条目页新增状态总览条**（未读/全部/已读/垃圾/回收站带计数、裸访问默认未读、未读=0 显示空状态引导、详情页让位、hashchange 跟随），**零耦合 FF 原生下拉**。
4. **Q4 日志口径收敛**：生产停用 `wp-mail-logging`（表 454 行保留），dev/生产统一；前后对照实测：停用前两表都记、停用后邮件照发且只记一处、零 PHP 报错。
5. **配套工具链**：限流 E2E、通知渲染级验收、后台 47 项行为断言 + 21 张截图（已按纪律打码 PII）、Q4 前后对照脚本、截图打码器。

## 关键数字

| 门 | dev | 生产 |
|---|---|---|
| `h24_gate.py --source` | 64 passed / 0 failed（负对照 47/17 转红） | — |
| `h24_gate.py --live` | 19 passed / 0 failed | — |
| `h24b_l1.php`（L1/L3/L5/L7） | 62 passed / 0 failed | 62 passed / 0 failed |
| 限流 E2E | ALL PASS | ALL PASS（429 / 不落库 / 零残留） |
| 后台行为断言 + 截图 | 47 项 / 11 张 | 43 项 / 10 张 |
| Q4 前后对照 | — | ALL PASS（停用后 `wp_wpml_mails` 零增长） |

生产实况：总览条渲染 `未读 (0)｜全部 (19)｜已读 (1)｜垃圾 (18)｜回收站 (211)`；`全部 = Σ状态 − 回收站` 与 FF 公式一致。

## 三个关键决策

- **「等于 DB」的断言上移到 PHP 侧**：FF 打开单条详情会把该条 `unread → read`，任何提前拍的快照跨脚本运行必然过期；浏览器侧改为与 FF 自己的 `resources?counts=true` 做**跨实现**比对（同一响应，零时差）。
- **「全部」用空筛选实现**：FF 6.2.14 状态下拉**没有「全部」项**，且 `entry_type=all` 会 `WHERE status='all'` 返回 0 行。
- **Q4 邮件隔离夹具带探针头**：先确认「夹具已加载且自定义头送达 PHP」再动手，避免测试邮件真发到 sales@；`trap EXIT` 无条件删除夹具。

## 遗留 / 待办

- **Turnstile 启用**（用户延后）：等 CF sitekey/secret；CSP 三处需补 `challenges.cloudflare.com`。
- **form 8 通知占位符**（id=39 `Privacy Consent: {inputs.company_name_1}` → `{inputs.privacy_consent_11.value}`）：生产实况确认待修正，工具 dev 全周期验证（含 byte-identical restore），**等 Sam 点头一键 apply**。
- **C 组边缘加固**：等 24h 观察窗（源站仍可直连绕过 CF）。
- **恢复自动回复 + 仅非 spam 触发守卫**：等防护稳定 ≥1 周。
- **运维手册两处过期**（L153「查 WP Mail Log」、L198 插件清单）：随下次复审重建 docx/pdf。

## 产物清单

- `server/mu-plugins/zz-sf-form-guard.php`（v1.2.0，已上生产，md5 `7c31e25d…`）
- `tools/`：`h24b_l1.php`、`h24b_rl_e2e.py`、`h24b_notif_render_check.py`、`h24b_admin_shots.{php,js}`、`h24b_fix_notif_placeholder.php`、`h24b_form_counts.php`、`h24b_q4_mail_logging.py`、`h24b_q4_deploy.sh`、`fixtures/zz-sf-zz-test-nomail.php`、`h24b_redact_shots.py`、`h24_gate.py`（更新）；删除过期的 `h24_e2e_ratelimit.py`
- `docs/`：`h24b-execution-report-2026-10-12.md`、`h24b-plan-2026-10-12.md`（含执行记录）、`change-log.md`（第 10 条）、`h24b-shots-dev/`、`h24b-shots-prod/`

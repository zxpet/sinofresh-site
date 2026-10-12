# H24b 执行报告 — 表单机器人防护八项补充修订

> 批次：H24b（承接 H24，同日 2026-10-12）
> 结论：**八项中六项已落地并全量验收通过；Turnstile 按裁决延后；通知占位符按裁决留待下批（已完成只读侦查与工具验证）。**
> 生产当前状态：`zz-sf-form-guard.php` **v1.2.0**（md5 `7c31e25dde209bf8de44685738b87ddd`，94 015 B）；`wp-mail-logging` **inactive**（表保留）。

---

## 一、范围与裁决回顾

用户在审完 H24 执行报告后给出八项修订，其中四项需裁决，裁决结果如下：

| # | 项 | 裁决 |
|---|---|---|
| 1 | Turnstile 正式启用 | **延后**（"先跳过 ①，其余七项先做"） |
| 2 | 限流放宽 | **选 1 自建计数**：只统计真实提交（`status in ('unread','read')`）、5 次/3600 秒、spam 不占配额；FF 原有限流**保留作兜底**，阈值覆写为 100 次/3600 秒 |
| 3 | 审计表保留期 + 告警带行数 | 做：90 天自动清理 + 每日 cron + 告警正文带「审计表当前行数」 |
| 4 | 后台复核入口 | 做：菜单明显 / 默认不显示 spam / 有「只看 spam」 |
| 5 | `wp-mail-logging` 双表并存 | **选 1**：生产停用（**不删表**，`wp_wpml_mails` 留作历史存档）；停用前确认 FluentSMTP 字段可替代；停用后实测；dev 与生产状态统一 |
| 6 | 同 IP 黑名单 | 不加白名单，但加**保险**：同 IP 24h 内被拦 ≥50 次自动进黑名单 |
| 7 | DMARC / 自动回复 | 同意报告处理；恢复自动回复时加「仅非 spam 触发」守卫 |
| 8 | C 组边缘加固 | 24h 观察窗后单独开窗口 |
| 附 | form 8 通知占位符笔误 | "建议下批一并修" ⇒ 本批只读侦查 |

**实施中途新增两条裁决（扫码发现事实与预期不符后停下询问）**：

- **「全部」入口形态** → **选 1 状态总览条**，四条规格：① 列表上方一行 `未读 (X) | 全部 (X) | 已读 (X) | 垃圾 (X) | 回收站`，带条数、点击切换；② 默认停在「未读」；③ 未读=0 显示空状态「当前没有未读询盘」+ [查看全部 (16)] [查看垃圾 (15)] 两个按钮，**不自动跳到全部**；④ **不动 FF 原生下拉**，只在它上方加这一行。
- **生产默认视图** → **选 3**：维持未读 + 空列表提示（不选 2：打开全部会让 spam 混在眼前，违背"默认不显示 spam"）。

**触发这两条裁决的代码级实测事实**（FF 6.2.14）：

- 状态筛选是 **Element-UI `el-select` 可清空下拉框**（不是标签页），选项来自 `Helper::getEntryStatuses()`＝`unread/read/favorites` + 强制追加的 `spam/trashed`；**没有「全部」项**。
- `Submission::countByGroup()` 里 `counts['all'] = array_sum($counts) − trashed`，**`all` 有数据却无 UI**。
- `Submission::customQuery()`：非空 `entry_type` → `WHERE status = entry_type` ⇒ **`entry_type=all` 会返回 0 行**（所以「全部」必须用**空筛选**实现，不能传 `all`）。
- 条目组件**没有 `$route` watcher** ⇒ 只改 hash 不会被 SPA 感知，必须整页加载（链接带一次性参数 `sf_fg_view` 使 fragment 之前不同）。
- 生产真实分布 `unread 0 / read 1 / spam 18 / trashed 211` ⇒ 默认切「未读」后运营打开就是空白页 ⇒ 空状态提示是生产的**主场景**，不是边缘情况。

---

## 二、交付物

### 2.1 mu-plugin `zz-sf-form-guard.php` v1.1.0 → **v1.2.0**（73 KB → 94 015 B）

| 新增/改动 | 说明 |
|---|---|
| 精细限流 | `sf_fg_real_limit_hit()` 等 8 个函数：只数真实提交、5/3600、transient 自动过期；挂在 `fluentform/submission_inserted`（spam 被拦路径**结构性**到不了这里，不占配额） |
| FF 兜底保留 | `SF_FG_MAX_SUBMISSIONS=100`／`SF_FG_MIN_INTERVAL=3600`（原 3/3600 改为 100/3600，只作粗粒度兜底） |
| 审计表保留期 | `SF_FG_LOG_RETENTION_DAYS=90` + `sf_fg_log_cleanup()`（幂等、按 `created_at < cutoff` 真删）+ 每日 cron `sf_fg_log_cleanup_event` |
| 自动加黑 | `sf_fg_abuse_maybe_autoblock()`：同 IP 24h ≥50 条 → 进黑名单（防 80.94.95.202 无限刷塞满审计表） |
| 告警增强 | 正文含「审计表当前行数」「近 24 小时被拦」「自动加黑的 IP」 |
| 后台入口 | `add_menu_page('表单防护'…58)` 顶层菜单（带当日被拦徽标）+ FF 子菜单入口 |
| 条目页总览条 | `sf_fg_entries_print_default_filter()` 挂 `fluentform/before_form_entry_app` 优先级 5：状态总览条 + 裸访问补 `type=unread` + 未读=0 空状态引导 + 详情页让位 + `hashchange` 跟随 + 一次性参数自抹；**零耦合 FF**（不注入 `entry_statuses`、不写 `entry_type`、不 `wp_redirect`） |
| 版本常量 | `SF_FG_VERSION='1.2.0'`（H24 版无此常量） |

### 2.2 工具（`tools/`，全部随仓库提交）

| 文件 | 用途 |
|---|---|
| `h24b_l1.php` | L1/L3/L5/L7 断言（dev/prod 通用，零污染），62 项 |
| `h24b_rl_e2e.py` | 精细限流 HTTP 验收（dev 全链路 / prod 受控预置计数） |
| `h24b_notif_render_check.py` | 通知**真实邮件正文**级渲染验收（含 `.value` 内联单行断言） |
| `h24b_admin_shots.php` / `.js` | 后台临时凭据签发/销毁 + 47 项行为断言 + 11 张截图 |
| `h24b_fix_notif_placeholder.php` | 通知占位符修正（status/apply/restore，dev 全周期已验证） |
| `h24b_form_counts.php` | 各表单状态分布一览（只读，也用于找「未读=0」空状态夹具） |
| `h24b_q4_mail_logging.py` | **Q4 前后对照验收**（停用前双写 → 停用 → 停用后只记一处） |
| `h24b_q4_deploy.sh` | Q4 流程封装：上传条件式邮件隔离夹具 → 跑验收 → **trap EXIT 无条件删夹具** |
| `fixtures/zz-sf-zz-test-nomail.php` | 条件式邮件隔离夹具（带 `X-SF-Test-Sink-Armed` 探针头，防"夹具没生效就把真邮件发给 sales@"） |
| `h24b_redact_shots.py` | 截图 PII 打码（数据单元格整体 ███） |
| `h24_gate.py` | 门禁更新：`--source` 64 项（新增 G12 17 项）、`--live` 19 项 |

### 2.3 证据截图

- `docs/h24b-shots-dev/`（11 张）、`docs/h24b-shots-prod/`（10 张）——**已打码**（05/06/07×2/08 共 12+ 处，`tools/h24b_redact_shots.py` 可复现）。

---

## 三、验证结果

### 3.1 dev（先全绿再上生产）

| 门 | 结果 |
|---|---|
| `h24_gate.py --source` | **64 passed / 0 failed**（负对照 HEAD worktree：47 passed / **17 failed** ⇒ 转红有效） |
| `h24_gate.py --live` | **19 passed / 0 failed** |
| `h24b_l1.php` | **62 passed / 0 failed** |
| `h24b_rl_e2e.py` | **ALL PASS**（机器人不占配额、第 6 次 429、429 不落库） |
| `h24b_notif_render_check.py` | **ALL PASS**（含「内联单行」） |
| `h24b_admin_shots.js` | **47 项断言 ALL PASS** + 11 张截图 |
| `h24b_fix_notif_placeholder.php` dev 全周期 | status → apply（+6）→ status → apply 幂等 → restore（**byte-identical**）→ 从 typo 版 apply（+10）两条路径字节一致 |

### 3.2 生产部署（2026-10-12 04:37 UTC）

| 步骤 | 证据 |
|---|---|
| 备份 | `/root/h24b-backup/prod-zz-sf-form-guard.php.bak-20261012T043702Z`（md5 `2a344b5c29d74b212c8a6e060988dad3`，71 156 B ＝ H24 版，亦即 git HEAD `4dccdbe` 的内容） |
| scp → `php -l` | No syntax errors |
| md5 三方一致 | 本地＝暂存＝安装后均 `7c31e25dde209bf8de44685738b87ddd`、94 015 B、`apache:apache 644` |
| 原子安装 | `install -o apache -g apache -m 644` → 同目录 `mv` |
| cron 预热 | `sf_fg_log_cleanup_event` 已排程（next ≈5 min，daily）——**不让首次调度落在请求路径** |
| 常量生效 | `SF_FG_VERSION=1.2.0`，`REAL_MAX=5`，`TTL=3600`，`AUTOBLOCK=50`，`RETENTION=90` |
| HTTP 冒烟 | `/`、`/products/`、`/contact/` 均 200；php-fpm 日志零新增错误 |

> 勘误：H24 版（71 156 B）**没有** `SF_FG_VERSION` 常量，`wp plugin list` 里 must-use 显示 `1.0.0` 是文件头未随行 bump —— 与本次无关，已记入待办。

### 3.3 生产验收

| 门 | 结果 |
|---|---|
| `h24b_l1.php`（prod） | **62 passed / 0 failed**；审计表回基线 18 行、黑名单无测试项 |
| `h24b_rl_e2e.py`（prod 受控） | **ALL PASS**：机器人载荷被拦且零发信（fsmpt 440→440、wpml 454→454）、计数仍 0；预置 5 后第 6 次 **HTTP 429** `{"errors":{"restricted":["Too Many Requests."]}}` 且不落库不写审计；reset 后恢复 200；四表回基线 |
| `h24b_admin_shots.js`（prod） | **43 项断言 ALL PASS** + 10 张截图；总览条渲染 `未读 (0)｜全部 (19)｜已读 (1)｜垃圾 (18)｜回收站 (211)`，与 FF 自身 counts 跨实现一致；空状态「当前没有未读询盘」+ [查看全部 (19)] [查看垃圾 (18)] 可见 |
| HTTP 层 | `/contact/` 200 且表单容器 16 个 `ff-el-input--` 节点 |

### 3.4 Q4（停用 `wp-mail-logging`）前后对照 —— **ALL PASS**

| 断言 | 停用前 | 停用后 |
|---|---|---|
| 真人询盘 HTTP | 200（`insert_id` 落库） | 200（`insert_id` 落库） |
| `wp_fsmpt_email_logs` | **+1**（440→441） | **+1**（440→441） |
| `wp_wpml_mails` | **+1**（454→455，双写确实存在） | **+0**（454→454，**口径收敛到一处**） |
| 新行字段 | `to`=隔离收件人 / `from`=`SINO FRESH Website <sales@zxpet.com>` / `subject`=`New Inquiry: Soft Chews from …` / `status`=`sent` / `response`=OK / 时间戳 | 同左 |
| 反面断言 | — | **无任何新邮件发往真实收件人** |
| PHP 致命错误 | 0 | 0 |

- **字段替代性（约束②）运行时复核**：`wp_fsmpt_email_logs` = `to/from/subject/status/response/created_at/…`；`wp_wpml_mails` = `mail_id/timestamp/host/receiver/subject/message/headers/attachments/error/plugin_version` ⇒ **后者无 from / status / response**，前者严格超集。
- 结束状态：`wp-mail-logging = inactive`（不删表，`wp_wpml_mails` 454 行历史存档保留）；dev 本就 inactive ⇒ **两边已统一**。
- 附加证据：FluentSMTP 日志里自动回复（`We've received your inquiry — SINO FRESH`）最后一封为 **06:37（上海时间）**，早于 H24 上线（10:38 上海时间）⇒ 自动回复停用在 v1.2.0 上继续成立。
  ⚠️ 读这类表要小心：`created_at` 是 `timestamp` 列，但 WP 用 `current_time('mysql')`（上海时间）在 UTC 会话下写入 ⇒ **读回来的字符串是上海墙上时间**，别当成 UTC 比对。

### 3.5 通知占位符（附带 bug，本批只读）

- 生产 form 8 通知 id=39（`Admin Notification`，766 B）实况：`Privacy Consent: {inputs.company_name_1}`（坏形态[0] 出现 1 次）、`{inputs.company_name_1}` 全串出现 3 次、目标串 0 次 ⇒ **STATE: 待修正**。
- dev 已全周期验证过修正工具（含 byte-identical restore），**一键可修**，等 Sam 点头。

---

## 四、本批新踩的坑（已写入记忆）

1. **FF 邮件里 checkbox 的渲染走 `isHtml=true` 分支**：`{inputs.privacy_consent_11}` 会被渲染成 `<ul><li>…</li></ul>`，纯文本正则会在第一个 `<` 处截断 ⇒ 要么按 HTML→纯文本断言，要么占位符用 **`.value`**（两个分支都输出内联纯文本）。
2. **FF 条目页只有下拉、没有「全部」项**，且 `entry_type=all` 返回 0 行 ⇒「全部」必须用空筛选。
3. **FF 打开单条详情会把该条 `unread → read`** ⇒ 任何"提前拍的服务端快照"跨脚本运行必然过期 ⇒ 「等于 DB」的断言必须放在 PHP 侧同一进程内独立复算（`[L7]`），浏览器侧只做**跨实现**比对（总览条 vs FF 自己的 counts）。
4. **只有 hash 不同的 URL，`page.goto` 不会重新加载文档** ⇒ 断言脚本行为必须 `goto + reload`（`hardGo()`）。
5. **wp-admin 永远等不到 `networkidle`**（心跳/长轮询）⇒ 一律 `domcontentloaded` + 显式等待。
6. **本机直连站点走 CF 边缘 25–40s 超时** ⇒ Playwright 必须 `--host-resolver-rules=MAP <host> 65.49.215.152` + `ignoreHTTPSErrors`。
7. **PHP 注释里写 `/var/www/*/wp-content` 会让 `*/` 提前闭合文档块** ⇒ 解析错误（本批真实踩到）。
8. **`wp db query` 不加 `--skip-column-names` 时第一行是表头** ⇒ 拿"第一行"做断言会打在字符串 `'to'` 上，连带产生一串假绿（本批真实踩到，已改）。
9. **`wf_fsmpt_email_logs.to` 存的是序列化数组**（`a:1:{i:0;a:1:{s:5:"email";s:28:"…";}}`）⇒ `LIKE '%addr%'` 仍能命中，但别假设它是纯地址。
10. **Playwright 命中校验**：`display:flex` 会盖掉 UA 的 `[hidden]{display:none}` ⇒ 自建隐藏块必须显式补 `#id[hidden]{display:none}`。
11. **生产 mu-plugin 的版本号在文件头**（`Version:`），与 `SF_FG_VERSION` 常量是两回事；`wp plugin list` 显示的是前者。

---

## 五、未做 / 待办

| 项 | 状态 | 触发条件 |
|---|---|---|
| Turnstile 正式启用 | 未做（裁决延后） | Sam 提供 CF sitekey/secret；届时 CSP 三处补 `challenges.cloudflare.com`（`script-src`/`frame-src`/`connect-src`，现为 Report-Only） |
| ~~form 8 通知占位符修正~~ | ✅ **已完成**（2026-10-12）—— 实际是 **5 个表单同一处缺陷**，已全部修好并用真通知验证 | 见 §七 |
| C 组边缘加固 | 待 24h 观察窗 | WAF 规则／提交端点限速／源站只放行 CF 网段 + `at` 自动回滚保险；**源站仍可直连绕过 CF 层** |
| 恢复自动回复 + 「仅非 spam 触发」守卫 | 待防护稳定 ≥1 周 | 观察 spam 表增速与真询盘量 |
| DMARC `p=none`→`p=quarantine` | 未做 | 硬约束：SPF/DKIM 未 100% 通过前绝不升档 |
| ~~运维手册修订~~ | ✅ **已完成**（2026-10-12）—— 实际**8 处**（不止两处）＋快速卡 1 处；docx/pdf/速查卡已重建 | 见 §七.4 |
| mu-plugin 文件头 `Version:` 未随行 bump | 4 个 mu-plugin 均显示 1.0.0/1.1.0 | 下次触碰对应文件时顺手改 |
| FF 6.2.14 → 6.2.15 | 有可用更新，本批未动 | 单独窗口评估 |

---

## 六、回滚方案

| 层 | 操作 |
|---|---|
| mu-plugin | `install -o apache -g apache -m 644 /root/h24b-backup/prod-zz-sf-form-guard.php.bak-20261012T043702Z /var/www/zxpet-v2/wp-content/mu-plugins/zz-sf-form-guard.php`（回到 H24 版 71 156 B）；或删文件彻底失效 |
| 限流计数 | `wp eval "sf_fg_rl_reset('<ip>');"`；或等 transient 3600 秒自然过期 |
| 自动加黑 | 复核页「改回正常」，或 `wp option delete sf_fg_blocklist` |
| cron | `wp cron event delete sf_fg_log_cleanup_event` |
| `wp-mail-logging` | `wp plugin activate wp-mail-logging`（表从未删过，恢复即双写） |
| 审计表清理 | 清理只删 `created_at < NOW()-90d` 的行；本次无存量超 90 天的行被删（基线 18 行全部保留期内） |

---

*执行：小宠（Sam 批准八项修订 + 四项裁决 + 两项中途裁决）。dev 全绿 → 生产部署 → 生产全量验收 → 零残留。*

---

## 七、追加工作（同日收尾；Sam 批准「顺手修掉」）

### 7.1 `form 8` 通知占位符 —— 修好并**用真通知验证**

| 项 | 值 |
|---|---|
| 目标行 | `wp_fluentform_form_meta` **id=39**（form 8「Admin Notification」） |
| **改前** | `Privacy Consent: {inputs.company_name_1}`　（766 B，sha256 `c7e2915e…`） |
| **改后** | `Privacy Consent: {inputs.privacy_consent_11.value}`　（776 B） |
| 应用回读 | 坏锚点残留 0 ／ 公司名 2（subject + Company 行）／ 目标串 1 ／ 长度差 **+10** ／ **反替换逐字节一致 = YES** |

**真通知验证（端到端，走真实访客路径）**：提交测试数据 → `insert_id 249` → 管理员通知**真发**到 `sales@zxpet.com`（FluentSMTP id **449**，`status=sent`）→ 从日志读回邮件正文：

```text
New inquiry received from the website:
Company: H24B Notif Verify (TEST)
Contact: Site Operator
Email: verify@example.com
Country: United States
Interested Dosage Form: Soft Chews
Notes: Internal end-to-end verification submitted by the site operator ...
Privacy Consent: I agree to the Privacy Policy          <-- 正确（勾选值）
```

断言 5 项全 PASS：勾选值 ✓ ／ 不显示公司名 ✓ ／ 未被 `<ul><li>` 包裹 ✓ ／ Company 行仍正常 ✓ ／ 六行字段齐全 ✓。
测试提交已按**测试邮箱精确定位**清理干净（残留 0）。工具：`tools/h24b_notif_verify.py` + 离线复核器 `tools/h24b_notif_body_check.py`。

**回滚（一条命令）**

```bash
cd /var/www/zxpet-v2 && SF_H24B_SITE=prod SF_H24B_MODE=restore \
  SF_H24B_FORM=8 wp eval-file /root/h24-tools/h24b_fix_privacy_line.php --allow-root
```

> 备份：服务器 `/root/h24b-backup/notif_privacy_raw.prod.8.json`；本地另存 `_backup/notif_placeholder_raw.prod.json`。

### 7.2 全量普查结论：**5 个表单的「Privacy Consent」行全是坏的**（三种坏法）

按 Sam 要求把 form 8/9/10/11/12 的通知模板**全部读了一遍**（工具 `tools/h24b_audit_notifs.php`，只读）：

| 表单 | feed | 改前 | 症状 | 改后 |
|---|---|---|---|---|
| 8 Get a Quote | 39 | `{inputs.company_name_1}` | 显示成公司名 | `{inputs.privacy_consent_11.value}` |
| 9 Request a Sample | 45 | `{inputs.company_name_1}` | 显示成公司名 | `{inputs.privacy_consent_12.value}` |
| 10 Book a Factory Tour | 51 | `{inputs.company_name_1}` | 显示成公司名 | `{inputs.privacy_consent_14.value}` |
| 11 Request COA | 57 | `{inputs.privacy_consent_9.i_agree_to_the_privacy_policy_9_1}` | **完全空白**（孤儿 key） | `{inputs.privacy_consent_9.value}` |
| 12 Feedback | 63 | `{inputs.privacy_consent_5.i_agree_to_the_privacy_policy_5_1}` | **完全空白**（孤儿 key） | `{inputs.privacy_consent_5.value}` |

成因：模板是从 form 8 复制出去的 —— 前两份**照抄了公司名占位符（改了字段没改值）**，后两份用了 FF 界面里「选项级」的 key，而 `ShortCodeParser` 只认 `{inputs.<字段>}` / `{inputs.<字段>.value}`，带选项后缀的**取不到 → 渲染为空**。

Sam 的裁决理由（「每天影响运营、单独走一次部署成本高」）对 9/10/11/12 完全适用，故**一并修掉**（超出原点的 4 处已在同一批次完成，备份齐备、可逐表单回滚）。

**dev 同步**：dev 形态与生产逐字一致，已同批 apply（5/5 已修正），两边状态统一。

### 7.3 字段对照表文档（新增）

`docs/form-notification-fields-2026-10-12.md`（24.7 KB / 690 行，脚本生成）—— 5 个表单的「字段清单 / 通知 feed / 主题与正文（原文+渲染）/ 占位符映射」，供以后改表单时对照。生成器：`tools/h24b_build_field_map.py`。

### 7.4 运维手册同步（实际 8 处 + 快速卡 1 处，非两处）

原以为只有 L153 与 L198 两处过期，实际 `WP Mail Log` 在手册里出现 **8 次**（L153 常见 5 问 / L198 技术栈表 / L226 后台菜单表 / L363 排查链 / L416 每周清单 / L449 日志位置 / L549 推演 / L635 速查表）＋ 快速卡 1 处。已全部改为 **FluentSMTP（Tools → Fluent SMTP → Email Logs）**，并在技术栈表注明「原 WP Mail Logging 1.16.0 已于 2026-10-12 停用，历史记录保留在 `wp_wpml_mails`（454 条）」。

**三件产物已重建**（避免 md 与 docx/pdf 静默分叉）：`ops-manual-v1.docx`（4.62 MB）、`ops-manual-v1.pdf`（6.70 MB / 45 页）、`ops-manual-quick-ref.pdf`（旧版已备份 `_backup/`）。
校验：docx/pdf 里 `WP Mail Log` 仅剩 1 处（＝刻意保留的「已停用」说明），`FluentSMTP` 7 处。

### 7.5 门禁新增两条防回退断言

`tools/h24_gate.py --live` 新增：
- **L8**：5 个表单 `Privacy Consent` 行全部为 `<字段>.value` 形态（跑 `h24b_fix_privacy_line.php status`）
- **L9**：通知模板普查无 R1 孤儿 / R2 跨语义（逐表单独立进程跑 `h24b_audit_notifs.php`）

### 7.6 ⚠️ 事故与处置：误删 1 条 spam 记录（如实记录）

**经过**：`h24b_notif_verify.py` 首版用 `MAX(id)` 当作「本次测试创建的 id」来清理。运行时测试提交因 `country_5` 取值非法被 FF 校验拒（HTTP 423，**未落库**），脚本仍按 `MAX(id)=247` 执行删除 —— **误删了攻击者（80.94.95.202）的一条第 spam 入库记录**。

**影响面（已核实）**：
- 该条本身就是垃圾询盘，业务数据无损失；
- **拦截证据链完整保留**：审计表 `wp_sf_form_spam_log` id=79 仍在（`submission_id=247`、ip、ua、email_domain、score=4、signals）；
- 后台复核页对 `submission_id > 0` 只做 `$wpdb->update(...WHERE id=247)` ⇒ **update 0 行，不报错、不影响功能**，仅该条的「释放」按钮无实际效果；
- MySQL **binlog 未开启**，无法按时间点精确恢复原文（已确认）。

**处置**：不伪造数据 —— 保留现状（审计证据完整），如实记录；并**修掉脚本根因**：清理一律按「本次测试独有的邮箱」精确定位（`response LIKE '%verify@example.com%'`），并删除遗留的按 id 删除分支。重跑后全 PASS，零残留。

### 7.7 观察窗数据（同日快照）

- 攻击者 **80.94.95.202** 当日累计触发 **24 次**，全部被拦（自动加黑阈值 24h≥50，尚未触发）；最近一次 13:22。
- 审计表 24 行**全部**来自该 IP，时间跨度 10:49 → 13:22（约 2.5 小时）。
- 管理员通知今日仅 44 封且**全部在 10:38（H24 上线）之前**；自动回复最后一封 06:37 < 10:38 ⇒ 两条「归零」结论在 v1.2.0 上继续成立。

### 7.8 本节产出的回滚命令汇总

```bash
# 5 个表单的 Privacy Consent 行（生产 / dev 各一条）
cd /var/www/zxpet-v2 &&           SF_H24B_SITE=prod SF_H24B_MODE=restore wp eval-file /root/h24-tools/h24b_fix_privacy_line.php --allow-root
cd /var/www/dev.zxpet.com/public && SF_H24B_SITE=dev  SF_H24B_MODE=restore wp eval-file /root/h24-tools/h24b_fix_privacy_line.php --allow-root
# 只回滚单个表单：再追加 SF_H24B_FORM=<id>
```

备份文件：`/root/h24b-backup/notif_privacy_raw.{prod,dev}.{8,9,10,11,12}.json`（含原始 value、改前/改后行、时间戳）。

---

*本节：小宠（Sam 批准「顺手修掉」+ 两条约束：①改完发真通知验证 ②立刻准备回滚）。dev 与生产同批修复，真通知验证 ALL PASS，门禁 64/0 + live 全绿。*

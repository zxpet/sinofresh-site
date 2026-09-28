# 上线 P1 构建 + P2 预验报告（2026-09-28）

> 执行范围：runbook v2 的 **P1（构建生产栈）→ P2（不经公网预验）**。**未切生产、未动 `/var/www/html` 与 `wordpress` 库**。
> P3（vhost 切换）**未执行**，等确认。
>
> ✅ **2026-09-28 16:25 更新：SMTP 已闭环。** P2 唯一卡点（prod 客户端密码失效）已修复并三步验收通过——
> 探针 `235` ✓ / 询盘重测日志 `status=sent` ✓ / 门 `--with-mail` **37/37** ✓。postfix 旧凭据一并换新（relay 实测 `250 Ok`）。
> **P2 全绿，P3 待你点头。** 详见 `docs/golive-smtp-rootcause-2026-09-28.md`。

---

## 一、P1 构建结果

| 项 | 值 |
|---|---|
| 新 docroot | `/var/www/zxpet-v2`（507 MB，owner `apache:apache`，无软链） |
| 新数据库 | `zxpet_prod`（utf8mb4 / utf8mb4_unicode_520_ci，51 张表，与 dev 同构） |
| DB 专用账号 | `zxpet_prod`@`localhost`（随机 36 位口令，仅授权 `zxpet_prod.*`；口令存服务器 `/root/.zxpet-prod-dbpass`，权限 600） |
| WP / PHP | 7.1.2 / 8.3.33（与 dev 一致） |
| 主题 | `sinofresh-theme` **2.10.88**，实拷贝（非软链），与 git 仓库 HEAD `dfa91ba` 对齐 |
| mu-plugins | **只有 `zz-sf-wps-consent-bridge.php`**（dev 的 lockdown / preflight / preflight.log 全部未带入） |
| wp-config | 由 dev 的生成后改写：DB 指向 `zxpet_prod`、**已删 `SF_DEV_LOCKDOWN`**、权限 `apache:apache 640`；`php -l` 通过 |
| 导入 | dev 库现导 dump（783 KB，51 表）→ `zxpet_prod`；URL 替换 `dev.zxpet.com → www.zxpet.com`（684＋102 处） |
| robots.txt | 物理文件，noindex＋AI 拦截版（`*` ＋ GPTBot / ClaudeAI 系 / PerplexityBot / Google-Extended 等 15 个 UA，全部 `Disallow: /`） |
| 测试数据清理（D3） | 已清空：WP Statistics（visitor 42 / pages 116 / relationships 612 / summary 9）、Fluent Forms 提交（21 条＋meta/明细/日志）、`wp_fsmpt_email_logs`、`wp_wpml_mails`（537）、`wp_actionscheduler_logs`。**表单定义（5 个 FF 表单）、26 页、7 文、21 条配方记录完好** |

### ⚠️ 关键决策：salts 不能全换（否则 SMTP 立刻失效）

FluentSMTP 的 SMTP 密码用 **AES-256-CTR** 加密存库，密钥＝**wp-config 的 `LOGGED_IN_KEY` + `LOGGED_IN_SALT`**（源码 `app/Functions/helpers.php` 实证）。runbook 原写「新随机 salts」→ 会导致导入后密码**解不开、SMTP 全线失效**。

处置：**`LOGGED_IN_KEY` / `LOGGED_IN_SALT` 沿用 dev，其余 6 个 salt（AUTH_KEY / SECURE_AUTH_KEY / NONCE_KEY / AUTH_SALT / SECURE_AUTH_SALT / NONCE_SALT）＋ `WP_CACHE_KEY_SALT` 全部换新**。13 项配置断言全过。已实测解密成功（168 字符密文 → 16 字符明文）。

（仅此一家插件用盐加密；全库扫描确认没有第二个盐加密密钥。）

---

## 二、P2 预验结果（临时 vhost，不经公网）

临时 vhost：`/etc/httpd/conf.d/zz-temp-v2-preverify.conf`，`Listen 127.0.0.1:8080`（**仅本机**，外网不可达），`ServerName www.zxpet.com` + `X-Forwarded-Proto: https → HTTPS=on`（避免 WP 跳到线上 https 主机）。

### 门：`tools/p2_preverify.py` → **34 项，34 通过，0 失败**（`--with-mail` 版 **37/37**，见 §3.8）

| 组 | 结果 |
|---|---|
| 首页/身份 | 200；canonical `https://www.zxpet.com/`；**无** `WWW-Authenticate`；**无** `X-Robots-Tag`；`noindex` meta 在位；主题 `ver=2.10.88`；HTML 内 0 处 `dev.zxpet.com` |
| robots.txt | 200；`User-agent: *` + `Disallow: /`；4 个指定 AI 爬虫全部点名；无遗留 Sitemap 行 |
| 全站可达 | **54 个已发布 URL 全 200**（26 页 ＋ 7 文 ＋ 21 配方）；**4 页引用的 55 张 uploads 图片全 200** |
| 接口面 | `/wp-json/` 200；`/wp-login.php` 200；`/wp-admin/` 302（→ 登录） |
| 栈身份 | `DB_NAME=zxpet_prod`；`home`/`siteurl`＝`https://www.zxpet.com`；`blog_public=0`（**noindex 期未放开**）；主题 sinofresh-theme |
| 封锁与同意 | mu-plugins 仅 `zz-sf-wps-consent-bridge.php`；dev-lockdown **未部署**；`consent_integration=wp_consent_api`；`wp_get_consent_type()=optin`；未同意时 `wp_has_consent('statistics')=false` |
| 询盘端点（负路径） | 蜜罐 400 ✓；伪造/过快时间戳 400 ✓；缺姓名 400 ✓（均不发送邮件） |
| 库内残留 | `wp_options` / `wp_posts` 中 `dev.zxpet.com` **0 行** |

### dev ↔ prod 首页逐字节对等核验

10 项结构指标（links 103 / imgs 30 / h2 12 / h3 47 / group 154 / form 1 / input 8 / button 9 / svg 27 / script 26）**逐项相同**。

归一化后**全部字节差异只有两处非确定性值**（表单 per-request nonce / hash）＋ dev 独有的 `noarchive` 一词（来自我们故意剔除的 dev-lockdown mu-plugin，`noindex, nofollow, noarchive` vs `noindex, nofollow`）。**结构漂移为零**。

---

## 三、SMTP：曾误判为腾讯限流 → 真因＝prod 密码失效 → **已修复闭环**

> ✅ **本节已闭环（16:25）。** 结论链：① 曾判「腾讯账号级限流」→ ② dev 15:57 两封都到货 ⇒ 限流假设被证伪
> → ③ 逐字节对比定位到 **prod 库 FluentSMTP 客户端密码失效**（salts 相同、导入逐字节忠实，非导入 bug）
> → ④ 覆盖修复 + postfix 凭据换新 + 三步验收全绿。权威取证见 `docs/golive-smtp-rootcause-2026-09-28.md`。
> 下方 3.x 的「限流 / postfix 触发风控」归因**作废**，保留仅作过程记录。

### 3.5 追加处置与更正（同日 15:05–15:15）

**① postfix 凭据已换成有效值，仍被拒 ⇒ 限流在腾讯侧、与配置无关**

`/etc/postfix/sasl_passwd` 已用**当前有效凭据**重写（备份 `sasl_passwd.bak.20260928`），`postmap` 重建。
随后**用新凭据做一次内部投递测试**（服务器 → `sales@zxpet.com`，零外部影响）：

```
postfix/smtp[…]: SASL authentication failed; server smtp.exmail.qq.com[101.32.113.90] said:
                 535 Error: authentication failed, system busy
… status=deferred (SASL authentication failed)
```

⇒ 修复动作正确，但**账号级限流仍在生效**（连刚刚成功过的凭据也被拒）。这不是我们能改的配置问题，只能等腾讯冷却 / 在企邮后台解封。

**② 队列已清空**：先删 25 封**不可投递**的（`*.example.invalid` / `*.example.com`），再删 25 封**内部/测试**的（18→`sales@`、5→`apache@`、4→`e2e-cert@`＋`sales@`、1→`sam@`、1→qq 测试件）。
**全量存档未动**：`/root/stuck-mail-20260928/`（51 个 `.eml`）＋ `stuck-mail-20260928.tgz`（50 KB）。

**③ 更正：那封"真实客户邮件"实为内部测试件，没有客户被耽误**

第一次判断（队列里唯一发往外部地址的信 = 真实询盘）**证据不足**，追加取证后推翻：

| 证据 | 内容 |
|---|---|
| 提交内容 | 表单 11「Request COA」，`company=sdsd`、`contact=ssd`（键盘乱敲），地址 `251817465@qq.com`，国家填 US，要 Soft Chews 的 COA + MSDS |
| **同一地址今天又用了两次** | dev 库 09-28 的两条「Get a Quote」提交（`wesdsd/fghjk`、`sdsd/ffggg`）**用的是同一个 QQ 地址** —— 也就是你配 SMTP 那段时间的手工表单测试 |
| 同批 4 条兄弟提交 | 同一时段（06:27–06:35）的 4 条全是我们的 E2E 机器人（`E2E Test Co` / `e2e-cert@example.com`） |

⇒ 该会话是**内部测试**，收件地址是你自己/同事的邮箱。**不需要重发、不需要还原**（`zxpet_prod` 的表单提交表保持 0 行，符合 D3「生产不带测试数据」的初衷）。

**④ D3 的一处副作用与结论**：TRUNCATE 清掉了 dev 里全部 22 条表单提交，**其中 1 条一开始被我当成真实询盘**。逐条核对后确认 22 条全为测试（E2E 机器人 / 乱敲内容 / 内部地址），**没有真实客户数据丢失**。教训：清测试数据应**按规则删**（按邮箱域名 / 来源 URL / 时间窗），不要整表 TRUNCATE。

### 3.6 配置快照与发送日志（15:14 补充证据）

**配置快照图**：`docs/golive-smtp-config-2026-09-28.png`（由 `wp option get fluentmail-settings` 实读渲染，密码掩码；非后台像素截图——临时 vhost 上 WP 认 `https://www.zxpet.com` 主机名，浏览器直登 admin 会跨域跳转，故未做 UI 截图）。

**`wp_fsmpt_email_logs` 实录**（生产栈，6 行）：

| id | 主题 | status | 应答 | 时间(站内时区 UTC+8) |
|---|---|---|---|---|
| 1 | [Inquiry] Website — P2 Preverify | **sent** | OK | 14:38:57 |
| 2 | [P2] SMTP test from production stack | failed | 422 认证失败 | 14:39:24 |
| 3 | [P2] SMTP test A (cli path) | failed | 422 | 14:40:19 |
| 4 | [Inquiry] Website — P2 Web Path | failed | 422 | 14:40:26 |
| 5 | [P2] SMTP retest after cool-down | failed | 422 | 14:42:15 |
| 6 | [Inquiry] Website — Fast | failed | 422 | 14:52:21 |

⇒ **配置本身已被 id=1 证明可用**（成功发送一次），之后全被账号级限流拦下。

### 3.7 冷却 45 分钟后的自动重测（15:24:15）— 仍被限流

```
P2 pre-verify: 37 checks, 35 passed, 2 failed
  FAIL inquiry happy path accepted (200 ok:true)  — 500 {"code":"sf_inquiry_mail","message":"We could not send that just now..."}
  FAIL mail transport reported the send as sent   — last log status: 'failed'
```

`--with-mail` 比基线多 3 项：happy path（依赖真实发信）、限流 429、邮件落库状态。
⇒ **34 项基线检查全过 ＋ 限流 429 也过**（35 passed）；2 个红全部是「真实发信成功」这条链。
**结论：限流仍在生效，非配置问题** —— 必须由腾讯侧解封（或更长冷却）。

### 3.8 修复执行与三步验收（16:15–16:24）— ✅ 闭环

用户确认方案 A 后执行。**只动 prod 的 `fluentmail-settings` option 与 postfix 凭据，未碰 docroot/DB 结构。**

**① 覆盖 fluentmail-settings（备份先行）**

```bash
# 备份（JSON + 原始 DB 值双份）
/root/prod-fms-backup-20260928-081513.json      # 1035 B  —— 回滚＝ wp option update fluentmail-settings --format=json < 该文件
/root/prod-fms-rawbackup-20260928-081513.txt    # 1318 B  —— 原始序列化值
# 覆盖：dev → prod
```

回读校验：prod 值 **逐字节 == dev 值**；密码密文 md5 `b3ac3c10c1508e8f911ee312f9251b88`（=dev，len 168）。

**② postfix 凭据换新**

`/etc/postfix/sasl_passwd` 里原是一个 **32 位失效密码**（md5 `a820bfaa…`，07:09 仍 535）。
处置：用 dev 的**有效**密码重建（备份 `sasl_passwd.bak.20260928-081625`）＋ `postmap` ＋ `systemctl reload postfix`。
实测发信：`status=sent (250 Ok: queued as …)`，队列清空。**postfix 这条独立问题同步闭环。**

**③ 三步验收（全绿）**

| 步 | 命令 | 结果 |
|---|---|---|
| 1 · 探针 | `php fms-probe.php PROD` ＋ `smtp-auth-probe.php PROD` | 解密 OK（明文 md5 `72275dd9…`）；直连 `235 Authentication successful` ✅ |
| 2 · 询盘重测 | POST `/wp-json/sinofresh/v1/inquiry`（经临时 vhost） | HTTP **200** `{"ok":true}`；`wp_fsmpt_email_logs` id=9 `status=sent` / `OK` ✅ |
| 3 · 门 | `python3 tools/p2_preverify.py --with-mail` | **37 checks, 37 passed, 0 failed** ✅ |

**④ 痕迹清理（P2 收尾）**

- `wp_fsmpt_email_logs` 10 行（全为 P2 测试）→ 归档 `/root/p2-email-logs-archive-20260928-082437.txt` 后删除，`AUTO_INCREMENT` 重置 1，**现 0 行**
- WP Statistics / Fluent Forms 提交表：**0 行**（无残留）；询盘限流 transient 无残留
- 服务器探针 `/tmp/{fms-probe,smtp-auth-probe,smtp-auth-probe2,pw-extract}.php`、`/tmp/{dev,prod}-fms*.json`、`/tmp/retest*.txt` **已删**（提取明文的临时文件用 `shred -u` 销毁）

### 已证实的部分

- FluentSMTP 配置完整且正确：`smtp.exmail.qq.com` / `465` / `ssl` / 账号 `sales@zxpet.com` / sender `SINO FRESH` / `force_from_email=yes`
- **14:38:49 有一封真实发送成功**：`[Inquiry] Website — P2 Preverify`，日志 `status=sent`、`provider=smtp`、`send_time_ms=8340`、SMTP 应答 `OK`
- 加密密码解密成功（沿用 `LOGGED_IN_KEY/SALT` 的决策由此验证）

### 之后全部失败，根因已查明

| 证据 | 内容 |
|---|---|
| 失败特征 | `422 SMTP Error: Could not authenticate.`；裸测（`smtplib`）得 `535 Error: authentication failed, system busy` |
| **换 IP 复测** | 从**本机（完全不同出口 IP）**用同一明文密码测试 → **同样 535**。⇒ 不是 IP 封禁，是**账号级**限流 |
| **根因** | 服务器 **postfix 长期用另一个 16 位密码**做 SASL relay（`/etc/postfix/sasl_passwd`，Sep 4 配置）→ 自 **Sep 24 起持续失败**，`journalctl` 记录 **3 天内 2724 次认证失败** ⇒ 腾讯把该账号当密码爆破，返回 "system busy" |
| 队列现状 | **50 封积压邮件（183 KB）**，最早 Sep 25；含 18 封 →`sales@`、8 封 →`e2e-cert@example.com`、21 封 →`sf-gate-sink@example.invalid`（测试） |

### 已执行的止血动作

1. **50 封全部逐封存档** `/root/stuck-mail-20260928/*.eml` ＋ 打包 `stuck-mail-20260928.tgz`
2. **`postsuper -h ALL`**：50 封全部 on hold ⇒ 停止失败认证风暴（可逆：`postsuper -H ALL`）
3. **发现并抢救 1 封真实客户邮件**：→ `251817465@qq.com`，主题 *Your document request — SINO FRESH*，**Sep 24 22:08 发出，4 天未送达**（COA 文档请求回执，含附件）。存 `lead-251817465-20260924.eml`

### 两个密码不一致（需你裁决）

| 位置 | 密码（md5 前 10 位） | 状态 |
|---|---|---|
| FluentSMTP（今天配的） | `fa667daf9f` | 成功过一次，现被限流 |
| postfix SASL（Sep 4 配的） | `0596c0aa36` | **已失效**（Sep 24 起 2724 次失败） |

推测：Sep 24 前后该「客户端专用密码」被重新生成/删除，postfix 手里的成了废 credential，而后它反复重试把账号送进了风控。

---

## 四、过程中的两个事故（已恢复，如实报）

### ① httpd 短暂停机 ~2 分钟（graceful reload 失败）

把临时 vhost 的 `Listen 8080` 改成 `Listen 127.0.0.1:8080` 后执行 `systemctl reload httpd`（graceful）→ 旧通配 socket 仍被持有，新绑定失败：
`make_sock: could not bind to address 127.0.0.1:8080` → `no listening sockets available, shutting down` ⇒ **80/443 全部停止监听**。
**已 `systemctl restart httpd` 恢复**：80/443/8080 全部回来，旧站仍为维护页 302、dev 仍为 401、临时 vhost 200。
影响面：旧站当时只有维护页，无真实访问损失；但属**我的操作失误**，与「不碰生产」原则有偏差，故明确记录。
**教训（已写入 runbook v3）**：改变 `Listen` 的**地址**必须用 `restart`，不能用 `reload`。

### ② 一个凭据被打印到本会话输出（建议轮换）

查 postfix 配置时我的掩码正则只覆盖了用户名部分，`/etc/postfix/sasl_passwd` 里的**密码明文（16 位）被打印**在本会话输出中。该密码已失效（正是上面那个 2724 次失败的 credential），但**仍建议在企邮后台轮换一次客户端专用密码**。

### ③（已加固）临时 vhost 初版绑在所有网卡

最初 `Listen 8080` 会让任何人访问 `IP:8080` 看到未发布站点。已收紧为 `Listen 127.0.0.1:8080`，并从本机验证外网不可达。

---

## 五、需要你确认 / 决定的点（P3 前）

| # | 事项 | 状态 / 建议 |
|---|---|---|
| 1 | **SMTP 密码失效**（原唯一卡点） | ✅ **已闭环**：覆盖 prod 的 `fluentmail-settings` + postfix 换新 + 三步验收全绿（见 §3.8） |
| 2 | ~~postfix relay 凭据~~ | ✅ **已闭环**：换为有效密码，relay 实测 `250 Ok` |
| 3 | ~~积压 50 封邮件~~ | ✅ **已闭环**：逐封存档（`/root/stuck-mail-20260928/` ＋ `.tgz`），队列清空；经复核无真实客户邮件 |
| 4 | **泄露的旧密码** | 被打印的是 postfix 里**已被替换掉的失效密码**，风险已消除。如仍想彻底了断，可在企邮后台再轮换客户端密码（换后需同步 FluentSMTP + postfix 两处） |
| 5 | **`noarchive` 第三道保险** | dev 有、prod 无。可启用现成文件 `zz-noindex-zxpet.conf.disabled`（`X-Robots-Tag: noindex,nofollow,noarchive`），建议 P3 时一并做 |
| 6 | **`wp_gf_*` 遗留 6 张表** | 生产库仍有 Gravity Forms 时代残留（entry 136 行等）。建议 P3 批次一并 drop |
| 7 | **站点标题** | `blogname` ＝ `sinofresh`（首页 `<title>sinofresh</title>`）。是否改成 SINO FRESH 品牌写法由你拍板 |

---

## 六、P3 执行预案（等你点头）

改 **3 个文件、4 处** `DocumentRoot`（＋对应 `<Directory>`）：

| 文件 | 位置 |
|---|---|
| `/etc/httpd/conf.d/zxpet.com.conf` | `:80` vhost（含 apex→www 301） |
| `/etc/httpd/conf.d/zxpet.com-le-ssl.conf` | `:443` vhost |
| `/etc/httpd/conf.d/wordpress-zxpet.conf` | `:80` 与 `:443` 两个 vhost（**www 的实际命中者**，按 conf.d 字典序先加载） |

全部 `DocumentRoot /var/www/html` → `/var/www/zxpet-v2`，然后 `apachectl -t && systemctl reload httpd`（**只改路径、不改 Listen，reload 安全**）。
回滚＝三处改回 `/var/www/html` + reload（<1 分钟；DB 全程不动，`wordpress` 库未写）。

**P3 前待办（更新）**：
- ✅ SMTP 三步验收通过（§3.8）
- ✅ 清测试痕迹（`wp_fsmpt_email_logs` 归零、探针删除）
- ⬜ 删临时 vhost：`rm /etc/httpd/conf.d/zz-temp-v2-preverify.conf && apachectl -t && systemctl reload httpd`
- ⬜（可选，随 P3 一并）启用 `noarchive` 头、drop `wp_gf_*` 6 张表
- **P3 执行前先 `httpd -t` 自检**（现为 `Syntax OK`）＋ 复核 4 处 `DocumentRoot` 仍为 `/var/www/html`（现均如此）

---

## 七、关键路径与命令

```bash
# 新栈
/var/www/zxpet-v2                # docroot（无软链）
zxpet_prod                       # DB（专用账号 zxpet_prod@localhost）
/root/golive-build-20260928-0633/db-sinofresh-fresh.sql.gz   # 导入源
/root/.zxpet-prod-dbpass         # DB 口令（600）

# 备份（P0）
/root/golive-backup-20260928-0520/   # 两库 dump + 旧 docroot + dev 快照 + httpd 配置 + sha256

# 抢救的邮件
/root/stuck-mail-20260928/lead-251817465-20260924.eml   # 真实 COA 询盘
/root/stuck-mail-20260928.tgz                           # 50 封全量存档

# 门
python3 tools/p2_preverify.py              # 34/34（只读）
python3 tools/p2_preverify.py --with-mail  # 追加 happy path + 429 + SMTP 实发
```

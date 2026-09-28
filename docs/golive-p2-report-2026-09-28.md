# 上线 P1 构建 + P2 预验报告（2026-09-28）

> 执行范围：runbook v2 的 **P1（构建生产栈）→ P2（不经公网预验）**。**未切生产、未动 `/var/www/html` 与 `wordpress` 库**。
> P3（vhost 切换）**未执行**，等确认。

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

### 门：`tools/p2_preverify.py` → **34 项，34 通过，0 失败**

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

## 三、SMTP：配置正确，但账号被腾讯限流（**P2 唯一未闭环项**）

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

| # | 事项 | 建议 |
|---|---|---|
| 1 | **SMTP 限流** | 已挂自动单次重测（约 25 分钟后）。若仍 535：请你登录**腾讯企业邮箱管理后台**看「登录/发信记录」是否有异常锁定，必要时解封；并把**当前有效的客户端专用密码**告诉我 |
| 2 | **postfix relay 修复** | 二选一：① 把 postfix 的 SASL 密码换成当前有效密码（系统级邮件恢复发送）② 去掉 relay 只留 FluentSMTP 发信。**建议①**，否则积压队列与新系统邮件会再次触发风控 |
| 3 | **积压的 50 封** | 建议：测试件（example.invalid / example.com / sf-gate-sink）删除；**那封真实 COA 询盘**我另行重发（现在 SMTP 不通） |
| 4 | **泄露的旧密码** | 建议在企邮后台轮换客户端专用密码（旧的本已失效，属保险动作） |
| 5 | **`noarchive`** | dev 有、prod 无（来自被剔除的 lockdown 插件）。可加 `X-Robots-Tag: noindex,nofollow,noarchive`（服务器现成文件 `zz-noindex-zxpet.conf.disabled` 可直接启用）作第三道保险，或保持现状 |
| 6 | **`wp_gf_*` 遗留表** | 生产库里还有 Gravity Forms 时代 6 张空/残表（entry 136 行等）。建议本次一并 drop，或留下次 |
| 7 | **站点标题** | `blogname` ＝ `sinofresh`（首页 `<title>sinofresh</title>`，与 dev 一致，非本批引入）。上线前是否要改成 SINO FRESH 品牌写法？ |

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

**P3 前待办**：SMTP 重测通过 → 删临时 vhost（`rm zz-temp-v2-preverify.conf` + reload）→ 清测试会话（`wp_statistics`、`wp_fsmpt_email_logs` 里 P2 的探测记录）。

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

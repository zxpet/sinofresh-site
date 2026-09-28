# 生产上线 Runbook（2026-09-25 起草 / 09-28 v2：noindex 版 + P0 已执行 / 09-28 v3：P1+P2 实测回填）

> 状态：**P0 备份 ✅、P1 构建 ✅、P2 预验 ✅（34/34，SMTP 一项待重测）**；**P3 未执行，等确认**。
> v2 修订（noindex 指令）：**P1.7 blog_public 保持 0**、**P1.8 robots.txt＝AI 拦截版**、P2/P4 断言反转。
> v3 修订（P1/P2 实测）：**salts 只换 6 个（见 P1.6）**、**P2 用 loopback 临时 vhost**、**改 Listen 必须 restart 不能 reload**、**SMTP 受账号级限流影响（见 §5）**。
> 回滚原则：旧生产（`/var/www/html` + DB `wordpress`）**整个保留不动**，回滚＝vhost 指回去，<1 分钟。
> 详细实测记录：`docs/golive-p2-report-2026-09-28.md`。

## 0. 勘察事实（2026-09-25 实测）

| 项 | dev（新站） | 生产（旧站） |
|---|---|---|
| docroot | `/var/www/dev.zxpet.com/public` | `/var/www/html` |
| DB | `sinofresh`（11.3 MB，prefix `wp_`） | `wordpress` |
| WP / PHP | 7.1.2 / 8.3.33 | 7.1.1 / 8.3.33 |
| 主题 | sinofresh-theme 2.10.88（软链→site-repo） | generatepress |
| 关键插件 | Fluent Forms 6.2.14 / TP 3.3.6 / WPS 14.16.14 / fluent-smtp | rank-math / fluent-smtp / puffergo / naibabiji |
| blog_public | 0（封锁中） | 1 |
| home/siteurl | https://dev.zxpet.com | https://www.zxpet.com |
| uploads | 67 MB | 12 MB |
| robots.txt | `Disallow: /` | — |
| mu-plugins | dev-lockdown / preflight / wps-consent-bridge | 无 |
| 磁盘余量 | 14 G（够） | |
| 证书 | `/etc/letsencrypt/live/zxpet.com/`（SAN＝zxpet.com + www.zxpet.com，直接可用） | |
| 443 vhost | `zxpet.com-le-ssl.conf`，DocumentRoot=/var/www/html | |

## 1. 策略：新目录 + 新 DB 晋升（方案 A）

不用原地升级 `/var/www/html`（旧站内容与 dev 完全不同源，原地拼装风险高、不可回滚）。
新站整体晋升为一个**新 docroot + 新 DB**，vhost 切 DocumentRoot 一刀切换。

**架构决策点（需确认）**：
- **D1 主域**：维持 `https://www.zxpet.com`（现状、SEO 延续、证书 SAN 已覆盖）。apex `zxpet.com` 301→www（现 vhost 已是这么做的）。
- **D2 旧生产内容**：`/var/www/html` + DB `wordpress` 原样保留作回滚（推荐），暂不清理不归档。
- **D3 dev 数据携出物**：dev DB 里的 WP Statistics 统计与 Fluent Forms 测试提交是否随迁？
  建议：迁移时 **TRUNCATE WP Statistics 表 + FF 测试提交**（生产不带测试数据），统计从零开始。
- **D4 CF 面板两件**（本机无 API token，需你手配，可同窗口做）：
  ① rate limit rule：`http.request.uri.path eq "/wp-json/sinofresh/v1/inquiry" and http.request.method eq "POST"`（建议加 `and not http.host eq "dev.zxpet.com"` 以免挡住 dev 的门测试），阈值 1 req / 60s / per IP，action=Block 60s——与服务器侧 60s 对齐，两层叠加；
  ② dev 域名 Bypass cache rule（dev-lockdown §8.1 遗留，顺手）。

## 2. 阶段与验收

### P0 备份（不动状态）——✅ 已执行 2026-09-28
- `mysqldump` sinofresh + wordpress 两库 → `/root/golive-backup-20260928-0520/`
- `tar` `/var/www/html` 全量 → 同目录；额外：dev docroot 此刻快照（上线栈以此为准）；`/etc/httpd/conf.d/` 全量副本
- 验收 ✅：gzip -t 通过、wordpress 22 / sinofresh 51 张 CREATE TABLE、`sha256sum -c` 全 OK（manifest 在同目录）

### P1 构建新栈（生产不受影响）——✅ 已执行 2026-09-28
> 实测产出：`/var/www/zxpet-v2`（507 MB，无软链）＋ DB `zxpet_prod`（专用账号 `zxpet_prod@localhost`，口令存 `/root/.zxpet-prod-dbpass`，600）。导入源 `/root/golive-build-20260928-0633/db-sinofresh-fresh.sql.gz`。
> D3 已执行：清空 WP Statistics（visitor 42/pages 116/rel 612/summary 9）、FF 提交 21 条＋明细、`wp_fsmpt_email_logs`、`wp_wpml_mails` 537、`wp_actionscheduler_logs`；**表单定义 5 个 / 26 页 / 7 文 / 21 配方完好**。
1. `rsync -aL`（**-L 解软链**）dev public → `/var/www/zxpet-v2`，**剔除**：
   `wp-config.php`、`mu-plugins/zz-sf-dev-lockdown.php`、`zz-sf-preflight.php`、`zz-sf-preflight.log*`、`themes/sinofresh-theme-preflight/`、`wp-content/upgrade/`、`cache/`
   （实测确认：目标 0 软链、0 dev-only 残留、主题实拷贝＝git HEAD）
2. mu-plugins 只留 **`zz-sf-wps-consent-bridge.php`**
3. 主题解软链：`rsync -aL` 后 sinofresh-theme 已是实拷贝（本次＝`dfa91ba` / 2.10.88）
4. DB：`CREATE DATABASE zxpet_prod`（utf8mb4/utf8mb4_unicode_520_ci）→ 建专用账号 → 导入 dump →（D3）清统计/测试提交
5. `wp search-replace 'https://dev.zxpet.com' 'https://www.zxpet.com' --all-tables --precise`，再补一遍裸 `dev.zxpet.com`（实测 684＋102 处；复扫 0 残留）
6. 新 `wp-config.php`：指向 zxpet_prod、**无 `SF_DEV_LOCKDOWN`**、**salts 只换 6 个**（见下 ⚠️）、`WP_CACHE_KEY_SALT` 换新、权限 `apache:apache 640`
   ⚠️ **`LOGGED_IN_KEY` / `LOGGED_IN_SALT` 必须沿用 dev**：FluentSMTP 的 SMTP 密码用 AES-256-CTR 加密存库，**密钥就是这两个 salt**（`app/Functions/helpers.php` 实证；`FLUENTMAIL_ENCRYPT_*` 未定义）。换成新 salts ⇒ 密码解不开、SMTP 全线失效。其余 6 个 salt（AUTH_KEY / SECURE_AUTH_KEY / NONCE_KEY / AUTH_SALT / SECURE_AUTH_SALT / NONCE_SALT）＋ `WP_CACHE_KEY_SALT` 正常换新。
7. ~~`wp option update blog_public 1`~~ **v2：跳过此步，blog_public 保持 0**（sinofresh 库本就是 0；noindex 阶段指令，放开收录时才改 1）
8. `robots.txt` **v2：noindex＋AI 拦截版**（物理文件，物理 robots 存在时 WP 虚拟 robots 不生效）：
```
User-agent: *
Disallow: /
User-agent: GPTBot
Disallow: /
User-agent: ClaudeBot
Disallow: /
User-agent: PerplexityBot
Disallow: /
User-agent: Google-Extended
Disallow: /
```
（`blog_public=0` 同时输出 `<meta name="robots" content="noindex">` 作第二道保险）
9. Basic auth / X-Robots-Tag 只存在于 dev vhost——新 vhost 重写时天然不带（→ §9 第 1/2/5 项）；`.htpasswd` 是 dev 实体**保留不动**
10. 权限：`chown -R apache:apache`，目录 755、文件 644、wp-config 640
11. 验收 ✅：`wp core verify-checksums`（仅预已知的 php-ai-client 差异）、`wp plugin list` 与 dev 一致（仅少两个 dev-only mu-plugin）、首页 200、`blog_public=0`

### P2 切换前预验（不经公网）——✅ 已执行 2026-09-28（门 34/34）
- 临时 vhost `/etc/httpd/conf.d/zz-temp-v2-preverify.conf`：
```
Listen 127.0.0.1:8080            # ⚠️ 必须绑 loopback，否则 IP:8080 就能看到未发布站点
<VirtualHost *:8080>
    ServerName www.zxpet.com
    ServerAlias zxpet.com
    DocumentRoot /var/www/zxpet-v2
    <Directory /var/www/zxpet-v2>
        AllowOverride All
        Require all granted
    </Directory>
    SetEnvIf X-Forwarded-Proto "^https$" HTTPS=on   # 让 WP 不跳到线上 https 主机
    ErrorLog /var/log/httpd/zxpet-v2-preverify-error.log
    CustomLog /var/log/httpd/zxpet-v2-preverify-access.log combined
</VirtualHost>
```
- 请求方式：`curl -H 'Host: www.zxpet.com' -H 'X-Forwarded-Proto: https' http://127.0.0.1:8080/…`（在服务器上执行）
- ⛔ **改 `Listen` 的地址必须 `systemctl restart httpd`，`reload`（graceful）会因旧 socket 未释放而 `could not bind` → 所有 vhost 停止监听**（2026-09-28 实测踩坑，见报告 §4①）。仅改 `DocumentRoot` 时 `reload` 安全。
- 验收门 `tools/p2_preverify.py`（默认只读；`--with-mail` 才发信）：
  54 个 URL 全 200（26 页/7 文/21 配方）、55 张 uploads 图片 200、canonical、noindex meta、robots.txt AI 拦截版、无 `WWW-Authenticate`/`X-Robots-Tag`、`blog_public=0`、mu-plugins 只 1 个、同意三断言、询盘端点 3 条负路径
- dev↔prod 首页归一化对等：10 项结构指标逐项相同，全字节差异只剩 nonce/hash ＋ dev 的 `noarchive`
- 验收后**删除临时 vhost**（`rm` + `systemctl reload httpd`）

### P3 切换（秒级）——**未执行，等确认**
- **改 3 个文件、4 处** `DocumentRoot`（＋对应 `<Directory>`），全部 `/var/www/html` → `/var/www/zxpet-v2`：
  | 文件 | 位置 | 说明 |
  |---|---|---|
  | `/etc/httpd/conf.d/zxpet.com.conf` | `:80` vhost | 含 apex `zxpet.com` → `https://www.zxpet.com` 301 |
  | `/etc/httpd/conf.d/zxpet.com-le-ssl.conf` | `:443` vhost | apex https |
  | `/etc/httpd/conf.d/wordpress-zxpet.conf` | `:80` 与 `:443` **各一处** | **www 的实际命中者**（conf.d 字典序在 `zxpet*.conf` 之前） |
  全局 Includes 无需动（`zz-security-headers.conf` / `zxpet-performance.conf` / `zxpet-seo-redirects.conf` 对新栈同样生效）
- `apachectl -t && systemctl reload httpd`（**只改路径、未增删 `Listen`，reload 安全**）
- 停机窗口＝reload 一瞬，无维护页需要；回滚＝三处改回 `/var/www/html` + reload（旧站与 `wordpress` 库全程未写）

### P3 前待办（2026-09-28 实测新增）
1. **SMTP 重测通过**（见 §5）；未通过前切过去＝询盘邮件静默丢件。**卡点＝腾讯账号级限流**（凭据已核对正确、postfix 已换用有效凭据，仍 535）⇒ 需等冷却或在企邮后台解封
2. **postfix relay**：凭据已换为有效值（备份 `.bak.20260928`）＋ `postmap`；队列已清空，不再有失败认证风暴
3. ~~积压队列~~ **已完成**：逐封存档后清空（无真实客户邮件）
4. **删除临时 vhost** + reload
5. 清 P2 探测痕迹：`wp_fsmpt_email_logs` / `wp_statistics_*`（本轮探测记录）

### P4 上线后自检（§9 末尾两条 + 扩展）——v2 断言反转
```bash
curl -sI https://zxpet.com/ | grep -iE "www-authenticate|x-robots-tag"   # 应无输出（WWW-Authenticate 无；X-Robots-Tag 无）
curl -s  https://zxpet.com/ | grep -o "<meta name=.robots.[^>]*>"        # v2：应有 noindex（内容期）
curl -s  https://zxpet.com/robots.txt                                    # v2：应有全站 Disallow + 4 个 AI UA 段
```
- 扩展：首页/表单页 200、inquiry 60s 节流 429、consent 门（未同意 0 hit）、sitemap、SEO 头、CF 缓存命中率
- dev 站保持封锁不动（继续当开发环境，DB 已导出快照）

### P6 放开收录（内容确认后，用户手令才执行）
- `wp option update blog_public 1`
- robots.txt 换正式版（`Disallow: /wp-admin/` 型）
- Google Search Console 提交 sitemap

### P5 回滚（随时可执行）
- vhost DocumentRoot 指回 `/var/www/html` + `systemctl reload httpd`
- DB 无需动（wordpress 库全程未写）

## 3. §9 十一项映射核对表

| §9 项 | 本 runbook 处置 |
|---|---|
| 1 Basic Auth / 2 .htpasswd / 5 X-Robots-Tag | 新 vhost 不含；.htpasswd 保留给 dev（退役时再删） |
| 3 meta robots 门控 | rsync 剔除 dev-lockdown mu-plugin |
| 4 SF_DEV_LOCKDOWN | 新 wp-config 不写 |
| 6 robots.txt | P1.8 v2：noindex＋AI 拦截版（放开时换正式版） |
| 7 blog_public | v2：P1.7 跳过、保持 0（noindex 期）；P6 放开 |
| 9 CF cache rule | D4② dev bypass 保留（dev 还在）；生产无 bypass 规则 |
| 10 CF Access / IP 白名单 | 未启用，N/A |
| 11 mu-plugins 单独部署 | P1.2 只带 consent-bridge |

## 4. 明确不做

- 不删 `/etc/httpd/.htpasswd-dev.zxpet.com`（dev 仍在用）
- 不清理 `/var/www/html` 与 `wordpress` 库（回滚资产）
- 不动 dev 站封锁（dev 继续开发）
- CF 面板操作（D4）由你手配，我只提供表达式与验证清单

---

## 5. 邮件链路真相（2026-09-28 实测，切前必读）

**两条互不相干的发信通道**：

| 通道 | 谁在用 | credential | 2026-09-28 状态 |
|---|---|---|---|
| FluentSMTP（WP 插件，直连） | 网站所有 `wp_mail()`：询盘、表单通知、COA | DB 里 AES 加密（密钥＝`LOGGED_IN_KEY/SALT`） | 参数正确；**14:38:49 实发成功一次**；随后被腾讯账号级限流 |
| postfix relay（系统 MTA） | `php mail()` 兜底、cron、系统邮件 | `/etc/postfix/sasl_passwd`（明文，**另一个旧密码**） | **自 Sep 24 起持续失败（3 天 2724 次认证失败）** |

- postfix：`relayhost=[smtp.exmail.qq.com]:587`、`smtp_sasl_auth_enable=yes`、`inet_interfaces=loopback-only`
- **根因链**：旧 credential 失效 → postfix 每几分钟重试 → 大规模失败登录 → 腾讯判定异常 → 账号返回 `535 authentication failed, system busy`（换 IP 复测同样 535 ⇒ 账号级，非 IP 级）
- **止血**：`postsuper -h ALL` 暂停全部 → 逐封存档 `/root/stuck-mail-20260928[.tgz]`（51 个 `.eml`）→ 复核后**清空队列**（先 25 封不可投递测试件，再 25 封内部/测试件；无真实客户邮件，见报告 §3.5③）
- ✅ **凭据已修**：`/etc/postfix/sasl_passwd` 换成当前有效值（备份 `.bak.20260928`）＋ `postmap`；但**用新凭据的内部投递测试仍 535** ⇒ 限流在腾讯侧，只能等冷却/后台解封
- **❗被掩码漏掉的泄露**：查配置时 `sasl_passwd` 的密码明文被打印到会话输出 → **建议轮换该客户端专用密码**（该密码本就已失效，属保险动作）

### SMTP 验证纪律（本批踩坑）
- ⛔ **不要连续发测试邮件**：短时间多次认证/发信会触发腾讯风控，可能让本来正常的 credential 也被拒（本批连续 4 次重测后全线 535）
- ✅ 正确做法：一次发送 → 看 `wp_fsmpt_email_logs.status=sent` ＋ `response` → 失败就等冷却（≥30 分钟）再单发一次
- ✅ 独立证据：`wp eval 'echo fluentMailEncryptDecrypt($blob,"d");'` 只看**长度**即可证明解密是否成立（不必打印明文）
- ✅ 换 IP 复测可区分「IP 封禁」与「账号限流」

---

## 6. CF 面板（你手配，P3 前顺手）

① rate limit rule：`http.request.uri.path eq "/wp-json/sinofresh/v1/inquiry" and http.request.method eq "POST"`，阈值 1 req / 60s / per IP，action=Block 60s（与服务器侧 60s 对齐）
② dev 域名 Bypass cache rule（dev-lockdown §8.1 遗留）

# dev.zxpet.com 封锁与反索引（2026-09-20）

> 目标：把未上线的临时域名 `dev.zxpet.com` 对搜索引擎与 AI 爬虫彻底关闭，且**完全不影响** `zxpet.com` / `www.zxpet.com`。
> 执行时间：2026-09-20 14:18 UTC（北京时间 22:18）。执行人：运维助手（root SSH）。
> **本文件不含任何密码。** 凭据位置见 §7。

---

## 0. TL;DR

| 项 | 结果 |
|---|---|
| 改动的文件 | **1 个既有文件**（dev vhost）+ **3 个新增/追加**（htpasswd、mu-plugin、wp-config 一行） |
| 生产站是否被触碰 | **否**。`conf.d` 全量 sha256 比对：只有 `dev.zxpet.com.conf` 变了 |
| 现在匿名访问 dev | **401 Unauthorized**（含 `/zh/` 全站） |
| 现在带凭据访问 dev | 200，且响应头带 `X-Robots-Tag: noindex, nofollow, noarchive` |
| 生产站现状 | 与改动前逐字节一致（302 → maintenance.html） |
| 仍在改的任务 | 主题仓库 `git status` 空；robots.txt / .htaccess 未动；页面 DOM 零回归 |
| **仍需人工完成** | **Cloudflare 边缘缓存清理** + 可选的 CF Access 升级（§8） |

---

## 1. 环境实测（与「外部检测」结论的差异）

**必须先纠正一件事**：交办说明里的「没有 robots.txt、没有 noindex 响应头」**与实测不符**。
三层防护里的两层**早就存在**，真正缺的只有 HTTP 认证。逐条列出：

| 交办说明 | 实测结论 | 证据 |
|---|---|---|
| 没有 HTTP 认证 | ✅ **成立**，全机无任何 `AuthType` | `grep -rniE "AuthType\|AuthUserFile" /etc/httpd/` → 空 |
| 没有 robots.txt | ❌ **不成立** | 物理文件 `public/robots.txt` 自 2026-09-20 05:46 存在（567 B），`Disallow: /` + 16 个 AI 爬虫分节 |
| 没有 noindex 响应头 | ❌ **不成立** | `https://dev.zxpet.com/` 响应头已含 `x-robots-tag: noindex, nofollow, noarchive`（源站与 CF 边缘均可见） |
| `<head>` 里的 meta robots | ⚠️ **存在但缺一项** | 实为 `<meta name='robots' content='noindex, nofollow'>` —— **少了 `noarchive`**，且来源于 DB 选项而非环境开关 |

> 推测外部检测是在 2026-09-20 05:46 之前跑的（站点 05:38 才迁移上云，05:46 才加上 robots.txt / .htaccess / X-Robots-Tag）。
> 无论如何，外部检测唯一命中的空白项——**HTTP 认证**——确实空白，且它恰恰是最关键的一层，本次已补上。

### 1.1 部署环境（已查明，无需猜测）

| 项 | 值 |
|---|---|
| 主机 | `65.49.215.152`（搬瓦工 VPS），AlmaLinux 9.7，root 免密 SSH 可用 |
| Web 服务器 | **Apache 2.4.62**（不是 Nginx）。`auth_basic / authn_file / authz_core / authz_user / headers / rewrite` 均已加载 |
| PHP | 8.3.33（`X-Powered-By: PHP/8.3.33`） |
| 前置 | **Cloudflare**（`server: cloudflare`），dev 与 prod 均代理 |
| dev vhost | `/etc/httpd/conf.d/dev.zxpet.com.conf`，DocumentRoot **`/var/www/dev.zxpet.com/public`** |
| dev 应用 | 独立 WordPress（DB `sinofresh`，`blog_public=0`，`home=siteurl=https://dev.zxpet.com`） |
| **生产 vhost（同机）** | `wordpress-zxpet.conf`(www, :80+:443)、`zxpet.com.conf`(:80)、`zxpet.com-le-ssl.conf`(:443)，DocumentRoot **`/var/www/html`**（另一套独立 WP，现为 maintenance 占位） |
| 代码仓库 | **仅** `/var/www/dev.zxpet.com/site-repo` 是 git 仓库；`public/` 不是；`themes/sinofresh-theme` 是指向 site-repo 的软链 |
| 关键隔离事实 | `public/wp-content/mu-plugins/` 是**真实目录、不在任何 git 仓库内** → 放封锁插件天然不进仓库 |

> ⚠️ **生产站与 dev 站同机**，所以「只对 dev 生效」不是自动成立的，必须靠 vhost / DocumentRoot / 路径隔离逐条保证。
> 本次的实现方式即建立在这一点上：所有改动都绑定在 `dev.zxpet.com` 这个 ServerName 或 `/var/www/dev.zxpet.com/public` 这个路径上。生产用的是 `/var/www/html`，两者无交集。

---

## 2. 四层防护：实施前状态 → 实际改动

| 层 | 实施前 | 本次动作 |
|---|---|---|
| **A** HTTP Basic Auth | ❌ 无 | ✅ **新增**（vhost `<Directory>` ×2） |
| **B** `X-Robots-Tag` 响应头 | ⚠️ 有，但 `Header set` 不覆盖 401/403 | ✅ **升级为 `Header always set`** |
| **C** dev 专用 `robots.txt` | ✅ 已存在且正确 | ➖ **不动**（已符合要求，且 `public/robots.txt` 与 WP 虚拟 robots 都指向同一结论） |
| **D** `<head>` meta robots | ⚠️ 有 `noindex, nofollow`，缺 `noarchive`，且来自 DB 选项 | ✅ **新增 mu-plugin**（环境常量 + 主机名双重门控），补上 `noarchive` 并改为显式声明 |

### 2.1 一个必须点明的坑（第 A 层的关键）

dev vhost 的 `<Directory>` 块原本是：

```apache
Header set X-Robots-Tag "noindex, nofollow, noarchive"
AllowOverride All
Require all granted
```

**如果只在后面追加 `Require valid-user` 而不删掉 `Require all granted`，认证会被完全绕过** ——
Apache 2.4 里同一 section 内多条 `Require` 是**隐式 `RequireAny`（或）**，
`Require all granted` 会让所有请求都通过，Basic Auth 形同虚设，而且**外表看不出任何异常**（照样返回 200）。
本次是**替换**掉该行，不是追加。

---

## 3. 改动清单（逐项，含 sha256）

改动前备份目录：**`/root/dev-lockdown-20260920-141751/`**（含备份前的全部 `conf.d/*.conf`、`sha256-before.txt`、封锁前 curl 基线）。

### 3.1 `/etc/httpd/conf.d/dev.zxpet.com.conf`（既有文件，被改）

- `sha256` `c96f22bae7db8e7e9f6ee2be3157c6b07927c59a02e7e5933a1a901e8590eedb`
  → `de50755c9fd621e80dd2bd974936c4bdb2465922fdd177dde20ad7035d0a8434`
- 文件头新增 13 行说明块（标注 DEV-ONLY、生产 vhost 位置、删除步骤）
- **两个** `<Directory /var/www/dev.zxpet.com/public>` 块（`:80` 与 `:443`）内容改为：

```apache
    <Directory /var/www/dev.zxpet.com/public>
        AllowOverride All

        # --- Layer A: HTTP Basic Auth -- blocks every crawler, incl. AI bots ---
        AuthType Basic
        AuthName "SINO FRESH dev - private preview"
        AuthUserFile /etc/httpd/.htpasswd-dev.zxpet.com
        Require valid-user

        # --- Layer B: de-index header on EVERY response, incl. 401 and 403 ---
        Header always set X-Robots-Tag "noindex, nofollow, noarchive"
    </Directory>
```

> `Require all granted` 被**删除**（原因见 §2.1）。

### 3.2 `/etc/httpd/.htpasswd-dev.zxpet.com`（新增）

- 属主 `root:apache`，权限 `640`（apache 可读，其他用户不可读）
- 位置在 **DocumentRoot 之外**（`/etc/httpd/`），Web 不可达
- 哈希算法：**bcrypt（`$2y$05$`）** —— 选 cost 5 是权衡结果：主机内存偏紧（存在 `zz-amy-lowmem.conf`），
  而 Basic Auth 会**对每一个静态资源请求**都做一次校验，cost 过高会明显拖慢页面加载。
  密码本身是 20 位随机字符（约 119 bit 熵），离线爆破不可行，因此低 cost 不构成实际弱点。

### 3.3 `/var/www/dev.zxpet.com/public/wp-content/mu-plugins/zz-sf-dev-lockdown.php`（新增）

- 属主 `apache:apache` `644`，2510 B，`php -l` 通过，WP 已识别为 must-use 插件（v1.0.0）
- 机制：挂 `wp_robots` 过滤器（优先级 99），设 `noindex / nofollow / noarchive`。
  WordPress 从这个数组渲染**唯一一个** `<meta name="robots">`，所以是**补全**而非产生第二个标签。
- **门控（两个条件必须同时成立）**：

```php
// 1) 生产主机名硬豁免 —— 即使本文件被误拷到生产站，也绝不生效
if ( in_array( $host, array( 'zxpet.com', 'www.zxpet.com' ), true ) ) return false;
// 2) 环境常量 —— 只存在于本机 wp-config.php，该文件不在任何 git 仓库
return ( defined( 'SF_DEV_LOCKDOWN' ) && SF_DEV_LOCKDOWN );
```

> 这一层是**冗余加固**（`blog_public=0` 已提供 noindex/nofollow）。它的价值有三：
> ① 补上缺失的 `noarchive`；② 不再依赖数据库选项——上线做 DB 克隆/恢复时，
> `blog_public` 可能被静默重置为 1，而常量不会；③ 意图显式化，不靠"查数据库才知道为什么不可索引"。

### 3.4 `/var/www/dev.zxpet.com/public/wp-config.php`（追加 1 行 define）

第 81 行插入（`php -l` 通过）：

```php
/* DEV-ONLY indexing lockdown switch.
 * Consumed by wp-content/mu-plugins/zz-sf-dev-lockdown.php, which emits
 * noindex,nofollow,noarchive on the staging host only.
 * This line MUST NOT exist in the production wp-config.php.
 * Remove it together with the mu-plugin at go-live. */
define( 'SF_DEV_LOCKDOWN', true );
```

### 3.5 **未改动**（有意保留）

| 文件 | 原因 |
|---|---|
| `public/robots.txt` | 已符合要求（`Disallow: /` + 16 AI 爬虫），且位于 docroot 内、不会被 WP 覆盖（WP 只在无物理文件时输出虚拟 robots.txt） |
| `public/.htaccess` | 已存在 AI 爬虫 UA → 403 段；本次未动。⚠️ 但该段写在 `# BEGIN WordPress` … `# END WordPress` **之间**，若有人在 wp-admin 重新保存固定链接，WP 会重写 .htaccess 并**抹掉这段** |
| 生产三个 vhost + `zxpet-performance.conf` + `zxpet-webp.conf` + `zxpet-seo-redirects.conf` | 一律未动（sha256 全等、时间戳未变） |
| 主题全部文件 | 未动（见 §6.3） |

---

## 4. 验证结果（逐项实测）

### 4.1 源站直连（`--resolve` 绕过 Cloudflare）

| 检查 | 期望 | 实测 |
|---|---|---|
| `/` 无认证 | 401 | **401**，含 `WWW-Authenticate: Basic realm="SINO FRESH dev - private preview"` |
| `/` 带认证 | 200 | **200** |
| 401 响应是否也带 `X-Robots-Tag` | 是 | **是**（`Header always set` 生效，这是升级的价值） |
| AI 爬虫 UA + 认证 | 阻断 | **403**（`.htaccess` 的 UA 规则在认证之前生效） |
| 401 响应体是否泄漏内容 | 否 | 仅 Apache 标准页；`grep -c "sinofresh\|wp-content"` = **0** |
| `.htpasswd` 是否可 Web 读取 | 否 | 403（被 `httpd.conf` 的 `<Files ".ht*"> Require all denied` 拒绝）；docroot 内无同名文件 |

**路径矩阵（源站）**

| 路径 | 无认证 | 带认证 |
|---|---|---|
| `/` | 401 | 200 |
| `/about/` | 401 | 200 |
| `/formulas/` | 401 | 200 |
| `/products/soft-chews/` | 401 | 200 |
| `/zh/` | 401 | 200 |
| `/zh/formulas/` | 401 | 200 |
| `/wp-login.php` | 401 | 200 |
| `/wp-json/` | 401 | 200 |
| `/readme.html` | 401 | 200 |
| `/wp-content/themes/sinofresh-theme/style.css` | 401 | 200 |

### 4.2 公网侧（经 Cloudflare，真实 URL）

| 检查 | 实测 |
|---|---|
| `https://dev.zxpet.com/` 无认证 | **401**，`cf-cache-status: DYNAMIC`（无缓存 200 残留） |
| 同上 + 破缓存参数 | **401**（一致） |
| `https://dev.zxpet.com/` 带认证 | 200，`X-Robots-Tag: noindex, nofollow, noarchive` |
| 带认证页面 `<head>` | `<meta name='robots' content='noindex, nofollow, noarchive' />` ✅ `noarchive` 已补上 |
| `https://dev.zxpet.com/robots.txt` | `User-agent: *` / `Disallow: /` |

### 4.3 生产域名未被影响

| 检查 | 改动前 | 改动后 |
|---|---|---|
| `https://zxpet.com/` | 302 → `https://zxpet.com/maintenance.html` | **完全一致** |
| `https://www.zxpet.com/` | 302 → `http://www.zxpet.com/maintenance.html` | **完全一致** |
| `www.zxpet.com` 响应头 | 无 `WWW-Authenticate`、无 `X-Robots-Tag` | **仍然无** |
| `conf.d/*.conf` sha256 全量比对 | — | **只有 `dev.zxpet.com.conf` 变化，其余 11 个文件逐字节相同** |
| 生产 vhost 文件时间戳 | 2026-06-26 / 08-21 / 09-04 | **未变** |

> 附带观察（**改动前就存在，不是本次引入，未做改动**）：`www.zxpet.com` 的 302 目标是 `http://` 明文，
> 而裸域 `zxpet.com` 跳的是 `https://`。两者不一致，建议上线前顺手统一为 https。

---

## 5. 暴露窗口与已有抓取证据

dev 访问日志覆盖 `2026-09-20 05:39:35` → `14:22:25`（UTC）。据此可精确还原暴露窗口：

| 时间段（UTC） | 状态 | 时长 |
|---|---|---|
| 05:38 – 05:46 | 站点已上线，**无 robots.txt、无 noindex、无 UA 拦截、无认证** | ≈ 8 分钟（完全裸奔） |
| 05:46 – 14:18 | robots.txt + X-Robots-Tag + meta noindex + AI 爬虫 403 已生效，**但仍无 HTTP 认证**（任何人可读全站，含 `/zh/`） | ≈ 8 小时 32 分 |
| 14:18 起 | **四层全开** | — |

> 注：日志最早一条是 05:39:35 的本机 `curl`，站点文件 mtime 为 05:38，因此窗口上限不超过 05:38。

### 5.1 已被谁访问过

- **AI 爬虫**：`GPTBot` 3 次、`ClaudeBot` 1 次、`anthropic` 3 次 —— 全部落在 **05:46 之后**，命中 `.htaccess` 的 **403**。
  其余（`OAI-SearchBot / Googlebot / bingbot / Bytespider / PerplexityBot / CCBot / YandexBot / AhrefsBot / SemrushBot`）**0 次**。
- **`robots.txt` 被读取 10 次（200）** —— 说明有工具/爬虫确实来查过，而它返回的是 `Disallow: /`。
- **sitemap 全部 404/301** —— 站点没有 sitemap，不存在通过 sitemap 批量发现 URL 的路径。
- **扫描器 `35.205.254.119`（Google Cloud 段）**：当日 **281 次请求（最高客户端）**，274×404，
  在枚举 `/wp-config.php`、`/.env`、`/.wp-config.php.swp`、`/wp-content/mysql.sql`、`/vercel.json`、`/www.bak` 等。

### 5.2 扫描器实际拿到了什么（重要）

| 请求 | 结果 | 判定 |
|---|---|---|
| `GET /wp-config.php` 09:36:28 | **200，响应体 0 字节**（日志 `%b` = `-`） | **未泄漏**。PHP 正常执行了该文件，只输出空内容；`wp-config.php` 的 DB 凭据**没有**被当源码吐出 |
| `GET /wp-content/debug.log` 09:36:29 | **200，内容 251 字节** | ⚠️ **真实泄漏**（该文件公网可读）。现已落在认证之后，但仍建议删除（§8） |
| `GET /.htpasswd.bak` 09:36:30 | 403 | **未泄漏**。被 `httpd.conf` 的 `<Files ".ht*">` 拒绝。另：该文件名说明**今天早前有人尝试过在 docroot 里放 htpasswd**，现已确认全机仅剩 `/etc/httpd/.htpasswd-dev.zxpet.com` 一个 |
| `GET /wp-settings.php` 09:36:30 | 500 | 无影响（PHP 直接执行核心文件，未输出源码） |

> 顺带确认：日志中**没有任何** `.env / .bak / .sql / .git` 类路径返回 200（除上表 debug.log）。
> 也就是说在无认证的 8.5 小时里，被扫到的最严重的实际泄漏是 `debug.log`。

---

## 6. 没破坏正在进行的改版任务（证据）

### 6.1 主题仓库零改动

```
$ git -C /var/www/dev.zxpet.com/site-repo status --short
（空）
$ git -C /var/www/dev.zxpet.com/site-repo log --oneline -1
c0308af Batch2C Step4: archive the breadcrumb fix (full record)
```

配置器、移动端底部横条、About/Quality 清理所涉及的全部文件都在这个仓库里 —— **一个字节都没动**。

### 6.2 页面逐行比对（首页）

封锁前后各取一份首页 HTML 做行级 diff（1929 行 vs 1929 行），差异 **14 行**，全部归因为以下三类，
且**已用「源站 vs Cloudflare 边缘」对照独立证明**（同一批差异在源站/边缘对比中复现，故与本次改动无关）：

| 差异类型 | 说明 |
|---|---|
| Cloudflare 邮箱混淆（4 处） | CF 把 `mailto:info@zxpet.com` 改写成 `/cdn-cgi/l/email-protection#…` 并注入 `email-decode.min.js`；源站本身一直是明文 `mailto:` |
| Cloudflare `speculationrules` 注入 | CF 的功能，源站不注入 |
| Gravity Forms 每次渲染的状态令牌（2 处） | `gform_currency` / `state_2` 隐藏字段的值随渲染变化，与封锁无关 |

→ **除 `<meta name='robots'>` 一行外，页面正文零差异。** 未删任何 DOM、未新增 JS/CSS、
未使用 `display:none`、未引入任何库或框架。

### 6.3 带认证的页面完整性

| 页面 | 状态 | 体积 | H2 | img |
|---|---|---|---|---|
| `/` | 200 | 230,604 B | 13 | 32 |
| `/about/` | 200 | 124,215 B | 6 | 16 |
| `/quality/` | 200 | 161,969 B | 9 | 21 |
| `/formulas/` | 200 | 130,616 B | 1 | 25 |
| `/products/soft-chews/` | 200 | 173,354 B | 6 | 15 |

`wp option get blog_public` → `0`；`wp plugin list --status=must-use` → `zz-sf-dev-lockdown 1.0.0` 已加载；
`debug.log` 与 `httpd` 错误日志无本次引入的新错误（错误日志中除既有的自签证书告警外，
只有认证失败记录 —— 见 §9）。

---

## 7. 回滚

**一键回滚脚本已生成并语法校验通过：**

```bash
ssh root@65.49.215.152 'bash /root/dev-lockdown-20260920-141751/REVERT.sh'
```

脚本做五件事（`set -euo pipefail`，任一步失败即停）：

1. 用 `dev.zxpet.com.conf.orig` **逐字节还原** dev vhost
2. 删除 `/etc/httpd/.htpasswd-dev.zxpet.com`
3. 删除 mu-plugin `zz-sf-dev-lockdown.php`
4. 用精确正则摘除 wp-config.php 里的 `SF_DEV_LOCKDOWN` 块（幂等，重复执行安全）
5. `httpd -t` 通过后 `systemctl reload httpd`

**回滚后的状态**：dev 恢复为"无认证，但仍有 `X-Robots-Tag` + `robots.txt Disallow: /` + AI 爬虫 403"。
若要把 dev 也变成完全开放，还需手工再删 `public/robots.txt` 与 `public/.htaccess` 里的 AI 爬虫段（脚本有意不碰它们）。

**更粗的回滚**：备份目录里有 `wp-config.php.orig`（改动前完整副本），可直接覆盖 —— 但若此后有人再编辑过 wp-config，
覆盖会连带丢弃那些编辑，所以脚本默认走精确摘除而非整文件还原。

### 7.1 凭据位置

- **只在本对话回复中给出一次**（用户名 + 20 位随机密码）
- 服务器副本：`/root/dev-lockdown-20260920-141751/CREDENTIALS.txt`（`chmod 600`，root only）
- htpasswd 本体：`/etc/httpd/.htpasswd-dev.zxpet.com`（`640 root:apache`）
- ✅ **确认未进入任何 git 仓库**：`grep -rl "<密码>" site-repo/ public/` → 空；
  `docs/`、`sinofresh-theme/`、`mu-plugins/` 均无凭据。**本文件（`docs/dev-lockdown.md`）也在仓库内，故不含密码。**

---

## 8. 仍需人工完成的事项

### 8.1 ⚠️ Cloudflare 边缘缓存清理（**必须做，我无法从服务器完成**）

实测：首页 37 个静态资源中，**9 个仍可匿名读取（200）**，因为 Cloudflare 边缘已有副本，
**带认证的请求才会回源，匿名请求直接命中边缘缓存**：

```
cf=HIT  /wp-content/plugins/gravityforms/assets/css/dist/gravity-forms-theme-framework.min.css
cf=HIT  /wp-content/plugins/gravityforms/assets/css/dist/gravity-forms-theme-reset.min.css
cf=HIT  /wp-content/plugins/gravityforms/assets/js/dist/scripts-theme.min.js
cf=HIT  /wp-content/plugins/gravityforms/assets/js/dist/utils.min.js
cf=HIT  /wp-content/plugins/gravityforms/js/gravityforms.min.js
cf=HIT  /wp-content/plugins/gravityforms/js/jquery.json.min.js
cf=HIT  /wp-content/plugins/translatepress-multilingual/assets/flags/4x3/en_US.svg
cf=HIT  /wp-content/plugins/translatepress-multilingual/assets/flags/4x3/zh_CN.svg
cf=HIT  /wp-content/themes/sinofresh-theme/assets/images/favicon-32.png
```

这些是第三方库文件与图标，**不含站点文案或产品内容**，风险有限 —— 但它们确实仍是可公开抓取/缓存的 dev 域名 URL。

**服务器上未找到任何 Cloudflare API Token**（`/root`、`/etc` 下均已搜索），故这一步必须由你在 CF 面板完成：

- **立即**：Caching → Configuration → **Purge by URL**，把上面 9 个 URL 逐个贴入清除
  （不要用 **Purge Everything**：`dev.zxpet.com` 极可能与 `zxpet.com` 同属一个 Zone，Purge Everything 会顺带清空生产站缓存）
- **永久**：加一条 **Cache Rule**：`hostname eq dev.zxpet.com` → **Bypass cache**。
  这样 dev 的任何响应都不会再进入边缘缓存，比"每次改了再清"可靠得多
- HTML 页面本身**没有**边缘缓存问题（实测 `cf-cache-status: DYNAMIC`）

### 8.2 建议但非必须

| 项 | 说明 |
|---|---|
| 删除 `public/wp-content/debug.log` | §5.2 已证明它曾被公网以 200 读出 251 字节。现已在认证之后，但仍属不该留在 docroot 的文件 |
| 用 Cloudflare Access 替换 Basic Auth（可选加固） | 更细的会话控制与审计；但需要 CF 账号权限，且会改变现有预览流程，建议不在改版期间做 |
| 删除 `public/readme.html` | WordPress 版本指纹文件，现在也已在认证之后 |
| 修复 `public/.htaccess` 的脆弱点 | AI 爬虫 403 段写在 `# BEGIN WordPress` 块内，保存固定链接时会被 WP 重写抹掉 → 建议挪到 `# BEGIN WordPress` **之前** |
| 统一 `www.zxpet.com` 的 302 目标为 `https://` | 见 §4.3 附带观察（改动前就存在） |

---

## 9. 上线前必须移除的 dev 封锁项（清单）

> 顺序建议按此表从上到下执行，每步后复验。

| # | 项目 | 位置 | 移除动作 | 漏掉的后果 |
|---|---|---|---|---|
| 1 | **HTTP Basic Auth**（4 行） | `dev.zxpet.com.conf` 两个 `<Directory>` 块 | 删 `AuthType` / `AuthName` / `AuthUserFile` / `Require valid-user` | 生产站弹登录框，访客完全无法访问 |
| 2 | **`.htpasswd` 实体** | `/etc/httpd/.htpasswd-dev.zxpet.com` | `rm` | 残留凭据文件 |
| 3 | **meta robots 门控** | `wp-content/mu-plugins/zz-sf-dev-lockdown.php` | `rm` 该文件 | 生产站输出 `noindex`，**整站无法被搜索引擎收录** |
| 4 | **环境常量** | `wp-config.php` 第 81 行附近 | 删除 `SF_DEV_LOCKDOWN` 定义块 | 同上（常量遗留会让插件在别的主机上也生效） |
| 5 | **`X-Robots-Tag` 响应头** | `dev.zxpet.com.conf` 两个 `<Directory>` 块 | 若 dev 仍存在但需开放，保留即可；**正式站 vhost 绝不能有** | 生产站被彻底去索引 |
| 6 | **`robots.txt` 的 `Disallow: /`** | `public/robots.txt` | 换成正式站的允许索引版本（或删除以回落到 WP 虚拟 robots.txt） | 搜索引擎不抓取，站点不上线收录 |
| 7 | **WordPress `blog_public`** | DB 选项（现为 `0`） | 改为 `1`（Settings → Reading → 取消 "Discourage search engines"） | WP 自己会输出 `noindex` + `Disallow: /`，**这是最容易被忽略的一项** |
| 8 | **AI 爬虫 403 段** | `public/.htaccess` | 按业务决定保留或删除（这是策略选择，不是 dev 专属封锁） | 保留则 AI 爬虫无法抓取，视业务目标而定 |
| 9 | **Cloudflare Cache Rule / 缓存** | CF 面板 | 删除 `dev.zxpet.com` 的 Bypass Cache 规则；清理 dev 缓存 | 规则若误配到生产域名，生产站不被缓存 |
| 10 | **Cloudflare Access / IP 白名单**（若启用了 8.2 的可选项） | CF 面板 | 移除策略 | 生产站被登录墙挡住 |

**另有两条自检**（上线后立即做）：
```bash
curl -sI https://zxpet.com/ | grep -iE "www-authenticate|x-robots-tag"   # 两项都应无输出
curl -s  https://zxpet.com/ | grep -o "<meta name=.robots.[^>]*>"        # 应无 noindex
curl -s  https://zxpet.com/robots.txt                                     # 不应是 Disallow: /
```

---

## 10. 对后续工作的影响（务必知悉）

1. **现在访问 `https://dev.zxpet.com/` 会弹出登录框**，浏览器预览、`curl`、截图脚本、E2E 测试
   **全部需要带上 Basic Auth 凭据**。curl 示例：
   ```bash
   curl -sI -u 'sfdev:<密码>' https://dev.zxpet.com/
   ```
2. **日志里已看到有人正在被挡**：
   ```
   14:20:41  [auth_basic:error] AH01618: user admin not found: /wp-admin/index.php
   14:21:32  [auth_basic:error] AH01618: user admin not found: /products/soft-chews/
   ```
   是经 Cloudflare 的浏览器会话在用用户名 **`admin`** 尝试登录。**请改用 §7.1 给出的用户名/密码**，不要把用户名当密码或沿用 WP 后台账号。
3. **主题仓库、robots.txt、.htaccess 均未被触碰**，正在进行的配置器 / 移动端横条 / About、Quality 清理任务不受影响。
4. **本机也看不到任何 CF 侧改动**：本次全部改动都在服务器层，无一进入 git。

---

## 附：本次新产生的文件

| 路径 | 说明 |
|---|---|
| `/root/dev-lockdown-20260920-141751/` | 改动前备份（全部 `conf.d/*.conf` + 3 个 dev 文件 + `sha256-before.txt` + `baseline-before/curl-headers.txt`） |
| `/root/dev-lockdown-20260920-141751/dev.zxpet.com.conf.orig` | dev vhost 原始副本（回滚用） |
| `/root/dev-lockdown-20260920-141751/dev.zxpet.com.conf.NEW` | 改动后副本 |
| `/root/dev-lockdown-20260920-141751/CREDENTIALS.txt` | Basic Auth 凭据（`600`，**不在此仓库**） |
| `/root/dev-lockdown-20260920-141751/REVERT.sh` | 一键回滚（`700`，已 `bash -n` 校验） |
| `/etc/httpd/.htpasswd-dev.zxpet.com` | htpasswd 本体（`640 root:apache`） |
| `/etc/httpd/conf.d/dev.zxpet.com.conf` | 已改（新增 banner + Basic Auth + `Header always set`） |
| `wp-content/mu-plugins/zz-sf-dev-lockdown.php` | 新增（meta robots 门控） |
| `wp-config.php` | 追加 `SF_DEV_LOCKDOWN` 常量 |
| **本文件** `docs/dev-lockdown.md` | 记录（在仓库内，故不含密码） |

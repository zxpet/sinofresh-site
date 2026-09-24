# 补充安全审计（二）· 破解插件 P0 ＋ 服务器层归因

> 上一份：`docs/security-supplement-2026-09-24.md`（8.1／8.6／8.7／8.8／8.9，14 过 / 14 待处置）。
> 本份处理用户裁决要求的第一步（**生产库只读检查表单字段**），结果**推翻了那一问的前提**，
> 并顺路把「缓存是谁设的、头该加在哪」两个悬问测清。**本份的顶线是一条 P0，不是那条 CVE。**

## 0. 范围与方法

- **生产：只读。** `wp core version`／`wp plugin list`／`wp db query "SHOW TABLES"`／`grep`。
  **未发任何 POST，未写任何数据，未改任何文件。**
- **dev：只读为主 ＋ 两处服务器一行配置**（`expose_php`、`ExpiresByType text/html`），两者均在用户裁决内，且都做了备份与复验。
- **穿透 CF 读真实响应头**：`curl -sk -H "Host: dev.zxpet.com" https://127.0.0.1/…`。
  ⛔ 只看 CF 的返回会把「源站设的」与「CF 改写的」混为一谈 —— 这是本节几个结论能站住的前提。

## 1. 结论速览

| # | 事项 | 判定 | 状态 |
|---|---|---|---|
| 1 | **生产库表单字段检查**（用户裁决第 1 步） | **前提不成立**：生产根本没装 Gravity Forms | ✅ 已查，见 §2 |
| 2 | 🔴 **两个商业插件是破解版**（GF 3.1.0.3 / TP Business 1.7.6） | **P0** | ⏸ 待用户裁决（§3） |
| 3 | CVE-2026-84434（GF ≤3.1.0.4，CVSS 9.8） | 仍成立，但**处置方式改了** | ⏸ 随 §3 一起定 |
| 4 | 上一版审计把「GF 更新检测坏了」读成小毛病 | **误读**，那是更新源被改写的症状 | ✅ 已纠正（§4） |
| 5 | 缓存 `max-age=86400` 是谁设的 | **Apache `zxpet-performance.conf`**（不是 CF、不是 nginx） | ✅ 已改（§6.2） |
| 6 | `x-powered-by` 是谁设的 | **`/etc/php.ini:410 expose_php`** | ✅ 已关（§6.1） |
| 7 | 六项安全头该加在 CF 还是 nginx | **都不是：加在 Apache 源站** | 📋 建议＋配置文本（§9） |
| 8 | 生产站插件完整性 | ✅ 4/4 过 WP.org 校验和，无篡改 | ✅ |

## 2. 生产库只读检查（用户裁决第 1 步）—— **本题不成立**

裁决要求：先在生产库只读检查 5 个启用表单有没有 `fileupload` / `hidden` 字段，「不要跳过第 1 步」。

**实测结果比预期更干净：生产站没有 Gravity Forms，也没有那 5 个表单。**

| | dev | **生产** |
|---|---|---|
| 文档根 | `/var/www/dev.zxpet.com/public` | **`/var/www/html`** |
| 数据库 | `sinofresh` | **`wordpress`** |
| WP 版本 | 7.1.1 | 7.1.1 |
| 插件 | akismet／gravityforms／translatepress-{business,multilingual}／wp-consent-api／wp-mail-logging／wp-statistics／zz-sf-* | **naibabiji-b2b-product-showcase／fluent-smtp／puffergo／seo-by-rank-math** |
| 主题 | `sinofresh-theme` | **`generatepress`** ＋ 四个默认主题 |
| `%gf_%` / `%trp_%` / `%statistics%` 表 | 有 | **0 张** |

⇒ 生产**没有** GF，因此：
- **没有可查的表单字段**，也就没有「生产恰好有 `fileupload` 字段 ⇒ 优先级升为立即」的可能；
- 裁决里的第 2、3 步（dev 升级 → 测 → 再生产升级）**不成立**：没有「生产升级」这一腿。
  GF 的「生产腿」应并入**上线 runbook**（届时新站取代 `/var/www/html`），不是现在做一次生产更新。
- 上一版审计写的「**生产库是另一份，必须重跑同一检查**」在事实层面是**错框**：它暗示生产跑同一套栈。
  已按实测改写（§4.2）。

## 3. 🔴 P0 · 两个商业插件是破解版

### 3.1 事实

| | **Gravity Forms 3.1.0.3** | **TranslatePress Business 1.7.6** |
|---|---|---|
| 文件 | `wp-content/plugins/gravityforms/gravityforms.php` | `wp-content/plugins/translatepress-business/index.php` |
| 改写更新源 | **`:145`** `define('GRAVITY_MANAGER_URL','https://gf.gpltimes.com')` | —（仍指厂商 URL） |
| 每次加载写假授权 | **`:150`** `update_option('rg_gforms_key','B5E0B5F8DD8689E6ACA49DD6E6E1A930')` | **`:29-31`** `trp_license_key='C6D0D7F8DB6898D6ACA49DC6C9F4B996'`、`trp_license_status='valid'`、`trp_license_details`（`expires 2074-07-04`） |
| 伪造授权响应 | **`:152-184`** `add_filter('pre_http_request', …)`：对 `https://gravityapi.com/wp-json/gravityapi/v1/licenses/` 的 **POST** 直接返回伪 JSON —— 产品名 `Gravity Forms Elite License`、`max_sites=unlimited`、`active_sites=105`、`date_expires=2035-01-01`、`remaining_seats=unlimited` | **`:33-56`** 同钩子：对含 `https://translatepress.com` 的 POST 直接返回 `{"success":true,"license":"valid",…}` |
| 静音 | `:151` `update_option('gform_pending_installation',false)`；`:153` `delete_option('rg_gforms_message')` | — |

- **两把 key 中段同为 `…D6ACA49DC6…`** ⇒ 同一生成源。
- **更新通道是活的**：调 `GFCommon::get_version_info()` 实测返回
  `is_valid_key=1`、`version=2.2.6.5`、`url=https://f004.backblazeb2.com/file/gpltimes/gfapi/gravityforms.zip`
  —— 即「厂商的版本接口」已经把本站的更新包指向一个**第三方 Backblaze 桶**。
  （说明：这次调用本身是一次出站请求，与 GF 自己的定时任务同类；此处如实记录。）
- **插件头完全正常**：`Plugin Name: Gravity Forms / Author: Gravity Forms / Version: 3.1.0.3`（TP 同样保留 Cozmoslabs 头）。
  ⇒ **后台界面与 `wp plugin list` 都看不出异常**，只能读源码。
- **校验和**：`wp plugin verify-checksums --all` 在 dev 是 **6/8 过**，跳过的 2 个**正是这两个**
  （商业插件不在 wordpress.org，没有官方校验和可比）。
- **无混淆**：`eval(base64_decode`／`gzinflate`／`assert($_` 命中 **0**；uploads 下 **0** 个 `.php`；
  管理员各 1 人（dev `sam@zxpet.com`／生产 `admin@zxpet.com`）；cron 全为正常钩子。
  两处 `pre_http_request` 闭包对不匹配的 URL 都原样返回 `$preempt` ⇒ **今天的行为只有「伪造授权」一条**。

### 3.2 定性

风险**不是**「已经被人植入后门」（未找到证据），而是：

1. **代码来源不可信** —— 不是厂商发布的字节，且其自我声明为 GPL 但不含厂商签名；
2. **更新通道被第三方控制** —— 只要 `gf.gpltimes.com` 想发什么，GF 的「更新」就会装什么；
3. **拦截器常驻** —— `pre_http_request` 在插件加载时无条件注册，位于**每个**请求（含后台）的 HTTP 通路里。

⇒ 因此这条**盖过** CVE-2026-84434：CVE 的修法是「升到 3.1.1+」，
**而这里根本不该用它自带的更新去升**（那正是被控制的通道，且接口目前只肯给 2.2.6.5 的包）。

### 3.3 建议（**待裁决，未执行**）

| 选项 | 说明 |
|---|---|
| A＋A | GF 与 TP Business 都**买正版**、从厂商下载覆盖安装（数据不动：GF 表单在 DB、TP 词典在 DB） |
| A＋B | GF 买正版；TP Business 若暂不需要其付费功能（SEO Pack／多语言附加）可**停用并移除**，主题侧 ZH 已撤下，当前不依赖它 |
| B＋B | 两个都换掉：GF 的用途（`/inquiry` 等表单）可由 WP.org 表单插件承接；TP 保留免费的 `translatepress-multilingual` 即可满足「EN 单语 + 将来恢复 ZH」 |

三条**共同**的立即动作（不改功能）：
1. ⛔ **dev 上不要再跑 `wp plugin update --all` / `wp plugin update gravityforms`**；
2. 若走购买路线，**先停用 → 删除插件目录 → 重装厂商包**（不要「覆盖升级」，避免残留注入）；
3. 装完后**复跑** `grep -rIn "gpltimes" wp-content/` ⇒ 必须 0 命中。

## 4. 与上一版审计的三处自我纠正

**4.1「GF 的更新检测本站是坏的」→ 误读。**
上一版把 `wp plugin list` 的 `version higher than expected` 记成「更新检测坏了，后台不会提示落后」。
真正含义是：**接口报的「最新版」比已装版更低**（2.2.6.5 < 3.1.0.3）——
这是**更新源被改写**的典型症状，本身就是 §3 的第一手证据。上一版把它当成 WP 的小毛病，削掉了这条线索。
⇒ **判据修正：`version higher than expected` 一律先去查该插件的更新 URL 与授权写入。**

**4.2「生产库是另一份，必须重跑同一检查」→ 事实错框。**
生产不是同栈镜像，而是**另一套站点**（§2）。这句话暗示「生产也跑 GF」，实测不成立。

**4.3 上一版的 GF 处置建议（「升级到 3.1.2」）指向了错的修复。**
在破解版上执行「升级」等于**向被控通道取包**。正确顺序是**先确认真伪，再谈版本**。

## 5. 服务器层归因（回答「CF 还是 nginx」）

- ⛔ **本站的 Web 服务器是 Apache httpd 2.4.62（AlmaLinux）＋ php-fpm 8.3.33 ＋ MariaDB 10.5，不是 nginx。**
  记录中的「生产机是 LEMP」对本机**不成立**（`nginx` 命令不存在；`ss -tlnp` 是 `httpd`）。
- ⇒ **`.htaccess` 是生效的**（两个文档根都 `AllowOverride All`）：
  生产维护模式**就是** `/var/www/html/.htaccess` 里的 `RewriteRule … [R=302,L]`。
  ⛔ 记录中「文件要放文档根外，因为 nginx 不读 .htaccess」的**前提是错的**（放文档根外仍更稳，但理由不成立）。
- ⛔ **源站可被绕过 CF 直连**：从外网打 `65.49.215.152` 带 `Host:` 头，实测拿到 `401`（dev 的 Basic Auth）——
  即 CF 不是唯一入口。**任何只加在 CF 的防护（头、WAF、限速）都能被绕开。**

### 5.1 缓存 `max-age=86400` 的来源

**Apache，`/etc/httpd/conf.d/zxpet-performance.conf`**（`conf.d/*.conf` 是**全服务器**级，两个站都吃）：

```apache
<IfModule mod_expires.c>
    ExpiresActive On
    …
    ExpiresDefault "access plus 1 day"      # ← text/html 落进这条 ⇒ Cache-Control: max-age=86400
</IfModule>
```

源站直连实测（改前）：dev `/about/` → `Cache-Control: max-age=86400`；`style.css` → `public, max-age=31536000, immutable`。
⇒ 同一文件里**动态 HTML 缓存一天、静态资源 immutable** —— 反过来才对。**与 CF 无关。**

### 5.2 `x-powered-by` 的来源

`/etc/php.ini:410` 的 `expose_php = On`（PHP 默认值）。与 Apache/CF 都无关。

### 5.3 顺带发现

- 源站 `Server:` 头直接暴露 `Apache/2.4.62 (AlmaLinux) OpenSSL/3.5.5`（CF 会遮，但直连不遮）。
  **一行可收**：`ServerTokens Prod` ＋ `ServerSignature Off`（文件 `/etc/httpd/conf/httpd.conf`）——**未执行**，等排期。
- 生产维护跳转的 `Location` 由源站拼成 **`http://www.zxpet.com/maintenance.html`**（`.htaccess` 写的是相对路径，
  scheme 取源站那一跳），于是构成 302 → 301 → 200 的链。属维护期临时现象，记一笔即可。

## 6. 已执行的两处改动（**非功能项**，含备份与复验）

备份：`/root/_secfix_bak/php.ini.20260924-103034`、`/root/_secfix_bak/zxpet-performance.conf.20260924-103034`

**6.1 `expose_php = On` → `Off`**（`/etc/php.ini:410`，`systemctl reload php-fpm`）
复验（源站直连、PHP 渲染页）：改前 `X-Powered-By: PHP/8.3.33` → **改后该头消失**（`/about/` 仍 200）。

**6.2 新增 `ExpiresByType text/html "access plus 0 seconds"`**（`zxpet-performance.conf` 的 `mod_expires` 块内，`httpd -t` → `systemctl reload httpd`）
复验：

| 响应 | 改前 | 改后 |
|---|---|---|
| dev HTML（源站） | `max-age=86400` | **`max-age=0`** |
| 生产 HTML（源站） | `max-age=86400` | **`max-age=0`** |
| dev `style.css` / `ui-components.js` | `public, max-age=31536000, immutable` | **不变** |
| dev 经 CF 访问 `/about/` | 200 | **200**（站点正常） |

⚠️ **两处都作用于整台机器（含生产）**；回滚＝把备份覆盖回去并 `reload`。

## 7. 用户裁决 → 落地状态

| 裁决 | 状态 |
|---|---|
| P1 先在生产库只读检查表单字段 | ✅ 已查 —— **前提不成立**（生产无 GF，§2） |
| P1 dev 升级 → 测 → 再生产升级 | ⏸ **指令已作废**：dev 那份不是厂商代码，**不可用其自带更新**；生产无此插件（§3.3） |
| P2 MariaDB 10.5.29 EOL ⇒ 迁 10.11／11.4／11.8 LTS | 📋 已记入待办（单独排期，非急诊） |
| P2 Cookie 技术修正「可直接做」 | 📋 落点已勘定，见 §8（属主题改动，走 bump＋门＋E2E） |
| P2 政策页文案重写 | 📋 同上 |
| P2 去掉 Manage Preferences 按钮 | 📋 同上（已定位：该按钮的 handler **就是** `decide(false)`） |
| P2 加撤回入口 | 📋 同上 |
| 六项安全头：排期，先定加在 CF 还是 nginx | ✅ 已定：**加在 Apache 源站**，附配置文本（§9） |
| `x-powered-by` 关掉 | ✅ **已关**（§6.1） |
| 缓存策略：查清是谁设的，再改 | ✅ 已查清（Apache）＋**已改**（§6.2） |
| 技能目录命名重叠 | 📋 已记，不急 |
| MEMORY.md 单列「写断言前自查」＋三实例 | ✅ 已写入 |

## 8. Cookie 批勘定（**未执行**，落点已定位到行）

`sinofresh-theme/assets/js/ui-components.js`：

| 项 | 现状 | 改法 |
|---|---|---|
| version / expires | `:13-17` `decide()` 只写 `{analytics, marketing, timestamp}`，**永不过期** | 加 `version: 1` 与 `expires`（如 +180 天）；读回时发现过期 ⇒ 当无记录、重显横幅 |
| Manage Preferences | `:28` `on(".sf-cookie-banner__manage", () => decide(false))` —— **承诺管理，实为一键拒绝且永久关闭** | 删按钮（`parts/footer.html`），只留 Accept All / Reject |
| 撤回入口 | **无** | 页脚加「Cookie settings」：清 localStorage 记录 → 重显横幅（即撤回） |
| `wp-consent-api` | 插件 active、每页加载，主题里 `wp_set_consent` **0 处调用** | **接上**：在 `decide()` 里调 `wp_set_consent('statistics'|'marketing','allow'|'deny')`，让这个已装的桥接件真的起作用 |
| 政策页文案 | 列 Analytics/Functionality/**Marketing** ＋ 具名 GA／Google Ads／LinkedIn／Facebook（**一个都不在**）；真正在跑的 **WP Statistics** 与 **Cloudflare Web Analytics** 正文出现 **0 次** | 按实跑重写：只留 Analytics（WP Statistics 匿名化 + CF Web Analytics），删掉未使用的第三方 |

⇒ 属主题改动 ⇒ 走 **版本 bump ＋ 预检 install ＋ 门 ＋ E2E ＋ 报告 → 停下等 pull**。

## 9. 六项安全头：建议落在 Apache 源站

**结论：加在 Apache 源站（`/etc/httpd/conf.d/` 单文件），不是 CF。**

理由：① 生产源站**可被直连打 IP 绕过 CF**（§5），只加在 CF 会留一个无头的入口；
② 一个文件、可备份可版本化，与现有 `zxpet-*.conf` 同一套维护方式；③ 不依赖 CF 套餐能力。
CF 侧可选后补一条 **HSTS** 做双保险。

建议文件（CSP 先 **report-only**：主题与 TP 都有内联脚本/样式，直接 enforce 会白屏）：

```apache
# /etc/httpd/conf.d/zz-security-headers.conf   （改动前 httpd -t + 备份）
<IfModule mod_headers.c>
    Header always set Strict-Transport-Security "max-age=31536000" env=HTTPS
    Header always set X-Content-Type-Options "nosniff"
    Header always set X-Frame-Options "SAMEORIGIN"
    Header always set Referrer-Policy "strict-origin-when-cross-origin"
    Header always set Permissions-Policy "geolocation=(), microphone=(), camera=(), payment=(), usb=()"
    Header always set Content-Security-Policy-Report-Only "default-src 'self'; script-src 'self' 'unsafe-inline' https://static.cloudflareinsights.com; style-src 'self' 'unsafe-inline'; img-src 'self' data: https://i.ytimg.com; frame-src https://www.youtube-nocookie.com; connect-src 'self' https://cloudflareinsights.com; base-uri 'self'; form-action 'self'; object-src 'none'"
</IfModule>
```

⚠️ `max-age` 暂不加 `includeSubDomains`：先确认没有子域还跑纯 HTTP，再加。
⚠️ 现在站点唯一的 `nosniff` 是 REST 控制器**自己**发的 —— 这正说明**站点没有全局策略**。

## 10. 复现

```bash
PY=/Users/meng/.workbuddy/binaries/python/versions/3.13.12/bin/python3
S=root@65.49.215.152

# --- 生产库只读：它到底装了什么 ---
ssh $S 'cd /var/www/html && wp core version --allow-root && wp plugin list --allow-root \
  && wp theme list --allow-root --fields=name,status && wp db query "SHOW TABLES;" --allow-root | grep -Ei "gf_|trp_"'

# --- P0 取证 ---
ssh $S 'cd /var/www/dev.zxpet.com/public \
  && grep -n "gpltimes\|pre_http_request\|rg_gforms_key" wp-content/plugins/gravityforms/gravityforms.php \
  && grep -n "trp_license_key\|pre_http_request" wp-content/plugins/translatepress-business/index.php \
  && grep -rIn "gpltimes" . | head'
ssh $S 'cd /var/www/dev.zxpet.com/public && wp eval "print_r(GFCommon::get_version_info());" --allow-root'

# --- 完整性 ---
ssh $S 'cd /var/www/dev.zxpet.com/public && wp plugin verify-checksums --all --allow-root'
ssh $S 'cd /var/www/html && wp plugin verify-checksums --all --allow-root'

# --- 绕过 CF 读源站头 ---
ssh $S 'curl -sk -H "Host: dev.zxpet.com" https://127.0.0.1/about/ -u sfdev:$PASS -D - -o /dev/null | grep -Ei "x-powered|cache-control"'
curl -sS -I -H "Host: dev.zxpet.com" http://65.49.215.152/     # 源站可直连的证明
```

## 11. 未做 / 边界

- **未动任何插件**：停用／删除／升级三样都没做 —— 换什么、买不买，是 §3.3 的裁决项。
- **未动生产站任何文件与数据**（只读子命令＋`grep`）；未发 POST；未改 WP 数据。
- **未提交代码**：本份只含文档；服务器两处改动的备份在 `/root/_secfix_bak/`。
- **Cookie 批未开工**：它是主题改动，且 GF/TP 的去留会改变 dev 的插件底座，先定 P0 更省事。

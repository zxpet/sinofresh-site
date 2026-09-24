# 补充安全审计 · 组件 CVE / Cookie 合规 / 第三方资源 / 服务器头

> 承接 `docs/site-survey-2026-09-24.md` §3（安全审计 A/B）。那一节答的是「陌生人能不能够到不该够到的东西」（30 项设计好的探针）；本节答它没问的四个问题。
> 日期 2026-09-24 · 对象 **dev `dev.zxpet.com`（登出态）** · 工具 `tools/b3f_sec_supplement.py` · 证据 `docs/security-supplement-2026-09-24/supplement.json`
> **本批只读、零改动**；生产站未触碰。

---

## 0. 范围与方法

| # | 问题 | 证据类型 |
|---|---|---|
| 8.1 / 8.9 | 运行的组件有没有公开 CVE、有没有该升没升 | `wp-cli` 只读清单（核心/插件/主题/DB/PHP）＋官方版本接口＋CVE 检索 |
| 8.6 | Cookie / 同意机制是否合规、是否与实情相符 | 主题源码（谁写决定、谁读决定）＋**服务端实测**（匿名访问真的设了什么）＋政策页正文 |
| 8.7 | 页面把哪些东西交给了第三方 | 普查语料 **108 页全量**离线清点（不是首页抽样）＋ SRI 计数 |
| 8.8 | 响应头缺什么 | **五种响应**的矩阵（HTML/REST/静态资源/404/明文 HTTP），不是一个页面 |

**两条方法论陷阱（都先踩到再修）**，写在这里以免下次重复：

1. ⛔ **Cloudflare 的 Web Analytics beacon 只在「看起来像导航」的请求上注入**。同一个 URL，`Accept: text/html,…` 拿到的 HTML 里有 `beacon.min.js`，curl 默认的 `Accept: */*` 拿到的一个字都没有。⇒ **「我 curl 没看到 beacon」是探针的产物，不是站点的实情**。工具因此固定用浏览器 Accept 读头与正文。
2. ⛔ **「字符串≠结构」第三次**：本工具第一版断言「政策页提到了 Cloudflare」时，是对**整份响应**做正则，而 `cloudflareinsights` 这个串就在 beacon 的 URL 里 ⇒ 判成「已披露」，而正文里 `Cloudflare` 出现 **0 次**（假绿）。修法＝先把 script/style 与标签剥掉、只对可见正文断言（`visible_text()`）。⇒ **凡「某文件/某页说了没说某事」，搜的必须是读者能看到的文本。**

---

## 1. 结论速览

**14 项通过 / 14 项待处置。** 其中 **1 项须在上线前处理（P1）**，**2 项须排期（P2）**，其余为 P3/P4 或纯记录。

| 结论 | 项 | 优先级 |
|---|---|---|
| 🔴 **Gravity Forms 3.1.0.3 落在 CVE-2026-84434（CVSS 9.8 未认证 RCE）的受影响区间内**，但**利用前提在本站实测不成立** | 8.1 | **P1（升级动作）** |
| 🟠 **dev 数据库 MariaDB 10.5.29 已 EOL 14 个月，不再有安全补丁** | 8.9 | **P2** |
| 🟠 **Cookie 政策描述的是一套本站不存在的第三方 cookie 体系；真实在跑的统计未披露；无撤回入口；Manage Preferences 是「拒绝」的伪装** | 8.6 | **P2** |
| 🟡 六项安全头全缺（HTML 侧）＋ `x-powered-by` 暴露 PHP 精确版本 | 8.8 | P3 |
| 🟡 HTML 被标 `max-age=86400`（私有一整天），静态资源却是 `immutable` —— 缓存策略反了 | 8.8 | P3 |
| 🟡 `wp-mail-logging` 1.16.0 → 1.17.0；GF 的更新检测本身是坏的（`version higher than expected`） | 8.1 | P3 |
| 🟡 `wp-consent-api` 装着、每页加载、**无人调用** | 8.6 | P3 |
| ✅ TranslatePress / WP Statistics / WP Consent API / Akismet / WP 核心 / PHP 均**无未修补 CVE** | 8.1 | — |
| ✅ 第三方只有 2 个域；外部脚本样式表 **108/108 全带 SRI**；YouTube 走 `youtube-nocookie` 点播门面 | 8.7 | — |
| ✅ **匿名访客一个 cookie 都不设**（实测无 `Set-Cookie`），决定存 localStorage | 8.6 | — |

---

## 2. 8.1 / 8.9 组件版本与 CVE

### 2.1 清单（dev，`wp-cli` 只读，2026-09-24）

| 组件 | 站上版本 | 官方最新 | 状态 |
|---|---|---|---|
| WordPress 核心 | **7.1.2** | 7.1.2 | ✅ 最新 |
| PHP（CLI 与 FPM） | **8.3.33** | 8.3 在支持期 | ✅ |
| 主题 `sinofresh-theme` | 2.10.79 | 自研，无上游 | ✅（历史批已清零注入面） |
| `translatepress-multilingual` | 3.3.6 | 3.3.6（2026-09-15） | ✅ 最新 |
| `translatepress-business` | 1.7.6 | 商业附加，随许可 | ✅ 未命中已知 CVE |
| **`gravityforms`** | **3.1.0.3** | **3.1.2（2026-09-17）** | 🔴 **见 2.2** |
| `wp-statistics` | 14.16.14 | 14.16.14（2026-09-19） | ✅ 最新 |
| `wp-mail-logging` | **1.16.0** | **1.17.0（2026-09-21）** | 🟡 落后一个小版 |
| `wp-consent-api` | 2.1.0 | 2.1.0 | ✅ 最新（但无人用，见 §3） |
| `akismet` | 5.7.2（停用） | 5.7.2 | ✅ |
| `hello` | 1.7.2（停用） | 1.7.2 | ✅ |
| **MariaDB** | **10.5.29** | 12.3 LTS | 🟠 **EOL** |

### 2.2 🔴 Gravity Forms 3.1.0.3 —— 命中区间，但利用前提不成立

**CVE-2026-84434**（2026-09-19 公开，CVSS **9.8**，CWE-434 任意文件上传）：未认证攻击者可通过**隐藏在表单里的 File Upload 字段**绕过扩展名校验上传可执行文件 ⇒ 远程代码执行。受影响区间 **≤ 3.1.0.4**，修复版 **3.1.1+**（当前最新 3.1.2）。本站跑 **3.1.0.3** —— **在区间内**。

**利用前提逐条实测（决定性的一步）**：漏洞要求某个**公开表单**含 **File Upload 字段且 Visibility = Hidden**。只读枚举 5 个启用表单的字段类型：

| 表单 | 字段类型统计 |
|---|---|
| 2 Get a Quote | text×2, email, select×2, textarea, checkbox, **hidden×1（隐藏文本框，非上传）** |
| 3 Request a Sample | text×3, email, phone, select×4, textarea×2, checkbox |
| 4 Book a Factory Tour | text×3, email, phone, select×5, date, html, time, textarea, checkbox |
| 5 Request COA | text×2, select×3, email, checkbox×2, textarea, **hidden×1** |
| 6 Feedback | select, text, textarea, email, checkbox |

⇒ **全站 0 个 `fileupload` 字段**，**0 个 `visibility:hidden` 字段**（`hidden` 是隐藏**输入框**类型，与「隐藏的文件上传字段」是两回事）。**⇒ dev 上该漏洞不可利用。**

**处置（不因前提不成立而降级为「不急」）**：
1. **升级到 3.1.2**（≥3.1.1 即修）。版本在区间内就是必须修的事实，前提只是「此刻恰好踩不到」——任何人日后加一个带上传的引流表单就自动踩上。
2. ⚠️ **生产站必须重跑同一份前提检查**：本节量的是 **dev 的数据库**。生产是独立库，表单可能不同。
3. ⚠️ **GF 的更新检测在本站是坏的**：`wp plugin list` 给出 `update = version higher than expected`，而不是 `available` ⇒ **仪表盘不会提示你落后**。所以「靠后台红点发现 GF 过期」这条路不存在，版本必须人工盯。

**已核对但本站不受影响的 TP 系列**（全部列出，以免下次重复查）：

| CVE | 影响区间 | 修复版 | 本站 3.3.6 |
|---|---|---|---|
| CVE-2026-78267 未认证提权（9.8） | ≤ 3.3.2 | 3.3.3 | ✅ |
| CVE-2026-19632 未认证管理员接管（9.8，泄密码重置 URL） | ≤ 3.3.1 | 3.3.2 | ✅ |
| CVE-2026-89412 存储型 XSS（7.2） | ≤ 3.3.5 | **3.3.6** | ✅ 恰好是修复版 |
| CVE-2026-76053 存储型 XSS（7.2） | ≤ 3.3.3 | 3.3.4 | ✅ |
| CVE-2026-75981 存储型 XSS（7.2） | ≤ 3.2.5 | 3.2.6 | ✅ |
| CVE-2026-66582 未认证 XSS（7.1） | ≤ 3.3.2 | 3.3.3 | ✅ |

> 附带事实：CVE-2026-19632 的利用前提之一是「**管理员 profile 的 locale 设为已发布的第二语言**」。zh 已在 2026-09-24 撤出 `publish-languages` ⇒ **本站连这条前提也不再成立**（撤下中文的第三个附带收益）。

**WP Statistics**：CVE-2026-3488（≤14.16.4，越权读统计/改隐私审计状态，6.5）、CVE-2026-15780（≤14.16.8，未认证存储型 XSS，7.2）——本站 14.16.14，**两者均已修**。

**WP Mail Logging**：CVE-2026-2471（≤1.15.0，反序列化对象注入，7.5）——本站 **1.16.0 已是修复版**；1.17.0 只是常规更新，无公开高危 CVE。⇒ P3，随下次维护带上即可。

### 2.3 🟠 MariaDB 10.5.29 —— 已 EOL 14 个月

- MariaDB 10.5 的社区维护**止于 2025-06-24**（企业扩展支持也已在 2025-07-16 结束）；10.5.29 是该系列**最后一个**版本，2025-05-06 之后不再有任何安全补丁。
- 今天是 2026-09-24 ⇒ **约 15 个月无补丁**。EOL 之后的 CVE 会照常公开，而「没有补丁可用」这件事**常规扫描器不会报**（它只比对已知 CVE 库）⇒ 攻击面随时间静默扩大。
- 建议路径：迁到 **10.11 LTS / 11.4 LTS / 11.8 LTS**（任一在支持期内）。生产是 AlmaLinux 9 同架构，两侧要一起排。
- 兜底（在迁移完成前）：数据库端口不对公网监听（本地 socket/127.0.0.1）、最小权限账号、备份可回滚。

---

## 3. 8.6 Cookie 与同意机制

### 3.1 好消息（先说，因为它改变了整套判断）

- ✅ **匿名访客一个 cookie 都不设**：以浏览器态请求首页与 `/cookie-policy/`，响应里**没有任何 `Set-Cookie`**。全部状态都在 `localStorage`。
- ✅ **GA4 是受了门的**：`assets/js/ui-components.js` 把决定镜像进 gtag consent state（`analytics_storage`/`ad_storage`/`ad_user_data`/`ad_personalization`），且 `functions.php:7068-7071` 的 `generate_lead` 事件也先读 `sf_cookie_consent`、`c.analytics!==true` 就直接 return ⇒ **拒绝后不发事件**。
- ✅ **dev 上根本没有 Google 标签**（无 gtag / GTM / GA），§2.6 普查结论一致。

→ 结论：**这套机制是「最小化」的，比多数站点干净**。下面全部是**表述与完整性**问题，不是「在偷偷追踪」。

### 3.2 缺口

**① 🔴 政策页描述的是一套本站不存在的 cookie 体系。**
`/cookie-policy/` §3 列了四类 cookie 并给了期限（Analytics「up to 2 years」、Functionality「up to 1 year」、Marketing「up to 2 years」），§4 具名「**Google Analytics, Google Ads, LinkedIn Insights, Facebook Pixel**」。实测：**这些一个都不在**（无 GA/GTM，无像素，无社媒脚本）。反向也缺：**真正在跑的两件事没写**——WP Statistics、Cloudflare Web Analytics（正文里 `Cloudflare` 出现 **0 次**、`Statistics` **0 次**）。
⇒ 夸大披露会主动招来问询，而漏披露是实质缺陷。两处都要改，方向相反：**删掉不存在的，写上存在的**。

**② 🔴「Manage Preferences」按钮 = 一键拒绝，且没有面板。**
`ui-components.js:28`：`on(".sf-cookie-banner__manage", () => decide(false))`。按钮承诺「管理偏好」，行为是**替你做出拒绝**并**永久关闭横幅**，用户**没有第二次机会**看选项。这是「明示同意」与「告知」两处的实打实问题，也是最容易改的一条。

**③ 🟠 没有撤回/更改入口。**
决定写进 `localStorage.sf_cookie_consent` 后就再不复现；政策 §5 却声称可以用「cookie consent tool」管理。**这个 tool 在首次决定后不存在**（页脚没有重新打开的入口）。GDPR 第 7(3) 条要求撤回与给予同样容易 ⇒ 需要页脚常驻一个「Cookie 设置」链接。

**④ 🟠 同意永不过期。**
存的字段是 `{analytics, marketing, timestamp}`，**没有 version、没有 expires**。⇒ 决定一旦做出终身有效，站点改版/新增追踪后无法重新征询。

**⑤ 🟠 `wp-consent-api` 装着但无人调用。**
插件是 active、`wp-consent-api.min.js` 每页都加载（108 页），但**主题里 `wp_set_consent`/`wp_has_consent` 出现 0 次**，且 `wp option list --search="*consent*"` **空**。⇒ 标准桥接件被供着不用：WP Statistics、将来的 GA 都读不到横幅的决定。
**修法二选一**（都是小改）：让横幅在 `decide()` 里调 `wp_set_consent('statistics', on?'allow':'deny')`（几行代码即可让全站插件都受门）；或停用该插件省掉一次请求。**推荐前者**，它同时解决 ⑥。

**⑥ 🟡 WP Statistics 在无门状态下运行。**
`wp_statistics` 选项：`anonymize_ips=1`、`hash_ips=1`（已匿名+哈希）**但** `consent_integration=""`、`do_not_track=""`。⇒ 无论同意与否都统计。因为它是**无 cookie**的（哈希 IP，第一方，不跨站），法务风险远低于 GA；但**它仍然是一项个人数据处理，必须在政策里写明**。开 `consent_integration`（配合 ⑤）是最省事的收口。

**⑦ 🟡 Cloudflare Web Analytics 也受同一问题**：108/108 页注入 `beacon.min.js`，**不受门、也不在政策里**。它是 CF 边缘注入的，站点侧不能靠主题关掉；只能在 CF 面板关掉该项、或用 CSP 拦（CSP 目前也没有，见 §5）。

---

## 4. 8.7 第三方资源

全量清点 **108 页**（离线普查语料，不是首页抽样）：

| 域 | 引用 | 页数 | 说明 |
|---|---|---|---|
| `static.cloudflareinsights.com` | 108 | **108** | CF Web Analytics beacon（边缘注入，**带 `integrity`**） |
| `i.ytimg.com` | 2 | 2 | 视频**封面图** `hqdefault.jpg` |

- ✅ **外部脚本/样式表 108 个标签，108 个带 SRI**（`integrity=`）⇒ 供应链篡改面已被覆盖。第三方脚本只有 beacon 一个。
- ✅ **没有第三方字体/CDN**：字体自托管，jQuery 走站点自身（`/wp-includes/js/jquery/…`），无 Google Fonts。
- ✅ **YouTube 是点播门面**：页面只放封面图，`about.js:64` / `formula-gallery.js:313` 在**点击时**才插入 `https://www.youtube-nocookie.com/embed/…` ⇒ **播放前不吃 YouTube 的 cookie**，且用的是 nocookie 域、带 `referrerpolicy="strict-origin-when-cross-origin"`。这一条整个网站做得比行业平均好。
- ⚠️ P4：封面上线前仍是一次到 `i.ytimg.com`（Google 域）的请求 ⇒ 访客 IP 会到 Google。可以自托管封面图消除；不值当为它单独做一批。
- ⚠️ 无 CSP ⇒ 上述约束是「现在的行为」，不是「被强制保证的行为」（见 §5）。

---

## 5. 8.8 服务器响应头

### 5.1 缺什么（矩阵：五种响应）

| 头 | HTML 首页 | HTML 深页 | REST | 静态 CSS | 404 |
|---|---|---|---|---|---|
| `strict-transport-security` | ✗ | ✗ | ✗ | ✗ | ✗ |
| `content-security-policy` | ✗ | ✗ | ✗ | ✗ | ✗ |
| `x-content-type-options` | ✗ | ✗ | **✓** | ✗ | ✗ |
| `x-frame-options` | ✗ | ✗ | ✗ | ✗ | ✗ |
| `referrer-policy` | ✗ | ✗ | ✗ | ✗ | ✗ |
| `permissions-policy` | ✗ | ✗ | ✗ | ✗ | ✗ |

⇒ **HTML 侧六项全缺**，唯一那个 `nosniff` 是 **WP REST 控制器自己发的**——它证明「WP 会发这个头」，同时也说明**站点没有任何全局策略**（同样是 WP 出的页面，一个有一个没有）。

现存的正面项：`server: cloudflare`（**不暴露 nginx 版本**）、`x-robots-tag: noindex,nofollow,noarchive`（封锁设计）、明文 HTTP **301 → HTTPS**（实测，CF 侧强制）、静态资源 `cache-control: public, max-age=31536000, immutable` + ETag。

### 5.2 两条附带问题

- 🟡 **`x-powered-by: PHP/8.3.33`** 暴露精确补丁号 ⇒ 让攻击者可以直接挑「8.3.33 之前修好的洞」来试。nginx 侧一行 `fastcgi_hide_header X-Powered-By;`（或 PHP `expose_php=Off`）即可。
- 🟡 **缓存策略是反的**：HTML 响应带 `cache-control: max-age=86400` + `expires`（**私有一整天**），而静态资源是 `immutable`。HTML 才是内容会变的那一层：dev 上这意味着浏览器可能**一整天看不到刚 pull 的改动**（本次 pull 后复验就是靠 `Cache-Control: no-cache` 绕开的）。建议 HTML 改为 `no-cache`（或 `max-age=0, must-revalidate`），静态资源保持不变。
- ℹ️ 记录：`nel` / `report-to` 指向 `a.nel.cloudflare.com`（CF 的网络错误上报）。属正常 CF 行为，但**它也是一次第三方遥测**，政策页若要完整可一并提及。

### 5.3 落地位置

这两个站点都跑 **Cloudflare + 源站 nginx**，两条路都行、要选一条以免重复与漂移：
- **CF 侧**（推荐做安全头）：Transform Rules → Modify Response Header，或 Managed Transforms。好处：立即生效、生产/dev 可分别设、不动服务器。
- **源站 nginx**：`add_header … always;` ×6 + `fastcgi_hide_header X-Powered-By`。好处：不依赖 CF 计划档位。
⚠️ **CSP 不要一次上最严**：站点有内联块样式（普查已知每页 59–65KB 内联 CSS）、GF 与 TP 都会内联脚本 ⇒ 先上 `Content-Security-Policy-Report-Only`，收一周报告再收紧。HSTS 上之前先确认**生产域名全量 HTTPS**（dev 已强制，生产待验）。
⚠️ 这些是**上线清单**的事，不是现在就该动生产的事。

---

## 6. 复现

```bash
# 组件清单（只读）
ssh root@65.49.215.152 'cd /var/www/dev.zxpet.com/public && wp plugin list --allow-root \
  --fields=name,status,version,update && wp core version --allow-root && \
  wp db query "SELECT @@version;" --allow-root'

# CVE-2026-84434 的前提检查：表单里有没有「隐藏的文件上传字段」
ssh root@65.49.215.152 'cd /var/www/dev.zxpet.com/public && wp eval '"'"'
foreach(GFAPI::get_forms() as $f){$t=array();foreach($f["fields"] as $fl){
  $k=$fl->type; $v=$fl->visibility??"visible"; if($v!=="visible")$k.="/".$v;
  $t[$k]=($t[$k]??0)+1;} echo $f["id"].": ".json_encode($t)."\n";}'"'"' --allow-root'

# 8.6 / 8.7 / 8.8 全量
python3 tools/b3f_sec_supplement.py --json docs/security-supplement-2026-09-24/supplement.json

# 统计插件的隐私设置（只读）
ssh root@65.49.215.152 'cd /var/www/dev.zxpet.com/public && wp option get wp_statistics --format=json --allow-root'
```

---

## 7. 自我纠正与本节的边界

1. ⛔ **探针假阴性**：第一轮 curl 用默认 `Accept: */*` ⇒ 三处都读不到 CF beacon，差点写成「站点没有第三方分析」。改成浏览器 Accept 后才与普查的 108/108 对上。**「我的工具看不到」先怀疑工具。**
2. ⛔ **假绿（本节内第二次踩「字符串≠结构」）**：政策页「是否披露 Cloudflare」的断言最初对整份响应做正则，命中的是 beacon URL ⇒ 判成「已披露」；改为只搜可见正文后，如实得到 **0 次**。已把 `visible_text()` 写进工具。
3. ⛔ **差点写下一条假断言**：工具初版有 `check('the same flag drives the lead event', True)` —— 一个恒真的占位断言。已改为真的去读 `functions.php` 里那两处字面量（`sf_cookie_consent`、`analytics!==true`）。
4. **本节只覆盖 dev。** 生产是独立主机与独立数据库：**GF 版本、表单结构、MariaDB 版本、响应头四项都要在生产重跑一遍**（响应头部分生产站当前 302 → `/maintenance.html`，等上线后再测才有意义）。
5. **本节的「FAIL」是发现，不是回归断言**：`b3f_sec_supplement.py` 记的是「期望态未达成」的清单，14/14 条都要靠改动才变绿；它不是每次上线都要跑绿的门。若将来要当门用，需另建基线（参照 `b3d_sec_probe.py` 的 24/30 基线做法）。
6. **未做**：没有对任何组件做本地漏洞复现、没有对生产发请求、没有改动任何插件/设置/服务器配置。GF 升级、MariaDB 迁移、安全头落地都属**另行立项**，等裁决。

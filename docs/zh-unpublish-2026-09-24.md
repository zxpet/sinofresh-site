# 撤下 ZH 语言 —— 实施记录（2026-09-24）

**性质**：已在 **dev 生效**（DB + 代码），**live 未 pull**，**生产零接触**。
**代码提交**：`49942b9`（主题）—— 预检副本已装该提交，落地为 `sinofresh-theme-preflight`。
**预检安装**：`49942b9339a6a1aef005945f6c345cdb4b02345f`
　　`functions.php` sha256 `27561924a17bbac46e61ff5f9f4420b6808129ce5ab96aae7cd9c7ad16c69d06`
　　`style.css` sha256 `eb0b48fea984fc66ae488fa6ccb4ce4d83189de5668d5a13b07ee266cf8f05e6`（未改动）
**依据**：裁决 ①②③④ 见 `docs/zh-unpublish-scan-2026-09-24.md` §6.5；**重新启用清单**见该文件 §6.6 与本文 §9。
**本批未 bump 版本**：`style.css` 一个字节都没动，没有 `?ver=` 需要失效的对象；bump 只会把 6 个工具文件的版本字面量一起拖下水（治理洞已立项）。
**产物**：`docs/zh-unpublish-2026-09-24/verify.json`（全量对照）、`rollback-baseline.txt`（回滚基线）、`shots/`（帧）。
**工具**：`tools/b3e_zh_redirect_unit.py`（31 条离线用例）、`tools/b3e_zh_verify.py`（全量对照，69 项）、`tools/b3e_zh_shots.py`（帧）、`tools/b3e_zh_apply.php`（DB 变更，可重入）。

---

## 0. 本批最反直觉的发现：**站点自己已经做了一部分 301**

改之前没人知道这一点。移出 `zh_CN` 之后，对 `/zh/*` 各发两次请求 —— 一次**不带**本批代码（live 侧），
一次**带**（预检侧）。用 `X-Redirect-By` 区分是谁发的：

| | 301 | 404 |
|---|---|---|
| **live 侧**（本批代码不在） | **20 条**，全部 `X-Redirect-By: WordPress` | **34 条**，无 `X-Redirect-By` |
| **预检侧**（本批代码在） | **54 条**，全部 `X-Redirect-By: SINO FRESH` | 0 |

即：**核心只覆盖 20/54，剩下 34 条原本是 404** —— 而用户的要求正是「不要 404」。

**归因（已读到源码）**：核心那条 301 来自
`redirect_canonical()` → `redirect_guess_404_permalink()`
（`wp-includes/canonical.php:215` 调用、`:927` 定义），而该调用**位于 `:147 if ( is_404() )` 分支之内**。
它的守卫是 `if ( get_query_var( 'name' ) )`：

- 顶层 page（`/zh/about/`、`/zh/quality/`、`/zh/products/`…）与 post（`/zh/case-study-*/`）
  **有 `name`** ⇒ 被「前缀 LIKE 猜测」猜中 ⇒ 301
- **CPT 重写路径**（21 条 `/zh/formulas/*`）**与根路径 `/zh/`**、以及**多层 page**（`/zh/products/soft-chews/`、
  `/zh/services/oem/` 等）**连 `name` 都不成立** ⇒ 不猜 ⇒ **留成 404**

**这条发现的含义**：
1. 本批的**实际增量是 34 条**（不是 54 条）—— 但**覆盖是 54/54**，因为本批规则也会接住那 20 条
   （priority 1 先跑，从源头发出 301，不再依赖核心的猜测）。
2. 核心那 20 条是**猜测的产物**（`post_name LIKE '<slug>%'`），不是精确映射；本批规则是**精确剥前缀**。
   两者在实测的 20 条上目标恰好一致，但**确定性不同**。
3. **没有本批规则时**，「/zh/* 不返回 404」这个要求**达成不了**：34 条里包含 `/zh/`（首页）
   与全部 21 个配方页 —— 恰恰是最可能被收录的两类。

---

## 1. 改动清单

### 1.1 代码（走 预检 → 门 → 确认 → pull）

| # | 文件 | 改动 |
|---|---|---|
| A | `sinofresh-theme/inc/zh-unpublish.php` | **新增**。`sinofresh_redirect_unpublished_zh()` 挂在 `template_redirect` priority 1 |
| B | `sinofresh-theme/functions.php` | 顶部增加一处 `require get_template_directory() . '/inc/zh-unpublish.php';`（第 4 处 require，带注释） |

规则行为（全部有离线用例覆盖，见 §7）：

- 读 `trp_settings['publish-languages']`，**只有** `["en_US"]` 时才动作 ⇒ **zh 恢复了规则自动失效**（裁决 ②）
- 只对 `GET` / `HEAD`；目标＝`home_url(剥掉 "/zh" 前缀后的路径)`；**保留 query string**
- `/zh/` 与 `/zh`（无尾斜杠）都 → `/`
- **不设 `is_404()` 门**（两种状态下都要能 301）
- 排除段：`wp-json`、`feed`、`wp-admin`、`wp-login.php`、`wp-content`、`wp-includes`、`wp-cron.php`、`xmlrpc.php`、`cdn-cgi`
- **豁免**：query 里含 `trp-edit-translation` 的请求 —— **只豁免带该参数的请求，不是整个 `/zh/` 前缀**（裁决 ④）
- `home_url()` 前用 `ltrim($rest,'/')` 折叠畸形 `//`，避免把协议相对路径交给 `home_url()`

### 1.2 数据库（**state，不是代码**）

| # | 项 | 改前 | 改后 | 回读确认 |
|---|---|---|---|---|
| 1 | `trp_settings['publish-languages']` | `["en_US","zh_CN"]` | **`["en_US"]`** | ✅ **未被弹回** |
| 2 | `trp_language_switcher_settings['floater']['enabled']` | `true` | **`false`** | ✅ |

**未动**（守住第 4 条）：`translation-languages` 仍 `["en_US","zh_CN"]`；`url-slugs` 仍 `{"en_US":"en","zh_CN":"zh"}`；
`default-language` 仍 `en_US`；`trp_language_switcher_settings` 的 `shortcode`/`menu` 两节原样；
`wp_trp_dictionary_en_us_zh_cn` 一行未动。

> **用户指定的强制动作 1 —— 已执行**：写入后**从 option 表回读**（清 `wp_cache` 再读，避开请求内缓存），
> 确认 `publish-languages === ["en_US"]`。`class-upgrade.php:2062-2074` 那段「互为子集就重置回
> translation-languages」的旧修补**没有触发**。`b3e_zh_apply.php` 可重入，重跑幂等（第二次 `BEFORE` 已是 `["en_US"]`）。

### 1.3 一个**不是**本批造成、但必须记录的数字

`wp_trp_dictionary_en_us_zh_cn` 的**行数在增长**：

| 时刻 | 行数 | 带译文 |
|---|---|---|
| 普查（2026-09-24 早） | 2388 | **0** |
| 本批实施时 | **2435** | **0** |

差的 47 行是**抓取造成的**：TranslatePress 在**每次前端渲染**时把遇到的新字符串登记进表
（实测最高 id 2431–2435 是 `Search`／`Search Results`／`Results for your search query.`／`Read More →`／
`「test」的搜索结果 – sinofresh`，正是普查与验证时抓过的搜索页）。

⇒ **「2388」不是不变量**，报告与记忆里都改口径。**真正稳定的判据是「带译文 = 0」**，
本批把它写成断言（第一版曾错误地把 2388 当常量断言，见 §7）。

---

## 2. 负对照：DB 未变时，规则必须一动不动

顺序是**先装代码、后改 DB**，所以中间存在一个天然负对照窗口：预检副本里有规则，而 `publish-languages`
仍是 `["en_US","zh_CN"]`。

| 路径（预检头） | 结果 |
|---|---|
| `/zh/about/` | **200**，无 `Location` |
| `/zh/` | **200**，无 `Location` |
| `/zh/feed/` | 200 |
| `/zh/wp-json/wp/v2/types` | 200 |

同时断言拿到的是预检资源：`themes/sinofresh-theme-preflight/style.css?ver=2.10.79`。
⇒ **规则在「zh 仍发布」时确实不动作**（裁决 ② 的自愈性由此得到现场证明，不只是离线用例）。

---

## 3. 全量对照（54 条 ZH 路由 × 2 侧，登出态）

来源 `docs/zh-unpublish-2026-09-24/verify.json`。**全部登出态** —— nginx Basic 不是 WP 登录，
所以每一发请求都是访客，这是必须的：切换器对 `manage_options` 读 `translation-languages`、
对访客才读 `publish-languages`（`class-language-switcher-v2.php::get_language_items()` 与
`class-url-converter.php:859-860` 两处同源判定）。

| | live 侧（无本批代码） | 预检侧（有本批代码） |
|---|---|---|
| 301 | 20（全 `by=WordPress`） | **54（全 `by=SINO FRESH`）** |
| 404 | **34** | 0 |
| 目标正确（剥前缀） | 20/20 | **54/54** |

**本批新增覆盖 34 条**，含 `/zh/`（首页）与全部 21 条 `/zh/formulas/*`。

---

## 4. 用户指定的强制动作 2：`/zh/about/` 移出后是 200 还是 404？→ **是 404**

不是 200。这个值**无法直接观察**（核心的猜测会把它立刻转成 301），所以用两步定下来：

1. **实测**：live 侧（无本批代码）`/zh/about/` → **301**，`X-Redirect-By: WordPress`。
2. **归因**：核心那条 301 来自 `redirect_guess_404_permalink()`，而该函数**只在 `if ( is_404() )` 分支内被调用**
   （`canonical.php:147` → `:215`）⇒ **请求必须先被判成 404**。

**扫描阶段静态读码给的「倾向 200」是错的**（`class-translation-render.php:83` 按 `translation-languages`
决定翻译，我们保留了它，于是推断内容仍会渲染出 200）。但扫描报告当时的原则是对的：
§6.3 的设计**不赌 200 也不赌 404**（挂 `template_redirect` 且不设 `is_404()` 门），两种结果都覆盖。

**对 §6.6 的影响**：无。重新启用时 `/zh/*` 会重新变 200（TP 恢复正常），规则同时失效，编辑器也恢复。

---

## 5. 例外、query string，以及一个取舍

| 路径（预检侧） | 结果 | 说明 |
|---|---|---|
| `/zh/feed/` | **200** | 声明豁免；本规则未重定向它 ✅ |
| `/zh/wp-json/wp/v2/types` | **404**（`by` 空） | **本规则未重定向它** ✅；它变 404 是 TP 不再认该前缀所致。⚠️ 注意：DB 变更**前**它是 200 —— 那时 zh 还在。该 URL 本身无意义（REST 走 `/wp-json/*`） |
| `/zh/about/?a=1&b=2` | 301 → `/about/?a=1&b=2` | query 串保留 ✅ |
| `/zh/about/?trp-edit-translation=true` | 301，**`by=WordPress`** | **本规则没碰它**（豁免生效）✅，但**核心的 404 猜测盖过了豁免** —— 见下 |
| `/zh/does-not-exist-xyz/` | 301 → `/does-not-exist-xyz/`（该处 404） | **取舍**，见下 |

### 5.1 豁免在实际链路里「不充分」，但无实际损失

豁免只约束**本规则**；核心的 404 猜测在 `template_redirect` priority 10 跑，而本规则 priority 1
已经**选择不动作**，于是控制权交回核心 ⇒ 编辑器 URL 仍被 301（`by=WordPress`）。

**为什么这不是问题**：
- 撤下期间**没有 zh 可编辑**，打不开编辑器是本状态的必然结果，不是损失；
- 重新启用时（§6.6 步骤 1）`/zh/*` 重新变 200 ⇒ 无 404 ⇒ 核心猜测不介入 ⇒ 编辑器自行恢复。
⇒ 豁免**保留**（它把「编辑器 URL 的处置」留给 TP/核心，本规则不在不该管的场景施加动作）。

### 5.2 取舍：垃圾 ZH 路径会 301 到不存在的 EN 路径

规则**无条件剥前缀**，不先问目标是否存在。所以 `/zh/{垃圾}/` → `301 /{垃圾}/` → 404。

**为什么不加存在性检查**（这是权衡后的决定，不是疏忽）：
- 扫描阶段实测 `url_to_postid()` 对全站 54 个对象只解析出 **53/54**，**`/blog/` 失配**（一个正常 page）。
  用解析器做守卫，会把**真实路由判成不存在** ⇒ 该 301 的不 301 ⇒ **真页面变 404**。
- 那是**比多一跳严重得多的错**：垃圾路径 301→404 与直接 404 对搜索引擎**等价**（soft 404）；
  而真页面 404 是真实损失。
⇒ **选择「精确剥前缀 + 不猜」，代价是多一跳**。

---

## 6. hreflang 与切换器（裁决 ③ 的两项要求）

**hreflang**：抓 `/about/`（预检）数 `<link hreflang>` ⇒ **`['en-US','en']` 两条，`zh`/`zh-CN` 0 条** ✅
（改动前为 `en,en-US,zh,zh-CN` 四条 —— 移出后 zh 两条自动消失，因为 `add_hreflang_to_head()`
读的正是 `publish-languages`；用户要求的「hreflang 不再声明 zh-CN」**不需要额外代码**。
另：TP 带 `trp_advanced_settings.enable_hreflang_xdefault` 开关，将来讨论 `x-default` 时它是现成的入口，不必写代码。）

**切换器**：

| 判据 | 值 |
|---|---|
| `document.querySelector('.trp-floating-switcher')` | **不存在** ✅ |
| `<nav class="trp-language-switcher">` 计数 | **0** ✅ |
| `trp-language-item` 计数 | **0** ✅ |
| `trp-language-switcher` 子串 | 3 处 —— **全是 asset 引用**：`trp-language-switcher-v2.css` 的 id/href、`trp-frontend-language-switcher.js` 的 script id/src |

⇒ **没有空壳**。裁决 ③ 选「关掉 floater」把扫描阶段担心的「按钮在、下拉空」问题一并消掉，
**不需要主题侧再加隐藏代码**（预测的错误方向也记在扫描报告 §4）。

⚠️ **一个次要观察**（P4，仅供后续排期）：TP 在单语言下**仍然 enqueue** 切换器的 CSS+JS（每页 2 个请求），
虽然一个字节的切换器 markup 都不渲染。可优化，但没有功能影响。

---

## 7. 离线用例：31 条，跑的是**真实文件**

`tools/b3e_zh_redirect_unit.py` → `tools/b3e_zh_redirect_probe.php`
（后者 stub 掉 4 个 WP 函数、**include 真实 `inc/zh-unpublish.php`**、调用真实函数；
因为重定向路径会 `exit`，能在输出里看到 `NO_REDIRECT` 就**证明规则主动不动作**，而不是断言被跳过）。

**第一块是负对照**：`publish-languages` 含 `zh_CN` 时，三条 `/zh/*` 必须**全部不动** ——
一条「无条件重定向」的规则会在这一块全红，而在后面所有正向用例上全绿。
其余覆盖：`/zh/` 与 `/zh` → `/`、深层路径、query 保留、HEAD、畸形 `//` 折叠、
非 `/zh/` 路径、形似前缀 `/zhxyz/`、8 个排除段、编辑器参数（3 种写法）、POST/PUT、
`publish-languages` 为 `[]`／缺键／三语言／`trp_settings` 缺失。**31/31 通过。**

**方法学自查（工具第一版的两个抓取层缺陷，都已修正并写进源码注释）**：

1. **`urllib` 默认跟随 301** ⇒ 54 条 301 被跟成 200，工具报「57 项失败」，全是它自己的。
   修正＝自定义 opener `redirect_request → None`，让 3xx 以 `HTTPError` 形式暴露 code + `Location`。
   **教训：看不到重定向的客户端，会把「跳转成功」读成「没有跳转」。**
2. **声明 `Accept-Encoding: gzip` 却从不解压** ⇒ body 是压缩字节，所有正文正则**静默匹配 0 条** ——
   一个带 2 条 hreflang 的页面被读成「一条都没有」。修正＝不发该头。
   **教训与普查那次 `skip-link` 同源：没有输出时先怀疑取证层，再怀疑站点。**
3. 断言目标写错一次：曾断言 `/zh/wp-json/...` 必须 200，但它**在 DB 变更后是 404**（TP 不再认该前缀）。
   改为断言**本规则没重定向它**（`by != SINO FRESH`）—— 锚在「我的规则做了什么」而不是「站点返回什么」。
4. 断言方式写错一次（**同类错误第二次复发**）：用子串 `'trp-language-switcher' in body` 判「切换器 markup 没了」，
   而该子串也出现在 asset 的 id/href 里 ⇒ 误报。改为锚 **markup**（`trp-language-item` == 0、`<nav class=...>` == 0）。
   这正是普查时 `wp-block-template-skip-link` 教过的 —— **字符串出现 ≠ markup 存在**。

---

## 8. 服务器日志：本批零错误

`/var/log/php-fpm/www-error.log` **最新条目 = 21-Sep-2026 09:11:03**，今天（24-Sep）**0 条**；
`/var/log/php-fpm/error.log`（master）今天全是正常 NOTICE（子进程按 `pm.max_requests` 正常回收，退出码 0）。
`WP_DEBUG=false`（`WP_DEBUG_LOG`=false，生产/开发均未开日志落盘）。

⇒ 本批的**代码变更 + DB 变更 + 约 250 次请求**没有产生任何 PHP 错误或警告。

⚠️ 顺带记录一条**历史**（非本批）：`www-error.log` 在 **21-Sep 09:11** 曾连续出现
`Cannot redeclare sinofresh_formula_faq_data()`（发生在**预检副本**目录），此后至今日志无新条目。
它是当时的状况，本批复测（全部 200/301，无 500）证明**当前不触发**；但「预检副本上曾出现函数重声明 fatal」
这一点值得留在记忆里。

---

## 9. ⚠️ 重新启用 zh 的操作清单（三步，**缺一不可**）

> 与 `docs/zh-unpublish-scan-2026-09-24.md` **§6.6** 同一份清单，两处都在。

| # | 动作 | 落在哪 | 漏做的后果 |
|---|---|---|---|
| **1** | `trp_settings['publish-languages']` 加回 **`zh_CN`** | DB（dev）+ **生产随上线 DB 带走** | hreflang 不会重新声明 zh-CN；切换器对访客仍无 zh |
| **2** | `trp_language_switcher_settings['floater']['enabled']` 改回 **`true`** | DB（同上） | zh 回来了但**访客找不到切换入口**（且页面看不出异常，最难发现） |
| **3** | **复验 hreflang 与切换器渲染**（**登出态**） | 抓 `/about/` 数 `<link hreflang>` + 查切换器 markup | 以为恢复了、实际没恢复 |

**第 4 件不用做**：`inc/zh-unpublish.php` 的 301 规则**自动失效**（它读 `publish-languages`，
步骤 1 一做完就不再满足「只含 en_US」）。回归测试＝ `tools/b3e_zh_redirect_unit.py` 的**第一块负对照**。

**另有一条独立的上线前提**：`sitemap`。`blog_public` 0→1 之后复验 `/wp-sitemap.xml` 是否含/不含 `/zh/*`
（当前「不适用」，因为**根本不存在 sitemap**：无 SEO 插件 + `blog_public=0`）。

---

## 10. 回滚方式

**代码**：`git revert 49942b9` 后重装预检（或 pull 后 revert）。

**DB**：基线在 `docs/zh-unpublish-2026-09-24/rollback-baseline.txt`，含两个 option 的
**原始 PHP 序列化串**与 JSON 形式。两条 `wp eval-file` 即还原：

```php
$s = get_option('trp_settings');            $s['publish-languages'] = array('en_US','zh_CN'); update_option('trp_settings', $s);
$w = get_option('trp_language_switcher_settings'); $w['floater']['enabled'] = true;       update_option('trp_language_switcher_settings', $w);
```

> ⚠️ 用 `wp eval-file` 或 `wp option patch`，**不要**把 JSON 直接写进 `option_value` ——
> 两个 option 存的是 **PHP 序列化数组**（实测 `a:11:{...}`），写 JSON 会破坏它。

**注意部署通道不同**：`publish-languages` 等是 **DB 状态**，重定向是 **代码** ——
上线（或回滚）时**两件都要带**，否则会出现「重定向在、zh 仍被发布」或反之。

---

## 11. 本批未做 / 复现命令

**未做**：未 pull（等确认）；未碰生产（HEAD 读响应头属授权内，本批未再发）；未跑机器翻译回填；
未改 `translation-languages`；未动词典表；未 bump 版本；未改任何模板/post meta。

```bash
PY=/Users/meng/.workbuddy/binaries/python/versions/3.13.12/bin/python3
PHP=/Users/meng/Library/Application\ Support/Local/lightning-services/php-8.2.29+0/bin/darwin-arm64/bin/php

# 1 离线用例（31 条，跑真实 PHP 文件）
$PY tools/b3e_zh_redirect_unit.py
# 2 全量对照（54 路由 × 2 侧，登出态；约 5.5 分钟，两侧各 sleep 1.3s）
$PY tools/b3e_zh_verify.py --json docs/zh-unpublish-2026-09-24/verify.json
# 3 帧（视觉证据；301 不靠浏览器证明）
/Users/meng/.workbuddy/binaries/python/envs/default/bin/python tools/b3e_zh_shots.py
# 4 预检安装（改代码后）
$PY tools/b2d_s1_preflight.py install <40 位 SHA>
```

> ⚠️ 复现 2 之前必须先确认 DB 状态：`publish-languages` 若已含 `zh_CN`（即已重新启用），
> 全量对照的**预检侧会全部变成 200** —— 那是正确行为（规则自愈），不是回归。
> **先跑 1 的第一块**能立刻区分这两种情况。

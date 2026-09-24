# 移出 zh_CN（方案 B）— 执行前只读扫描

**日期**：2026-09-24　**性质**：**只读**（未改 `trp_settings`、未改主题、未写任何文件到站点）
**站点**：`https://dev.zxpet.com`（live 主题 2.10.79 / `5b6beb3`；生产 `zxpet.com` **零接触**）
**口径**（用户裁定，本轮四条补充）：① **验收一律登出态**（切换器对管理员读 `translation-languages`，登录态会误判）
② `translation-languages` **保留**（2388 行词典留在编辑器可访问，将来方案 A 复用）③ sitemap 那条按实情标注
④ 紧迫性＝「上线前必须清掉」，不为它打乱其他批次

> **本轮未实施任何变更。** 结论在本文件 §5–§8，等确认。

---

## 1. 结论速览

| 你的要求 | 扫描结论 | 依据 |
|---|---|---|
| 1 移出 `publish-languages` | ✅ **可行，且按机制应能达成要求 3 的 hreflang 部分** | hreflang 生成读的正是 `publish-languages`（§3） |
| 2 `/zh/*` → 301 逐页回 EN | ✅ **可行且安全**：54 条 ZH 路由**去前缀后 100% 有 EN 对应页**（0 条孤儿） | §2 |
| 3-a hreflang 不再声明 `zh-CN` | ✅ **代码可证** | `class-url-converter.php:222` |
| 3-b 切换器不再出 zh 选项 | ⚠️ **zh 链接会消失，但浮动按钮本身不会消失**（预测为空下拉）｜**需裁决** | §4 |
| 3-c sitemap 不再含 `/zh/*` | ⚪ **「不适用」——当前根本不存在 sitemap** | §5 |
| 4 保留 2388 行词典 | ✅ **本方案完全不触碰该表** | §6 |
| 5 先扫后停 | ✅ 本文件 | — |

**两个必须实测才知道的量**（静态读码两可，见 §7）：
① 移出后 `/zh/about/` 是 200 还是 404；② 单语言时浮动按钮的真实外观。

---

## 2. 现状：设置与 `/zh/*`

### 2.1 `trp_settings`（TP 3.3.6，只读读取）

```json
{"default-language":"en_US",
 "translation-languages":["en_US","zh_CN"],
 "url-slugs":{"en_US":"en","zh_CN":"zh"},
 "publish-languages":["en_US","zh_CN"],
 "native_or_english_name":"native_name",
 "force-language-to-custom-links":"yes",
 "add-subdirectory-to-default-language":"no",
 "trp-ls-floater":"no","floater-position":"bottom-right"}
```

> ⚠️ **`publish-languages` 必须整项覆盖写**：它是数组，`wp option patch` 不适用；
> 且 `class-upgrade.php:2062-2074` 有一段「若两者互为子集则把 publish 重置为 translation」的旧 bug 修补逻辑
> ⇒ 写入后**必须回读确认**，不能假定写成功。

**已装插件**：akismet、gravityforms、**translatepress-business**、translatepress-multilingual、
wp-consent-api、wp-mail-logging、wp-statistics。
**没有任何 SEO 插件**（Yoast / RankMath / SEOPress / AIOSEO 均无）。
**已启用附加组件**：`tp-add-on-extra-languages`、**`tp-add-on-seo-pack`**；`automatic-language-detection` **关闭**（这点后面很关键）。

### 2.2 `/zh/*` 实测（访客态，本轮新抓）

| 路径 | 状态 | 备注 |
|---|---|---|
| `/zh/` | 200 | |
| `/zh/about/` | 200 | |
| `/zh/does-not-exist-xyz/` | **404** | 不存在的路径**本来就 404**，没有被索引的垃圾 |
| `/zh`（无尾斜杠） | **301 → `/zh/`** | 实施后会变成 301 → `/`（少一跳） |
| `/zh/feed/` | **200** | 语言前缀下的 feed 也能通 |
| `/zh/wp-json/wp/v2/types` | **200** | ⚠️ REST 在语言前缀下也通 ⇒ 重定向规则**必须排除**这类前缀 |
| `/zh/?s=test` | 200 | 搜索 |
| `/zh/sitemap.xml` | 404 | |

**逐页映射的可行性证明**：54 条 ZH 路由 **全部 200**，54 条 EN 路由**全部 200**，
且 **`/zh/{path}/` 去前缀后找不到 EN 对应页的有 0 条** ⇒ 「逐页对应、不跳首页」不是近似，是**逐条成立**。

**另一条方法学发现**：`url_to_postid()` 对全站 54 个已发布对象只命中 **53/54**，**唯一失配是 `/blog/`**
（`url_to_postid('/blog/')` 返回 0，实际是 page id=31，permalink 正常 200）——这是 WP 的解析边界。
⇒ **判「EN 目标是否存在」不要依赖解析器**；直接剥前缀最稳（§6 方案）。

---

## 3. hreflang：来源、位置、受哪个设置项控制

**不是主题输出的。** 主题全仓 grep `hreflang` 只在 `docs/` 的说明文里出现，**零代码**。

**来源**：`translatepress-multilingual/includes/class-url-converter.php:200 add_hreflang_to_head()`：

```php
$languages = $this->settings['publish-languages'];      // ← 前台走这一支
if ( $is_editor_preview ) {
    $languages = $this->settings['translation-languages'];   // ← 仅编辑器预览
}
```

**⇒ 把 `zh_CN` 移出 `publish-languages`，前台 hreflang 的 `zh-CN` / `zh` 两条会随之消失。要求 3-a 由机制保证。**

**输出位置**：`<head>` 内、`<link rel="canonical">` 之后。每页 **4 条**：

```html
<link rel="alternate" hreflang="en-US" href="https://dev.zxpet.com/about/"/>
<link rel="alternate" hreflang="zh-CN" href="https://dev.zxpet.com/zh/about/"/>
<link rel="alternate" hreflang="en"    href="https://dev.zxpet.com/about/"/>
<link rel="alternate" hreflang="zh"    href="https://dev.zxpet.com/zh/about/"/>
```

（EN 页与 ZH 页输出的**是同一组**。无 `x-default` —— `trp_advanced_settings.enable_hreflang_xdefault = 'disabled'`；
`hreflang_remove_locale = 'show_both'` 是「同时输出带地区与不带地区两种」的开关，即上面这 4 条。）

---

## 4. 切换器：渲染逻辑 + 一个会骗人的陷阱

**不是主题输出的。** 主题里对切换器**零代码**（只有 `_backup/header.html` 里一句注释说它「等 WPML 上线前先注释掉」）。

**来源**：`trp_language_switcher_settings.floater.enabled = true`，`type: dropdown`，`bottom-right`；
模板 `partials/floating-switcher.php`；语言列表 `includes/class-language-switcher-v2.php::get_language_items()`：

```php
$codes = current_user_can( 'manage_options' )
    ? ( $this->settings['translation-languages'] ?? [] )   // ← 管理员
    : ( $this->settings['publish-languages']     ?? [] );  // ← 访客
```

> 🔴 **这就是你第 1 条提醒的坑，已确认**：**登录态**看切换器，读的是 `translation-languages`，
> 而你要保留它 ⇒ **登录态会看到 zh 仍在，从而误判「要求 3-b 没达成」**。
> **本文件及后续所有验收：一律登出态**（curl 与 agent-browser 走的 nginx Basic 不是 WP 登录，天然访客态）。

**渲染结构**（`floating-switcher.php`）：当前语言渲染成**非链接控件**（`<div role="button">`），
下拉里只放「其它语言」：`$others = array_slice( $list, 1 );`

**访客态基线（实施前，取自已采语料）**：

| 页面 | 当前控件文字 | 下拉里的可点击项 |
|---|---|---|
| `/about/` | `English` | 1 个：`简体中文` → `/zh/about/` |
| `/zh/about/` | `简体中文` | 1 个：`English` → `/about/` |

**单语言时的行为（预测，需实测确认）**：唯一守卫是

```php
if ( empty( $list ) || !isset( $list[0]['code'] ) ) return '';   // :325-326
```

`publish-languages = [en_US]` 时 `$list` 仍有 1 项 ⇒ **不会返回空** ⇒
**浮动按钮仍然渲染**（显示 `English`），**但下拉是空的**。
⇒ **「点了回 EN」这一半达成不了——因为连可点项都没有；按钮会变成一个开了也空的壳。**
这是本方案唯一需要你裁决的副作用，见 §6 第 3 项。

---

## 5. sitemap：标为「不适用」

**实测 + 代码双重结论：当前站点根本没有 sitemap 可验证。**

1. **核心 sitemap 被关**：`wp option get blog_public` = **0**（本轮实测；`/wp-sitemap.xml`、`/sitemap_index.xml` 均 404）。
2. **没有 SEO 插件**：所以不存在「SEO 插件生成的 sitemap」。
3. **TP 的 SEO Pack 附加组件（虽已启用）不碰核心 sitemap**：它的 sitemap 钩子**全部只挂 SEO 插件**
   （`wpseo_sitemap_url`、`rank_math/sitemap/url`、`seopress_sitemaps_url`、`aioseo_sitemap_posts`），
   **没有任何 `wp_sitemaps`（WP 核心）钩子**。
4. 而且它写 sitemap 时读的也是 `publish-languages`（`add-ons-advanced/seo-pack/class-seo-pack.php:277`、`:441`）
   ⇒ **机制上「移出 `publish-languages`」同时也把「sitemap 里塞 /zh/*」这条路关掉了。**

⇒ **要求 3-c 标「不适用」**（不是「有 sitemap 但不含 /zh/*」，而是**没有 sitemap**）。
**复验时点**：`blog_public` 0→1（生产上线清单里那条）之后，且若届时装了 SEO 插件。

---

## 6. 实施方案（**已确认并执行**）

> **执行记录见 `docs/zh-unpublish-2026-09-24.md`**。本节保留当时的方案与裁决依据，
> 6.1–6.4 的结论全部落实；6.5 是裁决结果；**6.6 是将来重新启用 zh 的操作清单**。

### 6.1 改动清单（两处，性质不同）

| # | 改什么 | 落在哪 | 生效方式 |
|---|---|---|---|
| 1 | `trp_settings['publish-languages']` → `["en_US"]` | **dev 数据库**（option） | 立即；**生产需随上线 DB 一并带过去** |
| 2 | `/zh/*` → 301 剥前缀 | **主题代码**（走预检→门→确认） | dev 立即；生产随 `git pull` |

> ⚠️ **注意两者的部署通道不同**：①是 DB 状态，②是 `git`。上线时**两件都要带**，
> 否则会出现「重定向在、但 zh 仍被发布」（此时 hreflang 又回来了）或反之。已记入生产上线清单。

### 6.2 重定向落点：推荐 **A**

| | A 主题 `inc/` 内新文件＋`functions.php` 一处 `require`（**推荐**） | B nginx `location ^~ /zh/` |
|---|---|---|
| 单一真源 | ✅ 在 git 里，dev/prod 同一份 | ❌ dev 与 prod 各配一遍 |
| 与现有纪律 | ✅ 走既有 预检→门→确认→pull | ❌ 绕过门 |
| 上线成本 | ✅ 随 `git pull` | ❌ 上线时另开配置变更 |
| 性能 | 每请求一次 PHP（可忽略；301 可缓存） | ✅ 最快 |
| 能否做「只重定向真实存在的前缀」 | ✅ 可以 | ❌ 只能无条件剥前缀 |

### 6.3 规则形态：**从 `trp_settings` 动态派生（自愈）**

不把 `/zh/` 写死。规则＝「**在 `translation-languages` 里、但不在 `publish-languages` 里、且不是默认语言**的语言，
取其 `url-slugs` 值作为前缀」，命中就 301 剥掉该前缀。

**好处**：`zh_CN` 一旦重新发布（方案 A 完成），规则**自动失效**，零代码改动、零遗忘风险。
这也正好兑现你说的「翻译完成后再重新启用即可」。

**具体行为**：
- 只对 `GET` / `HEAD` 生效（不碰 POST）
- **挂 `template_redirect`（priority 1）**，**不加 `is_404()` 门** —— 因为「移出后 `/zh/about/` 是 200 还是 404」静态读码两可（§7），两种情况下都要能 301
- 保留 query string
- 排除非页面前缀：`wp-json`、`wp-admin`、`wp-content`、`wp-includes`、`wp-login.php`、`xmlrpc.php`、`cdn-cgi`、`feed`
- 跳过 `?trp-edit-translation=…` —— **否则将来 TP 翻译编辑器打不开 zh 版本**（编辑器预览靠 `/zh/…?trp-edit-translation=preview`，见 `class-url-converter.php:219`）
- 跳过 `is_admin()` / `wp_doing_ajax()` / `wp_doing_cron()`
- 目标＝`home_url(剥掉前缀后的路径)`；`/zh/` → `/`

### 6.4 不需要动的东西（守住你的第 4 条）

- ❌ 不动 `wp_trp_dictionary_en_us_zh_cn` 的 2388 行（本方案完全不读写该表）
- ❌ 不动 `translation-languages`（保留 zh_CN）
- ❌ 不动 `url-slugs`、`default-language`、`add-subdirectory-to-default-language`
- ❌ 不动 `trp_advanced_settings`（`disable_languages_sitemap` 保持 `no`：它只对有 SEO 插件的场景有意义，现在无 sitemap，改它没作用）

### 6.5 四项裁决结果（用户已定）

| # | 项 | 裁决 | 理由（用户原话摘要） |
|---|---|---|---|
| ① | 落点 | **A 主题 `inc/` 新文件 + `functions.php` 一处 `require`** | git 单一真源、走既有预检→门→确认、生产随 `pull` 生效；规则是业务逻辑（依赖 `trp_settings`），不是传输层配置 |
| ② | 规则形态 | **动态派生**（读 `publish-languages`，只含 `en_US` 时才挂 301） | zh 重新发布后规则自动失效，兑现「翻译完再启用」；写死 `/zh/` 会在 zh 恢复后变成错误重定向 |
| ③ | 空壳切换器 | **关掉 floater**（`floater.enabled = false`） | 单语言下只显示 English、下拉为空的浮动按钮是无意义 UI，保留反而暗示有其它语言 ⇒ **并须记入 6.6** |
| ④ | `?trp-edit-translation` 豁免 | **同意豁免，但范围收窄** —— 只豁免带该参数的请求，**不是整个 `/zh/` 前缀** | 不豁免则将来 TP 编辑器打不开 zh 版本 |

实施时两条强制动作（用户指定）：

1. **`publish-languages` 写入后回读确认** —— `class-upgrade.php:2062-2074` 那段旧修补逻辑可能把它重置回 `translation-languages`。写入后读一次，确认是 `["en_US"]`。
2. **移出后 `/zh/about/` 是 200 还是 404 要先量** —— 实测答案见 §7。

### 6.6 ⚠️ 重新启用 zh 的操作清单（三步，**缺一不可**）

将来方案 A（真翻译）完成后，把 zh 放回来必须**同时**做这三件事，否则会出现「重定向在、但 zh 仍被发布」或「hreflang 没回来」这类半开状态：

| # | 动作 | 落在哪 | 漏做的后果 |
|---|---|---|---|
| **1** | `trp_settings['publish-languages']` 加回 **`zh_CN`** | dev 数据库（option） + **生产随上线 DB 带过去** | hreflang 不会重新声明 zh-CN；切换器对访客仍不出现 zh |
| **2** | `trp_language_switcher_settings['floater']['enabled']` 改回 **`true`** | 同上（option） | zh 回来了但**访客找不到切换入口** |
| **3** | **复验 hreflang 与切换器渲染**（登出态）：`/about/` 应重新出现 `zh-CN`/`zh` 两条 hreflang，切换器应重新出现且列出「简体中文」 | 抓 `/about/` 数 `<link hreflang>` + 解析切换器 `<nav>` | 以为恢复了、实际没恢复（尤其步骤 2 漏做时**页面看不出异常**） |

> **第 4 件不用做**：`inc/zh-unpublish.php` 的 301 规则**自动失效** —— 它读 `publish-languages`，
> 只要该数组不只含 `en_US`（步骤 1 一做完就成立）规则立即停止动作。这是选「动态派生」换来的。
> 验证这一点不需要改动任何代码：`tools/b3e_zh_redirect_unit.py` 的第一块用例（`publish-languages`
> 含 `zh_CN` 时规则必须一动不动）就是它的回归测试。

**还有一条独立于本清单的上线前提**：`sitemap` 相关。`blog_public` 0→1 之后才需复验
`/wp-sitemap.xml` 是否含/不含 `/zh/*`（当前标为「不适用」，见 §5）。

---

## 7. 两个「实施后立刻测」的未知数 —— **已实测**

### 7.1 `/zh/about/` 移出后是 200 还是 404？→ **是 404**

不是 200。而且这个答案本身无法直接观察（下面解释），是用**源码 + 实测**两步定下来的：

1. **实测**：移出后对 `/zh/about/` 发未跟随的请求（live 侧，主题里**没有**本次新代码），得到
   **301**，`X-Redirect-By: WordPress` ⇒ 是**核心**发的，不是本批规则。
2. **归因**：核心的这条 301 来自 `redirect_canonical()` → `redirect_guess_404_permalink()`
   （`wp-includes/canonical.php:215` 调用、`:927` 定义），而该调用**位于 `:147 if ( is_404() )` 分支之内**。
   ⇒ **请求必须先被判成 404，才可能进入这个猜测**。所以移出后 `/zh/about/` 的真实状态是 **404**，
   只是被核心的「404 猜测」顺手转成了 301。
3. 断言的落点：核心那个函数有守卫 `if ( get_query_var( 'name' ) )`。page 路径（`/zh/about/`）
   有 `name`（解析为 `about`）⇒ 猜得中；**CPT 重写路径（`/zh/formulas/{slug}/`）与根路径（`/zh/`）
   连 `name` 都没有 ⇒ 一律留成 404**（实测两例均为 404）。

**对方案的实际影响**：静态读码当时给出的「倾向 200」是**错的**，但 §6.3 的设计（挂
`template_redirect` priority 1 且**不设 `is_404()` 门**）在两种结果下都成立 —— 这正是它当时
不赌 200 也不赌 404 的原因。

**顺带得到的结论**：核心的 301 只覆盖一部分 `/zh/` 路径（page 类），且靠**前缀 LIKE 猜测**
得到目标；本批规则覆盖全部 54 条且是**精确剥前缀**。两者在实测的 page 类路径上目标恰好一致，
但覆盖范围与确定性不同 —— 见 `docs/zh-unpublish-2026-09-24.md` 的对照表。

### 7.2 单语言时浮动按钮的实际外观？→ **它整个消失了，不存在空壳**

预测是「按钮在、下拉空」（§4 的 `if ( empty( $list ) ) return '';` 守卫）。
实测 `floater.enabled = false` 之后，`/about/` 的响应里
**`trp-floating-switcher` 与 `trp-language-switcher` 双双为 0 命中** —— 不是空壳，是整个不渲染。
⇒ 裁决 ③ 选「关掉 floater」正好把 §6.5 里担心的空壳问题一并消掉，**不需要主题侧再加隐藏代码**。

---

## 8. 实施后的验收清单（**全部登出态**）

| # | 断言 | 手段 |
|---|---|---|
| 1 | `publish-languages` 回读 = `["en_US"]`（防 `class-upgrade.php` 那段逻辑把它重置回去） | `wp option get trp_settings` |
| 2 | 抽样 10 条 `/zh/{path}/` 全 **301**，`Location` 精确等于对应 EN 路径 | curl 不跟随，读 header |
| 3 | `/zh/` → 301 → `/`；`/zh` → 301 → `/`（一跳） | curl |
| 4 | `/zh/does-not-exist-xyz/` 仍是 **404**（没被我们的规则误 301） | curl |
| 5 | hreflang 只剩 `en-US` / `en` 两条，`zh` 相关 0 条 | 抓 `/about/` 数 `<link hreflang>` |
| 6 | **登出态**浮动切换器：可点击项里 `简体中文`/`/zh/` **0 命中** | 抓 `/about/` 解析 `<nav trp-floating-switcher>` |
| 7 | `/zh/wp-json/wp/v2/types` **未被 301**（仍 200） | curl |
| 8 | EN 侧逐字节回归：EN 页与改动前**逐字节相同**（本次不应影响 EN） | 掩码比对（既有 `b3b2_noop_check.py` 手法） |
| 9 | 2388 行词典**行数与内容不变** | `wp db query` 前后各一次 |
| 10 | 全站普查的 108 页重抓，除 `/zh/*` 变 301 外**无新增异常** | `b3d_crawl.py` 复跑 |

---

## 9. 风险与依赖

- ✅ **重定向环：已排除。**
  - TP 前端唯一的 301（`compatibility-functions.php:1370`）只在 **Oxygen / Beaver** 构建器场景（本站没装）。
  - v2 切换器的 `resolve_language_context()` 三个跳转条件在本站**全不成立**：
    `add-subdirectory-to-default-language = no`，且 `determine_needed_language()` 在 URL 有语言时直接返回该语言
    ⇒ 只有「自动语言检测（ALD）附加组件」经 `trp_needed_language` 过滤器才可能改变它，而 **ALD 是关闭的**。
  - **TP 前端不读 `$_COOKIE['trp_language']`**（全插件只有 `user_meta` 用法）。
  - ⚠️ **但要把这条记成前提**：**将来若启用 ALD**，它可能把访客推向 `/zh/`，届时与本 301 构成环
    ⇒ 启用 ALD 前必须重验。已记入记忆。
- ⚠️ **生产通道**：`publish-languages` 是 DB 状态，`trp_add_ons_settings` / `trp_language_switcher_settings` 同理
  ⇒ 上线时**随 DB 一起带**，不要只在 dev 改。重定向是代码 ⇒ 随 `git pull`。（已列入生产上线清单）
- ⚠️ **Cloudflare**：dev 在生产 CF 后面（有 `/cdn-cgi/l/email-protection`），301 可被 CF 缓存；实施后若见旧状态，先怀疑缓存。
- ⚠️ **本次不动生产**。`zxpet.com` 当前 302 → `/maintenance.html`（维护中）。
  > 📌 边界澄清（用户本轮）：**HEAD 读响应头属已授权范围**，不算越界；不得发 POST/GET 爬生产页面。
  > 上一轮我主动标记的那次越界据此撤销——记录改为「在授权内的 HEAD」。

---

## 10. 本轮未做 & 复现命令

**未做**：未改任何设置 / 主题 / DB；未跑机器翻译；未动 2388 行词典；未接触生产页面。

```bash
# 设置与附加组件（只读）
ssh root@65.49.215.152 'cd /var/www/dev.zxpet.com/public && wp option get trp_settings --format=json --allow-root'
ssh root@65.49.215.152 'cd /var/www/dev.zxpet.com/public && wp option get trp_add_ons_settings --format=json --allow-root'

# /zh/* 现状（登出态；Basic 是 nginx 层，不是 WP 登录）
curl -s -o /dev/null -u 'sfdev:…' -H 'Accept-Encoding: gzip' -w '%{http_code} %{redirect_url}\n' https://dev.zxpet.com/zh/about/

# hreflang / 切换器（用已采语料，离线）
#   语料：docs/site-survey-2026-09-24/cache/（108 页原始字节）
```

**关键源码位置**（供复核）：
- hreflang：`translatepress-multilingual/includes/class-url-converter.php:200-290`
- 切换器列表：`translatepress-multilingual/includes/class-language-switcher-v2.php:536-546`（`get_language_items`）
- 切换器模板：`translatepress-multilingual/partials/floating-switcher.php`
- 跳转判定：`class-language-switcher-v2.php:124-198`（`resolve_language_context` / `redirect_to_correct_language`）
- SEO Pack 写 sitemap：`translatepress-business/add-ons-advanced/seo-pack/class-seo-pack.php:260,277`

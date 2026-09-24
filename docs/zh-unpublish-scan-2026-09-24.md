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

## 6. 实施方案（待确认，**未执行**）

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

### 6.5 需要你裁决的 4 项

1. **落点**：A 主题（推荐）还是 B nginx？
2. **规则形态**：动态派生（推荐）还是写死 `/zh/`？
3. **空壳切换器怎么办**（本方案唯一副作用）：
   - **(a) 同时关掉浮动切换器**：`trp_language_switcher_settings.floater.enabled = false`（第二个 DB 改动；将来启用 zh 时要记得开回来）
   - **(b) 主题侧隐藏**：单语言时不渲染切换器（自愈，但属主题改动，多一份代码）
   - **(c) 接受**：留着「English ▾」空壳（最省事，但访客点开会迷惑）
   - 我的倾向：**(a)**，因为它和「关一个语言」同属一类动作、同一步做完，且单语言站留着语言切换器本身就不合理。
4. **`?trp-edit-translation` 豁免**：建议豁免（保住将来翻译编辑器的 zh 入口）。同意吗？

---

## 7. 两个「实施后立刻测」的未知数

静态读码得不出答案，只能改完立刻量：

1. **`/zh/about/` 移出后是 200 还是 404？**
   - `class-translation-render.php:83` 按 **`translation-languages`** 决定是否翻译 ⇒ 我们保留了它 ⇒ **倾向 200**（内容仍英文，且 `$TRP_LANGUAGE=zh_CN`，即 `<html lang="zh-CN">` 打在英文上）。
   - 但 URL 解析是否也过滤 `publish-languages`，静态读码两可。
   - **两种结果都被 §6.3 的设计覆盖**（挂在 `template_redirect` 且不设 404 门）。
2. **单语言时浮动按钮的实际外观**：预测是「按钮在、下拉空」（§4）。要拍帧确认。

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

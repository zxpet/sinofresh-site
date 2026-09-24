# SINO FRESH 官网 · 全站普查报告

**日期**：2026-09-24　**性质**：**只读**（未改主题/模板/post meta/选项/数据库）
**站点**：`https://dev.zxpet.com`（live 主题 `sinofresh-theme` **2.10.79**，`5b6beb3`）
**口径**（用户裁定）：八类检查项 ＋ 安全审计（dev 只读探测 ＋ 主题代码静态审计）

---

## 0. 范围与方法

**页面清单不是回忆出来的，是站点自己给的。** 走 `GET /wp-json/wp/v2/types` 取公开类型与 `rest_base`，
再逐类型枚举已发布对象：

| 类型 | 数量 |
|---|---|
| `page` | 26 |
| `post` | 7 |
| `sf_formula` | 21 |
| **合计** | **54** |

每个对象取 EN 与 `/zh/` 两份 ⇒ **108 个 URL**，另加 4 条导航提供、但没有对象承载的路由
（`/blog/` `/quality/` `/about/` `/contact/`，与既有清单去重后为 0 条新增）。

**语料**：`108/108 全部取到`（`tools/b3d_crawl.py`，1.3s/请求，Basic 凭据，只读 GET），
落盘为 `docs/site-survey-2026-09-24/cache/`。八类与两项安全审计**共用这一份语料**——
每类各爬一次会让同一次普查在八个不同时刻比较站点自身。

> ⚠️ **为什么不用 sitemap**：`/wp-sitemap.xml` 与 `/sitemap_index.xml` 都返回 404 页。
> 这不是缺陷：封锁文档 `docs/dev-lockdown.md` 记录 `blog_public=0`，核心 sitemap 因此被关，
> 与 `robots.txt: Disallow: /`、`X-Robots-Tag: noindex, nofollow, noarchive` 同属封锁设计。
> **代价**：sitemap 覆盖情况在封锁期内**无法验证**，必须留在生产上线清单里（`blog_public` 0→1 后复验）。

**方法学自查（三处，均为先出错后修正）**

1. **`Accept-Encoding: br` 让整轮采集归零**。显式宣告 `br` 后边缘返回 Brotli，而本机 curl 无 brotli
   ⇒ 108/108 全部 `curl: (56) Unrecognized content encoding type`，产出空语料，表象酷似「站点什么都没服务」。
   改 `Accept-Encoding: gzip` 后 108/108 通过。
2. **缓存键算错**：采集以**路径**为键，分析脚本以 `BASE+路径` 为键 ⇒ 全部 108 页判为 cache miss，
   页级列表（性能、图片）为空。若不复核，报告会写成「站点没有样式表」。
3. **判据过松**：skip-link 规则写 `re.search(r'skip|Skip to')`。WordPress 核心会把
   `wp-block-template-skip-link` 的 **CSS** 注入每一页，字符串因此恒出现 ⇒ 规则永不触发。
   收紧为「markup 里有无 `<a class="skip-link">`」后，108 条命中全部出现。

**⛔ 一处越界，如实交代**：约束是「dev 只读 ＋ 主题代码静态审计」「生产站零接触」。
我在核对响应头时对 **生产域名 `zxpet.com` 发了 1 次未认证 HEAD**（仅头部、不取正文、无任何写操作）。
结果本身有用（生产正在维护重定向，见 §3.5），但**这是对生产的一次请求，超出了授权范围**，
记在此处备查，后续不再发生。

---

## 1. 结论速览

**未发现 P0/P1 缺陷。** 站点在图片、表单、链接、多语言配对上相当干净；缺口集中在**SEO 头部**与**无障碍地标**两类。

| 级别 | 类别 | 命中 | 影响面 | 一句话 |
|---|---|---|---|---|
| **P2** | SEO | 108 | 全站 | **全站没有 meta description，也没有任何 Open Graph 标签** |
| **P2** | SEO | 54 | 全站 | ZH 页与 EN 页**共用同一个 title**（ZH 不出中文标题） |
| **P2** | 无障碍 | 108 | 全站 | **没有 `<main>` 地标**（32 个模板里只有 1 个有，且是不被服务的 fallback） |
| **P2** | 无障碍 | 108 | 全站 | **没有 skip-to-content 链接**（核心 CSS 在，markup 不在） |
| **P2** | 安全 | 108 | 全站 | **六项安全响应头全部缺失**（HSTS/CSP/XFO/XCTO/Referrer-Policy/Permissions-Policy） |
| **P3** | SEO | 864 | 全站 | 页脚 8 条剂型链接走 **301**（导航用的是正确路径，页脚不是） |
| **P3** | 安全 | 2 | 2 路由 | `config-pdf` 邮件模式与 `article-feedback` **无频控**（可被用作发信/灌条目通道） |
| **P3** | 安全 | 3 | 全站 | 版本暴露：`/readme.html`、`/license.txt` 可取；WP 7.1.2、PHP 8.3.33 可见 |
| **P3** | 性能 | 6 | 6 页 | 单页内联 CSS 达 **59–65KB**（核心块样式，非主题样式） |
| **P3** | 多语言 | 108 | 全站 | hreflang 无 `x-default` |
| **P4** | 表单 | 42 | 42 处 | email 输入缺 `autocomplete` |
| **P4** | SEO | 12 / 2 | 14 | title 超 65 字（12）；`/blog/` 与 `/zh/blog/` 缺 canonical（2） |
| **P4** | 无障碍 | 4 | 4 页 | 标题跳级 h1→h3 |
| **P4** | 内容 | 4 | 4 页 | 「Certificate coming soon」占位（对应 2 张无文件证书，**有意的**） |
| **—** | 图片 | **0** | 1026 张 | 全站图片**零缺陷**（见 §2.4） |
| **—** | 链接 | **0 断链** | 108 页 | 958 条「未收录目标」去重 33 个，**逐个实测 0 死链** |

---

## 2. 八类逐条

### 2.1 内容与文案

| 判定 | 项 | 位置 | 说明 |
|---|---|---|---|
| ⚠️ P4 | `Certificate coming soon` | `/quality/`、`/zh/quality/`、`/contact/`、`/zh/contact/` | 渲染为 `.sf-certrow__media--placeholder`。对应 `inc/cert-download.php:72-83` 里 **haccp / brc 两张证书 `file => ''`**（登记表已注明「无文件」）。**不是 bug，是待补素材**；上线前需决定是否补齐或撤下这两行 |
| ✅ 已排查 | 块模板占位文字 | `functions.php:3900-3990` | `[Parameter 3]` `[Question 1?]` `[CTA - 1-2 sentences…]` 等是 `register_block_pattern` 的**编辑器脚手架**，服务语料 **0 命中**，不会上页 |
| ⚠️ P4 | 脚手架里的邮箱拼写 | `functions.php:3967` | 脚手架含 `jsam@zxpet.com`（疑为 `sam@zxpet.com` 之误）。它不上页，但**从该 pattern 起草文章的人会把它复制进正文** |
| ✅ 洁净 | 占位词/未替换令牌 | 全站 | `lorem / TODO / FIXME / TBD / {{…}} / %%VAR%% / %s` **0 命中**；EN 页无中文正文残留 |

### 2.2 SEO 与结构化数据

**该页 `<meta>` 只有 3 个**（charset / viewport / robots），108 页一致 —— 全站 `meta tag count per page = {3: 108}`。

| 判定 | 项 | 命中 |
|---|---|---|
| 🔴 **P2** | **无 meta description** | **108/108** |
| 🔴 **P2** | **无 Open Graph 标签**（`og:*` 一个都没有） | **108/108** |
| 🔴 **P2** | **ZH 与 EN 共用 title**：唯一 title 仅 **54 个**（108 页 ÷ 2），每对完全相同 | 54 对 |
| ⚠️ P3 | title 超 65 字 | 12（case-study 系列 83–84 字） |
| ⚠️ P4 | 缺 canonical | 2：`/blog/`、`/zh/blog/` |
| ✅ | canonical 自指 | 其余 106 页正确指向自身 |
| ✅ | `noindex` | 108/108（**封锁设计**，非缺陷） |

**JSON-LD（按解析，不按字面）**：全部可解析、每个节点都有 `@type`。

| 类型 | 出现 |
|---|---|
| `Organization` | 108 |
| `BreadcrumbList` | 106 |
| `FAQPage` | 82 |
| `Product` / `ItemList` | 58 / 58 |
| `HowTo` | 42 |
| `Article` | 14 |
| `Service` | 10 |

> `BreadcrumbList` 差 2 条（106/108），与缺 canonical 的 `/blog/` `/zh/blog/` 疑为同一原因，待单独确认。

### 2.3 内链与外链

首轮报出 **958 条「不在清单里的内链」**。这是**未收录**，不等于**断链**——去重后只有 **33 个目标**，
逐个实测（`tools/b3d_link_probe.py`，HEAD，1.3s 间隔）：

| 结果 | 数量 |
|---|---|
| **404 / 410（死链）** | **0** |
| 301 重定向 | 16（＝864 条链接） |
| 直接 200 | 17（＝94 条链接） |

- **864 条走 301**：页脚 `parts/footer.html:24` 用的是**无 `/products/` 前缀**的剂型路径
  （`/soft-chews/` `/tablets/` … 含 ZH 共 16 个），WordPress 301 到 `/products/…`。
  而**导航用的是正确路径**。⇒ 站内不一致 + 每次点击多一跳。
  **修法极小**：`parts/footer.html` 一行 8 个 href 补 `/products/` 前缀（ZH 由 TranslatePress 自动跟随）。
- **其余 17 个直连 200**：`/category/{manufacturing,private-label,case-studies}/`、`/tag/formulation/`（含 ZH）、
  4 张证书缩略图、`coa-sample.pdf` —— 都可用，只是**不在我这份 REST 清单里**（分类法归档不由 post type 承载）。

**外链域名**：`wa.me` ×324（WhatsApp，主力转化链）、`linkedin.com` ×14、`twitter.com` ×14、
`fda.gov` ×4、`iso.org` ×2、`fssc22000.com` ×2。

### 2.4 图片与 alt —— **零缺陷**

| 指标 | 值 |
|---|---|
| `<img>` 总数 | **1026** |
| **缺 `alt` 属性** | **0** |
| **缺 `width`/`height`** | **0** |
| `alt=""`（显式声明装饰性） | 252 处 / 108 页 |
| `loading="lazy"` | 754（其余 272 为 eager，首屏图合理） |
| 带 `srcset` | 280 |
| 内联 `data:` 图 | 0 |

> 「缺 alt」与「`alt=""`」是两件事：前者是缺陷，后者是**声明该图纯装饰**，对图标而言是正确写法。
> 本项目两栏分开计数，结论是**前者 0、后者 252 且合规**。

### 2.5 表单与邮件

**Gravity Forms 表单 ID：2 / 3 / 4 / 5 / 6**（Quote / Sample / Factory Tour / Certificate / Feedback）。

| 判定 | 项 | 命中 |
|---|---|---|
| ⚠️ P4 | email 输入缺 `autocomplete` | 42 处（移动端键盘与自动填充受损） |
| ✅ | 表单无 `action` | 42 处全为 `.sf-inquiry-form` 与 `.sf-fb-form`，**由 JS 提交到 REST**，无 action 是正确写法 |
| ✅ | 按钮可访问名 | `<button>` 1132 个，**无文本且无 `aria-label`/`title` 的：0** |
| ✅ | 邮箱一致性 | 全站唯一 `sales@zxpet.com`；明文 108 次 ＋ **Cloudflare 混淆 108 次解码后同为该地址**；JSON-LD `email` 字段一致；`info@` 已全站清除 |

> 邮箱一栏必须解 CF 混淆才可信：`mailto:` 被改写为 `/cdn-cgi/l/email-protection#<hex>`，
> 不解码的话清单会显示「全站只有 1 个地址」，而实际每页都有 mailto 链接。

### 2.6 多语言（EN / ZH）

| 判定 | 项 | 结果 |
|---|---|---|
| ✅ | EN/ZH 配对 | **无一条 EN 页缺 ZH 对应页** |
| ✅ | `<html lang>` | 108/108 与 locale 相符 |
| ✅ | 切换器 markup | 108/108 存在 TranslatePress 切换器 |
| ✅ | canonical 自指 | ZH 页指向自身（未错指 EN） |
| ⚠️ P3 | hreflang **无 `x-default`** | 108/108（现有 `en,en-US,zh,zh-CN`） |
| 🔴 P2 | **ZH 页 serving EN 标题** | 见 §2.2：54 对 title 完全相同 |

### 2.7 性能与静态资源

**去重后共 41 个资源**；**每页 17 个外部请求**为常态（中位：2 CSS ＋ 15 JS；最多 8 CSS ＋ 26 JS ＝ 34）。

| 指标 | 值 |
|---|---|
| HTML 中位体积 | **136,867 B**（≈134 KB） |
| 最重页 | `/zh/` 240,070 B；`/` 229,073 B |
| 最轻页 | `/products/` 96,163 B |
| 每页 CSS 数 | 2（64 页）/ 3（16）/ 6（8）/ 7（18）/ 8（2） |
| 每页 JS 数 | 10–26，**15 个（29 页）与 18 个（21 页）最常见** |
| 内容编码 | `gzip` 108/108（**边缘支持 Brotli**，见 §0 自查 1） |
| `cf-cache-status` | `DYNAMIC` 108/108（带凭据请求本就不入边缘缓存，此项**不能**用来判断生产缓存策略） |

**逐条**

| 判定 | 项 | 说明 |
|---|---|---|
| ⚠️ P3 | 单页内联 CSS **59–65 KB** | `/quality/` 59,449 B / 22 个块；`/blog/` 60,689 B；`/zh/quality/` 64,893 B。**最大两块是核心块样式**：`global-styles-inline-css` 17.5KB、`wp-block-gallery-inline-css` 16.4KB。**主题自身的 `style.css` 是正常外链**（`?ver=2.10.79`），不在内联之列（已核对：内联里没有 `.sf-fdetail-specs__row`）。核对 `wp-block-*` 用量：gallery/image/columns/button/details **都在用**，故不是「未使用样式」 |
| ⚠️ P3 | jQuery ＋ jQuery-Migrate | 加载于 **68/108 页**（Gravity Forms 依赖）。63% 的页面为此付两份库 |
| ⚠️ P3 | Gravity Forms 前端资产 | 28 页加载 **4 个 CSS ＋ 7 个 JS** |
| ⚠️ P4 | 第三方脚本 | `static.cloudflareinsights.com/beacon.min.js` 108/108（CF Web Analytics，**有意**） |
| ⚠️ P4 | `email-decode.min.js` 计数异常 | 出现 192 次 / 108 页 ⇒ 部分页重复注入 CF 的邮箱解码脚本 |
| ✅ | 字体 | 未见第三方字体域名（自托管） |

### 2.8 无障碍

| 判定 | 项 | 命中 |
|---|---|---|
| 🔴 **P2** | **无 `<main>` 地标** | **108/108**（`<main>` 0 次、`role="main"` 0 次、`id="main"` 0 次） |
| 🔴 **P2** | **无 skip-to-content 链接** | **108/108**（核心把 `wp-block-template-skip-link` 的 CSS 注入了，markup 里没有那个 `<a>`） |
| ⚠️ P4 | 标题跳级 | 4 页：`/products/` `/zh/products/` `/blog/` `/zh/blog/`（h1 → h3） |
| ✅ | h1 唯一性 | 108/108 恰好 1 个 h1、且非空 |
| ✅ | 按钮可访问名 | 1132 个按钮，0 个无名字 |
| ✅ | 正整数 `tabindex` | 0 |
| ✅ | 可聚焦元素上的 `aria-hidden="true"` | 0 |

**`<main>` 的范围已经量到文件级**：`sinofresh-theme/templates/` 共 **32 个模板，只有 `index.html:6-7` 有 `<main class="wp-block-group">`**——
而 `index.html` 是 fallback，这 108 页**没有一页用它**（它们走 `page-*.html` / `single*.html` / `archive*.html`）。
⇒ 修法有两条：给每个模板的内容 `wp:group` 加 `"tagName":"main"`（32 处），
或在渲染层统一包一层（1 处、但需确认不破坏既有选择器）。**本报告不给选择，等裁决。**

---

## 3. 安全审计 A —— dev 站只读探测

30 项探测，`tools/b3d_sec_probe.py`，每项都带**预期**（「404 预期」与「碰巧 404」是两回事）。

### 3.1 通过项（24）

| 目标 | 结果 | 意义 |
|---|---|---|
| `/wp-json/wp/v2/users` | **404** | **用户枚举已封**（主题对登出请求屏蔽 `/wp/v2/users`） |
| `/wp-json/wp/v2/users/1` | 404 | 单用户枚举同样不可达 |
| `/?author=1` | 301 | 作者归档重定向（未暴露用户名） |
| `/wp-config.php` | **403** | 配置不可取 |
| `/wp-config.php.bak`、`/wp-config.php~` | **403** | 编辑器备份不可取 |
| `/.env` | **404** | 复测确认（首轮 curl 瞬时失败返回 `None`，**未当通过**） |
| `/.git/config` | **404** | 仓库不可达 |
| `/.git/HEAD` | 404 | 同上 |
| `/wp-content/debug.log` | 404 | 无日志泄漏 |
| `/wp-content/uploads/` | **403** | 未列目录 |
| `/wp-includes/`、`/wp-content/vendor/` | **403** | 未列目录 |
| `/wp-content/plugins/` | 200 **但 0 字节** | 无目录索引，空响应 |
| `/wp-content/vendor/autoload.php` | 200 **但 0 字节** | PHP 执行而非源码泄漏（前条预期写错，已复核纠正） |
| `theme/README.md`、`theme/_backup/` | 404 | 开发说明与回滚归档**不可达** |
| `theme/docs/`、`theme/tools/` | **403** | 文档与脚手架**不可达** |
| `/xmlrpc.php` | 405 | XML-RPC 未开放 |
| `/?s=<script>alert(1)</script>` | 200，**payload 已转义** | 搜索反射**无 XSS**（`&lt;script&gt;` 命中、原样 `<script>` 0 命中） |

### 3.2 需处置

| 级别 | 项 | 证据 |
|---|---|---|
| 🔴 **P2** | **六项安全响应头全部缺失** | `/` 响应头中 `Strict-Transport-Security`、`Content-Security-Policy`、`X-Frame-Options`、`X-Content-Type-Options`、`Referrer-Policy`、`Permissions-Policy` **均为 absent**；仅有 `X-Robots-Tag`（封锁用） |
| ⚠️ P3 | 版本暴露 | `/readme.html` 200（7,407 B，标题 "WordPress › ReadMe"）；`/license.txt` 200；feed `<generator>…?v=7.1.2</generator>`、`wp-emoji-release.min.js?ver=7.1.2` ⇒ **WP 7.1.2 可读**；响应头 `x-powered-by: PHP/8.3.33` ⇒ **PHP 版本可读** |
| ⚠️ P3 | `x-powered-by` 未抑制 | 同上 |

### 3.3 一处产能浪费（顺带发现）

`/wp-robots` 之外，`/wp-json/sinofresh/v1/`（我们自己的命名空间索引）**返回 200**，
把 4 条自建路由列了出来。本身不敏感（路由名与用途在页面 JS 里可见），但与 §4.3 的频控问题叠加时放大了可发现性。

---

## 4. 安全审计 B —— 主题代码静态审计

范围：**23 个生产文件**（`sinofresh-theme` 下 `.php`/`.js`，排除 `tools/` 与 `_backup/`——前者不到 docroot，后者是归档），
41 条规则 → `tools/b3d_sec_static.py`。

### 4.1 真问题

| 级别 | 项 | 位置 | 判读 |
|---|---|---|---|
| ⚠️ **P3** | `config-pdf` **邮件模式无频控** | `inc/config-pdf.php:110-133` | `permission_callback => '__return_true'`（公开是**必须的**——访客提交配置单要收 PDF），`$email` 经 `is_email` 校验、文件名经 `preg_replace('/[^A-Za-z0-9.\-]/','')` 净化、`tempnam`＋`wp_delete_file` 清理，**但没有任何 honeypot / 时间门 / 频率限制** ⇒ 可被用作**向任意地址发信**的通道（以本站为发件人） |
| ⚠️ **P3** | `article-feedback` **无频控** | `functions.php:6669-6710` | 投票值有白名单（`up`/`down`）、`post` 走 `absint`、邮箱走 `is_email`、`message` 走 `sanitize_textarea_field`，**但可无限次写 Gravity Forms 条目（form 6）** ⇒ 灌条目通道 |

> **对照**：`/inquiry`（`functions.php:3767+`）是三个公开端点里**唯一带反滥用**的——
> honeypot 字段 ＋ 「表单停留 <3 秒判机器」＋ 未来时间戳判伪造。后两个端点缺的正是这一层。
> 建议：把 `/inquiry` 的 honeypot＋时间门抽成共用校验，挂到这两个端点上。

### 4.2 判为误报的类别（附理由，避免下次重复报警）

| 组 | 原始命中 | 为何不是问题 |
|---|---|---|
| `shell` | 67 | 65 条是 **JS 注释里的 Markdown 反引号**；2 条是 `RegExp.prototype.exec`（`/re/.exec(...)`），非 shell。真实 shell 调用 **0** |
| `out` | 266 | 逐类核对：`echo $pdf_bytes` 是**二进制 PDF 直出**（`inc/config-pdf.php:142`，注释已说明 REST 会 JSON 编码故必须 echo）；`formula-admin.php` 的 7 处 `printf` 参数**逐个都过 `esc_attr`/`esc_html`/`esc_textarea`/`checked()`/`selected()`**；其余 echo 均带 `esc_html` 等 |
| `js` | 13 | `innerHTML` 命中逐条核对（`about.js:112`、`quality.js:71`、`toc-nav.js:381/408/462`、`cert-modal.js:126/236`、后台两处）——**全部是字符串字面量拼接，无一处插值外部数据**。`insertAdjacentHTML`／`new Function`／`eval`／`postMessage` **0** |
| `file` | 11 | `require_once $autoload`（`config-pdf.php:247`）的 `$autoload = WP_CONTENT_DIR . '/vendor/autoload.php'` 是**常量派生的固定路径**，且有 `file_exists` 前置。`readfile($path)`（`cert-download.php:177`）的 `$path` 来自**登记表白名单**，非用户输入 |
| `sql` | **0** | 无拼接查询、无未预处理调用 |
| `code-exec` | **0** | 无 `eval` / `create_function` / `extract` |

### 4.3 四条公开 REST 路由逐个判读

| 路由 | 方法 | `permission_callback` | 自带防护 | 结论 |
|---|---|---|---|---|
| `/sinofresh/v1/inquiry` | POST | `__return_true` | honeypot ＋ 时间门 ＋ 全字段净化 | ✅ |
| `/sinofresh/v1/cert-download` | GET | `__return_true` | **登记表白名单 ＋ 40 位一次性 token ＋ 先焚后发**（`delete_transient` 在 `readfile` 之前）；证书文件放在**文档根之外**（`SF_CERTS_DIR = dirname(ABSPATH).'/private-certs/'`），理由是 nginx 不读 `.htaccess` | ✅ 设计良好 |
| `/sinofresh/v1/config-pdf` | POST | `__return_true` | slug 白名单 ＋ Dompdf `isRemoteEnabled:false` ＋ `chroot` ＋ 文件名净化 ＋ 单次转义不变量 | ⚠️ 缺频控（§4.1） |
| `/sinofresh/v1/article-feedback` | POST | `__return_true` | 枚举白名单 ＋ 净化 | ⚠️ 缺频控（§4.1） |

---

## 5. 需裁决 / 未决

1. **SEO 头部缺口（P2，108 页）**：meta description 与 Open Graph 全站没有。补的话是「每页一段摘要 + 一套 og」，
   涉及 54 个对象 × 2 语言的文案 —— 是本报告里**工作量最大**的一项，需要您定口径与责任人。
2. **ZH 页 title 不出中文（P2，54 对）**：是 TranslatePress 词条未翻译，还是**有意保持英文标题**？两者处置完全不同。
3. **`<main>` 怎么加（P2，108 页）**：32 个模板逐个加 `tagName`，还是渲染层统一包一层？报告不给选择。
4. **安全响应头（P2）**：六项全缺。dev 可在 nginx 层加；**生产必须在 Cloudflare 或 nginx 加**，且 HSTS 要求先确认全量 HTTPS。
5. **两张证书 `coming soon`（P4）**：haccp / brc 无文件。上线前补素材，还是撤下这两行？
6. **`config-pdf` / `article-feedback` 频控（P3）**：建议复用 `/inquiry` 的 honeypot＋时间门。
7. **页脚 8 条剂型链接（P3）**：一行改动，是否顺手并入下一批？
8. **`x-default` 加不加（P3）**：加则需决定默认指向 EN 还是 ZH。
9. **sitemap 无法验证（上线依赖）**：`blog_public` 0→1 之后必须复验 `/wp-sitemap.xml` 覆盖
   （这是 `docs/dev-lockdown.md` 生产清单里最易漏的一条）。
10. **块模板脚手架里的 `jsam@zxpet.com`**：疑为笔误，是否改为 `sam@zxpet.com` 或占位符。

---

## 6. 证据与复现

| 产物 | 路径 |
|---|---|
| 权威清单（54 对象 + 类型表） | `docs/site-survey-2026-09-24/inventory.json` |
| 采集结果（108 URL） | `docs/site-survey-2026-09-24/crawl.json` |
| 原始字节（108 页 + 响应头） | `docs/site-survey-2026-09-24/cache/`（15MB，**不进仓库**，见下） |
| 八类findings | `docs/site-survey-2026-09-24/findings.json` |
| 未收录内链实测 | `docs/site-survey-2026-09-24/link-probe.json` |
| dev 安全探测 | `docs/site-survey-2026-09-24/security-probe.json` |
| 主题静态审计 | `docs/site-survey-2026-09-24/security-static.json` |

```bash
PY=/Users/meng/.workbuddy/binaries/python/versions/3.13.12/bin/python3
# 1 清单（只读 REST）        2 采集（只读 GET，1.3s/请求，约 6 分钟）
$PY tools/b3d_inventory.py   && $PY tools/b3d_crawl.py
# 3 八类分析（离线，读语料）  4 未收录内链实测（33 个目标）
$PY tools/b3d_survey.py      && $PY tools/b3d_link_probe.py
# 5 dev 安全探测              6 主题静态审计（离线）
$PY tools/b3d_sec_probe.py   && $PY tools/b3d_sec_static.py
```

> `b3d_crawl.py` **不要**加 `Accept-Encoding: br`（见 §0 自查 1）。全部脚本只做 GET/HEAD，不写站点。

**关于 `cache/` 不进仓库**：108 页原始字节共 15MB，已按 `.gitignore` 的
`**/site-survey-*/cache/` 排除。理由与代价都已核对过：
- **清单已在库内**：`crawl.json` 逐 URL 记下 `status` / `bytes` / `sha1` / 完整响应头 —— 语料是**可核对的**，
  不靠原始字节也能证明「当时取到的是哪些页、各多少字节、哈希多少」。
- **逐字节复现本就不可能**：这些页面含 Gravity Forms 逐渲染变化的 `gform_hidden` nonce，
  重爬得到的是同一集合、不同字节。
- **代价**：要重跑八类分析（`b3d_survey.py` 等离线脚本）需先重爬一次（约 6 分钟、1.3s/请求）。
  §1–§4 的所有结论都由**库内的 json** 承载，不依赖 `cache/`。

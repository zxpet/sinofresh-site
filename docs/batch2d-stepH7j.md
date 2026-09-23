# Batch H7j — 导航间距 ＋ 核心事实带进 gutter ＋ 当前菜单项标记（第一批 · 批 C）（2026-09-23）

**状态：实施 ＋ 门（全绿）＋ 浏览器 E2E（162/162）＋ 帧（16 张，全部 non-flat）完成；已 push，未 pull。**
用户约束「批 C 只 push 不 pull」⇒ dev live 仍 `2.10.69`，本批代码只以预检副本
(`sinofresh-theme-preflight`, `2.10.71`) 存在于 dev 机器上，靠 `X-SF-Preflight: 1` 访问。

**版本令牌：`style.css` 2.10.70 → 2.10.71（两处同步：头部 `Version:` ＋ functions.php enqueue）；
`assets/js/config.js` 不动（仍 1.2.0）、`formula-gallery.js` 不动（仍 2.2.0）。**

---

## 〇、本批最重要的事：门和 E2E 都「全绿」之后，测出了三个真缺陷

本批的第一次交付是**绿的**：门 75/0、E2E 155/155。**但那 155 条里有四条是闭着眼睛的。**
把「当前项有没有标记」从**类名**改成**颜料**（`getComputedStyle`）之后，六个标记里有**四个根本看不见**。

记录在这里，是因为它推翻的正是本项目最危险的一类假绿：

> **「`is-active` 类在」≠「访客看得见」。** 一条背后没有规则生效的链接，照样带着 `is-active`。

三个缺陷，全部**先在修复前的副本上跑同一条断言、看到它红**，再改代码：

| # | 缺陷 | 面 | 机制（从源码读出，再用浏览器量） |
|---|---|---|---|
| **D1** | `left-line` 画的是「3px 的空」 | **全宽度、两套构建** | 它的 active 规则写成短式 `.sf-header--nav-left-line .sf-nav__link.is-active` ＝ **(0,3,0)**；而给它预留位置的基座规则 `.sf-header--nav-left-line .wp-block-navigation__container > .wp-block-navigation-item > .sf-nav__link { border-left: 3px solid transparent }` ＝ **(0,4,0)**。基座更深 ⇒ 基座的 `transparent` 赢。实测 1440px：`border-left-width: 3px`、`border-left-color: rgba(0,0,0,0)`。**唯一能看见这条规则的状态是 `:hover`**（那条恰好是 (0,4,0) 且排在后面）。 |
| **D2** | 手机抽屉里四个标记不可见（**含出货默认 `underline`**） | ≤768px 抽屉打开时 | 抽屉自己的行规则 `.wp-block-navigation__responsive-container.is-menu-open .wp-block-navigation__container > .wp-block-navigation-item > .wp-block-navigation-item__content` ＝ **(0,5,0)**（并给每一行 `font-weight: 600`，把「字重」这条通道整条掐死）；≤781px 的模态颜色规则 `.wp-block-navigation .wp-block-navigation__responsive-container.has-modal-open .wp-block-navigation-item__content` ＝ **(0,4,0)**。63b 里每条标记规则只有 (0,3,0)/(0,4,0) ⇒ 在抽屉里 `underline` 画成 1px 的 0.14 白、`thick-line` 1px 而非 4px、`color` 白而非品牌绿。实测：当前行与未标记行**完全无法区分**。 |
| **D3** | `underline` / `thick-line` 顺手擦掉了抽屉自己的行分隔线 | ≤768px 抽屉打开时 | 这两个是**用底边框画**的标记，因此必然带一条 `:not(.is-active) { border-bottom-color: transparent }` 去藏掉它们预留的 2px/4px。那条规则也是 **(0,5,0)**——与抽屉的行规则同深度——**且排在后面**，于是靠顺序赢，把抽屉每一非当前行的分隔线重涂成透明。实测：`underline`/`thick-line` 下是 `rgba(0,0,0,0)`，其余四个是抽屉自己的 `rgba(255,255,255,0.14)`。 |

三条的修法都遵循同一条规矩——**写到你要压过的那条规则的深度上**：
- **D1 修在 63b**（冲突的两条规则都在 63b 里，修在别处是掩盖）：active 两条规则改用与基座同形的长选择器 ⇒ (0,5,0)。
- **D2 修在 63c**：三条重述规则 (0,7,0)。`bg`/`pill` **故意不重述**——它们用 `background-color` 画，抽屉规则不碰这一属性，实测仍然有效。
- **D3 修在 63c**：一条 `:where()` 规则写全六个标记类（`:where()` 贡献 0 权重，总数 (0,7,0)），把抽屉的 0.14 分隔线还回来。

**没有一条是靠放宽断言「修好」的**；三条各自在 E2E 里有具名断言，并且都先在旧副本上红过。

---

## 一、三项待办与实现

| 待办 | 落点 | 实现 |
|---|---|---|
| **10** 导航项间距 10 → 20px | `parts/header.html` | `"blockGap":"10px"` → `"blockGap":"20px"`。**只改这一个数字**：居中排列不动、`rowGap` 与 `columnGap` 同步（原生 `blockGap` 一个值管两轴）。 |
| **15** 核心事实带进 gutter | `style.css` §63a | `.sf-facts-mini` 加 `padding-left/right: max(38px, calc((100% - var(--wp--style--global--content-size, 1200px)) / 2))`，`≤1024px` 降到 20px。**带子的盒子保持通铺**——它画的是页面那两条发丝线，只有内容内移。`justify-content: space-between` 保留。 |
| **20** 服务端渲染当前项标记（6 种样式） | `functions.php` ＋ `style.css` §63b/§63c | 六种样式 `underline`(默认) / `bg` / `thick-line` / `color` / `left-line` / `pill`；后台 Site Settings → Appearance → Navigation 单选；选项名 `sf_nav_active_style`；前台 `<header class="sf-header sf-header--nav-underline">`；当前链接 `.sf-nav__link.is-active` ＋ `aria-current`。 |

### 63b/63c 的契约（写进代码注释，也写这里）
- **谁被标记**由 `functions.php` 决定，**从不**是 Products 下拉里那九个链接之一——它们落在浅色弹层上，而六种标记全是给深绿 Forest 导航条画的。
- **一个值多载体**：`aria-current` 分两种——链接**指向**当前页 ⇒ `page`；链接的**区块包含**当前页 ⇒ `true`。`/products/soft-chews/` 上被标的是拥有这个下拉的 `/products/`，而不是被裁掉的那个剂型子链接。
- **每个占位的标记在全部七个顶级链接上都预留空间**（否则访客在页面间移动时导航条会跳动）；**Active+Hover ＝ Active 的值**——hover 已经拿到了注意力，给一个 brief 没命名的状态再发明第七种颜色就是调色板漂移的开始。
- **`color` 用 #5AB735 写在深绿 #1B4D3E 上，对比度 3.79:1**，低于 15px 文字的 4.5:1 AA 底线，只过大字号的 3:1。brief 点了这个颜色，就按点名的发，**记录在案而不是悄悄调暗**。
- **`left-line` 的 active 规则必须写成与基座同形的长选择器**（见 D1）。这是本批唯一一条「形式即内容」的规则。

## 二、改动清单

| 提交 | 文件 | 改动 |
|---|---|---|
| **`6bfacac`** 本批主体 | `sinofresh-theme/parts/header.html` | `blockGap` 10 → 20px |
| | `sinofresh-theme/style.css` | +§63a（gutter 阶梯 120/38/20）、+§63b（六种标记 × 四态）；`Version:` 2.10.71 |
| | `sinofresh-theme/functions.php` | 六 slug 数组 ＋ 白名单回落、`sf_nav_request_path()`/`sf_nav_path_under()`/`sf_nav_path_is()`、`sf_nav_mark_link()`、两个 `render_block` 过滤器、`register_setting` 带 sanitiser、后台单选 UI；enqueue 2.10.71 |
| **`0e5b5e4`** 本批修复 | `sinofresh-theme/style.css` | §63b `left-line` active 两条改长选择器（D1）；+§63c 三条重述 ＋ 一条 `:where()` 分隔线归还（D2/D3）；63b/63c 注释写清三条缺陷的机制 |
| 证据 | `tools/b2d_h7_gate.py` | `BATCHES['h7j']` ≈ +620 行：声明式变换、21 条 coverage、31 条 invariants、10 个矩阵变体、17 条 NC-src / 4 条 NC-page / 12 条编号 NC；**其中 6 条 NC-src 与 5 条 source 声明是本次修复新增的** |
| | `tools/b2d_h7j_*.py` | E2E（174 条）、门外的绘制探针、行/断点探针、截图工具 |

## 三、门（`tools/b2d_h7_gate.py --batch h7j`）

| 段 | 结果 |
|---|---|
| A/A（同一安装两次抓取） | 75 页 / **0 差异** |
| 主证（insert 方向） | 75 页 / **0 差异** / 声明 **1500 条全部 applied 1500/1500** |
| coverage | **21/21** |
| invariants | **31/31**（含 h1 每页 1、令牌每页 1、间距规则每页 1、变体类每页 1、十六链接、七页 `page` / 六十页 `true`、菜单未覆盖的八页零标记） |
| 掩码回读 | PASS；46 处非文本货币值 |
| 破坏矩阵 | **10/10 caught**（含「令牌不折叠」75 页差异、「不标记任何链接」applied 300/1500、「下拉子链接保住标记」60 页差异、「owner 不知道子项命中」44 页差异、「全宣告 true」7 页差异、「少声明一条」applied 1500/1499） |
| 具名负对照 | **33/33**（17 NC-src ＋ 4 NC-page ＋ 12 编号；含本次新增的 6 条 NC-src） |
| 源码段（`--source`，**独立一次调用**） | **39/39** |
| 结果文件 | `_backup/b2d-h7j-gate.json`、`_backup/b2d-h7j-gate-source.json` |

**基线 / 候选**：`_backup/b2d-h7i-candidates`（`2.10.70` 态）↔ `_backup/b2d-h7j-candidates-fix`
（**修复后提交 `0e5b5e4` 的抓取**），A/A 副本 `_backup/b2d-h7j-candidates-fix-aa`。
修复前的抓取 `_backup/b2d-h7j-candidates` 保留，用于「先在旧副本上跑红」的取证。

### 回归（h7g / h7h / h7i）
主证三段（含 A/A 与掩码回读）**全部 PASS**。旧批的 `--source` 段**必然部分红**，且**与本次改动无关**：
它们各自的版本令牌声明是钉在自己那一版上的（h7g 12/15、h7h 14/17、h7i 23/25 ok），
红的三行/三行/两行**全部是 `Version:` 与 `?ver=` 令牌**——本批从未碰过版本头，改动前后同红。

## 四、E2E（`tools/b2d_h7j_e2e.py`，**162/162**）

跑在**预检副本**上（批 C 不 pull ⇒ live 无本批代码）。新增 `--only paint|drawer` 以便**只跑一段**
——这正是「先在旧副本上看到它红」的手段。修好之后完整跑一次：**162/162**（修前 155 条，本次 +7 条抽屉断言）。

**新增/改造的断言（本批的核心）**：
1. **`borderLeftColor` 进签名**（原来八列里没有它）。少了这一列，D1 永远看不见：宽度 3px 是「体面」的值，
   而颜色是空。**这一条改动本身就抓到了 D1。**
2. **不变量，而不是更多期望值**：`uncoloured()` —— 一条规则占了位置却不画东西就是缺陷的形状。
   底边 1px 是主题自留的 21c 发丝线（每条链接都有），**比 1px 宽的都是标记预留的，就得自己上色**；左边框只有 `left-line` 预留。
   *这条不变量在 bar 和抽屉两处共用。*
3. **抽屉里的标记按「颜料」断言**（`drawer_marks()`）：每个变体只问它自己那条通道到达声明值 **且与未标记行不同**；
   `none` 作对照断言「**完全无法区分**」——读空白页时 `none` 会过而其余全挂，读到别的元素时 `none` 会挂，**两个方向都盖住**。
4. **抽屉的分隔线归还**（D3 具名断言）。
5. **抽屉行距改成逐行量**：原断言拿 `itemH`（第 0 行）当所有行的代表，而第 0 行**恰好就是被标记那行**，
   修好 D2 后它高了 1px ⇒ 原断言在 ±1 容差上**擦边通过**。改成 `step[i] − hs[i]`（每行自己的高度），
   实测六段全是 **20.0**。这正是本项目那条规矩：**断言擦边通过 ⇒ 重构断言，不是放宽它。**

## 五、工具链踩坑（本批实测，写给下一批）

1. **`--source` 是独立一次调用，不能与主证合跑**。`main()` 里是 `if args.source: … else: <主证/矩阵/负对照>`，
   把 `--source` 和 `--base/--cand` 一起传**只会跑源码段**，门照样打印 `PASS`——一个安静的假绿。
   这就是为什么记录里有两个 JSON。本次先踩了一次（覆盖写了 `b2d-h7j-gate.log`），重跑才拿回主证。
2. **候选集换过之后要重新抓，并解释「为什么两次抓取逐字节都不同」**。CSS-only 的改动理论上不动 HTML，
   但 75 页**原始字节全部不同**。逐类归因（`re.findall` 比「把这一类擦掉再看还差不差」可靠——
   后者对任何一页都为真，只要**别处**还有差异，本次第一版归因脚本就栽在这里）：
   - Cloudflare 邮件混淆 `data-cfemail` / `/cdn-cgi/l/email-protection#…`：**75/75 页**（每页 3 处）；
   - Gravity Forms 每次渲染的隐藏字段 `gform_currency` ＋ `state_N`：**23/75 页**（有表单的那些）；
   - Gravity Forms 电话字段每次渲染的 DOM id `gform_phone_dropdown_<hex>`（被 `aria-controls` 引用 4 处）：**2/75 页**。
   **三类全部排除后：0 页差异。** 这三类都由掩码集覆盖，所以门是稳的——但**「门绿」不等于「字节一样」**，
   这句话要能拆开讲。
3. **zsh 会吃掉提交信息里的反引号**（`command not found: border-left:`）。提交信息长且含代码 ⇒ 写进文件用 `git commit -F`。
4. **BSD grep 又咬了一次**：`grep -n "63c\|63b\|63a"` 静默返回空（exit 0），差点误判「63c 不在文件里」。
   **交替一律 `-E`，或用内置 Grep 工具。**
5. **macOS 没有 `timeout`**（`command not found`）⇒ 用 `ssh -o ConnectTimeout=`，别包 `timeout`。

## 六、仍需用户处理

1. **本批未 pull**：dev live 仍 `2.10.69`。本批代码只在预检副本里；上线时机由用户的下一次 pull 授权决定。
   上线前 10 项移除见 `docs/dev-lockdown.md`（最易漏 `blog_public` 0→1）。
2. **`color` 标记的对比度**：品牌绿 #5AB735 在深绿导航条上 3.79:1，未达 15px 文字的 AA 4.5:1。
   brief 点了这个颜色 ⇒ 按点名发。**若要在无障碍上收紧，需要用户裁决**（调暗绿色 / 只在大字号用 / 接受）。
3. **抽屉里「字重」这条通道不可用**（行规则给所有行 600）。`underline`/`color` 两种标记在手机上因此只靠边线/颜色区分。
   这是可接受的，但**是设计事实，不是可以靠 CSS 修的东西**——要改就得改抽屉行规则。
4. GO 批遗留：post 158 五处测试值仍待后台自清（`_backup/b2d-b2d-go-post158/originals.json`）。
5. Shape Library(8) / Container Library(7) 仍待传图（H7g 遗留）。

## 七、帧（`docs/batchH7j-shots/`，16 张，全部 non-flat 已验）

`h7j-01-desktop-bar-gap-20px` / `02-tablet-bar-768` / `03..08-desktop-mark-{underline,bg,thick-line,color,left-line,pill}` /
`09-desktop-owner-marked` / `10-facts-gutter-1440` / `11-facts-gutter-375` / `12-facts-gutter-1200` /
**`13..16-phone-drawer-{underline,color,left-line,thick-line}`**（本批新增的三张，以及默认那张重拍）。

抽屉帧从 1 张变 4 张：单张「出货默认」曾经会**把一个标记根本看不见的抽屉记录下来**——
修复前当前行与未标记行逐像素相同。裁剪用**绝对页面矩形 × devicePixelRatio**（H7i 踩过的坑），
每张查 `distinct > 8`。

---

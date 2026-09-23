# Batch H7i — 价格阶梯 ＋ 样品行 ＋ Send Inquiry ＋ hero 静音（第一批 · 批 B）（2026-09-23）

**状态：实施 ＋ 门（全绿）＋ 浏览器 E2E（59/59）＋ 帧（12 张）完成；已 push，未 pull。**
用户约束「批 B 只 push 不 pull」⇒ dev live 仍 `2.10.69`（H7h 态），本批代码只以预检副本
(`sinofresh-theme-preflight`, `2.10.70`, `967d252`) 存在于 dev 机器上，靠 `X-SF-Preflight: 1` 访问。

**版本令牌：`style.css` 2.10.69 → 2.10.70（两处同步：头部 `Version:` ＋ functions.php enqueue）；
`assets/js/config.js` 1.2.0 → 1.3.0。**
⚠️ 用户规划表写的是「批 B：2.10.68 → 2.10.69」，但 `2.10.69` 已被 H7h 占用（H7g=2.10.68、H7h=2.10.69）
⇒ 本批取 **2.10.70**，并顺延：批 C = 2.10.71、批 D = 2.10.72。这处偏移需用户确认一次。

## 一、四项待办与实现

| 待办 | 落点 | 实现 |
|---|---|---|
| **2** 右栏底部按钮 → Send Inquiry | `templates/single-sf_formula.html` | 原来那行是 `<a class="sf-fdetail2__cta" href="/contact/">Request Sample</a>`（纯链接）。改为 `href="/contact/#quote"` ＋ `data-sf-inquiry-open` ＋ 文字 `Send Inquiry`：**同一个按钮，无 JS 时仍是 /contact/#quote，有 JS 时开询盘弹窗**。不新增样式——沿用 38a 自己的 CTA 规则。 |
| **3** 价格阶梯（Ali 式） | `functions.php` ＋ `style.css` ＋ `inc/formula-admin.php` | ①后台表从 `qty / price` 改为 **`min / max / price`**（`max` 可空＝顶层开口，提示语写明）；②新增文本字段 **`sf_formula_sample_price`**（提示语：e.g. 50，空则整行不输出）；③前台 `Quantity & Pricing` 组由 pills 变 **3 列卡片网格**：`价格 / 区间 / pieces` 三行＋底部圆形指示点；④卡片下追加**样品行**（📦 图标＋`Sample price US$50.00`＋`Get Sample` 药丸）。 |
| **11** 删重复回声 | `style.css` | H7g 已经把「值预览行」(`__meta`) 改成 `--js` 门控；本批把**提示语** (`__hint`，"Choose one") 走同一条路：`.sf-fdetail-config--js .sf-fdetail-config__hint { display:none }`。**无 JS 时提示语保留**——那时它是唯一说明旁边药丸可点的话。 |
| **12** `[Video]` 占位 | 数据（`sf_formula_video_url`） | 代码侧 H7a 早就写好（`[Photos][Video]` 切换＋facade 帧，有 id 才输出 Video 标签）。本批**只填 post 158 的 `sf_formula_video_url`**，验证「填空即出现、零改码零重部署」。 |
| **16** 删 Hero 两个 CTA | `templates/single-sf_formula.html` | 整行 `sf-formula-hero__actions`（Send Inquiry ＋ Build Custom Formula）删除，留 HTML 注释说明去处：询盘路径移到参数列末尾（访客刚读完规格的位置）与悬浮胶囊。 |

### 价格阶梯的取舍（写进代码注释，也写这里）
- **仍是真 radio**：每张卡一个 `<input type="radio" name="sf-config-pricing">`，沿用同一个
  `data-sf-config-opt` 钩子、同一个 config.js 写的 `is-on` 类 ⇒ 摘要行、弹窗载体、无 JS 那行**都不需要知道这个 style 存在**。
- **卡片的文字 span 被跳过**（价格就是标签），config.js 回落到 input 的 value（＝区间字符串）。
- **样品费不是一条阶梯**：它是独立 meta。把 sample 塞进价格表里会把「一个样品的单价」当成品单价报价。
- **CSS 写在文件末尾**（第 63 节），理由同 38a-iii：覆盖 pill 基座（display / border-radius / padding）的规则
  必须排在它之后，否则在任何宽度都是死代码——H7b 踩过这个坑。

## 二、改动清单（`967d252`，6 文件）

| 文件 | 改动 |
|---|---|
| `sinofresh-theme/style.css` | +136：第 63 节——`.sf-fdetail-config__tiers` 3 列 grid、`.sf-tier` 卡片、价格/区间/单位三级字号、`.sf-tier__dot`（绝对定位，`:checked ~ .sf-tier__dot` 用 `~` 不是 `+`——点是 label 第 4 个子元素）、样品行、`--js` 下隐藏 hint、`@media (max-width:480px)` 三列收紧＋价格 16px＋样品行 `flex-wrap`。版本 → 2.10.70 |
| `sinofresh-theme/functions.php` | +230/-? ：`sinofresh_formula_config_groups()` 产出 `style=tiers` 组（`unit=pieces`、`sample_price`）；`sinofresh_formula_config()` 新增 tiers 分支（卡片＋样品行）；版本令牌两处同步；`[Video]` 相关注释补记（H7a 既有逻辑） |
| `sinofresh-theme/inc/formula-admin.php` | 后台表 `qty` → `min`/`max`/`price` ＋ hint；新增 `sf_formula_sample_price` 文本字段 ＋ hint；`sf_formula_missing_required()` 的「完整行」判据改为 **min＋price**（max 可选；**legacy `qty` 仍当 min** ⇒ 老数据不失效） |
| `sinofresh-theme/templates/single-sf_formula.html` | 删 hero 行动行；`Request Sample` 链接 → `Send Inquiry` ＋ `data-sf-inquiry-open` ＋ `/contact/#quote` |
| `sinofresh-theme/assets/js/config.js` | 1.2.0 → 1.3.0：新增第 4 件事——`[data-sf-inquiry-sample]` 的点击把一句话写进**空的** Message 框（`I would like to request a sample of {标题} ({价} per sample).`）；非空不写、提交后不写 |
| `tools/b2d_h7i_render_harness.php` | +269：本批的渲染冒烟桩 |

**DIFF 面**：`hero` 与右栏 CTA 两条改动**落在全部 42 张详情页**（21 条记录 × EN/`/zh/`）；
阶梯 / 样品行 / Video 帧 / JSON-LD offers / 弹窗价格行**只落在 post 158 的两页**（DB 事实：21 条记录里只有
post 158 同时带 `sf_formula_price_tiers`、`sf_formula_sample_price`、`sf_formula_video_url`，用 wp-cli 逐条点过）。

## 三、数据改动（**仅 dev 库，post 158 三处 meta**）

回滚记录：`_backup/b2d-h7i-post158/before.json`（含 before / after 两块 ＋ 回滚命令）。

| key | before（用户原值） | after（本批写入，**演示值**） |
|---|---|---|
| `sf_formula_video_url` | `""` | `https://www.youtube.com/watch?v=jNQXAC9IVRw` |
| `sf_formula_price_tiers` | `[{"qty":"200","price":"2.5"}]` | `[{"min":"10","max":"99","price":"3.88"},{"min":"100","max":"999","price":"3.58"},{"min":"1000","max":"","price":"3.28"}]` |
| `sf_formula_sample_price` | `""` | `50` |

- 写入用 `/tmp/sf-h7i-meta.php`（**两向比对**：写后回读并 `MATCH`/`MISMATCH` 断言）。
- 为什么要写：阶梯 / 样品行 / Video 帧都要**数据**才渲染得出来；不写就无从过门、无从 E2E。
- **这三个值是演示值**，等销售部填真数据（见「仍需用户处理」）。
- legacy 兼容：若把 `price_tiers` 回滚成 `[{"qty":"200","price":"2.5"}]`，渲染器把 `qty` 当 min ⇒ 仍渲染成
  一张「200」的卡 ＋ `US$2.50`，**不会白屏**。

## 四、门（`tools/b2d_h7_gate.py --batch h7i`）

| 段 | 结果 |
|---|---|
| A/A（同一安装两次抓取） | 75 页 / **0 差异** |
| 主证（insert 方向） | 75 页 / **0 差异** / 声明 92 条 **全部 applied 92/92** |
| coverage（36 条） | 全 ok（含 7 条 `absent`：`?ver=2.10.69`、`config.js?ver=1.2.0`、`sf-formula-hero__actions`、`sf-formula__cta--solid`、`sf-formula-hero__build`、旧 `Request Sample` 链接…） |
| invariants（23 条） | 全 ok（含 json-ld deep equal；本批用**具名例外**，见下） |
| 掩码回读 | 23 页 / **0 差异**；46 处非文本货币值 |
| 破坏矩阵（9 个变体） | **9/9 caught**（例：hero 不删 ⇒ 42 页差异＋applied 50/92；阶梯不补 ⇒ 2 页差异＋applied 90/92；令牌不折叠 ⇒ 75 页差异；运行数少声明一条 ⇒ applied 92/91） |
| 具名负对照（24 条） | 全 ok（含 3 条新 `NC-jsonld`、7 条 `NC-src`、2 条 `NC-page`、`NC13/14/15/16`） |
| 源码段（`--source`） | **25/25** |
| 结果文件 | `_backup/b2d-h7i-gate.json` |

基线 / 候选：`_backup/b2d-h7i-baselines`（`5db481d` 态，**写数据之前**）↔ `_backup/b2d-h7i-candidates`（`967d252`）；
A/A 副本 `_backup/b2d-h7i-candidates-aa`。被污染的旧三份已改名 `-contaminated` 保留。

## 五、E2E（`tools/b2d_h7i_e2e.py`，**59/59**）

跑在**预检副本**上（批 B 不 pull ⇒ live 无本批代码），会话配方见下。覆盖面：
EN 详情页 1440、它的 `/zh/` 孪生页、一张**无阶梯无视频**的记录（`/formulas/liquid-joint-support/`）、
375×812 与 360×780 两档手机。

主要的 59 条断言（节选）：
- **每一页先证明「是谁服务了这一页」**：主题链接含 `-preflight` 且 `ver=2.10.70`，`config.js?ver=1.3.0`，
  `formula-gallery.js?ver=2.2.0`，`h1 == 1`。（401 页 `pathname == "/"`、0 个样式表、标题空——所有查询静默返 0，
  形状极像「新标记没渲染」，所以这条守卫每页都跑。）
- hero：`.sf-formula-hero__actions` / `__build` / `__solid` 全 0，**而身份仍在**（breadcrumb ＋ `__title` ＋ `__meta`）
  ——「静音」不是「坏掉」。
- 阶梯：`display:grid` 且 3 条 track、3 张卡各 `display:grid`；三张卡 top/bottom 一致（一行）；卡内
  `input → 价格 → 区间 → 单位 → 点` 的 **DOM 顺序与几何顺序都成立**；三组 `US$3.88/10-99/pieces`、
  `US$3.58/100-999/pieces`、`US$3.28/≥1,000/pieces`；3 个同名 radio、值互异、初始未选。
- 点中间那张：只有它 checked、只有它 `is-on`、**只有它的点变成品牌绿 `rgb(90,183,53)`＋内嵌白环**
  （断言**颜料**而非类名——类名对「没有规则的点」也成立）；摘要行读作 `Quantity & Pricing: 100-999`。
- 样品行：在卡之后、图标＋`Sample price`＋`US$50.00`＋`Get Sample`（`/contact/#quote`、`data-sf-inquiry-open`、
  `data-sf-inquiry-sample="US$50.00"`）；点它 → 弹窗开、**不发生跳转**、Message 预填
  `I would like to request a sample of Joint Support Soft Chews (US$50.00 per sample).`；
  **再点一次不重复写**、**访客自己写的字不被覆盖**（双向）。
- 右栏：恰好 1 个 `.sf-fdetail2__cta`，文字 `Send Inquiry`，**页面上再无任何 `<a>` 读作 `Request Sample`**
  （`Request Sample` 全页仅剩 1 处，在 HTML 注释里——已断言「只出现在注释中」）。
- Video：`[Photos][Video]` 两个标签、帧 `data-video-id="jNQXAC9IVRw"`、预藏、poster ＝
  `i.ytimg.com/vi/jNQXAC9IVRw/hqdefault.jpg`、占 5 帧里的第 2 位；**无该 meta 的记录仍是孤零零一个 `Photos`**。
- `/zh/` 孪生页：阶梯三组值完全一致、右栏按钮 `href="/zh/contact/#quote"`、无 `Request Sample` 锚点、Video 帧在。
- 手机：默认折叠（`View all specs ▾`，`--js` 下列表内联）、展开后阶梯**仍是 3 列一行**（95.66px × 3）、
  价格降到 16px、卡内四件仍按序堆叠、折叠态与展开态**都不横向溢出**（`scrollWidth == innerWidth`）。

### 两处「断言错、产品对」的修正（重要，写给下一批）
1. **弹窗的 `is-open`**：`inquiry.js` 先 `modal.hidden = false`，再在 `requestAnimationFrame` 里加 `is-open`
   （注释写明：过渡需要一个起始值）。原断言在同一次点击的同一 tick 里读 `is-open` ⇒ 把「已经打开」判成「没打开」。
   **修法是重构断言**：点击后同步读一次（`isOpen:false`），一个往返后再读一次（`isOpen:true`）——
   这反而把「两段式显示」变成了真断言。**没有改产品。**
2. **样品行在 375 不换行**：CSS 写的是 `flex-wrap: wrap` ＋ 手机下 `margin-left:0`。实测跨 1440/414/390/
   375/360/320：四件内容需 **≈293.7px**，所以 **375–414 装得下、单行**；**360 与以下**才换行，且落到行的左缘
   （`l=38` ＝ 行的左缘，`margin-left:0` 生效）。原断言「375 应换行」是**断言错了**，产品对。
   **修法**：375 断言「装得下单行 ＋ 不溢出 ＋ wrap 规则在位」，360 断言「换行发生 ＋ 落到左缘 ＋ 仍不溢出」
   ——把一个错断言换成**双向的真断言**（否则 `flex-wrap:wrap` 就是一条没人见它响过的规则）。

## 六、门工具本次新增的三件事（`tools/b2d_h7_gate.py`，+660 行）

1. **`jsonld_delta`：具名三子句例外**。本批把 JSON-LD 的 `offers` 从 1 档改成 3 档，深等值必然红。
   与其放宽整条深等值，新增一个**只能点名**的例外（`jsonld_with_exception()` ＋ `_offers_out()`）：
   - (a) **除该键外**的每个字段必须在**全部** 75 页上仍深等值；
   - (b) 被点名的那几条页上，该键必须匹配声明的 `@type`/`priceCurrency`/`lowPrice`/`highPrice`/`offerCount`，
     且**两侧出现次数相同**（`len(fb) == len(fc)`，而不是 `fb == fc`——后者自相矛盾）；
   - (c) 逐档 `(price, minQuantity, maxQuantity)` 相等；且点名页集必须**恰好命中**。
   路由点：`invariants()` 里按声明分流；未声明 `jsonld_delta` 的批次仍走原来的 `jsonld_equal`（H7g / H7h 已回归通过）。
2. **`nc_jsonld` 负对照环**：三个变体（声明数字移动 / 被点名记录丢键 / 用
   `@type":"Product","name":"Calming Soft Chews"` 把 offer 块种到**非点名页**），要求逐个被 `invariants()` 判红。
3. **新源码目标**：`adm`（`inc/formula-admin.php`）与 `tpl`（`templates/single-sf_formula.html`）＋ `tpl_live`。

## 七、工具链踩坑（本批实测，写给下一批）

1. **预检访问的会话配方（修正旧笔记）**：`close --all → open <url>（落 401）→ set headers {X-SF-Preflight,
   Authorization: Basic …} → reload`。**只有设头之前那一次导航需要 `reload`**；之后的 `open` **保留**自定义头
   （实测：preflight → zh 页 → 仍 preflight）。`set credentials` 与 `set headers` 互斥，所以凭据**并进同一次
   `set headers`**，不要再调 `set credentials`。
2. **元素裁剪截图只要页面滚动过就是纯白**（本次 4 张 729/711/341 字节，`distinct=1`）：工具按**页面坐标**裁剪、
   按**视口坐标**截图，两者一错位就裁到内容旁边。`scrollIntoView` **不管用**。
   **解法**：`screenshot --full` ＋ 用元素的**绝对页面矩形**（`rect.top + scrollY`）× `devicePixelRatio` 做 PIL 裁剪。
   并且**每张都要查 non-flat**（`distinct > 8`）——「尺寸对 ≠ 内容对」。
   （隔离环境已装 Pillow：`/Users/meng/.workbuddy/binaries/python/envs/default/bin/python`。）
3. **BSD grep 再次咬人**：`grep -rln "a\|b"` 与 `grep -n "a\|b"` 在 macOS 上**静默返回空**（exit 0），
   本次把「折叠逻辑不在 config.js 里」误判了一次。**交替必须 `-E`。**

## 八、仍需用户处理

1. **post 158 三处 meta 是演示值**（见第三节），等销售部填真数据：
   - `Tier pricing` 现为 10-99 / 100-999 / 1,000+ 三档假价；后台表已是 **Min / Max / Price**，顶层 **Max 留空**。
   - `Sample price (USD)` 现为 `50`（渲染成 `US$50.00`）；**留空则整行样品行不输出**。
   - `sf_formula_video_url` 现为一个占位 YouTube 链接（`jNQXAC9IVRw`）；换真视频只改这个字段，**不用改码**。
   - 回滚：`_backup/b2d-h7i-post158/before.json`。
2. **GO 批遗留：post 158 五处测试值仍待用户后台自清**（原值见 `_backup/b2d-b2d-go-post158/originals.json`）。
3. **Shape Library(8) / Container Library(7) 仍待传图**（H7g 遗留）。
4. **本批未 pull**：dev live 仍 `2.10.69`。本批代码只在预检副本里；上线时机由用户的下一次 pull 授权决定。
   上线前 10 项移除见 `docs/dev-lockdown.md`（最易漏 `blog_public` 0→1）。
5. **版本号偏移需确认**：批 B 实发 **2.10.70**（规划表写 2.10.69，已被 H7h 占用）⇒ 批 C 2.10.71、批 D 2.10.72。

## 九、帧（`docs/batchH7i-shots/`，12 张，全部 non-flat 已验）

`h7i-01-desktop-hero-quiet` / `02-desktop-right-column` / `03-desktop-ladder` / `04-desktop-media-video-tab` /
`05-desktop-sample-dialog` / `06-phone-folded` / `07-phone-ladder-3col` / `08-phone-sample-wrapped` /
`09-zh-ladder` / `10-desktop-sample-row` / `11-desktop-send-inquiry` / `12-desktop-dialog-prefill`

---

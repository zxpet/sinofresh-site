# Batch 2D · Step 2 — 图集区（主图 + 缩略图切换）实施方案（待确认，**主题零改动**）

> 拍板：A＝**S1**（4 槽位）／B＝**h2**（附 375px 点轨条件）／C＝**shortcode**。
> 本文件只是方案。**此刻 `sinofresh-theme/` 一个字节未动**（扫描是只读的，`git status` 只多 `docs/`）。
> 全部 dev 访问带 `-u 'sfdev:VkEws18Kl5V1qp3TpZ6s'`。
> 扫描档：`docs/batch2d-step2-scan.md`（543 行）；本档是它的执行版。

---

## 0. 五个必须你过目的发现（3 个改你的指令、2 个更正我上轮的数字）

### 发现 1（改条件 B）：**375px 上根本没有点轨，条件 B 无法执行**

`.sf-toc` 是**桌面专用**：

```
style.css:7322-7326
@media (max-width: 1100px) {
	.sf-toc { display: none; }
}
```

- ≤1100px 整条点轨 `display:none`。375px 下它既不渲染也不可测，"8 项点轨溢出"这个动作**不存在**。
- 点轨是**竖列**（`7225: .sf-toc ul { flex-direction: column; gap: 16px }`，点 8px）。第 8 颗只让列高从 7×8+6×16=**152px** 变 8×8+7×16=**176px**（+24px），`top:50%; translateY(-50%)` 永远居中 ⇒ **竖向不可能溢出**。
- 标签卡（`.sf-toc__label`）是 `position:absolute` + `right:100%` + `white-space:nowrap` + `max-width:260px` + `opacity:0` 且 **`pointer-events:none`** ⇒ **不参与布局**，横向也不可能把点轨撑开。≥1101px 下 `right:20px`，向左最多 272px，视口宽 ≥1101px ⇒ 不越界。
- 新标题 `Inside Our Soft Chews Production`（32 字符）在 13px 下约 205px < 260px ⇒ 标签卡**不触发省略号**。

⇒ **结论：h2 安全，条件 B 的前提不成立，我建议按 h2 实施**。替代的、**真能测**的等价门写在 §七 第 9 项（375/768px 横向文档溢出=0、缩略图条 scroll-snap、无 JS 时有主图；≥1101px 用 1440 与 1280×700 实测**点轨 7→8**、8 个落点、点轨盒子在视口内、与浮动堆叠不重叠）。
若你坚持"375px 必须看到 8 颗点"，那等于要求**改 `display:none` 那个断点**——那是另一个批次，不该塞进图集。

### 发现 2（改"含 !important"）：**`.sf-fac` 的 `!important` 不能盲抄，本项目也不需要**

`style.css:4637-4642` 的注释自己写了根因：

> core's gallery sheet sizes the tiles itself — `.wp-block-gallery.has-nested-images.columns-3 figure.wp-block-image:not(#individual-image)` resolves to `width: calc(33.33% - 16px)`, so the tiles would float in tracks they never fill. The width here has to carry !important to win over that rule.

即：`.sf-fac` 是 **core `wp:gallery` 块**，core 的样式表用一条高特异性规则把瓦片宽写成 `calc(33.33% - 16px)`。

我们的 shortcode 产出**普通 `<figure>`**：没有 `.wp-block-gallery` 包装、没有 `wp-block-image` 类 ⇒ **那条 core 规则命不中**。实测旁证：全站 `style.css` 里**没有任何 img 类规则带 `!important`**（grep `img[^{]*{[^}]*!important` → 0 命中）；唯一可能干扰的 `.wp-block-image img { box-shadow:none }`（`style.css:1208`）同样命不中。

⇒ **不写 `!important`**，用 `.sf-gallery .sf-gallery__stage img`（specificity 0,3,1）稳压。核验若发现被压，**只在该条上补最小 `!important`** 并记录。这是对你"含 !important"的一条**有依据的偏离**，回一句即可驳回。

### 发现 3（改 S1 第 4 槽位）：**`liquids`/`dental-chews` 没有 300 变体；且第 1/第 4 张其实是同一画面**

服务端实测（`getimagesize`，非文档）：

| slug | full | -300x300 | -150x150 |
|---|---|---|---|
| soft-chews | 62 570 B | 15 940 B | 4 660 B |
| tablets | 33 902 B | 8 698 B | 2 826 B |
| powders | 95 306 B | 21 472 B | 6 026 B |
| pastes | 9 974 B | 3 030 B | 1 240 B |
| drops | 18 610 B | 4 522 B | 1 670 B |
| liquids | 13 422 B | **MISSING** | **MISSING** |
| fish-oil | 36 820 B | 10 740 B | 4 064 B |
| dental-chews | 42 998 B | **MISSING** | **MISSING** |

两个问题：

1. **2/8 页缺变体** ⇒ 槽位 4 在 liquids / dental-chews 上必须退回 `<slug>.webp`，即**同一个文件**出现两次。
2. 我上轮把 S1 写成"4 张互不相同"，**这个说法不准确，我更正**：`<slug>.webp` 与 `<slug>-300x300.webp` 是**同一张画面的两种像素尺寸**，不是两张不同的图。缩略图条里第 1 与第 4 会**看起来一模一样**——正是我用否决 S3 的那条理由（"4 张一样像坏图"），S1 只是把它从 4/4 降到 2/4。

⇒ 请你回 **S1a** 或 **S1b**：

| | 第 4 槽位 | 8 页一致性 | 代价 |
|---|---|---|---|
| **S1a（照你原话）** | `{slug}-300x300`，缺变体则退回 `{slug}` | 4 槽，几何一致 | 第 1/第 4 张同画面（6 页同图不同像素、**2 页同一文件**）；替换清单 = 3 个对象 |
| **S1b（我推荐）** | `fac-line.webp`（800×600，产线：托盘上的圆形片剂/咀嚼粒 + 三名操作员） | 4 槽，几何一致 | 替换清单 = 3 个对象（数量与 S1a **完全相同**）；4 张**真不同**、无缺分支 |

我推荐 **S1b** 的三条理由：① 替换清单数量不变（`fac-placeholder` + `fac-packaging` + `fac-line`，与 S1a 的 3 个相等）；② 消掉"两张缩略图一模一样"与"2 页缺变体分支"；③ `fac-line` 画面里有**成托盘的产品**，是四张里产品语义最强、最适合放在产品页的车间图（构图与 `fac-packaging` 明显不同场景，已逐张目视确认）。

> 若选 S1a，第 4 张的 alt 只能是第 1 张的复述（同一画面）——**这本身就是该方案的一个症状**。

### 发现 4（工具链，实测）：**版本号会让掩码门全站 DIFF；而现成的归一化工具会顺手删掉 `data-form`**

实测（直接 import `sf_masked_cmp.py` 的 `masked()`）：

| 输入差异 | 现有掩码下的结果 |
|---|---|
| `style.css?ver=2.10.44` → `2.10.45` | **DIFF（未掩）** |
| 在两个 `<script>` 之间**新增一个 `<script src=…>`** | **DIFF（正确，掩码没吞真改动）** |

所以"掩码回归预期 9 DIFF"若不处理 ver，就会变成 **47 DIFF**，等于没有信号。项目既有对策是 `tools/b2c_s2_ver_inventory.py`（其 docstring 明确反对 blanket 掩 `?ver=`，因为那会同时藏掉"某个资源被误改版本"）。

但**不能直接复用** `b2c_s2_norm_attrs.py`：它的 `FIXED`（line 39-44）除 ver 令牌外还**删掉 `data-form` / `data-sf-form`**——那是 2C 的声明改动，对本批是**纯多余的盲区**（K1 按钮正是靠 `data-form` 工作）。

⇒ 本批写 `tools/b2d_s2_norm.py`：**只归一化 `?ver=<token>`**（A/B 两侧渲染自**同一个** preflight 目录名，连目录折叠都不需要），**不删任何属性**。两把工具合起来的语义是严密的：

- `norm` + 掩码门 ⇒ "**除 ver 令牌外，没有别的字节动过**"（资源改名/新增/删除都会改 URL 字符串 ⇒ 照样 DIFF）
- `ver_inventory` ⇒ "**动的就是这两个 token，且只在这 9 页**"

并且**不去改已认证的 `sf_masked_cmp.py`**（第 1 批已经为它修过两次：`gf_phone_id` 掩码、`--user` 凭据）。

### 发现 5（更正数字）：`:has(` 全站实测 **170**，不是 172；`sf-gallery` 类名空置

| 文件 | `:has(` |
|---|---|
| `style.css` | **163** |
| `assets/css/configurator.css` | **7** |
| **合计** | **170** |

⇒ 不变量改为：**本批新增 0 处，批后仍是 163 / 7 / 170**（若你手上的 172 来自更早的统计，以这次实测为准）。另实测 `sf-gallery` / `sf-gallery__` 全仓（php/css/js/html）**0 命中**，可安全占用。

---

## 一、图集区结构

### 1.1 插入点（8 页字节级同源）

`templates/page-{slug}.html`，**hero 组结束与 `#formulas` 组开始之间**。锚点：

```
</section>
<!-- /wp:group -->

<!-- wp:group {"tagName":"section","anchor":"formulas"
```

| slug | 命中次数 | 锚点 sha256[:16] |
|---|---|---|
| 全部 8 页 | **各 1 次** | `8aa9e570f058aa72` |

（`anchor":"formulas"` 亦为**每页 1 次**，可作独立断言。）

### 1.2 插入块（每页只有 `form="…"` 不同）

```
<!-- B2D-S2: gallery -->
<!-- wp:group {"tagName":"section","anchor":"gallery","className":"sf-gallery","backgroundColor":"bg-light","layout":{"type":"constrained"},"style":{"spacing":{"padding":{"top":"var:preset|spacing|80","bottom":"var:preset|spacing|80"}}}} -->
<section id="gallery" class="wp-block-group sf-gallery has-bg-light-background-color has-background" style="padding-top:var(--wp--preset--spacing--80);padding-bottom:var(--wp--preset--spacing--80)">
<!-- wp:html -->
[sf_formula_gallery form="soft-chews"]
<!-- /wp:html -->
</section>
<!-- /wp:group -->
```

- 容器序列化**逐字取自 Block 9 / Block 11** 的 bg-light 组（`templates/page-*.html`），只**增** `anchor`/`className` 两个键、**不动**其余键与顺序。
- `bg-light` = **`#F3F6F4`**（`theme.json` palette，已实测）。`.sf-fac` 的注释把同一 token 描述为"the same token Core Values uses"，即站内既有灰带语言。
- 现有区块底色序列实测：`sf-hero-inner`(#2E6B54，深绿) → `sf-formulas`(白) → 配置器(白) → `sf-spectable`(白) → `sf-actives`(白) → **How We Work(#F3F6F4)** → FAQ(白) → Related(#F3F6F4) → CTA(绿)。
  插入后：**深绿 → 灰(#F3F6F4) → 白 ×4 → 灰 → 白 → 灰 → 绿**。图集若用白，会与后面四连白连成一片 5 块白 —— 这是选灰带的原因。
- 自闭合块一律 ` /-->`（本块内无自闭合块，模板里既有区块不动）。
- **h2 与全部图集内容都在 shortcode 输出里**，与第 1 批 `#actives` 同构（section 在模板、内容在 shortcode）。因此若 shortcode 返回空串，会留一条空灰带 —— 与 `#actives` 的既有行为一致，属已知取舍。

### 1.3 H2 文案（**要你选**）

主选 **A**：`Inside Our Soft Chews Production`（由 `sprintf('Inside Our %s Production', $label)` 生成，`$label` 走既有 `sinofresh_formula_label($form)`）
- 与 About 页既有的 **"Inside Our Factory"** 同声；含剂型关键词（SEO/AI 抓取）；32 字符、点轨标签卡不触省略号。

备选 B：`Soft Chews Product Gallery`（更偏"产品"，换实拍后标题不用改）
备选 C：`A Closer Look at Our Soft Chews`（最营销化）

> 取舍：A 的措辞与"车间图占 3/4"的占位现状最贴，但换实拍后若 4 张全是产品图，A 会略微失准；B 对两种内容都成立。**我仍推荐 A**（站内声音一致性优先，且换图时一并改标题是可选动作）。

### 1.4 导语段：**建议不加**

第 1 批 `#actives` 有导语（因为要解释"保证值"是什么意思）；图集不需要解释，标签 + alt 已承担语义，且**多一句就多一条 TP 待译串**。若你要，我给一句中性文案（`A look at our … production and packaging lines in Linyi, China.`），默认**不加**。

### 1.5 四槽位与容器

```
1. 本页剂型图（{slug}.webp, 720×720, 1:1）      ← 主图（首屏服务端渲染，唯一默认可见）
2. fac-placeholder.webp（1100×733, 3:2）        ← 缩略图
3. fac-packaging.webp（800×600, 4:3）           ← 缩略图
4. S1b: fac-line.webp（800×600, 4:3）           ← 缩略图      （或 S1a: {slug}-300x300，见 §0 发现 3）
```

比例覆盖 **1:1 / 3:2 / 4:3**（三种）；切图时舞台盒子**尺寸不变**（见 §三），不会跳。

---

## 二、图片清单与 alt

| 槽 | 文件 | 真实像素 | 体积 | 比例 | 水印 | loading | alt（`{L}` = 剂型标签，如 `Soft Chews`） |
|---|---|---|---|---|---|---|---|
| 1 | `{slug}.webp` | 720×720 | 9 974–95 306 B | 1:1 | 有 | **eager** + `decoding="async"` | `SINO FRESH {L} private label pet supplement product` |
| 2 | `fac-placeholder.webp` | 1100×733 | 121 516 B | 3:2 | 有（**完整在画面内**） | lazy | `{L} production line at the SINO FRESH GMP facility in Linyi, China` |
| 3 | `fac-packaging.webp` | 800×600 | 72 956 B | 4:3 | 有（**被画框切断**） | lazy | `{L} packaging line at the SINO FRESH GMP facility in Linyi, China` |
| 4b | `fac-line.webp` | 800×600 | 76 510 B | 4:3 | 有（右下被切） | lazy | `{L} moving along the tray line inside the SINO FRESH GMP facility` |

**硬约束与手法**

1. **alt 每张都含剂型关键词**（`{L}` 由 shortcode 从 `sinofresh_formula_label()` 取，8 页各自正确；`fish-oil`→`Fish Oil`，`dental-chews`→`Dental Chews`）。槽 1 的句式**沿用站内既有惯例**（`functions.php:877` 的 fcard alt 与模板里 7 个 tile 的 alt 都是 `SINO FRESH {L} private label pet supplement product`）。
2. **首图 eager、其余 lazy**；**不加 `fetchpriority="high"`**——图集在 hero **之后**，本页 LCP 是 hero 的 h1 文本而非任何图片，抢优先级反而有害。`loading="lazy"` 叠 `hidden` 的额外收益：非活动帧浏览器不会提前下载，点击时才取。
3. **`width`/`height` 用真实值**（720×720 / 1100×733 / 800×600），**不照抄陈旧属性**。已知真值来源是服务端 `getimagesize`，不是模板里那批 `width="800" height="600"`（那是 720×720 文件上的陈旧属性，模板里 7 处都错）。shortcode 内维护一张尺寸表，并**用脚本对服务端真值做一次全量断言**（§七 第 7 项），杜绝漂移。
4. **图集里不放 `figcaption`**：与 `.sf-fac` 的既有决定一致（"six identical frames with identical alt text added nothing a visitor could read"），语义由 alt + 缩略图的 `aria-label` 承担。
5. 缩略图由 JS 从舞台帧**派生**，其 `<img>` 用 `alt=""`（装饰性：按钮自身已有 `aria-label`），并复制同一组 `width`/`height`。

---

## 三、原生切换方案（零依赖）

### 3.1 DOM 契约（服务端渲染部分）

```html
<div class="sf-gallery__inner">
  <h2 class="sf-gallery__title">Inside Our Soft Chews Production</h2>

  <div class="sf-gallery__stage" role="tabpanel" id="sf-gallery-panel-{slug}">
    <figure class="sf-gallery__slide" id="sf-gallery-slide-{slug}-1"
            data-slot="1" data-label="Soft Chews">
      <img src="…/soft-chews.webp" alt="…" width="720" height="720"
           loading="eager" decoding="async">
    </figure>
    <figure class="sf-gallery__slide" id="sf-gallery-slide-{slug}-2"
            data-slot="2" data-label="Production" hidden>
      <img src="…/fac-placeholder.webp" alt="…" width="1100" height="733"
           loading="lazy" decoding="async">
    </figure>
    <!-- 槽 3、槽 4 同构，均 hidden -->
  </div>
  <!-- .sf-gallery__thumbs 由 JS 建；无 JS 时不存在 -->
</div>
```

- **主图服务端渲染** ⇒ 无 JS 也有图（只有槽 1 可见；槽 2-4 `hidden`，不下载）。
- 槽 2-4 的 `hidden` 属性是**无 JS 的降级开关**，不是 JS 的状态变量（见 3.3）。
- **单一数据源 = 舞台的 4 个 `<figure>`**：缩略图、aria 名称、切换目标全部从它们派生。未来换图只改 shortcode 一处。

### 3.2 JS 契约（`assets/js/formula-gallery.js`，新文件，ver `1.0.0`）

```
1) 根：document.querySelectorAll('.sf-gallery')，逐个处理；根内没有 .sf-gallery__stage 就跳过（shortcode 空串时的护栏）。
2) 采集：stage 下所有 figure.sf-gallery__slide（文档序）。
3) 建 thumbs：为每帧建一个真 <button type="button" role="tab">，内含 <img src=帧的 src alt="" width height loading="lazy" decoding="async">；
   容器 <div class="sf-gallery__thumbs" role="tablist" aria-label="Product photos">。
   按钮：id=sf-gallery-tab-{slug}-{i}、aria-controls=帧的 id、aria-label=帧的 data-label、aria-selected、tabindex（选中=0，其余=-1 → roving）。
4) 切图（select(i)）：只切 3 样东西 ——
   a. 帧的 class：活动帧去 sf-gallery__slide--off、非活动帧加；
   b. 按钮：aria-selected 与 tabindex；
   c. 舞台的 aria-label = 活动帧的 alt。
   **不移动、不重建、不克隆任何 DOM**；首帧的 hidden 在 init 时统一摘掉（此后由 class 控制显隐，才能淡入）。
5) 事件：**委托**一次，绑在根上（click → 命中 .sf-gallery__thumbs button 才处理）；keydown 在 tablist 上处理 ArrowLeft/ArrowRight/Home/End（移动焦点 + 选中）。
6) 淡入：`@media (prefers-reduced-motion: no-preference)` 下才给 opacity 过渡；reduce 时纯切换。
7) 无 JS：只剩主图 + 一条 <h2>，不报错、不留空白容器。
```

### 3.3 为什么用 `hidden` + class 双轨（而不是只用其一）

- 只用 `hidden`：`display:none` 无法过渡 ⇒ 用户要的"淡入"做不到，且 `hidden` 会被任何同特异性的 `display` 声明压掉。
- 只用 class（全部帧都渲染可见）：无 JS 时 4 张图**竖着堆**，页面塌掉。
- 双轨：服务端 `hidden` 保证**无 JS 时只露主图**；init 时摘掉 `hidden`、改用 `--off`（`opacity:0; pointer-events:none;` + 绝对定位叠放）⇒ JS 有淡入，且**盒子尺寸恒定**。并显式补一条 `.sf-gallery__slide[hidden] { display: none; }`（防止主题里任何 `display` 声明压过 UA 的 `[hidden]`）。
- 非活动帧加 `aria-hidden="true"`（`opacity:0` 的图仍会被读屏播报）；活动帧移除。已核对：`toc-nav.js:87` 的 SKIP 列表里有 `[aria-hidden='true']`，但**它只筛 h2**，帧里没有 h2 ⇒ 无副作用。

---

## 四、移动端

- **点击为主 + 滑动为辅**：缩略图按钮是主路径；舞台上的 Pointer Events 手势是增强。
- **滑动实现**（约 20 行，`pointerdown/pointermove/pointerup`，`setPointerCapture`）：
  - **意图锁定**：只有 `|dx| > 40px` **且** `|dx| > |dy| × 1.5` 才认作切图；否则**完全不 `preventDefault`**，纵向滚动原样交给浏览器。这是横向手势最常见的翻车点（把用户的纵向滑动吃掉）。
  - 只在 `|dx| > 40px` 的首次判定时锁方向（`axis` 变量），之后不再改判；`pointercancel` 复位。
  - 阈值内抬起 **不切图**（避免误触）。
- **≤768px 缩略图条**：`overflow-x: auto; scroll-snap-type: x mandatory; scroll-padding-left: …`，瓦片 `flex: 0 0 84px` + `scroll-snap-align: start`，露出约 4 张的量（375px 下 4×84+3×8 = 360px，与内容宽 ~343px 相近 ⇒ 轻微可滑，暗示"还有"）。
- **≥769px**：缩略图条居中一行（`justify-content: center`），不滚动。
- 舞台：`max-width: 680px; margin-inline: auto`（桌面），`aspect-ratio: 1/1`；≤768px 取满内容宽。
- **不使用任何 `:has()`**（站内计数不变量见 §0 发现 5）。

---

## 五、CSS（`style.css` 追加，选择器全部限在 `.sf-gallery` 下）

新增选择器清单（约 55–70 行，含注释）：

```
.sf-gallery__inner            /* 限宽 + 居中，不碰底色（底色在 section 上） */
.sf-gallery__title            /* 与 .sf-actives__title 同级视觉（h2 语义） */
.sf-gallery__stage            /* position:relative; max-width:680px; aspect-ratio:1/1; radius 8px; overflow:hidden */
.sf-gallery__slide            /* position:absolute; inset:0; margin:0 */
.sf-gallery__slide[hidden]    /* display:none —— 显式兜底 */
.sf-gallery__slide--off       /* opacity:0; pointer-events:none */
.sf-gallery__slide img        /* width/height 100%; object-fit:cover; object-position:center */
.sf-gallery__thumbs           /* flex row; gap 12px; role=tablist */
.sf-gallery__thumb            /* 84–116px 方瓦片；border:1px solid; radius 6px; padding:0 */
.sf-gallery__thumb img        /* 100%/100%; object-fit:cover */
.sf-gallery__thumb[aria-selected="true"]   /* 选中态：2px 主色描边 */
.sf-gallery__thumb:focus-visible           /* outline 2px accent, offset 2px */
@media (max-width: 768px)     /* 缩略图条 scroll-snap；舞台满宽 */
@media (prefers-reduced-motion: reduce)    /* 过渡全关 */
```

- **照抄 `.sf-fac` 的部分**：`border-radius:8px`、`aspect-ratio`、`object-fit:cover`、`object-position:center`、软阴影（`0 2px 12px rgba(0,0,0,.08)`）、`focus-visible` 用 `var(--wp--preset--color--accent)`、以及 `prefers-reduced-motion` 关过渡的写法。
- **不照抄的部分**：`!important`（理由见 §0 发现 2）、core Gallery 相关的宽度规则（我们不是 Gallery 块）。
- 舞台 `object-fit` 用 **`cover`**（不用 `contain`）：`cover` 不会在灰带上留出可见的同色补边、也不会让 3:2 的图画得比 1:1 的图**小一圈**；舞台盒子恒定 ⇒ ΔCLS ≈ 0。已知取舍：3:2 / 4:3 的车间图会被左右居中裁切 —— 这是站内既有语言（`.sf-fac` 同法），且**主图（1:1）零裁切**。
- **版本同步两处**：`style.css:5` 与 `functions.php:26` 同时 `2.10.45` → **`2.10.46`**；新脚本 ver `1.0.0`。

---

## 六、交互影响

| 对象 | 结论 | 依据 |
|---|---|---|
| **K1**（`.sf-formula__cta` + `data-formula`/`data-form`） | **零交互** | 图集不产出该 class；`formulas.js` 的选择器只在 K1 按钮上；本批不碰公式卡 |
| **K2**（`.sf-formulas-data` JSON 镜像） | **零交互**，且图集**不产出 K2**（与 `sf_formula_actives` 一致） | 新 shortcode 不输出该节点；核验项要求 K2 逐值同 |
| **配置器** | **零交互** | 图集不产出 `.configurator*`；`sessionStorage` 键名不变；不新增任何入队条件到配置器 |
| **Product JSON-LD（K6）** | **零交互** | K6 读**磁盘模板文件**并只认 `<span class="sf-spec-term">`；图集不出现该串。第 1 批已固化的四元组断言继续跑 |
| **toc-nav（唯一有真实副作用）** | **点轨 7 → 8**，新标题成为**第 1 颗点** | 实测渲染 h2 序列＝`Standard Formulas / Build Your Soft Chews Formula / Active Ingredients & Guaranteed Analysis / How We Work / Frequently Asked Questions / Related Dosage Forms / Request a Soft Chews Quote`；`toc-nav.js:84` 收 `main` 下全部 `h2`。图集块插在 `#formulas` **之前** ⇒ 新 h2 排第一，`anchor()`（line 103-105）随后给无 id 的 h2 打 `sf-sec-N`，**序号整体 +1**。显式 anchor（`#gallery` / `#formulas` / `#configurator` / `#actives` / `#inquiry-form`）**不受影响**。**条件 B 的替代实测见 §七 第 9 项；375px 无点轨（§0 发现 1）** |
| **入队 / 回归门** | 8 页（+ zh 镜像 1 页）**必然 DIFF**，是**预期项** | 新增 `formula-gallery.js`，且 style.css ver 变动。处理方式与证明见 §0 发现 4、§七 第 2/3 项 |
| **TranslatePress** | 新串**记为遗留**，随实拍替换一起重收录 | 新 h2（8 页 × `{L}`）、4 条 alt、3 个缩略图 aria 标签 |

---

## 七、回归点（12 项，含预期数字）

| # | 项 | 判据 / 预期 |
|---|---|---|
| 1 | **限定证明**（marker-driven） | 从候选渲染里删掉 `<!-- B2D-S2: gallery -->` 到 `<!-- wp:group {"tagName":"section","anchor":"formulas"` 之间的字节，与基线**逐字节**相同 ⇒ **47/47**（9 页带块 + 38 页原样）。判据是标记驱动，**不用页面白名单**；END 标记命中数须断言 = 1 |
| 2 | **掩码回归** | A 传＝基线 commit、B 传＝候选 commit（同一 preflight 目录名），先 `b2d_s2_norm.py` 归一化 ver 令牌 ⇒ 预期 **38 SAME / 9 DIFF**，DIFF 集合 ＝ 8 个剂型页 + `/zh/products/soft-chews/`。先跑 `--aa` 自检（**每个模板家族各挑一页**） |
| 3 | **资源清单** | `b2c_s2_ver_inventory.py`：`style.css` token 在 **47/47** 页变动；`formula-gallery.js` **只在 9 页出现**；**无其它 asset 变动**。另跑一次**未归一化**的原始掩码门存证（预期 47 DIFF），两结果并列进档 |
| 4 | **JSON-LD** | 47 页 deep-equal；8 个剂型 Product 仍为四元组 `(1 block, 无 additionalProperty, 页面有 class="sf-spec-term"=True, 页面无 <span class="sf-spec-term">=False, 模板文件无 sf-spec-term=False)` |
| 5 | **K2** | `.sf-formulas-data` 逐值同、3 个带标签段非空、顺序同 |
| 6 | **渲染计数** | 每页 `figure.sf-gallery__slide` = **4**；`hidden` 帧 = **3**；服务端 HTML 里 `sf-gallery__thumb` = **0**（JS 派生）；`<h2>` = **8**；`sf-actives__item` = 4/3/3/…（沿用第 1 批真值 21 / 99 / 43 全站） |
| 7 | **尺寸表对账** | shortcode 的尺寸表 vs 服务端 `getimagesize`：**逐文件相等**；9 页渲染出的 `width`/`height` 与真实像素一致（专门针对"陈旧属性"这条） |
| 8 | **`:has()` 不变量** | `style.css` = **163**、`configurator.css` = **7**、合 **170**（批前批后同值） |
| 9 | **浏览器 E2E**（`agent-browser`，`set credentials` 在 `open` 之前） | ≥1101px：**点轨 7→8**、8 颗依次落 `#sf-sec-{i}`、点轨盒子在视口内（`top≥0 && bottom≤innerHeight`）、与浮动堆叠无重叠、标签卡不越左界。1440 与 **1280×700** 各跑一次。切换：4 个缩略图依次点击 ⇒ 活动帧/`aria-selected`/`tabindex`/舞台 `aria-label` 全部正确；**←/→ 漫游焦点**；**合成 pointer 手势**：`dx=120,dy=10` ⇒ 切图；`dx=10,dy=120` ⇒ **不切**（意图锁定）；`dx=25,dy=5` ⇒ **不切**（阈值内）。375 与 768：**横向文档溢出 = 0**、缩略图条 `scroll-snap-type` 生效、无 JS 时主图在、控制台错误 = 0。zh 页渲染正常 |
| 10 | **工作区 ↔ 云端 md5** | 全部文件逐字节同（含**新增** `formula-gallery.js`，`_backup/`、`.DS_Store` 除外）；数量 = 批前 +1 |
| 11 | **版本同步** | `style.css:5` 与 `functions.php:26` 同时为 `2.10.46`；`style.css` 中 `Version:` 只出现 1 次 |
| 12 | **封锁未破** | 匿名 dev 仍 **401**；`www.zxpet.com` 仍 **302**；`mu-plugins/` 事后只剩 `zz-sf-dev-lockdown.php`；`themes/` 无 preflight 目录；云端 `git status` 干净 |

**取证**：6 张截图（1440 全带 / 1440 切到第 3 张 / 1280×700 点轨 / 375 舞台 / 375 缩略图条 / zh 带），存 `docs/b2d-step2-shots/`。

---

## 八、备份与回滚

- **实施前**：10 个文件快照进 `_backup/b2d-step2-<YYYYmmdd-HHMMSS>/` + `MANIFEST.md`（字节数 + sha256）：
  `functions.php`、`style.css`、`templates/page-{soft-chews,tablets,powders,pastes,drops,liquids,fish-oil,dental-chews}.html`
  （`_backup/` 已被 `**/_backup/` 排除在 git 之外）
- **新增文件**：`assets/js/formula-gallery.js`（无"改前版本"可备份；回滚＝同 commit revert 连带删除）
- **回滚**：**单 commit 承载全部实施改动**（10 改 + 1 新增）⇒ 一条 `git revert <sha>` 整体回退。工具/文档/取证**另开 commit**，不影响回滚粒度。

---

## 九、预检（沿用第 1 批已固化的装置）

| 项 | 做法 |
|---|---|
| 头门 | `X-SF-Preflight: 1`（**请求头**，不用 query，避免被回显进页面） |
| 副本主题 | `wp-content/themes/sinofresh-theme-preflight/`，来源 `git -C site-repo archive <commit> sinofresh-theme \| tar -x --strip-components=1`；mu-plugin 同时过滤 **`stylesheet` 与 `template`**（priority 99） |
| 工具 | 直接复用 `tools/b2d_s1_preflight.py install <commit>` / `remove` / `status`（与批次无关，通用） |
| 顺序 | 带门的抓取**全部排在**不带门之前；点击类测试**最后** |
| 凭据 | **所有**访问带 `-u 'sfdev:VkEws18Kl5V1qp3TpZ6s'`（不带＝两侧哈希同一个 401 页＝**静默全绿**） |
| 日志 | mu-plugin 日志写在 `mu-plugins/` 旁（**不写 `/tmp`**，`open_basedir` 会静默拦）；install 时把上一轮轮转为 `.prev`，避免毁掉上一传的证据 |
| 收尾 | `remove` 后删净副本 + mu-plugin + 日志，**复验**基线逐字节不变、`mu-plugins/` 只剩 lockdown |

> **一处命名分歧**：你写的是"独立主题目录 `sinofresh-preflight`"，现有工具链（`b2d_s1_preflight.py` 的守卫 `case` 与 `szz-sf-preflight` mu-plugin）把目录名写死为 **`sinofresh-theme-preflight`**。改名要同时改守卫与掩码项，**零收益** ⇒ **建议沿用 `sinofresh-theme-preflight`**（一句"同意"即生效；你若坚持改名我照改）。

---

## 十、需要你回的字（3 个）

| # | 项 | 选项 |
|---|---|---|
| 1 | **第 4 槽位** | **S1b（荐）**＝`fac-line.webp`（4 张真不同、替换清单数量与 S1a 相同） ／ S1a＝照原话用 `{slug}-300x300`（6 页同画面、**2 页同一文件**） |
| 2 | **H2 文案** | **A（荐）**＝`Inside Our Soft Chews Production` ／ B＝`Soft Chews Product Gallery` ／ C＝`A Closer Look at Our Soft Chews` |
| 3 | **`!important`** | **A（荐）**＝不写（有 specificity 依据；全站 img 规则 0 处 `!important`） ／ B＝照 `.sf-fac` 全量写 |

另：**条件 B 的替代实测**（§七 第 9 项）你若认可，回一句"h2 按替代门验"即可；若仍要"375px 看见 8 颗点"，那是改 `display:none` 断点，**属另一批次**，本批不做。

---

## 附：实施顺序（确认后执行）

```
0) 备份 10 文件 → _backup/b2d-step2-<ts>/ + MANIFEST.md
1) writing: functions.php（shortcode + 入队 + ver）、8 templates（同源块）、style.css（选择器 + ver）、assets/js/formula-gallery.js（新）
2) 本地静态自检：锚点 sha、命中数=1、块 JSON 可解析、PHP lint（借 LocalWP 的 php -l）、JS 语法
3) 提交 → push → 云端 pull + 只 chown 主题目录
4) 基线抓取（带凭据）→ 预检 install（基线 commit）→ A 传 → install（候选）→ B 传 → remove
5) 归一化 → 掩码门（含 --aa 自检）→ 资源清单 → 限定证明 → 数据层
6) 浏览器 E2E（1440 / 1280×700 / 768 / 375 / zh）+ 6 张取证图
7) 工作区↔云端 md5；封锁复验；清理复验
8) 文档 docs/batch2d-step2.md + 可视化报告；提交推送；**停下汇报，等你确认再进第 3 批**
```

**约束自检**：不删任何 DOM（纯新增）／不引入 JS 库或 CSS 框架（手写约 20 行手势 + 约 60 行切换）／自闭合块 ` /-->`／dev 全部访问带凭据／主题此刻**零改动**。

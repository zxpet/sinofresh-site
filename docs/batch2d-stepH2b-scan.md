# 批 H2b · Step 0 扫描报告（只扫不改）

> **日期**：2026-09-22 · **批次**：H2b（8 剂型页配置器删除 + chips 移位 + CTA 改向 + enqueue 清理）
> **形式**：只读扫描。**主题零改动**（`git status` 仅新增 `tools/b2d_h2b_scan.py`）。
> **工具**：`tools/b2d_h2b_scan.py`（纯读）；原始数据 `_backup/b2d-h2b-scan.json`
> **结论**：**发现 5 项与 playbook 预期不符**（第 1 类「必须停」）⇒ 停下报告，等裁决。
> **参照**：`docs/agent-playbook.md`（正文 + 附录 A）

---

## 0. 一句话

8 页配置器区块可安全整块删除（自闭合平衡 0，sprites/JSON-LD 无块外依赖），
但**「chips 落点」和「configurator.css 能不能删」两个前提在 playbook 里写反了**，
另有三处补偿规则/回归点 playbook 未覆盖。**这 5 项定不下来就不能动第一刀。**

---

## 1. 块边界（实测，1-based，含 `<!-- wp:group -->` 开闭）

| 页 | 总行 | **块起止** | 块内行 | 块内字节 | 块后 balance | chips 行 |
|---|---|---|---|---|---|---|
| soft-chews | 651 | **56 – 271** | 216 | 27,117 | 0 | 228 |
| dental-chews | 607 | **56 – 220** | 165 | 20,788 | 0 | 177 |
| fish-oil | 590 | **56 – 203** | 148 | 15,899 | 0 | 161 |
| tablets | 584 | **56 – 207** | 152 | 18,383 | 0 | 165 |
| powders | 580 | **56 – 203** | 148 | 17,881 | 0 | 161 |
| liquids | 577 | **56 – 190** | 135 | 16,376 | 0 | 149 |
| drops | 576 | **56 – 189** | 134 | 16,039 | 0 | 148 |
| pastes | 567 | **56 – 190** | 135 | 15,922 | 0 | 149 |
| **合计** | — | — | **1,233** | **148,405（144.9 KB）** | 8/8 = 0 | — |

- 块结构在 8 页**完全同构**：`L58 wp:heading` + `L61 wp:paragraph` + `L64 wp:html`（直到 `L269 <!-- /wp:html -->`、`L270 </section>`、`L271 <!-- /wp:group -->`）
- playbook §9【H2b】一 的行号系估算（`55-272` / `55-207` / `55-220` / 「其余 55-189 左右」）；**以本表为准**
- `block_markers`：`svg_sprite=1`、`symbol` 34/20/23/17/15/15/15/13、`form_tag=0`、`input_tag=2`、`select_tag=0`、`buttons=0`、`chips_shortcode=1`、`configurator_class` 226/168/183/161/150/144/145/152（**合计 1,329 处**）

### 块内自洽性（可整块删的证据）

| 断言 | 实测 |
|---|---|
| 块内 `application/ld+json` / `<script` / `sf-schema-desc` | **8/8 = 0** ⇒ K6 剂型页 JSON-LD 不受影响 |
| `<use href="#i-…">` 在块**之后**出现次数 | **8/8 = 0** ⇒ 34 个 symbol 的 sprite 无块外引用 |
| `configurator__sprite` 在块后出现 | 8/8 = 0 |
| 块内 `wp:html` 开闭平衡（删掉后全文 balance） | 8/8 = **0** ⇒ 删除不破坏区块解析 |

---

## 2. chips（`[sf_explore_chips]`）现状

- 短代码实现在 `functions.php:229-255`（`add_shortcode` 在 `255`）——**只产 `<nav class="sf-explore__chips">`**
- **band 外壳不归短代码**：`.sf-explore` + `<h3 class="sf-explore__title">Explore more dosage forms</h3>` + `<a class="sf-explore__btn" href="/products/">Browse All Products →</a>` **硬编码在模板里**（soft-chews L226 / 227 / 229），移位必须一并搬走
- 位置：`.sf-explore` 在**配置器 options 列内部**（8 页一致），即 chip 行跟着配置器一起被删 —— 与 playbook §4⑦ 相符 ✓
- 短代码数据源 = `get_pages(parent=19)`（Products 的已发布子页，`menu_order` 序），当前页带 `aria-current="page"` ✓ 与 playbook「移到 Hero 之后」不冲突

---

## 3. ⚠️ 不符 #1：配置器的**实际位置**与 playbook 描述相反

playbook §4 给的页序：`④ facts 行 → ⑤ 卡墙 → ⑥ 配置器（现位置：hero 之后、卡墙之前）→ ⑦ chips`

实测页序（8 页一致）：

```
L1        header template-part
L3  – 27  hero (.sf-hero-inner, #2E6B54)          ← 两个 CTA
L29 – 36  sf-facts-mini（F1 极简核心事实行，4 项）
L38 – 53  卡墙 #formulas（sf-formula_grid + Browse All Formulas →）
L56 – 271 配置器 #configurator  ← chips 在 L228，位于其 options 列内
L273+     How We Work → FAQ → Related Dosage Forms → Request a Quote
```

⇒ playbook 说配置器在「hero 之后、卡墙之前」，**实测在卡墙之后**。
⇒ 因此 §4⑦ 与 §9【H2b】二 给的 chips 新位置「Hero 之后、卡墙之前」**并不是配置器现在占的槽位**，
　 两种读法都自洽、不能自行挑：

| 选项 | chips 落点 | 理由 / 代价 |
|---|---|---|
| **A** | `hero` 与 `facts-mini` 之间（L28） | 字面「Hero 之后」；但把 hero 与它的核心事实行**拆开** |
| **B**（建议） | `facts-mini` 与 `卡墙` 之间（L37） | 保住 hero+facts 作为一块，chips 作卡墙的「前置导航带」；与「卡墙之前」字面一致 |
| **C** | 原地（`卡墙` 之后，即配置器原槽位） | 改动最小、DIFF 最小；但违背「Hero 之后」的字面 |

---

## 4. ⚠️ 不符 #2：`configurator.css` **不能直接删** —— `.sf-explore__btn` 在块外仍活

- `configurator.css`：**958 行 / 24,816 字符**；`:has(` **7 处**（其中 5 处真实规则：`body:has(.configurator__bar)` ×3、`body:has(.configurator__drawer.is-open)` ×2；2 处在注释里）；`!important` 0 处
- 选择器分组：`.configurator__*` 占绝对多数，另有 **`.sf-explore*` 一族在 L833–957（125 行，含 5 行注释）**
- **`.sf-explore__btn` 每页出现 2 次**：
  - `L50` —— **在卡墙里**（`<a class="sf-explore__btn" href="/formulas/">Browse All Formulas →</a>`）⇒ **卡墙保留 ⇒ 这个类必须活着**
  - `L229` —— 在配置器块内（`Browse All Products →`）⇒ 随块删除
- ⇒ playbook §9【H2b】四「先注释后删文件」如果不先把 `.sf-explore*` 迁走，**8 页卡墙的 `Browse All Formulas →` 会掉样式**（还原成裸链）
- 迁移清单（最低）：`.sf-explore`、`.sf-explore__title`、`.sf-explore__chips`、`.sf-explore__chip`、`.sf-explore__chip:hover/:focus-visible/.is-current`、`.sf-explore__btn`、`.sf-explore__btn:hover`、`@media(max-width:768px)` 块、`@media(prefers-reduced-motion)` 块 ⇒ **125 行全迁**
- `:has(` 账：删 `configurator.css` 后全站 **171 → 164**（style.css 的 164 不动），满足 playbook「170 处计数不增」✓（注：playbook 的基线 170 已漂成 171，见 §8）

---

## 5. ⚠️ 不符 #3：`style.css:5919` 是**专为体贴配置器做的补偿**，必须复原

```css
/* style.css:5915-5921 */
@media (max-width: 768px) {
	/* Tighten Standard Formulas -> configurator gap (inline spacing-80 paddings
	   on the templates need !important to override). 24px block gap + 32px
	   padding-top = 56px from band edge to the "Build Your …" title. */
	.sf-formulas { padding-bottom: 0 !important; }
	#configurator { padding-top: 32px !important; }
}
```

- `#configurator` 规则 ⇒ 配置器删掉后成**死规则**，应删
- `.sf-formulas { padding-bottom: 0 !important }` ⇒ **是为了让卡墙贴近配置器**；配置器没了之后，
　 卡墙底部 padding 为 0，移动端会直接**贴到下一段（How We Work 的 bg-light 带）**，`Browse All Formulas →` 贴边
- ⇒ 必须**同时**：删 `5920`、**还原 `5919`**（恢复卡墙正常下内边距）。playbook §9【H2b】完全未提，H6 的旧 CSS 清单（`.sf-facts__*` / `.sf-spectable__*` / `.sf-fdetail-media__*`）也不含它

---

## 6. ⚠️ 不符 #4：桌面点轨条目 **6 → 5**

- `toc-nav.js 2.0.0` 由 `functions.php:45` 按页面白名单入队（含 8 个剂型页），从 **H2 序列**编号
- 8 页 H2 各 **6 个**，其中第 2 个正是配置器的 `Build Your {剂型} Formula`：

```
1 Standard Formulas
2 Build Your <Form> Formula     ← H2b 删除
3 How We Work
4 Frequently Asked Questions
5 Related Dosage Forms
6 Request a <Form> Quote
```

- ⇒ 点轨 `.sf-toc`（桌面专用，`≤1100px` display:none）条目 **6→5**；`sf-sec-N` 下游锚点整体前移
- 这是**预期的正当变化**，但 playbook §9【H2b】回归清单只列「16 页 DIFF / basket / K1-K7」，
　 需补一条回归断言（E2E：轨道条目数 = 5，且第 2 条 = How We Work）

---

## 7. ⚠️ 不符 #5：`.sf-explore` 的尺寸前提随位置失效

`configurator.css:851-855` 原文：

> `/* Outline pills generated by the [sf_explore_chips] shortcode. … Sized one notch tighter than the option buttons so all 8 fit on a single row in the 65%-wide options column at 1440px. */`

- 现状：chip 带生活在 **65% 宽**的 options 列里，尺寸是按此调的
- 移出后（无论 A/B/C）都是**通栏**，1440px 下 8 个 chip 一行绰绰有余 ⇒ **尺寸与移动端节奏需重定**
  （`@media(max-width:768px)` 现在是「`flex-wrap:nowrap` + 横向滚动 + 隐藏滚动条」，通栏后未必还需要）
- playbook §9【H2b】未提；H3/H4 也依赖 `.sf-explore` 视觉基线

---

## 8. 数值漂移（**不阻塞**，按实测执行）

| 项 | playbook | 实测 |
|---|---|---|
| `:has()` 总数 | 170（163 + 7） | **171**（`style.css` **164** + `configurator.css` **7**，含 2 处注释） |
| `functions.php` enqueue | 「182-190」 | 182–213 是整个闭包；**删 188/189 两行**；`$is_dosage_page`(**186**) 必须留（**205** 行的 `formulas.js` 仍用它） |
| §4④ facts-mini | 「一行三项」 | 实际 **4 项**（MOQ / Lead time / Certifications / **Packaging**，Batch G 第 4 行） |
| §5 `text-primary` | `#1A1A1A` | `theme.json` = **`#1C2B24`**（其余 token 全一致；hero `#2E6B54` ✓ `style.css:1880`） |
| 详情页 hero CTA | 「配置器联动」 | `single-sf_formula.html:13` 两个控件：`<button class="sf-formula__cta">Reference this formula →`（K1，纯复制+sessionStorage）+ `<a href="{{FORM_HREF}}#configurator">Build Custom Formula`（改向目标）✓ |

---

## 9. 已核实**相符**的项（可放心照 playbook 做）

| 项 | 结论 |
|---|---|
| 8 页 hero CTA | `L22` `href="#configurator"`，文案 `Build Custom Formula` ✓ |
| 详情页 CTA | `single-sf_formula.html:13` `{{FORM_HREF}}#configurator` ✓ |
| `config-pdf` 端点 | `basket.js:391` **直接** `fetch('/wp-json/sinofresh/v1/config-pdf')`，与 `configurator.js` 无耦合 ⇒ **端点保留** ✓（playbook 正确） |
| `configurator.js` 侧调用 | 仅 `configurator.js:699` 一处；删 JS 即可，不动端点 ✓ |
| 块内自洽 | 无 JSON-LD / 无 `<script>` / sprite 无块外 `<use>` / `wp:html` balance 0 ✓ |
| 单一事实源 | `inc/formula-pools.php` 头部已声明「H2 删掉配置器后它是唯一副本」⇒ 卡墙参数池已就位 ✓ |
| K1–K7 契约 | K1 `formulas.js` 的 `getElementById('configurator')` 已 null-safe（`:110-113`）⇒ 删块后**自动静默退化**，不报错 ✓ |

---

## 10. 代码减少量（按当前实测）

| 资产 | 规模 | H2b 处理 |
|---|---|---|
| 8 页模板块内 HTML | **1,233 行 / 144.9 KB** | 整块删（chips 40 行外迁 ⇒ **净 −1,193 行**） |
| `assets/css/configurator.css` | 958 行 / 24.8 KB（其中 `.sf-explore*` 125 行） | **`.sf-explore*` 125 行外迁 → style.css**；余 833 行停入队后删 |
| `assets/js/configurator.js` | **876 行 / 31.3 KB** | 停入队 → 删（`config-pdf` 调用点随之消失，端点保留） |
| `style.css` | 8,778 行 | −1 行（`#configurator` 死规则）+ 1 行补偿还原 |
| `functions.php` | 4,742 行 | −2 行（188/189 enqueue） |
| `assets/js/formulas.js` | 117 行 | 不动（K1 契约不变；`:108-113` 死分支留 H6） |
| **合计** | — | **≈ −3,000 行 / ≈ −200 KB**；剂型页每页**少传 54.8 KB**（css 24.8 + js 31.3 ≈ 56 KB） |

---

## 11. 建议拆分（两批）

| 批 | 内容 | DIFF 集合 | 门方向 |
|---|---|---|---|
| **H2b1** | chips 外迁（band + nav 整体搬）→ 删块 → CTA 改向 → `.sf-explore*` 迁入 `style.css` → 偿还补偿（`5919/5920`）→ 移动端节奏重定 | **16 页必差**（8 en + 8 zh），其余 59 页只许 ver 令牌移动 | 纯删除：基线上删块 = 候选；逆操作还原 |
| **H2b2** | `functions.php` 停入队（删 **187–190 共 4 行**：两条 enqueue ＋ 空壳 `if`；⚠️ 185–186 的 `$dosage_pages`/`$is_dosage_page` 必须保留，205 行 `formulas.js` 仍在用）→ 资产删（`configurator.css` **整文件** ＋ `configurator.js`） | 16 页各少 2 行资源引用（`<link>` L119 ＋ `<script>`），其余 59 页逐字节不动 | 纯删除 |

理由：H2b1 是**结构与几何**改动（要跑视觉/几何 E2E），H2b2 是**资产下线**（要跑「资源不再被请求」断言）。
混在一起会让「DIFF 16 页」这个硬指标同时被两种原因触发，失败时无法归因。

---

## 12. 结论

**触发 playbook §7「必须停」第 1 类：扫描发现与预期不符（结构变化 + 新依赖）。**

需裁决 5 项：**#1 chips 落点（A/B/C）**、**#2 `.sf-explore*` 125 行外迁（是否同意）**、
**#3 补偿规则偿还（是否同意）**、**#4 点轨 6→5 是否记为预期变化**、**#5 通栏后尺寸重定口径**。

裁决后即出 H2b1 详细方案（Step 1-N），按手册自动执行。

**服务器状态**：未 pull；authority guard 未删；**DB 未动**；主题零改动。

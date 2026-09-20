# Batch 2D Step 4 — 配方详情页两处调整（扫描 · 方案）

日期：2026-09-21　状态：**扫描完成，等确认后动手**
起点：`9132f83`（本地 = 云端 = origin）

---

## 0. 一句话

两处改动**都只落在同一个 shortcode 内部**，都只影响 **42 个详情页**（21 en + 21 zh），
剂型页与其余 33 页预期**逐字节不动**；且删掉的两张卡，其数据在页面上**另有完整去处**
（⑤ actives 段 42/42 + Product JSON-LD 的 `additionalProperty`），**不丢任何信息**。

---

## 1. 现状（实测，非推测）

### 1.1 调用点只有一处

| shortcode | 定义 | 被谁调用 | 影响面 |
|---|---|---|---|
| `[sf_formula_detail]` | `functions.php:1401` | `templates/single-sf_formula.html:39` | 42 详情页 |
| `[sf_formula_gallery]` | `functions.php:1229` | `templates/single-sf_formula.html:22` | 42 详情页 |

→ **没有任何剂型页模板（8 个 `page-*.html`）调用它们**，所以"影响 21 条配方详情页"成立（含 zh 共 42 页）。

### 1.2 Specification 段现状

`sinofresh_formula_detail()` 遍历 3 个字段，各出一张卡（`functions.php:1409-1413`）：

```php
$fields = array(
    array('label' => 'Ingredients',         'key' => 'sf_formula_ingredients'),
    array('label' => 'Guaranteed Analysis', 'key' => 'sf_formula_analysis'),
    array('label' => 'Standard Specs',      'key' => 'sf_formula_specs'),
);
```

实测 `/formulas/ear-care-drops/`（42/42 页卡片标签集合与顺序**完全一致**）：

| 卡 | 值 | 长度 |
|---|---|---|
| Ingredients | `Organic Aloe Vera, Tea Tree Oil, Calendula` | 42 |
| Guaranteed Analysis | `Aloe Vera ≥10%` | 14 |
| Standard Specs | `30ml/50ml dropper bottle · 24 months shelf life` | 47 |

3 张卡**全部非空**（42/42，无"某配方缺某字段"的情况）。

### 1.3 图集 h2 现状

`functions.php:1265` — **全库唯一一处**（其余 `Inside Our` 命中都在 `_backup/` 或 about 页的 "Inside Our Factory"，无关）：

```php
. '<h2 class="sf-gallery__title">' . esc_html(sprintf('Inside Our %s Production', $label)) . '</h2>'
```

`$label = sinofresh_formula_label($form)`（剂型 label）。实测输出：
`/formulas/ear-care-drops/` → **`Inside Our Drops Production`**（`Drops` 是剂型，不是配方名）。

### 1.4 21 个配方名（= 页面 h1 = `post_title`）

| # | 配方名 | # | 配方名 |
|---|---|---|---|
| 1 | Bladder Support Powder | 12 | Natural Cleaning Dental Sticks |
| 2 | Calcium & Phosphorus Tablets | 13 | Nutrition Paste |
| 3 | Calming Soft Chews | 14 | Oral Care Dental Sticks |
| 4 | Digestive Soft Chews | 15 | Plaque Control Dental Chews |
| 5 | Ear Care Drops | 16 | Probiotic Powder |
| 6 | Hairball Remedy Paste | 17 | Pumpkin Digestive Powder |
| 7 | Joint Support Soft Chews | 18 | Pure Fish Oil Blend |
| 8 | Joint Support Tablets | 19 | Skin & Coat Soft Chews |
| 9 | Liquid Joint Support | 20 | Urinary Care Drops |
| 10 | Liquid Skin & Coat | 21 | Wild Alaskan Salmon Oil |
| 11 | Multivitamin Tablets | | |

**3 个标题含 `&`**（#2 / #10 / #19）⇒ 需 `esc_html()` 输出成 `&amp;`（浏览器显示正常）。

⚠️ **中文详情页（`/zh/formulas/…`）的 h1 也是英文**（实测 `/zh/formulas/ear-care-drops/` 的 h1 = `Ear Care Drops`）
⇒ 改后 zh 页 h2 = `A Closer Look at Ear Care Drops`。与现状（`Inside Our Drops Production`）**同为英文**，
**不引入新的中英混排**。

### 1.5 h2 不被任何消费者依赖（安全前提）

| 消费者 | 是否读 h2 文本 | 依据 |
|---|---|---|
| `assets/js/formula-gallery.js` | ❌ 只读 `.sf-gallery__inner` 的 `data-gallery` | `formula-gallery.js:38` |
| `style.css` | ❌ 只有 `.sf-gallery__title { margin: 0; }` | `style.css:7978` |
| `tools/b2d_s3_confine.py` gate 2 锚点 | ❌ 只抓 `.sf-gallery__inner` 的 `data-gallery` | `confine.py:84` |

⇒ 改文案**不动 DOM 结构、不动锚点**。

---

## 2. 改动方案（两处，都在 `functions.php`）

### 改动 A — Specification 只留 STANDARD SPECS

`sinofresh_formula_detail()`（1401–1431）：

```php
$fields = array(
    array('label' => 'Standard Specs', 'key' => 'sf_formula_specs'),
);
```

- 函数签名、`is_singular('sf_formula')` 守卫、空值跳过、全空返回 `''`、`sf-fdetail__grid` + `sf-fdetail__card` 结构**全部不动**
- **数据源不变**：3 个 meta 一个都不删、不改，只是其中两个不再渲染成卡
- 同步更新两处注释：`1385` 的 "the three-field specification"、`1409` 前后关于三字段的说明
  → 改为说明"只渲染 Standard Specs；Ingredients / Guaranteed Analysis 仍存于 meta，
  其展示由 ⑤ actives 段承载（两者改写自同一份数据）"

### 改动 B — 图集 h2 改文案

`sinofresh_formula_gallery()`（1238–1241 取 label、1265 输出）：

```php
// 取配方名（与 h1 的 {{TITLE}} 同源，见 functions.php:2793 => get_the_title()）
$title = is_singular('sf_formula') ? get_the_title(get_queried_object_id()) : '';
if ($title === '') {
    $title = $label;   // 兜底：任何异常下都不会让 h2 消失
}
...
. '<h2 class="sf-gallery__title">' . esc_html(sprintf('A Closer Look at %s', $title)) . '</h2>'
```

- `$label` 在本函数内**只被 h2 使用**（已 grep 确认）⇒ 保留为兜底，不做无意义的删除
- 输出仍是 `esc_html()`，DOM 结构一行不变

---

## 3. 为什么删两张卡不丢信息（两条独立证据）

### 证据 1 — ⑤ actives 段已完整承载同一份数据（42/42）

按 gate 4 的**原样形态**比对（`pills == Ingredients.split(",")`、
`"<dt> <dd>" 拼接 == Guaranteed Analysis.split(",")`）：

| 比对 | 结果 |
|---|---|
| actives 段的药丸 == Ingredients 卡 | **42 / 42 一致** |
| actives 段的行 == Guaranteed Analysis 卡 | **42 / 42 一致** |

即：这两张卡与 ⑤ `Formula & nutrition` 段是**同一份数据的两次渲染**（现状是重复展示）。

### 证据 2 — 机器可读数据仍在 Product JSON-LD 里

`/formulas/ear-care-drops/` 的 `@type=Product` 仍带：

```
additionalProperty: [
  {name: "Ingredients",         value: "Organic Aloe Vera, Tea Tree Oil, Calendula"},
  {name: "Guaranteed Analysis", value: "Aloe Vera ≥10%"},
  {name: "Standard Specs",      value: "..."} ]
description: "Ear Care Drops — a standard Drops formula from the SINO FRESH OEM/ODM range … Ingredients: … Guaranteed analysis: …"
```

详情页 JSON-LD **由 post 标题 + 3 字段 meta 直接构造，不读渲染 HTML** ⇒ 删卡后
SEO / 结构化数据**一字不减**。

> 结论：删掉的是**重复渲染**，不是数据。这也是本次改动最需要被证明的一点，已入核验计划（见 §5 门 4）。

---

## 4. 影响面

| 页面组 | 页数 | 预期 |
|---|---|---|
| en 详情页 | 21 | ④ 少两张卡 + ② h2 文案变 |
| zh 详情页 | 21 | 同上 |
| en 剂型页 | 8 | **逐字节不动** |
| zh 剂型页 | 7 | **逐字节不动** |
| 其它（首页/about/quality/…） | 18 | **逐字节不动** |
| 合计 | 75 | |

> 上表 18 与 17 的差别：第 3 批的 75 页里 non-target 是 18 条（含 `/formulas/`、`/zh/formulas/` 两个归档页）。

---

## 5. 改后核验计划（沿用第 3 批的仪器，不新造门）

1. **本批基线**：新建 `_backup/b2d-step4-baselines/{base,new}`（**不覆盖**第 3 批基线），base = 改动前 75 页
2. **门 1 `ver inventory`**：若采纳 D1(b)/(c)（动 CSS）则预期 style 版本令牌 2.10.47 → 2.10.48 全 75 页；
   若采纳 D1(a) 则预期**无版本令牌变化**
3. **门 2 限定证明**：42 详情页在锚点窗口内 DIFF（预期 = h2 文本 + 少两张卡的字节）；
   剂型页 15 页 + 其它 18 页**必须逐字节未动**
4. **门 4 改造（本批的关键门）**：原"非循环校验"的数据源（卡片）被删 ⇒ **改用跨版本比对**：
   **旧基线的三卡值** → 比 **新页面的 ⑤ actives 段**（药丸 = Ingredients；行 = Guaranteed Analysis），要求 **42/42**。
   这比原门更强：一次性证明"数据没变、只是不再重复渲染"
5. **门 3 脚本标签**：仍恰好 42 详情页（本次不动入队）
6. **JSON-LD 逐页解析**：`additionalProperty` 三字段在新 HTML 里仍在（42/42）
7. **身份链** `b2d_s3_identity.py`（691 文件 0 不一致）
8. **快验** `b2d_s3_quickcheck.py` 12 项（图集行为不受影响，应收敛 PASS）
9. **浏览器**：详情页 1440 / 375 / zh 截图；确认 h2 文案与单卡视觉
10. **日志零新增**：`dev.zxpet.com-ssl-error.log` 仍 1494 B / mtime `2026-09-20 19:31:11`
11. **上线**：push → 云端 `pull --ff-only` → 仓库级 md5（1196 文件）+ 两侧 `git status` 干净

---

## 6. 待你决定（三个待定项）

### D1 — 删到只剩一张卡后的宽度
`.sf-fdetail__grid` 是 `repeat(auto-fit, minmax(280px, 1fr))`（`style.css:5795`）。
只剩 1 张卡时它会**拉满 1200px**，而值只有 39–56 字符（约 350px 宽）⇒ 右侧约 850px 空白。

| 选项 | 做法 | 连带 |
|---|---|---|
| **(a) 不动 CSS** | 接受横条 | **不需要** bump 版本（本次只改 PHP 输出） |
| (b) 收窄单卡 | `.sf-fdetail__grid { max-width: 560px; }` | 需 bump **2.10.48**（两处同步） |
| (c) 其它宽度 | 你给数字 | 同 (b) |

### D2 — zh 页 h2 文案
zh 页 h1 就是英文，所以 h2 会是 `A Closer Look at Ear Care Drops`（英文短语 + 英文配方名）。
现状 `Inside Our Drops Production` 同样纯英文 ⇒ 我建议**照改**；若你希望 zh 页保留原文案，
需要给 shortcode 引入语言分支（复杂度上升），**不建议**。

### D3 — ④ 段那个 `Specification` h2 标题
你只提了"删卡"，没提标题。我**默认不动**（仍是 `Specification`）。

---

## 7. 本次不做的事

- ❌ 不删/不改任何 post meta（`sf_formula_ingredients` / `analysis` / `specs` 原样保留）
- ❌ 不动 `templates/single-sf_formula.html`（一个字节都不改）
- ❌ 不动入队、不引入 JS 库 / CSS 框架
- ❌ 不动 ⑤⑥ 段、⑦ related、⑧ CTA
- ❌ 不动 `tools/b2d_s2_check.py`（第 2 批存档；它打印的那个 h2 属于**已撤除的剂型页图集**，
  该脚本随第 3 批的剂型页撤除即已失效，与本批无关）

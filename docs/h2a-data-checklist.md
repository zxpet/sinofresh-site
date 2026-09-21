# H2a 运营填数据清单 · H2a Data-Entry Checklist

> 批次 Batch H2a（配方详情页参数区）· 生成于 2026-09-22 ·
> 核验：21 条详情页实测（候选字节，`_backup/b2d-h2a-baselines/params-audit.json`）
>
> **一句话 / In one line:** 详情页右侧参数区已经上线；有数据就有行，没数据就没行。
> 填完**不需要发版**，刷新页面即可看到新行。
> The detail page's parameter list is live: a row appears the moment its field has
> a value. **No deploy needed** — save the record and reload the page.

---

## 0. 后台在哪里 / Where this is in the admin

| English | 中文 |
|---|---|
| WP Admin → **Formulas** → click a record ("Joint Support Soft Chews" …) | 后台 → **Formulas** → 点开任一条目 |
| The block editor opens. Scroll to the **bottom** of the page. | 打开区块编辑器，滚到页面**最底部**。 |
| A collapsed panel named **"Meta Boxes"** sits there — click it to expand. | 有一个默认折叠的面板 **"Meta Boxes"**，点开它。 |
| All publishing fields live inside it. The four fields in this checklist are in the **"Right-column Parameters"** box. | 表单字段全在里面。本清单的四个字段在 **"Right-column Parameters"** 组里。 |

> ⚠️ 面板折叠是 WordPress 的界面状态，不是数据缺失。看不到字段时先展开 "Meta Boxes"。
> The collapsed panel is a UI state, not missing data.

---

## 1. 字段规范 / Field specification

| 字段 / Field | 后台位置 / Admin location | 填写说明 / How to fill | 示例 / Example |
|---|---|---|---|
| **Flavors**（风味） | Formulas → *record* → Meta Boxes → **Right-column Parameters** → `Flavors` | 多选复选框。**可勾多个**，也可以只勾一个。选项来自该剂型自己的风味池（见 §2 附表）；池里没有的写 `Custom` 并由业务补充说明。 | 狗狗软咀嚼：勾 `Chicken` + `Peanut Butter` → 详情页显示两枚标签 `Chicken` `Peanut Butter` |
| **Suitable For**（适用对象） | 同上 → `Suitable for` | 多选复选框，**只有两个选项**：`Dog` / `Cat`。猫狗通用就两个都勾。 | 勾 `Dog` + `Cat` → 详情页显示 `Dog` `Cat` |
| **Life Stage**（生命阶段） | 同上 → `Life stage` | **单选**（圆点按钮），只能选一个：`Puppy` / `Kitten` / `Adult` / `Senior` / `All Life Stages`。全阶段产品选 `All Life Stages`。 | 选 `All Life Stages` → 详情页显示 `All Life Stages` |
| **Tier pricing**（阶梯价） | 同上 → `Tier pricing` | 两列表格：`Min quantity`（起订量）与 `Unit price (USD)`（单价，美元）。**点 "+ Add row" 加行**；整行留空的行在保存时会被自动丢弃，不会写入。 | 3 行：`500 / 4.20`、`1000 / 3.85`、`5000 / 3.30` |

> **空 = 不显示。** 字段留空时，详情页**整行不渲染**（不会出现空白或 `—`）。
> **Empty means the row is absent** — no blank lines, no dashes.

---

## 2. 21 条逐帖跟踪表 / Record-by-record tracker

**图例 / Legend**

- **现在行数 / rows now** —— 候选字节实测：今天这条详情页参数区实际渲染几行。
- **Flavor 池 / flavor pool** —— 按剂型分组，见下方 A–H。
- **S** = Suitable For：`Dog` / `Cat`（可多选）
- **L** = Life Stage：`Puppy` / `Kitten` / `Adult` / `Senior` / `All Life Stages`（单选）
- **T** = Tier pricing：`Min quantity` + `Unit price (USD)`，可有 0–N 行

**风味池 / Flavor pools**（勾选范围内；都不是的用 `Custom`）

| 组 | 剂型 Form | 风味池 Flavor pool |
|---|---|---|
| A | soft-chews 软咀嚼 | Chicken · Beef · Lamb · Salmon · Peanut Butter · Cheese · Mint · Sweet Potato · Pumpkin · Blueberry · Mixed · Unflavored · Custom |
| B | tablets 片剂 | Chicken · Beef · Cheese · Liver · Unflavored · Custom |
| C | powders 粉剂 | Unflavored · Chicken · Beef · Cheese · Fish · Custom |
| D | pastes 膏剂 | Liver · Chicken · Salmon · Unflavored · Cheese · Custom |
| E | drops 滴剂 | Unflavored · Chicken · Beef · Fish · Mint · Custom |
| F | liquids 液体 | Unflavored · Chicken · Beef · Fish · Liver · Custom |
| G | fish-oil 鱼油 | Salmon · Sardine · Anchovy · Cod · Fish Blend · Custom ★ |
| H | dental-chews 洁齿 | Mint · Chicken · Beef · Cheese · Seaweed · Unflavored · Custom |

★ fish-oil 的该字段在后台标签是 **"Source"（来源）** 而不是 "Flavor"——同一字段、同一位置，只是鱼油把"风味"表述为"鱼种来源"。

| ID | 剂型 Form | 标题 Title | 现在行数 rows now | Flavor | S | L | T | 状态 |
|---|---|---|---|---|---|---|---|---|
| 158 | soft-chews | Joint Support Soft Chews | 6 | ☐ | ☐ | ☐ | ☐ | 待填 |
| 159 | soft-chews | Calming Soft Chews | 6 | ☐ | ☐ | ☐ | ☐ | 待填 |
| 160 | soft-chews | Digestive Soft Chews | 6 | ☐ | ☐ | ☐ | ☐ | 待填 |
| 161 | soft-chews | Skin & Coat Soft Chews | 6 | ☐ | ☐ | ☐ | ☐ | 待填 |
| 162 | tablets | Joint Support Tablets | 6 | ☐ | ☐ | ☐ | ☐ | 待填 |
| 163 | tablets | Multivitamin Tablets | 6 | ☐ | ☐ | ☐ | ☐ | 待填 |
| 164 | tablets | Calcium & Phosphorus Tablets | 6 | ☐ | ☐ | ☐ | ☐ | 待填 |
| 165 | powders | Probiotic Powder | 5 | ☐ | ☐ | ☐ | ☐ | 待填 ⚠️ |
| 166 | powders | Pumpkin Digestive Powder | 5 | ☐ | ☐ | ☐ | ☐ | 待填 ⚠️ |
| 167 | powders | Bladder Support Powder | 5 | ☐ | ☐ | ☐ | ☐ | 待填 ⚠️ |
| 168 | pastes | Hairball Remedy Paste | 5 | ☐ | ☐ | ☐ | ☐ | 待填 ⚠️ |
| 169 | pastes | Nutrition Paste | 5 | ☐ | ☐ | ☐ | ☐ | 待填 ⚠️ |
| 170 | drops | Ear Care Drops | 5 | ☐ | ☐ | ☐ | ☐ | 待填 ⚠️ |
| 171 | drops | Urinary Care Drops | 5 | ☐ | ☐ | ☐ | ☐ | 待填 ⚠️ |
| 172 | liquids | Liquid Joint Support | 5 | ☐ | ☐ | ☐ | ☐ | 待填 ⚠️ |
| 173 | liquids | Liquid Skin & Coat | 5 | ☐ | ☐ | ☐ | ☐ | 待填 ⚠️ |
| 174 | fish-oil | Wild Alaskan Salmon Oil | 5 | ☐ (Source) | ☐ | ☐ | ☐ | 待填 ⚠️ |
| 175 | fish-oil | Pure Fish Oil Blend | 5 | ☐ (Source) | ☐ | ☐ | ☐ | 待填 ⚠️ |
| 176 | dental-chews | Plaque Control Dental Chews | 6 | ☐ | ☐ | ☐ | ☐ | 待填 |
| 177 | dental-chews | Oral Care Dental Sticks | 6 | ☐ | ☐ | ☐ | ☐ | 待填 |
| 178 | dental-chews | Natural Cleaning Dental Sticks | 6 | ☐ | ☐ | ☐ | ☐ | 待填 |

**合计 / Totals：** 21 条 × 4 键 = **84 个待填单元格**。
行数分档：**10 条 6 行**（软咀嚼 4 + 片剂 3 + 洁齿 3）· **11 条 5 行**（粉 3 + 膏 2 + 滴 2 + 液体 2 + 鱼油 2）。
填完 4 键后，每条最多可到 **9–10 行**（新增 Flavor / Suitable For / Life Stage / Quantity & Pricing 四行）。

---

## 3. ⚠️ 五个剂型必须补 "Piece Weight" / Piece Weight needs a real number

**问题 / The problem.** 详情页的 **Piece Weight** 行不是从后台字段读的，而是从
**Standard Specs**（`Standard Specs` 文本框）里**解析**出来的：它取 specs 里第一段
既不是货架期、也不含 "per" 的文字。以下五个剂型的 specs 第一段本身就是**包装规格**，
所以今天详情页把一个**整包/整瓶容量**显示成了 "Piece Weight"：

The Piece Weight row is **parsed out of the Standard Specs text**, not read from a
field. For five dosage forms the first spec segment *is* a packaging size, so the
page currently prints a pack volume under a per-piece label:

| ID | 剂型 Form | 今天 Piece Weight 显示 / today it shows | 实际是 / but it really is |
|---|---|---|---|
| 165–167 | powders | `4oz/8oz/16oz jar` | 罐装规格 jar sizes |
| 168–169 | pastes | `50g/60g/100g/120g tube` | 软管规格 tube sizes |
| 170–171 | drops | `30ml/50ml dropper bottle` | 滴瓶规格 bottle sizes |
| 172–173 | liquids | `8oz/16oz/32oz pump bottle` | 泵瓶规格 bottle sizes |
| 174–175 | fish-oil | `8oz/16oz/32oz pump bottle` | 泵瓶规格 bottle sizes |

（以上为候选字节实测原文，见 §5 附录。 / measured verbatim.)

**要做什么 / What to do.** 运营为这 11 条记录确认**真实的单件/单次用量重量**，
写成 specs 的第一段，用 `·` 分隔：

For each of these 11 records, confirm the **true per-unit / per-serving weight** and
make it the first segment of Standard Specs, segments separated by `·`:

```
现在 / now :  4oz/8oz/16oz jar · 24 months shelf life
改后 / then:  1g/scoop · 4oz/8oz/16oz jar · 24 months shelf life
```

| 剂型 Form | 建议的 Piece Weight 写法（示例） / suggested phrasing |
|---|---|
| powders | `1g/scoop` 或 `2g/scoop`（每勺克重） |
| pastes | `5g/dose` 或 `2g/kg body weight`（每次用量） |
| drops | `0.5ml/drop` 或 `1ml/dose`（每滴/每次毫升） |
| liquids | `2.5ml/dose` 或 `5ml/10kg body weight`（每次用量） |
| fish-oil | `200mg omega-3 per softgel` 或 `500mg/serving`（每粒/每次 omega-3） |

> 三件必须注意 / Three cautions
> 1. 只在第一段加"单件用量"，**不要把罐/管/瓶规格删掉** —— 删了 Packaging 行会失去依据。
> 2. 段落之间必须是 `·`（中点号）分隔，解析器按它切段。
> 3. 改完刷新详情页确认 Piece Weight 变成用量数字；Pack Size 行只在 specs 里出现
>    `… per …`（如 `60/90/120 per bottle`）时才渲染，上述剂型若要显示 Pack Size，
>    需要补一段 `per` 短语。
>
> 1. Add the per-unit segment, **keep** the jar/tube/bottle segment.
> 2. Segments must be joined by `·` — that is the parser's delimiter.
> 3. Reload the page to confirm; Pack Size only renders when a `… per …` segment exists.

---

## 4. 填完之后 / After filling

1. **保存 / Save** —— 区块编辑器右上角 `Save`。
   > 保存时若还有必填项为空，会出现橙色横幅 **"Backfill needed (phase 1 …)"**。
   > 这是**提示不是阻断**，保存照常生效；横幅列出还缺哪些字段。
   > The orange banner is a warning, never a block.
2. **刷新详情页 / Reload the detail page** —— 例：`https://dev.zxpet.com/formulas/probiotic-powder/`
   新填的行立即出现，**无需发版**。
3. **抽查一行 / Spot-check** —— 打开开发者工具看 `<dl class="sf-fdetail2__params">` 的
   `<dt>` 数量，应比填之前的行数多。

**自查表单 / Self-check**

| 检查 / Check | 期望 / Expect |
|---|---|
| 详情页出现 `Flavor` 行 | 勾了几个风味就出现几枚标签 |
| 详情页出现 `Suitable For` 行 | `Dog` / `Cat` 标签 |
| 详情页出现 `Life Stage` 行 | 单个文字值 |
| 详情页出现 `Quantity & Pricing` 行 | 两列小表（起订量 / 单价） |
| 未填的字段 | 对应行**完全不出现**（不是空白） |

---

## 5. 附录 / Appendix

### 5.1 一条记录今天实际渲染的参数行（实测）

| 记录 / Record | 行数 | 渲染出的行 / rows rendered |
|---|---|---|
| 158–164（软咀嚼、片剂） | 6 | Piece Weight · Pack Size · Shelf life · Packaging · Certifications · Lead time |
| 165–175（粉/膏/滴/液体/鱼油） | 5 | Piece Weight · Shelf life · Packaging · Certifications · Lead time |
| 176–178（洁齿） | 6 | Piece Weight · Pack Size · Shelf life · Packaging · Certifications · Lead time |

Flavor / Suitable For / Life Stage / Quantity & Pricing **四行全部缺失** —— 就是本清单要补的四项。

### 5.2 同一表单里的其它必填项（不在本清单范围）

后台的 "Backfill needed" 横幅还会列出：`Featured image (main photo)`（主图）、
`Weight per piece`、`Pack counts`、`Shape`、`Recommended For`、`Use Cases`、`Who It's For`。

⚠️ 注意 / Note：这些字段目前**不驱动任何前台行**（例如 `Weight per piece` 后台字段
与详情页的 Piece Weight 行不是同一个来源 —— 后者解析自 Standard Specs，见 §3）。
运营可按品牌方需要逐步补齐，但它们**不会**改变详情页的显示。

These fields do not drive a front-end row today; filling them is still worth doing
for record-keeping, but it will not change the detail page.

### 5.3 数据出处 / Provenance

- 逐帖行数与解析值：`_backup/b2d-h2a-baselines/params-audit.json`（21 页候选字节实测）
- 选项池来源：`sinofresh-theme/inc/formula-pools.php`（H1 冻结，与 8 个剂型页配置器同源）
- 渲染实现：`sinofresh-theme/functions.php` → `sinofresh_formula_params()`

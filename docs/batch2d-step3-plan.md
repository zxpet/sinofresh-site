# 批次 2D 第 3 批 —— 方案（待确认）

> 事实依据全部来自 `docs/batch2d-step3-scan.md`。**本文只是方案，未改任何文件。**
> 目标：图集从 8 个剂型页**搬到** 21 条配方详情页，详情页新增 3 个模块。

---

## 一、撤掉剂型页图集（8 页）

### 做法

逐页删除第 30–37 行那 10 行（`\n\n<!-- B2D-S2: gallery -->\n…<!-- /wp:group -->\n` → `\n`），
即恢复成图集插入前的字节序列。

| 保留 | 撤除 |
|---|---|
| `assets/js/formula-gallery.js`（内容不动，版本仍 `1.0.0`） | 8 个模板里的 `sf-gallery` 段（各 10 行） |
| `style.css` 的 `.sf-gallery` 段（7965–8080，116 行） | 8 页的 `#gallery` 锚点 |
| `[sf_formula_gallery]` 短代码 | 8 剂型页上对 `formula-gallery.js` 的入队 |

### 证明（最强）

```
git diff cfbd5e4 -- sinofresh-theme/templates/page-*.html   →  必须输出为空
```

8 页与"图集之前"**逐字节相同**，由 git 直接背书，不需要掩码或截图。
（前提：`cfbd5e4` 之后这 8 个模板只被图集改过——已核，`+10 / −0`。）

### ⚠ 唯一的连带影响：入队迁移

`functions.php:182-189` 目前把 `formula-gallery.js` 入队到 `$is_dosage_page`。
本批要把它**移到 `is_singular('sf_formula')`**（否则详情页拿到 JS、8 剂型页白拿一份死重量）。

⇒ 8 个剂型页（+8 个 zh）的**资源集合发生变化**，掩码门**必然**报 DIFF。
这**不是回归**，必须配资源清单报告证明"只少了 `formula-gallery.js` 一个"（见 §五）。

---

## 二、配方详情页的模块顺序

`templates/single-sf_formula.html`（**一份模板服务全部 21 条**）。

| # | 模块 | 现状 | 本批动作 |
|---|---|---|---|
| ① | 面包屑 Hero | 已有 | **不动**（且必须继续是第一个元素，`style.css:1856` 依赖它） |
| ② | **轮播图集**（主图 + 4 缩略图） | 无 | **新增**：抄 2D-S2 的容器块，内容 `[sf_formula_gallery]` |
| ③ | 产品详细介绍（`[sf_formula_body]`） | 已有，但在 ④ **之后** | **移位**到 ④ 之前（不删、不改内容） |
| ④ | Specification 3 字段卡（`[sf_formula_detail]`） | 已有 | **不动** |
| ⑤ | **Formula & nutrition**（活性成分 + 保证值） | 无 | **新增**：`[sf_formula_detail_actives]` |
| ⑥ | **Ingredients & composition**（原料与配料） | 无 | **新增**：`[sf_formula_detail_composition]` |
| ⑦ | More {Form} Formulas（`[sf_formula_grid limit="4"]`） | 已有 | **不动** |
| ⑧ | CTA band | 已有 | **不动** |

### ② 轮播图集

- **容器＝2D-S2 那个块的原样复用**（`anchor:"gallery"` + `className:"sf-gallery"` +
  `backgroundColor:"bg-light"` + spacing 80/80），因为 **JS 靠 `querySelectorAll('.sf-gallery')` 找 root**
  （`formula-gallery.js:178`），不挂这个类缩略图条就不会生成。
- 短代码：**`[sf_formula_gallery]`（无参数）**。
  - ⛔ **不能写死 slug**：这份模板 21 条共用，写 `formula="joint-support-soft-chews"` 会在其余 20 页错。
  - ⛔ **派生的现有实现已经正确**：`sinofresh_formula_current_form('')` 在 `is_singular('sf_formula')` 上
    会从 taxonomy `sf_formula_form` 取出剂型 slug，槽 1 = `{剂型}.webp`。
  - ⇒ 你方案里的 `formula="{slug}"`／"读 post meta 获取剂型"两条**不成立**（剂型是 taxonomy），
    但**结果一样**，且不需要新短代码。若你仍想要 `[sf_formula_detail_gallery]` 这个名字，
    我可以加一个 3 行包装层，**默认推荐不加**。
- h2 文案沿用 `Inside Our {Label} Production`（零新字符串；对 "Joint Support Soft Chews" 页
  读作 "Inside Our Soft Chews Production"，与图集内容一致）。
- `alt` 沿用既有写法（含剂型关键词），首图 `eager`、其余 `lazy`，无 `fetchpriority="high"`。

### ③ 产品详细介绍

⛔ **今天它是空的**：`[sf_formula_body]` 读 `post_content`，实测 **21/21 = 0 字节**
⇒ 移位后不产生任何输出（已在线上复现）。数据出现只能靠后台补正文，
但 `post_content` **不受 authority guard 影响、后台可编辑**，所以这条是"留给运营"的合理设计。
**本批只做移位，不造数据。**

### ④ 不动

### ⑤ 与 ⑥

**共同形态**：短代码**自己吐出整个 `<section>`**（`<h2>` 也在短代码里），
空数据返回 `''` ⇒ **零字节、零空带、零孤儿标题**。
这是 `.sf-fdetail-body`（`style.css:5835` `padding:48px 0; background:card-white`）已经走通的范式。

**⑤ `[sf_formula_detail_actives]`**

| 项 | 值 |
|---|---|
| 数据 | `sf_formula_ingredients`（21/21）+ `sf_formula_analysis`（21/21）⇒ **今日即可见** |
| 解析 | **复用** `sinofresh_formula_split_top_level()`（`:940`）+ `sinofresh_formula_analysis_pairs()`（`:978`），**零新解析逻辑** |
| 成分 | `ul.sf-actives__ing > li.sf-actives__pill`（药丸，复用既有 CSS） |
| 保证值 | `dl.sf-spec-list > div.sf-spec-row > dt.sf-spec-term + dd.sf-spec-value`（复用既有 CSS） |
| 标题 | `<h2>Formula & nutrition</h2>` |
| 底色 | `card-white`（`#FFFFFF`），`padding: 48px 0` —— 与 ④ 同色，读作同一片"配方数据区"，各自有 H2 分隔 |
| 不输出 | K1 按钮 / K2 JSON 镜像 / ItemList / 额外 JSON-LD（页面已有 Product schema，重复只会污染） |
| 空 | 两者皆空 ⇒ `''` |

**⑥ `[sf_formula_detail_composition]`**

| 项 | 值 |
|---|---|
| 数据 | ⛔ **不存在**：`sf_formula_base` / `sf_formula_other_ingredients` / `sf_formula_composition` 全部 `present=0` |
| 标题 | `<h2>Ingredients &amp; composition</h2>` |
| 结构 | 2 行 `<dl>`：`Base` / `Other ingredients`，只渲染非空的 |
| 底色 | `card-white`，`padding: 48px 0` |
| 今日 | **无字段值 ⇒ 输出空字符串**，页面上完全不可见（符合"整块隐藏"） |
| 配套 | `functions.php:439` 的 `register_post_meta` 循环**新增这 2 个键**（`show_in_rest`）⇒ 后台可编辑 |

> ⚠️ **不要**拿 `sf_formula_ingredients` 去填 ⑥：它是**自由文本**，且在 `Ear Care Drops` 上是活性物清单、
> 在 `Hairball Remedy Paste` 上是带百分比的配料表——语义逐条不等；而且它**已被 ④ 和 ⑤ 消费**，
> 再用一次会在同一页把同一串印三遍。

### ③ / ⑤ / ⑥ 的页面底色（推荐值）

```
① 深绿#2E6B54 │ ② 浅灰#F3F6F4 │ ③ 白 │ ④ 白 │ ⑤ 白 │ ⑥ 白 │ ⑦ 浅灰 │ ⑧ 深绿
```
今天 ③⑥ 为空 ⇒ `深绿 │ 浅灰 │ 白(④+⑤) │ 浅灰(⑦) │ 深绿`，干净的交替，无相邻同色。
（把 ④⑤⑥ 做成连续白色是**有意的**：它们是同一件事——"这条配方的数据"。）

---

## 三、要动的文件（预计 14 个）

| 文件 | 改动 |
|---|---|
| `templates/page-{8 个剂型}.html` | 各 **−10 行**（撤图集） |
| `templates/single-sf_formula.html` | **+2 块**（② 图集、⑤⑥ 短代码位）、**移位 1 块**（③） |
| `functions.php` | ① 入队迁到 `is_singular('sf_formula')`；② 新增 2 个短代码；③ `register_post_meta` 加 2 个键；④ `:26` 版本 `2.10.46→2.10.47` |
| `style.css` | 末尾追加 ⑤⑥ 两段新 CSS；`style.css:5` 版本同步 `2.10.47` |
| `assets/js/formula-gallery.js` | **不动**（版本保持 `1.0.0`） |

### CSS 纪律

- 新类名走新前缀 `.sf-fdetail-actives*` / `.sf-fdetail-comp*`；
- **不新增 `:has(`**（保持 `163 / 7 / 170` 不变量）；
- **不新增 `!important` 声明**（`.sf-gallery` 段至今 0 条，保持）；
- 断点沿用主题惯例：`@media (max-width:1240px)` 补 38px 内边距、`@media (max-width:768px)` 20px；
- 不复用 `sf-spec-term` / `sf-spec-value` 作**新**样式钩子（K6 盲区，2D-S1 已立规矩）——
  这里是用**既有**的 `.sf-spec-*` 产出表格，属于既有契约，不是新借用。

### 区块纪律

- 自闭合一律 ` /-->`（交付内容 `grep "/ -->"` 零残留）；
- 新注释保持短（注释会输出到页面源码）；
- 新增块是**容器块**或 `wp:html`，不影响 8 剂型页的自闭合计数（各 3 个）。

---

## 四、回归门（沿用已固化的两把锁 + 三项配套）

| # | 门 | 期望 |
|---|---|---|
| 1 | **git 逐字节**：`git diff cfbd5e4 -- templates/page-*.html` | **输出为空**（8 页撤除的最强证明） |
| 2 | **限定证明**（marker-driven） | 21/21 详情页"删新块后与基线逐字节相同"；其余页 `identical` |
| 3 | **掩码回归** `tools/sf_masked_cmp.py` | 先 `--aa` 自检（挑最易假阳性的页：`/services/`、`/formulas/`、`/products/soft-chews/`），**必带 `-u`** |
| 4 | **ver 归一化** `tools/b2d_s2_norm.py` | 只折 `?ver=`，**不删属性** |
| 5 | **资源清单** `tools/b2c_s2_ver_inventory.py` | 8 剂型页(+zh) **只少** `formula-gallery.js`；21 详情页(+zh) **只有** `formula-gallery.js` 新增；`style.css` ver 全站 `2.10.46→2.10.47` |
| 6 | **JSON-LD deep-equal** | 21 条详情页的 `Product`（由 `functions.php:3232` 读 **post meta** 生成）+ `BreadcrumbList` + `Organization` + `ItemList` **逐字节不变**（本批不碰 meta 值） |
| 7 | **浏览器 E2E** | 详情页缩略图 4 格、点击切换、键盘 `←/→/Home/End`、滑动方向、无 JS 主图可见、375/768 缩略图条 `scroll-snap`、小屏横向溢出 = 0 |
| 8 | **工作区↔云端 md5** | 逐文件全等（`site-repo` 是软链目标） |

### 页面清单要从 47 扩到 **75**

现清单：15 普通页 + **8/8** EN 剂型 + **21/21** EN 详情 + **3** zh。
本批改动面正是 8+21，**zh 侧同模板同输出**，实测 `/zh/products/{8}/` **8/8 = 200**、
`/zh/formulas/{21}/` **21/21 = 200** ⇒ 补 7 个 zh 剂型 + 21 个 zh 详情 = **75 页**。

### 时间窗纪律

掩码基线受 WP nonce 12h 窗影响（边界 UTC 00:00 / 12:00 = CST 08:00 / 20:00；
现在 CST 00:3x，距下一次边界约 7.5 h）。若跨过边界，A/B 两侧的 `nonce=` 与
`config_nonce` 会翻窗 ⇒ 必须在同一 tick 内完成 A/B，否则用已补两种掩码的 `t22_render_cmp.py`。

---

## 五、执行顺序（确认后按此跑，逐节停下报告）

```
第 0 步  拆上一批预检脚手架（b2d_s1_preflight.py remove）
         复验：匿名 401 / www 302 / 带凭据 200；mu-plugins 与 themes 目录回到干净态
第 1 步  备份（_backup/b2d-step3-<ts>/，含 10 个模板 + functions.php + style.css + MANIFEST.md）
第 2 步  撤 8 剂型页图集 + 入队迁移 + 版本号
         门：git diff cfbd5e4 == 空；入队迁移后抓一次基线
第 3 步  详情页 ② 图集 + ③ 移位 + ⑤⑥ 短代码 + CSS
         门：限定证明 21/21；掩码回归；资源清单；JSON-LD deep-equal
第 4 步  浏览器 E2E（桌面 1440 / 1280×700 / 768 / 375，含 zh）
第 5 步  文档 + 取证截图（docs/batch2d-step3.md、docs/b2d-step3-shots/）→ 停下汇报
```

---

## 六、⚠ 需要你拍板的 6 件事

| # | 问题 | 我的建议 |
|---|---|---|
| **D1** | ③ 要把既有的 `[sf_formula_body]` 块从 ④ **之后**移到 ④ **之前**（你的顺序如此）。这是**移位**，不删内容 | ✅ 照你的顺序移（4 行 relocate，`git diff` 可审） |
| **D2** | ② 的短代码：用**无参** `[sf_formula_gallery]`，还是新建 `[sf_formula_detail_gallery formula="…"]` | ✅ **无参复用**（一份模板服务 21 条，写死 slug 必错） |
| **D3** | ⑤ 与 ④ **信息重叠**：④ 的 3 张卡已含 Ingredients / Guaranteed Analysis 的**纯文本**，⑤ 是同一份数据的**药丸+表格**版，同页先后出现 | ✅ 先都保留，看预览再定；若要收窄，④ 只留 `Standard Specs` |
| **D4** | ⑥ **无数据**（3 个候选 meta 全 `present=0`）。建字段+短代码+插块（今日输出空，等运营填）／还是本批不建 | ✅ **建字段 + 短代码 + 插块**，今日零输出，后台可编辑 |
| **D5** | 底色：我按 `② 浅灰 → ③④⑤⑥ 白 → ⑦ 浅灰` 排（今日 ③⑥ 空 ⇒ 白区 = ④+⑤） | ✅ 用这个；若要 ⑤ 走浅灰、⑥ 走白也可以，我按你定的改 |
| **D6** | 回归门清单从 47 扩到 **75**（补 7 zh 剂型 + 21 zh 详情，实测全 200） | ✅ 扩（本批改的就是这两个模板族） |

---

## 七、已知遗留（本批不做，记录在案）

- ⑤⑥ 的英文文案是**新 TP 字符串**，`/zh/` 会显示英文，随实拍替换批次一起重收录（同 2D-S1/S2）。
- 图集槽 2–4 仍是 `fac-*` 占位图、全库 34 张带 AI 水印 ⇒ **实拍替换＝上线阻塞项**，本批只验几何/间距。
- 槽 1 是**剂型**图（`{剂型}.webp`），不是该配方自己的照片——全库没有每配方独立产品图。

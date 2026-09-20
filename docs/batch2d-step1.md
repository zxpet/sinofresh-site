# 批次 2D · 第 1 批 —— 活性成分 + 保证值表（八剂型页）

> 状态：**已实施、已上云、12 项回归全绿**。commit **`58e24eb`**，云端 `site-repo` 已到该 commit 且 `git status` 干净。
> 方案（实施前）见 `docs/batch2d-step1-plan.md`；取证图 `docs/b2d-step1-shots/`。
> **下一步停在此处等你确认后再进第 2 批（图集）。**

---

## 0. 一句话结果

给八个剂型页在「典型规格表」与「How We Work」之间插了一段服务端渲染的
**Active Ingredients & Guaranteed Analysis**，数据直读 21 条 `sf_formula` 的既有 post meta，
每个剂型页列出该剂型的全部标准配方（成分药丸 + 保证值表）。

- **10 个文件**：`functions.php`（+191/−1）、`style.css`（+56/−1）、8 个模板（各 +9 行）
- 线上实测：`/products/soft-chews/` 177 110 B（原 173 420 B，**+3 690 B**），`#actives` 段 3 674 B
- **限定证明：9/9 带新块的页面删掉新块后与基线逐字节相同；38/38 不带新块的页面本来就逐字节相同（47/47）**
  ⇒ 除新块之外，卡数/卡序/JSON-LD/入队/markup/空白**一个字节都没动**
- 浏览器 30/30、数据层 46/46、掩码回归 38/47 SAME（9 个 DIFF 全部＝带新块的页面）、入队清单 1 项变化（只有 style.css 版本）
- 工作区 ↔ 云端逐文件 md5 **342/342 全等**

---

## 1. 交付物

| 文件 | 变化 | 现值 |
|---|---|---|
| `sinofresh-theme/functions.php` | +191 / −1 | 156 120 B，`sha256 120690d50ff9682a…` |
| `sinofresh-theme/style.css` | +56 / −1（55 行新增 + Version 行） | 250 582 B，`sha256 599fd2f0e1fad531…` |
| `templates/page-soft-chews.html` | +9 行 | 55 186 B |
| `templates/page-tablets.html` | +9 行 | 46 874 B |
| `templates/page-powders.html` | +9 行 | 46 326 B |
| `templates/page-pastes.html` | +9 行 | 44 411 B |
| `templates/page-drops.html` | +9 行 | 44 822 B |
| `templates/page-liquids.html` | +9 行 | 45 167 B |
| `templates/page-fish-oil.html` | +9 行 | 46 656 B |
| `templates/page-dental-chews.html` | +9 行 | 49 623 B |

合计 `10 files changed, 319 insertions(+), 2 deletions(-)`。

**工具（本批新增，均在仓库根 `tools/`）**

| 工具 | 作用 |
|---|---|
| `b2d_s1_apply.py` | 幂等改写器：`--check` 干跑 / `--apply` 落盘；每步 assert 前置条件并在写后回读 |
| `b2d_s1_preflight.py` | 云端预检脚手架：`install <commit>` / `remove` / `status` |
| `b2d_s1_preflight_mu.php` | 头门 mu-plugin 源（上传件，**不入主题树**） |
| `b2d_s1_confine.py` | **限定证明**：从候选页删掉新块后与基线逐字节比 |
| `b2d_s1_check.py` | 数据层回归（JSON-LD / K2 / 渲染计数） |
| `b2d_s1_browser.py` | 浏览器回归（点轨 / 配置器 / 375 / zh） |
| `sf_masked_cmp.py` | 掩码比对门 —— 本批**新增 `--user` 与 GF 电话控件掩码**（见 §6） |

---

## 2. 实施内容（逐字节可核对）

### 2.1 `functions.php`

插入点在 `add_shortcode('sf_formula_grid', 'sinofresh_formula_grid');`（原第 918 行）之后，
即紧接同侪配方短代码，不插在文件其它位置。新增：

- `sinofresh_formula_split_top_level($value)` —— 按**顶层逗号**切分（括号内逗号不切）
- `sinofresh_formula_analysis_pairs($value)` —— 按**第一个 U+2265（≥）**切成 term/value
- `sinofresh_formula_actives($atts)` + `add_shortcode('sf_formula_actives', …)`

两个纯函数与 `tools/b2d1_parser_dryrun.php` 里的固件**逐字节相同**——`b2d_s1_apply.py`
在写入前会从两边各抽一次函数体做等值断言，防止日后单侧漂移。

短代码要点：

- 查询参数与 `[sf_formula_grid]` **严格同形**：`post_type=sf_formula`、`post_status=publish`、
  `posts_per_page=-1`、`orderby=['menu_order'=>'ASC','title'=>'ASC']`、
  `ignore_sticky_posts`、`no_found_rows`、`tax_query(sf_formula_form=$form)`。
  ⇒ 同一配方在表格里的位次与它在上方网格里的卡位一致。
- 名字先 `html_entity_decode(get_the_title())` 再按上下文 `esc_html()`（与网格同一套单一权威写法）；
  `Skin & Coat Soft Chews` 这类实体编码标题不会双重转义。
- 无成分且无保证值 → 跳过该条；整体为空 → **返回 `''`**，段落整体塌陷（与 `sf_formula_body` 同约定）。
- **不输出** K2 副本、**不输出** ItemList JSON-LD。

### 2.2 八个模板

插入锚点（8 页同字节、各命中 1 次，`sha256[:16] = e2c5d61e6997f0d3`，58 B）：

```
</table>
<!-- /wp:html -->
</section>
<!-- /wp:group -->

```

插入段 8 行 + 1 空行，唯一逐页差异是 `form="…"`：

```
<!-- B2D-S1: actives -->
<!-- wp:group {"tagName":"section","anchor":"actives","className":"sf-actives","layout":{"type":"constrained"},"style":{"spacing":{"padding":{"top":"var:preset|spacing|80","bottom":"var:preset|spacing|80"}}}} -->
<section id="actives" class="wp-block-group sf-actives" style="padding-top:var(--wp--preset--spacing--80);padding-bottom:var(--wp--preset--spacing--80)">
<!-- wp:html -->
[sf_formula_actives form="soft-chews"]
<!-- /wp:html -->
</section>
<!-- /wp:group -->
```

- 容器注释与 `<section>` 开标签是**块② `#formulas` 的原样序列化**，只把 `formulas`→`actives`、
  `sf-formulas`→`sf-actives`。`b2d_s1_apply.py` 在写前会从同一页里抽出块② 的两行做替换后等值断言，
  所以这不是"我手写的另一种写法"，而是 Site Editor 反复保存过的同一种。
- 新块是容器块，**不产生自闭合**，` /-->` 纪律不受影响（8 页自闭合块仍各 3 个，`grep -E '"/ -->"'` 全仓 0）。
- 注释写成短标记 `<!-- B2D-S1: actives -->`，**会输出到页面源码**（与既有 `<!-- Block 9 … -->` 同族），
  同时给回归归一化脚本一个稳定锚点。
- 不重排既有块注释编号（现值 `2/4/9/10/11/12` 与实际序号不符，属历史残留，重排只会制造大 diff）。

### 2.3 `style.css` —— 追加 55 行（14 行是解释性注释，实际声明 41 行）

- `.sf-actives__title / __intro / __list / __item + __item / __name / __label`
- 药丸 `.sf-actives__ing` + `.sf-actives__pill`：**outline 圆角 999px + border-light**，
  沿用站内既有的 `.sf-topbar-badges` certificate pill 词汇。**刻意不复用 `.sf-fchip`**
  （那个类带 `cursor:pointer` 与 hover/`.is-active` 态，是筛选按钮的语义，用在静态名词上是错误的可供性）。
- `dl` 归零 2 条：`.sf-actives .sf-spec-list { margin: 10px 0 0 }` +
  `.sf-actives .sf-spec-term, .sf-actives .sf-spec-value { margin: 0 }`
  （`<dl>` 有 UA 默认 `margin-block:1em`，`<dd>` 有 `margin-inline-start:40px`，`.sf-spec-list` 只覆盖了 `margin-top`）
- **刻意不加 `@media` 断点**：28/10/16px 这些值在 375 下本来就成立，加一层响应式只会多一处需要回归的变量。
- 保证值表复用站内既有的紧凑 `.sf-spec-list`（`grid-template-columns:38% 1fr`），
  这里换用 `<dt>/<dd>`：**是 term/value 唯一正确的语义**，且 K6 解析器的正则要求
  `<span class="sf-spec-term">…</span><span class="sf-spec-value">…</span>`（两 span 间零空白），`<dt>` 天然不匹配。

### 2.4 版本号

| 文件 | 行 | 2.10.44 → 2.10.45 |
|---|---|---|
| `functions.php` | 26 | `wp_enqueue_style('sinofresh-style', …, '2.10.45')` |
| `style.css` | 5 | `Version: 2.10.45` |

全仓仅此 2 处出现版本号（已核；`b2d_s1_apply.py` 断言各恰好 1 次）。

---

## 3. 与批准方案的一处**主动偏离**（导语文案）

方案 §2.1 里我把导语示例写成了
`Every Soft Chews recipe in our standard range, …`，并注明"按 `sinofresh_formula_label($form)` 拼"。
实施时改成了：

```
Every formula in our standard {Label} range, with the ingredient list and the guaranteed
analysis we hold to in production. Use one as a starting point, or ask us to adjust the
actives and the levels for your own label.
```

**原因**：`Label` 取的是剂型页标题，八个值是 `Soft Chews / Tablets / Powders / Pastes / Drops /
Liquids / Fish Oil / Dental Chews` —— 全是复数。"Every Soft Chews recipe" 读得通，
但 "Every **Powders** recipe" / "Every **Drops** recipe" / "Every **Pastes** recipe" 四个页面的语法是错的。
把 Label 放到名词后面当定语（`every formula in our standard Powders range`）八个页面全部成立。

这是**唯一**一处偏离批准稿的地方，只动了一句文案，结构/选择器/回归判据一字未改。

---

## 4. 12 项回归 —— 逐项判据与实测

### 1) PHP 语法 ✅
`php -l functions.php` → `No syntax errors detected`。（另：插入前先把新增段单独 `php -l` 过了一遍。）

### 2) 块配平 × 8 ✅
`tools/b2c_s2_block_lint.py` → **8/8 PASS**，"block delimiters and HTML tags balanced, no malformed self-close"。
自闭合块各 3 个（与改前同），`grep -E '"/ -->"'` 全模板 **0**。

### 3) 新块 8 页同构 ✅
抽出 `<!-- B2D-S1: actives -->` → `<!-- Block 9: How We Work -->` 段，把 `form="…"` 归一后算 md5：
**8 页全部 `e54e6366049a001e`**（段长 492–499 B，差异全在 form 值）。

### 4) 掩码字节回归 ✅ 38/47 SAME（9 个 DIFF 全部＝预期）
预检 A/B 两趟（基线 `c0308af` vs 候选 `58e24eb`，**同一副本目录名**，均带门 + 带认证 + `--bust`），
经 `b2c_s2_norm_attrs.py` 归一 → `sf_masked_cmp.py`。**先跑 A/A 自检**。

| DIFF 的 9 页 | 说明 |
|---|---|
| `products-soft-chews / tablets / powders / pastes / drops / liquids / fish-oil / dental-chews` | 8 个剂型页，预期 |
| `zh-products-soft-chews` | 同一模板的 zh 版本，同一段新块，预期 |

其余 38 页（首页、`/formulas/`、21 个配方详情、`/zh/`、`/zh/formulas/`、about/quality/blog/contact/faq/services/cooperation/factory-tour/products/privacy/terms/cookie-policy/feedback）
**逐字节相同**。

### 5) 限定证明（纯加法最强证明）✅ **47/47**
`tools/b2d_s1_confine.py`：从候选页里**只删** `<!-- B2D-S1: actives -->` → 对应 `<!-- Block 9 … -->`
之间的那一段（含其后的空行），归一 `?ver=` 后与基线逐字节比。

```
pages carrying the band:    9/9  confined
pages without the band:    38/38 identical
PASS  confinement proof: 47/47 pages identical after removing the band
```

被删段长：soft-chews 3 674 B / tablets 3 002 / fish-oil 2 259 / liquids 2 319 / powders 2 270 /
pastes 2 024 / drops 1 662 / dental-chews 2 712 / zh-soft-chews 3 674。

**这一步同时是 SEO 数据层的证明**：卡序、JSON-LD、入队清单、markup 全部在新块之外，
逐字节相同就意味着它们没有被动过。

### 6) 入队资源清单 ✅
`tools/b2c_s2_ver_inventory.py A B` → **只有 `style.css` `2.10.44 → 2.10.45`（47 页）**；
`asset set identical on every page`（没有任何脚本/样式新增或消失）。

### 7) JSON-LD 单独核验 ✅ **46/46 中的 JSON-LD 部分全 PASS**
47 页全部 `<script type="application/ld+json">` 解析成对象后**双向 deep-equal**（A == B）。
`@type` 清单：`BreadcrumbList ×45 / FAQPage ×18 / ItemList ×32 / Organization ×47 / Product ×30 / Service ×1`。

八剂型页 Product schema 的**实测四元组**（每页都一样）：

| 观测项 | 值 | 含义 |
|---|---|---|
| `Product` 块数 | 1 | 未新增第二个 Product |
| 含 `additionalProperty` | **False** | **仍然缺失**（本批没有任何 schema 污染） |
| 页面里有 `class="sf-spec-term"` | True | 来自新块的 `<dt class="sf-spec-term">` |
| 页面里有 `<span class="sf-spec-term">` | **False** | 解析器要求的精确模式仍然不存在 |
| 模板文件里有 `sf-spec-term` | **False** | 解析器读的是 `templates/page-*.html`，那里根本没有这个字符串 |

⇒ **双重保险都成立**：① 解析器读磁盘模板，模板里只有一行短代码；② 即便改读渲染结果，它要的是 `<span>`，
而新块产出的是 `<dt>`。

### 8) K2 不受影响 ✅
`.sf-formulas-data` 解析后逐值比对 **A == B 全等**；条数 4/3/3/2/2/2/2/3（合计 21）；
每条 `sections` 恰好 3 组 `{label,value}` 且标签为 `Ingredients / Guaranteed Analysis / Standard Specs`、值全非空。

### 9) 新块渲染计数 ✅ 与干跑预测逐页相符

| 页面 | items | pills | analysis rows | 预期 |
|---|---|---|---|---|
| soft-chews | 4 | 24 | 8 | 4/24/8 ✅ |
| tablets | 3 | 18 | 7 | 3/18/7 ✅ |
| powders | 3 | 10 | 3 | 3/10/3 ✅ |
| pastes | 2 | 9 | 4 | 2/9/4 ✅ |
| drops | 2 | 6 | 2 | 2/6/2 ✅ |
| liquids | 2 | 11 | 6 | 2/11/6 ✅ |
| fish-oil | 2 | 6 | 8 | 2/6/8 ✅ |
| dental-chews | 3 | 15 | 5 | 3/15/5 ✅ |
| zh/soft-chews | 4 | 24 | 8 | 同 soft-chews ✅ |

合计 99 pills / 43 rows（与干跑一致）。另核：**无空 `<li>` / 无空 `<dd>`**，每个药丸与每个值都带文本。

### 10) 配置器不回归 ✅ 浏览器实测

| 检查 | 结果 |
|---|---|
| `.sf-formula__cta` 数量 | 4 ✅（与改前同） |
| 点第一个 → `sessionStorage['sinofresh_formula_soft-chews']` | `"Joint Support Soft Chews"` ✅ |
| toast 文案 | `"Formula name copied. Paste it in your inquiry."` ✅ |
| 点 Shape 组一个选项 → `.configurator__summary-row[data-group="shape"]` | `"Bone"` ✅ |
| `.configurator__item.is-selected` | 1 ✅ |
| `sessionStorage['sinofresh_config_soft-chews']` | `{"shape":"Bone","color":"","flavor":"",…}` ✅ |

### 11) toc-nav 点轨 ✅ 浏览器实测（6 → 7，新项第 3 位）

```
rail: #sf-sec-0 Standard Formulas
      #sf-sec-1 Build Your Soft Chews Formula
      #sf-sec-2 Active Ingredients & Guaranteed Analysis   ← 新
      #sf-sec-3 How We Work
      #sf-sec-4 Frequently Asked Questions
      #sf-sec-5 Related Dosage Forms
      #sf-sec-6 Request a Soft Chews Quote
```

- 点轨项数 **6 → 7**，新项在**第 3 位**，`href="#sf-sec-2"`
- `#sf-sec-2` 的文本确实就是新块的 H2；`#actives` 段 class 含 `sf-actives`
- **七项逐一点击全部落位**（点击后该 H2 距顶 96px，落在 97px 顶栏线附近；hash 同步更新）
- `#formulas / #configurator / #inquiry-form` 三个锚点仍在
- 页面无 `<main>` ⇒ 脚本回落 `document.body`，但 header/footer 里没有 H2，计数恰好 7

### 12) 响应式 + i18n + 图片 ✅

| 检查 | 结果 |
|---|---|
| 375×812 `scrollWidth vs clientWidth` | 375 / 375 → **无横向滚动** ✅ |
| 375 下新块计数 | 4 / 24 / 8 ✅ |
| 药丸换行 | 首条配方 24 个药丸占 **23 行**（每个几乎独占一行，说明 flex-wrap 正常且没有横向溢出） ✅ |
| `/zh/products/soft-chews/` | 200，`lang="zh-CN"`，新块渲染 4 条，标题英文原文（本批**不补 TP 串**，与方案一致） ✅ |
| 本批是否碰图片 | **完全不碰**（一条 `<img>` 都没动） ✅ |
| console / page errors | 无 error（仅 JQMIGRATE 提示日志） ✅ |

### 附：工作区 ↔ 云端 ✅
`find | md5sum` 双向比对（排除 `_backup/` 与 `.DS_Store`）：**本地 342 个 / 云端 342 个，仅本地 0 / 仅云端 0 / 内容不同 0**。
预检副本与线上主题的 `functions.php`、`style.css`、8 个模板 `sha256` **逐文件相同** ⇒ B 趟的渲染就是线上渲染，
限定证明可以直接转移到线上。拆除预检装置后复读线上 `/products/soft-chews/`，
与 B 趟候选页**逐字节一致**（抹掉本次请求自己的 `?sfcap=` 后）。

---

## 5. 预检装置与顺序纪律（本批实际执行）

```bash
# 基线趟
python3 tools/b2d_s1_preflight.py install c0308af          # 上传头门 mu-plugin + git archive 出副本
xargs python3 tools/sf_masked_cmp.py --fetch /tmp/b2d1/A --base https://dev.zxpet.com \
      --header 'X-SF-Preflight: 1' --bust < plist.txt      # 47 页，带 --user
# 候选趟
python3 tools/b2d_s1_preflight.py install 58e24eb
xargs python3 tools/sf_masked_cmp.py --fetch /tmp/b2d1/B --header 'X-SF-Preflight: 1' --bust < plist.txt
# 判读
python3 tools/b2c_s2_norm_attrs.py A nA --theme-dir sinofresh-theme-preflight   # (B→nB 同)
python3 tools/sf_masked_cmp.py nB nA          # 38/47 SAME
python3 tools/b2d_s1_confine.py A B           # 47/47
python3 tools/b2d_s1_check.py  A B            # 46/46
python3 tools/b2d_s1_browser.py               # 30/30
# 拆净
python3 tools/b2d_s1_preflight.py remove      # 主题副本 + mu-plugin + 日志一起删；残留只剩 zz-sf-dev-lockdown.php
```

- **头门**是请求头 `X-SF-Preflight: 1`，不是 query 参数（query 门会被页面回显，制造假差异）。
- 副本装成 `themes/sinofresh-theme-preflight/` 并过滤 **`stylesheet` + `template`** ——
  只过滤 `template` 会让所有资源 URL 仍指向线上主题，那样验的是线上文件。
- **带门访问排在任何不带门访问之前**，点击类测试放最后。本批 CF 侧已由你加了
  `hostname eq dev.zxpet.com → Bypass cache`，HTML 变体缓存问题消失，纪律仍按老规矩执行。
- 诊断日志写 `mu-plugins/` 自己旁边（**不写 `/tmp`**：`open_basedir` 会静默拦住，跑完一轮没有日志）。
  实测日志 57 行、`theme=sinofresh-theme-preflight`，证明门真的触发过。
- **所有 curl / 浏览器 / 预检请求都带 Basic 认证**（`--user 'sfdev:…'` / `agent-browser set credentials`）。

---

## 6. 计划外发现（两处，都已处理并回写工具）

### 6.1 `sf_masked_cmp.py` 在带 GF 电话字段的页面上**永远无法变绿**

`/services/` 的 A/A 自检（**改前状态、与本次改动无关**）失败，原因是 Gravity Forms 的电话国家下拉：

```html
aria-controls="gform_phone_dropdown_6aaff57794a38"
```

这个 id 由**微时间种子哈希**生成，**每次请求都不同**。实测连续三次抓取得到三个不同值：

```
gform_phone_dropdown_6aaff6462561a
gform_phone_dropdown_6aaff648a28fa
gform_phone_dropdown_6aaff64b62d20
```

⇒ 任何含 GF 电话字段的页面，A/A 自检**必然 FAIL**，掩码回归**必然报 DIFF**，
与改动无关。这是标准回归门的一个真实盲区。

**处理**：给 `sf_masked_cmp.py` 的掩码集新增一条
`gform_phone_dropdown_[0-9a-f]+ → gform_phone_dropdown_MASK`（命名 `gf_phone_id`）。
补掩码后 A/A 自检在 `/services/`、`/products/soft-chews/`、`/formulas/` 三处全部 PASS。
`services` 页的掩码回归也随之转为 SAME（38/47 → 若不打这条掩码就是 37/47 且永远如此）。

### 6.2 `sf_masked_cmp.py` 新增 `--user`

dev 全站 Basic Auth 后，若工具不带凭据，`curl` 会拿到 401 页面，
**两侧哈希同一个错误页 ⇒ 静默全绿**。已加 `--user`（默认读 `$SF_DEV_AUTH`），
并在 docstring 里写明"没有静默回退"。

### 6.3 预检脚本会覆盖上一趟的日志

原 `install` 里有 `rm -f zz-sf-preflight.log`，导致 **A 趟的日志被 B 趟 install 抹掉**，
基线趟"门确实触发过"的证据丢失。已改为轮转：`[ -f LOG ] && mv LOG LOG.prev`，
`remove` 时两个一起删。

---

## 7. 回滚

| 项 | 值 |
|---|---|
| 改动性质 | **纯新增**：不改 post meta、不改模板路由、不碰 K1/K2/K7、无 option/transient 写入 ⇒ 数据层零风险 |
| 单 commit 整体回退 | `git revert 58e24eb`（10 个文件一个 commit） |
| 备份 | `sinofresh-theme/_backup/b2d-step1-20260920-225306/`（10 文件 + `MANIFEST.md` 带 sha256；该目录被 `**/_backup/` 排除，不进仓库） |
| 云端 | `pull` 后只 `chown -R apache:apache sinofresh-theme`（**不要整仓 chown**，会让 root 的 git 报 dubious ownership） |
| 回滚后硬指标 | 8 页回到 `c0308af` 的渲染字节；`#actives` 段与那个 H2 消失；点轨回到 6 项；`style.css?ver=2.10.44` |

---

## 8. 已知遗留 / 外部依赖

1. **`.sf-spec-term` 这个类名现在在剂型页上出现两次含义**：块④规格表原本没有它（只有 `.sf-spectable__tr`），
   新块的 `<dt class="sf-spec-term">` 是页面上第一次出现。目前 **`assets/js/` 与 `includes/` 里没有任何脚本消费
   `.sf-spec-*`**（已 `grep` 复核为空），CSS 侧已用 `.sf-actives` 限定作用域。
   但日后若有人写一个**页面级** `.sf-spec-term` 选择器，它会同时命中两处。**这是本批唯一的结构性代价**，如实记录。
2. 本批**未补 TranslatePress 串**：`/zh/products/*/` 上的这段新内容显示英文原文（与方案一致，下一次 TP 收录时统一补）。
3. 水印图不在本批范围内（第 2 批图集才碰图片）。
4. 首页 `<title>` 仍是 `sinofresh`；≤1239px 内页 hero 文字贴边 —— 两项独立待办，未动。

---

## 9. 教训（可复用）

1. **A/A 自检必须在"最容易假阳性"的页面上也跑一遍**。本批只对 `/products/soft-chews/`、`/formulas/` 做过 A/A，
   两次都过；直到 `/services/` 报 DIFF 才发现 GF 电话控件 id 是逐请求随机的。
   **只在一两个页面上自检，等于没检**——随机源往往只在少数页面上出现。
2. **对比前要问"两侧会不会同时拿到同一个错误页"**。Basic Auth 之后，不带凭据的 `curl` 会把 401 页面
   一致地喂给两侧，掩码回归会报全绿。给工具加凭据时必须**显式 fail-fast 或写进文档**，不能依赖人记得。
3. **预检装置的清理逻辑要区分"清掉产物"和"清掉证据"**。`rm -f <log>` 看起来无害，实际是删掉上一趟的举证材料。
4. **批准稿里的示例文案也要按全部输入跑一遍**。`Every {Label} recipe` 在第一个剂型（Soft Chews）上读得通，
   在 Powders / Drops / Pastes 上是错的 —— 示例只用了一个案例，就会漏掉这种问题。
5. **"删掉新块后逐字节相同"比"掩码哈希相同"强得多**，而且写起来并不难（两个锚点定位即可）。
   只要改动是纯新增，就应该优先做这一步，而不是靠 DIFF 列表 + 人眼看上下文猜测。

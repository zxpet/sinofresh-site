# Batch G — 详情页「主图 + 参数」两栏 + 剂型页 Packaging 第 4 行

**状态：已过门 + 渲染取证完成，未上线（2026-09-21）**。提交链：`c4f4437`（源改动 + 门工具 + 方案档）→ 本档随证据一并提交。**Step 7（预检上线 + 八步闭环）等用户确认后才动手**；预检副本仍装在云端（`sinofresh-theme-preflight/`，来自 `c4f443721403ebe386a85ebaa02951b5d1805ad8`），线上工作树仍停在 `4504aa9`（F1）。

## 一、这批做了什么

1. **8 个剂型模板**：`.sf-facts-mini` 在 `Certifications` 行后增第 4 行 **Packaging**（`data-label="Packaging formats"`，无 h2）。值从各页配置器 `data-group="packaging"` 选项集抄录，去末项 `Custom`，统一以 **`, or custom formats`** 结尾（拍板 III：8 个剂型统一逗号版，soft-chews 的三重 `+` 保留）。
2. **详情页模板 `single-sf_formula.html`**：原独立全宽 `sf-gallery` group 改为 `section.sf-fdetail-media` 两栏——外层 constrained + `bg-light`（背景只挂外层），`__inner` 与左右两栏一律 `layout:default`（core 对 constrained 子项限宽居中，会打散 grid）；左栏 `#gallery`（h2 与 4 帧 slide 全保留），右栏 `aside` 装 `{{FORMULA_INTRO}}` + `[sf_formula_factsheet]` + `Request Sample` CTA。
3. **`functions.php`**（2.10.53 → **2.10.54**）：
   - `sinofresh_formula_specs_parts()`：`sf_formula_specs` **按 key 正则取字段**（shelf 先 `/\d+\s*months?\s+shelf\s+life/i` 移出，pack 再 `/\sper\s/i` 移出——裸 `per` 会假匹配 `dropper bottle`，实测 +2 假值），unit 取剩余首段；**2 段式 11 条无 pack ⇒ 整行不渲染**（拍板 I：缺就缺，不顶替）。
   - `sinofresh_formula_intro()`：`sf_formula_intro` meta 有值直接用，否则按模板拼 `{product} is a standard {form} formula … Minimum order quantity: {moq}. Lead time: {lead}.`（MOQ 自带 `from` ⇒ 冒号槽位）。**不复用 schema 生成函数** ⇒ JSON-LD 0 变化。
   - `[sf_formula_factsheet]` 短代码：`<dl>` 5 项 `Unit size / Pack options / Shelf life / Certifications / Packaging`，后两项经 `spec_cell()` 读剂型页新行（**零改动**，F1 的「先截块再按 data-label 取」天然兼容第 4 行）。空值行跳过。
   - `{{FORMULA_INTRO}}` 占位符映射（带 `<p>` 外壳）。
4. **`style.css`**（2.10.53 → **2.10.54**，两处同步）：`.sf-fdetail-media` 命名空间——`__inner` grid `minmax(0,3fr) minmax(0,2fr)` gap 48、`__inner > *{margin-block-start:0}`（抵消 core 的 flow margin，实测右栏被推下 24px）、左栏覆盖 `.sf-gallery__stage` 的 `max-width:680px;margin:30px auto 0`（否则又窄又居中）、`<dl>` dt/dd 形态、CTA 用 **`cta` #B54E0F**（拍板：与页尾 Request a Quote 统一）、`≤768px` 堆叠 gap 32。

## 二、门（`tools/b2d_g_confine.py`，六门 + 负对照 + 破坏矩阵）

**混合方向**：剂型 16 页走**插入批**（候选侧删新行还原基线）；详情 42 页走**结构重组**（四步：撤批注释 → 删右栏 → 左栏升回顶层并恢复 class/style → 按基线口径闭合）。

| 门 | 真数据候选结果 |
|---|---|
| 0 候选身份 | 75/75 来自预检副本（副本 `functions.php`/`style.css` sha256 与本地提交**逐位相同**） |
| 1 资源清单 | 仅 style.css `2.10.53 → 2.10.54` ×75，资源 SET 变化 0 |
| 2 掩码 DIFF | differ **58** / identical **17**，与期望集合精确命中 |
| 3 页级限定证明 | **58/58 逐字节还原**（剂型 16/16 + 详情 42/42）；八剂型行值与各自配置器交叉核对 **8/8 ok** |
| 4 源级重建 | **11 文件** undone==base（functions.php、style.css、8 剂型模板、single-sf_formula.html） |
| 5 JSON-LD | **75/75** deep-equal |
| 负对照（new=base） | **RC=1，144 条**（首条即显式守卫「NOTHING moved…is --new pointing at base?」） |

**破坏矩阵 9/9 被抓**（每个破坏恰好落在该负责的门上）：`drop-row`→门3 行缺失；`wrong-value`→门3 值≠配置器；`extra-diff`→门2 多 DIFF；`missing-aside`→门3 右栏缺失；`stray-byte`→门3 逐字节还原失败；`keep-h2`→门3 点轨 h2 断言；`version-only-one`→门1 74/75；`wrong-cta`→CTA 目的地；`zh-cta-dropped`→zh 按钮缺失。

### 门的自身 bug（Step 0「先合成候选跑通门」的收获，共 4 个）

前三门 bug 在**合成候选阶段**就 FAIL 出来，没浪费一次真数据抓取：

1. **`SIDE_RE` 只吃 2 个换行**：渲染器真实输出 `</section>\n\n\n<aside`（三个），少一个 ⇒ 每次撤销残留 1 字节，42 页全败。
2. **`CLOSERS_CAND` 少了结尾第三个换行**（`\n\n</section>\n\n` 应为 `\n\n</section>\n\n\n`）⇒ 尾部多 1 个 `\n`。两者都是「渲染接缝实测不推演」的教训重演——本次用 `do_blocks` oracle 把真实字节问出来后才修对。
3. **undo 漏撤批自己的模板注释**（`<!-- Batch G: … -->`，基线里没有）⇒ 改成显式四步，并把注释裁剪钉在开头字样上：改注释措辞 ⇒ 撤销不再命中 ⇒ 门报 no-op，而不是悄悄放行。
4. **CTA `href` 用了字面 `/contact/`**：TranslatePress 在本地化页把链接改写成 `/zh/contact/`（该页其它 CTA 全是这个形状），真数据阶段 21 条假 FAIL。改为「目的地」判据 `^(\/[a-z]{2})?\/contact\/$`，并给合成器补上 TP 改写建模（否则合成跑的门天然比真数据弱）＋ 新增 `wrong-cta` / `zh-cta-dropped` 两条负对照。

合成器本身也修了 2 处：formulas 分支「先插注释再定位」的索引偏移（曾产出 `<<section` 坏字节）；键名带 `.html` 后缀（F1 同款 bug 复发）。

## 三、渲染取证（`tools/b2d_g_evidence.py`，**340 项 / 0 失败**）

数字全部实测（`docs/batchG-evidence.json` 落盘，截图 `docs/batchG-shots/`），断言「拿到的是哪份样式表」也是一项检查（本批全走预检副本 `style.css?ver=2.10.54`）。

**详情页 @1440**（joint-support-soft-chews / pure-fish-oil-blend / zh 版）：2 栏 **691.188px / 460.797px**（比值 1.499≈3:2）、gap **48px**、左右顶边同为 **509**（右栏 `margin-block-start:0` 生效）、外层有背景且内层透明；`.sf-gallery__stage` **`max-width:none`、`margin-left:0`、宽 691＝栏宽**（旧 680px 居中帽已破）；4 帧 slide 与 `h2.sf-gallery__title` 都在；intro 逐字引用 hero 的 MOQ（`from 500–1,000 units`）与 Lead time；参数表 5 行按 canon 序、Packaging 以 `, or custom formats` 结尾；CTA `Request Sample` → `/contact/`（zh 页 `/zh/contact/`）、底色 `rgb(181,78,15)`；**0 JS 错、无横向滚动**。页面上同名按钮全量清点只有 1 个（x=859＝右栏左缘 120+691+48）。

**详情页 @375**：1 栏 299px、gap 32px、右栏落到左栏下方（554 → 1082）。**@768**：1 栏 692px、leftBottom 1303 → sideTop 1335（堆叠成立）。

**剂型页 @1440（8/8）**：4 个带 `data-label` 的值，第 4 个＝`Packaging formats` 且以 `, or custom formats` 结尾，前三个 label 不变；事实带**换行成 2 行**（tops `473,473,473,505`，带高 **55px**）＝拍板 II(a) 预先接受、本次实测定稿的形态；点轨 **6 点 / 6 个 h2** 自洽。**@375**：4 项各占一行（tops 615/677/738/800，带高 289px），点轨 6/6。

## 四、重要发现：详情页没有点轨（纠正方案前提）

方案里「详情页点轨 4 点」是**错误前提**。实测（预检与线上 2.10.53 各测一遍）：详情页 `toc-nav.js` **根本未入队**，`.sf-toc__dot` 为 **0**，全页无任何 `*toc*` 元素；线上同样为 0。所以本批的不变量不是「保持 4 点」，而是「**详情页点轨数与线上一致（0＝0）、剂型页 6 点不变**」——已用 live vs 候选两侧对照证实（detail `0/0`，dosage `6/6`，均 RAIL UNCHANGED）。断言一个不存在的东西，只会把对的改成错的；这条已写进取证工具的注释。

## 五、下一步（Step 7，等确认）

预检副本仍在云端、线上字节未动。确认后按八步闭环走：`pull --ff-only` → 掩码 75/75 identical → E2E → 拆预检 → 日志归因（沿用 2D-E 那条 fatal 的 `--allow` 记账）→ 身份链 691 文件 → 仓库 md5（`--exclude` 本档）→ 收尾提交。回滚路径＝预检脚手架的 `remove`＋工作树仍在 F1。

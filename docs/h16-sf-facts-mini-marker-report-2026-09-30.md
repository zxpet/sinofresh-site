# H16 · `[SF_FACTS_MINI soft-chews]` 裸文本 Bug — 排查报告

日期：2026-09-30 ｜ 环境：生产 www.zxpet.com（dev 对照） ｜ 状态：**已扫清，未修，等确认**

---

## 0. 一句话结论

**前台也坏了，不只后台。** 生产上 Soft Chews 页的参数带（MOQ / Lead time / Certifications / Packaging）整条没渲染，原位置吐出裸文本 `[SF_FACTS_MINI soft-chews]`。根因：**今天 13:38 在 Site Editor 里保存 `page-soft-chews` 模板产生了 DB 副本，副本里该块的 `<!-- wp:html -->` 定界符被剥掉**，块从 `core/html` 降级成 freeform，H10 的 `render_block` 过滤器（只认 `core/html`）不再匹配。而"编辑器里看到裸文本"本身是**设计如此**——HTML 块在编辑器里永远显示源码。

⚠️ 重要的是：**另外 3 个 DB 副本里有你今天的真实编辑**（front-page +618 字符可见文本、soft-chews 的相关剂型卡片文案重写），所以"删 DB 副本恢复文件权威"这条最省事的路**会丢你的工作**，不能走。

---

## 1. 前台 /products/soft-chews/ 实际显示（逐区块清点）

HTTP 200，123,768 字节。逐区块：

| 区块 | 状态 |
|---|---|
| header 模板件（topbar+nav） | ✅ 在 |
| 面包屑 nav | ✅ 在 |
| Hero（H1 / 剂型行 / 两个按钮） | ✅ 在 |
| **sf-facts-mini 参数带（MOQ/Lead time/Certifications/Packaging）** | ❌ **缺失（0 个）** |
| **原位置裸文本 `[SF_FACTS_MINI soft-chews]`** | ❌ **泄漏（可见文本里能读到）** |
| Standard Formulas 标题 + 配方网格（sf-fgrid）+ Browse All 按钮 | ✅ 在（卡片数与正常页同量级） |
| Explore more dosage forms | ✅ 在 |
| How We Work | ✅ 在 |
| FAQ（含 FAQPage JSON-LD） | ✅ 在 |
| Related Dosage Forms | ✅ 在 |
| CTA 询盘表单（FluentForm） | ✅ 在 |
| footer 模板件 | ✅ 在 |

用户在页面上实际读到的句子（剥标签后）：

> …Browse Standard Formulas  Build Custom Formula  **[SF_FACTS_MINI soft-chews]**  Standard Formulas  Proven recipes…

**缺失的内容 = 只有那一条参数带**；其余区块一个不缺。裸文本夹在 hero 按钮和 Standard Formulas 之间的空白带里，不显眼——这就是"前台看着正常"的原因。

## 2. 8 个剂型页逐页对照（生产）

| 页 | HTTP | 裸 marker 泄漏 | sf-facts-mini 带 |
|---|---|---|---|
| soft-chews | 200 | **1 ❌** | **0 ❌** |
| tablets / liquids / pastes / powders / dental-chews / drops / fish-oil | 200 | 0 ✅ | 1 ✅ |

**只有 soft-chews 坏**，其余 7 页全部健康。dev 8 页全健康（dev 无任何模板 DB 副本）。home / /products/ / /formulas/ 无泄漏。

## 3. 后台编辑视图实际显示

**Pages → Soft Chews（页面编辑器）**：几乎全空——只有标题 "Soft Chews" + "输入/来选择一个区块" 占位符。页面 `post_content` 是空的（len=0），编辑器不显示任何模板块、也看不到 marker。截图：`/tmp/h16-editor-page.png`。

**外观 → 编辑器（Site Editor）里的 `page-soft-chews` 模板**：这里才看得到 marker。编辑器里显示为源码的块（HTML 块永远显示源码，`render_block` 是服务端 PHP 过滤器，编辑器是 React 应用根本不跑它）：
- `[SF_FACTS_MINI soft-chews]` ← 你看到的那行
- 面包屑整段 `<nav class="sf-breadcrumb">…`
- `[sf_formula_grid form="soft-chews"]`
- `[sf_explore_chips]` 及 Explore 带的原始 HTML
- 各处 SVG 图标等原始 HTML

其余标准块（heading/paragraph/buttons/columns/group）正常渲染。**"除了 marker 别的也不显示"＝所有 wp:html 块都以源码形态出现，这是 HTML 块的固有行为，不是故障。**

## 4. 根因（证据链，全部实测）

1. **损伤现场**：生产 `wp_posts` 里有 4 个模板 DB 副本（Site Editor 保存产生，覆盖同名代码文件）：
   `page-soft-chews`(ID 396)、`front-page`(353)、`page-products`(357)、`header`(352)。**dev 一个都没有。**
2. **首次保存时间**：`page-soft-chews` 副本 `post_modified_gmt = 2026-09-30 05:38:55`（北京 13:38）。修订历史（revision 398）证明 13:38 那次保存写入的内容**就已经没有定界符**。
3. **parse_blocks 定证**：
   - DB 副本：marker 所在块 `blockName = NULL`（freeform），根级 `core/html` 块数 1→0；
   - 主题文件：`blockName = 'core/html'`，一切正常。
4. **do_blocks 实渲**：DB 副本 → 输出含裸 marker、无 `sf-facts-mini`；文件 → 无裸 marker、有 `sf-facts-mini`。
5. **过滤器失配点**：`functions.php:958` 的 H10 过滤器第一句 `if (($block['blockName'] ?? '') !== 'core/html') return $block_content;` —— freeform 块直接放行，裸文本原样输出。
6. **同型案例**：`header` 模板件（09-28 保存）也是根级 `core/html` 1→0，同型损伤（其内容是无害的 sentinel div，所以没被发现）。
7. **序列化器规则**（wp-includes/js/dist/blocks.js `serializeBlock`）：`blockName === getFreeformContentHandlerName() && !isInnerBlocks` ⇒ **只输出内容、不写定界符**。根级 freeform 一旦产生，保存就把它固化；嵌套在 group 里的不受影响（`[sf_formula_grid]` 保住了，正是这条规则的镜像证据）。
8. **纯往返不剥**：把服务器模板文件喂给真实 `wp.blocks.parse → serialize`（后台已登录页内实测）：`core/html`、`isValid=true`、往返后定界符完好。⇒ 剥定界符不是解析/序列化的固有损耗，而是块在编辑器里被降级成 freeform 后（验证失败转换/具体编辑操作）再保存所致。**header 与 soft-chews 两例 2/2 同型**，凡被 Site Editor 保存过且带根级 HTML 块的模板都会中招。

**回答"是设计如此还是 bug"**：分两层——
- 编辑器里显示裸文本 = **设计如此**（HTML 块永远显示源码，PHP 过滤器不进编辑器）。
- 前台也吐裸文本 + 参数带消失 = **真 bug**（Site Editor 保存损伤 DB 副本 + 过滤器只认 `core/html` 的组合）。

## 5. ⚠️ 附带发现：DB 副本里有你今天的真实编辑（决定修法）

可见文本逐字对比（剥注释/标签）：

| 模板 | DB vs 文件可见文本 | 性质 |
|---|---|---|
| page-products | 一致 | 纯重序列化，可安全删 |
| header | 一致 | 纯重序列化（定界符剥了但无可见影响） |
| **front-page** | **不一致（DB +618 字）**：`[sf_home_about]` 短码位置已被实际文案替代（"SinoFresh pet supplement manufacturing facility exterior. About Us…"） | **你的真实编辑，删了就丢** |
| **page-soft-chews** | **不一致（DB +57 字）**：Related Dosage Forms 卡片描述被重写（"…round and heart shapes. Custom sizes, colors…" vs 文件 "Precise dosing in a classic form…"） | **你的真实编辑，删了就丢** |

另外今天你还编辑了 About/Quality/Factory Tour 的**页面**正文（修订 11:45–13:28），那些在 post_content 里、不受本问题影响。

## 6. 修法（供选择，未执行）

**方案 B（推荐）：过滤器加固——让 marker 在 freeform 里也能渲染。**
把 `functions.php:958` 的过滤器从"只认 `core/html`"放宽为"`core/html` ＋ freeform（`blockName` 为 null 或 `core/freeform`）"，精确匹配依旧不变（trim 后整行等于 `[SF_FACTS_MINI <slug>]` 才替换）。效果：
- 生产前台**立即恢复**，不动 DB 副本一个字节、**零内容丢失**；
- 以后 Site Editor 再怎么剥定界符都**不再造成前台损坏**（防复发，这是关键——两案例证明该损伤会重复发生）；
- 改动约 3 行，走既有部署流程（dev → 生产显式部署）。

**方案 A（不推荐单用）：删 4 个 DB 副本让文件重新生效。**
前台也能恢复，但会丢掉 front-page 和 soft-chews 副本里的真实编辑（§5）。除非先把这两份编辑人工搬回主题文件，否则不可走。

**方案 C（结构性，动静大）：把 marker 改成真短码。**
已核实块模板管线在 `do_blocks` 前跑 `do_shortcode`（wp-includes/block-template.php:262），短码无论块状态如何都会展开。但这会动 H10 的字节一致性基线，需要重新过门，不作为本轮首选。

**建议组合：B 为主；A 的"搬回编辑"部分另立一个批次做**（把 front-page / soft-chews 副本里的编辑反向同步进主题文件再删副本，恢复"git 文件＝唯一权威"的部署模型——这是 Site Editor 铁律被打破后的欠账）。

**同时要明确的一件事**：修复后**编辑器里仍然会看到裸文本**（那是 HTML 块的正常形态），判断前台好坏要看页面本身。那个块在 Site Editor 里不要删、不要重打、不要"转换"。

## 7. 遗留与观察

- 排查期间该模板副本又被保存过一次（05:38:55 → 05:45:18，len 27518→27714），说明当时编辑器还开着；以上结论对两个版本都成立。
- 生产 `wp_template` DB 副本现象从 09-28 起就存在（header/front-page/page-products），今天新增 soft-chews。"Site Editor 禁存模板"铁律需要一次系统性了断（要么反向同步，要么接受 DB 为权威并改部署流程）。
- 排查用临时管理员会话已销毁（生产剩 7 个＝你自己的），服务器与本地临时脚本已清。

*报告：docs/h16-sf-facts-mini-marker-report-2026-09-30.md*

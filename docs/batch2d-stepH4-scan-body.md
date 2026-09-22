# 批次 H4 Step 0（第二遍）—— 本体扫描 ＋ 【停机报告】

> **状态：只读扫描完成，未改任何字节（主题 0 字节、DB 0 行、未建文件）。**
> **触发停机第 ① 类「扫描与手册不符」** —— 不是手册写错了，而是 H2b2 删掉配置器之后，
> 手册 §【H4】里 **3 处前提已经不存在**（详见 §3）。同时新增 2 项**几何风险**需要裁决（§4 D2/D3）。
> 第二遍扫描的必要性：第一遍（`docs/batch2d-stepH4-scan.md`）是为**邮箱前置**而做的，
> 只覆盖了「H4 不受阻塞的部分」（§6.1–§6.5 的端点/悬浮层/抽屉/锚点/enqueue 盘点），
> **没有核对手册范围里「勾选内容」与「移动端底栏」这两个可见项在现行代码上是否还成立**。
> 数据源：75 页断面 `_backup/b2d-h4e-candidates/`（＝H4e 候选，即 H4 的基线）
> ＋ 主题静态盘点。零写入，全部判据可复算。

---

## 1. 结论速览

| 项 | 实测 |
|---|---|
| `.sf-fdetail2__params`（参数带） | **42 / 75 页**（＝21 EN ＋ 21 ZH 详情页，与手册 DIFF 集合**完全一致**）✅ |
| `#inquiry-form` | **19 / 75 页**；**详情页一个都没有**（详情页 `id` 只有 `gallery`）|
| 详情页现有表单 | **无**（既没有 GF 表单，也没有 `#inquiry-form`）⇒ 弹窗是详情页**唯一**的轻量询盘路径 |
| GF Form 2「Get a Quote」 | **12 字段**，嵌在首页 ＋ 联系页 ＋ 8 剂型页（各自在 `#inquiry-form` 里）|
| 篮子 `SFBasket` | **写侧无生产者**：`SFBasket.add` 全主题**零调用**（唯一调用方 `configurator.js` 已随 H2b2 删除）|
| `sinofresh_formula_*` sessionStorage | 仍由 `formulas.js:87` 写，读者（配置器）已删 ⇒ 与 H6 第 5 项同源 |
| 悬浮栈 | `.sf-float-stack` 是**全站**件（`parts/footer.html:111`），`right:24 bottom:24 gap:12`、圆钮 52px／移动端 44px |
| 停不停 | ⛔ **停**（第 ① 类：手册范围的三处前提已随 H2b2 消失）|

---

## 2. 手册 §【H4】范围逐条对照现状

| # | 手册范围 | 现行代码事实 | 判定 |
|---|---|---|---|
| 1 | REST 端点 ＋ 邮件 ＋ honeypot ＋ 3 秒时间验证 | 端点范本现成（`functions.php:4693` 最轻量）；honeypot/3 秒＝纯新增 | ✅ 可照做 |
| 2 | 5 字段表单（Name\* / Email\* / Company / Country / Message） | 与 Form 2 的 12 字段**不重叠**，是独立的低摩擦表单 | ✅ 可照做 |
| 3 | 悬浮按钮 `right:24 bottom:100`、滚到参数区后出现、点击开弹窗 | **`bottom:100px` 不是基础值**，是 `body.has-cookie-banner` 的态（基础 24px）；参数带在 **42 页**存在 ⇒ 触发条件有确定落点 | ⚠️ D2/D3 |
| 4 | **勾选内容自动带入** | ⛔ **前提消失**：配置器已删 ⇒ 篮子无生产者、`sinofresh_formula_*` 无读者；详情页也没有任何「勾选」控件 | ⛔ **D1** |
| 5 | 4 步打样流程内嵌 | `sinofresh_sampling_steps()` 已就位（H3），三处消费中的第三处正是这里 | ✅ 可照做 |
| 6 | **移动端全屏抽屉** | 抽屉范本现成（`style.css` §45 `.sf-basket-drawer` ＋ overlay ＋ `.is-open` ＋ `[hidden]` ＋ esc） | ✅ 可照做 |
| — | 手册 ⑧ 附注「移动端：改为底部固定栏（全宽）」 | 与现有栈、`body.has-cookie-banner`（移动端抬到 **268px**）、iOS 安全区三者叠加 | ⛔ **D3** |

---

## 3. ⛔ 三处「前提已消失」的原文位置

**3.1 「勾选内容」这五个字现在没有指代物。**
手册 ④/⑧/⑨ 的完整叙事是「客户在配置器里勾选 → 篮子/摘要 → 弹窗自动带入」。
H2b2 删掉配置器后这条链断在中间：篮子 API 与 UI 都还在（`basket.js` 535 行、页头袋按钮、
右侧抽屉、`Submit Inquiry`、篮子 PDF），但**没有任何东西往篮子里放东西**。
详情页的 hero 里那个 `Reference this formula` 按钮（`single-sf_formula.html:13`）现在的行为是
**复制配方名 + toast**（`formulas.js:87`），`#configurator` 滚动静默跳过（`formulas.js:110` 有 `if` 保护）。

**3.2 详情页没有任何表单。** 全站 75 页里 19 页有 `#inquiry-form`（首页＋联系页＋8 剂型页 ×中英），
详情页 `id` 只有 `gallery`。⇒ H4 弹窗在详情页上是**从 0 到 1** 的询盘路径，
不是「在既有表单旁再加一个」。这反而说明手册把弹窗放在详情页是对的。

**3.3 `bottom:100px` 这个数不是常量。** 手册 ⑧ 写的 `right:24px; bottom:100px`，
后者实际是 `body.has-cookie-banner .sf-float-stack` 的值（`style.css:3963`）；
基础值是 `bottom:24px`（`:3913`），移动端 `16px`／有横幅 `268px`。
H2b1 附录 A.5 #7 专门测过这 4 个数（100／24／268／16），H4e E4 又复核过一次
（3 按钮、同一列 `left=1364`、`tops=[720,784,848]`）。**这组量是本项目已知最脆的几何之一。**

---

## 4. 待裁决 4 项

| # | 问题 | 推荐 | 理由 |
|---|---|---|---|
| **D1** | **「勾选内容」的真源**：篮子已无生产者，弹窗的 "Your Selection" 拿什么填？ | **A：由当前配方自己的元数据服务端渲染**（Flavor / Piece Weight / Pack Size / Suitable For / Life Stage / Quantity & Pricing），与 ④ 参数带**读同一批 meta**（`sf_formula_specs` 解析段、`sf_formula_flavors`、`sf_formula_species`、`sf_formula_lifestage`、`sf_formula_price_tiers`），**不新造数据来源**；同时**不做**「从篮子带入」 | 详情页上「客户正在看的那支配方」就是唯一有意义的 Selection；读同一批 meta ⇒ 不产生「同一事实两个来源」；篮子无生产者，接进来是死路 |
| **D2** | **悬浮按钮插在哪、长什么样**：栈是全站件，且几何脆弱 | **A：插进 `.sf-float-stack` 的**第一个**子元素**（栈是 `flex-direction:column` ＋ 底部锚定 ⇒ 首个子元素在**最上方**，既有 3 个按钮**一个像素都不动**）；**胶囊形 ＋ `Send Inquiry` 文案**、橙 `#B54E0F`；由 `[sf_inquiry_button]` 短码渲染，**非详情页返回空串** ⇒ footer.html 虽全站共用，**输出的差异只落在 42 页**（与手册 DIFF 集合一致）。无 JS 时按钮不出现（弹窗本身也要 JS），页面既有 CTA 不受影响 | 手册 ⑧ 的 `right:24 bottom:100` 就是**栈自身的坐标**（说明本意就是「放进栈里」）；插首位是唯一能同时满足「进栈」与「不动既有几何」的位置 |
| **D3** | **移动端形态**：手册 ⑧ 写「改为底部固定栏（全宽）」 | **A：不另起全宽底栏，移动端仍是栈内胶囊**（44px 高、文案保留） | 全宽底栏要与现有栈、移动端横幅态 `268px`、iOS 安全区三者重新排布 ⇒ 要重测 5 个几何量的多档取值，而本批目标是「详情页的询盘路径」不是再造移动端 CTA；且 42 页的详情页在移动端已有 hero CTA ＋ `/contact/#quote` |
| **D4** | **询盘怎么留痕** | **A：纯 `wp_mail` 到 `sf_contact_email`**（读选项，不硬编码，遵守 H4e 不变量）＋ 照证书那套「**客户信 ＋ 必给 sales**」口径；失败写 `error_log` | 手册原文即「发送邮件到 sales@zxpet.com」；**新建 GF 表单＝改 DB＝停机第 ③ 类**，本批不触发 |

> **附带项（已判定，无需裁决）**：
> ① honeypot 隐藏字段 ＋ 3 秒时间验证 —— 纯新增，照手册。
> ② 弹窗脚本**只挂详情页**（42 页），不全站入队 —— 手册 H4 回归段 ＋ 扫描档 §6.5 双重要求（H2b2 刚因无脑入队删过配置器）。
> ③ 弹窗移动端复用 `.sf-basket-drawer` 的交互语言（overlay／`is-open`／`[hidden]`／esc），不另造一套。
> ④ `#inquiry-form` 与 Form 2 **不动**（首页/联系页/8 剂型页的既有路径保持原样）。

---

## 5. 与手册不符时的处置原则（本次适用）

playbook 第十部分 Step 0 原文：

> **Step 0：扫描现状** → 检查是否与 playbook 预期相符 → 相符：直接进 Step 1 → **不符：停下报告**

本次「不符」的性质是 **范围前提被上一批删掉**（配置器），不是手册写错。
⇒ 处置＝**把裁决反写进 playbook §【H4】范围段**（H3 已建立同款先例：附录 A.8 #13
「若只改代码不回写文档，下一批会照着作废的范围再犯一次」）。

---

## 6. 证据索引（全部可复算，零写入）

| 判据 | 命令/来源 |
|---|---|
| 参数带 42 页、`#inquiry-form` 19 页 | 遍历 `_backup/b2d-h4e-candidates/*.html` 统计 `sf-fdetail2__params` / `id="inquiry-form"` |
| 详情页 `id` 只有 `gallery` | `templates/single-sf_formula.html`（139 行，全文 1 个 `gallery` 锚点）|
| `SFBasket.add` 零调用 | 全主题 grep（仅 `basket.js` 自身定义；`configurator.js` 已删）|
| `formulas.js` CTA 现行为 | `assets/js/formulas.js:78-112`（复制名 ＋ toast ＋ `#configurator` 死支有 `if` 保护）|
| Form 2 是 12 字段 | `_backup/gf2-slim-105901/form-2.json`（本地快照）|
| 悬浮栈几何 | `style.css:3913/3963/3997/4007`；H2b1 附录 A.5 #7；H4e E4 |
| 采样 4 步单一真源 | `functions.php:2526` `sinofresh_sampling_steps()` |

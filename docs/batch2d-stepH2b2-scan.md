# 批次 H2b2 Step 0 扫描 —— 停入队 + 删资产（纯删除批）

> 状态：**扫描完成，未改动任何文件**（主题仍等于 `ebe8f50`，工作树干净）。
> **用户更正 1**：playbook 明确不执行上线 ⇒ **Step 6 `git pull` 跳过**，本批只到"候选过门 + E2E"为止。
> **用户更正 2**：**H2b2 基线 = H2b1 后的预检副本**，不是 live。**预检副本保留不拆**（H2b2 要用）。
> 声明范围：`functions.php` 停入队 + 删 `configurator.css` / `configurator.js` 两个资产。
> 预期 DIFF 集合：**16 页**（8 剂型 × en/zh）少资源引用，其余 59 页逐字节不动。

---

## 0. 基线锁定（已实测，本节是本批能否成立的前提）

| 事项 | 实测 |
|---|---|
| 服务器预检副本 | `/var/www/dev.zxpet.com/public/wp-content/themes/sinofresh-theme-preflight/` |
| 与 `ebe8f50` 的字节关系 | 非 `_backup` 文件 **349 / 349 逐字节相同**（本地 `git archive ebe8f50 sinofresh-theme` 导出后逐文件 sha256 比对，`diff` 输出为空） |
| 页面基线断面 | `_backup/b2d-h2b1-candidates/` **75 页**；MANIFEST 首行记录 `# header: X-SF-Preflight: 1`；75/75 页含 `-preflight`；`style.css?ver=` 全为 **2.10.56** |

⇒ H2b2 的基线在任意时刻都可由 **`ebe8f50`** 重建，不依赖任何易碎副本；"基线滞后"风险＝0。
⇒ 预检副本内的 `_backup/*` 历史快照（含 8 个同名 `configurator.css`）**不参与**任何比较，只认入队路径
`assets/css/configurator.css`。

---

## 1. 声明范围 vs 实测 —— 三处更正

| # | 方案/交接文写的 | 实测 | 处置 |
|---|---|---|---|
| 1 | `functions.php` **−2 行**（188/189 enqueue） | **−4 行（187–190）**。187 是 `if ($is_dosage_page) {`、190 是 `}`；两条 enqueue 删掉后这个 `if` 成为空壳，必须连壳删。⚠️ **185–186 的 `$dosage_pages` / `$is_dosage_page` 不能删**——205 行 `formulas.js` 的入队仍在用（`if ($is_dosage_page \|\| is_singular('sf_formula') \|\| is_post_type_archive('sf_formula'))`） | 更正方案数字；删 187–190 共 4 行 |
| 2 | 删 `configurator.css` **`:667-707`「整段」** | **行号不成立**：`:667` 是一条普通块内注释的首行；**`:707` 不是任何块的边界**。真正的容器是 `@media (max-width: 767px) {`（**L642**），它一直开到**文件末尾 L831**。`html.no-has` 两条复刻的真实位置是 **L700 / L705**，那 5 条 `:has()` 规则在 L643 / L675 / L682 / L689 / L690 | 操作改为**整文件删除**（既不需要也不允许分段）；同步更正 3 处文档（见 §7） |
| 3 | 每页少传 **54.8 KB**（css 24.8 + js 31.3） | 实测 **53,084 B ＝ 51.8 KB**：css **21,808 B / 831 行** ＋ js **31,276 B / 875 行**。方案引用的 24.8 KB 是 H2b1 之前的体积（`.sf-explore*` 125 行已迁出） | 更正方案数字 |

其余声明项与实测一致：DIFF 集合 16 页 ✅、资产两项 ✅、`assets/css/` 目录一并消失（该目录下**只有** `configurator.css` 一个文件，全站对 `assets/css/` 的路径引用也只有 `functions.php:188` 这一处）。

---

## 2. 待删资产与页面级后果（逐页实测）

75 页基线断面中，**只有 16 页**引用这两个资产（8 剂型 × en/zh）；其余 59 页连字面都不出现。

| 页面 | 总行 | `<link>` 行 | `<script>` 行 |
|---|---|---|---|
| `products__soft-chews` | 903 | **119** | 852 |
| `products__tablets` | 900 | **119** | 849 |
| `products__powders` | 900 | **119** | 849 |
| `products__pastes` | 900 | **119** | 849 |
| `products__drops` | 910 | **119** | 859 |
| `products__liquids` | 910 | **119** | 859 |
| `products__fish-oil` | 910 | **119** | 859 |
| `products__dental-chews` | 910 | **119** | 859 |
| `zh__products__soft-chews` | 1190 | **119** | 1140 |
| `zh__products__tablets` | 1189 | **119** | 1139 |
| `zh__products__powders` | 1189 | **119** | 1139 |
| `zh__products__pastes` | 1183 | **119** | 1133 |
| `zh__products__drops` | 1193 | **119** | 1143 |
| `zh__products__liquids` | 1193 | **119** | 1143 |
| `zh__products__fish-oil` | 1193 | **119** | 1143 |
| `zh__products__dental-chews` | 1199 | **119** | 1149 |

要消失的两行（`products__soft-chews` 实测原样）：

```
L119  <link rel='stylesheet' id='sinofresh-configurator-css' href='https://dev.zxpet.com/wp-content/themes/
      sinofresh-theme-preflight/assets/css/configurator.css?ver=2.10' media='all' />
L852  <script id="sinofresh-configurator-js" src="https://dev.zxpet.com/wp-content/themes/
      sinofresh-theme-preflight/assets/js/configurator.js?ver=2.3"></script>
```

⇒ **限定证明的判据**：候选 = 基线**恰好**去掉这两行（按 `id='sinofresh-configurator-css'` /
`id="sinofresh-configurator-js"` 认领），逐字节相等；其余 59 页**逐字节相同**。
本批**不需要任何 ver bump**：删掉的两个 enqueue 带走了各自的令牌，其余文件零改动。

16 页上除这两行外唯一的 `configurator` 字样是 H2b1 的作者注释
（en `L290`、zh `L561–567`：`<!-- Block 4: Explore more dosage forms (moved out of the configurator, batch H2b1) -->`），
不是引用，**不动**。

---

## 3. 纯删除证明：`configurator.css` 117 条规则头逐条分类

用括号深度扫描（注释替换为等量空行以避免行号漂移）取得全部规则头，再按选择器前缀分类：

| 类别 | 条数 | 说明 |
|---|---|---|
| `.configurator…` 开头 | **110** | 配置器自身结构 |
| `body:has(.configurator…)` | **4** | L643 / 675 / 682 / 689–690（条形+抽屉叠层） |
| `textarea.configurator__custom-input` | **1** | L194，仍属配置器 |
| `html.no-has .trp-language-switcher` / `html.no-has .sf-float-stack` | **2** | L700 / L705 |

**没有第 118 类** —— 即：在**现代引擎**下，这个文件里**零条规则能匹配存活元素**（配置器 DOM 已在 H2b1
整块删除，`.sf-explore*` 125 行已在 H2b1 迁入 `style.css`）。所以：

> 删 `configurator.css` 对 16 页的**渲染是空操作**，唯一的例外是 §4 那一项 —— 而那一项也是收敛。

`:has(` 口径核对（`出现次数` 口径，不是行数）：

| 文件 | 出现次数 | 其中在注释里 | 在真选择器里 |
|---|---|---|---|
| `configurator.css` | 7 | 2（L695 / L698 的说明文字） | **5** |
| `style.css` | 164 | — | — |
| 合计 | 171 | | 删文件后 = **164** |

---

## 4. 旧引擎差值归零（本批唯一的行为变化，且是收敛）

L700 / L705 那两条 `html.no-has` 是**无条件复刻**（不受 `.configurator` 限定）。删掉它们之后：

| 元素 | live（有条） | H2b1 候选·现代引擎 | H2b2 候选·旧引擎（删掉复刻后） |
|---|---|---|---|
| `.sf-float-stack` | `132px` | 见 H2b1 四格（100 / 24 / 268 / 16） | **＝ 现代引擎取值 ⇒ 差值归零** |
| `.trp-language-switcher` | `68px` | `0px` | **＝ 现代引擎取值 ⇒ 差值归零** |

⇒ 本批 E2E 的硬判据：**同一页、同一视口，`no-has` stub 开/关两态下，两个固定层的 `bottom` 必须相等**
（H2b1 的四格法直接复用，只是这一次期望是"两态相同"而不是"两态不同"）。

⚠️ `html.no-has` **探针本身保留**（`functions.php:58–61`）：`style.css` §30（L4378–4404）仍以它为消费者
（`html.no-has section` / `.wp-block-columns` / `.sf-statbar__grid` / `.sf-dosage-grid` / `.sf-strip`）。

---

## 5. 零引用取证 —— 本批会**新造** 4 处死角，全部登记 H6，**本批不动**

方案把 K1–K7 契约与 `formulas.js`/`basket.js`/`config-pdf.php`/`formula-pools.php` 全列为**全程零改动**，
所以下面 4 项在 H2b2 里只登记、不修。它们都是"删 configurator.js 才成立"的直接后果：

| # | 死角 | 实测规模 / 取证 | 为何本批不动 |
|---|---|---|---|
| 1 | **K2 `.sf-formulas-data` 失去唯一读者**。`assets/js/configurator.js:644` 是它全站唯一的读取点（`querySelectorAll('script.sf-formulas-data')`），而它的存在理由就是那处读取（`functions.php:1089` 注释写明 "so configurator.js readFormula() can stop scraping `<details>`"） | **60 / 75 页**携带，合计 **72,720 B**，平均 1,212 B；最大 `/formulas/` 与 `/zh/formulas/` 各 **9,504 / 9,441 B** | 出 K2 的 `sinofresh_formula_grid` 属 K 系列契约冻结 |
| 2 | `formulas.js` 的 `#configurator` 分支成死支：`var target = document.getElementById('configurator')`（L110），H2b1 之后全站 75 页**已无**该 id | 有 `if (target)` 保护 ⇒ 不报错，只是永不进入 | K1 契约冻结（H2b-scan 原文即写"死分支留 H6"） |
| 3 | `style.css:1220` 的 `.configurator__summary-value` 成死选择器（`font-variant-numeric` 组选择器的一支） | 全站该类的产出点只有已删的块内 HTML；`inc/config-pdf.php` **不产出**该类（已 grep 核验）；`configurator.js:100` 只是查询者 | 改 `style.css` 会触发 ver bump ⇒ 把本批"16 页 −2 行 / 59 页同"的极净判据搞脏 |
| 4 | 会话键 `sinofresh_config_<slug>` / `sinofresh_formula_<slug>` 既无写者也无读者 | ⚠️ **这项在 H2b1 就已经成立**：`configurator.js:15-17` 是 `var root = document.querySelector('.configurator'); if (!root) { return; }` —— DOM 一删，脚本在任何页面上都**在写之前就早退** | 与 §6 的"零行为变化"证明是同一件事 |

---

## 6. 关键发现：`configurator.js` 在 H2b1 之后**已经是惰性脚本**

`configurator.js:15-17` 首句即 `if (!root) return;`。H2b1 删掉了配置器 DOM ⇒ 脚本在 16 页上
**不绑事件、不写 sessionStorage、不发请求**，只消耗 31,276 B 下载与一次解析。

⇒ 推论（本批最有价值的一条判据）：**删掉它必须是"零行为变化"**，可以正面证明而不是靠"看起来没变"——
在浏览器里对同一页取两态（脚本在场但惰性 / 脚本不在场），比对**同一次交互后的页面指纹**：
`sessionStorage.length`、`<body>` 结构化轮廓的哈希、`.sf-explore` 带与卡墙的几何、`performance` 里
configurator 相关请求数（在场应为 1 次下载 + 0 次 XHR）。

顺带证实"端点保留"是合理的：`/wp-json/sinofresh/v1/config-pdf` **不止 configurator.js 一个调用方**——
`assets/js/basket.js:391`（Stage 4 购物篮导出 PDF）也 POST 它 ⇒ 删 `configurator.js` **不会**让端点变孤岛。

---

## 7. 与手册的三处不一致 —— 均已在本次扫描中更正

| 位置 | 原文 | 更正为 |
|---|---|---|
| `docs/batch2d-stepH2b1.md:180`（H2b2 交接不变量 #1） | 「要一起删的整段：`configurator.css:667-707`」 | 整文件删除；`html.no-has` 复刻在 **L700 / L705**，容器是 **L642 起的媒体查询、直开到 L831** |
| `docs/batch2d-stepH2b1.md:134` | 「`:700-707` 那两条 `html.no-has`」 | **L700 与 L705**（两条不连续） |
| `docs/agent-playbook.md:988 / :999` | 同上两处 667-707 / 700-707 | 同上 |
| `.workbuddy/memory/MEMORY.md` | 「整段删 `configurator.css:667-707`」 | 同上 |
| `docs/batch2d-stepH2b-scan.md:195` | 「−2 行（188/189 enqueue）」 | **−4 行（187–190）**，且 185–186 必须保留 |

---

## 8. 是否触发停机（逐条判）

| 停机条件 | 判定 |
|---|---|
| ① 扫描与手册不符 | **不触发**。手册（playbook）的方法与约束未被推翻；被推翻的是**上一批留下的两处派生数字/行号**，方向明确、无歧义（删整个文件 vs 分段删，结论相同），已在 §7 就地更正 |
| ② 门抓到产品 bug | 本批尚未跑门 ⇒ 不适用 |
| ③ 需要改数据 | **不触发**。全批不碰 DB、不改契约、不改 option |

⇒ 无裁决项，可自动进 Step 1。

---

## 9. Step 1–N 计划（不含上线）

| Step | 内容 | 门 / 证据 |
|---|---|---|
| 1 | `functions.php` 删 187–190（连空壳 `if`），保留 185–186 | S1：185–186 仍在、205 行仍引用 `$is_dosage_page`；`php -l` 干净；`grep -c sinofresh-configurator` = 0 |
| 2 | 删 `assets/css/configurator.css`、`assets/js/configurator.js`（`assets/css/` 目录随之消失） | S2：两文件不存在、`assets/css/` 不在、全站对这两个路径的引用 = 0、`:has(` 合计 = 164 |
| 3 | `install ebe8f50` 重装基线 → 抓基线 75 页 → 与 `_backup/b2d-h2b1-candidates/` 逐字节核对（**基线不得滞后**） | S3：75/75 identical，否则停 |
| 4 | `install <H2b2 全 40 位 SHA>` → 抓候选 75 页 → 主门（限定证明：16 页恰少 2 行、59 页逐字节同）＋破坏矩阵＋三条负对照 | PASS 才继续 |
| 5 | 浏览器 E2E：① 16 页两资产 `id` 均不存在 ② 旧 URL 在预检副本返回 404 ③ **惰性脚本零行为变化**指纹比对 ④ **旧引擎差值归零**四格 ⑤ 16 页 200 / 无 console 错误 ⑥ `.sf-explore` 带与卡墙几何与基线逐值相同 | 截图 + 几何 |
| 6 | ~~`git pull`~~ **跳过（用户更正 1）**；收尾：批次文档 + 证据归档 + playbook 进度 + 记忆 | — |

---

## 10. 证据索引（本次扫描产出）

| 文件 | 内容 |
|---|---|
| 本文件 | Step 0 扫描全档 |
| `_backup/b2d-h2b1-candidates/` | H2b2 基线断面（75 页，`-preflight`，ver 2.10.56） |
| `/tmp/b2d-h2b2-base.local.manifest` / `.server.manifest` | 349 行 sha256 清单比对（临时产物，结论已记入 §0） |
| `docs/agent-playbook.md` 附录 B | H2b1 状态改为"不上线，Step 6 跳过"；H2b2 进 Step 0 完成 |

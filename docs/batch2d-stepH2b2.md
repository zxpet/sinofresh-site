# 批次 H2b2 全档 —— 停入队 + 删资产（纯删除批）

> **状态：Step 1–5 全过门 + E2E 全过；Step 6（`git pull`）按用户 2026-09-22 规则整条跳过。**
> 产品提交 **`3b9fc239bccd932eb6375edb5902bc47ef670dfc`**；基线 **`ebe8f505be6707536d5187fde617fab42b613311`**。
> 声明范围：`functions.php` 停入队 ＋ 删 `assets/css/configurator.css` / `assets/js/configurator.js`。
> 预期 DIFF 集合：**16 页**各少两行，**其余 59 页逐字节不动**。
> 扫描档：`docs/batch2d-stepH2b2-scan.md`（Step 0，含三处数字更正）。

---

## 0. 结论速览

| 项 | 结果 |
|---|---|
| 产品 diff | **1,710 删 / 0 增**，恰 3 个文件：`functions.php` −4 行、两个资产文件删除（`assets/css/` 目录随之消失） |
| 静态门 S1–S9 | **全过**；负对照 **6/6 as required** |
| 基线断面 | 重装 `ebe8f50` → 抓 75 页 → 与存档 **掩码比对 75/75 identical**；负对照 74/75 正确报差 |
| 候选装载 | 服务器预检副本 = 本地 `3b9fc23` 树 **347/347 逐字节相同**；75 页全 200 |
| 主门（限定证明） | **PASS 18 条 ok / 0 FAIL**：16 页恰少两行（按 `id=` 认领、逐字节重建）＋ 59 页逐字节同 |
| 破坏矩阵 | **10/10**，`missed: []` |
| 三条负对照 | 全部 FAIL 且**具名**（缺 served 清单 / 基线目录空 / 候选=基线） |
| 浏览器 E2E | **E1–E6 全过**；几何 **210 项对照逐值相同** |
| 版本号 | **未 bump**（两条被删 enqueue 带走了各自的令牌）——这是判据锐利的原因 |
| `:has(` 全站 | **171 → 164** |
| 计划外行为变化 | **恰好一条，且是收敛**：旧引擎差值归零（§5） |

---

## 1. Step 1–2：删了什么，留下了什么

工具 `tools/b2d_h2b2_patch.py`（`--check` / `--apply`）。**按结构定位，不按行号**：
锚 `$dosage_pages = [` → `$is_dosage_page = is_page(` → `if ($is_dosage_page) {` → 两条 enqueue → `}`；
行号 187–190 只作交叉核对，漂移即响亮失败。写盘前 validate、写盘后同进程读回再 validate，双重把关。

删除的 4 行（连空壳 `if`，不是只删两条 enqueue）：

```php
	if ($is_dosage_page) {
		wp_enqueue_style('sinofresh-configurator', ... '/assets/css/configurator.css', array(), '2.10');
		wp_enqueue_script('sinofresh-configurator', ... '/assets/js/configurator.js', array(), '2.3', true);
	}
```

### ⚠️ 两条必须留下的东西

| 保留项 | 为什么 |
|---|---|
| `functions.php:185–186` 的 `$dosage_pages` / `$is_dosage_page` | **L205 的 `formulas.js` 入队仍在用**：`if ($is_dosage_page \|\| is_singular('sf_formula') \|\| is_post_type_archive('sf_formula'))`。这是 K1 契约，连带删掉会让卡墙按钮的点击静默失效。断言：存活计数**恰为 2** |
| **5 条注释里的 `configurator.js`**（L507/1084/1086/1227/1233） | 它们是 K2 `.sf-formulas-data` 数据块与会话键的**存在理由记录**，本批两者都还在 ⇒ 属 H6 死角，不动。断言是双向的：**去块注释后活代码 0 次、注释里恰 5 次** |

第二项值得强调：一句「全文件不得出现 `configurator.js`」的检查会**把正确输出判为失败**；
而一句宽松的放过又会让它悄悄被"顺手清理"掉。所以口径必须写成两半。

| 文件 | 字节 | 行 |
|---|---|---|
| `assets/css/configurator.css` | 21,808 | 831 |
| `assets/js/configurator.js` | 31,276 | 875 |
| 合计 | **53,084 B（51.8 KB）** | 1,706 |

---

## 2. 静态门 S1–S9（`tools/b2d_h2b2_checks.py`）

| # | 断言 | 结果 |
|---|---|---|
| S1 | `functions.php`：守卫保留（`$is_dosage_page` ×2、formulas 守卫 ×1）、两条 enqueue 消失、相对基线 `{`/`}` 各 −1、行数 −4 | PASS |
| S2 | `php -l functions.php` 干净 | PASS |
| S3 | 两资产不存在、`assets/css/` 目录不在、全站对这两个路径的引用 = 0 | PASS |
| S4 | 主题文件集 = 基线集 − 恰好那两个文件（347 vs 349，无人为增减） | PASS |
| S5 | `:has(` 全站 **164**、`style.css` **164** | PASS |
| S6 | `configurator.js` 恰在 **5 条注释行**存活、活代码 0 | PASS |
| S7 | K1–K7 契约文件（`formulas.js` / `basket.js` / `config-pdf.php` / `formula-pools.php`）与 `ebe8f50` 逐字节相同 | PASS |
| S8 | `style.css` 仍定义 `.sf-explore*`（15 个规则头）；8 个剂型模板仍带 H2b1 作者注 | PASS |
| S9 | 文件级 diff 恰为声明的三项（`M functions.php`、`D` ×2） | PASS |

**负对照 6/6 as required**（`tools/b2d_h2b2_negctl.py`）：

| 对照 | 变异 | 期望 | 实测 |
|---|---|---|---|
| `faithful-copy-passes` | 不动（A/A） | 通过 | 通过 ✅ |
| `asset-restored` | 把 `configurator.css` 放回 | FAIL | S3+S4+S5 ✅ |
| `functions-php-reverted` | `functions.php` 退回基线 | FAIL | S1+S3+S6 ✅ |
| `stray-file-added` | 多一个杂物文件 | FAIL | S4 ✅ |
| `migrated-block-stripped` | 剥掉 `style.css` 的 `.sf-explore*` | FAIL | S8 ✅ |
| `functions-php-absent` | 整个删掉 `functions.php` | FAIL（**且具名**） | **S0** ✅ |

最后一条是本批改出来的：第一轮它是靠 `FileNotFoundError` 退出（rc=1），
数值上"抓到"了，但**没有任何判据**——负对照台现在要求「非零退出 **且** 至少一个具名检查」，
静态门也新增 **S0「必需输入存在」**。

---

## 3. Step 3：基线（重装 `ebe8f50`）

- `install ebe8f50…`（**先 `git fetch`**，见 §6）→ 抓 75 页（带 `X-SF-Preflight: 1`）。
- 与上一批存档 `_backup/b2d-h2b1-candidates/` **掩码比对：75/75 identical**。
- 硬判据（掩码门不管的、真正证明"是同一份主题"的）：**75/75** 页 `style.css?ver=2.10.56`、
  **75/75** 含 `-preflight`、`class="configurator` **全 0**、`sf-explore` 命中 **14×16 页 / 0×59 页**。
- 掩码门负对照：往一页注入一个标记 → **74/75**，正确报差。

⇒ 基线不滞后，且随时可由 SHA 重建。

---

## 4. Step 4：候选门（限定证明）

候选 `3b9fc23` 装好后，服务器副本与本地 `git archive 3b9fc23` 树比对：**347 / 347 逐字节相同**；
候选断面 75 页全 200（首轮曾 44 页 301，那是 §6 的事故，修好后重抓）。

**主门 `tools/b2d_h2b2_confine.py` —— PASS，18 条 ok / 0 FAIL：**

| 门 | 判据 |
|---|---|
| [0] | 两侧断面各 75 页（不满足即中止，避免派生症状淹没病因） |
| [1] | 两条资产引用在基线**恰 16 页各一次**、候选**全 75 页 0 次**；`style.css` 令牌**两侧都是 2.10.56**；被删行的 `?ver=` 恰为 `2.10` / `2.3` |
| [2] | 恰 **16 页差 / 59 页同**；且**折叠 `?ver=` 不改变答案**（= 没有任何版本令牌移动，这一条会把"顺手 bump 了别的东西"抓出来） |
| [3] | 16 页 = 基线**按 `id` 认领去掉那两行**后逐字节相等；59 页逐字节相同且从未出现该令牌 |
| [4] | 工作树 **347 个文件**与服务副本逐字节相同；4 个契约文件在且未动；两资产不在树里 |
| [5] | JSON-LD 全 75 页逐字节相同；每页 h1 恒 1 |
| [6] | H2b1 不变量：band 仍夹在 `#formulas` 与 How We Work 之间、hero CTA 在、H2b1 作者注在、`#configurator` 与 `Build Your …` h2 均 0 |

**破坏矩阵 10/10**（每条都写出被哪几个门抓到）：

| 变异 | 抓它的门 |
|---|---|
| `link-restored` / `script-restored`（把引用放回） | [1]+[3] |
| `third-line-removed`（多删一行） | [3]+[6] |
| `band-chip-missing`（拆掉一枚 chips） | [3] |
| `stable-page-touched`（动 59 页之一） | [2]+[3] |
| `style-token-moved`（移版本号） | [1]+[2]+[3] |
| `asset-file-restored`（资产文件放回树里） | [4] |
| `jsonld-drift`（注入一段 JSON-LD） | [3]+[5] |
| `declared-page-unchanged`（声明页原样） | [1]+[2]+[3] |
| `detail-cta-reverted`（回退详情 CTA） | [2]+[3] |

**负对照 3/3**：`served-manifest-missing`（缺参照必须 FAIL 而非 skip）、`baseline-empty`、
`candidate-equals-baseline` —— 三者都给出具名 `[n]` 判据，而非 traceback。

---

## 5. Step 5：浏览器 E2E（E1–E6 全过）

`tools/b2d_h2b2_e2e.py`。启动顺序沿用 H2b1 实测结论：
`close --all → set credentials（init script 在 env 里）→ open → set headers{Basic + X-SF-Preflight} → reload → set viewport`。

| # | 断言 | 实测 |
|---|---|---|
| **E1** | 16 页（8 剂型 × en/zh）200 且 HTML 里 `sinofresh-configurator` 引用 **0**；渲染页里 `cfgLinks/cfgInHead/cfgInBody` 全 0、configurator 资源请求 **0**、无 console 错误 | 全过 |
| **E2** | 两个旧 URL 在预检副本下 **404**；**同目录的 `formulas.js` 仍 200**（对照，证明 404 是删除而不是目录坏了） | 全过 |
| **E3** | **惰性脚本零行为变化**（§5.1） | 全过 |
| **E4** | **旧引擎差值归零**（§5.2） | 全过 |
| **E5** | 几何与 H2b1 候选测量**逐字段相同**：**210 项对照**（35 字段 × 6 档）全部一致 | 全过 |
| **E6** | 六档实拍截图 37–54 KB（480/768/1024/1100/1101/1440），band 取景避开吸顶栏 | 全过 |

### 5.1 E3：把"惰性"证明出来，而不是"看起来没变"

`configurator.js` 是**裸 IIFE**（实测：不是 `DOMContentLoaded` 包裹，L12 `(function () {`），
首句即 `var root = document.querySelector('.configurator'); if (!root) return;`。
H2b1 删掉 DOM 之后它就已经什么都不做了——所以本批的断言应该是**可以正面证明的零行为变化**：

- 先在页面上断言 `cfgTargets == 0`（`.configurator` / `.configurator__bar` / `#configurator-drawer` / `#configurator` 一个都没有）；
- 然后**用 `eval` 把基线自己那份 31 KB 的 `configurator.js` 注入页面并执行**（前置一行 `window.__cfgRan=…` 哨兵）；
- 两态对比：`sessionStorage` 键、`<body>` 结构轮廓节点数、band/卡墙几何、configurator 资源请求数。

实测：`cfgRan=1`（注入确实执行了）、`sessionStorage` 键恒为 `['wpEmojiSettingsSupports']`、
轮廓恒 **455** 节点、几何相同、configurator 请求 **0 → 0**。
另断言页面**不存在** `sinofresh_config_*` / `sinofresh_formula_*` 键——那正是 H6 死角 #4，顺手取证。

⚠️ **第一版这里是错的**（见 §7 自我修正 #5）：脚本点了 `a.sf-explore__btn`，而它的 `href="/formulas/"`
⇒ **页面跳走了**，哨兵随旧文档消失（`cfgRan=0`）、轮廓数"从 485 变 460"其实是在量另一个页面。
改成**捕获阶段 `preventDefault`** —— 事件照常传播给元素自身的处理器（真有绑定就会触发），只抑制跳转；
并加一条「点击后仍在 `/products/soft-chews/`」的断言把这个陷阱钉死。

### 5.2 E4：计划外变化在这一批翻向验证

H2b1 留下的四格表里，唯一未经裁决的行为变化是：`configurator.css` 里 **L700 / L705 两条
`html.no-has` 是无条件复刻**，所以旧引擎一直拿 `132/68`，而现代引擎收敛到全站取值。
本批把整份文件删掉 ⇒ 复刻消失 ⇒ **正确断言从"两态不同"翻成"两态必须相同"**。

| 视口 | 无 stub | 有 stub（`html.no-has`） | 差值 |
|---|---|---|---|
| 480px | float `268px` / lang `0px` | float `268px` / lang `0px` | **0** |
| 1440px | float `100px` / lang `0px` | float `100px` / lang `0px` | **0** |

stub 的正/负对照同时成立：无 stub 时 `stubRan=0` 且无 `no-has`；有 stub 时 `stubRan=1` 且有 `no-has`。
⇒ 旧引擎与现代引擎**差值归零**；`html.no-has` 探针本身保留（`style.css` §30 仍是消费者）。
`live` 侧的 `float 132 / lang 68` 从此成为历史特例（随配置器一起退役）。

---

## 6. ⚠️ 事故与修复：`install` 把预检副本清空了

**现象**：候选断面第二次抓取时 **44/75 页变 301 → 首页**（`/formulas/` 归档 ＋ 21 详情 ×2 语言）。
不带预检头时同一 URL 是 200，带 cache-buster 也照样 301 ⇒ 不是 CF 缓存，是源站。

**根因**：`tools/b2d_s1_preflight.py` 的 `install()` 里写的是

```bash
git -C $REPO cat-file -e <sha>^{commit} && echo "commit present"
rm -rf $PRE
mkdir -p $PRE
...
```

候选 SHA 尚未被服务器仓库 `git fetch` ⇒ `git cat-file -e` 失败、打印 `fatal: Not a valid object name`，
**但脚本没有退出**：`set -e` 的例外条款写明「`&&` 列表里**除最后一条之后的**命令失败不触发退出」。
于是它照常执行 `rm -rf` ＋ `mkdir -p`，最后死在空 tar 上 —— **副本目录还在、里面是空的**。
主题注册的 CPT 不存在 ⇒ 该 CPT 的所有 URL 301 回首页。

**修法**（已落地）：
`if ! <check>; then echo FATAL >&2; rm -f $MU.tmp; exit 4; fi` ＋ 解包后
`[ -f $PRE/functions.php ] || exit 5` 兜底。

**影响面**：预检副本（脚手架，可由 SHA 重建）；live 主题、DB、契约文件**均未受影响**；
基线断面是在事故**之前**抓的，且已用存档双向验证。
**教训**：任何"先删后建"的脚本，前提检查必须是 `if`/`exit`，不能是 `A && B`（RULES §Q.3、技能铁律 11）。
**衍生规则**：换候选前必须 `git -C <server-repo> fetch --prune origin` —— 本地 push 到 GitHub
不等于服务器仓库有该对象。

---

## 7. 六条自我修正（全部是我的断言错，产品零问题）

1. **补丁器断言过严**：要求全文件不出现 `configurator.js`，但它在 5 条注释里存活（且必须存活）
   ⇒ 改为「去块注释后活代码 0 次 / 注释恰 5 次」。
2. **补丁器括号断言错**：原文件裸 `{`/`}` 计数本来就不相等（字符串与注释里也有）
   ⇒ 改为断言**相对基线的增减恰为 −1 / −1**。
3. **S4 文件数口径错**：`git ls-tree --name-only` 对非 ASCII 路径**加引号**，工作树另有未跟踪的
   `.DS_Store` ⇒ 349 vs 154 的假失败。改用 `-z`（NUL 分隔）并列清单比对，排除 `.DS_Store` / `_backup`。
4. **负对照把"崩溃"当"抓到"**：`functions.php` 缺失时靠 `FileNotFoundError` 退出 ⇒ 新增具名 **S0**，
   且负对照台要求「非零退出 **且** 有具名检查」。
5. **E3 点了会跳转的链接**（`href="/formulas/"`）⇒ 页面导航、哨兵被清、轮廓数假变化。
   改为捕获阶段 `preventDefault` ＋「仍在原页」断言。
6. **E5 字段口径不全**：`rect()` 少了 `bottom` ⇒ `gapWallEdgeToBand` 算成 NaN（JSON 里变 `null`）；
   `bandBtn` 少了 `w`。补齐后 **210 项对照全部一致**（字段从 20 扩到 35，含 `bandPad` /
   `exploreBoxSizing` / `exploreContentW` / `tocLinks` / `heroBtnHref` 等）。

---

## 8. 本批新造的 4 处死角 —— 登记 H6，本批不动

| # | 死角 | 实测规模 | 为何不动 |
|---|---|---|---|
| 1 | **K2 `.sf-formulas-data` 失去唯一读者**（原 `configurator.js:644`） | **60/75 页**携带、合计 **72,720 B**，最大 `/formulas/` 与 `/zh/formulas/` 各 9,504 / 9,441 B | `sinofresh_formula_grid` 属 K 系列契约冻结 |
| 2 | `formulas.js:110` 的 `getElementById('configurator')` 成死支 | 有 `if (target)` 保护 ⇒ 不报错 | K1 契约冻结 |
| 3 | `style.css:1220` 的 `.configurator__summary-value` 成死选择器 | `config-pdf.php` 不产出该类（已核） | 改 `style.css` 会触发 ver bump ⇒ 会污染本批"16 页 −2 行 / 59 页同"的锐利判据 |
| 4 | 会话键 `sinofresh_config_*` / `sinofresh_formula_*` 无写者无读者 | **E3 已现场取证**：页面上根本不存在这两类键（自 H2b1 起即成立） | 与 §5.1 的"零行为变化"证明是同一件事 |

**端点不孤岛**（保留有据）：`/wp-json/sinofresh/v1/config-pdf` 除被删脚本外，
`assets/js/basket.js:391`（Stage 4 购物篮导出 PDF）也在 POST 它。

---

## 9. 证据索引

| 文件 | 内容 |
|---|---|
| `docs/batch2d-stepH2b2-scan.md` | Step 0 扫描全档（含三处数字更正） |
| `docs/batchH2b2-gates/gate-main.txt` / `.json` | 主门（限定证明）运行记录 |
| `docs/batchH2b2-gates/gate-matrix.txt` / `gate-sabotage.json` | 破坏矩阵 10/10 |
| `docs/batchH2b2-gates/gate-negatives.txt` / `.json` | 三条负对照 3/3 |
| `docs/batchH2b2-gates/static-s1s9.txt` / `.json` | 静态门 S1–S9 |
| `docs/batchH2b2-gates/static-negatives.txt` / `.json` | 静态门负对照 6/6 |
| `docs/batchH2b2-gates/served-manifest.txt` | 预检副本 347 文件 sha256 清单 |
| `docs/batchH2b2-gates/live-vs-preflight-anchor.txt` | 双向 URL 锚点（live 停 2.10.55＋配置器 / 候选 2.10.56＋0 资产） |
| `docs/batchH2b2-gates/e2e-run.txt` / `e2e.json` | E1–E6 全量运行记录（含 210 项几何对照原值） |
| `docs/batchH2b2-shots/band-{480,768,1024,1100,1101,1440}.png` | 六档实拍（37–54 KB 真图，非空白） |
| `docs/batchH2b2-shots/no-has-stub.js` | 旧引擎 stub（含哨兵） |
| `_backup/b2d-h2b2-baselines/` · `_backup/b2d-h2b2-candidates/` | 两侧断面（各 75 页，本地卷） |
| `tools/b2d_h2b2_patch.py` · `_checks.py` · `_negctl.py` · `_confine.py` · `_e2e.py` | 本批工具链 |

---

## 10. 交 H3 的不变量

1. **上线不存在**：`git pull` 整体跳过；live 长期停 `2.10.55` ＋ 配置器是预期状态。
2. **基线 = 上一批的预检副本**，可随时由该批 SHA 重建（实测 347/347 逐字节）；
   **在下一批用完之前禁拆**。换候选前先 `git fetch`，且 `install` 的前置检查必须是 `if`/`exit`。
3. **H3 起，本批的候选断面 `_backup/b2d-h2b2-candidates/` 就是基线**。
4. 容器结构（H2b1 之后）：hero → facts-mini → 卡墙 `#formulas` → **band** → How We Work → FAQ → Related → Quote。
5. `:has(` 全站 **164**；`configurator.css` / `configurator.js` 已不存在，任何"迁回/补规则"都是回退。
6. H6 待办清单已由 4 项增至 **8 项**（本批 4 项见 §8，前 4 项见 H2b2 扫描 §5）。

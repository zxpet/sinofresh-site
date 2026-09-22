# 批次 H7b —— Hero 主 CTA 从「复制品名」改为「打开询盘弹窗」，右栏标题升级为真正的 h1

**状态**：Step 1–5 全部完成。门四件套全绿（75/75 主证、覆盖 23 项、不变式 7 项、遮蔽读回 0 差），
源码检查 28/28，破坏矩阵 8/8 抓到，具名负对照 NC1–NC8 8/8，浏览器 E2E 49/0，截图 12/12 非平帧。
**Step 6（`git pull` 上线）按规则跳过** —— 本批只交候选。

**提交**：`856303e`（主题 5 文件）→ `3bd5606`（门声明 ＋ 机制泛化）→ `e311136`（模板注释回撤 ＋ 语言无关化）
→ `f8aed3d`（手机步进修补 ＋ 顺序断言）｜**令牌** `2.10.62 → 2.10.63`（两处同步）＋
`formulas.js 1.2.0 → 1.3.0` ＋ `inquiry.js 1.0.0 → 1.1.0`。

**基线**：`d2b5bbd`（H7a 收尾，`2.10.62`）的预检副本 —— 本批**唯一**的字节基准。
**本批不改数据、不动业务字段、不扩范围**（DB 零写入）。

**用户裁决（2026-09-22）**：① Hero 的 `Reference this formula` → `Send Inquiry`（开弹窗）；② H7b
「缩水执行」—— 结构性两步已由 H5-0 完成（Hero 已是 `div`、右栏已持 `h1`），本批**只剩 CSS**；
③ 三个令牌并入本批。

---

## 0. 本批是什么形状

上一批（H7a）动的是媒体列与开关，形状是「删一段 ＋ 加一套」。H7b 完全不同：它把**一个元素的身份**
换掉 —— 按钮变锚点、复制变开弹窗 —— 而这件事一旦漏掉一处，站点上不会报错、不会有 500、门也看不见。

| | H7a | **H7b** |
|---|---|---|
| 改动性质 | 删列 ＋ 加开关 | **改身份**（`button`→`a`）＋ 一处 CSS 阶梯 ＋ 三处令牌 |
| 主证 | 逐页逐字节 | 逐页逐字节（同） |
| 新增的第 5 类判据 | — | **计数双向断言**（`counts`：同一个串在基线/候选两侧都要等于声明值） |
| 新增的第 6 类判据 | — | **顺序断言**（手机步进规则必须**排在**它覆盖的规则之后） |

本批四条主判据 ＋ 两条补充：

1. **字节证明** —— 折叠三个令牌、把声明的编辑逐个应用回基线后，逐页逐字节等于候选；
2. **覆盖断言** —— 旧裸串在**候选**上计数 0（负向前瞻）；新串在**候选**上等于声明值；
3. **计数双向断言** —— 14 行 `counts` 同时量**两侧**（`base` 与 `cand` 都要对），
   例如 `Reference this formula` 必须 `[202, 160]`、`data-form="` 必须 `[202, 160]`；
4. **不变式** —— 与声明无关的计数（60/42/42/75、每页 `h1`、`h2` 位移、JSON-LD 语义）两侧相同；
5. **遮蔽读回** —— 掩码抹掉的 GF 612 字节状态块单独解出来再比一次（23 页 / 0 差）；
6. **顺序断言** —— 判据不只看规则内容，还看两条规则的**先后**。

---

## 1. 实际执行的改动（声明清单）

**主题树累计（`git diff --numstat d2b5bbd f8aed3d -- sinofresh-theme/`）：**

| 文件 | 增 / 删 | 内容 |
|---|---|---|
| `templates/single-sf_formula.html` | +1 / −1 | Hero 主 CTA：`button` → `a`，文案改 `Send Inquiry`，加 `data-sf-inquiry-open` |
| `assets/js/inquiry.js` | +41 / −13 | 单元素查询 → 多元素；reveal 限定胶囊；`opener` 按 `currentTarget` 记录 |
| `assets/js/formulas.js` | +20 / −3 | 跳过带 `data-sf-inquiry-open` 的 CTA（防「toast 叠弹窗」） |
| `style.css` | +41 / −11 | 右栏标题字号阶梯 ＋ 锚点去下划线 ＋ 两处过时注释订正 |
| `functions.php` | +13 / −8 | 三处 enqueue 令牌 ＋ 两处过时注释订正 |
| **合计** | **+116 / −36** | **零新增库、零新增 JS 文件、零 DB 写** |

### 1.1 模板：一行，42 个详情页

```diff
-<button type="button" class="sf-formula__cta sf-formula__cta--solid" data-formula="{{TITLE}}" data-form="{{FORM_SLUG}}">Reference this formula →</button>
+<a class="sf-formula__cta sf-formula__cta--solid" href="/contact/#quote" data-sf-inquiry-open>Send Inquiry</a>
```

`href` 与胶囊、`Build Custom Formula` 一致 —— **无 JS 时降级为跳转 `/contact/#quote`**，不是死按钮。
`data-formula` / `data-form` 随之消失（`data-form` 早被 H6 判为死载荷）。
类对 `sf-formula__cta sf-formula__cta--solid` **保留**：它俩供的是那块品牌绿底，不是行为。

### 1.2 CSS：右栏标题 28px → 32px，加一条手机步进

```diff
 .sf-fdetail2__title {
-	margin: 0 0 16px;
-	font-size: 28px;
+	margin: 0 0 24px;
+	font-size: 32px;
 	font-weight: 700;
-	line-height: 1.2;
+	line-height: 1.3;
 	letter-spacing: -0.01em;
 	color: var(--wp--preset--color--text-primary);
 }
+@media (max-width: 480px) {
+	.sf-fdetail2__title {
+		font-size: 26px;
+	}
+}
```

另两处：`.sf-formula-hero .sf-formula__cta--solid` 与 `:hover` 各加 `text-decoration: none;`
—— 元素从 `button` 变 `a` 之后，theme.json 给每个链接的 hover 下划线会露出来，
「填充按钮在指针下长出下划线」读起来像「一个丢了按钮皮的链接」。填充色一字未动。

### 1.3 JS：`inquiry.js` 1.1.0 的三处（本批真正的风险点）

`querySelector`（单数）在改造前**恰好等于**「全部」，因为胶囊是全站唯一持有该属性的元素。
H7b 把同一属性给了 Hero CTA，而 **Hero 在文档里更早**（胶囊与弹窗都从 footer 打印），
所以单数查询会返回 Hero，把胶囊变成**惰性元素**：点击未绑定、`hidden` 永不摘掉、焦点永不回归。
无报错、markup 合法、**字节门看不见** —— 与 H4 咬过这个文件的 `wp_footer` 优先级是同一个形状。

```diff
-		var btn   = document.querySelector('[data-sf-inquiry-open]');
+		var openers = document.querySelectorAll('[data-sf-inquiry-open]');
+		var capsule = document.querySelector('.sf-float-btn--inquiry[data-sf-inquiry-open]');
 		var modal = document.querySelector('.sf-inquiry-modal');
-		if (!btn || !modal) {
+		if (!openers.length || !modal) {
 			return;
 		}
@@
 		function reveal() {
 			revealed = true;
-			btn.hidden = false;
-			btn.classList.add('is-visible');
+			if (capsule) {
+				capsule.hidden = false;
+				capsule.classList.add('is-visible');
+			}
 			...
 		}
-		if (!band) {
+		if (!band || !capsule) {
 			reveal();
 		} else { /* 滚动监听仍然只由 band 驱动胶囊 */ }
@@
-		function open() {
+		function open(from) {
 			if (!modal.hidden) { return; }
-			opener = btn;
+			opener = from || null;      /* 每次调用记录：焦点回到真正被点的那个 */
 			...
 		}
-		btn.addEventListener('click', function (event) {
-			event.preventDefault();
-			open();
+		Array.prototype.forEach.call(openers, function (el) {
+			el.addEventListener('click', function (event) {
+				event.preventDefault();
+				open(el);
+			});
 		});
```

### 1.4 JS：`formulas.js` 1.3.0 的守卫

```diff
 	var buttons = document.querySelectorAll('.sf-formula__cta');
 	Array.prototype.forEach.call(buttons, function (btn) {
+		if (btn.hasAttribute('data-sf-inquiry-open')) {
+			return;
+		}
 		btn.addEventListener('click', function () { ...复制品名 + toast... });
```

判据选**行为属性**（`data-sf-inquiry-open`）而不是 `--solid` 类：规则要说的是
「一次点击，一个结果 —— 凡开弹窗的，不许再叠一个 toast」，而不是「哪一页 / 哪个变体」。
卡墙的 160 个卡片按钮（`class="sf-formula__cta"` 计数两侧恒 160）类、属性、复制行为全不受影响。

---

## 2. 门的形状与结果（基线 `d2b5bbd`，候选 `f8aed3d`）

`python3 tools/b2d_h7_gate.py --batch h7b --base _backup/b2d-h7b-baselines --cand _backup/b2d-h7b-candidates --aa _backup/b2d-h7b-cand2 --matrix --negctl --json _backup/b2d-h7b-gate.json`

| 判据 | 结果 |
|---|---|
| **A/A 前置**（同一安装抓两次） | 75 页 / 0 页有差 —— 门在打开之前先证明自己是闭的 |
| **主证明** | 75 页比较 / **0 页有差** / 应用 **42** 处编辑 / 声明 **42** |
| **覆盖 · 缺席** | 4 条旧裸串在候选上计数 = 0（`--solid" data-formula=`、`?ver=2.10.62`、`formulas.js?ver=1.2.0`、`inquiry.js?ver=1.0.0`） |
| **覆盖 · 在场** | 5 条（`data-sf-inquiry-open`=84、`>Send Inquiry</a>`=42、`?ver=2.10.63`=75、`formulas.js?ver=1.3.0`=60、`inquiry.js?ver=1.1.0`=42） |
| **覆盖 · 计数双向** | 14 行全绿（两侧都对），含 `Reference this formula` `[202,160]`、`data-form="` `[202,160]`、EN href `[21,42]`、zh href `[21,42]`、`sf-float-btn--inquiry` `[42,42]`、`sf-gallery__tabs` `[42,42]` |
| **不变式** | 7 项：CTA 页 60/60、细节带 42/42、胶囊页 42/42、`ld+json` 75/75、**每页 `h1` 恰 1（0 页异常）**、`h2` 位移 0 页、**JSON-LD 解析后深比相等** |
| **遮蔽读回** | 23 页 / 0 坏 / 46 个非文本货币值核对 |
| **破坏矩阵** | **8/8 抓到**（见 §2.1） |
| **具名负对照** | **NC1–NC8 8/8**（见 §2.2） |
| **源码检查** | **28/28**（`--source`，落盘 `_backup/b2d-h7b-source.json`） |

### 2.1 破坏矩阵（8 个变体，每个都必须被抓到）

| 变体 | 判据 | 差异页数 |
|---|---|---|
| Hero CTA 没被替换 | 主证明 | 42 |
| 按钮留着、属性硬贴上去 | 主证明 | 42 |
| 样式令牌没折叠 | 主证明 | 75 |
| formulas 令牌没折叠 | 主证明 | 60 |
| inquiry 令牌没折叠 | 主证明 | 42 |
| 单独漏掉一个 Hero 文案 | 主证明 | 1 |
| 单独漏掉一页的属性 | 主证明 | 1 |
| 单独一页多一个杂字符 | 主证明 | 1 |

「差异页数 = 1」那三行是本批证明力的下限：**只差一个字节也必须报红**。

### 2.2 具名负对照

- **NC1** 掩码集合里不含任何 catch-all blob 掩码（`quoted_blob` / `long_b64_run` 已被 H6 剔除并记录在案）；
- **NC2** catch-all 掩码能藏住一处同偏移游程编辑，**真实掩码集合看得见**（`page=contact.html blind=True sighted=False`）
  —— 这一条是整套掩码的合法性依据；
- **NC3** 把任一 Hero 按钮放回去，覆盖断言失败；
- **NC4** 让任一 Hero 开场元素掉钩子，覆盖断言失败；
- **NC5** 注入一个 `h2`，不变式失败；
- **NC6** A/A 拿去和**另一个状态**比，失败；
- **NC7** 篡改一个 GF blob，遮蔽读回失败；
- **NC8** 改一个 JSON-LD 的键名，语义深比失败。

---

## 3. 源码检查（28/28，`--source`）

覆盖三条链：**令牌**（`style.css` 头 `2.10.63` ＋ `functions.php` 三处 enqueue，且旧值 0 残留）、
**模板**（Hero 是带降级 href 的锚点、兄弟 CTA 未动、模板上再无「复制品名」的载荷）、
**CSS**（32px/1.3/24px/字重保留、**手机 26px 且排在它覆盖的规则之后**、锚点保留按钮皮、hover 无下划线）、
**JS**（`inquiry.js`：绑定全部而非第一个、单数查询 0 残留、reveal 限定胶囊、焦点回随点击、每个 opener 自传自身；
`formulas.js`：跳过弹窗开场元素但仍绑类）。

> 手机步进那条写成了**跨两段的正则**：它同时要求「26px 存在」与「它出现在基础规则之后」。
> 只断内容不断顺序的判据，会放行那个在 480px 上永远不生效的死步进 —— 本批真发生过，见 §5.3。

---

## 4. 浏览器 E2E（49/0，`tools/b2d_h7b_e2e.py`）

**两态几何**（`_backup/b2d-h7b-geom-base.json` / `-cand.json`，均断言拿到的是哪一份资源）：

| 量 | 基线 `?ver=2.10.62` | 候选 `?ver=2.10.63` |
|---|---|---|
| `heroTag` / 文案 | `BUTTON` / `Reference this formula →` | `A` / `Send Inquiry` |
| `heroHref` / 属性 | `null` / `False` | `/contact/#quote` / `True` |
| `heroFamily` | `Arial` | `Inter, system-ui, …` |
| 开场元素数 | 1 | **2**（Hero 为第 1 个） |
| 卡片按钮 | 4 × `BUTTON`，无属性 | 3 × `BUTTON`，无属性 |
| 每页 `h1` | 1 | 1 |
| 标题 桌面 | `28px / 33.6px / 16px / 700` | `32px / 41.6px / 24px / 700` |
| 标题 手机 | `28px / 33.6px / 16px / 700` | `26px / 33.8px / 24px / 700` |

`heroFamily` 从 `Arial` 变 `Inter` 是**按钮与锚点的字体继承差异**，不是本批改字体 —— 记在这里，
免得下一批把它当成回归。

**功能断言（详情页）**：Hero 是 `A` 且文案/`href`/钩子齐全 → 页上恰 2 个开场元素且 Hero 第一 →
3 个卡片按钮仍是 `BUTTON`、文案未变、无属性 → `h1` 恰 1 → H7a 的开关仍在（1 个 tab、`photos`、
`aria-pressed=true`、无视频帧）→ 点 Hero 打开弹窗（`hidden` 摘掉、`body` 锁定、标题是 `Send Inquiry`、
写明品名 `Joint Support Soft Chews`）→ **无 toast**、URL 未跳走 → Escape 关闭 → **焦点回到 Hero** →
点胶囊仍能开弹窗、仍无 toast → 关闭按钮关闭 → **焦点回到胶囊**。
**剂型页**：无弹窗，卡片点击仍出 toast「Formula name copied. Paste it in your inquiry.」。
**手机（420px）**：标题 26px、`h1` 仍 1、Hero 仍是锚点且有盒子（126×44）、无横向溢出、弹窗可开。

**截图 12 帧**（`docs/batchH7b-shots/` 6 ＋ `docs/batchH7b-geom/` 6），全部经
`tools/_png_nonflat.py` 解压 IDAT 断言：**每帧 256 个不同字节值，0 帧平**。

---

## 5. 本批四处发现（每一处都改了判据或工具，不是「顺便记一笔」）

### 5.1 区块模板里的注释就是**页面字节**

`templates/single-sf_formula.html` 是 FSE 区块模板：区块分隔符之间的自由 HTML 注释**原样渲染进页面**。
我最初在模板里加了一段说明注释，结果它出现在候选页面上，把 `sf-formula__cta--solid` 读成 84（应为 42）、
`data-sf-inquiry-open` 读成 126（应为 84）。**删注释，解释移到 PHP/CSS/JS**，并把这条规则写进声明。

### 5.2 TranslatePress 按语言重写 `href`

同一份模板字节，在 21 个 EN 页上渲染为 `/contact/#quote`，在 21 个 zh 页上渲染为 `/zh/contact/#quote`。
硬编码 `/contact/#quote` 的变换会**应用 42 处却只匹配 21 页**。修法：`_h7b_transform` 用前瞻从兄弟锚点
`sf-formula-hero__build` 里**捕获**目标，两种语言各自成立；`counts` 里加两行分别盯 `[21,42]`。

### 5.3 媒体查询**不增加优先级** —— 手机步进曾经是死的

26px 那条最初被放进了本带缩略图所在的 `@media (max-width:480px)`（约 8286 行），
而基础规则在约 8462 行 —— 媒体查询不提高优先级，**基础规则在每一个宽度上都赢**，步进静默失效。
**只有浏览器量出 420px 仍是 32px**，字节门、源码检查、覆盖断言都看不见它。
修法：把步进移到基础规则**紧随其后**；并把门的正则改为**跨两段**，只断内容不断顺序的判据会放行它。

### 5.4 工具/探针自身的两个坑（已修／已记）

- **`agent-browser set headers` 按 origin 作用域**：必须在 `open` 把浏览器移到目标站**之后**再设，
  否则请求裸奔 → 剂型页被服务成「无样式表」；E2E 里加了 `assert_headers()`。
- **一次会话里连按两次 Escape 会把工具落到 `about:blank`**：那一轮的 7 条 FAIL 全是假绿/假红，
  实为「根本不在被服务的页面上」。改用 `.sf-inquiry-modal__close` 关闭，并给每次点击后加 `on_page()` 守卫 ＋
  `where()` 轨迹日志。
- **`_png_nonflat.py` 曾把「0 帧」报成 PASS**：它只吃目录参数，传文件时 glob 到 0 个却打印
  `PASS 0 frame(s)` 并 exit 0 —— **正是这个工具存在意义的那个静默全绿**。已重写：接受文件与目录，
  **0 帧 = FAIL（exit 2）**，非 PNG = FLAT，并加了非 PNG / 空目录两个负对照。

---

## 6. 用户裁决与「缩水执行」的对账

| 裁决 | 本批动作 |
|---|---|
| ① Hero `Reference this formula` → `Send Inquiry` 开弹窗 | ✅ `856303e`，模板 1 行 ＋ `inquiry.js` ＋ `formulas.js` |
| ② H7b「缩水执行」：结构性两步已由 H5-0 完成，只剩 CSS | ✅ 只做 CSS（32/1.3/24 ＋ 手机 26）—— **前提半失效已单独报告** |
| ③ 三个令牌并入本批 | ✅ `style.css` 2.10.63（两处同步）／`formulas.js` 1.3.0／`inquiry.js` 1.1.0 |
| 一 commit 或分两个（你判断） | 拆成 **4 个**：主题 / 门声明 / 模板修正 / 手机步进 —— 后两个各自对应一处被发现的问题，合成一个会埋掉「门当初漏了什么」 |
| 门判据（用户给的 5 条） | ✅ 逐条落地：属性 42×2=84、卡墙 160 不受影响、每页 `h1` 恰 1、无 JS 有 href 降级、`?ver=` 从产品足迹剥出 |
| 不停机（方向一致）／不引入库／commit＋push／自动接 H7c | ✅ 自动接 H7c |

**「前提半失效」的说明**：裁决②说结构性两步已由 H5-0 完成 —— 实际 H5-0 只完成了
「Hero 标题是 `div`」与「右栏持 `h1`」两件事，所以本批确实只剩 CSS，**没有额外结构改动**；
但 H7a 的扫描里还写着「Hero 的 `h1` 需要搬走」，那半句在 H5-0 之后已经过时。
本批只按裁决执行，未做任何结构搬移。

---

## 7. 证据清单

| 类别 | 路径 |
|---|---|
| 基线页 / 候选页 / A-A 副本 | `_backup/b2d-h7b-baselines/`、`-candidates/`、`-cand2/`（各 75 页 ＋ `MANIFEST.tsv`） |
| 门结果 | `_backup/b2d-h7b-gate.json`、`-matrix.json`、`-aa-baseline.json`、`-source.json` |
| 路径清单 | `_backup/h7b-paths.txt`（75 行） |
| 两态几何 | `_backup/b2d-h7b-geom-base.json`、`-geom-cand.json` |
| E2E | `_backup/b2d-h7b-e2e.json`（49 行全 ok） |
| 站点静止证明 | `_backup/b2d-h7b-fp-before.json`（`f6e7e15d…`，50 行，前后各取一次相同） |
| 截图 | `docs/batchH7b-shots/`（6）、`docs/batchH7b-geom/`（6） |
| 工具 | `tools/b2d_h7_gate.py`（h7b 声明）、`tools/b2d_h7b_e2e.py`、`tools/_png_nonflat.py` |
| 服务器快照 | `/root/preflight-snapshot-h7b-before-2.10.62.tar.gz`（64 MB） |

**服务器状态**：预检副本从 `f8aed3d` 安装 → 线上复核 `style.css?ver=2.10.63` 且 `link` 指向
`sinofresh-theme-preflight/`；详情页实测 `data-sf-inquiry-open` × 2、`>Send Inquiry</a>` × 1、
`Reference this formula` × 3（＝3 个卡片按钮）、`<h1` × 1、`class="sf-inquiry-modal"` × 1。

**下一批（H7c）的基线 = 本批收尾提交**（`2.10.63`），禁止与 H7a 时期的副本混用。

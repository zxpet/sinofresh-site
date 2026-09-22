# 批 H2b1 详细方案：配置器删除（结构层）＋ `.sf-explore` 带迁位 ＋ CTA 改向

> **状态**：方案待确认（**未动手**）。主题零改动，DB 未动，服务器未 pull。
> **前置**：`docs/batch2d-stepH2b-scan.md`（Step 0 扫描）＋ `docs/agent-playbook.md` §9【H2b1】（已按 2026-09-22 裁决更新）。
> **拆分**：**H2b1**（本文）＝结构/样式；**H2b2** ＝停入队 + 删资产。两批各跑完整 Step 0→6。

---

## 一、范围

| | 内容 |
|---|---|
| **IN** | ① 8 剂型页删除配置器区块 ② `.sf-explore` 带（title + chips + Products 按钮）迁到**卡墙之后、How We Work 之前** ③ 8 剂型页 hero + 详情页 hero 的 CTA 改向 ④ `.sf-explore*` 125 行 CSS 从 `configurator.css` 迁入 `style.css` ⑤ `style.css:5915-5921` 补偿归还 ⑥ `.sf-explore` 通栏尺寸重定 ⑦ `style.css` ver bump |
| **OUT** | `functions.php` enqueue（**H2b2**）、资产文件删除（H2b2）、`configurator.js` 侧 `config-pdf` 调用删除（H2b2）、`formulas.js`/`basket.js`/`config-pdf.php`/`formula-pools.php`（**K1-K7 契约，全程零改动**）、DB（零改动） |

**变更规模（精确）**

| 项 | 值 |
|---|---|
| 8 页删除 | **1,241 行 / 145.2 KB**（含 `<!-- Block 4: Configurator -->` 标签行） |
| 8 页插入 | **96 行 / 5.2 KB**（每页 12 行新 section） |
| 8 页净减 | **1,145 行 / 140.0 KB** |
| `configurator.css` | 958 → **833 行**（−125） |
| `style.css` | 8,777 → **≈8,895 行**（+125 迁入 −7 补偿） |
| 停传体积（本批已生效） | 8 页各少传 ≈18 KB HTML |

**改动传播范围（Step 1 更正）**

> 本方案初稿（与 Step 0 扫描）把 DIFF 集合写成「16 页 = 8 剂型 en + 8 zh」，**漏了详情页那一行**：
> `templates/single-sf_formula.html` 是**全部 21 个剂型的单一模板**（en + zh 共 42 页都由它渲染），
> 所以 §2.2 的详情页 CTA 改向会让**全部 42 页**都变。已核实：`#configurator` 在主题模板里只出现
> 9 次——8 个 `page-*.html` 各 1 次（hero CTA）＋ `single-sf_formula.html` 1 次（hero CTA）；
> `functions.php:203` / `formulas.js:15` 是**注释**，`style.css:5920` 是本批要删的死规则，均不产生锚点。

| 页族 | 页数 | 本批是否变 | 原因 |
|---|---|---|---|
| 剂型页 en（`/products/<form>/`） | 8 | **变** | 删配置器 + 带迁位 + hero CTA |
| 剂型页 zh（`/zh/products/<form>/`） | 8 | **变** | 同上 |
| 详情页 en（`/formulas/<slug>/`） | 21 | **变** | hero CTA（`{{FORM_HREF}}#configurator` → `/contact/#quote`） |
| 详情页 zh（`/zh/formulas/<slug>/`） | 21 | **变** | 同上 |
| 其它（首页／about／contact／blog／归档…） | 17 | 不变 | 只许 ver 令牌移动 |
| **合计** | **75** | **58 DIFF / 17 SAME** | |

---

## 二、实现方式

### 2.0 统一走patcher，不手改

新建 `tools/b2d_h2b1_patch.py`（`--check` 只验不写／`--apply` 写入）：

- **前置断言**：逐页锚点**逐字节**匹配才动手（`<!-- Block 4: Configurator -->` + `<!-- wp:group …` + `<!-- /wp:group -->` 三元组 + 块内 `id="configurator"` 唯一）；任一页不匹配 ⇒ 整体拒绝，不做半途修改
- **写入后自查**（同一进程重读文件，防「编辑回执 ≠ 落盘」）：
  1. 块注释配平：每页 `<!-- wp:` 计数 − `<!-- /wp:` 计数 = 0（与基线同）
  2. `id="configurator"` 计数 = 0；`href="#configurator"` 计数 = 0
  3. 新带子 5 行 **sha256 前缀 = `835c81666e2a`**（＝基线 8 页共同值，逐字节未动）
  4. 行数差 = −205 / −154 / −141 / −137 / −137 / −124 / −124 / −123（soft-chews / dental-chews / tablets / powders / fish-oil / pastes / liquids / drops）

### 2.1 8 剂型页：删块 + 带迁位（同一处替换）

**替换区间**：L55 `<!-- Block 4: Configurator -->` … 块尾 `<!-- /wp:group -->`（逐页行号见下表）

| 页 | 替换区间 | 带子原位 | 净行变化 |
|---|---|---|---|
| `page-soft-chews.html` | 55-271 | 226-230 | −205 |
| `page-dental-chews.html` | 55-220 | 175-179 | −154 |
| `page-tablets.html` | 55-207 | 163-167 | −141 |
| `page-powders.html` | 55-203 | 159-163 | −137 |
| `page-fish-oil.html` | 55-203 | 159-163 | −137 |
| `page-pastes.html` | 55-190 | 147-151 | −124 |
| `page-liquids.html` | 55-190 | 147-151 | −124 |
| `page-drops.html` | 55-189 | 146-150 | −123 |

**替换为（每页 12 行，逐字节相同）**

```
<!-- Block 4: Explore more dosage forms (moved out of the configurator, batch H2b1) -->
<!-- wp:group {"tagName":"section","className":"sf-explore-band","layout":{"type":"constrained"},"style":{"spacing":{"padding":{"top":"0","bottom":"var:preset|spacing|80"}}}} -->
<section class="wp-block-group sf-explore-band" style="padding-top:0;padding-bottom:var(--wp--preset--spacing--80)">
<!-- wp:html -->
    <div class="sf-explore">
      <h3 class="sf-explore__title">Explore more dosage forms</h3>
      [sf_explore_chips]
      <a class="sf-explore__btn" href="/products/">Browse All Products &rarr;</a>
    </div>
<!-- /wp:html -->
</section>
<!-- /wp:group -->
```

**设计取值与理由**

- **带子 5 行原样保留（含 4/6 空格缩进）**，不改一字 ⇒ 换来一条硬断言：「迁位前后 sha 相同」（`835c81666e2a`）。缩进不整齐对渲染零影响；**取值＝保留原缩进**（0/2 空格重排方案会牺牲该断言，未采用）。
- **section padding = `top 0 / bottom 48px`**（`--wp--preset--spacing--80` 实测 = **48px**，见 playbook 附录 A.4-7）：`卡墙 padding-bottom 48` ＋ `带子 padding-top 0` = **48px** 标准节奏；带子读作卡墙的"尾巴"，落在"客户看完当前剂型配方之后"这个位置。备选 `top 48px`（＝双倍 96px）未采用；E7 以 **48px** 为验收阈值。
- **`sf-explore-band` 类**只为 E2E/DOM 顺序断言与后续 CSS 挂钩，不参与视觉。
- 带内 `Browse All Products →`（`/products/`）与卡墙 L50 的 `Browse All Formulas →`（`/formulas/`）是**两个不同出口**，均保留（见 §六 D2）。

### 2.2 CTA 改向（8 剂型页 hero + 详情页 hero）

| 文件 | 现 | 改为 |
|---|---|---|
| `page-*.html` L22（8 页同串） | `…wp-element-button" href="#configurator">Build Custom Formula</a>` | `…wp-element-button sf-quote-cta" href="/contact/#quote">Build Custom Formula</a>` |
| `templates/single-sf_formula.html` L13 | `<a class="sf-formula-hero__build" href="{{FORM_HREF}}#configurator">Build Custom Formula</a>` | `<a class="sf-formula-hero__build sf-quote-cta" href="/contact/#quote">Build Custom Formula</a>` |

**为什么是 `sf-quote-cta` 而不是裸 `/contact/`**（严格照 §9【H2b】3「改向 `/contact/`」执行，只补 `#quote`）：

- `quote-cta.js 1.0.0` **已是全站入队的既有契约**（`functions.php:39-40`），selector `a.sf-quote-cta`、目标 `#inquiry-form, #quote, #booking-form`；**页内有表单 → 本地平滑滚动；无表单 → 原生跳转**。与 header/footer `Get a Quote` 完全同款 ⇒ **零新增 JS、零新契约**。
- 剂型页 L590 有 `<section id="inquiry-form">` ⇒ hero 按钮保持**原始设计意图**（hero 两个按钮原本都是页内锚点：`#formulas` / `#configurator`），点完直接落到本页询盘表单。
- 详情页 `id` 只有 `gallery`（无页内表单）⇒ 该 class **不改变行为**，纯原生跳 `/contact/#quote`（＝ playbook 字面）。
- 无 JS 时 href 属性本身就是 `/contact/#quote` ⇒ 天然降级（E2E 会断言这一条）。
- ⚠️ 该 class 是"页内滚动"开关：去掉它则该按钮直接跳 `/contact/#quote`（一行级改动，见 §六 D1 备选列）。

### 2.3 CSS 迁移：`configurator.css:833-957` → `style.css` 末尾

**为什么必须"迁入即删原地"**：`style.css` 在 `functions.php:31` 入队、`configurator.css` 在 `:188` 入队 ⇒ **后者后加载**，同选择器**后者胜**。若只迁入不删原地，新值会被旧值**静默覆盖**（无报错、页面看着"没生效"）。

1. `configurator.css` 删除 **833-957**（含 `/* === Explore more dosage forms … */` 注释头与两个 `@media`）
2. `style.css` **末尾追加**（保持"后加载覆盖"语义；文件内加醒目分节注释 `/* === xx. Explore more dosage forms band (migrated from configurator.css, H2b1) === */`）
3. 追加时**归零 margin**：`.sf-explore{margin-top:24px}` → `0`；`@media(max-width:768px){.sf-explore{margin-top:20px}}` 该行删 —— 带子已是独立 section，不再需要与"上一配置组"拉开
4. **通栏重定（视觉验收项）**：桌面由 65% 窄栏变通栏，CSS 注释里"为在 1440px 一行放下 8 chip 而调紧"的前提失效：

| 选择器 | 现 | 取值（H2b1 落地） | 说明 |
|---|---|---|---|
| `.sf-explore` | `padding:32px` | `padding:32px` 不变 | 通栏卡片，8px 圆角保留 |
| `.sf-explore__chips` | `gap:6px` | **`gap:8px`** | 通栏有余量，8 chip 一行仍富余 |
| `.sf-explore__chip` | `padding:8px 12px; font-size:13px` | **`padding:10px 16px; font-size:14px`** | 与 §5 chips 规范（14px）对齐；`6px` 圆角保留（是"探索标签"非"多选标签"） |
| `.sf-explore__btn` | 桌面 `inline-block` | 不变 | 仍靠左 |
| `≤768px` | chips `nowrap` + 横滑；btn 通栏 | **原样保留** | 移动端原本就近似通栏，行为无回退 |

`:has(` 账：那 125 行内**无 `:has(`** ⇒ 迁入后 `style.css` 仍 164；H2b2 删文件后全站 **171 → 164**（不增，符合约束）。

### 2.4 `style.css:5915-5921` 补偿归还（整块删）

```css
@media (max-width: 768px) {
	/* Tighten Standard Formulas -> configurator gap … */
	.sf-formulas { padding-bottom: 0 !important; }
	#configurator { padding-top: 32px !important; }
}
```
- `.sf-formulas` 的 `padding-bottom` 还原为模板 inline 的 48px；`#configurator` 成死规则，一并删
- 删后移动端节奏：卡墙 48（模板）＋ 新带子 section top 0 = **48px**，比原来的 24+32=56px 略紧 —— 由 Step 5 移动端视觉验收判定（要回到 56px 只需给带子 section `padding-top:8px`）

### 2.5 ver bump（两处同步，认锚点别认行号）

- `functions.php`：`wp_enqueue_style('sinofresh-style', …, '2.10.55')` → **`'2.10.56'`**
- `style.css` 头部：`Version: 2.10.55` → **`2.10.56`**
- `configurator.css`：内容已变（−125 行）⇒ `functions.php:188` 的 `'2.9'` → **`'2.10'`**（该文件 H2b2 才停入队，但本轮已改内容，缓存必须失效）
- `configurator.js` `'2.3'` **不动**（本轮不改）

---

## 三、核验

### 3.1 静态自检（本地，改完立即跑）

| # | 断言 | 判据 |
|---|---|---|
| S1 | 8 页块注释配平 | 每页 `<!-- wp:` == `<!-- /wp:`；逐页与基线同 |
| S2 | 带子未被改动 | 8 页新带子 5 行 sha256 前缀 == `835c81666e2a` |
| S3 | 锚点归零 | 全主题 `id="configurator"` = 0；`href="#configurator"` = 0（注释里的说明文字不计入） |
| S4 | **选择器唯一性** | 迁入的 16 个 `.sf-explore*` 选择器：`style.css` 各定义 1 次、`configurator.css` 各 0 次 |
| S5 | `:has(` 账 | `style.css` 164（不变）、`configurator.css` 7（不变，迁移块内无 `:has(`） |
| S6 | 行数账 | 三处文件行数与 §一 预期一致（`configurator.css` −125；8 页净减 1,145） |
| S7 | 语法 | `php -l functions.php`；CSS 用括号/花括号配平检查（`configurator.css`、`style.css`） |
| S8 | 契约未动 | `git diff --stat` 里**不得出现** `formulas.js`/`basket.js`/`config-pdf.php`/`formula-pools.php`/`inc/**` |

### 3.2 门（预检副本 `X-SF-Preflight: 1`，75 页）

| # | 门 | 判据 |
|---|---|---|
| G1 | `sf_masked_cmp.py`（先 `--aa` 自检） | **58 DIFF（8 剂型 en + 8 zh + 21 详情 en + 21 zh）+ 17 SAME**；ver 令牌先归一化（`2.10.55→2.10.56`／`2.9→2.10`） |
| G2 | **限定证明（主门，marker-driven）** | 逐页**字节级**改写基线得到 expected，再与候选逐字节比对（只归一化 `?ver=` 令牌）。分两族：**剂型页**＝把基线里 `<section id="configurator"…>…</section>`（平衡切割）整段换成**候选自己的新带子 section 字节**，且断言该 section 内的 band `<div class="sf-explore">…</div>` 与**基线里的 band 逐字节相同**（防"带子被自洽篡改"）；**详情页**＝把基线 hero 构建按钮替换成声明的确切串。另断言逐页 hunk 数（剂型页 2、详情页 1、其它 0）与改动区间位置。**不只比"哪些页变了"，而是比"变的正是声明的那一处、且内容派生自基线"** |
| G3 | **负对照** | 候选副本故意改 1 字节（如 `&rarr;`→`→`）必须 DIFF；未改的 59 页必须 SAME；缺参照必须显式 FAIL |
| G4 | **破坏矩阵**（≥6 变体，每个必须被抓到） | ① 漏删 `wp:heading` ② 带子留在原位 ③ 带内少 1 个 chip ④ CTA 未改向 ⑤ ver 未 bump ⑥ `configurator.css` 残留旧 `.sf-explore` 定义 |
| G5 | JSON-LD（K6）逐字节不变 | 8 剂型页 **＋ 42 详情页**：`h1=1 / desc=1 / spec-terms=0 / legacy=0`（详情节 21 页）；JSON-LD 片段 sha 与基线相同 |
| G6 | 结构断言 | 8 剂型页渲染序：`#formulas` → `.sf-explore-band` → How We Work；页面内 `Build Your … Formula` **H2 归零**；42 详情页 hero 构建按钮 `href` = `/contact/#quote` 且带 `sf-quote-cta` |

### 3.3 浏览器 E2E（真浏览器 + 真凭据；`agent-browser close --all` 先清缓存）

| # | 项 | 判据 |
|---|---|---|
| E1 | 五档视口 480/768/1024/1440 + 1100/1101 边界 | 零水平溢出（`scrollWidth ≤ clientWidth+1`）、0 页面错误 |
| E2 | 点轨（≥1101px） | 条目 **= 5**；第 2 条 = **How We Work**；点击第 1 条落 `#formulas`（几何校验） |
| E3 | 带子几何 | 桌面宽度 ≈ 内容列宽（通栏）；移动端 chips 单行横滑（`scrollWidth > clientWidth`）、`is-current` 落在当前剂型 chip 上 |
| E4 | hero CTA 行为 | 点击后 `location.hash === '#inquiry-form'` 且**几何到位**（`#inquiry-form` 顶与视口顶差 ≤ `scroll-margin-top`+2px） |
| E5 | 无 JS 降级 | 禁 JS 后 `href` 属性 == `/contact/#quote`（详情页 E2E：点击落到 `/contact/`，且 `#quote` 标题就位） |
| E6 | 卡墙按钮样式存活（②的验收） | L50 `Browse All Formulas →` 的 `getComputedStyle`：`border 2px solid rgb(27,77,62)`、`color` 同、`padding 12px 24px`；与基线截图并排比对 |
| E7 | 移动端节奏 | 卡墙底 → 带子顶 = **48px**（几何量）+ 截图 |
| E8 | 遗留引擎分支 | stub `window.CSS.supports` 返回 false ⇒ `html.no-has` 存在；**记录 `.sf-float-stack` / `.trp-language-switcher` 的 `bottom` 实测值**（H2b2 删 `configurator.css:700/705` 后要回到此基线，见附录 A.4-1） |
| E9 | 几何 vs 截图双证据 | 一律以 `getBoundingClientRect` 为准；截图另开高视口（防 cookie 横幅遮挡 / 高于视口的元素画成空白） |

### 3.4 服务侧（Step 6，上线后）

- live 版本断言：`style.css?ver=2.10.56`、`configurator.css?ver=2.10`（断言资产 URL，**不是**只看页面 200）
- 75 页掩码门复跑（live）+ 身份链（697/0 口径）+ `sf_repo_md5.py` 回填
- 日志：按「**每一条都能归因**」逐条 `--allow` 记账（判别符 = user + 状态码 + UA；80/443 两份都要给；窗口外属上一批的也要给）
- **报告不能是它所报告集合的成员** ⇒ 两侧 `--exclude`，报告最后生成

---

## 四、约束

1. **不碰 DB**（无 `update_post_meta`/`update_option`/迁移）⇒ 本批**没有**「零留痕」判据，但也不豁免：`wp_posts`/`wp_postmeta` 计数与 sha 仍要在报告里给出前后对照（证明没被顺手动过）
2. **不改数据/不改契约**：`formulas.js`、`basket.js`、`config-pdf.php`、`formula-pools.php`、`inc/**` 零改动
3. **不停入队、不删文件**（全部留到 H2b2）
4. **预检副本不改 live**：`install <全 40 位 SHA>` 后，候选页必须带 `X-SF-Preflight: 1`；拆预检副本属「不执行」（等你）
5. 一切 curl/浏览器/抓取带 `-u 'sfdev:…'`（**明文**，禁 base64）—— 不带＝两侧同一 401 页＝静默全绿
6. `git pull` 上线属「不执行」：**Step 6 前停下等你一句话**
7. **停机条件**（立即停下汇报）：门 FAIL 且无法归因／破坏矩阵有漏网／E2E 出现无法归因的错误／发现需要改数据／实测与本文档不符

---

## 五、汇报点（Step 划分）

| Step | 内容 | 自动/停 |
|---|---|---|
| **1** | `tools/b2d_h2b1_patch.py` 编写 + `--check`（只验不写，输出 8 页锚点匹配报告） | 自动 |
| **2** | `--apply` 改 8 页模板（删块 + 带迁位 + CTA 改向）＋ S1–S3 自检 | 自动 |
| **3** | CSS 迁移 + 补偿归还 + 通栏重定 + ver bump ＋ S4–S8 自检 | 自动 |
| **4** | 预检副本：`fetch` → `install <40 位 SHA>` → G1–G6（含负对照与破坏矩阵） | 自动 |
| **5** | 浏览器 E2E E1–E9（含真浏览器 + 无 JS + 遗留引擎分支）＋ **完整报告** | **停：等你批准上线** |
| **6** | 八步上线闭环（`pull --ff-only` + 服务侧验证 + md5 回填 + 日志归因 + 文档记忆） | 停（`git pull` 属「不执行」） |
| **7** | 自动进 H2b2（停入队 + 删资产），同样跑完整 Step 0→6 | 自动 |

> Step 5 报告处为**放行点**：`git pull` 在 playbook【不执行】清单内，需你放行才执行；Step 1–5（含全部门与 E2E）自动跑。

---

## 六、已定的默认取值（决策记录：依据 ＋ 改动锚点）

> 三项**均已按 playbook 与既有契约拍定**，非待确认项；备选列仅作决策留痕，便于日后回溯。

| # | 取值 | 依据 | 备选（未采用） | 改动锚点 |
|---|---|---|---|---|
| **D1** | CTA = `href="/contact/#quote"` ＋ `sf-quote-cta`（剂型页内平滑滚动到本页 `#inquiry-form`；详情页原生跳转） | playbook §9【H2b1】3「改向 `/contact/`」＋ `quote-cta.js 1.0.0` **全站入队**的既有契约（`functions.php:39-40`）＝零新增 JS | ① 不加该 class ⇒ 剂型页也不再页内滚动、直接跳走 ② 详情页改 `{{FORM_HREF}}#inquiry-form` ⇒ 落到剂型页表单而非联系页 | 8 页 L22 ＋ `templates/single-sf_formula.html:13`；E4/E5 断言随之变 |
| **D2** | 带内 **保留** `Browse All Products →`（`/products/`），与卡墙 L50 `Browse All Formulas →`（`/formulas/`）并存 | 「纯位移」原则：带子整条搬、内容一字不改（换来 sha `835c81666e2a` 硬断言）；且两个 href 是**不同出口** | 删该行（1 行 × 8 页）⇒ 带子只剩 title ＋ chips | 8 页新块第 8 行 |
| **D3** | 带子 section `padding: 0 / 48px` | `--wp--preset--spacing--80` 实测 = **48px**；带子读作卡墙"尾巴"（裁决 D 的语义）⇒ 上方沿用卡墙的 48px 底边距，避免双倍 96px | `48px / 48px`（＝96px 全章节间距） | 8 页新块第 2/3 行（`wp:group` 属性 ＋ inline style）；E7 阈值随之改 |

---

## 七、风险与已知副作用

| # | 风险 | 处置 |
|---|---|---|
| R1 | 迁移后旧定义残留 ⇒ 静默覆盖 | S4 选择器唯一性硬断言 + G4-⑥ 破坏矩阵变体 |
| R2 | 8 页 H2 少了 `Build Your … Formula` ⇒ 点轨 6→5 | 已裁决记预期变化；E2 正向断言第 2 条 = How We Work |
| R3 | `.sf-explore` 由窄栏变通栏，视觉可能失衡 | E3/E7 几何 + 截图双证据；未达标则调 §2.3-4 表格里的三个值 |
| R4 | 移动端卡墙→带子由 56px 变 48px | E7 量出实际值，由视觉验收裁决是否补 8px |
| R5 | 详情页 `sinofresh_formula_*` sessionStorage 写侧失去读者（`configurator.js` 是唯一读者） | **本批不改** `formulas.js`（K1 契约）；记 H6 候选（已写入 playbook 附录 B） |
| R6 | 8 页渲染 HTML 少 ≈18 KB、少 1 个 H2 与 1 张 sprite | 纯减法，无新增结构化数据；对 SEO/GEO 无负面（§原则 4） |
| R7 | `.sf-float-stack`（全局页脚元素）在遗留引擎下被 `configurator.css:705` 抬高 132px | H2b1 只**量基线**；H2b2 删文件后必须回到 `style.css` 基线（已入 playbook 附录 A.4-1） |

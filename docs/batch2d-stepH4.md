# 批次 H4 全档 —— 询盘弹窗 + 悬浮胶囊

> **状态：Step 1–5 全过门 + E2E 全过（31 ok / 0 FAIL）；Step 6（`git pull` 上线）按用户 2026-09-22 规则整条跳过。**
> 主题提交 **`92dee472239edcaf8f209efa561ac3016a45a564`**（含两次修复 `a75640a`、`ef4ee12`）。
> 基线 **＝H4e 的预检副本断面** `_backup/b2d-h4e-candidates`（`ver=2.10.57`）。
> 候选 **`_backup/b2d-h4-candidates`**（`ver=2.10.59`）＋ A/A 第二份 `_backup/b2d-h4-candidates-aa`。
> **无 DB 改动**（本批纯主题侧）。
> 前置扫描档：`docs/batch2d-stepH4-scan-body.md`（含四项裁决 D1–D4）。

---

## 0. 结论速览

| 项 | 结果 |
|---|---|
| 主题 diff | **5 文件**：`functions.php`（+393 起）、`assets/js/inquiry.js`（新，约 250 行）、`style.css`（+439）、`parts/footer.html`（1 行）；ver **2.10.57 → 2.10.59**（两次 bump：2.10.58 与对齐修复的 2.10.59） |
| 主门（解码式限定证明） | **PASS — 12 条门 0 FAIL**：75/75 页；`strip_declared(候选)` 归一化后**逐字节＝基线** |
| 破坏矩阵 | **17/17** 全 CAUGHT |
| 具名负对照 | **5/5** 全部按名失败 |
| A/A 自检 | **PASS** —— 只余**故意的 [1]**，零误报 |
| H3 单测复跑 | **54 passed / 0 failed** ＋ 负对照 **6/6**（本批未破坏 H3 断言） |
| 浏览器 E2E | **PASS — 31 ok / 0 FAIL**（E1–E11），0 console error；**连续三遍全绿**（30 / 30 / 31） |
| 实拍 | **8 张**，全部远超 8000 B 下限（39 KB – 709 KB） |
| 变更页数 | **42/75**（21 EN 详情 + 21 ZH 详情）；**33 页零变更**（无胶囊、无弹窗、无 `inquiry.js`） |
| 计划外 | **2 个产品缺陷**（均由浏览器门抓到、已修）＋ 6 条工具教训，见 §2 / §3 |

---

## 1. 本批最重要的结论：字节门对这两个缺陷是瞎的

主门在**修复前**的候选上就已经是 **0 FAIL**。缺陷出在字节门看不见的两个维度：

1. **顺序**（脚本与它要读的标记谁先谁后）；
2. **几何**（一个更宽的兄弟节点把已有兄弟挤走）。

两者都**不在**任何一条被比对的字节里，所以 `cmp` 式的门无论多严格都只能打出全绿。
这正是浏览器门存在的理由 —— 也是本批最大的收获：**H4 引入了一个只能由行为门守住的改动类别**。

---

## 2. 缺陷一：弹窗打印在它自己的脚本之后（`a75640a`）

### 症状

E2E 首跑：胶囊**永不出现**、弹窗**永不打开**，而**控制台零错误**、DOM 齐全、`role=dialog` 齐全。

### 根因

`inquiry.js` 是**经典页脚脚本**（无 `defer`/`async`），在**解析期同步执行**；
而弹窗由 `add_action('wp_footer', 'sinofresh_inquiry_modal', 20)` 输出 ——
`wp_print_footer_scripts` 同样挂在 `wp_footer` 的 **优先级 20**，且注册在先，所以脚本先打印。
脚本首个守卫 `if (!btn || !modal) { return; }` 每次都成立 ⇒ 监听器一个都没挂上。

实测（候选抓包内字节偏移）：

```
inquiry.js      116986
弹窗标记        122203      ← 脚本在前
```

### 修法（两处，一个因）

| 处 | 改动 |
|---|---|
| `functions.php` | 弹窗优先级 **20 → 5**，让标记落在读它的脚本之前（＝页脚模板部件给 basket overlay 用的同一档） |
| `assets/js/inquiry.js` | `init()` 包裹，`document.readyState === 'loading'` 时改为 `DOMContentLoaded` 再初始化 —— **不再依赖一个它看不见的钩子优先级**，将来任何插件重排页脚都仍然成立 |

修复后实测：弹窗 **115275** ＜ 脚本 **120494**。

---

## 3. 缺陷二：更宽的胶囊把三个圆钮挤左 98px（`92dee47`）

### 症状

E2E 第二跑：**只在胶囊可见时**，既有三个悬浮圆钮从 `x=1364` 跑到 `x=1266`（右边缘 24 → 122）。

### 根因

`.sf-float-stack` 是 `position:fixed; right:24px` 的 **shrink-to-fit flex 列**，且**从未声明交叉轴对齐**。
列宽由**最宽的子女**决定：

- H4 之前：三个都是 52px 圆 ⇒ 列宽 52，问题不存在；
- H4 之后：胶囊 150px ⇒ 列宽 150，而**有显式宽度的子女在 `align-items:stretch` 下退化为 flex-start** ⇒
  三个圆落在列**左**边缘，距右边缘 98px。

**这是对既有悬浮栈几何的真回归** —— 而 H2b1 量过的那组偏移（100 / 24 / 268 / 16）正是本批要保的东西。

### 修法

`.sf-float-stack` 增加 `align-items: flex-end`。三个子女同宽时**是空操作**（所以对 33 个无胶囊页面无影响，
对既有三圆页也无影响），胶囊自身的 `align-self: flex-end` 随之删除 —— **一个机制胜过两个**。
`style.css` 变更 ⇒ **ver 2.10.58 → 2.10.59（`functions.php` ＋ `style.css` 头部两处同步）**。

修复后实测：四个按钮右边缘统一 **24px**（移动端 16px），间距 **12 / 12 / 12**，胶囊在最上（y=656）。

---

## 4. 声明范围与不变量

### 声明的三样新增（门的判据）

| 新增 | 落点 | 判据 |
|---|---|---|
| 胶囊 `[sf_inquiry_button]` | `parts/footer.html` 内 `.sf-float-stack` 的**首位** | 42 页，且＝参数带页面集合 |
| 弹窗 `sinofresh_inquiry_modal()` | `wp_footer` 优先级 5 | 同上 42 页 |
| `assets/js/inquiry.js` | 仅 `is_singular('sf_formula')` 入队 | 同上 42 页 |

`strip_declared()` 把这三样**逐字节**摘掉后，候选 75 页与基线**归一化后完全相同** ⇒ 本批的净效应就是这个声明，
没有夹带。

### 会话行数（实测，非推断）

弹窗「Your Selection」由**服务端按 post id 重算**，不是客户端传来的：

| 标签 | 出现次数 | 说明 |
|---|---|---|
| `Piece Weight` | 42 | 21 记录 × 2 语言，42/42 都有 |
| `Pack Size` | 20 | 20 条记录有 → 10 EN + 10 ZH 显示**两行**，其余**一行** |

`Flavor` / `Suitable For` / `Life Stage` / `Quantity & Pricing` 仍 **0/42** —— 与 H2a/H3 同一种
「渲染器先行、数据后补」状态，不属本批范围。

---

## 5. 门与四件套（全部产物在 `docs/batchH4-gates/`）

```
# 主门（解码式限定证明）
python3 tools/b2d_h4_confine.py \
  --baseline _backup/b2d-h4e-candidates \
  --candidate _backup/b2d-h4-candidates \
  --json docs/batchH4-gates/main-gate.json          # → main-gate.txt : PASS, 0 FAIL

# A/A 自检（同一状态两份独立抓取）
python3 tools/b2d_h4_confine.py --baseline _backup/b2d-h4-candidates \
  --candidate _backup/b2d-h4-candidates-aa --aa      # → aa-selftest.txt : PASS（只余故意 [1]）

python3 tools/b2d_h4_confine.py --baseline _backup/b2d-h4e-candidates \
  --candidate _backup/b2d-h4-candidates --matrix     # → matrix.txt : 17/17 CAUGHT
python3 tools/b2d_h4_confine.py --baseline _backup/b2d-h4e-candidates \
  --candidate _backup/b2d-h4-candidates --negctl     # → negctl.txt : 5/5 按名失败
```

主门 12 条（[0] 两侧身份／[1] 新增普查＋版本令牌／[2] 限定证明／[3] 33 页零变更／[4] 胶囊结构／
[5] 既有三钮不变／[6] 四步单一真源／[7] 会话标签集合／[8] 解码后地址＝`sales@`／[9] JSON-LD 不变／
[10] 不变量／[11] 表单完整性）**全 ok**。

### ⛔ 本批门的两条新铁律

1. **A/A 模式两侧都要 `strip_declared`**：A/A 的「基线」是**候选状态的第二次抓取**，它**同样带全部新增**；
   只摘一侧会把 42 个弹窗页全部误判为「超出声明的差异」。主跑里基线没有新增，摘它等于空操作 —— 所以
   **两侧都摘**是正确且统一的写法。
2. **A/A 的溯源目录也是预检副本**：`want_dir` 不能因 `expect_change=False` 就换成 `sinofresh-theme/`。

---

## 6. 浏览器 E2E（`tools/b2d_h4_e2e.py`，E1–E11）

| 项 | 断言 |
|---|---|
| **E1** | 页首胶囊 `hidden`（bandTop 677 > 500 阈值）；**真实滚轮**下滑到参数带越过视口中线后出现；**单向**（滚回页首仍在） |
| **E2** | 既有三钮**像素级不动**（(1364,720)/(1364,784)/(1364,848)）；胶囊是栈内**首位**子元素；四钮同右边缘 24px、间距 12、胶囊最上；标签 `Send Inquiry`、降级 `href=/contact/#quote` |
| **E3** | `hidden` 撤销 + `is-open` + `display:flex`；body 锁定；`role=dialog` + `aria-modal`；焦点入 `<input name=name>`；面板 560px；**两行会话**（Piece Weight 2g/piece ／ Pack Size 60/90/120 per bottle）；四步文案＝`sinofresh_sampling_steps()`；表单携带 post id 158；**弹窗真的盖住悬浮栈**（胶囊坐标处命中背板） |
| **E4** | Esc 关闭 + 解锁 + **焦点归还胶囊**；面板内点击不关闭；背板点击关闭 + 解锁 |
| **E5** | 蜜罐**最先**被拒（同一载荷带合法时钟）⇒ `Submission rejected.`；未进成功态；表单保留 |
| **E6** | 打开后 **1117ms / 1628ms** 提交 ⇒ `Please take a moment to complete the form.`；且断言**时钟确实重打**（`ts` 跨打开必须变化） |
| **E7** | 真实投递：成功面板替换表单、`Thank you — your inquiry is on its way.`、**2.5s 自关** |
| **E8** | ZH 详情页同款胶囊与弹窗（文案为英文：新串尚未进 TranslatePress）；`/about/` **无胶囊、无弹窗、无 `inquiry.js`** |
| **E9** | 单行记录页（Bladder Support Powder）只有 `Piece Weight` 一行 |
| **E10** | 390×844：三个 44px 圆 + 136px 胶囊，**右间距 16px**；面板＝整屏宽贴底抽屉（390×844 @ y=0） |
| **E11** | 全程 **0 console error** |

**E7 真发了邮件**（每次运行一封，标记 `H4 E2E`）：本批共 **5 封**，收件人＝`sf_contact_email`
（＝`sales@zxpet.com`）。这既验证了投递链路，也验证了收件人确实来自选项而非硬编码。

---

## 7. 工具侧六条教训（都写进了代码注释）

1. **`elementFromPoint` 判等太严**：点胶囊命中的是它内部的 `span.sf-float-btn__label`，不是 `<a>` 本身。
   判据应改为「点落在目标的子树内」（`closest('.目标')`）—— 既容忍子元素，又能抓住坐标漂移。
2. **不能要求四个按钮同宽**：胶囊本来是胶囊形。判据是「三个圆＝52/44 + 四者共享右边缘 + 间距 12」。
3. **弹窗打开时胶囊**物理上点不到**（背板铺满视口）⇒ 点它之前必须先关闭，否则会把「点到背板」误读成「胶囊坏了」。
4. ⛔ **长会话会漂移**：跑了几十次往返后浏览器落到 `about:blank` 或 `chrome-error://chromewebdata/`，
   于是所有读数都在描述那个空白文档 —— **看起来完全像「胶囊从 DOM 里消失了」**，上一轮因此产生了一整屏假产品结论。
   修法：状态探针**先看 `location.href`**，发现漂移就**重启会话**（`close --all` → 凭据 → 打开 → 设头 → reload）
   并**走带溯源断言的路径**重开，而不是继续在坏会话上下结论。
5. **状态读取失败必须大声拒跑**，不能返回空对象让后面的断言去「推断缺失」——
   「an impossibly fast submission reached the success state」就是这么来的假报告。
6. 端口探针自身要带 `try/catch`，并把失败原因（而非布尔）报出来：`form_ready` 现在会说
   「没弹窗 / 没打开 / 表单不是可见块 / 时钟没打上」。

---

## 8. 截图（`docs/batchH4-evidence/`，8 张）

| 文件 | 内容 | 体积 |
|---|---|---|
| `h4-01-desktop-top.png` | 详情页页首：**还没有**胶囊 | 491 KB |
| `h4-02-desktop-capsule.png` | 滚到参数带后：胶囊出现在三钮之上，共享右边缘 | 709 KB |
| `h4-03-desktop-dialog.png` | 弹窗：两行会话 + 四步打样 + 五字段表单（焦点在 Name） | 426 KB |
| `h4-04-desktop-honeypot.png` | 蜜罐被拒（端点可达且在拒） | 439 KB |
| `h4-05-mobile-capsule.png` | 390×844：44px 圆 + 136px 胶囊，16px 右间距 | 75 KB |
| `h4-06-mobile-sheet.png` | 移动端整屏贴底抽屉 | 40 KB |
| `h4-07-zh-dialog.png` | ZH 页同款（英文文案，待翻译） | 381 KB |
| `h4-08-plain-page.png` | 普通页：什么都没有 | 430 KB |

---

## 9. 四项裁决的执行回写（供手册 §【H4】 采用）

| # | 裁决 | 执行结果 |
|---|---|---|
| D1 | **A：会话行取自当前配方元数据**（`sinofresh_inquiry_selection_rows()` 读与参数带**同一份** meta） | 已实现；服务端 **再算一次**、不信客户端 ⇒ 实测 42 页 1 行、20 页 2 行 |
| D2 | **A：胶囊落悬浮栈内首位、胶囊形** | 已实现；**栈因此必须自己右对齐**（§3） |
| D3 | **A：胶囊就是栈内那个胶囊**（不另设页内按钮） | 已实现；42 页同款，33 页零变更 |
| D4 | **A：纯邮件**（不抄送客户、不做自动回复） | 已实现；收件人读 `sf_contact_email`，失败 `error_log` 且**不假装成功** |

**同时按手册 §【H4】 原文核销的既有要求**：
① 三步反垃圾全部在**服务端**（蜜罐／3 秒下限＋未来时间戳／字段校验）且**逐条实测**；
② 四步打样文案**复用** `sinofresh_sampling_steps()`（门 [6] 逐页比对四个标题）；
③ 收件人**读选项**，未硬编码；
④ 移动端抽屉已实测为整屏贴底。

---

## 10. 未做 / 不做

- **Step 6 上线（`git pull --ff-only`）整条跳过** —— 按用户 2026-09-22 规则；工作区是唯一真源，
  dev live 继续停在上线前的断面。
- **预检副本不拆**：它同时是 H4 的候选断面，也是**下一批（H5）的基线**，用完前禁拆。
- **无 DB 改动** ⇒ 无需快照/回滚。

## 11. 交给 H6 的新待办（第 11 项）

| # | 事项 | 来源 |
|---|---|---|
| 11 | ⛔ **成功之后重开弹窗仍显示「Thank you」，没有复位路径**：`form.hidden`/`success.hidden` 一旦翻转就不再复原，所以提交过的访客再点胶囊看到的是确认页而不是空表单。不属本批范围（本批没写复位），登记待决 | 本批 E2E E7 |

（H6 待办由 10 项增至 **11 项**。）

# 批次 H2b1 —— 剂型页去掉配置器、`.sf-explore` 带移位（结构与样式）

> 状态：**候选已过门 + E2E，等 Step 6**（`git pull --ff-only` 属「不执行」清单）。
> 改动内容：8 个剂型页删掉配置器整块（1,241 行）、把 `.sf-explore` 带（标题 + 剂型 chips +
> Browse All Products）整体搬到**卡墙之后、How We Work 之前**（裁决 D 的落点）；hero CTA 从
> `#configurator` 改成 `/contact/#quote` + `sf-quote-cta`（复用已入队契约，零新增 JS）；
> `.sf-explore*` 125 行 CSS 从 `configurator.css` 迁到 `style.css`；归还 `style.css:5915-5921`
> 的移动端补偿；ver bump。
> **不是零差异批**：58 页（16 剂型 + 42 详情）按声明必须变，其余 17 页只许版本令牌移动。
> 本批**不含** dequeue、不含删资产、不碰 DB、不改契约 —— 那些属 H2b2。

## 关键提交

`ebe8f505be6707536d5187fde617fab42b613311`（`ebe8f50`），已 `push origin/main`，
`git status` 对主题目录干净。

## 交付物与改动面

| 文件 | 改动 |
|---|---|
| `templates/page-{soft-chews,tablets,powders,pastes,drops,liquids,fish-oil,dental-chews}.html` | 删 `<!-- Block 4: Configurator -->` 整块；在原槽位（L55 起）插入 12 行 `.sf-explore-band`；hero CTA 换新形态 |
| `templates/single-sf_formula.html` | L13 hero 锚点：`{{FORM_HREF}}#configurator` → `/contact/#quote`，class 加 `sf-quote-cta`；面包屑的 `{{FORM_HREF}}` 保留 |
| `assets/css/configurator.css` | 125 行 `.sf-explore*` 迁移并**原地删除**；958 → 832 行；ver 2.9 → 2.10 |
| `style.css` | 接收 127 行 `.sf-explore*`；删 L5915–L5921 补偿；8,778 → 8,899 行；`Version: 2.10.56` |
| `functions.php` | `wp_enqueue_style(sinofresh-style)` ver 2.10.55 → 2.10.56 |

13 份候选文件哈希表：`docs/batchH2b1-gates/served-hashes.txt`（与工作树逐字节相同）。

## Step 1–2 结构改动（`tools/b2d_h2b1_patch.py`）

按 `<!-- Block 4: Configurator -->` 标记定位 + `<!-- wp:group -->` **栈式配对**求区间（先剥
自闭合 `<!-- wp:x /-->` 再计数，H2b 扫描器正是栽在这一步），并与扫描表的行号交叉核对。

| 页面 | 区间 | 删除行 | 应用后 delta | 带 sha12 | balance |
|---|---|---|---|---|---|
| page-soft-chews | L55–L271 | 217 | **−205** | `835c81666e2a` | 0 → 0 |
| page-tablets | L55–L207 | 153 | −141 | `835c81666e2a` | 0 → 0 |
| page-dental-chews | L55–L220 | 166 | −154 | `835c81666e2a` | 0 → 0 |
| page-powders | L55–L203 | 149 | −137 | `835c81666e2a` | 0 → 0 |
| page-fish-oil | L55–L203 | 149 | −137 | `835c81666e2a` | 0 → 0 |
| page-pastes | L55–L190 | 136 | −124 | `835c81666e2a` | 0 → 0 |
| page-liquids | L55–L190 | 136 | −124 | `835c81666e2a` | 0 → 0 |
| page-drops | L55–L189 | 135 | −123 | `835c81666e2a` | 0 → 0 |

删 1,241 行 / 插 96 行（8 × 12）= **净 −1,145 行**，与「替换区间 L55→`<!-- /wp:group -->`」的
预期逐页吻合。带子 5 行**逐字节搬运**，sha12 恒为 `835c81666e2a` —— 这是「搬家不是重打」的判据，
并且门 [3] 额外要求带本身必须与基线（live）逐字节相同，防止「自洽地被篡改」。

**可复现性门**（`tools/b2d_h2b1_repro.py`，本批新增）：用 `git archive ebe8f50~1` 搭沙盒，
把两个补丁器重跑一遍，再与提交比对 —— **12/12 文件逐字节相同**，`patch_ok=true`、`errors=[]`。
这补上了一个原本存在的证据洞：`_backup/b2d-h2b1-apply.json` 是**修正断言之前**的首次运行快照，
带 `"ok": false` 和一条 `{{FORM_HREF}} count moved` 的错误行（真实数量是 2→1，不是 2→2，
断言本身写错了）。权威记录改以 `docs/batchH2b1-gates/step1-2-reproduction.json` 为准。

## Step 3 CSS 迁移（`tools/b2d_h2b1_css.py`）

- `configurator.css` 块 L833–L957（125 行 / 3,036 B）→ 迁移后 127 行；文件 958 → **832** 行
- `style.css` 8,778 → **8,899** 行；`:has(` 计数 **164 / 7 不变**（口径＝出现次数）
- 15 条 `.sf-explore*` 规则头迁走，`configurator.css` 残留 **0 条**
- ⛔ **迁入即删原地**：`style.css` 在 `functions.php:31` 先加载、`configurator.css` 在 `:188`
  后加载，留一份副本会**静默覆盖**新值。核验＝选择器唯一性（新 1 次 / 旧 0 次），已入门 [4]
- 删补偿：`style.css` L5915–L5921（7 行）`@media (max-width:768px){.sf-formulas{padding-bottom:0!important} #configurator{padding-top:32px!important}}`
- ver 三处：`functions.php` 与 `style.css` 头部 `2.10.55 → 2.10.56`、`configurator.css` `2.9 → 2.10`
- `php -l functions.php`：No syntax errors detected（`php` 不在 PATH，脚本内置 Local 侧候选路径）

数值回正（实测，live → 候选）：chip 字号 **13px → 14px**、padding **`8px 12px` → `10px 16px`**、
chips gap **`6px` → `8px`**、`.sf-explore` `margin-top` **24px → 0**（移动端 `margin-top:20px` 一并去掉，
`padding:24px` 保留）。

## Step 4 门与核验

**静态 S1–S8 全过**（`docs/batchH2b1-gates/static-s1s8.json`）：分隔符配平且嵌套合法（8 页 + 详情）、
带 sha ×8 / 每页 1 个 section、模板内零 `#configurator`、详情 `sf-quote-cta`=1 / `href="/contact/#quote"`=1 /
`{{FORM_HREF}}`=1 / `{{FORM_CRUMB}}`=2、规则头归属 0/15、`:has(` 164/7、行数 832/8899、
`php -l` 干净、diff 不触碰契约文件。

**基线/候选各 75 页**：全部 200。基线侧 `#configurator` 恰好出现在 **58 页**（＝声明的变更集），
候选侧所有资产 URL 含 `-preflight`（provenance：不带这个 header 就会拿到 live 主题，而一切看起来都正常）。

**主门 `tools/b2d_h2b1_confine.py`：PASS，21 条 ok，0 FAIL**（`gate-main.txt` / `gate-main.json`）：

1. 资产版本：基线 75/75 `2.10.55`；候选 75/75 `2.10.56`；`configurator.css` 只在 16 个剂型页 `2.9 → 2.10`；其余资产不动
2. 页集：折叠 `?ver=` 后**恰 58 页差 / 17 页同**；未折叠时 75/75 全差（证明折叠只藏了声明的令牌）
3. 限定证明：58 页全部由基线字节**手术重建后逐字节相等**；带与基线逐字节相同；配置器 H2 8 页 1→0；全站无 `#configurator` 锚点残留
4. 13 份文件与服务端逐字节相同；4 个契约文件在位且未改；`configurator.css` 已无 `.sf-explore*` 规则头
5. 58 页 JSON-LD 逐字节不变；58 页恰 1 个 h1
6. 16 页渲染顺序 `#formulas → band → How We Work`；hero CTA 16 页各 1 次；42 详情页带声明锚点

**破坏矩阵 10/10 全被抓**（`gate-sabotage.json`，`missed: []`）：`keep-h2` / `band-not-moved` /
`chip-missing` / `cta-not-retargeted` / `ver-stale` / `old-css-left` / `stray-byte-on-a-stable-page` /
`declared-page-unchanged` / `detail-cta-reverted` / `band-entity-changed`。

**三条负对照全 FAIL（as required）**（`gate-negatives.txt`）：A 带内一个实体 `&rarr;`→`→`（渲染完全相同）⇒ FAIL；
B 缺 served-hash 参照 ⇒ FAIL 而**非 skip**；C 候选＝基线 ⇒ 9 行 FAIL。

**范围更正（Step 1 发现）**：方案原测「16 页差」。详情页 CTA 在 `single-sf_formula.html`
一个模板里服务 21 个配方 × 2 语言 ⇒ 真实集合是 **58 页（16 + 42）**。基线抓取独立佐证了这一点：
`#configurator` 恰在那 58 页上。

## Step 5 浏览器 E2E（`tools/b2d_h2b1_e2e.py`，E1–E9 全过）

`docs/batchH2b1-gates/e2e-run.txt` / `e2e.json`，截图 `docs/batchH2b1-shots/band-*.png`。

| # | 判据 | 结果 |
|---|---|---|
| E1 | 480/768/1024/1100/1101/1440 六档横向溢出 = 0；band 恰 1 个 | PASS |
| E2 | 点轨 **5 项**（live 6 项，`Build Your Soft Chews Formula` 随配置器消失）、第 2 项 `How We Work`、≤1100px 隐藏 | PASS |
| E3 | band 通栏（`x=0`、`w=vw` 六档）；面板居中（gutter 38/38、88/88）；8 枚 chip；14px / `10px 16px` / gap 8px；`is-current`=Soft Chews；≤768 单行可滑、≥1024 换行且无滚动 | PASS |
| E4 | hero CTA → hash `#inquiry-form`，**落定在 `scroll-margin-top` 96px 上**（96 vs 96.0），href `/contact/#quote`，class 含 `sf-quote-cta` | PASS |
| E5 | 原始字节 href：剂型 en `/contact/#quote`、zh `/zh/contact/#quote`；详情锚点原生化跳转落 `/contact/#quote` | PASS |
| E6 | 卡墙按钮与 live **逐值相同**（≤768：`12px 18px` / block / min-height 44px；≥1024：`12px 24px` / inline-block），描边/圆角/颜色不变 | PASS |
| E7 | 墙 `padding-bottom: 48px` **六档皆成立**（live 在 ≤768 被补偿压成 0）；band 恰落在「一个站内块间距」之下 ⇒ 边距 24px、距最后一行卡片 72px | PASS |
| E8 | `html.no-has` 只在 stub 下出现（负对照 `False` / 正对照 `True`，stub 执行 1 次） | PASS |
| E9 | 六张**实图** 37–54 KB，取景避开 sticky 头部 | PASS |

**live vs 候选几何对照**：`docs/batchH2b1-gates/geom-live-vs-candidate.txt`（`tools/b2d_h2b1_geom.py`
同一页渲两遍、同一批量同时打两列）。关键对照：

| 量 | live | 候选 | 性质 |
|---|---|---|---|
| `band`（section） | 不存在 | `x0 w=vw` 六档 | **声明变更**（通栏） |
| `.sf-explore` 1440 | `x120 w754`（塞在 `.configurator__options` 754 里） | `x88 w1264`（=1200 内容列 + 2×32 padding，`content-box`） | 声明变更 |
| `wallPadBottom` ≤768 | **0** | **48** | 补偿归还 |
| `chipFont` / `chipPad` / `chipsGap` | 13px / `8px 12px` / 6px | 14px / `10px 16px` / 8px | 声明变更 |
| `bandBtn` 六档 | — | **与 live 完全相同** | 未触碰 |
| `wallH2`（内容列） | 六档相同 | 六档相同 | 未触碰 |
| `wallContentBottom` | 六档相同 | 六档相同 | 未触碰 |
| `tocDisplay` | ≤1100 none / ≥1101 block | 相同 | 未触碰 |

## 计划外但已实测的行为变化：两个固定层落位（**已判定为收敛，非回归**）

删掉配置器条之后，`configurator.css:675-684` 的 `body:has(.configurator__bar)` 叠层规则
**永不匹配**，于是两个固定层（`.sf-float-stack`、TranslatePress 切换器）落回 `style.css` 自身取值；
而 **`:700` / `:705`** 那两条 `html.no-has` **无条件复刻**（不受 `.configurator` 限定）仍然生效。
（行号勘误：两条分别为 `html.no-has .trp-language-switcher` 与 `html.no-has .sf-float-stack`，见 H2b2 扫描 §7。）
480px 四格取证（`tools/b2d_h2b1_geom.py`，「有/无 stub」两态）：

| | 无 stub（现代引擎） | 有 stub（旧引擎） |
|---|---|---|
| **live** | float `132px` / lang `68px` | float `132px` / lang `68px` |
| **候选** | float `268px` / lang `0px` | float `132px` / lang `68px` |

再加两处对照（候选、横幅在场）：1440px ⇒ float `100px` / lang `0px`；无横幅 ⇒ 1440 `24px`、480 `16px`。
而**非剂型页**（`/about/`，本来就没有配置器）在同样条件下是 1440 `100px` / 480 `268px` / lang `0px`
—— **与候选剂型页完全一致**。

⇒ 结论：H2b1 让 8 个剂型页的固定层**收敛到全站其余页面的取值**（live 上它们被条顶到 132/68 属历史特例），
这是删条的自然结果，**不是回归**。用户已确认通过（2026-09-22）。
**用户同时更正两处**：① playbook 明确不执行上线 ⇒ 本批 **Step 6 `git pull` 跳过**；
② **H2b2 的基线是 H2b1 后的预检副本，不是 live**，且预检副本**保留不拆**。

## 六条自我修正（记功）

1. **方案页数算错（16 → 58）**：一个详情模板服务 42 页。靠**抓取断面**而不是推理改正（`#configurator` 恰在 58 页）。
2. **E3 断言是猜的**：拿 `content-box` 的面板（1264 = 1200 + 2×32）去比外层满宽 section，
   于是把一件正确的事报成「不是通栏」。改成实测不变式（`band.x=0 & band.w=vw`、gutter 左右相等）。
3. **E6 断言忽略了 ≤768 分支**：按钮在窄屏是 `12px 18px` / block / 44px。改成「与 live 逐值相同」，
   比硬编码期望更强，也不再是我自己的猜测。
4. **E7 期望值少算了一项**：站内节奏是 48（墙内边距）+ 24（块间距）= 72，而 live 的边距同样是 24/72。
5. **E4 采样早于动画结束**：平滑滚动约 1.2s 才落定，固定 sleep 抓到 177px 而误报。改成轮询 `scrollY`
   直到连续两次相同，并**钉住 `scroll-margin-top`**（96 vs 96.0）而不是一个拍出来的容差。
6. **E9 截图是空的**：`agent-browser screenshot <selector> <path>` 在本机写出 1.7 KB 白图（元素 1440×259），
   文件在、看着像证据、其实什么都没有。改成「滚到目标 + 视口截图」，并加**字节下限**把空白变成失败；
   取景还要扣掉 sticky 头部（该头部在 `scrollY=0` 时是 `static`，滚动后才被 JS 立起来，所以偏移必须**两段式**测）。

## 工具缺口与教训（写给 H2b2 与下一批）

1. ⛔ **`AGENT_BROWSER_INIT_SCRIPTS` / `--init-script` 必须覆盖「启动浏览器的那条命令」**，
   而那条命令是 `set credentials`，不是 `open`。挂在 `open` 上＝注册太晚、脚本静默不执行
   （E8 首次就是这么假绿的）。`agent-browser 0.27.0` **没有** `addinitscript` 子命令，
   尽管它自带的文档里写着有 —— 文档与二进制不一致，以二进制为准。四项排序全部实测：见
   `docs/batchH2b1-gates/e8-init-script-probe.json`。
2. ⛔ **`agent-browser screenshot <selector> <path>` 出空图**（见自我修正 6）。凡「元素截图」必须加体积下限。
3. ⛔ **断言要先在候选文本上跑，再落盘**：`apply_detail` 第一版先写后断言，且期望值写错，
   于是一次**正确**的编辑被报成失败（并且文件已被改写）。改法＝pure 校验（写前后各一次）＋同进程回读。
4. ⛔ **不要用固定 sleep 等动画**：轮询到「连续两次相同」才算落定。
5. ⛔ **凡「不是零差异批」的批次，证据快照要留可复现入口**：本次补上 `b2d_h2b1_repro.py`，
   把「提交字节＝工具产物」变成一条可重跑的门，而不是一句声明。

## H2b2 交接不变量

1. **整文件删除**（行号勘误，见 `docs/batch2d-stepH2b2-scan.md` §1/§7）：原先写的「`configurator.css:667-707` 整段」**行号不成立** ——
   `:667` 只是块内注释首行、**`:707` 不是任何块的边界**；真正的容器是 `@media (max-width: 767px) {`（**L642**），
   它一直开到**文件末尾 L831**。`html.no-has` 两条复刻在 **L700 / L705**，`:has(.configurator__bar)` 叠层在 L643/675/682/689/690。
   H2b2 删整个文件即覆盖全部；只删 `:has()` 那几条、留下 L700/L705，会让旧引擎保留独有的 132/68，与「删条」自相矛盾。
   全站 `:has(` 由 **171 → 164**（口径＝出现次数；其中 configurator.css 的 7 次有 2 次在注释里）。
2. **判据可复用四格法**：480px × 有/无 stub × live/候选，比 `.sf-float-stack` 与 `.trp-language-switcher` 的 `bottom`。
3. **`.sf-explore*` 已不在 `configurator.css`**（残留 0 条，门 [4] 守着）；H2b2 删文件时应复核这一条不变量。
4. `html.no-has` 探针本身**保留**（`style.css` §30 有消费者）。

## 证据索引

| 文件 | 内容 |
|---|---|
| `docs/batchH2b1-gates/static-s1s8.json` | 静态 S1–S8 |
| `docs/batchH2b1-gates/served-hashes.txt` | 13 份候选文件哈希 |
| `docs/batchH2b1-gates/gate-main.{txt,json}` | 主门 21 条 ok / 0 FAIL |
| `docs/batchH2b1-gates/gate-sabotage.json` / `gate-matrix.txt` | 破坏矩阵 10/10 |
| `docs/batchH2b1-gates/gate-negatives.txt` | 三条负对照 |
| `docs/batchH2b1-gates/step1-2-reproduction.json` | 可复现性：12/12 逐字节 |
| `docs/batchH2b1-gates/e2e-run.txt` / `e2e.json` | E1–E9 全程与逐档测量 |
| `docs/batchH2b1-gates/geom-live-vs-candidate.txt` | live/候选同批量的两列对照 |
| `docs/batchH2b1-gates/e8-init-script-probe.json` | init script 四种排序的实测 |
| `docs/batchH2b1-shots/band-{480,768,1024,1100,1101,1440}.png` | 六档实图 |
| `_backup/b2d-h2b1-baselines/` / `-candidates/` | 各 75 页断面 + MANIFEST |

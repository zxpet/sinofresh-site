# Batch 2D · Step E — 剂型页删三段（8 个剂型页变成纯列表页）

> 状态：**已上线并闭环**。上线 commit `df31199`，闭环 commit `87bb4cc`（门+证据）、
> `f0eceaa`（渲染证明+日志审计）。全仓 md5 **1288 文件 / 0 差异**。
> 本批是**纯删除批**：只删不加，代码/CSS 全部保留，给 F1 复用。

## 0. 一句话

8 个剂型页（`/products/{soft-chews,tablets,powders,pastes,drops,liquids,fish-oil,dental-chews}/`
及 8 个 `/zh/` 对应页）删掉三段，变成「Hero → 卡墙 → 配置器 → How We Work → FAQ →
相关产品 → CTA」的纯列表页；版本 `2.10.51 → 2.10.52`。

## 1. 删了什么（每个模板 74 行，共 592 行，0 插入）

| 段 | 定位方式 | 说明 |
|---|---|---|
| B2D-S5 核心事实带 + Direct Answer | `<!-- B2D-S5: core facts -->` … `<!-- /B2D-S5 -->` | 上一批刚上的 |
| `sf-spectable` 典型规格表 | group JSON `"className":"sf-spectable"`（早于批注记号，无 marker） | |
| B2D-S1 活性成分包装段 | `<!-- B2D-S1: actives -->` 开标记 + `/wp:group` | |

**保留**：`[sf_formula_actives]`、`[sf_formula_detail_actives]` shortcode 全部注册；
`.sf-spectable` / `.sf-actives__*` / `.sf-facts` 的 CSS 规则全部保留。

## 2. 两个决策点（开工前拍板）

1. **FAQ 保留**（决策 1-A）：目标结构漏写 FAQ，FAQ 不是重复事实来源，留在原位。
2. **详情页 hero meta 退化接受**（决策 2-A）：详情页 meta 行由剂型页 spectable 单元格拼出
   （`sinofresh_formula_spec_cell()` → `{{FORMULA_META}}`），本批后 21 个详情页 + 21 个
   `/zh/` 详情页的 meta 从
   `Soft Chews · MOQ from 500–1,000 units · Lead time 7–15 working days after packaging is ready`
   退化为 `Soft Chews`（函数的文档化 fallback）。**F1 把 spec_cell 重新指向新的事实来源。**
   ⇒ 这 42 页纳入预期 DIFF 集合。

## 3. 门（六门 + 负对照）

工具：`tools/b2d_e_apply.py`（删段重写器）、`tools/b2d_e_confine.py`（六门）。
报告：`docs/b2d-stepE-gates.txt`（PASS）、`docs/b2d-stepE-negctl.txt`（负对照 RC=1）。

| 门 | 结果 |
|---|---|
| 0 候选确来自预检副本 | 75/75 页带 `X-SF-Preflight: 1` |
| 1 资源清单 | 仅 `style.css` 2.10.51→2.10.52（75 页）；资产集合变化 **0** |
| 2 掩码比较 + 预期 DIFF 集合 | differ **58**（8 剂型 + 8 zh 剂型 + 21 详情 + 21 zh 详情）/ identical **17**，**集合精确命中，0 偏差** |
| 3 页级限定证明 | **58/58** 逐字节还原（删除批方向＝**在基线上删块再比候选**） |
| 4 源级重建 | 10 文件（style.css / functions.php / 8 模板）`applied:YES / undone==base:YES`，模板各 −2993…−3183 B 两段 |
| 5 JSON-LD 深比较 | **75/75** identical |

**负对照 187 条，RC=1**。注意：负对照里门 5（JSON-LD）仍 75/75 identical —— 它看不见
「什么都不做」的自比，这正是门 1 必须以不变量形式存在的理由。

### 建门时踩的三个 bug（都在候选跑之前/中修掉）

1. **模板侧锚点误写成渲染侧字面量**：`sf-spectable` 的模板锚点写成了
   `<section class="wp-block-group sf-spectable `（渲染侧才有，模板里 0 处）。
   ⇒ 渲染侧与模板侧锚点**分开命名**。
2. **路由分类器永远匹配不到**：`'__products__' in name` 匹配不到 `products__soft-chews`
   （没有前导下划线），16 个剂型页静默落进详情页分支。⇒ `startswith('products__')`。
3. ⛔ **删除批的限定证明方向写反**：删除批应「**在基线上删块**，结果必须逐字节等于候选」；
   第一版仍在候选里删。它照样产出 58 条 FAIL —— **总数看起来完全合理，但理由是错的**。
   教训：**方向错不会被计数发现，必须逐条读失败理由。**

## 4. 上线（先过门再上线）

```
git fetch → 装预检副本（git archive df31199…，副本哈希与本地已提交字节逐位相同）
→ X-SF-Preflight:1 抓 75 页 → 六门 PASS + 负对照 RC=1
→ 批准 → 服务器 git pull --ff-only → f4f43b6 → 87bb4cc（ff，工作树干净）
```

上线前实测：live 服务 `2.10.51`、三段 9 处 marker 在、无预检头走 live 主题目录。
上线后实测：`style.css?ver=2.10.52`、三段 marker **0**、`themes/sinofresh-theme/`、
无凭据 **401**。

## 5. 闭环证据（`docs/b2d-stepE-shots/`）

| 项 | 结果 | 产物 |
|---|---|---|
| A/A 掩码自检 | PASS（172949/172949 B） | — |
| 掩码闭环 `new` vs `live` | **75/75 identical**（候选带预检头、live 不带，双 MANIFEST 存证） | `closure.json` |
| 三方身份链（拆预检前） | workspace == live == preflight，**691 文件 0 不一致** | `identity.txt` |
| 两方身份链（拆预检后） | workspace == live，**691 文件 0 不一致** | `identity-after-teardown.txt` |
| 浏览器 E2E | **342 项检查 0 失败**，11 个页×视口组合 | `e2e.txt` / `e2e.json` / 7 张截图 |
| E2E 负对照 | 预检副本重建为**基线主题** → 31 项中 **10 项 FAIL**，全部落在该失败处 | `e2e-negctl.txt` |
| 拆预检 + 零残留 | 主题目录/mu-plugin/日志全移除；mu-plugins 只剩 `zz-sf-dev-lockdown.php`；docroot 代码零残留；DB `stylesheet/template=sinofresh-theme`；拆除后线上复验 2.10.52 / 0 三段 / 401 | `teardown.txt` |
| 错误日志逐条归因 | **PASS：0 条在窗口内，37 条逐条归因，0 条未清**；`debug.log` 不存在 | `logaudit.txt` |
| 日志审计负对照 | 我们故意带凭据直连 `/wp-settings.php` 写入一条真实 PHP fatal → 审计 **RC=1 抓住** | `logaudit-negctl.txt` |
| 全仓 md5 | **1288 个跟踪文件 / 0 差异**，非 ASCII 路径逐条 matched（排除报告自身） | `cloud-md5.txt` |
| 预检日志存档 | 75 条全部 `theme=sinofresh-theme-preflight`（03:07:13–03:07:35 UTC） | `e-preflight.log.txt` |

### E2E 断言的实质（不是「存在」，是「在 order 上、不留孤儿」）

- 三段在 DOM 里真的没了：`.sf-facts` / `.sf-spectable` / `.sf-actives` / `#actives` 计数全 0，
  两个作者注记号也不在。
- 主脊严格递增：每个 h2 所属 section 的 top 单调上升；**删除留下的间隙实测 hero→卡墙 24px、
  卡墙→配置器 24px** —— 留下孤儿空带会在这里暴露。
- FAQ / 相关产品 / CTA / 配置器都在，FAQ 项>0、相关产品项>0、卡片>0、配置器分组>0。
- 页面的 JS 真的跑了（点轨>0、卡片>0、配置器分组>0），所以「无 JS 报错」是**在工作的页面上**
  的结论：11 个组合 0 page error、0 console error，1440 与 375 均无横向滚动。

### ⚠️ 点轨数量：7 → 6（不是「不变」，也不可能不变）

用户要求写的是「点轨数量不变」。实测结论：**点轨从 7 个点变成 6 个点，8 个剂型页
（en+zh）一致，每页恰好少 1 个**。

原因是算术而非缺陷：`toc-nav.js` 给 `main` 里每个 `h2` 建一个点，而被删的
`sf-actives` 段自带一个 h2（`Active Ingredients & Guaranteed Analysis`）。
只要该段被删，点就必然少一个。

真正需要成立、且已逐页验证成立的是：

- **点轨自洽**：`点数 == h2 数`（每页 6 == 6），没有孤儿点；
- **没有点指向被删锚点**：`#actives` 不在轨上；
- 顺序 = 基线顺序去掉那一个 h2（从基线字节独立推导，且先断言该 h2 确实在基线里）。

如果点轨仍是 7，那才是 bug（轨道指向一个不存在的 section）。**若业务上要求点轨数量不变，
唯一出路是恢复该 h2（例如 F1 的新事实行带一个 h2），需要另行拍板。**

## 6. 闭环期新发现并修掉的工具缺口（`b2d_s5_logaudit.py`）

1. **窗口只能由预检日志 + 对称 margin 推导**。闭环活动（pull、live 重抓、E2E）发生在候选
   抓取**之后**；对称 margin 想够到闭环就得吞进批前扫描器噪音，然后莫名 FAIL。
   ⇒ 新增 `--window-from/--window-to` 显式窗口；本批窗口 = **我们自己的请求区间**
   （03:07:12–03:30:00 UTC，从访问日志 user 字段读出）。
2. **80 端口 vhost 的报错无法归属**：工具只读 SSL 访问日志，而
   `dev.zxpet.com-error.log` 里的 `/cgi-bin/luci` 探测（TP-Link 路由器 RCE 利用尝试，
   user `-`，404）只能靠 80 端口访问日志归属。⇒ 两份访问日志都读，并新增
   `AH01264 script not found` 归因规则。
3. **`--allow`**：负对照故意写进日志的那条错误会永远被归因为「我们的」。
   ⇒ `--allow 'TS=理由'` 把它作为**显式记录在案的例外**打进判决（是记录，不是屏蔽；
   未列出的照旧 FAIL）。
4. 归因纪律重申：**按认证用户名归因，绝不按客户端 IP**（CF 边缘 IP 共享）。
   本次 03:00:22 的 `AH01630` 来自 108.162.246.186（CF 边缘），UA 是一串 AI 爬虫
   （MoonshotBot/PerplexityBot/DeepSeekBot…）在扫 `.env`，user 全 `-`。

## 7. 提交

| commit | 内容 |
|---|---|
| `df31199` | 8 模板删 592 行 + 版本 2.10.52（两处同步）+ apply/confine 工具 |
| `87bb4cc` | 六门报告 + 负对照 + 门工具三 bug 修正 + 预检日志存档 |
| `f0eceaa` | 渲染证明 + 日志审计（含两处缺口修复 + `--allow`）+ 截图 |
| （本提交） | 批次文档 + 全仓 md5 报告 |

## 8. 残留 / 下一步

- **F1（下一批候选）**：把 `sinofresh_formula_spec_cell()` 重新指向新的事实来源，
  恢复 21+21 详情页的 `MOQ / Lead time` meta 行（本批接受的退化）。
- **MOQ 三处重复对账**（2D 第 6 批候选，未开工）：FAQ / `.sf-spectable` / `.sf-facts`
  —— 前两处中 spectable 已在本批删除，对账范围缩小为 FAQ vs 详情页 meta。
- 残留待办不变：实拍图 34 张；详细介绍（`post_content` 21 条全空）；
  ≤1239px hero 贴边；首页 `<title>` 仍是 `sinofresh`。

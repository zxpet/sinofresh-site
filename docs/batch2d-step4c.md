# 批次 2D · 第 4c 批 — `--solo` 的上限从「盒子」移到「轨道」

**结论**：已上线。线上 `dev.zxpet.com` 现在服务 `style.css?ver=2.10.50`，单张 Specification 卡落在 **x=120 / w=560**，与页面每个标题同一条左缘。

**产品 commit** `e365d6f`（2.10.49 → **2.10.50**，两处同步）
**工具/文档** `34fa2c2` → `2037318`（修 2 个工具缺陷 + 2 个新工具）→ `07a649a`（记录与报告）→ `836041b`（`sf_repo_md5: --exclude`）→ `020e4c2`（全仓 md5 报告）
**改前备份** `sinofresh-theme/_backup/b2d-step4b-20260921-070259/`（2.10.48 的两文件，经 `git show 94d64fd:` 逐字节核对）

---

## 1. 改了什么，为什么

上一批批准的写法（`.sf-fdetail__grid--solo { max-width: 560px; margin-inline: 0 }`）在浏览器里是**空操作**，这一批换成：

```css
.sf-fdetail__grid--solo {
	grid-template-columns: minmax(0, 560px);
}
```

原因（`docs/batch2d-step4b-findings.md` 有完整取证）：

| | 做法 | 实测落点 | 与标题 |
|---|---|---|---|
| A | `max-width:560px` + `margin-inline:0 !important` | x=38 / w=560 | 外凸 82px（38 是 section 的内容盒左缘，不是页面左缘） |
| **B（本次采用）** | `grid-template-columns: minmax(0, 560px)` | **x=120 / w=560** | **0px** |

关键点：B 不碰 grid 自己的居中（core 给受限子元素的 `auto` 边距把 1200px 的 grid 放在 x=120 正是想要的），只把**列**的宽度限住。`.sf-fdetail__grid` 基础规则（`repeat(auto-fit, minmax(280px, 1fr))`）一个字没动 ⇒ 卡片将来变回多张时不失能。

`max-width` 与 `margin-inline` **两个都删掉**：留着 `max-width:560px` 会把 grid 盒子压到 560 再居中得到 x=440，正好退回问题现场。

---

## 2. 五门 + 负对照（`tools/b2d_s4c_confine.py`）

基线 = **2.10.49 的预检抓取**（`_backup/b2d-step4b-baselines/new`，75 页全部 `ver=2.10.49`，MANIFEST 记了 `X-SF-Preflight: 1`；源文件取自 `git show effa435:`）。
候选 = **2.10.50 的预检抓取**（`_backup/b2d-step4c-baselines/new`，75 页全部 `ver=2.10.50`，75/75 指向 `sinofresh-theme-preflight`）。
报告 `docs/b2d-step4c-gates.txt`。

| 门 | 结果 |
|---|---|
| 1 资源清单 | `style.css 2.10.49 -> 2.10.50 on 75 page(s)`；asset SET 变动 **0** 页 |
| 2 掩码折叠 `?ver=` | **75/75 identical** |
| 3 style.css 重建 | 三条声明全部命中（各恰好 1 次）；撤销后 **undone == base : YES**（`796acac4…`） |
| 4 functions.php 重建 | **undone == base : YES**（`d9b9a0e3…`） |
| 5 JSON-LD deep-equal | **75/75 identical**（解码结构比对，不是掩码文本） |

**负对照**（`--new` 指向基线自身）：`RC=1`、**FAIL 7 条** —— 1 条 `NOTHING moved`、4 条「声明的新文本出现 0 次」、2 条重建不可比。
值得记下：这次负对照里 **门 2 与门 5 仍然报 `identical 75/75`**。它们本来就看不见「自己跟自己比」——正是门 1 那句 `NOTHING moved` 存在的理由。报告 `docs/b2d-step4c-negctl.txt`。

### 补充：部署真值（48 → 50 一步跨过）

本批的门证明的是「2.10.50 = 2.10.49 + 声明的改动」，而**线上实际服务的是 2.10.48**（4b 的 commit 从未被 pull）。所以额外跑了一次基线 = 线上 2.10.48（`_backup/b2d-step4b-baselines/base`，源文件取自 `git show 94d64fd:`）的一步跨过检查：**五门同样全 PASS**，`style.css 2.10.48 -> 2.10.50 on 75 page(s)`，重建 `undone == base : YES`（`c546caa3…` / `1a8a3134…`）。报告 `docs/b2d-step4c-gates-h48.txt`。
⇒ 上线的实际增量由「48→50」直接证明，不必只靠「48→49、49→50」两段传递。

---

## 3. 渲染取证（`tools/b2d_s4c_evidence.py`，预检副本上跑）**19/19 PASS**

`docs/b2d-step4c-shots/evidence.txt`｜`evidence.json`｜截图 `01-solo-preflight-{1440,375}.png`

- 先断言拿到的是**哪一份**样式：`…/themes/sinofresh-theme-preflight/style.css?ver=2.10.50`（不是这句就等于在拿旧字节作证）
- **1440**：`readyState=complete`、`innerWidth=1440`、`cardCount=1`、`--solo` 在类上、`tracks=560px`、**`cardW=560`**、`cardLeft==gridLeft==120`、`deltaVsSpecH2=0`、**页面 5 个 h2 全部 `@x=120`（共享左缘 5/5）**、无横向滚动
- **负对照**：把 `grid-template-columns` 还原成 auto-fit ⇒ 卡宽 **560 → 1200（+640px）**、轨道值随之改变 ⇒ 测量确实看得见这条规则
- **375**：`cardW=335`（`tracks=335px`，被可用宽度钳住而不是 560）、无横向滚动、与 Specification 的 `deltaVsSpecH2=0`
  - 顺带记录一个**既有**现象（非本批引入）：375 下页面上 `A Closer Look at…` 与 `Ready to Launch…` 在 x=38，而 `Specification` 等三颗在 x=20 —— 带背景的 section 有 core 给的 38px 内边距，标题落点因此不唯一。1440 下不存在这个分歧。

---

## 4. 上线与闭环

1. `git fetch`（云端只取对象，工作树仍是 `94d64fd` / **2.10.48**）⇒ 线上从未服务过 2.10.49 的字节
2. `install 34fa2c2…`（**全 40 位**）装预检副本；副本 `style.css`/`functions.php` 的 sha256 与本地工作区、与 `git show HEAD:` 对象**三方一致**（`c01f145d…` / `b03a9ed6…`）
3. 候选经 `X-SF-Preflight: 1` 抓 75 页 → 跑门（全 PASS）→ 才 `git pull --ff-only` ⇒ **线上没有服务过未过门的字节**
4. 上线后 `sf_masked_cmp.py new live` ⇒ **75/75 identical, DIFF 0**（`docs/b2d-step4c-shots/closure.txt`）。掩码计数里每页 16–18 个 `preflight_theme_dir` 说明「副本目录 → 实服务」的映射确实生效
5. 服务侧核对：`/products/soft-chews/` 返回 200 / 177547 B，页面引用 `sinofresh-theme/style.css?ver=2.10.50`

---

## 5. 拆除、日志、仓库级一致性

- **预检拆净**：`theme dir gone / mu-plugin gone / log gone`，`mu-plugins/` 只剩常驻 `zz-sf-dev-lockdown.php`；本轮预检日志 79 行随后一并删除（`teardown.txt`）
- **错误日志**：1494 B → **1939 B**，mtime `2026-09-20 23:23`（UTC）。**新增 2 行不是本批产生的** —— 是外部扫描器 `168.144.80.239` 对 `/cgi-bin/.%2e/…` 的路径穿越探测；该 IP 在访问日志里 **0 条**（请求在进入访问日志前就被拒），而我这一侧 `144.52.153.227` 在错误日志里 **0 行**（本批约 750 次请求无一产生告警）。
  ⛔ **口径修正**：把「日志体积/mtime 不变」当不变量会**必然误报** —— 这台机器暴露在公网上，随机扫描随时会写这两行。可靠的不变量是「**日志里没有本批自身造成的条目**」。
- **仓库级 md5**：新工具 `tools/sf_repo_md5.py`，**跟踪 1239 个文件、比较 1238 个、0 差异，13 个非 ASCII 名逐条 matched**（`cloud-md5.txt`）。
  它的**第一次**运行抓出 2 处不一致 —— 我本地已修、当时尚未提交的两个门工具的 `say()` 修复；**第二次**又抓出 1 处 —— 它自己（我先前用 shell 重定向把报告写进了被比较的目录，工具于是给半写状态的空文件做了哈希，得到 `d41d8cd9…`＝空文件摘要）。
  ⇒ 因此加了 `--exclude`：**报告不能是它所报告集合的成员**（内容依赖自身哈希，不存在稳定值）。排除后比较**逐字节可复现**：同一条命令再跑一次，输出与入库报告 `cmp` 相同。
  ⛔ 要记的教训不是「0 差异」而是「**每一个差异都能解释**」—— 这两次 FAIL 都是工具在替我把话说清楚。

---

## 6. 本批在工具里抓到的三个真 bug

1. **`say(s='')` 被用两个参数调用**（`b2d_s4b_confine.py` 里从 4b 就存在）。它只在**重建失败**那条路径上被触发 —— 也就是说「门通过」时这个 bug 永远藏着不响。4c 的 48→50 跑到了那条路，直接 `TypeError`。两个文件都改成 `say(*parts)`。
2. **2.10.48 那套声明字面量少算一个换行**：`TAIL_ANCHOR + NEW_PARA` 在候选文件里出现 **0 次**（真文件是 `…behaviour.\n\n   The cap…`，而 `NEW_PARA` 自身已带前导 `\n`）。修好后重建逐字节成立。
   这条值得单独记：它是**门自己报出来**的（「声明的新文本出现 0 次」），不是我去比 diff 看出来的。同时说明「各恰好出现 1 次」这个断言不是装饰 —— 少了它，`replace(..., 1)` 的撤销量就是不确定的。
3. **报告被写进了它正在报告的集合里**（见 §5）。这不是笔误而是设计缺陷：一个文件的内容若包含它自己的哈希，就不存在稳定值。加了 `--exclude`（两侧同时排除；且若给的是未跟踪路径直接拒绝运行，避免打错字悄悄把集合缩小）。

三个都是在**从没被走到的那条路径**上（失败输出、跨版本声明、自指报告）—— 也就是说它们只有在门要说话的时候才会暴露。这正是「门必须跑负对照 + 必须能自证」的实证理由。

---

## 7. 产物清单

| 文件 | 内容 |
|---|---|
| `docs/b2d-step4c-gates.txt` | 四门报告（49 → 50） |
| `docs/b2d-step4c-gates-h48.txt` | 四门报告（48 → 50，部署真值） |
| `docs/b2d-step4c-negctl.txt` | 负对照（FAIL 7 条） |
| `docs/b2d-step4c-shots/evidence.txt` `.json` | 渲染取证 19/19 |
| `docs/b2d-step4c-shots/01-solo-preflight-1440.png` `-375.png` | 预检副本上的截图 |
| `docs/b2d-step4c-shots/closure.txt` | 上线后 `sf_masked_cmp new live` 75/75 |
| `docs/b2d-step4c-shots/teardown.txt` | 预检拆除复验 |
| `docs/b2d-step4c-shots/cloud-md5.txt` | 仓库级 md5：跟踪 1239 / 比较 1238 / 0 差异（可逐字节复跑） |
| `tools/b2d_s4c_confine.py` | 门（`--from-ver` 选声明集 + JSON-LD 门 + 恰好一次断言） |
| `tools/b2d_s4c_evidence.py` | 渲染取证（含「拿到的是哪一份」与负对照） |
| `tools/sf_repo_md5.py` | 全仓 md5（非 ASCII 逐条证明） |
| `_backup/b2d-step4c-baselines/{src49,new,live}` | 2.10.49 源、候选取样、上线后取样 |

---

## 8. 遗留（不在本批）

- 第 5 批（剂型页核心事实行 + Direct Answer）的扫描与方案在 `docs/batch2d-step5-scan.md`，**D1–D6 待拍板**
- ③ 详细介绍 `post_content` 恒空；≤1239px hero 贴边；实拍图 34 张
- `MEMORY.md` 归并（按约定排在所有代码批次之后）

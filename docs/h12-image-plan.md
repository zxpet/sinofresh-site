# H12 步骤6 · Shape / Container 图片机制 — 方案（只出方案，不实施）

> 状态：**机制 100% 已在代码里，缺的只是图片内容**。本批次不写任何新代码；
> 以下第 2 节是运营/设计要做的操作，第 3 节是匹配规则，第 4 节是可选增强。

## 1. 现状盘点（本轮只读核验）

| 部件 | 位置 | 状态 |
|---|---|---|
| 图库后台 | Site Settings → **Container Library / Shape Library** 两个子页（`sf-containers` / `sf-shapes`） | ✅ 已上线：wp.media 选图、Add/Remove、按行存储 label + attachment_id |
| 前台取图 | `sf_formula_library_options()`（inc/formula-admin.php）按**标签精确匹配（大小写不敏感）**取 attachment_id | ✅ 已上线 |
| 前台渲染 | Shape / Container Type 组为 `image` 样式：有图显示图，**无图显示虚线空位＋标签文字**（`sf-fdetail-config__img--empty`，158 页实测如此） | ✅ 已上线，空库也有体面的兜底 |
| 数据现状 | dev 库 **containers=0、shapes=0**（两库全空） | ⚠️ 唯一缺口：图片 |

## 2. 落地操作（无需开发，后台即可完成）

1. 登录 wp-admin → **Site Settings → Shape Library**（或 Container Library）；
2. 点 **+ Add …** 一行一个：先填 **Label**（必须与选项池的词汇完全一致，见第 3 节），点 **Choose** 从媒体库选图；
3. 保存后前台该标签的选项立即出图，无需任何发布动作。

**图片规格建议（统一模板，一次做对）：**

- 尺寸 **正方形 ≥ 400×400**（前台展示框内 object-fit 缩放，方形不裁切）；
- **透明底 PNG**（或 WebP）：形状/容器图要浮在卡片白底上，白底 JPG 会有"方块感"；
- 同一图库内**风格统一**：同一光源、同一视角（容器 3/4 侧面，形状正俯视）、同一留白比例；
- 命名 `shape-bone.png` / `container-jar-120ml.png` 一类可读名，方便日后审计；
- 每张 ≤ 100KB（前台 chips 图很小，原图过大会拖慢详情页）。

**需上传的清单（按当前选项池）：**

- Shape Library：Bone / Round / Square / Heart / Star / Paw / Cylinder（软咀嚼 7 项）＋ 片剂（Round/Square/Oval…按 pool）＋ 膏剂/粉剂的外观示意（Texture/Appearance 组词汇）；
- Container Library：Bottle / Jar / Tube / Sachet / Pouch / Dropper Bottle / Pump Bottle / Can（按 packaging 池词汇）。

## 3. 匹配规则（出图/出空位的唯一判据）

- 前台某选项**有图** ⇔ 图库里存在 **label 完全一致（忽略大小写）** 的行且该行有图；
- 池里有、图库没有 → 该选项**照常显示**，只是空位（不会丢选项）；
- 图库里有、池里没有 → 不显示（图库是图片载体，不是选项来源）；
- 因此**改词汇必须两边同步**：选项池（formula-pools.php）改词后，图库行名要跟着改。

## 4. 可选增强（本轮不做，留待需求触发）

- **批量导入**：一次 CSV（label, 图片URL）灌库——适合首次 20+ 张图的场景；
- **按剂型默认图**：同一 label 不同剂型想用不同图时，需把图库行升格为「剂型+label」双键（涉及 `sf_formula_pool_option_image` 的匹配函数，约 30 行改动）；
- **WebP 自动转换**：上传时生成 WebP 副本（需服务器 imagewebp，当前未启用）；
- **图库行反查**：Library 子页显示"哪些公式在用这个 label"，防止改词断链。

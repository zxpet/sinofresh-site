# Batch H7h — 移动端字号 ＋ 布局重排 ＋ 补 H7g 门（2026-09-23）

**状态：实施＋门＋E2E＋截图全部完成；未 pull（用户约束「不 pull、不拆预检、不删守卫」）。**
**dev live 仍 `2.10.67`（GO 批态）；本批上线待用户下一次 pull 授权。**
产品提交：`65f8d56`（手机端全量改动）＋ `8a613bd`（门抓到的三处产品缺陷修复＋门声明＋E2E 驱动）。
**HEAD == origin/main == 8a613bd**，工作区已清（本档随收尾提交入库）。

## 四项用户裁决

1. **合并**——悬浮圆钮（email／WhatsApp／back-to-top）在 ≤480px 合并为**底部固定 CTA 条**：通栏、双按钮（Send Inquiry ＋ WhatsApp），email 与 back-to-top 撤出移动端；`body` 加 `padding-bottom` 防遮挡。
2. **折叠**——参数区默认显示前 3 组，折叠按钮「View all specs ▾」，展开后文案「Show fewer specs ▴」，状态写 `sessionStorage`（key `sf-config-fold`），刷新后保持。
3. **点指示器**——媒体区手机端改横滑已有（2.1.0 的 swipe），本批补**底部圆点指示器**（`.sf-gallery__dots`，点数＝照片数，`is-active` 跟随当前张），缩略图条手机端隐藏。
4. **双按钮**——底部条固定两键：询盘（滚动到 Quote）＋ WhatsApp（`sf-whatsapp-link` 同源）。

## 改动清单

### A. 字号地板（`style.css` 末尾新增第 62 节，`@media (max-width:480px)`）

放文件**最末**，保证每条字号覆盖排在基规则之后（H7b 教训：`.sf-fdetail2__title` 的 step 曾因排在基规则之上静默失效）。

| 元素 | 字号 |
|---|---|
| 参数 label／note／空槽名／content label／chip | **14px** |
| 选项文字／参数值／intro／hero 副标 / 正文 / FAQ 问答 / 按钮文字 | **16px** |
| 行高 | ≥1.5 |

（Apple HIG ＋ Material 16px 可读地板；14px 为次级信息地板。）

### B. 布局重排（同一 media 块）

- `.sf-fdetail-config__hint`（"Choose one or more"）手机端 `display:none`。
- 抽屉抑制：481–768 的抽屉逻辑保留，≤480 直接内联展示全部组＋折叠按钮；**折叠按钮与点指示器的隐藏规则必须放 media 块之外**（全局先 `display:none`，手机块内再开——否则 768/1440 出现无样式裸节点，E2E 实发）。
- Container／Shape 组 3 列网格，缩略图 **80×80**（`box-sizing:border-box`，否则虚线 1px 边框把 80 量成 82——E2E 实发），gap 8px。
- 缩略图条隐藏、点指示器 flex。
- 悬浮栈→底部条（见裁决 1 的 CSS），`.sf-float-btn--email/--top` 隐藏，`body{padding-bottom:78px}`。

### C. `config.js`（**1.1.0→1.2.0**）

折叠逻辑：`FOLD_KEY='sf-config-fold'`；`setFold(open)` 切 `sf-config-folded` 类＋`aria-expanded`＋按钮文案＋`sessionStorage`（try/catch 包裹）；默认折叠除非存储值为 `open`。docblock 第 3 条改述折叠（抽屉仍跑 481–768）。

### D. `formula-gallery.js`（**2.1.0→2.2.0**）

点指示器：`dots` 容器＋每张照片一个 `button.sf-gallery__dot`，click→`selectPhoto(i,false)`；`paint()` 里按 `is-active` 同步。swipe 本体是 2.1.0 已有，零改动；`touch-action: pan-y pinch-zoom` 已在。

### E. 版本令牌（两处同步）

- `style.css` **2.10.68→2.10.69**（头部 `Version:` ＋ functions.php enqueue）。
- `functions.php`：`config.js` **1.1.0→1.2.0**、`formula-gallery.js` **2.1.0→2.2.0**。

## H7g 门补齐（`tools/b2d_h7_gate.py`）

- `BATCHES['h7g']`（insert 方向）：删页脚 tel 锚（前瞻限定，联系页同串保留）＋插预览层＋插 8 选项 shape 组（meta 从页面自身 Shape 行派生）＋旧空槽重写。`applies=173`；sources 增 `'adm': 'inc/formula-admin.php'`（`sf_default_shapes` 不在 functions.php——首跑 FAIL 后改挂）。
- `BATCHES['h7h']`（insert 方向，**null edit**——纯 CSS/JS/令牌，渲染 HTML 只换代号）：三个令牌对；NC-src 读真源（折叠规则／持久化／dots 构建器，callable 全替换防子串自证）；矩阵 5 突变体。

## 验证

### H7g 门（全 PASS，`_backup/b2d-h7g-gate.json`）
A/A 75/0；主证 75/0、**applied 173/173**；覆盖（页脚 tel 75→0、联系页保留 76→1、wa.me 269→269、空槽旧串 14→0）；不变式＋scoped＋order 全过；掩码回读 23 页 0 差异；矩阵 **7/7**；具名负对照 **16/16**（NC1–NC8＋NC-src×2＋NC-page＋NC13 sighted＋NC14–16）；源码 **15/15**（对 `git archive e8f0172` 检出）。

### H7h 门（全 PASS，`_backup/b2d-h7h-gate.json`）
A/A 75/0；主证 75/0（null edit，applied 0/0 declared）；覆盖 8 条（旧代号 0、新代号 style 75／config 42／gallery 42）；不变式 11 条（含 JSON-LD deep-equal）；掩码回读 23 页＋46 二进制 0 差异；矩阵 **5/5**；负对照 **16/16**。

### E2E 三档（`tools/b2d_h7h_e2e.py`，装 `8a613bd` 后 **31/31**）

- **375×812**：字号全部达地板（label 14、其余 16）；折叠在 `joint-support-soft-chews`（6 组，非空洞断言）"3 of 6"→展开 6→刷新后保持；3 列／80×80／8px；缩略图条隐藏＋4 点＝4 照片；合成指针拖拽（`buttons:1`）切到第 2 张；底部条 fixed/横向/375 宽、email＋back-to-top 撤出、body padding 78px；询盘钮过参数带后可命中；hint 隐藏；**0 页面错误**。
- **768×1024**：抽屉钮保留、悬浮圆钮保留、缩略图条保留，无 dots／fold。
- **1440×900**：右栏 h1 32px、全部组内联、缩略图条、圆钮。

### 截图（`docs/batchH7h-shots/`，5 帧，全部 distinct=256 非空白）

`h7h-01-phone-fold-bar.png`（375×812 折叠态＋底部条）／`h7h-02-phone-expanded.png`（展开态）／`h7h-03-phone-dots.png`（点指示器＋横滑）／`h7h-04-tablet.png`（768×1024）／`h7h-05-desktop.png`（1440×900）。

### 门抓到的产品缺陷（3 处，均修于 `8a613bd`）

1. 80px 块量出 82（虚线边框无 `box-sizing`）→ 补 `border-box`。
2. dots／fold 按钮 768/1440 显示为无样式裸节点（隐藏规则只在 480 块内）→ 全局隐藏规则移到 media 块之前（同特异性，手机块后到胜出）。
3. 底部条 `bottom=268` 是 cookie 横幅共存态（设计如此）→ 断言改横幅感知。

### 过程踩坑（登记）

- E2E 首跑 13/31：`set viewport` 需 `ab("set","viewport",w,h)`（一个参数串 `"set viewport"` 静默无效）→ 加视口确认＋3 重试。
- 合成 PointerEvent 需 `buttons:1`（swipe handler 忽略 `!event.buttons`）。
- 折叠断言空洞：`calming-soft-chews` 只有 3 组，「3 of 3」证明不了任何事 → 换 6 组页＋`total>3` 守卫。
- h7g 覆盖 FAIL：needle 同时匹配 H7d 的 TEXT 选项 → 收紧含 `__img--empty` 槽类。

## 约束遵守

桌面/平板布局零改动（全部改动在 ≤480px 块或 JS 行为内）；零库引入；未 pull、预检未拆、守卫未删（`zz-sf-dev-lockdown.php` 常驻）。

## 仍需用户处理（不变）

1. **生产上线**（唯一剩余大项）：pull 授权＋`docs/dev-lockdown.md` 10 项移除＋`blog_public` 0→1。
2. post 158 五处测试值（用户后台自清；原值 `_backup/b2d-go-post158/originals.json`）。
3. Shape Library（8）＋Container Library（7）待上传图。
4. 预检副本现 `8a613bd`（`2.10.69` 态）——上一批副本是否删除待裁决。

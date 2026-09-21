# 批次 H1 —— 配方详情页后台发布模板重设计（含 H1a 数据迁移）

> 状态：**已上线闭环**（live `a0e2f88`，Step 4 收尾 2026-09-22）。
> 上线内容：18 必填 + 7 警告的后台发布模板（6 组 meta box）、Site Settings 动态认证行
> （`{{sf-certifications-line}}` 供 8 剂型 hero + 详情页 cert 行 + Organization Schema
> `hasCredential`）、Container Library 瓶型库（wp.media 选图）、Global FAQ 后台子页、
> H1a 数据迁移（21 条 × 5 键 = 105 键写入）。
> 前端零字节：H1a 全程 75/75 掩码 identical（基线→apply 后 live→pull 后 live 三次取证）。

## 关键提交链
`7a47f26`（Step1 真实树）→ `1d1a65e`/`fce8248`/`60ffa3f`（Step2 门内候选）→
`70b1c65`（wp_slash 修复：`update_post_meta` 魔引号陷阱）→
`a0e2f88`（保存端拍板 A：空值不写入，DELETE 键）→ `3d382c7`（E2E 工具沉淀）。

## 门与核验（候选 `a0e2f88`，全套重跑）
- 主门 PASS：75/75 掩码逐字节 identical、ver 2.10.54、admin 资产零泄漏、6 文件哈希对表、接线同源
- 负对照 FAIL（26+ 拒绝）、破坏矩阵 10/10 FAIL（报告 `_backup/b2d-h-baselines/*step3fix.txt`）
- 上线八步：pull --ff-only（40 位校验）→ 服务侧 4 项 → 掩码 75/75 → 后台 E2E 全项 →
  拆预检零残留 → 日志逐条归因 → 身份链 697×0 → 仓库 md5（见下）

## H1a 数据迁移与两次事故
1. **wp_unslash 魔引号陷阱**：`update_post_meta` 内部 `wp_unslash()` 剥掉 JSON 转义反斜杠
   （`\u2014`→`u2014`；含 `<a href>`/非 ASCII 即损坏）。正确写法＝
   `update_post_meta($id, $key, wp_slash(wp_json_encode($v, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES)))`。
   verify 抓到 21 条 faq 不一致 → rollback → 两侧（admin 保存端 + 迁移脚本）同型修复。
2. **保存端污染 16 键**：真实浏览器 Save 会序列化整个 metabox 表单，16 个「留空待填」键
   被写入 `'[]'`/`''`（census 105 不变量首存即破）。拍板 A：`sf_mb_store()` 统一入口——
   空串/`'[]'` → `delete_post_meta`（空即无键）；非空走原路径编码逐字节不变。
   复跑验证：保存后 16 键写入数 = 0。

## 后台 E2E（live，`tools/b2d_h_admin_e2e.js`，全项 PASS）
6 组 meta box / 服务端 Backfill 横幅 / 三表增删（price_tiers、cartons、faq）/ certs 动态行 /
容器库 wp.media 实开实关 / Global FAQ / 0 JS 错。测试零留痕（_edit 行删、sf-e2e 删、190 行、verify 105/105）。

## 错误日志归因（窗口 2026-09-21T01:00 → 09-22T04:00 UTC，margin 5）
- 49 条窗口内记录全部记账（`_backup/b2d-h-baselines/logaudit-h1-closure.txt` + allow 参数）：
  - 42× `Cannot redeclare sinofresh_formula_faq_data()`（09:10:58–09:11:03 UTC 突发）＝
    **我们的 sfdev 认证抓取流量** 1:1 对应 /zh/formulas/* 500，只涉及 preflight 副本字节
    （live 全程未服务）；候选变更后零复发（12:00 UTC 后 www-error.log 零新增）
  - 1× ABSPATH fatal（03:38:30）＝ sfdev 认证的 /wp-settings.php 直探（WP 自身防护，单次）
  - 1× MaxRequestWorkers（14:45:23）＝ 我们 75 页并发抓取瞬时打满 worker（182 请求/秒，无失败请求）
  - 其余 AH01630/AH10244/AH01264 ＝ 外部扫描器噪音（access log user 字段 `-`，从未认证通过）
- 工具修复：`b2d_s5_logaudit.py` status 混排 None 键排序崩溃（一行 key 修复）

## 遗留与 H2 待办
- **precheck banner**：客户端正则 `^(Publish|Update)$` 需改 `^(Publish|Update|Save)$`
  （Gutenberg 实际按钮文案是 Save；服务端 admin_notices 权威横幅不受影响）——并入 H2
- 配置器删除推 H2（`inc/config-pdf.php` 被 basket.js 共享，删配置器不能删端点）
- 2D 第 6 批候选：MOQ 重复对账（FAQ vs 详情页 meta）
- 残留：实拍图 34 张；详细介绍 21 条全空；≤1239px hero 贴边；首页 `<title>`

## 身份链与仓库 md5
- 身份链：`b2d_s3_identity.py` **697 tracked 文件，0 mismatch**（workspace ↔ site-repo，server HEAD `3d382c7`）
- 仓库 md5：**1360 files, 0 mismatches**（`sf_repo_md5.py --exclude 本文档`，JSON
  `_backup/b2d-h-baselines/repo-md5-h1.json`；数字回填于闭包时刻，复跑须继续排除本文档）
- 闭包时服务器 HEAD：`0022453`（= 本文档 md5 回填提交；`ee074ff` 为数字生成时点）

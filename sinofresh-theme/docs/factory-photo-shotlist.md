# 工厂实拍照片 —— 拍摄清单与替换规范

> 现状：`/about/` 与 `/factory-tour/` 上的设施照片全部是 AI 生成占位图（`fac-*`、`equip-*`，2026-09 上传）。
> 实拍到片后按下表替换，页面结构不变、不需要重新排版。

## 一、分工：两页都放，但画面不重复

| 页面 | 区块 | 照片角色 | 张数 | 比例 |
|---|---|---|---|---|
| `/about/` | Inside Our Factory | **精选展示**（品牌信任：我们是谁、有什么） | 6 | 4:3 |
| `/factory-tour/` | What You Can See During the Tour | **参观动线**（决策依据：客户来访当天按顺序看到什么） | 6 | 4:3 |

规则：**同一张照片不出现在两个页面**。About 用宽景/静物式全景，探厂页用"站在客户视角走进车间"的过程镜头。

## 二、拍摄清单

### About 页（6 张，替换 `/about/` 的 `sf-fac` 画廊）

| # | 文件名 | 拍摄对象 | 机位与构图 |
|---|---|---|---|
| 1 | `fac-cleanroom.webp` | 洁净车间全景 | 门口向内、通道居中、纵深线明确，无人或远景少量人员 |
| 2 | `fac-line.webp` | 自动化生产线全景 | 侧面 45°，带出联线关系与不锈钢设备序列 |
| 3 | `fac-lab.webp` | 研发实验室 | 实验台 + 仪器，桌面整洁，无杂物 |
| 4 | `fac-warehouse.webp` | 仓库货位 | 货架通道纵深，托盘整齐，标签朝向镜头 |
| 5 | `fac-retention.webp` | 留样室 | 留样架分格陈列，标签可辨（不露客户名） |
| 6 | `fac-packaging.webp` | 包装区 | 灌装→贴标→装箱工位连续画面 |

### 探厂页（6 张，按客户实际走厂顺序）

| # | 文件名 | 对应站卡 | 拍摄对象 |
|---|---|---|---|
| 1 | `tour-showroom.webp` | 01 Showroom & Reception | 500㎡ 展厅前台 + 剂型样品陈列墙 |
| 2 | `tour-warehouse.webp` | 02 Raw Material Warehouse | 原料收货/待检/放行分区（可带标识牌） |
| 3 | `tour-cleanroom.webp` | 03 ISO 8 Cleanroom | 洁净区风淋后通道，蓝白无尘服人员背影 |
| 4 | `tour-line.webp` | 04 8 Production Lines | 软咀嚼/片剂/粉剂线中景，设备运行状态 |
| 5 | `tour-lab.webp` | 05 R&D Center & Laboratory | 研发人员操作（背影/侧影），配方开发场景 |
| 6 | `tour-qc.webp` | 06 QC Laboratory & Retention Room | HPLC/GC/AAS 检测台 + 留样室连线 |

## 三、技术规格

- 长边 ≥ 2400px，交付 4:3（1600×1200 或 2400×1800），WebP q80；另留一份原始 JPG 归档
- 光线：车间以现场灯为主，**关闭闪光灯**；仪器屏幕避免反光与眩光
- 人物：出现可辨识面孔须取得肖像授权；优先背影/侧影/手部特写
- 合规：画面内不出现客户品牌包装、不出现第三方设备铭牌商标
- 上传目录：`wp-content/uploads/2026/09/`（与现有占位图同目录）

## 四、替换方法（两步）

1. **About 页**：`templates/page-about.html` 里把对应 `fac-*.webp` 的 `src` 换成新图；文件名保持不变时**无需改模板**，直接覆盖 uploads 里的同名文件即可。
2. **探厂页**：`templates/page-factory-tour.html` 中每个站卡有一个照片位，文件名的目标路径已经写在照片位上方的 HTML 注释里（`<!-- TODO: 替换为实拍照片 .../tour-*.webp -->`）。把这一段

   ```
   <!-- wp:group {"className":"sf-photo-slot","layout":{"type":"constrained"}} -->
   <div class="wp-block-group sf-photo-slot">
   <!-- wp:paragraph -->
   <p>Factory photo pending</p>
   <!-- /wp:paragraph -->
   </div>
   <!-- /wp:group -->
   ```

   换成一张图片块即可（照片位已按 4:3 预留，替换后网格不会跳动）：

   ```
   <!-- wp:image {"sizeSlug":"large","linkDestination":"none","className":"sf-photo-slot--filled"} -->
   <figure class="wp-block-image size-large"><img src="/wp-content/uploads/2026/09/tour-showroom.webp" alt="..." width="1600" height="1200"/></figure>
   <!-- /wp:image -->
   ```

   替换完成后，全站搜索 `Factory photo pending` 应零残留。

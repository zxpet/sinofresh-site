# Shape Library 保存失效 — 根因 + 修复预验 + 顺带发现（2026-09-28 18:40）

> 范围：**只读诊断 + 现场复现 + 修复方案预验**；**未改动任何主题文件 / 服务器配置 / 数据库**（`wp_options` 计数与 `max_id` 全程恒为 565 / 7390）
> 状态：**等你确认后才动手**（你明确要求「报告根因，停下等确认再修」）
> 上一项交付（P3 上线）见 `docs/golive-p3-report-2026-09-28.md`

---

## 一、你问的四个问题，逐条回答

| 你的假设 | 判定 | 证据 |
|---|---|---|
| ① H14 修复没 pull 到生产 | **否** | 本地 = dev = 生产 三方 md5 完全相同：`sf-site-settings.js` `5330df8e84f774bf1eb58e84e468747d`、`formula-admin.php` `d5e6d407e3254258611eb300f2f28c55`；页面加载 `?ver=1.0.3`；CF 边缘字节与源站逐字节一致 |
| ② 选图后隐藏字段没落值 | **否** | 生产管理员会话实测：隐藏字段 `0 → "349"`，预览从 `:empty`（"no image"）变成带 `<img>`，**控制台零错误** |
| ③ 所以要去生产 pull | **否** | 已在生产，无需 pull |
| ④ 隐藏字段有值、保存后没了 | **是 —— 根因在此** | SQL 轨迹 + 幂等性证明，见下 |

## 二、根因（一句话）

`sf_shapes` / `sf_containers` / `sf_global_faq` 的 `sanitize_callback` **不幂等**。WordPress 在**选项尚不存在**时会把回调**调用两次**（`update_option()` 一次；因为该选项无既存值，委派给 `add_option()` 时**再一次**）。第二次拿到的是**已规范化的行列表**，而回调按**表单的平行数组形状**读 `$v['slug']` → 键不存在 → 判空 → 返回 `array()` → 紧接着 H13 的「空则 `delete_option`」写侧钩子把**刚建好的行删掉**。`update_option()` **仍返回 true**，所以后台一路显示「已保存」，**没有任何错误提示**。

**死锁性质**：保存永远失败 ⇒ 选项永远不存在 ⇒ 永远走二次 sanitize 那条路 ⇒ **永远存不进去**。（只有选项已存在时才走单次 sanitize 的更新分支、才会成功 —— 这正是它长期没被发现的伪装。）

**铁证（SQL 轨迹）**：
```sql
SELECT option_value FROM wp_options WHERE option_name = 'sf_shapes' LIMIT 1
INSERT INTO wp_options (option_name, option_value, autoload)
  VALUES ('sf_shapes', 'a:0:{}', 'auto') ON DUPLICATE KEY UPDATE ...
SELECT autoload FROM wp_options WHERE option_name = 'sf_shapes'
DELETE FROM wp_options WHERE option_name = 'sf_shapes'    ← 建完立刻被删
```

**影响面**：源站日志里你自己的浏览器（Chrome/153）在 09:20–09:26（UTC）对三个设置页发了 5 次保存（`sf-factory-info` ×1 / `sf-containers` ×1 / `sf-shapes` ×3），全部 `302`。其中**可断言必然未落库**的是 `sf-shapes`（3 次）与 `sf-containers`（1 次）——这两个选项在库中不存在，走的正是这条死锁路径。（`sf-factory-info` 那一次不下断言：该页自身字段都是幂等回调且已存在，可能已正常落库；但它仍会触发 §四 里的「全组盖章」副作用。）

## 三、修复方案已预验（**未执行**）

方案 A ＝ 在三个回调入口加**幂等守卫**（识别「输入已是规范化行列表」并原样返回）。

把守卫套在**生产真实注册的回调**上、按 WP 的真实调用序列跑两遍（纯函数，**零写库**）：

| 选项 | 不加守卫 | 加守卫后 | 守卫对表单载荷误触发？ | 首遍输出逐字节不变？ |
|---|---|---|---|---|
| `sf_shapes` | 8 → **0** | 8 → **8** ✅ | no | yes |
| `sf_containers` | 8 → **0** | 8 → **8** ✅ | no | yes |
| `sf_global_faq` | 2 → **0** | 2 → **2** ✅ | no | yes |

改动落点（3 处，全在 `inc/formula-admin.php`）：`sf_containers` 877 行 / `sf_shapes` 917 行 / `sf_global_faq` 963 行。
**全组 23 个选项普查结论：需要修的恰好这 3 个**，其余 20 个天然幂等（含 `sf_certifications`，其回调实际在 `functions.php:5924`）。

两道**零写库门**已入库，修前修后都可复跑：
- `tools/sf_sanitize_guard_proof.php`（对照门，退出码 0 = 通过）
- `tools/sf_sanitize_idem_sweep.php`（全组幂等普查门）

## 四、顺带发现：线上「Factory & Trust」版块全站缺失 🔴

诊断过程中核同一批选项时发现的**独立缺陷**，而且**用户可见**：

| 判据 | 结果 |
|---|---|
| 线上 formula 详情页 | 21 页，HTTP 200 **21/21** |
| 规格表 shortcode 已渲染（**自证 shortcode 真的在跑**） | **21/21** |
| 含 `Factory & Trust` 版块 | **0/21** |

- `sf_trust_defaults()` 为 7 项中的 **4 项**备了出厂值（`15,000㎡` / `ISO 8` / `30+ countries` / `Within 24 hours`），另 3 项设计上就是空。
- 但 `sf_formula_trust_value()` 的契约是「**选项不存在** → 用出厂值；**选项 = 空串** → 这一行关掉」。现在 7 个选项**都存在但等于空串**，于是 4 个本该显示的行被当成「人工关掉」，整段（含标题）不产出。
- **空值怎么来的**：9/20 的 dev 转储里 `sf_trust_*` **根本不存在**；生产 `option_id` 显示它们在 H10 开发期（`sf_form_facts`=5252 之后 5253–5259）被创建。机制是 `wp-admin/options.php:336-340` —— **保存组内任一页面时，组内每个选项都会被写一次**，该页没有对应字段的选项被写 `null` → 过 sanitize → **变成空串并建行**。⇒ 是副作用盖章，**不是有人手工清空**。
- **处置（未执行，二选一）**：
  - **A（推荐）**：删除这 7 个 `sf_trust_*` 选项 → 回到「从未保存」→ 4 个出厂值恢复显示，3 个设计上关着的仍不显示。
  - **B**：改为显式写入目标文案（语义不变，但「谁开谁关」写死在库里）。
- 附带核实：`sf_form_facts` 也是空数组，但它的读者在**读取时**回退出厂值（实测 8 项全部正常）⇒ **无害，不用动**。全组 23 项里只有这 7 个信任行被空值伤害。

## 五、需要你拍的板

1. **是否执行方案 A**（3 处幂等守卫 + 两道门）？—— 已预验通过，风险低。
2. **「Factory & Trust」缺失选 A 还是 B**？—— 这是一次 DB 写，A 一行命令即可。
3. 另一处形态事实（供你安排后续）：**生产侧主题是真实目录、不是软链**（dev 才是软链到 `site-repo`）⇒ 生产**不随 `git pull` 自动生效**，任何主题改动都必须显式部署。

## 六、痕迹与终态

- 服务器 / 本地 `/tmp` 探针**全部删除**；临时管理员会话已 `destroy()`（保留你自己的 4 个）；mu-plugins 未动；主题文件与数据库**零改动**（`sf_shapes` / `sf_containers` / `sf_certifications` 仍不存在，`sf_global_faq` 仍未变）。
- 权威报告：`docs/shape-save-rootcause-2026-09-28.md`（含全部证据、复现命令、清理台账）。

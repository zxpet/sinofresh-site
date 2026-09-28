# 诊断报告：Shape Library 选图后保存不生效（2026-09-28）

> 范围：**只读诊断 + 现场复现 + 修复方案验证**。未修改生产站任何文件、未改主题代码、未改库（诊断期间的临时会话/探针已全部清理，见 §七；`wp_options` 计数与 `max_id` 全程恒为 565 / 7390）。
> 结论：**H14 已完整上线且正确；故障是第三个、H14 未覆盖的断点——sanitize 回调不幂等，导致「选项不存在时保存永不生效」的死锁。**
> 本次新增：① 方案 A 的幂等守卫**已在生产真实注册的回调上验证通过**（§五附，零写库）；② 两道零写库门入库 `tools/`（§六）；③ 顺带发现一处**线上用户可见的内容缺失**——「Factory & Trust」版块全站 21 页都不渲染（§八）。

---

## 一、结论速览

| 用户给的四个假设 | 判定 | 证据 |
|---|---|---|
| ① H14 没 pull 到生产 | **否** | 三方 md5 完全相同（§二） |
| ② 选图后隐藏字段没落值 | **否** | 实测 0 → 349，预览同步出图（§三） |
| ③ 没上生产所以要 pull | **否** | 已在生产，版本 1.0.3 |
| ④ 隐藏字段有值但保存后没了 | **是 —— 根因在此** | SQL 轨迹 + 幂等性证明（§四） |

**根因一句话**：`sf_shapes` / `sf_containers` / `sf_global_faq` 的 `sanitize_callback` **不幂等**。WordPress 在「选项尚不存在」时会**调用它两次**（`update_option()` 一次，委派给 `add_option()` 时再一次）。第二次拿到的是**已规范化的行数组**，回调按「平行数组」读 `$v['slug']` 等键 → 键不存在 → 判空 → 返回 `array()`；紧接着 H13 的「空则 `delete_option`」写侧钩子把刚建好的行删掉 ⇒ **保存静默失效**。

**死锁性质**：因为保存永远失败，选项永远不存在 ⇒ 永远走二次 sanitize 的 `add_option` 分支 ⇒ **永远存不进去**。只有「选项已存在」时才走单次 sanitize 的 `update_option` 更新分支，才会成功。

**另一处同源受害（见 §八）**：`sf_trust_*` 共 7 个选项被「保存设置页」这个动作盖成**空串** ⇒ 契约「空 = 关掉该行」生效 ⇒ **全站 21 个 formula 详情页的「Factory & Trust」版块整体不渲染**（实测：规格表 21/21 都在、信任带 21/21 都没）。

**修复就绪度**：方案 A 的幂等守卫**已在生产真实注册的回调上验证通过**（§五附），两道零写库门已入库 `tools/`（§六）。**尚未改动任何文件/数据**，等确认。

---

## 二、H14 是否已上生产 —— 已完整上线

| 文件 | 本地仓库 | dev | 生产 |
|---|---|---|---|
| `assets/admin/sf-site-settings.js` | `5330df8e84f774bf1eb58e84e468747d` | 同 | **同** |
| `inc/formula-admin.php` | `d5e6d407e3254258611eb300f2f28c55` | 同 | **同** |

- 选择器已是修复版 `input[name$="[attachment_id][]"]`（第 94、125 行），坏选择器 0 处。
- enqueue 版本 `1.0.3`（`formula-admin.php:772`），页面实际加载 `sf-site-settings.js?ver=1.0.3`（HTTP 200）。
- CF 边缘提供的字节与源站**逐字节相同**（`cf-cache-status: HIT`，md5 一致）⇒ 不是 CDN 缓存旧版。
- sanitize 已是 H14 的平行数组读法。
- ⚠️ **部署形态备注**：生产侧主题是**真实目录**（`/var/www/zxpet-v2/wp-content/themes/sinofresh-theme`，非软链），dev 侧才是软链到 `site-repo` ⇒ 生产**不随 `git pull` 自动生效**，必须显式部署。本次两侧 md5 相同，说明上一次部署已到位。（同时佐证：本故障与「没部署」无关。）

## 三、选图链路 —— 实测正常

用生产管理员会话驱动真实浏览器（Playwright，经 CF 走 `https://www.zxpet.com/wp-admin/admin.php?page=sf-shapes`）：

```
页面: title="Shape Library" / wp.media 可用 / 8 行 8 个隐藏字段皆为 0 / 预览为 :empty（显示 "no image"）
点第 1 行 Choose → 媒体弹窗打开（34 张可选）
选图 349 → 隐藏字段 : 0 → "349"
            预览     : 空 → <img src=".../fda-registration-sinofresh-150x150.png" width=80 height=80>
            :empty   : true → false（"no image" 占位消失）
            页面错误 : 无
```

⇒ **选图与预览这条链在生产完全正常**，H14 的选择器修复生效。

## 四、保存链路 —— 根因所在

### 4.1 现场复现（点保存 → 重载）

```
① 选图后   : hidden=349，预览有 <img>
② 点保存后 : 隐藏字段回到 0，预览回到空（"no image"）
             sf_shapes 选项仍不存在
```

保存请求本身是「成功」的：`POST /wp-admin/options.php` → **302 → `?page=sf-shapes&settings-updated=true`**。

### 4.2 SQL 轨迹（决定性证据）

在 `update_option('sf_shapes', <表单原样载荷>)` 前后挂了 `query` 过滤器，捕获到的真实 SQL：

```sql
SELECT option_value FROM wp_options WHERE option_name = 'sf_shapes' LIMIT 1
INSERT INTO `wp_options` (`option_name`,`option_value`,`autoload`)
  VALUES ('sf_shapes', 'a:0:{}', 'auto') ON DUPLICATE KEY UPDATE ...
SELECT autoload FROM wp_options WHERE option_name = 'sf_shapes'
DELETE FROM `wp_options` WHERE `option_name` = 'sf_shapes'      ← 建完立刻被删
```

- 写入的序列化值是 **`a:0:{}`（空数组）**，不是表单里的 8 行。
- `DELETE` 来自 H13 写侧钩子：`add_option_{$opt}` 收到空数组 → `delete_option()`。
- `update_option()` **返回 true**（`add_option()` 的 INSERT 成功了）⇒ 页面不报错，管理员看不到任何异常。

### 4.3 幂等性证明（纯函数，未写库）

把已注册的 sanitize 回调**连喂两次**（就是 WP 的真实调用序列），并对 `sf_site_settings` 组**全部 23 个选项**做普查：

| 选项 | 第 1 次 | 第 2 次 | 幂等？ |
|---|---|---|---|
| `sf_containers` | 8 行 | **0 行** | ❌ |
| `sf_shapes` | 8 行 | **0 行** | ❌ |
| `sf_global_faq` | 2 行 | **0 行** | ❌ |
| `sf_certifications` | 2 行 | 2 行 | ✅ 回调在 `functions.php:5924`，按 `[i][name\|url\|active]` 行主序读，天然幂等 |
| `sf_form_facts` / `sf_form_options` / `sf_contact_email` / `sf_nav_active_style` / `sf_factory_origin` / `sf_factory_oem` / 7 个 `sf_trust_*` | — | 与首次逐字节一致 | ✅ |
| 6 个纯文本项（`sf_working_hours` / `sf_contact_phone` / `sf_contact_address` / `sf_contact_whatsapp` / `sf_copyright_company` / `sf_copyright_suffix`） | — | 字符串 → 字符串 | ✅ `functions.php:5893`，`sanitize_text_field` + 空值回退默认，天然幂等 |

⇒ **需要修的精确是 3 个**：`sf_shapes`、`sf_containers`、`sf_global_faq`，且**全部位于 `inc/formula-admin.php`**（875 / 915 / 961 三处回调）。

非幂等的机制：第 1 次输入是表单的平行数组（`{slug:[],label:[],attachment_id:[]}`，此时 `$v[0]` 不存在）→ 正确产出 8 行；
第 2 次输入是**已规范化的行列表**（`[ {slug,label,attachment_id}, ... ]`，此时 `$v[0]` 存在）→ `isset($v['slug'])` 为假 → 三个数组都判空 → 返回 `array()`。

### 4.4 为什么 dev 上「验过」却没发现

- 选项 `sf_shapes` / `sf_containers` / `sf_certifications` 在 **dev 与 prod 两库里都不存在**（只有 `sf_global_faq` 存在，值为空数组）⇒ 两站都会走二次 sanitize 分支。
- H14 的门 `--preverify` 把新闭包**只应用一次**，`--live` 验的是**选图落值**（隐藏字段 + 预览），**没有验「保存 → 重载」**。⇒ 二次 sanitize 这条路径从未被门覆盖。**这是门的盲区。**

### 4.5 影响面

用户真实浏览器在源站日志里的保存记录（`Chrome/153`，非我的脚本 UA）：

```
09:20:20  POST options.php 302  referer .../page=sf-factory-info
09:20:39  POST options.php 302  referer .../page=sf-containers
09:20:55  POST options.php 302  referer .../page=sf-shapes
09:25:26  POST options.php 302  referer .../page=sf-shapes
09:26:09  POST options.php 302  referer .../page=sf-shapes
```

⇒ **可断言「必然未落库」的是 `sf-shapes`（3 次）与 `sf-containers`（1 次）**——这两个选项在库中不存在，走的正是二次 sanitize 的死锁路径。
（`sf-factory-info` 那一次**不下断言**：该页自身字段 `sf_factory_origin` / `sf_factory_oem` / `sf_form_facts` 都是幂等回调且已存在，可能已正常落库。已实测：这两个 `get_option` 有值、`sf_form_facts` 读者回退正常，与「能落库」一致、无法反证。但其保存**仍会触发 §8.3 的全组盖章副作用**。）

- 受影响（不存在 ⇒ 永远存不进去）：`sf_shapes`、`sf_containers`、`sf_certifications`、以及任何尚未存在的 `sf_site_settings` 组选项。
- 不受影响（已存在 ⇒ 走单次 sanitize 的更新分支）：`sf_global_faq`、`sf_form_options`、`sf_trust_*`、`sf_contact_*`、`sf_factory_*` 等。
- 与插件无关：`--skip-plugins` 下同样复现；TranslatePress 的 `pre_update_option` 过滤器经核查**无害**（仅在值含 `data-trpgettextoriginal=` 时动作）。

---

## 五、修复方案（**待确认，尚未执行**）

### 方案 A（推荐）：让 sanitize 回调幂等

在 `sf_shapes` / `sf_containers` / `sf_global_faq` 三个回调入口加一道**幂等守卫**——识别「已是规范化行列表」的输入并原样返回：

```php
'sanitize_callback' => function ($v) {
    /* 幂等守卫：WP 在选项不存在时会调用本回调两次
       （update_option 一次 + add_option 一次）。第二次传入的是
       已规范化的行列表，必须原样通过，否则会被判空抹掉。 */
    if (is_array($v) && isset($v[0]) && is_array($v[0])
        && array_key_exists('attachment_id', $v[0])) {
        return $v;
    }
    /* 以下为现有平行数组读取逻辑，不动 */
    ...
}
```

- 改动点：`inc/formula-admin.php` **三处**（`sf_containers` 第 877 行 / `sf_shapes` 第 917 行 / `sf_global_faq` 第 963 行，均在 `sanitize_callback` 闭包开头）。
- 覆盖 `sf_certifications` 复核（普查实测已幂等，建议补一条断言把它钉住）。
- 风险：低。守卫只在「输入已是目标形状」时直通，表单送来的平行数组不含 `0` 索引的行数组，不会被误判。

#### 方案 A 已在**生产真实注册的回调**上验证通过（纯函数、零写库）

把守卫套在生产站真实注册的回调上、按 WP 的真实调用序列跑两遍（探针 `/tmp/sf-guard-proof.php`，**未调用任何** `update_option` / `add_option` / `delete_option`；跑前跑后 `wp_options` 计数恒为 565、`max_id` 恒为 7390）：

| 选项 | 不加守卫 | 加守卫后 | 守卫对表单载荷误触发？ | 首遍输出逐字节不变？ | 两次调用走的分支 |
|---|---|---|---|---|---|
| `sf_shapes` | 8 → **0** | 8 → **8** ✅ | no | yes | `callback + guard` |
| `sf_containers` | 8 → **0** | 8 → **8** ✅ | no | yes | `callback + guard` |
| `sf_global_faq` | 2 → **0** | 2 → **2** ✅ | no | yes | `callback + guard` |

⇒ 守卫既能复现并修掉缺陷，又**不改变首遍（表单）行为**；分支序列 `callback + guard` 正是设计意图（第一次照常解析、第二次直通）。

### 方案 B（辅助/应急）：预置选项绕开二次 sanitize

先把选项写成默认值（`add_option('sf_shapes', sf_default_shapes())` 等），使其存在 ⇒ 之后保存走单次 sanitize 的更新分支。**仅作应急，不修根治**（新装的站还会踩），且不改 `sf_certifications` 的隐患。

### 配套：补门

- `h14_gate.py` 增加**二次应用**断言：`apply(apply(payload)) === apply(payload)`（幂等）。
- 增加**真实保存门**：走 options.php 的 `add_option` 分支（选项不存在时保存）并断言选项落库 —— 这才覆盖到 H14 漏掉的路径。
- 门不得只测「回调应用一次」。

### 连带项

- ⚠️ **已升级为独立发现，见 §八**：生产库 7 个 `sf_trust_*` 是空值 ⇒ 全站 21 个详情页的 **「Factory & Trust」版块整体不渲染**。这不是卫生问题，是线上内容缺失。（`sf_trust_*` 在 9/20 的 dev 转储里**根本不存在**，说明它们是被「保存设置页」这个动作**盖出来的空值**，不是人工置空。）
- `wordpress-zxpet.conf` 的管理端 POST 走 CF（`cdn-cgi/rum`）——本次诊断确认不影响保存语义，仅备注。

---

## 六、复现与验证命令（可复用 · 已入库）

两道门已沉淀进仓库 `tools/`（**不随主题部署**，跑时拷到服务器 `/tmp`；均为纯函数、**零写库**，跑前跑后 `wp_options` 计数应恒定）：

```bash
# H15 门（对照）：证明缺陷可复现 + 方案 A 守卫可修 + 首遍行为零漂移；退出码 0=通过
scp tools/sf_sanitize_guard_proof.php root@<host>:/tmp/
ssh root@<host> 'cd /var/www/zxpet-v2 && \
  wp eval-file /tmp/sf_sanitize_guard_proof.php --url=https://www.zxpet.com --allow-root; echo "EXIT=$?"'

# H15 门（普查）：全设置组 23 个选项的幂等清单；回答「到底几个要修」
scp tools/sf_sanitize_idem_sweep.php root@<host>:/tmp/
ssh root@<host> 'cd /var/www/zxpet-v2 && \
  wp eval-file /tmp/sf_sanitize_idem_sweep.php --url=https://www.zxpet.com --allow-root'

# 现场复现（浏览器）：带管理员会话开页面 → 选图 → 保存 → 重载，看 hidden 是否回 0
```

> ⚠️ 这两道门**不改任何状态**，因此**修前修后都可跑**：修前应看到「8 → 0 / 2 → 0」，修后应看到「8 → 8 / 2 → 2」。这就是方案 A 的验收判据。

## 七、诊断期间的痕迹与清理（全部已还原）

| 项 | 处理 |
|---|---|
| 两个临时管理员会话（`wp_generate_auth_cookie` 生成） | 已 `destroy()`，剩余会话为用户自己的 4 个 |
| 服务器 `/tmp` 诊断脚本（`sf-*.php`、`wl.php`） | 已删除；`/tmp/sf-guard-proof.php`、`/tmp/sf-idem-sweep.php`、`/tmp/sf_sanitize_*.php` 亦跑完即删 |
| 本地 `/tmp` 截图与脚本 | 已删除（`sf-*.php`、`ff-shape-*.cjs`、`.png` 均无残留） |
| 仓库 `tools/sf_sanitize_guard_proof.php`、`tools/sf_sanitize_idem_sweep.php` | **新增（有意保留）**：两道零写库门，供修前修后复跑 |
| mu-plugins | **未改动**（仍只有 `zz-sf-wps-consent-bridge.php`） |
| 主题文件 / 库数据 | **未改动**；`wp_options` 计数与 `max_id` 全程恒为 **565 / 7390** |
| `sf_shapes` / `sf_containers` / `sf_certifications` | 导入时不存在、现在仍不存在（保存本就失败） |
| `sf_global_faq` | 导入时即存在（空数组），现在仍存在、仍未变 |

> 注：`/tmp/sf-h7i-meta.php`、`/tmp/sf-h7i-setmeta.php` 是历史批次（H7i）遗留的服务器脚本，非本次产生，未动。

---

## 八、顺带发现：`Factory & Trust` 版块全站缺失（同源第二个受害者）

> 诊断主因时顺手核了同一批选项，发现这处**线上用户可见的内容缺失**。与主因**同一个机制家族**（`sf_site_settings` 组 + 保存设置页时的全组写回），但**后果不同**。

### 8.1 现场证据（只读）

| 判据 | 结果 |
|---|---|
| 线上 formula 详情页总数 | 21 |
| HTTP 200 | 21 / 21 |
| **规格表 shortcode 已渲染**（自证 shortcode 确实在跑） | 21 / 21 |
| **含 `Factory & Trust` 版块** | **0 / 21** |
| 缺该版块 | **21 / 21** |

`sf_formula_trust_value()` 在生产实测：

```
sf_trust_factory_size    get_option=''   trust_value=''
sf_trust_cleanroom       get_option=''   trust_value=''
sf_trust_capacity        get_option=''   trust_value=''
sf_trust_export_markets  get_option=''   trust_value=''
sf_trust_ontime          get_option=''   trust_value=''
sf_trust_response        get_option=''   trust_value=''
sf_trust_reorder         get_option=''   trust_value=''
```

### 8.2 为什么「不该缺」

`sf_trust_defaults()`（`functions.php:3329`）为 7 项中的 **4 项**备了出厂值：

| 键 | 出厂默认 | 当前实际 |
|---|---|---|
| `sf_trust_factory_size` | `15,000㎡` | **（空 → 不打印）** |
| `sf_trust_cleanroom` | `ISO 8` | **（空 → 不打印）** |
| `sf_trust_capacity` | `''`（设计上就是关的） | 空 |
| `sf_trust_export_markets` | `30+ countries` | **（空 → 不打印）** |
| `sf_trust_ontime` | `''`（设计上就是关的） | 空 |
| `sf_trust_response` | `Within 24 hours` | **（空 → 不打印）** |
| `sf_trust_reorder` | `''`（设计上就是关的） | 空 |

而 `sf_formula_trust_value()`（`functions.php:3342`）的契约是：

```php
$stored = get_option($key, null);
if ($stored === null) { return $d[$key]; }   // 从未保存过 ⇒ 出厂默认生效
return trim((string) $stored);               // '' ⇒ 这一行关掉
```

⇒ 只有「选项**完全不存在**」时出厂默认才生效。现在选项**存在但等于空串**，于是 4 个本该打印的行被当成「人工关掉」，「Factory & Trust」整段（含 `<h2>`）不产出。

### 8.3 空值是怎么来的（时间线）

| 证据 | 结论 |
|---|---|
| 9/20 的 dev 转储 `/root/sinofresh-db.sql.gz` 里 **grep 不到任何 `sf_trust_*`** | 9/20 时这 7 个选项**根本不存在**（当时出厂默认正常生效） |
| 生产 `option_id`：`sf_form_facts`=5252，`sf_trust_*`=**5253–5259**（紧随其后） | 它们是 **H10 批次开发期**被创建的 |
| `wp-admin/options.php:336-340`（WP 7.1.2 实测）：<br>`$value = null; if ( isset($_POST[$option]) ) { $value = $_POST[$option]; }` | **保存组内任一页面时，组内每个选项都会被写一次**；该页没有对应字段的选项被写成 `null` → 过 `sanitize_text_field` → **变成空串并建行** |
| dev 与 prod 的 21 个 `sf_*` 选项 option_id 与长度**逐项完全一致** | 生产是原样继承 dev 的状态（非本次诊断产生） |

⇒ 是「保存任意设置页 → 全组 23 个选项被盖章」的副作用，**不是有人手工清空**。

### 8.4 处置（**未执行，等你定**）

两种都只需一次 DB 写：

- **A（推荐，恢复默认）**：删除这 7 个 `sf_trust_*` 选项 → 回到「从未保存」状态 → 4 个出厂值恢复打印，3 个设计上关着的仍不打印。
  `wp option delete sf_trust_factory_size sf_trust_cleanroom ...`（7 条）
- **B（改为显式落值）**：把 4 个有意义的写成目标文案、3 个保持空 → 语义与现在一致，但「谁关谁开」写死在库里，便于运营改。

> 附带结论：`sf_form_facts` 也是空数组（`a:0:{}`），但它的读者在**读取时**回退出厂值，实测 `soft-chews/moq` 等 8 项全部正常 ⇒ **无害**，不需要动。全组 23 个选项里，**只有这 7 个信任行被空值伤害**。

### 8.5 复现命令

```bash
# 全站扫描：规格表 vs 信任带（应看到 21/21 vs 0/21）
ssh root@<host> 'cd /var/www/zxpet-v2
mapfile -t URLS < <(wp post list --post_type=sf_formula --post_status=publish \
  --field=url --posts_per_page=-1 --allow-root --url=https://www.zxpet.com)
for U in "${URLS[@]}"; do
  curl -sk -H "Host: www.zxpet.com" "https://127.0.0.1${U#*zxpet.com}" \
    | grep -qoE "sf-fdetail-(specs|trust)" | sort -u | tr "\n" " "; echo
done'

# 取值现场
ssh root@<host> 'cd /var/www/zxpet-v2 && wp eval \
  "foreach(sf_trust_defaults() as \$k=>\$dv){ printf(\"%-24s default=[%s] stored=[%s] out=[%s]\n\", \$k, \$dv, var_export(get_option(\$k,null),true), sf_formula_trust_value(\$k)); }" \
  --url=https://www.zxpet.com --allow-root'
```

> ⚠️ 扫描脚本的路径拼接坑（本次亲踩）：`${U#*zxpet.com}` 已含前导 `/`，再拼 `"/"` 会得到 `//formulas/...` → **301 空体**，于是所有页面都被误判成「没有规格表」。凡拿 `--field=url` 拼本地 loopback 请求，务必**自证 HTTP 200 与「该有的东西确实在」**（本次靠 `specs 21/21` 自证 shortcode 真的跑了）。

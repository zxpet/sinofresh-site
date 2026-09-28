# H15 执行报告 · Shape/Container/FAQ 保存失效修复 + Factory & Trust 版块恢复

> 生成时间：2026-09-28（北京时间）
> 授权：用户批准「方案 A」＋三项强制要求（两处修复 + 必须一并处理保存副作用盖章 + 显式部署生产）
> 上一项：诊断报告 `docs/shape-save-rootcause-2026-09-28.md`（只读诊断）
> 结论：**4/4 项验收全部通过；生产已上线；生产选项净变化 = 恰好删除 7 个 `sf_trust_*`**

---

## 一、改了什么（一句话）

| # | 修复 | 落点 | 状态 |
|---|---|---|---|
| 1 | 3 处 **sanitize 幂等守卫**（`sf_shapes` / `sf_containers` / `sf_global_faq`） | `sinofresh-theme/inc/formula-admin.php`（875 / 932 / 987 行，回调**第一句**） | ✅ 已部署生产 |
| 2 | **保存副作用盖章** 全局治理：组内 23 个选项加 `pre_update_option_*` 守卫（未提交的字段**一个字都不写**） | 同文件 ~1136 行（`admin_init` 优先级 99） | ✅ 已部署生产 |
| 3 | **Factory & Trust 回填**：Factory Information 页的 7 个信任输入改用 `sf_formula_trust_value()` 渲染 | 同文件 ~1384 行 | ✅ 已部署生产 |
| 4 | 删除生产上被盖空的 **7 个 `sf_trust_*` 选项**（回到「从未保存」＝出厂默认） | 生产 DB | ✅ 已执行 |

改动文件只有一个：`sinofresh-theme/inc/formula-admin.php`
- 改前 md5 `d5e6d407e3254258611eb300f2f28c55`（72931 B）
- 改后 md5 `1a603e819fb8ae7ed26ee3d06a409231`（77585 B）
- 本地 / dev / 生产**三方 md5 相同**；`git status` 对生产文件为空（生产 == HEAD `537cc8f`）

---

## 二、修复 1：三处幂等守卫 —— 为什么这样修

**病根（复述）**：选项**不存在**时 WP 把 `sanitize_callback` 调**两次**（`update_option()` 一次 → 因无既存值委派 `add_option()` 再一次）。第二次收到的是**已规范化的行列表**，而回调按**表单的平行数组形状**读 `$v['slug']` → 判空 → 返回 `array()` → H13「空则 `delete_option`」把刚建的行删掉；`update_option()` **仍返回 true** ⇒ 后台显示「已保存」，毫无报错。

**修法**：回调入口识别「输入已是本回调自己的输出形状」并**原样返回**：

```php
if (is_array($v) && isset($v[0]) && is_array($v[0]) && array_key_exists('attachment_id', $v[0])) {
    return $v;   // 已是行列表 ⇒ 幂等返回，绝不进入按表单形状解析的分支
}
```
（`sf_global_faq` 同型，探针键换成 `'q'`。）

**为什么不给 `sf_certifications` 也加**：它的回调在 `functions.php:5924`，**行主序、天然幂等**，普查已证；给它加守卫属于画蛇添足。但它**同样会被盖章**，由修复 2 的组级守卫覆盖 —— 两件事别混。

**零写库对照门**（`tools/sf_sanitize_guard_proof.php`，生产实测）：

| 选项 | 首遍 | 二遍 == 首遍？ | 行数 == 期望？ | 判定 |
|---|---|---|---|---|
| `sf_shapes` | 8 行 | yes | yes | PASS |
| `sf_containers` | 8 行 | yes | yes | PASS |
| `sf_global_faq` | 2 行 | yes | yes | PASS |

外加两项负对照：**守卫不误触发**（平行数组的表单载荷仍被正常解析，8/8 行）、**守卫不误放行**（形状像行列表但缺探针键 ⇒ 输出 0 行，仍在解析分支）。→ `退出码 0`

**全组 23 项普查**（`tools/sf_sanitize_idem_sweep.php`，生产实测）：
```
非幂等（需要守卫）: 无
纯文本型（天然幂等，未取载荷）: sf_working_hours, sf_contact_phone, sf_contact_address,
                              sf_contact_whatsapp, sf_copyright_company, sf_copyright_suffix
未注册回调: 无
设置组选项总数: 23
```
⇒ **「只修已知三个、漏掉同型缺陷」的风险已被排除。**

---

## 三、修复 2：保存副作用盖章 —— 用户强制要求的那一项

你要求：*「让保存逻辑跳过空字段，或者确认这 7 个字段保存后不会被重新写 null，否则下次保存 Settings 页又复发」*。

**盖章机制（已在源码逐行核实）**：`wp-admin/options.php` 把整组的**每一个**选项都写一遍；本页没有对应字段的选项，`$_POST[$option]` 不存在 ⇒ `$value = null` ⇒ `update_option($option, null)` ⇒ 过 sanitize ⇒ **变成空串并建行**。对「**空串 = 这一行关掉**」型读者（`sf_formula_trust_value()`）就是**静默内容消失**。

**修法（＝「跳过未提交字段」，落在写侧，改动面最小）**：给组内 23 个选项各挂一个 `pre_update_option_{$opt}` 过滤器：

```php
add_action('admin_init', function () {
    $allowed = apply_filters('allowed_options', array());
    $guard   = isset($allowed['sf_site_settings']) ? array_values((array) $allowed['sf_site_settings']) : array();
    foreach ($guard as $sf_guard_opt) {
        add_filter("pre_update_option_{$sf_guard_opt}", function ($value, $old_value, $option) {
            if (isset($_POST['option_page']) && 'sf_site_settings' === $_POST['option_page'] && !isset($_POST[$option])) {
                return $old_value;   // 本页没有这个字段 ⇒ 一个字都不写
            }
            return $value;
        }, 10, 3);
    }
}, 99);
```

**为什么这个钩子位是最优解**：`pre_update_option_*` 在 `sanitize_option()` **之后**、在 `$value === $old_value` 短路**之前**执行 —— 返回旧值即让 `update_option()` 提前 return，**完全不落库**。而「本页没有这个字段」⇒ 该字段**从未被 sanitize**，因此**不需要逐字段幂等**（这是修复 1 与修复 2 正交的原因）。
**同时不破坏正常语义**：管理员**真的**把某个框清空（该字段确实在 `$_POST` 里、值是 `''`）⇒ 守卫放行 ⇒ 照常写成 `''` ⇒ 该行照常关掉。**「主动关掉」与「被误盖」被彻底区分。**

**生产实测（7 个设置页逐一真发 `options.php` POST，`tools/sf_settings_stamp_gate.php`）**：

| 页面 | 保存 | ①探针确实落库 | ②非本页字段逐字节不变 | ③本页已存在字段不变 | ④信任带 4/4 非空 |
|---|---|---|---|---|---|
| `sf-site-settings` | 302 ✅ | ✅ | ✅（14 项） | ✅ | ✅ |
| `sf-shapes` | 302 ✅ | ✅ | ✅（22 项） | ✅ | ✅ |
| `sf-containers` | 302 ✅ | ✅ | ✅（22 项） | ✅ | ✅ |
| `sf-global-faq` | 302 ✅ | ✅ | ✅（22 项） | ✅ | ✅ |
| `sf-factory-info` | 302 ✅ | ✅ | ✅（14 项） | ✅ | ✅ |
| `sf-form-facts` | 302 ✅ | ✅ | ✅（22 项） | ✅ | ✅ |
| `sf-form-options` | 302 ✅ | ✅ | ✅（22 项） | ✅ | ✅ |

**7/7 页全绿，共 63 项断言 0 FAIL。** 其中对本次修复最关键的证据是 ② 里这一行形态：

```
   sf_trust_factory_size      [不存在] unchanged
   sf_trust_cleanroom         [不存在] unchanged
   ...（7 项全部）
```
即**「保存任何一页后，7 个信任选项仍处于『不存在』状态」** —— 不是「值没变」，而是**根本没被创建**。修复前它们会在这里被写成空串。

**门自身零残留（实测）**：跑完 7 页后与跑前逐项比对 → 新增 0、消失 0、值变化 0。⇒ 门不会把副作用留在库里。

---

## 四、修复 3/4：Factory & Trust 版块恢复

- **回填**：Factory Information 页的 7 个信任输入原本用 `get_option($key, '')` 渲染 ⇒ 选项不存在时**显示空框**，管理员一保存就把「空」写进去。改为 `sf_formula_trust_value($key)` 渲染后，**页面上显示的永远是生效值**（出厂默认），保存即持久化为同一串 ⇒ 之后「刚打开就保存」不再有破坏性。
- **删选项（生产，一行命令）**：删除全部 7 个 `sf_trust_*` ⇒ 回到「从未保存」⇒ 4 个出厂值恢复显示。
  实测（删除前后 raw `wp_options` 比对）：`21 → 14`，被删的**恰好**是这 7 个，**无新增、无值变化、无残留**。

**生产全站扫描（`tools/sf_factory_trust_scan.php`）—— 验收 ③**：
```
host=www.zxpet.com  配方页数=21  期望每页行数=4
   ... 21 页逐页：code=200  specs≥38  band=1  rows=4  OK
   达标 21/21 页   信任带行数合计=84（应为 84）
=> H15 验收③通过
```
（`specs` 计数是**自证短码真的跑了**的锚点 —— 防止「没有信任带」其实只是拿到一份空壳。）

**渲染内容核对**（抓真实页面、剥标签取可见文本）：
```
Factory & Trust | Factory Size 15,000㎡ | Cleanroom Class ISO 8 |
Export Markets 30+ countries | Response Time Within 24 hours
```
4 个出厂值齐全；设计上关闭的 3 行（Capacity / On-time / Reorder）**正确地不出行**。

---

## 五、四项验收 —— 逐条对账

| # | 你的验收标准 | 结果 | 证据 |
|---|---|---|---|
| **1** | Shape Library 选图 → 保存 → 刷新 → 图还在 | ✅ | **生产真浏览器**：前置 `attachment_id=0`（选项**不存在**，正是 bug 的发威条件）→ 选图（`data-id=53`）→ 保存（**302 → `settings-updated=true`**）→ 刷新 → 字段仍 `53`、缩略图仍在、8 行未丢。DB 真值 `row0 = {"slug":"bone","label":"Bone","attachment_id":53}` |
| **2** | Container Library 同样 | ✅ | 同上：`pre=0` → `picked=53` → 保存 → 刷新仍 `53`，7 行未丢。DB `row0 = {"slug":"round","label":"Round","attachment_id":53}` |
| **3** | 21 个配方页，Factory & Trust 版块显示出来 | ✅ | 生产 **21/21** 页 HTTP 200、每页 `band=1`、`rows=4`、合计 84；内容 = 4 个出厂值 |
| **4** | 保存任一 Settings 页后，这 7 个选项没被重新盖空 | ✅ | 生产 **7/7** 设置页逐一保存，7 个 `sf_trust_*` 在每一页保存后**仍为「不存在」**（② 断言 `[不存在] unchanged`）；附带 `sf_formula_trust_value()` 4 项非空全绿 |

> 验收 1/2 是在**生产**上做的（走 Cloudflare、真 Chromium、真媒体弹窗、真 302），不是只在 dev。做完后已把测试产物删除，生产**回到改动前的「未保存」态**。

---

## 六、部署记录（生产是真实目录，不随 `git pull` 生效）

按「dev 验证 → 部署生产」的顺序执行：

1. 取生产部署前指纹：`d5e6d407e3254258611eb300f2f28c55`，`apache:apache 644`。
2. 备份到 `/root/h15-rollback-prod-formula-admin.php`（md5 已核）。
3. 备份选项：7 个 trust → `/root/h15-prod-trust-options-backup.json`；全量 `sf_*` → `/root/h15-prod-sf-options-backup.json`。
4. 核 opcache：`validate_timestamps=On`、`revalidate_freq=2` ⇒ **无需 reload php-fpm**。
5. 原子替换：`scp` → `inc/.formula-admin.php.new` → `php -l` 无语法错 → md5 核对 → `mv` 就位 → `chown apache:apache` / `chmod 644`。
6. 终态：`apache:apache 644 77585 B md5 1a603e819fb8ae7ed26ee3d06a409231`，与本地逐字节一致。

**生产净变化（与动手前逐项 raw 比对）**：
```
改动前 21 个 sf_* 选项 → 现在 14 个
改动前存在、现在消失: sf_trust_capacity / cleanroom / export_markets / factory_size
                    / ontime / reorder / response     ← 恰好这 7 个（＝预期改动）
现在多出来的: 无
值有变化:     无（其余 14 项逐字节相同）
```

---

## 七、过程中发现并修正的「门自身缺陷」（值得记住）

`sf_settings_stamp_gate.php` 的 ③ 断言原版把「本页拥有的字段」**任何**变化都判 FAIL。但生产上 `sf_certifications` 本就**不存在**（出厂默认态），页面用 `get_option($k, sf_default_certifications())` 渲染 ⇒ 保存后该选项被**创建**，内容与代码默认**逐字段相同**（已核 `sf_default_certifications()`）。这是 **options.php 回填（round-trip）的既定行为**，用户可见内容零变化，**不是回归**。

处置（门升级 v3）：
- ③ **只对「原本存在、保存后变了」判 FAIL**；「原本不存在→被创建」降级为 INFO 并打印出来；
- 普通模式的**还原范围**从「只还原探针」扩到「探针 + 回填创建项」，让门**零残留**。实测升级后跑 7 页：新增 0 / 消失 0 / 值变化 0。

> 教训：**断言「字段没变」时必须先区分「原本不存在」与「原本是空串」** —— 这与本次 bug 的病根本身是同一类混淆。

---

## 八、回滚路径（都在手上）

| 对象 | 回滚物 | 方法 |
|---|---|---|
| 主题文件 | `/root/h15-rollback-prod-formula-admin.php`（md5 `d5e6d407…`） | `mv` 回 `inc/formula-admin.php` + `chown apache:apache` |
| 7 个 trust 选项 | `/root/h15-prod-trust-options-backup.json` | 按 json 逐项 `UPDATE/INSERT`（**别用 `update_option('')`**，见下） |
| 全量 sf_* 选项 | `/root/h15-prod-sf-options-backup.json` | 同上 |
| dev 侧 | `/root/h15-rollback-dev-formula-admin.php` + `/root/h15-trust-options-dev-backup.sql` | 同上 |

⚠️ 回滚选项**必须走裸 SQL**：数组型选项「还原成空数组」经 `update_option()` 会被 H13 钩子实际执行成 **delete_option**，字节对不上（实测把 `sf_global_faq` 的 `a:0:{}` 弄丢过，已修复该还原路径）。

---

## 九、遗留事项

1. **P6（打开收录）仍未执行** —— 站点当前仍是 `noindex`，等你的收件箱核对后再开。
2. 请核对真实收件箱 `sales@zxpet.com`（SMTP 双邮件实测是上一批做的，本次未涉及）。
3. `tools/p2_preverify.py` 已过时（指向已删的 `:8080` 临时 vhost），回归门需改指正式站。
4. 生产侧主题是**真实目录**：以后任何主题改动都要**显式部署**，不能只 `git pull`。
5. 深化的两条（可选）：给 `sf_factory_info` 页的信任字段加一行「清空即关闭该行」的说明文案；把 `sf_default_certifications()` 的 2 行空填充行从默认值里去掉（省得每次保存后 8 行变 6 行）。

---

## 十、痕迹清理台账

- 生产 / dev 的 mu-plugins：**无临时探针**（dev 仅 `zz-sf-dev-lockdown` / `zz-sf-preflight*` / `zz-sf-wps-consent-bridge`；生产仅 `zz-sf-wps-consent-bridge`）。
- 服务器 `/tmp` 与本地 `/tmp` 的 H15 探针、cookie、截图、门输出：**已删除**。
- 本次创建的两枚管理员会话 token：**已 `destroy()`**（不触碰用户自己的会话）。
- 生产选项终态见 §六；除 7 个 trust 的预期删除外，**零副作用**。

# Batch GO — 上线前清理 ＋ dev 站上线（2026-09-23）

> 授权：用户明确下令「执行上线前清理 + dev 站上线」，含此前十一批一律跳过的 Step 6（`git pull`）与 DB 写。
> 生产站（zxpet.com）本批不碰；dev 封锁（Basic Auth）保留。

## 0. 扫描结论（先于一切写入）

| 项 | 事实 | 判定 |
|---|---|---|
| `.gitignore` | `**/_backup/` 规则**已在**（上批止血时加），注释写明「已入库的历史文件需要单独 git rm --cached」 | 只需 `git rm -r --cached` |
| 受追踪 `_backup` | 348 个文件、全部在 `sinofresh-theme/_backup/`；23 个路径含 basket、42 个文件内容引用 basket | 无代码引用（仅 docs 散文提及） |
| 服务器仓库 | `/var/www/dev.zxpet.com/site-repo`，HEAD `57f73d0`（H2a 收尾），工作区干净，可 ff-only | pull 即生效 |
| 主题链接 | `public/wp-content/themes/sinofresh-theme` → **symlink** 到 repo | pull 无需复制步骤 |
| authority guard 的阴影风险 | dev DB 的 `wp_template` 行 **9 条、全部 `post_status=trash`**（`__trashed` 后缀） | **无已发布 DB 模板可遮蔽文件 ⇒ 删守卫安全** |
| 工具依赖 | 预检安装走 `git archive <SHA>`，不依赖 `_backup/` 工作树 | 移出追踪安全 |

## 1. post 158 测试值 —— 扫描与手册不符，升级用户后改判

手册列 3 处；实查 **5 处**（同一次 18:21:29 wp-admin 编辑写入，`_edit_last=1`）：

| meta_key | meta_id | 值 |
|---|---|---|
| `sf_formula_recommended_for` | 555 | `testsadasdfasf` |
| `sf_formula_use_cases` | 556 | `sdasdasdasdasd`（手册抄成 `sdasdasdasad`） |
| `sf_formula_price_tiers` | 566 | `[{"qty":"200","price":"2.5"}]` |
| `sf_formula_who_for` | 557 | `asdasdasdasdfgggffff`（手册未列） |
| `sf_formula_cartons` | 560 | `[{"count":"saasd","boxes":"","size":""}]`（手册未列） |

**裁决**：用户选择**改由自己从 wp-admin 清**，本批跳过 DB 写。5 处原值存
`_backup/b2d-go-post158/originals.json`（含 meta_id，回滚 = `wp post meta add 158 <key> <value>`）。
截稿时 5 值仍在前台（curl 逐串命中），**这是上线前仅剩的用户侧动作**。

字段归属（供后台清理参考）：三个文本字段渲染在阅读区正文块
（`sinofresh_formula_content()`，functions.php `2783/2792/2812`）；**H7c 的 12 行参数明细表不读它们**，
其行源 = taxonomy `sf_formula_form` ＋ `species/lifestage/shape/specs/ingredients` ＋ 剂型页 MOQ ＋
Site Settings 三项（`sinofresh_formula_specs_table()`，空即整行不渲染）。故清理**不减行数**：post 158
今天就是 10 行（species/lifestage 全站缺、shape=Custom 在），清理后仍 10 行。
`price_tiers` 另喂右栏「Quantity & Pricing」与 JSON-LD `offers`（`functions.php 2145/3146/5799`）。

## 2. `_backup/` 移出版本控制 — `16db3db`

`git rm -r --cached sinofresh-theme/_backup/`（348 个删除全部只动索引）。
验证：`git ls-files` 计 0；本地工作树 392 个文件原样保留；push 后 `origin/main` 同步。
**服务器 pull 后 `sinofresh-theme/_backup/` 从磁盘消失**（预期；其中 23 个文件是购物篮的历史阶段副本）。

## 3. authority guard 删除 — `d29c002`

- 备份先行：`sinofresh-theme/_backup/authority-guard-removal-20260923/functions.php`（sha `d8539adc…`＝改动前态）。
- 删 `pre_get_block_template`（原 75–111 行）与 `get_block_templates`（原 113–136 行）两过滤器，**纯删除 64 行、0 新增**。
- `php -l`（LocalWP php-8.2.29）通过；两钩子名残留计数 0。
- 令牌：**未动 style.css ⇒ 不 bump**，`2.10.67` 两处同步不变。functions.php 新 sha `8be8df1b…`。
- ⚠️ 代价记录：守卫注释里的两次事故（DB 模板遮蔽 front-page/header 文件）失去防线；
  现有 9 条 DB 行全在回收站，**今后任何人用 Edit Site 保存模板都会重新制造遮蔽**——这是用户知情选择。

## 4. dev 上线 — `git pull --ff-only`

`57f73d0 → d29c002`（ff-only，工作区干净）。live 主题经 symlink 立即变 `2.10.67`。

## 5. 验收（curl ＋ 浏览器，全带凭据）

**curl（服务器侧）**：匿名 **401**／带凭据 **200**；`style.css?ver=2.10.67`；
详情页全页 h1＝1 且＝右栏 `sf-fdetail2__title`；`sf-fdetail-specs__row` **10 行**；
`sf-basket-btn`／`sf-basket-drawer`／`basket.js` 计数 **0/0/0**；浮栈在位。

**浏览器（agent-browser，Python subprocess 顺序驱动）**：
- 详情页：H1 在右栏且为 `.sf-fdetail2__side` 首子元素（x=859）；参数表 10 行；0 basket 元素/脚本。
- 详情页滚动到参数带（y=1728）：浮钮 `hidden` 被 inquiry.js 摘除、`display:flex`、盒子 150×52、
  `elementFromPoint` 命中按钮本身、label "Send Inquiry"。
- 产品页 `/products/soft-chews/`：facts-mini 恰 4 项（flex，第 4 项 Packaging 值长自然换行）、盒子两两不重叠；
  **7 张卡片图**（`.sf-tile__media > a > img`，tablets→dental-chews）全部 `loaded` 且命中测试可点；
  浮栈 fixed＝WhatsApp/Email/回顶部；**0 basket**；两页 **0 页面错误、0 console error**。
- 证据帧 3 张（`docs/batchGO-shots/`，1440×900、distinct=256 非平帧）。

## 6. 本批两条新踩坑（验收断言侧，非站点缺陷）

1. **`agent-browser close` 后新开的会话不带凭据** ⇒ `open` 落在 401 页上，
   页面内容查询**全部 0 命中**，症状像「选择器错了」。守卫＝每个新会话先 `set credentials` 再 `open`，
   且任何 0 命中先验 `location.pathname + document.title` 证明拿到的是被服务的页面。
2. **悬浮 Send Inquiry 的可见性是「滚到参数带才摘 `hidden`」**，且 shortcode
   「非详情页返回空串」是设计契约（`functions.php` docblock 明说）——
   验收断言必须写成两段式（详情页滚动后出现＋产品页按设计缺席），写「存在」会假红。

## 7. 状态与遗留

- 提交：`16db3db`（_backup 移出）＋ `d29c002`（guard 删除）＋ 本档。`HEAD == origin/main`。
- 服务器：`site-repo` HEAD `d29c002`；live＝**`2.10.67`**（非 preflight 首次跟上）；`_backup/` 已从服务器消失。
- 预检副本仍＝`0b015e1`（`2.10.67` ＋ 有 guard），相对 live 已**过时**——是否删除/重装待用户裁决（本批未动）。
- **遗留（用户侧）**：① 后台清 post 158 的 5 处测试值（清单见 §1）② 生产上线前 `docs/dev-lockdown.md` 的 10 项移除（本批未做，dev 封锁保留）。
- 登记未动：`tools/_cert_basket_regression.js` 引用已删 UI；Organization schema 手抄地址默认值；
  `page-about.html`/`page-contact.html` 正文同串；H7a ARIA 建模。

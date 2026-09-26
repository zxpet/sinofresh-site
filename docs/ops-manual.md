# 中鲜宠食官网运维管理手册

> 版本：v1.0（基于 2026-09-26 dev 站实况扫描，主题 2.10.86）
> 适用对象：管理人员 / 编辑人员 / 专职网站维护人员
> 维护约定：本手册随网站批次更新同步修订；文中"技术支持"指网站开发者（Sam）。

---

## 目录

- 第 1 章 网站概览
- 第 2 章 后台基础操作
- 第 3 章 内容编辑总则（核心原则）
- 第 4 章 各页面编辑指南
- 第 5 章 产品详情页编辑详解（重点）
- 第 6 章 配置器十组详解
- 第 7 章 多语言管理
- 第 8 章 表单与询盘管理
- 第 9 章 网站设置（Site Settings）
- 第 10 章 日常维护
- 第 11 章 安全与合规
- 第 12 章 常见问题 FAQ
- 第 13 章 重要禁令（红线）
- 第 14 章 应急处理
- 第 15 章 附录

---

# 第 1 章 网站概览

## 1.1 网站技术栈

| 项目 | 实际值 |
|---|---|
| 建站系统 | WordPress 7.1.2（当前运行于 dev 环境生产将同版本上线） |
| 主题 | 自研区块主题 **sinofresh-theme**（当前版本 2.10.86），不走市场主题更新 |
| 表单系统 | Fluent Forms 6.2.14（免费版） |
| 多语言 | TranslatePress 3.3.6（免费版，当前仅发布 English） |
| 统计 | Cloudflare Web Analytics（无 Cookie）＋ WP Statistics 14.16.14（经同意后启用） |
| 同意框架 | WP Consent API 2.1.0 ＋ 站点自研 Cookie 横幅 |
| 邮件日志 | WP Mail Logging 1.16.0 |
| 数据库 | MariaDB（MySQL 兼容） |
| 服务器 | LEMP/云主机，dev 域名 dev.zxpet.com（Apache httpd 2.4，Basic 认证封锁中） |

⚠️ 注意：全站插件清单很短，这是刻意的。**不要安装清单之外的任何插件**（见第 13 章）。

## 1.2 网站结构（页面地图）

**核心页**

| 页面 | URL | 后台页面 ID |
|---|---|---|
| 首页 | / | 11 |
| About（关于我们） | /about/ | 14 |
| Quality & Compliance（质量） | /quality/ | 15 |
| Services（合作模式） | /services/ | 29 |
| Cooperation Models | /cooperation/ | 30 |
| Book a Factory Tour（工厂参观） | /factory-tour/ | 17 |
| Contact Us（联系） | /contact/ | 28 |
| Products（产品总览） | /products/ | 19 |
| FAQ | /faq/ | 76 |
| Blog | /blog/ | 31 |
| Feedback & Support（反馈） | /feedback/ | 97 |

**8 个剂型页**（模板生成，文字属固定结构）

| 剂型 | URL | ID |
|---|---|---|
| 软咀嚼 Soft Chews | /soft-chews/ | 20 |
| 片剂 Tablets | /tablets/ | 21 |
| 粉剂 Powders | /powders/ | 22 |
| 膏剂 Pastes | /pastes/ | 23 |
| 滴剂 Drops | /drops/ | 24 |
| 液体 Liquids | /liquids/ | 25 |
| 鱼油 Fish Oil | /fish-oil/ | 26 |
| 洁齿 Dental Chews | /dental-chews/ | 27 |

**Services 子页**：/oem/（217）、/odm/（218）、/contract-manufacturing/（219）、/private-label/（220）

**产品详情页**：21 条产品档案（Formulas），如 /formulas/joint-support-soft-chews/，完整清单见第 5 章。

**法务页**：/privacy-policy/（3）、/terms/（38）、/cookie-policy/（37）

## 1.3 后台入口

- 网址：`https://dev.zxpet.com/wp-admin`（上线后为正式域名/wp-admin）
- 打开先弹浏览器"登录提示"框（Basic 认证）——账号密码由管理员统一发放，**不是** WordPress 密码。输错或直接点掉弹窗只会看到 401 页面，不是网站坏了。
- 之后进入 WordPress 登录页，输入 WordPress 账号密码。

## 1.4 角色权限说明

| 角色 | 能做什么 | 不能做什么 |
|---|---|---|
| 管理员（Administrator） | 一切：内容、插件、主题设置、Site Settings 全部子页、用户管理 | —— |
| 编辑（Editor） | 发布/编辑所有页面与文章、编辑 Formulas 产品档案、管理评论、上传媒体 | 打不开 Site Settings／Social Links／Shape Library 等（需管理员） |
| 作者（Author） | 发布/编辑**自己的**文章、上传媒体 | 编辑别人的内容、Formulas、页面 |

⚠️ 注意：Site Settings 一族（联系信息、工厂信息、剂型事实、Form Options、Shape/Container 图库、Global FAQ）只对管理员可见，编辑人员看到菜单里没有属正常。

---

# 第 2 章 后台基础操作

## 2.1 登录后台

1. 浏览器打开 `https://dev.zxpet.com/wp-admin`
2. 弹出"登录提示"框 → 输入 Basic 账号密码（管理员发放，勾选"记住密码"）
3. 出现 WordPress 登录页 → 输入 WordPress 账号密码 → 进入仪表盘

**忘记密码**

- WordPress 密码：登录页点 **Lost your password?** → 输入注册邮箱（@zxpet.com）→ 收重置邮件。收不到邮件时找管理员用后台"用户→编辑→设置新密码"手动重置。
- Basic 认证密码：只能找管理员重发。
- 忘记用户名：找管理员在"用户"菜单查看。

## 2.2 左侧菜单导航（每一项是干什么的）

| 菜单项 | 作用 |
|---|---|
| Dashboard | 仪表盘首页 |
| Posts | 博客文章（/blog/ 的内容） |
| Media（媒体库） | 全站图片/视频统一管理 |
| Pages（页面） | 首页、About、Quality 等所有页面 |
| **Formulas** | 产品档案（21 条产品详情页的数据全在这） |
| Formulas → Dosage Forms / Functions | 产品分类/功能词表（一般不动，改动找技术） |
| **Site Settings** | 站点设置总入口（联系信息、版权、信任指标等，见第 9 章） |
| Site Settings 子页：Container Library / Shape Library / Global FAQ / Factory Information / Dosage Form Facts / Form Options | 见 9.2 |
| **Social Links** | 页脚社交图标链接 |
| **Forms**（Fluent Forms） | 全部 5 个表单的管理与提交记录 |
| TranslatePress | 语言设置与翻译界面 |
| WP Statistics | 访问统计（受 Cookie 同意门控） |
| WP Mail Log | 全站发信记录（排查"客户没收到邮件"用） |
| Comments | 评论管理（本站基本不用） |
| Appearance（外观） | 编辑人员**不要进**（含主题文件编辑器，见第 13 章） |
| Plugins / Users / Tools / Settings | 仅管理员；编辑人员忽略 |

## 2.3 预览、保存、发布、撤回

页面/文章编辑器右上角按钮：

- **Save draft**（保存草稿）：只存后台，前台看不到。
- **Preview**（预览）：在新标签打开草稿效果，只有登录用户能看。
- **Publish / Update**（发布/更新）：点一次前台立即生效。
- **Switch to draft**（转为草稿）：把已发布内容撤回前台（页面下树状态栏里）。

⚠️ 注意：改完没点 Update 就离开，改动会丢。养成"改→Save draft→Preview→Update"三步习惯。

## 2.4 上传图片与媒体库

1. 编辑器内点 **＋** → 选 **Image** 块 → **Upload**（上传）或 **Media Library**（从库中选）。
2. 也可直接把图片文件拖进编辑器。
3. 上传时右侧填 **Alt text**（图片替代文字）：一句描述图片内容的英文（前台是英文站）。
4. 媒体库独立入口：Media → Add New / Library。支持搜索、按月份筛选。

图片规范：产品图尽量 1:1、≥800×800px、白色/透明底；Shape/Container 小图见 5.8。

## 2.5 常见误操作与恢复

| 误操作 | 恢复办法 |
|---|---|
| 改错文字已发布 | 再进编辑器改回→Update。WordPress 不存"每个历史版本"（本站未启用版本修订），改前复制一段旧文字到别处最保险 |
| 误删页面/文章 | Pages/Posts 列表上方筛选 **Trash**（回收站）→ 悬停 → **Restore**。回收站 30 天后自动清空 |
| 误删图片 | Media 库没有回收站，**删除图片前必须确认无页面在用**；删了只能重新上传 |
| 页面整个改乱 | 立即停手联系技术支持（dev 环境有代码层备份与存档机制，可整页还原） |

---

# 第 3 章 内容编辑总则（核心原则）

## 3.1 一句话原则

> **内容可编辑，结构固定。**

文字、图片、参数值、配置器选项 → **你的地盘**，随便改。
布局、模块顺序、区块框架、代码 → **不要碰**。

## 3.2 可编辑内容清单（编辑人员负责）

1. About / Quality / Services / Factory Tour / 首页公司段的**正文**（进页面编辑器直接改）
2. Formulas 产品档案的全部字段（第 5 章逐项说明）
3. Site Settings 的文字项（联系方式、版权、信任指标、Form Options、Global FAQ、工厂信息、剂型事实）
4. 博客文章
5. 媒体库图片（替换/上传）
6. Form Options 三个下拉的选项文字（Country / Target Market / Dosage Form）

## 3.3 不可编辑内容清单（固定结构）

1. 页面头部导航、页脚（社交图标链接除外——Social Links 可改）
2. 页面模块的排列顺序与区块框架（如"价格区永远在简介下""参数表永远两栏"）
3. 首页除公司段外的所有区块文字
4. 8 个剂型页的模板文字
5. JSON-LD 结构化数据（系统自动生成）
6. 任何 PHP / CSS / JS / 模板文件

## 3.4 为什么结构不能改

模板是"骨架"，内容是"肉"。骨架上挂着样式、图片匹配、JSON-LD 数据、多语言收词、配置器渲染等一整套机制——**改一个区块顺序，可能导致整页样式崩掉或搜索引擎数据错乱**，而且这种损坏往往不报错、过几天才被发现。

## 3.5 改内容前必读（四步）

1. **复制原文**：把要改的段落先复制到备忘录——改坏了能贴回来。
2. **先预览**：Save draft → Preview，确认没问题再 Update。
3. **逐字核对**：外贸站所有前台文字是英文，改完通读一遍拼写与语法；不要中英混排进前台。
4. **一处一改**：一次改一个地方，别一口气大改。出问题好定位。

---

# 第 4 章 各页面编辑指南

> 通用入口：后台 **Pages → 找到页面 → Edit**。
> "模板固定"＝该部分在页面编辑器里看不到、属主题结构，改文字找技术支持。

## 4.1 首页（ID 11）

- **组成**：Hero 区 → 询盘表单 → 信任指标条 → 产品卡片区 → 剂型网格 → 认证区 → **公司介绍段** → 页脚。
- **可编辑**：
  - **公司介绍段全部文字**（标题、副题、四条 ✓、按钮文字）——后台 Pages → Home → 正文就是这一段（H12 起正文已迁入页面编辑器）。
- **固定结构**：Hero、表单、产品卡、剂型网格、认证区（其中信任指标数字来自 Site Settings，见 9.2）。
- **编辑示例**：把公司段标题 "A GMP-standard partner..." 改成新定位语 → Pages → Home → 在编辑器里定位标题 → 改字 → Save draft → 预览 → Update。
- **注意**：公司段里现有两处合法中文（公司地址），**不是错误**，不要"顺手改掉"。

## 4.2 About（ID 14）/ Quality（15）/ Services（29）/ Factory Tour（17）

- **组成**：页面头图（模板）＋ **正文区**（可编辑）＋ 页脚。
- **可编辑**：正文区所有文字、图片——Pages → About → 整页正文即所见内容。
- **固定结构**：面包屑导航、FAQ/结构化数据（自动生成）、页脚。
- **注意**：正文是"空则整页只剩头尾骨架"——**不要全选删除**；删段落时保留一小段或先在草稿确认。

## 4.3 Services 子页：OEM / ODM / Contract Manufacturing / Private Label

- 与 4.2 同理：Pages → 对应页 → 正文可编辑；头部与布局固定。
- 卡片入口链接在 Services 页正文中，改动链接文字即可，URL 不要动。

## 4.4 8 个剂型页（Soft Chews 等）

- **可编辑**：几乎没有——页面由模板生成（模块顺序、文案、图集布局全固定）。
- **需要改剂型页文字/图片时**：提需求给技术支持（改模板属开发动作，会走批次流程）。
- 图片更新：部分区块图片可在媒体库按文件名替换（同名覆盖），不确定就先问技术。

## 4.5 Contact（ID 28）

- **组成**：页面头＋联系信息（来自 Site Settings）＋ **Get a Quote 表单**（Fluent Forms #8）。
- **可编辑**：正文区文字；表单字段见第 8 章。
- 联系方式统一在 Site Settings 改（见 9.2），**不要**在页面正文里另写一份。

## 4.6 Blog（ID 31）与文章

- 发文：Posts → Add New → 写标题/正文 → 分类与标签 → 设置特色图片 → Publish。
- Blog 列表页的筛选 chips（All/Manufacturing/Private Label/Case Studies/Formulation）为固定结构，新增分类前先与技术确认。

## 4.7 FAQ（ID 76）与 Global FAQ

- 页面正文可编辑；全站 FAQ 数据在 **Site Settings → Global FAQ**（见 9.2），产品 FAQ 在每条 Formulas 里。

## 4.8 法务页（Privacy / Terms / Cookie Policy）

- 正文可编辑，但**改前必须告知技术支持**——这些页与合规机制（Cookie 横幅、同意门控）的表述互相咬合，改错一句话会造成合规描述与实际行为不符。

---

# 第 5 章 产品详情页编辑详解（重点章节）

## 5.0 产品档案是什么

- 后台入口：**Formulas → Add New / 列表点产品名**。
- 前台地址：`/formulas/产品slug/`（如 /formulas/joint-support-soft-chews/）。
- 当前共 **21 条**产品档案，覆盖 8 个剂型。
- 每条档案由若干"字段盒子"组成，按分组排列：**Basics → Media → 参数区(params) → 包装(packaging) → 正文(detail) → Spec Sheet(specsheet) → FAQ(faq)**，外加一个 **Configurator Display** 盒。
- 每个输入框下方都有**中文灰色提示**，说明这个字段是干什么的、留空会怎样——**先读提示再填**。

⚠️ 注意：**留空＝前台不显示该区块**（empty-means-absent）。所以"删掉一个区块"的正确做法就是清空对应字段并保存，而不是到前台找按钮。

## 5.1 字段分组与完整清单

### Basics 组

| 字段（后台标签） | 填什么 | 留空会怎样 |
|---|---|---|
| Introduction | 产品简介（详情页 Overview 段，标题下短文字） | 自动生成一句模板文案 |

### Media 组

| 字段 | 填什么 | 留空会怎样 |
|---|---|---|
| Gallery images | 图集（点选多张图） | 不显示图集 |
| YouTube URL | YouTube 视频链接 | 不显示视频 |
| Card badge | 卡片角标：Best Seller（金）/ Hot（红）/ New（蓝）/ None | 不显示角标 |

主图不在 Media 组——用编辑器右侧 **Featured image（特色图片）** 面板设置。

### 参数区（params）——详情页价格与配置器数据源

| 字段 | 填什么 | 留空/隐藏规则 |
|---|---|---|
| Flavors | 勾选口味（多选） | 客户前端单选 |
| Unit Weight | 勾选克重（仅软咀嚼/片剂/洁齿显示此字段） | 其它剂型该字段整个隐藏 |
| Counts | 勾选粒数（仅软咀嚼/片剂/洁齿） | 同上 |
| Net Content | 勾选净含量（所有剂型） | 必看：粒数信息写进净含量文字，鱼油如 "60 softgels (60g) per bottle" |
| Shape | 勾选形状/质地/外观 | 前端客户单选 |
| Function | 勾选功能宣称（所有剂型） | 客户单选，可 Custom |
| Colors | 勾选颜色（仅软咀嚼/片剂/洁齿/膏剂/粉剂有颜色池） | 鱼油/滴剂/液体无此字段，整组不显示 |
| Suitable for | 勾选 Dog / Cat | 两项都勾时前台额外出现 "Dog and Cat" |
| Life stage | 勾选生命周期 | 客户单选 |
| Container Type | 勾选包装形式 | 客户单选 |
| Tier pricing | 阶梯价表格（qty / price 两列，可多行） | **最高一档 Max 留空**，前台自动显示 "1,000 and up" |
| Sample price (USD) | 样品价，如 50 | 不显示 Get Sample 一行 |

### 包装组（packaging）

| 字段 | 说明 |
|---|---|
| Extra packaging | 额外包装选项，多选 |
| Carton dimensions | 装箱表：Pack count / Units per carton / Carton size (cm)，留空行不显示 |

### 正文组（detail）——每行一条，留空区块隐藏

| 字段 | 前台位置 |
|---|---|
| Ingredients | Formula & nutrition 区，pills 展示 |
| Guaranteed Analysis | term/value 网格；无含量的行不显示 |
| Standard Specs | 规格表 |
| Recommended For | 推荐场景 |
| Use Cases | 用例 |
| Who It's For | 适合谁 |

### Spec Sheet 组（H10 规格页四行）

| 字段 | 说明 |
|---|---|
| Sample Policy | 如 "Samples available, freight collect" |
| Customizable | 如 "Yes — formula, flavor, shape, color and packaging" |
| Private Label | 如 "Available" |
| Payment Terms | 如 "T/T 30% deposit, balance before shipment"。**勿编造，留空不显示** |

### FAQ 组

| 字段 | 说明 |
|---|---|
| Lead time | 交期，如 "30-35 days"，显示在详情页 meta 与 FAQ |
| Product FAQ | 问题已预填，**填答案即可**；全站 Global FAQ 自动追加在后 |

## 5.2 参数区怎么改（MOQ、交期、认证、产地、OEM）

详情页参数条（facts-mini）的这几项**不在产品档案里**，是**按剂型**统一配置的：

- 后台路径：**Site Settings → Dosage Form Facts**
- 内容：每个剂型一行四项——**MOQ**（如 from 500–1,000 units）、**Lead**（交期默认）、**Certs**（认证）、**Packaging**
- 改一处，**该剂型所有产品**的参数条同步更新。

⚠️ 注意：MOQ 改小/改大会直接影响客户预期，改动前和销售确认；产品档案里的 Tier pricing 数量档要能和 MOQ 对得上（首档数量＝最小起订量）。

## 5.3 配置器十组怎么改（后台多选 → 前端单选）

- **后台**：每个组是复选框（multi），勾选该产品支持的选项，可多勾。
- **前端**：客户在配置器里每组**只能单选一个**。
- 前台渲染顺序固定：Shape → Color → Flavor → Unit Weight → Counts → Net Content → Container → Function → Suitable For → Life Stage（价格区在最前）。
- 勾选的选项就是前台全部可选项——**少勾一个，客户就少一个选择**。

## 5.4 中文提示怎么看

每个字段输入框下方的灰色中文文字就是给编辑人员的操作说明（由主题内置）。改版后以实际页面提示为准；本手册第 6 章逐组附了提示要点。

## 5.5 组名覆盖怎么用（Configurator Display 盒）

- 位置：产品编辑页底部 **Configurator Display** 盒。
- 作用：只改**这一条产品**的组名/选项文字，不动全站词表。
- 三种覆盖，每种留空＝用默认：
  1. **Show/Hide 开关**：整组显示/隐藏（如该产品不做 Color，把 Color 组关掉）。
  2. **组名（Label）**：如把 "Shape" 改成 "Texture"。改一处，前后台同步。
  3. **选项文字（Options）**：每行一个；**覆盖后即为该组全部选项**（不是追加）。
- 保存逻辑：全部存进产品的 groups_config，属产品级数据，安全可逆——清空覆盖即回到全站默认。

## 5.6 选项文字怎么改（影响面提醒）

- 想改**全站词表**（如口味池加 "Duck"）→ 找技术支持（改代码级词表，走批次）。
- 只想改**某条产品**的显示文字 → 用 5.5 的选项覆盖。
- ⚠️ 注意：**改文字≠改数据**。已经收到的询盘/样品记录里存的是当时的选项文字，改词不会回溯旧记录，导出统计时注意口径。

## 5.7 正文怎么改（规格、配方、推荐场景、包装）

- Ingredients / Guaranteed Analysis / Standard Specs / Recommended For / Use Cases / Who It's For：均为"**每行一条**"的文本域。
- Guaranteed Analysis 格式：`成分: 含量`（冒号分隔），无含量的行会被自动隐藏。
- Standard Specs 格式：`标签: 值`。
- 改完预览详情页确认行数与显示正常。

## 5.8 图片怎么上传

- **产品主图**：编辑器右侧 Featured image。建议 1:1、≥800×800。
- **图集**：Media 组 Gallery images。
- **Shape 小图**：Site Settings → **Shape Library**（形状 Bone/Round/…，每行可挂一张 attachment 图；400×400 透明 PNG 最佳）。
- **Container 小图**：Site Settings → **Container Library**（Round/Square/Oval/Jar/Pouch/Tube/Custom）。
- ⚠️ 图库当前**是空的**（0 张图）：客户看到的形状/包装选择框会显示虚线占位框（dashed slot），不是故障。传图后前台自动换成真图，**无需改任何配置**。
- **证书图**：与 COA 下载机制联动，由技术管理；需要更新证书时联系技术支持。

## 5.9 标签合规信息怎么填

- Guaranteed Analysis 是美国饲料管理协会（AAFCO）式的保证分析值，**数值必须来自配方/检测报告，禁止估算**。
- Shelf life 固定四选一（下拉），不要自填。
- Payment Terms 必须是公司真实政策。
- 所有合规文案改动建议销售/质量部门过目后再发布。

---

# 第 6 章 配置器十组详解

> 通用规则：后台勾选（多选）＝供货能力；前端单选＝客户选购；**Show/Hide 开关**在该产品的 Configurator Display 盒里；**Custom** 出现时机＝词表里含 "Custom" 选项且被勾选（客户可自填文字）。species / stage 两组**没有** Custom。

## 6.1 Shape（形状/质地/外观）
- 干什么：产品的物理形态（Bone、Round、Heart…；膏剂叫 Texture，粉剂叫 Appearance）。
- 前端单选；组名按剂型有默认（Shape / Texture / Appearance / Form）。
- 注意：选项覆盖后即为全部选项；小图在 Shape Library（当前空库显示占位框）。

## 6.2 Color（颜色）
- 干什么：产品颜色（Brown、Beige…）。
- **只有 5 个剂型有颜色池**：软咀嚼/片剂/洁齿/膏剂/粉剂。鱼油/滴剂/液体整组隐藏——看不到属正常。
- Custom 可自填。

## 6.3 Flavor（口味）
- 干什么：口味（按剂型池不同：软咀嚼池最大含 Peanut Butter/Blueberry 等）。
- 组名默认按剂型 Flavor / Source（鱼油类"口味"实为来源）。
- Custom 可自填。

## 6.4 Unit Weight（单件克重）
- 干什么：单粒/单片克重（如 2g）。
- **仅软咀嚼/片剂/洁齿显示**，其它剂型整组隐藏。
- 组名默认 Weight per Piece / Weight per Tablet。Custom 可自填。

## 6.5 Counts（粒数）
- 干什么：每瓶/每包粒数（如 60）。
- **仅软咀嚼/片剂/洁齿显示**。组名默认 Count per Bottle / Count per Pack。Custom 可自填。

## 6.6 Net Content（净含量）
- 干什么：整瓶/整包净含量（如 120g per bottle）。**所有剂型显示**。
- 粒数信息写进净含量文字（鱼油：60 softgels (60g) per bottle）。

## 6.7 Container Type（包装形式）
- 干什么：客户选包装（Round、Jar、Pouch、Tube、Custom…）。
- 选项覆盖后即为全部选项；覆盖列表里写什么前台就显示什么。
- 小图在 Container Library。

## 6.8 Function（功能）
- 干什么：功能宣称（Hip & Joint、Skin & Coat、Digestive Health、Immune Support、Calming、Dental Care、Urinary Health、Multivitamin、Heart Health、Eye Health）。**所有剂型显示**。
- 全站词表在 Functions（Formulas 菜单下），改动找技术。Custom 可自填。

## 6.9 Suitable For（适用宠物）
- 干什么：Dog / Cat。后台两项都勾 → 前台额外出现 "Dog and Cat"。
- **无 Custom**。

## 6.10 Life Stage（生命周期）
- 干什么：Puppy / Kitten / Adult / Senior / All Life Stages。可后台多选、前端单选。
- **无 Custom**。

---

# 第 7 章 多语言管理

## 7.1 当前语言状态

- **English 已发布**（默认语言，URL 无前缀）。
- **中文（zh_CN）已撤下**：不在发布语言里，语言切换器关闭。/zh/* 链接会 301 回英文页——这是预期行为，不是故障。

## 7.2 如何翻译内容

TranslatePress 界面：后台顶栏 **Translate Page**（打开任一前台页面时）→ 左右分屏，点句子逐句翻译。**当前中文译文库为空**——重新启用中文前需要先补译文。

## 7.3 重新启用中文的三步清单（缺一不可）

1. **TranslatePress → Settings → 把 zh_CN 加回发布语言（publish-languages）**，保存后**刷新重进确认没有弹回**（系统有互为子集重置的修补逻辑）。
2. **打开语言切换器**：Settings 里 floater（浮动切换按钮）enabled 改回 true。
3. **登出状态验证**：用无痕窗口（不登录）检查 hreflang 标签、切换器出现、/zh/ 页面正常——语言相关的显示对管理员和访客可能不一样，必须登出验证。

⚠️ 注意：第 1 步保存后必须回读确认；三步做完才算启用。主题的语言 301 规则是动态派生的，启用后自动生效，无需动代码。

## 7.4 语言切换器说明

- 形态：右下角浮动按钮（dark 样式，约 h55×w128）。
- 不显示 → 先查 7.3 第 2 步的 floater 开关。

---

# 第 8 章 表单与询盘管理

## 8.1 全站表单清单（Fluent Forms）

| Form ID | 名称 | 用在哪 |
|---|---|---|
| 8 | Get a Quote | 询盘/报价（首页、Contact） |
| 9 | Request a Sample | 样品申请 |
| 10 | Book a Factory Tour | 工厂参观预约 |
| 11 | Request COA | COA 证书索取 |
| 12 | Feedback | 反馈（/feedback/） |

## 8.2 提交后发到哪

- 所有表单通知统一发 **sales@zxpet.com**（全站已收敛，不再用 info@zxpet.com）。
- 公开对外展示邮箱是 info@zxpet.com，**表单通知不要改回 info@**。

## 8.3 查看提交记录

- 后台 **Forms → Submissions**（Fluent Forms）→ 按表单筛选，可查看每条提交的全部字段、时间、来源页。
- 导出：Submissions → Export（CSV）。

## 8.4 如何修改表单字段（编辑人员谨慎操作）

- 后台 Forms → 对应表单 → Edit：拖拽式编辑器，字段、必填、选项文字可改。
- ⚠️ 注意：
  - **不要删除/重命名字段的 name 属性**（field name），通知流和统计依赖它；
  - Country / Target Market / Dosage Form 三个下拉的**选项由 Site Settings → Form Options 统一供给**，表单里改无效，要去 Form Options 改（改一处三个表单同步）；
  - 确认消息（提交后给客户看的话术）只能用纯 HTML（系统会剥脚本），改前找技术确认。

## 8.5 如何修改通知收件人

- Forms → 对应表单 → Settings & Integrations → Email Notification → 收件人改为新邮箱 → Save。
- 改完自己提交一单测试。

## 8.6 反垃圾与安全机制（不用管，但要知情）

- 询盘/投票类端点按 **IP 限流**（同一 IP 短时间高频提交返回 429，客户看到"请稍后再试"）。
- IP 记录统一取 CF-Connecting-IP（CDN 真实 IP），封禁/统计按真实来源。
- Cookie 同意门控见第 11 章。

## 8.7 收不到邮件怎么办

1. 先查 **Forms → Submissions**：记录在＝表单正常，是发信问题；记录也不在＝提交失败（查限流/必填）。
2. 查 **WP Mail Log**：每封系统外发邮件都有记录与错误。
3. 常见原因：收件箱垃圾箱、sales@ 邮箱满、SMTP 波动。
4. 都正常但收不到 → 联系技术支持查服务器发信通道。

---

# 第 9 章 网站设置（Site Settings）

## 9.1 总入口

后台左侧 **Site Settings**（仅管理员）。主页面有以下字段：

| 设置项 | 影响 |
|---|---|
| Contact email / phone / WhatsApp / address | 顶栏、Contact 页、页脚、表单上下文 |
| Working hours | 顶栏/页脚营业时间 |
| Copyright company / suffix | 页脚版权行 |
| Trust 指标组（factory_size / cleanroom / capacity / ontime / reorder / response / export_markets） | 首页信任指标条数字与文案 |
| Certifications | 认证区展示 |

## 9.2 子页一览

| 子页 | 干什么 | 改动影响 |
|---|---|---|
| **Dosage Form Facts** | 每个剂型一行的 MOQ/Lead/Certs/Packaging | 该剂型**全部产品**详情页参数条 |
| **Form Options** | 三个共享下拉（Country / Target Market / Dosage Form）的选项 | 多个表单同步更新 |
| **Global FAQ** | 全站 FAQ 数据 | 详情页 FAQ 区自动追加、FAQ 页 |
| **Factory Information** | 工厂信息（OEM 能力、产地等） | 详情页参数条相关行与工厂区块 |
| **Shape Library** | 形状词表＋小图 | 配置器 Shape 组显示 |
| **Container Library** | 包装词表＋小图 | 配置器 Container 组显示 |
| **Social Links**（独立主菜单） | 页脚社交图标 URL | 页脚图标（留空/填 # 图标仍显示指向 #） |

⚠️ 注意：文本类设置**清空保存会回落到默认值**（系统设计如此），想"真的空着不显示"的场景先找技术确认。

---

# 第 10 章 日常维护

## 10.1 检查清单

**每日（销售/编辑，2 分钟）**
- 提交一单测试询盘确认 sales@ 收到（或查看昨日 Submissions 数是否正常）
- 首页与 Contact 打开无错乱

**每周（编辑）**
- Forms → Submissions 导出归档
- WP Mail Log 抽查失败邮件
- 媒体库：新增图片 Alt text 是否已填

**每月（技术/管理员）**
- 后台 站点健康（Tools → Site Health）查看状态
- WP Statistics 流量月报
- 插件"可用更新"只记录**不上点更新**（走 10.3 流程）
- 检查磁盘空间与备份完整性

## 10.2 如何备份

当前无自动备份插件，备份由**技术人员**按以下口径执行：

- **数据库**：`wp db export`（含全部内容/表单记录/设置）
- **文件**：主题目录（git 仓库已版本化，天然有历史）＋ `wp-content/uploads` 打包
- 建议节奏：**改版批次上线前**＋**每月一次**全量；备份文件留存服务器外。
- ⚠️ 编辑人员做大批量改动前，自己也能做"轻备份"：把要改的原文整段复制到备忘录（第 3.5 节）。

## 10.3 如何更新插件（重要）

- ⛔ **绝不**运行 `wp plugin update --all`，**绝不**在后台一键"全部更新"。
- 理由：历史事故——本站曾装过更新通道被第三方改写的插件（Gravity Forms/TP Business 假 key 事件，已清除），批量更新可能把不可信版本拉进来。
- 正确流程：出现可用更新 → 逐个评估（是否 WP.org 官方源、更新说明、与主题兼容）→ 单个更新 → 全站回归 → 记录版本号。此操作**仅技术人员执行**。

## 10.4 健康检查与日志

- Tools → **Site Health**：状态页看 Critical/Recommended。
- 前台健康端点：技术侧有 /health 类检查（编辑人员无需操作）。
- 日志位置（服务器，技术人员查看）：
  - PHP 错误日志（debug.log / php-fpm error log）
  - WP Mail Log（后台可视化）
  - 访问日志（服务器层）

## 10.5 性能监控

- WP Statistics 看流量趋势；Cloudflare 面板看边缘缓存与安全事件。
- 明显变慢的排查顺序：是否新传了超大图 → 是否新装/更新了插件 → 联系技术查服务器负载。

---

# 第 11 章 安全与合规

## 11.1 Cookie 同意机制

- 站点是 **opt-in（先同意后统计）** 模式：访客未点 Accept 前，WP Statistics **一个字节都不收集**；点 Accept 后立即生效、无需刷新。
- Cloudflare Web Analytics 无 Cookie、不需要同意，始终运行。
- Cookie 横幅与撤回入口为自研，行为与 /cookie-policy/ 页描述一致。

## 11.2 隐私政策 / Cookie 政策在哪改

- 页面：/privacy-policy/（ID 3）、/cookie-policy/（37）、/terms/（38）。
- ⚠️ 改前必须告知技术支持：政策表述与横幅/统计实际行为互相咬合（哪些工具要不要同意、哪些无需同意），改错一句就是"政策说 A 系统做 B"的合规事故。

## 11.3 分析工具现状

| 工具 | Cookie | 需要同意 | 备注 |
|---|---|---|---|
| Cloudflare Web Analytics | 无 | 否 | 边缘注入，始终运行 |
| WP Statistics | 有 | **是**（opt-in） | 由 mu-plugin 桥接同意 API |

## 11.4 安全注意事项

- **不要改任何主题代码文件**（Appearance → Theme File Editor 同样不要进）。
- **不要安装来路不明的插件**（第 13 章）。
- 后台账号不共用；人员离职当天停用账号。
- 密码不要发微信群，用密码管理或私密渠道。

## 11.5 发现异常怎么办

- 前台出现不明弹窗/跳转/垃圾链接、后台出现陌生用户、表单激增垃圾 → **立即截图** → 联系技术支持 → 技术侧执行排查（日志、文件校验、数据库比对）。
- 不要自行删除"看起来可疑"的文件或用户。

---

# 第 12 章 常见问题 FAQ

> 格式：问题 → 原因 → 解决

**Q：改了内容前台没变？**
原因：① 没点 Update；② 浏览器/CDN 缓存；③ 改的是草稿。
解决：确认已 Update → 强制刷新（Cmd/Ctrl+Shift+R）→ 无痕窗口再试 → 仍不行联系技术（查服务器端缓存）。

**Q：图片上传失败？**
原因：文件过大（>几 MB）或格式不支持。
解决：压缩到 2MB 内再传；推荐 jpg/png/webp；产品主图 1:1。

**Q：表单收不到邮件？**
见 8.7 三步排查（Submissions → WP Mail Log → 技术支持）。

**Q：页面显示错乱？**
原因：编辑器里误删了结构区块，或粘贴了带样式的 Word 内容。
解决：撤销最近改动（改前复制过原文即可贴回）；Word 内容先粘到纯文本再进编辑器；恢复不了联系技术（dev 有整页存档可还原）。

**Q：后台打不开（一直弹登录框）？**
原因：Basic 认证凭据错误/过期。
解决：找管理员重发凭据；浏览器清除该站点凭据后重输。

**Q：忘记 WordPress 密码？**
见 2.1（自助重置邮件或管理员手动重置）。

**Q：误删了内容怎么恢复？**
Pages/Posts 回收站 30 天内可 Restore（2.5 节）；媒体库无回收站；整页损坏联系技术用存档还原。

**Q：语言切换器不见了？**
中文撤下时切换器随 floater 一起关闭，属预期。重新启用走 7.3 三步。

**Q：配置器选项不对/少了一组？**
先查三层：① 该组字段是否勾了选项（Formulas 产品档案）；② Configurator Display 是否把它 Hide 了；③ 该剂型本来就没有这组（如鱼油无 Color）。都在但不对 → 联系技术。

**Q：详情页某个区块消失了？**
empty-means-absent：对应字段被清空了。进产品档案把字段填回即可。

**Q：前台出现中文？**
仅公司地址两处为合法中文；其它位置出现中文＝误贴，进编辑器删除。

**Q：客户说提交后看到"请稍后再试"？**
IP 限流触发（短时间多次提交）。等几分钟再试；属正常防护。

**Q：Shape/Container 选项只有虚线框没有图？**
图库未传图（当前 0 张），传图后自动显示（5.8）。

---

# 第 13 章 重要禁令（红线）

1. ⛔ **不要改主题代码文件**（PHP/CSS/JS/模板）。改结构必须走技术支持的批次流程（改动会过自动化门禁验证）。
2. ⛔ **不要安装来路不明的插件**。历史教训：本站曾被"破解版"插件写入假 license key，其更新通道被第三方控制。新插件需求先找技术评估。
3. ⛔ **不要在 dev 跑插件批量更新**（`wp plugin update --all` 或后台一键全更）。逐个评估＋回归（10.3）。
4. ⛔ **不要删模板守卫/封锁机制**（dev 锁定、preflight、同意桥接 mu-plugin）——它们在保护站点，删了同意门控与部署安全立即失效。
5. ⛔ **不要直接改数据库**（phpMyAdmin/SQL 手写）。一切数据改动走后台界面或技术支持。
6. ⛔ **不要删除 SEO/JSON-LD 相关标记**（页面里看不到的部分是自动生成的）。
7. ⚠️ **改内容前先备份**（原文复制；大改动先知会技术做库备份）。

---

# 第 14 章 应急处理

## 14.1 网站打不开

1. 先确认范围：只有自己打不开（换网络/无痕试）还是全站打不开（手机流量试）。
2. 全站打不开：截图错误页 → 联系技术支持 → 技术查服务器状态（cloud/VPS 控制台、进程、日志）。
3. 只有 /wp-admin 打不开但前台正常：多半是 Basic 认证问题（12 章）。

## 14.2 被攻击 / 被挂马

1. **立即通知技术支持**，保留现场，不要自行删除文件。
2. 技术侧流程：隔离 → 日志取证 → 文件完整性校验（WP 核心与主题 checksum）→ 清除 → 修复入口（弱密码/漏洞插件）→ 全量改密。
3. 恢复后：核对内容（SEO 垃圾链接）、重新提交搜索引擎复审。

## 14.3 数据丢失恢复

- 内容误删：后台回收站（12 章）。
- 整库/整页损坏：技术人员用最近一次数据库备份＋主题 git 历史还原；表单提交记录随库一起回滚（会丢失备份点之后的新提交，需与销售核对补录）。

## 14.4 联系谁

| 事项 | 联系人 | 占位（请补充） |
|---|---|---|
| 网站技术一切问题 | 网站开发者（Sam） | ☎ __________ / 微信 ________ |
| 服务器/域名/云资源 | 主机服务商控制台 | 技术持有，勿动 |
| 表单业务口径（MOQ/价格） | 销售负责人 | __________ |

---

# 第 15 章 附录

## 15.1 术语表

| 术语 | 解释 |
|---|---|
| WordPress / WP | 建站系统本体 |
| 后台 / wp-admin | 管理界面，域名后加 /wp-admin |
| 区块编辑器（Block Editor） | 页面/文章的"积木式"编辑器，每个段落、图片、标题都是一个"块" |
| 页面 vs 文章 | Page（页面，如 About）与 Post（文章，博客用）是两种内容 |
| 特色图片（Featured image） | 产品/文章的"主图"，编辑器右侧面板设置 |
| meta / 自定义字段 | 附在一条内容上的结构化数据（如产品的阶梯价、口味清单） |
| 短代码（shortcode） | 形如 `[xxx]` 的占位标签，页面里放一个就能渲染一整块功能 |
| CPT（自定义文章类型） | Formulas（产品档案）就是站点自定义的内容类型 |
| Fluent Forms | 表单插件，全站 5 个表单都归它管 |
| TranslatePress | 前台逐句翻译的多语言插件 |
| mu-plugin | "必用插件"，随系统强制加载，只有技术能改（同意桥接等在此） |
| Basic 认证 | 打开网站前弹的浏览器级密码框（dev 环境封锁用） |
| opt-in | 访客先点"同意"，统计才开始收集的模式 |
| 301 跳转 | 永久重定向（中文页撤下后 /zh/ 自动跳回英文页） |
| JSON-LD | 给搜索引擎看的结构化数据，系统自动生成，勿动 |

## 15.2 后台菜单速查表

| 我要… | 去哪 |
|---|---|
| 改 About/Quality/Services/Factory Tour 正文 | Pages |
| 改首页公司段 | Pages → Home |
| 改产品参数/配置器/价格 | Formulas → 产品 |
| 改 MOQ/交期/认证（按剂型） | Site Settings → Dosage Form Facts |
| 改表单下拉选项（国家/市场/剂型） | Site Settings → Form Options |
| 改全站 FAQ | Site Settings → Global FAQ |
| 改工厂信息 | Site Settings → Factory Information |
| 传形状/包装小图 | Site Settings → Shape Library / Container Library |
| 改联系方式/版权/信任指标 | Site Settings 主页 |
| 改页脚社交图标 | Social Links |
| 查询盘提交 | Forms → Submissions |
| 查发信记录 | WP Mail Log |
| 看流量 | WP Statistics |
| 翻译 | 前台顶栏 Translate Page |

## 15.3 常用操作快捷键

| 场景 | 快捷键 |
|---|---|
| 强制刷新（看最新前台） | Cmd/Ctrl + Shift + R |
| 编辑器保存草稿 | Cmd/Ctrl + S（区块编辑器内） |
| 无痕窗口 | Cmd/Ctrl + Shift + N（Chrome） |

## 15.4 版本历史（主题 2.10.x，节选）

| 版本 | 内容 |
|---|---|
| 2.10.45 | 剂型页活性成分区（[sf_formula_actives]） |
| 2.10.52 | 装箱/包装格式行、详情页两栏改造 |
| 2.10.54 | 详情页媒体区、参数明细 |
| 2.10.68 | Shape 组缩略图＋预览层、页脚改造 |
| 2.10.72–2.10.76 | 导航/卡片/认证区/Services 子页系列改造 |
| 2.10.78–2.10.79 | 切换器避让、移动端底栏修复 |
| 2.10.82 | 配置器十组模型（H9） |
| 2.10.84 | 规格表三组变两组（H10b） |
| 2.10.85 | Form Options 单一可编辑源（H9b）；GF 全退役 |
| 2.10.86 | 表单 label 修复；四公司页＋首页公司段正文可编辑化（H12）；Color/Function 入十组；后台 31 字段中文提示 |

---

*手册结束。发现手册与实际不符时，请以站点实际为准并告知技术支持修订。*

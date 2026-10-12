# 中鲜宠食官网 · 日常操作速查卡

> 配套文档：docs/ops-manual-v1.md（v1.0.0 完整手册）｜适用主题版本 **2.10.90** ｜截至 2026-10-08

## 🔑 登录

**正式**：`https://www.zxpet.com/sf-linyi/`　｜　**dev（内测）**：`https://dev.zxpet.com/sf-linyi/`（先过 Basic 弹窗）

- `/wp-admin`、`/wp-login.php` 已停用（返回 404 页面）——**不是故障**，是登录加固。
- 忘记密码：登录页 **Lost your password?** → 5 分钟内最多点 **2 次**（超限锁 30 分钟）；没收到先查垃圾箱 → 隔 5 分钟再试 → 仍不行找管理员手动重置。
- 两步验证（2FA）：**当前未启用**（2026-10-08 实测），启用后另行通知。
- ⚠️ 登录地址与用户名属内部资料：不外传、不截图发群。

## ✍️ 高频编辑去哪点

| 我要改… | 路径 |
|---|---|
| About / Quality / Services / Factory Tour 正文 | **Pages** → 对应页 → 改正文 → Save draft → Preview → **Update** |
| 首页公司段 | **Pages** → Home |
| 产品参数/价格/配置器 | **Formulas** → 产品 → 对应字段盒（每个框下有中文提示） |
| MOQ / 交期 / 认证（按剂型） | **Site Settings → Dosage Form Facts** |
| 表单下拉选项（Country / Target Market / Dosage Form） | **Site Settings → Form Options**（三个表单同步） |
| 全站 FAQ | **Site Settings → Global FAQ** |
| 工厂信息 | **Site Settings → Factory Information** |
| 联系方式 / 版权 / 信任指标 | **Site Settings** 主页 |
| 页脚社交图标 | **Social Links** |
| 发博客 | **Posts → Add New** |

## 📨 询盘三步查

1. **Forms → Submissions**：记录在吗？（在＝提交成功）
2. **FluentSMTP → Email Logs**：信发出去了吗？
3. 都正常没收到 → 垃圾箱 → 找技术查发信通道。通知统一发 **sales@zxpet.com**。

## 🖼 图片规则

- 主图＝编辑器右侧 **Featured image**（1:1、≥800px；**占 1 个照片位**）
- 图集＝Media 组 **Gallery images**（多选＝**整体替换**，注意重新全选）
- 形状/包装小图＝**Shape Library / Container Library**（虚线框＝库空，传图即自动显示）
- 每张图填英文 **Alt text**

## ⚠️ 三条最容易踩的坑

1. **留空＝前台不显示**（区块消失先查字段是不是被清了）
2. **改完必须点 Update**，预览要用 Save draft → Preview
3. 前台**只允许英文**（唯一例外：公司地址两处中文是合法的）

## 🛑 红线（碰到就停手找技术）

- 不改主题代码 / 不进 Appearance→Theme File Editor / **不在 Site Editor 保存模板**
- 不装新插件 / 不跑插件批量更新 / 不对外透露登录地址
- 不直接改数据库
- 改内容前先备份（UpdraftPlus 装好后：改前点一次"立即备份"）；大改动知会技术

## 🆘 出事了

| 症状 | 动作 |
|---|---|
| 改了前台没变 | 强刷 Cmd+Shift+R → 无痕窗口 → 找技术 |
| 打开后台是 404 页面 | 正常现象，改用 `/sf-linyi/` |
| 页面错乱 | 撤销最近改动 → 贴回备份原文 → 找技术还原 |
| 全站打不开 | 截图 → 立即联系技术 |
| 可疑内容/陌生用户 | 截图保留现场 → 找技术，不要自己删 |

**应急联系人（待补充）：技术 ______ ｜ 主机商控制台：技术持有 ｜ 销售负责人 ______**

> 🔑 **用户名**：2026-10-06 起已由默认可猜名改为自定义用户名（向专职维护索取；与密码同等级保守）。

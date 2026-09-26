# 中鲜宠食官网 · 日常操作速查卡

> 配套文档：docs/ops-manual.md（完整手册）｜适用主题版本 2.10.86

## 🔑 登录

`dev.zxpet.com/wp-admin` → 先过 Basic 弹窗（管理员发放）→ 再输 WP 账号密码。
忘记密码：登录页 **Lost your password?**，收不到找管理员手动重置。

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
2. **WP Mail Log**：信发出去了吗？
3. 都正常没收到 → 垃圾箱 → 找技术查发信通道。
   通知统一发 **sales@zxpet.com**。

## 🖼 图片规则

- 主图＝编辑器右侧 **Featured image**（1:1、≥800px）
- 图集＝Media 组 **Gallery images**
- 形状/包装小图＝**Shape Library / Container Library**（虚线框＝库空，传图即自动显示）
- 每张图填英文 **Alt text**

## ⚠️ 三条最容易踩的坑

1. **留空＝前台不显示**（想隐藏区块就清空字段；区块消失先查字段是不是被清了）
2. **改完必须点 Update**，预览要用 Save draft → Preview
3. 前台**只允许英文**（唯一例外：公司地址两处中文是合法的）

## 🛑 红线（碰到就停手找技术）

- 不改主题代码 / 不删模板守卫
- 不装新插件 / 不跑插件批量更新
- 不直接改数据库
- 大改动前先备份原文＋知会技术

## 🆘 出事了

| 症状 | 动作 |
|---|---|
| 改了前台没变 | 强刷 Cmd+Shift+R → 无痕窗口 → 找技术 |
| 页面错乱 | 撤销最近改动 → 贴回备份原文 → 找技术还原 |
| 全站打不开 | 截图 → 立即联系技术 |
| 可疑内容/陌生用户 | 截图保留现场 → 找技术，不要自己删 |

**技术支持（待补充）：联系人 ______ / 电话 ______ / 微信 ______**

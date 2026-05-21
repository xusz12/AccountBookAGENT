# 记账员

## Role
x的私人记账员，负责账单的记录、分析、报告等专职事务。
使用Claude code工具。

## Key Knowledge
- Read notes/channels.md for what each channel is about and ongoing work
- Read notes/bill-analysis.md for x's bill data overview

## Active Context
- x的账单CSV保存在工作区: 导出数据_2026年05月21日.csv (1361条)
- 上次交互: 2026-05-21
- task #5 (历史数据导入) ✅ Done。住房拆分已执行：
  - 账本: 1360条，收入 ¥427,094.66 / 支出 ¥329,197.79 / 净额 ¥97,896.87
  - 住房 61条拆分完毕: 房贷(26), 电费(16), 物业费(11), 燃气费(3), 水费(4), 装修(1)
  - 删除测试记录¥6，补办身份证→其他支出-证件办理
  - 分类体系: 新增证件办理，删除修理
  - 备份: ledger_before_housing_fix_20260521.sqlite
  - 冻结已解除，账本可正常使用

## Workspace
- Git 仓库已初始化（@GitSupervisor_Mac 管理）
- 远端: git@github.com:xusz12/AccountBookAGENT.git
- `.sqlite` 已加入 .gitignore（账本数据不入库）
- 初始提交 f1b0aeb：16文件，含 ledger.py、导入脚本、笔记

## Server Context
- 服务器有多个活跃 agent，涵盖执行、决策、质检、新闻、wiki、git管理、版本管理等角色。
- 相关频道: #all (已加入), #Opencli工作区, #闲聊区, #TwitterCLI工作区, #技能维护小组, #新闻小组, #学生比赛小组

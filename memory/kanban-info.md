# 看板系统信息

## 基本信息
- **URL**: http://60.205.114.200:3000/
- **名称**: 任务看板系统
- **类型**: 自建任务看板系统
- **用途**: 量化研究报告数据管理和团队协作
- **API Base**: http://60.205.114.200:3000/api
- **API Key**: AYbX2htp1XsbIgoM0EzIcg1zMBls+HPH7VH0QAQ46UE=

## 我的身份信息
- **看板用户名**: 花京院
- **角色**: AI管家
- **职责**: 
  - 接受用户和Q太郎的任务分派
  - 进行任务处理、回复、任务状态控制
  - 在BBS与Q太郎沟通交流

## 功能模块

### 1. 任务管理
- 查看待办: `GET /api/tasks?status=todo`
- 创建任务: `POST /api/tasks`
- 更新状态: `PATCH /api/tasks/:id/status`
- 查看统计: `GET /api/stats/overview`

**负责人列表**: 开发专员、运维专员、产品经理、文档专员、测试专员、AI管家(花京院)

### 2. BBS交流区
- 帖子列表: `GET /api/bbs/posts`
- 创建帖子: `POST /api/bbs/posts`
- 帖子详情: `GET /api/bbs/posts/:id`
- 回复帖子: `POST /api/bbs/posts/:id/replies`
- 支持关联任务ID、置顶帖子

### 3. @提及功能
- 获取提及: `GET /api/bbs/mentions?user=用户名`
- 未读提及: `GET /api/bbs/mentions?user=用户名&unread_only=true`
- 标记已读: `PATCH /api/bbs/mentions/:id/read`
- 全部已读: `PATCH /api/bbs/mentions/read-all`

## 关联文件
- 情景分析因子模型研报.pdf
- 风格轮动策略研报.pdf
- scenario_results/scenario_analysis_results.csv
- style_rotation_results/style_rotation_returns.csv
- style_rotation_results/style_rotation_indicators.csv
- style_rotation_results/style_rotation_summary.csv

## BBS帖子
- **帖子ID**: 9
- **标题**: 【量化研报回测数据】情景分析与风格轮动策略数据分享
- **链接**: http://60.205.114.200:3000/api/bbs/posts/9
- **附件**:
  - 4个CSV数据文件（IC统计、指标序列、收益明细、业绩汇总）
  - 2个Python源码文件（情景分析模型、风格轮动策略）

## 记录时间
- 创建: 2026-03-15
- 更新: 2026-03-15 (添加API信息和身份信息)

## 参考文档
- 完整API文档: https://gitee.com/lobstergit/kanban/blob/master/references/API.md

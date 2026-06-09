## Requirements

### Requirement: WebUI 后端 REST API
系统 SHALL 提供 FastAPI 后端，暴露 REST API 端点。后端 SHALL 是 CLI 的薄壳，所有操作 SHALL 通过调用 CLI 子命令实现。端点 SHALL 包括 `GET /api/status`、`GET /api/progress`、`GET /api/graph`、`GET /api/models`、`GET /api/models/{hash}`、`POST /api/run`、`POST /api/branch`、`POST /api/merge`。

#### Scenario: 查询状态
- **WHEN** 前端请求 `GET /api/status`
- **THEN** 后端调用 `mlevo status --json` 并返回结果

#### Scenario: 启动训练
- **WHEN** 前端请求 `POST /api/run` 带 `{"round": 11, "preset": "tiny"}`
- **THEN** 后端调用 `mlevo run --round 11 --preset tiny --json` 并返回结果

### Requirement: 仪表板视图
WebUI SHALL 提供仪表板页面，显示当前训练状态（pipeline_state、current_round）、最近一轮结果（winrate、promoted）、训练进度（stage、pct、eta）。仪表板 SHALL 支持手动刷新（页面按钮）和自动轮询（可配置间隔，默认 30 秒）。

#### Scenario: 查看当前状态
- **WHEN** 用户打开仪表板页面
- **THEN** 显示当前 round、最近 winrate、pipeline state

#### Scenario: 训练进行中显示进度
- **WHEN** pipeline_state 为 running
- **THEN** 仪表板显示当前 stage、完成百分比、预计剩余时间

### Requirement: 模型进化图谱视图
WebUI SHALL 提供 DAG 图谱可视化页面。图谱 SHALL 显示模型节点（hash、winrate、promoted 状态）和边（change 名、hypothesis、param_diff）。节点 SHALL 使用颜色区分 promoted（绿色）和 failed（灰色）。边 SHALL 可点击查看 proposal 详情。

#### Scenario: 渲染完整图谱
- **WHEN** 用户打开图谱页面
- **THEN** 显示所有模型节点和边，mainline 和分支清晰可区分

#### Scenario: 点击节点查看详情
- **WHEN** 用户点击一个模型节点
- **THEN** 弹出详情面板，显示 hash、parent、winrate、params、关联 change

#### Scenario: 点击边查看 proposal
- **WHEN** 用户点击一条边
- **THEN** 弹出详情面板，显示 change 名、hypothesis、param_diff、结果

### Requirement: 日志浏览器
WebUI SHALL 提供日志浏览页面，显示训练日志。日志 SHALL 按 round 和 stage 分组，支持按 round 筛选和按 level（INFO/WARN/ERROR）过滤。

#### Scenario: 浏览训练日志
- **WHEN** 用户打开日志页面
- **THEN** 显示最近训练的日志列表，按时间倒序

#### Scenario: 按 round 筛选
- **WHEN** 用户选择 round 7
- **THEN** 仅显示 round 7 的训练日志

### Requirement: 分支管理视图
WebUI SHALL 提供分支管理页面，显示所有分支列表（名称、fork_from、最新 winrate、rounds 数）。页面 SHALL 支持创建分支和发起 PK 对决。

#### Scenario: 查看分支列表
- **WHEN** 用户打开分支管理页面
- **THEN** 显示所有活跃分支和已 archive 的分支

#### Scenario: 创建新分支
- **WHEN** 用户选择一个历史模型并点击"创建分支"
- **THEN** 调用 `mlevo branch --from {hash}` 并刷新分支列表

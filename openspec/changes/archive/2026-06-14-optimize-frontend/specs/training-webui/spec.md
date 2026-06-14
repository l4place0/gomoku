## MODIFIED Requirements

### Requirement: 仪表板视图
WebUI SHALL 提供仪表板页面，显示当前训练状态（pipeline_state、current_round）、最近一轮结果（winrate、promoted）、训练进度（stage、pct、eta）。仪表板 SHALL 支持手动刷新（页面按钮）和自动轮询（可配置间隔，默认 30 秒）。仪表板 SHALL 具有响应式网格布局，支持大屏及移动端，且在数据加载时展示闪烁动画的骨架屏（Skeleton Loader）。仪表板还 SHALL 包含一个专门的“最近一轮 PK 结果”展示卡片，用于展示最近一轮的详细胜率、状态和父模型等信息。

#### Scenario: 查看当前状态
- **WHEN** 用户打开仪表板页面
- **THEN** 显示当前 round、最近 winrate、pipeline state

#### Scenario: 训练进行中显示进度
- **WHEN** pipeline_state 为 running
- **THEN** 仪表板显示当前 stage、完成百分比、预计剩余时间

#### Scenario: 仪表板在首次加载时显示骨架屏
- **WHEN** 仪表板数据正在从后端 API 加载
- **THEN** 页面以骨架屏闪烁动画占位，避免出现空白或布局抖动

#### Scenario: 仪表板展示最近一轮 PK 结果卡片
- **WHEN** 仪表板加载成功且存在模型记录
- **THEN** 显示“最近一轮 PK 结果”卡片，包含最近一轮的胜率（根据结果呈现红/黄/绿不同高亮）、分支、评测结果徽章（PROMOTED 或 DISCARDED）

### Requirement: 模型进化图谱视图
WebUI SHALL 提供 DAG 图谱可视化页面。图谱 SHALL 显示模型节点（hash、winrate、promoted 状态）和边（change 名、hypothesis、param_diff）。节点 SHALL 使用颜色区分 promoted（绿色）和 failed（灰色）。边 SHALL 可点击查看 proposal 详情。图谱视图的节点排布 SHALL 采用防止重叠的布局算法（按 round 水平排布，按分支垂直排布，配合碰撞检测微调）。当选中某个模型节点时，与之直接相连的节点及边线 SHALL 高亮展示，其余无关节点和边线则暗淡（dimmed）以辅助分析。

#### Scenario: 渲染完整图谱
- **WHEN** 用户打开图谱页面
- **THEN** 显示所有模型节点和边，mainline 和分支清晰可区分

#### Scenario: 点击节点查看详情
- **WHEN** 用户点击一个模型节点
- **THEN** 弹出详情面板，显示 hash、parent、winrate、params、关联 change

#### Scenario: 点击边查看 proposal
- **WHEN** 用户点击一条边
- **THEN** 弹出详情面板，显示 change 名、hypothesis、param_diff、结果

#### Scenario: 点击节点高亮相关链路
- **WHEN** 用户在图谱中点击选中任意模型节点
- **THEN** 选中节点与其直接上下游的连线和节点保持高亮且连线带有流动动画，其它无关的节点和连线变暗

### Requirement: 日志浏览器
WebUI SHALL 提供日志浏览页面，显示训练日志。日志 SHALL 按 round 和 stage 分组，支持按 round 筛选和按 level（INFO/WARN/ERROR）过滤。日志浏览器 SHALL 支持在窗口内容更新时可选地自动滚动到最底部，并在日志加载时展示骨架屏，同时提供符合开发人员审美的终端仿真界面样式。

#### Scenario: 浏览训练日志
- **WHEN** 用户打开日志页面
- **THEN** 显示最近训练的日志列表，按时间倒序

#### Scenario: 按 round 筛选
- **WHEN** 用户选择 round 7
- **THEN** 仅显示 round 7 的训练日志

#### Scenario: 终端日志自动滚动
- **WHEN** 开启“自动滚动”复选框且日志追加新行
- **THEN** 日志文本框视口自动滚动至底部

## ADDED Requirements

### Requirement: 计划注册表持久化
系统 SHALL 维护 `plan_registry.jsonl` 文件作为训练计划注册表。每行 SHALL 记录一个训练计划的完整元数据，包括 plan 名称、最佳模型、胜率、轮次、来源计划、来源模型、设计假设、状态。

#### Scenario: 录入新计划
- **WHEN** 创建新的训练计划并完成首轮训练
- **THEN** 系统在 plan_registry.jsonl 追加一行，记录计划元数据和最佳模型

#### Scenario: 更新计划状态
- **WHEN** 计划完成更多轮次或状态变更
- **THEN** 系统更新对应行的 rounds_completed、best_model、status

### Requirement: 超边关系
每条超边 SHALL 包含 from_model（模型继承）和 hypothesis（设计假设）两个属性。

#### Scenario: 记录传承关系
- **WHEN** Plan B 从 Plan A 的最佳模型开始训练
- **THEN** Plan B 的 from_plan=Plan A，from_model=Plan A 的最佳模型 hash

### Requirement: CLI 计划查询
系统 SHALL 支持 `mlevo plans --json` 列出所有计划，`mlevo plan --name <name> --json` 查看计划详情。

#### Scenario: 列出所有计划
- **WHEN** 执行 `mlevo plans --json`
- **THEN** 返回所有计划列表，包含 plan、best_model、best_winrate、status

#### Scenario: 查看计划详情
- **WHEN** 执行 `mlevo plan --name v3-anti-overfit --json`
- **THEN** 返回计划详情，包含内层图谱（该计划的所有轮次）

### Requirement: WebUI 两层图谱
WebUI SHALL 支持两层图谱可视化：外层超图（计划级）和内层 DAG（轮次级）。

#### Scenario: 外层超图渲染
- **WHEN** 用户打开图谱页面
- **THEN** 显示计划级节点（plan 名称、最佳胜率）和超边（from_model、hypothesis）

#### Scenario: 展开内层 DAG
- **WHEN** 用户点击一个计划节点
- **THEN** 展开显示该计划内的轮次链（已有 DAG）

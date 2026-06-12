## ADDED Requirements

### Requirement: mlevo-propose 使用 OpenSpec 集成
mlevo-propose skill SHALL 引导 Agent 使用 OpenSpec propose 流程创建训练计划。Action Guide SHALL 包含 `openspec new change` 和 `mlevo new plan` 的组合使用。SHALL 引用 `mlevo schema --json` 获取可用命令。

#### Scenario: 创建新训练计划
- **WHEN** 用户请求创建新训练计划
- **THEN** Agent 先用 openspec 创建 change，再用 `mlevo new plan` 生成训练配置，最后用 `--change` 参数关联

### Requirement: mlevo-apply 支持新架构参数
mlevo-apply skill SHALL 引用 `mlevo decide --branch` 和 `mlevo run --branch/--preset/--change` 命令。SHALL 说明模型注册表自动记录和 DAG 图谱更新。SHALL 包含故障注入 `--inject` 的使用说明。

#### Scenario: 在分支上执行训练
- **WHEN** 用户在指定分支上执行训练
- **THEN** Agent 使用 `mlevo run --round N --branch <name> --change <change-name>`

#### Scenario: 使用 preset 快速验证
- **WHEN** 用户需要快速验证管线
- **THEN** Agent 使用 `mlevo run --round N --preset tiny`

### Requirement: mlevo-archive 集成模型注册表
mlevo-archive skill SHALL 使用三 Agent 流水线（Collector → Compiler → Verifier）替代原有的自由写入模式。SHALL 使用 `mlevo report` CLI 命令作为 Collector 的事实采集工具。SHALL 要求 Compiler 的结论中每个数字必须引用 facts.json 中的具体字段。SHALL 要求 Verifier 独立读取原始日志进行交叉验证，不依赖 facts.json。

#### Scenario: 正常归档流程
- **WHEN** 训练计划完成，用户请求归档
- **THEN** Agent 执行: (1) `mlevo archive "name"` 移动目录 (2) `mlevo report "name" --json` 生成 facts.json (3) 基于 facts.json 写 conclusion.md 草稿 (4) 独立读取原始日志验证 conclusion.md (5) 如通过则完成归档

#### Scenario: Verifier 打回
- **WHEN** Verifier 发现 conclusion.md 与日志不符
- **THEN** 输出 verdict.json（含逐条不符项），Compiler 基于驳回理由修正结论，重新提交验证

#### Scenario: 三次打回升级
- **WHEN** Verifier 连续 3 次打回 conclusion.md
- **THEN** Agent 停止重试，输出 verdict.json 和所有历史驳回理由，等待用户介入

#### Scenario: 结论中出现模糊表述
- **WHEN** conclusion.md 中包含"胜率偏低"、"表现一般"等无具体数字的表述
- **THEN** Verifier SHALL 以 REJECT 打回，要求补充具体数值

#### Scenario: PK 结果无效但结论未标注
- **WHEN** facts.json 中某轮 PK 的 verdict 为 INVALID，但 conclusion.md 未标注 PK 无效原因
- **THEN** Verifier SHALL 以 REJECT 打回，要求补充 PK 有效性标注

### Requirement: mlevo-explore 使用模型注册表
mlevo-explore skill SHALL 使用 `model_registry.jsonl` 作为主数据源（替代 evolution_ledger.json）。SHALL 引用 `mlevo graph/models/history` 命令进行 DAG 分析。SHALL 更新硬件约束为 GTX 1650Ti。

#### Scenario: 分析模型进化图谱
- **WHEN** 用户要求分析训练状态
- **THEN** Agent 使用 `mlevo graph --with-edges --json` 获取 DAG，分析节点和边

#### Scenario: 对比分支表现
- **WHEN** 用户要求对比两个分支
- **THEN** Agent 使用 `mlevo models --branch <name> --json` 获取各分支模型列表

### Requirement: 全部 skill 引用测试框架
所有 mlevo-* skill SHALL 引用 `mlevo test --suite all --json` 测试框架。在执行训练前建议先跑测试验证管线完整性。

#### Scenario: 训练前验证
- **WHEN** Agent 准备执行训练
- **THEN** 建议先执行 `mlevo test --suite unit --json` 验证基础逻辑

### Requirement: 全部 skill 引用 WebUI 监控
所有 mlevo-* skill SHALL 引用 WebUI 监控能力（`http://localhost:3000`）。在长时间训练时建议用户通过 WebUI 监控进度。

#### Scenario: 长时间训练监控
- **WHEN** Agent 启动一轮训练
- **THEN** 提示用户可通过 WebUI 监控训练进度

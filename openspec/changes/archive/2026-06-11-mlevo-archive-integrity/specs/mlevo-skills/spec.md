## MODIFIED Requirements

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

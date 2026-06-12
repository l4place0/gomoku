## Why

mlevo-archive 流程缺乏事实审核和交叉验证，导致归档结论与实际日志严重不符。Agent 写 conclusion.md 时只看 ledger 不看日志，产生多处失实记录：R1 PK 结果 0/0 被写成 0/100，R2 日志有 100 局结果被写成"跳过"，R3 实际 10 局被写成"5 局 SPRT 提前终止"。这些错误会传导到 training-knowledge.md，污染后续训练决策。

## What Changes

- **新增 `mlevo report` CLI 命令**: 从 PK 日志、训练日志、ledger 中自动提取结构化事实，输出 `facts.json`。确定性逻辑放 CLI，不依赖 Agent 判断。
- **重构 mlevo-archive skill 为三 Agent 流水线**: Collector（CLI 事实采集）→ Compiler（基于 facts.json 写结论）→ Verifier（独立核实结论 vs 原始日志）。Verifier 打回最多 3 次，超过后等人介入。
- **修正已腐化的归档文档**: 用新流程重新生成 b10c256nbt-validation 的 conclusion.md 和 training-knowledge.md 对应章节。

## Capabilities

### New Capabilities

- `archive-fact-report`: 从 PK 日志、训练日志、ledger 中提取结构化事实的 CLI 命令。覆盖日志解析、IPC 失败检测、颜色偏差统计、ledger 一致性检查。

### Modified Capabilities

- `mlevo-skills`: mlevo-archive skill 的工作流从"Agent 自由发挥"改为"三 Agent 流水线 + 事实审核"。新增 Verifier 打回机制和人工介入升级。

## Impact

- `ml/mlevo_cli.py`: 新增 `report` 子命令，解析 `round_*_pk.log`、`round_*_train.log`、`evolution_ledger.json`
- `.claude/skills/mlevo-archive/SKILL.md`: 重构工作流，集成 Collector/Compiler/Verifier 三阶段
- `docs/ml/plans/archive/2026-06-11-b10c256nbt-validation/conclusion.md`: 已修正，需验证一致性
- `docs/ml/specs/training-knowledge.md`: 已修正 b10c256nbt 章节，需验证一致性

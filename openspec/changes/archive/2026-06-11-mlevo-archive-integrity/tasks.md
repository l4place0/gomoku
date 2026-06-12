## 1. mlevo report CLI 命令

- [x] 1.1 在 `ml/mlevo_cli.py` 中实现 `cmd_report` 函数，支持 `mlevo report <plan-name> --json`
- [x] 1.2 实现 PK 日志解析：从 `round_*_pk.log` 提取完成局数、胜负分布、IPC 失败次数、VCF 错误次数
- [x] 1.3 实现训练日志解析：从 `round_*_train.log` 提取 vloss、pacc1、p0loss
- [x] 1.4 实现 Ledger 一致性检查：对比 PK 日志实际结果与 `evolution_ledger.json` 记录
- [x] 1.5 实现 PK 有效性判定：INVALID（IPC>0 或完成<50%）、DEGRADED（颜色偏差>70%）、VALID
- [x] 1.6 注册 `report` 子命令到 argparse 和 dispatch 表

## 2. mlevo-archive skill 重构

- [x] 2.1 更新 `.claude/skills/mlevo-archive/SKILL.md`：将工作流改为三 Agent 流水线（Collector → Compiler → Verifier）
- [x] 2.2 编写 Collector Agent 指令：调用 `mlevo report` 生成 facts.json
- [x] 2.3 编写 Compiler Agent 指令：基于 facts.json 写 conclusion.md，每项必须引用具体字段
- [x] 2.4 编写 Verifier Agent 指令：独立读原始日志验证 conclusion.md，逐项核对数字
- [x] 2.5 实现打回机制：Verifier REJECT 时传 verdict.json 给 Compiler 修正，最多 3 次
- [x] 2.6 实现人工介入升级：3 次 REJECT 后停止并输出历史驳回理由

## 3. 验证

- [x] 3.1 用 `mlevo report` 重新生成 b10c256nbt-validation 的 facts.json，与已修正的 conclusion.md 对比一致性
- [x] 3.2 用 `mlevo report` 验证 v4-stabilize-r9-r10 的 conclusion.md
- [x] 3.3 测试 mlevo report 对计划不存在、日志缺失等边界情况的处理

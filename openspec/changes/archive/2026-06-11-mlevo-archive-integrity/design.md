## Context

mlevo-archive 流程当前由 `mlevo_cli.py` 的 `cmd_archive` 函数和 `.claude/skills/mlevo-archive/SKILL.md` 组成。`cmd_archive` 只做 `shutil.move(plan_dir, target_dir)`，不生成任何分析内容。conclusion.md 和 training-knowledge.md 完全靠 Agent 自行判断写入，没有事实审核机制。

已发生的腐化案例：
- b10c256nbt R1: ledger 0/0 → 结论写 0/100
- b10c256nbt R2: 日志有 100 局 → 结论写"跳过"
- v4-stabilize R9/R10: 81% 为缓存假数据 → 未标注

现有数据源：
- `ml/data/logs/round_*_pk.log` — PK 游戏逐手日志
- `ml/data/logs/round_*_train.log` — 训练 loss/metrics 日志
- `ml/data/logs/evolution_ledger.json` — 每轮 PK 结果记录
- `ml/data/model_registry.jsonl` — 模型注册表
- `ml/data/b10c256nbt_data/pk_result_*.json` — 结构化 PK 结果

## Goals / Non-Goals

**Goals:**
- 归档结论的每个数字必须有日志依据，不允许凭空推断
- 自动检测日志异常（IPC 失败、颜色偏差、样本不足）
- Verifier 独立核实，发现偏差必须打回
- 三次打回后升级到人工介入

**Non-Goals:**
- 不修改 PK/训练流程本身，只修改归档流程
- 不自动修复日志中的异常（如 IPC 崩溃），只记录和报告
- 不改变 conclusion.md 的最终格式，只保障内容准确性

## Decisions

### Decision 1: Collector 放 CLI 而非 Agent

**选择**: 把事实采集逻辑放到 `mlevo report` CLI 命令

**理由**: 日志解析是确定性逻辑（grep 特定模式、计数、提取数字），放 CLI 更可靠、可测试、可复现。Agent 做确定性任务容易产生随机遗漏。

**替代方案**: 全部用 Agent — 灵活但不可靠，正是当前腐化的原因。

### Decision 2: Verifier 独立读日志，不看 facts.json

**选择**: Verifier 接收 conclusion.md 草稿 + 原始日志路径，自己独立解析日志

**理由**: 如果 Verifier 看 facts.json，它和 Collector 共享同一份数据，Collector 遗漏的内容 Verifier 也抓不到。独立读日志形成真正的交叉验证。

**替代方案**: Verifier 对比 facts.json vs conclusion.md — 更简单但无法检测 Collector 的遗漏。

### Decision 3: 打回机制带驳回理由上下文

**选择**: Compiler 被打回时，接收 Verifier 的 verdict.json（含逐条不符项），基于驳回理由修正

**理由**: 无上下文的盲目重试没有意义。Compiler 需要知道哪里错了才能修正。

### Decision 4: 三次打回后等人介入

**选择**: 最多重试 3 次，超过后输出 verdict.json 并停止

**理由**: 无限重试浪费 token。3 次后大概率是系统性问题（日志格式变了、Parser 有 bug），需要人判断。

## Risks / Trade-offs

- **[Risk] PK 日志格式不统一** → Collector 需要处理多种格式（sub1/sub2 分离、单进程交替、SPRT 提前终止）。缓解: 先支持最常见的格式，后续逐步扩展。
- **[Risk] Verifier 误判** → Verifier 可能因为日志格式解析错误而打回正确的结论。缓解: Verifier 的 issues 中必须引用原始日志行作为证据。
- **[Risk] 训练日志格式变化** → KataGomo 训练脚本的输出格式可能随版本变化。缓解: 训练指标提取用正则匹配，失败时标记为 `PARSE_ERROR` 而非硬编码默认值。
- **[Trade-off] CLI 命令 vs 全 Agent** → CLI 更可靠但需要写代码维护；Agent 更灵活但不可靠。选择 CLI 是因为腐化的根因正是 Agent 的不可靠性。

## Migration Plan

1. 实现 `mlevo report` CLI 命令（新增函数，不影响现有命令）
2. 更新 mlevo-archive skill（替换现有 skill 内容）
3. 用新流程验证 b10c256nbt-validation 的 conclusion.md（如果已修正则确认一致性）
4. 回滚策略: 旧 skill 内容可通过 git 恢复

## Open Questions

1. Collector 的 PK 日志解析需要支持哪些格式？（当前只有 sub1/sub2 和单进程交替两种）
2. training-knowledge.md 的更新是否也纳入 Verifier 验证范围？（当前只验证 conclusion.md）

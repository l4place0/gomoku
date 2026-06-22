## ADDED Requirements

### Requirement: atml-explore 交互式探索
atml-explore skill SHALL 分三阶段执行：Phase 1 强制采集（读取 docs/ml/ 和 ml/data/）、Phase 2 交互式循环探索（用户驱动方向）、Phase 3 结构化输出（写入 docs/ml/insights.json）。SHALL 强制读取 `docs/ml/specs/training-knowledge.md`、`ml/data/model_registry.jsonl`、最近 N 轮训练日志。数据来源 MUST 为 `docs/ml/` 和 `ml/data/`，不得凭空生成。

#### Scenario: 强制采集
- **WHEN** 用户执行 `/atml-explore`
- **THEN** Agent 先执行 `mlevo status --json`、`mlevo graph --with-edges --json`、`mlevo models --json`，读取 `docs/ml/specs/training-knowledge.md` 和最近 3 轮日志，生成 dashboard 概览后才进入 Phase 2

#### Scenario: 交互式探索
- **WHEN** Agent 呈现 dashboard 概览后
- **THEN** 等待用户指示，支持深入模型历史、对比分支、查看日志、验证假设等操作，循环直到用户明确结束

#### Scenario: 结构化输出
- **WHEN** 用户表示探索结束
- **THEN** 更新 `docs/ml/insights.json`（覆盖写入），输出行动建议（进入 propose 或继续 apply）

### Requirement: atml-propose 单脚手架
atml-propose skill SHALL 在 `docs/ml/changes/<name>/` 下创建全部变更产物（proposal.md、design.md、tasks.md、training_plan.json），不得调用 `openspec new change`。SHALL 读取 `docs/ml/insights.json`（如存在）和 `docs/ml/specs/training-knowledge.md` 作为上下文。

#### Scenario: 创建训练计划
- **WHEN** 用户请求创建新训练计划
- **THEN** Agent 先读取 insights.json 和 training-knowledge.md，然后在 `docs/ml/changes/<name>/` 下创建 proposal.md、design.md、tasks.md、training_plan.json

#### Scenario: 无 insights 时创建
- **WHEN** `docs/ml/insights.json` 不存在
- **THEN** Agent 跳过 insights 读取，仅基于 training-knowledge.md 和 CLI 能力创建计划

### Requirement: atml-apply 自动模式
atml-apply skill SHALL 默认以自动模式执行：无 guardrail warning 时直接执行训练，不打断用户。SHALL 读取 `docs/ml/changes/<name>/training_plan.json` 作为训练配置。SHALL 仅在 guardrail warning 出现时请求用户确认。

#### Scenario: 无警告自动执行
- **WHEN** `mlevo decide --json` 返回空 guardrail_warnings
- **THEN** Agent 直接执行 `mlevo run`，不请求用户确认

#### Scenario: 有警告时确认
- **WHEN** `mlevo decide --json` 返回非空 guardrail_warnings
- **THEN** Agent 展示警告并请求用户确认后再执行

#### Scenario: 多轮循环
- **WHEN** 用户要求执行多轮训练
- **THEN** Agent 循环执行 decide → (auto/confirm) → run → check，仅在 warning 时暂停

### Requirement: atml-archive 自适应路径
atml-archive skill SHALL 根据计划复杂度选择归档路径：≤2 轮且全 VALID → 快速路径（单 Agent），>2 轮或有 INVALID → 完整三 Agent 流水线。SHALL 归档到 `docs/ml/changes/archive/`。SHALL 更新 `docs/ml/specs/training-knowledge.md`。

#### Scenario: 快速归档
- **WHEN** 训练计划 ≤2 轮且所有 PK verdict 为 VALID
- **THEN** Agent 执行 `mlevo archive` + `mlevo report`，基于 facts.json 写 conclusion.md，更新 training-knowledge.md，归档到 `docs/ml/changes/archive/<date>-<name>/`

#### Scenario: 完整归档
- **WHEN** 训练计划 >2 轮或有 INVALID PK verdict
- **THEN** Agent 执行三 Agent 流水线：Collector（mlevo report → facts.json）→ Compiler（写 conclusion.md）→ Verifier（独立读原始日志验证），最多 3 次 REJECT

#### Scenario: 归档闭环
- **WHEN** 归档完成
- **THEN** training-knowledge.md 被更新，下次 `/atml-explore` 会强制读取该文件

### Requirement: atml 数据目录规范
所有 atml 变更产物 SHALL 存储在 `docs/ml/changes/` 下。运行时训练数据（日志、模型文件、注册表）存储在 `ml/data/` 下。两套数据物理分离，通过 plan name 关联。

#### Scenario: 变更产物路径
- **WHEN** Agent 创建或读取训练计划
- **THEN** 路径为 `docs/ml/changes/<name>/`（活跃）或 `docs/ml/changes/archive/<date>-<name>/`（已归档）

#### Scenario: 运行时数据路径
- **WHEN** Agent 读取训练日志或模型注册表
- **THEN** 路径为 `ml/data/logs/round_*_train.log`、`ml/data/model_registry.jsonl`

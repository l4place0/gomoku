## Context

mlevo-* skill 文件是 Agent 与 ML 训练管线交互的协议层。当前 skill 引用的命令、数据源、工作流步骤均基于旧架构（线性轮次、evolution_ledger.json）。新架构已完成 DAG 模型图谱、CLI 状态机、分支训练、WebUI 等工程化改造，skill 需要同步更新。

## Goals / Non-Goals

**Goals:**
- 每个 skill 的 Action Guide 引用正确的 CLI 子命令和参数
- 数据源从 evolution_ledger.json 迁移到 model_registry.jsonl
- 工作流步骤反映新的状态机和 DAG 图谱
- 添加分支训练、WebUI 监控、测试框架的引用

**Non-Goals:**
- 不修改 CLI 代码
- 不修改 WebUI 代码
- 不创建新的 skill

## Decisions

### D1: 每个 skill 的更新范围

| Skill | 核心变更 |
|-------|---------|
| mlevo-propose | `mlevo new plan` → OpenSpec propose + `mlevo new plan` + `--change` 关联 |
| mlevo-apply | `mlevo decide/run` 加 `--branch`/`--preset`/`--change`，加入注册表自动记录说明 |
| mlevo-archive | `mlevo archive` 加模型注册表归档说明，关联 OpenSpec archive |
| mlevo-explore | 数据源改为 `model_registry.jsonl`，加 `mlevo graph/models/history` 命令，更新硬件约束 |

### D2: 数据源映射

```
旧: logs/evolution_ledger.json → 新: model_registry.jsonl
旧: training_plan.json          → 保留 (训练计划配置)
旧: model.bin.gz 覆盖           → 新: models/{hash}.bin.gz 版本化
```

### D3: 命令映射

```
旧: mlevo run --round N
新: mlevo run --round N --branch <name> --preset <tiny|small|full> --change <change-name>

旧: mlevo decide
新: mlevo decide --branch <name>

新增:
  mlevo graph --with-edges --json    (DAG 图谱)
  mlevo models --branch <name> --json (模型列表)
  mlevo history --model <hash> --json (祖先链)
  mlevo test --suite all --json       (测试框架)
  mlevo schema --json                 (Agent 自描述)
```

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| Skill 更新后与旧流程不兼容 | 旧流程已通过 ml-pipeline-dag-engineering 重构，不再使用 |
| Agent 命令引用错误 | 更新后跑一次 mlevo test --suite all 验证 |

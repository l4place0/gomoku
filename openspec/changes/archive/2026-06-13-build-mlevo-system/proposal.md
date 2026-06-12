## Why

当前的 ML 训练技能 (`automl-supervised-evolution` SKILL.md) 是一份自然语言说明书，Agent 读完后自由发挥，缺少结构化的工作流管控。实际运行中暴露严重问题：4 轮训练全部 `promoted=false`，参数 (`sf_games=5`, `pk_games=2`, `sh_samples=200`) 与研究报告建议 (`sf_games≥500`, `pk_games≥20`, `sh_samples≥50000`) 差距达 100x-3000x，且没有自适应调参机制真正生效。

需要参照 OpenSpec 的 explore → propose → apply → archive 架构，构建一套 **结构化的 ML 进化工作流管理系统 (MLEvo)**，包含专用 CLI 工具、4 个独立 SKILL、文档目录结构、以及可执行的自适应决策引擎。

## What Changes

- **新增 `mlevo_cli.py`**：专用 CLI 工具管理 ML 进化计划的生命周期（创建/状态/决策/执行/归档），内嵌自适应决策引擎和研究报告硬约束检查
- **新增 `docs/ml/` 目录结构**：`plans/` (活跃计划) + `specs/` (持久化训练知识) + `references/` (外部研究文档)
- **新增 4 个 Agent SKILL**：`mlevo-explore`、`mlevo-propose`、`mlevo-apply`、`mlevo-archive`，各自对应进化计划的一个生命周期阶段
- **新增 4 个 Workflow**：`/ml-explore`、`/ml-propose`、`/ml-apply`、`/ml-archive` 斜杠命令
- **删除旧 SKILL**：移除 `automl-supervised-evolution` SKILL.md
- **保留 `automl_cli.py`**：作为底层执行引擎被 `mlevo_cli.py` 调用，不做结构性修改

## Capabilities

### New Capabilities
- `mlevo-workflow`: MLEvo CLI 工作流管理能力 — 计划 CRUD、状态查询、自适应参数决策、执行编排、归档与知识沉淀
- `mlevo-agent-skills`: 4 个独立 Agent SKILL + Workflow 的定义与行为规范

### Modified Capabilities
_(无现有 spec 需修改)_

## Impact

- **新增文件**：`mlevo_cli.py`，`docs/ml/**`，4 个 SKILL.md，4 个 workflow.md
- **删除文件**：`.agent/skills/automl-supervised-evolution/SKILL.md`
- **依赖关系**：`mlevo_cli.py` 调用 `automl_cli.py`，读写 `docs/ml/plans/` 和 `logs/evolution_ledger.json`
- **测试**：`mlevo_cli.py` 的纯逻辑函数（决策引擎、guardrail 检查、plan 解析）需 >90% 覆盖率

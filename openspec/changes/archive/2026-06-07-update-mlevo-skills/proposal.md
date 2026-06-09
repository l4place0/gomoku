## Why

mlevo-propose/apply/archive/explore 四个 skill 在 `ml-pipeline-dag-engineering` 架构升级前编写，引用的是旧架构接口（线性轮次、evolution_ledger.json、无分支支持）。新架构已上线 18 个 CLI 子命令、模型注册表、DAG 引擎、分支训练、WebUI 监控、测试框架，但 skill 未同步更新，导致 Agent 使用时行为与实际能力脱节。

## What Changes

- **mlevo-propose**: 更新为 OpenSpec 集成模式，关联 `--change` 参数，引用模型注册表而非 ledger
- **mlevo-apply**: 更新 `run` 命令参数（`--branch`/`--preset`/`--change`/`--inject`），加入模型注册表自动记录、DAG 图谱更新说明
- **mlevo-archive**: 更新为模型注册表归档 + OpenSpec archive 集成
- **mlevo-explore**: 数据源从 `evolution_ledger.json` 改为 `model_registry.jsonl`，加入 DAG 图谱分析、分支对比、`mlevo graph/models/history` 命令引用，更新硬件约束为 GTX 1650Ti
- 全部 skill: 更新环境信息（GTX 1060 → GTX 1650Ti）、添加 WebUI 监控引用、添加 `mlevo test` 测试框架引用

## Capabilities

### New Capabilities

_(无新增 capability，仅更新 skill 文件内容)_

### Modified Capabilities

- `ml-training`: skill 文件中的命令引用、数据源、工作流步骤需与新架构对齐

## Impact

- **文件**: `.claude/skills/mlevo-propose/SKILL.md`、`.claude/skills/mlevo-apply/SKILL.md`、`.claude/skills/mlevo-archive/SKILL.md`、`.claude/skills/mlevo-explore/SKILL.md`
- **无代码变更**: 仅修改 skill 文档，不涉及 Python/JS 代码
- **无依赖变更**: 不引入新依赖

# atml-workflow-v3-refactor

## Summary

将 mlevo-* 工作流系列全面重构为 atml-*，升级到 v3/v4 架构：交互式 explore、单脚手架 propose、auto 模式 apply、自适应路径 archive。同时将 atml 文档从 openspec/ 迁移到 docs/ml/ 下，实现 opsx（全代码库）和 atml（训练层）的职责分离。

## Motivation

原有 mlevo-* 工作流存在多个问题：
1. **技能间断裂**：explore 的发现无法传递给 propose，用户需手动转述
2. **双重脚手架**：propose 同时创建 OpenSpec change 和 mlevo plan，产生 3 个重复文件
3. **高摩擦 apply**：每轮训练都要求用户确认参数，多轮计划体验差
4. **archive 无轻量路径**：1 轮快速实验和 10 轮重要验证走同样重的 3-Agent 流水线
5. **无闭环**：archive 更新的 training-knowledge.md 不会自动影响下次决策
6. **文档混放**：atml 变更散落在 openspec/changes/ 中，和通用代码变更混在一起

## What Changes

- **重命名**：mlevo-{explore,propose,apply,archive} → atml-{explore,propose,apply,archive}
- **explore v3**：交互式三阶段（强制采集 → 循环探索 → 结构化输出 insights.json）
- **propose v3**：单一脚手架 docs/ml/changes/\<name\>/，不再调 openspec
- **apply v3**：auto 模式，无 guardrail warning 时不打断用户
- **archive v4**：自适应路径（≤2 轮全 VALID → 快速归档，否则 → 三 Agent 流水线）
- **路径迁移**：mlevo_cli.py 的 PLANS_DIR → CHANGES_DIR（docs/ml/changes/）
- **spec 迁移**：openspec/specs/atml-skills/ → docs/ml/specs/atml-skills/
- **v1.0 清理**：删除 .agent/skills/mlevo-* 过时文件

## Capabilities

### Modified Capabilities

- `atml-skills`：四个技能全部重写，新增交互式 explore、auto 模式 apply、自适应 archive、insights.json 数据传递

## Impact

- `.claude/skills/atml-{explore,propose,apply,archive}/SKILL.md`：全部重写
- `ml/mlevo_cli.py`：路径常量和 5 个函数更新
- `tests/ml/test_mlevo.py`：测试适配 CHANGES_DIR
- `docs/ml/specs/atml-skills/spec.md`：从 openspec 迁移并全面重写
- `docs/ml/changes/`：新建目录结构
- `openspec/specs/atml-skills/`：已迁移到 docs/ml/
- `.agent/skills/mlevo-*`：已删除

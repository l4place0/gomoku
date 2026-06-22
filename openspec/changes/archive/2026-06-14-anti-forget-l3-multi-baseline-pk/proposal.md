# anti-forget-l3-multi-baseline-pk

## Summary

扩展 PK 评估阶段，除父代基线外增加对祖父代和更早祖先的回归检验，直接检测模型是否遗忘了历史能力。

## Motivation

当前 PK 只与 immediate parent 对弈，无法发现渐进式遗忘——一个模型可能以 60% 胜率击败父代，但对祖父代只有 30% 胜率（意味着它忘记了更早学到的技能。研究报告中 Tablut 实验明确建议 25% 对局对过去检查点。model_registry.py 已有 `get_parent_chain()` 基础设施，只需在 PK 阶段利用它。

## Scope

- `ml/automl_cli.py` — `run_pk()` 增加多轮 PK：candidate vs parent + candidate vs grandparent
- `tools/headless_runner.py` — 支持快速短局回归 PK（少局数，主要用于检测严重遗忘）
- `ml/mlevo_cli.py` — `cmd_pk()` 支持 `--regression` 标志
- 回归 PK 结果写入 model_registry.jsonl 的 `regression_results` 字段

## Out of Scope

- selfplay 阶段不使用历史模型（属于更复杂的方案）
- 回归检测的自动化决策（属于 Layer 4）

## Success Criteria

- 每次晋升 PK 自动附带 1-2 场回归 PK
- regression_results 记录 candidate 对 ancestor 的胜率
- 回归 PK 额外耗时 < 20%（用少局数 + SPRT 早停）

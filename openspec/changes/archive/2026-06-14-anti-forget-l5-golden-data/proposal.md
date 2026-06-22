# anti-forget-l5-golden-data

## Summary

建立黄金数据/课程机制，持久化高价值棋局位置，在每轮训练中混入以确保模型不遗忘关键战术模式。

## Motivation

研究报告中 CuSP 框架的"反灾难性利用"原则：渐进探索的同时必须保留已解决的目标。当前管线已有 `mine_high_winrate_openings()` 在晋升后挖掘高胜率开局，但这些数据只写入开局库，不参与训练。将高价值位置（policy surprise 高、关键战术型）持久化为"黄金数据"并混入训练，可以确保模型不遗忘关键棋力。

## Scope

- `ml/data/curriculum/` — 新增目录
  - `golden_positions.jsonl` — 高价值棋局位置（来自 search_logs 的 policy surprise 高的走法）
  - `regression_suite.jsonl` — 回归测试集（祖先模型的标志性棋局）
- `ml/automl_cli.py` — 晋升后自动从 search_logs 挖掘 golden positions
- `ml/automl_cli.py` — shuffle 阶段混入 5-10% golden data
- 扩展 `mine_high_winrate_openings()` → `mine_golden_positions()`

## Out of Scope

- 开局库本身不修改（已有独立流程）
- curriculum 难度自适应（未来可探索）

## Success Criteria

- 晋升后自动产出 golden_positions.jsonl
- shuffle 日志显示 golden data 混入比例
- golden data 总量可控（< 总训练数据的 10%）

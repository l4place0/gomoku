## Why

基于 mlevo-explore 分析，R8-R10 出现严重过拟合：训练 loss 持续下降（1.98→1.82）但 winrate 暴跌（34-54%）。原因：DecisionEngine 在连续失败时增加 epochs + 降低 lr，导致在同质数据上过度训练。需要创建新的训练计划，采用反过拟合参数策略。

## What Changes

- 创建 `v3-anti-overfit` 训练计划，5 轮
- 关键参数调整：
  - `tr_epochs: 3 → 1`（最关键：减少过拟合）
  - `tr_lr: 0.00025 → 0.001`（回退到 Stage 2 水平）
  - `sf_games: 960 → 400`（不追量）
  - `sf_visits: 144 → 96`（回到研究建议区间）
  - `sh_samples: 30000`（保持）
  - `pk_games: 8 → 30`（增加评估可靠性）
- 集成开局随机化（opening_seeds.json + select_opening.py）

## Capabilities

### New Capabilities

_(无新增 capability，仅训练参数调整)_

### Modified Capabilities

- `ml-training`: 训练参数从过拟合配置回退到反过拟合配置

## Impact

- **训练计划**: `docs/ml/plans/v3-anti-overfit/training_plan.json`
- **模型**: b10c128（保持不变）
- **开局随机化**: 已实现（opening_seeds.json, 30 条种子）

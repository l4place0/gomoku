## Context

R8-R10 训练出现过拟合：loss 持续下降但 winrate 暴跌。DecisionEngine 的自适应调参方向错误（增加 epochs + 降低 lr = 过拟合加剧）。需要新的训练计划采用反过拟合策略。

## Goals / Non-Goals

**Goals:**
- 5 轮训练验证反过拟合参数策略
- 集成开局随机化提升数据多样性
- 每轮 1 epoch 避免在同质数据上反复训练

**Non-Goals:**
- 不追求最高 winrate（目标是稳定，不是最强）
- 不改变模型架构（保持 b10c128）
- 不实现滚动数据窗口（后续再做）

## Decisions

### D1: 参数策略

| 参数 | R8-R10 值 | v3 值 | 理由 |
|------|-----------|-------|------|
| tr_epochs | 3 | 1 | 最关键：减少过拟合 |
| tr_lr | 0.00025 | 0.001 | 回退到 Stage 2 水平 |
| sf_games | 960 | 400 | 不追量，质量优先 |
| sf_visits | 144 | 96 | 回到研究建议区间 |
| sh_samples | 30000 | 30000 | 保持 |
| pk_games | 8 | 30 | 增加评估可靠性 |

### D2: 开局随机化

使用 opening_seeds.json（30 条平衡种子）+ select_opening.py（随机选种子写入 cfg）。每轮 selfplay 前自动调用。

### D3: 分支策略

在 mainline 基础上创建 v3-anti-overfit 分支，从 round 7 模型（winrate 80.6%）分叉。

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| 1 epoch 可能欠拟合 | 观察 loss 下降趋势，如果 loss 不降再考虑加 epoch |
| 400 games 数据量可能不足 | 后续轮次可逐步增加 |
| lr=0.001 可能过高 | 对比 R6-R7（同样 lr=0.001）的成功经验 |

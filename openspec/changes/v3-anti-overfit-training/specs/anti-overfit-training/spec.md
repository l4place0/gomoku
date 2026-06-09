## ADDED Requirements

### Requirement: 反过拟合训练参数
训练计划 SHALL 使用反过拟合参数策略：tr_epochs=1, tr_lr=0.001, sf_games=400, sf_visits=96。

#### Scenario: 执行一轮训练
- **WHEN** 执行 `mlevo run --round 1 --plan v3-anti-overfit`
- **THEN** 使用 epochs=1, lr=0.001, games=400, visits=96 参数

### Requirement: 开局随机化集成
每轮 selfplay 前 SHALL 自动调用 select_opening.py 从 opening_seeds.json 随机选择开局种子。

#### Scenario: selfplay 前选择开局
- **WHEN** 训练进入 selfplay 阶段
- **THEN** 自动调用 select_opening.py，输出选中的开局种子

### Requirement: 分支训练
训练 SHALL 在 v3-anti-overfit 分支上执行，从 round 7 模型（winrate 80.6%）分叉。

#### Scenario: 创建分支
- **WHEN** 执行 `mlevo branch --from ac884021b92a --name v3-anti-overfit`
- **THEN** 创建分支，后续训练在此分支上进行

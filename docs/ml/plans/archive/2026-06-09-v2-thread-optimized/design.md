# Design: v2-thread-optimized

## Model Architecture
模型：`b10c128`（~3M参数，10个残差块，128通道）
- 轻量级，适合GTX 1650 Ti（4GB VRAM）
- 训练batch=64，显存占用约3-4GB

## 参数优化依据

### 自博弈并发
- 原配置 `numGameThreads=4`，GPU基本空转
- 提升至32线程，配合 `nnMaxBatchSize=128`
- 预期自博弈吞吐提升4-6倍

### 根节点噪声（新增）
- `rootNoiseEnabled=true`，`rootDirichletNoiseWeight=0.25`
- `rootPolicyTemperatureEarly=1.8`，`rootPolicyTemperature=1.2`
- `cpuctExploration=1.0`，与KataGomo Gom2024官方配置对齐
- 增强开局多样性，防止策略坍缩

### 训练节奏
- `max-epochs` 从1提升到2-3
- 解决价值损失单epoch不收敛的问题
- 学习率从0.002降至0.001，防止过拟合

### 评估可靠性
- PK局数从20提升到40-50
- 降低开局方差对胜率估计的干扰

## 阶段规划
| 阶段 | 轮次 | sf_games | sf_visits | tr_epochs | tr_lr | pk_games |
|---|---|---|---|---|---|---|
| 稳定提升 | 6-8 | 600 | 112 | 2 | 0.001 | 40 |
| 收敛收尾 | 9-10 | 800 | 128 | 3 | 0.0005 | 50 |

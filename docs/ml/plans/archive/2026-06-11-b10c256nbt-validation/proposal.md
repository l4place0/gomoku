# b10c256nbt Validation Plan

## Context

v4-stabilize 分支完成 10 轮训练后，b10c128 (2.96M params) 的 policy head 已饱和（pacc1 停滞在 ~50%），但 value head 仍在改善（vloss 从 0.951 降到 0.879）。这表明模型容量是瓶颈，需要更大网络。

Dry-run 测试确认 b10c256nbt (6.49M params) 在 GTX 1650 Ti (4GB) 上 batch=64 仅用 1.3GB VRAM，完全可行。

## Goal

用 3 轮训练验证 b10c256nbt 随机初始化后的收敛能力：
- R1: 验证训练流程跑通，loss 正常下降
- R2: 验证自博弈数据质量，模型开始学习
- R3: 验证 PK 评估可靠性，确认模型能否晋升

## Success Criteria

| 指标 | R1 目标 | R2 目标 | R3 目标 |
|------|---------|---------|---------|
| vloss | < 1.2 | < 1.0 | < 0.9 |
| pacc1 | > 35% | > 42% | > 47% |
| PK winrate | N/A (首轮无基线) | > 55% | > 58% |
| 训练无 OOM | ✓ | ✓ | ✓ |
| 无 NaN | ✓ | ✓ | ✓ |

## Risk

1. **收敛速度未知**: b10c256nbt 参数量是 b10c128 的 2.2 倍，可能需要更多轮才能看到 PK 晋升
2. **训练时间膨胀**: 每轮预计 ~20-25min（vs b10c128 的 ~25min），3 轮总计 ~1-1.5h
3. **小数据过拟合**: sh_samples=150K 是新参数，需要验证是否足够

## Key Parameters vs v4-stabilize

| 参数 | v4-stabilize (R10) | b10c256nbt-validation | 变更理由 |
|------|-------------------|----------------------|----------|
| model_kind | b10c128 | **b10c256nbt** | 容量升级 |
| tr_lr | 0.0005 | **0.001** | KataGo 社区推荐 256 通道用 0.001 |
| tr_batch | 64 | 64 | dry-run 确认可行 |
| sh_samples | 50000 | **150000** | 更大模型需要更多数据 |
| tr_epochs | 2 | **1** | 新模型先用 1 epoch 验证 |
| sf_games | 800 | 800 | 不变 |
| sf_visits | 128 | 128 | 不变 |
| pk_games | 100 | 100 | 不变 |
| pk_visits | 128/128 | 128/128 | 不变 |
| pk_threshold | 0.58 | 0.58 | 不变 |

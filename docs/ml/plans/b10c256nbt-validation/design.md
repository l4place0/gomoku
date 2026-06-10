# b10c256nbt Validation Design

## Architecture Comparison

| 属性 | b10c128 | b10c256nbt |
|------|---------|------------|
| 残差块 | 10 blocks (regular) | 10 blocks (bottlenest2) |
| trunk 通道 | 128 | 256 |
| gpool 通道 | 32 | 64 |
| 参数量 | 2,961,633 | 6,491,653 |
| VRAM (batch=64) | ~800 MiB | ~1,300 MiB |
| 步速 (batch=64) | ~16s | ~62s |

## Why b10c256nbt

1. **参数效率**: bottleneck 结构用 6.49M 参数达到 256 通道，比普通 b10c256 省约 45% 参数
2. **VRAM 友好**: 1.3GB 训练 + 自博弈串行模式，4GB 显卡无压力
3. **社区验证**: KataGomo 社区推荐的中等体量模型，适合消费级显卡
4. **容量翻倍**: 相比 b10c128，policy head 有更大表达空间，有望突破 pacc1 停滞

## Learning Rate Strategy

**lr=0.001 恒定**（基于 KataGo 社区推荐）：
- 256 通道网络在达到极高强度前，恒定高 lr 提供更好正则化
- 如果 loss 震荡，降到 0.0001
- 如果 ploss 长期不下降且死子率升高，降到 0.0001

## Data Pipeline Changes

| 项目 | 旧值 | 新值 | 原因 |
|------|------|------|------|
| sh_samples | 50,000 | **150,000** | 更大模型需要更多样化的训练数据 |
| samples_per_epoch | 50,000 | **150,000** | 匹配 sh_samples，避免浪费 |

当前每轮自博弈 ~800 games 产生 ~2M rows。sh_samples=150K 窗口只用 7.5%，仍有大量数据被丢弃。如果 3 轮验证通过，后续可考虑进一步增大到 300K。

## Experiment Design

### R1: Smoke Test
- 目的：验证 b10c256nbt 训练流程端到端跑通
- 重点：无 OOM、无 NaN、loss 正常下降
- 预期：vloss < 1.2（新模型随机初始化，vloss 初始值约 1.3-1.5）

### R2: Convergence Check
- 目的：验证模型开始从自博弈数据中学习
- 重点：vloss 下降、pacc1 提升
- 预期：vloss < 1.0，pacc1 > 42%

### R3: Promotion Test
- 目的：验证模型能否在 PK 中晋升
- 重点：PK 胜率 > 58%（阈值 0.58）
- 预期：如果 R2 的 vloss < 1.0，R3 有较大概率晋升

## Estimated Time

| 轮次 | 自博弈 | Shuffle | 训练 | PK | 合计 |
|------|--------|---------|------|-----|------|
| R1 | ~20min | ~3min | ~15min | ~10min | ~48min |
| R2 | ~20min | ~3min | ~15min | ~10min | ~48min |
| R3 | ~20min | ~3min | ~15min | ~10min | ~48min |
| **总计** | | | | | **~2.5h** |

注：训练时间基于 dry-run 测量（b10c256nbt batch=64 约 62s/step，150K samples ≈ 2344 steps ≈ 24min/epoch）。实际上下波动取决于 GPU 热节流。

# b10c256nbt Validation Plan - 结论

## 目标
验证 b10c256nbt (6.49M params) 作为 b10c128 (2.96M params) 的升级，在 GTX 1650 Ti (4GB VRAM, 7.7GB RAM WSL2) 上的可行性。

## 实际执行

计划 3 轮，全部完成。每轮从 R1 checkpoint 重新训练。

### R1: Smoke Test
- 自博弈: 400 games, sf_visits=128, sf_threads=8
- 训练: vloss=0.882, pacc1=36.9%, p0loss=2.075
- PK: 0/100 (0%) vs KataGomo b10c128 baseline
- 状态: 训练通过，PK 失败（预期，随机初始化 vs 训练模型）

### R2: 数据不足导致回退
- 自博弈: 320 games（WSL 崩溃后恢复）
- 训练: vloss=0.948 (回退), p0loss=2.201 (回退)
- PK: 跳过（RAM 7.3GB 触发 WSL 崩溃）
- 状态: 失败

### R3: 改善 policy 但 value 回退
- 自博弈: 200 games, sf_visits=64
- 训练: vloss=0.941, pacc1=43.8%, p0loss=1.857
- PK: 0/5 (SPRT 提前终止) vs R1 模型
- 状态: 失败

## 结果

| 指标 | R1 | R2 | R3 | 趋势 |
|------|-----|-----|-----|------|
| vloss | **0.882** | 0.948 | 0.941 | R1 最佳 |
| pacc1 | 36.9% | N/A | **43.8%** | 改善 |
| p0loss | 2.075 | 2.201 | **1.857** | 改善 |
| PK | 0/100 | 跳过 | 0/5 | 全败 |

## 关键发现

1. **VRAM 不是瓶颈**: b10c256nbt 训练仅用 1.3GB VRAM (batch=64)，远低于 4GB 极限
2. **RAM 是真正瓶颈**: PK 阶段 RAM 峰值 7.3GB，接近 WSL2 的 7.7GB 极限，多次触发崩溃
3. **数据量不足**: sh_samples=10K 每轮只产生 1 个训练步，b10c256nbt 的 6.49M 参数需要更多数据
4. **Value head 饱和**: vloss 在 R1 后持续回退，说明 10K rows 的数据窗口太小，value 信号不足
5. **Policy head 有改善**: pacc1 从 36.9% 提升到 43.8%，说明模型在学习落子预测
6. **原始 KataGomo baseline 丢失**: R2 自博弈准备时覆盖了 KataGomo/models/model.bin.gz

## 修复项

1. **PK 任务号机制**: 修复孤儿进程导致的假胜率问题（pk_task_id）
2. **单进程交替颜色 PK**: 合并 sub1/sub2 为单进程，减少模型加载开销
3. **SPRT 提前终止**: 实现序贯概率比检验，极端情况可提前结束 PK
4. **被动监控层**: 集成 StageMetrics 到 automl_cli.py，自动采集资源指标

## 建议

1. **恢复原始 KataGomo baseline**: 从 KataGomo 仓库重新获取 b10c128 baseline
2. **增加数据量**: sh_samples 提到 50K+，需要更多自博弈游戏（800+ games）
3. **考虑 b10c128 继续训练**: b10c256nbt 在当前数据量下可能过大，b10c128 更匹配
4. **降低 PK 资源消耗**: pk_visits=32, pk_games=10 是安全上限

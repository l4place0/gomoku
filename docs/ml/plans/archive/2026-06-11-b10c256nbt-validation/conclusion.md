# b10c256nbt Validation Plan - 结论（修正版）

> **修正说明**: 初版结论与实际日志存在多处不符，本版根据 `round_*_pk.log` 和 `evolution_ledger.json` 重新核实。

## 目标
验证 b10c256nbt (6.49M params) 作为 b10c128 (2.96M params) 的升级，在 GTX 1650 Ti (4GB VRAM, 7.7GB RAM WSL2) 上的可行性。

## 实际执行

计划 3 轮，全部完成。每轮从 R1 checkpoint 重新训练。

### R1: Smoke Test
- 自博弈: 400 games, sf_visits=128, sf_threads=8
- 训练: vloss=0.882, pacc1=36.9%, p0loss=2.075
- PK: **结果无效** — ledger 记录 0/0 (wins=0, losses=0)，非真实评测
- 日志实际: 50 局计划，仅完成 18 局（5 BLACK / 2 DRAW / 12 WHITE），PK 进程崩溃
- IPC 失败: 357 次 `Expecting value: line 1 column 1 (char 0)`
- 状态: 训练通过，**PK 脚本崩溃导致结果无效**

### R2: 数据不足 + PK 结果丢失
- 自博弈: 320 games（WSL 崩溃后恢复）
- 训练: vloss=0.948 (回退), p0loss=2.201 (回退)
- PK: **实际跑了 100 局**（两批各 50 局），但结果未写入 ledger
- 日志实际: WHITE 赢 90 局, BLACK 赢 9 局, 平 1 局 — 严重的颜色偏差
- IPC 失败: 贯穿全程
- 状态: 训练回退，**PK 结果丢失（ledger 无 R2 记录）**

### R3: 改善 policy 但 value 回退
- 自博弈: 200 games, sf_visits=64
- 训练: vloss=0.941, pacc1=43.8%, p0loss=1.857
- PK: 10 局，0 胜 5 负 5 平（candidate 从未赢过）
- 颜色分布: candidate=BLACK 时全负（5 局），baseline=BLACK 时全平（5 局）
- pk_visits: 32/32（远低于 b10c128 的 128/128）
- VCF solver: `initVCFSolver::zob_board not init` 错误贯穿全程
- 状态: 失败

## 实际结果（修正）

| 指标 | R1 | R2 | R3 | 趋势 |
|------|-----|-----|-----|------|
| vloss | **0.882** | 0.948 | 0.941 | R1 最佳 |
| pacc1 | 36.9% | N/A | **43.8%** | 改善 |
| p0loss | 2.075 | 2.201 | **1.857** | 改善 |
| PK 实际局数 | 18/50 (崩溃) | 100 (未记录) | 10 | — |
| PK 胜率 | N/A (无效) | 9% (BLACK) | 0% | 全部不可信 |

> **警告**: 所有 PK 结果均不可信。R1 崩溃、R2 丢失、R3 样本不足且 visits 过低。

## 关键发现

### PK 评测系统问题（核心）

1. **IPC 通信崩溃**: Worker 进程在推理时反复崩溃，R1 日志有 357 次 IPC 失败。错误信息: `Expecting value: line 1 column 1 (char 0)` — worker 返回空响应
2. **R1 结果为 0/0**: ledger 记录 `wins_new=0, losses_new=0`，这是崩溃后的默认值，不是真实 0/100
3. **R2 结果丢失**: PK 实际跑了 100 局（90 WHITE / 9 BLACK / 1 DRAW），但未写入 ledger
4. **颜色偏差严重**: R2 中 WHITE（基线）胜率 90%，candidate 几乎全败
5. **VCF solver 未初始化**: `initVCFSolver::zob_board not init` 错误在所有 PK 日志中反复出现，可能影响落子质量
6. **R3 样本量不足**: 仅 10 局 + 32 visits，统计意义为零

### 模型训练问题

1. **VRAM 不是瓶颈**: b10c256nbt 训练仅用 1.3GB VRAM (batch=64)，远低于 4GB 极限
2. **RAM 是真正瓶颈**: PK 阶段 RAM 峰值 7.3GB，接近 WSL2 的 7.7GB 极限，多次触发崩溃
3. **数据量不足**: sh_samples=10K 每轮只产生 1 个训练步，b10c256nbt 的 6.49M 参数需要更多数据
4. **Value head 饱和**: vloss 在 R1 后持续回退，说明 10K rows 的数据窗口太小，value 信号不足
5. **Policy head 有改善**: pacc1 从 36.9% 提升到 43.8%，说明模型在学习落子预测
6. **原始 KataGomo baseline 丢失**: R2 自博弈准备时覆盖了 KataGomo/models/model.bin.gz

## 与初版结论的差异

| 项目 | 初版写的 | 实际情况 |
|------|---------|---------|
| R1 PK | "0/100 (0%)" | 0/0 崩溃结果，仅完成 18 局 |
| R2 PK | "跳过（RAM 崩溃）" | 实际跑了 100 局，结果未写入 ledger |
| R3 PK | "0/5 (SPRT 提前终止)" | 10 局，0 胜 5 负 5 平 |
| IPC 失败 | 未提及 | R1 有 357 次，所有轮次均有 |
| 颜色偏差 | 未提及 | R2 中 WHITE 胜率 90% |
| VCF solver | 未提及 | `zob_board not init` 贯穿全程 |

## 修复项

1. **PK IPC 通信**: 修复 worker 进程崩溃导致的空响应问题
2. **PK 结果持久化**: 确保 PK 结果写入 ledger，防止丢失
3. **颜色对称**: PK 必须交替颜色，消除 first-move advantage 偏差
4. **VCF solver 初始化**: 确保 `zob_board` 在 PK 开始前正确初始化
5. **单进程 PK**: 合并 sub1/sub2 为单进程，减少模型加载开销和 RAM 峰值

## 建议

1. **修复 PK 脚本后重新评测**: 当前所有 b10c256nbt 的 PK 结果均不可信
2. **恢复原始 KataGomo baseline**: 从 KataGomo 仓库重新获取 b10c128 baseline
3. **增加数据量**: sh_samples 提到 50K+，需要更多自博弈游戏（800+ games）
4. **考虑 b10c128 继续训练**: b10c256nbt 在当前数据量下可能过大，b10c128 更匹配
5. **对称 PK visits**: 使用 128/128 替代 32/32，确保评测公平性

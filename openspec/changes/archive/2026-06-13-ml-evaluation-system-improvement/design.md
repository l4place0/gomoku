## Context

当前 PK 评估系统使用纯阈值判定：`evaluate_promotion(winrate, threshold)` 即 `winrate >= threshold`。这在局数少（30-100 局）时方差大，好模型容易被误杀。同时，学习率调度无记忆机制，DecisionEngine 每轮独立决定 lr，导致成功后 lr 被回调（v4-stabilize r7-8 lr=0.0003 成功，r9 跳回 0.0005 失败）。

硬件约束：GTX 1650 Ti（4GB VRAM），并行流水线已落地（selfplay+train 并行，FP16 启用）。

相关已有变更：
- `fix-pk-and-dual-model`（进行中 2/8）：WorkerClient IPC、VCF solver 修复、颜色偏差修复
- `training-pipeline-optimization`（已完成）：并行化、FP16、异步 shuffle

## Goals / Non-Goals

**Goals:**
- 用 SPRT 替代纯阈值判定，减少误判，支持 early stop
- lr 调度有记忆，成功锁定、失败微降
- PK 结果包含统计显著性指标（置信区间、Elo 估计）
- b10c256nbt 接入 model_registry

**Non-Goals:**
- 不修改 KataGomo C++ DLL
- 不修改 KataGo 的 train.py
- 不引入 Elo rating 系统（只做单次评估的 Elo 估计）
- 不改变并行流水线架构

## Decisions

### Decision 1: SPRT 实现位置

**选择**: 在 `headless_runner.py` 中实现 SPRT early stop，在 `automl_cli.py` 的 `evaluate_promotion()` 中实现 SPRT 判定逻辑

**理由**: headless_runner 负责实际对弈，early stop 需要在对弈过程中判定；evaluate_promotion 负责最终晋升决策，需要基于 SPRT 结果判定。两者分工明确。

**替代方案**: 全部放在 automl_cli — 但这样 early stop 需要 IPC 回调，复杂度高。

### Decision 2: SPRT 参数选择

**选择**: 默认 H0: Elo_diff=0, H1: Elo_diff=35, alpha=0.05, beta=0.05

**理由**: Elo_diff=35 对应约 55% 胜率，与当前 pk_threshold=0.55 对齐。alpha=beta=0.05 是标准显著性水平。这些参数可通过 CLI 覆盖。

**替代方案**: 固定局数 + 置信区间 — 更简单但无法 early stop，局数浪费。

### Decision 3: lr 记忆存储位置

**选择**: 在 model_registry.jsonl 的 params 字段中记录 lr，在 plan_registry.jsonl 中记录 lr 策略

**理由**: 每个模型的 lr 是训练参数的一部分，天然适合存在 params 中。plan 级别的 lr 策略（锁定/微降）存在 plan_registry 中。

**替代方案**: 独立 lr_history.jsonl — 增加文件管理复杂度，且与模型记录分离不直观。

### Decision 4: lr 调度策略

**选择**: 成功晋升 → lr 锁定（不回调）；连续失败 2 次 → lr 乘 0.7；最低不低于 0.0001

**理由**: 成功后锁定防止回调导致失败（v4-stabilize 的教训）。连续失败说明当前 lr 可能过大，微降探索。最低阈值防止 lr 趋零。

**替代方案**: cosine annealing — 需要预设总轮次，不适合开放式训练。

### Decision 5: b10c256nbt 接入方式

**选择**: 在 automl_cli.py 中新增 `--model-kind b10c256nbt` 支持，训练时使用 b10c256nbt 数据目录

**理由**: 当前 automl_cli 硬编码 b10c128，需要参数化。b10c256nbt 数据已在 `ml/data/b10c256nbt_data/` 中。

## Risks / Trade-offs

- **[Risk] SPRT 在小样本下不稳定** → 设置最小局数下限（20 局），低于下限时不做 early stop
- **[Risk] lr 锁定导致探索不足** → 连续失败时 lr 仍会微降，且可通过 plan 手动覆盖
- **[Risk] b10c256nbt VRAM 不够** → 并行模式下 FP16 已省 30% VRAM，需要实测确认；若不够，降 batch size
- **[Trade-off] SPRT 增加复杂度** → 但比固定局数更可靠，且 early stop 节省时间

## Migration Plan

1. SPRT 和 lr 记忆是新增功能，向后兼容，旧 registry 数据可正常读取
2. b10c256nbt 接入需要确认数据目录结构和训练脚本兼容性
3. 依赖 fix-pk-and-dual-model 完成（VCF 修复、颜色偏差修复）

## Open Questions

1. SPRT 的 Elo_diff 默认值 35 是否合适？需要根据历史 PK 数据校准
2. b10c256nbt 在并行模式下的实际 VRAM 占用是多少？
3. fix-pk-and-dual-model 剩余 6 个任务的阻塞点是什么？

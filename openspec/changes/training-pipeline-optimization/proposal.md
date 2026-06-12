## Why

训练流水线每轮耗时 57 分钟（Selfplay 30min + Train 15min + PK 10min + Shuffle/Export 2min），全部阶段严格串行。深度调研报告（report.md）确认：通过 OS 级时间片切分让 selfplay 和 training 并行、启用 FP16 节省 VRAM、异步化 shuffle/export，可将单轮时间降至 ~25 分钟（2.3x 加速）。

## What Changes

- **Selfplay 与 Training 并行**: 将当前串行流水线改为 selfplay 和 training 作为独立进程并行运行在同一个 GPU 上，通过 OS 级时间片切分共享 GPU 资源。[ref:3][ref:4]
- **Shuffle/Export 异步化**: 将 shuffle 和 export 从串行阻塞阶段改为后台持续运行的服务，与 selfplay/train 并行。[ref:33]
- **FP16 混合精度**: 启用 `-use-fp16` 减少 VRAM 占用 ~30-40%，为并行运行腾出 VRAM 预算。[ref:17][ref:20]
- **nnMaxBatchSize 调优**: 通过 benchmark 确定 GTX 1650 Ti 上的最优 nnMaxBatchSize（64/96/128）。[ref:6][ref:8]
- **Policy surprise weighting**: 在 selfplay 配置中启用 policySurpriseDataWeight=0.5，提高数据效率。[ref:28]
- **VRAM 预算管理**: 实现 selfplay 和 training 的 VRAM 预算分配，确保并行时不 OOM。

## Capabilities

### New Capabilities

- `pipeline-parallelism`: 流水线并行化 — selfplay/train 并行、shuffle/export 异步化、VRAM 预算管理
- `fp16-training`: FP16 混合精度训练 — 启用 GradScaler、监控 loss scale、VRAM 节省验证

### Modified Capabilities

- `cli-headless-runner`: automl_cli.py 的流水线控制逻辑从串行改为并行，新增 VRAM 监控和进程管理

## Impact

- `ml/automl_cli.py`: 流水线主逻辑重构 — 串行改并行、新增 VRAM 监控、FP16 参数
- `ml/data/b10c256nbt_data/native_selfplay_15.cfg`: 新增 policySurpriseDataWeight、nnMaxBatchSize 调优
- `ml/run_training_loop.py`: 适配新的并行流水线
- `ml/mlevo_cli.py`: DecisionEngine 适配 FP16 和 batch size 调优逻辑
- `docs/ml/specs/training-knowledge.md`: 记录 FP16 和并行化的经验

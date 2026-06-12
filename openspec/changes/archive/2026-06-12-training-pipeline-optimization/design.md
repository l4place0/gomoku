## Context

当前训练流水线 5 个阶段严格串行：Selfplay(30min) → Shuffle(1min) → Train(15min) → Export(1min) → PK(10min) = 57min/轮。

深度调研报告（report.md）确认：
- OS 级时间片切分在消费级 GPU 上可行，Fulcrum 研究显示 >97% 可靠性 [ref:4]
- NVIDIA MPS 不支持消费级 GPU [ref:32]
- batch size 可安全缩小到 64（无 batch norm 下限）[ref:25]
- FP16 在 GTX 1650 Ti 上无 Tensor Core 加速，但可省 30-40% VRAM [ref:30]
- KataGo 不使用 PyTorch DataLoader，自定义 streaming generator [ref:11]
- Shuffle 可异步后台运行 [ref:33]
- 一轮数据陈旧可容忍 [ref:23]

代码映射（code-report-mapping.md）确认：
- nnMaxBatchSize 当前 = 64（native_selfplay_15.cfg:6）
- FP16 通过 --tr-fp16 参数控制（automl_cli.py:630）
- Shuffle 当前串行执行（automl_cli.py:520-599）
- GPU 环境通过 gpu_env() 设置（automl_cli.py:38-41）

## Goals / Non-Goals

**Goals:**
- 单轮时间从 57min 降到 ~25min
- Selfplay 和 Training 并行运行在同一 GPU 上
- Shuffle/Export 作为后台服务持续运行
- FP16 减少 VRAM 占用，为并行腾出空间
- 实测 nnMaxBatchSize 最优值

**Non-Goals:**
- 不修改 KataGomo C++ DLL
- 不修改 KataGo 的 train.py 或 shuffle.py
- 不引入多 GPU 支持
- 不改变训练质量（loss/胜率应保持或提升）

## Decisions

### Decision 1: OS 级时间片切分（非 MPS）

**选择**: 用标准进程调度实现 selfplay 和 training 并行

**理由**: MPS 不支持消费级 GPU [ref:32]。Fulcrum 研究证明时间片切分在边缘 GPU 上 >97% 可靠 [ref:4]。

**替代方案**: MPS — 不可用；CUDA Unified Memory — 4GB 下会 thrashing [ref:31]。

### Decision 2: VRAM 预算分配

**选择**: Selfplay ~2GB + Training ~2GB 的静态分配

**理由**: 4GB VRAM 总量。nnMaxBatchSize=64 约 1.5GB，FP16 可再省 30%。Training batch=64 约 1.3GB。并行时需要留余量。

**风险**: 未实测验证 [ref:9]。需要 nvidia-smi 监控确认。

### Decision 3: Shuffle/Export 异步化

**选择**: 参考 shuffle_and_export_loop.sh [ref:33]，将 shuffle 和 export 改为后台循环服务

**理由**: 当前 shuffle 和 export 各阻塞 ~1min，合计 ~2min。改为后台服务后可与 selfplay/train 完全重叠。

### Decision 4: FP16 启用策略

**选择**: 先在 selfplay 推理中启用 FP16（cudaUseFP16=true），再在 training 中测试

**理由**: Selfplay 推理对精度要求较低，FP16 风险小。Training 中 GradScaler 可自动处理 NaN [ref:20]，但需要监控。

### Decision 5: nnMaxBatchSize 调优方法

**选择**: 用 benchmark 测试 64/96/128 三个值，选 nnEvals/s 最高的

**理由**: [ref:8] 确认"值大于默认不一定最好"。GTX 1650 Ti 的最优值需要实测。

## Risks / Trade-offs

- **[Risk] VRAM OOM** → 先用 nvidia-smi 实测并行时的 VRAM 占用，设置安全余量
- **[Risk] 时间片切分导致训练变慢** → Fulcrum 显示 7% 吞吐损失 [ref:4]，可接受
- **[Risk] FP16 训练不稳定** → GradScaler 自动处理 [ref:20]，output heads FP32 保底 [ref:18]
- **[Risk] 数据陈旧影响收敛** → 一轮陈旧可容忍 [ref:23]，policy surprise weighting 缓解 [ref:28]
- **[Trade-off] 并行复杂度** → 串行简单可靠，并行需要进程管理和错误恢复

## Open Questions

1. VRAM 实测：selfplay + training 并行时各占多少？
2. nnMaxBatchSize 最优值：64 vs 96 vs 128？
3. FP16 + lr=0.001 是否稳定？
4. 并行时 selfplay 吞吐下降多少？

# 训练流水线工程优化 — 调研报告

## 1. 当前流水线架构

### 1.1 阶段划分

每轮训练包含 5 个严格串行的阶段：

```
Selfplay → Shuffle → Train → Export → PK
  30min     1min     15min    1min    10min   ≈ 57min/轮
```

代码位置: `ml/automl_cli.py` lines 459-765

### 1.2 各阶段详情

| 阶段 | 代码位置 | 耗时 | 瓶颈资源 | 输入 | 输出 |
|------|---------|------|---------|------|------|
| Selfplay | automl_cli.py:459-518 | ~30min | GPU (推理) | 模型权重 + 开局种子 | .npz 游戏数据 |
| Shuffle | automl_cli.py:520-599 | ~1min | CPU + 磁盘 | .npz 文件 | shuffled .npz |
| Train | automl_cli.py:601-649 | ~15min | GPU (训练) | shuffled .npz | checkpoint |
| Export | automl_cli.py:651-699 | ~1min | CPU | checkpoint | .bin.gz 模型 |
| PK | automl_cli.py:701-765 | ~10min | GPU (推理) | candidate + baseline | 胜率结果 |

### 1.3 资源约束

- GPU: GTX 1650 Ti, 4GB VRAM
- RAM: 7.7GB (WSL2 限制)
- 磁盘: SSD
- CPU: 多核（自博弈用 8 线程）

### 1.4 关键配置参数

| 参数 | 当前值 | 作用 |
|------|--------|------|
| sf_games | 200 | 每轮自博弈游戏数 |
| sf_visits | 64 | MCTS 搜索深度 |
| sf_threads | 8 | 自博弈并行线程数 |
| nnMaxBatchSize | 64 | GPU 推理批大小 |
| tr_batch | 64 | 训练批大小 |
| tr_epochs | 1 | 每轮训练 epoch 数 |
| sh_samples | 10000 | shuffle 数据窗口 |
| pk_games | 10 | PK 评测游戏数 |
| pk_visits | 32 | PK 搜索深度 |

## 2. 瓶颈分析

### 2.1 时间分布

```
Selfplay  ████████████████████████████████████████████████████  52% (30min)
Train     ██████████████████████████                            26% (15min)
PK        ██████████████████                                    18% (10min)
Shuffle   ██                                                     2% (1min)
Export    ██                                                     2% (1min)
```

### 2.2 Selfplay 瓶颈

**问题**: 200 games × 64 visits × 8 threads ≈ 30 min

**GPU 利用率分析**:
- nnMaxBatchSize=64 时，GPU 利用率约 50-70%
- KataGo 官方建议 nnMaxBatchSize=256 可达 85-87% 利用率
- 但 256 在 4GB VRAM 上可能 OOM

**游戏并行度**:
- 8 个 game threads 共享 1 个 GPU
- 每个 game 内部是串行的（一步一步下）
- 线程间通过 nnBatchSize 竞争 GPU

**参考**:
- KataGo 官方文档: selfplay 线程数应为 CPU 核心数的 1-2 倍
- GTX 1650 Ti 实测: batch=64 约 16s/step (b10c128), 47-95s/step (b10c256nbt)

### 2.3 Train 瓶颈

**问题**: Step time 47-95s，波动大（热节流）

**数据加载**:
- 当前: 直接从磁盘读取 .npz 文件
- 优化空间: 数据预取 (prefetch)、内存缓存

**批大小**:
- 当前 batch=64，VRAM 约 1.3GB
- 可以尝试 batch=128 (VRAM 约 2.0GB)
- 更大 batch → 更少 step → 更快完成

**FP16**:
- 之前测试 FP16 + lr=0.00025 导致 NaN
- 但 FP16 + lr=0.001 可能可行
- 需要验证

**参考**:
- training-knowledge.md: "b10c256nbt batch=64 约 62s/step"
- training-knowledge.md: "b10c128 约 16s/step"

### 2.4 PK 瓶颈

**问题**: 两个进程竞争 GPU，IPC 通信开销

**当前架构**:
- headless_runner.py: 主进程，加载 DLL 做 BLACK AI
- ai_worker.py: 子进程，加载 DLL 做 WHITE AI
- 两个 DLL 实例共享同一 GPU

**优化空间**:
- WorkerClient 已实现（fix-pk-and-dual-model change）
- 单进程双模型可避免 IPC 开销
- SPRT 提前终止可减少游戏数

### 2.5 串行等待

**最大问题**: 所有阶段严格串行

```
Round N:   [Selfplay]──[Shuffle]──[Train]──[Export]──[PK]
Round N+1:                                              [Selfplay]──...
```

Round N+1 的 Selfplay 必须等 Round N 的 PK 完成，即使两者无数据依赖。

## 3. 优化方案

### 3.1 流水线并行

**原理**: 让不同轮次的阶段重叠执行

```
Round N:   [Selfplay]──[Shuffle]──[Train]──[Export]──[PK]
Round N+1:              [Selfplay]──[Shuffle]──[Train]──...
```

**前置条件**:
- Round N+1 的 Selfplay 可以在 Round N 的 Train 开始后立即启动
- 需要 Round N 的 checkpoint 在 Train 完成后立即可用于 Selfplay
- Round N+1 的 Selfplay 用 Round N 的 checkpoint

**收益**: 一轮时间从 57min 降到 ~35min（Selfplay 与 Train 重叠）

**风险**:
- GPU 竞争: Selfplay 和 Train 同时跑会竞争 GPU
- 数据新鲜度: 用旧 checkpoint 跑 selfplay 可能导致数据分布偏移

**KataGo 参考**:
- KataGo 官方支持异步训练模式
- 大规模训练中，selfplay 和 training 是并行的
- 但 KataGo 用多 GPU，单 GPU 场景需要特殊处理

### 3.2 Partial Data Training

**原理**: 不等全部 selfplay 完成，用部分数据开始训练

```
Round N Selfplay: [===200 games===]
Round N Train:              [===100% data===]
Round N+1 Selfplay:              [===200 games===]  ← 并行
Round N+1 Train:                            [===partial===]  ← 用部分数据
```

**KataGo 支持**:
- train.py 的 `-samples-per-epoch` 控制每 epoch 的样本数
- shuffle.py 的 `-min-rows` 控制最小行数
- 可以设置较低的 `-min-rows` 让 training 更早开始

**收益**: 进一步重叠 Selfplay 和 Train

**风险**:
- 部分数据可能导致训练不稳定
- 需要仔细选择 partial data 的大小

### 3.3 Selfplay 加速

**3.3.1 增大 nnMaxBatchSize**

| nnMaxBatchSize | VRAM 占用 | GPU 利用率 | 预估吞吐提升 |
|---------------|----------|-----------|------------|
| 64 (当前) | ~1.3GB | ~50-70% | 基准 |
| 128 | ~2.0GB | ~70-80% | +20-30% |
| 256 | ~3.5GB | ~85-87% | +40-50% |

**风险**: 4GB VRAM 上 batch=256 可能 OOM，需要实测

**3.3.2 减少 visits**

| visits | 游戏质量 | 时间 | 适用场景 |
|--------|---------|------|---------|
| 32 | 低 | ~15min | 快速验证 |
| 64 (当前) | 中 | ~30min | 常规训练 |
| 128 | 高 | ~60min | 最终评测 |

**权衡**: visits 越低，数据质量越差，但吞吐越高

**3.3.3 游戏级并行**

当前: 8 threads × 1 GPU
优化: 多进程 selfplay，每个进程独立加载模型

**KataGo 参考**:
- 官方 selfplay 配置: `numGameThreads=512`
- 但这是多 GPU 场景
- 单 GPU 上过多线程会导致 GPU 竞争

### 3.4 Train 加速

**3.4.1 数据预取**

当前: 训练时从磁盘读取 .npz
优化: 用 DataLoader 的 prefetch 功能，提前加载下一批数据

**PyTorch 参考**:
- `torch.utils.data.DataLoader(num_workers=N, prefetch_factor=M)`
- 可以用多进程加载数据，不阻塞 GPU 训练

**3.4.2 梯度累积**

当前: batch=64，每个 step 更新一次权重
优化: 梯度累积 N 步，effective batch = 64 × N

**收益**: 更大的 effective batch → 更少 step → 更快完成
**风险**: 需要调整学习率

**3.4.3 FP16**

当前: FP32 训练
优化: FP16 混合精度训练

**已知问题**: FP16 + lr=0.00025 导致 NaN
**可能方案**: FP16 + lr=0.001（需要验证）

**收益**: 训练速度提升 1.5-2x，VRAM 占用减少 50%

### 3.5 PK 加速

**3.5.1 WorkerClient 单进程**

已实现（fix-pk-and-dual-model change），可避免 IPC 开销

**3.5.2 SPRT 提前终止**

已实现，极端情况可提前结束 PK

**3.5.3 减少 PK 游戏数**

| pk_games | 置信区间 | 适用场景 |
|----------|---------|---------|
| 10 | ±30% | 快速筛选 |
| 30 | ±15% | 常规评测 |
| 100 | ±8% | 可靠评测 |

## 4. 关键调研问题

### 4.1 KataGo 训练模式

1. KataGo 的 selfplay 和 training 是否支持单 GPU 并行？
2. train.py 是否支持增量数据加载（不等 shuffle 完成）？
3. nnMaxBatchSize 在 GTX 1650 Ti 上的最大安全值是多少？
4. KataGo 的异步训练模式是如何工作的？

**调研资源**:
- KataGo 官方文档: https://github.com/lightvector/KataGo
- KataGo 训练指南: `KataGomo/docs/training.md`
- KataGo selfplay 配置: `KataGomo/scripts/gomocup/selfplay.cfg`

### 4.2 PyTorch 训练优化

1. DataLoader 的 prefetch 在小数据集上有效吗？
2. 梯度累积对 KataGo 训练有帮助吗？
3. FP16 混合精度在 GTX 1650 Ti 上稳定吗？
4. 如何解决 FP16 + 低学习率的 NaN 问题？

**调研资源**:
- PyTorch DataLoader 文档
- PyTorch AMP (Automatic Mixed Precision) 文档
- KataGo train.py 的 FP16 实现

### 4.3 单 GPU 流水线

1. 单 GPU 上同时跑 selfplay 和 training 的最佳策略是什么？
2. 如何动态分配 GPU 资源给 selfplay 和 training？
3. 是否可以用 CUDA MPS (Multi-Process Service) 来共享 GPU？
4. 流水线并行在单 GPU 上的收益有多大？

**调研资源**:
- NVIDIA CUDA MPS 文档
- KataGo 的 GPU 资源管理
- 单 GPU 流水线并行的研究论文

### 4.4 数据新鲜度

1. 用旧 checkpoint 跑 selfplay 对训练有什么影响？
2. 数据分布偏移会导致什么问题？
3. 如何平衡数据新鲜度和训练稳定性？
4. KataGo 是如何处理数据新鲜度的？

**调研资源**:
- KataGo 的数据窗口管理
- 强化学习中的 off-policy 问题
- 自博弈训练的数据分布分析

## 5. 预期收益

| 优化方案 | 预估收益 | 实现复杂度 | 风险 |
|---------|---------|-----------|------|
| 流水线并行 | -22min/轮 (57→35min) | 高 | GPU 竞争 |
| 增大 nnMaxBatchSize | -5min/轮 | 低 | OOM 风险 |
| 数据预取 | -3min/轮 | 中 | 内存压力 |
| FP16 | -7min/轮 | 中 | NaN 风险 |
| 减少 visits | -10min/轮 | 低 | 质量下降 |
| WorkerClient PK | -2min/轮 | 已实现 | — |

**最佳组合**: 流水线并行 + 增大 nnMaxBatchSize + 数据预取
**预期总收益**: 57min/轮 → 25min/轮 (2.3x 加速)

## 6. 实验计划

### Phase 1: 基准测试 (1天)

1. 测量当前各阶段的精确耗时
2. 测量 GPU 利用率和 VRAM 占用
3. 测量 nnMaxBatchSize=128/256 的可行性和吞吐提升

### Phase 2: 单点优化 (2-3天)

1. 增大 nnMaxBatchSize 到 128 或 256
2. 实现数据预取
3. 测试 FP16 可行性

### Phase 3: 流水线并行 (3-5天)

1. 实现 Selfplay 和 Train 的并行
2. 测试 partial data training
3. 验证数据新鲜度影响

### Phase 4: 集成测试 (2天)

1. 端到端测试优化后的流水线
2. 对比优化前后的训练效果
3. 验证模型质量没有下降

## 7. 参考资料

### 项目内部

- `ml/automl_cli.py`: 训练流水线主逻辑
- `ml/run_training_loop.py`: 多轮训练循环
- `docs/ml/specs/training-knowledge.md`: 训练知识库
- `docs/ml/references/deep-research-report.md`: 深度研究报告
- `ml/benchmark/`: 性能基准测试

### 外部资源

- KataGo 官方仓库: https://github.com/lightvector/KataGo
- KataGo 训练文档: https://katagotraining.org/
- PyTorch DataLoader: https://pytorch.org/docs/stable/data.html
- PyTorch AMP: https://pytorch.org/docs/stable/amp.html
- NVIDIA CUDA MPS: https://docs.nvidia.com/cuda/cuda-c-programming-guide/index.html#mps

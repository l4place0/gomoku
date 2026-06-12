# 训练流水线优化 — 报告与代码双向映射

> 本文件建立深度调研报告 (`report.md`) 与项目实现之间的事实关联。
> 每个映射都包含报告引用、代码位置、当前值、建议值。

## 1. nnMaxBatchSize (GPU 推理批大小)

### 报告 → 代码

| 报告发现 | 代码位置 | 当前值 | 说明 |
|---------|---------|--------|------|
| [ref:6] nnMaxBatchSize 默认约等于 numSearchThreads | `ml/data/b10c256nbt_data/native_selfplay_15.cfg:6` | `nnMaxBatchSize = 64` | 实际使用的配置 |
| [ref:6] 可手动指定防止 OOM | `ml/automl_cli.py:242` | `nnMaxBatchSize = {batch_size}` (fallback 模板) | sync_native_runtime_cfg 函数 |
| [ref:6] JSON 配置路径 | `ml/automl_cli.py:312` | `"nnMaxBatchSize": str(batch_size)` | dict 方式写入 cfg |
| [ref:7] VRAM 与 batch 线性相关 | `KataGomo/scripts/selfplay.cfg:16` | `nnMaxBatchSize = 512` | 上游默认（对我们太大） |
| [ref:8] 值大于默认不一定更好 | `KataGomo/python/scripts/selfplay.cfg:28` | `nnMaxBatchSize = 256` | 上游 Python 配置 |
| [ref:9] T550 在默认 batch 下 OOM | — | — | 验证了 4GB 约束的真实性 |

### 代码 → 报告

```
native_selfplay_15.cfg:6  nnMaxBatchSize = 64
  ← [ref:6] 可手动指定
  ← [ref:7] VRAM 线性 scaling
  ← [ref:9] 小 GPU 需要缩小
  ← [ref:8] 最优值需实测

automl_cli.py:242  nnMaxBatchSize = {batch_size}
  ← [ref:6] 默认约等于 numSearchThreads
  ← [ref:8] genconfig 调优选择最佳 nnEvals/s
```

### 当前状态

- **已优化**: b10c256nbt 配置使用 `nnMaxBatchSize=64`（比上游 256/512 小）
- **待验证**: 是否可以提升到 96 或 128 以提高吞吐

---

## 2. FP16 混合精度训练

### 报告 → 代码

| 报告发现 | 代码位置 | 当前值 | 说明 |
|---------|---------|--------|------|
| [ref:17] `-use-fp16` 创建 GradScaler | `ml/automl_cli.py:630-631` | `if args.tr_fp16: train_cmd.append("-use-fp16")` | 通过 --tr-fp16 参数控制 |
| [ref:17] output heads 保持 FP32 | `KataGomo/cpp/configs/training/selfplay8b20.cfg:123` | `cudaUseFP16 = true` | 上游有 FP16 selfplay 配置 |
| [ref:18] compute capability >= 7 启用 tensor cores | — | GTX 1650 Ti = CUDA 7.5 | 但硬件无 Tensor Core |
| [ref:20] GradScaler init_scale=65536 | — | — | 自动 NaN 检测和 scale 调整 |
| [ref:30] GTX 1650 Ti 无 Tensor Core | — | — | FP16 只省 VRAM，不加速计算 |

### 代码 → 报告

```
automl_cli.py:630-631  if args.tr_fp16: train_cmd.append("-use-fp16")
  ← [ref:17] KataGo 原生支持
  ← [ref:20] GradScaler 自动处理 NaN
  ← [ref:18] output heads FP32 保底
  ← [ref:30] 无 Tensor Core → 只省 VRAM
```

### 当前状态

- **已支持**: automl_cli.py 有 `--tr-fp16` 参数
- **未启用**: training-knowledge.md 记录 FP16 + lr=0.00025 导致 NaN
- **待验证**: FP16 + lr=0.001 是否可行（GradScaler 应能处理）

---

## 3. Shuffle 异步化

### 报告 → 代码

| 报告发现 | 代码位置 | 当前值 | 说明 |
|---------|---------|--------|------|
| [ref:33] shuffle_and_export_loop.sh 后台运行 | `ml/automl_cli.py:520-599` | 串行执行 shuffle | 当前阻塞流水线 |
| [ref:33] shuffle 和 export 并行后台 | `KataGomo/SelfplayTraining.md` | 引用了两种脚本 | 我们用的是串行方式 |
| [ref:34] shuffle 用 multiprocessing.Pool | `ml/automl_cli.py:542-569` | 调用 shuffle.py -num-processes | 正确使用了并行 shuffle |
| [ref:27] taper-window-exponent=0.65 | `ml/automl_cli.py:546` | `-taper-window-exponent` 从 args 读取 | 可配置 |

### 代码 → 报告

```
automl_cli.py:520-599  # STAGE 2: SHUFFLE (串行)
  ← [ref:33] 可改为后台异步运行
  ← [ref:34] shuffle.py 本身支持并行

automl_cli.py:651-699  # STAGE 4: EXPORT (串行)
  ← [ref:33] 可与 shuffle 一起后台运行
```

### 当前状态

- **串行阻塞**: shuffle 和 export 各阻塞 ~1min
- **优化空间**: 改为后台服务，与 selfplay/train 并行

---

## 4. Selfplay 配置

### 报告 → 代码

| 报告发现 | 代码位置 | 当前值 | 说明 |
|---------|---------|--------|------|
| [ref:1] selfplay 应占 4x-40x GPU | `native_selfplay_15.cfg:4` | `numGameThreads = 8` | 8 线程并行 |
| [ref:1] 同步循环串行执行 | `automl_cli.py:459-518` | Selfplay 阶段串行 | 阻塞后续阶段 |
| [ref:24] maxVisits=600 (上游) | `native_selfplay_15.cfg:8` | `maxVisits = 64` | 我们用低 visits 加速 |
| [ref:24] cheapSearchProb=0.75 (上游) | `native_selfplay_15.cfg:9` | `cheapSearchProb = 0.0` | 我们关闭了 cheap search |
| [ref:28] policySurpriseDataWeight=0.5 | `native_selfplay_15.cfg` | 未设置 | 上游有此优化 |
| [ref:28] reduceVisits=true | `native_selfplay_15.cfg` | `reduceVisits = true` | 已启用 |

### 代码 → 报告

```
native_selfplay_15.cfg:4  numGameThreads = 8
  ← [ref:1] selfplay 应占大部分 GPU 时间
  ← [ref:24] 上游用更多线程

native_selfplay_15.cfg:8  maxVisits = 64
  ← [ref:24] 上游默认 600，我们用 64 加速
  ← [ref:28] reduceVisits 可进一步减少

native_selfplay_15.cfg:9  cheapSearchProb = 0.0
  ← [ref:24] 上游用 0.75，我们关闭
```

### 当前状态

- **低 visits**: 64 vs 上游 600，吞吐高但数据质量低
- **无 cheap search**: 关闭了 cheapSearchProb
- **无 policy surprise**: 未设置 policySurpriseDataWeight

---

## 5. 训练参数

### 报告 → 代码

| 报告发现 | 代码位置 | 当前值 | 说明 |
|---------|---------|--------|------|
| [ref:12] KataGo 支持 5 种 optimizer | `automl_cli.py:610-631` | 未指定 optimizer | 使用默认 SGD |
| [ref:12] torch.compile 默认启用 | `automl_cli.py` | 未传 -no-compile | 默认启用 |
| [ref:25] batch size 无下限 (fixup) | `automl_cli.py:619` | `-batch-size {tr_batch}` (64) | 可安全缩小 |
| [ref:15] 学习率需线性 scaling | `mlevo_cli.py:196` | lr 衰减逻辑 | 已实现自适应 lr |

### 代码 → 报告

```
automl_cli.py:610-631  train.py 调用参数
  ← [ref:12] 支持 AdamW/Muon/NorMuon/Aurora
  ← [ref:25] batch size 无下限
  ← [ref:17] -use-fp16 可选

mlevo_cli.py:196  decided["tr_lr"] = max(0.0001, baseline * 0.5)
  ← [ref:15] lr 需随 batch size 线性调整
```

### 当前状态

- **默认 SGD**: 未尝试其他 optimizer
- **batch=64**: 可以尝试更大（如 128）
- **lr 自适应**: 已实现 plateau 检测和衰减

---

## 6. GPU 资源管理

### 报告 → 代码

| 报告发现 | 代码位置 | 当前值 | 说明 |
|---------|---------|--------|------|
| [ref:3] 时间片切分可行 | `automl_cli.py:38-41` | gpu_env() 设置 CUDA_VISIBLE_DEVICES | 当前串行，未并行 |
| [ref:3] 无内存隔离 | `automl_cli.py:482,503,632` | 同一 GPU 传给所有子进程 | 需要手动管理 VRAM |
| [ref:32] nvidia-smi 无 per-process 限制 | — | — | 需要手动监控 |
| [ref:4] Fulcrum: >97% 可靠性 | — | — | 时间片切分的学术依据 |
| [ref:5] MPS 不支持消费级 GPU | — | — | GTX 1650 Ti 无法用 MPS |

### 代码 → 报告

```
automl_cli.py:38-41  gpu_env()
  ← [ref:3] 时间片切分是可行方案
  ← [ref:32] 无法强制 per-process VRAM 限制
  ← [ref:5] MPS 不可用

automl_cli.py:482,503,632  gpu_env(args.gpu)
  ← [ref:3] 所有阶段共享同一 GPU
  ← [ref:4] 并行时需手动管理 VRAM 预算
```

### 当前状态

- **串行执行**: 所有阶段依次使用 GPU
- **未并行**: selfplay 和 training 不重叠
- **优化空间**: 实现时间片切分，并行运行

---

## 7. 数据新鲜度

### 报告 → 代码

| 报告发现 | 代码位置 | 当前值 | 说明 |
|---------|---------|--------|------|
| [ref:22] optimistic policy 不用于 selfplay | — | — | 避免 feedback loop |
| [ref:23] 分布式训练容忍更大陈旧 | — | — | 单 GPU 一轮陈旧可接受 |
| [ref:26] 并行训练新模型直到追上 | — | — | KataGo 的模型切换策略 |
| [ref:28] policy surprise weighting | `native_selfplay_15.cfg` | 未设置 | 可提高数据效率 |

### 代码 → 报告

```
训练流水线 (串行)
  ← [ref:23] 一轮陈旧可容忍
  ← [ref:26] 并行训练策略可参考
  ← [ref:28] policy surprise 可缓解陈旧影响
```

### 当前状态

- **严格串行**: 无数据陈旧问题
- **并行后需关注**: selfplay 用旧 checkpoint 的影响

---

## 8. 关键阻塞项

| 阻塞项 | 报告依据 | 代码位置 | 验证方法 |
|--------|---------|---------|---------|
| VRAM 预算 | [ref:7] 线性 scaling | native_selfplay_15.cfg | nvidia-smi 实测 |
| FP16 稳定性 | [ref:20] GradScaler | automl_cli.py:630 | 跑一轮观察 |
| 时间片切分性能 | [ref:4] Fulcrum | automl_cli.py:38 | 并行跑 selfplay+train |
| nnMaxBatchSize 最优值 | [ref:8] 需实测 | native_selfplay_15.cfg:6 | benchmark 不同值 |

---

## 9. 优化优先级

基于报告依据和代码现状：

| 优先级 | 优化项 | 报告依据 | 代码改动 | 预估收益 |
|--------|--------|---------|---------|---------|
| P0 | Shuffle 异步化 | [ref:33] | automl_cli.py 520-599 | -2min/轮 |
| P0 | FP16 启用测试 | [ref:17][ref:20] | --tr-fp16 参数 | -7min/轮 (估) |
| P1 | nnMaxBatchSize 调优 | [ref:6][ref:8] | native_selfplay_15.cfg | -5min/轮 (估) |
| P1 | 时间片切分 | [ref:3][ref:4] | automl_cli.py 并行化 | -22min/轮 (估) |
| P2 | Policy surprise | [ref:28] | native_selfplay_15.cfg | 数据质量提升 |
| P2 | 其他 optimizer | [ref:12] | train.py 参数 | 待验证 |

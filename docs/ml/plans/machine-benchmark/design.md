# machine-benchmark Design

## Phase 1: 短基准测试

### 测试矩阵

```
Selfplay (sf_games=20 每个配置):
  sf_threads ∈ [2, 4, 8, 12, 16]
  sf_visits  ∈ [64, 96, 128]
  → 15 个组合, 每个 ~2-5 min, 总计 ~45 min

Train (1 epoch 每个配置, 用现有数据):
  tr_batch    ∈ [32, 64, 128]
  sh_samples  ∈ [50K, 100K, 150K]
  → 9 个组合, 每个 ~2-15 min, 总计 ~60 min

PK (10 games 每个配置):
  pk_visits ∈ [64, 128, 256]
  → 3 个配置, 每个 ~2 min, 总计 ~6 min
```

### 采集指标

| 指标 | 采集方式 | 单位 |
|------|---------|------|
| ram_peak | 命令前后 `free` 差值 | GB |
| vram_peak | `nvidia-smi` 最大值 | MiB |
| gpu_util_avg | `nvidia-smi` 平均 | % |
| throughput | games/sec 或 steps/sec | - |
| step_time_p50 | 中位步时 | seconds |
| step_time_p99 | 尾部步时 | seconds |
| wall_time | 实际耗时 | seconds |

### 输出格式

```json
{
  "timestamp": "2026-06-10T12:00:00Z",
  "hardware": {
    "gpu": "GTX 1650 Ti",
    "vram_mb": 4096,
    "ram_gb": 7.7,
    "platform": "WSL2"
  },
  "model": "b10c256nbt",
  "params_count": 6491653,
  "selfplay": {
    "best": {"sf_threads": 8, "sf_visits": 128},
    "results": [
      {"sf_threads": 2, "sf_visits": 64, "ram_gb": 1.8, "vram_mb": 400, "games_per_min": 0.5},
      {"sf_threads": 4, "sf_visits": 64, "ram_gb": 2.2, "vram_mb": 400, "games_per_min": 0.9},
      {"sf_threads": 8, "sf_visits": 64, "ram_gb": 3.0, "vram_mb": 410, "games_per_min": 1.5}
    ]
  },
  "train": {
    "best": {"tr_batch": 64},
    "results": [
      {"tr_batch": 32, "sh_samples": 50000, "vram_mb": 765, "steps_per_sec": 0.027},
      {"tr_batch": 64, "sh_samples": 50000, "vram_mb": 1299, "steps_per_sec": 0.016},
      {"tr_batch": 128, "sh_samples": 50000, "vram_mb": 2043, "steps_per_sec": 0.009}
    ]
  },
  "pk": {
    "best": {"pk_visits": 128},
    "results": [
      {"pk_visits": 64, "vram_mb": 350, "games_per_min": 5.0},
      {"pk_visits": 128, "vram_mb": 400, "games_per_min": 3.0},
      {"pk_visits": 256, "vram_mb": 450, "games_per_min": 1.5}
    ]
  }
}
```

### 测试脚本结构

```
ml/benchmark/
├── run_benchmark.py      # 主入口，编排所有测试
├── collectors.py          # GPU/RAM/CPU 采集器
├── selfplay_bench.py     # 自博弈基准
├── train_bench.py        # 训练基准
├── pk_bench.py           # PK 基准
└── results/              # 输出目录
    └── machine_profile.json
```

## Phase 2: 被动监控

### 嵌入点

在 automl_cli.py 的每个阶段前后插入采集逻辑：

```
Selfplay 阶段:
  前: 记录 ram_before
  后: 记录 ram_after, games_completed, wall_time

Train 阶段:
  每步: 记录 step_time, p0loss, vloss (已有日志，需结构化)
  后: 记录 ram_after, vram_peak

PK 阶段:
  前: 记录 ram_before
  后: 记录 ram_after, wall_time
```

### 输出格式

每次训练追加到 `ml/data/logs/metrics.jsonl`：

```jsonl
{"ts":"2026-06-10T12:00:00Z","round":1,"stage":"train","step":0,"step_time":41.2,"gpu_mem":1299,"gpu_util":98,"p0loss":5.42,"vloss":1.30}
{"ts":"2026-06-10T12:00:41Z","round":1,"stage":"train","step":1,"step_time":37.1,"gpu_mem":1299,"gpu_util":97,"p0loss":5.40,"vloss":1.29}
...
{"ts":"2026-06-10T12:15:00Z","round":1,"stage":"summary","ram_before":2.1,"ram_after":3.4,"vram_peak":1299,"wall_time":900}
```

### 与 DecisionEngine 集成

DecisionEngine 在计算参数时读取 machine_profile.json，输出建议：

```python
class DecisionEngine:
    def __init__(self, baseline_config, history, profile_path=None):
        self.profile = load_profile(profile_path) if profile_path else None

    def decide(self, round_no):
        params = self._compute_params(round_no)
        if self.profile:
            warnings = self._check_against_profile(params)
            # 输出警告但不阻断
        return params, warnings, rationale
```

## 实现计划

| 步骤 | 内容 | 预计时间 |
|------|------|----------|
| 1 | 实现 collectors.py (GPU/RAM 采集) | 10 min |
| 2 | 实现 selfplay_bench.py | 15 min |
| 3 | 实现 train_bench.py | 10 min |
| 4 | 实现 pk_bench.py | 10 min |
| 5 | 实现 run_bench.py (编排) | 10 min |
| 6 | 跑 Phase 1 基准测试 | ~2 hours |
| 7 | 实现被动监控层 (嵌入 automl_cli.py) | 15 min |
| 8 | 集成 DecisionEngine | 10 min |

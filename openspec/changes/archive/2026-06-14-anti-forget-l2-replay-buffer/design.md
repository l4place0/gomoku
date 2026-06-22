# Design: Replay Buffer

## 当前数据流

```
Round N:
  selfplay/ → shuffle (删除旧shuffledddata) → shuffleddata/current/ → train.py
  Round N+1: 数据完全丢弃，重新生成
```

## 设计方案

### 核心思路

在 selfplay 完成后，自动将当前轮数据的子集复制到 `replay_buffer/` 目录。shuffle 阶段同时读取当前轮数据和回放数据，按比例混合。

### 目录结构

```
ml/data/<model_name>/
├── selfplay/              ← 当前轮自弈数据（已有）
├── replay_buffer/         ← 新增：历史数据回放缓冲
│   ├── round_001/         ← 每轮一个子目录
│   │   └── *.npz
│   ├── round_002/
│   └── ...
├── shuffleddata/          ← 已有
└── ...
```

### 回放缓冲管理策略

1. **写入**：selfplay 完成后，从 selfplay/ 中随机采样 `replay_ratio` 比例的数据，复制到 `replay_buffer/round_N/`
2. **容量控制**：保留最近 `replay_max_rounds` 轮的数据，超出的 FIFO 淘汰
3. **读取**：shuffle 阶段传入多个 `-dirs` 参数，KataGo shuffle.py 原生支持

### 参数设计

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--replay-ratio` | 0.2 | 每轮保留 20% 数据到回放缓冲 |
| `--replay-max-rounds` | 5 | 最多保留最近 5 轮回放数据 |

### automl_cli.py 改动点

1. `create_parser()` — 添加 2 个 replay 参数
2. `run_selfplay()` 完成后 — 新增 `_fill_replay_buffer()` 函数
3. `run_shuffle()` — 修改 datadir 传参，混合当前轮 + replay 目录

### shuffle.py 多目录支持

KataGo 的 `shuffle.py` 已支持 `-dirs dir1 dir2 dir3` 多目录输入。只需在构建 shuffle 命令时追加 replay_buffer 的子目录即可。

### 不改动

- `train.py` — 无需修改
- `mlevo_cli.py` — replay 参数通过 plan 注入，无需特殊处理
- `shuffle.py` — 已原生支持多目录

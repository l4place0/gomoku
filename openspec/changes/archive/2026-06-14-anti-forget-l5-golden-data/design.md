# Design: Golden Data Curriculum

## 当前状态

`mine_high_winrate_openings()` 在晋升后从 search_logs.jsonl 挖掘高胜率开局，写入开局库。但这些数据只用于开局选择，不参与训练。

## 设计方案

### 核心思路

扩展现有挖掘函数，同时将高价值位置保存为 NPZ 格式的"黄金数据"，混入训练。

### 目录结构

```
ml/data/<model_name>/
├── curriculum/                    ← 新增
│   ├── golden_positions.jsonl     ← 高价值位置元数据
│   └── golden_data.npz            ← 可直接用于训练的 NPZ
├── selfplay/
└── ...
```

### 数据流

```
search_logs.jsonl
       │
       ▼
mine_golden_positions()
       │
       ├── 高 winrate 开局 → opening_book.json (已有)
       └── 高 policy surprise 位置 → golden_positions.jsonl → golden_data.npz
                                                                      │
shuffle 阶段 ─────────────────────────────────────────────────────────┘
  input_dirs = [selfplay/, replay_buffer/round_*/, curriculum/]
```

### 参数设计

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--golden-min-visits` | 800 | 最低搜索次数 |
| `--golden-surprise-threshold` | 0.3 | policy surprise 阈值 |
| `--golden-max-positions` | 5000 | 最大保留位置数 |

### 代码改动点

1. `ml/automl_cli.py create_parser()` — 添加 golden 参数
2. `ml/automl_cli.py` — 新增 `mine_golden_positions()` 函数（扩展自 mine_high_winrate_openings）
3. `ml/automl_cli.py` — 晋升后调用 `mine_golden_positions()`
4. `ml/automl_cli.py run_shuffle()` — 将 curriculum/ 加入 shuffle 输入目录
5. `ml/data/curriculum/` — 自动创建目录

### 不改动

- `shuffle.py` — 已支持多目录
- `train.py` — 无需修改
- `mlevo_cli.py` — golden 参数通过 plan 注入

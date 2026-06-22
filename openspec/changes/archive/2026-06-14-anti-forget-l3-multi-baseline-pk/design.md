# Design: Multi-Baseline PK Regression Detection

## 当前 PK 流程

```
candidate vs GAME_MODEL_PATH (current best = immediate parent)
  → winrate ≥ threshold → promote
  → winrate < threshold → reject
```

只与 immediate parent 对比，无法检测渐进遗忘。

## 设计方案

### 核心思路

在主 PK 通过后，额外对祖先模型运行回归 PK。用更少局数 + 更宽松阈值，只检测严重遗忘。

### 回归 PK 策略

```
candidate vs parent (主 PK)         → 必须通过，≥ pk_threshold
candidate vs grandparent (回归 PK)  → 必须通过，≥ regression_threshold (0.40)
candidate vs great-grandparent      → 可选，仅在 --pk-regression-depth=3 时
```

### 参数设计

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--pk-regression` | True | 启用回归 PK |
| `--pk-regression-games` | 10 | 回归 PK 局数（少于主 PK） |
| `--pk-regression-threshold` | 0.40 | 回归通过阈值（宽松） |
| `--pk-regression-depth` | 2 | 回归深度（2=到祖父代） |

### 模型定位

1. 主 PK 前，从 ModelRegistry 获取当前 best 的 hash
2. 用 `get_parent_chain()` 获取祖先链
3. 祖父代模型路径：`ml/data/models/{grandparent_hash}.bin.gz`
4. 如果祖先模型文件不存在，跳过该层回归 PK

### 结果记录

回归 PK 结果写入主 PK JSON 输出的 `regression_results` 字段：

```json
{
  "summary": { "candidate_wins": 12, "baseline_wins": 8, ... },
  "regression_results": [
    {"ancestor": "grandparent", "hash": "abc123", "wins": 7, "losses": 3, "winrate": 0.70, "passed": true},
    {"ancestor": "great-grandparent", "hash": "def456", "wins": 5, "losses": 5, "winrate": 0.50, "passed": true}
  ]
}
```

### 代码改动点

1. `ml/automl_cli.py create_parser()` — 添加 4 个 pk-regression 参数
2. `ml/automl_cli.py run_pk()` — 主 PK 通过后，调用 `_run_regression_pks()`
3. 新函数 `_run_regression_pks()` — 遍历祖先，执行回归 PK
4. `ml/model_registry.py` — 新增 `get_ancestor_at_depth(hash, depth)` 便捷方法

### 不改动

- `tools/headless_runner.py` — 已支持任意两个模型对弈
- `ml/mlevo_cli.py` — 回归 PK 参数通过 plan 注入

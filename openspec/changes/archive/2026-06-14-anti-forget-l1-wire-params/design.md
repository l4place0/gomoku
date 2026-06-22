# Design: Wire Anti-Overfitting Parameters

## Current State

`KataGomo/python/train.py` 已实现 4 个防过拟合参数：

| 参数 | 默认值 | 作用 |
|------|--------|------|
| `-max-train-bucket-per-new-data` | 0 (无限制) | 每个新数据行最多训练多少次 |
| `-max-train-bucket-size` | 0 (无限制) | 总训练 bucket 上限 |
| `-stop-when-train-bucket-limited` | false | 到限时自动停止训练 |
| `-no-repeat-files` | false | 不重复使用已训练过的文件 |

`ml/automl_cli.py` 的 `create_parser()` 和 `run_train()` 均未暴露这些参数。

## Design

### automl_cli.py 改动

1. `create_parser()` 添加 4 个参数：
   - `--tr-max-bucket-per-data` (int, default 8)
   - `--tr-max-bucket-size` (int, default 500000)
   - `--tr-stop-when-limited` (store_true, default True)
   - `--tr-no-repeat-files` (store_true, default False)

2. `run_train()` 中构建 train.py 命令时，将这 4 个参数追加到 cmd 列表

### mlevo_cli.py 改动

`DecisionEngine` 的 preset/preset_defaults 中添加合理默认值，确保通过 mlevo 调用时也有这些约束。

### 默认值选择理由

- `max-train-bucket-per-new-data=8`：KataGo 官方推荐值，防止数据被过度训练
- `max-train-bucket-size=500000`：与 KataGo synchronous_loop.sh 一致
- `stop-when-limited=True`：到限后应停止而非继续无效训练
- `no-repeat-files=False`：保守默认，不改变现有行为（可后续开启）

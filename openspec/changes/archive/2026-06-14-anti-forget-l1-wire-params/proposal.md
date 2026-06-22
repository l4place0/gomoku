# anti-forget-l1-wire-params

## Summary

接线 train.py 中已实现但 automl_cli.py 未暴露的防过拟合参数，零代码编写成本，立即生效。

## Motivation

KataGo 官方推荐每个数据点最多训练 8 次（`max-train-bucket-per-new-data=8`），这是防止持续训练中灾难性遗忘的首要措施。当前 `KataGomo/python/train.py` 已完整实现 bucket 系统，但 `ml/automl_cli.py` 未将这些参数接线到 CLI 和训练命令中，导致 200K 数据可能被训练数百 epoch 而无任何限制。

## Scope

- `ml/automl_cli.py` — `create_parser()` 添加 4 个参数，`run_train()` 传递给 train.py
- `ml/mlevo_cli.py` — DecisionEngine 中添加合理默认值
- `training_plan.json` schema — 文档化新参数

## Out of Scope

- train.py 本身不需修改（已有实现）
- shuffle.py 不需修改
- 自弈配置不需修改

## Success Criteria

- `automl_cli.py --help` 显示 4 个新参数
- 训练日志中出现 "bucket limited" 提示（当触发时）
- 默认 `max-train-bucket-per-new-data=8` 与 KataGo 官方一致

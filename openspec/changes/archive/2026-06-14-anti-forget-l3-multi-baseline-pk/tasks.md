# Tasks: Multi-Baseline PK Regression Detection

- [x] 1. `automl_cli.py create_parser()` 添加 `--pk-regression` / `--pk-regression-games` / `--pk-regression-threshold` / `--pk-regression-depth` 参数
- [x] 2. `model_registry.py` 新增 `get_ancestor_at_depth(hash, depth)` 方法
- [x] 3. 实现 `_run_regression_pks()` 函数：遍历祖先执行回归 PK
- [x] 4. `run_pk()` 主 PK 通过后调用 `_run_regression_pks()`，结果写入 PK JSON
- [x] 5. 语法检查验证

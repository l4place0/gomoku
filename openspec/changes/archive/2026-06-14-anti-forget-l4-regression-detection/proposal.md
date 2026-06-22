# anti-forget-l4-regression-detection

## Summary

在 DecisionEngine 中新增 RegressionDetector，自动扫描模型谱系历史，检测性能骤降或渐进退化趋势，并触发回退或参数调整。

## Motivation

当前 DecisionEngine 只处理连续失败（`_count_consecutive_failures`），不检测渐进式遗忘。一个模型可能每轮都通过 PK（winrate 55-60%），但胜率呈持续下降趋势——从 80% 降到 60% 再到 55%。这种"慢遗忘"当前完全不被察觉。结合 Layer 3 的多基线 PK 数据，可以构建更智能的回归检测。

## Scope

- `ml/mlevo_cli.py` — 新增 `RegressionDetector` 类
  - `scan_history(branch, window=5)` — 扫描最近 N 轮 winrate
  - `detect_sudden_drop(threshold=0.15)` — 单轮骤降检测
  - `detect_trend_decline(window=3)` — 连续下降趋势检测
  - `detect_ancestor_regression(current_hash, threshold=0.10)` — 对祖先回归检测
- `ml/mlevo_cli.py` — `cmd_run()` 中在 DecisionEngine 之前调用 RegressionDetector
- `ml/model_registry.py` — 新增 `get_winrate_trend(branch, window)` 辅助方法

## Out of Scope

- 自动回退机制（需人工确认）
- 回归 PK 的执行（属于 Layer 3）

## Success Criteria

- 检测到回归时输出 JSON 告警：`{"regression": true, "type": "trend_decline", "severity": "high"}`
- DecisionEngine 根据回归类型自动降低 lr 或增加 selfplay 量
- 日志中可见回归检测结果

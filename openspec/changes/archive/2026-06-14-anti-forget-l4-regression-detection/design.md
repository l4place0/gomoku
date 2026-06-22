# Design: Performance Regression Detection

## 当前 DecisionEngine

DecisionEngine 只处理：
- 连续失败计数（`_count_consecutive_failures`）
- LR plateau 检测（loss diff < threshold）
- OOM/NaN 恢复

不检测渐进式遗忘——模型可能每轮通过 PK 但 winrate 持续下降。

## 设计方案

### RegressionDetector 类

新增独立类，在 DecisionEngine 之前调用，扫描 history 检测 3 种回归模式：

```python
class RegressionDetector:
    def __init__(self, history, strategy=None):
        self.history = history
        self.strategy = {**DEFAULT_REGRESSION_STRATEGY, **(strategy or {})}

    def detect(self, window=5) -> list[dict]:
        """扫描历史，返回检测到的回归列表"""
        regressions = []
        regressions += self.detect_sudden_drop()
        regressions += self.detect_trend_decline()
        regressions += self.detect_ancestor_regression()
        return regressions
```

### 3 种检测模式

| 模式 | 方法 | 触发条件 | 严重程度 |
|------|------|----------|----------|
| 骤降 | `detect_sudden_drop()` | 单轮 winrate 下降 > 15% | high |
| 趋势下降 | `detect_trend_decline()` | 连续 3 轮 winrate 下降 | medium |
| 祖先回归 | `detect_ancestor_regression()` | 当前 winrate < 祖先平均 winrate - 10% | medium |

### 集成点

在 `cmd_run()` 中，DecisionEngine 之前调用：

```python
detector = RegressionDetector(history)
regressions = detector.detect()
if regressions:
    # 注入回归信息到 DecisionEngine 的 strategy
    strategy["regression_detected"] = regressions
```

DecisionEngine.decide() 中新增回归响应逻辑：
- 检测到 high 回归 → 额外降低 lr（乘以 regression_lr_decay）
- 检测到 medium 回归 → 增加 sf_games（entropy boost 增强）

### 代码改动点

1. `ml/mlevo_cli.py` — 新增 `RegressionDetector` 类（DecisionEngine 之后）
2. `ml/mlevo_cli.py` — `DEFAULT_STRATEGY` 添加回归相关策略参数
3. `ml/mlevo_cli.py` — `cmd_run()` 中在 DecisionEngine 之前调用 RegressionDetector
4. `ml/mlevo_cli.py` — `DecisionEngine.decide()` 中新增回归响应分支
5. `ml/model_registry.py` — 新增 `get_winrate_trend(branch, window)` 辅助方法

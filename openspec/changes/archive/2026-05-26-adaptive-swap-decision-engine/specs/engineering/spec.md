## ADDED Requirements

### Requirement: 三手交换双向相对评分展示
在第 3 手落子后的三手交换抉择关卡，Pygame 侧边栏日志与控制台 SHALL 完整记录并展示双向相对估算分数：不交换保持白棋得分 (`score_white`) 与交换换手执黑得分 (`score_black`)，确保决策过程透明可视。

#### Scenario: 成功记录与展示双向估值日志
- **WHEN** AI 执白在第 3 手评估交换决策
- **THEN** 系统 SHALL 打印 `score_white` 与 `score_black`，并在 UI 日志中展示当前估分详情

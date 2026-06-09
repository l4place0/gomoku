## ADDED Requirements

### Requirement: AI自适应双向博弈价值比较
在进行第 3 手三手交换（Swap2）决策时，AI SHALL 彻底废除硬编码静态分值阈值（如 `AI_SWAP_THRESHOLD = -300`），转而使用动态、自适应的双向博弈相对价值评估决策算法：
1. 评估当前局面下保持执白应对的最大估分 `score_white`。
2. 评估当前局面下换手执黑应对的最大估分 `score_black`。
3. 比较二者，若 `score_black > score_white`，AI SHALL 执行换手决策（换为执黑，人类执白）；否则不换手。

#### Scenario: AI在黑棋大优时进行三手交换
- **WHEN** AI 执白遇到第 3 手，且计算出 `score_black = 1200` 显著高于 `score_white = -1500`
- **THEN** AI SHALL 自动换手执黑，迫使人类换为执白，达成防守策略

#### Scenario: AI在均势或白优时不进行三手交换
- **WHEN** AI 执白遇到第 3 手，且计算出 `score_white = 150` 大于等于 `score_black = -150`
- **THEN** AI SHALL 维持原状不换手，继续执白对局

# 棋力侧 (Game Strength)

> 五子棋领域知识。决定引擎"看得多准"——在给定搜索深度下，能否正确判断局面好坏。

---

## 1. 棋型识别

### 模式匹配
- **文件**: [GameEngine.h](file:///C:/Users/19065/@me/workspace/gomoku/GameEngine.h) `recognizePattern()` L768-837
- **方法**: 将每个方向上的 9 格线段编码为字符串，然后用 `string::find()` 匹配模式

### 线段编码
- **文件**: `getLinePattern()` L747-766
- 以 `(x, y)` 为中心，沿指定方向取 `[-4, +4]` 共 9 个位置
- 编码规则:

| 字符 | 含义 |
|------|------|
| `1` | 己方棋子（或中心点本身） |
| `0` | 空位 |
| `2` | 对方棋子 或 禁手点上的黑子 |
| `B` | 边界 |

### 七种棋型

| 棋型 | 枚举值 | 匹配模式 | 默认分值 |
|------|--------|---------|---------|
| 五连 (FIVE) | 0 | `11111` | 100000 |
| 活四 (FOUR) | 1 | `011110` | 10000 |
| 冲四 (BLOCKED_FOUR) | 2 | `011112`, `211110`, `10111`, `11011`, `11101` | 5000 |
| 活三 (THREE) | 3 | `01110`, `010110`, `011010` | 1000 |
| 眠三 (BLOCKED_THREE) | 4 | `001112`, `211100`, `021110`, `011012` | 500 |
| 活二 (TWO) | 5 | `00110`, `01010`, `01100`, `00110` | 200 |
| 眠二 (BLOCKED_TWO) | 6 | `000112`, `211000`, `021100`, `001102` | 100 |

### 四个方向
- 横 `(1,0)`、竖 `(0,1)`、主对角线 `(1,1)`、副对角线 `(1,-1)`
- 每个棋子在四个方向上分别进行棋型识别，累加得分

---

## 2. 评估函数

### 叶节点评估
- **文件**: [GameEngine.h](file:///C:/Users/19065/@me/workspace/gomoku/GameEngine.h) `evaluate()` L676-700
- **逻辑**:
  1. 遍历所有已落子位置
  2. 己方棋子 → 累加 `evaluateMove()` 到 `scoreCurr`
  3. 对方棋子 → 累加 `evaluateMove()` 到 `scoreEnemy`
  4. 返回 `scoreCurr × ownScale - scoreEnemy × enemyScale`（启用模型时）
  5. 黑方禁手点返回 `-forbiddenPenalty`

### 单子评估
- **文件**: `evaluateMove()` L702-717
- 步骤:
  1. 四个方向分别做棋型识别，累加规则评分
  2. 计算到棋盘中心的曼哈顿距离 `centerDistance`
  3. 调用 `evaluator.scoreMove(stats, neighborCnt, centerDistance, ruleScore)`

### ModelEvaluator 混合评估
- **文件**: [GameEngine.h](file:///C:/Users/19065/@me/workspace/gomoku/GameEngine.h) `ModelEvaluator` L330-421
- **公式**: `finalScore = blend × modelScore + (1-blend) × ruleScore`
- **modelScore 计算**:
  ```
  modelScore = bias
             + Σ(patternCount[i] × patternWeight[i])
             + neighborCnt × neighborWeight
             + (BOARD_SIZE - centerDistance) × centerWeight
  ```

---

## 3. 权重配置

### 配置文件
- **文件**: [model_weights.txt](file:///C:/Users/19065/@me/workspace/gomoku/model_weights.txt)
- **格式**: `key=value`，`#` 开头为注释

### 当前权重值

| 参数 | 值 | 含义 |
|------|-----|------|
| `blend` | 0.70 | 模型评分 vs 规则评分的混合比例 |
| `bias` | 0 | 模型评分基础偏移 |
| `own_scale` | 1.00 | 己方总评分缩放系数 |
| `enemy_scale` | 1.08 | 对方总评分缩放系数 (>1 = 偏防守) |
| `center_weight` | 8 | 中心距离权重 |
| `neighbor_weight` | 18 | 邻居数量权重 |
| `forbidden_penalty` | 100000 | 禁手惩罚分 |
| `pattern.five` | 100000 | 五连权重 |
| `pattern.four` | 12500 | 活四权重 |
| `pattern.blocked_four` | 6200 | 冲四权重 |
| `pattern.three` | 1450 | 活三权重 |
| `pattern.blocked_three` | 620 | 眠三权重 |
| `pattern.two` | 260 | 活二权重 |
| `pattern.blocked_two` | 120 | 眠二权重 |

### 加载机制
- `ModelEvaluator::load()` 读取文件，逐行解析 `key=value`
- 加载成功后 `enabled = true`，混合评估生效
- 加载失败则 `enabled = false`，退回纯规则评分（使用 `patternScore[]` 硬编码值）

---

## 4. 禁手判定

### 禁手规则 (Renju)
- **仅对黑方生效**
- **三种禁手**: 长连（六子及以上）、三三、四四
- **五连不是禁手**: 黑方恰好五子连线为胜

### 实现
- **文件**: [GameEngine.h](file:///C:/Users/19065/@me/workspace/gomoku/GameEngine.h) L839-870
- **依赖**: KataGomo 的 `CForbiddenPointFinder`（来自 `KataGomo/cpp/forbiddenPoint/`）
- `isForbiddenPoint(x, y)`: 创建临时 `CForbiddenPointFinder`，同步棋盘状态后判定
- `refreshForbiddenPointsAround(x, y)`: 每次落子/撤销后，更新半径 5 范围内所有空位的禁手标记

### 禁手在评估中的影响
- 走法生成时排除禁手点（黑方）
- `evaluate()` 中遇到禁手点的黑子返回 `-forbiddenPenalty`
- 棋盘渲染时禁手点显示红色 × 标记

---

## 5. 胜负判定

### 检查逻辑
- **文件**: [GameEngine.h](file:///C:/Users/19065/@me/workspace/gomoku/GameEngine.h) `checkWin()` L88-116
- 四个方向计算连线长度
- **黑方**: 恰好 5 子连线才算胜（长连为禁手，不胜）
- **白方**: ≥ 5 子连线即胜

---

## 6. 评估体系总结

```
                    evaluateMove(pos, role)
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
         4方向棋型识别   邻居计数     中心距离
         Σ count×score  neighborCnt  centerDist
              │            │            │
              └────────────┼────────────┘
                           ▼
                    ModelEvaluator.scoreMove()
                    blend×model + (1-blend)×rule
                           │
                           ▼
                    evaluate(role)
                    Σ己方 × ownScale - Σ对方 × enemyScale
                           │
                           ▼
               applyKataRootBlend() (根节点)
               ab×(1-vBlend) + kata_value×vBlend + kata_policy×pBlend
```

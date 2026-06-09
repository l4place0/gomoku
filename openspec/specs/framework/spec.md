# 框架层 (Framework)

> 通用博弈搜索框架。决定引擎"能看多远、搜得多快"。这些机制不依赖五子棋领域知识，理论上可移植到其他棋类。

---

## 1. 搜索算法

### NegaMax Alpha-Beta
- **文件**: [GameEngine.h](file:///C:/Users/19065/@me/workspace/gomoku/GameEngine.h) `negaMax()` L642-660
- **算法**: NegaMax 框架 + Alpha-Beta 剪枝
- **递归终止**: 到达当前设定的 `maxDepth` 时调用 `evaluate(role)` 返回叶节点评分

```
negaMax(depth, alpha, beta, role):
    if 置换表命中 → 返回缓存值
    if depth == maxDepth → 返回 evaluate(role)
    for move in genMoves(role):
        doMove(move, role)
        alpha = max(alpha, -negaMax(depth+1, -beta, -alpha, opponent))
        undoMove(move, role)
        if alpha >= beta → Beta 截断，返回
    return alpha
```

### 迭代加深
- **文件**: [GameEngine.h](file:///C:/Users/19065/@me/workspace/gomoku/GameEngine.h) `getBestMoves()` L200-271
- 从 `depth=1` 到 `CurrentMaxDepth` 逐层加深搜索
- 每层完成后按 `moveScore` 排序所有候选着法
- 超时（`MAX_TIME_MS`）时跳出到 `TIMEOUT_EXIT`

### 搜索深度自适应
- **文件**: [GameEngine.h](file:///C:/Users/19065/@me/workspace/gomoku/GameEngine.h) `decideSearchDepth()` L632-640
- 根据已落子数 (`turn`) 动态决定最大搜索深度：

| 已落子数 | 最大深度 | 阶段 |
|---------|---------|------|
| ≤ 4 | 2 | 开局 |
| ≤ 8 | 4 | 初期 |
| ≤ 14 | 6 | 中期 |
| ≤ 22 | 8 | 中后期 |
| > 22 | MAX_DEPTH (20) | 终局 |

### 时间控制
- **常量**: `MAX_TIME_MS = 100000` (100 秒)
- 在迭代加深的每个候选着法前检查已用时间，超时则终止

---

## 2. 置换表 (Transposition Table)

### Zobrist 哈希
- **文件**: [GameEngine.h](file:///C:/Users/19065/@me/workspace/gomoku/GameEngine.h) 构造函数 L879-891
- 初始化: `mt19937_64` 为每个 `board[i][j]` 生成两个 64 位随机数（黑/白各一个）
- 落子/撤销时 XOR 更新 `zobristHash`

### 哈希表
- **数据结构**: `unordered_map<unsigned long long, HashItem>` L432
- **HashItem 字段**:
  - `depth`: 搜索深度
  - `score`: 评分
  - `bestMove`: 最佳着法（当前未使用）
  - `flagType`: EXACT / ALPHA / BETA

### 查询逻辑
- **文件**: `probeHashHIt()` L662-674
- 命中条件: 存在且 `hi.depth <= depth`（注意：此处逻辑是深度更浅的缓存可被更深的搜索使用）
- EXACT → 直接返回
- ALPHA → 若 `score <= alpha` 则返回 alpha
- BETA → 若 `score >= beta` 则返回 beta

### 清理
- 每次 `getBestMoves()` 结束后调用 `clearHashTable()` 全量清空

---

## 3. 走法生成与排序

### 走法生成
- **文件**: [GameEngine.h](file:///C:/Users/19065/@me/workspace/gomoku/GameEngine.h) `genMoves()` L729-745
- **筛选条件**: `board[i][j].role == NONE && neighborCnt > 0 && 非禁手点(黑方)`
- 即只考虑已有棋子邻居的空位（半径1范围内有棋子）

### 邻居计数
- `board[i][j].neighborCnt`: 半径 1 内已有棋子的数量
- 落子时 +1，撤销时 -1
- 用于走法生成的过滤和排序的次级指标

### 走法排序
- **搜索内部**: `genMoves()` 对每个候选调用 `evaluatePoint(pos, role)` → `evaluateMove()` 计算评分，按评分降序排列
- **根节点**: `getBestMoves()` 中迭代加深后，按 `moveScore` 降序排列，同分时按 `neighborCnt` 降序

---

## 4. 搜索统计

### MoveData 结构
- **文件**: [GameEngine.h](file:///C:/Users/19065/@me/workspace/gomoku/GameEngine.h) L295-324
- 每次 `getBestMoves()` 调用时重置

| 字段 | 含义 |
|------|------|
| `searchCnt` | 总搜索节点数 |
| `hashHitCnt` | 置换表命中次数 |
| `betaCutCnt` | Beta 截断次数 |
| `maxDepth` | 实际达到的最大深度 |
| `thinkingTimeInMs` | 总思考时间 (ms) |

### 搜索日志 JSON
- **文件**: `buildLastSearchLogJson()` L566-629
- 记录完整搜索元数据 + Top10 候选的详细评分（alphaBeta / kataPolicy / kataValue / final）
- 通过 DLL 接口 `GetLastSearchLogJson()` 暴露给 Python

---

## 5. 当前参数汇总

```
MAX_DEPTH         = 20          # 最大搜索深度上限
MAX_TIME_MS       = 100000      # 搜索超时 (100秒)
INF               = 1e9         # Alpha-Beta 初始窗口
UNK               = 1e9 + 1     # 置换表未命中标记
neighborUpdateR   = 1           # 邻居更新半径
BOARD_SIZE        = 15          # 棋盘大小
```

---

## 6. 已知局限与改进方向

> 以下为当前状态的客观记录，非行动项。

- **无 Aspiration Window**: 迭代加深每层都用 `[-INF, INF]` 全窗口搜索
- **无 Move Ordering Heuristic**: 没有 killer move、history heuristic 等
- **无 Null Move Pruning / LMR**: 未使用任何高级剪枝技术
- **置换表无容量限制**: `unordered_map` 无大小约束，每次搜索后全量清空
- **走法生成无分级**: 所有候选等价评估，未区分"必须看"和"可以跳过"的着法
- **HashItem.bestMove 未使用**: 存储了但查询时未用于走法排序


---

## 7. 2026-05 Hybrid Opening Book & Search Fusion (New Requirements)

### Requirement: 动态三层走法排序套件
系统 SHALL 在 Alpha-Beta 搜索中引入动态走法排序。在生成候选走法后，系统 SHALL 对其进行动态评分并重新排序，具体规则如下：
1. **Hash Move 具有最高优先级**（如果走法与置换表中命中记录的 `bestMove` 相同，得分赋予 `10,000,000`）。
2. **Killer Move 具有次高优先级**（如果走法与该深度的杀手走法 `killerMoves[depth][0]` 或 `killerMoves[depth][1]` 相同，得分赋予 `9,000,000` 或 `8,000,000`）。
3. **History Heuristic 具有动态叠加权重**（将静态模式评估评分与全局历史剪裁得分 `historyScore[x][y]` 叠加，合并区间为 `[0, 1,000,000]`）。

### Requirement: 杀手启发与历史剪裁数据沉淀
系统 SHALL 在 `negaMax` 搜索产生 Beta 剪裁（`alpha >= beta`）时，自动沉淀战术数据：
1. 系统 SHALL 将当前走法存入当前深度的杀手着法缓存 `killerMoves[depth]` 中（最多保存 2 个非重复着法）。
2. 系统 SHALL 在全局历史评分表上对当前着法进行加权累加：`historyScore[move.x][move.y] += (depth + 1) * (depth + 1)`。

### Requirement: NegaMax Alpha-Beta 搜索与置换表回填
系统 SHALL 在 `negaMax` 递归搜索时，在置换表哈希项 `HashItem` 中完整保存并利用 `bestMove`（最佳着法）。当发生 Beta 剪裁或正常搜索返回时，系统 SHALL 将产生最佳得分（或引发剪裁）的走法与对应的 `Flag`（ALPHA / BETA / EXACT）一并写入该节点的置换表。

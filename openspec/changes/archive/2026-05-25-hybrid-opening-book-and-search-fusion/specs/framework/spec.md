## ADDED Requirements

### Requirement: 动态三层走法排序套件
系统 SHALL 在 Alpha-Beta 搜索中引入动态走法排序。在生成候选走法后，系统 SHALL 对其进行动态评分并重新排序，具体规则如下：
1. **Hash Move 具有最高优先级**（如果走法与置换表中命中记录的 `bestMove` 相同，得分赋予 `10,000,000`）。
2. **Killer Move 具有次高优先级**（如果走法与该深度的杀手走法 `killerMoves[depth][0]` 或 `killerMoves[depth][1]` 相同，得分赋予 `9,000,000` 或 `8,000,000`）。
3. **History Heuristic 具有动态叠加权重**（将静态模式评估评分与全局历史剪裁得分 `historyScore[x][y]` 叠加，合并区间为 `[0, 1,000,000]`）。

#### Scenario: 置换表着法排在首位
- **WHEN** 搜索进入特定节点，且置换表命中记录中存在有效的最佳着法 `bestMove = (7, 8)`
- **THEN** 排序算法 SHALL 将着法 `(7, 8)` 排在候选走法队列的绝对第一位优先搜索

---

### Requirement: 杀手启发与历史剪裁数据沉淀
系统 SHALL 在 `negaMax` 搜索产生 Beta 剪裁（`alpha >= beta`）时，自动沉淀战术数据：
1. 系统 SHALL 将当前走法存入当前深度的杀手着法缓存 `killerMoves[depth]` 中（最多保存 2 个非重复着法）。
2. 系统 SHALL 在全局历史评分表上对当前着法进行加权累加：`historyScore[move.x][move.y] += (depth + 1) * (depth + 1)`。

#### Scenario: 发生剪裁时自动记录杀手与历史分
- **WHEN** 搜索在深度 4 发生 Beta 剪裁，剪裁走法为 `(6, 6)`
- **THEN** 系统 SHALL 将 `(6, 6)` 存入 `killerMoves[4][0]`，并对 `historyScore[6][6]` 累加 `25` 分

---

## MODIFIED Requirements

### Requirement: NegaMax Alpha-Beta 搜索与置换表回填
系统 SHALL 在 `negaMax` 递归搜索时，在置换表哈希项 `HashItem` 中完整保存并利用 `bestMove`（最佳着法）。当发生 Beta 剪裁或正常搜索返回时，系统 SHALL 将产生最佳得分（或引发剪裁）的走法与对应的 `Flag`（ALPHA / BETA / EXACT）一并写入该节点的置换表。

#### Scenario: 成功写入并回填置换表最佳着法
- **WHEN** 节点搜索结束，最佳走法为 `(7, 7)`，返回的局势评分为精确得分
- **THEN** 系统 SHALL 创建 `Flag::F_EXACT` 的哈希项，将 `bestMove` 设为 `(7, 7)`，写入 `hashTable[zobristHash]`

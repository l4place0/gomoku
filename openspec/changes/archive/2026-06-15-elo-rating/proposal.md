# elo-rating

## Summary

引入 Elo/Bradley-Terry 评分系统替代 raw winrate，使 PK 决策基于统计稳健的 MLE 评分。复用已有的 `KataGomo/python/elo.py` 作为后端，四阶段渐进式集成。

## Motivation

当前 PK 只用 `wins/total` 计算 winrate，20 局 PK 中 ~10% 标准误差导致晋升/淘汰决策不稳定。代码库已有两套 Elo 代码未被利用：
- `ml/sprt.py`: `winrate_to_elo()` / `elo_to_winrate()` 转换 + SPRT
- `KataGomo/python/elo.py`: 855 行完整 MLE Elo，Gauss-Newton 优化，支持 Bayesian 先验和先手优势建模

研究结论（见 `docs/research/elo-rating-integration.md`）：复用 KataGomo 的 MLE 方案优于引入 openskill.py，因为已有代码、支持先手优势、支持稀疏图正则化。

## Scope

- **Phase 1 数据收集**：PK 后记录 pairwise 结果到 `elo_history.json`，不影响现有逻辑
- **Phase 2 离线计算**：基于 KataGomo/python/elo.py 批量计算 Elo 排名 + 置信区间
- **Phase 3 辅助晋升**：Elo diff + CI 作为晋升决策的补充信号
- **Phase 4 DAG 集成**：分支对比、全局排名

## Success Criteria

- PK JSON 输出包含 `elo_diff`, `ci_lower`, `ci_upper`
- 晋升判定基于 Elo diff > 0（且置信区间不含 0）
- 多分支模型可按 Elo 排名

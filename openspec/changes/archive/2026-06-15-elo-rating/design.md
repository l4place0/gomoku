## Context

当前 PK 流水线用 raw winrate（wins/total）做晋升决策，20 局 PK 的标准误差约 10%，导致：
- 有效改进被误判为退化（假阴性）
- 微弱退化被误判为改进（假阳性）
- 回归检测依赖硬编码阈值（0.15 突降、0.10 低于祖先均值），对小样本脆弱

代码库已有两套 Elo 代码：
- `ml/sprt.py`: 轻量级 Elo 转换 + SPRT，已集成到 headless_runner
- `KataGomo/python/elo.py`: 855 行 MLE Elo，Gauss-Newton 优化，支持 Bayesian 先验、先手优势建模、协方差矩阵

关键发现：headless_runner 已输出 per-color wins（candidate_black_wins 等），可直接用于先手优势建模。

## Goals / Non-Goals

**Goals:**
- 累积所有 PK 的 pairwise 比较数据，构建全局比较图
- 用 KataGomo/python/elo.py 计算 MLE Elo ± stderr
- 输出包含 elo_diff, ci_lower, ci_upper 的结构化结果
- 支持先手优势估计（P1 advantage）
- 与现有流水线向后兼容（Phase 1 零侵入）

**Non-Goals:**
- 不替换 SPRT 早停机制（SPRT 继续用于实时终止决策）
- 不引入 openskill.py 外部依赖
- 不修改游戏引擎或自弈逻辑
- 不实现在线增量 Elo 更新（批量计算即可）

## Decisions

### D1: 复用 KataGomo/python/elo.py 而非 openskill.py

**选择**: 以 KataGomo/python/elo.py 为 Elo 计算后端

**理由**:
- 已在项目中，零依赖成本
- MLE + Gauss-Newton 比 Weng-Lin 近似更精确（尤其小样本）
- 内置 `P1_ADVANTAGE_NAME` 支持先手优势建模
- `make_sequential_prior` 解决稀疏图正则化
- `make_center_elos_prior` 锚定群体均值
- Fisher 信息矩阵提供精确协方差/置信区间

**备选方案**: openskill.py（Weng-Lin Bayesian）— 为多人匹配设计，无先手优势建模，需新增外部依赖

### D2: 四阶段渐进式集成

```
Phase 1: 数据收集     ─ 零风险，只记录
Phase 2: 离线计算     ─ 低风险，只读取+可视化
Phase 3: 辅助晋升决策 ─ 中风险，补充信号
Phase 4: DAG 集成     ─ 分支对比
```

**理由**: 每阶段独立可交付，前一阶段为后一阶段提供数据，任何阶段可暂停而不损失已有价值

### D3: 数据格式 — JSONL pairwise records

**存储**: `ml/data/elo_history.jsonl`

每行一条 PK 记录：
```json
{
  "candidate": "a1b2c3d4e5f6",
  "baseline": "f6e5d4c3b2a1",
  "candidate_wins": 12,
  "baseline_wins": 8,
  "candidate_black_wins": 7,
  "candidate_white_wins": 5,
  "baseline_black_wins": 4,
  "baseline_white_wins": 4,
  "round": 15,
  "branch": "mainline",
  "timestamp": "2026-06-14T23:00:00Z"
}
```

**理由**:
- 与 model_registry.jsonl 格式一致（JSONL 行式追加）
- per-color wins 支持 P1 advantage 建模
- 保留 round/branch 元数据用于 DAG 关联
- 候选/基线双方 hash 都记录，支持双向查询

### D4: Elo 计算策略 — 批量重算而非增量

每次调用 `compute_elos()` 时从 elo_history.jsonl 全量重算，而非增量更新。

**理由**:
- 数据量小（每轮 1 条记录，~20 局），全量计算 <100ms
- 避免增量更新的数值漂移问题
- 简化实现，易于调试和验证
- KataGomo 的 `compute_elos()` 本身就是批量接口

### D5: 先手优势建模

利用 headless_runner 已输出的 per-color wins，将 PK 结果拆分为两条记录：
- candidate 作为 P1（黑）: candidate_black_wins vs baseline_white_wins
- candidate 作为 P2（白）: candidate_white_wins vs baseline_black_wins

配合 `make_single_player_prior(P1_ADVANTAGE_NAME, num_games=10, elo=0)` 估计先手优势。

**理由**: 五子棋先手优势显著，不建模会导致 Elo 估计偏斜

### D6: 比较图正则化

同时使用两个先验：
1. `make_sequential_prior(players_by_round, num_games=10)` — 相邻轮次模型预期相近
2. `make_center_elos_prior(all_players, elo=0)` — 锚定群体均值

**理由**: 研究表明两者组合足以锚定任意稀疏图（KataGomo elo.py docstring line 440）

## Risks / Trade-offs

| 风险 | 严重度 | 缓解措施 |
|------|--------|----------|
| 稀疏比较图导致 MLE 不稳定 | 中 | sequential_prior + center_elos_prior 正则化 |
| 20 局 PK 的 Elo 置信区间较宽 | 低 | 多轮累积后有效样本量增长，CI 收窄 |
| 先手优势估计需要足够样本 | 低 | 每轮 20 局拆分后各有 ~10 局，50+ 轮后稳定 |
| Phase 3 改变晋升逻辑可能引入回归 | 中 | Phase 3 为可选，保留旧逻辑作为 fallback |
| 模型重训后 hash 变化但语义连续 | 低 | sequential_prior 处理相邻版本关系 |

## Migration Plan

1. **Phase 1 部署**: 只在 run_pk() 末尾追加写 elo_history.jsonl，不改变任何输出
2. **回填历史**: 从 evolution_ledger.json 提取已有 PK 结果，生成 elo_history.jsonl 初始数据
3. **Phase 2 部署**: 新增 CLI 命令 `python -m ml.elo_rating compute`，独立运行不影响流水线
4. **Phase 3 部署**: 在 evaluate_promotion() 中添加 Elo CI 检查，默认关闭，配置开启
5. **回滚**: 每阶段可独立回滚，Phase 1 回滚 = 删除 elo_history.jsonl 追加逻辑

## Open Questions

- Elo 计算的 `num_games` 参数（sequential_prior 强度）需要多少？建议从 10 开始实验
- Phase 3 的晋升阈值：Elo diff > 0 且 CI 不含 0，还是设定具体 Elo 阈值？
- 是否需要定时重算 Elo（如每天/每 N 轮），还是每次 PK 后立即重算？

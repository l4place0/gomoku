# 🧠 Gomoku ML Training Knowledge Spec

This document details the persistent hyperparameter rules, constraints, and guardrails for KataGomo training on GTX 1060 6GB.

## 🏁 Recommended Hyperparameter Sweet Spots

| Parameter | Recommended Range | Description |
|---|---|---|
| `sf_games` | **500 - 1500** | Selfplay games per round. Balancing loop throughput and sample diversity. |
| `sf_visits` | **96 - 128** | Number of MCTS search visits. Use lightweight search to expedite selfplay. |
| `sh_samples` | **150,000 - 300,000** | Size of the rolling data window for shuffling and training. |
| `tr_lr` | **0.001 - 0.002** | Learning rate. Decay dynamically if training loss plateaus. |
| `tr_batch` | **64 - 96** | Training batch size optimized for GTX 1060 VRAM limits. |
| `pk_games` | **20 - 50** | Evaluation games in the PK arena to determine promotion. |

## 🛡️ Guardrails and Hard Constraints

Any evolution plan parameters MUST satisfy the following strict minimum thresholds to ensure meaningful training:

- **Selfplay Games (`sf_games`)**: `sf_games >= 100` (Suggested: `>= 500`)
- **PK Arena Games (`pk_games`)**: `pk_games >= 20`
- **Shuffled Samples (`sh_samples`)**: `sh_samples >= 50000` (Suggested: `>= 150000`)
- **Learning Rate (`tr_lr`)**: `tr_lr >= 0.0005` (FP16 floor: 0.00025 causes NaN underflow with b10c128)
- **Batch Size (`tr_batch`)**: `tr_batch >= 16`

## 🔄 Adaptive Evolution Rules

1. **Adaptive Learning Rate Decay**: If the training loss difference across epochs in the previous round is `< 0.05` (plateau), multiply the learning rate by `0.5` (floor to `0.0001`).
2. **Entropy Boost**: If the candidate model fails promotion (`promoted: false`), increase the next round's `sf_games` by `20%` and `sf_visits` by `+16` over the stage baseline to explore a broader state space.
3. **Crash Recovery**: 
   - **Out of Memory (OOM)**: Reduce `tr_batch` by half.
   - **NaN Loss**: Rollback to the previous round's model weights and halve `tr_lr`.

## 🧠 Insights from gtx1650ti-b10c128-10round (2026-06-07)

The completed 10-round evolution plan on GTX 1650 Ti (4GB VRAM, WSL2) yielded critical operational insights:

1. **FP16 NaN Threshold at Low LR**:
   - lr=0.00025 triggered NaN in both rounds 9 and 10 (27+ NaN occurrences each).
   - lr=0.0005 was stable across rounds 6-8. **Set lr floor to 0.0005 for FP16 b10c128 training.**
   - Root cause: FP16 underflow when gradients become too small at very low learning rates.

2. **SWA as NaN Shield**:
   - Even with mid-training NaN bursts, SWA (Stochastic Weight Averaging) preserved valid weights.
   - Validation metrics remained normal (p0loss=1.82, pacc1=47.8%) despite 27 NaN occurrences during training.
   - Always use `-use-swa` for export to recover from NaN episodes.

3. **Promotion Rate and Best Model**:
   - 4 promotions in 10 rounds (40%). Best model at round 7 (80.6% winrate, pacc1=44.2%).
   - Later rounds (8-10) failed to promote despite higher pacc1 — the champion model became too strong to beat.
   - Suggests longer training plans (>10 rounds) may yield diminishing returns without architectural changes.

4. **Selfplay Throughput (GTX 1650 Ti)**:
   - 400 games × 64 visits × 32 threads ≈ 45 min, ~925k rows
   - 600 games × 112 visits × 32 threads ≈ 70 min, ~1.5M rows
   - 960 games × 144 visits × 32 threads ≈ 180 min, ~3.1M rows
   - Scaling is roughly linear with `games × visits`.

5. **PK Draw Rate Tracks Model Strength**:
   - Early rounds: ~0% draws. Peak at round 8: 42.5% draws (17/40).
   - High draw rates indicate models are evenly matched — consider increasing pk_games to get sufficient decided games.

6. **lr Decay Chain**:
   - Started at 0.002 (warmup) → 0.001 (stage 2 plateau) → 0.0005 (plateau) → 0.00025 (plateau, NaN).
   - The DecisionEngine plateau detection (Δloss < 0.05) was too sensitive for late-stage fine-tuning where improvements are naturally small.

7. **Training Crash Recovery Protocol**:
   - Round 5 crash (p0loss=215): lr too high (0.002) after accumulated data. Fixed by stage 2 lr=0.001 + checkpoint rollback.
   - Rounds 9-10 NaN: lr too low (0.00025). Fixed by SWA export, but checkpoint rollback still recommended.
   - **Always keep checkpoint_prev* backups — they saved rounds 6 and 10.**

8. **Data Window Management**:
   - Cumulative data grew from 925k (R1) to 3.2M (R10) rows per selfplay round.
   - Shuffle window of 30k samples with exponential decay (0.8 exponent) effectively managed recency bias.
   - sh_samples=30k was adequate given the window function, despite being below the 50k guardrail.

## 🧠 Insights from v3-anti-overfit (2026-06-08)

The 5-round anti-overfitting plan validated the hypothesis that reducing epochs and increasing learning rate prevents overfitting:

1. **Anti-Overfitting Strategy Confirmed**:
   - `tr_epochs=1` (vs R8-R10's 3 epochs) + `tr_lr=0.001` (vs 0.00025) = 60% promotion rate
   - R8-R10 had 0% promotion rate with epochs=3, lr=0.00025
   - Key insight: more epochs on similar data causes memorization, not learning

2. **NaN Recovery Works**:
   - Round 2 triggered NaN detection → DecisionEngine reduced lr from 0.001 to 0.0005
   - Rounds 3-4 recovered with high winrates (61.5%, 96.7%)
   - NaN recovery is a valid strategy, not just a safety net

3. **Opening Randomization Effective**:
   - 30 balanced seeds in `opening_seeds.json`
   - Each selfplay round uses a different opening
   - No code changes needed, just config

4. **Best Model at Round 4 (96.7% winrate)**:
   - Highest winrate achieved in any plan so far
   - Suggests 4-5 rounds is optimal for anti-overfit training
   - Round 5 failed (43.3%) — model may have saturated

5. **Recommended Parameters for Next Plan**:
   - `tr_epochs`: 1 (always)
   - `tr_lr`: 0.001 (start), let DecisionEngine adjust on NaN
   - `sf_games`: 400-600
   - `sf_visits`: 96
   - `pk_games`: 30

## 🧠 Insights from v4-stabilize (2026-06-09)

The 7-round stabilization plan fixed critical infrastructure bugs and validated model-data alignment:

1. **Checkpoint running_metrics NaN 是真正的 NaN 根因**:
   - FP16 不是 NaN 的根本原因 — FP32 + 脏 checkpoint 仍然 NaN
   - 真正根因：`running_metrics["sums"]` 包含 NaN，lookahead optimizer 用这些值计算 SWA 权重
   - 模型权重和 optimizer state 都正常，但 running_metrics 的 NaN 通过 SWA 传播
   - **修复**：训练 log 含 `p0loss=nan` 时自动清除 checkpoint

2. **模型与数据必须同源**:
   - R1-R3：主线 checkpoint + v3 自博弈数据 → 持续恶化（43%→40%→22%）
   - R5 起：对齐 checkpoint 与自博弈模型 → 立即回升（64.6%）
   - 用 A 模型 checkpoint + B 模型数据训练，效果比两者都差

3. **100 局 PK 比 30 局可靠得多**:
   - 30 局置信区间 ±15%，100 局 ±8%
   - v3 R4 的 96.7%（30 局）很可能是噪声
   - **建议**：pk_games >= 100 用于可靠评估

4. **阶段切换需要渐进**:
   - R5→R6 从 stage1（lr=0.0005, sf=600）切到 stage2（lr=0.0003, sf=800）
   - R6 突然退化到 33.3%，R7 才恢复到 73%
   - **建议**：阶段切换时保持 lr 不变，只增加数据量

5. **哈希碰撞修复**:
   - `compute_model_hash` 只看文件内容 → 训练未改变权重时碰撞
   - **修复**：注册时混合 `file_hash + round + branch + timestamp`

6. **最佳参数组合**:
   - `tr_epochs=1`, `tr_lr=0.0005`, `sf_games=600`, `sf_visits=96`, `pk_games=100`
   - 81% 胜率（R8），从 v3 R3（61.5%）提升 20 个百分点

## 🧠 Insights from gtx1060-b10c128-evolution (2026-05-28)

The completed 5-round evolution plan on a local GTX 1650 Ti GPU provided critical operational insights:

1. **Saturating GPU via `nnMaxBatchSize = 256`**:
   - For lightweight networks like `b10c128` (approx. 2.96M parameters, consuming only ~11MB of VRAM), small batch sizes like 64 severely underutilize the GPU.
   - Increasing `nnMaxBatchSize` to **256** successfully saturates GPU CUDA cores (raising utilization to **~85-87%**) without causing Out of Memory (OOM) errors on 4GB VRAM cards. This maximizes self-play search throughput.
2. **Optimal Thread Count (`sf_threads = 4`)**:
   - On standard desktop CPUs, maintaining `sf_threads = 4` prevents excessive thread-context switching and CPU scheduling friction while providing a continuous stream of batches to the GPU.
3. **Weight Promotion Guardrail**:
   - The Round 4 candidate achieved an outstanding **75.00% winrate** in the PK Arena, proving that the adaptive parameter adjustments (SWA, LR decays) are highly effective.
   - The Round 5 candidate scored exactly **50.00% winrate**, which triggered the $\ge 55\%$ promotion guardrail and prevented regression, demonstrating the robustness of the headless PK evaluation logic.


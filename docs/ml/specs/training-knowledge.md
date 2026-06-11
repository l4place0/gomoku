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

## 🧠 Insights from v4-stabilize R9-R10 (2026-06-10)

The 2-round follow-up plan validated lr=0.0005 + epochs=2 and exposed critical PK evaluation bugs:

1. **PK 评估缓存 bug 导致假胜率**:
   - `automl_cli.py` PK 失败时不清理旧 `pk_sub*.json`，误读 R8 缓存结果
   - R8 的 81%、R9 的 81%、R10 的 81% 全部是假数据（同一个 JSON 文件）
   - **修复**: PK 运行前强制删除旧 JSON；永远检查 PK 日志确认评估真正执行
   - **教训**: PK 胜率数字不可盲信，必须验证 pk_sub*.json 时间戳和 PK 日志内容

2. **workspace reorg 后 4 个路径 bug**:
   - `mlevo_cli.py`: subprocess 缺少 `cwd=str(BASE_DIR)` → automl_cli.py 找不到
   - `headless_runner.py`: `from ml.verify_opening_book` import 失败（ml 包不在 path）
   - `ai_worker.py`: 路径安全检查用 `BASE_DIR`（tools/）拒绝 ml/data/ 下的模型路径
   - `automl_cli.py`: PK 失败时读取旧 JSON 缓存
   - **教训**: 目录重组后必须跑一次完整 PK 端到端验证

3. **lr=0.0005 + epochs=2 有效但需累积**:
   - R9: 48.84% 未晋升（从 R8 checkpoint 重新训练，vloss 0.911）
   - R10: 72.92% 晋升（从 R9 checkpoint 继续，vloss 0.886 — 分支最低值）
   - 两轮累积训练后模型真实超越 R8 基线
   - **建议**: lr=0.0005 + epochs=2 需要至少 2 轮才能见效

4. **对称 pk_visits 消除颜色偏差**:
   - 修复前: 执黑 50-0 全胜，执白 0-50 全负（128/64 不对称 visits）
   - 修复后 R10: 执白 38-8-4，执黑 32-18-0（128/128 对称 visits）
   - **建议**: pk_visits_b 和 pk_visits_w 必须相等

5. **最佳参数组合 (v4-stabilize)**:
   - `tr_epochs=2`, `tr_lr=0.0005`, `sf_games=800`, `sf_visits=128`, `sh_samples=50000`
   - `pk_games=100`, `pk_visits_b=128`, `pk_visits_w=128`, `pk_threshold=0.58`
   - R10 真实胜率 72.92%（vloss 0.886，pacc1 49.7%）

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

## 🧠 Insights from b10c256nbt-validation (2026-06-11)

The 3-round validation of b10c256nbt (6.49M params) on GTX 1650 Ti (4GB VRAM, 7.7GB RAM WSL2) revealed critical constraints:

1. **VRAM is NOT the bottleneck**:
   - b10c256nbt training (batch=64): peak VRAM 1.3GB, well within 4GB limit
   - b10c256nbt training (batch=128): peak VRAM 2.0GB, still safe
   - Dry-run confirmed: batch=64 recommended, batch=128 possible

2. **RAM IS the bottleneck (WSL2 crash risk)**:
   - PK stage: RAM peak 7.3GB / 7.7GB WSL2 limit → multiple WSL crashes
   - Root cause: headless_runner.py loads two model copies (DLL + subprocess)
   - **Safe PK limit: pk_games=10, pk_visits=32** (RAM ~5GB)
   - **Dangerous: pk_games=100, pk_visits=96** (RAM 7.3GB, crash risk)

3. **Data volume critical for larger models**:
   - sh_samples=10K produced only 1 training step per round
   - b10c256nbt's 6.49M params need 50K+ rows to learn effectively
   - R1 (best): vloss=0.882, pacc1=36.9%
   - R2/R3 (10K rows): vloss regressed to 0.941-0.948

4. **Value head saturation at low data**:
   - vloss improved in R1 (0.882) but regressed in R2/R3
   - Policy head improved: pacc1 36.9% → 43.8%
   - Model learns policy but overfits value at 10K rows

5. **Selfplay throughput (b10c256nbt, sf_visits=64)**:
   - 200 games × 64 visits × 8 threads ≈ 30 min
   - ~40% slower than b10c128 at same visits

6. **Training throughput (b10c256nbt, batch=64)**:
   - Step time: 47-95s (thermal throttling)
   - ~4x slower than b10c128 (16s/step)

7. **PK engineering improvements implemented**:
   - Single-process alternating colors (replaces two sub-rounds)
   - SPRT early termination (stops when result is decisive)
   - Task ID for PK output files (prevents orphan conflicts)
   - Passive metrics collector (StageMetrics in automl_cli.py)

8. **Recommended parameters for b10c256nbt**:
   - `tr_batch`: 64 (safe), 128 (possible)
   - `tr_lr`: 0.001 (KataGo community recommendation)
   - `sh_samples`: 50000+ (minimum for effective learning)
   - `sf_games`: 800+ (sufficient data per round)
   - `sf_visits`: 64-96 (throughput vs quality tradeoff)
   - `pk_games`: 10-30 (RAM safe)
   - `pk_visits`: 32 (RAM safe)


# Design: v2-stable-recovery

## Model Architecture

- **Model kind**: `b10c128` (~2.96M params, 10 blocks, 128 channels)
- **Board size**: 15x15 (single-size, FREESTYLE)
- **Optimizer**: Lookahead (alpha=0.5, k=6) + FP16 training
- **Loss weights**: soft_policy_weight_scale=8.0, value_loss_scale=0.6, td_value_loss_scales=[0.6, 0.6, 0.6]

## Hardware Constraints

- **GPU**: NVIDIA GeForce GTX 1650 Ti (4GB VRAM, compute 7.5)
- **Batch size**: 64 (fits comfortably in 4GB for b10c128)
- **Selfplay threads**: 32 (CPU-bound, proven effective in Round 6)

## Parameters Rationale

### Selfplay (sf_*)

| Param | Recovery (R7-9) | Scale-up (R10-12) | Convergence (R13-14) | Rationale |
|-------|-----------------|--------------------|-----------------------|-----------|
| sf_games | 600 | 800 | 1000 | More games = more diverse data |
| sf_visits | 112 | 128 | 128 | Round 4's sweet spot; 128 showed no regression with proper training |
| sf_threads | 32 | 32 | 32 | Fixed — Round 6 proved this works |

### Training (tr_*)

| Param | Recovery (R7-9) | Scale-up (R10-12) | Convergence (R13-14) | Rationale |
|-------|-----------------|--------------------|-----------------------|-----------|
| tr_lr | 0.002 | 0.0015 | 0.001 | Gradual decay; Round 4 proved 0.002 works |
| tr_batch | 64 | 64 | 64 | Fixed for 1650 Ti |
| tr_epochs | 1 | 1 | 1 | **Critical**: 2 epochs caused Round 6 overfitting |
| sh_samples | 30000 | 30000 | 30000 | Keep consistent |

### PK Arena (pk_*)

| Param | Recovery (R7-9) | Scale-up (R10-12) | Convergence (R13-14) | Rationale |
|-------|-----------------|--------------------|-----------------------|-----------|
| pk_games | 50 | 50 | 60 | More games = more statistical power |
| pk_visits_b | 128 | 128 | 128 | Fixed baseline search |
| pk_visits_w | 64 | 64 | 64 | Fixed challenger search |
| pk_threshold | 0.55 | 0.55 | 0.55 | Standard per deep research report |

## Key Design Decisions

1. **Single epoch only**: Round 6 proved that 2 epochs on the same data causes overfitting without proportional strength gain. All stages use tr_epochs=1.

2. **Gradual LR decay**: Instead of jumping from 0.002 to 0.001, we decay by 0.0005 per stage. This avoids the sharp regression seen in Round 6.

3. **Increasing game volume**: sf_games grows from 600→800→1000 to provide more diverse training data as the model gets stronger and selfplay quality improves.

4. **Thread count fixed at 32**: Round 6's throughput (760 games/hr) was healthy. No need to change.

## Risk Mitigation

- If Round 7 fails promotion: keep Recovery params for Round 8 (don't escalate)
- If 2 consecutive failures: consider switching to b6c96 for a fresh restart
- If OOM: reduce tr_batch to 32
- Monitor vloss for overfitting signals (vloss increasing while p0loss decreasing)

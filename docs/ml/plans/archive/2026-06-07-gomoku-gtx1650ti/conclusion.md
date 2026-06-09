# Conclusion: gomoku-gtx1650ti

Archived Date: 2026-06-07 00:28:16

## Performance Summary
- **Total Rounds**: 10
- **Promotions**: 4 / 10 (40.00%)

## Round by Round Execution Results
- **Round 1**: Winrate 90.91% | Promoted: YES | Games: 30 (Baseline sf_games: 400)
- **Round 2**: Winrate 50.00% | Promoted: NO | Games: 30 (Baseline sf_games: 400)
- **Round 3**: Winrate 70.00% | Promoted: YES | Games: 30 (Baseline sf_games: 480)
- **Round 4**: Winrate 40.00% | Promoted: NO | Games: 30 (Baseline sf_games: 400)
- **Round 5**: Winrate 35.71% | Promoted: NO | Games: 30 (Baseline sf_games: 480)
- **Round 6**: Winrate 72.50% | Promoted: YES | Games: 40 (Baseline sf_games: 720)
- **Round 7**: Winrate 80.56% | Promoted: YES | Games: 40 (Baseline sf_games: 600)
- **Round 8**: Winrate 52.17% | Promoted: NO | Games: 40 (Baseline sf_games: 600)
- **Round 9**: Winrate 34.15% | Promoted: NO | Games: 50 (Baseline sf_games: 960)
- **Round 10**: Winrate 54.00% | Promoted: NO | Games: 50 (Baseline sf_games: 960)

## Persisted Hyperparameters and Suggestions

### Key Lessons
1. **lr floor = 0.0005** for FP16 b10c128 — 0.00025 causes NaN underflow
2. **SWA saved models from NaN** — always export with `-use-swa`
3. **Best model at round 7** (80.6% winrate, pacc1=44.2%, p0loss=1.98)
4. **Entropy boost works**: R3 (70%) and R6 (72.5%) both promoted after boost
5. **Stage 3 refinement (rounds 9-10)** failed to produce promotions despite higher pacc1
6. **Checkpoint rollback protocol** saved rounds 6 and 10 from corrupted weights
7. **Total compute**: ~31 hours on GTX 1650 Ti, 10 rounds, 6,380 selfplay games, ~19M training rows

### Recommended Next Plan
- Start from round 7 best model weights
- Use lr=0.001 with cosine schedule instead of plateau-based halving
- Increase model capacity (b10c256 or b15c128) for next evolution stage
- PK games: increase to 60+ for high-draw-rate scenarios

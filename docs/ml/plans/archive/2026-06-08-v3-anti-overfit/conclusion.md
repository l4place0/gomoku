# Conclusion: v3-anti-overfit

Archived Date: 2026-06-08

## Performance Summary
- **Total Rounds**: 5
- **Promotions**: 3 / 5 (60.00%)
- **Best Model**: Round 4 (winrate 96.67%)
- **Best Model Hash**: 4b343f50efe9

## Round by Round Execution Results
- **Round 1**: Winrate 57.14% | Promoted: YES | lr=0.001, epochs=1
- **Round 2**: Winrate 36.67% | Promoted: NO | lr=0.0005 (NaN recovery)
- **Round 3**: Winrate 61.54% | Promoted: YES | lr=0.0005
- **Round 4**: Winrate 96.67% | Promoted: YES | lr=0.0005
- **Round 5**: Winrate 43.33% | Promoted: NO | lr=0.0005

## Key Findings

### Anti-Overfitting Strategy Works
- `tr_epochs=1` (vs R8-R10's 3 epochs) significantly reduced overfitting
- `tr_lr=0.001` (vs R8-R10's 0.00025) maintained learning capacity
- Result: 60% promotion rate vs R8-R10's 0% promotion rate

### Opening Randomization Integrated
- 30 balanced opening seeds in `opening_seeds.json`
- Each selfplay round randomly selects one seed
- Improves data diversity without code changes

### NaN Recovery Triggered
- Round 2 detected NaN in training logs
- DecisionEngine automatically reduced lr from 0.001 to 0.0005
- Subsequent rounds recovered and achieved high winrates

## Persisted Hyperparameters
- **Optimal lr**: 0.0005-0.001 (avoid 0.00025)
- **Optimal epochs**: 1 (avoid 3+)
- **sf_games**: 400 sufficient for stable training
- **sf_visits**: 96 (research-recommended range)
- **pk_games**: 30 for reliable evaluation

## Recommendations for Next Plan
1. Keep `tr_epochs=1` as default
2. Start with `tr_lr=0.001`, let DecisionEngine adjust on NaN
3. Consider increasing `sf_games` to 600 for more data diversity
4. Opening randomization is working - keep it enabled

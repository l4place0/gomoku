## 1. Phase 1: Data Collection

- [x] 1.1 Create `ml/elo_tracker.py` with `EloTracker` class: append pairwise PK results to `ml/data/elo_history.jsonl`
- [x] 1.2 Define JSONL schema: candidate, baseline, candidate_wins, baseline_wins, per-color wins, round, branch, timestamp
- [x] 1.3 Modify `ml/automl_cli.py:run_pk()` to call `EloTracker.record()` after each PK round (after SPRT result available)
- [x] 1.4 Skip recording when auto-promote (no baseline / winrate=1.0)
- [x] 1.5 Create backfill utility `ml/elo_tracker.py:backfill_from_ledger()` to extract historical PK data from `evolution_ledger.json`
- [x] 1.6 Run backfill and verify `elo_history.jsonl` contains expected records
- [x] 1.7 Add unit tests for EloTracker: record serialization, append-only, skip auto-promote

## 2. Phase 2: Offline Elo Computation

- [x] 2.1 Create `ml/elo_rating.py` with `EloRatingEngine` class wrapping KataGomo/python/elo.py
- [x] 2.2 Implement `compute_all()`: read elo_history.jsonl, build Likelihood objects via `likelihood_of_games()`, call `compute_elos()`
- [x] 2.3 Implement P1 advantage modeling: split per-color wins into P1/P2 Likelihood records with `include_first_player_advantage=True`
- [x] 2.4 Add `make_sequential_prior()` on models ordered by round within each branch (num_games=10)
- [x] 2.5 Add `make_center_elos_prior()` to anchor population mean at Elo 0
- [x] 2.6 Implement `get_pairwise_diff(candidate, baseline)`: return elo_diff, ci_lower, ci_upper from covariance matrix
- [x] 2.7 Create CLI `python -m ml.elo_rating compute` with `--json` option
- [x] 2.8 Add unit tests for EloRatingEngine: mock PK data, verify Elo output, verify CI computation
- [x] 2.9 Manual validation: run on backfilled data, compare Elo rankings with raw winrate trends

## 3. Phase 3: Elo-Guided Promotion

- [x] 3.1 Modify `evaluate_promotion()` in `ml/automl_cli.py` to accept optional Elo params (elo_diff, ci_lower, ci_upper)
- [x] 3.2 Add Elo CI check: log warning when winrate passes but CI includes 0
- [x] 3.3 Modify `run_pk()` to call `EloRatingEngine.get_pairwise_diff()` and include Elo fields in PK output JSON
- [x] 3.4 Add Elo fields to `evolution_ledger.json` entries (elo_diff, ci_lower, ci_upper)
- [x] 3.5 Add Elo-based regression detection to `RegressionDetector` in `ml/mlevo_cli.py`: Elo drop > 50 = high severity
- [x] 3.6 Add unit tests for updated evaluate_promotion() with Elo parameters
- [x] 3.7 Verify backward compatibility: when no elo_history exists, behavior unchanged

## 4. Phase 4: DAG Integration

- [x] 4.1 Add `elo` field to `ModelRecord` in `ml/model_registry.py` (optional, default None)
- [x] 4.2 After Elo computation, update ModelRecord entries with their Elo ratings
- [x] 4.3 Add `get_elo_ranking()` method to `ModelRegistry`: return all models sorted by Elo
- [x] 4.4 Add branch-level Elo comparison to `ml/dag_engine.py`: average Elo per branch
- [x] 4.5 Add `--elo-rank` option to CLI for viewing global Elo rankings across branches

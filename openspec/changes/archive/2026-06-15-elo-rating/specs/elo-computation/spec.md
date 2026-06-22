## ADDED Requirements

### Requirement: Compute MLE Elo ratings from pairwise data
The system SHALL compute maximum-likelihood Elo ratings for all models using KataGomo/python/elo.py's `compute_elos()` function.

#### Scenario: Compute Elo for all registered models
- **WHEN** `elo_rating compute` is invoked
- **THEN** it reads all records from `elo_history.jsonl`, constructs Likelihood objects via `likelihood_of_games()`, applies priors, and calls `compute_elos()` to produce EloInfo for all models

#### Scenario: Output includes Elo and stderr
- **WHEN** Elo computation completes
- **THEN** for each model the output includes: hash, Elo rating, standard error, effective game count

### Requirement: Support first-player advantage estimation
The system SHALL model first-player advantage by splitting per-color wins into separate Likelihood objects with `include_first_player_advantage=True`.

#### Scenario: P1 advantage from per-color data
- **WHEN** PK data includes candidate_black_wins=7, baseline_white_wins=3 (candidate as P1)
- **THEN** two Likelihood records are created: one for candidate-as-P1 winning 7/10, one for baseline-as-P2 winning 3/10, both tagged with P1_ADVANTAGE_NAME

#### Scenario: P1 advantage prior
- **WHEN** computing Elos with first-player advantage enabled
- **THEN** a `make_single_player_prior(P1_ADVANTAGE_NAME, num_games=10, elo=0)` is included to anchor the advantage estimate

### Requirement: Apply regularization priors for sparse graphs
The system SHALL apply both sequential and center priors to ensure numerical stability on the sparse comparison graph.

#### Scenario: Sequential prior on training lineage
- **WHEN** models are ordered by round number within each branch
- **THEN** a `make_sequential_prior()` with num_games=10 is applied between adjacent models

#### Scenario: Center prior on all models
- **WHEN** computing Elos
- **THEN** a `make_center_elos_prior(all_players, elo=0)` is applied to anchor the population mean

### Requirement: CLI command for offline Elo computation
The system SHALL provide a CLI command `python -m ml.elo_rating compute` that reads elo_history.jsonl and outputs Elo rankings.

#### Scenario: Default output format
- **WHEN** `python -m ml.elo_rating compute` runs
- **THEN** it prints a table sorted by Elo descending, with columns: hash, elo, stderr, effective_games

#### Scenario: JSON output option
- **WHEN** `python -m ml.elo_rating compute --json` runs
- **THEN** it outputs a JSON array of model rankings with elo, stderr, ci_lower (Elo - 1.96*stderr), ci_upper (Elo + 1.96*stderr)

### Requirement: Pairwise Elo difference with confidence interval
The system SHALL compute Elo difference and 95% confidence interval between any two models.

#### Scenario: Candidate vs baseline Elo diff
- **WHEN** Elo computation completes for a PK pair
- **THEN** the output includes elo_diff = Elo(candidate) - Elo(baseline), ci_lower, ci_upper computed from the covariance matrix

#### Scenario: Confidence interval from covariance
- **WHEN** computing CI for Elo difference
- **THEN** the CI uses the full covariance matrix: stderr_diff = sqrt(var_p1 + var_p2 - 2*cov_p1_p2), CI = elo_diff ± 1.96 * stderr_diff

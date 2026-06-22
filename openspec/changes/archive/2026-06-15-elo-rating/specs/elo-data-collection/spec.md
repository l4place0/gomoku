## ADDED Requirements

### Requirement: Record pairwise PK results after each evaluation
After each PK round completes, the system SHALL append a pairwise result record to `ml/data/elo_history.jsonl`.

#### Scenario: Normal PK round completes
- **WHEN** `run_pk()` finishes and produces a summary with candidate_wins, baseline_wins, and per-color wins
- **THEN** a JSON line is appended to `elo_history.jsonl` containing: candidate hash, baseline hash, win counts (total and per-color), round number, branch name, and ISO 8601 timestamp

#### Scenario: PK round with SPRT early stop
- **WHEN** SPRT triggers early termination after fewer than planned games
- **THEN** the record is still appended with the actual completed game counts (not planned counts)

#### Scenario: First PK round (no baseline)
- **WHEN** no current best model exists and candidate auto-promotes with winrate=1.0
- **THEN** no record is appended (no pairwise comparison occurred)

### Requirement: JSONL format for elo_history
Each line in `elo_history.jsonl` SHALL be a valid JSON object with the following fields:
- `candidate` (string): SHA256 hash of candidate model
- `baseline` (string): SHA256 hash of baseline model
- `candidate_wins` (int): total wins by candidate
- `baseline_wins` (int): total wins by baseline
- `candidate_black_wins` (int): wins by candidate when playing black (P1)
- `candidate_white_wins` (int): wins by candidate when playing white (P2)
- `baseline_black_wins` (int): wins by baseline when playing black (P1)
- `baseline_white_wins` (int): wins by baseline when playing white (P2)
- `round` (int): training round number
- `branch` (string): branch name
- `timestamp` (string): ISO 8601 timestamp

#### Scenario: Record serialization
- **WHEN** a PK result is recorded
- **THEN** the JSON line is valid JSON and contains all required fields

#### Scenario: Append-only file
- **WHEN** multiple PK rounds complete
- **THEN** `elo_history.jsonl` contains one line per PK round, appended in chronological order

### Requirement: Backfill historical PK data
The system SHALL provide a utility to extract historical PK results from `evolution_ledger.json` and populate `elo_history.jsonl`.

#### Scenario: Backfill from existing ledger
- **WHEN** the backfill utility runs on an existing `evolution_ledger.json`
- **THEN** it generates `elo_history.jsonl` entries for all rounds that have PK data with win counts

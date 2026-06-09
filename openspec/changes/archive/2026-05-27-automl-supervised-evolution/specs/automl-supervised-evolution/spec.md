## ADDED Requirements

### Requirement: Orchestrated Execution and Parameter Mapping
The system SHALL support executing the entire machine learning evolution round through a single entry point `automl_cli.py`, which maps CLI arguments to the parameters of the self-play, shuffle, train, export, and PK stages.

#### Scenario: Running single round with custom arguments
- **WHEN** the user runs `uv run python automl_cli.py --round 1 --sf-games 10 --tr-lr 0.001 --pk-games 2`
- **THEN** the system SHALL execute exactly 10 selfplay games, run data shuffle, train PyTorch model with learning rate 0.001, export the model weights, and execute exactly 2 PK games, writing structured high-level summary progress to standard output.

### Requirement: Complete Evidence Chain and Logger Split
The system SHALL print a complete, clear, structured "Parameter Evidence Chain" detailing all input hyperparameters at the start of each round, and redirect all verbose sub-process logs (stdout and stderr) to specific files under the `logs/` directory.

#### Scenario: Checking log redirection and evidence chain output
- **WHEN** `automl_cli.py` is invoked with valid arguments
- **THEN** the system SHALL print a formatted parameter mapping block to stdout, and verify that all detailed outputs from child processes are successfully written to `logs/round_{round}_selfplay.log`, `logs/round_{round}_shuffle.log`, `logs/round_{round}_train.log`, `logs/round_{round}_export.log`, and `logs/round_{round}_pk.log` respectively, leaving the standard output clean and concise.

### Requirement: ELO Promotion and Opening Book Sync
The system SHALL run a balanced PK evaluation between the newly trained model and the current best model using `headless_runner.py` with dynamic color swap. If the new model's overall winrate meets or exceeds the promotion threshold, the system SHALL promote it to the active best model and sync high-visits sequences to the opening book.

#### Scenario: Model promotion upon successful evaluation
- **WHEN** the candidate model wins 13 out of 20 games (65% winrate, which is >= 55% threshold) in the PK match
- **THEN** the system SHALL overwrite the current best model weight file with the new model weights, backup the old weights, copy the new weights to `KataGomo/models/model.bin.gz`, and automatically parse `search_logs.jsonl` to append high-winrate canonical moves to `opening_book.json`.

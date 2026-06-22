## ADDED Requirements

### Requirement: CLI Scaffold Plan (mlevo new plan)
The CLI tool MUST support creating a new ML evolution plan via the `mlevo new plan "<name>"` command.
The command SHALL create a subdirectory named `<name>` under `docs/ml/plans/` and scaffold four files: `proposal.md`, `design.md`, `training_plan.json`, and `tasks.md`.
The template for `training_plan.json` SHALL include standard placeholder parameters matching the recommended Gomoku training requirements.

#### Scenario: Successful creation of a new plan
- **WHEN** user executes `uv run python mlevo_cli.py new plan "test-plan"`
- **THEN** directory `docs/ml/plans/test-plan/` exists and contains `proposal.md`, `design.md`, `training_plan.json`, and `tasks.md`

### Requirement: CLI Plan Listing (mlevo list)
The CLI tool MUST support listing all plans via `mlevo list`.
The output SHALL list all active plans in `docs/ml/plans/` and all archived plans under `docs/ml/plans/archive/` along with their status.

#### Scenario: Successful listing of active plans
- **WHEN** user executes `uv run python mlevo_cli.py list`
- **THEN** output lists the names of active plans under `docs/ml/plans/`

### Requirement: CLI Plan Status (mlevo status)
The CLI tool MUST support viewing plan status via `mlevo status [--plan <name>]`.
If `--plan` is omitted, the CLI SHALL identify the active plan (if only one active plan exists) and print its details.
The command SHALL parse `logs/evolution_ledger.json` and display the progress (completed rounds, win rates, promotion status) alongside the tasks listed in `tasks.md`.

#### Scenario: View status of a specific plan
- **WHEN** user executes `uv run python mlevo_cli.py status --plan "test-plan"`
- **THEN** output displays current round progress and completed rounds from ledger

### Requirement: Adaptive Parameter Decision Engine (mlevo decide)
The CLI tool MUST support computing next round parameters via `mlevo decide --plan <name>`.
The decision engine SHALL read the active round stage from `training_plan.json` to extract baseline parameters: `sf_games`, `sf_visits`, `sh_samples`, `tr_lr`, `tr_batch`, `pk_games`.
The decision engine SHALL read the last completed round results from `logs/evolution_ledger.json` (or plan's history) and apply three rules:
1. **Adaptive LR Decay (rule_lr_decay)**: If the training loss difference in the previous round was `< 0.05` across epochs (flatlining), the learning rate `tr_lr` SHALL be multiplied by `0.5` (down to a floor of `0.0001`).
2. **Entropy Boost (rule_entropy_boost)**: If the candidate model in the previous round failed to get promoted (`promoted: false`), the next round's `sf_games` SHALL be increased by `20%` (1.2x) over the plan's stage baseline, and `sf_visits` SHALL be increased by `+16` over the stage baseline.
3. **Crash Recovery (rule_crash_recovery)**: If the last round crashed with a `NaN` loss or OOM (based on ledger/logs), parameters SHALL be scaled down (OOM: halve `tr_batch` or `sf_threads`; NaN: rollback to previous safe model, halve `tr_lr`).
The decision engine SHALL perform a **Guardrail Check (guardrail_check)** verifying that parameters satisfy research report limits: `sf_games >= 100`, `pk_games >= 20`, `sh_samples >= 50000`.
If any parameter violates the guardrail, a warning SHALL be logged and appended to the decision results.
The command SHALL output the decision as a JSON object containing the computed parameters, reasons for each decision, and guardrail warnings.

#### Scenario: Learning rate decay triggered on loss plateau
- **WHEN** previous round training loss difference across epochs is less than 0.05 and user runs `uv run python mlevo_cli.py decide --plan "test-plan"`
- **THEN** output JSON contains `tr_lr` decayed by 50% from the stage baseline and decision reason includes learning rate decay

#### Scenario: Entropy boost triggered on failed promotion
- **WHEN** previous round model failed to be promoted and user runs `uv run python mlevo_cli.py decide --plan "test-plan"`
- **THEN** output JSON contains `sf_games` increased by 20% and `sf_visits` increased by 16 over stage baseline

#### Scenario: Guardrail warning triggered on low games count
- **WHEN** active plan stage defines `sf_games = 5` and user runs `uv run python mlevo_cli.py decide --plan "test-plan"`
- **THEN** output JSON contains a guardrail warning stating `sf_games` is below the recommended minimum of 100

### Requirement: Round Execution (mlevo run)
The CLI tool MUST support running a specific round via `mlevo run --plan <name> --round <N>`.
The CLI SHALL invoke `automl_cli.py` via subprocess to execute the selfplay, shuffling, training, exporting, and PK stages.
The CLI SHALL pass the parameters specified for the round, capturing the execution logs and updating `logs/evolution_ledger.json` upon completion.

#### Scenario: Run round with custom parameters
- **WHEN** user executes `uv run python mlevo_cli.py run --plan "test-plan" --round 1` with valid parameters in `training_plan.json`
- **THEN** system invokes `automl_cli.py` with the corresponding round and parameters

### Requirement: Plan Archive (mlevo archive)
The CLI tool MUST support archiving a plan via `mlevo archive <name>`.
The command SHALL move the plan directory `docs/ml/plans/<name>` to `docs/ml/plans/archive/YYYY-MM-DD-<name>/`.
The command SHALL generate `conclusion.md` compiling performance metrics and take a snapshot of `logs/evolution_ledger.json` saved as `ledger_snapshot.json` in the archived folder.

#### Scenario: Successful archiving of an active plan
- **WHEN** user executes `uv run python mlevo_cli.py archive "test-plan"`
- **THEN** directory `docs/ml/plans/test-plan/` is moved to `docs/ml/plans/archive/YYYY-MM-DD-test-plan/` and contains `conclusion.md` and `ledger_snapshot.json`

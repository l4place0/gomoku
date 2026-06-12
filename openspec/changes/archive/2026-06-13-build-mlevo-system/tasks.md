## 1. Setup and Directory Structure

- [x] 1.1 Create the directory structure under `docs/ml/` (`plans`, `plans/archive`, `specs`, `references`)
- [x] 1.2 Copy `deep-research-report.md` to `docs/ml/references/deep-research-report.md`
- [x] 1.3 Create the initial `docs/ml/specs/training-knowledge.md` containing hyperparameter rules and minimum recommended constraints

## 2. Implement mlevo_cli.py Core Commands

- [x] 2.1 Set up argparse in `mlevo_cli.py` supporting `new plan`, `list`, `status`, `decide`, `run`, `archive`
- [x] 2.2 Implement `mlevo new plan "<name>"` scaffolding logic to generate proposal, design, tasks, and initial training plan under plans directory
- [x] 2.3 Implement `mlevo list` to print active and archived plans
- [x] 2.4 Implement `mlevo status` parsing logic to print the ledger history and current checklist task status
- [x] 2.5 Implement `mlevo archive <name>` logic to move active plan folder to archive, generate conclusion report, and snapshot ledger

## 3. Implement Adaptive Parameter Decision Engine

- [x] 3.1 Implement `DecisionEngine` class in `mlevo_cli.py` containing baseline extraction and history/ledger retrieval
- [x] 3.2 Implement `rule_lr_decay` for scaling down learning rate on flatlining loss difference across epochs
- [x] 3.3 Implement `rule_entropy_boost` for scaling up games and visits when a candidate is not promoted
- [x] 3.4 Implement `rule_crash_recovery` for scaling down batch/threads on OOM and rolling back/halving lr on NaN
- [x] 3.5 Implement `guardrail_check` verifying parameters satisfy deep research report minimums (`sf_games >= 100`, `pk_games >= 20`, `sh_samples >= 50000`)
- [x] 3.6 Integrate decision engine with `mlevo decide --plan <name>` command, formatting output as structured JSON

## 4. Implement automl_cli.py Execution Integration

- [x] 4.1 Implement `mlevo run --plan <name> --round <N>` invoking `automl_cli.py` via subprocess
- [x] 4.2 Ensure stderr/stdout streaming, logging, and automatic ledger entry updating upon round completion

## 5. Implement Agent Skills, Workflows & Cleanup

- [x] 5.1 Define `mlevo-explore`, `mlevo-propose`, `mlevo-apply`, `mlevo-archive` skills under `.agent/skills/`
- [x] 5.2 Create workflows `ml-explore.md`, `ml-propose.md`, `ml-apply.md`, `ml-archive.md` under `.agent/workflows/`
- [x] 5.3 Delete the old `.agent/skills/automl-supervised-evolution/SKILL.md` file

## 6. Verification and Automated Testing

- [x] 6.1 Create automated tests in `tests/test_mlevo.py` using `pytest` framework, ensuring >90% coverage on `DecisionEngine` logic
- [x] 6.2 Run all unit and integration tests using `uv run pytest` and ensure 100% pass

## 1. Setup & Automated Tests

- [x] 1.1 Create `tests/test_automl.py` containing unit tests for CLI argument parsing, evidence chain formatting, and ELO-based promotion threshold checks.
- [x] 1.2 Add mock integration tests to verify log file redirection and split outputs.

## 2. AutoML CLI Implementation (automl_cli.py)

- [x] 2.1 Implement `automl_cli.py` argument parsing matching all synchronized training, self-play, and PK parameters.
- [x] 2.2 Implement the "Parameter Evidence Chain" print block to stdout at the start of each round.
- [x] 2.3 Implement sequential execution logic with stdout/stderr redirection to separate log files under `logs/`.
- [x] 2.4 Implement ELO-based promotion checks, active model weight replacement, and high-visits opening book mining in `automl_cli.py`.

## 3. Agent Supervision Skill

- [x] 3.1 Create the `.agent/skills/automl-supervised-evolution/SKILL.md` skill instruction file under the workspace.

## 4. End-to-End Verification

- [x] 4.1 Run the full automated test suite using `uv run pytest` to ensure 100% success.
- [x] 4.2 Perform an end-to-end dry-run of a single round using minimal parameters and inspect the `logs/` directory to verify evidence integrity.

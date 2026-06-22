## MODIFIED Requirements

### Requirement: CLI Arguments Configuration
The system SHALL parse CLI parameters to configure the headless runner's match options including models, match count, rules, and logging path。SHALL 支持 SPRT 相关参数。

#### Scenario: Running with customized command arguments
- **WHEN** the user invokes `headless_runner.py` with arguments `--black-model "./models/m1.bin.gz" --white-model "./models/m2.bin.gz" --games 5 --output "./results.json"`
- **THEN** the system SHALL load model `m1.bin.gz` for Black and model `m2.bin.gz` for White, run exactly 5 games, and save a formatted json report to `./results.json`.

#### Scenario: Running with SPRT early stop
- **WHEN** the user invokes `headless_runner.py` with `--early-stop --sprt-h1 35 --sprt-alpha 0.05`
- **THEN** the system SHALL 实现 SPRT early stop，在似然比达到边界时提前终止对弈

#### Scenario: SPRT early stop with minimum games
- **WHEN** `--early-stop` is enabled and `--min-games 20` is specified
- **THEN** the system SHALL 不在前 20 局触发 SPRT early stop

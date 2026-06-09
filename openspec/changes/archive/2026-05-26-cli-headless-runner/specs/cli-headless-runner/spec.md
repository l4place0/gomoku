## ADDED Requirements

### Requirement: CLI Arguments Configuration
The system SHALL parse CLI parameters to configure the headless runner's match options including models, match count, rules, and logging path.

#### Scenario: Running with customized command arguments
- **WHEN** the user invokes `headless_runner.py` with arguments `--black-model "./models/m1.bin.gz" --white-model "./models/m2.bin.gz" --games 5 --output "./results.json"`
- **THEN** the system SHALL load model `m1.bin.gz` for Black and model `m2.bin.gz` for White, run exactly 5 games, and save a formatted json report to `./results.json`.

### Requirement: Rules Enforcement
The system SHALL enforce complete Gomoku rules (including Opening Book query, Three-Hand Swap evaluation, and Five-Hand N-play decision-making) without GUI interactions.

#### Scenario: Running AI vs AI match through opening and swap rules
- **WHEN** the game starts
- **THEN** the system SHALL place the first stone at the board center, query opening books, automatically trigger MCTS evaluations for Three-Hand Swap to determine whether to swap, and execute Five-Hand N-play candidate selection and filter automatically based on AI decisions.

### Requirement: Formatted JSON Output Reports
The system SHALL write a comprehensive summary report in JSON format upon completion of all match games.

#### Scenario: Generating final match report
- **WHEN** all scheduled games complete successfully
- **THEN** the system SHALL write a JSON file containing the total match count, win rate statistics, average move counts, and the detailed history sequence of each game.

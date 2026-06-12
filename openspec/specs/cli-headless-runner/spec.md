# cli-headless-runner Specification

## Purpose
TBD - created by archiving change cli-headless-runner. Update Purpose after archive.
## Requirements
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


---

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

---

## MODIFIED Requirements

### Requirement: headless_runner 使用 WorkerClient
headless_runner.py SHALL 使用 WorkerClient 类替代直接 subprocess.Popen 调用。SHALL 在启动时创建 WorkerClient 实例。SHALL 在每局结束后调用 reset_board() 重置双方状态。

#### Scenario: 正常 PK 对弈
- **WHEN** 启动 PK 评测
- **THEN** 创建 WorkerClient，执行对弈，每局后 reset_board()，关闭 WorkerClient

#### Scenario: Worker 崩溃恢复
- **WHEN** WorkerClient.query() 返回 WORKER_CRASHED
- **THEN** 重启 WorkerClient，重试当前局（最多 1 次重启）

### Requirement: 颜色对称
headless_runner.py SHALL 确保 candidate 和 baseline 双方在每局开始时拥有相同的引擎状态。SHALL 每局双方都重置 board state（不重新加载模型）。

#### Scenario: 颜色分配
- **WHEN** 第 N 局开始
- **THEN** N 为偶数时 candidate=BLACK，N 为奇数时 candidate=WHITE

#### Scenario: 状态对称
- **WHEN** 每局开始
- **THEN** 双方的 board state 都被重置为初始状态，VCF solver 重新初始化

### Requirement: PK 结果正确记录
headless_runner.py SHALL 将每局结果正确记录到输出文件。SHALL 统计 BLACK/WHITE/DRAW 各自的胜局数。SHALL 在 PK 完成后输出汇总。

#### Scenario: PK 完成
- **WHEN** 所有对局完成
- **THEN** 输出包含 total_games、black_wins、white_wins、draws 的 JSON 结果

#### Scenario: PK 中途失败
- **WHEN** 对弈中途 worker 崩溃且无法恢复
- **THEN** 输出已完成的对局结果，并标记 PK 未完成

### Requirement: VCF solver 初始化
ai_worker.py SHALL 在 model load 后、首次 GetTopMoves 前初始化 VCF solver 的 zob_board。

#### Scenario: 正常初始化
- **WHEN** ai_worker.py 加载模型后
- **THEN** 调用 VCF 初始化，后续 GetTopMoves 不再报 zob_board not init 错误

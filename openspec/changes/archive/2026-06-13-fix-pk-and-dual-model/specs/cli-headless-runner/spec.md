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

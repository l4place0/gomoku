## ADDED Requirements

### Requirement: Selfplay 与 Training 并行执行
automl_cli.py SHALL 在同一 GPU 上并行运行 selfplay 和 training 进程。SHALL 使用 OS 级时间片切分实现 GPU 共享。SHALL 在 selfplay 完成后立即启动下一轮 training，不等待 PK 完成。

#### Scenario: 正常并行执行
- **WHEN** 一轮训练开始
- **THEN** selfplay 进程和 training 进程同时运行，共享 GPU 时间片

#### Scenario: Training 先完成
- **WHEN** training 在 selfplay 之前完成
- **THEN** training 进程退出，selfplay 继续独占 GPU 直到完成

#### Scenario: Selfplay 先完成
- **WHEN** selfplay 在 training 之前完成
- **THEN** selfplay 数据写入磁盘，training 继续独占 GPU 直到完成

### Requirement: VRAM 预算管理
automl_cli.py SHALL 在并行运行时监控 VRAM 使用。SHALL 确保 selfplay 和 training 的 VRAM 总和不超过 GPU 总量的 90%。SHALL 在 VRAM 超限时自动降低 nnMaxBatchSize 或 training batch size。

#### Scenario: VRAM 正常
- **WHEN** 并行运行时 VRAM 使用 < 90%
- **THEN** 正常执行，不调整参数

#### Scenario: VRAM 接近上限
- **WHEN** 并行运行时 VRAM 使用 >= 90%
- **THEN** 自动降低 nnMaxBatchSize 到 32 或 training batch 到 32

### Requirement: Shuffle 异步化
automl_cli.py SHALL 将 shuffle 和 export 改为后台持续运行的服务。SHALL 在 selfplay 数据写入后自动触发 shuffle。SHALL 不阻塞 training 的启动。

#### Scenario: Shuffle 后台运行
- **WHEN** selfplay 数据写入完成
- **THEN** 后台 shuffle 服务自动处理新数据，不阻塞 training

#### Scenario: Export 后台运行
- **WHEN** training checkpoint 更新
- **THEN** 后台 export 服务自动导出模型，不阻塞下一轮

### Requirement: 进程生命周期管理
automl_cli.py SHALL 正确管理并行进程的启动和关闭。SHALL 在任一进程崩溃时清理所有子进程。SHALL 在收到 SIGTERM 时优雅关闭所有进程。

#### Scenario: 正常关闭
- **WHEN** 所有阶段完成
- **THEN** 所有后台进程被清理，资源释放

#### Scenario: 进程崩溃
- **WHEN** selfplay 或 training 进程异常退出
- **THEN** 记录错误，清理所有子进程，标记本轮失败

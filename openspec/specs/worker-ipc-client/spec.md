## ADDED Requirements

### Requirement: WorkerClient 进程管理
WorkerClient SHALL 封装 ai_worker.py 子进程的启动和关闭。SHALL 在 start() 时等待 worker 输出 `{"status": "ready"}` 确认初始化完成。SHALL 在 close() 时发送 `quit` 并 terminate 进程。

#### Scenario: 正常启动
- **WHEN** 调用 `WorkerClient(model_path, config_path).start()`
- **THEN** 启动 ai_worker.py 子进程，等待 ready 信号，返回 True

#### Scenario: 启动失败
- **WHEN** ai_worker.py 进程启动后 10s 内未输出 ready 信号
- **THEN** start() 返回 False，进程被 terminate

#### Scenario: 正常关闭
- **WHEN** 调用 `client.close()`
- **THEN** 向 stdin 发送 `quit`，等待 1s，terminate 进程

### Requirement: WorkerClient 查询通信
WorkerClient.query() SHALL 通过 stdin/stdout JSON 管道与 worker 通信。SHALL 发送包含 action/history/visits 的 JSON 请求。SHALL 解析响应中的 x/y/score 字段。

#### Scenario: 正常查询
- **WHEN** 发送有效的 search 请求
- **THEN** 返回 `{"status": "ok", "x": N, "y": N, "score": N}`

#### Scenario: Worker 返回错误
- **WHEN** worker 返回 `{"status": "error", "error": "..."}`
- **THEN** 返回 `{"status": "error", "error": "..."}` 原样传递

### Requirement: WorkerClient 超时控制
WorkerClient.query() SHALL 对 stdout.readline() 设置 timeout。SHALL 在超时后检测进程是否存活。SHALL 在进程存活时重试，进程死亡时返回错误。

#### Scenario: Worker 响应正常
- **WHEN** worker 在 timeout 内返回 JSON 响应
- **THEN** 正常返回结果，不触发超时

#### Scenario: Worker 静默但存活
- **WHEN** readline() 超时且 is_alive() 为 True
- **THEN** 重试查询（最多 max_retries 次）

#### Scenario: Worker 崩溃
- **WHEN** readline() 超时且 is_alive() 为 False
- **THEN** 返回 `{"status": "error", "error": "WORKER_CRASHED"}`

### Requirement: WorkerClient 进程健康检测
WorkerClient.is_alive() SHALL 用 poll() 检测子进程是否存活。SHALL 在进程退出时返回 False。

#### Scenario: 进程存活
- **WHEN** 子进程正在运行
- **THEN** is_alive() 返回 True

#### Scenario: 进程已退出
- **WHEN** 子进程已退出（returncode != None）
- **THEN** is_alive() 返回 False

### Requirement: WorkerClient Board 重置
WorkerClient.reset_board() SHALL 通知 worker 重置棋盘状态。SHALL 发送 `{"action": "reset"}` 命令。

#### Scenario: 正常重置
- **WHEN** 调用 reset_board()
- **THEN** worker 清空棋盘状态，返回 `{"status": "ok"}`

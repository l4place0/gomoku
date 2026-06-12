## Why

PK 评测系统存在三个互相依赖的 bug（IPC 崩溃、颜色偏差、VCF 未初始化），导致 b10c256nbt 的所有 PK 结果无效。同时，双模型对弈功能（multi-process-dual-model-selfplay）因 IPC 层未完成而停滞在 2/8。两者的共同瓶颈是 ai_worker.py 的进程通信层 — 修复 IPC 同时解决 PK bug 和解锁双模型对弈。

## What Changes

- **新增 WorkerClient 类**: 从 headless_runner.py 提取 IPC 通信逻辑到独立类，封装 stdin/stdout 管道、timeout、进程健康检测、重试。PK 和双模型对弈共用。
- **修复 IPC 崩溃**: readline() 加 timeout（当前无超时，worker 崩溃后主进程永久阻塞）。Worker 崩溃后自动重试（当前仅 1 次重试）。
- **修复颜色偏差**: 双方每局都重置 board state（不重载模型），消除 DLL 单例状态污染导致的 WHITE 90% 胜率偏差。
- **修复 VCF solver**: 在 ai_worker.py 中确保 model load 后、首次 GetTopMoves 前初始化 zob_board。
- **完成双模型对弈**: game.py 集成 WorkerClient，UI 增加白方模型选择和热重载。
- **测试分层**: Layer 1 纯逻辑测试（颜色/结果判定）+ Layer 2 IPC 协议测试（mock WorkerClient）+ Layer 3 集成测试（真实 DLL）。

## Capabilities

### New Capabilities

- `worker-ipc-client`: WorkerClient 类 — 封装 ai_worker.py 进程的 stdin/stdout 通信、timeout、健康检测、重试。PK 和双模型对弈共用的 IPC 基础设施。

### Modified Capabilities

- `cli-headless-runner`: headless_runner.py 改用 WorkerClient 替代直接 Popen 调用。颜色分配逻辑改为每局重置 board state。游戏结果正确写入 ledger。

## Impact

- `tools/ai_worker.py`: VCF solver 初始化修复（zob_board 在 model load 后初始化）
- `tools/headless_runner.py`: 重构为使用 WorkerClient；颜色对称修复；结果记录修复
- `ml/automl_cli.py`: PK 结果写入 ledger 的逻辑修复
- `game.py`: 集成 WorkerClient 实现双模型对弈
- 侧边栏 UI: 白方模型选择 + 热重载按钮
- `tests/`: 新增 test_worker_client.py、test_pk_logic.py、test_pk_integration.py

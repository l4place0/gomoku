## 1. WorkerClient 类实现

- [x] 1.1 创建 `tools/worker_client.py`，实现 WorkerClient 类：__init__(model_path, config_path, timeout=10.0)
- [x] 1.2 实现 start()：启动 ai_worker.py 子进程，等待 ready 信号，超时返回 False
- [x] 1.3 实现 query()：发送 JSON 请求到 stdin，读取 stdout 响应，返回结构化 dict
- [x] 1.4 实现 readline timeout：用 threading.Timer 或 select 实现 stdout.readline() 超时
- [x] 1.5 实现 is_alive()：用 poll() 检测子进程状态
- [x] 1.6 实现 close()：发送 quit + terminate + 等待清理
- [x] 1.7 实现 reset_board()：发送 `{"action": "reset"}` 到 worker

## 2. ai_worker.py 修复

- [x] 2.1 实现 reset 命令处理：接收 `{"action": "reset"}`，清空本地 board state
- [x] 2.2 修复 VCF 初始化：model load 后调用 VCF init 确保 zob_board 已初始化

## 3. headless_runner.py 重构

- [x] 3.1 替换 subprocess.Popen 为 WorkerClient：启动、查询、关闭全部走 WorkerClient
- [x] 3.2 实现颜色对称：每局双方都调用 reset_board() 重置状态
- [x] 3.3 实现 worker 崩溃恢复：WORKER_CRASHED 时重启 WorkerClient，重试当前局
- [x] 3.4 修复结果记录：PK 完成后正确输出 total_games、black_wins、white_wins、draws

## 4. 双模型对弈集成

- [x] 4.1 game.py 集成 WorkerClient：白方 AI 配置时启动 worker，通过 WorkerClient 查询
- [x] 4.2 侧边栏 UI：白方模型路径显示 + 浏览按钮 + 热重载按钮（已存在）
- [x] 4.3 游戏关闭/重置时安全关闭 WorkerClient（reset_board + finally cleanup）

## 5. 测试

- [x] 5.1 Layer 1: test_pk_logic.py — 颜色分配、结果判定、ledger 一致性、PK 有效性
- [x] 5.2 Layer 2: test_worker_client.py — mock WorkerClient 测试 timeout、重试、错误分类
- [x] 5.2a 测试 readline timeout：worker 静默 → 超时 → 重试
- [x] 5.2b 测试 worker 崩溃检测：进程退出 → WORKER_CRASHED
- [x] 5.2c 测试 JSON 解析错误：畸形响应 → 优雅降级
- [x] 5.3 Layer 3: test_pk_integration.py — 真实 DLL 集成测试
- [x] 5.3a 完整 PK 对弈：5 局完成，IPC 无失败（VCFSolver 警告为已知 cosmetic 问题）
- [x] 5.3b 颜色对称验证：同模型 5 局全平局，颜色偏差为 0%

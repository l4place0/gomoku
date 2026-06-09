## Context

当前项目中所有的五子棋局势评估、AI 策略自对弈及日志记录必须通过 `game.py` 的 GUI 渲染流程。这直接阻碍了在大规模无图形界面的服务器环境下进行批量对局评测与 Elo 排名计算。

通过加载 `GameEngine.dll` 和桥接 `ai_worker.py` 的子进程 IPC，我们有能力完全绕过 Pygame 窗口，实现一个轻量、极速且纯 CLI 的运行器。

## Goals / Non-Goals

**Goals:**
- 实现全新的纯 CLI 对局工具 `headless_runner.py`。
- 支持加载黑白不同的独立物理权重包。
- 自动运行并处理完整的国际正规五子棋规则判定（开局库、三手交换、五手打点）。
- 对局赛段结束时将总结果写入标准的 JSON 格式文件。

**Non-Goals:**
- 绝不使用或导入 `pygame` 或其他任何 GUI/图形依赖。
- 本阶段不需要提供高级进程池的动态负载均衡并发，默认并发局数限制为 1。

## Decisions

### 1. 引擎加载与生命周期选择 (Direct DLL Load + Subprocess Worker)
- **选择**：黑方 AI 使用主进程直接加载的 `GameEngine.dll` 执行，而白方 AI 则通过拉起 `ai_worker.py` 脚本子进程，使用 Python 进程间管道 (stdin/stdout Pipes) 发送棋盘历史状态并获取其推理决策。
- **原因**：这能够在单机单卡上规避 `GameEngine.dll` 的单例神经网络加载冲突，同时在 Python 层完美隔离并独立控制两个不同的物理模型权重。

### 2. 规则自动判断器设计 (Automatic Referee State Machine)
- **选择**：重新实现一个简洁的状态机裁判环。
- **原因**：由于 `GamePhase` 在 `game.py` 里绑定了大量的界面渲染操作，我们在 `headless_runner.py` 里将使用更直接的基于 `gs.history` 长度与落子角色的状态分发，从而保证 100% 规则吻合且毫无 Pygame 耦合。

## Risks / Trade-offs

- **[Risk]**: 两个 AI 引擎在短时间内执行大量推理导致显卡显存溢出 (OOM) 或 CUDA Context 冲突。
  - **Mitigation**: 严格限制最大并发为 1；并在每一场 Game 结束后进行适度延时或显存清理。
- **[Risk]**: 子进程 `ai_worker.py` 因为异常退出而留下僵尸进程，导致显存泄露。
  - **Mitigation**: 裁判主程序将对局循环置于 `try...finally` 块中，并在 `finally` 里强行调用子进程的 `terminate()` 摧毁进程树。

## Context

在之前的双 AI 对弈中，我们受限于 C++ DLL 单例模式的限制，无法让黑白双方各自加载截然不同的 `.bin.gz` 权重文件进行真正的“权重对局”。若在单进程中尝试销毁并重新初始化 KataGomo 实例，不仅耗时数秒导致严重顿卡，而且在同一个 GPU 显存段上初始化两个 evaluator 极易发生显存抢占与 Context 崩溃。

利用 **操作系统的进程隔离机制 (OS Process Isolation)**，将第二方 AI 剥离成一个后台轻量进程 `ai_worker.py`，可以优雅且 100% 安全地克服这个单例难题。

## Goals / Non-Goals

**Goals:**
- **物理双权重对决**：黑白双方 AI 可以分别加载完全不同的物理 `.bin.gz` 模型文件。
- **0 显存/CUDA 冲突**：利用进程隔离，让操作系统级多进程调度完美解决并发显存安全和 Context 共享冲突。
- **免 C++ 代码重构**：保持底层单例 DLL 不变，在应用层实现轻量级 Worker。

**Non-Goals:**
- **重构 C++ 多实例**：不再尝试去修改 C++ 引擎的 getInstance() 行为，也不在单进程中并存两个 evaluator。

## Decisions

### 决策一：多进程 Worker 架构与标准输入输出 IPC 管道
我们选择编写一个专门的轻量托管程序 `ai_worker.py`。

```
       ┌────────────────────────┐
       │   主进程 (game.py)     │ (加载主模型 model_A)
       └───────────┬────────────┘
                   │
                   │ (拉起 / subprocess.Popen)
                   ▼
       ┌────────────────────────┐
       │  子进程 (ai_worker.py) │ (加载副模型 model_B)
       └────────────────────────┘
```

- **IPC 通信交互协议**：
  - 当轮到白方 AI (子进程) 行棋时，主进程将当前棋局的历史 `history` 转换为简单的 JSON 字符串，通过 stdin 管道写入子进程。
  - 子进程内部加载相同的 `GameEngine.dll` 并载入 model_B 权重。子进程读取 stdin，调用 `DoMove` 在本地同步棋盘，执行 `GetTopMoves` 进行 MCTS 搜索。
  - 搜索完毕后，子进程将结果 `{ "x": x, "y": y, "score": score, "searchId": searchId }` 格式化为 JSON 行写入 stdout。
  - 主进程阻塞读取 stdout 获得落子点，执行落子，完成闭环。

### 决策二：生命周期的优雅闭环
为了防止游戏意外关闭或重启时，后台残留孤儿 Python 进程占用显存，我们引入生命周期保活机制：
- 主进程拉起子进程时，设定其为子进程关系。当主进程触发退出或 `sys.exit()` 时，在 `finally` 块中显式发送 `quit` 命令给子进程，并调用 `proc.terminate()` 和 `proc.wait()` 确保其彻底销毁。
- 子进程增加 `stdin` 关闭检测：如果主进程异常闪退导致管道被操作系统自动关闭（EOF），子进程 SHALL 自动捕捉该异常并退出进程，实现 100% 的“零僵尸进程”泄露保障。

## Risks / Trade-offs

- **[Risk]** 双进程 KataGomo 并存时，如果 GPU 显存不足（例如显存小于 4GB）可能会发生显存溢出（OOM）。
  - **Mitigation**: 在 UI 界面友情提示用户：进行多物理权重自对弈时，请确保有足够的显存（建议 6GB 以上），或建议将 Visits 控制在合理范围。

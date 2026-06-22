## Context

PK 评测系统有三个互相依赖的 bug：

1. **IPC 崩溃**: headless_runner.py 的 `readline()` 无 timeout。Worker DLL 崩溃后 stdout 静默，主进程永久阻塞。仅有 1 次重试（line 465），无 watchdog。
2. **颜色偏差**: 候选模型总是 BLACK（偶数局），基线总是 WHITE（奇数局）。DLL 单例导致 BLACK 侧每局重载模型、WHITE 侧不重载，引擎状态不对称。R2 PK 中 WHITE 胜率 90%。
3. **VCF 未初始化**: `zob_board` 在 board 创建时初始化，不在 model load 时。ai_worker.py 加载模型后立刻调用 GetTopMoves，zobrist 表未初始化。

双模型对弈（multi-process-dual-model-selfplay）停滞在 2/8，剩余任务全部依赖 IPC 层完成。

## Goals / Non-Goals

**Goals:**
- 修复 IPC 通信：timeout + watchdog + 重试 + 错误分类
- 修复颜色偏差：双方每局重置 board state（不重载模型）
- 修复 VCF 初始化：model load 后初始化 zob_board
- 提取 WorkerClient 类：PK 和双模型对弈共用
- 完成双模型对弈：game.py IPC 桥接 + UI
- 测试分层：纯逻辑 / IPC mock / 集成测试

**Non-Goals:**
- 不改变 KataGomo C++ DLL 代码
- 不改变自博弈流程（只改 PK 和双模型对弈）
- 不改变 mlevo report / archive 流程（已修复）

## Decisions

### Decision 1: WorkerClient 抽象（方案 B）

**选择**: 从 headless_runner.py 提取 IPC 逻辑到 WorkerClient 类

**理由**:
- game.py 需要同样的 IPC 逻辑，WorkerClient 可直接复用
- timeout/watchdog 封装在 WorkerClient 里比散落在 headless_runner.py 更干净
- mock WorkerClient 测试的是"如何处理 worker 响应"，不是"如何调用 Popen"

**替代方案**: Mock subprocess.Popen（方案 A）— 零重构但测试耦合实现细节，game.py 无法复用。

### Decision 2: Board state reset 而非 model reload（方案 B）

**选择**: 每局双方都重置 board state（DoMove/UndoMove 清空），不重新加载模型

**理由**:
- 模型加载耗时 ~2-5s，每局重载会让 PK 时间翻倍
- 颜色偏差的根因是 board state 残留，不是模型权重问题
- reset board state 只需清空 env + 重新初始化 VCF

**替代方案**: 每局双方都重新加载模型 — 干净但太慢。

### Decision 3: WorkerClient 接口设计

```python
class WorkerClient:
    def __init__(self, model_path, config_path, timeout=10.0)
    def start(self) -> bool          # 启动 worker 进程，等待 ready
    def query(self, history, visits, policy, value, engine) -> dict  # 发送搜索请求
    def is_alive(self) -> bool       # 检查进程是否存活
    def close(self) -> None          # 发送 quit + terminate
    def reset_board(self) -> None    # 通知 worker 重置 board state
```

timeout 参数控制 readline() 的超时时间。query() 返回结构化 dict（含 status/x/y/score/error）。is_alive() 用 poll() 检测进程状态。

### Decision 4: 测试分层

| Layer | 依赖 | 速度 | 覆盖 |
|-------|------|------|------|
| 1: 纯逻辑 | 无 | ms | 颜色分配、结果判定、ledger 一致性 |
| 2: IPC mock | mock WorkerClient | ms | timeout 行为、重试逻辑、错误分类 |
| 3: 集成 | 真实 DLL | s-min | 完整 PK、VCF 初始化、双模型对弈 |

## Risks / Trade-offs

- **[Risk] 重构引入新 bug** → 用 Layer 3 集成测试兜底，重构前后跑同一组 PK 对比结果
- **[Risk] reset board state 不完整** → VCF zobrist 表可能残留；缓解：reset 时显式重新初始化 VCF
- **[Risk] timeout 值选择** → 太短误杀慢响应，太长失去 timeout 意义；缓解：默认 10s，可通过参数调整
- **[Trade-off] WorkerClient 是同步阻塞** → 简单但不支持并行查询；当前场景（单进程 PK）足够，未来如需并行可改为 async

## Open Questions

1. timeout 默认值：10s 是否足够？需要实测 worker 正常响应时间
2. reset_board 是否需要通知 worker 进程？还是只重置 DLL 侧的 env？

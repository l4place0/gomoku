## Why

为了评估不同版本的神经网络权重模型（即不同的 `.bin.gz` 模型文件）在实战中的棋力差异，系统需要支持真正的双网络模型对弈。由于底层 C++ DLL 采用单例设计且重构并发 CUDA context 极易崩溃，最简单、安全、健壮的方法是利用**多进程隔离机制（Multi-Process Isolation）**：主 GUI 进程载入主模型，通过启动一个独立的后台轻量 Python 进程作为副模型托管容器，使用管道（stdin/stdout）或简单 socket 进行 IPC 落子通信，实现完全独立的双模型对决。

## What Changes

- **轻量副模型托管程序 (Worker)**：编写一个独立的轻量级 Python 脚本 `ai_worker.py`，负责在独立进程中加载 C++ DLL 引擎并载入副模型权重文件。
- **进程间通信 (IPC) 协议设计**：在主进程与 Worker 进程间实现简单的 stdin/stdout 通信协议，传入当前棋盘 history，返回最佳落子 `(x, y)` 坐标。
- **Worker 进程生命周期管理**：在 `game.py` 开启自对弈时，主程序使用 `subprocess.Popen` 自动拉起 `ai_worker.py`，并在游戏关闭时自动安全销毁。
- **自对弈对决控制面板适配**：侧边栏支持玩家为“黑方 AI”与“白方 AI”分别指定不同的物理 `.bin.gz` 权重文件路径，并支持一键热重载。

## Capabilities

### New Capabilities
- `multi-process-selfplay`: 通过子进程隔离机制运行独立的副模型引擎，并通过管道（stdin/stdout）进行进程间落子通信，实现真正的物理双模型对战。

### Modified Capabilities
- `engineering`: 侧边栏及主循环适配多进程 Worker 的拉起与销毁生命周期，扩展选择 `.bin.gz` 文件的 UI。

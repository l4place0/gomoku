## ADDED Requirements

### Requirement: 隔离的多进程副模型托管服务
系统 SHALL 支持通过拉起独立的操作系统子进程来托管副模型。主进程运行主模型，子进程加载独立的 `GameEngine.dll` 并载入独立的 `.bin.gz` 神经网络权重。主子进程之间通过标准输入输出管道（stdin/stdout）进行数据交互，传递当前的棋局历史，接收副模型计算出的推荐着法坐标。

#### Scenario: 自动启动副进程与管道握手
- **WHEN** 游戏启动且进入 `AI_VS_AI` 模式
- **THEN** 主进程 SHALL 使用 `subprocess.Popen` 拉起 `ai_worker.py`，载入指定的白方模型，并进行简单的握手（如发送 `ping`，返回 `pong`）。

#### Scenario: 管道通信决策与落子
- **WHEN** 轮到白方 AI (副模型进程) 落子
- **THEN** 主进程 SHALL 通过标准输出向子进程写入当前棋盘 history (如 `[(7,7), (7,8)]`) 并以换行符结尾，子进程读取输入、执行本地搜索，并通过 stdout 返回最佳着法 `(x, y)` 坐标。

### Requirement: 物理权重模型动态文件选择与重载
系统 SHALL 允许玩家在对决控制台中，为黑白两方 AI 选择不同的物理 `.bin.gz` 神经网络权重路径。当修改选择后，主进程或 Worker 进程 SHALL 自动执行 `LoadKataModel` 重新载入模型。

#### Scenario: 更改白方模型权重并热重载
- **WHEN** 玩家选择了一个新的白方模型路径 `model_v2.bin.gz` 并点击“重载”
- **THEN** 系统 SHALL 安全销毁当前的子进程，使用新的模型路径重新拉起 `ai_worker.py`，保持棋局的完整流转。

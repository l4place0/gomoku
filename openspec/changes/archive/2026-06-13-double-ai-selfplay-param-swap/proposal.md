## Why

为了提升和评估五子棋引擎的棋力，我们需要直观、动态地对比不同搜索参数与决策框架的强弱。本变更旨引入“双 AI 对战（AI vs AI）”自对弈流程，支持在不修改 C++ DLL 单例引擎的前提下，在每一回合动态切换双侧 AI 的搜索参数（如 visits、policy_blend 等）或核心决策引擎，以便进行全自动的模型测试与量化分析，并提供极佳的观战体验。

## What Changes

- **新增双 AI 对局状态机分支**：扩展 `GamePhase` 和 `GameState`，在状态机中提供全自动的自对战流程支持，屏蔽人类手动点击的鼠标交互。
- **动态参数切换机制**：在黑白双方 AI 的回合，落子决策前实时通过 `SetKataSearchParams` 或 `SetKataEnabled` 注入各自对应的专属配置（如 visits、policy/value 混合比、甚至切换为 MiniMax+VCF 引擎）。
- **对决控制与步时延迟**：在 Python 端引入可调节的步时延迟机制（Delay），防止 AI 瞬间落子完毕导致界面卡死，让玩家能够平滑观战。
- **全新双 AI 仪表盘 UI**：侧边栏扩展为专门的双 AI 对战控制台，实时显示双方 AI 当前使用的引擎、visits、耗时、上一步评分以及历史搜索指标。
- **自对弈日志持久化**：`game_logger.py` 增强，支持在记录 move 时标识两个 AI 分别的身份、所属参数（ visits、engine ），方便后期进行对局数据回溯。

## Capabilities

### New Capabilities
- `double-ai-selfplay`: 提供完整的自动化双 AI 自对弈流程，支持黑白双方使用独立的搜索参数与不同的算法引擎，包含对弈暂停/继续控制与动作延迟。

### Modified Capabilities
- `engineering`: 改造原有的游戏循环、事件管理器与 GUI 侧边栏，支持 AI vs AI 控制面板的渲染与参数滑动条交互；扩展日志子系统。

## Impact

- **game.py**：游戏主循环、状态机切换、`handle_normal` 事件处理、侧边栏渲染等需要进行整体重构，兼容 `GamePhase.AI_VS_AI` 的存在。
- **game_logger.py**：在记录对局日志时，需将 AI 身份（如 `ai_black`, `ai_white`）及其对应参数记入日志文件。

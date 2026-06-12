## 1. 核心状态机与控制时序重构

- [x] 1.1 扩展 `GamePhase` 枚举，加入 `AI_VS_AI` 状态阶段；在 `GameState` 数据类中新增自对弈控制所需的属性字段（如 `game_mode`, `ai_black_cfg`, `ai_white_cfg`, `ai_delay_ms`, `is_paused` 等）。
- [x] 1.2 重构 `is_role_human` 逻辑，确保当进入 `AI_VS_AI` 阶段时，任何角色（BLACK / WHITE）都 SHALL 被判定为非人类角色，从而自动拦截常规的手动鼠标落子事件。
- [x] 1.3 在 Pygame 事件轮询及更新流程中，加入非阻塞式的步时延迟检查机制（利用 `pygame.time.get_ticks()`），支持以平滑、可设定的毫秒间隔（Delay）交替驱动双方落子。

## 2. 动态参数与引擎切换注入

- [x] 2.1 改造 AI 走子逻辑，使之在落子前从 `GameState` 动态读取当前落子 AI 专属的 Visits（模拟次数）、PolicyBlend 和 ValueBlend 参数。
- [x] 2.2 在执行 `GetTopMoves` 搜索之前，调用 `dll.SetKataEnabled` 与 `dll.SetKataSearchParams` 将当前执子 AI 的专属参数瞬时加载到全局 C++ 引擎中。
- [x] 2.3 支持引擎类型切换决策：若当前执子方被配置为启发式 `MiniMax` 引擎，系统在决策前注入参数时 SHALL 通过 `dll.SetKataEnabled(env, False)` 停用网络，实现不同决策算法的动态交手。

## 3. 双 AI 对决控制台与 UI 滑动条实现

- [x] 3.1 重构侧边栏渲染模块，在对局处于 `AI_VS_AI` 模式时，绘制专用的“双 AI 对决控制台”界面。
- [x] 3.2 实现参数调节 UI：为黑白两方 AI 独立绘制参数调节滑块（如 Visits、PolicyBlend、ValueBlend 的拖拽条），并处理拖拽事件与更新 `GameState`。
- [x] 3.3 在界面中设计“开始对决 / 暂停 / 继续”以及“重置”按钮，并高亮指示当前正在思考的 AI 身份状态。

## 4. 结构化持久日志记录增强

- [x] 4.1 修改 `game_logger.py` 中的 `move` 记录函数签名与持久化格式，新增支持写入 AI 角色身份（`ai_black`, `ai_white`）与当前搜索参数的字段。
- [x] 4.2 在自对弈每次落子成功后，将本步 AI 的实际搜索参数（visits, 决策引擎等）作为结构化元数据同步持久化到运行日志。

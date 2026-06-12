## ADDED Requirements

### Requirement: Pygame 双 AI 控制台与参数配置面板
侧边栏（Sidebar）在双 AI 对决阶段 SHALL 渲染专用的“双 AI 对决控制台”。控制台 SHALL 包含：
1. 双侧 AI 状态展示区，分别使用红/白高亮标签指示当前正在思考的 AI。
2. 双侧 AI 独立参数调节区：通过滑块或增减按钮调节 visits（范围 2 至 1000）、policyBlend 和 valueBlend；以及引擎切换下拉菜单/选择钮。
3. 播放控制键：提供“开始对决 / 暂停 / 继续”以及“重置”按钮，且实时支持交互。
4. 步时延迟滑块：可设定 100ms 至 2000ms 之间的延迟间隔。

#### Scenario: 侧边栏对决面板渲染与滑块调节
- **WHEN** 进入 `AI_VS_AI` 阶段并且玩家拖动“白方模拟次数 (Visits)”滑块至 128
- **THEN** 侧边栏实时重绘并更新数值，且白方 AI 下一次落子思考前系统注入的 visits 必须为 128。

### Requirement: 自对弈多属性结构化日志记录
日志子系统（`game_logger.py`）SHALL 针对双 AI 自对弈进行适配。在记录每次 move 时，除基本的步数与坐标外，系统 SHALL 写入结构化字段：`role_identity`（如 `"ai_black"`, `"ai_white"`）、`engine_type`（如 `"MCTS"`, `"MiniMax"`）以及实际执行的 `visits` 模拟参数。

#### Scenario: 写入双 AI 对决日志
- **WHEN** 黑方 AI 成功执行落子 DoMove
- **THEN** `game_logger.py` 同步在 `runtime.log` 和对局日志中写入带有时序与 `{ "role_identity": "ai_black", "engine_type": "MCTS", "visits": 256 }` 等元数据的结构化事件。

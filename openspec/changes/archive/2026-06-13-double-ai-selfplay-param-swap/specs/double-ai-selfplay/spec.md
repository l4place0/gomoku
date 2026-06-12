## ADDED Requirements

### Requirement: 双 AI 自动化自对弈核心回路与时序控制
系统 SHALL 包含一个全自动的“双 AI 对决 (AI vs AI)”对弈状态机回路。在该回路中，系统 SHALL 自动交替执行黑白双方 AI 的决策与落子操作，并在每次落子后执行 `CheckWin` 检测。在此模式下，两个角色都 SHALL 判定为非人类角色，以屏蔽所有鼠标落子事件。同时，系统 SHALL 在每次落子后执行可设定的步时延迟（Delay），以确保界面渲染及观战的平滑性。

#### Scenario: 启动双 AI 自对弈与交替落子
- **WHEN** 玩家在主界面或控制台点击“开始对决”且游戏阶段进入 `AI_VS_AI` 且游戏未结束
- **THEN** 系统 SHALL 自动轮流调用对应角色的 AI 决策引擎落子，每次落子之间插入设定的步时延迟，直到产生胜负或和棋。

#### Scenario: 对决暂停与继续
- **WHEN** 对决进行中且玩家点击侧边栏“暂停对决”按钮
- **THEN** 系统 SHALL 立即挂起自对弈时序回路，并保持当前棋盘与状态，直到玩家再次点击“继续对决”。

### Requirement: 对决局中双 AI 独立搜索参数与算法引擎动态注入
系统 SHALL 允许为黑白双方 AI 分别配置独立的决策引擎（例如：KataGomo MCTS 神经网络引擎 vs 启发式 MiniMax+VCF 算杀引擎）与搜索参数（如 visits、policyBlend、valueBlend）。在每次轮到特定 AI 落子前，系统 SHALL 通过 `SetKataEnabled` 和 `SetKataSearchParams` 动态且实时地向底层 DLL 引擎注入该 AI 的配置，以执行对应的着法搜索。

#### Scenario: 轮流注入专属搜索参数与引擎切换
- **WHEN** 进入黑方 AI（Visits=256, 神经网络模式）的决策步骤
- **THEN** 系统 SHALL 自动调用 `SetKataEnabled(env, True)` 并且调用 `SetKataSearchParams(env, 256, 0.0, 0.6, 0.6)`，然后执行 `GetTopMoves` 搜索着法。
- **WHEN** 进入白方 AI（启发式 MiniMax, 禁用神经网络模式）的决策步骤
- **THEN** 系统 SHALL 自动调用 `SetKataEnabled(env, False)` 并且调用 `SetKataSearchParams(env, 0, 0.0, 0.0, 0.0)`，然后使用 MiniMax 算法搜索着法。
